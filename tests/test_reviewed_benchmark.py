from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civiclab.common import RunStore,atomic_json,canonical_hash,sha256_file
from civiclab.dashboard import verified_run
from civiclab.benchmark_export import project_aggregate,validate_projection
from civiclab.reviewed_benchmark import run_finalization,AUDIT,SCHEMA,CONFIG
from tests.test_benchmark_export import fixture,provenance

ROOT=Path(__file__).resolve().parents[1]
MODULE='src/civiclab/reviewed_benchmark.py'


class ReviewFinalizationTests(unittest.TestCase):
    def setup_fixture(self,root):
        payload=project_aggregate(fixture(),provenance())
        with RunStore(root,'E02',{'role':'MOCK_APPROVED_PROJECTION_FIXTURE'},kind='MOCK') as source:
            source.write('demographic-benchmark.local.json',payload);source.finish({'status':'MOCK'})
        (root/SCHEMA).parent.mkdir(parents=True,exist_ok=True);(root/SCHEMA).write_bytes((ROOT/SCHEMA).read_bytes())
        (root/MODULE).parent.mkdir(parents=True,exist_ok=True);(root/MODULE).write_bytes((ROOT/MODULE).read_bytes())
        row={'run_id':source.run_id,'checksums_sha256':sha256_file(source.path/'checksums.json'),
             'artifact_sha256':sha256_file(source.path/'demographic-benchmark.local.json'),'artifact_canonical_sha256':canonical_hash(payload)}
        atomic_json(root/AUDIT,{'auditor_role':'independent_auditor','status':'PASS_EXACT_WYOMING_OWNER_REVIEW_PROJECTION_OUTPUT',
            'accepted_payload_sha256':row['artifact_sha256'],'accepted_payload_canonical_sha256':row['artifact_canonical_sha256'],
            'accepted_runs':[row],'projection_schema_sha256':sha256_file(root/SCHEMA),'fixture':'MOCK_ONLY'})
        config={'schema_version':1,'stage':'OWNER_REVIEW_BYTE_EXACT_FINALIZATION','source':{
            'run_id':row['run_id'],'checksums_sha256':row['checksums_sha256'],'payload_sha256':row['artifact_sha256'],'canonical_sha256':row['artifact_canonical_sha256']},
            'required_files':{n:sha256_file(root/n) for n in (AUDIT,SCHEMA,MODULE)},'execution_approval':None}
        atomic_json(root/CONFIG,config);return source.path

    def authorize_mock(self,root):
        c=json.loads((root/CONFIG).read_text());c['execution_approval']={'path':'reports/INDEPENDENT_AUDIT_MOCK_FINALIZATION.json','sha256':'d'*64};atomic_json(root/CONFIG,c)

    def test_null_gate_then_byte_exact_new_run_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=self.setup_fixture(root);before=sha256_file(source/'checksums.json')
            with patch('civiclab.reviewed_benchmark.RunStore',side_effect=AssertionError('approval required before persistence')):
                with self.assertRaisesRegex(ValueError,'BLOCKED'):run_finalization(root,kind='MOCK')
            self.authorize_mock(root)
            def observe(value,schema):
                targets=[p for p in (root/'data/processed/runs').iterdir() if p!=source]
                self.assertTrue(any((p/'manifest.json').exists() and (p/'review-config.json').exists() for p in targets))
                validate_projection(value,schema)
            with patch('civiclab.reviewed_benchmark.require_code_approval'),patch('civiclab.reviewed_benchmark.validate_projection',side_effect=observe):
                first=run_finalization(root,kind='MOCK');second=run_finalization(root,kind='MOCK')
            original=(source/'demographic-benchmark.local.json').read_bytes()
            self.assertEqual((first/'demographic-benchmark.json').read_bytes(),original)
            self.assertEqual((second/'demographic-benchmark.json').read_bytes(),original)
            self.assertEqual((first/'review-finalization.json').read_bytes(),(second/'review-finalization.json').read_bytes())
            self.assertEqual(sha256_file(source/'checksums.json'),before)
            self.assertFalse((first/'pending-payload.local.json').exists())
            self.assertEqual(verified_run(first)['integrity'],'PASS')
            trace=json.loads((first/'review-finalization.json').read_text())
            self.assertFalse(trace['external_publication_authorized']);self.assertTrue(trace['owner_review_only'])

    def test_unaccepted_audit_or_metadata_fails_before_runstore(self):
        for mode in ('status','wrong_run','secret_metadata'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.setup_fixture(root)
                c=json.loads((root/CONFIG).read_text());a=json.loads((root/AUDIT).read_text())
                if mode=='status':a['status']='UNREVIEWED'
                elif mode=='wrong_run':a['accepted_runs'][0]['run_id']='e02-'+'f'*32
                else:c['authorization']='PRIVATE_MARKER'
                atomic_json(root/AUDIT,a);c['required_files'][AUDIT]=sha256_file(root/AUDIT);atomic_json(root/CONFIG,c)
                with patch('civiclab.reviewed_benchmark.RunStore',side_effect=AssertionError('rejected metadata persisted')):
                    with self.assertRaises(ValueError):run_finalization(root,kind='MOCK')

    def test_source_drift_and_cancellation_seal_failure_without_public_payload(self):
        for cancel in (False,True):
            with self.subTest(cancel=cancel),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);source=self.setup_fixture(root);self.authorize_mock(root)
                def interrupt(value,schema):
                    validate_projection(value,schema)
                    if cancel:raise KeyboardInterrupt()
                    (source/'demographic-benchmark.local.json').write_text('{"private":"PRIVATE_MARKER"}')
                with patch('civiclab.reviewed_benchmark.require_code_approval'),patch('civiclab.reviewed_benchmark.validate_projection',side_effect=interrupt):
                    with self.assertRaises(KeyboardInterrupt if cancel else ValueError):run_finalization(root,kind='MOCK')
                failed=next(p for p in (root/'data/processed/runs').iterdir() if p!=source)
                self.assertEqual(verified_run(failed)['summary']['status'],'FAILED')
                self.assertFalse((failed/'demographic-benchmark.json').exists())
                self.assertNotIn('PRIVATE_MARKER',(failed/'failure.json').read_text())

    def test_payload_promotion_failure_retains_only_local_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=self.setup_fixture(root);self.authorize_mock(root);link=os.link
            def link_then_fail(first,second):
                link(first,second);raise RuntimeError('PRIVATE_MARKER')
            with patch('civiclab.reviewed_benchmark.require_code_approval'),patch('civiclab.reviewed_benchmark.os.link',side_effect=link_then_fail):
                with self.assertRaises(RuntimeError):run_finalization(root,kind='MOCK')
            failed=next(p for p in (root/'data/processed/runs').iterdir() if p!=source)
            self.assertEqual(verified_run(failed)['summary']['status'],'FAILED')
            self.assertFalse((failed/'demographic-benchmark.json').exists())
            self.assertTrue((failed/'failed-payload.local.json').exists())
            self.assertNotIn('PRIVATE_MARKER',(failed/'failure.json').read_text())
