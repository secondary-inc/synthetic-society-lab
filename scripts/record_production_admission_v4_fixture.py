#!/usr/bin/env python3
"""Record AUTHORED v4 controls in a mocked OS home, never a real owner.

Requires checkout test helpers (PYTHONPATH=src:tests). No network, credential,
real-price, operator-approval or production-owner options are exposed.
"""
import argparse
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from civiclab.common import atomic_json, canonical_hash, sha256_file
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import (
    _Credential, prepare_new_dispatch, prepare_existing_statistics)
from test_production_admission_v4 import (
    account, materials, initialize, approval, grant, seen, settle, checkpoint, T0)


def record(directory):
    root = Path(directory).resolve()
    base = (Path(__file__).resolve().parents[1] / 'data/processed/fixture_scopes').resolve()
    if base not in root.parents:
        raise ExecutionBlocked('new checkout fixture_scopes directory required')
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    home = root / 'AUTHORED_OS_HOME'
    now = [T0]
    observations, refusals, payloads, settlements = [], [], [], []
    key_reads, metadata_reads = [], []

    def key():
        key_reads.append('AUTHORED_STUB_ACCESS_NO_ENV_READ')
        return _Credential('AUTHORED_FAKE_CREDENTIAL_NEVER_PERSIST')

    with account(home, now), patch('civiclab.production_admission_v4._read_environment_key', side_effect=key):
        release, review, raw, receipt = materials('AUTHORED-V4-RECORDED-ONE')
        owner = initialize(release, review)
        observations.append({'stage': 'ZERO_BOOTSTRAP', 'snapshot': owner.snapshot()})

        def prepare(r, v, a, epoch, body, proof):
            def fetch(model):
                metadata_reads.append({'model': model, 'stub_only': True})
                return body, proof
            with patch('civiclab.production_admission_v4._fetch_public_catalog', side_effect=fetch):
                return prepare_new_dispatch(r, v, a, expected_review_hash=canonical_hash(v),
                                            expected_approval_hash=epoch)

        def refuse(label, call):
            before = {str(p): sha256_file(p) for p in (owner.db_path, owner.anchor, owner.registration)}
            keys = len(key_reads)
            try:
                call()
            except ExecutionBlocked:
                pass
            else:
                raise AssertionError('expected refusal: ' + label)
            after = {str(p): sha256_file(p) for p in (owner.db_path, owner.anchor, owner.registration)}
            if before != after or keys != len(key_reads):
                raise AssertionError('refusal changed protected history or read fake key: ' + label)
            refusals.append({'case': label, 'protected_bytes_unchanged': True,
                             'additional_stub_key_reads': 0, 'model_calls': 0})

        a = approval(owner, release, review, count=1)
        epoch = canonical_hash(a)
        refuse('ungranted-assertion', lambda: prepare(release, review, a, epoch, raw, receipt))
        epoch = grant(owner, a, release, review)
        prepared = prepare(release, review, a, epoch, raw, receipt)
        payloads.append({'payload': prepared.payload, 'context': prepared.context})
        r = prepared.reserve()
        refuse('unfinished-phase', lambda: prepare(release, review, a, epoch, raw, receipt))
        answer, identity = seen(owner, r)
        statistics = prepare_existing_statistics(owner, r)
        if statistics['generation_id'] != identity:
            raise AssertionError('statistics identity changed')
        settle(owner, r, identity)
        owner.commit_phase(r, checkpoint(owner, r, answer))
        settlements.append({'receipt': r, 'answer': answer, 'generation_id': identity,
                            'simulated_microusd': 1})
        observations.append({'stage': 'FIRST_COMMITTED', 'snapshot': owner.snapshot()})
        refuse('repeated-completed-phase', prepared.reserve)
        refuse('repeated-statistics', lambda: prepare_existing_statistics(owner, r))

        # Explicit simulated external renewal binds a different exact request.
        # It preserves the first dispatch and charge; no allowance is reset.
        now[0] += timedelta(minutes=2)
        second, second_review, second_raw, second_receipt = materials('AUTHORED-V4-RECORDED-TWO')
        second_receipt['observed_at_utc'] = now[0].isoformat()
        a2 = approval(owner, second, second_review, count=2, now=now[0])
        epoch2 = grant(owner, a2, second, second_review)
        refuse('stale-original-authority', lambda: prepare(release, review, a, epoch, raw, receipt))
        next_request = prepare(second, second_review, a2, epoch2, second_raw, second_receipt)
        payloads.append({'payload': next_request.payload, 'context': next_request.context})
        r2 = next_request.reserve()
        answer2, identity2 = seen(owner, r2)
        prepare_existing_statistics(owner, r2)
        settle(owner, r2, identity2)
        owner.commit_phase(r2, checkpoint(owner, r2, answer2))
        settlements.append({'receipt': r2, 'answer': answer2, 'generation_id': identity2,
                            'simulated_microusd': 1})
        observations.append({'stage': 'RENEWED_SECOND_COMMITTED', 'snapshot': owner.snapshot()})
        refuse('renewal-does-not-allow-repeat', next_request.reserve)
        final = owner.snapshot()
        if final['consumed_microusd']['dispatches'] != 2 or final['consumed_microusd']['total'] != 2:
            raise AssertionError('lifetime counters differ from authored oracle')
        for name, value in (
            ('releases', [release, second]), ('authored-reviews', [review, second_review]),
            ('authored-approvals', [a, a2]), ('observations', observations), ('payloads', payloads),
            ('settlements', settlements), ('refusals', refusals), ('stub-key-accesses', key_reads),
            ('stub-metadata-accesses', metadata_reads)):
            atomic_json(root / (name + '.local.json'), value)
        (root / 'authored-catalog.body').write_bytes(raw)

    index = {str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob('*')) if p.is_file()}
    atomic_json(root / 'index.local.json', {
        'kind': 'AUTHORED_PRODUCTION_ADMISSION_V4_NO_REAL_AUTHORITY', 'artifacts': index,
        'simulated_dispatches': 2, 'simulated_settled_microusd': 2,
        'approval_epochs': 2, 'refusals': len(refusals), 'stub_key_reads': len(key_reads),
        'actual_owner_bootstraps': 0, 'actual_key_reads': 0, 'network_requests': 0,
        'model_calls': 0, 'spend_usd': 0})
    return {'index_path': str(root / 'index.local.json'),
            'index_sha256': sha256_file(root / 'index.local.json'), 'indexed_files': len(index),
            'kind': 'AUTHORED_ONLY', 'actual_owner_bootstraps': 0, 'actual_key_reads': 0,
            'network_requests': 0, 'model_calls': 0, 'spend_usd': 0}


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    print(json.dumps(record(parser.parse_args().directory), sort_keys=True))
