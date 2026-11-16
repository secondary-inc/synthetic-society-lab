"""Pure, unwired refusal observability and explicit dry-run proposal.

No subprocess, pip, filesystem write or automatic log flush occurs here.
The recording subclass always delegates denials to its frozen base guard.
"""
import json
import os
from pathlib import Path
import threading

MAX_EVENTS = 16
MAX_JSON_BYTES = 4096
MAX_COUNTER = 2147483647
DIAGNOSTIC_SCOPE = 'data/processed/e01_pypdf701_build_v1/diagnostic-v2-20261116'
DIAGNOSTIC_TARGET = '.venv-e01-pypdf-7.0.1-DIAGNOSTIC-NOT-INSTALL-v2'
CODES = frozenset({
    'GUEST_RAW_PATH', 'GUEST_WRITE_OUTSIDE_OWNED', 'GUEST_READ_OUTSIDE_ALLOWLIST',
    'GUEST_UNKNOWN_MUTATION_DESCRIPTOR', 'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED',
    'GUEST_READ_CAP', 'GUEST_SYMLINK_SOURCE', 'GUEST_SYMLINK_TRAVERSAL',
    'GUEST_UNBOUNDED_MUTATION', 'GUEST_OUTPUT_CAP', 'GUEST_WRITE_CAP',
    'GUEST_TRUNCATE_DENIED', 'DOWNLOADED_PACKAGE_IMPORT_DENIED',
    'DIAGNOSTIC_WRITE_OUTSIDE_SCOPE'})
OPERATIONS = frozenset({'FILE_READ', 'FILE_WRITE', 'SOCKET_CONSTRUCT', 'SOCKET_BIND', 'SOCKET_CONNECT',
                        'SOCKET_RESOLVE', 'SOCKET_METADATA', 'SOCKET_UNKNOWN', 'SUBPROCESS', 'FORK',
                        'EXEC', 'NATIVE_LOAD', 'MUTATION', 'OUTPUT', 'WRITE_CHARGE'})


def classify_socket_event(event):
    # Exact closed labels only. This does not inspect any audit arguments and
    # never enables the operation. Unknown socket events remain distinguishable.
    if type(event) is not str: return 'SOCKET_UNKNOWN'
    if event == 'socket.__new__': return 'SOCKET_CONSTRUCT'
    if event == 'socket.bind': return 'SOCKET_BIND'
    if event in {'socket.connect', 'socket.connect_ex'}: return 'SOCKET_CONNECT'
    if event in {'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyname_ex',
                 'socket.gethostbyaddr', 'socket.getnameinfo'}: return 'SOCKET_RESOLVE'
    if event == 'socket.gethostname': return 'SOCKET_METADATA'
    return 'SOCKET_UNKNOWN'


class RefusalJournal:
    def __init__(self):
        self.events = []
        self.total = 0
        self.dropped = 0
        self.saturated = False
        self.lock = threading.RLock()

    def record(self, code, operation):
        safe_code = code if type(code) is str and code in CODES else 'UNKNOWN_REFUSAL_CODE'
        safe_operation = operation if type(operation) is str and operation in OPERATIONS else 'UNKNOWN'
        with self.lock:
            if self.total < MAX_COUNTER: self.total += 1
            else: self.saturated = True
            if len(self.events) < MAX_EVENTS:
                self.events.append({'sequence': self.total, 'code': safe_code, 'operation': safe_operation})
            elif self.dropped < MAX_COUNTER: self.dropped += 1
            else: self.saturated = True

    def packed(self):
        with self.lock:
            value = {'kind': 'BOUNDED_GUEST_REFUSAL_JOURNAL_V2',
                     'events': [dict(event) for event in self.events],
                     'total_events': self.total, 'dropped_events': self.dropped,
                     'counter_saturated': self.saturated}
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        if len(raw) > MAX_JSON_BYTES: raise ValueError('REFUSAL_JOURNAL_SIZE')
        return raw


def recording_policy_class(base_policy):
    class RecordingPolicy(base_policy):
        def __init__(self, *args, **kwargs):
            self.refusal_journal = RefusalJournal()
            self._refusal_context = threading.local()
            super().__init__(*args, **kwargs)

        def refuse(self, reason):
            try:
                self.refusal_journal.record(reason, getattr(self._refusal_context, 'operation', 'UNKNOWN'))
            finally:
                # Even a diagnostic failure cannot prevent the original denial.
                super().refuse(reason)

        def audit(self, event, args):
            old = getattr(self._refusal_context, 'operation', 'UNKNOWN')
            if event == 'open' and len(args) > 2 and type(args[2]) is int:
                operation = 'FILE_WRITE' if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND) else 'FILE_READ'
            elif event.startswith('socket.'): operation = classify_socket_event(event)
            elif event == 'subprocess.Popen': operation = 'SUBPROCESS'
            elif event == 'ctypes.dlopen': operation = 'NATIVE_LOAD'
            elif event in {'os.fork', 'os.forkpty'}: operation = 'FORK'
            elif event in {'os.posix_spawn', 'os.system', 'os.exec', 'os.spawn'}: operation = 'EXEC'
            else: operation = 'MUTATION'
            self._refusal_context.operation = operation
            try: return super().audit(event, args)
            finally: self._refusal_context.operation = old

        def path(self, value, flags):
            old = getattr(self._refusal_context, 'operation', 'UNKNOWN')
            self._refusal_context.operation = ('FILE_WRITE' if flags &
                (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND) else 'FILE_READ')
            try:
                result = super().path(value, flags)
                writing = flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                if writing and not Path(value).is_relative_to(self.stage):
                    self.refuse('DIAGNOSTIC_WRITE_OUTSIDE_SCOPE')
                return result
            finally: self._refusal_context.operation = old

        def charge(self, data, output=False):
            old = getattr(self._refusal_context, 'operation', 'UNKNOWN')
            self._refusal_context.operation = 'OUTPUT' if output else 'WRITE_CHARGE'
            try: return super().charge(data, output)
            finally: self._refusal_context.operation = old

    return RecordingPolicy


def diagnostic_policy_class(base_policy):
    recording = recording_policy_class(base_policy)
    class DiagnosticPolicy(recording):
        def __init__(self, root, binding, payload):
            super().__init__(root, binding, payload)
            # Explicit instance routing, never mutation of frozen module globals.
            self.stage = self.root/DIAGNOSTIC_SCOPE
            self.target = self.root/DIAGNOSTIC_TARGET
            for path in (self.stage, self.target):
                if any(parent.is_symlink() for parent in (path, *path.parents)):
                    raise ValueError('DIAGNOSTIC_ROUTE_ALIAS')
            if self.target.exists(): raise ValueError('DIAGNOSTIC_TARGET_EXISTS')
    return DiagnosticPolicy


def dry_run_arguments(original):
    """Only add one reviewed --dry-run flag to the exact install argument list."""
    if (type(original) is not list or not 16 <= len(original) <= 64
            or any(type(value) is not str or len(value) > 4096 for value in original)):
        raise ValueError('DRY_RUN_ARGUMENT_SCHEMA')
    if original[:6] != ['pip', '--isolated', '--disable-pip-version-check', '--no-input',
                        '--use-deprecated=legacy-certs', 'install']:
        raise ValueError('DRY_RUN_ARGUMENT_PREFIX')
    required = ['--prefix', '--ignore-installed', '--no-index', '--find-links', '--no-deps',
                '--no-compile', '--no-cache-dir', '--only-binary=:all:', '--require-hashes', '-r']
    if any(original.count(value) != 1 for value in required):
        raise ValueError('DRY_RUN_ARGUMENT_FLAGS')
    if len(original) != 19:
        raise ValueError('DRY_RUN_ARGUMENT_COUNT')
    if any(value in original for value in ['--dry-run', '--report', '--target', '--user', '--python']):
        raise ValueError('DRY_RUN_UNREVIEWED_OPTION')
    expected = original[:6]+['--prefix', original[7], '--ignore-installed', '--no-index',
        '--find-links', original[11], '--no-deps', '--no-compile', '--no-cache-dir',
        '--only-binary=:all:', '--require-hashes', '-r', original[18]]
    if original != expected:
        raise ValueError('DRY_RUN_ARGUMENT_ORDER')
    if any(not Path(original[index]).is_absolute() or '..' in Path(original[index]).parts
           for index in (7, 11, 18)):
        raise ValueError('DRY_RUN_ARGUMENT_PATHS')
    return original[:6]+['--dry-run']+original[6:]
