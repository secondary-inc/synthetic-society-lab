"""Pure MOCK arithmetic/missingness tests, never empirical treatment results."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.e02 import wrapper_crossmodel_v1 as m
from test_e02_issue_cue_crossmodel_v1 import terms

RAW=(Path(__file__).resolve().parents[1]/'configs/e02_wrapper_crossmodel_v1_20261115.json').read_bytes()
P=m.load_protocol(RAW)

def answer(job):
    value=40 if job['model_key']=='A' else 60
    if job['phase']=='post':
        values={'A':{('NEWS','OMITTED'):60,('SOCIAL','OMITTED'):80,('NEWS','SHOWN'):65,('SOCIAL','SHOWN'):70},
                'B':{('NEWS','OMITTED'):50,('SOCIAL','OMITTED'):80,('NEWS','SHOWN'):55,('SOCIAL','SHOWN'):65}}
        value=values[job['model_key']][job['wrapper'],job['visibility']]
    return {'democratic_party':60,'republican_party':40,'policy_support':value,
            'factual_answer':'NOT_REPORTED' if job['phase']=='pre' else 'INCREASE_40'}

def build(mutate=None,stop_at=None):
    ts=terms();rows=[];requests=[]
    while True:
        state=m.next_action(RAW,ts,canonical_bytes(rows))
        if state['status']!='REQUEST_READY_NOT_ADMITTED':return state,requests,rows
        r=state['request'];job=P['jobs'][r['execution_order']];value=answer(job)
        if mutate:value=mutate(job,value)
        status='FAILED_UNCERTAIN' if job['execution_order']==stop_at else 'ANSWER'
        rows.append({'execution_order':job['execution_order'],'phase':job['phase'],
            'payload_sha256':r['payload_sha256'],'status':status,'answer':value if status=='ANSWER' else None})
        requests.append(r)

class PureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state,cls.requests,cls.rows=build()
        cls.result=m.analyze(RAW,canonical_bytes(cls.state['response_envelope']))
    def test_fixed_source_content_order_and_80_new_jobs(self):
        self.assertEqual(len(P['jobs']),80);self.assertEqual(sum(j['phase']=='pre' for j in P['jobs']),16)
        self.assertEqual(P['source_protocol_sha256'],m.base.PROTOCOL_SHA256)
        for rank,i in enumerate(range(0,80,2)):
            a,b=P['jobs'][i:i+2];self.assertEqual([a['model_key'],b['model_key']],['A','B'] if rank%2==0 else ['B','A'])
            self.assertEqual({k:v for k,v in a.items() if k not in ('model_key','execution_order','baseline_execution_order')},
                             {k:v for k,v in b.items() if k not in ('model_key','execution_order','baseline_execution_order')})
            for job in (a,b):
                if job['phase']=='post':
                    before=P['jobs'][job['baseline_execution_order']]
                    self.assertEqual((before['model_key'],before['profile'],before['topic_id']),
                                     (job['model_key'],job['profile'],job['topic_id']))
        self.assertFalse(P['actual_authority']);self.assertIsNone(P['results'])
        with self.assertRaises(ExecutionBlocked):m.load_protocol(RAW+b' ')
    def test_matched_arithmetic_oracles_and_descriptive_denominators(self):
        x=self.result['matched_configuration_contrasts']
        self.assertEqual(x['primary_wrapper_omitted']['B_minus_A']['mean_points'],10)
        self.assertEqual(x['visibility_interaction']['B_minus_A']['mean_points'],-5)
        self.assertEqual(x['primary_wrapper_omitted']['same_intersection_configurations']['A']['mean_points'],20)
        self.assertEqual(x['primary_wrapper_omitted']['same_intersection_configurations']['B']['mean_points'],30)
        self.assertEqual(x['visibility_interaction']['B_minus_A']['complete_units'],8)
        self.assertIsNone(x['primary_wrapper_omitted']['B_minus_A']['interval_95'])
        self.assertEqual(self.result['response_provenance'],'MOCK');self.assertFalse(self.result['saved_answers_reused'])
    def test_only_wrapper_and_own_support_change_and_no_model_label_in_request(self):
        by={r['execution_order']:r for r in self.requests}
        for job in P['jobs']:
            req=by[job['execution_order']]['request']
            self.assertNotIn('model_key',req);self.assertNotIn('topic_id',req)
            if job['visibility']=='SHOWN':
                expected=40 if job['model_key']=='A' else 60
                self.assertEqual(req['pre_response'],{'policy_support':expected})
            else:self.assertNotIn('pre_response',req)
        for i in range(0,80,2):
            a,b=self.requests[i:i+2]
            if a['request']['phase']=='pre' or 'pre_response' not in a['request']:
                self.assertEqual(a['request'],b['request'])
    def test_invalid_pre_skips_only_own_two_shown_posts(self):
        first=P['jobs'][0]
        def mutate(j,a):
            if j['execution_order']==0:a['policy_support']=None
            return a
        state,requests,rows=build(mutate);out=m.analyze(RAW,canonical_bytes(state['response_envelope']))
        skipped=[j for j,r in zip(P['jobs'],state['response_envelope']['records']) if r['status']=='SKIPPED_INVALID_PRE']
        self.assertEqual(len(requests),78);self.assertEqual(len(skipped),2)
        self.assertTrue(all(j['model_key']==first['model_key'] and j['profile']==first['profile'] and j['topic_id']==first['topic_id'] for j in skipped))
        self.assertEqual(out['matched_configuration_contrasts']['primary_wrapper_omitted']['B_minus_A']['complete_units'],8)
        self.assertEqual(out['matched_configuration_contrasts']['visibility_interaction']['B_minus_A']['complete_units'],7)
    def test_common_intersection_excludes_one_missing_support_without_imputation(self):
        target=next(j['execution_order'] for j in P['jobs'] if j['phase']=='post' and j['model_key']=='B' and j['wrapper']=='SOCIAL' and j['visibility']=='OMITTED')
        def mutate(j,a):
            if j['execution_order']==target:a['policy_support']=None
            return a
        state,_,_=build(mutate);out=m.analyze(RAW,canonical_bytes(state['response_envelope']))
        x=out['matched_configuration_contrasts']['primary_wrapper_omitted']
        self.assertEqual(x['B_minus_A']['complete_units'],7)
        self.assertEqual({v['complete_units'] for v in x['same_intersection_configurations'].values()},{7})
        self.assertEqual(out['configuration_analyses']['A']['primary_wrapper_omitted']['complete_units'],8)
        self.assertEqual(out['configuration_analyses']['B']['primary_wrapper_omitted']['complete_units'],7)
    def test_unrelated_missingness_and_wrong_fact_do_not_gate_support(self):
        def mutate(j,a):
            a['democratic_party']=None;a['factual_answer']='NOT_REPORTED';return a
        state,_,_=build(mutate);out=m.analyze(RAW,canonical_bytes(state['response_envelope']))
        self.assertEqual(out['matched_configuration_contrasts']['visibility_interaction']['B_minus_A']['complete_units'],8)
        self.assertEqual(out['configuration_analyses']['A']['comprehension']['LIBRARY']['NEWS']['OMITTED']['observed_factual_errors'],4)
    def test_stop_no_second_configuration_or_later_dispatch_and_tamper_refusal(self):
        state,requests,rows=build(stop_at=0)
        self.assertEqual(len(requests),1);self.assertEqual(state['status'],'STOPPED')
        self.assertEqual(sum(r['status']=='NOT_ATTEMPTED' for r in state['response_envelope']['records']),79)
        for change in ('order','hash','answer'):
            bad=deepcopy(self.rows)
            if change=='order':bad[0],bad[1]=bad[1],bad[0]
            elif change=='hash':bad[0]['payload_sha256']='0'*64
            else:bad[0]['status']='FAILED_UNCERTAIN'
            with self.assertRaises(ExecutionBlocked):m.next_action(RAW,terms(),canonical_bytes(bad))
    def test_cost_route_identity_and_no_io(self):
        ts=terms();cost=m.cost_envelope(RAW,ts)
        self.assertEqual(cost['maximum_POSTs'],80);self.assertLessEqual(cost['maximum_batch_microusd'],200000)
        for role in ('A','B'):
            bad=deepcopy(ts);bad[role]['reported_provider']='OTHER'
            with self.assertRaises((ExecutionBlocked,ValueError)):m.cost_envelope(RAW,bad)
        with patch('builtins.open',side_effect=AssertionError('pure filesystem')),patch('socket.socket',side_effect=AssertionError('pure network')):
            state=m.next_action(RAW,ts,b'[]');self.assertEqual(state['request']['execution_order'],0)
            self.assertEqual(m.analyze(RAW,canonical_bytes(self.state['response_envelope']))['planned_posts'],64)

if __name__=='__main__':unittest.main()
