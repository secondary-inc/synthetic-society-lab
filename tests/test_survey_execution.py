"""Integrated adapter/phase tests: authored data, fake billing, no network."""
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from civiclab.common import canonical_hash, sha256_file
from civiclab.dashboard import verified_run
from civiclab.model import BudgetLedger, ExecutionBlocked
from civiclab.reproduction import build_package
from civiclab.survey_execution import FixtureTransport, PhaseJournal, run_mock_bridge, run_live_bridge

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = json.loads((ROOT / 'configs/e02_instrument.json').read_text())
STIMULI = json.loads((ROOT / 'configs/e02_demo_stimuli.json').read_text())
PROFILES = [{'profile_id': 'FICT-' + str(i), 'party': ('D', 'R', 'I')[i % 3]} for i in range(3)]


def crash_after_adapter_success(root):
    from civiclab import survey_execution as execution
    original = execution.PhaseJournal.finish
    def crash(self, unit, phase, status, result):
        if status == 'DONE_VALID':
            os._exit(71)
        return original(self, unit, phase, status, result)
    with patch.object(execution.PhaseJournal, 'finish', crash):
        execution.run_mock_bridge(root, PROFILES, STIMULI[:1], INSTRUMENT)


class SurveyBridgeTests(unittest.TestCase):
    def test_full_crossed_mock_through_adapter_and_independent_rescore(self):
        with tempfile.TemporaryDirectory() as tmp, patch('socket.create_connection', side_effect=AssertionError('network forbidden')):
            path = run_mock_bridge(tmp, PROFILES, STIMULI, INSTRUMENT)
            run = verified_run(path)
            self.assertEqual(run['summary']['mock_adapter_calls'], 90)
            self.assertEqual(run['summary']['paid_calls'], 0)
            self.assertEqual(run['summary']['spent_usd'], 0)
            analysis = json.loads((path / 'analysis.json').read_text())
            self.assertEqual(analysis['estimate_thermometer_points'], 2)
            self.assertEqual(analysis['responses'], 45)
            responses = json.loads((path / 'responses.local.json').read_text())
            for row in responses:
                self.assertIsNone(row['pre_request']['exposure'])
                self.assertEqual(row['post_request']['pre_response'], row['pre'])
                self.assertEqual(row['request_hashes'], [canonical_hash(row['pre_request']), canonical_hash(row['post_request'])])
            with self.assertRaisesRegex(ValueError, 'local-only'):
                build_package(Path(tmp), Path(tmp) / 'refused.zip', [path.name])

    def test_invalid_pre_skips_own_post_and_keeps_complete_assignment_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT,
                                   script={'answers': {'1': {'democratic_party': None, 'republican_party': 50}}})
            summary = verified_run(path)['summary']
            self.assertEqual(summary['units'], 15)
            self.assertEqual(summary['mock_adapter_calls'], 29)
            self.assertEqual(summary['skipped_post_phases'], 1)
            responses = json.loads((path / 'responses.local.json').read_text())
            row = next(r for r in responses if r['phase_status']['post'] == 'SKIPPED_INVALID_PRE')
            self.assertEqual(row['change']['status'], 'INVALID_PAIR')
            self.assertEqual(row['post'], {'democratic_party': None, 'republican_party': None})
            self.assertEqual(len(responses), 15)

    def test_invalid_post_no_repair_or_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT,
                                   script={'answers': {'2': {'democratic_party': 101, 'republican_party': False}}})
            run = verified_run(path)
            self.assertEqual(run['summary']['mock_adapter_calls'], 30)
            self.assertEqual(run['summary']['skipped_post_phases'], 0)
            first = min(json.loads((path / 'responses.local.json').read_text()), key=lambda r: r['execution_order'])
            self.assertEqual(first['phase_status']['post'], 'DONE_INVALID')

    def test_clean_pre_phase_pause_resume_reuses_exact_baseline_and_charge(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, stop_after_phases=1)
            self.assertFalse((path / 'checksums.json').exists())
            before = BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()
            self.assertEqual(len(before), 1)
            run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, resume=path)
            after = BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()
            self.assertEqual(len(after), 30)
            self.assertIn(before[0]['id'], {r['id'] for r in after})
            self.assertEqual(verified_run(path)['summary']['mock_adapter_calls'], 30)

    def test_changed_inputs_and_instrument_refuse_resume_without_dispatch(self):
        for which in ('profiles', 'instrument', 'stimuli'):
            with self.subTest(which=which), tempfile.TemporaryDirectory() as tmp:
                path = run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, stop_after_phases=1)
                profiles, stimuli, instrument = deepcopy(PROFILES), deepcopy(STIMULI[:1]), deepcopy(INSTRUMENT)
                if which == 'profiles': profiles[0]['party'] = 'R'
                elif which == 'instrument': instrument['instructions'] += ' changed'
                else: stimuli[0]['text'] += ' changed'
                before = sha256_file(path / 'budget-ledger.local.sqlite')
                with patch.object(FixtureTransport, '__call__', side_effect=AssertionError('must not dispatch')):
                    with self.assertRaises(ValueError): run_mock_bridge(tmp, profiles, stimuli, instrument, resume=path)
                self.assertEqual(before, sha256_file(path / 'budget-ledger.local.sqlite'))

    def test_checkpoint_output_request_or_deleted_phase_cannot_be_reused(self):
        for mode in ('output', 'request', 'deleted'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                path = run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, stop_after_phases=1)
                with sqlite3.connect(path / 'phase-journal.local.sqlite') as db:
                    if mode == 'deleted': db.execute('DELETE FROM phases')
                    elif mode == 'request': db.execute("UPDATE phases SET request='{}'")
                    else:
                        result = json.loads(db.execute('SELECT result FROM phases').fetchone()[0])
                        result['output']['democratic_party'] = 0
                        db.execute('UPDATE phases SET result=?', (json.dumps(result),))
                checkpoint = json.loads((path / 'phase-pair-checkpoint.local.json').read_text())
                checkpoint['journal_sha256'] = sha256_file(path / 'phase-journal.local.sqlite')
                (path / 'phase-pair-checkpoint.local.json').write_text(json.dumps(checkpoint))
                with patch.object(FixtureTransport, '__call__', side_effect=AssertionError('must not dispatch')):
                    with self.assertRaises((ValueError, ExecutionBlocked)):
                        run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, resume=path)
                self.assertEqual(verified_run(path)['summary']['status'], 'FAILED_MOCK_SURVEY_BRIDGE')

    def test_actual_abrupt_death_after_charge_before_checkpoint_never_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = multiprocessing.get_context('spawn')
            process = context.Process(target=crash_after_adapter_success, args=(tmp,))
            process.start(); process.join(15)
            if process.is_alive(): process.kill(); process.join(); self.fail('child failed to exit')
            self.assertEqual(process.exitcode, 71)
            path = next((Path(tmp) / 'data/processed/runs').iterdir())
            self.assertEqual(PhaseJournal(path / 'phase-journal.local.sqlite').rows()[0]['status'], 'STARTED')
            self.assertEqual(len(BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()), 1)
            with patch.object(FixtureTransport, '__call__', side_effect=AssertionError('must not dispatch')):
                with self.assertRaises(ExecutionBlocked): run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, resume=path)
            self.assertEqual(len(BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()), 1)

    def test_existing_run_owner_blocks_concurrent_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, stop_after_phases=1)
            import fcntl
            with (path / '.lock').open('a') as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(RuntimeError, 'owned'):
                    run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, resume=path)
            self.assertEqual(len(BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()), 1)

    def test_timeout_and_cancellation_conservatively_charge_and_seal_failure(self):
        for script, error in (({'fail_at': 1}, ExecutionBlocked), ({'cancel_at': 1}, KeyboardInterrupt)):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(error): run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, script=script)
                path = next((Path(tmp) / 'data/processed/runs').iterdir())
                charges = BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()
                self.assertEqual(len(charges), 1)
                self.assertEqual(charges[0]['status'], 'UNCERTAIN')
                self.assertEqual(charges[0]['charged_microusd'], charges[0]['reserved_microusd'])
                self.assertEqual(verified_run(path)['summary']['status'], 'FAILED_MOCK_SURVEY_BRIDGE')
                self.assertNotIn('authored transport timeout', (path / 'failure.json').read_text())


    def test_routing_unknown_billing_and_overrun_are_not_retried(self):
        original = FixtureTransport.__call__
        for mode in ('provider', 'unknown_cost', 'overrun'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                def altered(self, payload, key):
                    result = original(self, payload, key)
                    if mode == 'provider': result['provider'] = 'UNAPPROVED_FIXTURE_ROUTE'
                    elif mode == 'unknown_cost': del result['usage']['cost']
                    else: result['usage']['cost'] = '2'
                    return result
                with patch.object(FixtureTransport, '__call__', altered):
                    with self.assertRaises(ExecutionBlocked):
                        run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT)
                path = next((Path(tmp) / 'data/processed/runs').iterdir())
                charges = BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()
                self.assertEqual(len(charges), 1)
                self.assertIn(charges[0]['status'], ('UNCERTAIN', 'OVERRUN'))
                self.assertGreaterEqual(charges[0]['charged_microusd'], charges[0]['reserved_microusd'])
                self.assertEqual(verified_run(path)['summary']['status'], 'FAILED_MOCK_SURVEY_BRIDGE')

    def test_changed_code_and_duplicate_assignments_fail_before_new_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = run_mock_bridge(root, PROFILES, STIMULI[:1], INSTRUMENT, stop_after_phases=1)
            (root / 'src').mkdir()
            (root / 'src/changed.py').write_text('changed = True\n')
            with patch.object(FixtureTransport, '__call__', side_effect=AssertionError('must not dispatch')):
                with self.assertRaises(ValueError):
                    run_mock_bridge(root, PROFILES, STIMULI[:1], INSTRUMENT, resume=path)
                with self.assertRaises(ValueError):
                    run_mock_bridge(root, PROFILES + [PROFILES[0]], STIMULI[:1], INSTRUMENT)
            self.assertEqual(len(BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()), 1)


    def test_missing_pair_database_and_coedited_manifest_price_do_not_reset_accounting(self):
        for mode in ('missing_budget', 'changed_price'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                path = run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, stop_after_phases=1)
                if mode == 'missing_budget':
                    # Preserve the bytes elsewhere; refusal must not create a replacement ledger.
                    (path / 'budget-ledger.local.sqlite').rename(path / 'preserved-budget.local.sqlite')
                else:
                    manifest = json.loads((path / 'manifest.json').read_text())
                    manifest['config']['fixture_price']['input_usd_per_token'] = '0.000002'
                    (path / 'manifest.json').write_text(json.dumps(manifest))
                with patch.object(FixtureTransport, '__call__', side_effect=AssertionError('must not dispatch')):
                    with self.assertRaises((ValueError, ExecutionBlocked)):
                        run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, resume=path)
                if mode == 'missing_budget':
                    self.assertFalse((path / 'budget-ledger.local.sqlite').exists())

    def test_outside_resume_and_raw_profile_fields_are_rejected_before_io(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            with patch.object(FixtureTransport, '__call__', side_effect=AssertionError('must not dispatch')):
                with self.assertRaisesRegex(ValueError, 'outside'):
                    run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, resume=other)
                profiles = deepcopy(PROFILES); profiles[0]['respondent_name'] = 'PRIVATE_TEST_MARKER'
                with self.assertRaises(ValueError):
                    run_mock_bridge(tmp, profiles, STIMULI[:1], INSTRUMENT)
            self.assertFalse((Path(tmp) / 'data').exists())


    def test_coedited_routes_seeds_and_reservations_refuse_before_any_transport(self):
        modes = ('provider', 'model', 'seed', 'temperature', 'retries', 'input_bound',
                 'zero_reservation', 'charged_above_reservation', 'prompt_boolean', 'output_tokens')
        for mode in modes:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                path = run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, stop_after_phases=1)
                with sqlite3.connect(path / 'phase-journal.local.sqlite') as db:
                    unit, phase, text = db.execute('SELECT unit,phase,result FROM phases').fetchone()
                    result = json.loads(text)
                    receipt = result['receipt']
                    with sqlite3.connect(path / 'budget-ledger.local.sqlite') as budget:
                        metadata = json.loads(budget.execute('SELECT data FROM metadata WHERE id=?', (receipt,)).fetchone()[0])
                        if mode == 'provider':
                            result['provider'] = metadata['actual_provider'] = 'UNAPPROVED'
                        elif mode == 'model':
                            result['model'] = metadata['actual_model'] = 'unapproved/model'
                        elif mode == 'seed': metadata['seed'] += 1
                        elif mode == 'temperature': metadata['temperature'] = 1
                        elif mode == 'retries': metadata['retries'] = 1
                        elif mode == 'input_bound': metadata['input_token_bound'] += 1
                        elif mode == 'zero_reservation': budget.execute('UPDATE charges SET reserved=0')
                        elif mode == 'charged_above_reservation': budget.execute('UPDATE charges SET charged=reserved+1')
                        elif mode == 'prompt_boolean':
                            result['usage']['prompt_tokens'] = True
                            metadata['usage']['prompt_tokens'] = True
                        else:
                            result['usage']['completion_tokens'] = 513
                            metadata['usage']['completion_tokens'] = 513
                        budget.execute('UPDATE metadata SET data=? WHERE id=?', (json.dumps(metadata), receipt))
                    db.execute('UPDATE phases SET result=? WHERE unit=? AND phase=?', (json.dumps(result), unit, phase))
                checkpoint = json.loads((path / 'phase-pair-checkpoint.local.json').read_text())
                checkpoint.update(journal_sha256=sha256_file(path / 'phase-journal.local.sqlite'),
                                  budget_sha256=sha256_file(path / 'budget-ledger.local.sqlite'))
                (path / 'phase-pair-checkpoint.local.json').write_text(json.dumps(checkpoint))
                with patch.object(FixtureTransport, '__call__') as transport:
                    with self.assertRaises((ValueError, ExecutionBlocked)):
                        run_mock_bridge(tmp, PROFILES, STIMULI[:1], INSTRUMENT, resume=path)
                    self.assertEqual(transport.call_count, 0)
                self.assertEqual(len(BudgetLedger(path / 'budget-ledger.local.sqlite').snapshot()), 1)

    def test_live_dispatch_and_non_demo_inputs_block_without_transport_or_credentials(self):
        with tempfile.TemporaryDirectory() as tmp, patch('civiclab.model.network_transport', side_effect=AssertionError('network forbidden')):
            with self.assertRaises(ExecutionBlocked): run_live_bridge(tmp)
            stimuli = deepcopy(STIMULI[:1]); stimuli[0]['kind'] = 'OFFICIAL'
            with self.assertRaises(ValueError): run_mock_bridge(tmp, PROFILES, stimuli, INSTRUMENT)
            self.assertFalse((Path(tmp) / 'data').exists())
