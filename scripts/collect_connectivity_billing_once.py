#!/usr/bin/env python3
"""One separately approved billing-evidence GET; never inference or settlement.

Pending independent exact-code/caller review and explicit owner authorization.
Canonical retained metadata are not HTTP wire bytes. Nothing here reads or
modifies the original financial owner, reservations, claims or checkpoints.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'src') not in sys.path:sys.path.insert(0,str(ROOT/'src'))
from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from civiclab.production_compatibility_transport_v4_2 import _CompatibilityTransportV4_2,_SafeTransportFailure
from civiclab.production_compatibility_v4_2_1 import _no_secret,_cost,_observed_cost,_auxiliary_observation,_safe_error_kind

# Identity supplied by the lead from its finite retained-journal observation.
# No original-owner path is opened by this script. The exact original request
# envelope and evidence byte hashes are externally supplied, not inferred.
MANIFEST={'kind':'CONNECTIVITY_BILLING_EVIDENCE_ONCE_V1',
    'run_id':'compatibility-additional-20261105-01',
    'receipt':'ddf80d6eb0222d75ad3ff5e42253534d',
    'generation_id':'gen-1793870664-fiuZqWWWJpQTEUx4ZrXe',
    'model':'openai/gpt-4.1-nano','provider':'Azure','input_token_bound':2276,
    'output_token_bound':32,'observed_response_cost_microusd':7,
    'source_event_sha256':'22dec282dfbe2f3b0331c9e8b0a9af12fb2becd802c1387d541af3da66e3530f',
    'source_request_sha256':'44969824c6bcdb5832cdfea8917301baa737f280f0496235a685db93ea97673b',
    'request_hash':'21215033b9732a8eb4c1019f1db76abe5790ad8feadaa47fb0b08a33528cb296'}


def _manifest(value):
    value=json.loads(canonical_bytes(value))
    if type(value) is not dict or set(value)!=set(MANIFEST) or value['kind']!=MANIFEST['kind']:
        raise ExecutionBlocked('closed evidence manifest required')
    for key,pattern in [('run_id',r'[A-Za-z0-9_-]{1,128}'),('receipt',r'[a-f0-9]{32}'),
                        ('generation_id',r'gen-[A-Za-z0-9-]{1,124}'),('source_event_sha256',r'[a-f0-9]{64}'),
                        ('source_request_sha256',r'[a-f0-9]{64}'),('request_hash',r'[a-f0-9]{64}')]:
        if type(value[key]) is not str or re.fullmatch(pattern,value[key]) is None:
            raise ExecutionBlocked('safe fixed evidence identity required')
    if value!=MANIFEST:raise ExecutionBlocked('only the exact original generation/request manifest is allowed')
    if value['model']!='openai/gpt-4.1-nano' or value['provider']!='Azure':
        raise ExecutionBlocked('fixed original model/provider required')
    for key,limit in [('input_token_bound',100000),('output_token_bound',32),('observed_response_cost_microusd',1000000)]:
        if type(value[key]) is not int or not 0<=value[key]<=limit:
            raise ExecutionBlocked('exact bounded native/cost manifest required')
    if value['input_token_bound']<1 or value['output_token_bound']!=32:
        raise ExecutionBlocked('original input envelope and 32 output ceiling required')
    return value


def contract(manifest,root=ROOT):
    modules=('common','model','owner_budget_v3','live_billing_v2','production_owner_v4',
             'production_admission_v4','production_price_v4','openrouter_http_v2',
             'production_compatibility_transport_v4_2','production_compatibility_v4_2_1')
    files=[Path(__file__).resolve()]+[ROOT/'src/civiclab'/f'{name}.py' for name in modules]
    return {'kind':'ONE_BILLING_GET_CONTRACT_V1','manifest':_manifest(manifest),
            'pins':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'credential_source':str(Path(root)/'.env'),
            'output_directory':str(Path(root)/'data/processed/connectivity_billing_once'/manifest['run_id']),
            'GETs':1,'POSTs':0,'retries':0,'HTTP_seconds':30,'socket_seconds':15,
            'owner_reads':0,'owner_writes':0,'settlement':False,'provider_representation':'CANONICAL_PARSED_PROVIDER_OBJECT_V1'}


def _directory(path):
    for p in (path,*path.parents):
        if not stat.S_ISDIR(p.lstat().st_mode):raise ExecutionBlocked('real directory ancestry required')


def _write(path,value):
    raw=canonical_bytes(value)
    if len(raw)>2000000:raise ExecutionBlocked('bounded canonical artifact required')
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def _credential(root):
    if subprocess.run(['git','-C',str(root),'check-ignore','--quiet','--','.env'],
                      stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode!=0:
        raise ExecutionBlocked('credential source must be Git ignored')
    path=root/'.env';fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        metadata=os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid!=os.getuid() or metadata.st_mode&0o077 or metadata.st_size>65536:
            raise ExecutionBlocked('private owned bounded credential file required')
        raw=stream.read(65537)
    if len(raw)>65536:raise ExecutionBlocked('credential file grew beyond bound')
    values=[]
    for line in raw.decode('utf-8').splitlines():
        match=re.match(r'^\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*?)\s*$',line)
        if match:
            parsed=shlex.split(match[1],comments=True,posix=True)
            if len(parsed)!=1:raise ExecutionBlocked('one literal credential value required')
            values.append(parsed[0])
    if len(values)!=1 or not 16<=len(values[0])<=4096 or re.fullmatch(r'sk-or-v1-[A-Za-z0-9_-]+',values[0]) is None:
        raise ExecutionBlocked('single valid literal credential assignment required')
    return _Credential(values[0])


def _transport(credential):return _CompatibilityTransportV4_2(credential)


def validate_statistics(response,manifest):
    data=response.get('data') if type(response) is dict else None
    if type(data) is not dict or data.get('id')!=manifest['generation_id']:
        raise ExecutionBlocked('generation billing identity unverified')
    if data.get('model')!=manifest['model'] or data.get('provider_name')!=manifest['provider'] or data.get('is_byok') is not False:
        raise ExecutionBlocked('serving identity or billing mode unverified')
    for key,bound in [('native_tokens_prompt',manifest['input_token_bound']),
                      ('native_tokens_completion',manifest['output_token_bound']),('native_tokens_reasoning',0)]:
        if type(data.get(key)) is not int or not 0<=data[key]<=bound:
            raise ExecutionBlocked('native usage unverified')
    auxiliary,valid=_auxiliary_observation(data)
    if not valid:raise ExecutionBlocked('unsupported auxiliary activity')
    amount=_cost(data.get('total_cost'))
    return {'status':'VERIFIED_BILLING_EVIDENCE_ONLY','reported_provider_cost_microusd':amount,
            'model':data['model'],'provider':data['provider_name'],'auxiliary':auxiliary,
            'response_cost_observation_microusd':manifest['observed_response_cost_microusd'],
            'reported_cost_matches_response_observation':amount==manifest['observed_response_cost_microusd'],
            'reported_cost_exceeds_original_hold':amount>340,
            'quality_verified':False,'financial_state_changed':False,'holds_released':False}


def collect_once(manifest,*,expected_contract_hash,owner_approved=False,root=ROOT):
    if owner_approved is not True:raise ExecutionBlocked('separate explicit approval for one additional billing GET required')
    root=Path(root);m=_manifest(manifest);c=contract(m,root)
    if canonical_hash(c)!=expected_contract_hash:raise ExecutionBlocked('externally reviewed exact contract required')
    _directory(root);base=root/'data/processed/connectivity_billing_once'
    current=root
    for part in ('data','processed','connectivity_billing_once'):
        current=current/part
        if not current.exists() and not current.is_symlink():current.mkdir(mode=0o700)
        _directory(current)
    output=base/m['run_id'];output.mkdir(mode=0o700,exist_ok=False)
    _write(output/'intent.local.json',{'contract_hash':expected_contract_hash,'manifest':m,'operation':'ONE_GET_NO_RETRY_NO_OWNER_WRITE'})
    attempts=0;body='MISSING';credential=None;observed_cost=None
    try:
        credential=_credential(root);transport=_transport(credential)
        attempts=1;response=transport.statistics(m['generation_id'])
        data=response.get('data') if type(response) is dict else None
        # A safe scalar belonging to this exact generation survives unrelated
        # privacy/storage failures. Credential-bearing monetary values refuse
        # here, before any body hashing or persistence.
        if (type(data) is dict and type(data.get('id')) is str and
            data['id']==m['generation_id'] and data.get('total_cost') is not None):
            try:observed_cost=_observed_cost(data['total_cost'],credential)
            except (ValueError,TypeError,ArithmeticError):pass  # Invalid cost is not an observation.
        _no_secret(response,credential)
        _write(output/'statistics.local.json',response);body='RETAINED_CANONICAL_COMPLETE'
        diagnostic=validate_statistics(response,m)
    except BaseException as error:
        diagnostic={'status':'STOPPED_NO_RETRY','error_type':_safe_error_kind(error)}
        if type(error) is _SafeTransportFailure:diagnostic['transport']=error.diagnostic()
        if isinstance(error,(KeyboardInterrupt,SystemExit)):
            diagnostic['status']='CANCELLED_NO_RETRY'
    diagnostic.update(GET_attempts=attempts,POSTs=0,provider_body=body,
                      provider_representation='CANONICAL_PARSED_PROVIDER_OBJECT_V1',
                      financial_state_changed=False,original_hold_microusd=340,
                      observed_total_cost_microusd=observed_cost,
                      observed_cost_exceeds_original_hold=(observed_cost>340 if observed_cost is not None else None),
                      invoice_or_quality_adoption=False,original_HTTP_wire_bytes_retained=False)
    _write(output/'diagnostic.local.json',diagnostic)
    return diagnostic


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approve-one-billing-get',action='store_true')
    parser.add_argument('--contract-sha256',required=True)
    args=parser.parse_args()
    try:result=collect_once(MANIFEST,expected_contract_hash=args.contract_sha256,owner_approved=args.approve_one_billing_get)
    except BaseException:
        print('Billing evidence collector refused before completion; no automatic retry.');return 1
    print(json.dumps(result,sort_keys=True));return 0 if result['status']=='VERIFIED_BILLING_EVIDENCE_ONLY' else 1


if __name__=='__main__':raise SystemExit(main())
