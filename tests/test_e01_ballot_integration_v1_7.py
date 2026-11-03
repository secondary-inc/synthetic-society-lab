"""Authored DE/NE integration/lifecycle fixtures, not source acquisition/results."""
import copy
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from civiclab.common import canonical_hash, sha256_file
from civiclab.e01 import ballots_v1_7 as v
from civiclab.reproduction import build_package
from tests.test_e01_delaware_v1_7 import html,book,INDEX
from tests.test_e01_nebraska_v1_7 import boxes

REPO=Path(__file__).resolve().parents[1]


def baseline_report():
    rosters={s:{'state':s,'candidates':[{'official_name':'DEMO PRIOR '+s,'party_class':'UNSPECIFIED'}],
        'source_hashes':['0'*64],'observations':{'final_ballot_accepted':False}} for s in 'AK CO IA KS ME NC NH NJ VA WY'.split()}
    return {'status':'READINESS_PARTIAL_NOT_SOURCE_OR_SAMPLE_ACCEPTANCE','scope':'OFFICIAL_BALLOT_READINESS_ONLY',
        'local_only_rosters':rosters,'regular_frame_slots':33,'source_hash_checks':29,'official_rosters_extracted':10,
        'candidate_observations':[{'state':s,'status':'PENDING'} for s in v.base.CLASS_II_STATES],
        'context_contests':[],'context_observations':{},'source_adoption':False,'actual_selection':False,
        'final_ballots_accepted':0,'cost_usd':0,'model_calls':0}


class FakePDF:
    def __init__(self):
        self.pages=[SimpleNamespace(rotation=90,width=792,height=612,extract_words=boxes)]+[None]*23
        self.metadata={'CreationDate':"D:20260916164704-05'00'",'ModDate':"D:20260916164704-05'00'"}
    def __enter__(self):return self
    def __exit__(self,*a):return False


def fixture(root):
    contract=json.loads((REPO/v.CONTRACT_PATH).read_text())
    raw={s['source_id']:root/s['path'] for s in contract['sources']}
    for p in raw.values():p.parent.mkdir(parents=True,exist_ok=True)
    raw['de_index'].write_text(INDEX);raw['de_general'].write_text(html());raw['de_writeins'].write_text(html(writein=True));book(raw['de_general_xlsx'])
    raw['ne_index'].write_text('/Final_Statewide_General_Candidate_Filing_List_9.11.26.pdf');raw['ne_general'].write_bytes(b'DEMO geometry PDF placeholder')
    for s in contract['sources']:s.update(bytes=raw[s['source_id']].stat().st_size,sha256=sha256_file(raw[s['source_id']]))
    base=json.loads((REPO/v.BASE_PATH).read_text())
    for relative in v.PIN_PATHS:
        p=root/relative;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((REPO/relative).read_bytes())
    (root/v.BASE_PATH).write_text(json.dumps(base));(root/v.CONTRACT_PATH).write_text(json.dumps(contract))
    config=json.loads((REPO/'configs/e01_ballot_readiness_v1_7.json').read_text())
    config['frozen_input_hashes']={p:sha256_file(root/p) for p in v.PIN_PATHS}
    return config,raw


def fixture_runtime(root,config):
    stack=ExitStack()
    stack.enter_context(patch.object(v,'BASE_SHA',config['frozen_input_hashes'][v.BASE_PATH]))
    stack.enter_context(patch.object(v,'CONTRACT_SHA',config['frozen_input_hashes'][v.CONTRACT_PATH]))
    for module in (v.base,v.de,v.ne):stack.enter_context(patch.object(module,'__file__',str(root/('src/'+module.__name__.replace('.','/')+'.py'))))
    fake=SimpleNamespace(__version__='0.11.9',open=lambda path:FakePDF())
    stack.enter_context(patch.dict('sys.modules',{'pdfplumber':fake}))
    stack.enter_context(patch.object(v.base,'validate_readiness',side_effect=lambda *a:baseline_report()))
    return stack


class IntegrationTests(unittest.TestCase):
    def test_fixture_full_admission_readers_replay_prior_rosters_and_literal_context(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c,raw=fixture(root)
            with fixture_runtime(root,c):paths=[v.run_readiness(root,c),v.run_readiness(root,c)]
            for name in ['ballot_readiness.json','candidate_rosters.local.json']:self.assertEqual((paths[0]/name).read_bytes(),(paths[1]/name).read_bytes())
            public=json.loads((paths[0]/'ballot_readiness.json').read_text());local=json.loads((paths[0]/'candidate_rosters.local.json').read_text())
            for s,roster in baseline_report()['local_only_rosters'].items():self.assertEqual(local[s],roster)
            self.assertEqual((public['source_hash_checks'],public['official_rosters_extracted'],public['preserved_prior_roster_count']),(35,12,10))
            d,n=local['DE'],local['NE'];self.assertEqual((d['printed_candidates'],d['declared_write_ins']),(2,3))
            self.assertEqual([r['source_status_literal'] for r in d['candidates']],['Qualified']*5)
            self.assertTrue(all(r['source_party_label'] is None and r['party_class']=='UNSPECIFIED' for r in d['candidates'][2:]))
            self.assertTrue(all(r['filing_date_printed']=='2026-06-12' for r in d['candidates']))
            self.assertEqual(n['source_printed_edition'],'2026-09-11');self.assertEqual(n['pdf_creation_metadata'],"D:20260916164704-05'00'")
            self.assertEqual([r['source_party_label'] for r in n['candidates']],['Republican','Legal Marijuana NOW','Nebraska Working People','America First','By Petition'])
            self.assertEqual([r['party_class'] for r in n['candidates']],['R']+['UNSPECIFIED']*4)
            self.assertFalse(n['observations']['one_observed_D_and_R']);self.assertEqual(public['final_ballots_accepted'],0)
            for token in ['DEMO PRIVATE CONTACT','DEMO RESIDENCE','DEMO CITY']:self.assertNotIn(token,json.dumps(local))
            self.assertNotIn('DEMO A',json.dumps(public));self.assertNotIn('DEMO NAME',json.dumps(public))
            self.assertFalse(public['actual_selection']);self.assertFalse(public['source_adoption'])
            with self.assertRaisesRegex(ValueError,'local-only'):build_package(root,root/'pack.zip',[paths[0].name])

    def test_secret_or_extra_metadata_refused_before_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c,_=fixture(root)
            for change in [lambda q:q.update(url='https://user:SYNTHETIC_SECRET@fixture.gov'),
                           lambda q:q['frozen_input_hashes'].update({'https://fixture.gov/?key=SYNTHETIC_SECRET':'0'*64}),
                           lambda q:q['frozen_input_hashes'].update({v.BASE_PATH:'SYNTHETIC_SECRET'}),
                           lambda q:q.update(geometry_runtime={'engine':'pdfplumber','version':'SYNTHETIC_SECRET'}),
                           lambda q:q.update(source_adoption=True),lambda q:q.update(schema_version=True)]:
                altered=copy.deepcopy(c);change(altered)
                with fixture_runtime(root,c),patch.object(v,'RunStore') as store,self.assertRaises(ValueError):v.run_readiness(root,altered)
                store.assert_not_called()
            self.assertFalse((root/'data/processed/runs').exists())

    def test_source_implementation_or_contract_drift_fails_and_seals(self):
        for key in ['de_index','de_general','de_writeins','de_general_xlsx','ne_index','ne_general','src/civiclab/e01/delaware_v1_7.py',v.CONTRACT_PATH,v.BASE_PATH]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);c,raw=fixture(root);p=raw.get(key,root/key);p.write_bytes(p.read_bytes()+b'ALTERED')
                with fixture_runtime(root,c),self.assertRaises(ValueError):v.run_readiness(root,c)
                self.assert_failure(root,'ValueError')

    def test_runtime_absent_or_wrong_version_and_actual_reader_identity_refused(self):
        for mode in ['absent','version','reader']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);c,_=fixture(root)
                with fixture_runtime(root,c),ExitStack() as stack:
                    if mode=='absent':stack.enter_context(patch.object(v.importlib,'import_module',side_effect=ImportError('SYNTHETIC_SECRET')))
                    elif mode=='version':stack.enter_context(patch.object(v.importlib,'import_module',return_value=SimpleNamespace(__version__='0.0')))
                    else:stack.enter_context(patch.object(v.ne,'read_pdf',return_value={'geometry_engine':'unknown','geometry_engine_version':'0.11.9'}))
                    with self.assertRaises(RuntimeError):v.run_readiness(root,c)
                self.assert_failure(root,'RuntimeError')

    def assert_failure(self,root,kind):
        runs=list((root/'data/processed/runs').iterdir());self.assertEqual(len(runs),1);run=runs[0]
        self.assertEqual(json.loads((run/'failure.json').read_text()),{'status':'FAILED','error_type':kind})
        self.assertEqual(json.loads((run/'summary.json').read_text())['status'],'FAILED')
        self.assertFalse((run/'ballot_readiness.json').exists());self.assertFalse((run/'candidate_rosters.local.json').exists())
        for name,digest in json.loads((run/'checksums.json').read_text()).items():self.assertEqual(sha256_file(run/name),digest)
        for p in run.iterdir():
            if p.is_file():self.assertNotIn(b'SYNTHETIC_SECRET',p.read_bytes())

    def test_cancellation_and_parser_failures_preserved_type_only(self):
        for exception in [RuntimeError('SYNTHETIC_SECRET'),KeyboardInterrupt('SYNTHETIC_SECRET'),SystemExit('SYNTHETIC_SECRET')]:
            for reader in [(v.de,'reconcile'),(v.ne,'read_pdf')]:
                with tempfile.TemporaryDirectory() as td:
                    root=Path(td);c,_=fixture(root)
                    with fixture_runtime(root,c),patch.object(reader[0],reader[1],side_effect=exception),self.assertRaises(type(exception)):v.run_readiness(root,c)
                    self.assert_failure(root,type(exception).__name__)

    def test_mid_read_source_mutation_refused_before_successful_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c,raw=fixture(root);original=v.de.reconcile
            def mutate(*args):
                result=original(*args);raw['de_general'].write_bytes(b'ALTERED');return result
            with fixture_runtime(root,c),patch.object(v.de,'reconcile',side_effect=mutate),self.assertRaises(ValueError):v.run_readiness(root,c)
            self.assert_failure(root,'ValueError')

    def test_input_symlink_or_import_origin_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c,raw=fixture(root);p=raw['de_index'];other=p.with_name('copy.html');p.rename(other);p.symlink_to(other.name)
            with fixture_runtime(root,c),self.assertRaisesRegex(ValueError,'symlink'):v.verify_inputs(root,c)
            p.unlink();other.rename(p)
            with fixture_runtime(root,c),patch.object(v.ne,'__file__','/tmp/foreign/nebraska_v1_7.py'),self.assertRaisesRegex(ValueError,'origin'):v.verify_inputs(root,c)

    def test_source_contract_substitution_even_with_new_file_pin_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c,_=fixture(root)
            altered=copy.deepcopy(c);altered['frozen_input_hashes'][v.CONTRACT_PATH]='0'*64
            with fixture_runtime(root,c),self.assertRaisesRegex(ValueError,'original input'):v.admit_metadata(altered)


if __name__=='__main__':unittest.main()
