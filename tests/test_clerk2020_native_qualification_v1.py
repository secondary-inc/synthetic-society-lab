"""Authored files and no-PDF pipe children only; decoder execution is mocked."""
import base64
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from civiclab.e01 import clerk2020_native_qualification_v1 as q
from civiclab.e01.clerk2020_m2_v1_1_contracts import Refused, canonical, decode, digest, sha


def prepare(root):
    refs = {}
    for name in q.CODE_PATHS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = ('# AUTHORED MOCK CODE RECORD ' + name).encode()
        path.write_bytes(raw)
        refs[name] = {'bytes': len(raw), 'sha256': sha(raw)}
    review = {'kind': 'CLERK_NATIVE_QUALIFICATION_CODE_REVIEW_V1',
              'status': 'PASS_EXACT_GENERATED_FIXTURE_PHASE_ONLY',
              'auditor_role': 'independent_auditor', 'code_refs': refs,
              'limits': q.LIMITS, 'actual_source_authority': False}
    review_raw = canonical(review)
    packet = {'schema_version': 1, 'kind': q.KIND, 'phase_id': 'qualification-v1',
              'root_sha256': sha(str(root).encode()), 'policy_sha256': q.POLICY_SHA,
              'code_refs': refs, 'review_bytes_b64': base64.b64encode(review_raw).decode(),
              'review_sha256': sha(review_raw), 'limits': q.LIMITS}
    raw = canonical(packet)
    return raw, sha(raw)


class FakeProcess:
    def __init__(self):
        self.stdin, self.stdout, self.stderr = BytesIO(), BytesIO(), BytesIO()
        self.pid, self.returncode = 123, 0
        self.waited = False

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        self.waited = True
        return self.returncode


def fake_response():
    manifest = [['REPO/' + q.CODE_PATHS[0], 1, 'a' * 64]]
    return {'label': 'MOCK_GENERATED_PDF_ONLY',
            'status': 'NATIVE_GENERATED_FIXTURES_COMPLETE',
            'actual_source_reads': 0, 'model_calls': 0, 'reader_attempts': 4,
            'expected_page_extractions': 119, 'positive_page_counts': [81, 38],
            'negative_cases_refused': 2, 'python': '3.12.14', 'pypdf': '6.10.0',
            'interpreter_implementation': 'cpython', 'platform': 'darwin', 'machine': 'arm64',
            'runtime_manifest': manifest, 'runtime_manifest_sha256': digest(manifest),
            'runtime_hash_bytes_observed': 1, 'runtime_hash_bytes_reserved': 2,
            'runtime_manifest_scope': q.MANIFEST_SCOPE, 'guard': q.GUARD_SCOPE}


def fake_exchange(process, packet, start, out, err):
    # This is never native qualification evidence. Only the parent's lifecycle
    # and durable accounting are exercised using an authored child response.
    out.extend(canonical(fake_response()))
    return 0


class QualificationTests(unittest.TestCase):
    def test_runtime_manifest_uses_only_authored_temp_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            prepare(root)
            base = root / 'data/processed/AUTHORED_TOOLCHAIN'
            binary = base / 'bin/python'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'AUTHORED_NOT_AN_INTERPRETER')
            module = SimpleNamespace(__file__=str(root / q.CODE_PATHS[0]), __cached__=None)
            with (patch.object(q.sys, 'base_prefix', str(base)),
                  patch.object(q.sys, 'executable', str(binary)),
                  patch.object(q.sys, 'modules', {'AUTHORED': module})):
                rows, observed, reserved = q._runtime_inventory(root)
            self.assertEqual(len(rows), 2)
            self.assertTrue(any(row[0] == 'PYTHON_BASE/bin/python' for row in rows))
            self.assertEqual(observed, sum(row[1] for row in rows))
            self.assertEqual(reserved, observed + 2)

    def test_runtime_origin_cannot_trigger_source_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            base = root / 'AUTHORED_BASE'
            binary = base / 'bin/python'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'AUTHORED_NOT_AN_INTERPRETER')
            module = SimpleNamespace(__file__=str(root / 'data/raw/FORBIDDEN.pdf'), __cached__=None)
            with (patch.object(q.sys, 'modules', {'AUTHORED': module}),
                  patch.object(q.sys, 'base_prefix', str(base)),
                  patch.object(q.sys, 'executable', str(binary)),
                  patch.object(q, '_stable_hash') as hasher):
                with self.assertRaises(Refused):
                    q._runtime_inventory(root)
                self.assertFalse(hasher.called)

    def test_worker_error_stage_without_raw_message(self):
        with patch.object(q, 'WORKER_STAGE', 'GUARDED_FIXTURES'):
            result = q._worker_failure(ValueError('AUTHORED_PRIVATE_ERROR_TEXT'))
        self.assertNotIn(b'AUTHORED_PRIVATE_ERROR_TEXT', result)
        self.assertEqual(decode(result)['stage'], 'GUARDED_FIXTURES')
        self.assertEqual(decode(result)['error_type'], 'ValueError')

    def test_partial_manifest_preserved_as_unqualified_on_error(self):
        partial = {'runtime_manifest': fake_response()['runtime_manifest'],
                   'runtime_manifest_sha256': fake_response()['runtime_manifest_sha256']}
        with patch.object(q, 'WORKER_PARTIAL', partial):
            result = decode(q._worker_failure(TimeoutError('PRIVATE')))
        self.assertEqual(result['runtime_manifest'], partial['runtime_manifest'])
        self.assertEqual(result['status'], 'NATIVE_FIXTURE_UNKNOWN_STOP')
    def test_worker_closed_shape_identity_and_manifest_hash(self):
        self.assertEqual(q.validate_worker(canonical(fake_response())), fake_response())
        for key, value in [('extra', 1), ('actual_source_reads', False),
                           ('python', 'UNKNOWN'), ('runtime_manifest_sha256', 'f' * 64),
                           ('runtime_hash_bytes_reserved', 1)]:
            wrong = fake_response()
            wrong[key] = value
            with self.subTest(key=key), self.assertRaises(Refused):
                q.validate_worker(canonical(wrong))

    def test_worker_manifest_cannot_name_sources_or_traverse(self):
        for name in ['REPO/data/raw/acquired.pdf', 'REPO/.env', 'REPO/../file', '/absolute']:
            wrong = fake_response()
            wrong['runtime_manifest'][0][0] = name
            wrong['runtime_manifest_sha256'] = digest(wrong['runtime_manifest'])
            with self.assertRaises(Refused):
                q.validate_worker(canonical(wrong))

    def exchange_child(self, code, packet, *, wall=None):
        process = subprocess.Popen([sys.executable, '-I', '-B', '-c', code],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True,
                                   env={'PATH': q.os.defpath, 'LC_ALL': 'C'})
        out, err = bytearray(), bytearray()
        try:
            if wall is None:
                peak = q._exchange(process, packet, time.monotonic(), out, err)
            else:
                with patch.dict(q.LIMITS, {'child_wall_seconds': wall}):
                    peak = q._exchange(process, packet, time.monotonic(), out, err)
            return bytes(out), bytes(err), peak
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=1)
            for stream in [process.stdin, process.stdout, process.stderr]:
                stream.close()

    def test_native_pipe_exchange_authored_echo_only(self):
        raw = canonical({'label': 'MOCK_NATIVE_PIPE_NOT_PDF_LIBRARY'})
        out, err, peak = self.exchange_child(
            'import sys; raw=sys.stdin.buffer.read(); sys.stdout.buffer.write(raw)', raw)
        self.assertEqual(out, raw)
        self.assertEqual(err, b'')
        self.assertGreaterEqual(peak, 0)

    def test_native_pipe_stderr_is_stop(self):
        with self.assertRaises(Refused):
            self.exchange_child('import sys; sys.stdin.buffer.read(); sys.stderr.write("AUTHORED_ERROR")', b'{}')

    def test_native_pipe_overflow_is_stop(self):
        with self.assertRaises(Refused):
            self.exchange_child('import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(b"x"*114689)', b'{}')

    def test_native_pipe_deadline_is_stop(self):
        # Isolate the pipe deadline from the independent /bin/ps probe deadline.
        with patch.object(q, '_sample_rss', return_value=0), self.assertRaises(Refused):
            self.exchange_child('import sys,time; sys.stdin.buffer.read(); time.sleep(2)', b'{}', wall=1)

    def test_rss_probe_timeout_stops_parent_reaps_child_and_consumes_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, expected = prepare(root)
            real_popen = subprocess.Popen
            children = []
            def authored_pipe_child(command, **kwargs):
                # Keep real pipes, wait/kill/close and production _exchange;
                # substitute only a fixed source-free Python child program.
                process = real_popen([sys.executable, '-I', '-B', '-S', '-c',
                    'import sys,time; sys.stdin.buffer.read(); time.sleep(2)'], **kwargs)
                children.append(process)
                return process
            probe_error = subprocess.TimeoutExpired(['/bin/ps'], 0.0004)
            with (patch.object(q.subprocess, 'Popen', side_effect=authored_pipe_child) as start,
                  patch.object(q.subprocess, 'run', side_effect=probe_error) as probe):
                with self.assertRaises(q.QualificationStopped):
                    q.run_phase(root, raw, expected)
            self.assertEqual(start.call_count, 1)
            self.assertEqual(probe.call_count, 1)
            self.assertEqual(probe.call_args.args[0],
                             ['/bin/ps', '-o', 'rss=', '-p', str(children[0].pid)])
            self.assertGreater(probe.call_args.kwargs['timeout'], 0)
            self.assertLessEqual(probe.call_args.kwargs['timeout'], 1)
            self.assertIsNotNone(children[0].returncode)
            self.assertLess(children[0].returncode, 0)
            self.assertTrue(all(s.closed for s in
                                (children[0].stdin, children[0].stdout, children[0].stderr)))
            scope = root / q.SCOPE
            outcome = decode((scope / 'OUTCOME.json').read_bytes())
            self.assertEqual(outcome['status'], 'QUALIFICATION_STOPPED_UNKNOWN_NO_RETRY')
            self.assertEqual(outcome['full_limits_consumed'], q.LIMITS)
            self.assertIsNone(outcome['reader_attempts_observed'])
            self.assertTrue(outcome['native_attempt_observed'])
            self.assertEqual(outcome['actual_source_reads'], 0)
            self.assertFalse((scope / 'worker.json').exists())
            self.assertFalse((root / 'data/raw').exists())
            with patch.object(q.subprocess, 'Popen') as retry:
                with self.assertRaises(FileExistsError):
                    q.run_phase(root, raw, expected)
            retry.assert_not_called()

    def test_native_authored_guard_denies_io_and_spawn_before_effect(self):
        source = str(Path(__file__).resolve().parents[1] / 'src')
        code = '''import sys,json,os,socket,subprocess,ctypes
sys.path.insert(0,SOURCE)
from civiclab.e01 import clerk2020_native_qualification_v1 as q
q._install_parse_guard()
blocked=0
calls=[lambda:open('/AUTHORED_NONEXISTENT_FILE'), lambda:os.listdir('.'),
       lambda:socket.socket(), lambda:subprocess.run([sys.executable,'-c','pass']),
       lambda:ctypes.CDLL('/AUTHORED_NONEXISTENT_LIBRARY')]
for call in calls:
    try: call()
    except q.QualificationStopped: blocked+=1
print(json.dumps({'label':'MOCK_GUARD_NOT_NATIVE_PDF','blocked':blocked}))
'''.replace('SOURCE', repr(source))
        out, err, _ = self.exchange_child(code, b'{}')
        self.assertEqual(json.loads(out), {'label': 'MOCK_GUARD_NOT_NATIVE_PDF', 'blocked': 5})
        self.assertEqual(err, b'')

    def test_packet_is_memory_only_and_exact(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, expected = prepare(root)
            with patch.object(q, '_no_alias', side_effect=AssertionError('NO_FS_DURING_PACKET')):
                packet = q.validate_packet(root, raw, expected)
            self.assertEqual(packet['limits']['source_reads'], 0)
            self.assertFalse((root / q.SCOPE).exists())

    def test_hash_root_schema_and_limits_tamper_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, expected = prepare(root)
            for key, value in [('root_sha256', 'f' * 64), ('schema_version', True),
                               ('phase_id', 'new-budget-root'), ('policy_sha256', 'f' * 64)]:
                packet = decode(raw)
                packet[key] = value
                changed = canonical(packet)
                with self.subTest(key=key), self.assertRaises(Refused):
                    q.validate_packet(root, changed, sha(changed))
            with self.assertRaises(Refused):
                q.validate_packet(root, raw, 'f' * 64)

    def test_no_bool_limit_coercion(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            packet = decode(raw)
            packet['limits']['native_import_attempts'] = True
            changed = canonical(packet)
            with self.assertRaises(Refused):
                q.validate_packet(root, changed, sha(changed))

    def test_extra_paths_and_missing_refs_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            for operation in ['extra', 'missing']:
                packet = decode(raw)
                if operation == 'extra':
                    packet['code_refs']['data/raw/forbidden.pdf'] = {'bytes': 1, 'sha256': 'a' * 64}
                else:
                    del packet['code_refs'][q.CODE_PATHS[0]]
                changed = canonical(packet)
                with self.assertRaises(Refused):
                    q.validate_packet(root, changed, sha(changed))

    def test_review_cannot_authorize_actual_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            packet = decode(raw)
            review = decode(base64.b64decode(packet['review_bytes_b64']))
            review['actual_source_authority'] = True
            r = canonical(review)
            packet['review_bytes_b64'] = base64.b64encode(r).decode()
            packet['review_sha256'] = sha(r)
            changed = canonical(packet)
            with self.assertRaises(Refused):
                q.validate_packet(root, changed, sha(changed))

    def test_review_shape_and_status_are_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            for key, value in [('status', 'BLOCKED'), ('auditor_role', 'implementer')]:
                packet = decode(raw)
                review = decode(base64.b64decode(packet['review_bytes_b64']))
                review[key] = value
                r = canonical(review)
                packet['review_bytes_b64'] = base64.b64encode(r).decode()
                packet['review_sha256'] = sha(r)
                changed = canonical(packet)
                with self.assertRaises(Refused):
                    q.validate_packet(root, changed, sha(changed))

    def test_durable_fixed_slot_refuses_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            store = q.DurableQualification(root)
            store.write('STARTED.json', b'{}')
            with self.assertRaises(FileExistsError):
                q.DurableQualification(root)
            with self.assertRaises(FileExistsError):
                store.write('STARTED.json', b'{}')
            self.assertEqual((store.path / 'STARTED.json').read_bytes(), b'{}')

    def test_crash_after_directory_consumes_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            q.DurableQualification(root)
            self.assertFalse((root / q.SCOPE / 'STARTED.json').exists())
            with self.assertRaises(FileExistsError):
                q.DurableQualification(root)

    def test_slot_mode_and_unknown_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            store = q.DurableQualification(Path(folder).resolve())
            store.write('STARTED.json', b'{}')
            self.assertEqual((store.path / 'STARTED.json').stat().st_mode & 0o777, 0o600)
            self.assertEqual(store.path.stat().st_mode & 0o777, 0o700)
            for name in ['../escape', 'unknown.json']:
                with self.assertRaises(Refused):
                    store.write(name, b'{}')

    def test_write_and_mutually_exclusive_output_caps(self):
        with tempfile.TemporaryDirectory() as folder:
            store = q.DurableQualification(Path(folder).resolve())
            with self.assertRaises(Refused):
                store.write('STARTED.json', b'x' * 2049)
            store.write('worker.json', b'{}')
            with self.assertRaises(Refused):
                store.write('partial_stdout.local.bin', b'{}')

    def test_post_persist_fsync_failure_keeps_consumed_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            store = q.DurableQualification(root)
            with patch.object(q, '_fsync_dir', side_effect=OSError('AUTHORED_EIO')):
                with self.assertRaises(OSError):
                    store.write('STARTED.json', b'{}')
            self.assertEqual((store.path / 'STARTED.json').read_bytes(), b'{}')
            with self.assertRaises(FileExistsError):
                q.DurableQualification(root)

    def test_symlink_scope_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            (root / 'target').mkdir()
            (root / 'data').symlink_to(root / 'target', target_is_directory=True)
            with self.assertRaises(Refused):
                q.DurableQualification(root)

    def test_stable_hash_and_probe_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder).resolve() / 'AUTHORED'
            p.write_bytes(b'abc')
            self.assertEqual(q._stable_hash(p, 4), (sha(b'abc'), 3, 4))
            with self.assertRaises(Refused):
                q._stable_hash(p, 3)
            alias = p.with_name('alias')
            alias.symlink_to(p)
            with self.assertRaises(Refused):
                q._stable_hash(alias, 4)

    def test_parent_one_worker_and_no_source_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, expected = prepare(root)
            process = FakeProcess()
            with (patch.object(q.subprocess, 'Popen', return_value=process) as start,
                  patch.object(q, '_exchange', side_effect=fake_exchange)):
                result = q.run_phase(root, raw, expected)
            self.assertEqual(start.call_count, 1)
            self.assertEqual(start.call_args.args[0][1:3], ['-I', '-B'])
            self.assertEqual(set(start.call_args.kwargs['env']), {'PATH', 'LC_ALL'})
            self.assertEqual(result['status'], 'GENERATED_QUALIFICATION_RECORDED_NOT_ADMITTED')
            self.assertFalse(result['runtime_and_backend_admission'])
            self.assertIsNone(result['sampled_child_peak_rss_bytes'])
            self.assertEqual(result['actual_source_reads'], 0)
            self.assertTrue(process.waited)
            self.assertEqual(result['reserved_code_bytes'] - result['observed_code_bytes'], len(q.CODE_PATHS))
            self.assertFalse((root / 'data/raw').exists())

    def test_start_reservation_before_code_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, expected = prepare(root)
            original = q._stable_hash
            def checked(path, allowance):
                self.assertTrue((root / q.SCOPE / 'STARTED.json').exists())
                self.assertIn(str(path.relative_to(root)), q.CODE_PATHS)
                return original(path, allowance)
            with (patch.object(q, '_stable_hash', side_effect=checked),
                  patch.object(q.subprocess, 'Popen', return_value=FakeProcess()),
                  patch.object(q, '_exchange', side_effect=fake_exchange)):
                q.run_phase(root, raw, expected)

    def test_code_drift_stops_before_child_and_cannot_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, expected = prepare(root)
            (root / q.CODE_PATHS[0]).write_bytes(b'CHANGED')
            with patch.object(q.subprocess, 'Popen') as start:
                with self.assertRaises(q.QualificationStopped):
                    q.run_phase(root, raw, expected)
                self.assertFalse(start.called)
            with self.assertRaises(FileExistsError):
                q.run_phase(root, raw, expected)
            outcome = json.loads((root / q.SCOPE / 'OUTCOME.json').read_bytes())
            self.assertIsNone(outcome['reader_attempts_observed'])
            self.assertEqual(outcome['full_limits_consumed'], q.LIMITS)

    def test_child_unknown_retains_partial_and_no_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, expected = prepare(root)
            def fail(process, packet, start, out, err):
                out.extend(b'AUTHORED_PARTIAL')
                err.extend(b'AUTHORED_ERROR')
                raise TimeoutError()
            with (patch.object(q.subprocess, 'Popen', return_value=FakeProcess()),
                  patch.object(q, '_exchange', side_effect=fail)):
                with self.assertRaises(q.QualificationStopped):
                    q.run_phase(root, raw, expected)
            scope = root / q.SCOPE
            self.assertEqual((scope / 'partial_stdout.local.bin').read_bytes(), b'AUTHORED_PARTIAL')
            self.assertEqual((scope / 'stderr.local.bin').read_bytes(), b'AUTHORED_ERROR')
            self.assertFalse((scope / 'worker.json').exists())
            with self.assertRaises(FileExistsError):
                q.run_phase(root, raw, expected)

    def test_invalid_child_payload_does_not_qualify(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, expected = prepare(root)
            def wrong(process, packet, start, out, err):
                out.extend(canonical({'status': 'NATIVE_GENERATED_FIXTURES_COMPLETE', 'actual_source_reads': 1}))
                return 1
            with (patch.object(q.subprocess, 'Popen', return_value=FakeProcess()),
                  patch.object(q, '_exchange', side_effect=wrong)):
                with self.assertRaises(q.QualificationStopped):
                    q.run_phase(root, raw, expected)
            self.assertFalse((root / q.SCOPE / 'worker.json').exists())

    def test_no_implicit_pypdf_import(self):
        import sys
        self.assertNotIn('pypdf', sys.modules)


if __name__ == '__main__':
    unittest.main()
