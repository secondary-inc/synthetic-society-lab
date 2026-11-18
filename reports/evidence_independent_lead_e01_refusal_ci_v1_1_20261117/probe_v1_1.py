"""Independent authored-only collector/child harness check; no real input reader."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import resource
import signal
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
PINS = {
    'src/civiclab/e01/source_job_ledger_v1.py': 'fdb303d28be7c2d880a67ebb01bfd9d77e61228e7a5887acbf7efc39b959b3a5',
    'scripts/run_e01_saved_job_ledger_suite_v1.py': '33d208d3a19cf2fc4322e3e480a5ec27a07680bd89f5da4487f182629b1b8089',
    'tests/test_e01_source_job_ledger_v1.py': '598702cf080a066ae9904151e255e8613b03ad0eee17765b63f568a960629ee1',
}
for name, digest in PINS.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest

def process_state():
    return (resource.getrlimit(resource.RLIMIT_CPU),
            resource.getrlimit(resource.RLIMIT_FSIZE),
            signal.getsignal(signal.SIGALRM), signal.getitimer(signal.ITIMER_REAL),
            sys.gettrace(), sys.getprofile())

before = process_state()
stream = io.StringIO()
with contextlib.redirect_stdout(stream):
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'),
                                               pattern='test_e01_source_job_ledger_v1.py')
    assert suite.countTestCases() == 1
    assert process_state() == before
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun == 1
assert process_state() == before
raw = stream.getvalue()
assert len(raw.encode()) <= 65536
matches = [line.split('E01_SAVED_LEDGER_CI_NESTED_V1=', 1)[1] for line in raw.splitlines() if 'E01_SAVED_LEDGER_CI_NESTED_V1=' in line]
assert len(matches) == 1
nested = json.loads(matches[0])
assert nested['status'] == 'MOCK_NESTED_33_PASS'
assert len(nested['nested_cases']) == len(set(nested['nested_cases'])) == 33
assert nested['nested_receipt']['guard']['denied'] == 0

# Exercise parent cleanup branches with inert process/selector doubles.
# No extra OS child, signal, real FD, filesystem write or sleep occurs here.
module = sys.modules['test_e01_source_job_ledger_v1']
original = {k: getattr(module, k) for k in ('subprocess', 'selectors', 'os', 'time')}
class Pipe:
    closed = False
    def close(self): self.closed = True
class Child:
    def __init__(self, force_kill=False):
        self.stdout = Pipe(); self.returncode = None
        self.terminated = self.killed = 0; self.force_kill = force_kill
    def poll(self): return self.returncode
    def terminate(self): self.terminated += 1
    def kill(self): self.killed += 1; self.returncode = -9
    def wait(self, timeout):
        if self.force_kill and not self.killed:
            raise original['subprocess'].TimeoutExpired('AUTHORED_FAKE', timeout)
        self.returncode = self.returncode if self.returncode is not None else -15
        return self.returncode
class Selector:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def register(self, *args): pass
    def get_map(self): return {1: True}
    def select(self, timeout): return [(types.SimpleNamespace(fd=123), 1)]

controls = []
try:
    for kind in ('deadline', 'overflow', 'deadline_force_kill'):
        child = Child(force_kill=kind.endswith('force_kill'))
        ticks = iter([0., 179.])
        module.subprocess = types.SimpleNamespace(Popen=lambda *a, **k: child,
            DEVNULL=-3, PIPE=-1, STDOUT=-2,
            TimeoutExpired=original['subprocess'].TimeoutExpired)
        module.selectors = types.SimpleNamespace(DefaultSelector=Selector, EVENT_READ=1)
        module.time = types.SimpleNamespace(monotonic=(lambda: 0.) if kind == 'overflow' else lambda: next(ticks))
        module.os = types.SimpleNamespace(read=lambda fd, size: b'x' * size)
        try:
            module.bounded_child()
            raise AssertionError('Expected bounded-child refusal')
        except AssertionError as error:
            expected = 'CI_CHILD_CONSOLE_CAP' if kind == 'overflow' else 'CI_CHILD_DEADLINE'
            assert str(error) == expected
        assert child.terminated == 1 and child.stdout.closed
        assert child.killed == int(kind.endswith('force_kill'))
        controls.append(kind)
finally:
    for name, value in original.items(): setattr(module, name, value)
assert process_state() == before
print(raw, end='')
print(json.dumps({'kind': 'INDEPENDENT_E01_COLLECTOR_AND_CHILD_CHECK',
    'ordinary_cases': 1, 'nested_cases': 33, 'mock_cleanup_controls': controls,
    'collector_controls_unchanged': True, 'actual_reader_calls': 0,
    'network_calls': 0, 'model_calls': 0, 'cost_usd': 0,
    'startup_accounting': 'NOT_CLAIMED'}, sort_keys=True))
