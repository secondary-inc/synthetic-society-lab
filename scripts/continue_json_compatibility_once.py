"""User-terminal-only continuation of the approved one-request check. No retry."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
PACKET = 'configs/json_compatibility_continuation_v1_terminal_packet.json'
HANDOFF = 'data/processed/compatibility_operator_handoff/continuation-20261103-02'
RUN_ID = 'compatibility-20261103-gpt41nano-02'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def read_ref(ref):
    relative = Path(ref['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('unsafe reference')
    path = ROOT / relative
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('reference alias')
    with path.open('rb') as stream: raw = stream.read(4*1024*1024+1)
    if len(raw)>4*1024*1024 or sha(raw)!=ref['sha256']:
        raise ValueError('reference changed or oversized')
    if 'bytes' in ref and len(raw)!=ref['bytes']:
        raise ValueError('reference size changed')
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--confirm-rotated-dedicated-key', action='store_true', required=True)
    args = parser.parse_args()
    if not args.confirm_rotated_dedicated_key or Path.cwd()!=ROOT:
        raise ValueError('run from project with newly rotated dedicated key')
    packet = read_ref({'path':PACKET,'sha256':args.packet_sha256})
    if packet['launcher_sha256']!=sha(Path(__file__).read_bytes()):
        raise ValueError('launcher differs from reviewed packet')
    release = read_ref(packet['release'])
    review = read_ref(packet['foundation_review'])
    executor = read_ref(packet['executor_review'])
    launcher_review = read_ref(packet['launcher_review'])
    stop = read_ref(packet['original_stop'])
    read_ref(packet['original_stop_audit'])
    if (launcher_review['status']!='PASS_TERMINAL_CONTINUATION_LAUNCHER_V1'
        or launcher_review['launcher_sha256']!=packet['launcher_sha256']):
        raise ValueError('independent launcher review absent')
    from civiclab.common import canonical_hash, atomic_json
    from civiclab.production_owner_v4 import ProductionOwnerV4, request_binding
    from civiclab.production_admission_v4 import make_context
    from civiclab.production_compatibility_v4_1 import (
        execution_contract, validate_execution_release, execute_compatibility)
    RH, EH = canonical_hash(review), canonical_hash(executor)
    if (canonical_hash(execution_contract())!=packet['contract_sha256']
        or RH!=packet['foundation_canonical_sha256']
        or EH!=packet['executor_canonical_sha256']
        or release['request']['run_id']!=RUN_ID):
        raise ValueError('exact execution bindings changed')
    if any(stop[k]!=0 for k in ('actual_charges','actual_model_POST_attempts',
                               'actual_statistics_GET_attempts','actual_statistics_claims')):
        raise ValueError('original attempt was not a zero-dispatch stop')
    for name, pin in {**stop['private_evidence_files'], **stop['run_files']}.items():
        read_ref({'path':name, **pin})
    original_journal = ROOT / stop['run_path']
    if {str(p.relative_to(ROOT)) for p in original_journal.iterdir()}!=set(stop['run_files']):
        raise ValueError('original journal membership changed')
    original_approval = read_ref({'path':stop['private_operator_handoff']+'/approval.local.json',
                                 **stop['private_evidence_files'][stop['private_operator_handoff']+'/approval.local.json']})
    owner = ProductionOwnerV4.open()  # Never initialize another owner.
    before = owner.snapshot()
    zero = {'total':0,'modules':{'E01':0,'E02':0},'dispatches':0,
            'module_dispatches':{'E01':0,'E02':0}}
    if (before['consumed_microusd']!=zero or before['charges']
        or before['statistics_claimed_receipts']
        or before['approval_hash']!=canonical_hash(original_approval)
        or before['approval']!=original_approval):
        raise ValueError('original owner state changed; no continuation')
    caps = {'total_microusd':1000,'module_microusd':{'E01':0,'E02':1000},
            'total_dispatches':1,'module_dispatches':{'E01':0,'E02':1}}
    if any(original_approval[k]!=v for k,v in caps.items()):
        raise ValueError('original lifetime limits differ')
    now = datetime.now(timezone.utc)
    end = datetime.fromisoformat(release['interpretation']['valid_until_utc'])
    if now>=end: raise ValueError('reviewed price window expired')
    approval = deepcopy(original_approval)
    approval.update(approval_id=uuid.uuid4().hex,
        previous_approval_hash=before['approval_hash'],review_hash=RH,
        release_hash=canonical_hash(release),valid_from_utc=(now-timedelta(seconds=1)).isoformat(),
        valid_until_utc=end.isoformat())
    terms, request = release['terms'], release['request']
    proof = {'url':'https://openrouter.ai/api/v1/models/'+terms['model']+'/endpoints',
             'body_sha256':terms['initial_catalog_sha256'],'observed_at_utc':now.isoformat(),
             'metadata_semantic_hash':terms['metadata_semantic_hash']}
    context = make_context(release,'0'*64,proof)
    envelope = request['envelope']
    approval['allowed_plans'] = {request['plan_hash']:{'module':'E02',
        'terms_sha256':canonical_hash(terms),'max_tokens':envelope['max_tokens'],
        'max_input_token_bound':envelope['input_token_bound'],
        'request_binding_hash':request_binding(context)}}
    AH = canonical_hash(approval)
    validate_execution_release(release,review,approval,executor,
        expected_review_hash=RH,expected_approval_hash=AH,expected_executor_review_hash=EH)
    journal = ROOT/'data/processed/compatibility_runs'/RUN_ID
    handoff = ROOT/HANDOFF
    for path in (journal,handoff,*handoff.parents):
        if path.is_symlink(): raise ValueError('continuation path alias')
    if journal.exists(): raise FileExistsError('continuation journal exists; no retry')
    handoff.mkdir(mode=0o700,exist_ok=False)  # One terminal invocation wins.
    stage = 'RENEW_EXISTING_ABSOLUTE_APPROVAL'
    try:
        atomic_json(handoff/'before-owner.local.json',before)
        atomic_json(handoff/'human-continuation.local.json',{
            'authority':'DIRECT_USER_TERMINAL_COMMAND_REQUEST_AND_EXECUTION',
            'rotated_dedicated_key_asserted_by_terminal_flag':True,
            'key_read_by_launcher':False,'lifetime_microusd':1000,
            'lifetime_dispatches':1,'automatic_retry':False,'credit_purchase':False})
        atomic_json(handoff/'approval.local.json',approval)
        owner.grant_operator_authorization(approval,expected_approval_hash=AH,
            release=release,review=review,expected_review_hash=RH)
        stage = 'ONE_REVIEWED_EXECUTOR_CALL'
        # Only the reviewed factory reads OPENROUTER_API_KEY, after its gates.
        result = execute_compatibility(ROOT,release,review,approval,executor,
            expected_review_hash=RH,expected_approval_hash=AH,expected_executor_review_hash=EH)
        atomic_json(handoff/'result.local.json',result)
        print(json.dumps(result['summary'],sort_keys=True))
    except BaseException as error:
        atomic_json(handoff/'failure.local.json',{'status':'STOPPED_NO_RETRY',
            'stage':stage,'error_type':type(error).__name__})
        print(json.dumps({'status':'STOPPED_NO_RETRY','stage':stage,
                          'error_type':type(error).__name__}))
        return 1
    finally:
        atomic_json(handoff/'after-owner.local.json',owner.snapshot())
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status':'REFUSED_NO_RETRY','error_type':type(error).__name__}))
        raise SystemExit(1) from None
