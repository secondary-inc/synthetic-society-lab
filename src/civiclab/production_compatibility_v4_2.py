"""Unreleased v4.2 safe diagnostics candidate; no live release or launcher.

Tests use mocked OS homes, external assertions, catalog and private transport.
External hashes are trusted workflow bindings, not human authentication.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import re
import sys

from .common import atomic_json, canonical_bytes, canonical_hash, sha256_file, utc_now, redact
from .model import ExecutionBlocked, micros
from .owner_budget_v3 import digest, freeze
from .production_admission_v4 import precheck_review, precheck_dispatch_approval, prepare_new_dispatch
from .production_owner_v4 import new_operation_time
from .production_price_v4 import financial_context
from .production_compatibility_transport_v4_2 import _CompatibilityTransportV4_2, _SafeTransportFailure

KIND = 'ONE_REQUEST_JSON_COMPATIBILITY_EXECUTION_V4_2'
_RECEIPTS = ('INDEPENDENT_AUDIT_PRODUCTION_ADMISSION_V4_COMPONENT_RAW.json',
             'INDEPENDENT_AUDIT_PRODUCTION_COMPATIBILITY_EXECUTOR_V4_METHODS.json',
             'INDEPENDENT_AUDIT_PRODUCTION_COMPATIBILITY_V4_AUXILIARY_USAGE_FINDING.json')


def execution_contract():
    from . import (common, model, openrouter_http_v2, live_billing_v2, owner_budget_v3,
                   production_admission_v4, production_owner_v4, production_price_v4,
                   production_compatibility_transport_v4_2, production_compatibility_v4)
    modules = (sys.modules[__name__], common, model, openrouter_http_v2, live_billing_v2,
               owner_budget_v3, production_admission_v4, production_owner_v4,
               production_price_v4, production_compatibility_transport_v4_2, production_compatibility_v4)
    repo = Path(__file__).resolve().parents[2]
    return {'kind': KIND, 'code_pins': {str(Path(m.__file__).relative_to(repo)): sha256_file(m.__file__) for m in modules},
            'dependency_receipts': {p: sha256_file(repo / 'reports' / p) for p in _RECEIPTS},
            'policy': {'POST_attempts': 1, 'statistics_GET_attempts': 1, 'inference_retries': 0,
                       'socket_seconds': 15, 'cooperative_seconds': 30, 'body_bytes': 2_000_000,
                       'quality': 'EXACT_OBJECT_OK_JSON_BOOLEAN_TRUE',
                       'safe_diagnostics': 'CLOSED_STAGE_CATEGORY_INTEGER_HTTP_STATUS_V4_2',
                       'checkpoint_schema': 1, 'global_owner_commit_required': True,
                       'auxiliary_observation_policy': 'PRESENT_ZERO_INTEGER_OR_REFUSE_ABSENT_NOT_REPORTED_V4_1'}}


def validate_execution_release(release, review, approval, executor_review, *,
                               expected_review_hash, expected_approval_hash, expected_executor_review_hash):
    release, review = precheck_review(release, review, expected_review_hash)
    approval = precheck_dispatch_approval(approval, expected_approval_hash, release, review,
                                         expected_review_hash, now=new_operation_time())
    er = freeze(executor_review); digest(expected_executor_review_hash)
    contract = execution_contract()
    if (type(er) is not dict or set(er) != {'kind', 'review_id', 'reviewer_role', 'contract_sha256',
                                           'foundation_review_sha256', 'release_sha256'}
        or er['kind'] != 'INDEPENDENT_COMPATIBILITY_EXECUTOR_REVIEW_V4_2'
        or er['reviewer_role'] != 'independent_auditor'
        or canonical_hash(er) != expected_executor_review_hash
        or er['contract_sha256'] != canonical_hash(contract)
        or review['limitations_sha256'] != canonical_hash(contract)
        or er['foundation_review_sha256'] != expected_review_hash
        or er['release_sha256'] != canonical_hash(release)):
        raise ExecutionBlocked('exact external executor/code contract release required')
    digest(er['review_id'], 32)
    return release, review, approval, er, contract


class _Journal:
    def __init__(self, workspace, run_id, manifest):
        self.path = Path(workspace).resolve() / 'data/processed/compatibility_runs' / run_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.mkdir(mode=0o700, exist_ok=False)
        self.sequence = 0; self.previous = None
        self.write('manifest', manifest)
        self.event('EXECUTION_STARTED')

    def write(self, name, value):
        path = self.path / (name + '.local.json')
        if path.exists():
            raise ExecutionBlocked('immutable compatibility artifact already exists')
        if redact(value) != value:
            raise ExecutionBlocked('credential-like compatibility artifact refused')
        atomic_json(path, value)
        return path

    def event(self, kind, **fields):
        self.sequence += 1
        value = {'sequence': self.sequence, 'previous_sha256': self.previous,
                 'at_utc': utc_now(), 'event': kind, **fields}
        path = self.write('event-' + str(self.sequence).zfill(6), value)
        self.previous = sha256_file(path)

    def finish(self, summary):
        self.event('TERMINAL', status=summary['status'])
        self.write('summary', summary)
        self.write('checksums', {p.name: sha256_file(p) for p in sorted(self.path.iterdir()) if p.is_file()})


def _transport(credential):
    return _CompatibilityTransportV4_2(credential)


def _no_secret(value, credential):
    raw = canonical_bytes(value)
    if len(raw) > 2_000_000 or credential._value.encode('utf-8') in raw or redact(value) != value:
        raise ExecutionBlocked('private response body refused before hashing or persistence')


def _answer(response):
    choices = response.get('choices')
    message = choices[0].get('message') if type(choices) is list and len(choices) == 1 and type(choices[0]) is dict else None
    text = message.get('content') if type(message) is dict else None
    if type(text) is not str or len(text.encode('utf-8')) > 4096:
        return {'status': 'INVALID_CONTENT', 'parsed': None, 'raw_text': None}
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('duplicate JSON member')
            result[k] = v
        return result
    try:
        value = json.loads(text, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        canonical_bytes(value)
    except (ValueError, TypeError, RecursionError):
        return {'status': 'INVALID_JSON', 'parsed': None, 'raw_text': text}
    valid = type(value) is dict and set(value) == {'ok'} and value['ok'] is True
    return {'status': 'VALID' if valid else 'INVALID_SHAPE', 'parsed': value, 'raw_text': text}


@financial_context
def _cost(value):
    if type(value) not in (int, float, str) or len(str(value)) > 64:
        raise ValueError('bounded monetary scalar required')
    number = Decimal(str(value))
    if not number.is_finite() or not -18 <= number.as_tuple().exponent <= 18:
        raise ValueError('unsupported observed monetary domain')
    return micros(value)


def _observed_cost(value, credential):
    # Safe scalar bookkeeping may precede refusal of the rest of a body. Never
    # persist a key-looking numeric string or hash untrusted credential material.
    if credential._value in str(value):
        raise ExecutionBlocked('credential material in accounting scalar')
    return _cost(value)


def _usage_bounds(usage, envelope):
    if usage is None:
        return  # Native generation usage is still mandatory below.
    if type(usage) is not dict:
        raise ValueError('invalid completion usage')
    for field, bound in (('prompt_tokens', envelope['input_token_bound']),
                         ('completion_tokens', envelope['max_tokens'])):
        if field in usage and (type(usage[field]) is not int or not 0 <= usage[field] <= bound):
            raise ValueError('reported completion usage outside envelope')
    if 'total_tokens' in usage:
        if (type(usage['total_tokens']) is not int or 'prompt_tokens' not in usage
            or 'completion_tokens' not in usage
            or usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']):
            raise ValueError('completion usage total unverified')
    details = usage.get('completion_tokens_details')
    if details is not None and (type(details) is not dict or
        ('reasoning_tokens' in details and (type(details['reasoning_tokens']) is not int or details['reasoning_tokens'] != 0))):
        raise ValueError('reasoning usage outside released contract')



# Cached official GenerationResponse counters are recorded separately from the
# frozen owner billing schema. Missing is not evidence of observed zero.
_AUXILIARY_COUNTERS = ('native_tokens_completion_images', 'num_media_prompt',
    'num_media_completion', 'num_input_audio_prompt', 'num_search_results', 'num_fetches')


def _auxiliary_observation(stats):
    observations = {}; valid = True
    for field in _AUXILIARY_COUNTERS:
        if field not in stats:
            observations[field] = {'status': 'NOT_REPORTED'}
            continue
        value = stats[field]
        if type(value) is int and value == 0:
            observations[field] = {'status': 'OBSERVED_ZERO', 'value': 0}
        else:
            valid = False
            status = 'NONZERO_OR_NEGATIVE' if type(value) is int else 'UNSUPPORTED_OR_NULL_DOMAIN'
            observations[field] = {'status': status}
            if type(value) is int and -1_000_000_000 <= value <= 1_000_000_000:
                observations[field]['value'] = value
    for field in ('web_search_engine', 'service_tier'):
        if field not in stats:
            observations[field] = {'status': 'NOT_REPORTED'}
        elif stats[field] is None:
            observations[field] = {'status': 'NULL_REPORTED_NO_IDENTITY_CLAIM'}
        else:
            observations[field] = {'status': 'UNRELEASED_NON_NULL_VALUE'}; valid = False
    for field in ('streamed', 'cancelled'):
        if field not in stats:
            observations[field] = {'status': 'NOT_REPORTED'}
        elif stats[field] is False:
            observations[field] = {'status': 'OBSERVED_FALSE', 'value': False}
        else:
            observations[field] = {'status': 'UNSUPPORTED_OR_TRUE_DOMAIN'}; valid = False
    return {'policy': 'TEXT_ONLY_OBSERVABLE_AUXILIARY_FIELDS_V4_1',
            'fields': observations, 'admitted_under_reviewed_request_applicability': valid}, valid


def _row(owner, receipt):
    return next(r for r in owner.snapshot()['charges'] if r['id'] == receipt)



class _SafeExecutionFailure(ExecutionBlocked):
    def __init__(self, diagnostic):
        self.diagnostic = deepcopy(diagnostic)
        super().__init__('compatibility execution stopped; inspect safe diagnostic; no retry')


def _safe_error_kind(error):
    # A custom exception class name can itself contain secret material.
    kinds = {ExecutionBlocked: 'ExecutionBlocked', _SafeTransportFailure: 'SafeTransportFailure',
             ValueError: 'ValueError', TypeError: 'TypeError', OSError: 'OSError',
             RuntimeError: 'RuntimeError', KeyboardInterrupt: 'KeyboardInterrupt',
             SystemExit: 'SystemExit', TimeoutError: 'TimeoutError'}
    return kinds.get(type(error), 'UnclassifiedFailure')


def _failure_diagnostic(error, stage, posts, statistics, receipt, known, row):
    transport = None
    if type(error) is _SafeTransportFailure:
        try:
            transport = error.diagnostic()
        except Exception:
            pass  # Never serialize arbitrary exception fields or their strings.
    def amount(field):
        value = row.get(field) if type(row) is dict else None
        return value if type(value) is int and value >= 0 else None
    return {'executor_stage': stage, 'transport': transport,
            'dispatch_outcome': 'POST_ATTEMPTED' if posts else 'PRE_POST_STOP',
            'model_POST_attempts': posts, 'statistics_GET_attempts': statistics,
            'reservation_recorded': receipt is not None,
            'reserved_microusd': amount('reserved'),
            'conservative_charged_microusd': amount('charged'),
            'reported_provider_cost_microusd': known if type(known) is int else None,
            'automatic_retry': False}


def execute_compatibility(workspace, release, review, approval, executor_review, *,
                          expected_review_hash, expected_approval_hash, expected_executor_review_hash):
    release, review, approval, er, contract = validate_execution_release(
        release, review, approval, executor_review, expected_review_hash=expected_review_hash,
        expected_approval_hash=expected_approval_hash, expected_executor_review_hash=expected_executor_review_hash)
    run_id = release['request']['run_id']
    journal = _Journal(workspace, run_id, {'kind': KIND, 'run_id': run_id,
                        'release_sha256': canonical_hash(release), 'review_sha256': expected_review_hash,
                        'approval_sha256': expected_approval_hash, 'executor_review': er, 'contract': contract})
    owner = None; receipt = None; known = None; generation = None
    post_attempts = 0; stats_attempts = 0
    stage = 'PUBLIC_PREPARATION'; accounting = None
    try:
        journal.event('PUBLIC_METADATA_PREPARATION_INTENT')
        prepared = prepare_new_dispatch(release, review, approval, expected_review_hash=expected_review_hash,
                                        expected_approval_hash=expected_approval_hash)
        owner = prepared._owner; credential = prepared._credential
        stage = 'TRANSPORT_CONSTRUCTION'
        transport = _transport(credential)  # No request; invalid key shape fails before reservation.
        stage = 'PAYLOAD_VALIDATION'
        payload = prepared.payload; context = prepared.context
        body = canonical_bytes(payload)
        if canonical_hash(payload) != context['payload_hash']:
            raise ExecutionBlocked('admitted request changed')
        journal.write('request', {'payload': payload, 'context': context})
        stage = 'RESERVATION'
        receipt = prepared.reserve()
        stage = 'POST_INTENT'
        journal.event('RESERVED_BEFORE_POST', receipt=receipt, request_sha256=context['payload_hash'])
        # If this durable intent fails, no POST occurs; the owner retains STARTED.
        journal.event('MODEL_POST_INTENT', receipt=receipt)
        post_attempts = 1
        stage = 'MODEL_POST'
        response = transport.post_bytes(body)
        stage = 'RESPONSE_VALIDATION'
        usage = response.get('usage') if type(response) is dict else None
        if type(usage) is dict and usage.get('cost') is not None:
            known = _observed_cost(usage['cost'], credential)
        _no_secret(response, credential)
        if type(response) is not dict:
            raise ValueError('invalid response domain')
        identity = response.get('id')
        valid_id = type(identity) is str and len(identity) <= 128 and re.fullmatch(r'gen-[0-9A-Za-z-]+', identity)
        if valid_id:
            generation = identity
        if known is not None and known > context['envelope']['reserved_microusd']:
            owner.transition(receipt, 'UNCERTAIN', observed_cost=known, generation_id=generation,
                             error_type='ObservedChargeOverrun')
            raise ExecutionBlocked('known charge exceeds reservation; no statistics')
        if not valid_id or response.get('model') != context['terms']['model']:
            raise ValueError('unverified generation/model')
        answer = _answer(response)
        owner.transition(receipt, 'RESPONSE_SEEN', generation_id=generation,
                         output_hash=canonical_hash(answer), observed_cost=known)
        journal.event('RESPONSE_SEEN', receipt=receipt, generation_id=generation,
                      quality_status=answer['status'], known_microusd=known)
        stage = 'STATISTICS_CLAIM'
        owner.claim_statistics_lookup(receipt)
        journal.event('STATISTICS_GET_INTENT', receipt=receipt, generation_id=generation)
        stats_attempts = 1
        stage = 'STATISTICS_GET'
        result = transport.statistics(generation)
        stage = 'STATISTICS_VALIDATION'
        stats = result.get('data') if type(result) is dict else None
        if type(stats) is dict and stats.get('id') == generation and stats.get('total_cost') is not None:
            known = max(known or 0, _observed_cost(stats['total_cost'], credential))
        _no_secret(result, credential)
        if type(stats) is not dict or stats.get('id') != generation:
            raise ValueError('generation metadata identity unavailable')
        if known is not None and known > context['envelope']['reserved_microusd']:
            owner.transition(receipt, 'OVERRUN', observed_cost=known)
            raise ExecutionBlocked('generation cost exceeds reservation')
        if (stats.get('model') != context['terms']['model']
            or stats.get('provider_name') != context['terms']['reported_provider']
            or stats.get('is_byok') is not False):
            raise ValueError('actual serving identity or billing mode unverified')
        for field, bound in (('native_tokens_prompt', context['envelope']['input_token_bound']),
                             ('native_tokens_completion', context['envelope']['max_tokens']),
                             ('native_tokens_reasoning', 0)):
            if type(stats.get(field)) is not int or not 0 <= stats[field] <= bound:
                raise ValueError('native usage unverified')
        auxiliary, admitted_auxiliary = _auxiliary_observation(stats)
        journal.write('auxiliary-observation', auxiliary)
        if not admitted_auxiliary:
            raise ExecutionBlocked('observed generation activity outside text-only contract')
        amount = _cost(stats['total_cost'])
        _usage_bounds(usage, context['envelope'])
        if type(usage) is dict and usage.get('cost') is not None and Decimal(str(usage['cost'])) != Decimal(str(stats['total_cost'])):
            raise ValueError('response and generation cost disagree')
        billing = {k: stats[k] for k in ('id', 'model', 'provider_name', 'total_cost',
                   'native_tokens_prompt', 'native_tokens_completion', 'native_tokens_reasoning', 'is_byok')}
        stage = 'SETTLEMENT'
        owner.transition(receipt, 'SETTLED', observed_cost=amount, billing=billing)
        stage = 'CHECKPOINT'
        checkpoint = journal.write('phase', {'schema_version': 1, 'run_id': run_id,
                    'unit_id': context['unit_id'], 'phase': context['phase'], 'receipt': receipt,
                    'request_hash': context['envelope']['request_hash'], 'output': answer})
        journal.write('billing', billing)
        journal.event('PHASE_CHECKPOINT_DURABLE', receipt=receipt, sha256=sha256_file(checkpoint))
        stage = 'OWNER_COMMIT'
        owner.commit_phase(receipt, checkpoint)
        journal.event('OWNER_PHASE_COMMITTED', receipt=receipt)
        summary = {'status': 'COMPATIBLE' if answer['status'] == 'VALID' else 'CHARGED_QUALITY_FAILURE',
                   'kind': KIND, 'receipt': receipt, 'generation_id': generation,
                   'quality_status': answer['status'], 'charged_microusd': amount,
                   'model_POST_attempts': post_attempts, 'statistics_GET_attempts': stats_attempts,
                   'scope': 'ONE_NONPOLITICAL_API_COMPATIBILITY_OBSERVATION_NO_SCIENTIFIC_EFFECT'}
        stage = 'JOURNAL_FINISH'
        journal.finish(summary)
        return {'path': str(journal.path), 'summary': summary}
    except BaseException as error:
        if owner is not None and receipt is not None:
            try:
                row = _row(owner, receipt)
                if row['status'] in ('STARTED', 'RESPONSE_SEEN', 'SETTLED'):
                    owner.transition(receipt, 'UNCERTAIN', observed_cost=known,
                                     generation_id=generation, error_type=_safe_error_kind(error))
            except BaseException:
                pass  # Torn state remains fail-closed; no always-writable marker claim.
        try:
            accounting = _row(owner, receipt) if owner is not None and receipt is not None else None
        except BaseException:
            accounting = None
        diagnostic = _failure_diagnostic(error, stage, post_attempts, stats_attempts, receipt, known, accounting)
        try:
            journal.event('FAILED_OR_UNCERTAIN', error_type=_safe_error_kind(error), receipt=receipt, diagnostic=diagnostic)
            journal.finish({'status': 'FAILED_OR_UNCERTAIN', 'kind': KIND, 'receipt': receipt,
                            'error_type': _safe_error_kind(error), 'model_POST_attempts': post_attempts,
                            'statistics_GET_attempts': stats_attempts, 'automatic_retry': False,
                            'diagnostic': diagnostic})
        except BaseException:
            pass  # Preserve all bytes, including a possible durable terminal success.
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise KeyboardInterrupt() from None
        raise _SafeExecutionFailure(diagnostic) from None
