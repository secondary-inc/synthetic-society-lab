"""Authored arithmetic/quality oracles; no observed model results."""
import copy
import hashlib
import json
from pathlib import Path
import random
import unittest

from civiclab.e02.exploratory_pilot_analysis_v1 import (
    analyze, PROTOCOL_SHA256, PROJECTION_SHA256, ASSIGNMENT_SHA256)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (ROOT/'configs/e02_exploratory_live_pilot_v1_1.json').read_bytes()
CONFIG = json.loads(PROTOCOL)


def envelope():
    rows = []
    for job in CONFIG['assignments']:
        # Each party's baseline gap0; C1gap2, C2gap6 => paired contrast4.
        for phase in ('pre','post'):
            amount = 0 if phase=='pre' else 1 if job['arm']=='C1' else 3
            sign = 1 if job['profile']['party']=='D' else -1
            answer = {'democratic_party':50+sign*amount,'republican_party':50-sign*amount}
            rows.append({'execution_order':job['execution_order'],'phase':phase,'status':'ANSWER','answer':answer})
    return {'response_provenance':'MOCK','protocol_sha256':PROTOCOL_SHA256,
            'projection_sha256':PROJECTION_SHA256,'assignment_sha256':ASSIGNMENT_SHA256,'records':rows}


def raw(value):
    return json.dumps(value,allow_nan=False).encode()


def run(value):
    return analyze(PROTOCOL,raw(value))


def omit_block(value, profile, stimulus):
    for job in CONFIG['assignments']:
        if job['profile']['profile_id']==profile and job['stimulus_id']==stimulus:
            i=job['execution_order']
            value['records'][2*i].update(status='ANSWER',answer={'democratic_party':None,'republican_party':50})
            value['records'][2*i+1].update(status='SKIPPED_INVALID_PRE',answer=None)


class AnalysisTests(unittest.TestCase):
    def test_constant_hand_oracle_and_provenance(self):
        out=run(envelope())
        self.assertEqual(out['estimate_thermometer_points'],4)
        self.assertEqual(out['interval_95_descriptive_crossed_bootstrap'],[4,4])
        self.assertEqual(out['complete_blocks'],8)
        self.assertEqual(out['phase_counts'],{'VALID':32})
        self.assertEqual(out['bootstrap']['nonempty_draws'],2000)
        self.assertEqual(out['sensitivity']['party_means'],{'D':4,'R':4})
        self.assertEqual(out['sensitivity']['absolute_gap_mean_difference_points'],4)
        self.assertTrue(all(v==4 for v in out['sensitivity']['leave_one_profile_out'].values()))
        self.assertEqual(out['response_provenance'],'MOCK')
        self.assertIn('DEMO',out['input_stimulus_provenance'])
        self.assertFalse(out['authority_created'])

    def test_negative_republican_orientation(self):
        e=envelope()
        # Change R C2post from warmthR56-D44 to D56-R44: change -12,
        # compared with R C1change2 => -14, two blocks. Six others? 4 Dblocks at4.
        for job in CONFIG['assignments']:
            if job['profile']['party']=='R' and job['arm']=='C2':
                e['records'][2*job['execution_order']+1]['answer']={'democratic_party':56,'republican_party':44}
        out=run(e)
        self.assertEqual(out['sensitivity']['party_means'],{'D':4,'R':-14})
        self.assertEqual(out['estimate_thermometer_points'],-5)

    def test_extreme_difference_range(self):
        e=envelope()
        for job in CONFIG['assignments']:
            sign=1 if job['profile']['party']=='D' else -1
            for phase in ('pre','post'):
                in_warm = (job['arm']=='C1') == (phase=='pre')
                d=100 if in_warm==(sign==1) else 0
                e['records'][2*job['execution_order']+(phase=='post')]['answer']={'democratic_party':d,'republican_party':100-d}
        self.assertEqual(run(e)['estimate_thermometer_points'],400)

    def test_invalid_pre_skip_excludes_entire_block(self):
        e=envelope();e['records'][0]['answer']={'democratic_party':None,'republican_party':50}
        e['records'][1].update(status='SKIPPED_INVALID_PRE',answer=None)
        out=run(e)
        self.assertEqual(out['complete_blocks'],7)
        self.assertEqual(out['phase_counts'],{'INVALID_ANSWER':1,'SKIPPED_INVALID_PRE':1,'VALID':30})
        b=next(b for b in out['blocks'] if b['status']!='COMPLETE')
        self.assertEqual(b['arms'][CONFIG['assignments'][0]['arm']]['pre_quality'],'INVALID_ANSWER')
        self.assertEqual(out['estimate_thermometer_points'],4)

    def test_invalid_pre_cannot_dispatch_post(self):
        e=envelope();e['records'][0]['answer']={}
        with self.assertRaisesRegex(ValueError,'invalid baseline'):run(e)

    def test_unjustified_skip_rejected(self):
        e=envelope();e['records'][1].update(status='SKIPPED_INVALID_PRE',answer=None)
        with self.assertRaisesRegex(ValueError,'without invalid'):run(e)

    def test_invalid_post_and_parse_error(self):
        for status,answer in [('ANSWER',{'democratic_party':True,'republican_party':50}),('PARSE_ERROR',None)]:
            with self.subTest(status=status):
                e=envelope();e['records'][1].update(status=status,answer=answer)
                self.assertEqual(run(e)['complete_blocks'],7)

    def test_invalid_answer_types_bounded(self):
        for answer in [None,[],{},'bad',{'democratic_party':50},
                       {'democratic_party':50,'republican_party':50,'extra':1},
                       {'democratic_party':1000,'republican_party':50},
                       {'democratic_party':10**400,'republican_party':50}]:
            with self.subTest(answer_type=type(answer).__name__):
                e=envelope();e['records'][1]['answer']=answer
                self.assertEqual(run(e)['complete_blocks'],7)

    def test_no_data_null_masks(self):
        e=envelope()
        for row in e['records']:row.update(status='NOT_ATTEMPTED',answer=None)
        out=run(e)
        self.assertEqual(out['status'],'NOT_ESTIMABLE')
        self.assertIsNone(out['estimate_thermometer_points'])
        self.assertIsNone(out['interval_95_descriptive_crossed_bootstrap'])
        self.assertEqual(out['bootstrap']['nonempty_draws'],0)
        self.assertTrue(all(v is None for v in out['sensitivity']['party_means'].values()))

    def test_invalid_all_data_null_masks(self):
        e=envelope()
        for i,row in enumerate(e['records']):
            row.update(status='ANSWER' if i%2==0 else 'SKIPPED_INVALID_PRE',answer={} if i%2==0 else None)
        self.assertEqual(run(e)['complete_blocks'],0)

    def test_insufficient_cluster_interval_null(self):
        e=envelope()
        for p in CONFIG['profiles'][1:]:
            for s in CONFIG['stimuli']:omit_block(e,p['profile_id'],s['id'])
        out=run(e)
        self.assertEqual(out['complete_blocks'],2)
        self.assertEqual(out['estimate_thermometer_points'],4)
        self.assertIsNone(out['interval_95_descriptive_crossed_bootstrap'])

    def test_crossed_missing_cells_zero_draws_and_reference_oracle(self):
        e=envelope();ps=[p['profile_id'] for p in CONFIG['profiles']];ss=[s['id'] for s in CONFIG['stimuli']]
        keep={(ps[0],ss[0]),(ps[1],ss[1])}
        for p in ps:
            for s in ss:
                if (p,s) not in keep:omit_block(e,p,s)
        # Give second complete block contrast8: C2gap10 minus C1gap2.
        for j in CONFIG['assignments']:
            if (j['profile']['profile_id'],j['stimulus_id'])==(ps[1],ss[1]) and j['arm']=='C2':
                e['records'][2*j['execution_order']+1]['answer']={'democratic_party':55,'republican_party':45}
        out=run(e)
        self.assertEqual(out['estimate_thermometer_points'],6)
        self.assertEqual(out['interval_95_descriptive_crossed_bootstrap'],[4,8])
        # Independent expanded Cartesian-resample oracle; no Counter weighting.
        rng=random.Random(20261103);draws=[];zero=0
        values={(ps[0],ss[0]):4,(ps[1],ss[1]):8}
        for _ in range(2000):
            pp=rng.choices(ps[:2],k=2);st=rng.choices(sorted(ss),k=2)
            sample=[values[p,s] for p in pp for s in st if (p,s) in values]
            if sample:draws.append(sum(sample)/len(sample))
            else:zero+=1
        self.assertGreater(zero,0)
        self.assertEqual(out['bootstrap']['zero_weight_draws'],zero)
        self.assertEqual(out['bootstrap']['nonempty_draws'],len(draws))

    def test_reproducible_and_input_order_invariant_except_input_hash(self):
        e=envelope();a=run(e);self.assertEqual(a,run(e))
        e['records'].reverse();b=run(e)
        a.pop('response_envelope_sha256');b.pop('response_envelope_sha256')
        self.assertEqual(a,b)

    def test_live_provenance_declared_not_certified(self):
        e=envelope();e['response_provenance']='EXPLORATORY_REAL_MODEL'
        out=run(e);self.assertEqual(out['response_provenance'],'EXPLORATORY_REAL_MODEL')
        self.assertIn('DECLARED_ONLY',out['provenance_verification'])

    def test_financial_stop_and_cancel(self):
        for status in ('FAILED_UNCERTAIN','CANCELLED'):
            e=envelope();e['records'][0].update(status=status,answer=None)
            for row in e['records'][1:]:row.update(status='NOT_ATTEMPTED',answer=None)
            out=run(e);self.assertTrue(out['run_stopped']);self.assertEqual(out['complete_blocks'],0)

    def test_attempt_after_stop_rejected(self):
        e=envelope();e['records'][0].update(status='FAILED_UNCERTAIN',answer=None)
        e['records'][1].update(status='NOT_ATTEMPTED',answer=None)
        with self.assertRaisesRegex(ValueError,'after run stop'):run(e)

    def test_closed_bindings_and_protocol_bytes(self):
        for field in ('protocol_sha256','projection_sha256','assignment_sha256','response_provenance'):
            e=envelope();e[field]='bad'
            with self.assertRaises(ValueError):run(e)
        with self.assertRaises(ValueError):analyze(PROTOCOL+b' ',raw(envelope()))
        e=envelope();e['extra']=1
        with self.assertRaises(ValueError):run(e)

    def test_rows_duplicate_missing_extra_types(self):
        cases=[]
        e=envelope();e['records'].pop();cases.append(e)
        e=envelope();e['records'][1]=copy.deepcopy(e['records'][0]);cases.append(e)
        e=envelope();e['records'][0]['execution_order']=True;cases.append(e)
        e=envelope();e['records'][0]['extra']=True;cases.append(e)
        e=envelope();e['records'][0]['status']='RETRY';cases.append(e)
        for e in cases:
            with self.assertRaises(ValueError):run(e)

    def test_json_finiteness_duplicates_bounds(self):
        for blob in [b'{"x":1,"x":2}',b'NaN',b'1e999',b'['*1000+b']'*1000,b'x'*131073]:
            with self.assertRaises(ValueError):analyze(PROTOCOL,blob)
        with self.assertRaises(ValueError):analyze(PROTOCOL,'not bytes')

    def test_no_authority_or_protocol_changes(self):
        self.assertEqual(hashlib.sha256(PROTOCOL).hexdigest(),PROTOCOL_SHA256)
        self.assertFalse(CONFIG['actual_authority'])


if __name__=='__main__':unittest.main()
