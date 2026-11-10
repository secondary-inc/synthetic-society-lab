"""Finite provider-alias and identity tests; no external calls or credentials."""
from copy import deepcopy
from datetime import timedelta
import unittest

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.e02 import crossmodel_price_v1 as p
from civiclab.e02 import crossmodel_metadata_v1 as m
from civiclab.model import ExecutionBlocked
from civiclab.production_price_v4 import APPLICABILITY,COMPONENTS
from test_production_price_v4 import T0,catalog


def qwen_release():
    data=catalog();data['data']['id']=p.MODEL
    e=data['data']['endpoints'][0];data['data']['endpoints']=[e]
    e.update(model_id=p.MODEL,provider_name='Nebius',tag=p.ROUTE)
    e['supported_parameters']=[v for v in e['supported_parameters'] if v!='max_completion_tokens']+['max_tokens']
    e['pricing']={k:'0' for k in COMPONENTS};e['pricing']['request']='0.000340'
    raw=canonical_bytes(data)
    d={'kind':'EXTERNAL_TEXT_PRICE_INTERPRETATION_V4','model':p.MODEL,'requested_route':p.ROUTE,
        'reported_provider':'Nebius','route_scope':'ENDPOINT_PREFIX','catalog_sha256':canonical_hash(data),
        'missing_prices':{p.ROUTE:{}},'applicability':deepcopy(APPLICABILITY),
        'evidence_sha256':['a'*64],'valid_from_utc':(T0-timedelta(minutes=1)).isoformat(),
        'valid_until_utc':(T0+timedelta(hours=2)).isoformat()}
    terms=p.contract_from_catalog(raw,d,expected_decision_hash=canonical_hash(d))
    receipt={'url':'https://openrouter.ai/api/v1/models/'+p.MODEL+'/endpoints',
        'body_sha256':canonical_hash(data),'observed_at_utc':T0.isoformat()}
    return data,{'kind':'LIMITED_PILOT_PRICE_RELEASE_V1','terms':terms,'interpretation':d},receipt


class PriceTests(unittest.TestCase):
    def test_legacy_capability_is_explicit_and_raw_unchanged(self):
        data,release,r=qwen_release();raw=canonical_bytes(data)
        proof=p.fresh_proof(raw,r,release['interpretation'],release['terms'],now=T0)
        self.assertEqual(proof['body_sha256'],canonical_hash(data))
        self.assertNotIn('max_completion_tokens',data['data']['endpoints'][0]['supported_parameters'])
        sem=p.semantic(raw,release['interpretation'])[p.ROUTE]
        self.assertIn('max_completion_tokens',sem['supported_parameters'])
        self.assertNotIn('max_completion_tokens',sem['observed_supported_parameters'])
        self.assertEqual(release['terms']['output_parameter'],'max_completion_tokens')

    def test_changed_required_capability_price_route_or_unknown_fee_rejected(self):
        for change in ('seed','none','price','route','fee','canonical_already','wrong_raw'):
            data,release,r=qwen_release();e=data['data']['endpoints'][0]
            if change=='seed':e['supported_parameters'].remove('seed')
            if change=='none':e['supports_tool_choice']['none']=False
            if change=='price':e['pricing']['prompt']='0.000001'
            if change=='route':e['tag']='nebius/another'
            if change=='fee':e['pricing']['unreviewed_fee']='0'
            if change=='canonical_already':e['supported_parameters'].append('max_completion_tokens')
            raw=canonical_bytes(data)
            if change!='wrong_raw':r['body_sha256']=canonical_hash(data)
            else:r['body_sha256']='0'*64
            with self.subTest(change=change),self.assertRaises((ValueError,ExecutionBlocked)):
                p.fresh_proof(raw,r,release['interpretation'],release['terms'],now=T0)

    def test_expired_future_proofs_and_wrong_interpretation_rejected(self):
        data,release,r=qwen_release()
        for now in (T0-timedelta(seconds=1),T0+timedelta(seconds=901)):
            with self.assertRaises(ExecutionBlocked):p.fresh_proof(canonical_bytes(data),r,release['interpretation'],release['terms'],now=now)
        release['interpretation']['reported_provider']='Other'
        with self.assertRaises(ExecutionBlocked):p.fresh_proof(canonical_bytes(data),r,release['interpretation'],release['terms'],now=T0)


class MetadataTests(unittest.TestCase):
    def test_exact_family_identity_billing_and_unknown_auxiliary_counters(self):
        stats={'id':'gen-authored-qwen','model':p.MODEL,'provider_name':'Nebius','total_cost':0.000001,
            'native_tokens_prompt':3,'native_tokens_completion':2,'native_tokens_reasoning':0,
            'is_byok':False,'service_tier':'default','streamed':False,'cancelled':False}
        kwargs=dict(generation_id=stats['id'],requested_model=p.MODEL,reported_provider='Nebius',input_bound=8192,output_bound=256,reserved_microusd=1785)
        result=m.normalize_statistics(stats,**kwargs)
        self.assertEqual(result['billing']['model'],p.MODEL)
        self.assertEqual(result['telemetry']['optional_counters']['num_fetches']['status'],'NOT_REPORTED_UNKNOWN')
        for key,value in [('model',p.MODEL+'-unknown'),('provider_name','Azure'),('is_byok',True),('native_tokens_reasoning',1),('native_tokens_reasoning',None),('total_cost',0.002),('native_tokens_completion',257),('service_tier',None),('num_fetches',1)]:
            with self.subTest(key=key,value=value),self.assertRaises((ValueError,ExecutionBlocked)):
                m.normalize_statistics({**stats,key:value},**kwargs)
        self.assertFalse(m.response_model_allowed('anything',p.MODEL))
        self.assertTrue(m.response_model_allowed(m.DATED_MODEL,m.BASE_MODEL))

if __name__=='__main__':unittest.main()
