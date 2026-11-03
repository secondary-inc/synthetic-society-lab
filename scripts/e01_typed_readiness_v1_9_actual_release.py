"""Bounded local v1.9 primary/replay receipt harness for one explicit lead release.

This script is not an owner-authorization service. Execution requires the
separate recorded lead instruction. No automatic retry or inference/network.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import time

from civiclab.common import canonical_hash, sha256_file
from civiclab.e01 import ballots_v1_9 as m

AUTHORIZATION = 'E01_TYPED_V1_9_CACHED_PRIMARY_REPLAY_20261103'
CONFIG = 'configs/e01_typed_readiness_v1_9_candidate.json'
AUDIT = 'reports/INDEPENDENT_AUDIT_E01_TYPED_READINESS_V1_9_CODE_COMMIT_CLARIFIED.json'
EXPECTED = {
    CONFIG: 'f906665266fa7f816d37002e677fdc1d3e99bcefe7a1c1163d56bc91eb48a5ac',
    'src/civiclab/e01/ballots_v1_9.py': 'c4f9cdde81cd58b9b2c5f97e6ac41dab4764b48c12376be732887e254a3be04a',
    AUDIT: 'e61f5e2b1c9c55e3167e2894c542a696140f3d7f4d6bb6678a35a96521771918',
}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    # Immutable control records: a failed/uncertain phase cannot be retried by
    # rerunning this harness. No research payload goes into this receipt.
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def pins_and_runtime(root):
    for path, expected in EXPECTED.items():
        assert sha256_file(root / path) == expected, 'PIN_DRIFT_ABORT'
    c = m.snapshot(json.loads((root / CONFIG).read_text()))
    pins = {**c['code_config_audit_pins'], **EXPECTED}
    assert all(sha256_file(root / p) == h for p, h in pins.items()), 'PIN_DRIFT_ABORT'
    versions = {}
    for line in (root / 'configs/runtime_python312_geometry_20261103.txt').read_text().splitlines():
        if '==' in line and not line.startswith('#'):
            package, expected = line.split('==')
            versions[package] = importlib.metadata.version(package)
            assert versions[package] == expected, 'RUNTIME_DRIFT_ABORT'
    assert sys.version_info[:2] == (3, 12), 'RUNTIME_DRIFT_ABORT'
    return c, pins, versions


def hashes(path):
    return {p.name: sha256_file(p) for p in sorted(path.iterdir()) if p.is_file() and p.name != '.lock'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['preflight', 'primary', 'replay'])
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--control', required=True, type=Path)
    parser.add_argument('--execute-lead-release', required=True, choices=[AUTHORIZATION])
    args = parser.parse_args()
    root = args.root.resolve()
    control = args.control.absolute()
    assert control.parent == root / 'data/processed/e01_typed_v1_9_actual_control'
    assert not any(p.is_symlink() for p in (control, *control.parents))
    if args.phase == 'preflight':
        control.mkdir(parents=True, exist_ok=False)
    assert control.is_dir()
    save(control / (args.phase + '_started.local.json'), {'phase': args.phase, 'started_at_utc': now(),
         'lead_authorization': AUTHORIZATION, 'retry_authorized': False})
    try:
        c, pins, versions = pins_and_runtime(root)
        if args.phase == 'preflight':
            # Hash exactly the admitted40source/fourreference set, no pure parse.
            refs = m.verify_bound_inputs(m.root_guard(root), c)
            assert set(refs) == {'legacy_public', 'legacy_rosters', 'id_records', 'id_diagnostics'}
            save(control / 'preflight_complete.local.json', {'completed_at_utc': now(), 'pins': pins,
                 'runtime_versions': versions, 'python': sys.version.split()[0],
                 'source_declarations': c['sources'], 'references': c['references'],
                 'distinct_source_count': len(c['sources']), 'declared_source_bytes': sum(s['bytes'] for s in c['sources']),
                 'helper_calls': 0, 'model_calls': 0, 'cost_usd': 0})
            print(json.dumps({'phase': args.phase, 'status': 'PREFLIGHT_PINS_AND_RUNTIME_MATCH', 'sources': 40, 'references': 4}))
            return
        assert (control / 'preflight_complete.local.json').is_file(), 'PREFLIGHT_REQUIRED'
        if args.phase == 'replay':
            assert (control / 'primary_complete.local.json').is_file(), 'PRIMARY_ACK_REQUIRED_NO_AUTORETRY'
        previous = {p.name for p in (root / 'data/processed/runs').iterdir() if p.is_dir() and p.name.startswith('e01-')}
        output = io.StringIO()
        error = None
        path = None
        started = time.monotonic()
        with redirect_stdout(output), redirect_stderr(output):
            try:
                path = m.run_readiness(root, c)
            except BaseException as exc:
                error = type(exc).__name__
        # Keep every captured diagnostic local regardless of content; export
        # only its hash, bytecount and safe exception type.
        log = output.getvalue().encode()
        (control / (args.phase + '_diagnostics.local.txt')).write_bytes(log)
        created = sorted(p.name for p in (root / 'data/processed/runs').iterdir()
                         if p.is_dir() and p.name.startswith('e01-') and p.name not in previous)
        receipt = {'phase': args.phase, 'lead_authorization': AUTHORIZATION, 'completed_at_utc': now(),
                   'elapsed_seconds': time.monotonic() - started, 'new_parent_ids': created,
                   'caller_error_type': error, 'automatic_retry': False, 'captured_diagnostic_sha256': hashlib.sha256(log).hexdigest(),
                   'captured_diagnostic_bytes': len(log), 'pins': pins, 'runtime_versions': versions,
                   'model_calls': 0, 'cost_usd': 0}
        if error:
            receipt['status'] = 'CALLER_OUTCOME_REQUIRES_INDEPENDENT_READ_ONLY_RESOLUTION_NO_RETRY'
            receipt['artifact_hashes'] = {name: hashes(root / 'data/processed/runs' / name) for name in created}
            save(control / (args.phase + '_uncertain_or_failed.local.json'), receipt)
            print(json.dumps({'phase': args.phase, 'status': receipt['status'], 'error_type': error, 'run_ids': created}))
            raise SystemExit(2)
        assert path is not None and created == [path.name], 'UNEXPECTED_PARENT_SET_REVIEW_REQUIRED'
        public = m.read_verified_public(path)
        assert all(sha256_file(root / p) == h for p, h in pins.items()), 'POST_RUN_PIN_DRIFT'
        receipt.update(status='CALLER_ACK_AND_TYPED_SEAL_VERIFIED_PENDING_INDEPENDENT_POST_RUN_REVIEW',
                       run_id=path.name, run_path=str(path.relative_to(root)), artifact_hashes=hashes(path),
                       conditional_typed_metrics=public['metrics'], accepted_coverage_promoted=False)
        save(control / (args.phase + '_complete.local.json'), receipt)
        print(json.dumps({'phase': args.phase, 'status': receipt['status'], 'run_id': path.name}))
    except BaseException as exc:
        marker = control / (args.phase + '_control_error.local.json')
        if not marker.exists():
            save(marker, {'phase': args.phase, 'status': 'STOP_REVIEW_NO_RETRY', 'error_type': type(exc).__name__,
                          'at_utc': now(), 'lead_authorization': AUTHORIZATION})
        raise


if __name__ == '__main__':
    main()
