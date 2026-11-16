"""Two bounded public catalog GETs; no key, live owner, or inference access."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/processed/e02_wrapper_crossmodel_v1_20261115_price_01'
sys.path.insert(0, str(ROOT / 'src'))
from civiclab.common import canonical_bytes, canonical_hash
from civiclab.production_admission_v4 import _fetch_public_catalog
from civiclab.e02.crossmodel_price_v1 import contract_from_catalog

EXPORT = ROOT / 'data/processed/e02_wrapper_visibility_actual_v1_03/post-run-owner-export.local.json'
EXPORT_SHA = 'da5abbf754c6787b3073295cd6ebc54e704fa331792635a70c3d287da9cdc861'
EXPORT_BYTES = 3033541


def write(name, value, raw=False):
    body = value if raw else canonical_bytes(value)
    with os.fdopen(os.open(BASE / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as out:
        out.write(body)
        out.flush()
        os.fsync(out.fileno())


def main():
    if any(p.is_symlink() for p in (BASE, *BASE.parents)):
        raise RuntimeError('scope alias')
    BASE.mkdir(mode=0o700, exist_ok=False)
    write('intent.json', {'kind': 'PUBLIC_CROSSMODEL_PRICE_PREPARATION',
                         'GET_max': 2, 'retries': 0, 'body_bytes_per_GET_max': 2000000,
                         'overflow_probe_bytes_per_GET_max': 1,
                         'socket_seconds': 15, 'request_seconds': 30,
                         'credential_reads': 0, 'live_owner_access': 0, 'model_POSTs': 0,
                         'API_cost_USD': 0, 'runtime_catalog_GETs_separate': 16})
    attempts = 0
    try:
        with EXPORT.open('rb') as stream:
            raw = stream.read(EXPORT_BYTES + 1)
        if len(raw) != EXPORT_BYTES or hashlib.sha256(raw).hexdigest() != EXPORT_SHA:
            raise RuntimeError('closed predecessor differs')
        old = json.loads(raw)['issue_cue_crossmodel_recovery']['packet']['price_release']
        evidence = json.loads((ROOT / 'reports/INDEPENDENT_AUDIT_E02_CROSSMODEL_PRICE_METADATA_COMPONENTS_20261110.json').read_bytes())['evidence']
        for ref in evidence:
            with (ROOT / ref['file']).open('rb') as stream:
                body = stream.read(ref['bytes'] + 1)
            if len(body) != ref['bytes'] or hashlib.sha256(body).hexdigest() != ref['sha256']:
                raise RuntimeError('retained interpretation evidence differs')
        releases, quotes, unchanged = {}, {}, {}
        for role in ['A', 'B']:
            write('GET-' + role + '-intent.json', {'role': role, 'model': old[role]['terms']['model'], 'ordinal': attempts + 1})
            attempts += 1
            raw, receipt = _fetch_public_catalog(old[role]['terms']['model'])
            write('catalog-' + role + '.json', raw, raw=True)
            write('receipt-' + role + '.json', receipt)
            now = datetime.now(timezone.utc)
            decision = deepcopy(old[role]['interpretation'])
            decision.update(catalog_sha256=hashlib.sha256(raw).hexdigest(),
                            valid_from_utc=now.isoformat(),
                            valid_until_utc=(now + timedelta(hours=24)).isoformat())
            terms = contract_from_catalog(raw, decision, expected_decision_hash=canonical_hash(decision))
            releases[role] = dict(kind='LIMITED_PILOT_PRICE_RELEASE_V1', terms=terms, interpretation=decision)
            amount = (Decimal(terms['input_usd_per_token']) * 8192 +
                      Decimal(terms['output_usd_per_token']) * 256 + Decimal(terms['request_fee_usd'])) * 1000000
            quotes[role] = int(amount.to_integral_value(rounding=ROUND_CEILING))
            if quotes[role] > 1785:
                raise RuntimeError('per-call research ceiling')
            unchanged[role] = terms['metadata_semantic_hash'] == old[role]['terms']['metadata_semantic_hash']
        maximum = sum(quotes.values()) * 40
        if maximum > 142800 or maximum > 200000:
            raise RuntimeError('batch ceiling')
        write('price-release.candidate.json', releases)
        result = dict(status='PRICE_CANDIDATE_REQUIRES_INDEPENDENT_PARTICULAR_REVIEW',
                      preparation_GETs=attempts, inference_calls=0, API_cost_USD=0,
                      price_release_sha256=canonical_hash(releases),
                      maximum_microusd_per_call=quotes, maximum_batch_microusd=maximum,
                      semantics_unchanged_from_prior=unchanged,
                      prior_evidence=evidence,
                      missing_components='Inherited explicit conditional interpretations, not observed zero fees.',
                      current_dispatch='Requires fresh matching catalog within 900 seconds before each admitted phase.')
        write('TERMINAL.json', result)
        print(json.dumps({k: v for k, v in result.items() if k != 'prior_evidence'}, sort_keys=True))
    except BaseException as error:
        write('TERMINAL.json', dict(status='STOPPED_NO_RETRY', error_type=type(error).__name__,
                                   preparation_GETs=attempts, inference_calls=0, API_cost_USD=0))
        raise


if __name__ == '__main__':
    main()
