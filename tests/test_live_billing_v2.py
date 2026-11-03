"""Owner-wide reservation/reconciliation tests: authored data, no network/key."""
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from civiclab.common import atomic_json, canonical_hash, sha256_file
from civiclab.live_billing_v2 import GlobalFixtureLedger, create_live_client, fixture_policy
from civiclab.model import ExecutionBlocked
from civiclab.reconciled_client_v2 import FixtureHTTP, ReconciledFixtureClient, fixture_terms

MESSAGES = [{'role': 'user', 'content': 'Authored fictional survey only'}]


def checkpoint(directory, result):
    p = Path(directory) / ('phase-' + result['receipt'] + '.local.json')
    c = result['context']
    atomic_json(p, {'schema_version': 1, **{k: c[k] for k in ('run_id', 'unit_id', 'phase')},
                    'receipt': result['receipt'], 'request_hash': c['envelope']['request_hash'],
                    'output': result['answer']})
    return p


def race_child(directory, policy, output):
    ledger = GlobalFixtureLedger.open(directory, policy); terms = fixture_terms()
    transport = FixtureHTTP(terms); client = ReconciledFixtureClient(ledger, terms, transport)
    try:
        client.complete(MESSAGES, run_id='race-' + str(os.getpid()), unit_id='unit', phase='pre')
        output.put('RESERVED_AND_SETTLED')
    except ExecutionBlocked: output.put('BLOCKED')


def crash_child(directory, policy, stage):
    ledger = GlobalFixtureLedger.open(directory, policy); terms = fixture_terms()
    client = ReconciledFixtureClient(ledger, terms, FixtureHTTP(terms))
    if stage == 'ANCHOR':
        with patch('civiclab.live_billing_v2.atomic_json', side_effect=lambda *_: os._exit(74)):
            client.complete(MESSAGES, run_id='crash', unit_id='unit', phase='pre')
    elif stage == 'STATS':
        with patch.object(FixtureHTTP, 'stats', side_effect=lambda *_: os._exit(73)):
            client.complete(MESSAGES, run_id='crash', unit_id='unit', phase='pre')
    elif stage == 'POST':
        with patch.object(FixtureHTTP, 'post', side_effect=lambda *_: os._exit(71)):
            client.complete(MESSAGES, run_id='crash', unit_id='unit', phase='pre')
    else:
        original = GlobalFixtureLedger.transition
        def die(self, receipt, status, **fields):
            row = original(self, receipt, status, **fields)
            if status == 'SETTLED': os._exit(72)
            return row
        with patch.object(GlobalFixtureLedger, 'transition', die):
            client.complete(MESSAGES, run_id='crash', unit_id='unit', phase='pre')


class LiveBillingV2Tests(unittest.TestCase):
    def make(self, directory, policy=None, *, content=None, overrides=None):
        ledger = GlobalFixtureLedger.create(directory, policy)
        terms = fixture_terms(); transport = FixtureHTTP(terms, content=content, overrides=overrides)
        return ledger, ReconciledFixtureClient(ledger, terms, transport), transport

    def test_reservation_precedes_post_and_billing_is_not_phase_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, client, transport = self.make(tmp)
            original = FixtureHTTP.post
            def observe(self, payload):
                row = ledger.snapshot()[0]
                self_test.assertEqual(row['status'], 'STARTED')
                self_test.assertEqual(row['context']['payload_hash'], canonical_hash(payload))
                self_test.assertEqual(row['context']['sampling']['seed'], 123)
                return original(self, payload)
            self_test = self
            with patch.object(FixtureHTTP, 'post', observe):
                result = client.complete(MESSAGES, run_id='run', unit_id='u', phase='pre', seed=123)
            self.assertEqual(len(transport.calls), 2)
            self.assertEqual(ledger.snapshot()[0]['status'], 'SETTLED')
            before = len(transport.calls)
            with self.assertRaises(ExecutionBlocked): client.complete(MESSAGES, run_id='other', unit_id='u', phase='pre')
            self.assertEqual(len(transport.calls), before)
            ledger.commit_phase(result['receipt'], checkpoint(tmp, result))
            self.assertEqual(ledger.snapshot()[0]['status'], 'PHASE_COMMITTED')
            self.assertEqual(ledger.snapshot()[0]['charged'], 2)

    def test_new_run_directory_module_and_reopen_do_not_renew_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = fixture_policy(total=2000, e01=2000, e02=2000)
            ledger, client, transport = self.make(Path(tmp) / 'owner', policy)
            result = client.complete(MESSAGES, run_id='first', unit_id='u', phase='pre')
            ledger.commit_phase(result['receipt'], checkpoint(Path(tmp), result))
            # The second request would fit an empty ledger, but not remaining cap.
            amount = result['context']['envelope']['reserved_microusd']
            policy_limit = amount + 1
            # Use a separate exact-bound fixture to make this assertion independent
            # of message serialization length or a hard-coded reservation estimate.
        with tempfile.TemporaryDirectory() as tmp:
            policy = fixture_policy(total=policy_limit, e01=policy_limit, e02=policy_limit)
            ledger, client, transport = self.make(Path(tmp) / 'owner', policy)
            result = client.complete(MESSAGES, run_id='first', unit_id='u', phase='pre')
            ledger.commit_phase(result['receipt'], checkpoint(tmp, result))
            ledger = GlobalFixtureLedger.open(Path(tmp) / 'owner', policy)
            second_http = FixtureHTTP(); second = ReconciledFixtureClient(ledger, fixture_terms(), second_http)
            (Path(tmp) / 'new-output-directory').mkdir()
            with self.assertRaises(ExecutionBlocked): second.complete(MESSAGES, run_id='second', unit_id='new', phase='forecast', module='E01')
            self.assertEqual(second_http.calls, [])
            self.assertEqual(len(ledger.snapshot()), 1)

    def test_missing_state_and_changed_policy_cannot_bootstrap_or_refund(self):
        for mode in ('database', 'anchor', 'policy'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                ledger, client, _ = self.make(tmp)
                result = client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
                policy = fixture_policy()
                if mode == 'database': ledger.db_path.rename(ledger.db_path.with_suffix('.preserved'))
                elif mode == 'anchor': ledger.anchor.rename(ledger.anchor.with_suffix('.preserved'))
                else: policy['total_microusd'] += 1
                with self.assertRaises((ExecutionBlocked, ValueError)): GlobalFixtureLedger.open(tmp, policy)
                with self.assertRaises((ExecutionBlocked, FileExistsError)): GlobalFixtureLedger.create(tmp)

    def test_phase_key_deduplicates_changed_seed_request_and_route_terms(self):
        for mode in ('seed', 'request', 'terms'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                ledger, client, transport = self.make(tmp)
                result = client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
                ledger.commit_phase(result['receipt'], checkpoint(tmp, result))
                messages = deepcopy(MESSAGES); seed = 0
                if mode == 'seed': seed = 1
                elif mode == 'request': messages[0]['content'] += ' changed'
                else: client.terms['input_usd_per_token'] = '0.000002'
                before = len(transport.calls)
                with self.assertRaises(ExecutionBlocked): client.complete(messages, run_id='r', unit_id='u', phase='pre', seed=seed)
                self.assertEqual(len(transport.calls), before)

    def test_null_wrong_identity_native_usage_and_fee_disagreement_hold_global_charge(self):
        cases = [({'provider_name': None}, {}), ({'provider_name': 'Unapproved'}, {}),
                 ({'model': 'wrong'}, {}), ({'id': 'gen-other'}, {}), ({'is_byok': True}, {}),
                 ({'native_tokens_prompt': None}, {}), ({'native_tokens_completion': 513}, {}),
                 ({'native_tokens_reasoning': 1}, {}), ({'total_cost': '0.001'}, {})]
        for stats, response in cases:
            with self.subTest(stats=stats), tempfile.TemporaryDirectory() as tmp:
                ledger, client, transport = self.make(tmp, overrides={'stats': stats, 'response': response})
                with self.assertRaises(ExecutionBlocked): client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
                row = ledger.snapshot()[0]
                self.assertIn(row['status'], ('UNCERTAIN', 'OVERRUN'))
                self.assertGreaterEqual(row['charged'], row['reserved'])
                before = len(transport.calls)
                with self.assertRaises(ExecutionBlocked): client.complete(MESSAGES, run_id='different', unit_id='x', phase='pre')
                self.assertEqual(len(transport.calls), before)

    def test_stats_timeout_post_timeout_and_cancellation_have_no_retry_or_refund(self):
        for method, error in (('post', TimeoutError), ('stats', TimeoutError), ('stats', KeyboardInterrupt)):
            with self.subTest(method=method, error=error), tempfile.TemporaryDirectory() as tmp:
                ledger, client, transport = self.make(tmp)
                with patch.object(FixtureHTTP, method, side_effect=error('PRIVATE_ERROR_MARKER')) as called:
                    with self.assertRaises(KeyboardInterrupt if error is KeyboardInterrupt else ExecutionBlocked):
                        client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
                    self.assertEqual(called.call_count, 1)
                row = ledger.snapshot()[0]
                self.assertEqual(row['status'], 'UNCERTAIN'); self.assertEqual(row['charged'], row['reserved'])
                self.assertNotIn('PRIVATE_ERROR_MARKER', json.dumps(row))

    def test_observed_overrun_is_preserved_and_globally_halts(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, client, transport = self.make(tmp, overrides={'response': {'usage': {'cost': '2'}}})
            with self.assertRaises(ExecutionBlocked): client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
            row = ledger.snapshot()[0]
            self.assertEqual(row['status'], 'OVERRUN'); self.assertEqual(row['charged'], 2_000_000)
            self.assertEqual(len(transport.calls), 1)

    def test_invalid_answers_are_billed_recorded_and_do_not_trigger_repair(self):
        for content, status in (('not json', 'INVALID_JSON'), ('[]', 'NON_OBJECT_JSON'), (None, 'PARSED_OBJECT')):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                ledger, client, transport = self.make(tmp, content=content)
                result = client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
                self.assertEqual(result['answer']['status'], status)
                self.assertEqual(ledger.snapshot()[0]['status'], 'SETTLED')
                self.assertEqual(len(transport.calls), 2)
                ledger.commit_phase(result['receipt'], checkpoint(tmp, result))


    def test_refusal_is_a_quality_event_not_unknown_billing(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, client, transport = self.make(tmp, overrides={'response': {'choices': [{'message': {'content': None, 'refusal': 'authored refusal'}}]}})
            result = client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
            self.assertEqual(result['answer']['status'], 'MISSING_OR_REFUSAL')
            self.assertIsNone(result['answer']['parsed'])
            self.assertEqual(ledger.snapshot()[0]['status'], 'SETTLED')
            self.assertEqual(len(transport.calls), 2)
            ledger.commit_phase(result['receipt'], checkpoint(tmp, result))

    def test_generation_metadata_and_private_reasoning_are_not_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, client, _ = self.make(tmp, overrides={'stats': {'external_user': 'PRIVATE_MARKER', 'user_agent': 'PRIVATE_MARKER', 'reasoning': 'PRIVATE_MARKER'},
                                                        'response': {'reasoning': 'PRIVATE_MARKER'}})
            result = client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
            self.assertNotIn('PRIVATE_MARKER', json.dumps(result))
            self.assertNotIn('PRIVATE_MARKER', json.dumps(ledger.snapshot()))

    def test_counter_tamper_and_torn_anchor_block_without_another_call(self):
        for mode in ('counter', 'anchor_failure'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                ledger, client, transport = self.make(tmp)
                if mode == 'anchor_failure':
                    with patch('civiclab.live_billing_v2.atomic_json', side_effect=OSError('PRIVATE_MARKER')):
                        with self.assertRaises(OSError): client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
                    self.assertEqual(transport.calls, [])
                else:
                    result = client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
                    with sqlite3.connect(ledger.db_path) as db:
                        text = db.execute('SELECT data FROM charges').fetchone()[0]; row = json.loads(text)
                        row['charged'] = 0; db.execute('UPDATE charges SET data=?', (json.dumps(row),))
                before = len(transport.calls)
                with self.assertRaises((ExecutionBlocked, ValueError)): client.complete(MESSAGES, run_id='other', unit_id='x', phase='pre')
                self.assertEqual(len(transport.calls), before)

    def test_checkpoint_bound_to_exact_receipt_output_and_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, client, _ = self.make(tmp)
            result = client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
            p = checkpoint(tmp, result); value = json.loads(p.read_text()); value['unit_id'] = 'other'; atomic_json(p, value)
            with self.assertRaises(ValueError): ledger.commit_phase(result['receipt'], p)
            with self.assertRaises(ExecutionBlocked): ledger.transition(result['receipt'], 'PHASE_COMMITTED', checkpoint_hash='a' * 64)
            self.assertEqual(ledger.snapshot()[0]['status'], 'SETTLED')
            ledger.commit_phase(result['receipt'], checkpoint(tmp, result))

    def test_actual_process_death_before_post_and_after_settlement_blocks_replay(self):
        for stage in ('POST', 'STATS', 'SETTLED', 'ANCHOR'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                ledger = GlobalFixtureLedger.create(tmp); policy = fixture_policy()
                process = multiprocessing.get_context('spawn').Process(target=crash_child, args=(tmp, policy, stage))
                process.start(); process.join(20)
                if process.is_alive(): process.kill(); process.join(); self.fail('crash child did not terminate')
                self.assertEqual(process.exitcode, {'POST': 71, 'SETTLED': 72, 'STATS': 73, 'ANCHOR': 74}[stage])
                if stage == 'ANCHOR':
                    with self.assertRaises(ExecutionBlocked): GlobalFixtureLedger.open(tmp, policy)
                    with sqlite3.connect(ledger.db_path) as db:
                        row = json.loads(db.execute('SELECT data FROM charges').fetchone()[0])
                        self.assertEqual(row['charged'], row['reserved'])
                    continue
                ledger = GlobalFixtureLedger.open(tmp, policy); transport = FixtureHTTP()
                client = ReconciledFixtureClient(ledger, fixture_terms(), transport)
                with self.assertRaises(ExecutionBlocked): client.complete(MESSAGES, run_id='other', unit_id='x', phase='pre')
                self.assertEqual(transport.calls, []); self.assertEqual(len(ledger.snapshot()), 1)

    def test_two_process_reservation_race_has_one_winner(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = GlobalFixtureLedger.create(tmp); ctx = multiprocessing.get_context('spawn'); output = ctx.Queue()
            workers = [ctx.Process(target=race_child, args=(tmp, fixture_policy(), output)) for _ in range(2)]
            for p in workers: p.start()
            for p in workers:
                p.join(20)
                if p.is_alive(): p.kill(); p.join(); self.fail('race worker did not terminate')
                self.assertEqual(p.exitcode, 0)
            self.assertEqual(sorted(output.get(timeout=2) for _ in workers), ['BLOCKED', 'RESERVED_AND_SETTLED'])
            self.assertEqual(len(ledger.snapshot()), 1)


    def test_nullable_chat_cost_uses_authoritative_stats_and_foreign_generation_cost_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger, client, transport = self.make(tmp, overrides={'response': {'usage': {'cost': None}}})
            result = client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
            self.assertEqual(result['charged_microusd'], 2)
            self.assertEqual(len(transport.calls), 2)
        with tempfile.TemporaryDirectory() as tmp:
            ledger, client, transport = self.make(tmp, overrides={'stats': {'id': 'gen-FOREIGN', 'total_cost': 99}})
            with self.assertRaises(ExecutionBlocked): client.complete(MESSAGES, run_id='r', unit_id='u', phase='pre')
            row = ledger.snapshot()[0]
            self.assertEqual(row['observed_cost'], 2)
            self.assertEqual(row['charged'], row['reserved'])

    def test_live_factory_never_loads_keys_or_opens_network(self):
        with patch('socket.create_connection', side_effect=AssertionError('network forbidden')):
            with self.assertRaises(ExecutionBlocked): create_live_client()
