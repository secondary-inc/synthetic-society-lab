"""MOCK installer inputs and launcher. No real pip, venv, network or native run."""
import copy
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


f = load('p2_authored_p1_fixtures', ROOT/'tests/test_e01_pypdf701_acquisition_v1_2.py')
p = load('p2_installer', ROOT/'scripts/install_e01_pypdf701_runtime_v1.py')


def scheme(target):
    return {'purelib': str(target/'lib/python3.12/site-packages'), 'platlib': str(target/'lib/python3.12/site-packages'),
            'scripts': str(target/'bin'), 'data': str(target)}


class PureInstallerTests(unittest.TestCase):
    def test_marker_target_versions_and_inactive_extras(self):
        self.assertTrue(p.marker_active('python_version >= "3.11" and implementation_name == "cpython"'))
        self.assertFalse(p.marker_active('python_version < "3.11"'))
        self.assertFalse(p.marker_active('extra == "crypto" or sys_platform == "win32"'))
        self.assertTrue(p.marker_active('platform_machine in "arm64,x86_64"'))
        self.assertTrue(p.marker_active('"3.11" < python_version'))

    def test_marker_parser_never_executes_code_or_unknown_names(self):
        for marker in ('__import__("os").system("echo BAD")', 'unknown == "x"', 'python_version < 3.11',
                       'extra == "x" and unknown == "x"', 'not True', 'python_version ~= "3.11"', '"x"'):
            with self.subTest(marker=marker), self.assertRaises(p.Refused): p.marker_active(marker)

    def test_active_closure_and_inactive_dependencies_are_explicit(self):
        requirements = {name: [] for name in p.VERSIONS}
        requirements['pypdf'] = ['typing_extensions>=4.0; python_version < "3.11"', 'cryptography>=3.1; extra == "crypto"']
        requirements['cryptography'] = ['cffi>=2.0; platform_python_implementation != "PyPy"']
        requirements['cffi'] = ['pycparser>=2.18']
        report = p.dependency_closure(requirements)
        self.assertEqual(sum(row['active'] for row in report), 2)
        self.assertEqual(sum(row['disposition'] == 'INACTIVE_MARKER_NO_EXTRA_ACTIVATION' for row in report), 2)

    def test_unknown_unsatisfied_extra_or_direct_url_active_dependency_blocks(self):
        for value in ('unknown>=1.0', 'cffi>=9.0', 'cffi[other]>=2', 'cffi @ https://example.com/code.whl', 'cffi>=2.*'):
            requirements = {name: [] for name in p.VERSIONS}; requirements['cryptography'] = [value]
            with self.subTest(value=value), self.assertRaises(p.Refused): p.dependency_closure(requirements)

    def test_python312_S_base_prefix_does_not_change_explicit_target(self):
        target = Path('/MOCK/newenv')
        seen = []
        def public_paths(*, vars):
            seen.append(vars)
            return scheme(Path(vars['base']))
        with patch.object(sys, 'prefix', '/MOCK/existingBASE'):
            result = p.target_scheme(target, public_paths)
            args = p.pip_arguments('install', target, Path('/MOCK/build/install-v1-20261115/requirements.txt'))
        self.assertEqual(seen, [{'base': str(target), 'platbase': str(target)}])
        self.assertEqual(result['purelib'], '/MOCK/newenv/lib/python3.12/site-packages')
        self.assertEqual(args[args.index('--prefix')+1], str(target))
        self.assertIn('--ignore-installed', args)
        for flag in ('--no-index', '--no-deps', '--no-compile', '--no-cache-dir', '--only-binary=:all:', '--require-hashes'):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index('--find-links')+1], '/MOCK/build/acquisition-v1_2-20261115/wheels')
        self.assertNotIn('--python', args)

    def test_bad_computed_install_scheme_fails_closed(self):
        with self.assertRaises(p.Refused):
            p.target_scheme(Path('/MOCK/newenv'), lambda **_: scheme(Path('/MOCK/base')))

    def test_strict_json_duplicate_nonfinite_and_ref_paths(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}'):
            with self.assertRaises(p.Refused): p.json_body(raw)
        for name in ('../SECRET', '/ABSOLUTE', 'a//b', ''):
            with self.assertRaises(p.Refused): p.relative(Path('/MOCK'), name)


class InstallerFixtureTests(unittest.TestCase):
    def setUp(self):
        self.prefix = f.SecondSuccessorTests()
        self.prefix.setUp(); self.addCleanup(self.prefix.doCleanups)
        self.root = self.prefix.root
        self.assertEqual(self.prefix.run_collect()['status'], 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
        self.methods = p.json_body((ROOT/p.METHODS).read_bytes())
        self.methods['root_sha256'] = p.sha(str(self.root).encode())
        self.methods['acquisition_methods_ref'] = self.save('configs/e01_pypdf701_acquisition_v1_2_20261115.json',
                                                          p.packed(self.prefix.methods))
        self.methods['acquisition_code_sha256'] = p.sha((ROOT/'scripts/acquire_e01_pypdf701_artifacts_v1_2.py').read_bytes())
        for ref in (p.BASE_REF, p.GUARD_REF): self.save(ref['path'], (ROOT/ref['path']).read_bytes())
        self.base = self.root/'MOCK_BASE'
        executable_ref = self.save('MOCK_BASE/bin/python3.12', b'# MOCK EXECUTABLE NEVER EXECUTED\n')
        executable_ref['path'] = str(self.root/executable_ref['path'])
        pip_root = '.venv/lib/python3.12/site-packages/pip'
        files = {}
        for name, body in [('__init__.py', b'__version__="25.0.1"\n# MOCK PIP ONLY\n'),
                           ('__main__.py', b'# MOCK NEVER RUN\n'), ('__pip-runner__.py', b'# MOCK NEVER RUN\n')]:
            ref = self.save(pip_root+'/'+name, body); files[ref['path']] = {k: ref[k] for k in ('bytes', 'sha256')}
        metadata_ref = self.save('.venv/lib/python3.12/site-packages/pip-25.0.1.dist-info/METADATA',
                                 b'Metadata-Version: 2.3\nName: pip\nVersion: 25.0.1\n\n')
        self.binding = {'kind': 'E01_INSTALLER_BINDING_V1', 'pip_version': '25.0.1',
            'target': {'python': '3.12.14', 'OS': 'macOS', 'architecture': 'arm64'},
            'base_prefix': str(self.base), 'executable_ref': executable_ref,
            'pip_root': pip_root, 'pip_files': files, 'pip_metadata_ref': metadata_ref,
            'installation': False, 'package_imports': False, 'network': 0}
        self.binding['counts'] = {'files': len(files)+2, 'directories': 1,
            'total_bytes': sum(ref['bytes'] for ref in files.values())+metadata_ref['bytes']+executable_ref['bytes']}
        self.methods['installer_binding_ref'] = self.save('data/processed/MOCK_INSTALLER_BINDING/binding.json', p.packed(self.binding))
        lock_path = p.P1_SCOPE+'/hashlock.json'
        lock = p.json_body((self.root/lock_path).read_bytes())
        self.packet = {'kind': 'E01_PYPDF701_INSTALL_PACKET_V1', 'root_sha256': self.methods['root_sha256'],
            'methods_sha256': p.sha(p.packed(self.methods)),
            'acquisition_terminal_ref': self.ref(p.P1_SCOPE+'/TERMINAL.json'), 'hashlock_ref': self.ref(lock_path),
            'wheels': [{k: w[k] for k in ('name', 'version', 'filename', 'size', 'sha256')} for w in lock['wheels']]}
        original_loader = p.load_bound_module
        def fixture_helper(root, ref, name, reader=None):
            if ref == p.BASE_REF:
                # The frozen helper's exact authored PYPDF identity patch. No
                # real wheel is used; every other algorithm remains unchanged.
                if reader is not None: reader.read(ref)
                return f.c
            return original_loader(root, ref, name, reader)
        self.loader_patch = patch.object(p, 'load_bound_module', side_effect=fixture_helper)
        self.loader_patch.start(); self.addCleanup(self.loader_patch.stop)
        self.calls = []
        self.time = [0.0]

    def save(self, name, raw):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {'path': name, 'bytes': len(raw), 'sha256': p.sha(raw)}
    def ref(self, name):
        raw = (self.root/name).read_bytes()
        return {'path': name, 'bytes': len(raw), 'sha256': p.sha(raw)}

    def fake_launcher(self, command, env, root, budget, number):
        self.calls.append(command)
        stage = command[command.index('--guest')+1]
        target = root/p.TARGET
        if stage == 'venv':
            (target/'bin').mkdir(parents=True)
            (target/'bin/python').symlink_to(self.binding['executable_ref']['path'])
            (target/'pyvenv.cfg').write_text('home = '+str(self.base/'bin')+'\ninclude-system-site-packages = false\n')
        if stage == 'install':
            for name, version in p.VERSIONS.items():
                path = root/p.SITE/(name+'-'+version+'.dist-info/METADATA'); path.parent.mkdir(parents=True)
                path.write_text('Metadata-Version: 2.3\nName: '+name+'\nVersion: '+version+'\n\n')
        receipt = {'kind': 'P2_GUEST_COMPLETE', 'stage': stage, 'guard_violations': 0,
            'downloaded_package_imports': False, 'explicit_prefix': str(target), 'target_scheme': scheme(target),
            'observed_sys_prefix': str(self.base), 'metadata_only': p.installed_metadata(root/p.SITE) if stage == 'check' else None}
        (root/p.OUTPUT/(stage+'-guest-result.json')).write_bytes(p.packed(receipt))
        return {'exit_code': 0, 'pip_helper_descendants_permitted': 0, 'output': [], 'observed_reaped_CPU_seconds': 0}

    def execute(self, launcher=None):
        return p.execute(self.root, self.methods, self.packet, launcher=launcher or self.fake_launcher, clock=lambda: self.time[0])
    def terminal(self): return p.json_body((self.root/p.OUTPUT/'TERMINAL.json').read_bytes())

    def test_complete_mock_three_main_commands_no_oldsite_or_inference(self):
        result = self.execute()
        self.assertEqual(result['status'], 'OFFLINE_INSTALL_COMPLETE_NOT_RUNTIME_QUALIFICATION')
        self.assertEqual(len(self.calls), 3)
        self.assertEqual([cmd[cmd.index('--guest')+1] for cmd in self.calls], ['venv', 'install', 'check'])
        self.assertEqual(self.calls[0][0], self.binding['executable_ref']['path'])
        for command in self.calls[1:]: self.assertEqual(command[0], str(self.root/p.TARGET/'bin/python'))
        for command in self.calls:
            self.assertEqual(command[1:4], ['-I', '-B', '-S']); self.assertNotIn('--python', command)
        terminal = self.terminal()
        self.assertEqual(terminal['network_model_calls'], 0); self.assertFalse(terminal['runtime_or_source_qualification'])
        self.assertEqual(p.installed_metadata(self.root/p.SITE)['versions'], p.VERSIONS)
        self.assertFalse(any(name in sys.modules for name in p.BLOCKED_IMPORTS))
        self.prefix.unchanged()

    def test_consumed_or_existing_target_not_reused(self):
        self.execute(); old = (self.root/p.OUTPUT/'TERMINAL.json').read_bytes(); self.calls.clear()
        with self.assertRaisesRegex(p.Refused, 'P2_ALREADY_CONSUMED'): self.execute()
        self.assertEqual(self.calls, []); self.assertEqual(old, (self.root/p.OUTPUT/'TERMINAL.json').read_bytes())

    def test_preexisting_target_fails_before_new_stage(self):
        (self.root/p.TARGET).mkdir()
        with self.assertRaisesRegex(p.Refused, 'P2_ALREADY_CONSUMED'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists()); self.assertEqual(self.calls, [])

    def test_v1_1_failure_cannot_masquerade_as_complete_v1_2(self):
        self.packet['acquisition_terminal_ref'] = self.ref(f.v.n.OUTPUT+'/TERMINAL.json')
        with self.assertRaisesRegex(p.Refused, 'ACQUISITION_PATHS'): self.execute()
        self.assertEqual(self.calls, [])

    def test_wrong_external_wheel_hash_blocks_before_mutation(self):
        self.packet['wheels'][0]['sha256'] = 'f'*64
        with self.assertRaisesRegex(p.Refused, 'EXTERNAL_FIVE_WHEEL_BINDING'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists()); self.assertEqual(self.calls, [])

    def test_corrupt_wheel_or_ancestor_bytes_refuse(self):
        name = self.packet['wheels'][1]['filename']; path = self.root/p.P1_SCOPE/'wheels'/name
        raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(p.Refused, 'INPUT_HASH'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_oldest_ancestor_ref_remains_required(self):
        path = self.root/f.c.OUTPUT/'TERMINAL.json'; raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(p.Refused, 'INPUT_HASH'): self.execute()
        self.assertEqual(self.calls, [])

    def test_bootstrap_hash_and_extra_pip_file_are_blockers(self):
        self.save(self.binding['pip_root']+'/UNBOUND.py', b'# MOCK NEW FILE\n')
        with self.assertRaisesRegex(p.Refused, 'PIP_MANIFEST_MEMBERSHIP'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_base_binary_hash_change_blocks_before_mutation(self):
        path = Path(self.binding['executable_ref']['path']); raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(p.Refused, 'INPUT_HASH'): self.execute()
        self.assertEqual(self.calls, [])

    def test_unbound_empty_pip_directory_changes_bootstrap_identity(self):
        (self.root/self.binding['pip_root']/'MOCK_EXTRA_DIRECTORY').mkdir()
        with self.assertRaisesRegex(p.Refused, 'BOOTSTRAP_COUNTS'): self.execute()
        self.assertEqual(self.calls, [])

    def test_failed_command_preserves_partial_env_and_no_retry(self):
        def fail(command, env, root, budget, number):
            result = self.fake_launcher(command, env, root, budget, number)
            if number == 2: result['exit_code'] = 1
            return result
        result = self.execute(fail)
        self.assertEqual(result['reason'], 'P2_COMMAND_FAILED'); self.assertEqual(len(self.calls), 2)
        self.assertTrue((self.root/p.TARGET).exists()); self.assertTrue(self.terminal()['partial_environment_preserved'])

    def test_stopped_command_retains_record_and_holds_scope_consumed(self):
        def stopped(command, env, root, budget, number):
            raise p.CommandStopped('P2_COMMAND_OUTPUT_CAP', {'exit_code': -9, 'stopped': True,
                'observed_reaped_CPU_seconds': 1, 'pip_helper_descendants_permitted': 0, 'output': []})
        result = self.execute(stopped)
        self.assertEqual(result['reason'], 'P2_COMMAND_OUTPUT_CAP')
        self.assertTrue((self.root/p.OUTPUT/'1-COMMAND_STOPPED.json').exists())
        self.assertEqual(self.terminal()['commands_started'], 1)

    def test_wrong_guest_target_scheme_is_rejected(self):
        def wrong(command, env, root, budget, number):
            result = self.fake_launcher(command, env, root, budget, number)
            stage = command[command.index('--guest')+1]; path = root/p.OUTPUT/(stage+'-guest-result.json')
            receipt = p.json_body(path.read_bytes()); receipt['target_scheme'] = scheme(self.base); path.write_bytes(p.packed(receipt))
            return result
        self.assertEqual(self.execute(wrong)['reason'], 'GUEST_TARGET_SCHEME')
        self.assertEqual(len(self.calls), 1)

    def test_installed_extra_distribution_blocks_exact_closure(self):
        def extra(command, env, root, budget, number):
            result = self.fake_launcher(command, env, root, budget, number)
            if number == 2:
                path = root/p.SITE/'UNEXPECTED-1.0.dist-info/METADATA'; path.parent.mkdir(); path.write_text('Name: UNEXPECTED\nVersion: 1.0\n')
            return result
        result = self.execute(extra)
        self.assertEqual(result['status'], 'FAILED_PARTIAL_ENV_NO_RETRY')
        self.assertEqual(result['reason'], 'INSTALLED_IDENTITIES')

    def test_changed_old_pip_detected_after_commands(self):
        def change(command, env, root, budget, number):
            result = self.fake_launcher(command, env, root, budget, number)
            if number == 3:
                path = root/self.binding['pip_root']/'__main__.py'; raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
            return result
        self.assertEqual(self.execute(change)['reason'], 'INPUT_HASH')

    def test_guest_blocks_network_helpers_downloaded_import_and_outside_write(self):
        policy = p.GuestPolicy(self.root, self.binding, {'wheels': self.packet['wheels'], 'remaining_output_bytes': 1024})
        for event in ('socket.connect', 'subprocess.Popen', 'os.fork', 'ctypes.dlopen'):
            with self.subTest(event=event), self.assertRaises(p.Refused): policy.audit(event, ())
        finder = p.DownloadedImportGuard(policy)
        for name in p.BLOCKED_IMPORTS:
            with self.subTest(name=name), self.assertRaises(p.Refused): finder.find_spec(name+'.MOCK')
        self.assertIsNone(finder.find_spec('pip._vendor.MOCK'))
        with self.assertRaises(p.Refused): policy.path(self.root/'DO_NOT_WRITE', os.O_WRONLY)
        policy.path(self.root/p.OUTPUT/'allowed.tmp', os.O_WRONLY)

    def test_write_and_output_limits_refuse_before_effect(self):
        policy = p.GuestPolicy(self.root, self.binding, {'wheels': self.packet['wheels'], 'remaining_output_bytes': 3})
        stream = io.BytesIO(); wrapped = p.ChargedFile(stream, policy, True)
        wrapped.write(b'ab')
        with self.assertRaisesRegex(p.Refused, 'GUEST_OUTPUT_CAP'): wrapped.write(b'cd')
        self.assertEqual(stream.getvalue(), b'ab')
        policy.writes = p.CAPS['guest_cumulative_write_bytes_each']
        other = io.BytesIO()
        with self.assertRaisesRegex(p.Refused, 'GUEST_WRITE_CAP'): p.ChargedFile(other, policy).write(b'x')
        self.assertEqual(other.getvalue(), b'')

    def test_budget_wall_rollback_and_observed_cpu_refuse(self):
        budget = p.StageBudget(self.root, clock=lambda: self.time[0]); self.time[0] = 120
        with self.assertRaisesRegex(p.Refused, 'P2_WALL_LIMIT'): budget.check()
        self.time[0] = -1
        with self.assertRaisesRegex(p.Refused, 'P2_CLOCK_REGRESSION'): budget.check()
        self.time[0] = 0
        budget = p.StageBudget(self.root, clock=lambda: self.time[0])
        with patch.object(p.resource, 'getrusage', return_value=SimpleNamespace(ru_utime=40, ru_stime=0)):
            with self.assertRaisesRegex(p.Refused, 'P2_OBSERVED_AGGREGATE_CPU_LIMIT'): budget.check()

    def test_actual_mock_run_pip_path_excludes_oldsite_and_uses_prefix(self):
        (self.root/p.SITE).mkdir(parents=True)
        before_path, before_args, before_pip = list(sys.path), sys.argv, sys.modules.get('pip')
        observed = []
        def ordinary_cli(*args, **kwargs):
            observed.append((list(sys.path), list(sys.argv), args, kwargs))
        try:
            with (patch.object(p, 'target_scheme', side_effect=lambda target: scheme(target)),
                  patch.object(p.runpy, 'run_module', side_effect=ordinary_cli)):
                p.run_pip(self.binding, 'install', self.root)
            paths, args, _, _ = observed[0]
            self.assertEqual(paths[0], str(self.root/p.SITE))
            self.assertNotIn(str((self.root/self.binding['pip_root']).parent), paths)
            self.assertEqual(args[args.index('--prefix')+1], str(self.root/p.TARGET))
        finally:
            sys.path[:] = before_path; sys.argv = before_args
            if before_pip is None: sys.modules.pop('pip', None)
            else: sys.modules['pip'] = before_pip


class CaptureAndQuotaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/p.OUTPUT).mkdir(parents=True)
        self.budget = p.StageBudget(self.root)

    def fake_process(self, *args, **kwargs):
        def pipe(body):
            read, write = os.pipe(); os.write(write, body); os.close(write)
            return os.fdopen(read, 'rb', buffering=0)
        self.assertTrue(kwargs['start_new_session'])
        self.assertEqual(kwargs['stdin'], p.subprocess.DEVNULL)
        return SimpleNamespace(pid=12345, stdout=pipe(b'abc'), stderr=pipe(b'd'), returncode=None)

    def test_capture_backend_retains_stdout_stderr_and_reaped_cpu_without_process(self):
        usage = SimpleNamespace(ru_utime=.1, ru_stime=.2)
        with (patch.object(p.subprocess, 'Popen', side_effect=self.fake_process),
              patch.object(p.os, 'wait4', return_value=(12345, 0, usage))):
            result = p.run_command(['MOCK_NO_EXEC'], {}, self.root, self.budget, 1)
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(self.budget.output, 4)
        self.assertAlmostEqual(self.budget.reaped_cpu, .3)
        self.assertEqual([ref['bytes'] for ref in result['output']], [3, 1])
        self.assertEqual((self.root/p.OUTPUT/'1-stdout.bin').read_bytes(), b'abc')

    def test_capture_overflow_kills_reaps_and_records_stopped_prefix(self):
        usage = SimpleNamespace(ru_utime=.1, ru_stime=.2)
        self.budget.output = p.CAPS['command_output_bytes']-1
        with (patch.object(p.subprocess, 'Popen', side_effect=self.fake_process),
              patch.object(p.os, 'wait4', return_value=(12345, 9, usage)),
              patch.object(p.os, 'killpg') as kill):
            with self.assertRaises(p.CommandStopped) as error:
                p.run_command(['MOCK_NO_EXEC'], {}, self.root, self.budget, 1)
        self.assertIn('P2_COMMAND_OUTPUT_CAP', str(error.exception))
        kill.assert_called_once_with(12345, p.signal.SIGKILL)
        self.assertEqual(error.exception.record['exit_code'], -9)
        self.assertAlmostEqual(self.budget.reaped_cpu, .3)
        self.assertTrue((self.root/p.OUTPUT/'1-stdout.bin').exists())

    def test_owned_size_cap_uses_observed_tree_and_refuses_special_file(self):
        path = self.root/p.OUTPUT/'MOCK'
        path.write_bytes(b'x')
        self.assertGreaterEqual(p.owned_size(self.root), 1)
        original = Path.lstat
        def huge(item):
            if item == path: return SimpleNamespace(st_mode=0o100600, st_size=p.CAPS['owned_logical_bytes']+1)
            return original(item)
        with patch.object(Path, 'lstat', huge):
            with self.assertRaisesRegex(p.Refused, 'OWNED_LOGICAL_BYTES_CAP'): p.owned_size(self.root)

    def test_control_terminal_headroom_and_reader_quota_precede_file_effect(self):
        journal = p.Journal(self.root); journal.bytes = p.CAPS['control_write_bytes']-32768
        with self.assertRaisesRegex(p.Refused, 'P2_CONTROL_WRITE_CAP'): journal.save('NO_EFFECT.json', b'x')
        self.assertFalse((self.root/p.OUTPUT/'NO_EFFECT.json').exists())
        journal.save('TERMINAL.json', b'{}')
        raw = b'MOCK'; name = 'MOCK_INPUT'; (self.root/name).write_bytes(raw)
        reader = p.Reader(self.root, limit=3)
        with self.assertRaisesRegex(p.Refused, 'READ_CAP'):
            reader.read({'path': name, 'bytes': len(raw), 'sha256': p.sha(raw)})


if __name__ == '__main__':
    f.f.f.guarded_test_main()
