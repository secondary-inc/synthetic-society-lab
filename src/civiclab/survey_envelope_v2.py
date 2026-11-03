"""Offline survey request bounds for the v2 billing integration.

No dispatch, credential, authority or scientific release. Terms currently accept
only explicitly authored fixture pricing through the accepted v2 quote function.
"""
from copy import deepcopy
import json
import sys

from .common import canonical_hash, sha256_file
from .e02.instrument import score
from .live_billing_v2 import quote
from .model import ExecutionBlocked
from .survey_execution import INSTRUMENT_HASH, messages, pre_request, post_request

NUMBER_TEXT_BOUND = 32


def _runtime():
    f = sys.float_info
    if (f.radix, f.mant_dig, f.max_exp, f.min_exp) != (2, 53, 1024, -1021):
        raise ExecutionBlocked('unsupported numerical runtime for survey envelope')


def _pins():
    from pathlib import Path
    from . import survey_execution, live_billing_v2, model
    return {Path(m.__file__).name: sha256_file(Path(m.__file__))
            for m in (sys.modules[__name__], survey_execution, live_billing_v2, model)}


def compile_envelope(job, instrument, terms, *, max_tokens=512):
    """Freeze exact baseline and a conservative adaptive-post byte envelope."""
    _runtime()
    if canonical_hash(instrument) != INSTRUMENT_HASH:
        raise ValueError('exact frozen engineering instrument required')
    # Surrogate string values add JSON quoting/escaping beyond an admissible
    # number representation. They are never a response, prompt or dispatched call.
    surrogate = {k: 'X' * NUMBER_TEXT_BOUND for k in ('democratic_party', 'republican_party')}
    before = messages(pre_request(job, instrument))
    after_bound = messages(post_request(job, instrument, surrogate))
    pre_quote = quote(before, max_tokens, terms)
    post_quote = quote(after_bound, max_tokens, terms)
    plan = {'stage': 'OFFLINE_SURVEY_ADAPTIVE_ENVELOPE_V2', 'job': deepcopy(job),
            'instrument': deepcopy(instrument), 'terms': deepcopy(terms),
            'max_tokens': max_tokens, 'number_text_bound': NUMBER_TEXT_BOUND,
            'source_pins': _pins(), 'pre_quote': pre_quote, 'post_bound': post_quote,
            'pair_reserved_microusd_bound': pre_quote['reserved_microusd'] + post_quote['reserved_microusd']}
    # Deep-copy through the same finite JSON representation; no implicit object
    # subclasses, mutable external aliases or nonfinite price values retained.
    return json.loads(json.dumps(plan, sort_keys=True, allow_nan=False))


def validate_plan(plan, *, expected_hash):
    if canonical_hash(plan) != expected_hash:
        raise ExecutionBlocked('survey envelope differs from separately frozen plan hash')
    expected = compile_envelope(plan['job'], plan['instrument'], plan['terms'], max_tokens=plan['max_tokens'])
    if canonical_hash(plan) != canonical_hash(expected):
        raise ExecutionBlocked('survey envelope differs from exact frozen derivation')
    return expected


def prepare_phase(plan, phase, *, expected_plan_hash, before=None):
    """Return exact request/quote or a no-dispatch invalid-baseline disposition.

    Callers must still reserve in the owner ledger BEFORE any network operation.
    This function never interprets a planning bound as owner spending authority.
    """
    plan = validate_plan(plan, expected_hash=expected_plan_hash)
    job, instrument = plan['job'], plan['instrument']
    if phase == 'pre':
        if before is not None: raise ValueError('baseline cannot receive another response')
        request = pre_request(job, instrument)
    elif phase == 'post':
        if (type(before) is not dict or set(before) != {'democratic_party', 'republican_party'}
            or any(type(v) not in (int, float) or not 0 <= v <= 100 for v in before.values())
            or score(before, job['profile']['party'])['status'] != 'VALID'):
            return {'status': 'SKIPPED_INVALID_PRE', 'request': None, 'messages': None, 'quote': None}
        # A real JSON decoder yields exact built-in numbers. Do not canonicalize
        # arbitrary numeric subclasses or let booleans change the bound.
        for value in before.values():
            if type(value) not in (int, float) or len(json.dumps(value, allow_nan=False)) > NUMBER_TEXT_BOUND:
                raise ExecutionBlocked('baseline numerical encoding exceeds frozen post envelope')
        request = post_request(job, instrument, before)
    else:
        raise ValueError('unknown survey phase')
    content = messages(request)
    actual = quote(content, plan['max_tokens'], plan['terms'])
    bound = plan['pre_quote'] if phase == 'pre' else plan['post_bound']
    for key in ('input_token_bound', 'encoded_message_bytes', 'reserved_microusd'):
        if actual[key] > bound[key]: raise ExecutionBlocked('actual request exceeds frozen phase envelope')
    if phase == 'pre' and actual != bound: raise ExecutionBlocked('baseline differs from exact request quote')
    return {'status': 'READY_FOR_SEPARATE_RESERVATION_NOT_AUTHORIZED', 'request': request,
            'messages': content, 'quote': actual}
