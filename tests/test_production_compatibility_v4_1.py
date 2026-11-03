"""Authored executor assertions with mocked OS home/catalog/key/transport."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from civiclab.common import canonical_hash, canonical_bytes
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from civiclab.production_owner_v4 import ProductionOwnerV4
from civiclab.production_compatibility_v4_1 import (
    execution_contract, execute_compatibility, _Journal, _answer)
from civiclab.production_compatibility_transport_v4 import _CompatibilityTransportV4, _CheckedHTTPS
from test_production_admission_v4 import account, materials, initialize, approval, grant, T0
import test_openrouter_http_v2 as transport_fixture
from test_openrouter_http_v2 import Response, Opener, KEY


class Stub:
    def __init__(self, model='fixture/model-v4'):
        self.model = model; self.posts = []; self.lookups = []
        self.response = {'id': 'gen-' + uuid.uuid4().hex, 'model': model,
                         'usage': {'cost': 0.000001},
                         'choices': [{'message': {'content': '{"ok":true}'}}]}
        self.stats = {'data': {'id': self.response['id'], 'model': model,
            'provider_name': 'FixtureProvider', 'total_cost': 0.000001,
            'native_tokens_prompt': 1, 'native_tokens_completion': 1,
            'native_tokens_reasoning': 0, 'is_byok': False}}
        self.post_error = self.stats_error = None

    def post_bytes(self, body):
        self.posts.append(body)
        if self.post_error: raise self.post_error
        return deepcopy(self.response)

    def statistics(self, identity):
        self.lookups.append(identity)
        if self.stats_error: raise self.stats_error
        return deepcopy(self.stats)


def assertions():
    release, review, raw, receipt = materials('AUTHORED-COMPAT-EXEC-' + uuid.uuid4().hex)
    review['limitations_sha256'] = canonical_hash(execution_contract())
    er = {'kind': 'INDEPENDENT_COMPATIBILITY_EXECUTOR_REVIEW_V4_1', 'review_id': uuid.uuid4().hex,
          'reviewer_role': 'independent_auditor', 'contract_sha256': canonical_hash(execution_contract()),
          'foundation_review_sha256': canonical_hash(review), 'release_sha256': canonical_hash(release)}
    return release, review, er, raw, receipt


def child_execute(home, args, kw, raw, receipt, stage, counts, queue=None):
    with account(home):
        stub = Stub(); post = stub.post_bytes; stats = stub.statistics
        def counted_post(body):
            with counts.get_lock(): counts[0] += 1
            result = post(body)
            if stage == 'POST_RETURN': os._exit(91)
            return result
        def counted_stats(identity):
            with counts.get_lock(): counts[1] += 1
            result = stats(identity)
            if stage == 'STATS_RETURN': os._exit(92)
            return result
        stub.post_bytes = counted_post; stub.statistics = counted_stats
        event = _Journal.event
        def hook(journal, kind, **fields):
            event(journal, kind, **fields)
            if kind == stage: os._exit(93)
        with patch('civiclab.production_admission_v4._fetch_public_catalog', return_value=(raw, receipt)), \
             patch('civiclab.production_admission_v4._read_environment_key', return_value=_Credential('AUTHORED_FAKE_EXECUTOR_CREDENTIAL')), \
             patch('civiclab.production_compatibility_v4_1._transport', return_value=stub), \
             patch.object(_Journal, 'event', hook):
            try:
                execute_compatibility(*args, **kw)
                if queue: queue.put('COMMITTED')
            except (ExecutionBlocked, FileExistsError):
                if queue: queue.put('REFUSED')


class CompatibilityTests(unittest.TestCase):
    @contextmanager
    def case(self):
        with tempfile.TemporaryDirectory() as t:
            workspace = Path(t).resolve() / 'WORKSPACE'; home = Path(t).resolve() / 'AUTHORED_OS_HOME'
            with account(home) as now:
                r, v, er, raw, receipt = assertions(); owner = initialize(r, v)
                a = approval(owner, r, v, count=1); epoch = grant(owner, a, r, v)
                stub = Stub()
                with patch('civiclab.production_admission_v4._fetch_public_catalog', return_value=(raw, receipt)) as metadata, \
                     patch('civiclab.production_admission_v4._read_environment_key', return_value=_Credential('AUTHORED_FAKE_EXECUTOR_CREDENTIAL')) as key, \
                     patch('civiclab.production_compatibility_v4_1._transport', return_value=stub):
                    args = (workspace, r, v, a, er)
                    kwargs = {'expected_review_hash': canonical_hash(v), 'expected_approval_hash': epoch,
                              'expected_executor_review_hash': canonical_hash(er)}
                    yield args, kwargs, owner, stub, now, metadata, key

    def test_positive_exact_bytes_one_post_statistics_and_durable_owner_commit(self):
        with self.case() as (args, kw, owner, stub, now, metadata, key):
            result = execute_compatibility(*args, **kw)
            self.assertEqual(result['summary']['status'], 'COMPATIBLE')
            self.assertEqual(stub.posts, [canonical_bytes(args[1]['request']['payload'])])
            self.assertEqual(stub.lookups, [stub.response['id']])
            row = owner.snapshot()['charges'][0]
            self.assertEqual(row['status'], 'PHASE_COMMITTED')
            self.assertEqual(row['charged'], 1)
            self.assertEqual(owner.snapshot()['consumed_microusd']['dispatches'], 1)
            path = Path(result['path']); ledger = json.loads((path / 'checksums.local.json').read_text())
            self.assertIn('phase.local.json', ledger)
            self.assertTrue(all(b'AUTHORED_FAKE_EXECUTOR_CREDENTIAL' not in p.read_bytes() for p in path.iterdir()))
            with self.assertRaises((ExecutionBlocked, FileExistsError)):
                execute_compatibility(*args, **kw)
            self.assertEqual(len(stub.posts), 1); self.assertEqual(metadata.call_count, 1)

    def test_bad_outer_release_refuses_before_workspace_catalog_key_or_owner(self):
        for mode in ('contract', 'review', 'role', 'limits', 'approval', 'code'):
            with self.subTest(mode=mode), self.case() as (args, kw, owner, stub, now, metadata, key):
                args = deepcopy(args); kw = deepcopy(kw)
                if mode == 'contract': args[4]['contract_sha256'] = '0' * 64
                elif mode == 'review': kw['expected_executor_review_hash'] = '0' * 64
                elif mode == 'role': args[4]['reviewer_role'] = 'implementer'
                elif mode == 'limits': args[2]['limitations_sha256'] = '0' * 64
                elif mode == 'approval': kw['expected_approval_hash'] = '0' * 64
                elif mode == 'code': args[1]['source_pins']['CHANGED'] = '0' * 64
                with patch('civiclab.production_owner_v4.pwd.getpwuid', side_effect=AssertionError('OS home touched')):
                    with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
                self.assertFalse(args[0].exists()); metadata.assert_not_called(); key.assert_not_called()
                self.assertEqual(stub.posts, [])

    def test_invalid_answers_are_billed_committed_quality_failures_no_repair(self):
        for text in ('{"ok":1}', '{"ok":true,"extra":0}', '{"ok":false,"ok":true}', 'NaN', '[]', 'bad'):
            with self.subTest(text=text), self.case() as (args, kw, owner, stub, *rest):
                stub.response['choices'][0]['message']['content'] = text
                result = execute_compatibility(*args, **kw)
                self.assertEqual(result['summary']['status'], 'CHARGED_QUALITY_FAILURE')
                self.assertEqual(owner.snapshot()['charges'][0]['status'], 'PHASE_COMMITTED')
                self.assertEqual(len(stub.posts), 1); self.assertEqual(len(stub.lookups), 1)

    def test_bad_response_or_billing_preserves_global_barrier_and_charge(self):
        for mode in ('noid', 'model', 'provider', 'native', 'reasoning', 'byok', 'cost', 'disagree', 'wrongid', 'post', 'stats', 'cancel'):
            with self.subTest(mode=mode), self.case() as (args, kw, owner, stub, *rest):
                if mode == 'noid': stub.response['id'] = None
                elif mode == 'model': stub.response['model'] = 'wrong/model'
                elif mode == 'provider': stub.stats['data']['provider_name'] = None
                elif mode == 'native': stub.stats['data']['native_tokens_prompt'] = True
                elif mode == 'reasoning': stub.stats['data']['native_tokens_reasoning'] = 1
                elif mode == 'byok': stub.stats['data']['is_byok'] = True
                elif mode == 'cost': stub.stats['data']['total_cost'] = None
                elif mode == 'disagree': stub.stats['data']['total_cost'] = 0.000002
                elif mode == 'wrongid': stub.stats['data']['id'] = 'gen-other'
                elif mode == 'post': stub.post_error = RuntimeError('AUTHORED_FAKE_EXECUTOR_CREDENTIAL')
                elif mode == 'stats': stub.stats_error = TimeoutError()
                elif mode == 'cancel': stub.post_error = KeyboardInterrupt()
                with self.assertRaises((ExecutionBlocked, KeyboardInterrupt)):
                    execute_compatibility(*args, **kw)
                row = owner.snapshot()['charges'][0]
                self.assertEqual(row['status'], 'UNCERTAIN')
                self.assertGreaterEqual(row['charged'], row['reserved'])
                self.assertEqual(len(stub.posts), 1)
                self.assertLessEqual(len(stub.lookups), 1)
                with self.assertRaises(ExecutionBlocked): owner.reserve(row['context'])

    def test_observed_overrun_retained_immediately_without_statistics(self):
        with self.case() as (args, kw, owner, stub, *rest):
            stub.response['usage']['cost'] = 1
            with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
            row = owner.snapshot()['charges'][0]
            self.assertEqual(row['status'], 'UNCERTAIN'); self.assertEqual(row['charged'], 1_000_000)
            self.assertEqual(stub.lookups, [])

    def test_secret_body_is_neither_hashed_as_output_nor_persisted(self):
        for location in ('content', 'hidden', 'statistics'):
            with self.subTest(location=location), self.case() as (args, kw, owner, stub, *rest):
                secret = 'AUTHORED_FAKE_EXECUTOR_CREDENTIAL'
                if location == 'content': stub.response['choices'][0]['message']['content'] = secret
                elif location == 'hidden': stub.response['private_reasoning'] = secret
                else: stub.stats['data']['other'] = secret
                with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
                for p in args[0].rglob('*'):
                    if p.is_file(): self.assertNotIn(secret.encode(), p.read_bytes())
                row = owner.snapshot()['charges'][0]
                if location != 'statistics': self.assertIsNone(row['output_hash'])
                self.assertEqual(row['status'], 'UNCERTAIN')

    def test_journal_failure_before_post_keeps_reservation_without_call(self):
        original = _Journal.event
        def fail(journal, kind, **fields):
            if kind == 'MODEL_POST_INTENT': raise OSError('AUTHORED_DISK_FAILURE')
            return original(journal, kind, **fields)
        with self.case() as (args, kw, owner, stub, *rest), patch.object(_Journal, 'event', fail):
            with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
            self.assertEqual(stub.posts, [])
            self.assertEqual(owner.snapshot()['charges'][0]['status'], 'UNCERTAIN')

    def test_expiry_during_inflight_accounting_does_not_hide_billing(self):
        with self.case() as (args, kw, owner, stub, now, *rest):
            post = stub.post_bytes
            def late(body):
                value = post(body); now[0] += timedelta(days=2); return value
            stub.post_bytes = late
            result = execute_compatibility(*args, **kw)
            self.assertEqual(result['summary']['charged_microusd'], 1)
            self.assertEqual(owner.snapshot()['charges'][0]['status'], 'PHASE_COMMITTED')

    def test_quality_boolean_and_duplicate_boundary(self):
        self.assertEqual(_answer({'choices':[{'message':{'content':'{"ok":true}'}}]})['status'], 'VALID')
        for text in ('{"ok":1}', '{"ok":true,"ok":true}'):
            self.assertNotEqual(_answer({'choices':[{'message':{'content':text}}]})['status'], 'VALID')

    def test_credential_body_failure_still_retains_safe_greater_observed_charge(self):
        for location in ('response', 'statistics'):
            with self.subTest(location=location), self.case() as (args, kw, owner, stub, *rest):
                if location == 'response':
                    stub.response['usage']['cost'] = 1
                    stub.response['secret'] = 'AUTHORED_FAKE_EXECUTOR_CREDENTIAL'
                else:
                    stub.stats['data']['total_cost'] = 1
                    stub.stats['data']['secret'] = 'AUTHORED_FAKE_EXECUTOR_CREDENTIAL'
                with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
                row = owner.snapshot()['charges'][0]
                self.assertEqual(row['charged'], 1_000_000)
                self.assertEqual(row['status'], 'UNCERTAIN')

    def test_reported_usage_and_monetary_domains_cannot_silently_pass(self):
        variants = [{'prompt_tokens': True}, {'completion_tokens': 10000},
                    {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 3},
                    {'completion_tokens_details': {'reasoning_tokens': 1}},
                    {'cost': '1e999999999'}, {'cost': True}, {'cost': 'NaN'}]
        for change in variants:
            with self.subTest(change=change), self.case() as (args, kw, owner, stub, *rest):
                stub.response['usage'].update(change)
                with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
                self.assertEqual(owner.snapshot()['charges'][0]['status'], 'UNCERTAIN')
                self.assertEqual(len(stub.posts), 1)

    def test_real_process_deaths_keep_dispatch_counts_and_exact_owner_phase(self):
        stages = {'RESERVED_BEFORE_POST': ('STARTED', 0, 0), 'MODEL_POST_INTENT': ('STARTED', 0, 0),
                  'POST_RETURN': ('STARTED', 1, 0), 'RESPONSE_SEEN': ('RESPONSE_SEEN', 1, 0),
                  'STATISTICS_GET_INTENT': ('RESPONSE_SEEN', 1, 0),
                  'STATS_RETURN': ('RESPONSE_SEEN', 1, 1),
                  'PHASE_CHECKPOINT_DURABLE': ('SETTLED', 1, 1),
                  'OWNER_PHASE_COMMITTED': ('PHASE_COMMITTED', 1, 1)}
        ctx = multiprocessing.get_context('spawn')
        for stage, (status, posts, statistics) in stages.items():
            with self.subTest(stage=stage), self.case() as (args, kw, owner, stub, now, metadata, key):
                home = owner.directory.parents[3]
                raw, receipt = metadata.return_value; counts = ctx.Array('i', [0, 0])
                process = ctx.Process(target=child_execute, args=(home, args, kw, raw, receipt, stage, counts))
                process.start(); process.join(20)
                if process.is_alive(): process.kill(); process.join(); self.fail('authored child timeout')
                self.assertIn(process.exitcode, (91, 92, 93))
                row = owner.snapshot()['charges'][0]
                self.assertEqual(row['status'], status); self.assertEqual(list(counts), [posts, statistics])
                self.assertEqual(owner.snapshot()['consumed_microusd']['dispatches'], 1)
                if status != 'PHASE_COMMITTED':
                    self.assertGreaterEqual(row['charged'], row['reserved'] if status != 'SETTLED' else 1)

    def test_two_real_processes_cannot_duplicate_dispatch_with_different_output_roots(self):
        ctx = multiprocessing.get_context('spawn')
        with self.case() as (args, kw, owner, stub, now, metadata, key):
            home = owner.directory.parents[3]; raw, receipt = metadata.return_value
            counts = ctx.Array('i', [0, 0]); queue = ctx.Queue()
            args2 = (args[0].with_name('SECOND_OUTPUT'), *args[1:])
            children = [ctx.Process(target=child_execute, args=(home, a, kw, raw, receipt, None, counts, queue)) for a in (args, args2)]
            for p in children: p.start()
            for p in children:
                p.join(20)
                if p.is_alive(): p.kill(); p.join(); self.fail('authored child timeout')
                self.assertEqual(p.exitcode, 0)
            outcomes = [queue.get(timeout=2) for _ in children]
            self.assertEqual(sorted(outcomes), ['COMMITTED', 'REFUSED'])
            self.assertEqual(list(counts), [1, 1]); self.assertEqual(len(owner.snapshot()['charges']), 1)

    def test_private_transport_sends_exact_bytes_to_fixed_path_and_safe_generation(self):
        with patch('civiclab.production_compatibility_transport_v4._CheckedHTTPS') as factory:
            credential = _Credential('AUTHORED_FAKE_TRANSPORT_CREDENTIAL')
            transport = _CompatibilityTransportV4(credential)
            factory.assert_called_once_with('AUTHORED_FAKE_TRANSPORT_CREDENTIAL')
            body = b'{"authored":true}'
            transport.post_bytes(body)
            factory.return_value._request.assert_called_once_with(
                'https://openrouter.ai/api/v1/chat/completions', 'POST', body)
            transport.statistics('gen-AUTHORED')
            factory.return_value.stats.assert_called_once_with('gen-AUTHORED')
            self.assertNotIn('AUTHORED_FAKE_TRANSPORT_CREDENTIAL', repr(transport))
            for bad in (None, {}, b'', b'x' * 262145):
                with self.assertRaises(ExecutionBlocked): transport.post_bytes(bad)
            for bad in ('../../x', 'gen-x?content=true', 'http://other', None):
                with self.assertRaises(ExecutionBlocked): transport.statistics(bad)
            self.assertEqual(factory.return_value._request.call_count, 1)
            self.assertEqual(factory.return_value.stats.call_count, 1)

    def test_rollback_or_unavailable_clock_after_post_still_commits_known_billing(self):
        for value in (T0 - timedelta(seconds=1), RuntimeError('AUTHORED_CLOCK_UNAVAILABLE')):
            with self.subTest(clock=type(value).__name__), self.case() as (args, kw, owner, stub, now, *rest):
                post = stub.post_bytes
                def late(body):
                    response = post(body); now[0] = value; return response
                stub.post_bytes = late
                result = execute_compatibility(*args, **kw)
                self.assertEqual(result['summary']['charged_microusd'], 1)
                self.assertEqual(owner.snapshot()['charges'][0]['status'], 'PHASE_COMMITTED')
                self.assertEqual(len(stub.lookups), 1)

    def test_owner_commit_survives_lost_final_ack_and_readonly_error_logging(self):
        write = _Journal.write
        lost = [False]
        def uncertain(journal, name, value):
            if lost[0]: raise OSError('AUTHORED_READONLY')
            result = write(journal, name, value)
            if name == 'checksums':
                lost[0] = True
                raise OSError('AUTHORED_LOST_ACK')
            return result
        with self.case() as (args, kw, owner, stub, *rest), patch.object(_Journal, 'write', uncertain):
            with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
            row = owner.snapshot()['charges'][0]
            self.assertEqual(row['status'], 'PHASE_COMMITTED')
            path = args[0] / 'data/processed/compatibility_runs' / args[1]['request']['run_id']
            self.assertTrue((path / 'checksums.local.json').is_file())
            self.assertEqual(json.loads((path / 'summary.local.json').read_text())['status'], 'COMPATIBLE')
            self.assertEqual(len(stub.posts), 1)

    def test_every_present_auxiliary_counter_requires_builtin_integer_zero(self):
        fields = ('native_tokens_completion_images', 'num_media_prompt', 'num_media_completion',
                  'num_input_audio_prompt', 'num_search_results', 'num_fetches')
        for field in fields:
            for value in (1, -1, False, None, '0', 0.0, {}):
                with self.subTest(field=field, value=value), self.case() as (args, kw, owner, stub, *rest):
                    stub.stats['data'][field] = value
                    with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
                    row = owner.snapshot()['charges'][0]
                    self.assertEqual(row['status'], 'UNCERTAIN')
                    self.assertGreaterEqual(row['charged'], row['reserved'])
                    self.assertEqual(row['observed_cost'], 1)
                    self.assertEqual(len(stub.posts), 1); self.assertEqual(len(stub.lookups), 1)
                    with self.assertRaises(ExecutionBlocked): owner.reserve(row['context'])

    def test_non_null_engine_tier_and_unexpected_stream_or_cancellation_refuse(self):
        for field, values in (('web_search_engine', ('engine', '', False, 0)),
                              ('service_tier', ('priority', 'standard', '', False)),
                              ('streamed', (True, None, 0, 'false')),
                              ('cancelled', (True, None, 0, 'false'))):
            for value in values:
                with self.subTest(field=field, value=value), self.case() as (args, kw, owner, stub, *rest):
                    stub.stats['data'][field] = value
                    with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
                    self.assertEqual(owner.snapshot()['charges'][0]['status'], 'UNCERTAIN')
                    self.assertEqual(len(stub.posts), 1); self.assertEqual(len(stub.lookups), 1)

    def test_observed_zero_and_absence_have_distinct_retained_observation_status(self):
        fields = ('native_tokens_completion_images', 'num_media_prompt', 'num_media_completion',
                  'num_input_audio_prompt', 'num_search_results', 'num_fetches')
        for reported in (True, False):
            with self.subTest(reported=reported), self.case() as (args, kw, owner, stub, *rest):
                if reported:
                    stub.stats['data'].update({f: 0 for f in fields})
                    stub.stats['data'].update(web_search_engine=None, service_tier=None, streamed=False, cancelled=False)
                result = execute_compatibility(*args, **kw)
                observation = json.loads((Path(result['path']) / 'auxiliary-observation.local.json').read_text())
                for field in fields:
                    self.assertEqual(observation['fields'][field]['status'], 'OBSERVED_ZERO' if reported else 'NOT_REPORTED')
                    self.assertEqual('value' in observation['fields'][field], reported)
                self.assertEqual(result['summary']['status'], 'COMPATIBLE')

    def test_auxiliary_refusal_keeps_greater_known_charge_and_sanitizes_engine_value(self):
        with self.case() as (args, kw, owner, stub, *rest):
            stub.response['usage'].pop('cost')
            stub.stats['data'].update(total_cost=0.000002, num_search_results=1,
                                      web_search_engine='UNTRUSTED_PRIVATE_ENGINE_VALUE')
            with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kw)
            row = owner.snapshot()['charges'][0]
            self.assertEqual(row['observed_cost'], 2); self.assertGreaterEqual(row['charged'], 2)
            self.assertEqual(row['status'], 'UNCERTAIN')
            for p in args[0].rglob('*'):
                if p.is_file(): self.assertNotIn(b'UNTRUSTED_PRIVATE_ENGINE_VALUE', p.read_bytes())


class CompatibilityTransportTests(transport_fixture.TransportTests):
    """Run the original framing/JSON/fixed-route oracles on the new wrapper."""
    def make(self, response=None, error=None):
        client = _CheckedHTTPS(KEY); opener = Opener(response, error); client._opener = opener
        return client, opener

    def test_observed_response_close_error_refuses_success_without_retry(self):
        class CloseFailure(Response):
            def close(self):
                already_closed = self.closed
                super().close()
                if not already_closed: raise OSError(KEY)
        response = CloseFailure(); client, opener = self.make(response)
        with self.assertRaises(ExecutionBlocked) as caught: client.post({})
        self.assertNotIn(KEY, str(caught.exception))
        self.assertEqual(len(opener.calls), 1); self.assertTrue(response.closed)
