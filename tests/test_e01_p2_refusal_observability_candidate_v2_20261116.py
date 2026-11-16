"""Authored effects only: no process, pip, installed package or native run."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

c = load('refusal_candidate', ROOT/'scripts/e01_p2_refusal_observability_candidate_v2_20261116.py')
p = load('frozen_v1_5', ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py')
t = load('frozen_authored_runner', ROOT/'tests/test_e01_pypdf701_install_v1_3.py')


class RefusalObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e01-refusal-MOCK-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.binding = {'base_prefix': str(self.root/'MOCK_BASE'), 'pip_root': 'MOCK_PIP/pip',
                        'pip_files': [], 'pip_metadata_ref': {'path': 'MOCK_PIP/pip.dist-info/METADATA'}}
        self.payload = {'wheels': [], 'remaining_output_bytes': 16}
        self.policy = c.diagnostic_policy_class(p.GuestPolicy)(self.root, self.binding, self.payload)

    def decoded(self): return json.loads(self.policy.refusal_journal.packed())

    def optional_probe_simulation(self, path):
        # Same discover/catch shape as pinned pip, with only the guard callback.
        # The fake executable is never launched.
        found = shutil.which('rustc', path=path)
        if found is not None:
            try: self.policy.audit('subprocess.Popen', (found, ['rustc', '--version'], None, None))
            except Exception: pass
        return 0

    def test_swallowed_refusal_still_fails_original_postcondition(self):
        tools = self.root/'MOCK_BIN'; tools.mkdir()
        executable = tools/'rustc'; executable.write_bytes(b'MOCK NEVER EXECUTE\n'); executable.chmod(0o700)
        self.assertEqual(self.optional_probe_simulation(str(tools)), 0)
        self.assertEqual(self.policy.violations, 1)
        event = self.decoded()['events'][0]
        self.assertEqual(event['code'], 'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED')
        self.assertEqual(event['operation'], 'SUBPROCESS')
        with self.assertRaisesRegex(p.Refused, 'GUEST_CAUGHT_VIOLATION'):
            p.need(self.policy.violations == 0, 'GUEST_CAUGHT_VIOLATION')

    def test_absent_authored_executable_has_no_denial(self):
        tools = self.root/'MOCK_EMPTY_BIN'; tools.mkdir()
        self.assertEqual(self.optional_probe_simulation(str(tools)), 0)
        self.assertEqual(self.policy.violations, 0)
        self.assertEqual(self.decoded()['events'], [])



    def test_direct_absolute_helper_native_and_network_attempts_remain_denied(self):
        for event, expected in [('subprocess.Popen', 'SUBPROCESS'), ('ctypes.dlopen', 'NATIVE_LOAD'),
                                ('socket.connect', 'SOCKET'), ('os.fork', 'FORK'), ('os.exec', 'EXEC')]:
            with self.assertRaisesRegex(p.Refused, 'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED'):
                self.policy.audit(event, ('MOCK_PRIVATE_ARGUMENT_MUST_NOT_BE_LOGGED',))
            self.assertEqual(self.decoded()['events'][-1]['operation'], expected)
        self.assertNotIn(b'MOCK_PRIVATE_ARGUMENT', self.policy.refusal_journal.packed())

    def test_read_and_write_denials_preserve_guard_and_record_only_code(self):
        for flags, expected in [(os.O_RDONLY, 'FILE_READ'), (os.O_WRONLY, 'FILE_WRITE')]:
            with self.assertRaises(p.Refused): self.policy.path(self.root/'MOCK_PRIVATE_PATH', flags)
            self.assertEqual(self.decoded()['events'][-1]['operation'], expected)
        self.assertNotIn(b'MOCK_PRIVATE_PATH', self.policy.refusal_journal.packed())
        self.assertFalse((self.root/'MOCK_PRIVATE_PATH').exists())

    def test_original_write_and_output_limits_remain_enforced(self):
        self.policy.writes = p.CAPS['guest_cumulative_write_bytes_each']
        with self.assertRaisesRegex(p.Refused, 'GUEST_WRITE_CAP'): self.policy.charge(b'X')
        with self.assertRaisesRegex(p.Refused, 'GUEST_OUTPUT_CAP'): self.policy.charge(b'X'*17, True)
        self.assertEqual([event['operation'] for event in self.decoded()['events']], ['WRITE_CHARGE', 'OUTPUT'])

    def test_diagnostic_error_cannot_suppress_original_refusal(self):
        with patch.object(self.policy.refusal_journal, 'record', side_effect=RuntimeError('MOCK_DIAGNOSTIC_FAILURE')):
            with self.assertRaisesRegex(p.Refused, 'GUEST_READ_OUTSIDE_ALLOWLIST'):
                self.policy.path(self.root/'MOCK_PRIVATE_PATH', os.O_RDONLY)
        self.assertEqual(self.policy.violations, 1)

    def test_journal_unknown_values_never_call_user_coercion(self):
        class Unsafe:
            def __str__(self): raise AssertionError('NO_COERCION')
            def __repr__(self): raise AssertionError('NO_REPR')
        self.policy.refusal_journal.record(Unsafe(), Unsafe())
        self.assertEqual(self.decoded()['events'][0]['code'], 'UNKNOWN_REFUSAL_CODE')
        self.assertEqual(self.decoded()['events'][0]['operation'], 'UNKNOWN')

    def test_journal_memory_and_serialization_are_finite(self):
        for _ in range(10000): self.policy.refusal_journal.record('GUEST_READ_OUTSIDE_ALLOWLIST', 'FILE_READ')
        value = self.decoded()
        self.assertEqual(len(value['events']), 16)
        self.assertEqual(value['total_events'], 10000)
        self.assertEqual(value['dropped_events'], 9984)
        self.assertLessEqual(len(self.policy.refusal_journal.packed()), c.MAX_JSON_BYTES)

    def test_saturated_counts_remain_finite(self):
        journal = self.policy.refusal_journal
        journal.total = c.MAX_COUNTER; journal.dropped = c.MAX_COUNTER
        for _ in range(c.MAX_EVENTS+1): journal.record('GUEST_OUTPUT_CAP', 'OUTPUT')
        self.assertTrue(self.decoded()['counter_saturated'])
        self.assertEqual(self.decoded()['total_events'], c.MAX_COUNTER)


    def test_original_frozen_installer_unchanged(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py').read_bytes()).hexdigest(),
                         '32162b1ddc0b31637842c3a5ecc0caa36dde6d6f32f2111a94c2336f59c178b4')

    def test_diagnostic_tightens_target_writes_but_retains_scope_writes(self):
        target = self.policy.target/'MOCK_FILE'
        with self.assertRaisesRegex(p.Refused, 'DIAGNOSTIC_WRITE_OUTSIDE_SCOPE'):
            self.policy.path(target, os.O_WRONLY)
        self.assertFalse(target.exists())
        self.policy.path(self.policy.stage/'MOCK_JOURNAL.json', os.O_WRONLY)
        self.assertEqual(self.decoded()['events'][0]['code'], 'DIAGNOSTIC_WRITE_OUTSIDE_SCOPE')

    def test_dry_run_arguments_change_only_one_explicit_flag(self):
        target = self.root/'MOCK_DIAGNOSTIC_NEVER_CREATED'
        requirements = self.root/'data/processed/e01_pypdf701_build_v1/diagnostic-v1/requirements.txt'
        original = p.pip_arguments('install', target, requirements)
        result = c.dry_run_arguments(original)
        self.assertEqual(result, original[:6]+['--dry-run']+original[6:])
        self.assertNotIn('--dry-run', original)
        self.assertEqual(result.count('--dry-run'), 1)
        self.assertFalse(target.exists())

    def test_dry_run_arguments_reject_unreviewed_or_missing_flags(self):
        original = p.pip_arguments('install', self.root/'MOCK_NEVER_CREATED',
                                   self.root/'data/processed/e01_pypdf701_build_v1/diagnostic-v1/requirements.txt')
        for altered in (original+['--dry-run'], original+['--user'],
                        [value for value in original if value != '--no-index'], ['pip', 'check']):
            with self.assertRaises(ValueError): c.dry_run_arguments(altered)

    def test_recording_paths_and_charges_always_delegate_to_original_guard(self):
        import ast
        tree = ast.parse((ROOT/'scripts/e01_p2_refusal_observability_candidate_v2_20261116.py').read_bytes())
        factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'recording_policy_class')
        cls = next(node for node in factory.body if isinstance(node, ast.ClassDef))
        for name in ('path', 'audit', 'charge', 'refuse'):
            method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
            self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                                and node.func.attr == name and isinstance(node.func.value, ast.Call)
                                and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == 'super'
                                for node in ast.walk(method)))

    def test_all_three_previous_targets_and_scopes_remain_unowned_and_unreadable(self):
        for name in (p.PRIOR_TARGET, p.LATEST_TARGET, p.TARGET, p.PRIOR_OUTPUT, p.LATEST_OUTPUT, p.OUTPUT):
            path = self.root/name/'MOCK_OLD_FILE'
            self.assertFalse(self.policy.owned(path))
            for flags in (os.O_RDONLY, os.O_WRONLY):
                with self.assertRaises(p.Refused): self.policy.path(path, flags)

    def test_diagnostic_route_never_creates_target_and_refuses_preexisting_target(self):
        self.assertFalse(self.policy.target.exists())
        self.policy.target.mkdir()
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC_TARGET_EXISTS'):
            c.diagnostic_policy_class(p.GuestPolicy)(self.root, self.binding, self.payload)

    def test_diagnostic_route_alias_refuses(self):
        self.policy.target.symlink_to(self.root/'MOCK_MISSING')
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC_ROUTE_ALIAS'):
            c.diagnostic_policy_class(p.GuestPolicy)(self.root, self.binding, self.payload)


if __name__ == '__main__':
    t.g.old.guarded_test_main()
