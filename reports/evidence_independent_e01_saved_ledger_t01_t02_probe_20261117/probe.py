"""Single bounded authored-only regression confirmation; never actual inputs."""
import sys, os, time, resource, signal
START = time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
resource.setrlimit(resource.RLIMIT_FSIZE, (2097152, 2097152))
signal.alarm(30)
import ast, hashlib, json, math, types, copy
from pathlib import Path
SOURCE = Path.cwd() / 'src/civiclab/e01/source_job_ledger_v1.py'
SNAPSHOT = Path.cwd() / 'reports/evidence_e01_saved_job_ledger_v1_code_20261117/discovery_safe_v1_1/corrected_test_snapshot.py'
PINS = {SOURCE: 'fc0bf218eb486b4489bd109dcffc84d9538716cc80dd6034edb66bbb8b9415d7',
        SNAPSHOT: '2d9913891b91d4ac155e5850f7e2ba98d5675a43320f16850cc8bb6b96b57f7a'}
COUNTERS = {'read_bytes': 0, 'write_bytes': 0, 'denied': 0}
def audit(event, args):
    if time.monotonic() - START >= 30:
        raise RuntimeError('PROBE_WALL_CAP')
    if event.startswith(('socket.', 'subprocess.', 'ctypes.')) or event in {'os.system', 'os.fork', 'os.posix_spawn', 'os.exec', 'os.kill'}:
        COUNTERS['denied'] += 1
        raise PermissionError('EXTERNAL_DENIED')
    if event == 'open':
        name, mode, flags = args
        if type(name) is int or Path(os.fsdecode(name)).absolute() not in PINS or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            COUNTERS['denied'] += 1
            raise PermissionError('READ_WRITE_SCOPE')
        COUNTERS['read_bytes'] += Path(name).stat().st_size + 1
        if COUNTERS['read_bytes'] > 4194304:
            raise RuntimeError('READ_CAP')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.symlink', 'os.link', 'os.chmod', 'os.utime', 'os.truncate'}:
        COUNTERS['denied'] += 1
        raise PermissionError('MUTATION_DENIED')
sys.addaudithook(audit)
raw = {p: p.read_bytes() for p in PINS}
assert all(hashlib.sha256(raw[p]).hexdigest() == h for p, h in PINS.items())
M = types.ModuleType('independent_mock_ledger')
M.__file__ = str(SOURCE)
exec(compile(raw[SOURCE], str(SOURCE), 'exec'), M.__dict__)
# Extract only the two fixed fixture builders, not test cases, guard or main.
tree = ast.parse(raw[SNAPSHOT])
selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'ref', 'authored'}]
assert len(selected) == 2
env = {'M': M}
exec(compile(ast.Module(body=selected, type_ignores=[]), '<fixed-authored-fixture-builders>', 'exec'), env)
json_cases = []
for name, value in [('finite', b'{"x":1.25,"nested":[2e2,-3.5]}'),
                    ('overflow_positive', b'{"x":1e999}'),
                    ('overflow_negative', b'{"x":-1e999}'),
                    ('overflow_nested', b'{"x":[{"y":1e999}]}'),
                    ('literal_nan_control', b'{"x":NaN}'),
                    ('literal_infinity_control', b'{"x":Infinity}')]:
    def nonfinite(v):
        if isinstance(v, float): return not math.isfinite(v)
        if isinstance(v, list): return any(nonfinite(x) for x in v)
        if isinstance(v, dict): return any(nonfinite(x) for x in v.values())
        return False
    try:
        decoded = M.exact_json(value)
        observation = {'returned': True, 'contains_nonfinite': nonfinite(decoded), 'refusal': None}
    except M.LedgerRefused as error:
        observation = {'returned': False, 'contains_nonfinite': None, 'refusal': error.code}
    json_cases.append({'case': name, **observation})

io_cases = []
for label, operation, error_type in [('positive_read_control', None, None),
                                     ('size_permission_caught', 'size', PermissionError),
                                     ('read_oserror_caught', 'read', OSError),
                                     ('size_missing_control', 'size', FileNotFoundError),
                                     ('read_missing_control', 'read', FileNotFoundError)]:
    files, plan, prefix, *_ = env['authored']()
    store = M.MemoryFixture(files)
    output = M.MemoryOutput()
    observed = {'callback_calls': 0, 'injected': 0, 'caught_exception_type': None}
    class Reader:
        mock_only = True
        def read_verified_public(self, view, prefix, config):
            observed['callback_calls'] += 1
            if operation is not None:
                original = getattr(store, operation)
                def broken(*args):
                    observed['injected'] += 1
                    raise error_type('AUTHORED_FIXED_ERROR')
                setattr(store, operation, broken)
                try:
                    view.read(prefix + '/typed_document_readiness.json')
                except (OSError, M.LedgerRefused) as error:
                    observed['caught_exception_type'] = type(error).__name__
                finally:
                    setattr(store, operation, original)
            return view.json(prefix + '/typed_document_readiness.json')
    try:
        result = M.compile_mock_once(plan, store, Reader(), output, expected_plan_sha256=M.sha(M.packed(plan)))
        observation = {'compiled': True, 'raised_type': None, 'budget_failed': result['budget']['failed']}
    except (OSError, M.LedgerRefused) as error:
        failure = M.exact_json(output.files['FAILURE.json'])
        observation = {'compiled': False, 'raised_type': type(error).__name__, 'budget_failed': failure['budget']['failed']}
    io_cases.append({'case': label, **observed, **observation, 'complete_present': 'COMPLETE.json' in output.files})
assert json_cases[0]['returned'] and not json_cases[0]['contains_nonfinite']
assert all(not x['returned'] and x['refusal'] == 'JSON_NONFINITE' for x in json_cases[4:])
assert io_cases[0]['compiled'] and io_cases[0]['complete_present']
assert all(not x['compiled'] and x['budget_failed'] and not x['complete_present'] for x in io_cases[3:])
report = {'kind': 'INDEPENDENT_E01_T01_T02_AUTHORED_CONFIRMATION', 'runtime': sys.version.split()[0],
          'json_cases': json_cases, 'io_cases': io_cases, 'guard': COUNTERS,
          'T01_confirmed': all(x['returned'] and x['contains_nonfinite'] for x in json_cases[1:4]),
          'T02_confirmed': all(x['compiled'] and x['complete_present'] and not x['budget_failed'] for x in io_cases[1:3]),
          'wall_seconds': time.monotonic() - START, 'actual_reader_calls': 0, 'network_calls': 0, 'model_calls': 0, 'cost_usd': 0}
assert COUNTERS['denied'] == 0
text = json.dumps(report, sort_keys=True)
assert len(text.encode()) <= 65536
print(text)
