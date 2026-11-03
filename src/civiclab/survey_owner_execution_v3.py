"""Journaled survey/renewable-owner integration, authored transport only.

No owner authorization, HTTP release, actual source population or paid execution.
Owner creation and approval renewal are external to this per-run entrypoint.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys

from .common import RunStore, atomic_json, canonical_hash, redact, sha256_file
from .e02.experiment import assignments, evaluate
from .e02.instrument import change
from .owner_budget_v3 import OwnerBudgetFixtureV3, SCOPE, digest, freeze
from .model import ExecutionBlocked
from .reconciled_client_v2 import FixtureHTTP, fixture_terms, visible_answer
from .survey_envelope_v2 import compile_envelope, prepare_phase
from .owner_survey_client_v3 import OwnerSurveyFixtureClientV3
from .survey_execution import (PhaseJournal, INSTRUMENT_HASH, DEMO_STIMULUS_HASHES,
                               pre_request, post_request)

STAGE = 'MOCK_OWNER_EPOCH_SURVEY_PHASE_INTEGRATION_V3'


def _pins():
    from . import common, model, owner_budget_v3, owner_survey_client_v3, reconciled_client_v2, survey_envelope_v2, survey_execution
    from .e02 import instrument, experiment
    return {Path(m.__file__).name: sha256_file(Path(m.__file__))
            for m in (sys.modules[__name__], common, model, owner_budget_v3, owner_survey_client_v3,
                      reconciled_client_v2, survey_envelope_v2, survey_execution, instrument, experiment)}


def _valid(value):
    return (type(value) is dict and set(value) == {'democratic_party', 'republican_party'}
            and all(type(v) in (int, float) and 0 <= v <= 100 for v in value.values()))


def _context(prepared, terms, run_id, unit, phase, seed, plan_hash, approval_hash):
    prices = {k: Decimal(terms[v]) * (1_000_000 if k != 'request' else 1)
              for k, v in (('prompt', 'input_usd_per_token'), ('completion', 'output_usd_per_token'), ('request', 'request_fee_usd'))}
    payload = {'model': terms['model'], 'messages': prepared['messages'], 'stream': False,
               'seed': seed, 'temperature': 0, 'max_tokens': prepared['quote']['max_tokens'],
               'response_format': {'type': 'json_object'}, 'plugins': [],
               'provider': {'only': [terms['requested_route']], 'allow_fallbacks': False,
                            'require_parameters': True, 'max_price': {k: float(v) for k, v in prices.items()}}}
    return {'approval_hash': approval_hash, 'plan_hash': plan_hash,
            'run_id': run_id, 'unit_id': unit, 'phase': phase, 'module': 'E02',
            'terms': terms, 'envelope': prepared['quote'], 'payload_hash': canonical_hash(payload),
            'sampling': {'seed': seed, 'temperature': 0, 'retries': 0}}


def _checkpoint_path(run, unit, phase):
    return run.path / ('phase-' + unit + '-' + phase + '.local.json')


def _identity(ledger):
    return ledger.snapshot()['owner_id']


def _verify(run, journal, ledger, jobs, plans, instrument, terms):
    """Reconstruct own requests/quality/billing; retain other runs' charges."""
    charges = ledger.snapshot()['charges']
    if any(c['status'] != 'PHASE_COMMITTED' for c in charges):
        raise ExecutionBlocked('unfinished global phase; no dispatch or automatic reconciliation')
    own = {c['id']: c for c in charges if c['context']['run_id'] == run.run_id}
    raw_rows = journal.rows()
    rows = {(r['unit'], r['phase']): r for r in raw_rows}
    if len(rows) != len(raw_rows):
        raise ExecutionBlocked('duplicate journal phase identity')
    known = {canonical_hash(job): job for job in jobs}; consumed = set(); files = set()
    for (unit, phase), row in rows.items():
        if unit not in known or phase not in ('pre', 'post'):
            raise ExecutionBlocked('journal phase outside exact frozen assignments')
        if row['status'] not in ('DONE_VALID', 'DONE_INVALID', 'SKIPPED_INVALID_PRE'):
            raise ExecutionBlocked('interrupted phase; no automatic replay')
        job = known[unit]; before_row = rows.get((unit, 'pre'))
        before = before_row['result']['output'] if phase == 'post' and before_row else None
        if phase == 'post' and (before_row is None or before_row['status'] not in ('DONE_VALID', 'DONE_INVALID')):
            raise ExecutionBlocked('post has no completed own baseline')
        expected = pre_request(job, instrument) if phase == 'pre' else post_request(job, instrument, before)
        binding = row['request']
        if (type(binding) is not dict or set(binding) != {'survey_request','plan_hash','approval_hash'}
            or binding['plan_hash'] != canonical_hash(plans[unit])):
            raise ExecutionBlocked('journal authority/plan binding changed')
        expected_binding = {'survey_request': expected, 'plan_hash': canonical_hash(plans[unit]),
                            'approval_hash': binding['approval_hash']}
        if canonical_hash(binding) != canonical_hash(expected_binding) or row['request_hash'] != canonical_hash(expected_binding):
            raise ExecutionBlocked('journal request differs from frozen unit/phase/baseline')
        result = row['result']
        if row['status'] == 'SKIPPED_INVALID_PRE':
            if binding['approval_hash'] is not None or phase != 'post' or before_row['status'] != 'DONE_INVALID' or result != {'output': None, 'reason': 'SKIPPED_INVALID_PRE'}:
                raise ExecutionBlocked('invalid skipped-phase disposition')
            continue
        if phase == 'post' and before_row['status'] != 'DONE_VALID':
            raise ExecutionBlocked('invalid baseline dispatched a post request')
        if not isinstance(result, dict) or set(result) != {'completion', 'output'}:
            raise ExecutionBlocked('journal result schema changed')
        digest(binding['approval_hash'])
        complete = result['completion']; receipt = complete.get('receipt')
        if receipt in consumed or receipt not in own:
            raise ExecutionBlocked('missing/foreign/duplicate global receipt')
        charge = own[receipt]; plan = plans[unit]
        prepared = prepare_phase(plan, phase, expected_plan_hash=canonical_hash(plan), before=before)
        if prepared['messages'] is None: raise ExecutionBlocked('unexpected skipped phase billing')
        context = _context(prepared, terms, run.run_id, unit, phase, job['pair_seed'], canonical_hash(plan), binding['approval_hash'])
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
                             'scope': SCOPE, 'actual_network_requests': 0, 'actual_paid_calls': 0, 'actual_spend_usd': 0}
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


def compile_owner_study(profiles, stimuli, instrument, *, terms=None, content=None,
                        overrides=None, seed=20261103, repeats=1):
    """Pure authored specification; external expected hash still required."""
    terms = freeze(terms or fixture_terms())
    overrides = freeze(overrides or {})
    inputs = freeze([profiles, stimuli, instrument, terms, content, overrides])
    if redact(inputs) != inputs: raise ValueError('credential-like fixture input rejected')
    profiles, stimuli, instrument, terms, content, overrides = inputs
    if (canonical_hash(instrument) != INSTRUMENT_HASH or not stimuli
        or any(canonical_hash(s) not in DEMO_STIMULUS_HASHES for s in stimuli)):
        raise ValueError('exact frozen engineering instrument/notices required')
    if any(type(p) is not dict or set(p) != {'profile_id', 'party'}
           or type(p['profile_id']) is not str or not 1 <= len(p['profile_id']) <= 80 or not p['profile_id'].strip()
           or p['party'] not in ('D', 'R', 'I', 'UNKNOWN') for p in profiles):
        raise ValueError('fictional ID/explicit party-only profiles required')
    if type(seed) is not int or not 0 <= seed < 2**32 or type(repeats) is not int or not 1 <= repeats <= 10:
        raise ValueError('bounded seed and repeats required')
    jobs = assignments(profiles, stimuli, seed, repeats)
    if not jobs or len(jobs) > 180 or len({canonical_hash(j) for j in jobs}) != len(jobs): raise ValueError('nonempty unique fixture assignments within180 required')
    plans = {canonical_hash(job): compile_envelope(job, instrument, terms) for job in jobs}
    return {'stage': STAGE, 'profiles': profiles, 'stimuli': stimuli, 'instrument': instrument,
            'terms': terms, 'content': content, 'overrides': overrides, 'seed': seed,
            'repeats': repeats, 'jobs': jobs, 'plans': plans, 'source_pins': _pins(),
            'invalid_policy': 'RETAIN_RAW_PRIVATE; SCORING_NULL_INVALID; SKIP_POST_FOR_INVALID_PRE'}


def run_mock_owner_bridge(root, study, *, expected_study_hash, expected_approval_hash,
                          ledger, transport=None, resume=None, stop_after_phases=None):
    """Existing owner only; no bootstrap, grant, reset or caller survey answers."""
    if type(ledger) is not OwnerBudgetFixtureV3:
        raise ExecutionBlocked('exact existing authored owner fixture required')
    study = freeze(study); digest(expected_study_hash); digest(expected_approval_hash)
    if canonical_hash(study) != expected_study_hash:
        raise ExecutionBlocked('study differs from externally expected specification')
    rebuilt = compile_owner_study(study['profiles'], study['stimuli'], study['instrument'],
        terms=study['terms'], content=study['content'], overrides=study['overrides'],
        seed=study['seed'], repeats=study['repeats'])
    if canonical_hash(rebuilt) != expected_study_hash:
        raise ExecutionBlocked('study differs from exact frozen derivation')
    root = Path(root).resolve()
    profiles, stimuli, instrument, terms = [study[k] for k in ('profiles','stimuli','instrument','terms')]
    content, overrides, seed, repeats = [study[k] for k in ('content','overrides','seed','repeats')]
    jobs, plans = study['jobs'], study['plans']
    transport = transport if transport is not None else FixtureHTTP(terms, content=content, overrides=overrides)
    if (type(transport) is not FixtureHTTP or freeze(transport.terms) != terms
        or canonical_hash([transport.content, transport.overrides]) != canonical_hash([content, overrides])):
        raise ExecutionBlocked('exact fake provider and frozen script required')
    if stop_after_phases is not None and (type(stop_after_phases) is not int or stop_after_phases < 1):
        raise ValueError('positive clean checkpoint phase limit required')
    # Verify whole owner authority/global barrier before any run writes.
    if any(r['status'] != 'PHASE_COMMITTED' for r in ledger.snapshot()['charges']):
        raise ExecutionBlocked('unfinished owner phase blocks run admission')
    ledger_id = _identity(ledger)
    config = {'stage': STAGE, 'seed': seed, 'repeats': repeats, 'jobs_hash': canonical_hash(jobs),
              'instrument_hash': canonical_hash(instrument), 'stimuli_hash': canonical_hash(stimuli),
              'plans_hash': canonical_hash(plans), 'terms': terms,
              'transport_script_hash': canonical_hash([content, overrides]), 'source_pins': _pins(),
              'fixture_owner_directory': str(ledger.directory), 'fixture_owner_id': ledger_id,
              'expected_study_hash': expected_study_hash, 'fixture_scope': SCOPE, 'python': sys.version, 'actual_paid_budget_usd': 0,
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
            own = [c for c in ledger.snapshot()['charges'] if c['context']['run_id'] == run.run_id]
            return {'schema_version': 1, 'config_hash': canonical_hash(config), 'ledger_id': ledger_id,
                    'journal_sha256': sha256_file(journal_path), 'own_charges_hash': canonical_hash(own),
                    'phase_files': {p.name: sha256_file(p) for p in sorted(run.path.glob('phase-*.local.json'))}}
        if resume and canonical_hash(json.loads(pair.read_text())) != canonical_hash(pair_state()):
            raise ExecutionBlocked('own journal/ledger/checkpoint changed; no replay')
        rows = _verify(run, journal, ledger, jobs, plans, instrument, terms)
        atomic_json(pair, pair_state())
        router = OwnerSurveyFixtureClientV3(ledger, terms, transport); phases = 0
        for job in jobs:
            unit = canonical_hash(job); plan = plans[unit]
            for phase in ('pre', 'post'):
                if (unit, phase) in rows: continue
                before_row = rows.get((unit, 'pre'))
                before = before_row['result']['output'] if before_row else None
                prepared = prepare_phase(plan, phase, expected_plan_hash=canonical_hash(plan), before=before)
                request = pre_request(job, instrument) if phase == 'pre' else post_request(job, instrument, before)
                # Revalidate all own phases and whole owner before every dispatch.
                rows = _verify(run, journal, ledger, jobs, plans, instrument, terms)
                binding = {'survey_request': request, 'plan_hash': canonical_hash(plan),
                           'approval_hash': expected_approval_hash if prepared['messages'] is not None else None}
                journal.start(unit, phase, binding)
                run.event('global_survey_phase_started', unit=unit, phase=phase, request_hash=canonical_hash(request))
                if prepared['messages'] is None:
                    result = {'output': None, 'reason': 'SKIPPED_INVALID_PRE'}; status = 'SKIPPED_INVALID_PRE'
                else:
                    try:
                        complete = router.complete(plan, expected_plan_hash=canonical_hash(plan),
                            expected_approval_hash=expected_approval_hash, run_id=run.run_id,
                            phase=phase, before=before)
                        if canonical_hash(complete['context']) != canonical_hash(_context(prepared, terms, run.run_id, unit, phase, job['pair_seed'], canonical_hash(plan), binding['approval_hash'])):
                            raise ExecutionBlocked('client context differs from independently prepared phase')
                        parsed = complete['answer']['parsed']; output = parsed if _valid(parsed) else None
                        result = {'completion': complete, 'output': output}; status = 'DONE_VALID' if output is not None else 'DONE_INVALID'
                        path = _checkpoint_path(run, unit, phase)
                        atomic_json(path, {'schema_version': 1, 'run_id': run.run_id, 'unit_id': unit,
                                           'phase': phase, 'receipt': complete['receipt'],
                                           'request_hash': prepared['quote']['request_hash'], 'output': complete['answer']})
                    except BaseException:
                        # Only verified absence permits a zero-owner-reservation label.
                        disposition = 'FAILED_OWNER_STATE_UNKNOWN'
                        try:
                            matches = [r for r in ledger.snapshot()['charges'] if r['context']['run_id'] == run.run_id
                                       and r['context']['unit_id'] == unit and r['context']['phase'] == phase]
                            disposition = 'FAILED_UNRESOLVED_PHASE' if matches else 'FAILED_BEFORE_OWNER_RESERVATION'
                        except BaseException:
                            pass
                        journal.finish(unit, phase, disposition, {'error': 'FAILED_PHASE_NO_AUTOMATIC_RETRY'})
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
                              'pre_request': a['request']['survey_request'], 'post_request': b['request']['survey_request'],
                              'request_hashes': [canonical_hash(a['request']['survey_request']), canonical_hash(b['request']['survey_request'])],
                              'change': change(before, after, job['profile']['party']),
                              'phase_status': {'pre': a['status'], 'post': b['status']},
                              'phase_accounting': {'pre': a['result'], 'post': b['result']}})
        analysis = evaluate(responses, seed, expected_assignments=jobs, expected_instrument=instrument)
        own = [c for c in ledger.snapshot()['charges'] if c['context']['run_id'] == run.run_id]
        run.write('responses.local.json', responses); run.write('analysis.json', analysis)
        run.write('accounting.local.json', own)
        run.finish({'status': 'PASS_MOCK_OWNER_EPOCH_SURVEY_PHASE_INTEGRATION', 'units': len(jobs),
                    'completed_global_calls': len(own), 'skipped_post_phases': sum(r['status']=='SKIPPED_INVALID_PRE' for r in rows.values()),
                    'simulated_charged_microusd': sum(c['charged'] for c in own),
                    'actual_network_requests': 0, 'actual_model_calls': 0, 'actual_spend_usd': 0,
                    'scope': 'MOCK engineering, private/unbundled; no live admission or human/model effect',
                    'original_population_gate': 'BLOCKED'})
        return run.path
    except BaseException as error:
        if not run.finished:
            run.write('failure.json', {'status': 'FAILED', 'error_type': type(error).__name__, 'retry_authorized': False})
            run.finish({'status': 'FAILED_MOCK_OWNER_EPOCH_SURVEY_INTEGRATION', 'actual_network_requests': 0,
                        'actual_model_calls': 0, 'actual_spend_usd': 0,
                        'reconciliation': 'PRIVATE_JOURNAL_AND_GLOBAL_OWNER; NO_AUTOMATIC_RETRY'})
        raise
    finally:
        run._release_lock()


def run_live_owner_bridge(*args, **kwargs):
    raise ExecutionBlocked('production owner survey admission unavailable; owner/study/price release required')
