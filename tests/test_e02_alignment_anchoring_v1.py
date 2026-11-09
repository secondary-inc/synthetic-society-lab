"""Pure, authored arithmetic/control oracles; no empirical model effects."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.e02 import alignment_anchoring_v1 as m
from test_additional_compatibility_owner_v1 import materials

RAW=(Path(__file__).resolve().parents[1]/'configs/e02_alignment_anchoring_followup_v1.json').read_bytes()
P=m.load_protocol(RAW)


def terms():return materials('AUTHORED_ALIGNMENT_PRICE_ONLY')[0]['terms']


def answer(job,*,unchanged=False):
    support=50
    if job['phase']=='post' and not unchanged:
        support={'N01':50,'N02':80 if job['baseline_mode']=='OMITTED' else 65,
                 'N03':20 if job['baseline_mode']=='OMITTED' else 35}[job['notice_id']]
    return {'democratic_party':60,'republican_party':40,'library_support':support,
            'visits_change':next(n['visits_change_key'] for n in P['notices'] if n['id']==job['notice_id'])}


def build(*,mutate=None,stop_at=None,unchanged=False):
    t=terms();rows=[];requests=[]
    while True:
        state=m.next_action(RAW,t,canonical_bytes(rows))
        if state['status']!='REQUEST_READY_NOT_ADMITTED':return rows,state,requests,t
        r=state['request'];job=P['jobs'][r['execution_order']];value=answer(job,unchanged=unchanged)
        if mutate:value=mutate(job,value)
        status='FAILED_UNCERTAIN' if len(rows)==stop_at else 'ANSWER'
        rows.append({'execution_order':r['execution_order'],'phase':r['phase'],'payload_sha256':r['payload_sha256'],
                     'status':status,'answer':value if status=='ANSWER' else None});requests.append(r)


def analyzed(**kwargs):
    rows,state,requests,t=build(**kwargs)
    return m.analyze(RAW,canonical_bytes(state['response_envelope'])),rows,state,requests,t


class AlignmentTests(unittest.TestCase):
    def test_exact28_protocol_quotes_and_no_authority(self):
        self.assertEqual(len(P['jobs']),28);self.assertEqual([j['phase'] for j in P['jobs'][:4]],['pre']*4)
        self.assertFalse(P['actual_authority']);self.assertIsNone(P['results'])
        self.assertEqual(m.cost_envelope(RAW,terms())['maximum_POSTs'],28)
        with self.assertRaises(ExecutionBlocked):m.load_protocol(RAW+b' ')
    def test_authored_changed_arithmetic_and_comprehension_oracle(self):
        out,rows,state,requests,_=analyzed()
        self.assertEqual(len(rows),28);self.assertEqual(out['primary_absent_content_contrast']['mean_points'],60)
        self.assertEqual(out['shown_content_contrast']['mean_points'],30)
        self.assertEqual(out['anchoring_interaction']['mean_points'],-30)
        self.assertEqual(out['primary_absent_content_contrast']['complete_contexts'],4)
        self.assertIsNone(out['primary_absent_content_contrast']['interval_95'])
        self.assertTrue(out['prespecified_patterns']['content_sensitive']);self.assertTrue(out['prespecified_patterns']['anchoring_compatible'])
        self.assertTrue(all(row['value']==0 for row in out['separate_partisan_gap_changes']))
        self.assertEqual(out['comprehension']['OMITTED']['correct'],12)
        self.assertEqual(out['comprehension']['SHOWN']['correct'],12)
        self.assertEqual(out['response_provenance'],'MOCK')
    def test_unchanged_oracle_null_interval_not_equivalence(self):
        out,*_=analyzed(unchanged=True)
        self.assertEqual(out['primary_absent_content_contrast']['mean_points'],0)
        self.assertEqual(out['anchoring_interaction']['mean_points'],0)
        self.assertTrue(out['prespecified_patterns']['support_stable_notice_understood'])
        self.assertIn('no inferential interval or equivalence',out['limitations'])
    def test_exact_request_ablation_no_hidden_answers_or_condition_keys(self):
        _,_,_,requests,_=analyzed()
        by={r['execution_order']:r for r in requests}
        for profile in P['profiles']:
            for notice in P['notices']:
                pair=[j for j in P['jobs'] if j['phase']=='post' and j['profile']==profile and j['notice_id']==notice['id']]
                shown=next(by[j['execution_order']] for j in pair if j['baseline_mode']=='SHOWN')
                omitted=next(by[j['execution_order']] for j in pair if j['baseline_mode']=='OMITTED')
                a=deepcopy(shown['request']);b=omitted['request']
                baseline=a.pop('pre_response');self.assertEqual(set(baseline),m.KEYS);self.assertEqual(a,b)
                self.assertNotIn('baseline_mode',b);self.assertNotIn('notice_id',b['notice'])
                self.assertNotIn('visits_change_key',b['notice'])
                self.assertEqual(shown['payload']['seed'],omitted['payload']['seed'])
                self.assertEqual(shown['payload']['messages'][0],omitted['payload']['messages'][0])
    def test_baselines_are_new_neutral_reference_not_unexposed(self):
        _,_,_,requests,_=analyzed()
        for request in requests[:4]:
            self.assertIn('No measured effect',request['request']['notice']['text'])
            self.assertNotIn('pre_response',request['request'])
            self.assertEqual(request['phase'],'pre')
    def test_invalid_pre_skips_three_shown_but_keeps_omitted_and_primary(self):
        pid=P['profiles'][0]['profile_id']
        def mutate(job,value):
            if job['phase']=='pre' and job['profile']['profile_id']==pid:value['library_support']=None
            return value
        out,rows,state,requests,_=analyzed(mutate=mutate)
        self.assertEqual(len(rows),25);self.assertEqual(out['phase_counts']['SKIPPED_INVALID_PRE'],3)
        self.assertEqual(out['primary_absent_content_contrast']['complete_contexts'],4)
        self.assertEqual(out['anchoring_interaction']['complete_contexts'],3)
        self.assertFalse(any(r['request']['profile']['profile_id']==pid and r['baseline_mode']=='SHOWN' for r in requests))
    def test_wrong_comprehension_never_excludes_primary_or_reelicits_baseline(self):
        def mutate(job,value):value['visits_change']='DECREASE_40';return value
        out,rows,*_=analyzed(mutate=mutate)
        self.assertEqual(len(rows),28);self.assertEqual(out['primary_absent_content_contrast']['mean_points'],60)
        self.assertEqual(out['primary_absent_content_contrast']['complete_contexts'],4)
        self.assertFalse(out['prespecified_patterns']['content_sensitive'])
        self.assertTrue(out['prespecified_patterns']['task_following_concern'])
    def test_unrelated_bad_thermometers_do_not_exclude_valid_support(self):
        def mutate(job,value):
            if job['phase']=='post':value['democratic_party']=None
            return value
        out,*_=analyzed(mutate=mutate)
        self.assertEqual(out['primary_absent_content_contrast']['mean_points'],60)
        self.assertTrue(all(r['value'] is None for r in out['separate_partisan_gap_changes']))
    def test_support_missing_one_target_excludes_only_required_context(self):
        pid=P['profiles'][0]['profile_id']
        def mutate(job,value):
            if job['phase']=='post' and job['profile']['profile_id']==pid and job['notice_id']=='N02' and job['baseline_mode']=='OMITTED':value['library_support']=None
            return value
        out,*_=analyzed(mutate=mutate)
        self.assertEqual(out['primary_absent_content_contrast']['complete_contexts'],3)
        self.assertEqual(out['shown_content_contrast']['complete_contexts'],4)
        self.assertEqual(out['anchoring_interaction']['complete_contexts'],3)
    def test_partisan_direction_is_preserved_separately(self):
        def mutate(job,value):
            if job['phase']=='post':value['democratic_party']=61;value['republican_party']=39
            return value
        out,*_=analyzed(mutate=mutate)
        for row in out['separate_partisan_gap_changes']:self.assertEqual(row['value'],2 if row['party']=='D' else -2)
    def test_stop_and_empty_record_dispositions_export_all28(self):
        for n in (0,4,15):
            with self.subTest(n=n):
                out,rows,state,_,t=analyzed(stop_at=n)
                self.assertEqual(state['status'],'STOPPED');self.assertEqual(len(state['response_envelope']['records']),28)
                self.assertEqual(out['phase_counts']['FAILED_UNCERTAIN'],1)
                self.assertTrue(all(r['status']=='NOT_ATTEMPTED' for r in state['records'][n+1:]))
        envelope=m.response_envelope(RAW,b'[]',stopped=True)
        out=m.analyze(RAW,canonical_bytes(envelope));self.assertEqual(out['status'],'NOT_ESTIMABLE')
        self.assertIsNone(out['primary_absent_content_contrast']['mean_points'])
        with self.assertRaises(ExecutionBlocked):m.response_envelope(RAW,b'[]')
    def test_envelope_export_terms_and_structural_projection_match(self):
        rows,state,_,t=build()
        a=m.response_envelope(RAW,canonical_bytes(rows),terms=t)
        b=m.response_envelope(RAW,canonical_bytes(rows))
        self.assertEqual(a,b);self.assertEqual(a,state['response_envelope'])
        live=m.response_envelope(RAW,canonical_bytes(rows),response_provenance='EXPLORATORY_REAL_MODEL')
        self.assertEqual(m.analyze(RAW,canonical_bytes(live))['response_provenance'],'EXPLORATORY_REAL_MODEL')
    def test_tampering_extra_afterstop_and_envelope_bindings_refused(self):
        rows,state,_,t=build();bad=deepcopy(rows);bad[4]['payload_sha256']='0'*64
        with self.assertRaises(ExecutionBlocked):m.next_action(RAW,t,canonical_bytes(bad))
        stopped=deepcopy(rows[:1]);stopped[0].update(status='FAILED_UNCERTAIN',answer=None)
        with self.assertRaises(ExecutionBlocked):m.next_action(RAW,t,canonical_bytes(stopped+rows[1:2]))
        for key in ('protocol_sha256','instrument_sha256','assignment_sha256','response_provenance'):
            e=deepcopy(state['response_envelope']);e[key]='bad'
            with self.assertRaises(ExecutionBlocked):m.analyze(RAW,canonical_bytes(e))
    def test_parser_duplicate_nonfinite_object_and_size_bounds(self):
        for text in ['{"x":1,"x":2}','NaN','[]','1e999','"text"','{"x":"'+'z'*33+'"}', '{"x":'+ '1'*33+'}']:
            r=m.parse_response({'choices':[{'message':{'content':text}}]})
            self.assertEqual(r['status'],'PARSE_ERROR',text[:20])
        good=answer(P['jobs'][0]);r=m.parse_response({'choices':[{'message':{'content':json.dumps(good)}}]})
        self.assertEqual(r['answer'],good)
    def test_secondary_notice_denominators_and_baseline_quality_explicit(self):
        out,*_=analyzed()
        self.assertEqual(out['baseline_quality']['valid_for_shown'],4)
        self.assertEqual(out['baseline_quality']['comprehension_counts'],{'CORRECT':4})
        for mode in ('OMITTED','SHOWN'):
            self.assertEqual(out['comprehension'][mode]['by_notice']['N02'],{'planned':4,'valid':4,'correct':4})
            self.assertEqual(out['separate_partisan_content_contrasts'][mode]['mean_points'],0)
    def test_duplicate_records_invalid_skips_and_post_afterstop_rejected(self):
        _,_,state,_,_=analyzed()
        for mutation in ('duplicate','skip','afterstop'):
            with self.subTest(mutation=mutation):
                e=deepcopy(state['response_envelope'])
                if mutation=='duplicate':e['records'][1]=deepcopy(e['records'][0])
                elif mutation=='skip':e['records'][0].update(status='SKIPPED_INVALID_PRE',answer=None)
                else:e['records'][0].update(status='FAILED_UNCERTAIN',answer=None)
                with self.assertRaises(ExecutionBlocked):m.analyze(RAW,canonical_bytes(e))
    def test_primary_range_extremes_and_no_io(self):
        def mutate(job,value):
            if job['phase']=='post':value['library_support']=100 if job['notice_id']=='N02' else 0
            return value
        out,*_=analyzed(mutate=mutate)
        self.assertEqual(out['primary_absent_content_contrast']['mean_points'],100)
        with patch('builtins.open',side_effect=AssertionError('pure code performed I/O')):
            self.assertEqual(m.load_protocol(RAW)['protocol_id'],P['protocol_id'])


if __name__=='__main__':unittest.main()
