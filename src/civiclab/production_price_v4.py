"""Text price-contract mathematics; no consent, credentials or transport.

External interpretation/release hashes are trusted workflow inputs, not human or
provider authentication. Actual catalog observations alone are insufficient.
"""
from decimal import Decimal,Context,localcontext
from functools import wraps
import json
import re

from .common import canonical_bytes, canonical_hash, redact
from .model import ExecutionBlocked, call_envelope, micros
from .owner_budget_v3 import digest, freeze, utc
from .live_billing_v2 import integer

KIND = 'REVIEWED_TEXT_PRICE_CONTRACT_V4'
COMPONENTS = ('prompt','input_cache_read','input_cache_write','input_cache_write_1h',
              'completion','internal_reasoning','request')
NON_TEXT = {'audio','audio_output','image','image_output','image_token','input_audio_cache','web_search'}
REQUIRED_PARAMETERS = {'temperature','seed','max_completion_tokens','response_format','tool_choice'}
APPLICABILITY = {'text_only':True,'tools_plugins_disabled':True,'byok_disabled':True,
                 'non_reasoning_reviewed':True,'cache_bound_mode':'SUM_ALL_INPUT_COMPONENTS',
                 'non_text_fees_inapplicable_reviewed':True,
                 'conditional_overrides_absent_or_empty_reviewed':True,
                 'input_framing_bound_reviewed':True}


def financial_context(function):
    @wraps(function)
    def pinned(*args,**kwargs):
        with localcontext(Context(prec=80)):
            return function(*args,**kwargs)
    return pinned


def _identities(value):
    if type(value['model']) is not str or len(value['model'])>128 or not re.fullmatch(r'[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*',value['model']):
        raise ValueError('invalid model ID')
    if type(value['requested_route']) is not str or len(value['requested_route'])>128 or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*(?:/[a-z0-9][a-z0-9_-]*)*',value['requested_route']):
        raise ValueError('invalid route')
    if value['route_scope'] not in ('PROVIDER_FAMILY','ENDPOINT_PREFIX'):
        raise ValueError('explicit route scope required; no hardware identity claim')
    if value['route_scope']=='ENDPOINT_PREFIX' and '/' not in value['requested_route']:
        raise ValueError('base slug cannot claim a specific suffix')
    if value['route_scope']=='PROVIDER_FAMILY' and '/' in value['requested_route']:
        raise ValueError('suffixed route must declare a prefix scope')
    provider=value['reported_provider']
    if type(provider) is not str or not 1 <= len(provider) <= 128 or any(ord(c)<32 for c in provider):
        raise ValueError('invalid reported provider')


def decimal_price(value):
    if type(value) is not str or not 1 <= len(value) <= 64:
        raise ValueError('bounded decimal string required')
    d = Decimal(value)
    if not d.is_finite() or not 0 <= d <= 100 or not -18<=d.as_tuple().exponent<=18:
        raise ValueError('unsupported price domain')
    return d


def _json(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= 2_000_000:
        raise ValueError('bounded catalog bytes required')
    def pairs(values):
        out = {}
        for key,value in values:
            if key in out: raise ValueError('duplicate catalog key')
            out[key] = value
        return out
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite catalog')))
    canonical_bytes(value)
    return value


def _semantic(raw, decision):
    data = _json(raw)['data']
    if data['id'] != decision['model']: raise ExecutionBlocked('catalog model differs')
    selected = {}; route = decision['requested_route']
    for endpoint in data['endpoints']:
        tag = endpoint.get('tag')
        if type(tag) is not str or len(tag)>128 or not (tag == route or tag.startswith(route+'/')): continue
        if tag in selected or len(selected) >= 32: raise ValueError('duplicate/oversize route members')
        if (endpoint.get('provider_name') != decision['reported_provider']
            or endpoint.get('model_id') != decision['model'] or endpoint.get('service_tier') is not None
            or endpoint.get('native_tools') != {}):
            raise ExecutionBlocked('unsupported serving identity/tier')
        parameters = endpoint['supported_parameters']
        if (type(parameters) is not list or any(type(p) is not str for p in parameters)
            or not REQUIRED_PARAMETERS <= set(parameters)
            or endpoint.get('supports_tool_choice',{}).get('none') is not True):
            raise ExecutionBlocked('required request parameters not advertised')
        pricing = endpoint['pricing']
        if type(pricing) is not dict or set(pricing) - set(COMPONENTS) - NON_TEXT - {'discount','overrides'}:
            raise ExecutionBlocked('unreviewed price component')
        if pricing.get('overrides',[]) != []: raise ExecutionBlocked('conditional price overrides unsupported')
        if 'prompt' not in pricing or 'completion' not in pricing:
            raise ExecutionBlocked('native token prices absent')
        discount = pricing.get('discount',0)
        if type(discount) not in (int,float) or not 0 <= discount <= 1: raise ValueError('invalid discount')
        defaults = decision['missing_prices'].get(tag)
        missing = set(COMPONENTS) - set(pricing)
        if type(defaults) is not dict or set(defaults) != missing:
            raise ExecutionBlocked('missing prices need exact external interpretation')
        values = {k:format(decimal_price(pricing[k] if k in pricing else defaults[k]),'f') for k in COMPONENTS}
        other = {k:format(decimal_price(pricing[k]),'f') for k in NON_TEXT if k in pricing}
        selected[tag] = {'components':values,'non_text_disabled':other,
            'discount_observed':str(discount),
            'supported_parameters':sorted(set(parameters)),
            'implicit_caching':endpoint.get('supports_implicit_caching'),
            'quantization':endpoint.get('quantization'), 'provider_name':endpoint['provider_name']}
    if not selected or set(selected) != set(decision['missing_prices']):
        raise ExecutionBlocked('route membership differs from interpretation')
    return selected


def validate_decision(decision):
    keys = {'kind','model','requested_route','reported_provider','route_scope','catalog_sha256',
            'missing_prices','applicability','evidence_sha256','valid_from_utc','valid_until_utc'}
    if (type(decision) is not dict or set(decision) != keys
        or decision['kind'] != 'EXTERNAL_TEXT_PRICE_INTERPRETATION_V4'
        or canonical_hash(decision['applicability']) != canonical_hash(APPLICABILITY)):
        raise ExecutionBlocked('complete externally reviewed interpretation required')
    digest(decision['catalog_sha256'])
    _identities(decision)
    if utc(decision['valid_from_utc']) >= utc(decision['valid_until_utc']): raise ValueError('invalid contract interval')
    if type(decision['evidence_sha256']) is not list or not 1 <= len(decision['evidence_sha256']) <= 32:
        raise ExecutionBlocked('external interpretation evidence required')
    for h in decision['evidence_sha256']: digest(h)
    if type(decision['missing_prices']) is not dict: raise ValueError('explicit missing-component map required')


@financial_context
def contract_from_catalog(raw, decision, *, expected_decision_hash):
    """Admit supplied evidence only; does not authenticate its external reviewer."""
    import hashlib
    decision = freeze(decision); digest(expected_decision_hash)
    if canonical_hash(decision) != expected_decision_hash: raise ExecutionBlocked('interpretation hash changed')
    validate_decision(decision)
    if hashlib.sha256(raw).hexdigest() != decision['catalog_sha256']: raise ExecutionBlocked('catalog bytes changed')
    semantic = _semantic(raw, decision)
    components = {tag:entry['components'] for tag,entry in semantic.items()}
    input_bound = max(sum(decimal_price(values[k]) for k in COMPONENTS[:4]) for values in components.values())
    output_bound = max(sum(decimal_price(values[k]) for k in ('completion','internal_reasoning')) for values in components.values())
    request_bound = max(decimal_price(values['request']) for values in components.values())
    value = {'kind':KIND, **{k:decision[k] for k in ('model','requested_route','reported_provider','route_scope','valid_from_utc','valid_until_utc')},
        'interpretation_hash':expected_decision_hash,'initial_catalog_sha256':decision['catalog_sha256'],
        'metadata_semantic_hash':canonical_hash(semantic),'components_by_tag':components,
        'input_usd_per_token':format(input_bound,'f'),'output_usd_per_token':format(output_bound,'f'),
        'request_fee_usd':format(request_bound,'f'),'output_parameter':'max_completion_tokens'}
    validate_terms(value)
    return freeze(value)


@financial_context
def validate_terms(terms):
    keys = {'kind','model','requested_route','reported_provider','route_scope','valid_from_utc','valid_until_utc',
        'interpretation_hash','initial_catalog_sha256','metadata_semantic_hash','components_by_tag',
        'input_usd_per_token','output_usd_per_token','request_fee_usd','output_parameter'}
    if type(terms) is not dict or set(terms) != keys or terms['kind'] != KIND or terms['output_parameter'] != 'max_completion_tokens':
        raise ExecutionBlocked('complete v4 text contract required')
    _identities(terms)
    for k in ('interpretation_hash','initial_catalog_sha256','metadata_semantic_hash'):digest(terms[k])
    if utc(terms['valid_from_utc']) >= utc(terms['valid_until_utc']):raise ValueError('invalid contract time')
    entries=terms['components_by_tag']
    if type(entries) is not dict or not 1 <= len(entries) <= 32:raise ValueError('bounded component table required')
    for tag,values in entries.items():
        if (type(tag) is not str or not(tag==terms['requested_route'] or tag.startswith(terms['requested_route']+'/'))
            or type(values) is not dict or set(values)!=set(COMPONENTS)):raise ValueError('component table shape')
        for v in values.values():decimal_price(v)
    expected = {'input_usd_per_token':max(sum(decimal_price(v[k]) for k in COMPONENTS[:4]) for v in entries.values()),
        'output_usd_per_token':max(sum(decimal_price(v[k]) for k in ('completion','internal_reasoning')) for v in entries.values()),
        'request_fee_usd':max(decimal_price(v['request']) for v in entries.values())}
    for k,v in expected.items():
        if decimal_price(terms[k]) != v:raise ValueError('contract bound differs from all component sums')
    if redact(terms) != terms:raise ValueError('credential-like contract refused')


def fresh_proof(raw, receipt, decision, terms, *, now):
    """New-dispatch check; never required to read an expired historical charge."""
    import hashlib
    receipt,decision,terms=freeze(receipt),freeze(decision),freeze(terms)
    validate_terms(terms);validate_decision(decision)
    if canonical_hash(decision)!=terms['interpretation_hash']:raise ExecutionBlocked('interpretation differs')
    if type(receipt) is not dict or set(receipt)!={'url','body_sha256','observed_at_utc'}:raise ValueError('receipt shape')
    expected_url='https://openrouter.ai/api/v1/models/'+terms['model']+'/endpoints'
    if receipt['url']!=expected_url or hashlib.sha256(raw).hexdigest()!=receipt['body_sha256']:
        raise ExecutionBlocked('catalog receipt differs')
    semantic=_semantic(raw,decision)
    if (canonical_hash(semantic)!=terms['metadata_semantic_hash']
        or canonical_hash({tag:v['components'] for tag,v in semantic.items()})!=canonical_hash(terms['components_by_tag'])):
        raise ExecutionBlocked('catalog semantic contract changed')
    observed=utc(receipt['observed_at_utc'])
    if not utc(terms['valid_from_utc'])<=now<utc(terms['valid_until_utc']) or not 0 <= (now-observed).total_seconds() <= 900:
        raise ExecutionBlocked('new dispatch price evidence not current')
    return {**receipt,'metadata_semantic_hash':terms['metadata_semantic_hash']}


@financial_context
def quote(messages,max_tokens,terms):
    terms=freeze(terms);validate_terms(terms)
    if redact(messages)!=messages:raise ValueError('credential-like messages refused')
    env={**call_envelope(freeze(messages),max_tokens),'message_count':len(messages)}
    amount=(Decimal(env['input_token_bound'])*decimal_price(terms['input_usd_per_token'])
            +Decimal(max_tokens)*decimal_price(terms['output_usd_per_token'])+decimal_price(terms['request_fee_usd']))
    return {**env,'reserved_microusd':integer(micros(amount),1)}
