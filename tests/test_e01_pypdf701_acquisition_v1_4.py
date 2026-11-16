"""MOCK fresh metadata after genuinely expired historical fixture timestamps."""
import ast
import copy
from datetime import timedelta
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


g = load('p1_4_previous_fixtures', ROOT/'tests/test_e01_pypdf701_acquisition_v1_3.py')
w = load('p1_4_collector', ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_4.py')
c, old = w.c, g.old


class FreshMetadataTests(unittest.TestCase):
    def setUp(self):
        self.previous = g.FourthAttemptFixtureTests()
        self.previous.setUp(); self.addCleanup(self.previous.doCleanups)
        self.root, self.source = self.previous.root, self.previous.source
        self.patch = patch.object(c, 'PYPDF', self.source.files['pypdf'])
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.now = old.NOW+timedelta(days=1)
        self.methods = c.json_body((ROOT/w.METHODS).read_bytes())
        self.methods['root_sha256'] = c.sha(str(self.root).encode())
        self.methods['latest_methods_ref'] = self.previous.methods['previous_methods_ref']
        self.methods['latest_refs'] = self.previous.methods['previous_refs']
        self.methods['prior_cumulative'] = self.previous.methods['prior_cumulative']
        self.methods['cached_pypdf_ref'] = self.previous.methods['cached_pypdf_ref']
        self.methods['original_methods_ref'] = self.save('configs/e01_pypdf701_acquisition_v1_20261115.json', c.packed(self.source.methods))
        self.original = {str(p.relative_to(self.root)): p.read_bytes()
            for scope in (c.OUTPUT, w.n.OUTPUT, w.v.v.OUTPUT) for p in (self.root/scope).rglob('*') if p.is_file()}
        date = old.format_datetime(self.now, usegmt=True)
        self.responses = {}
        for name, version in c.VERSIONS.items():
            url = f'https://pypi.org/pypi/{name}/{version}/json'
            self.responses[url] = old.Response(self.source.responses[url].body, headers={'date': date, 'age': '0'})
        for url, name in ((c.API, 'metadata/advisories-current.json'), (c.PROVENANCE, 'metadata/pypdf-provenance.json')):
            self.responses[url] = old.Response((self.root/w.v.v.OUTPUT/name).read_bytes(), headers={'date': date, 'age': '0'})
        for name in list(c.VERSIONS)[1:]:
            url = self.source.files[name]['url']
            self.responses[url] = old.Response(self.source.responses[url].body, 'wheel',
                headers={'date': date, 'age': '1425974', 'cache-control': 'max-age=365000000, immutable, public'})
        self.transport = old.Transport(self.responses)

    def save(self, name, raw):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {'path': name, 'bytes': len(raw), 'sha256': c.sha(raw)}

    def collector(self, deadline=None):
        return w.Collector(self.root, self.methods, self.transport,
            clock=lambda: self.source.time[0], cpu=lambda: self.source.cpu[0], utc=lambda: self.now,
            operation_deadline_utc=deadline if deadline is not None else self.now+timedelta(seconds=120))

    def run_collect(self): return self.collector().run()
    def terminal(self): return c.json_body((self.root/w.OUTPUT/'TERMINAL.json').read_bytes())
    def unchanged(self):
        current = {str(p.relative_to(self.root)): p.read_bytes()
            for scope in (c.OUTPUT, w.n.OUTPUT, w.v.v.OUTPUT) for p in (self.root/scope).rglob('*') if p.is_file()}
        self.assertEqual(self.original, current)

    def test_expired_history_is_only_history_and_all_seven_responses_are_new(self):
        with patch.object(w.v.Collector, 'predecessor', side_effect=AssertionError('NO_EXPIRED_GATE_OR_FORGED_UTC')):
            result = self.run_collect()
        self.assertEqual(result['status'], 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        self.assertEqual(len(self.transport.calls), 11)
        expected = [f'https://pypi.org/pypi/{name}/{version}/json' for name, version in c.VERSIONS.items()]+[c.API,c.PROVENANCE]
        self.assertEqual(self.transport.calls[:7], expected)
        self.assertNotIn(c.PYPDF['url'], self.transport.calls)
        self.assertEqual(result['budget']['attempts'], {'GET': 21, 'metadata_GET': 15, 'wheel_GET': 6})
        prior = self.methods['prior_cumulative']['budget']['body_bytes_charged']
        self.assertEqual(result['budget']['body_bytes_charged']['metadata'], prior['metadata']+
                         sum(len(self.responses[url].body) for url in expected))
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 33554432+
                         sum(len(self.responses[self.source.files[name]['url']].body) for name in list(c.VERSIONS)[1:]))
        receipt = c.json_body((self.root/w.OUTPUT/'fresh-metadata-receipt.json').read_bytes())
        self.assertEqual(receipt['fresh_metadata_GETs'], 7); self.assertEqual(len(receipt['fresh_metadata_refs']), 7)
        lock = c.json_body((self.root/w.OUTPUT/'hashlock.json').read_bytes())
        self.assertEqual(len(lock['wheels']), 5); self.assertFalse(lock['ready_for_install'])
        self.assertEqual(lock['failed_wheel_GET_charges_retained'], 33554432)
        self.assertEqual(c.CAPS['GET'], 13)
        self.unchanged()

    def test_real_methods_table_keeps_latest_prefix_counts_and_terminal(self):
        m = c.json_body((ROOT/w.METHODS).read_bytes())
        prior = c.json_body((ROOT/m['latest_methods_ref']['path']).read_bytes())['prior_cumulative']
        total = sum(ref['bytes'] for ref in m['latest_refs'].values())
        raw = sum(ref['bytes'] for name, ref in m['latest_refs'].items() if name.startswith(('metadata/','wheels/')))
        self.assertEqual(m['latest_refs']['TERMINAL.json']['bytes'], 3234)
        self.assertEqual(m['prior_cumulative']['owned_bytes'], prior['owned_bytes']+total)
        self.assertEqual(m['prior_cumulative']['control_bytes'], prior['control_bytes']+total-raw)
        self.assertEqual(m['prior_cumulative']['owned_bytes'], 3041964)
        self.assertEqual(m['prior_cumulative']['control_bytes'], 134401)
        self.assertEqual(m['prior_cumulative']['events'], 20)

    def test_host_suspension_utc_deadline_stops_while_monotonic_stays_still(self):
        collector = self.collector(); self.now += timedelta(seconds=121)
        self.assertEqual(self.source.time[0], 0)
        with self.assertRaisesRegex(c.Refused, 'ABSOLUTE_UTC_DEADLINE_EXPIRED'): collector.run()
        self.assertEqual(self.transport.calls, []); self.assertFalse((self.root/w.OUTPUT).exists())

    def test_utc_rollback_is_not_a_freshness_extension(self):
        collector = self.collector(); self.now -= timedelta(seconds=1)
        with self.assertRaisesRegex(c.Refused, 'UTC_CLOCK_REGRESSION'): collector.run()
        self.assertEqual(self.transport.calls, [])

    def test_deadline_is_external_aware_utc_and_at_most_120_seconds(self):
        for deadline in (self.now-timedelta(seconds=1), self.now+timedelta(seconds=121), self.now.replace(tzinfo=None)):
            with self.subTest(deadline=deadline), self.assertRaisesRegex(c.Refused, 'ABSOLUTE_UTC_DEADLINE_BINDING'):
                self.collector(deadline)
        self.assertEqual(self.transport.calls, [])

    def test_new_metadata_may_not_use_immutable_wheel_age_exception(self):
        response = self.responses[next(iter(self.responses))]
        response.headers.update(age='1425974', **{'cache-control':'max-age=365000000, immutable, public'})
        result = self.run_collect()
        self.assertEqual(result['reason'], 'HTTP_FRESHNESS'); self.assertEqual(response.offset, 0)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 33554432)
        self.assertEqual(result['budget']['body_bytes_charged']['metadata'],
                         self.methods['prior_cumulative']['budget']['body_bytes_charged']['metadata']+c.CAPS['metadata_each'])

    def test_old_date_cannot_be_promoted_by_new_namespace(self):
        response = self.responses[next(iter(self.responses))]
        response.headers['date'] = old.format_datetime(old.NOW, usegmt=True)
        result = self.run_collect()
        self.assertEqual(result['reason'], 'HTTP_DATE_FRESHNESS'); self.assertEqual(response.offset, 0)

    def test_new_applicable_advisory_stops_before_provenance_or_wheels(self):
        rows = c.json_body(self.responses[c.API].body)
        rows.append(old.advisory('GHSA-neww-1234-5678', '<8.0.0', '>=8.0.0'))
        self.responses[c.API] = old.Response(c.packed(rows), headers={'date':old.format_datetime(self.now,usegmt=True)})
        result = self.run_collect()
        self.assertEqual(result['reason'], 'APPLICABLE_ADVISORY')
        self.assertEqual(len(self.transport.calls), 6); self.assertNotIn(c.PROVENANCE, self.transport.calls)
        self.assertFalse((self.root/w.OUTPUT/'wheels').exists())

    def test_fresh_advisory_page_needing_pagination_has_no_extra_get(self):
        self.responses[c.API].headers['link'] = '<'+c.API+'&after=MOCK_CURSOR>; rel="next"'
        result = self.run_collect()
        self.assertEqual(result['reason'], 'FRESH_ADVISORY_SINGLE_PAGE_CAP')
        self.assertEqual(len(self.transport.calls), 6)

    def test_changed_fixed_companion_identity_stops_before_any_wheel(self):
        url = 'https://pypi.org/pypi/cffi/2.1.1/json'
        doc = c.json_body(self.responses[url].body); doc['urls'][0]['digests']['sha256'] = 'f'*64
        self.responses[url] = old.Response(c.packed(doc), headers={'date':old.format_datetime(self.now,usegmt=True)})
        result = self.run_collect()
        self.assertEqual(result['reason'], 'CHANGED_FIXED_ARTIFACT_IDENTITY')
        self.assertEqual(len(self.transport.calls), 2)

    def test_cache_tamper_or_historical_terminal_tamper_refuses_before_network(self):
        path = self.root/self.methods['cached_pypdf_ref']['path']; raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(c.Refused, 'INPUT_HASH'): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_original_failed_ancestor_remains_required(self):
        path = self.root/c.OUTPUT/'TERMINAL.json'; raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(c.Refused, 'INPUT_HASH'): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_unmodeled_v1_3_state_blocks_instead_of_assuming_zero_consumption(self):
        (self.root/w.v.OUTPUT).mkdir()
        with self.assertRaisesRegex(c.Refused, 'UNMODELED_V1_3_STATE'): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_new_stage_is_create_once_and_never_replayed(self):
        self.run_collect(); terminal = (self.root/w.OUTPUT/'TERMINAL.json').read_bytes(); self.transport.calls.clear()
        with self.assertRaisesRegex(c.Refused, 'SUCCESSOR_ALREADY_CONSUMED'): self.run_collect()
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(terminal, (self.root/w.OUTPUT/'TERMINAL.json').read_bytes())

    def test_only_seven_metadata_urls_and_gated_companions_are_available(self):
        collector = self.collector(); collector.predecessor()
        for url, kind in ((c.PYPDF['url'],'wheel'), (self.source.files['cffi']['url'],'wheel'),
                          ('https://example.com/OTHER','metadata')):
            with self.subTest(url=url), self.assertRaisesRegex(c.Refused, 'FIXED_METADATA_OR_COMPANIONS_ONLY'):
                collector.fetch(url, kind, 'NEVER', 'NEVER')
        self.assertEqual(self.transport.calls, [])

    def test_cumulative_21_get_cap_and_original_byte_caps_do_not_reset(self):
        collector = self.collector(); collector.predecessor()
        for kind in ['metadata']*7+['wheel']*4:
            collector.budget.begin(kind); collector.budget.settle(kind,0)
        self.assertEqual(collector.budget.attempts, {'GET':21,'metadata_GET':15,'wheel_GET':6})
        self.assertEqual(collector.budget.bytes['wheel'],33554432)
        with self.assertRaisesRegex(c.Refused,'REQUEST_CAP'): collector.budget.begin('wheel')
        with self.assertRaisesRegex(c.Refused,'REQUEST_CAP'): collector.budget.begin('metadata')
        self.assertEqual(w.CAPS['network_total'],c.CAPS['network_total'])

    def test_failure_keeps_new_full_hold_and_all_prior_charges(self):
        first = next(iter(self.responses)); self.responses[first] = TimeoutError('DO_NOT_LEAK')
        result = self.run_collect()
        self.assertEqual(result['reason'],'TimeoutError'); self.assertEqual(self.transport.calls,[first])
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'],33554432)
        self.assertNotIn(b'DO_NOT_LEAK',(self.root/w.OUTPUT/'TERMINAL.json').read_bytes())
        self.unchanged()

    def test_suspend_during_body_read_preserves_failed_full_metadata_reservation(self):
        response = self.responses[next(iter(self.responses))]; original = response.read
        def suspend(size,timeout):
            chunk = original(size,timeout); self.now += timedelta(seconds=121); return chunk
        response.read = suspend
        result = self.run_collect()
        self.assertEqual(result['reason'],'ABSOLUTE_UTC_DEADLINE_EXPIRED')
        self.assertEqual(len(self.transport.calls),1)
        self.assertFalse((self.root/w.OUTPUT/'metadata/pypdf.json').exists())

    def test_monotonic_or_cpu_limit_remains_independent_of_utc(self):
        for wall,cpu in ((120,0),(0,30),(-1,0),(0,-1)):
            collector = self.collector(); self.source.time[0],self.source.cpu[0] = wall,cpu
            with self.subTest(wall=wall,cpu=cpu), self.assertRaises(c.Refused): collector.budget.check()
            self.source.time[0] = self.source.cpu[0] = 0

    def post_final_write_refusal(self, change, reason):
        collector = self.collector(); original = collector.write
        def advance_after_durable_hashlock(name, body, control=True):
            ref = original(name, body, control)
            if name == 'hashlock.json': change(collector)
            return ref
        collector.write = advance_after_durable_hashlock
        result = collector.run()
        self.assertEqual(result['status'], 'FAILED_OR_UNKNOWN_NO_RETRY')
        self.assertEqual(result['reason'], reason)
        self.assertTrue((self.root/w.OUTPUT/'hashlock.json').exists())
        terminal = self.terminal()
        self.assertEqual(terminal['status'], 'FAILED_OR_UNKNOWN_NO_RETRY')
        self.assertTrue(any(ref['path'] == 'hashlock.json' for ref in terminal['artifacts']))
        self.assertEqual(len(self.transport.calls), 11)
        self.unchanged()

    def test_post_final_hashlock_write_utc_expiry_cannot_commit_success(self):
        def expire(collector): self.now = collector.budget.deadline
        self.post_final_write_refusal(expire, 'ABSOLUTE_UTC_DEADLINE_EXPIRED')

    def test_post_final_hashlock_write_utc_rollback_cannot_commit_success(self):
        def rollback(_): self.now -= timedelta(seconds=1)
        self.post_final_write_refusal(rollback, 'UTC_CLOCK_REGRESSION')

    def test_post_final_hashlock_write_monotonic_expiry_cannot_commit_success(self):
        def expire(_): self.source.time[0] = 120
        self.post_final_write_refusal(expire, 'CONTINUATION_RESOURCE_LIMIT')

    def test_post_final_hashlock_write_cpu_expiry_cannot_commit_success(self):
        def expire(_): self.source.cpu[0] = 30
        self.post_final_write_refusal(expire, 'CONTINUATION_RESOURCE_LIMIT')


class RetainedPolicyTests(unittest.TestCase):
    def test_immutable_freshness_policy_and_raw_transport_are_unchanged(self):
        before = ast.parse((ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_3.py').read_bytes())
        after = ast.parse((ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_4.py').read_bytes())
        for name in ('cache_directives','freshness_decision','HTTPTransport'):
            first = next(node for node in before.body if getattr(node,'name',None) == name)
            second = next(node for node in after.body if getattr(node,'name',None) == name)
            self.assertEqual(ast.dump(first,include_attributes=False),ast.dump(second,include_attributes=False))


if __name__ == '__main__':
    old.guarded_test_main()
