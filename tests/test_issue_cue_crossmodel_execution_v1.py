"""Same-owner two-model integration. All HTTP, credentials and clocks are authored."""
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
from civiclab.e02.issue_cue_crossmodel_owner_v1 import CrossmodelOwnerV1,code_contract,LIMITS,PROTOCOL
from civiclab.e02 import issue_cue_crossmodel_client_v1 as client
from civiclab.e02 import alignment_anchoring_client_v1 as previous_client
from civiclab.e02.crossmodel_price_v1 import fresh_proof
from test_alignment_anchoring_execution_v1 import case as previous_case,Transport as PreviousTransport,boundaries as previous_boundaries
from test_crossmodel_price_metadata_v1 import qwen_release
from test_production_price_v4 import catalog,COMPONENTS,T0


def bind(q):
    p=q['policy'];p['code_contract_hash']=canonical_hash(code_contract())
    q['authority']={'kind':'CROSSMODEL_PILOT_AUTHORITY_V1','approval_id':uuid.uuid4().hex,
        'policy_hash':canonical_hash(p),'code_contract_hash':p['code_contract_hash']}
    q['review']={'kind':'INDEPENDENT_CROSSMODEL_STUDY_REVIEW_V1','reviewer_role':'independent_auditor',
        'review_id':uuid.uuid4().hex,'inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='review'})}
    return q


class PreviousWithMissingItems(PreviousTransport):
    def post_bytes(self,raw):
        result=super().post_bytes(raw)
        if self.posts in (3,4):
            answer=json.loads(result['choices'][0]['message']['content']);answer['democratic_party']=None
            result['choices'][0]['message']['content']=json.dumps(answer)
        return result


@contextmanager
def case():
    with previous_case() as (prior,b,proof,oldrows):
        transport=PreviousWithMissingItems()
        with previous_boundaries(prior,proof,transport):
            result=previous_client.execute_followup(b,expected_packet_hash=canonical_hash(b))
        assert result['status']=='COMPLETE' and transport.posts==22
        owner=CrossmodelOwnerV1()
        with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
        before=deepcopy(state);old=b['policy'];data_b,release_b,receipt_b=qwen_release()
        releases={'A':deepcopy(b['price_release']),'B':release_b}
        p={'kind':'CROSSMODEL_STUDY_POLICY_V1','owner_id':owner.header['owner_id'],
            'run_id':'AUTHORED_ISSUE_CUE_CROSSMODEL','valid_from_utc':old['valid_from_utc'],
            'valid_until_utc':old['valid_until_utc'],'limits':deepcopy(LIMITS),
            'protocol_sha256':sha256_file(PROTOCOL),'price_release_hash':canonical_hash(releases),
            'consent_evidence_hash':canonical_hash('AUTHORED_STANDING_AUTHORITY'),
            'predecessor':{'head':head,'history_hash':canonical_hash(state['_prefix_events']),
                'rows_hash':canonical_hash(state['rows']),'study_hash':canonical_hash(state['study']),
                'continuation_hash':canonical_hash(state['continuation']),
                'alignment_hash':canonical_hash(state['alignment_followup']),
                'claims_hash':canonical_hash(sorted(state['statistics_claims'])),'consumed':deepcopy(state['consumed'])}}
        q=bind({'kind':'CROSSMODEL_STUDY_PACKET_V1','policy':p,'price_release':releases})
        proof_b=fresh_proof(canonical_bytes(data_b),receipt_b,release_b['interpretation'],release_b['terms'],now=T0)
        yield owner,q,{'A':proof,'B':proof_b},before


class Transport:
    def __init__(self,mode='success'):self.posts=0;self.gets=0;self.mode=mode;self.models={};self.payloads=[]
    def post_bytes(self,raw):
        self.posts+=1;p=json.loads(raw);generation=f'gen-crossmodel-authored-{self.posts}'
        self.models[generation]=p['model'];self.payloads.append(p)
        return {'id':generation,'model':p['model'],
            'choices':[{'message':{'content':json.dumps({'democratic_party':None,
                'library_support':50,'visits_change':'NOT_REPORTED'})}}],
            'usage':{'cost':0.000001,'prompt_tokens':1,'completion_tokens':1}}
    def statistics(self,generation):
        self.gets+=1
        if self.mode=='404' or (self.mode=='delayed' and self.gets<=2):
            raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
        model=self.models[generation]
        return {'data':{'id':generation,'model':model,'provider_name':'Azure' if model.startswith('openai/') else 'Nebius',
            'is_byok':False,'total_cost':0.000001,'native_tokens_prompt':1,'native_tokens_completion':1,
            'native_tokens_reasoning':0,'service_tier':'default','streamed':False,'cancelled':False}}


@contextmanager
def boundaries(owner,proofs,transport):
    data=catalog();data['data']['id']='openai/gpt-4.1-nano'
    for i,e in enumerate(data['data']['endpoints']):
        e.update(model_id='openai/gpt-4.1-nano',provider_name='Azure',tag='azure' if i==0 else 'azure/authored')
        e['pricing']={k:'0' for k in COMPONENTS};e['pricing']['request']='0.000340'
    b,_,rb=qwen_release();catalogs={'A':data,'B':b}
    calls=[]
    def fetch(model):
        role='A' if model.startswith('openai/') else 'B';calls.append(role)
        return canonical_bytes(catalogs[role]),{k:proofs[role][k] for k in ('url','body_sha256','observed_at_utc')}
    mono=[0.0]
    with patch.object(client,'_owner',return_value=owner), \
         patch.object(client,'_fetch_public_catalog',side_effect=fetch), \
         patch.object(client,'_read_environment_key',return_value=_Credential('AUTHORED_KEY_NOT_REAL_123456789')), \
         patch.object(client,'_transport',return_value=transport), \
         patch.object(client.time,'monotonic',side_effect=lambda:mono[0]), \
         patch.object(client.time,'sleep',side_effect=lambda n:mono.__setitem__(0,mono[0]+n)):
        yield calls


class ExecutionTests(unittest.TestCase):
    def test_full_two_model_run_preserves_all_old_history_and_finite_caps(self):
        with case() as (owner,q,proofs,before):
            original=owner.snapshot()
            for change in ('ancestry','cap','model','clock'):
                bad=deepcopy(q)
                if change=='ancestry':bad['policy']['predecessor']['alignment_hash']='0'*64
                if change=='cap':bad['policy']['limits']['new_model_POSTs']=57
                if change=='model':bad['price_release']['B']['terms']['reported_provider']='Azure'
                if change=='clock':bad['policy']['valid_until_utc']=bad['policy']['valid_from_utc']
                bind(bad)
                with self.subTest(change=change),self.assertRaises((ExecutionBlocked,ValueError)):
                    owner.start_crossmodel(bad,proofs,expected_packet_hash=canonical_hash(bad))
                self.assertEqual(owner.snapshot(),original)
            t=Transport('delayed')
            with boundaries(owner,proofs,t) as calls:
                result=client.execute_crossmodel(q,expected_packet_hash=canonical_hash(q))
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual((t.posts,t.gets),(56,58))
            self.assertEqual(calls,['A','B','A','B']);self.assertEqual(result['catalog_GET_attempts'],4)
            self.assertEqual(len(result['response_envelope']['records']),56)
            self.assertEqual(result['analysis']['response_provenance'],'MOCK')
            for a,b in zip(t.payloads[::2],t.payloads[1::2]):
                self.assertNotEqual(a['model'],b['model']);self.assertEqual(a['seed'],b['seed'])
            with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
            self.assertEqual(state['consumed']['dispatches'],112);self.assertEqual(state['unfinished'],3)
            self.assertEqual(state['_prefix_events'][:len(before['_prefix_events'])],before['_prefix_events'])
            self.assertEqual({k:state['rows'][k] for k in before['rows']},before['rows'])
            for key in ('study','continuation','alignment_followup'):self.assertEqual(state[key],before[key])
            self.assertEqual(sum(r['charged'] for r in state['rows'].values()),state['consumed']['total'])
            with self.assertRaises(ExecutionBlocked):owner.start_crossmodel(q,proofs,expected_packet_hash=canonical_hash(q))
            with self.assertRaises(ExecutionBlocked):owner.refresh_prices(q,proofs,expected_packet_hash=canonical_hash(q))
            with self.assertRaises(ExecutionBlocked):owner.transition(next(iter(before['rows'])),'UNCERTAIN',error_type='AuthoredForeignRow')

    def test_exhausted_billing_retains_full_hold_and_prevents_another_dispatch(self):
        with case() as (owner,q,proofs,before):
            t=Transport('404')
            with boundaries(owner,proofs,t) as calls,self.assertRaises(_SafeExecutionFailure):
                client.execute_crossmodel(q,expected_packet_hash=canonical_hash(q))
            self.assertEqual((t.posts,t.gets),(1,3));self.assertEqual(calls,['A','B'])
            self.assertEqual(owner.study_snapshot()['status'],'STOPPED')
            self.assertEqual(owner.reserve_next(q,proofs,expected_packet_hash=canonical_hash(q),transport_ready=lambda c:True)['status'],'STOPPED')
            with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
            row=state['rows'][state['issue_cue_crossmodel']['receipts'][0]]
            self.assertEqual(row['charged'],row['reserved']);self.assertEqual(state['unfinished'],4)
            self.assertEqual({k:state['rows'][k] for k in before['rows']},before['rows'])

if __name__=='__main__':unittest.main()
