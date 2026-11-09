#!/usr/bin/env python3
"""One reviewed continuation; no prior prompt replay, new owner or top-up."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from civiclab.common import canonical_bytes, canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_owner_v4 import new_operation_time
from civiclab.owner_budget_v3 import utc
from civiclab.production_compatibility_v4_2_1 import _SafeExecutionFailure, _safe_error_kind
from civiclab.e02.exploratory_continuation_owner_v1 import validate_bundle
from collect_connectivity_billing_once import _credential, _directory, _write

BASE=ROOT/'data/processed/e02_continuation_20261108_01'
OLD=ROOT/'data/processed/e02_actual_release_20261105_01'
RUN='e02-exploratory-continuation-20261108-01'
EXPORT_SHA='517d18d1595983e5ffbfbc6f0dc5223cf228534904720eefdc9db21aad545a32'
RESPONSE_SHA='2f36a4e37fd46b16c6022f4e4f30cd5c7150feb67ddebffe13013eb86ef02302'
RECEIPT='07c60fe627276fa0be6bf972b9e0faee'
CREDENTIAL_READER_SHA='0b5ea3cca5d6d71550985d1da12f9264f223662af7d6429ecab4d88b4cb8f4a7'


def read(path,expected,limit=2000000):
    _directory(path.parent)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise ExecutionBlocked('bounded regular caller input required')
    with path.open('rb') as f:raw=f.read(limit+1)
    if len(raw)>limit or hashlib.sha256(raw).hexdigest()!=expected:
        raise ExecutionBlocked('reviewed caller input differs')
    return raw


def main(bundle_sha,caller_sha):
    read(Path(__file__).resolve(),caller_sha)
    raw=read(BASE/'bundle.local.json',bundle_sha,50000);b=json.loads(raw)
    if canonical_bytes(b)!=raw:raise ExecutionBlocked('canonical bundle required')
    b=validate_bundle(b,expected_bundle_hash=bundle_sha)
    e=json.loads(read(OLD/'post-run-owner-export.local.json',EXPORT_SHA))
    expected={'head':e['head'],'history_hash':canonical_hash(e['history']),
        'rows_hash':canonical_hash(e['rows']),'study_hash':canonical_hash(e['study']),
        'claims_hash':canonical_hash(sorted(e['statistics_claims']))}
    if (b['predecessor']!=expected or b['packet']['policy']['run_id']!=RUN
        or b['recovery']['receipt']!=RECEIPT
        or b['recovery']['response_sha256']!=RESPONSE_SHA):
        raise ExecutionBlocked('exact original stopped run required')
    if (read(OLD/'retained-journal'/f'{RECEIPT}-response.json',RESPONSE_SHA)
        !=canonical_bytes(b['recovery']['response'])
        or read(BASE/'billing-recovery/statistics.json',b['recovery']['statistics_sha256'])
        !=canonical_bytes(b['recovery']['statistics'])):
        raise ExecutionBlocked('exact retained recovery evidence required')
    read(ROOT/'scripts/collect_connectivity_billing_once.py',CREDENTIAL_READER_SHA)
    now=new_operation_time();p=b['packet']['policy']
    if not utc(p['valid_from_utc'])<=now or (utc(p['valid_until_utc'])-now).total_seconds()<120:
        raise ExecutionBlocked('fresh finite continuation window required')
    _write(BASE/'execution-intent.local.json',{'kind':'OWNER_AUTHORIZED_E02_CONTINUATION_ONCE',
        'bundle_sha256':bundle_sha,'caller_sha256':caller_sha,'new_model_POSTs_max':16,
        'new_statistics_GETs_max':48,'POST_retries':0,'credit_purchases':0})
    credential=_credential(ROOT);previous=os.environ.get('OPENROUTER_API_KEY')
    os.environ['OPENROUTER_API_KEY']=credential._value
    try:
        from civiclab.e02.exploratory_continuation_v1 import execute_continuation
        result=execute_continuation(b,expected_bundle_hash=bundle_sha,
            response_provenance='EXPLORATORY_REAL_MODEL')
        return {k:result[k] for k in ('status','model_POST_attempts','statistics_GET_attempts',
            'catalog_GET_attempts','path','analysis_status','snapshot') if k in result}
    finally:
        if previous is None:os.environ.pop('OPENROUTER_API_KEY',None)
        else:os.environ['OPENROUTER_API_KEY']=previous


if __name__=='__main__':
    try:
        if len(sys.argv)!=3:raise ExecutionBlocked('reviewed bundle/caller hashes required')
        result=main(sys.argv[1],sys.argv[2])
    except BaseException as error:
        result={'status':'STOPPED','error_type':_safe_error_kind(error),'automatic_retry':False}
        if type(error) is _SafeExecutionFailure:result['diagnostic']=error.diagnostic
    print(json.dumps(result,sort_keys=True))
