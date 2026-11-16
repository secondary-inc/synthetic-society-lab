"""Guarded authored controller/guest fixtures. No actual diagnostic or pip run."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
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

d = load('authored_diagnostic_runner_v2', ROOT/'scripts/diagnose_e01_pypdf701_guard_v2.py')
g = load('accepted_diagnostic_v1_fixtures', ROOT/'tests/test_e01_pypdf701_guard_diagnostic_v1.py')
g.d = d.q
g.f.p = d.p; g.f.old.p = d.p; g.f.old.t.p = d.p
f = g.f

ORIGINAL_READER = d.p.Reader


def temporary_fixture_reader():
    """Cache only verified mock bytes; keep original per-reference charges.

    Nested fixture construction revalidates the same temporary controls many
    times. File identity changes always fall back to the original disk reader.
    Production code uses the unmodified original Reader in its own process.
    """
    cache, retained_bytes = {}, [0]
    temporary_root = Path(tempfile.gettempdir()).resolve()
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    class FixtureReader(ORIGINAL_READER):
        def read(self, ref, absolute=False):
            if not (type(ref) is dict and set(ref) == {'path','bytes','sha256'}
                    and type(ref['path']) is str and type(ref['bytes']) is int
                    and 0 <= ref['bytes'] <= d.p.CAPS['single_file_bytes']
                    and type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256'])):
                return super().read(ref,absolute=absolute)
            root = Path(self.root).absolute()
            if not root.is_relative_to(temporary_root) or root.is_relative_to(ROOT):
                return super().read(ref,absolute=absolute)
            path = Path(ref['path']) if absolute else d.p.relative(root,ref['path'])
            d.need(not absolute or path.is_absolute(),'ABSOLUTE_REF')
            if not path.is_relative_to(root): return super().read(ref,absolute=absolute)
            d.no_alias(path); before = path.stat(follow_symlinks=False)
            d.need(stat.S_ISREG(before.st_mode) and before.st_size == ref['bytes'],'INPUT_TYPE_SIZE')
            key = (str(path),identity(before),ref['bytes'],ref['sha256'])
            if key in cache:
                # Cached bytes do not grant access after permission revocation.
                # The original disk reader determines the resulting denial.
                if not os.access(path,os.R_OK): return super().read(ref,absolute=absolute)
                self.charged += ref['bytes']+1
                d.need(self.charged <= self.limit,'READ_CAP')
                raw = cache[key]
                d.need(len(raw) == ref['bytes'] and d.sha(raw) == ref['sha256'],'INPUT_HASH')
                return raw
            raw = super().read(ref,absolute=absolute)
            after = path.stat(follow_symlinks=False)
            if identity(before) == identity(after) and retained_bytes[0]+len(raw) <= 8388608:
                cache[key] = raw; retained_bytes[0] += len(raw)
            return raw
    return FixtureReader



class DiagnosticFixtureTests(unittest.TestCase):
    def setUp(self):
        reader_patch = patch.object(d.p,'Reader',temporary_fixture_reader())
        reader_patch.start(); self.addCleanup(reader_patch.stop)
        self.prior = g.DiagnosticFixtureTests('test_no_refusal_is_only_diagnostic_and_preserves_all_old_roots')
        self.prior.setUp(); self.addCleanup(self.prior.doCleanups)
        self.old, self.root = self.prior.old, self.prior.root
        def prior_refusal(command, env, root, budget, number):
            result = self.prior.launcher(command, env, root, budget, number)
            observer = d.q.c.RefusalJournal()
            observer.record('GUEST_NETWORK_HELPER_OR_CTYPES_DENIED', 'SOCKET')
            (root/d.q.OUTPUT/'guest-refusals.json').write_bytes(observer.packed())
            path = root/d.q.OUTPUT/'guest-result.json'; receipt = d.json_body(path.read_bytes())
            receipt.update(guard_violations=1, error_code='GUEST_CAUGHT_VIOLATION')
            path.write_bytes(d.packed(receipt))
            outputs = []
            for suffix, body in [('stdout', b'MOCK WOULD INSTALL NOT ACCEPTANCE\n'),
                                 ('stderr', b'GUEST_CAUGHT_VIOLATION\n')]:
                name = '1-'+suffix+'.bin'; (root/d.q.OUTPUT/name).write_bytes(body)
                outputs.append({'path': name, 'bytes': len(body), 'sha256': d.sha(body)})
                budget.output += len(body)
            result.update(exit_code=1, output=outputs)
            return result
        self.assertEqual(self.prior.execute(prior_refusal)['outcome'], 'REFUSAL_OBSERVED')
        self.methods = d.json_body((ROOT/d.METHODS).read_bytes())
        self.methods['root_sha256'] = d.sha(str(self.root).encode())
        for ref in (d.FROZEN_REF, d.CANDIDATE_REF, d.PROPOSAL_REF, d.COMPONENT_REVIEW_REF,
                    d.PRIOR_DIAGNOSTIC_REF, d.RATIONALE_REF, d.MAPPING_REF, d.PRIOR_ACTUAL_REVIEW_REF):
            self.save(ref['path'], (ROOT/ref['path']).read_bytes())
        for name in ('frozen_methods_ref', 'prior_packet_ref', 'latest_terminal_ref',
                     'latest_started_ref', 'requirements_ref'):
            self.methods[name] = self.prior.methods[name]
        self.methods['prior_diagnostic_methods_ref'] = self.ref(d.q.METHODS)
        refs = {'packet': self.save('data/processed/e01_pypdf701_build_v1/diagnostic-v1-packet-20261116.json',
                                    d.packed(self.prior.packet))}
        for name in ('TERMINAL.json', 'STARTED.json', 'requirements.txt', 'guest-payload.json',
                     '1-COMMAND_RESERVED.json', '1-COMMAND_RECORDED.json', '1-stdout.bin', '1-stderr.bin',
                     'guest-refusals.json', 'guest-result.json'):
            refs[name] = self.ref(d.q.OUTPUT+'/'+name)
        self.methods['prior_diagnostic_refs'] = refs
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
        self.packet = {**core, 'review_ref': self.save('reports/INDEPENDENT_AUDIT_MOCK_DIAGNOSTIC_V2.json', d.packed(review))}

    def launcher(self, command, env, root, budget, number):
        self.calls.append((command, env, number))
        payload = d.json_body((root/d.OUTPUT/'guest-payload.json').read_bytes())
        observer = d.c.RefusalJournal()
        (root/d.OUTPUT/'guest-refusals.json').write_bytes(observer.packed())
        receipt = {'kind': 'E01_GUARD_DIAGNOSTIC_GUEST_RESULT_V2',
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
        self.assertEqual(terminal['prior']['actual_prior_commands_started'], 7)
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
        self.assertEqual(self.execute(changed)['reason'], 'DIAGNOSTIC_V1_STARTED')

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

    def test_closed_v1_coarse_event_is_retained_without_historical_relabeling(self):
        before = d.snapshot(self.root)
        self.execute()
        history = self.terminal()['prior']['diagnostic_v1']
        self.assertEqual(history['original_coarse_journal']['kind'], 'BOUNDED_GUEST_REFUSAL_JOURNAL_V1')
        self.assertEqual(history['original_coarse_journal']['events'][0]['operation'], 'SOCKET')
        self.assertEqual(d.snapshot(self.root), before)
        self.assertEqual(self.terminal()['refusals']['kind'], 'BOUNDED_GUEST_REFUSAL_JOURNAL_V2')

    def test_missing_closed_v1_control_cannot_be_omitted(self):
        del self.methods['prior_diagnostic_refs']['1-stdout.bin']
        self.rebind_release()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_V1_REF_SET'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_old_packet_disable_is_not_released_by_new_packet(self):
        ref = self.methods['prior_diagnostic_refs']['packet']
        packet = d.json_body((self.root/ref['path']).read_bytes()); packet['execution_enabled'] = False
        self.methods['prior_diagnostic_refs']['packet'] = self.save(ref['path'], d.packed(packet))
        self.rebind_release()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_EXPLICIT_RELEASE_REQUIRED'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_rehashed_old_guest_cannot_erase_original_violation(self):
        ref = self.methods['prior_diagnostic_refs']['guest-result.json']
        guest = d.json_body((self.root/ref['path']).read_bytes()); guest['guard_violations'] = 0
        self.methods['prior_diagnostic_refs']['guest-result.json'] = self.save(ref['path'], d.packed(guest))
        self.rebind_release()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_V1_GUEST_RESULT'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_rehashed_old_journal_cannot_be_reinterpreted_as_construction(self):
        ref = self.methods['prior_diagnostic_refs']['guest-refusals.json']
        value = d.json_body((self.root/ref['path']).read_bytes())
        value['events'][0]['operation'] = 'SOCKET_CONSTRUCT'
        self.methods['prior_diagnostic_refs']['guest-refusals.json'] = self.save(ref['path'], d.packed(value))
        self.rebind_release()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_JOURNAL_EVENT'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_coherently_rehashed_old_argv_cannot_omit_dry_run(self):
        refs = self.methods['prior_diagnostic_refs']; ref = refs['guest-payload.json']
        value = d.json_body((self.root/ref['path']).read_bytes())
        value['pip_arguments'].remove('--dry-run')
        refs['guest-payload.json'] = self.save(ref['path'], d.packed(value))
        terminal_ref = refs['TERMINAL.json']; terminal = d.json_body((self.root/terminal_ref['path']).read_bytes())
        for index, artifact in enumerate(terminal['artifacts']):
            if artifact['path'] == 'guest-payload.json':
                terminal['artifacts'][index] = {**refs['guest-payload.json'], 'path': 'guest-payload.json'}
        refs['TERMINAL.json'] = self.save(terminal_ref['path'], d.packed(terminal))
        self.rebind_release()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_V1_PAYLOAD'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_changed_old_stdout_cannot_be_rebound_without_original_record(self):
        ref = self.methods['prior_diagnostic_refs']['1-stdout.bin']
        self.methods['prior_diagnostic_refs']['1-stdout.bin'] = self.save(ref['path'], b'MOCK DIFFERENT OUTPUT')
        self.rebind_release()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_V1_OUTPUT_REF'): self.execute()

    def test_metadata_change_in_consumed_diagnostic_scope_prevents_success(self):
        def changed(command, env, root, budget, number):
            result = self.launcher(command, env, root, budget, number)
            (root/d.q.OUTPUT/'MOCK_EXTRA_OLD_FILE').write_bytes(b'X'); return result
        self.assertEqual(self.execute(changed)['reason'], 'DIAGNOSTIC_OLD_STATE_CHANGED')

    def test_preexisting_old_fictional_prefix_remains_a_failure(self):
        (self.root/d.q.TARGET).mkdir()
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_V1_TARGET_CREATED'): self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())

    def test_finer_construction_event_remains_failed_and_no_callsite_is_inferred(self):
        def refused(command, env, root, budget, number):
            result = self.launcher(command, env, root, budget, number)
            journal = d.c.RefusalJournal()
            journal.record('GUEST_NETWORK_HELPER_OR_CTYPES_DENIED', 'SOCKET_CONSTRUCT')
            (root/d.OUTPUT/'guest-refusals.json').write_bytes(journal.packed())
            path = root/d.OUTPUT/'guest-result.json'; guest = d.json_body(path.read_bytes())
            guest.update(guard_violations=1, error_code='GUEST_CAUGHT_VIOLATION')
            path.write_bytes(d.packed(guest)); result['exit_code'] = 1; return result
        self.assertEqual(self.execute(refused)['outcome'], 'REFUSAL_OBSERVED')
        value = self.terminal()
        self.assertEqual(value['refusals']['events'][0]['operation'], 'SOCKET_CONSTRUCT')
        self.assertFalse(value['installation_accepted'])
        self.assertNotIn('callsite', value)
        self.assertEqual(value['prior']['diagnostic_v1']['original_coarse_journal']['events'][0]['operation'], 'SOCKET')


class DiagnosticPureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e01-diagnostic-pure-MOCK-'); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_all_eight_roots_share_one_storage_limit(self):
        members = set()
        for name in d.PRESERVED_ROOTS+(d.OUTPUT,):
            tree = self.root/name; tree.mkdir(parents=True); path = tree/'MOCK_LARGE'; path.write_bytes(b'X'); members.add(path)
        original = Path.lstat
        def large(path):
            if path in members: return SimpleNamespace(st_mode=0o100600, st_size=(d.DIAGNOSTIC_SCOPE_BYTES if path.parent in (self.root/d.q.OUTPUT, self.root/d.OUTPUT)
                    else (d.CAPS['owned_logical_bytes']-2*d.DIAGNOSTIC_SCOPE_BYTES)//6+1))
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

    def test_old_consumed_diagnostic_retains_sixteen_mib_limit(self):
        tree = self.root/d.q.OUTPUT; tree.mkdir(parents=True); path = tree/'MOCK_LARGE'; path.write_bytes(b'X')
        original = Path.lstat
        def large(value):
            if value == path: return SimpleNamespace(st_mode=0o100600, st_size=d.DIAGNOSTIC_SCOPE_BYTES+1)
            return original(value)
        with patch.object(Path, 'lstat', large):
            with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_SCOPE_LOGICAL_CAP'): d.owned_size(self.root)

    def test_journal_v1_and_v2_consumers_are_explicitly_separate(self):
        old = d.q.c.RefusalJournal().packed(); new = d.c.RefusalJournal().packed()
        self.assertEqual(d.q.validate_journal(old)['kind'], 'BOUNDED_GUEST_REFUSAL_JOURNAL_V1')
        self.assertEqual(d.validate_journal(new)['kind'], 'BOUNDED_GUEST_REFUSAL_JOURNAL_V2')
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_JOURNAL_SCHEMA'): d.validate_journal(old)
        with self.assertRaisesRegex(d.Refused, 'DIAGNOSTIC_JOURNAL_SCHEMA'): d.q.validate_journal(new)

    def test_existing_installation_validation_is_unchanged(self):
        old_tree = ast.parse((ROOT/d.PRIOR_DIAGNOSTIC_REF['path']).read_bytes())
        new_tree = ast.parse((ROOT/d.CODE_PATH).read_bytes())
        before = next(node for node in old_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'verify_inputs')
        after = next(node for node in new_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'verify_installation_inputs')
        after.name = before.name
        self.assertEqual(ast.dump(before, include_attributes=False), ast.dump(after, include_attributes=False))

    def test_new_journal_consumer_only_changes_protocol_label_from_frozen_v1(self):
        old_tree = ast.parse((ROOT/d.PRIOR_DIAGNOSTIC_REF['path']).read_bytes())
        new_tree = ast.parse((ROOT/d.CODE_PATH).read_bytes())
        before = next(node for node in old_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_journal')
        after = next(node for node in new_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_journal')
        class Normalize(ast.NodeTransformer):
            def visit_Constant(self, node):
                if node.value == 'BOUNDED_GUEST_REFUSAL_JOURNAL_V2': node.value = 'BOUNDED_GUEST_REFUSAL_JOURNAL_V1'
                return node
        self.assertEqual(ast.dump(before, include_attributes=False), ast.dump(Normalize().visit(after), include_attributes=False))

    def test_prior_runner_methods_and_authored_suite_remain_frozen(self):
        pins = [('scripts/diagnose_e01_pypdf701_guard_v1.py',37439,'c71209bcb3a8d0ec485c28dd5f3249d6b34faafd30677dcc908cbf1a656f3f31'),
                ('configs/e01_pypdf701_guard_diagnostic_v1_20261116.json',3624,'14b336eb9ac616c99f73023e6105e9903fc3521f53cc42b5939e42ae0dc2bca4'),
                ('tests/test_e01_pypdf701_guard_diagnostic_v1.py',25126,'16d745a764d1601dfd9f7668ad1ac18c165e80689ee59704a9f90d0384445a8b')]
        for name, size, digest in pins:
            raw = (ROOT/name).read_bytes(); self.assertEqual(len(raw),size); self.assertEqual(d.sha(raw),digest)

    def test_test_only_verified_cache_keeps_logical_quota_and_invalidates_mutation(self):
        path=self.root/'MOCK_VERIFIED_BYTES';path.write_bytes(b'MOCK')
        ref={'path':path.name,'bytes':4,'sha256':d.sha(b'MOCK')}
        reader=temporary_fixture_reader()(self.root,limit=10)
        self.assertEqual(reader.read(ref),b'MOCK');self.assertEqual(reader.read(ref),b'MOCK')
        self.assertEqual(reader.charged,10)
        with self.assertRaisesRegex(d.Refused,'READ_CAP'):reader.read(ref)
        changed=temporary_fixture_reader()(self.root)
        changed.read(ref);path.write_bytes(b'DIFF')
        with self.assertRaisesRegex(d.Refused,'INPUT_HASH'):changed.read(ref)

    def test_test_only_cache_refuses_read_denial_even_with_same_stat_identity(self):
        path=self.root/'MOCK_READ_PERMISSION';path.write_bytes(b'MOCK')
        ref={'path':path.name,'bytes':4,'sha256':d.sha(b'MOCK')}
        reader=temporary_fixture_reader()(self.root);reader.read(ref)
        raw_open=os.open
        def denied(value,*args,**kwargs):
            if Path(value)==path:raise PermissionError('MOCK_READ_DENIED')
            return raw_open(value,*args,**kwargs)
        with patch.object(os,'access',return_value=False),patch.object(os,'open',side_effect=denied):
            with self.assertRaisesRegex(PermissionError,'MOCK_READ_DENIED'):reader.read(ref)
        self.assertEqual(reader.charged,10)

    def test_test_only_cache_does_not_follow_replaced_symlink(self):
        path=self.root/'MOCK_BEFORE_ALIAS';path.write_bytes(b'MOCK')
        ref={'path':path.name,'bytes':4,'sha256':d.sha(b'MOCK')}
        reader=temporary_fixture_reader()(self.root);reader.read(ref)
        actual=self.root/'MOCK_NEW_LOCATION';path.rename(actual);path.symlink_to(actual)
        with self.assertRaisesRegex(d.Refused,'PATH_ALIAS'):reader.read(ref)

    def test_test_only_cache_refuses_rehashed_corruption_and_invalid_reference(self):
        path=self.root/'MOCK_REF_IDENTITY';path.write_bytes(b'MOCK')
        ref={'path':path.name,'bytes':4,'sha256':d.sha(b'MOCK')}
        reader=temporary_fixture_reader()(self.root);reader.read(ref)
        with self.assertRaisesRegex(d.Refused,'INPUT_HASH'):reader.read({**ref,'sha256':'0'*64})
        with self.assertRaisesRegex(d.Refused,'INPUT_REF'):reader.read({**ref,'bytes':True})

    def test_test_only_cache_never_claims_production_reader_replacement(self):
        self.assertIs(d.p.Reader,ORIGINAL_READER)
        source=(ROOT/d.CODE_PATH).read_text()
        self.assertNotIn('temporary_fixture_reader',source)

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
        for ref in (d.FROZEN_REF,d.CANDIDATE_REF,d.PROPOSAL_REF,d.COMPONENT_REVIEW_REF,d.PRIOR_DIAGNOSTIC_REF):
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
