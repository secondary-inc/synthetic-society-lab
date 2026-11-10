"""Frozen two-configuration support-only cue study; pure planning and scoring.

No credentials, filesystem, HTTP, dispatch, owner mutation or inference. Authored
arithmetic tests are engineering oracles, never empirical positive controls.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import re

from ..common import canonical_bytes, canonical_hash
from ..model import ExecutionBlocked, micros
from ..production_price_v4 import validate_terms, quote, decimal_price, financial_context
from ..production_admission_v4 import _payload
from .exploratory_pilot_analysis_v1 import _load
from .alignment_anchoring_v1 import _bounded_answer, _number, parse_response
from .instrument import score as thermometer_score

PROTOCOL_SHA256 = 'ccedb7aa9989fd0e1e96cb8c0e132e154c4383cf63210a599bc51ab683ace1e8'
KEYS = {'democratic_party', 'republican_party', 'library_support', 'visits_change'}
NUMERIC = ('democratic_party', 'republican_party', 'library_support')
VISITS = ('INCREASE_40', 'DECREASE_40', 'NOT_REPORTED')
DISPATCHED = {'ANSWER', 'PARSE_ERROR', 'FAILED_UNCERTAIN', 'CANCELLED'}
ROLES = ('A', 'B')
MODES = ('OMITTED', 'SHOWN')
BOUND = 262144


def load_protocol(raw):
    if type(raw) is not bytes or len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ExecutionBlocked('exact frozen issue-cue protocol required')
    p = _load(raw, 65536)
    if (len(p['jobs']) != 56 or canonical_hash(p['jobs']) != p['assignment_canonical_sha256']
            or canonical_hash(p['instrument']) != p['instrument_canonical_sha256']):
        raise ExecutionBlocked('instrument or assignment differs')
    return p


def _shape(answer):
    return type(answer) is dict and set(answer) <= KEYS


def valid_baseline(answer):
    return _shape(answer) and _number(answer.get('library_support'))


@financial_context
def cost_envelope(protocol_bytes, terms_by_model):
    p = load_protocol(protocol_bytes)
    if type(terms_by_model) is not dict or set(terms_by_model) != set(ROLES):
        raise ExecutionBlocked('exact two role-specific contracts required')
    ceilings = {}
    for role in ROLES:
        terms = terms_by_model[role]
        validate_terms(terms)
        if any(terms[k] != v for k, v in p['models'][role].items()):
            raise ExecutionBlocked('fixed model/provider/route/output binding differs')
        amount = micros(Decimal(8192)*decimal_price(terms['input_usd_per_token'])
                        + Decimal(256)*decimal_price(terms['output_usd_per_token'])
                        + decimal_price(terms['request_fee_usd']))
        if not 0 < amount <= 1785:
            raise ExecutionBlocked('per-call maximum exceeded')
        ceilings[role] = amount
    batch = 28*sum(ceilings.values())
    if batch > 100000:
        raise ExecutionBlocked('full-batch maximum exceeded')
    return {'maximum_POSTs': 56, 'maximum_GETs': 168, 'maximum_catalog_GETs': 4,
            'per_model_call_microusd': ceilings, 'maximum_batch_microusd': batch,
            'batch_subceiling_microusd': 100000, 'actual_authority': False}


def _compile(p, terms, job, baseline):
    notice = next(n for n in p['notices'] if n['id'] == job['notice_id'])
    request = {'phase': job['phase'], 'seed': job['pair_seed'], 'profile': deepcopy(job['profile']),
               'survey': deepcopy(p['instrument']), 'item_order': deepcopy(job['item_order']),
               'notice': {k: notice[k] for k in ('text', 'source_label', 'wrapper')}}
    if job['baseline_mode'] == 'SHOWN':
        request['pre_response'] = {'library_support': baseline['library_support']}
    messages = [{'role': 'system', 'content': p['system_prompt']},
                {'role': 'user', 'content': json.dumps(request, sort_keys=True, allow_nan=False)}]
    envelope = quote(messages, 256, terms)
    if envelope['input_token_bound'] > 8192 or envelope['reserved_microusd'] > 1785:
        raise ExecutionBlocked('exact request exceeds frozen envelope')
    payload = _payload(messages, job['pair_seed'], 256, terms)
    if len(canonical_bytes(payload)) > BOUND:
        raise ExecutionBlocked('payload bound')
    return {**{k: job[k] for k in ('execution_order', 'phase', 'model_key', 'pair_seed',
                                   'baseline_execution_order', 'baseline_mode')},
            'unit_sha256': canonical_hash(job), 'request': request, 'messages': messages,
            'payload': payload, 'payload_sha256': canonical_hash(payload),
            'envelope': envelope, 'actual_authority': False}


def _envelope(p, records, provenance):
    if provenance not in ('MOCK', 'EXPLORATORY_REAL_MODEL'):
        raise ExecutionBlocked('explicit provenance required')
    result = {'protocol_sha256': PROTOCOL_SHA256, 'instrument_sha256': p['instrument_canonical_sha256'],
              'assignment_sha256': p['assignment_canonical_sha256'],
              'response_provenance': provenance, 'records': records}
    if len(canonical_bytes(result)) > BOUND:
        raise ExecutionBlocked('envelope bound')
    return result


def _walk(p, transcript, terms_by_model=None, stopped=False):
    """Replay every dispatch in fixed order; derive skips and terminal dispositions."""
    if type(transcript) is not list or len(transcript) > 56:
        raise ExecutionBlocked('finite ordered transcript required')
    rows = []; pre = {}; position = 0; halt = False
    for job in p['jobs']:
        i, phase = job['execution_order'], job['phase']
        before = pre.get(job['baseline_execution_order'])
        empty = dict(execution_order=i, phase=phase, answer=None)
        if halt:
            rows.append({**empty, 'status': 'NOT_ATTEMPTED'}); continue
        if job['baseline_mode'] == 'SHOWN' and not valid_baseline(before):
            rows.append({**empty, 'status': 'SKIPPED_INVALID_PRE'}); continue
        compiled = _compile(p, terms_by_model[job['model_key']], job, before) if terms_by_model else None
        if position == len(transcript):
            if stopped:
                halt = True; rows.append({**empty, 'status': 'NOT_ATTEMPTED'}); continue
            if compiled:
                return {'status': 'REQUEST_READY_NOT_ADMITTED', 'request': compiled,
                        'derived_records': rows, 'transcript_sha256': canonical_hash(transcript),
                        'actual_authority': False}
            raise ExecutionBlocked('incomplete nonstopped transcript')
        row = transcript[position]
        if (type(row) is not dict or set(row) != {'execution_order', 'phase', 'payload_sha256', 'status', 'answer'}
                or type(row['execution_order']) is not int or row['execution_order'] != i or row['phase'] != phase
                or type(row['status']) is not str or row['status'] not in DISPATCHED
                or type(row['payload_sha256']) is not str or re.fullmatch('[a-f0-9]{64}', row['payload_sha256']) is None
                or (compiled and row['payload_sha256'] != compiled['payload_sha256'])
                or (row['status'] != 'ANSWER' and row['answer'] is not None)):
            raise ExecutionBlocked('phase/payload/sequence/disposition differs')
        if row['status'] == 'ANSWER':
            try: _bounded_answer(row['answer'])
            except (ValueError, TypeError, RecursionError, UnicodeError, OverflowError):
                raise ExecutionBlocked('answer contradicts parser bound') from None
        rows.append({k: row[k] for k in ('execution_order', 'phase', 'status', 'answer')})
        position += 1
        if phase == 'pre': pre[i] = row['answer'] if row['status'] == 'ANSWER' else None
        if row['status'] in ('FAILED_UNCERTAIN', 'CANCELLED'): halt = True
    if position != len(transcript):
        raise ExecutionBlocked('extra records after terminal disposition')
    return {'status': 'STOPPED' if halt else 'COMPLETE', 'records': rows,
            'response_envelope': _envelope(p, rows, 'MOCK'), 'actual_authority': False}


def next_action(protocol_bytes, terms_by_model, transcript_bytes):
    p = load_protocol(protocol_bytes); cost_envelope(protocol_bytes, terms_by_model)
    return _walk(p, _load(transcript_bytes, BOUND), terms_by_model)


def response_envelope(protocol_bytes, transcript_bytes, *, response_provenance='MOCK', stopped=False,
                      terms_by_model=None):
    """Owner-authenticated export. With terms also replay every payload hash.

    Without terms this validates structure and scientific skips only; caller must
    authenticate original financial/checkpoint evidence. No billing claim follows.
    """
    p = load_protocol(protocol_bytes)
    if type(stopped) is not bool: raise ExecutionBlocked('literal stop flag required')
    if terms_by_model is not None: cost_envelope(protocol_bytes, terms_by_model)
    state = _walk(p, _load(transcript_bytes, BOUND), terms_by_model, stopped)
    return _envelope(p, state['records'], response_provenance)


def _item_scores(answer, party, notice_key, status='ANSWER'):
    shape = _shape(answer)
    def quality(k):
        if status != 'ANSWER': return 'UNASKED' if status in ('SKIPPED_INVALID_PRE', 'NOT_ATTEMPTED') else 'NO_USABLE_ANSWER'
        if not shape: return 'INVALID_SHAPE'
        if k not in answer: return 'MISSING_KEY'
        if answer[k] is None: return 'MISSING_NULL'
        return 'VALID' if (_number(answer[k]) if k in NUMERIC else type(answer[k]) is str and answer[k] in VISITS) else 'INVALID'
    qualities = {k: quality(k) for k in sorted(KEYS)}
    nums = {k: answer[k] if qualities[k] == 'VALID' else None for k in NUMERIC}
    cq = qualities['visits_change']
    comprehension = ('CORRECT' if answer['visits_change'] == notice_key else 'INCORRECT') if cq == 'VALID' else cq
    gap = thermometer_score({k: nums[k] for k in ('democratic_party', 'republican_party')}, party)['primary']
    return {'support': nums['library_support'], 'party_gap': gap, 'item_quality': qualities,
            'comprehension': comprehension, 'baseline_valid': status == 'ANSWER' and valid_baseline(answer)}


def _summary(values):
    complete = [v['value'] for v in values if v['value'] is not None]
    return {'planned_contexts': 4, 'complete_contexts': len(complete),
            'mean_points': sum(complete)/len(complete) if complete else None,
            'min_points': min(complete) if complete else None, 'max_points': max(complete) if complete else None,
            'context_values': values, 'interval_95': None,
            'uncertainty_status': 'NOT_ESTIMATED_PURPOSIVE_TECHNICAL_CONTEXTS_ONE_ISSUE'}


def _comprehension(cells):
    counts = Counter(s['comprehension'] for s in cells)
    valid = counts['CORRECT'] + counts['INCORRECT']; planned = len(cells)
    return {'planned': planned, 'valid': valid, 'correct': counts['CORRECT'],
            'observed_factual_errors': counts['INCORRECT'],
            'correct_per_planned': counts['CORRECT']/planned if planned else None,
            'correct_per_valid': counts['CORRECT']/valid if valid else None,
            'quality_counts': dict(counts)}


def analyze(protocol_bytes, canonical_envelope_bytes):
    p = load_protocol(protocol_bytes); e = _load(canonical_envelope_bytes, BOUND)
    if (type(e) is not dict or set(e) != {'protocol_sha256', 'instrument_sha256', 'assignment_sha256', 'response_provenance', 'records'}
            or e['protocol_sha256'] != PROTOCOL_SHA256 or e['instrument_sha256'] != p['instrument_canonical_sha256']
            or e['assignment_sha256'] != p['assignment_canonical_sha256']
            or e['response_provenance'] not in ('MOCK', 'EXPLORATORY_REAL_MODEL')
            or type(e['records']) is not list or len(e['records']) != 56):
        raise ExecutionBlocked('exact frozen 56-disposition envelope required')
    indexed = {}; scored = {}; halt = False; counts = Counter()
    for row in e['records']:
        if (type(row) is not dict or set(row) != {'execution_order', 'phase', 'status', 'answer'}
                or type(row['execution_order']) is not int or not 0 <= row['execution_order'] < 56
                or row['execution_order'] in indexed):
            raise ExecutionBlocked('duplicate or malformed phase record')
        indexed[row['execution_order']] = row
    for job in p['jobs']:
        i = job['execution_order']; row = indexed[i]; status = row['status']
        before = indexed.get(job['baseline_execution_order'], {}).get('answer')
        needs_skip = job['baseline_mode'] == 'SHOWN' and not valid_baseline(before)
        if (row['phase'] != job['phase'] or type(status) is not str
                or status not in DISPATCHED | {'SKIPPED_INVALID_PRE', 'NOT_ATTEMPTED'}
                or (status != 'ANSWER' and row['answer'] is not None)
                or (halt and status != 'NOT_ATTEMPTED')
                or (status == 'SKIPPED_INVALID_PRE' and not needs_skip)
                or (not halt and needs_skip and status not in ('SKIPPED_INVALID_PRE', 'NOT_ATTEMPTED'))):
            raise ExecutionBlocked('unsupported phase/skip/terminal disposition')
        if status == 'ANSWER':
            try: _bounded_answer(row['answer'])
            except (ValueError, TypeError, RecursionError, UnicodeError, OverflowError):
                raise ExecutionBlocked('answer bound differs') from None
        if status in ('FAILED_UNCERTAIN', 'CANCELLED', 'NOT_ATTEMPTED'): halt = True
        notice = next(n for n in p['notices'] if n['id'] == job['notice_id'])
        scored[i] = _item_scores(row['answer'], job['profile']['party'], notice['visits_change_key'], status)
        counts[status] += 1
    models = {}; interaction_values = {}
    for role in ROLES:
        jobs = [j for j in p['jobs'] if j['model_key'] == role]
        pre = {j['profile']['profile_id']: scored[j['execution_order']] for j in jobs if j['phase'] == 'pre'}
        cells = {(j['profile']['profile_id'], j['notice_id'], j['baseline_mode']): scored[j['execution_order']] for j in jobs if j['phase'] == 'post'}
        contrasts = {mode: [] for mode in MODES}; interactions = []; neutral = []; gaps = []; party_content = {mode: [] for mode in MODES}
        for profile in p['profiles']:
            pid = profile['profile_id']; ds = {}; info = {'profile_id': pid, 'party': profile['party']}
            for mode in MODES:
                plus = cells[pid, 'N02', mode]; minus = cells[pid, 'N03', mode]
                def difference(a, b): return a-b if a is not None and b is not None else None
                ds[mode] = difference(plus['support'], minus['support'])
                contrasts[mode].append({**info, 'value': ds[mode]})
                neutral.append({**info, 'mode': mode, 'value': difference(cells[pid, 'N01', mode]['support'], pre[pid]['support'])})
                party_content[mode].append({**info, 'value': difference(plus['party_gap'], minus['party_gap'])})
                for notice in ('N01', 'N02', 'N03'):
                    gaps.append({**info, 'mode': mode, 'notice_id': notice,
                                 'value': difference(cells[pid, notice, mode]['party_gap'], pre[pid]['party_gap'])})
            interactions.append({**info, 'value': difference(ds['SHOWN'], ds['OMITTED'])})
        interaction_values[role] = {r['profile_id']: r['value'] for r in interactions}
        comp = {}
        for mode in MODES:
            comp[mode] = _comprehension([cells[x['profile_id'], n, mode] for x in p['profiles'] for n in ('N01', 'N02', 'N03')])
            comp[mode]['directional'] = _comprehension([cells[x['profile_id'], n, mode] for x in p['profiles'] for n in ('N02', 'N03')])
            comp[mode]['by_notice'] = {n: _comprehension([cells[x['profile_id'], n, mode] for x in p['profiles']]) for n in ('N01', 'N02', 'N03')}
        primary = _summary(interactions); omitted = _summary(contrasts['OMITTED'])
        content_sensitive = (omitted['complete_contexts'] == 4 and omitted['mean_points'] > 0
                             and sum(x['value'] is not None and x['value'] > 0 for x in contrasts['OMITTED']) >= 3)
        factual_coverage = all(comp[mode]['directional']['correct'] >= 6 for mode in MODES)
        attenuation = (primary['complete_contexts'] == 4 and primary['mean_points'] < 0
                       and sum(x['value'] is not None and x['value'] < 0 for x in interactions) >= 3
                       and content_sensitive and factual_coverage)
        quality = Counter((k, q) for j in jobs for k, q in scored[j['execution_order']]['item_quality'].items())
        models[role] = {'binding': p['models'][role], 'primary_cue_interaction': primary,
                        'content_contrasts': {mode: _summary(contrasts[mode]) for mode in MODES},
                        'neutral_reference_support_changes': neutral, 'separate_partisan_gap_changes': gaps,
                        'separate_partisan_content_contrasts': {mode: _summary(party_content[mode]) for mode in MODES},
                        'comprehension': comp, 'baseline_quality': {'planned': 4, 'valid_for_shown': sum(x['baseline_valid'] for x in pre.values()),
                        'comprehension': _comprehension(list(pre.values()))},
                        'item_quality_counts': [{'item': k, 'quality': q, 'count': n} for (k, q), n in sorted(quality.items())],
                        'prespecified_patterns': {'content_sensitive': bool(content_sensitive),
                        'adequate_directional_factual_coverage': bool(factual_coverage),
                        'attenuation_in_this_configuration': bool(attenuation),
                        'observed_factual_errors': sum(comp[mode]['observed_factual_errors'] for mode in MODES)}}
    cross = []
    for profile in p['profiles']:
        pid = profile['profile_id']; a, b = (interaction_values[r][pid] for r in ROLES)
        cross.append({'profile_id': pid, 'A_value': a, 'B_value': b,
                      'value': b-a if a is not None and b is not None else None})
    any_primary = any(models[r]['primary_cue_interaction']['complete_contexts'] for r in ROLES)
    return {'kind': 'EXPLORATORY_ISSUE_CUE_CROSSMODEL_V1', 'response_provenance': e['response_provenance'],
            'protocol_sha256': PROTOCOL_SHA256, 'response_envelope_sha256': hashlib.sha256(canonical_envelope_bytes).hexdigest(),
            'status': 'NOT_ESTIMABLE' if not any_primary else 'DESCRIPTIVE_PARTIAL' if halt else 'DESCRIPTIVE_COMPLETE_BATCH',
            'models': models, 'crossmodel_common_context_interaction_difference': _summary(cross),
            'phase_counts': dict(counts), 'scored_phases': [{'execution_order': i, **scored[i]} for i in range(56)],
            'prespecified_patterns': {'attenuation_across_both_fixed_configurations': all(models[r]['prespecified_patterns']['attenuation_in_this_configuration'] for r in ROLES)},
            'limitations': p['scientific_scope']+' Distinct model/provider/tokenization/quantization configurations; technical seeds do not ensure deterministic or common randomness. No human mechanism, family-wide replication, inferential interval or equivalence claim. Old full-answer cue results are not pooled.',
            'actual_authority': False}
