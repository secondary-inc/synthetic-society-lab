"""Authored pure engineering checks; no empirical inference or paid operations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes, canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.e02 import issue_cue_crossmodel_v1 as m
from test_additional_compatibility_owner_v1 import materials

RAW = (Path(__file__).resolve().parents[1]/'configs/e02_issue_cue_crossmodel_v1.json').read_bytes()
P = m.load_protocol(RAW)


def terms():
    a = materials('AUTHORED_CROSSMODEL_PRICE_ONLY')[0]['terms']
    a['request_fee_usd'] = '0'
    for v in a['components_by_tag'].values(): v['request'] = '0'
    b = deepcopy(a); b.update(P['models']['B'])
    b['components_by_tag'] = {'nebius/fp8': deepcopy(next(iter(a['components_by_tag'].values())))}
    for t,inp,out in ((a,'0.000000143','0.00000044'),(b,'0.00000020','0.00000030')):
        t['input_usd_per_token']=inp; t['output_usd_per_token']=out
        for v in t['components_by_tag'].values():v['prompt']=inp;v['completion']=out
    return {'A': a, 'B': b}


def answer(job, unchanged=False):
    support = 40 if job['model_key'] == 'A' else 60
    if job['phase'] == 'post':
        support = 50
        if not unchanged:
            support = ({'N01':50, 'N02':80 if job['baseline_mode']=='OMITTED' else 65,
                        'N03':20 if job['baseline_mode']=='OMITTED' else 35} if job['model_key']=='A' else
                       {'N01':50, 'N02':90 if job['baseline_mode']=='OMITTED' else 60,
                        'N03':10 if job['baseline_mode']=='OMITTED' else 40})[job['notice_id']]
    return {'democratic_party':60, 'republican_party':40, 'library_support':support,
            'visits_change':next(n['visits_change_key'] for n in P['notices'] if n['id']==job['notice_id'])}


def build(mutate=None, stop_at=None, unchanged=False):
    t=terms(); rows=[]; requests=[]
    while True:
        state=m.next_action(RAW,t,canonical_bytes(rows))
        if state['status']!='REQUEST_READY_NOT_ADMITTED':return rows,state,requests,t
        r=state['request']; job=P['jobs'][r['execution_order']]; value=answer(job,unchanged)
        if mutate:value=mutate(job,value)
        status='FAILED_UNCERTAIN' if len(rows)==stop_at else 'ANSWER'
        rows.append(dict(execution_order=r['execution_order'],phase=r['phase'],payload_sha256=r['payload_sha256'],status=status,answer=value if status=='ANSWER' else None))
        requests.append(r)


def analyzed(**kw):
    rows,state,requests,t=build(**kw)
    return m.analyze(RAW,canonical_bytes(state['response_envelope'])),rows,state,requests,t


class CrossmodelTests(unittest.TestCase):
    def test_exact_fixed56_and_matched_alternating_pairs(self):
        self.assertEqual(len(P['jobs']),56)
        self.assertEqual([j['phase'] for j in P['jobs'][:8]],['pre']*8)
        for start,end in ((0,8),(8,56)):
            for pair,i in enumerate(range(start,end,2)):
                a,b=P['jobs'][i:i+2]
                self.assertEqual([a['model_key'],b['model_key']],['A','B'] if pair%2==0 else ['B','A'])
                self.assertEqual({k:v for k,v in a.items() if k not in ('model_key','execution_order','baseline_execution_order')},
                                 {k:v for k,v in b.items() if k not in ('model_key','execution_order','baseline_execution_order')})
        for job in P['jobs'][8:]:
            before=P['jobs'][job['baseline_execution_order']]
            self.assertEqual((before['model_key'],before['profile']),(job['model_key'],job['profile']))
        self.assertEqual(P['envelope']['maximum_total_tokens'],56*(8192+256))
        with self.assertRaises(ExecutionBlocked):m.load_protocol(RAW+b' ')
    def test_schedule_reconstructs_seed_without_outcomes(self):
        profiles=list(P['profiles']);random.Random(P['seed']).shuffle(profiles)
        self.assertEqual([P['jobs'][i]['profile'] for i in range(0,8,2)],profiles)
        cells=[(p,n,mode) for p in profiles for n in ('N01','N02','N03') for mode in ('OMITTED','SHOWN')]
        random.Random(P['seed']+1).shuffle(cells)
        self.assertEqual([(j['profile'],j['notice_id'],j['baseline_mode']) for j in P['jobs'][8::2]],cells)
        for j in P['jobs']:
            seed=int(canonical_hash([P['seed'],j['profile']['profile_id']])[:8],16)
            items=[i['id'] for i in P['instrument']['items']];random.Random(seed).shuffle(items)
            self.assertEqual(j['pair_seed'],seed);self.assertEqual(j['item_order'],items)
    def test_cost_model_binding_and_caps(self):
        t=terms();self.assertEqual(m.cost_envelope(RAW,t)['maximum_POSTs'],56)
        for mutation in ('swap','extra','cost','provider','route','scope','output'):
            x=deepcopy(t)
            if mutation=='swap':x['A'],x['B']=x['B'],x['A']
            elif mutation=='extra':x['C']=x['A']
            elif mutation=='cost':
                x['A']['request_fee_usd']='1'
                for v in x['A']['components_by_tag'].values():v['request']='1'
            else:x['B'][{'provider':'reported_provider','route':'requested_route','scope':'route_scope','output':'output_parameter'}[mutation]]='bad'
            with self.assertRaises((ExecutionBlocked,ValueError)):m.cost_envelope(RAW,x)
    def test_arithmetic_two_interactions_common_crossmodel_and_labels(self):
        out,rows,state,requests,t=analyzed()
        self.assertEqual(len(rows),56)
        self.assertEqual(out['models']['A']['primary_cue_interaction']['mean_points'],-30)
        self.assertEqual(out['models']['B']['primary_cue_interaction']['mean_points'],-60)
        self.assertEqual(out['crossmodel_common_context_interaction_difference']['mean_points'],-30)
        self.assertEqual(out['crossmodel_common_context_interaction_difference']['complete_contexts'],4)
        self.assertTrue(out['prespecified_patterns']['attenuation_across_both_fixed_configurations'])
        self.assertEqual(out['response_provenance'],'MOCK');self.assertFalse(out['actual_authority'])
        self.assertIsNone(out['models']['A']['primary_cue_interaction']['interval_95'])
    def test_only_own_support_added_request_ablation(self):
        out,rows,state,requests,t=analyzed();by={r['execution_order']:r for r in requests}
        for job in P['jobs'][8:]:
            if job['baseline_mode']!='SHOWN':continue
            shown=by[job['execution_order']]
            twin=next(j for j in P['jobs'] if j['model_key']==job['model_key'] and j['profile']==job['profile'] and j['notice_id']==job['notice_id'] and j['baseline_mode']=='OMITTED')
            a=deepcopy(shown['request']);cue=a.pop('pre_response')
            self.assertEqual(cue,{'library_support':40 if job['model_key']=='A' else 60})
            self.assertEqual(a,by[twin['execution_order']]['request'])
            self.assertNotIn('model_key',a);self.assertNotIn('baseline_mode',a)
            self.assertNotIn('visits_change_key',a['notice']);self.assertNotIn('id',a['notice'])
            self.assertEqual(shown['payload']['model'],P['models'][job['model_key']]['model'])
            self.assertEqual(shown['payload']['max_completion_tokens'],256)
            self.assertFalse(shown['payload']['provider']['allow_fallbacks'])
    def test_missing_unrelated_pre_items_preserve_all_support_cues(self):
        def mutate(j,a):
            if j['phase']=='pre':a.pop('democratic_party');a['republican_party']=None;a.pop('visits_change')
            return a
        out,rows,*_=analyzed(mutate=mutate)
        self.assertEqual(len(rows),56)
        for role in m.ROLES:
            self.assertEqual(out['models'][role]['baseline_quality']['valid_for_shown'],4)
            self.assertEqual(out['models'][role]['primary_cue_interaction']['complete_contexts'],4)
            self.assertTrue(all(x['value'] is None for x in out['models'][role]['separate_partisan_gap_changes']))
    def test_invalid_own_pre_skips_only_three_same_model_posts(self):
        pid=P['profiles'][0]['profile_id']
        for invalid in (None,True,'50',-1,101):
            def mutate(j,a):
                if j['phase']=='pre' and j['model_key']=='B' and j['profile']['profile_id']==pid:a['library_support']=invalid
                return a
            out,rows,state,requests,t=analyzed(mutate=mutate)
            self.assertEqual(len(rows),53);self.assertEqual(out['phase_counts']['SKIPPED_INVALID_PRE'],3)
            self.assertEqual(out['models']['A']['primary_cue_interaction']['complete_contexts'],4)
            self.assertEqual(out['models']['B']['primary_cue_interaction']['complete_contexts'],3)
            self.assertEqual(out['models']['B']['content_contrasts']['OMITTED']['complete_contexts'],4)
            self.assertEqual(out['models']['B']['comprehension']['SHOWN']['observed_factual_errors'],0)
            self.assertEqual(out['models']['B']['comprehension']['SHOWN']['quality_counts']['UNASKED'],3)
    def test_unknown_extra_key_invalidates_all_items_no_repair(self):
        def mutate(j,a):
            if j['phase']=='pre':a['unknown']=1
            return a
        out,rows,*_=analyzed(mutate=mutate)
        self.assertEqual(len(rows),32);self.assertEqual(out['phase_counts']['SKIPPED_INVALID_PRE'],24)
        self.assertEqual(out['status'],'NOT_ESTIMABLE')
        self.assertIsNone(out['crossmodel_common_context_interaction_difference']['mean_points'])
        self.assertFalse(out['prespecified_patterns']['attenuation_across_both_fixed_configurations'])
    def test_crossmodel_common_intersection_never_difference_unmatched_means(self):
        pid=P['profiles'][0]['profile_id']
        def mutate(j,a):
            if j['phase']=='post' and j['model_key']=='A' and j['profile']['profile_id']==pid:
                if j['notice_id']=='N02':a['library_support']=100
                if j['notice_id']=='N03':a['library_support']=0 if j['baseline_mode']=='OMITTED' else 100
            if j['phase']=='post' and j['model_key']=='B' and j['profile']['profile_id']==pid and j['notice_id']=='N02' and j['baseline_mode']=='OMITTED':a.pop('library_support')
            return a
        out,*_=analyzed(mutate=mutate)
        self.assertEqual(out['models']['A']['primary_cue_interaction']['mean_points'],-47.5)
        self.assertEqual(out['models']['B']['primary_cue_interaction']['mean_points'],-60)
        self.assertEqual(out['crossmodel_common_context_interaction_difference']['complete_contexts'],3)
        self.assertEqual(out['crossmodel_common_context_interaction_difference']['mean_points'],-30)
    def test_quality_denominators_separate_wrong_missing_and_unasked(self):
        pid=P['profiles'][0]['profile_id']
        def mutate(j,a):
            if j['phase']=='post' and j['model_key']=='A' and j['baseline_mode']=='OMITTED' and j['profile']['profile_id']==pid:
                if j['notice_id']=='N01':a.pop('visits_change')
                if j['notice_id']=='N02':a['visits_change']=None
                if j['notice_id']=='N03':a['visits_change']='INCREASE_40'
            return a
        out,*_=analyzed(mutate=mutate);c=out['models']['A']['comprehension']['OMITTED']
        self.assertEqual((c['planned'],c['valid'],c['correct'],c['observed_factual_errors']),(12,10,9,1))
        self.assertEqual(c['quality_counts']['MISSING_KEY'],1);self.assertEqual(c['quality_counts']['MISSING_NULL'],1)
        self.assertEqual(out['models']['A']['primary_cue_interaction']['complete_contexts'],4)
    def test_stop_export_empty_and_no_extra_after_stop(self):
        for i in (0,7,28,55):
            out,rows,state,requests,t=analyzed(stop_at=i)
            self.assertEqual(state['status'],'STOPPED');self.assertEqual(len(state['records']),56)
            self.assertEqual(out['phase_counts']['FAILED_UNCERTAIN'],1)
            self.assertTrue(all(r['status']=='NOT_ATTEMPTED' for r in state['records'][i+1:]))
            self.assertEqual(m.response_envelope(RAW,canonical_bytes(rows),terms_by_model=t),state['response_envelope'])
        e=m.response_envelope(RAW,b'[]',stopped=True,terms_by_model=terms())
        out=m.analyze(RAW,canonical_bytes(e));self.assertEqual(out['status'],'NOT_ESTIMABLE')
        self.assertIsNone(out['models']['A']['primary_cue_interaction']['mean_points'])
        with self.assertRaises(ExecutionBlocked):m.response_envelope(RAW,b'[]')
        rows,state,requests,t=build();rows[0].update(status='FAILED_UNCERTAIN',answer=None)
        with self.assertRaises(ExecutionBlocked):m.next_action(RAW,t,canonical_bytes(rows[:2]))
    def test_full_export_payload_tamper_and_protocol_envelope_pins(self):
        rows,state,requests,t=build()
        self.assertEqual(m.response_envelope(RAW,canonical_bytes(rows)),state['response_envelope'])
        self.assertEqual(m.response_envelope(RAW,canonical_bytes(rows),terms_by_model=t),state['response_envelope'])
        rows[1]['payload_sha256']=rows[0]['payload_sha256']
        with self.assertRaises(ExecutionBlocked):m.next_action(RAW,t,canonical_bytes(rows))
        for k in ('protocol_sha256','instrument_sha256','assignment_sha256','response_provenance'):
            e=deepcopy(state['response_envelope']);e[k]='bad'
            with self.assertRaises(ExecutionBlocked):m.analyze(RAW,canonical_bytes(e))
        for mutation in ('duplicate','skip','afterstop'):
            e=deepcopy(state['response_envelope'])
            if mutation=='duplicate':e['records'][1]=deepcopy(e['records'][0])
            elif mutation=='skip':e['records'][0].update(status='SKIPPED_INVALID_PRE',answer=None)
            else:e['records'][0].update(status='FAILED_UNCERTAIN',answer=None)
            with self.assertRaises(ExecutionBlocked):m.analyze(RAW,canonical_bytes(e))
    def test_parse_bounded_partial_known_shape_and_scoring(self):
        for text in ('[]','NaN','1e999','{"x":1,"x":2}','{"x":"'+'x'*33+'"}'):
            self.assertEqual(m.parse_response({'choices':[{'message':{'content':text}}]})['status'],'PARSE_ERROR')
        for a,eligible in (({'library_support':50},True),({'library_support':50,'extra':1},False),({},False)):
            parsed=m.parse_response({'choices':[{'message':{'content':json.dumps(a)}}]})
            self.assertEqual(parsed['answer'],a);self.assertEqual(m.valid_baseline(a),eligible)
        for bad in (True,'50',None,101,-1,float('nan'),float('inf')):self.assertFalse(m.valid_baseline({'library_support':bad}))
    def test_unchanged_and_pure_no_effect_claim_or_io(self):
        out,*_=analyzed(unchanged=True)
        self.assertEqual(out['models']['A']['primary_cue_interaction']['mean_points'],0)
        self.assertFalse(out['prespecified_patterns']['attenuation_across_both_fixed_configurations'])
        self.assertIn('equivalence',out['limitations'])
        with patch('builtins.open',side_effect=AssertionError('unexpected I/O')):
            self.assertEqual(m.next_action(RAW,terms(),b'[]')['request']['execution_order'],0)


if __name__=='__main__':unittest.main()
