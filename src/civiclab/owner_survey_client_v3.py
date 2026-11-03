"""Authored E02 request/client integration with renewable owner fixture epochs.

No HTTP, credentials, owner bootstrap, human approval, run or journal creation.
Existing owner/planner/v2 reconciliation modules remain unchanged.
"""
from decimal import Decimal
import re

from .common import canonical_bytes, canonical_hash
from .live_billing_v2 import quote
from .model import ExecutionBlocked, micros
from .owner_budget_v3 import OwnerBudgetFixtureV3, SCOPE, digest, freeze
from .reconciled_client_v2 import FixtureHTTP, visible_answer
from .survey_envelope_v2 import prepare_phase


class OwnerSurveyFixtureClientV3:
    """One fake request, one owner reservation; external checkpoint still required."""
    def __init__(self, ledger, terms, transport):
        if type(ledger) is not OwnerBudgetFixtureV3 or type(transport) is not FixtureHTTP:
            raise ExecutionBlocked('exact authored owner fixture and fake transport required')
        self.ledger = ledger
        self.terms = freeze(terms)
        self.transport = transport
        quote([{'role': 'user', 'content': 'validation only'}], 1, self.terms)
        if freeze(transport.terms) != self.terms:
            raise ExecutionBlocked('fixture transport terms differ')

    def complete(self, plan, *, expected_plan_hash, expected_approval_hash,
                 run_id, phase, before=None):
        if type(self.ledger) is not OwnerBudgetFixtureV3 or type(self.transport) is not FixtureHTTP:
            raise ExecutionBlocked('exact authored owner fixture and fake transport required')
        # Detach before validation; never silently substitute current approval.
        plan = freeze(plan); terms = freeze(self.terms)
        digest(expected_plan_hash); digest(expected_approval_hash)
        if plan['terms'] != terms or freeze(self.transport.terms) != terms:
            raise ExecutionBlocked('plan/client/transport terms differ')
        if phase == 'post' and (type(before) is not dict
            or set(before) != {'democratic_party', 'republican_party'}
            or any(type(v) not in (int, float) or not 0 <= v <= 100 for v in before.values())):
            # Nonfinite/non-JSON or custom objects are invalid, never serialized.
            # Normalize only to the planner's invalid disposition, not an answer.
            baseline = None
        else:
            baseline = freeze(before)
        prepared = prepare_phase(plan, phase, expected_plan_hash=expected_plan_hash, before=baseline)
        if prepared['messages'] is None:
            return prepared  # No owner event, receipt, quote, answer or fake call.
        seed = plan['job']['pair_seed']
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError('bounded frozen pair seed required')
        messages = prepared['messages']; envelope = prepared['quote']
        max_tokens = plan['max_tokens']
        prices = {k: Decimal(terms[v]) * (1_000_000 if k != 'request' else 1)
                  for k, v in (('prompt', 'input_usd_per_token'), ('completion', 'output_usd_per_token'), ('request', 'request_fee_usd'))}
        if any(Decimal(str(float(v))) != v for v in prices.values()):
            raise ValueError('price ceiling cannot be serialized without decimal drift')
        payload = {'model': terms['model'], 'messages': messages, 'stream': False,
                   'seed': seed, 'temperature': 0, 'max_tokens': max_tokens,
                   'response_format': {'type': 'json_object'}, 'plugins': [],
                   'provider': {'only': [terms['requested_route']], 'allow_fallbacks': False,
                                'require_parameters': True, 'max_price': {k: float(v) for k, v in prices.items()}}}
        context = {'approval_hash': expected_approval_hash, 'plan_hash': expected_plan_hash,
                   'run_id': run_id, 'unit_id': canonical_hash(plan['job']), 'phase': phase, 'module': 'E02',
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
            if any(r['id'] != receipt and r['generation_id'] == identity for r in self.ledger.snapshot()['charges']):
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
                    'context': freeze(context), 'charged_microusd': row['charged'],
                    'status': 'SETTLED_AWAITING_DURABLE_PHASE_CHECKPOINT',
                    'scope': SCOPE, 'actual_network_requests': 0, 'actual_paid_calls': 0, 'actual_spend_usd': 0}
        except BaseException as error:
            try:
                row = next(r for r in self.ledger.snapshot()['charges'] if r['id'] == receipt)
                if row['status'] in ('STARTED', 'RESPONSE_SEEN', 'SETTLED'):
                    self.ledger.transition(receipt, 'UNCERTAIN', observed_cost=known_cost,
                                           generation_id=generation_id, error_type=type(error).__name__)
            except BaseException:
                # Torn persistence remains fail-closed under the independent
                # anchor, even when a failure cannot itself be committed.
                pass
            if not isinstance(error, Exception): raise
            raise ExecutionBlocked('owner survey phase unresolved or overrun; no retry') from None


def create_live_owner_survey_client(*args, **kwargs):
    raise ExecutionBlocked('owner/study/price/credential/HTTP release unavailable')
