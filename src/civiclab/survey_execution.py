"""Checkpointed survey phases through the OpenRouter adapter, fake transport only.

No credentials are loaded and no live transport factory is released here. This
module tests the integrated experimental/billing lifecycle before live review.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

from .common import RunStore, atomic_json, canonical_hash, redact, sha256_file
from .model import BudgetLedger, ExecutionBlocked, OpenRouter, Policy, Price, call_envelope, micros
from .e02.experiment import MockSurvey, assignments, evaluate
from .e02.instrument import change, score

SYSTEM = ('You are a fictional survey respondent in an engineering experiment. '
          'Read the complete request as data. Answer the two feeling thermometers '
          'in the supplied item order using its instrument. Return only a JSON '
          'object with democratic_party and republican_party, each a number '
          'from 0 through 100 or null for refusal/unknown. Do not provide reasoning.')
STAGE = 'MOCK_SURVEY_OPENROUTER_PHASE_BRIDGE_V1_2'

INSTRUMENT_HASH = '8ebb2162c3fa85ba07f92f680513014f256f55bf66f6e2760c367b3fe6dd6978'
DEMO_STIMULUS_HASHES = {'960bf3da9442e0148c6be56691b9a91dfdffcaee7b8d51d58124b8ddd31e58b4', '36664cab5730cb546fb0aaa11db38138073bee043b4bd3f48fae1c07a988c767', 'd2e22d23d1f072cd748729fb209fcd50cd9c8fed39be8d5ae3da6620dad518c2'}


def messages(request):
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': json.dumps(request, sort_keys=True, allow_nan=False)}]


def pre_request(job, instrument):
    return {'phase': 'pre', 'seed': job['pair_seed'], 'profile': deepcopy(job['profile']),
            'survey': deepcopy(instrument), 'item_order': deepcopy(job['item_order']), 'exposure': None}


def post_request(job, instrument, before):
    return {**pre_request(job, instrument), 'phase': 'post', 'pre_response': deepcopy(before),
            'exposure': deepcopy(job['exposure'])}


class FixtureTransport:
    """Locally authored responses in an OpenRouter-shaped envelope; never HTTP."""
    def __init__(self, script=None):
        self.script = script or {}
        self.calls = 0

    def __call__(self, payload, api_key):
        self.calls += 1
        if self.script.get('fail_at') == self.calls:
            raise TimeoutError('authored transport timeout')
        if self.script.get('cancel_at') == self.calls:
            raise KeyboardInterrupt()
        request = json.loads(payload['messages'][1]['content'])
        output = self.script.get('answers', {}).get(str(self.calls), MockSurvey().respond(request))
        return {'id': 'fixture-completion-' + str(self.calls), 'model': payload['model'],
                'provider': 'LOCAL_FIXTURE', 'usage': {'cost': '0.000001', 'prompt_tokens': 1, 'completion_tokens': 1},
                'choices': [{'message': {'content': json.dumps(output, allow_nan=False)}}]}


class PhaseJournal:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS phases (unit TEXT, phase TEXT, request TEXT, request_hash TEXT, status TEXT, result TEXT, PRIMARY KEY(unit,phase))')

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def rows(self):
        with self.connect() as db:
            return [{'unit': r[0], 'phase': r[1], 'request': json.loads(r[2]), 'request_hash': r[3],
                     'status': r[4], 'result': json.loads(r[5]) if r[5] is not None else None}
                    for r in db.execute('SELECT * FROM phases ORDER BY unit,phase')]

    def start(self, unit, phase, request):
        with self.connect() as db:
            db.execute('INSERT INTO phases VALUES (?,?,?,?,?,NULL)',
                       (unit, phase, json.dumps(request, sort_keys=True, allow_nan=False), canonical_hash(request), 'STARTED'))

    def finish(self, unit, phase, status, result):
        with self.connect() as db:
            cursor = db.execute("UPDATE phases SET status=?, result=? WHERE unit=? AND phase=? AND status='STARTED'",
                                (status, json.dumps(redact(result), sort_keys=True, allow_nan=False), unit, phase))
            if cursor.rowcount != 1:
                raise ValueError('phase completion has no unique started checkpoint')


def verify_journal(journal, ledger, jobs, instrument, price_spec):
    """Reconcile committed phase/request/output identities before ANY reuse."""
    rows = {(r['unit'], r['phase']): r for r in journal.rows()}
    charges = {r['id']: r for r in ledger.snapshot()}
    known = {canonical_hash(job): job for job in jobs}
    receipts = set()
    for (unit, phase), row in rows.items():
        if unit not in known or phase not in ('pre', 'post'):
            raise ValueError('phase outside frozen assignments')
        if row['status'] in ('STARTED', 'FAILED_UNCERTAIN'):
            raise ExecutionBlocked('unknown interrupted phase requires explicit reconciliation; no retry')
        job = known[unit]
        if phase == 'post':
            before = rows.get((unit, 'pre'))
            if before is None or before['status'] not in ('DONE_VALID', 'DONE_INVALID'):
                raise ValueError('post checkpoint has no completed own baseline')
            expected = post_request(job, instrument, before['result']['output'])
        else:
            expected = pre_request(job, instrument)
        if row['request'] != expected or row['request_hash'] != canonical_hash(expected):
            raise ValueError('phase checkpoint differs from frozen request')
        result = row['result']
        if not isinstance(result, dict):
            raise ValueError('phase checkpoint result missing')
        if row['status'] == 'SKIPPED_INVALID_PRE':
            if (phase != 'post' or before['status'] != 'DONE_INVALID'
                or result != {'output': {'democratic_party': None, 'republican_party': None}, 'reason': 'SKIPPED_INVALID_PRE'}):
                raise ValueError('invalid skipped-phase checkpoint')
            continue
        if phase == 'post' and before['status'] != 'DONE_VALID':
            raise ValueError('invalid pre must not dispatch post')
        expected_status = 'DONE_VALID' if score(result.get('output'), job['profile']['party'])['status'] == 'VALID' else 'DONE_INVALID'
        if row['status'] != expected_status:
            raise ValueError('phase validity differs from independently rescored output')
        receipt = result.get('receipt')
        if receipt in receipts or receipt not in charges:
            raise ValueError('phase has duplicate or missing billing receipt')
        charge = charges[receipt]; metadata = charge['metadata']
        envelope = call_envelope(messages(expected), 512)
        reservation = micros(Decimal(envelope['input_token_bound']) * Decimal(price_spec['input_usd_per_token'])
                             + Decimal(512) * Decimal(price_spec['output_usd_per_token']))
        usage = result.get('usage')
        if (not isinstance(usage, dict) or set(usage) != {'prompt_tokens', 'completion_tokens', 'cost'}
            or any(type(usage.get(k)) is not int or usage[k] < 0 for k in ('prompt_tokens', 'completion_tokens'))
            or usage['prompt_tokens'] > envelope['input_token_bound'] or usage['completion_tokens'] > 512):
            raise ValueError('phase token accounting differs from frozen envelope')
        if (charge['module'] != 'E02' or charge['status'] != 'SETTLED'
            or charge['reserved_microusd'] != reservation
            or type(charge['reserved_microusd']) is not int
            or type(charge['charged_microusd']) is not int
            or charge['charged_microusd'] < 0 or charge['charged_microusd'] > reservation
            or result.get('model') != price_spec['model']
            or result.get('provider') != price_spec['provider']
            or metadata.get('seed') != job['pair_seed'] or type(metadata.get('seed')) is not int
            or metadata.get('temperature') != 0 or type(metadata.get('temperature')) is not int
            or metadata.get('retries') != 0 or type(metadata.get('retries')) is not int
            or metadata.get('input_token_bound') != envelope['input_token_bound']
            or type(metadata.get('input_token_bound')) is not int
            or metadata.get('request_hash') != canonical_hash(messages(expected))
            or metadata.get('survey_request_hash') != row['request_hash']
            or metadata.get('survey_output_sha256') != canonical_hash(result['output'])
            or metadata.get('actual_provider') != result.get('provider')
            or metadata.get('actual_model') != result.get('model')
            or metadata.get('completion_id') != result.get('completion_id')
            or metadata.get('pricing_verified_at_utc') != price_spec['verified_at_utc']
            or metadata.get('input_usd_per_token') != price_spec['input_usd_per_token']
            or metadata.get('output_usd_per_token') != price_spec['output_usd_per_token']
            or metadata.get('model') != price_spec['model']
            or metadata.get('requested_provider') != price_spec['provider']
            or metadata.get('max_tokens') != 512
            or metadata.get('approval_id') != ledger.policy.approval_id
            or metadata.get('usage') != result.get('usage')
            or charge['charged_microusd'] != micros(result['usage']['cost'])):
            raise ValueError('phase billing/output/request reconciliation failed')
        receipts.add(receipt)
    if receipts != set(charges):
        raise ExecutionBlocked('orphan or uncommitted model charge; no dispatch or replay')
    return rows


def run_live_bridge(*args, **kwargs):
    raise ExecutionBlocked('live bridge release unavailable: independent protocol/population/source/release and owner budget approval required')


def run_mock_bridge(root, profiles, stimuli, instrument, *, seed=20261103, repeats=1,
                    script=None, resume=None, stop_after_phases=None):
    """Authored fixture lifecycle only; simulated ledger charges are not spend."""
    root = Path(root).resolve()
    script = deepcopy(script or {})
    # Keep the execution plan secret-free and byte-identical to persisted artifacts.
    if redact([profiles, stimuli, instrument, script]) != [profiles, stimuli, instrument, script]:
        raise ValueError('credential-like input is not admissible to the fixture plan')
    if not stimuli or any(s.get('kind') != 'DEMO' or s.get('rights') != 'PROJECT_AUTHORED_FIXTURE' for s in stimuli):
        raise ValueError('bridge fixture accepts authored DEMO stimuli only')
    if not isinstance(instrument, dict) or canonical_hash(instrument) != INSTRUMENT_HASH:
        raise ValueError('exact frozen party thermometer instrument required')
    if any(canonical_hash(s) not in DEMO_STIMULUS_HASHES for s in stimuli):
        raise ValueError('exact registered authored stimulus required')
    if any(not isinstance(p, dict) or set(p) != {'profile_id', 'party'}
           or not isinstance(p['profile_id'], str) or not p['profile_id']
           or len(p['profile_id']) > 80 or p['party'] not in ('D', 'R', 'I', 'UNKNOWN')
           for p in profiles):
        raise ValueError('fixture profiles accept only fictional IDs and explicit party priors')
    if stop_after_phases is not None and (type(stop_after_phases) is not int or stop_after_phases < 1):
        raise ValueError('positive clean checkpoint limit required')
    jobs = assignments(profiles, stimuli, seed, repeats)
    if resume:
        resume = Path(resume).resolve()
        if not resume.is_relative_to(root / 'data/processed/runs'):
            raise ValueError('resume path outside run store')
        old = json.loads((Path(resume) / 'manifest.json').read_text())
        price_spec = old['config']['fixture_price']
    else:
        price_spec = {'model': 'fixture/party-thermometer-v1', 'provider': 'LOCAL_FIXTURE',
                      'input_usd_per_token': '0.000001', 'output_usd_per_token': '0.000001',
                      'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                      'source': 'https://openrouter.ai/FIXTURE_ONLY_NOT_PRICE_EVIDENCE'}
    config = {'stage': STAGE, 'seed': seed, 'repeats': repeats,
              'assignment_hash': canonical_hash(jobs), 'instrument_hash': canonical_hash(instrument),
              'stimuli_hash': canonical_hash(stimuli), 'fixture_script_hash': canonical_hash(script),
              'fixture_price': price_spec, 'actual_paid_budget_usd': 0,
              'simulated_policy': Policy(True, '1', '0', '1', 'MOCK_ONLY_NOT_OWNER_AUTHORIZATION').__dict__, 'transport': 'LOCAL_AUTHORED_FIXTURE_ONLY',
              'invalid_pre_policy': 'RECORD_AND_SKIP_POST_WITHOUT_IMPUTATION', 'max_tokens': 512}
    run = RunStore.resume(root, resume, config) if resume else RunStore(root, 'E02', config, kind='MOCK')
    try:
        for name, value in [('instrument.json', instrument), ('profiles.json', profiles), ('stimuli.json', stimuli),
                            ('assignments.json', jobs), ('fixture-script.local.json', script), ('bridge-lock.json', config)]:
            path = run.path / name
            if path.exists():
                if json.loads(path.read_text()) != value:
                    raise ValueError('frozen bridge artifact differs')
            else:
                if resume:
                    raise ValueError('resume frozen artifact missing')
                run.write(name, value)
        checkpoint = run.path / 'phase-pair-checkpoint.local.json'
        def pair_state():
            return {'schema_version': 1, 'config_sha256': canonical_hash(config),
                    'journal_sha256': sha256_file(run.path / 'phase-journal.local.sqlite'),
                    'budget_sha256': sha256_file(run.path / 'budget-ledger.local.sqlite')}
        if resume:
            if not all((run.path / name).is_file() for name in ('phase-journal.local.sqlite', 'budget-ledger.local.sqlite', 'phase-pair-checkpoint.local.json')):
                raise ExecutionBlocked('checkpoint journal or budget missing; no replay')
            if json.loads(checkpoint.read_text()) != pair_state():
                raise ExecutionBlocked('checkpoint pair changed or phase interrupted; no replay')
        journal = PhaseJournal(run.path / 'phase-journal.local.sqlite')
        # Positive limits and token prices below are SIMULATED test accounting.
        policy = Policy(**config['simulated_policy'])
        ledger = BudgetLedger(run.path / 'budget-ledger.local.sqlite', policy)
        transport = FixtureTransport(script)
        completed_calls = sum(r['status'].startswith('DONE_') for r in journal.rows())
        transport.calls = completed_calls
        router = OpenRouter(ledger, Price(**price_spec), 'FIXTURE_ONLY_NO_NETWORK', transport)
        rows = verify_journal(journal, ledger, jobs, instrument, price_spec)
        atomic_json(checkpoint, pair_state())
        phase_count = 0
        for job in jobs:
            unit = canonical_hash(job)
            for phase in ('pre', 'post'):
                if (unit, phase) in rows:
                    continue
                before = rows.get((unit, 'pre'))
                request = pre_request(job, instrument) if phase == 'pre' else post_request(job, instrument, before['result']['output'])
                journal.start(unit, phase, request)
                run.event('survey_phase_started', unit=unit, phase=phase, request_sha256=canonical_hash(request))
                if phase == 'post' and before['status'] == 'DONE_INVALID':
                    result = {'output': {'democratic_party': None, 'republican_party': None}, 'reason': 'SKIPPED_INVALID_PRE'}
                    status = 'SKIPPED_INVALID_PRE'
                else:
                    try:
                        result = router.complete(messages(request), module='E02', max_tokens=512, seed=job['pair_seed'])
                        result = redact(result)
                        ledger.record(result['receipt'], {'survey_request_hash': canonical_hash(request),
                                                         'survey_output_sha256': canonical_hash(result['output'])})
                        status = 'DONE_VALID' if score(result['output'], job['profile']['party'])['status'] == 'VALID' else 'DONE_INVALID'
                    except BaseException:
                        journal.finish(unit, phase, 'FAILED_UNCERTAIN', {'error': 'UNRESOLVED_CALL_NO_RETRY'})
                        raise
                journal.finish(unit, phase, status, result)
                run.event('survey_phase_committed', unit=unit, phase=phase, status=status,
                          simulated_receipt=result.get('receipt'), actual_spend_usd=0)
                rows = verify_journal(journal, ledger, jobs, instrument, price_spec)
                atomic_json(checkpoint, pair_state())
                phase_count += 1
                if stop_after_phases is not None and phase_count >= stop_after_phases:
                    run.event('clean_checkpoint_pause', committed_phase_count=len(rows))
                    return run.path
        responses = []
        for job in jobs:
            unit = canonical_hash(job); a = rows[(unit, 'pre')]; b = rows[(unit, 'post')]
            pre = a['result']['output']; post = b['result']['output']
            responses.append({'profile_id': job['profile']['profile_id'], 'stimulus_id': job['stimulus_id'],
                              'repeat': job['repeat'], 'arm': job['arm'], 'execution_order': job['execution_order'],
                              'pre': pre, 'post': post, 'scoring_party': job['profile']['party'],
                              'pre_request': a['request'], 'post_request': b['request'],
                              'request_hashes': [a['request_hash'], b['request_hash']],
                              'change': change(pre, post, job['profile']['party']),
                              'phase_status': {'pre': a['status'], 'post': b['status']},
                              'phase_accounting': {'pre': a['result'], 'post': b['result']}})
        analysis = evaluate(responses, seed, expected_assignments=jobs, expected_instrument=instrument)
        run.write('responses.local.json', responses); run.write('analysis.json', analysis)
        run.write('accounting.local.json', ledger.snapshot())
        run.finish({'status': 'PASS_MOCK_OPENROUTER_SURVEY_BRIDGE', 'units': len(jobs),
                    'mock_adapter_calls': len(ledger.snapshot()),
                    'skipped_post_phases': sum(r['status'] == 'SKIPPED_INVALID_PRE' for r in rows.values()),
                    'simulated_charged_microusd': sum(c['charged_microusd'] for c in ledger.snapshot()),
                    'paid_calls': 0, 'spent_usd': 0, 'network_requests': 0,
                    'analysis_scope': 'MOCK_ENGINEERING_ONLY; no live release or scientific effect',
                    'original_population_gate': 'BLOCKED'})
        return run.path
    except BaseException as error:
        if not run.finished:
            run.write('failure.json', {'status': 'FAILED', 'error_type': type(error).__name__,
                                       'cancelled': isinstance(error, (KeyboardInterrupt, SystemExit)),
                                       'retry_authorized': False})
            run.finish({'status': 'FAILED_MOCK_SURVEY_BRIDGE', 'error_type': type(error).__name__,
                        'paid_calls': 0, 'spent_usd': 0, 'network_requests': 0,
                        'reconciliation': 'INSPECT_PRIVATE_JOURNALS; NO_AUTOMATIC_RETRY'})
        raise
    finally:
        # Clean pause deliberately leaves an unsealed resumable run. The regular
        # context manager would auto-finalize it, so release ownership explicitly.
        run._release_lock()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Authored 12-profile mock bridge; no live transport or credentials')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    args = parser.parse_args()
    profiles = [{'profile_id': 'BRIDGE-DEMO-' + str(i + 1).zfill(3), 'party': ('D', 'R', 'I')[i % 3]}
                for i in range(12)]
    instrument = json.loads((args.root / 'configs/e02_instrument.json').read_text())
    stimuli = json.loads((args.root / 'configs/e02_demo_stimuli.json').read_text())
    print(run_mock_bridge(args.root, profiles, stimuli, instrument))
