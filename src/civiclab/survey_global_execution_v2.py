"""Journaled survey/global-billing integration, authored transport only.

No owner authorization, HTTP release, actual source population or paid execution.
Global fixture ledger creation is explicit and external to this per-run entrypoint.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys

from .common import RunStore, atomic_json, canonical_hash, redact, sha256_file
from .e02.experiment import assignments, evaluate
from .e02.instrument import change
from .live_billing_v2 import GlobalFixtureLedger
from .model import ExecutionBlocked
from .reconciled_client_v2 import FixtureHTTP, ReconciledFixtureClient, fixture_terms, visible_answer
from .survey_envelope_v2 import compile_envelope, prepare_phase
from .survey_execution import (PhaseJournal, INSTRUMENT_HASH, DEMO_STIMULUS_HASHES,
                               pre_request, post_request)

STAGE = 'MOCK_GLOBAL_SURVEY_PHASE_INTEGRATION_V2'


def _pins():
    from . import common, model, live_billing_v2, reconciled_client_v2, survey_envelope_v2, survey_execution
    from .e02 import instrument, experiment
    return {Path(m.__file__).name: sha256_file(Path(m.__file__))
            for m in (sys.modules[__name__], common, model, live_billing_v2,
                      reconciled_client_v2, survey_envelope_v2, survey_execution, instrument, experiment)}


def _valid(value):
    return (type(value) is dict and set(value) == {'democratic_party', 'republican_party'}
            and all(type(v) in (int, float) and 0 <= v <= 100 for v in value.values()))


def _context(prepared, terms, run_id, unit, phase, seed):
    prices = {k: Decimal(terms[v]) * (1_000_000 if k != 'request' else 1)
              for k, v in (('prompt', 'input_usd_per_token'), ('completion', 'output_usd_per_token'), ('request', 'request_fee_usd'))}
    payload = {'model': terms['model'], 'messages': prepared['messages'], 'stream': False,
               'seed': seed, 'temperature': 0, 'max_tokens': prepared['quote']['max_tokens'],
               'response_format': {'type': 'json_object'}, 'plugins': [],
               'provider': {'only': [terms['requested_route']], 'allow_fallbacks': False,
                            'require_parameters': True, 'max_price': {k: float(v) for k, v in prices.items()}}}
    return {'run_id': run_id, 'unit_id': unit, 'phase': phase, 'module': 'E02',
            'terms': terms, 'envelope': prepared['quote'], 'payload_hash': canonical_hash(payload),
            'sampling': {'seed': seed, 'temperature': 0, 'retries': 0}}


def _checkpoint_path(run, unit, phase):
    return run.path / ('phase-' + unit + '-' + phase + '.local.json')


def _identity(ledger):
    # open/snapshot validates the immutable header/anchor chain first.
    ledger.snapshot()
    return json.loads(ledger.anchor.read_text())['ledger_id']


def _verify(run, journal, ledger, jobs, plans, instrument, terms):
    """Reconstruct own requests/quality/billing; retain other runs' charges."""
    charges = ledger.snapshot()
    if any(c['status'] != 'PHASE_COMMITTED' for c in charges):
        raise ExecutionBlocked('unfinished global phase; no dispatch or automatic reconciliation')
    own = {c['id']: c for c in charges if c['context']['run_id'] == run.run_id}
    rows = {(r['unit'], r['phase']): r for r in journal.rows()}
    known = {canonical_hash(job): job for job in jobs}; consumed = set(); files = set()
    for (unit, phase), row in rows.items():
        if unit not in known or phase not in ('pre', 'post'):
            raise ExecutionBlocked('journal phase outside exact frozen assignments')
        if row['status'] in ('STARTED', 'FAILED_UNCERTAIN'):
            raise ExecutionBlocked('interrupted phase; no automatic replay')
        job = known[unit]; before_row = rows.get((unit, 'pre'))
        before = before_row['result']['output'] if phase == 'post' and before_row else None
        if phase == 'post' and (before_row is None or before_row['status'] not in ('DONE_VALID', 'DONE_INVALID')):
            raise ExecutionBlocked('post has no completed own baseline')
        expected = pre_request(job, instrument) if phase == 'pre' else post_request(job, instrument, before)
        if canonical_hash(row['request']) != canonical_hash(expected) or row['request_hash'] != canonical_hash(expected):
            raise ExecutionBlocked('journal request differs from frozen unit/phase/baseline')
        result = row['result']
        if row['status'] == 'SKIPPED_INVALID_PRE':
            if phase != 'post' or before_row['status'] != 'DONE_INVALID' or result != {'output': None, 'reason': 'SKIPPED_INVALID_PRE'}:
                raise ExecutionBlocked('invalid skipped-phase disposition')
            continue
        if phase == 'post' and before_row['status'] != 'DONE_VALID':
            raise ExecutionBlocked('invalid baseline dispatched a post request')
        if not isinstance(result, dict) or set(result) != {'completion', 'output'}:
            raise ExecutionBlocked('journal result schema changed')
        complete = result['completion']; receipt = complete.get('receipt')
        if receipt in consumed or receipt not in own:
            raise ExecutionBlocked('missing/foreign/duplicate global receipt')
        charge = own[receipt]; plan = plans[unit]
        prepared = prepare_phase(plan, phase, expected_plan_hash=canonical_hash(plan), before=before)
        if prepared['messages'] is None: raise ExecutionBlocked('unexpected skipped phase billing')
        context = _context(prepared, terms, run.run_id, unit, phase, job['pair_seed'])
        answer = complete.get('answer')
        if not isinstance(answer, dict): raise ExecutionBlocked('missing visible answer envelope')
        if answer.get('raw_text') is None:
            rebuilt = {'status': answer.get('status') if answer.get('status') in ('MISSING_OR_REFUSAL', 'INVALID_CONTENT_TYPE') else None,
                       'parsed': None, 'raw_text': None}
        else:
            rebuilt = visible_answer({'choices': [{'message': {'content': answer.get('raw_text')}}]})
        if canonical_hash(answer) != canonical_hash(rebuilt): raise ExecutionBlocked('visible answer parse/status differs')
        output = answer['parsed'] if _valid(answer['parsed']) else None
        expected_complete = {'receipt': receipt, 'answer': answer, 'billing': charge['billing'],
                             'context': context, 'charged_microusd': charge['charged'],
                             'status': 'SETTLED_AWAITING_DURABLE_PHASE_CHECKPOINT',
                             'actual_network_requests': 0, 'actual_paid_calls': 0, 'actual_spend_usd': 0}
        if (canonical_hash(complete) != canonical_hash(expected_complete)
            or canonical_hash(charge['context']) != canonical_hash(context)
            or canonical_hash(result['output']) != canonical_hash(output)
            or canonical_hash(answer) != charge['output_hash']
            or row['status'] != ('DONE_VALID' if output is not None else 'DONE_INVALID')):
            raise ExecutionBlocked('phase request/output/route/quality/billing reconciliation failed')
        path = _checkpoint_path(run, unit, phase); files.add(path.name)
        expected_checkpoint = {'schema_version': 1, 'run_id': run.run_id, 'unit_id': unit,
                               'phase': phase, 'receipt': receipt,
                               'request_hash': prepared['quote']['request_hash'], 'output': answer}
        if (not path.is_file() or sha256_file(path) != charge['checkpoint_hash']
            or canonical_hash(json.loads(path.read_text())) != canonical_hash(expected_checkpoint)):
            raise ExecutionBlocked('durable phase checkpoint missing or changed')
        consumed.add(receipt)
    if consumed != set(own): raise ExecutionBlocked('orphan own global receipt; no replay')
    if {p.name for p in run.path.glob('phase-*.local.json')} != files:
        raise ExecutionBlocked('unexpected local phase checkpoint')
    return rows


def run_mock_global_bridge(root, profiles, stimuli, instrument, *, ledger, transport=None,
                           terms=None, seed=20261103, repeats=1, resume=None, stop_after_phases=None):
    """Explicit existing owner fixture ledger; this entrypoint never resets it."""
    root = Path(root).resolve(); terms = deepcopy(terms or fixture_terms())
    if type(ledger) is not GlobalFixtureLedger: raise ExecutionBlocked('exact authored fixture ledger required')
    transport = transport if transport is not None else FixtureHTTP(terms)
    if type(transport) is not FixtureHTTP or transport.terms != terms:
        raise ExecutionBlocked('exact owned fake transport and matching terms required')
    inputs = deepcopy([profiles, stimuli, instrument, terms, transport.content, transport.overrides])
    if redact(inputs) != inputs: raise ValueError('credential-like fixture input rejected')
    profiles, stimuli, instrument, terms, content, overrides = inputs
    if (canonical_hash(instrument) != INSTRUMENT_HASH or not stimuli
        or any(canonical_hash(s) not in DEMO_STIMULUS_HASHES for s in stimuli)):
        raise ValueError('exact frozen engineering instrument/notices required')
    if any(type(p) is not dict or set(p) != {'profile_id', 'party'}
           or type(p['profile_id']) is not str or not 1 <= len(p['profile_id']) <= 80
           or p['party'] not in ('D', 'R', 'I', 'UNKNOWN') for p in profiles):
        raise ValueError('fictional ID/explicit party-only profiles required')
    if type(seed) is not int or not 0 <= seed < 2**32 or type(repeats) is not int or not 1 <= repeats <= 10:
        raise ValueError('bounded seed and repeats required')
    if stop_after_phases is not None and (type(stop_after_phases) is not int or stop_after_phases < 1):
        raise ValueError('positive clean checkpoint phase limit required')
    jobs = assignments(profiles, stimuli, seed, repeats)
    if len(jobs) > 2000: raise ValueError('fixture integration unit cap exceeded')
    plans = {canonical_hash(job): compile_envelope(job, instrument, terms) for job in jobs}
    ledger_id = _identity(ledger)
    config = {'stage': STAGE, 'seed': seed, 'repeats': repeats, 'jobs_hash': canonical_hash(jobs),
              'instrument_hash': canonical_hash(instrument), 'stimuli_hash': canonical_hash(stimuli),
              'plans_hash': canonical_hash(plans), 'terms': terms,
              'transport_script_hash': canonical_hash([content, overrides]), 'source_pins': _pins(),
              'fixture_owner_directory': str(ledger.directory), 'fixture_owner_id': ledger_id,
              'fixture_policy': ledger.policy, 'python': sys.version, 'actual_paid_budget_usd': 0,
              'invalid_policy': 'RETAIN_RAW_PRIVATE; SCORING_NULL_INVALID; SKIP_POST_FOR_INVALID_PRE'}
    run = RunStore.resume(root, resume, config) if resume else RunStore(root, 'E02', config, kind='MOCK')
    run.path.chmod(0o700)
    try:
        for name, value in [('assignments.local.json', jobs), ('instrument.json', instrument),
                            ('profiles.local.json', profiles), ('stimuli.json', stimuli),
                            ('request-plans.local.json', plans), ('fixture-script.local.json', [content, overrides])]:
            path = run.path / name
            if path.exists():
                if canonical_hash(json.loads(path.read_text())) != canonical_hash(value): raise ExecutionBlocked('frozen input changed')
            elif resume: raise ExecutionBlocked('frozen input missing')
            else: run.write(name, value)
        journal_path = run.path / 'global-phase-journal.local.sqlite'
        pair = run.path / 'global-phase-pair.local.json'
        if resume and (not journal_path.is_file() or not pair.is_file()):
            raise ExecutionBlocked('journal or own-ledger checkpoint missing; no reset')
        journal = PhaseJournal(journal_path); journal_path.chmod(0o600)
        def pair_state():
            own = [c for c in ledger.snapshot() if c['context']['run_id'] == run.run_id]
            return {'schema_version': 1, 'config_hash': canonical_hash(config), 'ledger_id': ledger_id,
                    'journal_sha256': sha256_file(journal_path), 'own_charges_hash': canonical_hash(own),
                    'phase_files': {p.name: sha256_file(p) for p in sorted(run.path.glob('phase-*.local.json'))}}
        if resume and canonical_hash(json.loads(pair.read_text())) != canonical_hash(pair_state()):
            raise ExecutionBlocked('own journal/ledger/checkpoint changed; no replay')
        rows = _verify(run, journal, ledger, jobs, plans, instrument, terms)
        atomic_json(pair, pair_state())
        router = ReconciledFixtureClient(ledger, terms, transport); phases = 0
        for job in jobs:
            unit = canonical_hash(job); plan = plans[unit]
            for phase in ('pre', 'post'):
                if (unit, phase) in rows: continue
                before_row = rows.get((unit, 'pre'))
                before = before_row['result']['output'] if before_row else None
                prepared = prepare_phase(plan, phase, expected_plan_hash=canonical_hash(plan), before=before)
                request = pre_request(job, instrument) if phase == 'pre' else post_request(job, instrument, before)
                journal.start(unit, phase, request)
                run.event('global_survey_phase_started', unit=unit, phase=phase, request_hash=canonical_hash(request))
                if prepared['messages'] is None:
                    result = {'output': None, 'reason': 'SKIPPED_INVALID_PRE'}; status = 'SKIPPED_INVALID_PRE'
                else:
                    try:
                        complete = router.complete(prepared['messages'], run_id=run.run_id, unit_id=unit,
                                                   phase=phase, seed=job['pair_seed'])
                        if canonical_hash(complete['context']) != canonical_hash(_context(prepared, terms, run.run_id, unit, phase, job['pair_seed'])):
                            raise ExecutionBlocked('client context differs from independently prepared phase')
                        parsed = complete['answer']['parsed']; output = parsed if _valid(parsed) else None
                        result = {'completion': complete, 'output': output}; status = 'DONE_VALID' if output is not None else 'DONE_INVALID'
                        path = _checkpoint_path(run, unit, phase)
                        atomic_json(path, {'schema_version': 1, 'run_id': run.run_id, 'unit_id': unit,
                                           'phase': phase, 'receipt': complete['receipt'],
                                           'request_hash': prepared['quote']['request_hash'], 'output': complete['answer']})
                    except BaseException:
                        journal.finish(unit, phase, 'FAILED_UNCERTAIN', {'error': 'UNRESOLVED_PHASE_NO_RETRY'})
                        raise
                journal.finish(unit, phase, status, result)
                if 'completion' in result:
                    ledger.commit_phase(result['completion']['receipt'], _checkpoint_path(run, unit, phase))
                rows = _verify(run, journal, ledger, jobs, plans, instrument, terms)
                atomic_json(pair, pair_state()); phases += 1
                run.event('global_survey_phase_committed', unit=unit, phase=phase, status=status, actual_spend_usd=0)
                if stop_after_phases is not None and phases >= stop_after_phases:
                    run.event('clean_checkpoint_pause', completed_phases=len(rows)); return run.path
        responses = []
        for job in jobs:
            unit = canonical_hash(job); a, b = rows[(unit, 'pre')], rows[(unit, 'post')]
            before, after = a['result']['output'], b['result']['output']
            responses.append({'profile_id': job['profile']['profile_id'], 'stimulus_id': job['stimulus_id'],
                              'repeat': job['repeat'], 'arm': job['arm'], 'execution_order': job['execution_order'],
                              'pre': before, 'post': after, 'scoring_party': job['profile']['party'],
                              'pre_request': a['request'], 'post_request': b['request'],
                              'request_hashes': [a['request_hash'], b['request_hash']],
                              'change': change(before, after, job['profile']['party']),
                              'phase_status': {'pre': a['status'], 'post': b['status']},
                              'phase_accounting': {'pre': a['result'], 'post': b['result']}})
        analysis = evaluate(responses, seed, expected_assignments=jobs, expected_instrument=instrument)
        own = [c for c in ledger.snapshot() if c['context']['run_id'] == run.run_id]
        run.write('responses.local.json', responses); run.write('analysis.json', analysis)
        run.write('accounting.local.json', own)
        run.finish({'status': 'PASS_MOCK_GLOBAL_SURVEY_PHASE_INTEGRATION', 'units': len(jobs),
                    'completed_global_calls': len(own), 'skipped_post_phases': sum(r['status']=='SKIPPED_INVALID_PRE' for r in rows.values()),
                    'simulated_charged_microusd': sum(c['charged'] for c in own),
                    'actual_network_requests': 0, 'actual_model_calls': 0, 'actual_spend_usd': 0,
                    'scope': 'MOCK engineering, private/unbundled; no live admission or human/model effect',
                    'original_population_gate': 'BLOCKED'})
        return run.path
    except BaseException as error:
        if not run.finished:
            run.write('failure.json', {'status': 'FAILED', 'error_type': type(error).__name__, 'retry_authorized': False})
            run.finish({'status': 'FAILED_MOCK_GLOBAL_SURVEY_INTEGRATION', 'actual_network_requests': 0,
                        'actual_model_calls': 0, 'actual_spend_usd': 0,
                        'reconciliation': 'PRIVATE_JOURNAL_AND_GLOBAL_OWNER; NO_AUTOMATIC_RETRY'})
        raise
    finally:
        run._release_lock()


def run_live_global_bridge(*args, **kwargs):
    raise ExecutionBlocked('production global survey admission unavailable; owner/study/price release required')
