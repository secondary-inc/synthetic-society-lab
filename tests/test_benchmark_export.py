from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civiclab.benchmark_export import CELLS,STATUS,RESOURCE_NOTE,SOURCE_URL,SOURCE_EVIDENCE,project_aggregate,validate_projection,run_projection
from civiclab.common import RunStore,atomic_json,canonical_hash,sha256_file
from civiclab.dashboard import verified_run
from civiclab.reproduction import build_package

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='configs/wyoming_benchmark_projection_schema_v1.json'
METHODS='reports/INDEPENDENT_AUDIT_WYOMING_DISCLOSURE_PROPOSAL_METHODS.json'
ACTUAL='reports/INDEPENDENT_AUDIT_E02_PUMS_WY_ACTUAL.json'
MODULE='src/civiclab/benchmark_export.py'


def fixture():
    error={'variance_sdr':4.,'standard_error':2.,'moe90':3.29,'status':STATUS}
    return {'state':'56','period':'2020-2024five-year','population_fit':'NOT_RUN','person_weight_rescaled':False,
            'total_person_rows':400,'retained_unweighted_count':360,'point_person_weight_sum':720,
            'source':{'archive_sha256':'a'*64,'member_sha256':'b'*64,'actual_uncompressed_bytes':1000},
            'replicate_person_weight_sums':['DO_NOT_EXPORT']*80,'exclusion_counts':{'DO_NOT_EXPORT':1},
            'count_covariance_sdr':{'DO_NOT_EXPORT':1},
            'cells':{key:{'count':30,'weight_sum':60,'point_share':1/12,'low_support':False,
                          'count_uncertainty':deepcopy(error),'share_uncertainty':deepcopy(error),
                          'replicate_sums':['DO_NOT_EXPORT']*80,'allocated_counts':{'DO_NOT_EXPORT':1}}
                     for key in CELLS}}


def provenance():
    result={k:'a'*64 for k in ('checksums_sha256','aggregate_file_sha256','aggregate_canonical_sha256','archive_sha256','member_sha256','projection_config_sha256','projection_schema_sha256','methods_approval_sha256','source_arithmetic_audit_sha256','projection_implementation_sha256','projection_execution_approval_sha256','source_evidence_sha256','source_header_sha256')}
    return result|{'run_id':'e02-'+'a'*32,'source_recorded_at_utc':'2026-11-03T12:00:00+00:00','source_public_url':SOURCE_URL,'source_archive_bytes':100,'source_member_bytes':1000,'source_header_bytes':1876,'source_header_columns':285,'source_elapsed_seconds':.5,'source_process_highwater_rss_bytes':1024,'source_resource_limits_note':RESOURCE_NOTE}


class BenchmarkProjectionTests(unittest.TestCase):
    def setUp(self):self.schema=json.loads((ROOT/SCHEMA).read_text())

    def test_literal_whitelist_and_complete_fixed_cells(self):
        source=fixture();before=deepcopy(source);result=project_aggregate(source,provenance())
        validate_projection(result,self.schema)
        self.assertEqual(source,before);self.assertEqual(len(result['cells']),12)
        self.assertNotIn('DO_NOT_EXPORT',json.dumps(result))
        self.assertEqual(sum(c['point_person_weight_count'] for c in result['cells']),720)
        self.assertEqual(result['scientific_population_gate'],'BLOCKED')

    def test_any_bad_cell_denies_whole_projection(self):
        for field,value in [('count',29),('count',True),('low_support',True),('point_share',float('nan')),('point_share',.5)]:
            with self.subTest(field=field,value=value):
                source=fixture();source['cells'][CELLS[-1]][field]=value
                with self.assertRaises(ValueError):project_aggregate(source,provenance())
        for field,value in [('standard_error',0),('moe90',float('inf')),('status','UNKNOWN')]:
            source=fixture();source['cells'][CELLS[-1]]['share_uncertainty'][field]=value
            with self.assertRaises(ValueError):project_aggregate(source,provenance())
        source=fixture();del source['cells'][CELLS[-1]]
        with self.assertRaises(ValueError):project_aggregate(source,provenance())

    def test_output_schema_and_relational_constraints(self):
        result=project_aggregate(fixture(),provenance())
        mutations=[lambda d:d.update(raw_ids=['PRIVATE']),
                   lambda d:d['cells'][0].update(contact='PRIVATE'),
                   lambda d:d['cells'][0].update(point_share=True),
                   lambda d:d['cells'].__setitem__(1,deepcopy(d['cells'][0])),
                   lambda d:d.update(point_person_weight_total=721)]
        for mutate in mutations:
            value=deepcopy(result);mutate(value)
            with self.assertRaises(ValueError):validate_projection(value,self.schema)

    def setup_runner(self,root):
        aggregate=fixture()
        with RunStore(root,'E02',{'role':'MOCK_SOURCE_FIXTURE'},kind='MOCK') as source:
            source.write('aggregate-local-only.json',aggregate);source.finish({'status':'MOCK'})
        (root/SCHEMA).parent.mkdir(parents=True,exist_ok=True);(root/SCHEMA).write_text(json.dumps(self.schema))
        for name in (METHODS,ACTUAL):atomic_json(root/name,{'scope':'MOCK_FIXTURE_ONLY'})
        (root/MODULE).parent.mkdir(parents=True,exist_ok=True);(root/MODULE).write_bytes((ROOT/MODULE).read_bytes())
        atomic_json(root/SOURCE_EVIDENCE,{'source_archive':{'sha256':'a'*64,'bytes':100,'path':'DO_NOT_EXPORT'},
            'observed_person_member_sha256':'b'*64,'observed_person_member_bytes':1000,
            'header':{'sha256':'d'*64,'bytes':1876,'columns':285},'runs':[{
                'run_id':source.run_id,'aggregate_file_sha256':sha256_file(source.path/'aggregate-local-only.json'),
                'checksums_sha256':sha256_file(source.path/'checksums.json'),'elapsed_seconds':.5,'process_highwater_rss_bytes_macos':1024}]})
        config={'schema_version':1,'stage':'OWNER_REVIEW_PROJECTION_ONLY','source':{
            'run_id':source.run_id,'checksums_sha256':sha256_file(source.path/'checksums.json'),
            'aggregate_file_sha256':sha256_file(source.path/'aggregate-local-only.json'),
            'aggregate_canonical_sha256':canonical_hash(aggregate),'archive_sha256':'a'*64,'member_sha256':'b'*64},
            'output_schema':SCHEMA,'required_files':{name:sha256_file(root/name) for name in (METHODS,ACTUAL,SCHEMA,SOURCE_EVIDENCE,MODULE)},'execution_approval':None}
        atomic_json(root/'configs/wyoming_benchmark_projection_v1.json',config)
        return source.path

    def authorize_mock(self,root):
        path=root/'configs/wyoming_benchmark_projection_v1.json';c=json.loads(path.read_text())
        c['execution_approval']={'path':'reports/INDEPENDENT_AUDIT_MOCK_FIXTURE.json','sha256':'c'*64};atomic_json(path,c)

    def test_gate_and_manifest_then_local_replay_no_premature_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=self.setup_runner(root)
            before=set((root/'data/processed/runs').iterdir())
            with self.assertRaisesRegex(ValueError,'BLOCKED'):run_projection(root,kind='MOCK')
            self.assertEqual(set((root/'data/processed/runs').iterdir()),before)
            self.authorize_mock(root)
            def observe(aggregate,proof):
                current=[p for p in (root/'data/processed/runs').iterdir() if p not in before]
                self.assertTrue(any((p/'manifest.json').exists() and (p/'projection-config.json').exists() for p in current))
                return project_aggregate(aggregate,proof)
            with patch('civiclab.benchmark_export.require_approval'),patch('civiclab.benchmark_export.project_aggregate',side_effect=observe):
                first=run_projection(root,kind='MOCK');second=run_projection(root,kind='MOCK')
            self.assertEqual((first/'demographic-benchmark.local.json').read_bytes(),(second/'demographic-benchmark.local.json').read_bytes())
            self.assertEqual(verified_run(first)['integrity'],'PASS')
            with self.assertRaisesRegex(ValueError,'local-only'):build_package(root,root/'refused.zip',[first.name])
            self.assertEqual(verified_run(source)['integrity'],'PASS')

    def test_source_drift_and_cancel_seal_failure_without_projection(self):
        for cancel in (False,True):
            with self.subTest(cancel=cancel),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);source=self.setup_runner(root);self.authorize_mock(root)
                def interrupt(aggregate,proof):
                    if cancel:raise KeyboardInterrupt()
                    result=project_aggregate(aggregate,proof)
                    (source/'aggregate-local-only.json').write_text('{"private_marker":"DO_NOT_EXPORT"}')
                    return result
                with patch('civiclab.benchmark_export.require_approval'),patch('civiclab.benchmark_export.project_aggregate',side_effect=interrupt):
                    with self.assertRaises(KeyboardInterrupt if cancel else ValueError):run_projection(root,kind='MOCK')
                failed=next(p for p in (root/'data/processed/runs').iterdir() if p!=source)
                self.assertEqual(verified_run(failed)['summary']['status'],'FAILED')
                self.assertFalse((failed/'demographic-benchmark.local.json').exists())
                self.assertNotIn('DO_NOT_EXPORT',(failed/'failure.json').read_text())

    def test_unadmitted_metadata_cannot_create_run_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_runner(root)
            path=root/'configs/wyoming_benchmark_projection_v1.json';config=json.loads(path.read_text())
            before=set((root/'data/processed/runs').iterdir())
            for mode in ('extra','source_identity','dependency'):
                bad=deepcopy(config)
                if mode=='extra':bad['api_key']='DO_NOT_EXPORT'
                elif mode=='source_identity':bad['source']['run_id']='https://user:DO_NOT_EXPORT@example.com'
                else:bad['required_files']['src/file?token=DO_NOT_EXPORT']='a'*64
                atomic_json(path,bad)
                with patch('civiclab.benchmark_export.RunStore',side_effect=AssertionError('metadata must be rejected before persistence')):
                    with self.assertRaises(ValueError):run_projection(root,kind='MOCK')
                self.assertEqual(set((root/'data/processed/runs').iterdir()),before)
