"""Authored immutable-cache headers and stopped ancestry; no actual GETs."""
import copy
from datetime import timedelta
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


f = load('p1_3_prior_fixtures', ROOT/'tests/test_e01_pypdf701_acquisition_v1_2.py')
w = load('p1_3_collector', ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_3.py')
c = w.c
old = f.f.f
NOW = old.NOW


def headers(age='1425974', control='max-age=365000000, immutable, public', delta=0):
    result = {'date': old.format_datetime(NOW+timedelta(seconds=delta), usegmt=True), 'age': age}
    if control is not None: result['cache-control'] = control
    return result


class ArtifactFreshnessTests(unittest.TestCase):
    def test_immutable_current_date_aged_artifact_uses_unique_maxage(self):
        raw = headers(); before = dict(raw)
        decision = w.freshness_decision(raw, 'wheel', NOW)
        self.assertEqual(decision['policy'], 'FIXED_IMMUTABLE_ARTIFACT_UNIQUE_MAX_AGE')
        self.assertEqual(decision['Age_seconds'], 1425974)
        self.assertEqual(decision['max_age_seconds'], 365000000)
        self.assertEqual(raw, before)

    def test_original_date_future_and_past_checks_remain(self):
        for delta in (-301, 301):
            with self.subTest(delta=delta), self.assertRaisesRegex(c.Refused, 'HTTP_DATE_FRESHNESS'):
                w.freshness_decision(headers(delta=delta), 'wheel', NOW)
        for delta in (-300, 300): self.assertIsInstance(w.freshness_decision(headers(delta=delta), 'wheel', NOW), dict)

    def test_metadata_never_receives_artifact_exception(self):
        with self.assertRaisesRegex(c.Refused, 'HTTP_FRESHNESS'):
            w.freshness_decision(headers(), 'metadata', NOW)
        self.assertEqual(w.freshness_decision(headers('3600', 's-maxage=1'), 'metadata', NOW)['policy'],
                         'ORIGINAL_METADATA_AGE_3600')

    def test_no_immutable_or_no_maxage_keeps_legacy_age_bound(self):
        for control in (None, 'public', 'max-age=365000000, public', 'immutable, public'):
            with self.subTest(control=control), self.assertRaisesRegex(c.Refused, 'HTTP_FRESHNESS'):
                w.freshness_decision(headers('3601', control), 'wheel', NOW)
            self.assertEqual(w.freshness_decision(headers('3600', control), 'wheel', NOW)['policy'], 'ORIGINAL_WHEEL_AGE_3600')

    def test_missing_age_uses_explicit_legacy_zero_not_immutable_exception(self):
        raw = headers(); del raw['age']
        result = w.freshness_decision(raw, 'wheel', NOW)
        self.assertEqual(result['policy'], 'ORIGINAL_WHEEL_AGE_3600')
        self.assertTrue(result['Age_absent_default_zero'])

    def test_expired_equal_maxage_and_invalid_age_refuse(self):
        for age in ('365000000', '365000001'):
            with self.subTest(age=age), self.assertRaisesRegex(c.Refused, 'HTTP_IMMUTABLE_AGE_EXPIRED'):
                w.freshness_decision(headers(age), 'wheel', NOW)
        for age in ('-1', '+1', '1.5', '1e6', 'unknown', '2147483648', '9'*20):
            with self.subTest(age=age), self.assertRaises(c.Refused): w.freshness_decision(headers(age), 'wheel', NOW)

    def test_smaxage_conflicts_duplicates_and_bad_numbers_never_fallback(self):
        controls = ['max-age=365000000, immutable, s-maxage=10', 'max-age=10, max-age=20, immutable',
            'max-age=10, MAX-AGE=20, immutable', 'max-age=365000000, immutable, private',
            'max-age=365000000, immutable, no-cache', 'max-age=365000000, immutable, no-store',
            'max-age="365000000", immutable', 'max-age=-1, immutable', 'max-age=1.5, immutable',
            'max-age=2147483648, immutable', 'max-age, immutable', 'max-age=100, immutable=yes',
            'max-age=100, immutable, immutable', '', 'max-age=100,,immutable']
        for control in controls:
            # Even a legacy-small age cannot hide malformed/conflicting policy.
            with self.subTest(control=control), self.assertRaises(c.Refused):
                w.freshness_decision(headers('1', control), 'wheel', NOW)

    def test_cache_control_case_and_directive_bounds(self):
        self.assertEqual(w.cache_directives('MAX-AGE=365000000, IMMUTABLE, PUBLIC')['max-age'], 365000000)
        for value in ('a'*2049, ','.join('d'+str(i) for i in range(33))):
            with self.assertRaises(c.Refused): w.cache_directives(value)

    def test_transport_preserves_repeated_cache_fields_for_refusal(self):
        actual = SimpleNamespace(headers={'cache-control': 's-maxage=10'},
            response=SimpleNamespace(getheaders=lambda: [('Cache-Control', 'max-age=365000000, immutable'), ('Cache-Control', 's-maxage=10')]))
        with patch.object(c.HTTPTransport, 'open', return_value=actual):
            response = w.HTTPTransport().open('MOCK_NO_NETWORK', 20)
        self.assertEqual(response.raw_cache_control_values, ['max-age=365000000, immutable', 's-maxage=10'])
        self.assertEqual(response.headers, {'cache-control': 's-maxage=10'})


class FourthAttemptFixtureTests(unittest.TestCase):
    def setUp(self):
        self.previous = f.SecondSuccessorTests()
        self.previous.setUp(); self.addCleanup(self.previous.doCleanups)
        self.root, self.source = self.previous.root, self.previous.source
        self.patch = patch.object(c, 'PYPDF', self.source.files['pypdf'])
        self.patch.start(); self.addCleanup(self.patch.stop)
        first = next(iter(self.previous.responses))
        self.previous.responses[first].headers.update(headers())
        result = self.previous.run_collect()
        self.assertEqual(result['reason'], 'HTTP_FRESHNESS')
        self.assertEqual(result['budget']['attempts'], {'GET': 10, 'metadata_GET': 8, 'wheel_GET': 2})
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 33554432)
        self.original = {str(p.relative_to(self.root)): p.read_bytes()
            for scope in (c.OUTPUT, w.n.OUTPUT, w.v.OUTPUT) for p in (self.root/scope).rglob('*') if p.is_file()}
        self.methods = c.json_body((ROOT/w.METHODS).read_bytes())
        self.methods['root_sha256'] = c.sha(str(self.root).encode())
        self.methods['previous_methods_ref'] = self.save('configs/e01_pypdf701_acquisition_v1_2_20261115.json',
                                                        c.packed(self.previous.methods))
        terminal = self.previous.terminal()
        refs = {ref['path']: {k: ref[k] for k in ('bytes', 'sha256')} for ref in terminal['artifacts']}
        raw = (self.root/w.v.OUTPUT/'TERMINAL.json').read_bytes(); refs['TERMINAL.json'] = {'bytes': len(raw), 'sha256': c.sha(raw)}
        self.methods['previous_refs'] = refs
        physical = sum(ref['bytes'] for ref in refs.values())
        raw_output = sum(ref['bytes'] for name, ref in refs.items() if name.startswith(('metadata/', 'wheels/')))
        prior = self.previous.methods['prior_cumulative']
        self.methods['prior_cumulative'] = {'owned_bytes': prior['owned_bytes']+physical,
            'control_bytes': prior['control_bytes']+physical-raw_output, 'events': 20, 'budget': terminal['budget']}
        wheel_name = 'wheels/'+c.PYPDF['filename']
        self.methods['cached_pypdf_ref'] = {'path': w.v.OUTPUT+'/'+wheel_name, **refs[wheel_name]}
        self.methods['freshness_diagnostic_ref'] = self.save('data/processed/e01_cffi_freshness_diagnostic_20261115_01/TERMINAL.json',
            c.packed({'status': 'HEAD_METADATA_ONLY_COMPLETE', 'HEAD_attempts': 1, 'GET_attempts': 0,
                'application_body_bytes_read': 0, 'HTTP_status': 200, 'url': first, 'observed_at_utc': NOW.isoformat(),
                'headers': {'Date': headers()['date'], 'Age': '1425974', 'Cache-Control': 'max-age=365000000, immutable, public',
                            'Content-Length': str(self.source.files['cffi']['size'])}}))
        self.responses = {self.source.files[name]['url']: old.Response(self.source.responses[self.source.files[name]['url']].body,
            'wheel', headers=headers()) for name in list(c.VERSIONS)[1:]}
        self.transport = old.Transport(self.responses)

    def save(self, name, raw):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {'path': name, 'bytes': len(raw), 'sha256': c.sha(raw)}
    def collector(self):
        return w.Collector(self.root, self.methods, self.transport,
            clock=lambda: self.source.time[0], cpu=lambda: self.source.cpu[0], utc=lambda: NOW)
    def run_collect(self): return self.collector().run()
    def terminal(self): return c.json_body((self.root/w.OUTPUT/'TERMINAL.json').read_bytes())
    def unchanged(self):
        after = {str(p.relative_to(self.root)): p.read_bytes()
            for scope in (c.OUTPUT, w.n.OUTPUT, w.v.OUTPUT) for p in (self.root/scope).rglob('*') if p.is_file()}
        self.assertEqual(self.original, after)

    def test_real_methods_table_includes_all_three_terminal_writes(self):
        m = c.json_body((ROOT/w.METHODS).read_bytes())
        previous = c.json_body((ROOT/m['previous_methods_ref']['path']).read_bytes())
        total = sum(ref['bytes'] for ref in m['previous_refs'].values())
        raw = sum(ref['bytes'] for name, ref in m['previous_refs'].items() if name.startswith(('metadata/', 'wheels/')))
        self.assertEqual(len(m['previous_refs']), 17)
        self.assertEqual(m['previous_refs']['TERMINAL.json']['bytes'], 3234)
        self.assertEqual(total, 1410819); self.assertEqual(raw, 1364907)
        self.assertEqual(m['prior_cumulative']['owned_bytes'], previous['prior_cumulative']['owned_bytes']+total)
        self.assertEqual(m['prior_cumulative']['control_bytes'], previous['prior_cumulative']['control_bytes']+total-raw)
        self.assertEqual(m['prior_cumulative']['owned_bytes'], 3041964)
        self.assertEqual(m['prior_cumulative']['control_bytes'], 134401)

    def test_complete_four_gets_aged_immutable_wheels_all_charges_retained(self):
        raw_headers = {url: dict(response.headers) for url, response in self.responses.items()}
        with patch.object(c.zipfile.ZipFile, 'extractall', side_effect=AssertionError('NO_EXTRACTION')):
            result = self.run_collect()
        self.assertEqual(result['status'], 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        self.assertEqual(len(self.transport.calls), 4); self.assertNotIn(c.PYPDF['url'], self.transport.calls)
        self.assertEqual(result['budget']['attempts'], {'GET': 14, 'metadata_GET': 8, 'wheel_GET': 6})
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 33554432+sum(len(r.body) for r in self.responses.values()))
        self.assertEqual(c.CAPS['GET'], 13); self.assertEqual(c.CAPS['wheel_GET'], 5)
        self.assertEqual({url: response.headers for url, response in self.responses.items()}, raw_headers)
        lock = c.json_body((self.root/w.OUTPUT/'hashlock.json').read_bytes())
        self.assertEqual(len(lock['wheels']), 5); self.assertFalse(lock['ready_for_install'])
        self.assertEqual(lock['failed_wheel_GET_charges_retained'], 33554432)
        self.unchanged()

    def test_raw_headers_and_decision_durably_recorded_without_faking(self):
        self.run_collect()
        events = [c.json_body(path.read_bytes()) for path in (self.root/w.OUTPUT/'events').glob('*.json')]
        decisions = [event for event in events if event['kind'] == 'RAW_HTTP_HEADER_DECISION']
        self.assertEqual(len(decisions), 4)
        for event in decisions:
            self.assertEqual(event['raw_headers']['age'], '1425974')
            self.assertEqual(event['raw_headers']['cache-control'], 'max-age=365000000, immutable, public')
            self.assertEqual(event['decision']['policy'], 'FIXED_IMMUTABLE_ARTIFACT_UNIQUE_MAX_AGE')
        self.assertEqual(self.terminal()['cumulative_root_authorized_GET_cap'], 14)

    def test_conflicting_shared_cache_field_refuses_before_body_and_records_raw(self):
        response = self.responses[next(iter(self.responses))]
        response.headers['cache-control'] += ', s-maxage=10'
        result = self.run_collect()
        self.assertEqual(result['reason'], 'CACHE_CONTROL_SHARED_MAXAGE_REFUSED')
        self.assertEqual(response.offset, 0); self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 50331648)
        event = c.json_body((self.root/w.OUTPUT/'events/23.json').read_bytes())
        self.assertEqual(event['decision']['status'], 'REFUSED')
        self.assertIn('s-maxage=10', event['raw_headers']['cache-control'])

    def test_repeated_http_cache_fields_are_not_last_wins(self):
        response = self.responses[next(iter(self.responses))]
        response.raw_cache_control_values = [response.headers['cache-control'], 's-maxage=10']
        result = self.run_collect()
        self.assertEqual(result['reason'], 'CACHE_CONTROL_DUPLICATE_FIELD'); self.assertEqual(response.offset, 0)
        self.assertEqual(len(self.transport.calls), 1)

    def test_stale_date_still_refuses_before_body_even_if_immutable(self):
        response = self.responses[next(iter(self.responses))]; response.headers.update(headers(delta=-301))
        result = self.run_collect()
        self.assertEqual(result['reason'], 'HTTP_DATE_FRESHNESS'); self.assertEqual(response.offset, 0)
        self.assertEqual(len(self.transport.calls), 1)

    def test_missing_immutable_does_not_get_age_exception(self):
        response = self.responses[next(iter(self.responses))]
        response.headers['cache-control'] = 'max-age=365000000, public'
        result = self.run_collect()
        self.assertEqual(result['reason'], 'HTTP_FRESHNESS'); self.assertEqual(response.offset, 0)

    def test_hash_mismatch_remains_refused_after_cache_acceptance(self):
        first = next(iter(self.responses)); self.responses[first] = old.Response(b'WRONG', 'wheel', headers=headers())
        result = self.run_collect()
        self.assertEqual(result['reason'], 'WHEEL_IDENTITY'); self.assertFalse((self.root/w.OUTPUT/'hashlock.json').exists())
        self.unchanged()

    def test_binary_mime_accepted_directly_and_never_rewritten(self):
        for response in self.responses.values(): response.headers['content-type'] = 'binary/octet-stream'
        result = self.run_collect()
        self.assertEqual(result['status'], 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        self.assertTrue(all(response.headers['content-type'] == 'binary/octet-stream' for response in self.responses.values()))
        events = [c.json_body(path.read_bytes()) for path in (self.root/w.OUTPUT/'events').glob('*.json')]
        self.assertTrue(all(event['raw_headers']['content-type'] == 'binary/octet-stream'
                            for event in events if event['kind'] == 'RAW_HTTP_HEADER_DECISION'))

    def test_compressed_response_still_refused_before_body(self):
        response = self.responses[next(iter(self.responses))]; response.headers['content-encoding'] = 'gzip'
        result = self.run_collect()
        self.assertEqual(result['reason'], 'CONTENT_ENCODING'); self.assertEqual(response.offset, 0)
        self.assertEqual(len(self.transport.calls), 1)

    def test_redirect_not_followed_and_raw_decision_retained(self):
        response = self.responses[next(iter(self.responses))]; response.status = 302
        result = self.run_collect()
        self.assertEqual(result['reason'], 'HTTP_STATUS'); self.assertEqual(response.offset, 0)
        self.assertEqual(len(self.transport.calls), 1)

    def test_content_length_mismatch_never_settles_partial_body_as_success(self):
        response = self.responses[next(iter(self.responses))]
        response.headers['content-length'] = str(len(response.body)+1)
        result = self.run_collect()
        self.assertEqual(result['reason'], 'CONTENT_LENGTH')
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 50331648)
        self.assertFalse((self.root/w.OUTPUT/'hashlock.json').exists())

    def test_stream_without_declared_length_cannot_reach_reserved_cap(self):
        first = next(iter(self.responses)); response = old.Response(b'x'*c.CAPS['wheel_each'], 'wheel', headers=headers())
        del response.headers['content-length']; self.responses[first] = response
        result = self.run_collect()
        self.assertEqual(result['reason'], 'BODY_CAP')
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 50331648)
        self.assertEqual(self.terminal()['current_request']['observed_partial_body_bytes'], c.CAPS['wheel_each'])

    def test_deadline_for_saved_advisory_is_not_extended(self):
        collector = self.collector(); collector.utc = lambda: NOW+timedelta(seconds=3601)
        with self.assertRaisesRegex(c.Refused, 'SAVED_CURRENT_CAPTURE_STALE_OR_FUTURE'): collector.run()
        self.assertFalse((self.root/w.OUTPUT).exists()); self.assertEqual(self.transport.calls, [])

    def test_changed_previous_terminal_or_cached_wheel_is_not_adopted(self):
        path = self.root/self.methods['cached_pypdf_ref']['path']; raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(c.Refused, 'INPUT_HASH'): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_cumulative_get_allowance_is_exactly_one_more_and_cannot_reset(self):
        collector = self.collector(); collector.predecessor()
        self.assertEqual(collector.budget.attempts['GET'], 10)
        for _ in range(4): collector.budget.begin('wheel'); collector.budget.settle('wheel', 0)
        with self.assertRaisesRegex(c.Refused, 'REQUEST_CAP'): collector.budget.begin('wheel')
        with self.assertRaisesRegex(c.Refused, 'REQUEST_CAP'): collector.budget.begin('metadata')
        self.assertEqual(collector.budget.attempts['GET'], 14)
        self.methods['additional_technical_GET'] = 2
        with self.assertRaisesRegex(c.Refused, 'METHODS_IDENTITY'): self.run_collect()

    def test_no_new_pypdf_or_unknown_url_dispatch(self):
        collector = self.collector(); collector.predecessor()
        for url in (c.PYPDF['url'], 'https://example.com/UNKNOWN.whl'):
            with self.assertRaisesRegex(c.Refused, 'FOUR_FIXED_COMPANIONS_ONLY'):
                collector.fetch(url, 'wheel', 'NEVER.whl', 'NEVER.whl')
        self.assertEqual(self.transport.calls, [])

    def test_duplicate_or_failed_scope_cannot_replay(self):
        self.run_collect(); old_terminal = (self.root/w.OUTPUT/'TERMINAL.json').read_bytes(); self.transport.calls.clear()
        with self.assertRaisesRegex(c.Refused, 'SUCCESSOR_ALREADY_CONSUMED'): self.run_collect()
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(old_terminal, (self.root/w.OUTPUT/'TERMINAL.json').read_bytes())

    def test_timeout_keeps_all_old_charges_and_new_full_reservation(self):
        first = next(iter(self.responses)); self.responses[first] = TimeoutError('DO_NOT_LEAK')
        result = self.run_collect()
        self.assertEqual(result['reason'], 'TimeoutError'); self.assertEqual(self.transport.calls, [first])
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 50331648)
        self.assertNotIn(b'DO_NOT_LEAK', (self.root/w.OUTPUT/'TERMINAL.json').read_bytes())


if __name__ == '__main__':
    old.guarded_test_main()
