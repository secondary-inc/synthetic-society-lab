"""MOCK bytes only. No real metadata, wheels, source, network or installation."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


f = load('p1_authored_fixtures', ROOT / 'tests/test_e01_pypdf701_acquisition_v1.py')
n = load('p1_continuation', ROOT / 'scripts/acquire_e01_pypdf701_artifacts_v1_1.py')
c = n.c


def row(name, ecosystem, affected, patched):
    return {'package': {'name': name, 'ecosystem': ecosystem},
            'vulnerable_version_range': affected, 'patched_versions': patched}


def distribution_pair():
    a = f.advisory('GHSA-4vvm-4w3v-6mr8', '<= 3.8.1', '>=3.9.0')
    a['vulnerabilities'].append(row('PyPDF2', 'pip', '>=2.2.0', ''))
    a['description'] = 'It is recommended to upgrade to `pypdf>=3.9.0`. PyPDF2 users should migrate to pypdf.'
    return a


class AdvisoryContinuationTests(unittest.TestCase):
    def test_actual_methods_reference_table_includes_terminal_write(self):
        # Public declared ref table only: no actual data/source/runtime reads.
        m = c.json_body((ROOT/n.METHODS).read_bytes())
        p = m['predecessor']
        self.assertEqual(len(p['refs']), 20)
        self.assertEqual(p['refs']['TERMINAL.json']['bytes'], 2667)
        total = sum(r['bytes'] for r in p['refs'].values())
        body = sum(r['bytes'] for name, r in p['refs'].items() if name.startswith('metadata/'))
        self.assertEqual(total, 601081)
        self.assertEqual(body, 593885)
        self.assertEqual(p['owned_bytes'], total)
        self.assertEqual(p['control_bytes'], total-body)
        self.assertEqual(p['control_bytes'], 7196)

    def test_all_observed_label_forms_assessed_not_discarded(self):
        a = f.advisory()
        a['vulnerabilities'] = [row('PyPDF2', 'pip', '<=1.27.4', '1.27.5'),
            row('pypdf', 'pypi', '<6.10.2', '>=6.10.2'), row('pypi', 'pip', '<6.21.4', '>=6.21.4')]
        report = n.assess_advisories([[a]])
        self.assertEqual(len(report['advisories'][0]['assessments']), 3)
        self.assertNotEqual(report['status'], 'BLOCKED_APPLICABLE_ADVISORY')
        for entry in report['advisories'][0]['assessments']:
            self.assertTrue(entry['label_uncertain'])

    def test_exact_prefix_retained_and_entire_expression_checked(self):
        a = f.advisory()
        a['vulnerabilities'] = [row('PyPDF2', 'pip', 'PyPDF2==2.10.5', 'PyPDF2>=2.10.6')]
        entry = n.assess_advisories([[a]])['advisories'][0]['assessments'][0]
        self.assertEqual(entry['range'], 'PyPDF2==2.10.5')
        self.assertEqual(entry['normalized_range'], '==2.10.5')
        self.assertEqual(entry['normalized_patched_versions'], '>=2.10.6')
        for expression in ('PyPDF2foo==2.10.5', 'pypdf==2.10.5', 'PyPDF2==2.10.5 OR >7',
                           'PyPDF2>=2.*', 'PyPDF2', 'PyPDF2~=2.10', '>=2.0rc1'):
            with self.subTest(expression=expression), self.assertRaises(c.Refused):
                n.normalized_range(expression, 'PyPDF2')

    def test_exact_paired_distribution_evidence_preserves_unpatched_pypdf2(self):
        report = n.assess_advisories([[distribution_pair()]])
        self.assertNotEqual(report['status'], 'BLOCKED_APPLICABLE_ADVISORY')
        old = report['advisories'][0]['assessments'][1]
        self.assertTrue(old['candidate_affected_conservatively'])
        self.assertTrue(old['candidate_distribution_excluded'])
        self.assertFalse(old['candidate_affected'])
        self.assertEqual(old['patched_versions'], '')

    def test_paired_exception_fails_closed_if_evidence_changes(self):
        for change in ('description', 'pair', 'range', 'patch', 'label'):
            a = distribution_pair()
            if change == 'description': a['description'] = 'UNKNOWN'
            if change == 'pair': a['vulnerabilities'].pop(0)
            if change == 'range': a['vulnerabilities'][1]['vulnerable_version_range'] = '>=2.2.1'
            if change == 'patch': a['vulnerabilities'][0]['patched_versions'] = '>=3.9.1'
            if change == 'label': a['vulnerabilities'][1]['package']['ecosystem'] = 'pypi'
            with self.subTest(change=change), self.assertRaises(c.Refused):
                n.assess_advisories([[a]])

    def test_other_open_ended_or_ambiguous_label_range_blocks(self):
        for name, eco in [('pypdf', 'pip'), ('PyPDF2', 'pip'), ('pypi', 'pip'), ('pypdf', 'pypi')]:
            a = f.advisory(affected='>=2.2.0', patched='')
            a['vulnerabilities'][0]['package'] = {'name': name, 'ecosystem': eco}
            with self.subTest(name=name, eco=eco):
                self.assertEqual(n.assess_advisories([[a]])['status'], 'BLOCKED_APPLICABLE_ADVISORY')

    def test_unknowns_duplicates_nonfinite_and_bad_patch_refuse(self):
        cases = []
        for name, eco in [('other', 'pip'), ('pypdf', 'npm'), (None, 'pip')]:
            a = f.advisory()
            a['vulnerabilities'][0]['package'] = {'name': name, 'ecosystem': eco}
            cases.append([a])
        for key, val in [('vulnerable_version_range', '<7.*'), ('patched_versions', 'latest')]:
            a = f.advisory(); a['vulnerabilities'][0][key] = val; cases.append([a])
        cases.extend([[], [f.advisory(), f.advisory()]])
        for case in cases:
            with self.subTest(case=case), self.assertRaises(c.Refused):
                n.assess_advisories([case])
        with self.assertRaises(c.Refused):
            c.json_body(b'{"x":NaN}')


class AcquisitionContinuationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = f.ArtifactAcquisitionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root
        self.patch = patch.object(c, 'PYPDF', self.fixture.files['pypdf'])
        self.patch.start()
        self.addCleanup(self.patch.stop)
        a = f.advisory('GHSA-xcjx-m2pj-8g79', '<=1.27.4', '1.27.5')
        a['vulnerabilities'][0]['package']['name'] = 'PyPDF2'
        b = f.advisory('GHSA-hm9v-vj3r-r55m', 'PyPDF2==2.10.5', 'PyPDF2>=2.10.6')
        b['vulnerabilities'][0]['package']['name'] = 'PyPDF2'
        self.advisories = [a, b, distribution_pair()]
        self.fixture.responses[f.c.API] = f.Response(c.packed(self.advisories))
        result = self.fixture.run_collect()
        self.assertEqual(result['reason'], 'ADVISORY_PACKAGE_MISSING')
        self.assertEqual(len(self.fixture.transport.calls), 6)
        self.original = {str(p.relative_to(self.root)): p.read_bytes() for p in (self.root/c.OUTPUT).rglob('*') if p.is_file()}
        terminal = self.fixture.terminal()
        refs = {r['path']: {'bytes': r['bytes'], 'sha256': r['sha256']} for r in terminal['artifacts']}
        terminal_raw = (self.root/c.OUTPUT/'TERMINAL.json').read_bytes()
        refs['TERMINAL.json'] = {'bytes': len(terminal_raw), 'sha256': c.sha(terminal_raw)}
        self.methods = c.json_body((ROOT/n.METHODS).read_bytes())
        self.methods['root_sha256'] = c.sha(str(self.root).encode())
        self.methods['predecessor'] = {'scope': c.OUTPUT,
            'methods_sha256': c.sha(c.packed(self.fixture.methods)), 'refs': refs,
            'budget': terminal['budget'], 'owned_bytes': sum(r['bytes'] for r in refs.values()),
            'control_bytes': sum(r['bytes'] for key, r in refs.items() if not key.startswith('metadata/')), 'events': 12}
        self.transport = f.Transport({key: val for key, val in self.fixture.responses.items()
                                      if key == c.PROVENANCE or key.startswith('https://files.pythonhosted.org/')})
        self.transport.responses[c.API] = f.Response(c.packed(self.advisories))

    def collector(self, **kwargs):
        return n.Collector(self.root, self.methods, self.transport,
            clock=lambda: self.fixture.time[0], cpu=lambda: self.fixture.cpu[0], utc=lambda: f.NOW, **kwargs)

    def run_collect(self): return self.collector().run()

    def terminal(self): return c.json_body((self.root/n.OUTPUT/'TERMINAL.json').read_bytes())

    def assert_original_unchanged(self):
        current = {str(p.relative_to(self.root)): p.read_bytes() for p in (self.root/c.OUTPUT).rglob('*') if p.is_file()}
        self.assertEqual(self.original, current)

    def rebind(self, name, value):
        raw = c.packed(value)
        (self.root/c.OUTPUT/name).write_bytes(raw)
        ref = {'bytes': len(raw), 'sha256': c.sha(raw)}
        self.methods['predecessor']['refs'][name] = ref
        return ref

    def rebind_indexed(self, name, value):
        ref = self.rebind(name, value)
        terminal = self.fixture.terminal()
        for item in terminal['artifacts']:
            if item['path'] == name:
                item.update(ref)
        self.rebind('TERMINAL.json', terminal)
        refs = self.methods['predecessor']['refs']
        self.methods['predecessor']['owned_bytes'] = sum(r['bytes'] for r in refs.values())
        self.methods['predecessor']['control_bytes'] = sum(r['bytes'] for key, r in refs.items() if not key.startswith('metadata/'))

    def test_complete_reuses_dated_bodies_with_seven_new_gets_and_old_accounting(self):
        old_bytes = self.methods['predecessor']['budget']['body_bytes_charged']['metadata']
        with patch.object(c.zipfile.ZipFile, 'extractall', side_effect=AssertionError('NO_EXTRACTION')):
            result = self.run_collect()
        self.assertEqual(result['status'], 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        self.assertEqual(len(self.transport.calls), 7)
        self.assertEqual(self.transport.calls[:2], [c.API, c.PROVENANCE])
        self.assertEqual(result['budget']['attempts'], {'GET': 13, 'metadata_GET': 8, 'wheel_GET': 5})
        self.assertEqual(result['budget']['body_bytes_charged']['metadata'], old_bytes +
                         len(self.transport.responses[c.API].body) + len(self.fixture.responses[c.PROVENANCE].body))
        terminal = self.terminal()
        self.assertEqual(terminal['predecessor'], self.methods['predecessor'])
        lock = c.json_body((self.root/n.OUTPUT/'hashlock.json').read_bytes())
        self.assertEqual(len(lock['wheels']), 5)
        self.assertFalse(lock['ready_for_install'])
        self.assertFalse(lock['qualification_or_source_authority'])
        assessment = c.json_body((self.root/n.OUTPUT/'advisory-assessment.json').read_bytes())
        self.assertTrue(assessment['fresh_current_response'])
        for wheel in lock['wheels']:
            for key in ('metadata_ref', 'artifact_ref'):
                ref = wheel[key]
                self.assertEqual(c.sha((self.root/n.OUTPUT/ref['path']).read_bytes()), ref['sha256'])
        self.assert_original_unchanged()

    def test_request_event_kind_immutable_and_request_kind_explicit(self):
        self.run_collect()
        event = c.json_body((self.root/n.OUTPUT/'events/13.json').read_bytes())
        self.assertEqual(event['kind'], 'REQUEST_RESERVED')
        self.assertEqual(event['request_kind'], 'metadata')
        self.assertEqual(event['sequence'], 13)
        self.assertEqual(event['budget']['attempts']['GET'], 7)
        collector = self.collector()
        for details in ({'kind': 'FORGED'}, {'sequence': 900}):
            with self.assertRaises(c.Refused): collector.event('RESPONSE_RECORDED', details)
        self.assert_original_unchanged()

    def test_duplicate_successor_and_partial_scope_cannot_replay(self):
        self.run_collect()
        old = (self.root/n.OUTPUT/'TERMINAL.json').read_bytes()
        self.transport.calls.clear()
        with self.assertRaises(c.Refused): self.run_collect()
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(old, (self.root/n.OUTPUT/'TERMINAL.json').read_bytes())

    def test_wrong_predecessor_hash_or_missing_reference_zero_requests(self):
        self.methods['predecessor']['refs']['metadata/pypdf.json']['sha256'] = 'f'*64
        with self.assertRaises(c.Refused): self.run_collect()
        self.assertEqual(self.transport.calls, [])
        self.assertFalse((self.root/n.OUTPUT).exists())

    def test_unknown_or_wrong_terminal_state_is_not_adopted(self):
        terminal = self.fixture.terminal()
        terminal['budget']['outstanding_body_hold'] = 1
        self.rebind('TERMINAL.json', terminal)
        with self.assertRaises(c.Refused): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_bad_predecessor_index_or_reservation_is_not_adopted(self):
        event = c.json_body((self.root/c.OUTPUT/'events/01.json').read_bytes())
        event['budget']['outstanding_body_hold'] = 0
        self.rebind_indexed('events/01.json', event)
        with self.assertRaisesRegex(c.Refused, 'PREDECESSOR_RESERVATION'): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_stale_or_future_cached_metadata_refuses_before_scope(self):
        from datetime import timedelta
        for delta in (-1, 14401):
            collector = self.collector()
            collector.utc = lambda: f.NOW + timedelta(seconds=delta)
            with self.subTest(delta=delta), self.assertRaises(c.Refused): collector.run()
        self.assertFalse((self.root/n.OUTPUT).exists())
        self.assertEqual(self.transport.calls, [])

    def test_wrong_methods_and_increased_limits_refuse(self):
        for key, value in [('caps', {}), ('output', c.OUTPUT), ('base_code_sha256', 'a'*64), ('continuation_limits', {})]:
            old = self.methods[key]; self.methods[key] = value
            with self.subTest(key=key), self.assertRaises(c.Refused): self.run_collect()
            self.methods[key] = old
        self.assertEqual(self.transport.calls, [])
        self.assertFalse((self.root/n.OUTPUT).exists())

    def test_alias_input_and_output_refuse(self):
        path = self.root/c.OUTPUT/'metadata/pypdf.json'
        other = self.root/'AUTHORED.json'; other.write_bytes(path.read_bytes()); path.unlink(); path.symlink_to(other)
        with self.assertRaises(c.Refused): self.run_collect()
        self.assertEqual(self.transport.calls, [])

    def test_failed_new_request_no_retry_full_hold_and_original_preserved(self):
        self.transport.responses[c.API] = TimeoutError('DO_NOT_LEAK_THIS')
        old = self.methods['predecessor']['budget']['body_bytes_charged']['metadata']
        result = self.run_collect()
        self.assertEqual(result['reason'], 'TimeoutError')
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(result['budget']['attempts']['GET'], 7)
        self.assertEqual(result['budget']['body_bytes_charged']['metadata'], old+c.CAPS['metadata_each'])
        self.assertNotIn('DO_NOT_LEAK_THIS', json.dumps(self.terminal()))
        self.assertFalse((self.root/n.OUTPUT/'hashlock.json').exists())
        self.assert_original_unchanged()

    def test_fresh_applicable_advisory_blocks_before_provenance_or_wheel(self):
        self.transport.responses[c.API] = f.Response(c.packed(
            self.advisories + [f.advisory('GHSA-neww-1234-5678', '<7.1.0', '>=7.1.0')]))
        result = self.run_collect()
        self.assertEqual(result['reason'], 'APPLICABLE_ADVISORY')
        self.assertEqual(self.transport.calls, [c.API])
        self.assertTrue((self.root/n.OUTPUT/'advisory-assessment.json').exists())

    def test_fresh_page_requiring_pagination_stops_without_second_get(self):
        after = c.API + '&after=AUTHORED_CURSOR'
        self.transport.responses[c.API] = f.Response(c.packed(self.advisories),
            headers={'link': '<' + after + '>; rel="next"'})
        result = self.run_collect()
        self.assertEqual(result['reason'], 'FRESH_ADVISORY_SINGLE_PAGE_CAP')
        self.assertEqual(self.transport.calls, [c.API])
        self.assertFalse((self.root/n.OUTPUT/'hashlock.json').exists())

    def test_changed_fresh_exception_refuses_before_wheels(self):
        a = distribution_pair(); a['description'] = 'CHANGED_PRIMARY_EVIDENCE'
        self.transport.responses[c.API] = f.Response(c.packed([a]))
        result = self.run_collect()
        self.assertEqual(result['reason'], 'DISTRIBUTION_EVIDENCE_MISMATCH')
        self.assertEqual(self.transport.calls, [c.API])

    def test_full_fresh_page_without_link_is_unknown_not_complete(self):
        page = [f.advisory(f'GHSA-{i:04d}-1234-5678') for i in range(100)]
        self.transport.responses[c.API] = f.Response(c.packed(page))
        result = self.run_collect()
        self.assertEqual(result['reason'], 'ADVISORY_TRUNCATION_UNKNOWN')
        self.assertEqual(self.transport.calls, [c.API])

    def test_successor_alias_refuses_without_get_or_old_scope_change(self):
        path = self.root/n.OUTPUT
        other = self.root/'AUTHORED_OTHER'; other.mkdir()
        path.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(c.Refused, 'OUTPUT_ALIAS'): self.run_collect()
        self.assertEqual(self.transport.calls, [])
        self.assert_original_unchanged()

    def test_cumulative_writes_and_event_caps_not_reset(self):
        collector = self.collector(); collector.predecessor()
        self.assertEqual(collector.written, self.methods['predecessor']['owned_bytes'])
        self.assertEqual(collector.control, self.methods['predecessor']['control_bytes'])
        self.assertEqual(collector.events, 12)
        collector.events = 64
        with self.assertRaises(c.Refused): collector.event('NOTE', {})
        collector.written = c.CAPS['owned_write_bytes']
        with self.assertRaises(c.Refused): collector.write('NO.json', b'{}')

    def test_remaining_request_and_body_allowances_are_cumulative(self):
        collector = self.collector(); collector.predecessor()
        self.assertEqual(collector.budget.attempts['GET'], 6)
        for _ in range(7):
            kind = 'wheel' if collector.budget.attempts['wheel_GET'] < 5 else 'metadata'
            collector.budget.begin(kind)
            collector.budget.settle(kind, 0)
        with self.assertRaises(c.Refused): collector.budget.begin('metadata')
        collector = self.collector(); collector.predecessor()
        collector.budget.bytes['metadata'] = c.CAPS['metadata_total']-2
        self.assertEqual(collector.budget.begin('metadata'), 2)
        collector.budget.settle('metadata')
        with self.assertRaises(c.Refused): collector.budget.begin('metadata')

    def test_continuation_wall_cpu_and_rollback_refuse(self):
        for time, cpu in ((120, 0), (0, 30), (-1, 0), (0, -1)):
            collector = self.collector()
            self.fixture.time[0], self.fixture.cpu[0] = time, cpu
            with self.subTest(time=time, cpu=cpu), self.assertRaises(c.Refused): collector.budget.check()
            self.fixture.time[0] = self.fixture.cpu[0] = 0

    def test_bad_wheel_preserves_failure_no_hashlock_and_no_install(self):
        url = self.fixture.files['pypdf']['url']
        self.transport.responses[url] = f.Response(b'NOT_A_WHEEL', 'wheel')
        result = self.run_collect()
        self.assertEqual(result['reason'], 'WHEEL_IDENTITY')
        self.assertEqual(len(self.transport.calls), 3)
        self.assertFalse((self.root/n.OUTPUT/'hashlock.json').exists())
        self.assert_original_unchanged()


if __name__ == '__main__':
    # Reuse the independently reviewed authored-only IO/process guard. Its
    # unittest.main discovers this module; actual data and subprocesses deny.
    f.guarded_test_main()
