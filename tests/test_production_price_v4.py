"""Authored price contracts; no genuine review, endpoint or network authority."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from decimal import Decimal,ROUND_CEILING
import hashlib,json,unittest

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_price_v4 import (COMPONENTS,APPLICABILITY,REQUIRED_PARAMETERS,
    contract_from_catalog,fresh_proof,quote,validate_terms)

T0=datetime(2026,11,3,12,tzinfo=timezone.utc)


def catalog():
    values={k:'0' for k in COMPONENTS};values.update(prompt='0.0000001',completion='0.0000004',input_cache_read='0.00000002',input_cache_write='0.00000003',request='0.0000001')
    def member(tag,prices):
        return {'tag':tag,'model_id':'fixture/model-v4','provider_name':'FixtureProvider',
            'service_tier':None,'supported_parameters':sorted(REQUIRED_PARAMETERS),
            'supports_tool_choice':{'none':True},'native_tools':{},'supports_implicit_caching':True,
            'quantization':'AUTHORED','pricing':prices,'latency_last_30m':0.5}
    west={k:'0' for k in COMPONENTS};west.update(prompt='0.0000002',completion='0.0000003',input_cache_read='0.00000001')
    return {'data':{'id':'fixture/model-v4','endpoints':[member('fixture',values),member('fixture/west',west)]}}


def decision_for(data):
    raw=canonical_bytes(data)
    return {'kind':'EXTERNAL_TEXT_PRICE_INTERPRETATION_V4','model':'fixture/model-v4',
        'requested_route':'fixture','reported_provider':'FixtureProvider','route_scope':'PROVIDER_FAMILY',
        'catalog_sha256':hashlib.sha256(raw).hexdigest(),
        'missing_prices':{e['tag']:{k:'0' for k in COMPONENTS if k not in e['pricing']} for e in data['data']['endpoints']},
        'applicability':deepcopy(APPLICABILITY),'evidence_sha256':[canonical_hash('AUTHORED_NOT_EXTERNAL_EVIDENCE')],
        'valid_from_utc':(T0-timedelta(minutes=1)).isoformat(),'valid_until_utc':(T0+timedelta(days=1)).isoformat()}


def fixture_contract():
    data=catalog();decision=decision_for(data);raw=canonical_bytes(data)
    terms=contract_from_catalog(raw,decision,expected_decision_hash=canonical_hash(decision))
    receipt={'url':'https://openrouter.ai/api/v1/models/fixture/model-v4/endpoints',
        'body_sha256':hashlib.sha256(raw).hexdigest(),'observed_at_utc':T0.isoformat()}
    return raw,decision,terms,receipt


class ProductionPriceTests(unittest.TestCase):
    def test_conservative_component_maxima_and_fractional_per_request_rounding(self):
        raw,decision,terms,receipt=fixture_contract()
        self.assertEqual(Decimal(terms['input_usd_per_token']),Decimal('0.00000021'))
        self.assertEqual(Decimal(terms['output_usd_per_token']),Decimal('0.0000004'))
        self.assertEqual(Decimal(terms['request_fee_usd']),Decimal('0.0000001'))
        env=quote([{'role':'user','content':'AUTHORED PRICE MATH'}],32,terms)
        expected=Decimal(env['input_token_bound'])*Decimal('0.00000021')+32*Decimal('0.0000004')+Decimal('0.0000001')
        self.assertEqual(env['reserved_microusd'],int((expected*1000000).to_integral_value(rounding=ROUND_CEILING)))
        data=catalog()
        for e in data['data']['endpoints']:
            e['pricing']={k:'0' for k in COMPONENTS};e['pricing']['request']='0.0000001'
        d=decision_for(data);t=contract_from_catalog(canonical_bytes(data),d,expected_decision_hash=canonical_hash(d))
        a=quote([{'role':'user','content':'A'}],1,t);b=quote([{'role':'user','content':'B'}],1,t)
        self.assertEqual(a['reserved_microusd']+b['reserved_microusd'],2)
        self.assertEqual(int((Decimal('0.0000002')*1000000).to_integral_value(rounding=ROUND_CEILING)),1)

    def test_missing_fee_has_no_automatic_zero_and_requires_external_binding(self):
        data=catalog();del data['data']['endpoints'][0]['pricing']['request'];d=decision_for(data)
        d['missing_prices']['fixture']={}
        with self.assertRaises(ExecutionBlocked):contract_from_catalog(canonical_bytes(data),d,expected_decision_hash=canonical_hash(d))
        d['missing_prices']['fixture']={'request':'0'}
        terms=contract_from_catalog(canonical_bytes(data),d,expected_decision_hash=canonical_hash(d))
        self.assertEqual(terms['request_fee_usd'],'0')
        with self.assertRaises(ExecutionBlocked):contract_from_catalog(canonical_bytes(data),d,expected_decision_hash='0'*64)
        d['applicability']['tools_plugins_disabled']=False
        with self.assertRaises(ExecutionBlocked):contract_from_catalog(canonical_bytes(data),d,expected_decision_hash=canonical_hash(d))

    def test_unsupported_fees_tiers_overrides_tools_and_parameters_refuse(self):
        changes=[lambda e:e['pricing'].__setitem__('unknown_fee','1'),
            lambda e:e['pricing'].__setitem__('overrides',[{'request':'1'}]),
            lambda e:e.__setitem__('service_tier','priority'),
            lambda e:e.__setitem__('native_tools',{'web_search':True}),
            lambda e:e.__setitem__('supported_parameters',[]),
            lambda e:e['supports_tool_choice'].__setitem__('none',False),
            lambda e:e['pricing'].__setitem__('prompt',float('inf')),
            lambda e:e['pricing'].__setitem__('completion','NaN')]
        for change in changes:
            with self.subTest(change=change):
                data=catalog();change(data['data']['endpoints'][0])
                try:d=decision_for(data)
                except ValueError:continue
                with self.assertRaises((ValueError,ExecutionBlocked)):
                    contract_from_catalog(canonical_bytes(data),d,expected_decision_hash=canonical_hash(d))

    def test_freshness_for_dispatch_does_not_invalidate_historical_math(self):
        raw,d,t,r=fixture_contract()
        self.assertEqual(fresh_proof(raw,r,d,t,now=T0)['metadata_semantic_hash'],t['metadata_semantic_hash'])
        for now in (T0-timedelta(seconds=1),T0+timedelta(seconds=901),T0+timedelta(days=2)):
            with self.assertRaises(ExecutionBlocked):fresh_proof(raw,r,d,t,now=now)
        validate_terms(t)
        self.assertGreater(quote([{'role':'user','content':'Historical quote still readable'}],32,t)['reserved_microusd'],0)

    def test_refresh_may_change_telemetry_but_not_semantics_or_proof(self):
        raw,d,t,r=fixture_contract();data=json.loads(raw)
        data['data']['endpoints'][0]['latency_last_30m']=9.9;new=canonical_bytes(data)
        r['body_sha256']=hashlib.sha256(new).hexdigest()
        fresh_proof(new,r,d,t,now=T0)
        data['data']['endpoints'][0]['pricing']['prompt']='0.000001'
        new=canonical_bytes(data);r['body_sha256']=hashlib.sha256(new).hexdigest()
        with self.assertRaises(ExecutionBlocked):fresh_proof(new,r,d,t,now=T0)
        r['url']='https://example.invalid/catalog'
        with self.assertRaises(ExecutionBlocked):fresh_proof(raw,r,d,t,now=T0)

    def test_snapshot_and_caller_alias_changes_cannot_change_contract(self):
        data=catalog();d=decision_for(data);expected=canonical_hash(d);raw=canonical_bytes(data)
        terms=contract_from_catalog(raw,d,expected_decision_hash=expected)
        d['missing_prices']['fixture']['request']='1';data['data']['endpoints'][0]['pricing']['prompt']='1'
        self.assertEqual(terms['request_fee_usd'],'0.0000001')
        with self.assertRaises(ExecutionBlocked):contract_from_catalog(canonical_bytes(data),d,expected_decision_hash=expected)
        terms['components_by_tag']['fixture']['prompt']='1'
        with self.assertRaises(ValueError):validate_terms(terms)

    def test_route_scope_membership_and_strict_json_identity(self):
        raw,d,t,r=fixture_contract();d['route_scope']='ENDPOINT_PREFIX'
        with self.assertRaises(ValueError):contract_from_catalog(raw,d,expected_decision_hash=canonical_hash(d))
        data=catalog();data['data']['endpoints'].append(deepcopy(data['data']['endpoints'][0]));d=decision_for(data)
        with self.assertRaises(ValueError):contract_from_catalog(canonical_bytes(data),d,expected_decision_hash=canonical_hash(d))
        d=decision_for(catalog());bad=b'{"data":{},"data":{}}';d['catalog_sha256']=hashlib.sha256(bad).hexdigest()
        with self.assertRaises(ValueError):contract_from_catalog(bad,d,expected_decision_hash=canonical_hash(d))

    def test_financial_math_is_independent_of_mutable_caller_decimal_context(self):
        from decimal import localcontext,Context
        from fractions import Fraction
        from civiclab.production_admission_v4 import compile_compatibility_release
        raw,d,terms,receipt=fixture_contract()
        baseline=compile_compatibility_release(terms,d,run_id='AUTHORED-DECIMAL-CONTEXT')
        expected_env=quote([{'role':'user','content':'CONTEXT INDEPENDENCE'}],37,terms)
        amount=(Fraction(terms['input_usd_per_token'])*expected_env['input_token_bound']
                +Fraction(terms['output_usd_per_token'])*37+Fraction(terms['request_fee_usd']))*1000000
        self.assertEqual(expected_env['reserved_microusd'],(amount.numerator+amount.denominator-1)//amount.denominator)
        with localcontext(Context(prec=2)):
            rebuilt=contract_from_catalog(raw,d,expected_decision_hash=canonical_hash(d))
            self.assertEqual(rebuilt,terms)
            self.assertEqual(quote([{'role':'user','content':'CONTEXT INDEPENDENCE'}],37,terms),expected_env)
            self.assertEqual(compile_compatibility_release(terms,d,run_id='AUTHORED-DECIMAL-CONTEXT'),baseline)
