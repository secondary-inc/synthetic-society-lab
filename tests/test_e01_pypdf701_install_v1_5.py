"""Guarded recovery fixtures. Never execute actual pip, venv or source work."""
import ast
import copy
import hashlib
import importlib.util
import mimetypes
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

old = load('accepted_v1_3_fixtures', ROOT/'tests/test_e01_pypdf701_install_v1_3.py')
p = load('recovery_v1_5', ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py')
old.p = p
old.t.p = p


class RecoveryFixtureTests(old.ConsumerFixtureTests):
    def setUp(self):
        super().setUp()
        old_methods = copy.deepcopy(self.methods)
        old_methods.pop('recovery')
        old_methods.update(kind='E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1_3',
                           output=p.PRIOR_OUTPUT, target=p.PRIOR_TARGET,
                           new_site=p.PRIOR_TARGET+'/lib/python3.12/site-packages')
        recovery = copy.deepcopy(self.methods['recovery']['stages'][0])
        recovery['code_ref'] = self.save(recovery['code_ref']['path'],
            (ROOT/'scripts/install_e01_pypdf701_runtime_v1_3.py').read_bytes())
        recovery['methods_ref'] = self.save(recovery['methods_ref']['path'], p.packed(old_methods))
        old_packet = copy.deepcopy(self.packet)
        old_packet['methods_sha256'] = recovery['methods_ref']['sha256']
        recovery['packet_ref'] = self.save(recovery['packet_ref']['path'], p.packed(old_packet))
        started = {'kind': 'P2_STARTED_NO_RETRY', 'caps': p.CAPS,
                   'code_sha256': recovery['code_ref']['sha256'],
                   'methods_sha256': recovery['methods_ref']['sha256'],
                   'packet_sha256': recovery['packet_ref']['sha256'],
                   'binding_ref': self.methods['installer_binding_ref']}
        recovery['started_ref'] = self.save(p.PRIOR_OUTPUT+'/STARTED.json', p.packed(started))
        outputs = []
        for number in (1, 2):
            refs = []
            for suffix in ('stdout', 'stderr'):
                name = str(number)+'-'+suffix+'.bin'
                ref = self.save(p.PRIOR_OUTPUT+'/'+name, b'MOCK ONLY' if number == 2 and suffix == 'stderr' else b'')
                refs.append({**ref, 'path': name})
            outputs.append({'exit_code': 0 if number == 1 else 1,
                            'pip_helper_descendants_permitted': 0, 'output': refs})
        terminal = {'kind': 'P2_TERMINAL_V1', 'status': 'FAILED_PARTIAL_ENV_NO_RETRY',
                    'reason': 'P2_COMMAND_FAILED', 'stage': 'install', 'commands_started': 2,
                    'no_retry': True, 'partial_environment_preserved': True,
                    'network_model_calls': 0, 'cost_USD': 0, 'downloaded_package_imports': False,
                    'runtime_or_source_qualification': False, 'pip_helper_descendants_permitted': 0,
                    'results': outputs, 'captured_command_output_bytes': 9,
                    'parent_bound_reference_read_bytes_charged': 1024,
                    'observed_self_and_reaped_CPU_seconds': .5,
                    'artifacts': [{**recovery['started_ref'], 'path': 'STARTED.json'}]}
        recovery['terminal_ref'] = self.save(p.PRIOR_OUTPUT+'/TERMINAL.json', p.packed(terminal))
        prior = self.root/p.PRIOR_TARGET
        (prior/'bin').mkdir(parents=True)
        (prior/'bin/python').symlink_to(self.binding['executable_ref']['path'])
        (prior/'pyvenv.cfg').write_bytes(b'MOCK OLD PARTIAL ENVIRONMENT\n')
        self.methods['recovery']['stages'][0] = recovery
        latest = copy.deepcopy(self.methods['recovery']['stages'][1])
        latest_methods = copy.deepcopy(self.methods)
        latest_methods.update(kind='E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1_4',
                              output=p.LATEST_OUTPUT, target=p.LATEST_TARGET,
                              new_site=p.LATEST_TARGET+'/lib/python3.12/site-packages', recovery=recovery)
        latest['code_ref'] = self.save(latest['code_ref']['path'],
            (ROOT/'scripts/install_e01_pypdf701_runtime_v1_4.py').read_bytes())
        latest['methods_ref'] = self.save(latest['methods_ref']['path'], p.packed(latest_methods))
        latest_packet = copy.deepcopy(self.packet)
        latest_packet['methods_sha256'] = latest['methods_ref']['sha256']
        latest['packet_ref'] = self.save(latest['packet_ref']['path'], p.packed(latest_packet))
        first_evidence = p.verify_failed_install(self.root, self.methods, self.packet,
                                                 p.Reader(self.root), recovery, 0)
        first_snapshot = p.prior_metadata_snapshot(self.root,
                                                   (self.root/p.PRIOR_OUTPUT, self.root/p.PRIOR_TARGET))
        latest_started = {'kind': 'P2_STARTED_NO_RETRY', 'caps': p.CAPS,
                          'code_sha256': latest['code_ref']['sha256'],
                          'methods_sha256': latest['methods_ref']['sha256'],
                          'packet_sha256': latest['packet_ref']['sha256'],
                          'binding_ref': self.methods['installer_binding_ref'],
                          'prior_installation': first_evidence,
                          'recovery_allocation': p.FIRST_RECOVERY_ALLOCATION,
                          'prior_metadata_snapshot': first_snapshot}
        latest['started_ref'] = self.save(p.LATEST_OUTPUT+'/STARTED.json', p.packed(latest_started))
        latest_outputs = []
        for number in (1, 2):
            refs = []
            for suffix in ('stdout', 'stderr'):
                name = str(number)+'-'+suffix+'.bin'
                ref = self.save(p.LATEST_OUTPUT+'/'+name,
                                b'MOCK MIME REFUSAL' if number == 2 and suffix == 'stderr' else b'')
                refs.append({**ref, 'path': name})
            latest_outputs.append({'exit_code': 0 if number == 1 else 1,
                                   'pip_helper_descendants_permitted': 0, 'output': refs})
        latest_terminal = copy.deepcopy(terminal)
        latest_terminal.update(results=latest_outputs, captured_command_output_bytes=17,
                               parent_bound_reference_read_bytes_charged=2048,
                               observed_self_and_reaped_CPU_seconds=.75,
                               artifacts=[{**latest['started_ref'], 'path': 'STARTED.json'}],
                               prior_installation=first_evidence,
                               recovery_allocation=p.FIRST_RECOVERY_ALLOCATION,
                               prior_metadata_snapshot=first_snapshot)
        latest['terminal_ref'] = self.save(p.LATEST_OUTPUT+'/TERMINAL.json', p.packed(latest_terminal))
        latest_target = self.root/p.LATEST_TARGET
        (latest_target/'bin').mkdir(parents=True)
        (latest_target/'bin/python').symlink_to(self.binding['executable_ref']['path'])
        (latest_target/'pyvenv.cfg').write_bytes(b'MOCK SECOND PARTIAL ENVIRONMENT\n')
        self.methods['recovery']['stages'][1] = latest
        self.packet['methods_sha256'] = p.sha(p.packed(self.methods))

    def fake_launcher(self, command, env, root, budget, number):
        result = super().fake_launcher(command, env, root, budget, number)
        stage = command[command.index('--guest')+1]
        path = root/p.OUTPUT/(stage+'-guest-result.json')
        receipt = p.json_body(path.read_bytes())
        receipt['mime_configuration'] = None if stage == 'venv' else copy.deepcopy(p.MIME_RECEIPT)
        path.write_bytes(p.packed(receipt))
        return result

    def test_actual_mock_run_pip_path_excludes_oldsite_and_uses_prefix(self):
        (self.root/p.SITE).mkdir(parents=True)
        stdlib = self.base/'lib/python3.12'; dynamic = stdlib/'lib-dynload'
        dynamic.mkdir(parents=True)
        original = [str(self.base/'lib/python312.zip'), str(stdlib), str(dynamic)]
        before_path, before_args, before_pip = list(sys.path), sys.argv, sys.modules.get('pip')
        observed = []
        def ordinary_cli(*args, **kwargs):
            observed.append((list(sys.path), list(sys.argv)))
        try:
            sys.path[:] = original
            with (patch.object(p, 'target_scheme', side_effect=lambda target: old.t.scheme(target)),
                  patch.object(p.runpy, 'run_module', side_effect=ordinary_cli)):
                p.run_pip(self.binding, 'install', self.root)
            paths, args = observed[0]
            self.assertEqual(paths, [str(self.root/p.SITE), str(stdlib), str(dynamic)])
            self.assertNotIn(str((self.root/self.binding['pip_root']).parent), paths)
            self.assertEqual(args[args.index('--prefix')+1], str(self.root/p.TARGET))
        finally:
            sys.path[:] = before_path; sys.argv = before_args
            if before_pip is None: sys.modules.pop('pip', None)
            else: sys.modules['pip'] = before_pip

    def test_recovery_success_preserves_old_scope_and_target_and_full_allocation(self):
        snapshot = p.prior_metadata_snapshot(self.root)
        self.assertEqual(self.execute()['status'], 'OFFLINE_INSTALL_COMPLETE_NOT_RUNTIME_QUALIFICATION')
        self.assertEqual(p.prior_metadata_snapshot(self.root), snapshot)
        self.assertEqual(self.terminal()['recovery_allocation'], p.RECOVERY_ALLOCATION)
        self.assertEqual(self.terminal()['prior_installation']['actual_prior_commands_started'], 4)
        self.assertEqual(self.terminal()['recovery_allocation']['prior_main_commands'], 6)
        self.assertEqual(len(self.calls), 3)

    def test_corrupt_failed_ancestor_blocks_before_new_stage(self):
        path = self.root/p.PRIOR_OUTPUT/'TERMINAL.json'
        path.write_bytes(b'X'+path.read_bytes()[1:])
        with self.assertRaisesRegex(p.Refused, 'INPUT_HASH'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_coherently_rehashed_nonfailed_ancestor_refuses(self):
        ref = self.methods['recovery']['stages'][0]['terminal_ref']
        value = p.json_body((self.root/ref['path']).read_bytes())
        value['status'] = 'OFFLINE_INSTALL_COMPLETE_NOT_RUNTIME_QUALIFICATION'
        self.methods['recovery']['stages'][0]['terminal_ref'] = self.save(ref['path'], p.packed(value))
        self.packet['methods_sha256'] = p.sha(p.packed(self.methods))
        with self.assertRaisesRegex(p.Refused, 'RECOVERY_FAILED_INSTALL'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_missing_prior_target_refuses_before_new_stage(self):
        import shutil
        shutil.rmtree(self.root/p.PRIOR_TARGET)
        with self.assertRaisesRegex(p.Refused, 'RECOVERY_PRESERVED_TREE_MISSING'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_recovery_allocation_cannot_reset_prior_charges(self):
        self.methods['recovery']['allocation']['prior_main_commands'] = 0
        with self.assertRaisesRegex(p.Refused, 'P2_METHODS_IDENTITY'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_old_tree_mutations_and_reads_remain_outside_guest_permissions(self):
        policy = p.GuestPolicy(self.root, self.binding, {'wheels': self.packet['wheels'], 'remaining_output_bytes': 100})
        for path in (self.root/p.PRIOR_TARGET/'pyvenv.cfg', self.root/p.PRIOR_OUTPUT/'STARTED.json',
                     self.root/p.LATEST_TARGET/'pyvenv.cfg', self.root/p.LATEST_OUTPUT/'STARTED.json'):
            self.assertFalse(policy.owned(path))
            for flags in (os.O_WRONLY, os.O_RDONLY):
                with self.assertRaises(p.Refused): policy.path(path, flags)

    def test_old_target_metadata_change_prevents_success(self):
        def changed(command, env, root, budget, number):
            result = self.fake_launcher(command, env, root, budget, number)
            if number == 3: (root/p.PRIOR_TARGET/'UNEXPECTED_MOCK').write_bytes(b'X')
            return result
        self.assertEqual(self.execute(changed)['reason'], 'RECOVERY_CHAIN_BINDING')
        self.assertTrue((self.root/p.PRIOR_TARGET/'UNEXPECTED_MOCK').exists())

    def test_failed_recovery_preserves_both_partial_targets(self):
        before = p.prior_metadata_snapshot(self.root)
        def failed(command, env, root, budget, number):
            result = self.fake_launcher(command, env, root, budget, number)
            if number == 2: result['exit_code'] = 1
            return result
        self.assertEqual(self.execute(failed)['reason'], 'P2_COMMAND_FAILED')
        self.assertEqual(p.prior_metadata_snapshot(self.root), before)
        self.assertTrue((self.root/p.TARGET).is_dir())

    def test_combined_occupancy_counts_both_old_and_new_targets(self):
        old_file = self.root/p.PRIOR_TARGET/'pyvenv.cfg'
        new_file = self.root/p.TARGET/'MOCK_BIG'
        new_file.parent.mkdir(); new_file.write_bytes(b'X')
        original = Path.lstat
        def large(path):
            if path in (old_file, new_file):
                return SimpleNamespace(st_mode=0o100600, st_size=p.CAPS['owned_logical_bytes']//2+1)
            return original(path)
        with patch.object(Path, 'lstat', large):
            with self.assertRaisesRegex(p.Refused, 'OWNED_LOGICAL_BYTES_CAP'): p.owned_size(self.root)

    def test_preflight_includes_preserved_occupancy(self):
        with patch.object(p, 'owned_size', return_value=p.CAPS['owned_logical_bytes']-1):
            with self.assertRaisesRegex(p.Refused, 'OWNED_PREFLIGHT_UPPER_BOUND'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_latest_failed_ancestor_hash_and_chain_cannot_be_dropped(self):
        ref = self.methods['recovery']['stages'][1]['terminal_ref']
        path = self.root/ref['path']; raw = path.read_bytes()
        path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(p.Refused, 'INPUT_HASH'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_reordered_or_missing_failed_stages_refuse(self):
        original = copy.deepcopy(self.methods['recovery']['stages'])
        for altered in (list(reversed(original)), original[:1]):
            self.methods['recovery']['stages'] = altered
            self.packet['methods_sha256'] = p.sha(p.packed(self.methods))
            with self.assertRaisesRegex(p.Refused, 'RECOVERY_IDENTITY|RECOVERY_CHAIN_IDENTITY'):
                self.execute()
            self.assertFalse((self.root/p.OUTPUT).exists())

    def test_coherently_rehashed_latest_snapshot_cannot_replace_first_history(self):
        descriptor = self.methods['recovery']['stages'][1]
        ref = descriptor['terminal_ref']
        terminal = p.json_body((self.root/ref['path']).read_bytes())
        terminal['prior_metadata_snapshot']['sha256'] = '0'*64
        descriptor['terminal_ref'] = self.save(ref['path'], p.packed(terminal))
        self.packet['methods_sha256'] = p.sha(p.packed(self.methods))
        with self.assertRaisesRegex(p.Refused, 'RECOVERY_CHAIN_BINDING'): self.execute()
        self.assertFalse((self.root/p.OUTPUT).exists())

    def test_latest_old_target_metadata_change_cannot_pass(self):
        def changed(command, env, root, budget, number):
            result = self.fake_launcher(command, env, root, budget, number)
            if number == 3: (root/p.LATEST_TARGET/'UNEXPECTED_MOCK').write_bytes(b'X')
            return result
        self.assertEqual(self.execute(changed)['reason'], 'PRIOR_INSTALLATION_CHANGED')

    def test_all_six_trees_share_single_logical_limit(self):
        members = set()
        for name in (p.PRIOR_OUTPUT, p.PRIOR_TARGET, p.LATEST_OUTPUT, p.LATEST_TARGET, p.OUTPUT, p.TARGET):
            tree = self.root/name; tree.mkdir(parents=True, exist_ok=True)
            path = tree/'MOCK_LARGE_MEMBER'; path.write_bytes(b'X'); members.add(path)
        original = Path.lstat
        def large(path):
            if path in members:
                return SimpleNamespace(st_mode=0o100600, st_size=p.CAPS['owned_logical_bytes']//6+1)
            return original(path)
        with patch.object(Path, 'lstat', large):
            with self.assertRaisesRegex(p.Refused, 'OWNED_LOGICAL_BYTES_CAP'): p.owned_size(self.root)

    def test_missing_mime_guest_proof_stops_before_third_command(self):
        def missing(command, env, root, budget, number):
            result = self.fake_launcher(command, env, root, budget, number)
            if number == 2:
                path = root/p.OUTPUT/'install-guest-result.json'
                receipt = p.json_body(path.read_bytes()); receipt.pop('mime_configuration')
                path.write_bytes(p.packed(receipt))
            return result
        self.assertEqual(self.execute(missing)['reason'], 'GUEST_MIME_CONFIGURATION')
        self.assertEqual(len(self.calls), 2)


class ProductionMimeTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory(prefix='e01-p2-production-mime-MOCK-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()/'MOCK_BASE'
        self.path = self.base/'lib/python3.12/mimetypes.py'
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(Path(mimetypes.__file__).read_bytes())
        self.module = load('authored_stdlib_mime_production', self.path)
        self.binding = {'base_prefix': str(self.base)}
        self.fake = self.base/'MOCK_MIME_TYPES'
        self.fake.write_text('text/html whl\napplication/x-mock txt\n')
        self.module.knownfiles = [str(self.fake)]

    def prepare_without_io(self):
        with (patch.dict(sys.modules, {'mimetypes': self.module}),
              patch.object(__import__('builtins'), 'open', side_effect=AssertionError('NO_MIME_FILE_OPEN'))):
            receipt = p.prepare_builtin_mime(self.binding)
            self.assertEqual(receipt, p.MIME_RECEIPT)
            self.assertEqual(self.module.guess_type('file:///MOCK/index.html', strict=False), ('text/html', None))
            self.assertEqual(self.module.guess_type('file:///MOCK/data.txt'), ('text/plain', None))
            self.assertNotEqual(self.module.guess_type('file:///MOCK/pypdf-7.0.1-py3-none-any.whl', strict=False)[0], 'text/html')

    def test_bound_stdlib_origin_fresh_initialization_has_no_mime_file_reads(self):
        self.prepare_without_io()

    def test_bound_stdlib_origin_prepopulated_initialization_resets_mappings(self):
        self.module.init(files=[])
        self.assertEqual(self.module.guess_type('file:///MOCK/a.whl')[0], 'text/html')
        self.prepare_without_io()

    def test_unknown_origin_refuses_before_initialization(self):
        self.module.__file__ = str(self.base/'MOCK_WRONG_ORIGIN.py')
        with patch.dict(sys.modules, {'mimetypes': self.module}), patch.object(self.module, 'init') as init:
            with self.assertRaisesRegex(p.Refused, 'MIME_STDLIB_ORIGIN'): p.prepare_builtin_mime(self.binding)
            init.assert_not_called()

    def test_unknown_spec_origin_refuses_before_initialization(self):
        self.module.__spec__.origin = str(self.base/'MOCK_WRONG_SPEC.py')
        with patch.dict(sys.modules, {'mimetypes': self.module}), patch.object(self.module, 'init') as init:
            with self.assertRaisesRegex(p.Refused, 'MIME_STDLIB_ORIGIN'): p.prepare_builtin_mime(self.binding)
            init.assert_not_called()

    def test_alias_origin_refuses_before_initialization(self):
        actual = self.path.with_name('MOCK_REAL_MIME.py'); self.path.rename(actual)
        self.path.symlink_to(actual)
        with patch.dict(sys.modules, {'mimetypes': self.module}), patch.object(self.module, 'init') as init:
            with self.assertRaisesRegex(p.Refused, 'PATH_ALIAS'): p.prepare_builtin_mime(self.binding)
            init.assert_not_called()

    def test_init_error_propagates_once_without_fallback(self):
        with (patch.dict(sys.modules, {'mimetypes': self.module}),
              patch.object(self.module, 'init', side_effect=RuntimeError('MOCK_INIT_STOP')) as init):
            with self.assertRaisesRegex(RuntimeError, 'MOCK_INIT_STOP'): p.prepare_builtin_mime(self.binding)
            init.assert_called_once_with(files=None)

    def test_invalid_public_state_refuses(self):
        self.module.knownfiles = 'MOCK_BAD_TYPE'
        with patch.dict(sys.modules, {'mimetypes': self.module}), patch.object(self.module, 'init') as init:
            with self.assertRaisesRegex(p.Refused, 'MIME_STATE_SCHEMA'): p.prepare_builtin_mime(self.binding)
            init.assert_not_called()


class RecoveryPureTests(old.ConsumerPureTests):
    def test_narrow_path_candidate_refuses_existing_alias_and_unknown_roots(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()/'MOCK_BASE'
            stdlib = base/'lib/python3.12'; dynamic = stdlib/'lib-dynload'
            dynamic.mkdir(parents=True); archive = base/'lib/python312.zip'
            paths = [str(archive), str(stdlib), str(dynamic)]
            self.assertEqual(p.narrowed_paths(paths, base), paths[1:])
            for altered in (paths+[str(base/'UNKNOWN')], paths[1:], list(reversed(paths)), paths+[paths[0]]):
                with self.assertRaisesRegex(p.Refused, 'PIP_UNEXPECTED_PATHS'): p.narrowed_paths(altered, base)
            archive.write_bytes(b'MOCK')
            with self.assertRaisesRegex(p.Refused, 'PIP_ZIP_PRESENT'): p.narrowed_paths(paths, base)
            archive.unlink(); archive.symlink_to(base/'MISSING')
            with self.assertRaisesRegex(p.Refused, 'PIP_PATH_ALIAS'): p.narrowed_paths(paths, base)
            archive.unlink(); dynamic.rmdir()
            with self.assertRaisesRegex(p.Refused, 'PIP_STDLIB_DIRECTORY'): p.narrowed_paths(paths, base)


class RecoveryCaptureTests(old.ConsumerCaptureTests):
    def test_final_terminal_counts_its_own_combined_logical_bytes(self):
        (self.root/p.PRIOR_TARGET).mkdir()
        (self.root/p.PRIOR_TARGET/'MOCK').write_bytes(b'old')
        journal = p.Journal(self.root)
        journal.save('TERMINAL.json', {'kind': 'MOCK_TERMINAL'})
        terminal = p.json_body((self.root/p.OUTPUT/'TERMINAL.json').read_bytes())
        self.assertEqual(terminal['combined_logical_bytes_including_terminal'], p.owned_size(self.root))

    def test_logical_terminal_headroom_refuses_before_file_creation(self):
        with patch.object(p, 'owned_size', return_value=p.CAPS['owned_logical_bytes']-32768):
            with self.assertRaisesRegex(p.Refused, 'P2_COMBINED_JOURNAL_LOGICAL_CAP'):
                p.Journal(self.root).save('NO_EFFECT.json', b'X')
        self.assertFalse((self.root/p.OUTPUT/'NO_EFFECT.json').exists())

    def test_final_terminal_over_cap_refuses_before_file_creation(self):
        with patch.object(p, 'owned_size', return_value=p.CAPS['owned_logical_bytes']-1):
            with self.assertRaisesRegex(p.Refused, 'P2_COMBINED_JOURNAL_LOGICAL_CAP'):
                p.Journal(self.root).save('TERMINAL.json', {'kind': 'MOCK_TOO_LARGE'})
        self.assertFalse((self.root/p.OUTPUT/'TERMINAL.json').exists())


class RecoveryDeltaTests(unittest.TestCase):
    def test_previous_frozen_candidate_hashes_unchanged(self):
        expected = {'scripts/install_e01_pypdf701_runtime_v1_3.py': 'a4e6e9580bfbfdad96b960cc2837ae5e76771e6c6109217c97f50f1a1837f062',
                    'configs/e01_pypdf701_install_v1_3_20261116.json': '5b80e9f9bebd5b55c288c4023604a7b8af52a1140a94a79bcb9b6b72223cc743',
                    'tests/test_e01_pypdf701_install_v1_3.py': '9e47a1b4f7fe22e9a9640614a6f195e3e88fe5415a68c84f4af0364ea0a22a90'}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest)

    def test_previous_v1_4_source_methods_and_tests_unchanged(self):
        expected = {'scripts/install_e01_pypdf701_runtime_v1_4.py': '5d118a009805890854dcad6e17c89d297376cb685b22c0374a2fd5fb33d4b6f3',
                    'configs/e01_pypdf701_install_v1_4_20261116.json': '4a3b12a980652c26c48bdffd8308bc7d4f7252c7c5189ae6174600ea5334d9c6',
                    'tests/test_e01_pypdf701_install_v1_4.py': '70110d7002c32b10aa9be702abdce03158ce31334be5ae93a097e869f39a2c56'}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest)

    def test_other_core_functions_remain_identical_after_explicit_routing(self):
        before = ast.parse((ROOT/'scripts/install_e01_pypdf701_runtime_v1_4.py').read_bytes())
        after = ast.parse((ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py').read_bytes())
        replacements = {'scripts/install_e01_pypdf701_runtime_v1_5.py': 'scripts/install_e01_pypdf701_runtime_v1_4.py',
            'configs/e01_pypdf701_install_v1_5_20261116.json': 'configs/e01_pypdf701_install_v1_4_20261116.json',
            'data/processed/e01_pypdf701_build_v1/install-v1_5-20261116': 'data/processed/e01_pypdf701_build_v1/install-v1_4-20261116',
            '.venv-e01-pypdf-7.0.1-v3': '.venv-e01-pypdf-7.0.1-v2',
            'E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1_5': 'E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1_4'}
        class Normalize(ast.NodeTransformer):
            def visit_Constant(self, node):
                if type(node.value) is str and node.value in replacements: node.value = replacements[node.value]
                return node
        after = Normalize().visit(after)
        permitted = {'guest_main', 'verify_prior_install', 'prior_metadata_snapshot', 'owned_size',
                     'validate_methods', 'execute'}
        new = {'initialize_builtin_mime_types', 'prepare_builtin_mime', 'verify_failed_install'}
        def selected(module):
            return {node.name: ast.dump(node, include_attributes=False) for node in module.body
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name not in permitted|new}
        self.assertEqual(selected(before), selected(after))

    def test_mime_helper_is_accepted_candidate_with_only_refusal_type_changed(self):
        candidate = ast.parse((ROOT/'scripts/e01_p2_builtin_mime_candidate_v2_20261116.py').read_bytes())
        production = ast.parse((ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py').read_bytes())
        expected = next(node for node in candidate.body if isinstance(node, ast.FunctionDef))
        actual = next(node for node in production.body if isinstance(node, ast.FunctionDef)
                      and node.name == 'initialize_builtin_mime_types')
        class Normalize(ast.NodeTransformer):
            def visit_Name(self, node):
                if node.id == 'Refused': node.id = 'ValueError'
                return node
        self.assertEqual(ast.dump(expected, include_attributes=False),
                         ast.dump(Normalize().visit(actual), include_attributes=False))

    def test_mime_preparation_is_after_guard_and_before_pip(self):
        source = (ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py').read_text()
        body = source[source.index('def guest_main('):source.index('def verify_failed_install(')]
        self.assertLess(body.index('policy = install_guest_guard('), body.index('prepare_builtin_mime(binding)'))
        self.assertLess(body.index('prepare_builtin_mime(binding)'), body.index('metadata = run_pip('))


if __name__ == '__main__':
    old.g.old.guarded_test_main()
