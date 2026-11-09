"""Real append-only owner and client together; fake clock/key/HTTP only."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.production_admission_v4 import _Credential
from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
from civiclab.e02 import exploratory_continuation_v1 as client
from test_e02_continuation_owner_v1 import continuation_case
from test_production_price_v4 import catalog,T0,COMPONENTS


class Transport:
    def __init__(self,delayed=True):self.posts=0;self.gets=0;self.delayed=delayed
    def post_bytes(self,raw):
        self.posts+=1;p=json.loads(raw)
        return {'id':f'gen-continuation-integration-{self.posts}','model':p['model'],
            'choices':[{'message':{'content':'{"democratic_party":50,"republican_party":50}'}}],
            'usage':{'cost':0.000001,'prompt_tokens':1,'completion_tokens':1}}
    def statistics(self,generation):
        self.gets+=1
        if self.delayed and self.gets<=2:raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
        return {'data':{'id':generation,'model':'openai/gpt-4.1-nano-2025-04-14',
            'provider_name':'Azure','is_byok':False,'total_cost':0.000001,'native_tokens_prompt':1,
            'native_tokens_completion':1,'native_tokens_reasoning':0,'service_tier':'default',
            'streamed':True,'cancelled':False}}


class IntegrationTests(unittest.TestCase):
    def test_real_owner_client_finish_only_remaining_slots_with_delayed_metadata(self):
        with continuation_case() as (owner,b,proof,oldrows):
            data=catalog();data['data']['id']='openai/gpt-4.1-nano'
            for i,e in enumerate(data['data']['endpoints']):
                e.update(model_id='openai/gpt-4.1-nano',provider_name='Azure',
                    tag='azure' if i==0 else 'azure/authored')
                e['pricing']={k:'0' for k in COMPONENTS};e['pricing']['request']='0.000340'
            raw=canonical_bytes(data)
            metadata={k:proof[k] for k in ('url','body_sha256','observed_at_utc')}
            self.assertEqual(canonical_hash(data),metadata['body_sha256'])
            t=Transport();mono=[0.0]
            with patch.object(client,'_owner',return_value=owner), \
                 patch.object(client,'_fetch_public_catalog',return_value=(raw,metadata)), \
                 patch.object(client,'_read_environment_key',return_value=_Credential('AUTHORED_KEY_NOT_REAL_123456789')), \
                 patch.object(client,'_transport',return_value=t), \
                 patch.object(client.time,'monotonic',side_effect=lambda:mono[0]), \
                 patch.object(client.time,'sleep',side_effect=lambda n:mono.__setitem__(0,mono[0]+n)):
                result=client.execute_continuation(b,expected_bundle_hash=canonical_hash(b))
            self.assertEqual(result['status'],'COMPLETE')
            self.assertEqual((t.posts,t.gets),(16,18))
            self.assertEqual(result['snapshot']['study_dispatches'],32)
            self.assertEqual(len(result['response_envelope']['records']),32)
            self.assertEqual(result['analysis']['response_provenance'],'MOCK')
            with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
            self.assertEqual(state['unfinished'],3)
            self.assertEqual(state['consumed']['dispatches'],34)
            self.assertEqual({k:state['rows'][k] for k in oldrows},oldrows)
            self.assertEqual(len(state['study']['witnesses']),32)
            self.assertEqual(sum(r['charged'] for r in state['rows'].values()),state['consumed']['total'])


if __name__=='__main__':unittest.main()
