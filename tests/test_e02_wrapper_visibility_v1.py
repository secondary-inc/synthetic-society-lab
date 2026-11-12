"""Authored arithmetic/sequence oracles only, never empirical model findings."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.e02 import wrapper_visibility_v1 as m
from test_e02_issue_cue_crossmodel_v1 import terms as prior_terms

ROOT=Path(__file__).resolve().parents[1]
RAW=(ROOT/'configs/e02_wrapper_visibility_v1.json').read_bytes()
P=m.load_protocol(RAW)


def terms():return prior_terms()['B']


def answer(job):
    support=(20 if job['topic_id']=='LIBRARY' else 40)+int(job['profile']['profile_id'][-1])
    if job['phase']=='post':support={('NEWS','OMITTED'):60,('SOCIAL','OMITTED'):80,('NEWS','SHOWN'):65,('SOCIAL','SHOWN'):70}[job['wrapper'],job['visibility']]
    return {'democratic_party':60,'republican_party':40,'policy_support':support,
            'factual_answer':'NOT_REPORTED' if job['phase']=='pre' else 'INCREASE_40'}


def build(mutate=None,status_at=None,*,io_guard=False):
    ts=terms();rows=[];requests=[]
    def run():
        while True:
            state=m.next_action(RAW,ts,canonical_bytes(rows))
            if state['status']!='REQUEST_READY_NOT_ADMITTED':return rows,state,requests,ts
            r=state['request'];job=P['jobs'][r['execution_order']];value=answer(job)
            if mutate:value=mutate(job,value)
            status=status_at.get(r['execution_order'],'ANSWER') if status_at else 'ANSWER'
            rows.append({'execution_order':r['execution_order'],'phase':r['phase'],'payload_sha256':r['payload_sha256'],'status':status,'answer':value if status=='ANSWER' else None});requests.append(r)
    if io_guard:
        with patch('builtins.open',side_effect=AssertionError('pure code I/O')),patch('socket.socket',side_effect=AssertionError('pure code network')):return run()
    return run()


def analyzed(**kw):
    rows,state,requests,ts=build(**kw)
    return m.analyze(RAW,canonical_bytes(state['response_envelope'])),rows,state,requests,ts


class WrapperTests(unittest.TestCase):
    def test_freeze_ancestry_and_no_scientific_deviation(self):
        original=(ROOT/'configs/e02_wrapper_visibility_proposal_v1_20261112.json').read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),P['proposal_ancestry']['sha256'])
        self.assertEqual(P['proposal_ancestry']['design_changes'],[])
        q=json.loads(original)
        for key in q:
            if key not in ('protocol_id','status','frozen'):self.assertEqual(P[key],q[key],key)
        self.assertFalse(P['actual_authority']);self.assertIsNone(P['results'])
        with self.assertRaises(ExecutionBlocked):m.load_protocol(RAW+b' ')
    def test_seed_order_balance_exact_factorial_and_baseline_binding(self):
        contexts=[{'profile':p,'topic_id':t['topic_id']} for p in P['profiles'] for t in P['topics']]
        random.Random(P['seed']).shuffle(contexts)
        self.assertEqual([(j['profile'],j['topic_id']) for j in P['jobs'][:8]],[(c['profile'],c['topic_id']) for c in contexts])
        post=contexts.copy();random.Random(P['seed']+1).shuffle(post)
        cells=[('NEWS','OMITTED'),('SOCIAL','OMITTED'),('NEWS','SHOWN'),('SOCIAL','SHOWN')]
        for rank,start in enumerate(range(8,40,4)):
            block=P['jobs'][start:start+4];c=post[rank];rot=rank%4
            self.assertEqual([(j['wrapper'],j['visibility']) for j in block],cells[rot:]+cells[:rot])
            for j in block:
                self.assertEqual(j['profile'],c['profile']);self.assertEqual(j['topic_id'],c['topic_id'])
                pre=P['jobs'][j['baseline_execution_order']];self.assertEqual((pre['profile'],pre['topic_id']),(j['profile'],j['topic_id']))
                seed=int(canonical_hash([P['seed'],j['profile']['profile_id'],j['topic_id']])[:8],16)
                order=P['instrument']['requested_keys'].copy();random.Random(seed).shuffle(order)
                self.assertEqual((j['pair_seed'],j['item_order']),(seed,order))
    def test_cost_fixed_route_allin_and_caps(self):
        t=terms();e=m.cost_envelope(RAW,t)
        self.assertEqual(e['maximum_POSTs'],40);self.assertEqual(e['maximum_batch_microusd'],40*1716);self.assertFalse(e['actual_authority'])
        for key,value in [('model','other'),('reported_provider','Azure'),('requested_route','other'),('route_scope','PROVIDER_FAMILY'),('output_parameter','max_tokens')]:
            bad=deepcopy(t);bad[key]=value
            with self.subTest(key=key),self.assertRaises((ExecutionBlocked,ValueError)):m.cost_envelope(RAW,bad)
        bad=deepcopy(t);bad['request_fee_usd']='0.01'
        for v in bad['components_by_tag'].values():v['request']='0.01'
        with self.assertRaises(ExecutionBlocked):m.cost_envelope(RAW,bad)
    def test_authored_positive_arithmetic_and_all_denominators(self):
        out,rows,state,requests,t=analyzed()
        self.assertEqual(len(rows),40);self.assertEqual(out['primary_wrapper_omitted']['mean_points'],20)
        self.assertEqual(out['visibility_interaction']['mean_points'],-15)
        self.assertEqual(out['matched_wrapper_contrasts']['SHOWN']['mean_points'],5)
        self.assertEqual(out['absolute_wrapper_magnitude_change']['mean_points'],-15)
        self.assertEqual(out['direction_diagnostics']['compatible_magnitude_masking_count'],8)
        self.assertEqual(out['direction_diagnostics']['sign_reversal_count'],0)
        self.assertEqual(out['response_provenance'],'MOCK');self.assertIsNone(out['primary_wrapper_omitted']['interval_95'])
        for topic in P['topics']:
            self.assertEqual(out['primary_by_topic'][topic['topic_id']]['complete_units'],4)
            for wrapper in ('NEWS','SOCIAL'):
                for vis in ('OMITTED','SHOWN'):self.assertEqual(out['comprehension'][topic['topic_id']][wrapper][vis]['correct'],4)
        self.assertTrue(all(r['value']==0 for r in out['separate_party_gap_wrapper_contrasts']['OMITTED']['unit_values']))
    def test_exact_content_label_cue_ablation_and_own_topic_baselines(self):
        out,rows,state,requests,t=analyzed();by={r['execution_order']:r for r in requests}
        for start in range(8,40,4):
            quartet=P['jobs'][start:start+4];compiled={(j['wrapper'],j['visibility']):by[j['execution_order']] for j in quartet}
            for vis in ('OMITTED','SHOWN'):
                a=deepcopy(compiled['NEWS',vis]['request']);b=deepcopy(compiled['SOCIAL',vis]['request'])
                self.assertEqual((a['notice'].pop('presentation_label'),b['notice'].pop('presentation_label')),('news article','social-media post'))
                self.assertEqual(a,b)
            for wrapper in ('NEWS','SOCIAL'):
                shown=compiled[wrapper,'SHOWN'];a=deepcopy(shown['request']);b=compiled[wrapper,'OMITTED']['request']
                expected=answer(P['jobs'][shown['baseline_execution_order']])['policy_support']
                self.assertEqual(a.pop('pre_response'),{'policy_support':expected});self.assertEqual(a,b)
                self.assertEqual(shown['payload']['provider']['only'],['nebius/fp8']);self.assertFalse(shown['payload']['provider']['allow_fallbacks'])
            j=quartet[0];topic=next(t for t in P['topics'] if t['topic_id']==j['topic_id']);req=compiled['NEWS','OMITTED']['request']
            self.assertEqual(req['survey']['items'][2]['question'],topic['support_question'])
            self.assertEqual(req['survey']['items'][3]['question'],topic['factual_question'])
            self.assertEqual(set(req['notice']),{'text','source_label','presentation_label'})
            self.assertNotIn('topic_id',req);self.assertNotIn('visibility',req);self.assertNotIn('treatment_answer',json.dumps(req))
    def test_neutral_reference_baseline_has_common_label_and_no_prior(self):
        _,_,_,requests,_=analyzed()
        for r in requests[:8]:
            self.assertEqual(r['request']['notice']['presentation_label'],'reference survey')
            self.assertNotIn('pre_response',r['request']);self.assertIn('No measured effect',r['request']['notice']['text'])
    def test_unrelated_missing_null_invalid_pre_items_never_exclude_support(self):
        def mutate(j,a):
            if j['phase']=='pre':a.pop('democratic_party');a['republican_party']=False;a['factual_answer']=None
            return a
        out,rows,*_=analyzed(mutate=mutate)
        self.assertEqual(len(rows),40);self.assertEqual(out['visibility_interaction']['complete_units'],8)
        self.assertEqual(out['primary_wrapper_omitted']['mean_points'],20)
        self.assertTrue(all(r['value'] is not None for r in out['support_reference_changes']))
        # Reference support itself is valid, so support drift remains estimable.
    def test_missing_pre_support_keeps_omitted_primary_and_skips_only_two_shown(self):
        target=P['jobs'][0]
        def mutate(j,a):
            if j['phase']=='pre' and j['execution_order']==0:a['policy_support']=None
            return a
        out,rows,state,requests,t=analyzed(mutate=mutate)
        self.assertEqual(len(rows),38);self.assertEqual(out['phase_counts']['SKIPPED_INVALID_PRE'],2)
        self.assertEqual(out['primary_wrapper_omitted']['complete_units'],8)
        self.assertEqual(out['visibility_interaction']['complete_units'],7)
        tid=target['topic_id']
        for wrapper in ('NEWS','SOCIAL'):
            c=out['comprehension'][tid][wrapper]['SHOWN'];self.assertEqual(c['observed_factual_errors'],0);self.assertEqual(c['quality_counts']['UNASKED'],1)
    def test_all_pre_support_invalid_still_complete_primary_no_secondary_zero_imputation(self):
        def mutate(j,a):
            if j['phase']=='pre':a.pop('policy_support')
            return a
        out,rows,*_=analyzed(mutate=mutate)
        self.assertEqual(len(rows),24);self.assertEqual(out['phase_counts']['SKIPPED_INVALID_PRE'],16)
        self.assertEqual(out['primary_wrapper_omitted']['complete_units'],8)
        self.assertEqual(out['visibility_interaction']['complete_units'],0)
        self.assertIsNone(out['visibility_interaction']['mean_points']);self.assertIsNone(out['absolute_wrapper_magnitude_change']['mean_points'])
    def test_unknown_extra_keys_invalidate_all_scores_and_no_repair(self):
        def mutate(j,a):a['unknown']='x';return a
        out,rows,*_=analyzed(mutate=mutate)
        self.assertEqual(len(rows),24);self.assertEqual(out['primary_wrapper_omitted']['status'],'NOT_ESTIMABLE')
        self.assertIsNone(out['primary_wrapper_omitted']['mean_points'])
        self.assertTrue(all(s['support'] is None for s in out['scored_phases']))
    def test_matched_secondary_never_subtracts_unequal_means(self):
        target=P['jobs'][0];key=(target['profile']['profile_id'],target['topic_id'])
        def mutate(j,a):
            if j['phase']=='post' and (j['profile']['profile_id'],j['topic_id'])==key:
                if j['visibility']=='OMITTED':a['policy_support']=100 if j['wrapper']=='SOCIAL' else 0
                elif j['wrapper']=='NEWS':a.pop('policy_support')
            return a
        out,*_=analyzed(mutate=mutate)
        self.assertEqual(out['primary_wrapper_omitted']['mean_points'],30)
        self.assertEqual(out['wrapper_contrasts']['SHOWN']['mean_points'],5)
        self.assertEqual(out['matched_wrapper_contrasts']['OMITTED']['mean_points'],20)
        self.assertEqual(out['visibility_interaction']['mean_points'],-15)
        self.assertEqual(out['visibility_interaction']['complete_units'],7)
    def test_signed_negative_can_reverse_and_positive_can_mean_shrinkage(self):
        for omitted,shown,expected_i,expected_mag,reversal,compatible in [(20,-5,-25,-15,8,0),(-20,-5,15,-15,0,8),(20,40,20,20,0,0)]:
            def mutate(j,a):
                if j['phase']=='post':a['policy_support']=50+(omitted if j['visibility']=='OMITTED' else shown) if j['wrapper']=='SOCIAL' else 50
                return a
            out,*_=analyzed(mutate=mutate)
            self.assertEqual(out['visibility_interaction']['mean_points'],expected_i)
            self.assertEqual(out['absolute_wrapper_magnitude_change']['mean_points'],expected_mag)
            self.assertEqual(out['direction_diagnostics']['sign_reversal_count'],reversal)
            self.assertEqual(out['direction_diagnostics']['compatible_magnitude_masking_count'],compatible)
    def test_factual_error_missing_key_null_unasked_are_separate_without_exclusion(self):
        orders=[j['execution_order'] for j in P['jobs'] if j['phase']=='post'][:3]
        def mutate(j,a):
            if j['execution_order']==orders[0]:a['factual_answer']='NOT_REPORTED'
            if j['execution_order']==orders[1]:a.pop('factual_answer')
            if j['execution_order']==orders[2]:a['factual_answer']=None
            return a
        out,*_=analyzed(mutate=mutate)
        q=[s['comprehension'] for s in out['scored_phases']]
        self.assertEqual(q.count('INCORRECT'),1);self.assertEqual(q.count('MISSING_KEY'),1);self.assertEqual(q.count('MISSING_NULL'),1)
        self.assertEqual(out['visibility_interaction']['complete_units'],8)
    def test_partial_topic_party_and_leave_one_topic_denominators(self):
        def mutate(j,a):
            if j['phase']=='post' and j['topic_id']=='LIBRARY' and j['profile']['party']=='D' and j['visibility']=='OMITTED' and j['wrapper']=='NEWS':a['policy_support']=None
            return a
        out,*_=analyzed(mutate=mutate)
        self.assertEqual(out['primary_wrapper_omitted']['complete_units'],6);self.assertEqual(out['primary_wrapper_omitted']['status'],'DESCRIPTIVE_PARTIAL')
        self.assertEqual(out['primary_by_topic']['LIBRARY']['complete_units'],2);self.assertEqual(out['primary_by_topic']['TRANSIT']['complete_units'],4)
        self.assertEqual(out['primary_by_party']['D']['complete_units'],2);self.assertEqual(out['leave_one_topic_out']['TRANSIT']['complete_units'],2)
    def test_party_direction_secondary_does_not_gate_custom_primary(self):
        def mutate(j,a):
            if j['phase']=='post' and j['wrapper']=='SOCIAL':a['democratic_party']=65;a['republican_party']=35
            return a
        out,*_=analyzed(mutate=mutate)
        for r in out['separate_party_gap_wrapper_contrasts']['OMITTED']['unit_values']:self.assertEqual(r['value'],10 if r['party']=='D' else -10)
        self.assertEqual(out['primary_wrapper_omitted']['mean_points'],20)
    def test_stop_cancel_parse_failure_and_empty_export_40_dispositions(self):
        for i,status in ((0,'FAILED_UNCERTAIN'),(8,'CANCELLED'),(20,'FAILED_UNCERTAIN'),(39,'CANCELLED')):
            out,rows,state,req,ts=analyzed(status_at={i:status})
            self.assertEqual(state['status'],'STOPPED');self.assertEqual(len(state['records']),40)
            self.assertTrue(all(r['status']=='NOT_ATTEMPTED' for r in state['records'][i+1:]))
            self.assertEqual(m.response_envelope(RAW,ts,canonical_bytes(rows)),state['response_envelope'])
        out,rows,*_=analyzed(status_at={0:'PARSE_ERROR'})
        self.assertEqual(out['phase_counts']['SKIPPED_INVALID_PRE'],2);self.assertEqual(out['phase_counts']['PARSE_ERROR'],1)
        self.assertEqual(out['primary_wrapper_omitted']['complete_units'],8)
        e=m.response_envelope(RAW,terms(),b'[]',stopped=True);out=m.analyze(RAW,canonical_bytes(e))
        self.assertIsNone(out['primary_wrapper_omitted']['mean_points']);self.assertEqual(out['phase_counts'],{'NOT_ATTEMPTED':40})
        with self.assertRaises(ExecutionBlocked):m.response_envelope(RAW,terms(),b'[]')
    def test_replay_exact_envelope_and_tampered_hash_order_extra_retry_rejected(self):
        rows,state,requests,t=build()
        self.assertEqual(m.response_envelope(RAW,t,canonical_bytes(rows)),state['response_envelope'])
        self.assertEqual(build()[0],rows)
        for change in ('payload','duplicate','reorder','bool','extra'):
            bad=deepcopy(rows)
            if change=='payload':bad[10]['payload_sha256']='0'*64
            if change=='duplicate':bad.insert(10,deepcopy(bad[9]))
            if change=='reorder':bad[8],bad[9]=bad[9],bad[8]
            if change=='bool':bad[0]['execution_order']=False
            if change=='extra':bad.append(deepcopy(bad[-1]))
            with self.subTest(change=change),self.assertRaises(ExecutionBlocked):m.next_action(RAW,t,canonical_bytes(bad))
        bad=deepcopy(rows);bad[0].update(status='FAILED_UNCERTAIN',answer=None)
        with self.assertRaises(ExecutionBlocked):m.next_action(RAW,t,canonical_bytes(bad[:2]))
    def test_envelope_binding_duplicate_wrong_skip_after_stop_refused(self):
        _,state,_,_=build()
        for change in ('protocol_sha256','assignment_sha256','instrument_sha256','topics_sha256','response_provenance','duplicate','skip','afterstop'):
            e=deepcopy(state['response_envelope'])
            if change=='duplicate':e['records'][1]=deepcopy(e['records'][0])
            elif change=='skip':e['records'][0].update(status='SKIPPED_INVALID_PRE',answer=None)
            elif change=='afterstop':e['records'][0].update(status='FAILED_UNCERTAIN',answer=None)
            else:e[change]='bad'
            with self.subTest(change=change),self.assertRaises(ExecutionBlocked):m.analyze(RAW,canonical_bytes(e))
    def test_parser_bounds_and_itemwise_values(self):
        for text in ('[]','NaN','1e999','{"a":1,"a":2}','{"policy_support":"'+'x'*33+'"}','{"x":'+'1'*33+'}'):
            self.assertEqual(m.parse_response({'choices':[{'message':{'content':text}}]})['status'],'PARSE_ERROR')
        for value in (None,True,'50',-1,101,float('nan'),float('inf')):self.assertFalse(m.valid_baseline({'policy_support':value}))
        a={'policy_support':50};self.assertTrue(m.valid_baseline(a))
        self.assertEqual(m.parse_response({'choices':[{'message':{'content':json.dumps(a)}}]})['answer'],a)
    def test_zero_and_extreme_oracles_no_inferential_claim_and_no_io(self):
        def zero(j,a):a['policy_support']=50;return a
        out,*_=analyzed(mutate=zero,io_guard=True)
        self.assertEqual(out['primary_wrapper_omitted']['mean_points'],0);self.assertEqual(out['visibility_interaction']['mean_points'],0)
        self.assertIsNone(out['visibility_interaction']['interval_95']);self.assertIn('equivalence',out['limitations'])
        for direction in (1,-1):
            def extreme(j,a):
                if j['phase']=='post':a['policy_support']=100 if ((j['wrapper']=='SOCIAL')==(j['visibility']=='SHOWN'))==(direction==1) else 0
                return a
            out,*_=analyzed(mutate=extreme)
            self.assertEqual(abs(out['primary_wrapper_omitted']['mean_points']),100)
            self.assertEqual(out['visibility_interaction']['mean_points'],200*direction)

if __name__=='__main__':unittest.main()
