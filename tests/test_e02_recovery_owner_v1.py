"""Authored recovery admission; no real owner, credentials or network."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import unittest

from civiclab.common import canonical_bytes, canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_compatibility_v4_2_1 import _answer
from civiclab.e02.exploratory_owner_v1 import (
    StudyOwnerV1, RECOVERY_METHODS_SHA, MODEL_IDENTITY_SHA)
from test_additional_compatibility_owner_v1 import case, append
from test_e02_exploratory_owner_v1 import packet_for, reserve, phase_files


def rebind(q):
    p,r,o,a,t = (q[k] for k in ('policy','review','owner_assertion','authority','terminal_review'))
    r['policy_hash']=canonical_hash(p)
    o.update(policy_hash=canonical_hash(p),review_hash=canonical_hash(r))
    a.update(policy_hash=canonical_hash(p),review_hash=canonical_hash(r),owner_assertion_hash=canonical_hash(o))
    t['packet_inputs_hash']=canonical_hash({k:v for k,v in q.items() if k!='terminal_review'})


def modern_stats(billing):
    return {**billing,'model':'openai/gpt-4.1-nano-2025-04-14',
            'service_tier':'default','streamed':True,'cancelled':False,
            'num_media_prompt':None,'num_search_results':None,'num_media_completion':0}


@contextmanager
def recovery_case():
    with case() as (prior,original,b,x,release,clock,old):
        append(prior,b,x,release)
        witness=_answer({'choices':[{'message':{'content':'{"ok": true}'}}]})
        generation='gen-authored-recovered'
        prior.transition(b['receipt'],'RESPONSE_SEEN',generation_id=generation,
                         output_hash=canonical_hash(witness),observed_cost=7)
        prior.claim_statistics_lookup(b['receipt'])
        prior.transition(b['receipt'],'UNCERTAIN',observed_cost=7,error_type='AuthoredUnavailableStatistics')
        owner=StudyOwnerV1.open();q=packet_for(owner,release,b['receipt']);p=q['policy']
        stats={'data':modern_stats({'id':generation,'model':release['terms']['model'],
            'provider_name':'Azure','is_byok':False,'total_cost':0.000007,
            'native_tokens_prompt':46,'native_tokens_completion':6,'native_tokens_reasoning':0})}
        p['kind']='LIMITED_PILOT_RECOVERY_POLICY_V1'
        p['recovery']={'kind':'CONNECTIVITY_RECOVERY_EVIDENCE_V1',
            'source_export_sha256':canonical_hash('AUTHORED_EXPORT'),
            'predecessor_hash':canonical_hash(p['predecessor']),
            'compatibility_receipt':b['receipt'],'generation_id':generation,
            'statistics_raw_sha256':hashlib.sha256(canonical_bytes(stats)).hexdigest(),
            'statistics':stats,'decoded_output_witness':witness,'original_response_retained':False,
            'historical_unfinished':2,'historical_consumed_microusd':680,
            'model_identity_source_sha256':MODEL_IDENTITY_SHA,'methods_sha256':RECOVERY_METHODS_SHA,
            'evidence_audit_sha256':canonical_hash('AUTHORED_EVIDENCE_REVIEW')}
        rebind(q)
        with owner._lock(),owner._connect() as db: state,head=owner._verify(db)
        yield owner,q,b['context']['price_proof'],clock,deepcopy(state['rows'])


def settle_modern(owner,ack,*,mutate_stats=None,mutate_response=None):
    from civiclab.e02.exploratory_metadata_v1 import normalize_statistics
    from civiclab.e02.exploratory_response_v1 import parse_survey_response
    output,billing,generation=phase_files(owner,ack,{'democratic_party':50,'republican_party':50})
    base=owner._journal(ack['context']['run_id']);receipt=ack['receipt'];c=ack['context']
    stats=modern_stats(billing)
    response_path=base/(receipt+'-response.json');cp_path=base/(receipt+'-checkpoint.json')
    response=json.loads(response_path.read_bytes());response['model']=stats['model']
    if mutate_response:mutate_response(response)
    raw=canonical_bytes(response);response_path.write_bytes(raw)
    parsed=parse_survey_response(response)
    output={'status':parsed['status'],'answer':parsed['answer'],'response_raw_sha256':hashlib.sha256(raw).hexdigest()}
    cp=json.loads(cp_path.read_bytes());cp['output']=output;cp_path.write_bytes(canonical_bytes(cp))
    projection=normalize_statistics(stats,generation_id=generation,
        requested_model=c['terms']['model'],reported_provider=c['terms']['reported_provider'],
        input_bound=c['envelope']['input_token_bound'],output_bound=512,
        reserved_microusd=c['envelope']['reserved_microusd'])['billing']
    if mutate_stats:mutate_stats(stats)
    (base/(receipt+'-statistics.json')).write_bytes(canonical_bytes({'data':stats}))
    owner.transition(receipt,'RESPONSE_SEEN',generation_id=generation,output_hash=canonical_hash(output),observed_cost=1)
    owner.claim_statistics_lookup(receipt)
    owner.transition(receipt,'SETTLED',observed_cost=1,billing=projection)


class RecoveryOwnerTests(unittest.TestCase):
    def test_complete_32_preserves_two_historical_uncertain_rows(self):
        with recovery_case() as (owner,q,proof,clock,oldrows):
            for _ in range(32):
                ack=reserve(owner,q,proof);settle_modern(owner,ack);owner.commit_survey(ack['receipt'])
            result=reserve(owner,q,proof)
            self.assertEqual(result['status'],'COMPLETE')
            self.assertEqual(result['consumed_microusd']['total'],712)
            self.assertEqual(result['consumed_microusd']['dispatches'],34)
            with owner._lock(),owner._connect() as db: state,_=owner._verify(db)
            self.assertEqual(state['unfinished'],2)
            self.assertEqual({k:state['rows'][k] for k in oldrows},oldrows)
            self.assertEqual(len(state['study']['witnesses']),32)

    def test_third_unfinished_blocks_any_next_grant(self):
        for mark_uncertain in (False,True):
            with self.subTest(mark_uncertain=mark_uncertain),recovery_case() as (owner,q,proof,_,oldrows):
                ack=reserve(owner,q,proof)
                if mark_uncertain:owner.transition(ack['receipt'],'UNCERTAIN',error_type='AuthoredStop')
                if mark_uncertain:self.assertEqual(reserve(owner,q,proof)['status'],'STOPPED')
                else:
                    with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)
                with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
                self.assertEqual(state['unfinished'],3)
                self.assertEqual({k:state['rows'][k] for k in oldrows},oldrows)
                self.assertEqual(state['consumed']['dispatches'],3)

    def test_forged_recovery_or_historical_bindings_rejected_without_write(self):
        for field in ('predecessor','generation','output','raw_hash','cost','identity','tier','count','history','claim','response_backfill'):
            with self.subTest(field=field),recovery_case() as (owner,q,proof,*_):
                before=owner.snapshot();p=q['policy'];r=p['recovery']
                if field=='predecessor':r['predecessor_hash']='0'*64
                elif field=='generation':r['generation_id']='gen-other'
                elif field=='output':r['decoded_output_witness']['raw_text']='{"ok":false}'
                elif field=='raw_hash':r['statistics_raw_sha256']='0'*64
                elif field in ('cost','identity','tier'):
                    name,value={'cost':('total_cost',0.000008),'identity':('model','openai/gpt-4.1-nano-OTHER'),
                                'tier':('service_tier',None)}[field]
                    r['statistics']['data'][name]=value
                    r['statistics_raw_sha256']=hashlib.sha256(canonical_bytes(r['statistics'])).hexdigest()
                elif field=='count':r['historical_unfinished']=True
                elif field in ('history','claim'):
                    p['predecessor']['history_hash' if field=='history' else 'statistics_claims_hash']='0'*64
                    r['predecessor_hash']=canonical_hash(p['predecessor'])
                else:r['original_response_retained']=True
                rebind(q)
                with self.assertRaises((ExecutionBlocked,ValueError)):reserve(owner,q,proof)
                self.assertEqual(owner.snapshot(),before)

    def test_legacy_mode_does_not_admit_failed_compatibility(self):
        with recovery_case() as (owner,q,proof,*_):
            q['policy']['kind']='LIMITED_PILOT_POLICY_V1';del q['policy']['recovery'];rebind(q)
            with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)

    def test_commit_rederives_raw_normalized_billing_and_activity(self):
        mutations=[lambda s:s.update(model='openai/gpt-4.1-nano-OTHER'),
                   lambda s:s.update(num_search_results=1),lambda s:s.update(native_tokens_prompt=True),
                   lambda s:s.update(service_tier=None),lambda s:s.update(streamed=None),
                   lambda s:s.update(total_cost=0.000002),lambda s:s.update(cancelled=True)]
        for mutate in mutations:
            with self.subTest(mutate=mutate),recovery_case() as (owner,q,proof,*_):
                ack=reserve(owner,q,proof);settle_modern(owner,ack,mutate_stats=mutate)
                with self.assertRaises((ExecutionBlocked,ValueError)):owner.commit_survey(ack['receipt'])
                self.assertEqual(owner.study_snapshot()['transcript'],[])
                with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)

    def test_wrong_dated_response_model_refused_at_commit(self):
        with recovery_case() as (owner,q,proof,*_):
            ack=reserve(owner,q,proof)
            settle_modern(owner,ack,mutate_response=lambda r:r.update(model='openai/gpt-4.1-nano-OTHER'))
            with self.assertRaises((ExecutionBlocked,ValueError)):owner.commit_survey(ack['receipt'])


if __name__=='__main__':unittest.main()
