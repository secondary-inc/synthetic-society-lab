#!/usr/bin/env python3
"""Bounded metadata recovery for one already dispatched E02 generation.

Never sends a model prompt or opens/mutates the financial owner. Preserves the
original journal and full hold. The caller must supply the reviewed contract.
"""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from civiclab.common import canonical_bytes, canonical_hash, sha256_file
from civiclab.model import ExecutionBlocked
from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
from civiclab.production_compatibility_v4_2_1 import _no_secret, _safe_error_kind, _usage_bounds, _observed_cost
from civiclab.e02.exploratory_owner_v1 import code_contract
from civiclab.e02.exploratory_metadata_v1 import normalize_statistics, response_model_allowed
from civiclab.e02.exploratory_live_client_v1 import _no_provider_reasoning, _no_unsupported_response_activity
from civiclab.e02.exploratory_response_v1 import parse_survey_response
from collect_connectivity_billing_once import _credential, _transport, _directory, _write

RECEIPT = '07c60fe627276fa0be6bf972b9e0faee'
GENERATION = 'gen-1793873410-17Xn9RsYhfAyAy5B0lou'
SOURCE = 'data/processed/e02_actual_release_20261105_01'
EXPORT_SHA = '517d18d1595983e5ffbfbc6f0dc5223cf228534904720eefdc9db21aad545a32'
RESPONSE_SHA = '2f36a4e37fd46b16c6022f4e4f30cd5c7150feb67ddebffe13013eb86ef02302'
OUTPUT = 'data/processed/e02_continuation_20261108_01/billing-recovery'


def contract():
    return {'kind': 'E02_EXISTING_GENERATION_BILLING_RECOVERY_V1',
        'pins': {str(Path(__file__).relative_to(ROOT)): sha256_file(Path(__file__)),
                 'scripts/collect_connectivity_billing_once.py': sha256_file(ROOT/'scripts/collect_connectivity_billing_once.py')},
        'base_code': code_contract(), 'receipt': RECEIPT, 'generation_id': GENERATION,
        'export_sha256': EXPORT_SHA, 'response_sha256': RESPONSE_SHA,
        'maximum_GETs': 3, 'POSTs': 0, 'retry_statuses': [404], 'retry_waits_seconds': [10, 20],
        'deadline_seconds': 150, 'HTTP_seconds': 30, 'owner_writes': 0,
        'output': OUTPUT, 'hold_microusd': 788}


def _read(path, expected):
    _directory(path.parent)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2000000:
        raise ExecutionBlocked('bounded regular evidence required')
    with path.open('rb') as stream:
        raw = stream.read(2000001)
    if len(raw)>2000000 or hashlib.sha256(raw).hexdigest()!=expected:
        raise ExecutionBlocked('retained evidence hash differs')
    result=json.loads(raw)
    if canonical_bytes(result)!=raw: raise ExecutionBlocked('canonical evidence required')
    return result


def evidence(root):
    export=_read(root/SOURCE/'post-run-owner-export.local.json', EXPORT_SHA)
    response=_read(root/SOURCE/'retained-journal'/f'{RECEIPT}-response.json', RESPONSE_SHA)
    row=export['rows'][RECEIPT]
    parsed=parse_survey_response(response)
    output={'status': parsed['status'], 'answer': parsed['answer'], 'response_raw_sha256': RESPONSE_SHA}
    if (row['status']!='UNCERTAIN' or row['reserved']!=788 or row['charged']!=788
        or row['observed_cost']!=54 or row['generation_id']!=GENERATION
        or response.get('id')!=GENERATION or canonical_hash(output)!=row['output_hash']
        or export['consumed']['total']!=2136 or export['consumed']['dispatches']!=18
        or export['unfinished']!=3):
        raise ExecutionBlocked('original stopped generation/hold differs')
    _no_provider_reasoning(response); _no_unsupported_response_activity(response)
    _usage_bounds(response.get('usage'),row['context']['envelope'])
    if not response_model_allowed(response.get('model'), row['context']['terms']['model']):
        raise ExecutionBlocked('original response model differs')
    return row,response


def collect(expected_contract_hash, *, root=ROOT):
    if canonical_hash(contract())!=expected_contract_hash:
        raise ExecutionBlocked('reviewed collector contract differs')
    root=Path(root); row,response=evidence(root)
    directory=root/OUTPUT; _directory(directory.parent)
    directory.mkdir(mode=0o700,exist_ok=False)
    _write(directory/'intent.json', {'contract_sha256': expected_contract_hash,
        'generation_id': GENERATION, 'max_GETs':3, 'POSTs':0})
    attempts=0; retained=False; observed_cost=None; started=time.monotonic(); maximum=started
    def gate(reserve=0):
        nonlocal maximum
        now=time.monotonic()
        if now<maximum or not 0<=now-started<150-reserve:
            raise ExecutionBlocked('billing recovery deadline')
        maximum=now
    try:
        credential=_credential(root); transport=_transport(credential)
        for i in range(3):
            gate(30)
            _write(directory/f'get-{i+1}-intent.json', {'generation_id':GENERATION,'attempt':i+1})
            gate(30); attempts+=1
            try:
                result=transport.statistics(GENERATION)
            except _SafeTransportFailure as error:
                d=error.diagnostic(); _write(directory/f'get-{i+1}-failure.json',d)
                if d['http_status']!=404 or d['close_failed'] or i==2: raise
                wait=(10,20)[i]
                for _ in range(wait):
                    gate(31);time.sleep(1)
                continue
            data=result.get('data') if type(result) is dict else None
            if (type(data) is dict and type(data.get('id')) is str
                and data['id']==GENERATION and data.get('total_cost') is not None):
                try:observed_cost=_observed_cost(data['total_cost'],credential)
                except (ValueError,TypeError,ArithmeticError):pass
            gate(); _no_secret(result,credential)
            _write(directory/'statistics.json',result);retained=True
            c=row['context']; e=c['envelope']
            normalized=normalize_statistics(result.get('data'),generation_id=GENERATION,
                requested_model=c['terms']['model'],reported_provider=c['terms']['reported_provider'],
                input_bound=e['input_token_bound'],output_bound=e['max_tokens'],reserved_microusd=row['reserved'])
            if Decimal(str(response['usage']['cost']))!=Decimal(str(result['data']['total_cost'])):
                raise ExecutionBlocked('response and generation cost differ')
            diagnostic={'status':'VERIFIED_BILLING_EVIDENCE_ONLY','billing':normalized['billing'],
                'telemetry':normalized['telemetry'],'original_response_sha256':RESPONSE_SHA,
                'statistics_sha256':canonical_hash(result)}
            break
    except BaseException as error:
        diagnostic={'status':'STOPPED','error_type':_safe_error_kind(error)}
        if type(error) is _SafeTransportFailure:diagnostic['transport']=error.diagnostic()
        if isinstance(error,(KeyboardInterrupt,SystemExit)):diagnostic['status']='CANCELLED'
    diagnostic.update(GET_attempts=attempts,POSTs=0,body_retained=retained,
        financial_state_changed=False,original_hold_microusd=788,
        observed_total_cost_microusd=observed_cost,
        observed_cost_exceeds_hold=(observed_cost>788 if observed_cost is not None else None))
    _write(directory/'result.json',diagnostic)
    return diagnostic


if __name__=='__main__':
    try:
        if len(sys.argv)!=2:raise ExecutionBlocked('reviewed contract hash required')
        result=collect(sys.argv[1])
    except BaseException as error:
        result={'status':'REFUSED','error_type':_safe_error_kind(error)}
    print(json.dumps(result,sort_keys=True))
