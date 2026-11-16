"""Pure, unwired refusal observability and deterministic PATH proposal.

No subprocess, pip, filesystem write or automatic log flush occurs here.
The recording subclass always delegates denials to its frozen base guard.
"""
import json
import os
from pathlib import Path
import stat
import sys
import threading

MAX_EVENTS = 16
MAX_JSON_BYTES = 4096
MAX_COUNTER = 2147483647
CODES = frozenset({
    'GUEST_RAW_PATH', 'GUEST_WRITE_OUTSIDE_OWNED', 'GUEST_READ_OUTSIDE_ALLOWLIST',
    'GUEST_UNKNOWN_MUTATION_DESCRIPTOR', 'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED',
    'GUEST_READ_CAP', 'GUEST_SYMLINK_SOURCE', 'GUEST_SYMLINK_TRAVERSAL',
    'GUEST_UNBOUNDED_MUTATION', 'GUEST_OUTPUT_CAP', 'GUEST_WRITE_CAP',
    'GUEST_TRUNCATE_DENIED', 'DOWNLOADED_PACKAGE_IMPORT_DENIED'})
OPERATIONS = frozenset({'FILE_READ', 'FILE_WRITE', 'SOCKET', 'SUBPROCESS', 'FORK',
                        'EXEC', 'NATIVE_LOAD', 'MUTATION', 'OUTPUT', 'WRITE_CHARGE'})


def deterministic_guest_path():
    if sys.platform != 'darwin':
        raise ValueError('PATH_PLATFORM')
    path = Path('/dev/null')
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError('PATH_SENTINEL_ALIAS')
    if not stat.S_ISCHR(path.lstat().st_mode):
        raise ValueError('PATH_SENTINEL_TYPE')
    # A non-directory, non-empty sole PATH component cannot search cwd or tools.
    return str(path)


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
            value = {'kind': 'BOUNDED_GUEST_REFUSAL_JOURNAL_V1',
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
            if event.startswith('socket.'): operation = 'SOCKET'
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
            try: return super().path(value, flags)
            finally: self._refusal_context.operation = old

        def charge(self, data, output=False):
            old = getattr(self._refusal_context, 'operation', 'UNKNOWN')
            self._refusal_context.operation = 'OUTPUT' if output else 'WRITE_CHARGE'
            try: return super().charge(data, output)
            finally: self._refusal_context.operation = old

    return RecordingPolicy
