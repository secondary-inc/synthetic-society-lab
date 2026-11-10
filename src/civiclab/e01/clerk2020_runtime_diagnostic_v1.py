"""One separately released runtime-manifest diagnostic, never a qualification retry.

Frozen qualification-v1 and its consumed limits remain intact. This phase imports
the same proposed reader, performs at most one frozen collector pass, and calls
no PDF reader/extractor. The only origin overlay is two reviewed project files
needed for the diagnostic itself; no external origin rule or module is removed.
"""
import base64
import os
from pathlib import Path
import re
import subprocess
import sys
import time

if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == '--runtime-diagnostic-worker':
    sys.path.insert(0, str(Path(sys.argv[2]).absolute() / 'src'))

from civiclab.e01 import clerk2020_native_qualification_v1 as frozen
from civiclab.e01.clerk2020_m2_v1_1_contracts import Refused, canonical, decode, digest, exact, hex64, require, sha
from civiclab.e01.clerk2020_qualification_failure_context_v1_1 import failure_context

ENTRY = 'src/civiclab/e01/clerk2020_runtime_diagnostic_v1.py'
OVERLAY = (ENTRY, 'src/civiclab/e01/clerk2020_qualification_failure_context_v1_1.py')
CODE_PATHS = frozen.CODE_PATHS + OVERLAY
CRITICAL_REFS = {
    'src/civiclab/e01/clerk2020_native_qualification_v1.py': '29ff273b6d7a97d83a01573bfee39f060927b1f41501e2f86b4ada1c3323382f',
    'src/civiclab/e01/clerk2020_qualification_failure_context_v1_1.py': '730440fa2090865e94b81fcd42320094f4981023b2adb0b22ed37a4eb7ea4ab9',
}
SCOPE = 'data/processed/e01_clerk2020_native_qualification_v1/runtime-diagnostic-v1'
KIND = 'CLERK2020_RUNTIME_DIAGNOSTIC_RELEASE_V1'
OLD_PLAN = '7f8cfb3889bf3306733ac8f9a9bed59fc8f1cd24c91c090adeab70f28911d54e'
ANCESTOR = {
    'scope': frozen.SCOPE, 'plan_sha256': OLD_PLAN,
    'records': {
        'STARTED.json': {'bytes': 660, 'sha256': '9f3b9aa63691818a550b582783b2fd5049f9db6ae79e406b3485bae8539fd378'},
        'OUTCOME.json': {'bytes': 775, 'sha256': '691206c41eac017175b3adab3392435815cbfd07efc4fa376bb6797a65ff52ca'},
        'partial_stdout.local.bin': {'bytes': 114, 'sha256': 'd155497b8919144990a65cc3e9d9001a93be8d89298caa8ef287ebd08a21bf2d'},
    },
    'full_consumed_limits': frozen.LIMITS,
    'credit_restored': 0,
}
LIMITS = {**frozen.LIMITS, 'reader_attempts': 0, 'page_extractions': 0,
          'collector_passes': 1, 'ancestor_record_reads': 6, 'ancestor_read_bytes_reserved': 3104}
SITES = {
    ('_no_alias', 63): 'ABSOLUTE_LEXICAL_PATH', ('_no_alias', 64): 'SYMLINK_PATH',
    ('_stable_hash', 75): 'FILE_SIZE_TYPE_OR_READ_ALLOWANCE',
    ('_stable_hash', 80): 'OPEN_DESCRIPTOR_IDENTITY',
    ('_stable_hash', 87): 'READ_SIZE_OR_FINAL_DESCRIPTOR_IDENTITY',
    ('_stable_hash', 88): 'FINAL_PATH_IDENTITY',
    ('_runtime_inventory', 366): 'ORIGIN_ALLOWLIST',
    ('_runtime_inventory', 370): 'RUNTIME_FILE_COUNT',
    ('_runtime_inventory', 374): 'RUNTIME_ROOT_ROLE',
    ('_runtime_inventory', 382): 'MANIFEST_SERIALIZATION_SIZE',
}
STATUS = {'REJECTION_RECORDED', 'REJECTION_NOT_REPRODUCED', 'PRECONDITION_STOP'}
ERROR_NAMES = ((Refused, 'Refused'), (OSError, 'OSError'), (FileNotFoundError, 'FileNotFoundError'),
               (PermissionError, 'PermissionError'), (MemoryError, 'MemoryError'),
               (RuntimeError, 'RuntimeError'), (ValueError, 'ValueError'), (TypeError, 'TypeError'))
TRUSTED_CODES = tuple((func.__code__, name) for name, func in [
    ('_runtime_inventory', frozen._runtime_inventory), ('_stable_hash', frozen._stable_hash),
    ('_no_alias', frozen._no_alias)])


class DurableDiagnostic(frozen.DurableQualification):
    def __init__(self, root):
        root = Path(root).absolute()
        frozen._no_alias(root)
        self.path = root / SCOPE
        frozen._no_alias(self.path)
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.path.mkdir(mode=0o700, exist_ok=False)
        frozen._fsync_dir(self.path.parent)
        self.spent = 0


def validate_packet(root, raw, expected):
    require(type(raw) is bytes and len(raw) <= LIMITS['packet_bytes'] and hex64(expected) and sha(raw) == expected)
    packet = decode(raw, LIMITS['packet_bytes'])
    exact(packet, {'schema_version', 'kind', 'phase_id', 'root_sha256', 'ancestor',
                   'limits', 'code_refs', 'project_overlay', 'review_bytes_b64', 'review_sha256'})
    require(type(packet['schema_version']) is int and packet['schema_version'] == 1
            and packet['kind'] == KIND and packet['phase_id'] == 'runtime-diagnostic-v1'
            and packet['root_sha256'] == sha(str(Path(root).absolute()).encode())
            and canonical(packet['ancestor']) == canonical(ANCESTOR)
            and canonical(packet['limits']) == canonical(LIMITS)
            and packet['project_overlay'] == list(OVERLAY))
    exact(packet['code_refs'], CODE_PATHS)
    for ref in packet['code_refs'].values():
        exact(ref, {'bytes', 'sha256'})
        require(type(ref['bytes']) is int and 0 < ref['bytes'] <= 262144 and hex64(ref['sha256']))
    require(all(packet['code_refs'][name]['sha256'] == h for name, h in CRITICAL_REFS.items()))
    require(sum(r['bytes'] + 1 for r in packet['code_refs'].values()) <= LIMITS['code_read_bytes'])
    try:
        review_raw = base64.b64decode(packet['review_bytes_b64'], validate=True)
    except (TypeError, ValueError):
        raise frozen.QualificationStopped() from None
    require(sha(review_raw) == packet['review_sha256'])
    review = decode(review_raw, 16384)
    exact(review, {'kind', 'status', 'reviewer_role', 'code_refs', 'limits', 'ancestor',
                   'project_overlay', 'source_authority', 'qualification_authority'})
    require(review['kind'] == 'CLERK2020_RUNTIME_DIAGNOSTIC_CODE_BINDING_V1'
            and review['status'] == 'PASS_EXACT_RUNTIME_DIAGNOSTIC_ONLY'
            and review['reviewer_role'] == 'independent_auditor'
            and review['code_refs'] == packet['code_refs']
            and canonical(review['limits']) == canonical(LIMITS)
            and canonical(review['ancestor']) == canonical(ANCESTOR)
            and review['project_overlay'] == list(OVERLAY)
            and review['source_authority'] is False and review['qualification_authority'] is False)
    return packet


def _site(exc, root):
    context = failure_context(exc, str(root))
    tb = BaseException.__getattribute__(exc, '__traceback__')
    sites, steps = [], 0
    while tb is not None and steps < 32:
        name = next((name for code, name in TRUSTED_CODES if tb.tb_frame.f_code is code), None)
        key = (name, tb.tb_lineno)
        if name is not None and key in SITES:
            sites.append({'function': name, 'line': tb.tb_lineno, 'predicate': SITES[key]})
        tb = tb.tb_next
        steps += 1
    return (sites[-1] if sites else None), context


def collect_diagnostic(root):
    """One collector call with explicit reviewed project-only instrumentation."""
    previous = frozen.CODE_PATHS
    require(previous == CODE_PATHS[:-2])
    frozen.CODE_PATHS = CODE_PATHS
    try:
        try:
            rows, actual, reserved = frozen._runtime_inventory(root)
        except BaseException as exc:
            try:
                site, context = _site(exc, root)
            except ValueError:
                site, context = None, None
            return {'status': 'REJECTION_RECORDED',
                    'error_type': next((label for cls, label in ERROR_NAMES if type(exc) is cls), 'UNCLASSIFIED'),
                    'site': site, 'context': context, 'manifest': None,
                    'runtime_bytes_observed': None, 'runtime_bytes_reserved': None}
        return {'status': 'REJECTION_NOT_REPRODUCED', 'error_type': None, 'site': None,
                'context': None, 'manifest': rows, 'runtime_bytes_observed': actual,
                'runtime_bytes_reserved': reserved}
    finally:
        frozen.CODE_PATHS = previous


def _validate_child(raw):
    child = decode(raw, LIMITS['stdout_bytes'])
    fixed = {'kind': 'CLERK2020_RUNTIME_DIAGNOSTIC_RESULT_V1', 'ancestor_plan_sha256': OLD_PLAN,
             'source_reads': 0, 'reader_attempts': 0, 'page_extractions': 0,
             'model_calls': 0, 'network_requests': 0, 'project_overlay': list(OVERLAY),
             'external_origin_rules_changed': False, 'excluded_modules': 0,
             'qualification_or_source_admission': False}
    variable = {'status', 'stage', 'collector_passes_attempted', 'error_type', 'site', 'context', 'manifest',
                'runtime_bytes_observed', 'runtime_bytes_reserved'}
    exact(child, set(fixed) | variable)
    require(canonical({k: child[k] for k in fixed}) == canonical(fixed)
            and child['status'] in STATUS and child['stage'] in {'RESOURCE', 'PRELOAD', 'IDENTITY', 'COLLECTOR'})
    require(type(child['collector_passes_attempted']) is int
            and child['collector_passes_attempted'] == (1 if child['stage'] == 'COLLECTOR' else 0))
    require(child['error_type'] is None or child['error_type'] in {'Refused', 'OSError', 'FileNotFoundError',
            'PermissionError', 'MemoryError', 'RuntimeError', 'ValueError', 'TypeError', 'UNCLASSIFIED'})
    if child['site'] is not None:
        site = child['site']
        exact(site, {'function', 'line', 'predicate'})
        require(type(site['line']) is int and SITES.get((site['function'], site['line'])) == site['predicate'])
    context = child['context']
    if context is not None:
        exact(context, {'kind', 'frozen_source', 'qualified_frames', 'traceback_truncated',
                        'extra_runtime_or_source_io', 'exception_message_retained', 'permits_retry_or_policy_change'})
        require(context['kind'] == 'PROPOSED_FUTURE_FAILURE_CONTEXT_V1_1_NOT_ORIGINAL_RUN_DIAGNOSIS'
                and context['frozen_source'] == 'src/civiclab/e01/clerk2020_native_qualification_v1.py'
                and type(context['traceback_truncated']) is bool
                and type(context['extra_runtime_or_source_io']) is int and context['extra_runtime_or_source_io'] == 0
                and context['exception_message_retained'] is False and context['permits_retry_or_policy_change'] is False
                and type(context['qualified_frames']) is list and len(context['qualified_frames']) <= 32)
        for frame in context['qualified_frames']:
            fields = {'function', 'line', 'last_iteration_module_not_proven_cause',
                      'last_iteration_origin_category_not_proven_cause'}
            require(type(frame) is dict and {'function', 'line'} <= set(frame) <= fields
                    and frame['function'] in {'_worker', '_runtime_inventory', '_stable_hash', '_no_alias', 'allowed'}
                    and type(frame['line']) is int and 1 <= frame['line'] <= 1000)
            name = frame.get('last_iteration_module_not_proven_cause')
            require(name is None or type(name) is str and re.fullmatch('[A-Za-z0-9_.]{1,128}', name))
            require(frame.get('last_iteration_origin_category_not_proven_cause') in {
                None, 'UNKNOWN', 'RESEARCH_DATA_PATH_REFUSED', 'VENV_PYPDF', 'VENV_OTHER_PACKAGE',
                'PROJECT_CODE', 'OTHER_OR_UNKNOWN'})
    if child['site'] is not None:
        require(child['stage'] == 'COLLECTOR' and child['status'] == 'REJECTION_RECORDED'
                and context is not None and any(f['function'] == child['site']['function']
                and f['line'] == child['site']['line'] for f in context['qualified_frames']))
    if child['status'] == 'REJECTION_NOT_REPRODUCED':
        require(child['stage'] == 'COLLECTOR' and child['site'] is None and context is None
                and child['error_type'] is None and type(child['manifest']) is list
                and 1 <= len(child['manifest']) <= LIMITS['runtime_files'])
        total, seen = 0, set()
        for row in child['manifest']:
            require(type(row) is list and len(row) == 3)
            name, size, h = row
            require(type(name) is str and len(name.encode()) <= 512 and name.startswith(('REPO/', 'PYTHON_BASE/'))
                    and not name.startswith(('REPO/data/', 'REPO/.env'))
                    and all(p not in {'', '.', '..'} for p in name.split('/'))
                    and not any(ord(c) < 32 or c == '\\' for c in name) and name not in seen
                    and type(size) is int and 0 <= size <= LIMITS['runtime_hash_bytes'] and hex64(h))
            total += size
            seen.add(name)
        require(type(child['runtime_bytes_observed']) is int and child['runtime_bytes_observed'] == total
                and type(child['runtime_bytes_reserved']) is int
                and child['runtime_bytes_reserved'] == total + len(seen) <= LIMITS['runtime_hash_bytes']
                and len(canonical(child['manifest'])) <= LIMITS['runtime_manifest_bytes'])
    else:
        require(child['manifest'] is None and child['runtime_bytes_observed'] is None
                and child['runtime_bytes_reserved'] is None and child['error_type'] is not None)
        if child['status'] == 'PRECONDITION_STOP':
            require(child['site'] is None and context is None)
        else:
            require(child['stage'] == 'COLLECTOR')
    return child


def _check_ancestor(root):
    observed = reserved = 0
    for name, ref in ANCESTOR['records'].items():
        h, size, charge = frozen._stable_hash(root / ANCESTOR['scope'] / name, ref['bytes'] + 1)
        require(h == ref['sha256'] and size == ref['bytes'])
        observed += size
        reserved += charge
    return observed, reserved


def run_phase(root, raw, expected):
    root = Path(root).absolute()
    packet = validate_packet(root, raw, expected)
    store = DurableDiagnostic(root)
    started = time.monotonic()
    store.write('STARTED.json', canonical({'kind': KIND, 'plan_sha256': expected,
                'ancestor_plan_sha256': OLD_PLAN, 'ancestor_full_limits_remain_consumed': True,
                'limits': LIMITS, 'no_retry': True, 'qualification_or_source_authority': False}))
    proc, out, err = None, bytearray(), bytearray()
    observed_code = reserved_code = 0
    ancestry = None
    failed = False
    try:
        ancestry = _check_ancestor(root)
        for name, ref in packet['code_refs'].items():
            h, size, charge = frozen._stable_hash(root / name, LIMITS['code_read_bytes'] - reserved_code)
            observed_code += size
            reserved_code += charge
            require(h == ref['sha256'] and size == ref['bytes'])
        require((time.monotonic() - started) * 1000 < LIMITS['wall_ms'])
        proc = subprocess.Popen([sys.executable, '-I', '-B', '-S', str(root / ENTRY),
                                '--runtime-diagnostic-worker', str(root)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, cwd=root, env={'PATH': os.defpath, 'LC_ALL': 'C'})
        peak = frozen._exchange(proc, canonical({'ancestor_plan_sha256': OLD_PLAN}), started, out, err)
        child = _validate_child(bytes(out))
        require((time.monotonic() - started) * 1000 < LIMITS['wall_ms'])
        second = _check_ancestor(root)
        require(ancestry == second)
        require((time.monotonic() - started) * 1000 < LIMITS['wall_ms'])
        store.write('worker.json', bytes(out))
        outcome = {'status': 'DIAGNOSTIC_RECORDED_NOT_QUALIFICATION_OR_SOURCE_ADMISSION',
                   'plan_sha256': expected, 'worker_sha256': sha(bytes(out)),
                   'diagnostic_status': child['status'], 'ancestor_plan_sha256': OLD_PLAN,
                   'ancestor_full_limits_remain_consumed': True, 'ancestor_unchanged': True,
                   'ancestor_metadata_bytes_observed': ancestry[0] * 2,
                   'ancestor_metadata_bytes_reserved': ancestry[1] * 2,
                   'code_bytes_observed': observed_code, 'code_bytes_reserved': reserved_code,
                   'sampled_child_peak_rss_bytes': peak if peak else None,
                   'source_reads': 0, 'reader_attempts': 0, 'page_extractions': 0,
                   'model_calls': 0, 'cost_usd': 0}
    except BaseException:
        failed = True
        outcome = {'status': 'DIAGNOSTIC_STOP_UNKNOWN_NO_RETRY', 'plan_sha256': expected,
                   'ancestor_plan_sha256': OLD_PLAN, 'ancestor_full_limits_remain_consumed': True,
                   'new_full_limits_consumed': LIMITS, 'observed_native_attempt': proc is not None,
                   'source_reads': 0, 'reader_attempts': 0, 'page_extractions': 0, 'model_calls': 0, 'cost_usd': 0}
    finally:
        if proc is not None:
            try:
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, 9)
                    except ProcessLookupError:
                        pass
                proc.wait(timeout=1)
            except BaseException:
                failed = True
                outcome = {'status': 'DIAGNOSTIC_REAP_UNKNOWN_NO_RETRY',
                           'plan_sha256': expected, 'ancestor_plan_sha256': OLD_PLAN,
                           'ancestor_full_limits_remain_consumed': True, 'new_full_limits_consumed': LIMITS,
                           'source_reads': 0, 'reader_attempts': 0, 'page_extractions': 0,
                           'model_calls': 0, 'cost_usd': 0}
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()
    if failed:
        if out and not (store.path / 'worker.json').exists():
            store.write('partial_stdout.local.bin', bytes(out[:LIMITS['stdout_bytes']]))
        if err:
            store.write('stderr.local.bin', bytes(err[:LIMITS['stderr_bytes']]))
    store.write('OUTCOME.json', canonical(outcome))
    if failed:
        raise frozen.QualificationStopped()
    return outcome


def _diagnostic_guard(event, args):
    if (event.startswith(('socket.', 'os.exec')) or event in {
            'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn'}):
        require(False)


def _worker(root):
    import resource
    stage = 'RESOURCE'
    base = {'kind': 'CLERK2020_RUNTIME_DIAGNOSTIC_RESULT_V1', 'ancestor_plan_sha256': OLD_PLAN,
            'source_reads': 0, 'reader_attempts': 0, 'page_extractions': 0, 'model_calls': 0,
            'network_requests': 0, 'project_overlay': list(OVERLAY), 'external_origin_rules_changed': False,
            'excluded_modules': 0, 'qualification_or_source_admission': False}
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (LIMITS['child_cpu_soft_seconds'], LIMITS['child_cpu_hard_seconds']))
        require(decode(sys.stdin.buffer.read(1025), 1024) == {'ancestor_plan_sha256': OLD_PLAN})
        sys.path[:0] = [str(root / 'src'), str(root / 'tests'), str(root / '.venv/lib/python3.12/site-packages')]
        stage = 'PRELOAD'
        sys.addaudithook(_diagnostic_guard)
        import pypdf
        import test_clerk2020_native_inventory_v1  # Same preload as original, never call its PDF fixtures.
        stage = 'IDENTITY'
        require(sys.implementation.name == 'cpython' and sys.version.split()[0] == '3.12.14'
                and sys.platform == 'darwin' and os.uname().machine == 'arm64' and pypdf.__version__ == '6.10.0')
        stage = 'COLLECTOR'
        result = collect_diagnostic(root)
    except BaseException:
        result = {'status': 'PRECONDITION_STOP', 'error_type': 'UNCLASSIFIED', 'site': None,
                  'context': None, 'manifest': None, 'runtime_bytes_observed': None, 'runtime_bytes_reserved': None}
    raw = canonical({**base, **result, 'stage': stage,
                     'collector_passes_attempted': 1 if stage == 'COLLECTOR' else 0})
    require(len(raw) <= LIMITS['stdout_bytes'])
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--runtime-diagnostic-worker':
        _worker(Path(sys.argv[2]).absolute())
    else:
        raise SystemExit('Exact reviewed root diagnostic release required; no source/qualification retry entry.')
