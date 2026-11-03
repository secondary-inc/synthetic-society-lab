"""Synthetic end-to-end source admission/lifecycle fixtures for Maine integration."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civiclab.e01 import ballots as b
from tests.test_e01_ballots import ledger,write_source
from tests.test_e01_maine_v1_5 import workbook,key,withdraw,ins


def config(root):
    c=ledger(root)
    for name,role in [('me_general','OFFICIAL_CANDIDATE_LIST_XLSX'),('me_withdrawals','OFFICIAL_WITHDRAWAL_REPLACEMENT_LIST'),
                      ('me_writeins','OFFICIAL_DECLARED_WRITE_IN_LIST'),('me_office_key','OFFICIAL_OFFICE_CODE_KEY'),
                      ('me_index_browser','OFFICIAL_CANDIDATE_INDEX')]:
        data=b'DEMO PDF placeholder'
        if name=='me_index_browser':data=b'November 3, 2026 - General Election\n7/27/2026\n09/22/2026\n10/16/26'
        s=write_source(root,name,data,role);s['capture_kind']='BROWSER_VISIBLE_TEXT_UTF8_NOT_HTTP_WIRE_BYTES' if name=='me_index_browser' else 'BROWSER_DOWNLOAD_BYTES'
        if name=='me_general':
            workbook(root/s['path']);raw=(root/s['path']).read_bytes();s.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        c['sources'].append(s)
    next(x for x in c['class_II_frame'] if x['state']=='ME')['candidate_source_ids']=['me_general','me_withdrawals','me_writeins','me_office_key','me_index_browser']
    return c


def pages(path):return {'me_office_key':key(),'me_withdrawals':withdraw(),'me_writeins':ins()}[path.name]


class MaineIntegrationTests(unittest.TestCase):
    def test_complete_five_source_fixture_literal_records_counts_and_replay(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c=config(root)
            with patch.object(b,'pdf_pages',side_effect=pages):paths=[b.run_readiness(root,c),b.run_readiness(root,c)]
            for n in ['ballot_readiness.json','candidate_rosters.local.json']:self.assertEqual((paths[0]/n).read_bytes(),(paths[1]/n).read_bytes())
            public=json.loads((paths[0]/'ballot_readiness.json').read_text());local=json.loads((paths[0]/'candidate_rosters.local.json').read_text())['ME']
            self.assertEqual((public['regular_frame_slots'],public['official_rosters_extracted'],public['source_hash_checks']),(33,1,6))
            self.assertEqual((local['printed_candidates'],local['declared_write_ins'],local['historical_replacement_count']),(2,2,1))
            self.assertEqual([x['party_class'] for x in local['candidates']],['R','D','UNSPECIFIED','UNSPECIFIED'])
            self.assertEqual([x['source_party_label'] for x in local['candidates']],['R','D','Faith in Humanity','Un-enrolled'])
            self.assertEqual(local['writein_pdf_edition'],'2026-10-15');self.assertEqual(local['writein_index_display_date'],'2026-10-16')
            self.assertNotIn('DEMO RESIDENCE',json.dumps(local));self.assertNotIn('DEMO NEW',json.dumps(public))
            self.assertEqual(public['final_ballots_accepted'],0);self.assertFalse(public['source_adoption']);self.assertFalse(public['actual_selection'])
            self.assertTrue(local['maine_reconciliation']['withdrawn_candidates_absent_printed_roster'])

    def test_exact_five_roles_and_representations_not_interchangeable(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c=config(root)
            me=next(x for x in c['class_II_frame'] if x['state']=='ME')
            for mutate in [lambda q:q['class_II_frame'].__setitem__(b.CLASS_II_STATES.index('ME'),{**me,'candidate_source_ids':me['candidate_source_ids'][:-1]}),
                           lambda q:q['sources'][1].update(source_role='OFFICIAL_CANDIDATE_LIST'),
                           lambda q:q['sources'][2].update(source_role='OFFICIAL_DECLARED_WRITE_IN_LIST'),
                           lambda q:q['sources'][3].update(capture_kind='HTTP_RESPONSE_BYTES'),
                           lambda q:q['sources'][-1].update(capture_kind='BROWSER_DOWNLOAD_BYTES')]:
                changed=copy.deepcopy(c);mutate(changed)
                with patch.object(b,'pdf_pages',side_effect=pages),self.assertRaises(ValueError):b.validate_readiness(root,changed)

    def test_secret_bearing_me_metadata_rejected_before_runstore(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c=config(root)
            for update in [{'url':'https://user:SYNTHETIC_ME_SECRET@fixture.gov/file'},
                           {'response_headers':{'Set-Cookie':'SYNTHETIC_ME_SECRET'}},
                           {'url':'https://fixture.gov/file?token=SYNTHETIC_ME_SECRET'},
                           {'response_headers':{'Date':'invented browser header'}}]:
                changed=copy.deepcopy(c);changed['sources'][1].update(update)
                with patch.object(b,'RunStore') as store,self.assertRaises(ValueError):b.run_readiness(root,changed)
                store.assert_not_called()
            self.assertFalse((root/'data/processed/runs').exists())
            self.assertTrue(all(b'SYNTHETIC_ME_SECRET' not in p.read_bytes() for p in root.rglob('*') if p.is_file()))

    def test_admitted_maine_parser_and_cancellation_failures_sealed_type_only(self):
        for exc in [RuntimeError('SYNTHETIC_ME_SECRET'),KeyboardInterrupt('SYNTHETIC_ME_SECRET'),SystemExit('SYNTHETIC_ME_SECRET')]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);c=config(root)
                with patch.object(b,'pdf_pages',side_effect=pages),patch.object(b,'reconcile_maine',side_effect=exc),self.assertRaises(type(exc)):
                    b.run_readiness(root,c)
                run=list((root/'data/processed/runs').iterdir())[0]
                self.assertEqual(json.loads((run/'failure.json').read_text()),{'status':'FAILED','error_type':type(exc).__name__})
                self.assertEqual(json.loads((run/'summary.json').read_text())['status'],'FAILED')
                self.assertFalse((run/'ballot_readiness.json').exists());self.assertFalse((run/'candidate_rosters.local.json').exists())
                for n,h in json.loads((run/'checksums.json').read_text()).items():self.assertEqual(hashlib.sha256((run/n).read_bytes()).hexdigest(),h)
                self.assertTrue(all(b'SYNTHETIC_ME_SECRET' not in p.read_bytes() for p in run.iterdir() if p.is_file()))

    def test_key_or_replacement_disagreement_cannot_emit_final_artifact(self):
        for source,old,new in [('me_office_key','US  US SENATOR','US  STATE SENATOR'),('me_withdrawals','DEMO NEW','DEMO ALTERED')]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);c=config(root)
                def altered(path):return [x.replace(old,new) for x in pages(path)] if path.name==source else pages(path)
                with patch.object(b,'pdf_pages',side_effect=altered),self.assertRaises(ValueError):b.run_readiness(root,c)
                run=list((root/'data/processed/runs').iterdir())[0]
                self.assertFalse((run/'ballot_readiness.json').exists());self.assertEqual(json.loads((run/'summary.json').read_text())['status'],'FAILED')


if __name__=='__main__':unittest.main()
