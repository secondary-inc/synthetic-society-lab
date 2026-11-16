"""Authored stopped predecessors/cache/HEAD bytes. No real acquisition."""
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


f = load('p1_1_authored', ROOT/'tests/test_e01_pypdf701_acquisition_v1_1.py')
v = load('p1_2_collector', ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_2.py')
c = v.c


class SecondSuccessorTests(unittest.TestCase):
    def setUp(self):
        self.previous = f.AcquisitionContinuationTests()
        self.previous.setUp(); self.addCleanup(self.previous.doCleanups)
        self.root = self.previous.root
        self.source = self.previous.fixture
        self.patch = patch.object(c, 'PYPDF', self.source.files['pypdf'])
        self.patch.start(); self.addCleanup(self.patch.stop)
        pypdf_url = self.source.files['pypdf']['url']
        self.previous.transport.responses[pypdf_url] = f.f.Response(self.source.responses[pypdf_url].body,
            'wheel', headers={'content-type': 'binary/octet-stream'})
        result = self.previous.run_collect()
        self.assertEqual(result['reason'], 'CONTENT_TYPE')
        self.assertEqual(result['budget']['attempts'], {'GET': 9, 'metadata_GET': 8, 'wheel_GET': 1})
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], c.CAPS['wheel_each'])
        self.original = {str(p.relative_to(self.root)): p.read_bytes()
            for scope in (c.OUTPUT, v.n.OUTPUT) for p in (self.root/scope).rglob('*') if p.is_file()}
        self.methods = c.json_body((ROOT/v.METHODS).read_bytes())
        self.methods['root_sha256'] = c.sha(str(self.root).encode())
        self.methods['previous_methods_ref'] = self.save('configs/e01_pypdf701_acquisition_v1_1_20261115.json',
                                                        c.packed(self.previous.methods))
        terminal = self.previous.terminal()
        refs = {ref['path']: {k: ref[k] for k in ('bytes', 'sha256')} for ref in terminal['artifacts']}
        raw = (self.root/v.n.OUTPUT/'TERMINAL.json').read_bytes()
        refs['TERMINAL.json'] = {'bytes': len(raw), 'sha256': c.sha(raw)}
        self.methods['previous_refs'] = refs
        physical = sum(ref['bytes'] for ref in refs.values())
        metadata = sum(ref['bytes'] for name, ref in refs.items() if name.startswith('metadata/'))
        old = self.previous.methods['predecessor']
        self.methods['prior_cumulative'] = {'owned_bytes': old['owned_bytes']+physical,
            'control_bytes': old['control_bytes']+physical-metadata, 'events': 17, 'budget': terminal['budget']}
        self.methods['cached_pypdf_ref'] = self.save('data/processed/e01_pypdf_fresh_install_20261112/'+c.PYPDF['filename'],
                                                   self.source.responses[pypdf_url].body)
        self.methods['mime_diagnostic_ref'] = self.save('data/processed/e01_pypdf701_mime_diagnostic_20261115_01/TERMINAL.json',
            c.packed({'status': 'HEAD_METADATA_ONLY_COMPLETE', 'HEAD_attempts': 2, 'application_body_bytes_read': 0,
                'observations': [{'url': c.PYPDF['url'], 'HTTP_status': 200, 'application_body_bytes_read': 0,
                    'headers': {'Content-Type': 'binary/octet-stream', 'Content-Length': str(c.PYPDF['size']), 'Location': None}},
                    {'url': self.source.files['cffi']['url'], 'HTTP_status': 200,
                     'headers': {'Content-Type': 'application/octet-stream', 'Content-Length': str(self.source.files['cffi']['size'])}}]}))
        self.responses = {self.source.files[name]['url']: f.f.Response(
            self.source.responses[self.source.files[name]['url']].body, 'wheel') for name in list(c.VERSIONS)[1:]}
        self.transport = f.f.Transport(self.responses)

    def save(self, name, raw):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {'path': name, 'bytes': len(raw), 'sha256': c.sha(raw)}

    def collector(self):
        return v.Collector(self.root, self.methods, self.transport,
            clock=lambda: self.source.time[0], cpu=lambda: self.source.cpu[0], utc=lambda: f.f.NOW)

    def run_collect(self): return self.collector().run()
    def terminal(self): return c.json_body((self.root/v.OUTPUT/'TERMINAL.json').read_bytes())

    def unchanged(self):
        current = {str(p.relative_to(self.root)): p.read_bytes()
            for scope in (c.OUTPUT, v.n.OUTPUT) for p in (self.root/scope).rglob('*') if p.is_file()}
        self.assertEqual(self.original, current)

    def test_actual_methods_ref_table_includes_both_terminals(self):
        m = c.json_body((ROOT/v.METHODS).read_bytes())
        p = c.json_body((ROOT/m['previous_methods_ref']['path']).read_bytes())
        total = sum(ref['bytes'] for ref in m['previous_refs'].values())
        metadata = sum(ref['bytes'] for name, ref in m['previous_refs'].items() if name.startswith('metadata/'))
        self.assertEqual(len(m['previous_refs']), 19)
        self.assertEqual(m['previous_refs']['TERMINAL.json']['bytes'], 5574)
        self.assertEqual(p['predecessor']['refs']['TERMINAL.json']['bytes'], 2667)
        self.assertEqual(total, 1030064)
        self.assertEqual(metadata, 948771)
        self.assertEqual(m['prior_cumulative']['owned_bytes'], p['predecessor']['owned_bytes']+total)
        self.assertEqual(m['prior_cumulative']['control_bytes'], p['predecessor']['control_bytes']+total-metadata)
        self.assertEqual(m['prior_cumulative']['owned_bytes'], 1631145)
        self.assertEqual(m['prior_cumulative']['control_bytes'], 88489)

    def test_complete_cache_plus_only_four_gets_and_full_failed_hold_retained(self):
        with patch.object(c.zipfile.ZipFile, 'extractall', side_effect=AssertionError('NO_EXTRACTION')):
            result = self.run_collect()
        self.assertEqual(result['status'], 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        self.assertEqual(len(self.transport.calls), 4)
        self.assertNotIn(c.PYPDF['url'], self.transport.calls)
        self.assertTrue(all(response.closed for response in self.transport.returned))
        self.assertEqual(result['budget']['attempts'], {'GET': 13, 'metadata_GET': 8, 'wheel_GET': 5})
        old_metadata = self.methods['prior_cumulative']['budget']['body_bytes_charged']['metadata']
        self.assertEqual(result['budget']['body_bytes_charged']['metadata'], old_metadata)
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], c.CAPS['wheel_each']+
                         sum(len(response.body) for response in self.responses.values()))
        lock = c.json_body((self.root/v.OUTPUT/'hashlock.json').read_bytes())
        self.assertEqual(len(lock['wheels']), 5)
        self.assertFalse(lock['ready_for_install']); self.assertFalse(lock['qualification_or_source_authority'])
        self.assertEqual(lock['failed_pypdf_GET_charge_retained'], 16777216)
        self.assertEqual(lock['wheels'][0]['acquisition_origin'], 'EXACT_HASHED_CACHE_REUSE_PREVIOUSLY_ACCEPTED_20261112')
        for item in lock['wheels']:
            ref = item['artifact_ref']
            self.assertEqual(c.sha((self.root/v.OUTPUT/ref['path']).read_bytes()), item['sha256'])
        self.unchanged()

    def test_new_binary_mime_recorded_raw_and_only_normalized_for_frozen_guard(self):
        for response in self.responses.values(): response.headers['content-type'] = 'binary/octet-stream'
        result = self.run_collect()
        self.assertEqual(result['status'], 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        events = [c.json_body(path.read_bytes()) for path in (self.root/v.OUTPUT/'events').glob('*.json')]
        headers = [event for event in events if event['kind'] == 'WHEEL_RESPONSE_MEDIA']
        self.assertEqual(len(headers), 4)
        for event in headers:
            self.assertEqual(event['raw_content_type'], 'binary/octet-stream')
            self.assertEqual(event['mapping'], 'binary/octet-stream_TO_application/octet-stream')
        self.assertTrue(all(response.headers['content-type'] == 'binary/octet-stream' for response in self.responses.values()))

    def test_existing_zip_and_octet_types_unchanged(self):
        for response in self.responses.values(): response.headers['content-type'] = 'application/zip; authored=yes'
        result = self.run_collect()
        self.assertEqual(result['status'], 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        events = [c.json_body(p.read_bytes()) for p in (self.root/v.OUTPUT/'events').glob('*.json')]
        self.assertTrue(all(e['mapping'] == 'UNCHANGED' for e in events if e['kind'] == 'WHEEL_RESPONSE_MEDIA'))

    def test_unknown_mime_stops_first_companion_and_retains_another_full_hold(self):
        self.responses[next(iter(self.responses))].headers['content-type'] = 'text/html'
        result = self.run_collect()
        self.assertEqual(result['reason'], 'UNKNOWN_WHEEL_MEDIA')
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 2*c.CAPS['wheel_each'])
        self.assertTrue(self.transport.returned[0].closed)
        self.assertFalse((self.root/v.OUTPUT/'hashlock.json').exists())
        self.unchanged()

    def test_cache_hash_tamper_or_missing_refuses_without_get_or_new_scope(self):
        path = self.root/self.methods['cached_pypdf_ref']['path']; raw = path.read_bytes()
        path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(c.Refused, 'INPUT_HASH'): self.run_collect()
        self.assertEqual(self.transport.calls, [])
        self.assertFalse((self.root/v.OUTPUT).exists())

    def test_missing_cache_no_refetch(self):
        (self.root/self.methods['cached_pypdf_ref']['path']).unlink()
        with self.assertRaises(FileNotFoundError): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_cache_zip_failure_precedes_all_companion_requests(self):
        with patch.object(c, 'inspect_wheel', side_effect=c.Refused('AUTHORED_ZIP_CRC')):
            result = self.run_collect()
        self.assertEqual(result['reason'], 'AUTHORED_ZIP_CRC')
        self.assertEqual(self.transport.calls, [])
        self.assertFalse((self.root/v.OUTPUT/'wheels'/c.PYPDF['filename']).exists())

    def test_wrong_head_type_or_body_evidence_refuses(self):
        ref = self.methods['mime_diagnostic_ref']; doc = c.json_body((self.root/ref['path']).read_bytes())
        doc['application_body_bytes_read'] = 1
        self.methods['mime_diagnostic_ref'] = self.save(ref['path'], c.packed(doc))
        with self.assertRaisesRegex(c.Refused, 'MIME_DIAGNOSTIC'): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_changed_head_media_is_not_supported_by_diagnostic(self):
        ref = self.methods['mime_diagnostic_ref']; doc = c.json_body((self.root/ref['path']).read_bytes())
        doc['observations'][0]['headers']['Content-Type'] = 'text/plain'
        self.methods['mime_diagnostic_ref'] = self.save(ref['path'], c.packed(doc))
        with self.assertRaisesRegex(c.Refused, 'MIME_PRIMARY_EVIDENCE'): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_previous_body_tamper_refuses(self):
        path = self.root/v.n.OUTPUT/'metadata/pypdf-provenance.json'
        raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(c.Refused, 'INPUT_HASH'): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_bad_cumulative_write_count_refuses_before_marker(self):
        self.methods['prior_cumulative']['owned_bytes'] -= 1
        with self.assertRaisesRegex(c.Refused, 'CUMULATIVE_WRITE_ACCOUNTING'): self.run_collect()
        self.assertFalse((self.root/v.OUTPUT).exists())

    def test_stale_saved_current_capture_refuses_no_refresh(self):
        for delta in (-1, 3601):
            collector = self.collector(); collector.utc = lambda: f.f.NOW+timedelta(seconds=delta)
            with self.subTest(delta=delta), self.assertRaises(c.Refused): collector.run()
        self.assertEqual(self.transport.calls, [])

    def test_no_extra_metadata_request_allowance(self):
        collector = self.collector(); collector.predecessor()
        with self.assertRaisesRegex(c.Refused, 'REQUEST_CAP'):
            collector.fetch(c.PROVENANCE, 'metadata', 'NEVER.json')
        self.assertEqual(self.transport.calls, [])

    def test_transport_itself_refuses_pypdf_or_unknown_url_before_http(self):
        collector = self.collector(); collector.predecessor()
        for url in (c.PYPDF['url'], 'https://example.com/OTHER.whl'):
            with self.subTest(url=url), self.assertRaisesRegex(c.Refused, 'COMPANION_ONLY'):
                collector.transport.open(url, 20)
        self.assertEqual(self.transport.calls, [])

    def test_companion_timeout_no_retry_unknown_full_hold_and_redaction(self):
        first = next(iter(self.responses)); self.responses[first] = TimeoutError('DO_NOT_LEAK')
        result = self.run_collect()
        self.assertEqual(result['reason'], 'TimeoutError')
        self.assertEqual(self.transport.calls, [first])
        self.assertEqual(result['budget']['body_bytes_charged']['wheel'], 2*c.CAPS['wheel_each'])
        self.assertNotIn(b'DO_NOT_LEAK', (self.root/v.OUTPUT/'TERMINAL.json').read_bytes())
        self.unchanged()

    def test_companion_body_hash_still_required_after_mime_mapping(self):
        first = next(iter(self.responses)); self.responses[first] = f.f.Response(b'WRONG_BYTES', 'wheel',
            headers={'content-type': 'binary/octet-stream'})
        result = self.run_collect()
        self.assertEqual(result['reason'], 'WHEEL_IDENTITY')
        self.assertEqual(len(self.transport.calls), 1)
        self.assertFalse((self.root/v.OUTPUT/'hashlock.json').exists())

    def test_redirect_is_not_followed_or_retried(self):
        self.responses[next(iter(self.responses))].status = 302
        result = self.run_collect()
        self.assertEqual(result['reason'], 'HTTP_STATUS')
        self.assertEqual(len(self.transport.calls), 1)

    def test_duplicate_or_partial_successor_never_replayed(self):
        self.run_collect(); old = (self.root/v.OUTPUT/'TERMINAL.json').read_bytes(); self.transport.calls.clear()
        with self.assertRaisesRegex(c.Refused, 'SUCCESSOR_ALREADY_CONSUMED'): self.run_collect()
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(old, (self.root/v.OUTPUT/'TERMINAL.json').read_bytes())

    def test_alias_input_or_output_refuses_before_http(self):
        path = self.root/self.methods['cached_pypdf_ref']['path']
        other = self.root/'AUTHORED_CACHE'; other.write_bytes(path.read_bytes()); path.unlink(); path.symlink_to(other)
        with self.assertRaises(c.Refused): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_larger_limits_and_unknown_media_allowlist_are_not_accepted(self):
        for key, value in [('allowed_wheel_media', ['text/html']), ('remaining_GET_split', {'total': 5}),
                           ('continuation_limits', {}), ('output', v.n.OUTPUT)]:
            original = self.methods[key]; self.methods[key] = value
            with self.subTest(key=key), self.assertRaises(c.Refused): self.run_collect()
            self.methods[key] = original
        self.assertEqual(self.transport.calls, [])

    def test_cumulative_output_events_and_cpu_not_reset(self):
        collector = self.collector(); collector.predecessor()
        self.assertEqual(collector.written, self.methods['prior_cumulative']['owned_bytes'])
        self.assertEqual(collector.control, self.methods['prior_cumulative']['control_bytes'])
        self.assertEqual(collector.events, 17)
        for wall, cpu in ((120, 0), (0, 30), (-1, 0), (0, -1)):
            self.source.time[0], self.source.cpu[0] = wall, cpu
            with self.subTest(wall=wall, cpu=cpu), self.assertRaises(c.Refused): collector.budget.check()
            self.source.time[0] = self.source.cpu[0] = 0


if __name__ == '__main__':
    f.f.guarded_test_main()
