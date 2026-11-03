"""Owner-review viewer extension for two independently admitted demographic runs.

The original viewer stays hash-stable. Only exact admitted finalized payloads
are loaded; original local aggregates/projections never supply typed cells.
Audit-role labels establish workflow evidence, not cryptographic identity.
"""
import hashlib
from importlib.resources import files
import json
from pathlib import Path

from . import dashboard
from .benchmark_export import validate_projection
from .common import atomic_json, canonical_hash, sha256_file

ADMISSION = 'reports/INDEPENDENT_AUDIT_WYOMING_FINALIZATION_ADMISSION.json'
ADMISSION_SHA256 = '3f13ba4cddddf54b390e0236072e1a52f97c7373100e0d658404d0ed15491224'
SCHEMA = 'configs/wyoming_benchmark_projection_schema_v1.json'
ANCHOR = 'if(run.citizen_comparison){'


def bounded_read(path, limit=2_000_000):
    with path.open('rb') as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError('owner-review artifact exceeds limit')
    return value


def snapshot(root, run_ids=None):
    root = Path(root).resolve()
    data = dashboard.snapshot(root, run_ids)
    audit_path = root / ADMISSION
    if not audit_path.is_file():
        return data
    raw = bounded_read(audit_path)
    if hashlib.sha256(raw).hexdigest() != ADMISSION_SHA256:
        raise ValueError('owner-review admission receipt changed')
    audit = json.loads(raw)
    if (audit.get('status') != 'PASS_EXACT_WYOMING_FINALIZATION_OWNER_REVIEW_ADMISSION'
        or audit.get('auditor_role') != 'independent_auditor'
        or audit.get('owner_review_only') is not True
        or audit.get('external_publication_authorized') is not False):
        raise ValueError('owner-review admission scope mismatch')
    schema_path = root / SCHEMA
    schema_raw = bounded_read(schema_path)
    if hashlib.sha256(schema_raw).hexdigest() != audit['projection_schema_sha256']:
        raise ValueError('owner-review schema changed')
    schema = json.loads(schema_raw)
    accepted = {p['run_id']: p for p in audit['accepted_runs']}
    for run in data['runs']:
        proof = accepted.get(run['manifest']['run_id'])
        if proof is None:
            continue
        if (run['checksums_sha256'] != proof['checksums_sha256']
            or run['artifacts'].get('demographic-benchmark.json') != proof['artifact_sha256']
            or run['artifacts'].get('review-finalization.json') != proof['trace_sha256']):
            raise ValueError('owner-review finalized run identity mismatch')
        folder = root / 'data/processed/runs' / proof['run_id']
        payload_path = folder / 'demographic-benchmark.json'
        trace_path = folder / 'review-finalization.json'
        for path in (payload_path, trace_path):
            if not path.resolve().is_relative_to(folder.resolve()):
                raise ValueError('owner-review artifact escapes run')
        payload_raw = bounded_read(payload_path)
        trace_raw = bounded_read(trace_path)
        if (hashlib.sha256(payload_raw).hexdigest() != proof['artifact_sha256']
            or hashlib.sha256(trace_raw).hexdigest() != proof['trace_sha256']):
            raise ValueError('owner-review payload or trace changed')
        payload = json.loads(payload_raw)
        if canonical_hash(payload) != proof['artifact_canonical_sha256']:
            raise ValueError('owner-review canonical payload mismatch')
        validate_projection(payload, schema)
        trace = json.loads(trace_raw)
        bindings = {
            'accepted_payload_sha256': proof['artifact_sha256'],
            'accepted_canonical_sha256': proof['artifact_canonical_sha256'],
            'projection_schema_sha256': audit['projection_schema_sha256'],
            'finalization_config_sha256': audit['config_sha256'],
            'finalization_implementation_sha256': audit['reviewed_implementation_sha256'],
            'finalization_execution_approval_sha256': audit['code_execution_approval_sha256'],
            'output_disclosure_audit_sha256': audit['output_disclosure_audit_sha256'],
            'owner_review_only': True,
            'external_publication_authorized': False,
            'source_run_preserved': True,
        }
        if any(trace.get(k) != v for k, v in bindings.items()):
            raise ValueError('owner-review trace scope mismatch')
        if (sha256_file(folder / 'checksums.json') != proof['checksums_sha256']
            or sha256_file(payload_path) != proof['artifact_sha256']
            or sha256_file(trace_path) != proof['trace_sha256']):
            raise ValueError('owner-review run changed during reading')
        run['demographic_benchmark'] = payload
        run['benchmark_admission'] = {'path': ADMISSION, 'sha256': ADMISSION_SHA256,
                                      'trace_sha256': proof['trace_sha256'],
                                      'scope': audit['admission_scope']}
    if (sha256_file(audit_path) != ADMISSION_SHA256
        or sha256_file(schema_path) != audit['projection_schema_sha256']):
        raise ValueError('owner-review admission changed during reading')
    return data


def build(root, output, run_ids=None):
    data = snapshot(root, run_ids)
    if not data['runs']:
        raise ValueError('no completed verified runs to display')
    template = files('civiclab').joinpath('templates/run-viewer.html').read_text()
    detail = files('civiclab').joinpath('templates/benchmark-detail.html').read_text()
    if template.count(ANCHOR) != 1:
        raise ValueError('owner-review viewer composition anchor changed')
    template = template.replace(ANCHOR, detail + '\n' + ANCHOR)
    payload = json.dumps(data, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / 'snapshot.json', data)
    (output / 'index.html').write_text(template.replace('__RECORDED_DATA__', payload))
    return output / 'index.html'
