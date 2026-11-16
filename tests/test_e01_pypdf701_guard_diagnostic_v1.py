"""Guarded authored controller/guest fixtures. No actual diagnostic or pip run."""
import ast
import copy
import hashlib
import importlib.util
import json
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

d = load('authored_diagnostic_runner', ROOT/'scripts/diagnose_e01_pypdf701_guard_v1.py')
f = load('accepted_installer_v1_5_fixtures', ROOT/'tests/test_e01_pypdf701_install_v1_5.py')
f.p = d.p; f.old.p = d.p; f.old.t.p = d.p


class DiagnosticFixtureTests(unittest.TestCase):
    def setUp(self):
        self.old = f.RecoveryFixtureTests('test_complete_mock_three_main_commands_no_oldsite_or_inference')
        self.old.setUp(); self.addCleanup(self.old.doCleanups)
        self.root = self.old.root
        def old_failure(command, env, root, budget, number):
            result = self.old.fake_launcher(command, env, root, budget, number)
            refs = []
            for suffix in ('stdout', 'stderr'):
                body = b'' if number == 1 else (b'MOCK SUCCESS TEXT NOT ACCEPTANCE\n' if suffix == 'stdout'
                                                else b'GUEST_CAUGHT_VIOLATION\n')
                name = str(number)+'-'+suffix+'.bin'
                (root/d.p.OUTPUT/name).write_bytes(body)
                refs.append({'path': name, 'bytes': len(body), 'sha256': d.sha(body)})
                budget.output += len(body)
            result['output'] = refs
            if number == 2:
                result['exit_code'] = 1
                (root/d.p.OUTPUT/'install-guest-result.json').unlink()
            return result
        self.assertEqual(self.old.execute(old_failure)['reason'], 'P2_COMMAND_FAILED')
        self.methods = d.json_body((ROOT/d.METHODS).read_bytes())
        self.methods['root_sha256'] = d.sha(str(self.root).encode())
        for ref in (d.FROZEN_REF, d.CANDIDATE_REF, d.PROPOSAL_REF, d.COMPONENT_REVIEW_REF):
            self.save(ref['path'], (ROOT/ref['path']).read_bytes())
        self.methods['frozen_methods_ref'] = self.save(d.p.METHODS, d.packed(self.old.methods))
        self.methods['prior_packet_ref'] = self.save(
            'data/processed/e01_pypdf701_build_v1/install-v1_5-packet-20261116.json', d.packed(self.old.packet))
        self.methods['latest_terminal_ref'] = self.ref(d.p.OUTPUT+'/TERMINAL.json')
        self.methods['latest_started_ref'] = self.ref(d.p.OUTPUT+'/STARTED.json')
        self.methods['requirements_ref'] = self.ref(d.p.OUTPUT+'/requirements.txt')
        self.code_ref = self.save(d.CODE_PATH, (ROOT/d.CODE_PATH).read_bytes())
        self.calls = []; self.time = [0.0]
        self.rebind_release()

    def save(self, name, raw):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {'path': name, 'bytes': len(raw), 'sha256': d.sha(raw)}

    def ref(self, name):
        raw = (self.root/name).read_bytes()
        return {'path': name, 'bytes': len(raw), 'sha256': d.sha(raw)}

    def rebind_release(self):
        self.save(d.METHODS, d.packed(self.methods))
        core = {'kind': 'E01_GUARD_DIAGNOSTIC_EXECUTION_PACKET_V1',
                'root_sha256': self.methods['root_sha256'], 'methods_sha256': d.sha(d.packed(self.methods)),
                'diagnostic_code_ref': self.code_ref, 'execution_enabled': True}
        review = {'status': 'PASS_MOCK_AUTHORED_ONLY_NOT_ACTUAL_RELEASE',
                  'reviewed_packet_core_sha256': d.sha(d.packed(core)),
                  'evidence_refs': {d.CODE_PATH: self.code_ref, d.METHODS: self.ref(d.METHODS)}}
        self.packet = {**core, 'review_ref': self.save('reports/INDEPENDENT_AUDIT_MOCK_DIAGNOSTIC.json', d.packed(review))}

    def launcher(self, command, env, root, budget, number):
        self.calls.append((command, env, number))
        payload = d.json_body((root/d.OUTPUT/'guest-payload.json').read_bytes())
        observer = d.c.RefusalJournal()
        (root/d.OUTPUT/'guest-refusals.json').write_bytes(observer.packed())
        receipt = {'kind': 'E01_GUARD_DIAGNOSTIC_GUEST_RESULT_V1',
                   'pip_arguments_sha256': d.sha(d.packed(payload['pip_arguments'])),
                   'guard_violations': 0, 'pip_completed': True, 'error_code': None,
                   'mime_configuration': d.p.MIME_RECEIPT, 'installation_accepted': False,
                   'downloaded_package_imports': False, 'target_exists': False}
        (root/d.OUTPUT/'guest-result.json').write_bytes(d.packed(receipt))
        return {'exit_code': 0, 'pip_helper_descendants_permitted': 0, 'output': [],
                'observed_reaped_CPU_seconds': 0}

    def execute(self, launcher=None):
        return d.execute(self.root, self.methods, self.packet, launcher=launcher or self.launcher,
                         clock=lambda: self.time[0])

    def terminal(self): return d.json_body((self.root/d.OUTPUT/'TERMINAL.json').read_bytes())

    def test_no_refusal_is_only_diagnostic_and_preserves_all_old_roots(self):
        before = d.snapshot(self.root)
        result = self.execute()
        self.assertEqual(result['outcome'], 'NO_REFUSAL_REPRODUCED')
        self.assertFalse(result['installation_accepted'])
        self.assertEqual(d.snapshot(self.root), before)
        self.assertFalse((self.root/d.TARGET).exists())
        self.assertEqual(len(self.calls), 1)
        command, env, number = self.calls[0]
        self.assertEqual(command[0], self.old.binding['executable_ref']['path'])
        self.assertEqual(command[1:4], ['-I', '-B', '-S'])
        self.assertEqual(env['PATH'], str(self.old.base/'bin')+':/usr/bin:/bin')
        self.assertEqual(number, 1)
        terminal = self.terminal()
        self.assertEqual(terminal['allocation'], d.ALLOCATION)
        self.assertEqual(terminal['prior']['actual_prior_commands_started'], 6)
        self.assertEqual(terminal['combined_logical_bytes_including_terminal'], d.owned_size(self.root))

    def test_consumed_scope_cannot_be_replayed(self):
        self.execute(); self.calls.clear()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_ALREADY_CONSUMED'): self.execute()
        self.assertEqual(self.calls, [])

    def test_preexisting_uncreated_prefix_refuses_before_scope(self):
        (self.root/d.TARGET).mkdir()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_ALREADY_CONSUMED'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_missing_enabled_packet_refuses_before_mutation(self):
        self.packet['execution_enabled'] = False
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_EXPLICIT_RELEASE_REQUIRED'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_unrelated_particular_review_is_rejected(self):
        ref = self.packet['review_ref']; review = d.json_body((self.root/ref['path']).read_bytes())
        review['reviewed_packet_core_sha256'] = '0'*64
        self.packet['review_ref'] = self.save(ref['path'], d.packed(review))
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_EXACT_PARTICULAR_REVIEW'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_changed_running_source_is_rejected(self):
        self.save(d.CODE_PATH, b'MOCK DIFFERENT CODE')
        with self.assertRaisesRegex(d.Refused, 'INPUT_TYPE_SIZE|INPUT_HASH'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_prior_full_allocations_cannot_reset(self):
        self.methods['allocation']['prior_main_commands'] = 0
        self.rebind_release()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_METHODS_IDENTITY'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_changed_latest_failed_terminal_rejected_before_scope(self):
        path = self.root/d.p.OUTPUT/'TERMINAL.json'; raw = path.read_bytes()
        path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(d.Refused, 'INPUT_HASH'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_older_failed_source_still_required(self):
        path = self.root/'scripts/install_e01_pypdf701_runtime_v1_3.py'
        raw = path.read_bytes(); path.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(d.Refused, 'INPUT_HASH'): self.execute()

    def test_prior_unknown_denial_marker_cannot_be_removed_even_with_new_hash(self):
        terminal_ref = self.methods['latest_terminal_ref']
        terminal = d.json_body((self.root/terminal_ref['path']).read_bytes())
        ref = terminal['results'][1]['output'][1]
        full = self.save(d.p.OUTPUT+'/'+ref['path'], b'MOCK UNRELATED FAILURE\n')
        terminal['results'][1]['output'][1] = {**full, 'path': ref['path']}
        terminal['captured_command_output_bytes'] = sum(r['bytes'] for item in terminal['results'] for r in item['output'])
        self.methods['latest_terminal_ref'] = self.save(terminal_ref['path'], d.packed(terminal))
        self.rebind_release()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_PRIOR_UNKNOWN_DENIAL'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_refusal_evidence_retains_failed_child_postcondition(self):
        def refused(command, env, root, budget, number):
            result = self.launcher(command, env, root, budget, number)
            journal = d.c.RefusalJournal(); journal.record('GUEST_READ_OUTSIDE_ALLOWLIST', 'FILE_READ')
            (root/d.OUTPUT/'guest-refusals.json').write_bytes(journal.packed())
            path = root/d.OUTPUT/'guest-result.json'; receipt = d.json_body(path.read_bytes())
            receipt.update(guard_violations=1, error_code='GUEST_CAUGHT_VIOLATION')
            path.write_bytes(d.packed(receipt)); result['exit_code'] = 1
            return result
        outcome = self.execute(refused)
        self.assertEqual(outcome['outcome'], 'REFUSAL_OBSERVED')
        self.assertEqual(outcome['reason'], 'GUEST_CAUGHT_VIOLATION')
        self.assertFalse(outcome['installation_accepted'])

    def test_zero_exit_cannot_waive_nonzero_violation(self):
        def waived(command, env, root, budget, number):
            result = self.launcher(command, env, root, budget, number)
            journal = d.c.RefusalJournal(); journal.record('GUEST_READ_CAP', 'FILE_READ')
            (root/d.OUTPUT/'guest-refusals.json').write_bytes(journal.packed())
            path = root/d.OUTPUT/'guest-result.json'; receipt = d.json_body(path.read_bytes())
            receipt.update(guard_violations=1, error_code='GUEST_CAUGHT_VIOLATION')
            path.write_bytes(d.packed(receipt)); return result
        result = self.execute(waived)
        self.assertEqual(result['outcome'], 'FAILED_DIAGNOSTIC')
        self.assertEqual(result['reason'], 'DIAGNOSTIC_REFUSAL_POSTCONDITION')

    def test_missing_journal_is_failure_and_never_installation_acceptance(self):
        def missing(command, env, root, budget, number):
            result = self.launcher(command, env, root, budget, number)
            (root/d.OUTPUT/'guest-refusals.json').unlink(); return result
        self.assertEqual(self.execute(missing)['outcome'], 'FAILED_DIAGNOSTIC')

    def test_raw_path_journal_entry_is_rejected(self):
        def unsafe(command, env, root, budget, number):
            result = self.launcher(command, env, root, budget, number)
            value = d.json_body((root/d.OUTPUT/'guest-refusals.json').read_bytes())
            value.update(events=[{'sequence': 1, 'code': '/MOCK/PRIVATE', 'operation': 'FILE_READ'}], total_events=1)
            (root/d.OUTPUT/'guest-refusals.json').write_bytes(d.packed(value)); return result
        self.assertEqual(self.execute(unsafe)['reason'], 'DIAGNOSTIC_JOURNAL_EVENT')

    def test_target_creation_or_old_metadata_change_cannot_pass(self):
        def changed(command, env, root, budget, number):
            result = self.launcher(command, env, root, budget, number)
            (root/d.p.TARGET/'MOCK_UNEXPECTED').write_bytes(b'X'); return result
        self.assertEqual(self.execute(changed)['reason'], 'DIAGNOSTIC_OLD_STATE_CHANGED')

    def test_fictional_prefix_creation_cannot_pass(self):
        def created(command, env, root, budget, number):
            result = self.launcher(command, env, root, budget, number)
            (root/d.TARGET).mkdir(); return result
        self.assertEqual(self.execute(created)['reason'], 'DIAGNOSTIC_TARGET_CREATED')

    def test_command_stop_records_failure_without_retry(self):
        def stopped(*args):
            raise d.CommandStopped('MOCK_BOUND_STOP', {'exit_code': -9, 'stopped': True,
                'observed_reaped_CPU_seconds': 1, 'pip_helper_descendants_permitted': 0, 'output': []})
        result = self.execute(stopped)
        self.assertEqual(result['outcome'], 'FAILED_DIAGNOSTIC')
        self.assertEqual(result['commands_started'], 1)
        self.assertTrue((self.root/d.OUTPUT/'1-COMMAND_STOPPED.json').exists())

    def test_preflight_reserves_entire_diagnostic_scope(self):
        with patch.object(d, 'owned_size', return_value=d.CAPS['owned_logical_bytes']-d.DIAGNOSTIC_SCOPE_BYTES+1):
            with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_STORAGE_PREFLIGHT'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_exact_dry_run_payload_and_no_external_environment(self):
        self.execute()
        payload = d.json_body((self.root/d.OUTPUT/'guest-payload.json').read_bytes())
        original = d.p.pip_arguments('install', self.root/d.TARGET, self.root/d.OUTPUT/'requirements.txt')
        self.assertEqual(payload['pip_arguments'], original[:6]+['--dry-run']+original[6:])
        self.assertLessEqual(payload['remaining_wall_seconds'], 30)
        self.assertEqual(set(self.calls[0][1]), {'HOME','TMPDIR','PATH','PIP_CONFIG_FILE',
                         'PIP_DISABLE_PIP_VERSION_CHECK','PYTHONDONTWRITEBYTECODE','LC_ALL','LANG'})


class DiagnosticPureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e01-diagnostic-pure-MOCK-'); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_all_seven_roots_share_one_storage_limit(self):
        members = set()
        for name in d.PRESERVED_ROOTS+(d.OUTPUT,):
            tree = self.root/name; tree.mkdir(parents=True); path = tree/'MOCK_LARGE'; path.write_bytes(b'X'); members.add(path)
        original = Path.lstat
        def large(path):
            if path in members: return SimpleNamespace(st_mode=0o100600, st_size=d.CAPS['owned_logical_bytes']//7+1)
            return original(path)
        with patch.object(Path, 'lstat', large):
            with self.assertRaisesRegex(d.Refused, 'OWNED_LOGICAL_BYTES_CAP'): d.owned_size(self.root)

    def test_diagnostic_scope_has_its_own_smaller_limit(self):
        tree = self.root/d.OUTPUT; tree.mkdir(parents=True); path = tree/'MOCK_LARGE'; path.write_bytes(b'X')
        original = Path.lstat
        def large(value):
            if value == path: return SimpleNamespace(st_mode=0o100600, st_size=d.DIAGNOSTIC_SCOPE_BYTES+1)
            return original(value)
        with patch.object(Path, 'lstat', large):
            with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_SCOPE_LOGICAL_CAP'): d.owned_size(self.root)

    def test_terminal_final_union_bytes_and_scope_precharge(self):
        (self.root/d.OUTPUT).mkdir(parents=True)
        d.Journal(self.root).save('TERMINAL.json', {'kind':'MOCK_ONLY'})
        value = d.json_body((self.root/d.OUTPUT/'TERMINAL.json').read_bytes())
        self.assertEqual(value['combined_logical_bytes_including_terminal'], d.owned_size(self.root))
        with patch.object(d, 'logical_scope_size', return_value=d.DIAGNOSTIC_SCOPE_BYTES-1):
            with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_SCOPE_JOURNAL_CAP'):
                d.Journal(self.root).save('NO_EFFECT.json', b'XX')
        self.assertFalse((self.root/d.OUTPUT/'NO_EFFECT.json').exists())

    def test_budget_thirty_second_deadline_cpu_and_rollback(self):
        value = [0.0]; budget = d.StageBudget(self.root, lambda:value[0])
        value[0] = 30
        with self.assertRaisesRegex(d.Refused, 'P2_WALL_LIMIT'): budget.check()
        value[0] = -1
        with self.assertRaisesRegex(d.Refused, 'P2_CLOCK_REGRESSION'): budget.check()
        value[0] = 0; budget = d.StageBudget(self.root, lambda:value[0])
        with patch.object(d.resource, 'getrusage', return_value=SimpleNamespace(ru_utime=20,st_utime=0,ru_stime=0)):
            with self.assertRaisesRegex(d.Refused, 'P2_OBSERVED_AGGREGATE_CPU_LIMIT'): budget.check()

    def test_mock_run_pip_uses_only_pinned_package_and_one_dry_run(self):
        base = self.root/'MOCK_BASE'; dynamic = base/'lib/python3.12/lib-dynload'; dynamic.mkdir(parents=True)
        pip = self.root/'.venv/lib/python3.12/site-packages/pip'; pip.mkdir(parents=True)
        (pip/'__init__.py').write_text('__version__="25.0.1"\n# MOCK NEVER A REAL PIP\n')
        binding = {'base_prefix':str(base),'pip_root':str(pip.relative_to(self.root))}
        arguments = d.c.dry_run_arguments(d.p.pip_arguments('install',self.root/d.TARGET,self.root/d.OUTPUT/'requirements.txt'))
        before_path, before_args, before_pip = list(sys.path), sys.argv, sys.modules.get('pip')
        observed = []
        try:
            sys.path[:] = [str(base/'lib/python312.zip'),str(base/'lib/python3.12'),str(dynamic)]
            with (patch.object(d.p,'target_scheme',return_value={}),
                  patch.object(d.runpy,'run_module',side_effect=lambda *a,**k:observed.append((list(sys.path),list(sys.argv))))):
                d.run_dry_pip(binding,self.root,arguments)
            self.assertEqual(observed[0][1],arguments)
            self.assertNotIn(str(pip.parent),observed[0][0])
            self.assertEqual(observed[0][0][0],str(self.root/d.SITE))
        finally:
            sys.path[:]=before_path;sys.argv=before_args
            if before_pip is None:sys.modules.pop('pip',None)
            else:sys.modules['pip']=before_pip
        self.assertFalse((self.root/d.TARGET).exists())

    def test_unknown_journal_fields_and_oversize_refuse(self):
        value=d.json_body(d.c.RefusalJournal().packed());value['raw_path']='/MOCK_PRIVATE'
        with self.assertRaisesRegex(d.Refused,'DIAGNOSTIC_JOURNAL_SCHEMA'):d.validate_journal(d.packed(value))
        with self.assertRaisesRegex(d.Refused,'DIAGNOSTIC_JOURNAL_SIZE'):d.validate_journal(b'X'*4097)

    def test_original_versions_candidate_proposal_and_review_hashes_unchanged(self):
        for ref in (d.FROZEN_REF,d.CANDIDATE_REF,d.PROPOSAL_REF,d.COMPONENT_REVIEW_REF):
            raw=(ROOT/ref['path']).read_bytes()
            self.assertEqual(len(raw),ref['bytes']);self.assertEqual(d.sha(raw),ref['sha256'])

    def test_guest_installs_guard_before_mime_pip_and_flushes_before_postcondition(self):
        source=(ROOT/d.CODE_PATH).read_text();body=source[source.index('def guest_main('):source.index('def main(')]
        self.assertLess(body.index('policy = install_guard('),body.index('mime = p.prepare_builtin_mime('))
        self.assertLess(body.index('mime = p.prepare_builtin_mime('),body.index('run_dry_pip('))
        self.assertLess(body.index("write_guest_file('guest-refusals.json'"),body.index("need(policy.violations == 0"))

    def test_frozen_process_launcher_and_budget_copy_only_tighten_limits(self):
        original = ast.parse((ROOT/d.FROZEN_REF['path']).read_bytes())
        updated = ast.parse((ROOT/d.CODE_PATH).read_bytes())
        class Normalize(ast.NodeTransformer):
            def visit_Constant(self, node):
                if type(node.value) is int and node.value == 30: node.value = 120
                elif type(node.value) is int and node.value == 20: node.value = 40
                return node
        for name in ('run_command','StageBudget','CommandStopped'):
            before = next(node for node in original.body if getattr(node,'name',None) == name)
            after = next(node for node in updated.body if getattr(node,'name',None) == name)
            self.assertEqual(ast.dump(before,include_attributes=False),
                             ast.dump(Normalize().visit(after),include_attributes=False))

    def test_frozen_journal_copy_only_adds_scope_precharge(self):
        original = ast.parse((ROOT/d.FROZEN_REF['path']).read_bytes())
        updated = ast.parse((ROOT/d.CODE_PATH).read_bytes())
        before = next(node for node in original.body if isinstance(node,ast.ClassDef) and node.name=='Journal')
        after = next(node for node in updated.body if isinstance(node,ast.ClassDef) and node.name=='Journal')
        method = next(node for node in after.body if isinstance(node,ast.FunctionDef) and node.name=='save')
        removed=[]; retained=[]
        for node in method.body:
            text=ast.unparse(node)
            if text.startswith('scope_occupied = ') or 'DIAGNOSTIC_SCOPE_JOURNAL_CAP' in text:removed.append(node)
            else:retained.append(node)
        self.assertEqual(len(removed),2);method.body=retained
        self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False))

    def test_installed_guard_retains_every_wrapper_after_routing(self):
        original = ast.parse((ROOT/d.FROZEN_REF['path']).read_bytes())
        updated = ast.parse((ROOT/d.CODE_PATH).read_bytes())
        before = next(node for node in original.body if isinstance(node,ast.FunctionDef) and node.name=='install_guest_guard')
        after = next(node for node in updated.body if isinstance(node,ast.FunctionDef) and node.name=='install_guard')
        after.name=before.name
        after.body=[node for node in after.body if not (isinstance(node,ast.Import) and any(alias.name=='io' for alias in node.names))
                    and not (isinstance(node,ast.Expr) and 'policy.exact_reads.update' in ast.unparse(node))]
        assignment=next(node for node in after.body if isinstance(node,ast.Assign)
                        and any(isinstance(target,ast.Name) and target.id=='policy' for target in node.targets))
        self.assertEqual(ast.unparse(assignment.value),'c.diagnostic_policy_class(p.GuestPolicy)(root, binding, payload)')
        assignment.value=ast.parse('GuestPolicy(root, binding, payload)',mode='eval').body
        class Normalize(ast.NodeTransformer):
            def visit_Attribute(self,node):
                if isinstance(node.value,ast.Name) and node.value.id=='p' and node.attr in {
                    'load_bound_module','GUARD_REF','DownloadedImportGuard','ChargedFile'}:
                    return ast.copy_location(ast.Name(id=node.attr,ctx=node.ctx),node)
                return self.generic_visit(node)
            def visit_Constant(self,node):
                if node.value=='diagnostic_bound_dirfd_guard':node.value='p2_reviewed_dirfd_guard'
                return node
        self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(Normalize().visit(after),include_attributes=False))

    def fake_process(self,*args,**kwargs):
        def pipe(body):
            read,write=os.pipe();os.write(write,body);os.close(write)
            return os.fdopen(read,'rb',buffering=0)
        self.assertTrue(kwargs['start_new_session'])
        return SimpleNamespace(pid=54321,stdout=pipe(b'abc'),stderr=pipe(b'd'),returncode=None)

    def test_process_capture_observes_reaped_cpu_without_actual_process(self):
        (self.root/d.OUTPUT).mkdir(parents=True);budget=d.StageBudget(self.root)
        usage=SimpleNamespace(ru_utime=.1,ru_stime=.2)
        with (patch.object(d.subprocess,'Popen',side_effect=self.fake_process),
              patch.object(d.os,'wait4',return_value=(54321,0,usage))):
            result=d.run_command(['MOCK_NEVER_EXECUTED'],{},self.root,budget,1)
        self.assertEqual(result['exit_code'],0);self.assertAlmostEqual(budget.reaped_cpu,.3)
        self.assertEqual((self.root/d.OUTPUT/'1-stdout.bin').read_bytes(),b'abc')

    def test_process_output_overflow_kills_reaps_without_retry(self):
        (self.root/d.OUTPUT).mkdir(parents=True);budget=d.StageBudget(self.root)
        budget.output=d.CAPS['command_output_bytes']-1
        usage=SimpleNamespace(ru_utime=.1,ru_stime=.2)
        with (patch.object(d.subprocess,'Popen',side_effect=self.fake_process),
              patch.object(d.os,'killpg') as kill,
              patch.object(d.os,'wait4',return_value=(54321,9,usage))):
            with self.assertRaises(d.CommandStopped) as stopped:
                d.run_command(['MOCK_NEVER_EXECUTED'],{},self.root,budget,1)
        kill.assert_called_once_with(54321,d.signal.SIGKILL)
        self.assertEqual(stopped.exception.record['exit_code'],-9)


if __name__ == '__main__':
    f.old.g.old.guarded_test_main()
