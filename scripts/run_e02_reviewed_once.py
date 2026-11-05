#!/usr/bin/env python3
"""Finite caller; requires independent exact packet/caller release before use.

Uses the owner's existing run-now/$5 authorization, never a new budget. The
fixed run permits at most 32 E02 model requests and a $1 study subset. Never
retry this caller or reset its intent, journals, historical rows or claims.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'src') not in sys.path:sys.path.insert(0,str(ROOT/'src'))
from civiclab.common import canonical_bytes, canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.owner_budget_v3 import utc
from civiclab.production_owner_v4 import new_operation_time
from civiclab.production_compatibility_v4_2_1 import _SafeExecutionFailure, _safe_error_kind
from civiclab.e02.exploratory_owner_v1 import validate_packet, recovery_mode
from civiclab.e02.exploratory_live_client_v1 import execute_authored
from collect_connectivity_billing_once import _credential, _directory, _write

RUN='e02-exploratory-live-20261105-01'
BASE=ROOT/'data/processed/e02_actual_release_20261105_01'
SOURCES={
    'export':('data/processed/compatibility_operator_handoff/additional-release-20261105-01/post-stop-owner-export.local.json',
        '54f13061a4d0191fcd685358a1f1c789ecd80ba5cbfca7a1734da54a97e57cf9'),
    'statistics':('data/processed/connectivity_billing_once/compatibility-additional-20261105-01/statistics.local.json',
        'af51fa8c450e25b6801622d3804a22e5132ad7dbf819437b8597223cfe85e33c'),
    'audit':('reports/INDEPENDENT_AUDIT_CONNECTIVITY_BILLING_ACTUAL_20261105.json',
        '0a8f142cfd746ba436a6a8fa3ab40c750aac18e88838125ff2d3e91a794df960'),
    'identity':('data/processed/connectivity_billing_once/public-metadata-20261105-01/model.json',
        'e234cd7362756b3bfe4411471f6966bec6a2be7ef81bff131f6a4c30ea9164be'),
    'credential_reader':('scripts/collect_connectivity_billing_once.py',
        '0b5ea3cca5d6d71550985d1da12f9264f223662af7d6429ecab4d88b4cb8f4a7')}


def _read(path,expected,limit=524288):
    _directory(path.parent)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise ExecutionBlocked('bounded fixed reviewed file required')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit or hashlib.sha256(raw).hexdigest()!=expected:
        raise ExecutionBlocked('reviewed source bytes differ')
    return raw


def main(expected_packet_sha256,expected_caller_sha256):
    # Expected hashes must come from independent particular release, not from
    # recomputing a changed file at execution time.
    _read(Path(__file__).resolve(),expected_caller_sha256)
    raw=_read(BASE/'packet.local.json',expected_packet_sha256)
    packet=json.loads(raw)
    if canonical_bytes(packet)!=raw:raise ExecutionBlocked('canonical packet required')
    packet=validate_packet(packet,expected_packet_hash=expected_packet_sha256)
    p=packet['policy'];r=p.get('recovery',{})
    if not recovery_mode(p) or p['run_id']!=RUN:
        raise ExecutionBlocked('exact reviewed recovery run required')
    evidence={name:_read(ROOT/path,sha) for name,(path,sha) in SOURCES.items()}
    export=json.loads(evidence['export'])
    predecessor={'header_hash':canonical_hash(export['header']),'head':export['head'],
        'history_hash':canonical_hash(export['history']),'active_approval_hash':export['active_approval_hash'],
        'rows_hash':canonical_hash(export['rows']),
        'statistics_claims_hash':canonical_hash(sorted(export['statistics_claims']))}
    if (p['predecessor']!=predecessor or r['source_export_sha256']!=SOURCES['export'][1]
        or r['evidence_audit_sha256']!=SOURCES['audit'][1]
        or r['model_identity_source_sha256']!=SOURCES['identity'][1]
        or r['statistics_raw_sha256']!=SOURCES['statistics'][1]
        or canonical_bytes(r['statistics'])!=evidence['statistics']):
        raise ExecutionBlocked('recovery provenance differs from exact retained evidence')
    now=new_operation_time()
    if (not utc(p['valid_from_utc'])<=now
        or (utc(p['valid_until_utc'])-now).total_seconds()<120):
        raise ExecutionBlocked('full phase unavailable in reviewed window')
    _write(BASE/'execution-intent.local.json',{'kind':'OWNER_AUTHORIZED_ONE_E02_PILOT_EXECUTION',
        'packet_sha256':expected_packet_sha256,'caller_sha256':expected_caller_sha256,
        'response_provenance':'EXPLORATORY_REAL_MODEL','retries':0,'purchases':0})
    credential=_credential(ROOT)
    previous=os.environ.get('OPENROUTER_API_KEY')
    os.environ['OPENROUTER_API_KEY']=credential._value
    try:
        result=execute_authored(packet,expected_packet_hash=expected_packet_sha256,
                               response_provenance='EXPLORATORY_REAL_MODEL')
        return {k:result[k] for k in ('status','model_POST_attempts','statistics_GET_attempts',
            'catalog_GET_attempts','path','analysis_status','snapshot') if k in result}
    finally:
        if previous is None:os.environ.pop('OPENROUTER_API_KEY',None)
        else:os.environ['OPENROUTER_API_KEY']=previous


if __name__=='__main__':
    try:
        if len(sys.argv)!=3:raise ExecutionBlocked('exact reviewed packet and caller hashes required')
        summary=main(sys.argv[1],sys.argv[2])
    except BaseException as error:
        summary={'status':'STOPPED_NO_RETRY','error_type':_safe_error_kind(error),'automatic_retry':False}
        if type(error) is _SafeExecutionFailure:summary['diagnostic']=error.diagnostic
    print(json.dumps(summary,sort_keys=True))
