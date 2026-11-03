"""Mocked POST + generation-stat reconciliation over the global v2 ledger.

No credentials, network opener or real transport are implemented by this module.
Provider reply text is distinct from authoritative billing/serving metadata.
"""
from copy import deepcopy
from decimal import Decimal
import json
import re
import uuid

from .common import canonical_bytes, canonical_hash, redact
from .live_billing_v2 import GlobalFixtureLedger, quote
from .model import ExecutionBlocked, micros


def fixture_terms():
    return {'model': 'fixture/model-v2', 'requested_route': 'fixture-route',
            'reported_provider': 'Fixture Serving Name', 'input_usd_per_token': '0.000001',
            'output_usd_per_token': '0.000001', 'request_fee_usd': '0',
            'pricing_scope': 'AUTHORED_FIXTURE_NOT_PRICE_EVIDENCE'}


class FixtureHTTP:
    """Authored envelopes without a chat-level provider field, as in the schema."""
    def __init__(self, terms=None, *, content=None, overrides=None):
        self.terms = deepcopy(terms or fixture_terms()); self.content = content
        self.overrides = deepcopy(overrides or {}); self.calls = []; self.responses = {}

    def post(self, payload):
        self.calls.append(('POST', payload['model']))
        identity = 'gen-' + uuid.uuid4().hex
        content = self.content if self.content is not None else json.dumps({'democratic_party': 60, 'republican_party': 40})
        exact_cost = Decimal(self.terms['input_usd_per_token']) + Decimal(self.terms['output_usd_per_token']) + Decimal(self.terms['request_fee_usd'])
        cost = float(exact_cost)
        if Decimal(str(cost)) != exact_cost: raise ValueError('fixture billing cannot be represented by the JSON-number oracle')
        result = {'id': identity, 'model': payload['model'], 'created': 0, 'object': 'chat.completion', 'system_fingerprint': None,
                  'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': content}}],
                  'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2, 'cost': cost}}
        result.update(self.overrides.get('response', {}))
        self.responses[identity] = cost
        return result

    def stats(self, identity):
        self.calls.append(('GET_STATS', identity))
        result = {'id': identity, 'model': self.terms['model'],
                  'provider_name': self.terms['reported_provider'], 'total_cost': self.responses[identity],
                  'native_tokens_prompt': 1, 'native_tokens_completion': 1,
                  'native_tokens_reasoning': 0, 'is_byok': False}
        result.update(self.overrides.get('stats', {}))
        return {'data': result}


def visible_answer(response):
    """Retain redacted user-visible text only; never private reasoning fields."""
    choices = response.get('choices')
    message = choices[0].get('message') if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
    text = message.get('content') if isinstance(message, dict) else None
    if text is None: return {'status': 'MISSING_OR_REFUSAL', 'parsed': None, 'raw_text': None}
    if not isinstance(text, str): return {'status': 'INVALID_CONTENT_TYPE', 'parsed': None, 'raw_text': None}
    text = redact(text)
    try: parsed = json.loads(text)
    except ValueError: return {'status': 'INVALID_JSON', 'parsed': None, 'raw_text': text}
    # Reject nonfinite nonstandard JSON before persistence; invalid answers are
    # answer-quality events, not automatic financial uncertainties or retries.
    try: canonical_bytes(parsed)
    except (ValueError, TypeError): return {'status': 'INVALID_JSON_DOMAIN', 'parsed': None, 'raw_text': text}
    return {'status': 'PARSED_OBJECT' if isinstance(parsed, dict) else 'NON_OBJECT_JSON',
            'parsed': parsed, 'raw_text': text}


class ReconciledFixtureClient:
    def __init__(self, ledger, terms, transport):
        if type(ledger) is not GlobalFixtureLedger or type(transport) is not FixtureHTTP:
            raise ExecutionBlocked('only the authored global-ledger/mock transport candidate is released')
        self.ledger = ledger; self.terms = deepcopy(terms); self.transport = transport
        # Validate the complete pricing shape without dispatching or reserving.
        quote([{'role': 'user', 'content': 'validation only'}], 1, self.terms)

    def complete(self, messages, *, run_id, unit_id, phase, module='E02', max_tokens=512, seed=0):
        if type(seed) is not int or not 0 <= seed < 2**32: raise ValueError('bounded integer seed required')
        messages = deepcopy(messages); terms = deepcopy(self.terms)
        envelope = quote(messages, max_tokens, terms)
        prices = {k: Decimal(terms[v]) * (1_000_000 if k != 'request' else 1)
                  for k, v in (('prompt', 'input_usd_per_token'), ('completion', 'output_usd_per_token'), ('request', 'request_fee_usd'))}
        if any(Decimal(str(float(v))) != v for v in prices.values()):
            raise ValueError('price ceiling cannot be serialized without decimal drift')
        payload = {'model': terms['model'], 'messages': messages, 'stream': False,
                   'seed': seed, 'temperature': 0, 'max_tokens': max_tokens,
                   'response_format': {'type': 'json_object'}, 'plugins': [],
                   'provider': {'only': [terms['requested_route']], 'allow_fallbacks': False,
                                'require_parameters': True, 'max_price': {k: float(v) for k, v in prices.items()}}}
        context = {'run_id': run_id, 'unit_id': unit_id, 'phase': phase, 'module': module,
                   'terms': terms, 'envelope': envelope, 'payload_hash': canonical_hash(payload),
                   'sampling': {'seed': seed, 'temperature': 0, 'retries': 0}}
        receipt = self.ledger.reserve(context)
        known_cost = None; generation_id = None
        try:
            response = self.transport.post(payload)
            if not isinstance(response, dict) or len(canonical_bytes(response)) > 2_000_000:
                raise ValueError('invalid or oversized inference envelope')
            usage = response.get('usage')
            if isinstance(usage, dict) and usage.get('cost') is not None: known_cost = micros(usage['cost'])
            identity = response.get('id')
            valid_identity = isinstance(identity, str) and len(identity) <= 128 and re.fullmatch(r'gen-[0-9A-Za-z-]+', identity)
            if not valid_identity or response.get('model') != terms['model']:
                raise ValueError('generation/model identity unverified')
            if any(r['id'] != receipt and r['generation_id'] == identity for r in self.ledger.snapshot()):
                raise ExecutionBlocked('generation identity already bound to another phase; no statistics lookup')
            generation_id = identity
            answer = visible_answer(response)
            self.ledger.transition(receipt, 'RESPONSE_SEEN', generation_id=generation_id,
                                   output_hash=canonical_hash(answer), observed_cost=known_cost)
            if known_cost is not None and known_cost > envelope['reserved_microusd']:
                self.ledger.transition(receipt, 'OVERRUN', observed_cost=known_cost)
                raise ExecutionBlocked('reported inference charge exceeds reservation')
            # Exactly one lookup for the same safe identifier. Failure does not
            # dispatch another POST, fetch content, or release the reservation.
            stats_response = self.transport.stats(generation_id)
            if not isinstance(stats_response, dict) or len(canonical_bytes(stats_response)) > 2_000_000:
                raise ValueError('invalid or oversized generation envelope')
            stats = stats_response.get('data')
            if not isinstance(stats, dict): raise ValueError('generation metadata unavailable')
            if stats.get('id') != generation_id: raise ValueError('generation billing belongs to a different response')
            if 'total_cost' in stats: known_cost = max(known_cost or 0, micros(stats['total_cost']))
            if (stats.get('id') != generation_id or stats.get('model') != terms['model']
                or stats.get('provider_name') != terms['reported_provider'] or stats.get('is_byok') is not False):
                raise ValueError('actual serving identity or billing mode unverified')
            for field, bound in (('native_tokens_prompt', envelope['input_token_bound']),
                                 ('native_tokens_completion', max_tokens), ('native_tokens_reasoning', 0)):
                if type(stats.get(field)) is not int or not 0 <= stats[field] <= bound:
                    raise ValueError('native token accounting outside approved fixture envelope')
            amount = micros(stats['total_cost'])
            if isinstance(usage, dict) and usage.get('cost') is not None and Decimal(str(usage['cost'])) != Decimal(str(stats['total_cost'])):
                raise ValueError('response and generation billing disagree')
            if amount > envelope['reserved_microusd']:
                self.ledger.transition(receipt, 'OVERRUN', observed_cost=known_cost)
                raise ExecutionBlocked('generation charge exceeds reservation')
            # Only a safe scalar allowlist is returned. Never echo arbitrary
            # generation metadata, personal identifiers, referrers or reasoning.
            safe_stats = {k: stats[k] for k in ('id', 'model', 'provider_name', 'total_cost',
                         'native_tokens_prompt', 'native_tokens_completion', 'native_tokens_reasoning', 'is_byok')}
            row = self.ledger.transition(receipt, 'SETTLED', observed_cost=amount, billing=safe_stats)
            return {'receipt': receipt, 'answer': answer, 'billing': safe_stats,
                    'context': deepcopy(context), 'charged_microusd': row['charged'],
                    'status': 'SETTLED_AWAITING_DURABLE_PHASE_CHECKPOINT',
                    'actual_network_requests': 0, 'actual_paid_calls': 0, 'actual_spend_usd': 0}
        except BaseException as error:
            try:
                row = next(r for r in self.ledger.snapshot() if r['id'] == receipt)
                if row['status'] in ('STARTED', 'RESPONSE_SEEN', 'SETTLED'):
                    self.ledger.transition(receipt, 'UNCERTAIN', observed_cost=known_cost,
                                           generation_id=generation_id, error_type=type(error).__name__)
            except BaseException:
                # Torn persistence remains fail-closed under the independent
                # anchor, even when a failure cannot itself be committed.
                pass
            if not isinstance(error, Exception): raise
            raise ExecutionBlocked('global phase unresolved or overrun; no retry (' + type(error).__name__ + ')') from None
