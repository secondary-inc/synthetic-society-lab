"""Authored synthetic text/hash fixtures; no real raw sources required in CI."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab.e01 import ballots as b


def nj_fixture():
    names=[('DEMO ALPHA','Democratic'),('DEMO BETA','Republican'),('DEMO GAMMA','DEMO PETITION'),('DEMO DELTA','DEMO GROUP')]
    pages=[]
    for i,(name,party) in enumerate(names,1):
        pages.append(f'07/27/2026  Official List  Page {i} of 5\nCandidates for US Senate\nFor GENERAL ELECTION 11/03/2026 Election, * denotes incumbent\nName  Address  Party  County  Slogan\n{name}  100 DEMO ROAD  {party}\n')
    pages.append('07/27/2026  Official List  Page 5 of 5\nCandidates for US Senate\nFor GENERAL ELECTION 11/03/2026 Election, * denotes incumbent\nCandidate Totals for Party\nTotal Candidates  4\n')
    return pages


def nc_fixture():
    header='CANDIDATE NAME'.ljust(35)+'NAME ON BALLOT'.ljust(35)+'PARTY'.ljust(10)+'FILING DATE  ADDRESS'
    def row(name,party):return name.ljust(35)+name.ljust(35)+party.ljust(10)+'01/01/2026  100 DEMO ROAD'
    return ['Election: 11/03/2026\n'+header+'\nUS SENATE\n'+row('DEMO ALPHA','DEM')+'\n'+row('DEMO BETA','REP')+'\n'+row('DEMO GAMMA','GRE')+'\nUS HOUSE OF REPRESENTATIVES DISTRICT 01\n'+row('DEMO HOUSE','REP')]


def write_source(root,key,data,role='OFFICIAL_CANDIDATE_LIST'):
    path=Path(root)/'data/raw'/key;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    return {'source_id':key,'url':'https://fixture.gov/'+key,'path':str(path.relative_to(root)),
            'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'retrieved_at_utc':'2026-11-03T12:00:00Z',
            'capture_kind':'HTTP_RESPONSE_BYTES','source_role':role,'published_date':'2026-07-27',
            'status':'DEMO_FIXTURE_PENDING_REVIEW','response_headers':{}}


def ledger(root):
    text='Class II January 3, 2021 January 3, 2027\n'+'\n'.join('(D-'+s+')' for s in b.CLASS_II_STATES)
    source=write_source(root,'senate_class_II',text.encode(),'OFFICIAL_CLASS_IDENTITY')
    rows=[{'state':s,'contest_id':f'2026-{s}-SENATE-C2','seat_class':2,'election_date':'2026-11-03',
           'scope':'REGULAR_CLASS_II_FRAME','candidate_source_ids':[],'amendment_review':'PENDING','independent_ballot_review':'PENDING'} for s in b.CLASS_II_STATES]
    return {'schema_version':1,'scope':'OFFICIAL_BALLOT_READINESS_ONLY','source_adoption':False,'sources':[source],
            'class_identity_source_id':'senate_class_II','class_II_frame':rows,
            'context_contests':[{'contest_id':x,'scope':'CONTEXT_OUTSIDE_REGULAR_QUOTAS','official_source_ids':[],
                                 'status':'DEMO_PENDING','reason':'DEMO context metadata, never quota filler'} for x in sorted(b.CONTEXT_IDS)]}


class BallotExtractorTests(unittest.TestCase):
    def test_nj_all_pages_and_publication_date_not_election_date(self):
        roster=b.extract_nj_senate(nj_fixture())
        self.assertEqual(len(roster['candidates']),4)
        self.assertEqual(roster['publication_date_printed'],'07/27/2026')
        self.assertEqual([r['party_class'] for r in roster['candidates']],['D','R','UNSPECIFIED','UNSPECIFIED'])
        self.assertEqual([r['source_party_label'] for r in roster['candidates']],
                         ['Democratic','Republican','DEMO PETITION','DEMO GROUP'])
        self.assertNotIn('100 DEMO ROAD',json.dumps(roster))
        self.assertFalse(b.roster_observations(roster)['final_ballot_accepted'])

    def test_nj_refuses_missing_reordered_duplicate_total_wrong_office_and_ambiguous_names(self):
        for mutate in [lambda p:p.pop(),lambda p:p.reverse(),lambda p:p.__setitem__(1,p[1].replace('DEMO BETA','DEMO ALPHA')),
                       lambda p:p.__setitem__(4,p[4].replace('Candidates  4','Candidates  5')),
                       lambda p:p.__setitem__(0,p[0].replace('US Senate','State Senate')),
                       lambda p:p.__setitem__(0,p[0].replace('11/03/2026','11/05/2024')),
                       lambda p:p.__setitem__(0,p[0].replace('DEMO ALPHA','DEMO  ALPHA'))]:
            pages=nj_fixture();mutate(pages)
            with self.assertRaises(ValueError):b.extract_nj_senate(pages)

    def test_nc_exact_senate_block_not_house_or_state_senate(self):
        roster=b.extract_nc_senate(nc_fixture())
        self.assertEqual([r['official_name'] for r in roster['candidates']],['DEMO ALPHA','DEMO BETA','DEMO GAMMA'])
        self.assertEqual(b.roster_observations(roster)['observed_party_class_counts'],{'D':1,'R':1,'OTHER':1})
        self.assertNotIn('DEMO HOUSE',json.dumps(roster));self.assertNotIn('100 DEMO ROAD',json.dumps(roster))
        for old,new in [('US SENATE','NC STATE SENATE'),('11/03/2026','05/05/2026'),('GRE','ZZZ')]:
            with self.assertRaises(ValueError):b.extract_nc_senate([nc_fixture()[0].replace(old,new)])
        with self.assertRaises(ValueError):b.extract_nc_senate([nc_fixture()[0].split('US HOUSE')[0]])

    def test_nc_duplicate_and_partial_candidate_refused(self):
        for text in [nc_fixture()[0].replace('DEMO BETA','DEMO ALPHA'),nc_fixture()[0].replace('DEM'.ljust(10),' '.ljust(10))]:
            with self.assertRaises(ValueError):b.extract_nc_senate([text])

    def test_html_scripts_do_not_become_document_facts(self):
        text=b.visible_html_text(b'<p>REAL DOCUMENT</p><script>FALSE ELECTION</script><style>BAD</style>')
        self.assertEqual(text,'REAL DOCUMENT')


class BallotReadinessTests(unittest.TestCase):
    def test_all_33_slots_preserved_pending_not_claimed_complete(self):
        with tempfile.TemporaryDirectory() as td:
            report=b.validate_readiness(Path(td),ledger(Path(td)))
            self.assertEqual(report['regular_frame_slots'],33)
            self.assertEqual(len(report['candidate_observations']),33)
            self.assertEqual(report['official_rosters_extracted'],0)
            self.assertFalse(report['source_adoption']);self.assertFalse(report['actual_selection'])
            self.assertEqual(report['final_ballots_accepted'],0)

    def test_hash_paths_dates_roles_and_headers_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=ledger(root);original=config['sources'][0]
            for changes in [{'sha256':'0'*64},{'bytes':-1},{'path':'../outside'},
                            {'url':'https://user:password@fixture.gov/a'},{'url':'https://example.com/a'},
                            {'retrieved_at_utc':'2026-11-03'},{'source_role':'FEC_REGISTRATION'},
                            {'capture_kind':'WIRE_BYTES_ASSUMED_FROM_BROWSER'},{'response_headers':{'Set-Cookie':'secret'}}]:
                with self.assertRaises(ValueError):b.verify_source(root,{**original,**changes})
            (root/original['path']).write_text('modified official source')
            with self.assertRaises(ValueError):b.validate_readiness(root,config)

    def test_no_missing_duplicate_or_context_in_regular_frame(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=ledger(root)
            for mutate in [lambda c:c['class_II_frame'].pop(),lambda c:c['class_II_frame'].__setitem__(0,c['class_II_frame'][1]),
                           lambda c:c['class_II_frame'][0].update(state='OH'),
                           lambda c:c['context_contests'][0].update(scope='REGULAR_CLASS_II_FRAME'),
                           lambda c:c['class_II_frame'][0].update(amendment_review='ACCEPTED'),
                           lambda c:c.update(source_adoption=True),lambda c:c['class_II_frame'][0].update(observed_votes=100)]:
                changed=copy.deepcopy(config);mutate(changed)
                with self.assertRaises(ValueError):b.validate_readiness(root,changed)

    def test_nj_certification_must_match_roster_and_no_fec_substitution(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=ledger(root)
            for name,role in [('nj_senate','OFFICIAL_CANDIDATE_LIST'),('nj_nominee_certification','OFFICIAL_NOMINEE_CERTIFICATION')]:
                config['sources'].append(write_source(root,name,b'DEMO PDF placeholder',role))
            row=next(x for x in config['class_II_frame'] if x['state']=='NJ');row['candidate_source_ids']=['nj_senate','nj_nominee_certification']
            with patch.object(b,'pdf_pages',side_effect=lambda path:['CERTIFICATION']+nj_fixture() if path.name=='nj_nominee_certification' else nj_fixture()):
                report=b.validate_readiness(root,config)
                self.assertEqual(report['official_rosters_extracted'],1)
                self.assertEqual(report['final_ballots_accepted'],0)
            mismatch=nj_fixture();mismatch[0]=mismatch[0].replace('DEMO ALPHA','DEMO OTHER')
            with patch.object(b,'pdf_pages',side_effect=lambda path:['CERTIFICATION']+mismatch if path.name=='nj_nominee_certification' else nj_fixture()):
                with self.assertRaisesRegex(ValueError,'disagree'):b.validate_readiness(root,config)
            # Same names and normalized classes must not hide a literal-label change.
            mismatch=nj_fixture();mismatch[2]=mismatch[2].replace('DEMO PETITION','DEMO ALTERNATE PETITION')
            with patch.object(b,'pdf_pages',side_effect=lambda path:['CERTIFICATION']+mismatch if path.name=='nj_nominee_certification' else nj_fixture()):
                with self.assertRaisesRegex(ValueError,'disagree'):b.validate_readiness(root,config)
            row['candidate_source_ids']=['senate_class_II']
            with self.assertRaisesRegex(ValueError,'not official roster'):b.validate_readiness(root,config)


class BallotFailureLifecycleTests(unittest.TestCase):
    def assert_sealed_failure(self,root,config,error):
        with patch.object(b,'pdf_pages',side_effect=error):
            with self.assertRaises(type(error)):b.run_readiness(root,config)
        runs=list((root/'data/processed/runs').iterdir());self.assertEqual(len(runs),1)
        run=runs[0]
        self.assertEqual(json.loads((run/'manifest.json').read_text())['config']['config_sha256'],b.canonical_hash(config))
        self.assertEqual(json.loads((run/'failure.json').read_text()),
                         {'status':'FAILED','error_type':type(error).__name__})
        self.assertEqual(json.loads((run/'summary.json').read_text())['status'],'FAILED')
        self.assertFalse((run/'ballot_readiness.json').exists())
        self.assertFalse((run/'candidate_rosters.local.json').exists())
        events=[json.loads(x) for x in (run/'events.jsonl').read_text().splitlines()]
        self.assertTrue(any(x['event']=='failed' and x['error_type']==type(error).__name__ for x in events))
        for name,digest in json.loads((run/'checksums.json').read_text()).items():
            self.assertEqual(hashlib.sha256((run/name).read_bytes()).hexdigest(),digest)
        for path in run.iterdir():
            if path.is_file():self.assertNotIn('SENSITIVE_PARSER_DETAIL',path.read_text())

    def config_with_nj(self,root):
        config=ledger(root)
        config['sources'].append(write_source(root,'nj_senate',b'DEMO PDF placeholder'))
        next(x for x in config['class_II_frame'] if x['state']=='NJ')['candidate_source_ids']=['nj_senate']
        return config

    def test_admitted_parser_exception_sealed_without_details_or_final_result(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.assert_sealed_failure(root,self.config_with_nj(root),RuntimeError('SENSITIVE_PARSER_DETAIL'))

    def test_keyboard_interrupt_sealed_without_final_result(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.assert_sealed_failure(root,self.config_with_nj(root),KeyboardInterrupt('SENSITIVE_PARSER_DETAIL'))

    def test_system_exit_sealed_without_final_result(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.assert_sealed_failure(root,self.config_with_nj(root),SystemExit('SENSITIVE_PARSER_DETAIL'))

    def test_admitted_source_hash_failure_is_sealed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config_with_nj(root)
            config['sources'][0]['sha256']='0'*64
            self.assert_sealed_failure(root,config,ValueError('SENSITIVE_PARSER_DETAIL'))

    def test_secret_metadata_rejected_before_run_or_artifact_creation(self):
        mutations=[{'url':'https://DEMO_USER:SYNTHETIC_SECRET_MARKER@fixture.gov/source'},
                   {'response_headers':{'Set-Cookie':'SYNTHETIC_SECRET_MARKER'}},
                   {'response_headers':{'Authorization':'Bearer SYNTHETIC_SECRET_MARKER'}},
                   {'url':'https://fixture.gov/source?token=SYNTHETIC_SECRET_MARKER'},
                   {'response_headers':{'ETag':'safe\r\nSet-Cookie: SYNTHETIC_SECRET_MARKER'}}]
        for mutation in mutations:
            with self.subTest(metadata_keys=list(mutation)),tempfile.TemporaryDirectory() as td:
                root=Path(td);config=ledger(root);config['sources'][0].update(mutation)
                with patch.object(b,'RunStore') as store,patch.object(b,'pdf_pages') as parser:
                    with self.assertRaises(ValueError):b.run_readiness(root,config)
                    store.assert_not_called();parser.assert_not_called()
                self.assertFalse((root/'data/processed/runs').exists())
                for path in root.rglob('*'):
                    if path.is_file():self.assertNotIn(b'SYNTHETIC_SECRET_MARKER',path.read_bytes())

    def test_success_replay_sealed_with_literal_labels(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);config=self.config_with_nj(root)
            with patch.object(b,'pdf_pages',return_value=nj_fixture()):
                paths=[b.run_readiness(root,config),b.run_readiness(root,config)]
            for name in ['ballot_readiness.json','candidate_rosters.local.json']:
                self.assertEqual((paths[0]/name).read_bytes(),(paths[1]/name).read_bytes())
            roster=json.loads((paths[0]/'candidate_rosters.local.json').read_text())['NJ']
            self.assertEqual(roster['candidates'][2]['source_party_label'],'DEMO PETITION')
            self.assertEqual(roster['candidates'][2]['party_class'],'UNSPECIFIED')


if __name__=='__main__':unittest.main()
