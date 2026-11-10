"""Explicit OpenRouter parameter-alias admission for the fixed Qwen comparator.

Raw catalog bytes and their hashes remain untouched. This version interprets
the advertised legacy max_tokens capability as the documented successor
max_completion_tokens for exactly one model/route. It never modifies v4 code,
prices, native response metadata, or the wire request's output-token limit.
"""
import hashlib

from ..common import canonical_bytes, canonical_hash
from ..model import ExecutionBlocked
from ..owner_budget_v3 import freeze, utc
from .. import production_price_v4 as old

MODEL = 'qwen/qwen3-30b-a3b-instruct-2507'
ROUTE = 'nebius/fp8'


def semantic(raw, decision):
    if decision['model'] != MODEL:
        return old._semantic(raw, decision)
    if (decision['requested_route'] != ROUTE or decision['reported_provider'] != 'Nebius'
            or decision['route_scope'] != 'ENDPOINT_PREFIX'):
        raise ExecutionBlocked('fixed comparator route required')
    value = old._json(raw)
    observed = {}
    for endpoint in value['data']['endpoints']:
        tag = endpoint.get('tag')
        if type(tag) is not str or not (tag == ROUTE or tag.startswith(ROUTE + '/')):
            continue
        params = endpoint.get('supported_parameters')
        if (type(params) is not list or any(type(p) is not str for p in params)
                or 'max_tokens' not in params or 'max_completion_tokens' in params):
            raise ExecutionBlocked('reviewed exact legacy parameter observation changed')
        observed[tag] = sorted(set(params))
        endpoint['supported_parameters'] = params + ['max_completion_tokens']
    checked = old._semantic(canonical_bytes(value), decision)
    for tag, entry in checked.items():
        entry['observed_supported_parameters'] = observed[tag]
        entry['parameter_interpretation'] = 'OPENROUTER_DOCUMENTED_MAX_TOKENS_SUCCESSOR'
    return checked


@old.financial_context
def contract_from_catalog(raw, decision, *, expected_decision_hash):
    decision = freeze(decision)
    old.validate_decision(decision)
    if (canonical_hash(decision) != expected_decision_hash
            or hashlib.sha256(raw).hexdigest() != decision['catalog_sha256']):
        raise ExecutionBlocked('exact reviewed raw price evidence required')
    values = semantic(raw, decision)
    components = {tag: entry['components'] for tag, entry in values.items()}
    p = old.decimal_price
    result = {
        'kind': old.KIND,
        **{k: decision[k] for k in ('model', 'requested_route', 'reported_provider',
                                  'route_scope', 'valid_from_utc', 'valid_until_utc')},
        'interpretation_hash': expected_decision_hash,
        'initial_catalog_sha256': decision['catalog_sha256'],
        'metadata_semantic_hash': canonical_hash(values),
        'components_by_tag': components,
        'input_usd_per_token': format(max(sum(p(v[k]) for k in old.COMPONENTS[:4])
                                         for v in components.values()), 'f'),
        'output_usd_per_token': format(max(p(v['completion']) + p(v['internal_reasoning'])
                                          for v in components.values()), 'f'),
        'request_fee_usd': format(max(p(v['request']) for v in components.values()), 'f'),
        'output_parameter': 'max_completion_tokens',
    }
    old.validate_terms(result)
    return freeze(result)


def fresh_proof(raw, receipt, decision, terms, *, now):
    receipt, decision, terms = freeze(receipt), freeze(decision), freeze(terms)
    old.validate_terms(terms)
    old.validate_decision(decision)
    if canonical_hash(decision) != terms['interpretation_hash']:
        raise ExecutionBlocked('price interpretation differs')
    if type(receipt) is not dict or set(receipt) != {'url', 'body_sha256', 'observed_at_utc'}:
        raise ExecutionBlocked('bounded raw metadata receipt required')
    if (receipt['url'] != 'https://openrouter.ai/api/v1/models/' + terms['model'] + '/endpoints'
            or hashlib.sha256(raw).hexdigest() != receipt['body_sha256']):
        raise ExecutionBlocked('raw catalog receipt differs')
    values = semantic(raw, decision)
    if (canonical_hash(values) != terms['metadata_semantic_hash']
            or canonical_hash({k: v['components'] for k, v in values.items()})
            != canonical_hash(terms['components_by_tag'])):
        raise ExecutionBlocked('catalog prices, route or capabilities changed')
    if (not utc(terms['valid_from_utc']) <= now < utc(terms['valid_until_utc'])
            or not 0 <= (now - utc(receipt['observed_at_utc'])).total_seconds() <= 900):
        raise ExecutionBlocked('new dispatch price evidence not current')
    return {**receipt, 'metadata_semantic_hash': terms['metadata_semantic_hash']}
