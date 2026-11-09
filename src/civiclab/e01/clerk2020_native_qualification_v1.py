"""One-shot generated-PDF qualification; NEVER reads acquired Clerk sources.

The external, hash-bound release and separate code review are required before
execution. No default authority, grant creation, retry or source factory toggle.
The fixed durable directory is consumed before explicit code/runtime reads.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

# Isolated -I worker startup has no workspace PYTHONPATH. The parent pins this
# exact file before spawning; this is the small reviewed bootstrap boundary.
if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == '--qualification-worker':
    sys.path[:0] = [str(Path(sys.argv[2]).absolute() / 'src')]

from civiclab.e01.clerk2020_m2_v1_1_contracts import (
    canonical, decode, digest, exact, hex64, require, sha,
)

KIND = 'CLERK_NATIVE_GENERATED_QUALIFICATION_RELEASE_V1'
SCOPE = 'data/processed/e01_clerk2020_native_qualification_v1/qualification-v1'
POLICY_SHA = '7e87d6844ca5bec346af91359d38a9c7a612503962d13b4749fd93d3811fb0e6'
CODE_PATHS = (
    'src/civiclab/__init__.py',
    'src/civiclab/e01/__init__.py',
    'src/civiclab/e01/pipeline.py',
    'src/civiclab/common.py',
    'src/civiclab/e01/clerk2020_native_qualification_v1.py',
    'src/civiclab/e01/clerk2020_native_inventory_v1.py',
    'src/civiclab/e01/clerk2020_m2_v1_1_contracts.py',
    'src/civiclab/e01/clerk2020_m2_v1_1_backend.py',
    'tests/test_clerk2020_native_inventory_v1.py',
)
MANIFEST_SCOPE = 'Observed loaded origin/cache files plus interpreter; not complete native dependency admission'
GUARD_SCOPE = 'Cooperative Python event guard after imports; not an OS sandbox or decoder allocation bound'
WORKER_STAGE = 'STARTUP'
WORKER_PARTIAL = {}
LIMITS = {
    'source_reads': 0, 'network_requests': 0, 'model_calls': 0,
    'native_import_attempts': 1, 'reader_attempts': 4, 'page_extractions': 119,
    'wall_ms': 45000, 'child_wall_seconds': 30, 'child_cpu_soft_seconds': 10,
    'child_cpu_hard_seconds': 11, 'rss_peak_bytes': 268435456,
    'runtime_files': 1024, 'runtime_hash_bytes': 536870912,
    'runtime_manifest_bytes': 98304, 'code_read_bytes': 1048576,
    'stdout_bytes': 114688, 'stderr_bytes': 4096, 'owned_write_bytes': 131072,
    'packet_bytes': 32768,
}


class QualificationStopped(RuntimeError):
    def __init__(self):
        super().__init__('CLERK_QUALIFICATION_STOPPED_PRESERVE_NO_RETRY')


def _no_alias(path):
    require(path.is_absolute() and '..' not in path.parts)
    require(not any(p.is_symlink() for p in (path, *path.parents)))


def _identity(st):
    return st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def _stable_hash(path, allowance):
    """One explicit read pass plus EOF probe; reservation includes the probe."""
    _no_alias(path)
    before = path.stat()
    require(before.st_size + 1 <= allowance and path.is_file())
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    h, count = hashlib.sha256(), 0
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        require(_identity(opened) == _identity(before))
        while count <= before.st_size:
            chunk = stream.read(min(65536, before.st_size + 1 - count))
            if not chunk:
                break
            count += len(chunk)
            h.update(chunk)
        require(count == before.st_size and _identity(os.fstat(stream.fileno())) == _identity(opened))
    require(_identity(path.stat()) == _identity(before))
    return h.hexdigest(), count, count + 1


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class DurableQualification:
    """Specialized immutable qualification slots; no actual source permission."""
    ALLOWED = {'STARTED.json': 2048, 'worker.json': 114688,
               'partial_stdout.local.bin': 114688, 'stderr.local.bin': 4096,
               'OUTCOME.json': 4096}

    def __init__(self, root):
        root = Path(root).absolute()
        _no_alias(root)
        self.path = root / SCOPE
        _no_alias(self.path)
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        # A crash after mkdir consumes the fixed slot even without STARTED.
        self.path.mkdir(mode=0o700, exist_ok=False)
        _fsync_dir(self.path.parent)
        self.spent = 0

    def write(self, name, raw):
        require(name in self.ALLOWED and type(raw) is bytes and len(raw) <= self.ALLOWED[name])
        require(self.spent + len(raw) <= LIMITS['owned_write_bytes'])
        if name == 'worker.json':
            require(not (self.path / 'partial_stdout.local.bin').exists())
        if name == 'partial_stdout.local.bin':
            require(not (self.path / 'worker.json').exists())
        # Conservatively consume this permission before the write. A failed
        # create/write/fsync is never retried, refunded or put at another path.
        self.spent += len(raw)
        fd = os.open(self.path / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            require(stream.write(raw) == len(raw))
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_dir(self.path)


def validate_packet(root, raw, expected_hash):
    require(type(raw) is bytes and len(raw) <= LIMITS['packet_bytes']
            and hex64(expected_hash) and sha(raw) == expected_hash)
    plan = decode(raw, LIMITS['packet_bytes'])
    exact(plan, {'schema_version', 'kind', 'root_sha256', 'phase_id', 'policy_sha256',
                 'code_refs', 'review_bytes_b64', 'review_sha256', 'limits'})
    require(type(plan['schema_version']) is int and plan['schema_version'] == 1
            and plan['kind'] == KIND and plan['phase_id'] == 'qualification-v1'
            and plan['root_sha256'] == sha(str(Path(root).absolute()).encode())
            and plan['policy_sha256'] == POLICY_SHA and canonical(plan['limits']) == canonical(LIMITS))
    exact(plan['code_refs'], CODE_PATHS)
    for ref in plan['code_refs'].values():
        exact(ref, {'bytes', 'sha256'})
        require(type(ref['bytes']) is int and 0 < ref['bytes'] <= 262144 and hex64(ref['sha256']))
    require(sum(x['bytes'] + 1 for x in plan['code_refs'].values()) <= LIMITS['code_read_bytes'])
    try:
        review_raw = base64.b64decode(plan['review_bytes_b64'], validate=True)
    except (ValueError, TypeError):
        raise QualificationStopped() from None
    require(sha(review_raw) == plan['review_sha256'])
    review = decode(review_raw, 16384)
    exact(review, {'kind', 'status', 'auditor_role', 'code_refs', 'limits', 'actual_source_authority'})
    require(review['kind'] == 'CLERK_NATIVE_QUALIFICATION_CODE_REVIEW_V1'
            and review['status'] == 'PASS_EXACT_GENERATED_FIXTURE_PHASE_ONLY'
            and review['auditor_role'] == 'independent_auditor'
            and review['code_refs'] == plan['code_refs'] and canonical(review['limits']) == canonical(LIMITS)
            and review['actual_source_authority'] is False)
    return plan


def _sample_rss(pid, timeout):
    probe = subprocess.run(['/bin/ps', '-o', 'rss=', '-p', str(pid)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, env={'PATH': os.defpath, 'LC_ALL': 'C'})
    require(probe.returncode == 0 and not probe.stderr and len(probe.stdout) <= 128)
    raw = probe.stdout.strip()
    require(raw.isdigit() and 0 < int(raw) * 1024 <= LIMITS['rss_peak_bytes'])
    return int(raw) * 1024


def _exchange(process, packet, start, out, err):
    offset, peak, prior = 0, 0, start
    def remaining():
        nonlocal prior
        now = time.monotonic()
        require(now >= prior)
        prior = now
        remaining_ms = min(LIMITS['child_wall_seconds'] * 1000,
                           LIMITS['wall_ms']) - (now - start) * 1000
        require(remaining_ms > 0)
        return remaining_ms / 1000
    with selectors.DefaultSelector() as select:
        for stream, event in [(process.stdin, selectors.EVENT_WRITE),
                              (process.stdout, selectors.EVENT_READ), (process.stderr, selectors.EVENT_READ)]:
            os.set_blocking(stream.fileno(), False)
            select.register(stream, event)
        while select.get_map():
            left = remaining()
            if process.poll() is None:
                try:
                    peak = max(peak, _sample_rss(process.pid, min(1, left)))
                except Exception:
                    if process.poll() is None:
                        raise
            for key, _ in select.select(min(0.05, remaining())):
                stream = key.fileobj
                if stream is process.stdin:
                    try:
                        n = os.write(stream.fileno(), packet[offset:offset + 65536])
                    except BlockingIOError:
                        continue
                    require(n > 0)
                    offset += n
                    if offset == len(packet):
                        select.unregister(stream)
                        stream.close()
                else:
                    target, cap = ((out, LIMITS['stdout_bytes']) if stream is process.stdout
                                   else (err, LIMITS['stderr_bytes']))
                    try:
                        chunk = os.read(stream.fileno(), min(65536, cap - len(target) + 1))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        select.unregister(stream)
                        stream.close()
                        continue
                    target.extend(chunk)
                    require(len(target) <= cap)
        process.wait(timeout=remaining())
    require(process.returncode == 0 and offset == len(packet) and not err)
    return peak


def validate_worker(raw):
    worker = decode(raw, LIMITS['stdout_bytes'])
    expected = {'label': 'MOCK_GENERATED_PDF_ONLY', 'status': 'NATIVE_GENERATED_FIXTURES_COMPLETE',
                'reader_attempts': 4, 'expected_page_extractions': 119,
                'positive_page_counts': [81, 38], 'negative_cases_refused': 2,
                'actual_source_reads': 0, 'model_calls': 0,
                'python': '3.12.14', 'pypdf': '6.10.0',
                'interpreter_implementation': 'cpython', 'platform': 'darwin', 'machine': 'arm64',
                'runtime_manifest_scope': MANIFEST_SCOPE, 'guard': GUARD_SCOPE}
    extra = {'runtime_manifest', 'runtime_manifest_sha256', 'runtime_hash_bytes_observed',
             'runtime_hash_bytes_reserved'}
    exact(worker, set(expected) | extra)
    require(canonical({k: worker[k] for k in expected}) == canonical(expected))
    rows = worker['runtime_manifest']
    require(type(rows) is list and 1 <= len(rows) <= LIMITS['runtime_files']
            and len(canonical(rows)) <= LIMITS['runtime_manifest_bytes'])
    paths, total = set(), 0
    for row in rows:
        require(type(row) is list and len(row) == 3)
        path, size, h = row
        require(type(path) is str and len(path.encode()) <= 512
                and path.startswith(('REPO/', 'PYTHON_BASE/'))
                and all(p not in {'', '.', '..'} for p in path.split('/'))
                and not any(ord(c) < 32 or c == '\\' for c in path)
                and path not in paths and type(size) is int and 0 <= size <= LIMITS['runtime_hash_bytes']
                and hex64(h))
        require(not path.startswith(('REPO/data/', 'REPO/.env')))
        paths.add(path)
        total += size
    require(hex64(worker['runtime_manifest_sha256']) and digest(rows) == worker['runtime_manifest_sha256'])
    require(type(worker['runtime_hash_bytes_observed']) is int
            and worker['runtime_hash_bytes_observed'] == total
            and type(worker['runtime_hash_bytes_reserved']) is int
            and worker['runtime_hash_bytes_reserved'] == total + len(rows)
            and total + len(rows) <= LIMITS['runtime_hash_bytes'])
    return worker


def run_phase(root, raw, expected_hash):
    """Actual fixture execution ONLY after root supplies exact reviewed packet."""
    root = Path(root).absolute()
    plan = validate_packet(root, raw, expected_hash)  # Memory only, before reservation.
    ledger = DurableQualification(root)
    ledger.write('STARTED.json', canonical({'kind': KIND, 'plan_sha256': expected_hash,
                 'limits': LIMITS, 'consumed': True, 'no_retry': True,
                 'actual_source_authority': False}))
    start = time.monotonic()
    observed_code = reserved_code = 0
    process, out, err = None, bytearray(), bytearray()
    failed = False
    result = None
    try:
        for name, ref in plan['code_refs'].items():
            actual, count, reserved = _stable_hash(root / name, LIMITS['code_read_bytes'] - reserved_code)
            observed_code += count
            reserved_code += reserved
            require(count == ref['bytes'] and actual == ref['sha256'])
        require((time.monotonic() - start) * 1000 < LIMITS['wall_ms'])
        entry = 'src/civiclab/e01/clerk2020_native_qualification_v1.py'
        command = [sys.executable, '-I', '-B', '-S', str(root / entry), '--qualification-worker', str(root)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=root, start_new_session=True,
                                   env={'PATH': os.defpath, 'LC_ALL': 'C'})
        peak = _exchange(process, canonical({'policy_sha256': POLICY_SHA}), start, out, err)
        require((time.monotonic() - start) * 1000 < LIMITS['wall_ms'])
        validate_worker(bytes(out))
        ledger.write('worker.json', bytes(out))
        result = {'status': 'GENERATED_QUALIFICATION_RECORDED_NOT_ADMITTED',
                  'plan_sha256': expected_hash, 'worker_sha256': sha(bytes(out)),
                  'observed_code_bytes': observed_code,
                  'reserved_code_bytes': reserved_code,
                  'sampled_child_peak_rss_bytes': peak if peak else None, 'actual_source_reads': 0,
                  'runtime_and_backend_admission': False, 'model_calls': 0, 'cost_usd': 0}
    except BaseException:
        failed = True
        result = {'status': 'QUALIFICATION_STOPPED_UNKNOWN_NO_RETRY',
                  'plan_sha256': expected_hash, 'actual_source_reads': 0,
                  'observed_code_bytes': observed_code, 'native_attempt_observed': process is not None,
                  'reserved_code_bytes': reserved_code,
                  'reader_attempts_observed': None, 'full_limits_consumed': LIMITS,
                  'model_calls': 0, 'cost_usd': 0}
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait(timeout=1)
            except BaseException:
                failed = True
                result = {'status': 'QUALIFICATION_REAP_UNKNOWN_NO_RETRY', 'actual_source_reads': 0,
                          'full_limits_consumed': LIMITS, 'model_calls': 0, 'cost_usd': 0}
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
    if failed:
        if out and not (ledger.path / 'worker.json').exists():
            ledger.write('partial_stdout.local.bin', bytes(out[:LIMITS['stdout_bytes']]))
        if err:
            ledger.write('stderr.local.bin', bytes(err[:LIMITS['stderr_bytes']]))
    ledger.write('OUTCOME.json', canonical(result))
    if failed:
        raise QualificationStopped()
    return result


def _runtime_inventory(root):
    roots = [root, Path(sys.base_prefix).resolve()]
    def allowed(path):
        # No repository data/raw, processed controls or arbitrary personal files
        # can become a runtime hash target through a module-origin attribute.
        if path.is_relative_to(root / 'data/raw') or path.name == '.env':
            return False
        if path.is_relative_to(roots[1]):
            return True
        if not path.is_relative_to(root):
            return False
        rel = str(path.relative_to(root))
        if rel in CODE_PATHS:
            return True
        if rel.startswith('.venv/lib/python3.12/site-packages/pypdf/'):
            return True
        if '/__pycache__/' in rel and rel.endswith('.pyc'):
            import importlib.util
            try:
                return str(Path(importlib.util.source_from_cache(str(path))).relative_to(root)) in CODE_PATHS
            except (ValueError, NotImplementedError):
                return False
        return False
    candidates = {Path(sys.executable).resolve()}
    for module in tuple(sys.modules.values()):
        for attr in ['__file__', '__cached__']:
            name = getattr(module, attr, None)
            if type(name) is str:
                path = Path(os.path.abspath(name))
                require(allowed(path))
                if path.is_file():
                    _no_alias(path)
                    candidates.add(path)
    require(len(candidates) <= LIMITS['runtime_files'])
    rows, reserved_total, actual_total = [], 0, 0
    for path in sorted(candidates):
        choices = [(i, path.relative_to(base)) for i, base in enumerate(roots) if path.is_relative_to(base)]
        require(bool(choices))
        # A reviewed toolchain may live under repository data/processed; prefer
        # its explicit runtime role rather than labeling it research data.
        index, relative = choices[-1]
        h, size, reserved = _stable_hash(path, LIMITS['runtime_hash_bytes'] - reserved_total)
        reserved_total += reserved
        actual_total += size
        rows.append([('REPO/' if index == 0 else 'PYTHON_BASE/') + str(relative), size, h])
    require(len(canonical(rows)) <= LIMITS['runtime_manifest_bytes'])
    return rows, actual_total, reserved_total


def _install_parse_guard():
    def guard(event, args):
        if (event in {'open', 'os.listdir', 'os.scandir', 'os.chdir', 'import', 'ctypes.dlopen',
                      'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn'}
                or event.startswith(('socket.', 'os.exec'))):
            raise QualificationStopped()
    sys.addaudithook(guard)


def _worker(root):
    """No acquired-source paths; only one pinned native import and generated PDFs."""
    global WORKER_STAGE, WORKER_PARTIAL
    WORKER_STAGE = 'RESOURCE_LIMITS'
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (LIMITS['child_cpu_soft_seconds'], LIMITS['child_cpu_hard_seconds']))
    WORKER_STAGE = 'PACKET'
    packet = decode(sys.stdin.buffer.read(1025), 1024)
    require(packet == {'policy_sha256': POLICY_SHA})
    # -S suppresses site/.pth startup; expose only the pinned source tree and the
    # existing environment package directory. Unknown transitive origins refuse.
    sys.path[:0] = [str(root / 'src'), str(root / 'tests'),
                   str(root / '.venv/lib/python3.12/site-packages')]
    WORKER_STAGE = 'NATIVE_IMPORT'
    import pypdf
    from test_clerk2020_native_inventory_v1 import exercise_native_generated_pdf
    WORKER_STAGE = 'IDENTITY'
    require(sys.implementation.name == 'cpython' and sys.version.split()[0] == '3.12.14'
            and sys.platform == 'darwin' and os.uname().machine == 'arm64'
            and pypdf.__version__ == '6.10.0')
    WORKER_STAGE = 'RUNTIME_MANIFEST'
    manifest, observed, reserved = _runtime_inventory(root)
    WORKER_PARTIAL = {'runtime_manifest': manifest, 'runtime_manifest_sha256': digest(manifest),
                      'runtime_hash_bytes_observed': observed, 'runtime_hash_bytes_reserved': reserved}
    WORKER_STAGE = 'GUARDED_FIXTURES'
    _install_parse_guard()
    result = exercise_native_generated_pdf(pypdf.PdfReader)
    result.update({'status': 'NATIVE_GENERATED_FIXTURES_COMPLETE',
                   'python': sys.version.split()[0], 'pypdf': pypdf.__version__,
                   'interpreter_implementation': 'cpython', 'platform': sys.platform, 'machine': os.uname().machine,
                   'runtime_manifest': manifest, 'runtime_manifest_sha256': digest(manifest),
                   'runtime_hash_bytes_observed': observed, 'runtime_hash_bytes_reserved': reserved,
                   'runtime_manifest_scope': MANIFEST_SCOPE, 'guard': GUARD_SCOPE})
    WORKER_STAGE = 'SERIALIZE'
    raw = canonical(result)
    require(len(raw) <= LIMITS['stdout_bytes'])
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def _worker_failure(exc):
    allowed = {'Refused', 'InventoryRefused', 'QualificationStopped', 'ModuleNotFoundError',
               'ImportError', 'MemoryError', 'TimeoutError', 'OSError', 'ValueError',
               'TypeError', 'RuntimeError', 'KeyboardInterrupt', 'SystemExit'}
    obj = {**WORKER_PARTIAL, 'status': 'NATIVE_FIXTURE_UNKNOWN_STOP', 'actual_source_reads': 0,
           'stage': WORKER_STAGE,
           'error_type': type(exc).__name__ if type(exc).__name__ in allowed else 'UNCLASSIFIED'}
    raw = canonical(obj)
    if len(raw) > LIMITS['stdout_bytes']:
        raw = canonical({'status': 'NATIVE_FIXTURE_UNKNOWN_STOP', 'actual_source_reads': 0,
                         'stage': 'SERIALIZE', 'error_type': 'UNCLASSIFIED'})
    return raw


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--qualification-worker':
        try:
            _worker(Path(sys.argv[2]).absolute())
        except BaseException as exc:
            sys.stdout.buffer.write(_worker_failure(exc))
            raise SystemExit(2) from None
    else:
        raise SystemExit('Explicit reviewed root caller required; no source execution entry.')
