"""Synthetic-only source gates and independent exhaustive selection oracles."""
import copy
import itertools
import json
import random
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from civiclab.e01 import selection as s


def fixture(house=27,senate=12,seed=0):
    rng=random.Random(seed);states=sorted(set(s.REGIONS)-{'DC'});rows=[]
    for office,n in [('HOUSE',house),('SENATE',senate)]:
        for i in range(n):
            state=states[i%len(states)];district=f'{i//len(states)+1:02d}' if office=='HOUSE' else 'STATEWIDE'
            seat=None if office=='HOUSE' else i//len(states)+1
            rows.append({'race_id':f'DEMO-2026-{state}-HOUSE-{district}' if office=='HOUSE' else f'DEMO-2026-{state}-SENATE-C{seat}',
                'office':office,'state':state,'district':district,'seat_class':seat,
                'band':s.BANDS[i%4] if seed==0 else rng.choice(s.BANDS),
                'sampling_party':('D','R','OTHER')[i%3] if seed==0 else rng.choice(s.PARTIES),
                'eligibility':'ELIGIBLE','exclusion_reason':None,'evidence_refs':['rating','ballot','seat']})
    sources=[{'source_id':k,'source_type':t,'url':f'fixture://DEMO/{k}','sha256':'a'*64,
              'published_at_utc':'2026-11-02T00:00:00Z','first_observed_at_utc':'2026-11-02T01:00:00Z',
              'retrieved_at_utc':'2026-11-03T12:00:00Z','revision':'DEMO-v1','reuse_status':'FIXTURE_AUTHORED',
              'asof_status':'VERIFIED_FIXTURE','amendment_status':'RESOLVED_FIXTURE'}
             for k,t in [('rating','RATINGS'),('ballot','BALLOT'),('seat','SEAT_PARTY')]]
    return {'schema_version':1,'dataset_kind':'DEMO_SELECTION_FIXTURE','algorithm':s.ALGORITHM,'seed':s.SEED,
            'cutoff':s.CUTOFF,'expected_race_ids':[r['race_id'] for r in rows],
            'coverage_status':'COMPLETE_FIXTURE','sources':sources,'rows':rows}


def independent_rank(row):
    import hashlib
    return hashlib.sha256(('E01_2026_SELECTION_PROPOSAL_v1|20261103|'+row['office']+'|'+row['race_id']).encode()).hexdigest(),row['race_id']


def oracle(rows,office,deep=False):
    """No production quota/model/objective/ranking helper called by this oracle."""
    rows=sorted(rows,key=independent_rank)
    bands=('TOSS_UP','LEAN','LIKELY','SOLID');parties=('D','R','OTHER')
    if deep:
        if office=='HOUSE' and {r['band'] for r in rows}!=set(bands):return []
        n=4 if office=='HOUSE' else 2
        if len(rows)<n:return []
    else:n=min(24 if office=='HOUSE' else 8,len(rows))
    best=None;winner=[]
    for combo in itertools.combinations(range(len(rows)),n):
        chosen=[rows[i] for i in combo];present={r['band'] for r in chosen}
        if deep:
            if office=='HOUSE' and present!=set(bands):continue
            if office=='SENATE':
                groups={r['band'] in bands[:2] for r in rows}
                if len(groups)==2 and {r['band'] in bands[:2] for r in chosen}!={False,True}:continue
            target=2 if office=='HOUSE' else 1
            value=[sum(abs(sum(r['sampling_party']==p for r in chosen)-target) for p in ('D','R')),
                   -len({s.REGIONS[r['state']] for r in chosen})]
            if office=='HOUSE':value.append(-len({r['state'] for r in chosen}))
        else:
            if n>=len({r['band'] for r in rows}) and present!={r['band'] for r in rows}:continue
            quotas=(4,4,2,2) if office=='HOUSE' else (1,1,1,1)
            deviation=0
            for band,q in zip(bands,quotas):
                for p in parties:
                    count=sum(r['band']==band and r['sampling_party']==p for r in chosen)
                    deviation+=abs(count-(0 if p=='OTHER' else q))
            value=[deviation,abs(sum(r['sampling_party']=='D' for r in chosen)-sum(r['sampling_party']=='R' for r in chosen)),
                   -len({s.REGIONS[r['state']] for r in chosen}),-len({r['state'] for r in chosen})]
        key=tuple(value)+(combo,)
        if best is None or key<best:best=key;winner=[r['race_id'] for r in chosen]
    return winner


class SourceGateTests(unittest.TestCase):
    def test_real_denied_even_with_complete_flags(self):
        f=fixture();f['dataset_kind']='REAL';f['permission_approved']=True
        with self.assertRaisesRegex(s.SelectionBlocked,'REAL selection remains blocked'):s.select_fixture(f)

    def test_no_missing_universe_pending_or_silent_exclusion(self):
        for mutate in [lambda f:f['rows'].pop(),lambda f:f['rows'].append(copy.deepcopy(f['rows'][0])),
                       lambda f:f['rows'][0].update(eligibility='PENDING'),
                       lambda f:f['rows'][0].update(eligibility='EXCLUDED_STRUCTURAL',exclusion_reason='NO_POLLS'),
                       lambda f:f.update(coverage_status='PARTIAL'),
                       lambda f:f['sources'][0].update(amendment_status='PENDING'),
                       lambda f:f['sources'][0].update(reuse_status='PUBLIC_VISIBLE'),
                       lambda f:f['sources'][0].update(url='https://www.cookpolitical.com/ratings'),
                       lambda f:f['rows'][0].update(observed_margin_pp=3)]:
            f=fixture();mutate(f)
            with self.assertRaises(s.SelectionBlocked):s.validate_fixture(f)

    def test_seed_cutoff_identity_region_and_provenance_guards(self):
        for mutate in [lambda f:f.update(seed=1),lambda f:f.update(cutoff='2026-11-03T05:00:00Z'),
                       lambda f:f['rows'][0].update(state='ZZ'),lambda f:f['rows'][0].update(district='1'),
                       lambda f:f['rows'][0].update(race_id='REAL-2026-AL-HOUSE-01'),
                       lambda f:f['sources'][0].update(first_observed_at_utc='2026-11-03T05:00:00Z'),
                       lambda f:f['sources'][0].update(published_at_utc='2026-11-02'),
                       lambda f:f['sources'][0].update(sha256='unknown'),
                       lambda f:f['rows'][0].update(evidence_refs=['rating','ballot'])]:
            f=fixture();mutate(f)
            with self.assertRaises(s.SelectionBlocked):s.validate_fixture(f)

    def test_structural_exclusion_is_logged_and_unavailable_input_cannot_replace(self):
        f=fixture(4,2);f['rows'][0].update(eligibility='EXCLUDED_STRUCTURAL',exclusion_reason='NO_REPUBLICAN')
        result=s.select_fixture(f)
        self.assertEqual(len(result['exclusions']),1)
        self.assertNotIn(f['rows'][0]['race_id'],result['broad']['HOUSE']['selected'])
        ids=result['broad']['SENATE']['selected']
        records=[{'race_id':x,'cutoff':s.CUTOFF,'status':'COMPLETE'} for x in ids]
        self.assertEqual(s.comparison_gate(ids,{'S0':records,'A0':records})['status'],'FIXTURE_FULL_SET_MATCHED')
        for changed in [records[:-1],[{**r,'status':'FAILED'} for r in records],[{**r,'race_id':'DEMO-replacement'} for r in records]]:
            with self.assertRaises(s.SelectionBlocked):s.comparison_gate(ids,{'S0':records,'A0':changed})


class SolverTests(unittest.TestCase):
    def compare_oracles(self,f):
        result=s.select_fixture(f)
        for office in ('HOUSE','SENATE'):
            rows=[r for r in f['rows'] if r['office']==office and r['eligibility']=='ELIGIBLE']
            expected=oracle(rows,office)
            self.assertEqual(result['broad'][office]['selected'],expected)
            deep=oracle([r for r in rows if r['race_id'] in expected],office,True)
            self.assertEqual(result['deep'][office]['selected'],deep)
        return result

    def test_exhaustive_reference_house_27_senate_12_other_and_shortfalls(self):
        self.compare_oracles(fixture())

    def test_randomized_adversarial_senate_exhaustive(self):
        for seed in range(1,7):self.compare_oracles(fixture(7,11,seed))

    def test_exhaustive_house_repeated_states_geography_and_party_priority(self):
        f=fixture(27,10,seed=8)
        for i,row in enumerate(r for r in f['rows'] if r['office']=='HOUSE'):
            row['state']=('AK','AL','CT','IA','CA','DE','AZ','NY')[i%8]
            row['district']=f'{i//8+1:02d}'
            row['race_id']=f"DEMO-2026-{row['state']}-HOUSE-{row['district']}"
        f['expected_race_ids']=[r['race_id'] for r in f['rows']]
        self.compare_oracles(f)

    def test_row_order_invariance_and_fixed_rank_exactness(self):
        f=fixture(25,10);a=s.select_fixture(f)
        f['rows'].reverse();f['sources'].reverse();f['expected_race_ids'].reverse();b=s.select_fixture(f)
        self.assertEqual(a['selection_sha256'],b['selection_sha256'])
        for office in ('HOUSE','SENATE'):
            self.assertEqual(a['broad'][office]['selected'],b['broad'][office]['selected'])
            for r in a['broad'][office]['ranks']:
                row=next(x for x in f['rows'] if x['race_id']==r['race_id'])
                self.assertEqual(r['sha256'],independent_rank(row)[0])

    def test_hash_collision_tie_breaks_on_canonical_id(self):
        f=fixture(4,4)
        class Collision:
            def hexdigest(self):return '0'*64
        with patch.object(s.hashlib,'sha256',return_value=Collision()):
            # Validate ordering directly; patching shared hashlib also changes canonical hashes.
            self.assertEqual([r['race_id'] for r in sorted(f['rows'],key=s.rank_key)],sorted(r['race_id'] for r in f['rows']))

    def test_absent_band_senate_fallback_insufficient_and_other_targets(self):
        f=fixture(5,5)
        for r in f['rows']:r.update(band='TOSS_UP',sampling_party='OTHER')
        result=self.compare_oracles(f)
        self.assertEqual(result['deep']['HOUSE']['status'],'BLOCKED_DEEP_HOUSE_ABSENT_BAND')
        self.assertEqual(result['deep']['SENATE']['fallback'],'ABSENT_LESS_COMPETITIVE_GROUP')
        self.assertEqual(result['deep']['SENATE']['objective_vector'][0],2)
        self.assertFalse(s.select_fixture(fixture(2,1))['full_six_deep_fixture'])
        empty=s.select_fixture(fixture(0,0))
        self.assertEqual(empty['broad']['HOUSE']['status'],'BLOCKED_EMPTY_OFFICE')

    def test_refuse_timeout_nonoptimal_unknown_gap_fractional_or_infeasible(self):
        from types import SimpleNamespace
        import numpy as np
        good=dict(status=0,success=True,x=np.array([1.]),mip_gap=0.,mip_dual_bound=1.,fun=1.)
        for bad in [dict(status=1),dict(success=False),dict(mip_gap=None),dict(mip_gap=.01),
                    dict(x=np.array([.5])),dict(x=np.array([2.])),dict(fun=2.),dict(mip_dual_bound=.9),dict(mip_dual_bound=float('nan'))]:
            r=SimpleNamespace(**(good|bad))
            with self.assertRaises(s.SelectionBlocked):s._checked_solution(r,np.array([1.]),np.array([[1.]]),[1],[1],[1])
        with self.assertRaisesRegex(s.SelectionBlocked,'time limit'):s.select_fixture(fixture(),max_seconds=1e-12)
        for value in [float('inf'),0,121,True]:
            with self.assertRaises(s.SelectionBlocked):s.select_fixture(fixture(),max_seconds=value)

    def test_full_size_synthetic_frame_optimal_not_tiny_only_solver(self):
        f=fixture(435,33);start=time.monotonic();r=s.select_fixture(f,max_seconds=60)
        self.assertLess(time.monotonic()-start,60)
        self.assertEqual(len(r['broad']['HOUSE']['selected']),24)
        self.assertEqual(len(r['broad']['SENATE']['selected']),8)
        self.assertTrue(r['full_six_deep_fixture'])
        for office in ('HOUSE','SENATE'):
            self.assertEqual(r['broad'][office]['objective_vector'][0],0)
            self.assertTrue(all(x['status']=='OPTIMAL' and x['gap']==0 for group in ('broad','deep') for x in r[group][office]['stages']))

    def test_run_logging_preserves_success_and_solver_failure(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path=s.run_fixture(Path(td),fixture(4,4))
            self.assertTrue((path/'selection.result.json').exists())
            self.assertTrue((path/'checksums.json').exists())
            with self.assertRaises(s.SelectionBlocked):s.run_fixture(Path(td),fixture(),max_seconds=1e-12)
            failed=[p for p in (Path(td)/'data/processed/runs').iterdir() if json.loads((p/'summary.json').read_text())['status']=='DEMO_SELECTION_FIXTURE_FAILED']
            self.assertEqual(len(failed),1)
            self.assertTrue((failed[0]/'selection.fixture.json').exists())
            self.assertIn('"event":"selection_failed"',(failed[0]/'events.jsonl').read_text())
            self.assertTrue((failed[0]/'checksums.json').exists())
            self.assertTrue((failed[0]/'selection.failure.json').exists())

    def test_later_solver_failure_retains_earlier_optimality_receipts(self):
        import tempfile
        original=s._MILP.optimize
        counter=[0]
        def fail_second(model,*args,**kwargs):
            counter[0]+=1
            if counter[0]==2:raise s.SelectionBlocked('deliberate later-stage fixture failure')
            return original(model,*args,**kwargs)
        with tempfile.TemporaryDirectory() as td:
            with patch.object(s._MILP,'optimize',fail_second):
                with self.assertRaises(s.SelectionBlocked):s.run_fixture(Path(td),fixture())
            run=next((Path(td)/'data/processed/runs').iterdir())
            events=[json.loads(x) for x in (run/'events.jsonl').read_text().splitlines()]
            self.assertTrue(any(x.get('event')=='selection_solver_stage' and x.get('status')=='OPTIMAL' for x in events))
            self.assertEqual(json.loads((run/'summary.json').read_text())['status'],'DEMO_SELECTION_FIXTURE_FAILED')
            self.assertFalse((run/'selection.result.json').exists())
            self.assertTrue((run/'checksums.json').exists())

    def test_versioned_policy_matches_implementation(self):
        p=json.loads((Path(__file__).parents[1]/'configs/e01_selection_v1.json').read_text())
        self.assertEqual((p['algorithm'],p['seed'],p['cutoff']),(s.ALGORITHM,s.SEED,s.CUTOFF))
        self.assertEqual(p['region_by_state'],s.REGIONS)
        import hashlib
        proposal=(Path(__file__).parents[1]/p['proposal_path']).read_bytes()
        approval=json.loads((Path(__file__).parents[1]/p['methods_approval']).read_text())
        self.assertEqual(hashlib.sha256(proposal).hexdigest(),approval['proposal_sha256'])
        self.assertEqual(p['proposal_sha256'],approval['proposal_sha256'])
        for office in ('HOUSE','SENATE'):
            self.assertEqual(p['quota_by_office'][office],{b:{q:s._quota(office)[b,q] for q in s.PARTIES} for b in s.BANDS})


if __name__=='__main__':unittest.main()
