"""Isolated same-owner follow-up integration; all HTTP/key boundaries mocked."""
from contextlib import contextmanager
from copy import deepcopy
import json
import unittest
import uuid
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash,sha256_file
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
from civiclab.production_compatibility_v4_2_1 import _SafeExecutionFailure
from civiclab.e02.alignment_anchoring_owner_v1 import AlignmentOwnerV1,code_contract,LIMITS,PROTOCOL
from civiclab.e02 import alignment_anchoring_client_v1 as client
from test_e02_continuation_owner_v1 import continuation_case
from test_e02_exploratory_owner_v1 import reserve
from test_e02_recovery_owner_v1 import settle_modern
from test_production_price_v4 import catalog,COMPONENTS


def bind(q):
    p=q['policy'];p['code_contract_hash']=canonical_hash(code_contract())
    q['authority']={'kind':'ALIGNMENT_PILOT_AUTHORITY_V1','approval_id':uuid.uuid4().hex,
        'policy_hash':canonical_hash(p),'code_contract_hash':p['code_contract_hash']}
    q['review']={'kind':'INDEPENDENT_ALIGNMENT_STUDY_REVIEW_V1','reviewer_role':'independent_auditor',
        'review_id':uuid.uuid4().hex,'inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='review'})}
    return q


@contextmanager
def case():
    with continuation_case() as (prior,b,proof,oldrows):
        prior.start_continuation(b,proof,expected_bundle_hash=canonical_hash(b))
        for _ in range(16):
            ack=reserve(prior,b['packet'],proof);settle_modern(prior,ack);prior.commit_survey(ack['receipt'])
        owner=AlignmentOwnerV1()
        with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
        before=deepcopy(state);old=b['packet']['policy'];release=deepcopy(b['packet']['price_release'])
        p={'kind':'ALIGNMENT_STUDY_POLICY_V1','owner_id':owner.header['owner_id'],
            'run_id':'AUTHORED_ALIGNMENT_FOLLOWUP','valid_from_utc':old['valid_from_utc'],
            'valid_until_utc':old['valid_until_utc'],'limits':deepcopy(LIMITS),
            'protocol_sha256':sha256_file(PROTOCOL),'price_release_hash':canonical_hash(release),
            'consent_evidence_hash':canonical_hash('AUTHORED_STANDING_AUTHORITY'),
            'predecessor':{'head':head,'history_hash':canonical_hash(state['_prefix_events']),
                'rows_hash':canonical_hash(state['rows']),'study_hash':canonical_hash(state['study']),
                'continuation_hash':canonical_hash(state['continuation']),
                'claims_hash':canonical_hash(sorted(state['statistics_claims'])),'consumed':deepcopy(state['consumed'])}}
        q=bind({'kind':'ALIGNMENT_STUDY_PACKET_V1','policy':p,'price_release':release})
        yield owner,q,proof,before


class Transport:
    def __init__(self,mode='success'):self.posts=0;self.gets=0;self.mode=mode
    def post_bytes(self,raw):
        self.posts+=1;p=json.loads(raw)
        result={'id':f'gen-alignment-authored-{self.posts}','model':p['model'],
            'choices':[{'message':{'content':json.dumps({'democratic_party':50,'republican_party':50,
                'library_support':50,'visits_change':'NOT_REPORTED'})}}],
            'usage':{'cost':0.000001,'prompt_tokens':1,'completion_tokens':1}}
        if self.mode=='delayed' and self.posts==1:result.pop('usage')
        return result
    def statistics(self,generation):
        self.gets+=1
        if self.mode=='404' or (self.mode=='delayed' and self.gets<=2):
            raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
        return {'data':{'id':generation,'model':'openai/gpt-4.1-nano-2025-04-14','provider_name':'Azure',
            'is_byok':False,'total_cost':0.000001,'native_tokens_prompt':1,'native_tokens_completion':1,
            'native_tokens_reasoning':0,'service_tier':'default','streamed':True,'cancelled':False}}


@contextmanager
def boundaries(owner,proof,transport):
    data=catalog();data['data']['id']='openai/gpt-4.1-nano'
    for i,e in enumerate(data['data']['endpoints']):
        e.update(model_id='openai/gpt-4.1-nano',provider_name='Azure',tag='azure' if i==0 else 'azure/authored')
        e['pricing']={k:'0' for k in COMPONENTS};e['pricing']['request']='0.000340'
    metadata={k:proof[k] for k in ('url','body_sha256','observed_at_utc')}
    assert canonical_hash(data)==metadata['body_sha256']
    mono=[0.0]
    with patch.object(client,'_owner',return_value=owner), \
         patch.object(client,'_fetch_public_catalog',return_value=(canonical_bytes(data),metadata)), \
         patch.object(client,'_read_environment_key',return_value=_Credential('AUTHORED_KEY_NOT_REAL_123456789')), \
         patch.object(client,'_transport',return_value=transport), \
         patch.object(client.time,'monotonic',side_effect=lambda:mono[0]), \
         patch.object(client.time,'sleep',side_effect=lambda n:mono.__setitem__(0,mono[0]+n)):
        yield


class ExecutionTests(unittest.TestCase):
    def test_complete_followup_preserves_original_history_and_cannot_replay(self):
        with case() as (owner,q,proof,before):
            t=Transport('delayed')
            with boundaries(owner,proof,t):result=client.execute_followup(q,expected_packet_hash=canonical_hash(q))
            self.assertEqual(result['status'],'COMPLETE')
            self.assertEqual((t.posts,t.gets),(28,30))
            self.assertEqual(len(result['response_envelope']['records']),28)
            self.assertEqual(result['analysis']['response_provenance'],'MOCK')
            with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
            self.assertEqual(len(state['_prefix_events']),len(before['_prefix_events'])+169)
            self.assertEqual(state['consumed']['dispatches'],62);self.assertEqual(state['unfinished'],3)
            self.assertEqual(state['_prefix_events'][:len(before['_prefix_events'])],before['_prefix_events'])
            self.assertEqual({k:state['rows'][k] for k in before['rows']},before['rows'])
            self.assertEqual(state['study'],before['study']);self.assertEqual(state['continuation'],before['continuation'])
            self.assertEqual(sum(r['charged'] for r in state['rows'].values()),state['consumed']['total'])
            with self.assertRaises(ExecutionBlocked):owner.start_followup(q,proof,expected_packet_hash=canonical_hash(q))
            self.assertEqual(owner.reserve_next(q,proof,expected_packet_hash=canonical_hash(q),transport_ready=lambda c:True)['status'],'COMPLETE')
            with self.assertRaises(ExecutionBlocked):owner.transition(next(iter(before['rows'])),'UNCERTAIN',error_type='AuthoredForeignRow')

    def test_exhausted_billing_keeps_hold_and_stops_after_one_post(self):
        with case() as (owner,q,proof,before):
            t=Transport('404')
            with boundaries(owner,proof,t),self.assertRaises(_SafeExecutionFailure):
                client.execute_followup(q,expected_packet_hash=canonical_hash(q))
            self.assertEqual((t.posts,t.gets),(1,3))
            s=owner.study_snapshot();self.assertEqual(s['status'],'STOPPED')
            self.assertEqual(s['transcript'][0]['status'],'FAILED_UNCERTAIN')
            self.assertEqual(owner.reserve_next(q,proof,expected_packet_hash=canonical_hash(q),transport_ready=lambda c:True)['status'],'STOPPED')
            with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
            row=state['rows'][state['alignment_followup']['receipts'][0]]
            self.assertEqual(row['charged'],row['reserved']);self.assertEqual(state['unfinished'],4)
            self.assertEqual({k:state['rows'][k] for k in before['rows']},before['rows'])

    def test_changed_ancestry_caps_or_clock_refused_without_new_rows(self):
        with case() as (owner,q,proof,before):
            original=owner.snapshot()
            for field in ('ancestry','count','money','expired'):
                candidate=deepcopy(q)
                if field=='ancestry':candidate['policy']['predecessor']['rows_hash']='0'*64
                elif field=='count':candidate['policy']['limits']['new_model_POSTs']=29
                elif field=='money':candidate['policy']['limits']['cumulative_E02_microusd']=1000001
                else:candidate['policy']['valid_until_utc']=candidate['policy']['valid_from_utc']
                bind(candidate)
                with self.subTest(field=field),self.assertRaises((ExecutionBlocked,ValueError)):
                    owner.start_followup(candidate,proof,expected_packet_hash=canonical_hash(candidate))
                self.assertEqual(owner.snapshot(),original)


if __name__=='__main__':unittest.main()
