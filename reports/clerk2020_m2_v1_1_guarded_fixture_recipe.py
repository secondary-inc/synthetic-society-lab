"""Reproduce only authored M2 components; actual research inputs stay denied."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
BLOCKED = [str(ROOT / 'data/raw'), str(ROOT / 'data/processed')]
# This is a test-interpreter stdlib exception, not a runtime identity admission.
STDLIB = str(Path(sys.base_prefix) / 'lib' / ('python%d.%d' % sys.version_info[:2]))


def guard(event, args):
    if event in {'open', 'os.listdir', 'os.scandir'} and args and isinstance(args[0], (str, bytes)):
        path = args[0].decode() if isinstance(args[0], bytes) else args[0]
        # Normalize lexical dot components without resolving/statting source files.
        import os
        path = os.path.abspath(path)
        if any(path == b or path.startswith(b + '/') for b in BLOCKED):
            if not (path == STDLIB or path.startswith(STDLIB + '/')):
                raise RuntimeError('ACTUAL_RESEARCH_SOURCE_IO_FORBIDDEN')
    if event.startswith('socket.'):
        raise RuntimeError('NETWORK_FORBIDDEN')


sys.addaudithook(guard)
import test_clerk2020_m2_v1_1 as fixture
from civiclab.e01.clerk2020_m2_v1_1_contracts import canonical, digest, run_id, sha

result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromModule(fixture))
if not result.wasSuccessful():
    sys.exit(1)

t, payloads, bindings = fixture.terminal_fixture()
outcome = t.finalize(payloads, bindings)
checks = fixture.CrashPoint()
again, p2, b2 = fixture.terminal_fixture(checks)
again.finalize(p2, b2)
assert t.store.snapshot() == again.store.snapshot()
code_paths = [
    'src/civiclab/e01/clerk2020_m2_v1_1_contracts.py',
    'src/civiclab/e01/clerk2020_m2_v1_1_control.py',
    'src/civiclab/e01/clerk2020_m2_v1_1_backend.py',
    'tests/test_clerk2020_m2_v1_1.py',
    'reports/clerk2020_m2_v1_1_guarded_fixture_recipe.py',
]
code_refs = {name: sha((ROOT / name).read_bytes()) for name in code_paths}
input_refs = [sha(raw) for raw in fixture.documents()]
fixture_decision = {'label': 'MOCK', 'code_refs': code_refs,
                    'input_hashes': input_refs, 'seed': 0}
report = {
    'label': 'MOCK_AUTHORED_ONLY_NOT_REAL_PDF_OR_NATIVE_DURABILITY',
    'python_observed': sys.version.split()[0], 'tests': result.testsRun,
    'test_success': result.wasSuccessful(), 'actual_source_reads': 0,
    'fixture_run_id': run_id('DEMO_CAMPAIGN', 'AUTHORED_FIXTURE', fixture_decision),
    'fixture_id_scope': 'Outer deterministic authored evidence ID; not an actual admitted source run',
    'code_refs': code_refs, 'authored_input_hashes': input_refs, 'seed': 0,
    'serving_provider': None, 'usage': None, 'actual_billing': None,
    'actual_runtime_inspection_or_admission': False, 'actual_backend_import': False,
    'actual_keys_env_network_model_calls': 0, 'cost_usd': 0,
    'native_crash_or_resource_containment': 'NOT_RUN',
    'boundary_count': len(checks.seen), 'boundaries': checks.seen,
    'prefix_sha256': sha(t.prefix()), 'prefix_bytes': len(t.prefix()),
    'result': outcome, 'counters': t.counters.snapshot(),
    'deterministic_mock_rerun_identical': True,
    'rerun_scope': 'Independent authored fixture objects, not a source-job replay or budget reset',
    'artifacts': [{'slot': name, 'sha256': sha(raw), 'bytes': len(raw),
                   'authored_utf8_content': raw.decode('utf8')}
                  for name, raw in sorted(t.store.snapshot().items())],
    'policy_sha256': hashlib.sha256(fixture.POLICY).hexdigest(),
}
# Caller chooses a NEW evidence path explicitly; default prints only a summary.
if len(sys.argv) == 2:
    destination = Path(sys.argv[1])
    assert destination.parent == ROOT / 'reports'
    assert destination.name.startswith('clerk2020_m2_v1_1_')
    with destination.open('x') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
print(json.dumps({k: report[k] for k in ['label', 'python_observed', 'tests',
    'boundary_count', 'test_success', 'actual_source_reads', 'cost_usd',
    'deterministic_mock_rerun_identical']}, sort_keys=True))
