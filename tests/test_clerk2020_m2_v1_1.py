"""Authored bytes only. No actual PDF/runtime/credential/network access."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from civiclab.e01.clerk2020_m2_v1_1_contracts import (
    Axis, Counters, Refused, actual_factory, canonical, check_declared_graph,
    decode, digest, relative_path, run_id, sha, SampledResourceWindow,
)
from civiclab.e01.clerk2020_m2_v1_1_control import (
    ClosedRecords, CrashPoint, LEDGER_FILES, MockBootstrap, MockCrash,
    MockRegistrar, MockStore, MockTCB, MockTerminal, POLICY_SHA, policy_from_bytes,
)
from civiclab.e01.clerk2020_m2_v1_1_backend import (
    MAGIC, PAGE_FIELDS, MockInspection, actual_backend, authored_fake_pdf, inspect_authored,
    page_projection,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = (ROOT / 'configs/e01_clerk2020_m2_inspection_design_v1_1.json').read_bytes()
SPEC = json.loads(POLICY)
H = 'a' * 64


def registrar():
    r = MockRegistrar()
    r.register('DEMO_CAMPAIGN', 'DEMO_SET', 'DEMO_ANCHOR', H)
    return r


def documents(text='Authored fictional format fixture.\nNo real records.'):
    return [authored_fake_pdf('DEMO_2020', [text] * 81),
            authored_fake_pdf('DEMO_2026', [text] * 38)]


def terminal_fixture(crash=None):
    r = registrar()
    store = MockStore(crash)
    inspection = MockInspection()
    output = inspection.run(documents(), CrashPoint())
    terminal = MockTerminal(store, r, 'DEMO_CAMPAIGN', H, 'b' * 64, inspection.counters)
    payloads = {name: canonical({'label': 'MOCK', 'fixture': name})
                for name in LEDGER_FILES if name != 'counters.prefix.local.json'}
    payloads.update(output)
    bindings = {k: digest({'label': 'MOCK', 'binding': k}) for k in {
        'registration_sha256', 'static_spec_sha256', 'genesis_sha256',
        'execution_decision_sha256', 'issued_envelope_sha256',
        'source_set_sha256', 'external_reservation_sha256'}}
    return terminal, payloads, bindings


class Contracts(unittest.TestCase):
    def test_canonical_exact_utf8(self):
        self.assertEqual(canonical({'z': 'é', 'a': 1}), b'{"a":1,"z":"\xc3\xa9"}')
        self.assertEqual(decode(canonical({'z': 'é', 'a': 1})), {'a': 1, 'z': 'é'})

    def test_canonical_refuses_unsupported(self):
        for value in [1.0, float('nan'), {1: 'x'}, (1,), object(), '\ud800']:
            with self.subTest(value=type(value).__name__), self.assertRaises(Refused):
                canonical(value)

    def test_json_duplicates_noncanonical_nonfinite(self):
        for raw in [b'{"a":1,"a":2}', b'{ "a":1}', b'NaN', b'1.0', b'{}\n', b'\xff']:
            with self.subTest(raw=raw), self.assertRaises(Refused):
                decode(raw)

    def test_depth_nodes_and_size(self):
        x = None
        for _ in range(14):
            x = [x]
        for value in [x, [None] * 16384]:
            with self.assertRaises(Refused):
                canonical(value)
        with self.assertRaises(Refused):
            decode(b'"' + b'a' * 262144 + b'"')

    def test_paths(self):
        self.assertTrue(relative_path('data/processed/DEMO/file.json'))
        for p in ['/etc/passwd', '../x', 'a/../x', 'a//b', 'a/./b', 'a\\b', 'a\x00b', 'C:x']:
            self.assertFalse(relative_path(p), p)

    def test_factory_always_disabled(self):
        for fn in [actual_factory, actual_backend]:
            with self.assertRaises(Refused):
                fn(enabled=True, approved=True, budget=100, source=object())

    def test_graph_and_injected_cycle(self):
        graph = SPEC['closed_hash_DAG']
        self.assertTrue(check_declared_graph(graph['nodes'], graph['edges']))
        with self.assertRaises(Refused):
            check_declared_graph(graph['nodes'], graph['edges'] + [['CallerObservation', 'SourceSet']])

    def test_graph_unknown_duplicate_nodes(self):
        for nodes, edges in [(['A', 'A'], []), (['A'], [['A', 'B']]), (['A'], [['A']])]:
            with self.assertRaises(Refused):
                check_declared_graph(nodes, edges)

    def test_run_id_downstream_only(self):
        one = run_id('DEMO_A', 'JOB_A', {'schema_version': 1})
        self.assertRegex(one, '^e01-[0-9a-f]{32}$')
        self.assertNotEqual(one, run_id('DEMO_A', 'JOB_A', {'schema_version': 2}))

    def test_policy_pin_and_detachment(self):
        p = policy_from_bytes(POLICY)
        p['actual_factory_enabled'] = True
        self.assertFalse(policy_from_bytes(POLICY)['actual_factory_enabled'])
        with self.assertRaises(Refused):
            policy_from_bytes(POLICY + b' ')

    def test_closed_record_extra_missing_bool_int(self):
        v = ClosedRecords(POLICY)
        reference = {'path': 'mock/file.json', 'sha256': H, 'bytes': 1}
        self.assertEqual(v.validate('Ref', reference), reference)
        for wrong in [{**reference, 'extra': 1}, {k: v for k, v in reference.items() if k != 'path'},
                      {**reference, 'bytes': True}, {**reference, 'sha256': 'A' * 64},
                      {**reference, 'path': '../raw.pdf'}]:
            with self.assertRaises(Refused):
                v.validate('Ref', wrong)

    def test_opaque_fixed_predicate_requires_exact_binding(self):
        v = ClosedRecords(POLICY)
        obj = {'schema_version': 1, 'kind': 'M2_PHASE_PACKET_V1_1',
               **{k: 'DEMO' for k in ['registration_bytes_b64', 'static_spec_bytes_b64',
                                      'decision_bytes_b64', 'issued_envelope_bytes_b64']}}
        with self.assertRaises(Refused):
            v.validate('PhasePacket', obj)
        bindings = {k: x for k, x in obj.items() if k.endswith('_b64')}
        self.assertEqual(v.validate('PhasePacket', obj, bindings), obj)
        obj['decision_bytes_b64'] = 'CHANGED'
        with self.assertRaises(Refused):
            v.validate('PhasePacket', obj, bindings)

    def test_ledger_exact_no_seal_or_latest_head(self):
        v = ClosedRecords(POLICY)
        ledger = dict.fromkeys(LEDGER_FILES, H)
        self.assertEqual(v.validate('PrefixLedger', ledger), ledger)
        for extra in ['seal_sha256', 'latest_anchor_sha256', 'checksums.json']:
            with self.assertRaises(Refused):
                v.validate('PrefixLedger', {**ledger, extra: H})

    def test_preserved_all_17_m1_pins(self):
        for name, expected in SPEC['M1_all17_pins_unchanged'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)

    def test_axis_record_semantics_not_only_shape(self):
        validator = ClosedRecords(POLICY)
        good = Axis(10).allocate(10).precharge(10).record()
        self.assertEqual(validator.validate('CounterAxis', good), good)
        for bad in [{**good, 'held': 1}, {**good, 'observed': 0},
                    {**good, 'uncertain_charged': 11}]:
            with self.assertRaises(Refused):
                validator.validate('CounterAxis', bad)

    def test_terminal_records_and_payloads_have_exact_accepted_shapes(self):
        t, p, b = terminal_fixture()
        t.finalize(p, b)
        v = ClosedRecords(POLICY)
        for name, shape in [('seal', 'FinalSeal'), ('writer_ACK', 'WriterAck'),
                            ('counters.prefix.local.json', 'CounterState')]:
            record = decode(t.store.get(name))
            self.assertEqual(v.validate(shape, record), record)
        for line in t.prefix().splitlines():
            event = decode(line)
            v.validate(event['event_type'], event['payload'], event=True)
            with self.assertRaises(Refused):
                v.validate(event['event_type'], {**event['payload'], 'future_seal': H}, event=True)

    def test_counter_state_exact_15_axes_and_fixed_ceilings(self):
        t, p, b = terminal_fixture()
        t.finalize(p, b)
        v = ClosedRecords(POLICY)
        x = decode(t.store.get('counters.prefix.local.json'))
        x['axes']['source_jobs']['ceiling'] = 2
        with self.assertRaises(Refused):
            v.validate('CounterState', x)
        del x['axes']['source_jobs']
        with self.assertRaises(Refused):
            v.validate('CounterState', x)

    def test_methods_audit_and_predecessors_unchanged(self):
        pins = {
          'reports/INDEPENDENT_AUDIT_E01_CLERK2020_M2_DESIGN_V1_1_METHODS.json':
          'c4d0539514dda630926661f5f0492c0807d629f7dbeeb1e77a2e3e5c04d5d075',
          'configs/e01_clerk2020_m2_inspection_design_v1.json':
          'a7ef796ea2d99a708ee5d31c4eeae9809d621cc3b46f35a523fab374a10057c9',
          'docs/E01_CLERK2020_M2_INSPECTION_DESIGN_v1.md':
          '6b306d48539adc3c4beb0d22ead232c8c084046bcae9e2abbbb10838353c6d7b',
        }
        for name, expected in pins.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)


class CounterTests(unittest.TestCase):
    def test_resource_sample_windows_and_no_restart(self):
        for values in [(75001, 1, 1), (1, 50001, 1), (1, 1, 268435457),
                       (float('nan'), 1, 1), (True, 1, 1), (1, 1, 0)]:
            w = SampledResourceWindow(75000, 50000)
            with self.assertRaises(Refused):
                w.sample(*values)
            with self.assertRaises(Refused):
                w.sample(1, 1, 1)

    def test_resource_clock_cpu_rollback_refuses(self):
        for values in [(1, 10, 1), (10, 1, 1)]:
            w = SampledResourceWindow(75000, 50000)
            w.sample(10, 10, 1)
            with self.assertRaises(Refused):
                w.sample(*values)

    def test_known_settlement_restores_only_unspent_hold(self):
        a = Axis(10).allocate(10).reserve(8).settle(8, 3)
        self.assertEqual((a.held, a.reserved, a.charged, a.observed), (7, 0, 3, 3))

    def test_unknown_charges_full_and_nulls_observed(self):
        a = Axis(10).allocate(10).reserve(8).settle(8)
        self.assertEqual((a.held, a.charged, a.uncertain_charged, a.observed), (2, 8, 8, None))
        stopped = a.stop_unknown()
        self.assertEqual(stopped.charged, 10)
        self.assertEqual(stopped.stop_unknown(), stopped)

    def test_precharge_no_refund(self):
        a = Axis(10).allocate(10).precharge(10)
        with self.assertRaises(Refused):
            a.settle(10, 0)
        self.assertEqual(a.charged, 10)

    def test_cap_and_bool_negative_guards(self):
        for v in [True, -1, 1.0, 11]:
            with self.assertRaises(Refused):
                Axis(10).allocate(v)
        with self.assertRaises(Refused):
            Axis(10).allocate(1).reserve(2)

    def test_atomic_multiaxis_refusal(self):
        c = Counters()
        initial = c.snapshot()
        with self.assertRaises(Refused):
            c.transition('allocate', {'metadata_read_bytes': 1, 'source_jobs': 2})
        self.assertEqual(initial, c.snapshot())

    def test_snapshot_detached(self):
        c = Counters()
        s = c.snapshot()
        s['source_jobs']['ceiling'] = 999
        self.assertEqual(c.snapshot()['source_jobs']['ceiling'], 1)

    def test_exhaustive_small_axis_conservation(self):
        for ceiling in range(8):
            for r in range(ceiling + 1):
                for actual in range(r + 1):
                    axis = Axis(ceiling).allocate(ceiling).reserve(r).settle(r, actual)
                    self.assertEqual(axis.held + axis.charged, ceiling)
                    self.assertEqual(axis.charged, actual)


class AdmissionTests(unittest.TestCase):
    def test_fixed_namespace_and_source_set_no_new_root(self):
        r = registrar()
        with self.assertRaises(Refused):
            r.register('DIFFERENT_RELEASE', 'DEMO_SET', 'OTHER_ANCHOR', H)
        with self.assertRaises(Refused):
            r.register('DIFFERENT_RELEASE', 'OTHER_SET', 'OTHER_ANCHOR', H)
        raw = r.issue('DEMO_CAMPAIGN', 'BOOT', 'ATTEMPT', H, None)
        self.assertEqual(decode(raw)['campaign_id'], 'DEMO_CAMPAIGN')

    def test_issuance_one_shot_even_without_consume(self):
        r = registrar()
        r.issue('DEMO_CAMPAIGN', 'BOOT', 'ONE', H, None)
        with self.assertRaises(Refused):
            r.issue('DEMO_CAMPAIGN', 'BOOT', 'TWO', H, None)

    def test_external_hash_and_cross_registrar(self):
        r = registrar()
        raw = r.issue('DEMO_CAMPAIGN', 'BOOT', 'ONE', H, None)
        with self.assertRaises(Refused):
            r.consume(raw, 'f' * 64, CrashPoint())
        with self.assertRaises(Refused):
            registrar().consume(raw, sha(raw), CrashPoint())

    def test_cas_stale_anchor(self):
        r = registrar()
        r.cas('DEMO_CAMPAIGN', None, H)
        with self.assertRaises(Refused):
            r.cas('DEMO_CAMPAIGN', None, 'b' * 64)

    def test_registration_race_only_one(self):
        r = MockRegistrar()
        def register(i):
            try:
                r.register('C' + str(i), 'DEMO_SET', 'A' + str(i), H)
                return True
            except Refused:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(register, range(8))), 1)

    def test_consume_race_only_one(self):
        r = registrar()
        raw = r.issue('DEMO_CAMPAIGN', 'BOOT', 'ONE', H, None)
        def consume(_):
            try:
                r.consume(raw, sha(raw), CrashPoint())
                return True
            except Refused:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(consume, range(8))), 1)

    def test_reservation_crash_consumes_no_retry(self):
        for boundary in ['reservation.before', 'reservation.after']:
            r = registrar()
            raw = r.issue('DEMO_CAMPAIGN', 'BOOT', 'ONE', H, None)
            with self.assertRaises(MockCrash):
                r.consume(raw, sha(raw), CrashPoint(boundary))
            with self.assertRaises(Refused):
                r.consume(raw, sha(raw), CrashPoint())

    def bootstrap(self):
        r = registrar()
        raw = r.issue('DEMO_CAMPAIGN', 'BOOT', 'ONE', H, None)
        body = b'AUTHORED CODE BYTES'
        tcb = MockTCB({'DEMO_CODE': body})
        manifest = canonical([{'artifact': 'DEMO_CODE', 'axis': 'code_integrity_read_bytes',
                              'bytes': len(body), 'sha256': sha(body)}])
        return MockBootstrap(r, tcb), raw, manifest

    def test_bootstrap_read_reservation_and_no_source(self):
        b, raw, manifest = self.bootstrap()
        points = CrashPoint()
        receipt = b.run(raw, sha(raw), manifest, points)
        self.assertLess(points.seen.index('reservation.after'), points.seen.index('read.reserve'))
        self.assertLess(points.seen.index('read.reserve'), points.seen.index('read.effect'))
        self.assertEqual(receipt['source_reads'], 0)
        self.assertEqual(b.tcb.reads, ['DEMO_CODE'])
        self.assertEqual(receipt['counters']['source_read_bytes']['charged'], 0)
        self.assertIsNone(receipt['counters']['cpu_ms']['observed'])

    def test_no_read_without_held_reservation(self):
        tcb = MockTCB({'DEMO_CODE': b'x'})
        with self.assertRaises(Refused):
            tcb.read_reserved('DEMO_CODE', 'code_integrity_read_bytes', 2, Counters(), CrashPoint())
        self.assertEqual(tcb.reads, [])

    def test_bootstrap_hash_failure_no_replay(self):
        b, raw, manifest = self.bootstrap()
        wrong = decode(manifest)
        wrong[0]['sha256'] = 'f' * 64
        with self.assertRaises(Refused):
            b.run(raw, sha(raw), canonical(wrong))
        with self.assertRaises(Refused):
            b.run(raw, sha(raw), manifest)
        self.assertTrue(b.stopped)

    def test_bootstrap_each_crash_no_repeat(self):
        for boundary in ['reservation.before', 'reservation.after', 'read.reserve', 'read.effect', 'bootstrap.anchor']:
            b, raw, manifest = self.bootstrap()
            with self.subTest(boundary=boundary), self.assertRaises(MockCrash):
                b.run(raw, sha(raw), manifest, CrashPoint(boundary))
            with self.assertRaises(Refused):
                b.run(raw, sha(raw), manifest)
            if boundary.startswith('reservation'):
                self.assertEqual(b.tcb.reads, [])
            else:
                self.assertEqual(b.counters.snapshot()['code_integrity_read_bytes']['charged'], 535822336)

    def test_tcb_rejects_path_or_callback(self):
        for artifacts in [{'../raw.pdf': b'x'}, {'DEMO_CODE': lambda: b'x'}]:
            with self.assertRaises(Refused):
                MockTCB(artifacts)


class BackendTests(unittest.TestCase):
    def test_source_and_backend_reservation_before_effect_no_replay(self):
        job = MockInspection()
        crash = CrashPoint()
        output = job.run(documents(), crash)
        self.assertLess(crash.seen.index('source.reserve'), crash.seen.index('source.effect'))
        self.assertLess(crash.seen.index('backend.reserved'), crash.seen.index('backend.effect'))
        self.assertEqual(job.counters.snapshot()['page_extractions']['observed'], 119)
        self.assertEqual(len(job.effects), 2)
        with self.assertRaises(Refused):
            job.run(documents(), CrashPoint())
        self.assertIn('inspection_diagnostics.json', output)

    def test_source_backend_crash_max_charged_and_no_replay(self):
        for boundary in ['source.reserve', 'source.effect', 'backend.reserved', 'backend.effect']:
            job = MockInspection()
            with self.assertRaises(MockCrash):
                job.run(documents(), CrashPoint(boundary))
            self.assertEqual(job.counters.snapshot()['page_extractions']['charged'], 119)
            self.assertIsNone(job.counters.snapshot()['page_extractions']['observed'])
            with self.assertRaises(Refused):
                job.run(documents(), CrashPoint())

    def test_119_page_fixture_bounds_unknowns_and_privacy(self):
        out = inspect_authored(documents('DEMO_PRIVATE_NAME should never be public.'))
        private = decode(out['inspection_projection.local.json'])
        public = decode(out['inspection_diagnostics.json'])
        self.assertEqual(public['page_counts'], [81, 38])
        self.assertNotIn(b'DEMO_PRIVATE_NAME', out['inspection_diagnostics.json'])
        self.assertEqual(public['candidate_or_vote_records_parsed'], 0)
        self.assertLessEqual(sum(map(len, out.values())), 262144)
        for d in private['documents']:
            for row in d['pages']:
                self.assertEqual(set(row), PAGE_FIELDS)
                self.assertEqual(row['source_role_UNKNOWN_UNREVIEWED'], 'UNKNOWN')
                self.assertLessEqual(len(canonical(row)), 2048)

    def test_all_fake_unsupported_flags_refuse(self):
        for flag in ['encrypted', 'active', 'warning', 'malformed']:
            docs = documents()
            docs[0] = authored_fake_pdf('DEMO_2020', ['x'] * 81, **{flag: True})
            with self.subTest(flag=flag), self.assertRaises(Refused):
                inspect_authored(docs)

    def test_not_real_pdf_or_changed_count(self):
        docs = documents()
        for replacement in [b'%PDF-1.4\n', authored_fake_pdf('DEMO_2020', ['x'] * 80)]:
            with self.assertRaises(Refused):
                inspect_authored([replacement, docs[1]])

    def test_source_duplicate_refused(self):
        with self.assertRaises(Refused):
            inspect_authored([authored_fake_pdf('DEMO_X', ['x'] * 81),
                              authored_fake_pdf('DEMO_X', ['x'] * 38)])

    def test_multibyte_escape_clipping_ranges_and_hashes(self):
        for text in ['é' * 3000, '😀' * 3000, '\x00\\"\n' * 2000, 'A' * 40000, '']:
            row = page_projection('DEMO_PAGE', H, 1, text)
            raw = text.encode('utf8')
            retained = 0
            prior_end = 0
            for window in row['snippet_windows']:
                a, b = window['utf8_start'], window['utf8_end']
                self.assertGreaterEqual(a, prior_end)
                self.assertEqual(raw[a:b].decode('utf8'), window['text'])
                self.assertEqual(sha(raw[a:b]), window['utf8_sha256'])
                prior_end = b
                retained += b - a
            self.assertLessEqual(retained, 1024)
            self.assertLessEqual(len(canonical(row)), 2048)
            self.assertEqual(retained + row['omitted_text_utf8_bytes'], len(raw))
            self.assertEqual(row['retained_whole_page'], retained == len(raw))

    def test_empty_and_short_full_coverage(self):
        for text in ['', 'a', 'one\ntwo']:
            row = page_projection('DEMO_PAGE', H, 1, text)
            self.assertTrue(row['retained_whole_page'])
            self.assertEqual(row['omitted_text_utf8_bytes'], 0)

    def test_large_page_invalid_hash_and_surrogate(self):
        for text in ['a' * 40001, '\ud800']:
            with self.assertRaises(Refused):
                page_projection('DEMO_PAGE', H, 1, text)
        with self.assertRaises(Refused):
            page_projection('DEMO_PAGE', 'bad', 1, 'text')

    def test_raw_body_canonical_duplicates_and_limits(self):
        for raw in [MAGIC + b'{"label":"MOCK","label":"MOCK"}', MAGIC + b'x' * 1048576]:
            with self.assertRaises(Refused):
                inspect_authored([raw, documents()[1]])


class TerminalTests(unittest.TestCase):
    def test_success_prefix_seal_tail_ack_and_caller(self):
        t, payloads, bindings = terminal_fixture()
        result = t.finalize(payloads, bindings)
        self.assertEqual(result['label'], 'MOCK')
        self.assertTrue(t.caller_returned)
        files = t.store.snapshot()
        seal = decode(files['seal'])
        self.assertEqual(seal['sealed_prefix_file_sha256'], sha(t.prefix()))
        self.assertEqual(seal['sealed_prefix_bytes'], len(t.prefix()))
        self.assertEqual([e['event_type'] for e in t.tail()], ['VERIFY_OK', 'ACK_COMMITTED'])
        self.assertNotIn('writer_ack_sha256', seal)
        self.assertNotIn('tail_head', seal)
        self.assertEqual(t.tail()[0]['previous_sha256'], sha(files['seal']))
        self.assertEqual(t.tail()[1]['writer_ack_sha256'], sha(files['writer_ACK']))
        self.assertEqual(t.registrar.current(t.campaign), sha(files['completed_anchor']))
        for line in t.prefix().splitlines():
            self.assertLessEqual(len(line) + 1, 1024)

    def test_closed_prefix_and_second_finalization_refuse(self):
        t, p, b = terminal_fixture()
        t.finalize(p, b)
        original = t.prefix(), t.store.snapshot()
        with self.assertRaises(Refused):
            t.finalize(p, b)
        with self.assertRaises(Refused):
            t.append('COMMIT_PREFIX', {})
        self.assertEqual(original, (t.prefix(), t.store.snapshot()))

    def test_all_observed_boundaries_crash_no_retry_or_refund(self):
        successful, p, b = terminal_fixture()
        successful.finalize(p, b)
        boundaries = successful.store.crash.seen
        self.assertGreaterEqual(len(boundaries), 40)
        for boundary in boundaries:
            t, p, b = terminal_fixture(CrashPoint(boundary))
            with self.subTest(boundary=boundary), self.assertRaises(MockCrash):
                t.finalize(p, b)
            state = t.prefix(), t.store.snapshot(), t.counters.snapshot()
            self.assertFalse(t.caller_returned)
            with self.assertRaises(Refused):
                t.finalize(p, b)
            self.assertEqual(state, (t.prefix(), t.store.snapshot(), t.counters.snapshot()))
            self.assertEqual(state[2]['record_verification_read_bytes']['charged'], 2097152)
            self.assertIsNone(state[2]['record_verification_read_bytes']['observed'])

    def test_lost_ack_after_durable_file_unknown(self):
        t, p, b = terminal_fixture(CrashPoint('writer_ACK.after'))
        with self.assertRaises(MockCrash):
            t.finalize(p, b)
        self.assertIn('writer_ACK', t.store.snapshot())
        self.assertNotIn('completed_anchor', t.store.snapshot())
        self.assertEqual(t.status, 'MOCK_SEALED_OR_ACK_UNKNOWN')
        self.assertFalse(t.caller_returned)

    def test_lost_caller_after_completed_anchor_unknown(self):
        t, p, b = terminal_fixture(CrashPoint('caller.before'))
        with self.assertRaises(MockCrash):
            t.finalize(p, b)
        self.assertIn('completed_anchor', t.store.snapshot())
        self.assertIsNotNone(t.registrar.current(t.campaign))
        self.assertFalse(t.caller_returned)
        self.assertEqual(t.status, 'MOCK_SEALED_OR_ACK_UNKNOWN')

    def test_counter_snapshot_no_future_hashes(self):
        t, p, b = terminal_fixture()
        t.finalize(p, b)
        x = decode(t.store.get('counters.prefix.local.json'))
        self.assertNotIn('seal_sha256', x)
        self.assertNotIn('prefix_ledger_sha256', x)
        self.assertEqual(x['observed_through_sequence'], 1)
        self.assertEqual(x['external_reservation_sha256'], b['external_reservation_sha256'])
        self.assertEqual(x['source_set_sha256'], b['source_set_sha256'])
        self.assertEqual(x['axes']['record_verification_read_bytes']['charged'], 2097152)
        self.assertIsNone(x['axes']['record_verification_read_bytes']['observed'])

    def test_nonmock_or_extra_payloads_refuse(self):
        for operation in ['unlabel', 'extra', 'missing']:
            t, p, b = terminal_fixture()
            if operation == 'unlabel':
                p['summary.json'] = canonical({'text': 'not a MOCK artifact'})
            elif operation == 'extra':
                p['extra.json'] = b'{}'
            else:
                del p['summary.json']
            with self.assertRaises(Refused):
                t.finalize(p, b)
            self.assertEqual(t.store.snapshot(), {})

    def test_drift_between_seal_and_verification_refuses(self):
        t, p, b = terminal_fixture()
        def mutate(name):
            if name == 'verification.before':
                t.store._files['summary.json'] = canonical({'label': 'MOCK', 'drift': True})
        t.store.crash = mutate
        with self.assertRaises(Refused):
            t.finalize(p, b)
        self.assertNotIn('writer_ACK', t.store.snapshot())

    def test_journal_drift_refuses(self):
        t, p, b = terminal_fixture()
        def mutate(name):
            if name == 'verification.before':
                t.store._files['journal_1'] = b'altered\n'
        t.store.crash = mutate
        with self.assertRaises(Refused):
            t.finalize(p, b)

    def test_store_one_shot_and_category_intersection(self):
        store = MockStore()
        store.create('data', b'x', 262144, 'data')
        with self.assertRaises(Refused):
            store.create('data', b'x', 1, 'data')
        with self.assertRaises(Refused):
            store.create('overflow', b'x', 1, 'data')
        store.create('metadata', b'x', 24576)
        with self.assertRaises(Refused):
            store.create('metadata2', b'x', 1)

    def test_slot_crash_is_consumed(self):
        s = MockStore(CrashPoint('data.before'))
        with self.assertRaises(MockCrash):
            s.create('data', b'x', 1, 'data')
        s.crash = CrashPoint()
        with self.assertRaises(Refused):
            s.create('data', b'x', 1, 'data')

    def test_snapshot_cannot_mutate_store(self):
        s = MockStore()
        s.create('data', b'original', 8, 'data')
        s.snapshot()['data'] = b'changed'
        self.assertEqual(s.get('data'), b'original')

    def test_no_io_or_actual_backend_in_pure_pipeline(self):
        # Imports and accepted public policy read happen before the guard.
        def refuse(*args, **kwargs):
            raise AssertionError('FORBIDDEN_ACTUAL_IO')
        with patch('builtins.open', refuse), patch('os.open', refuse), patch('socket.socket', refuse):
            t, p, b = terminal_fixture()
            self.assertFalse(t.finalize(p, b)['actual_source_access'])

    def test_terminal_data_and_precommit_overflow_refuse(self):
        t, p, b = terminal_fixture()
        p['inspection_diagnostics.json'] = canonical({'label': 'MOCK', 'large': 'x' * 8192})
        with self.assertRaises(Refused):
            t.finalize(p, b)
        t, p, b = terminal_fixture()
        p['manifest.json'] = canonical({'label': 'MOCK', 'large': 'x' * 24576})
        with self.assertRaises(Refused):
            t.finalize(p, b)

    def test_prefix_commit_before_seal_failure_no_ack(self):
        t, p, b = terminal_fixture(CrashPoint('seal.before'))
        with self.assertRaises(MockCrash):
            t.finalize(p, b)
        frozen = t.prefix()
        self.assertNotIn('seal', t.store.snapshot())
        self.assertNotIn('writer_ACK', t.store.snapshot())
        with self.assertRaises(Refused):
            t.append('COMMIT_PREFIX', {})
        self.assertEqual(t.prefix(), frozen)


if __name__ == '__main__':
    unittest.main()
