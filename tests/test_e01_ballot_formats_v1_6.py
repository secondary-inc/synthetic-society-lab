"""Authored exact-shape IA/NH text fixtures plus synthetic pipeline lifecycle."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civiclab.e01 import ballots as b
from civiclab.e01 import ballot_formats_v1_6 as f
from tests.test_e01_ballots import ledger,write_source

IA_INDEX='November 3, 2026 General Election\nCandidate List\nCandidates are only added after review and acceptance'
NH_INDEX='2026 General Election Candidates\nVacancies Created Following the State Primary 2026\nWithdrawals'


def ia():
    first='Candidate List\nNovember 3, 2026 General Election\nFor the Office Of…  Party  Ballot Name(s)  Address  Phone  Email  Filing Date\nUnited States Senator  Republican  DEMO ALPHA  DEMO ADDRESS  DEMO PHONE  demo@example.invalid  6/2/2026\n  Democratic  DEMO BETA  DEMO ADDRESS  DEMO PHONE  demo@example.invalid  6/2/2026\n  DEMO LABEL  DEMO GAMMA  DEMO ADDRESS  DEMO PHONE  demo@example.invalid  6/2/2026\nUnited States Representative District 1  DEMO HOUSE\n8/19/2026 1:36 PM'
    return [first]+['DEMO OTHER PAGE']*13


def positioned(values,starts):
    line=''
    for value,start in zip(values,starts):
        if len(line)>start:raise ValueError('authored fixture overlaps columns')
        line+=' '*(start-len(line))+value
    return line


def nh():
    header=positioned(['Candidate Name','Domicile','Candidate Address','City/State/Zip','Party'],[0,31,54,93,130])
    rows=[positioned(['DEMO ALPHA','DEMO CITY','DEMO ADDRESS','DEMO STATE ZIP','DEM'],[0,32,55,93,130]),
          positioned(['DEMO BETA','DEMO CITY','DEMO ADDRESS','DEMO STATE ZIP','REP'],[0,32,55,93,130]),
          ' '*55+'PO BOX 42',
          positioned(['DEMO GAMMA','DEMO CITY','DEMO ADDRESS','DEMO STATE ZIP','DEMO CODE'],[0,32,55,93,130])]
    first='CANDIDATE LIST W/ ADDRESS - 09/17/2026\n'+header+'\nUnited States Senator\n'+'\n'.join(rows)+'\nRepresentative in Congress\nDEMO HOUSE'
    return [first]+['DEMO OTHER PAGE']*45


def vacancy():return ['Vacancies Created Following the State Primary - 2026\nSTATE OFFICE DEMO']


def withdrawals():return ['Withdrawals - 2026\nSTATE OFFICE DEMO']


def config(root):
    c=ledger(root)
    specs=[('ia_general','OFFICIAL_CANDIDATE_LIST'),('ia_index_browser','OFFICIAL_CANDIDATE_INDEX'),
           ('nh_general','OFFICIAL_CANDIDATE_LIST'),('nh_index_browser','OFFICIAL_CANDIDATE_INDEX'),
           ('nh_post_primary_vacancies','OFFICIAL_POST_PRIMARY_VACANCY_CONTEXT'),('nh_withdrawals','OFFICIAL_FILING_WITHDRAWAL_CONTEXT')]
    for name,role in specs:
        data=IA_INDEX.encode() if name=='ia_index_browser' else NH_INDEX.encode() if name=='nh_index_browser' else b'DEMO PDF'
        source=write_source(root,name,data,role);source['capture_kind']='BROWSER_VISIBLE_TEXT_UTF8_NOT_HTTP_WIRE_BYTES' if 'index'in name else 'BROWSER_DOWNLOAD_BYTES';c['sources'].append(source)
    next(x for x in c['class_II_frame'] if x['state']=='IA')['candidate_source_ids']=[x[0] for x in specs[:2]]
    next(x for x in c['class_II_frame'] if x['state']=='NH')['candidate_source_ids']=[x[0] for x in specs[2:]]
    return c


def pdf(path):return {'ia_general':ia(),'nh_general':nh(),'nh_post_primary_vacancies':vacancy(),'nh_withdrawals':withdrawals()}[path.name]


class NewRosterTests(unittest.TestCase):
    def test_iowa_three_literal_labels_bounded_no_contacts(self):
        r=f.extract_ia_senate(ia(),IA_INDEX);self.assertEqual(len(r['candidates']),3)
        self.assertEqual([x['source_party_label'] for x in r['candidates']],['Republican','Democratic','DEMO LABEL'])
        self.assertEqual(r['candidates'][-1]['party_class'],'UNSPECIFIED')
        for value in ['DEMO ADDRESS','DEMO PHONE','demo@example.invalid','DEMO HOUSE']:self.assertNotIn(value,str(r))

    def test_iowa_wrong_header_stage_date_truncation_duplicate_and_boundary_refused(self):
        for old,new in [('2026 General Election','2024 General Election'),('Ballot Name(s)','Unknown Column'),
                        ('8/19/2026','8/20/2026'),('6/2/2026','9/1/2026'),('DEMO BETA','DEMO ALPHA'),
                        ('United States Representative District 1','STATE HOUSE')]:
            p=ia();p[0]=p[0].replace(old,new)
            with self.assertRaises(ValueError):f.extract_ia_senate(p,IA_INDEX)
        with self.assertRaises(ValueError):f.extract_ia_senate(ia()[:-1],IA_INDEX)
        with self.assertRaises(ValueError):f.extract_ia_senate(ia(),IA_INDEX.replace('2026','2024'))

    def test_new_hampshire_index_stage_and_pdf_edition_literal_unknown_no_contacts(self):
        r=f.extract_nh_senate(nh(),NH_INDEX,vacancy(),withdrawals())
        self.assertEqual([x['party_class'] for x in r['candidates']],['D','R','UNSPECIFIED'])
        self.assertEqual(r['candidates'][-1]['source_party_label'],'DEMO CODE')
        self.assertEqual(r['general_stage_evidence'],'OFFICIAL_INDEX_LINK_NOT_PDF_BODY_STAMP')
        self.assertIn('NOT_ABSENCE_OF_AMENDMENTS',r['context_observation'])
        for value in ['DEMO CITY','DEMO ADDRESS','DEMO STATE ZIP','DEMO HOUSE']:self.assertNotIn(value,str(r))

    def test_nh_context_possible_senate_change_not_silently_excluded(self):
        with self.assertRaises(ValueError):f.extract_nh_senate(nh(),NH_INDEX,vacancy()+vacancy(),withdrawals())
        with self.assertRaises(ValueError):f.extract_nh_senate(nh(),NH_INDEX,vacancy(),['Withdrawals - 2026\nUnited States Senator DEMO'])
        with self.assertRaises(ValueError):f.extract_nh_senate(nh(),NH_INDEX,vacancy(),['Other document'])
        with self.assertRaises(ValueError):f.extract_nh_senate(nh(),NH_INDEX.replace('General','Primary'),vacancy(),withdrawals())
        for old,new in [('09/17/2026','09/18/2026'),('DEMO BETA','DEMO ALPHA'),('Representative in Congress','STATE HOUSE')]:
            p=nh();p[0]=p[0].replace(old,new)
            with self.assertRaises(ValueError):f.extract_nh_senate(p,NH_INDEX,vacancy(),withdrawals())

    def test_nh_exact_column_continuation_bound_to_second_candidate_omitted(self):
        r=f.extract_nh_senate(nh(),NH_INDEX,vacancy(),withdrawals())
        self.assertEqual(r['omitted_address_continuation_count'],1)
        self.assertEqual(len(r['candidates']),3);self.assertNotIn('PO BOX 42',str(r))
        self.assertEqual([x['official_name'] for x in r['candidates']],['DEMO ALPHA','DEMO BETA','DEMO GAMMA'])

    def test_nh_one_field_name_party_overlap_unknown_and_duplicate_continuations_refused(self):
        original=' '*55+'PO BOX 42'
        variants=['DEMO EXTRA NAME',' '*130+'DEM',' '*55+'DEMO EXTRA NAME',' '*55+'UNKNOWN 42',
                  ' '*54+'PO BOX 42',' '*90+'PO BOX 42',' '*55+'PO  BOX 42',original+'\n'+original]
        for replacement in variants:
            p=nh();p[0]=p[0].replace(original,replacement)
            with self.subTest(layout=replacement[:8]),self.assertRaises(ValueError):f.extract_nh_senate(p,NH_INDEX,vacancy(),withdrawals())
        p=nh();p[0]=p[0].replace(original+'\n','')
        with self.assertRaises(ValueError):f.extract_nh_senate(p,NH_INDEX,vacancy(),withdrawals())

    def test_nh_continuation_requires_preceding_second_complete_candidate(self):
        original=' '*55+'PO BOX 42'
        p=nh();p[0]=p[0].replace(original+'\n','').replace('United States Senator\n','United States Senator\n'+original+'\n')
        with self.assertRaises(ValueError):f.extract_nh_senate(p,NH_INDEX,vacancy(),withdrawals())
        p=nh();lines=p[0].splitlines();idx=lines.index(original);lines[idx-1],lines[idx]=lines[idx],lines[idx-1];p[0]='\n'.join(lines)
        with self.assertRaises(ValueError):f.extract_nh_senate(p,NH_INDEX,vacancy(),withdrawals())
        p=nh();p[0]=p[0].replace('Candidate Address','Wrong Address')
        with self.assertRaises(ValueError):f.extract_nh_senate(p,NH_INDEX,vacancy(),withdrawals())

    def test_integrated_fixture_roles_and_replay_no_acceptance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c=config(root)
            with patch.object(b,'pdf_pages',side_effect=pdf):ps=[b.run_readiness(root,c),b.run_readiness(root,c)]
            for n in ['ballot_readiness.json','candidate_rosters.local.json']:self.assertEqual((ps[0]/n).read_bytes(),(ps[1]/n).read_bytes())
            r=json.loads((ps[0]/'ballot_readiness.json').read_text());self.assertEqual((r['regular_frame_slots'],r['official_rosters_extracted']),(33,2))
            self.assertEqual(r['final_ballots_accepted'],0);self.assertFalse(r['source_adoption']);self.assertNotIn('DEMO ALPHA',str(r))
            for mutate in [lambda q:q['sources'][1].update(source_role='OFFICIAL_CANDIDATE_INDEX'),lambda q:q['sources'][-1].update(source_role='OFFICIAL_CANDIDATE_LIST'),lambda q:q['sources'][1].update(capture_kind='HTTP_RESPONSE_BYTES')]:
                d=copy.deepcopy(c);mutate(d)
                with patch.object(b,'pdf_pages',side_effect=pdf),self.assertRaises(ValueError):b.validate_readiness(root,d)

    def test_secretmetadata_refused_and_admitted_parser_cancel_failure_sealed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c=config(root);bad=copy.deepcopy(c);bad['sources'][1]['url']='https://user:DEMO_SECRET@fixture.gov/source'
            with patch.object(b,'RunStore') as store,self.assertRaises(ValueError):b.run_readiness(root,bad)
            store.assert_not_called()
        for exc in [RuntimeError('DEMO_SECRET'),KeyboardInterrupt('DEMO_SECRET')]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);c=config(root)
                with patch.object(b,'pdf_pages',side_effect=pdf),patch.object(b,'extract_ia_senate',side_effect=exc),self.assertRaises(type(exc)):b.run_readiness(root,c)
                run=list((root/'data/processed/runs').iterdir())[0];self.assertEqual(json.loads((run/'summary.json').read_text())['status'],'FAILED')
                self.assertFalse((run/'ballot_readiness.json').exists());self.assertFalse((run/'candidate_rosters.local.json').exists())
                for name,h in json.loads((run/'checksums.json').read_text()).items():self.assertEqual(hashlib.sha256((run/name).read_bytes()).hexdigest(),h)
                self.assertTrue(all('DEMO_SECRET' not in p.read_text() for p in run.iterdir() if p.is_file()))


if __name__=='__main__':unittest.main()
