#!/usr/bin/env python3
"""Record a private AUTHORED compatibility control; no production options.

Requires checkout test helpers via PYTHONPATH=src:tests. OS account, clock,
catalog, key and transport boundaries are all patched to authored fixtures.
"""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from civiclab.common import atomic_json, canonical_hash, sha256_file
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from civiclab.production_compatibility_v4 import execute_compatibility
from test_production_admission_v4 import account, initialize, approval, grant
from test_production_compatibility_v4 import assertions, Stub


def record(directory):
    root = Path(directory).resolve()
    base = (Path(__file__).resolve().parents[1] / 'data/processed/fixture_scopes').resolve()
    if base not in root.parents:
        raise ExecutionBlocked('new checkout fixture_scopes child required')
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    home = root / 'AUTHORED_OS_HOME'; workspace = root / 'AUTHORED_WORKSPACE'
    with account(home):
        release, review, er, raw, receipt = assertions()
        owner = initialize(release, review)
        a = approval(owner, release, review, count=1)
        epoch = grant(owner, a, release, review)
        stub = Stub()
        kwargs = {'expected_review_hash': canonical_hash(review), 'expected_approval_hash': epoch,
                  'expected_executor_review_hash': canonical_hash(er)}
        with patch('civiclab.production_admission_v4._fetch_public_catalog', return_value=(raw, receipt)) as metadata, \
             patch('civiclab.production_admission_v4._read_environment_key', return_value=_Credential('AUTHORED_FAKE_EXECUTOR_CREDENTIAL')) as key, \
             patch('civiclab.production_compatibility_v4._transport', return_value=stub):
            result = execute_compatibility(workspace, release, review, a, er, **kwargs)
            refusals = []
            for label, output in (('same-output-no-replay', workspace),
                                  ('new-output-no-allowance-reset', root / 'SECOND_AUTHORED_WORKSPACE')):
                before = (owner.db_path.read_bytes(), owner.anchor.read_bytes(), len(stub.posts), len(stub.lookups), key.call_count)
                try:
                    execute_compatibility(output, release, review, a, er, **kwargs)
                except (ExecutionBlocked, FileExistsError):
                    pass
                else:
                    raise AssertionError('expected refusal: ' + label)
                after = (owner.db_path.read_bytes(), owner.anchor.read_bytes(), len(stub.posts), len(stub.lookups), key.call_count)
                if before != after:
                    raise AssertionError('refusal changed owner, dispatched or read key')
                refusals.append({'case': label, 'owner_bytes_unchanged': True,
                                 'additional_stub_POSTs': 0, 'additional_stub_statistics': 0,
                                 'additional_stub_key_reads': 0,
                                 'new_output_may_retain_failed_private_journal': output != workspace})
            snapshot = owner.snapshot()
            if len(stub.posts) != 1 or len(stub.lookups) != 1 or snapshot['charges'][0]['status'] != 'PHASE_COMMITTED':
                raise AssertionError('authored compatibility oracle mismatch')
            for name, value in (('release', release), ('authored-foundation-review', review),
                                ('authored-executor-review', er), ('authored-operator-assertion', a),
                                ('authored-response', stub.response), ('authored-statistics', stub.stats),
                                ('fake-request-bytes-decoded', [json.loads(b) for b in stub.posts]),
                                ('fake-statistics-identities', stub.lookups), ('owner-snapshot', snapshot),
                                ('refusals', refusals), ('result', result)):
                atomic_json(root / (name + '.local.json'), value)
            (root / 'authored-catalog.body').write_bytes(raw)
            observed = {'stub_key_reads': key.call_count, 'stub_metadata_GETs': metadata.call_count,
                        'stub_model_POSTs': len(stub.posts), 'stub_statistics_GETs': len(stub.lookups)}
    files = {str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob('*')) if p.is_file()}
    atomic_json(root / 'index.local.json', {
        'kind': 'AUTHORED_COMPATIBILITY_EXECUTOR_CONTROL_NO_REAL_AUTHORITY', 'artifacts': files,
        **observed, 'simulated_charged_microusd': snapshot['consumed_microusd']['total'],
        'actual_owner_bootstraps': 0, 'actual_key_reads': 0, 'network_requests': 0,
        'model_calls': 0, 'experimental_spend_usd': 0})
    return {'kind': 'AUTHORED_ONLY', 'path': str(root), 'index_sha256': sha256_file(root / 'index.local.json'),
            'indexed_files': len(files), **observed, 'actual_owner_bootstraps': 0,
            'actual_key_reads': 0, 'network_requests': 0, 'model_calls': 0, 'experimental_spend_usd': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    print(json.dumps(record(parser.parse_args().directory), sort_keys=True))
