"""Finite CI-only integration probe; no ordinary suite or research execution."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'scripts/run_offline_ci_v1.py'
EXPECTED = '9882cc86841b222f436c3210dd597bcf8d22623f08b31bdf95c5e691c940131b'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_CPU, (359, 360))
def deadline(*_):
    raise TimeoutError('FOCUSED_CI_DEADLINE')
signal.signal(signal.SIGALRM, deadline)
signal.setitimer(signal.ITIMER_REAL, 360)
spec = importlib.util.spec_from_file_location('reviewed_ci_runner', SOURCE)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)
specification = ci.plan(ROOT)
jobs = [dict(j, wall_seconds=30) for j in specification['jobs'] if j['phase'] != 'ordinary']
assert len(jobs) == 10
output = Path(__file__).parent / ('actual-' + sys.version.split()[0])
output.mkdir(mode=0o700, exist_ok=False)
ci.save_new(output / 'PLAN.json', {
    'kind': 'FINITE_FOCUSED_CI_INTEGRATION_PLAN', 'runner_sha256': EXPECTED,
    'jobs': jobs, 'python': sys.version.split()[0], 'maximum_children': 10,
    'overall_wall_seconds': 360, 'per_child_wall_seconds': 30,
    'per_child_output_bytes': 262144, 'ordinary_collection': False,
    'scope': 'Frozen engineering test groups only; no package installation or research release.',
})
started = time.monotonic()
results = []
for job in jobs:
    assert time.monotonic() - started < 325
    command = [sys.executable, '-I', '-B', '-S', str(SOURCE), '--child', job['group'],
               '--phase', job['phase'], '--runner-sha256', EXPECTED]
    ci.save_new(output / (job['id'] + '-RESERVED.json'), {'attempt': 1, 'job': job, 'argv': command})
    execution = ci.supervise(command, ci.child_environment(os.environ), job, output)
    receipt = None
    try:
        receipt = ci.parse_receipt(Path(execution['stdout']).read_bytes(), job, EXPECTED)
        ci.validate_coverage(receipt, job, specification)
        accepted = (execution['reason'] is None and execution['reaped']
                    and execution['returncode'] == 0 and receipt['status'] in {'PASS', 'NOT_RUN'})
    except (OSError, ValueError, ci.IsolationError):
        accepted = False
    result = {'job_id': job['id'], 'accepted': accepted, 'receipt': receipt, 'execution': execution}
    ci.save_new(output / (job['id'] + '-RESULT.json'), result)
    results.append(result)
    if not accepted:
        break
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
summary = {
    'kind': 'FOCUSED_CI_INTEGRATION_RESULT', 'python': sys.version.split()[0],
    'status': 'PASS_REQUESTED_GROUPS' if len(results) == 10 and all(r['accepted'] for r in results) else 'STOPPED',
    'groups_attempted': len(results), 'planned_groups': 10,
    'tests_run': sum((r['receipt'] or {}).get('tests_run') or 0 for r in results),
    'not_run_groups': [r['job_id'] for r in results if (r['receipt'] or {}).get('status') == 'NOT_RUN'],
    'elapsed_seconds': time.monotonic() - started, 'results': results,
    'full_collection_or_workflow': 'NOT_RUN', 'model_cost_USD': 0,
}
ci.save_new(output / 'SUMMARY.json', summary)
print(json.dumps({k: v for k, v in summary.items() if k != 'results'}, sort_keys=True))
raise SystemExit(0 if summary['status'] == 'PASS_REQUESTED_GROUPS' else 1)
