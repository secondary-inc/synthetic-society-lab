#!/usr/bin/env python3
"""One separately reviewed80-call wrapper/configuration batch, preserving all original owner history."""
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_owner_v4 import new_operation_time
from civiclab.owner_budget_v3 import utc
from civiclab.production_compatibility_v4_2_1 import _SafeExecutionFailure,_safe_error_kind
from civiclab.e02.wrapper_crossmodel_v1_owner import validate_packet
from collect_connectivity_billing_once import _credential,_write
from run_e02_continuation_once import read

BASE=ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01'
OLD=ROOT/'data/processed/e02_wrapper_visibility_actual_v1_03'
RUN='e02-wrapper-crossmodel-v1-20261115-01'
EXPORT_SHA='da5abbf754c6787b3073295cd6ebc54e704fa331792635a70c3d287da9cdc861'
EXPORT_BYTES=3033541
CREDENTIAL_READER_SHA='0b5ea3cca5d6d71550985d1da12f9264f223662af7d6429ecab4d88b4cb8f4a7'


def main(packet_sha,caller_sha):
    read(Path(__file__).resolve(),caller_sha)
    raw=read(BASE/'packet.local.json',packet_sha,65000);q=json.loads(raw)
    if canonical_bytes(q)!=raw:raise ExecutionBlocked('canonical exact follow-up packet required')
    q=validate_packet(q,expected_packet_hash=packet_sha)
    e=json.loads(read(OLD/'post-run-owner-export.local.json',EXPORT_SHA,EXPORT_BYTES))
    expected={'head':e['head'],'history_hash':canonical_hash(e['history']),
        'rows_hash':canonical_hash(e['rows']),'study_hash':canonical_hash(e['study']),
        'continuation_hash':canonical_hash(e['continuation']),
        'alignment_hash':canonical_hash(e['alignment_followup']),
        'crossmodel_hash':canonical_hash(e['issue_cue_crossmodel']),
        'recovery_hash':canonical_hash(e['issue_cue_crossmodel_recovery']),
        'wrapper_hash':canonical_hash(e['wrapper_visibility']),
        'claims_hash':canonical_hash(sorted(e['statistics_claims'])),'consumed':e['consumed']}
    if q['policy']['predecessor']!=expected or q['policy']['run_id']!=RUN:
        raise ExecutionBlocked('exact prior complete same-owner state required')
    read(ROOT/'scripts/collect_connectivity_billing_once.py',CREDENTIAL_READER_SHA)
    now=new_operation_time();p=q['policy']
    if not utc(p['valid_from_utc'])<=now or (utc(p['valid_until_utc'])-now).total_seconds()<120:
        raise ExecutionBlocked('fresh finite follow-up window required')
    _write(BASE/'execution-intent.local.json',{'kind':'OWNER_AUTHORIZED_WRAPPER_CROSSMODEL_V1_ONCE',
        'packet_sha256':packet_sha,'caller_sha256':caller_sha,'new_model_POSTs_max':80,
        'new_statistics_GETs_max':240,'catalog_GETs_max':16,'catalog_refresh_before_slots':[10,20,30,40,50,60,70],'POST_retries':0,'new_batch_cap_microusd':200000,
        'cumulative_E02_cap_microusd':1000000,'shared_cap_microusd':5000000,'credit_purchases':0})
    credential=_credential(ROOT);previous=os.environ.get('OPENROUTER_API_KEY')
    os.environ['OPENROUTER_API_KEY']=credential._value
    try:
        from civiclab.e02.wrapper_crossmodel_v1_client import execute_wrapper_crossmodel_v1
        result=execute_wrapper_crossmodel_v1(q,expected_packet_hash=packet_sha,response_provenance='EXPLORATORY_REAL_MODEL')
        return {k:result[k] for k in ('status','model_POST_attempts','statistics_GET_attempts',
            'catalog_GET_attempts','path','analysis_status','snapshot') if k in result}
    finally:
        if previous is None:os.environ.pop('OPENROUTER_API_KEY',None)
        else:os.environ['OPENROUTER_API_KEY']=previous


if __name__=='__main__':
    try:
        if len(sys.argv)!=3:raise ExecutionBlocked('reviewed packet/caller hashes required')
        result=main(sys.argv[1],sys.argv[2])
    except BaseException as error:
        result={'status':'STOPPED','error_type':_safe_error_kind(error),'automatic_retry':False}
        if type(error) is _SafeExecutionFailure:result['diagnostic']=error.diagnostic
    print(json.dumps(result,sort_keys=True))
