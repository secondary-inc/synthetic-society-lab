"""MOCK-only diagnostic successor; no live or consumed-slot release.

Sealed one-slot execution with existing transports/price/billing validators.

No key acquisition here. Caller admission is separate; author tests inject only
inert doubles. A failed/uncertain attempt cannot be resumed by execute again.
"""
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
import time
import re

from ..common import canonical_bytes,canonical_hash
from ..model import ExecutionBlocked
from ..owner_budget_v3 import utc
from ..production_compatibility_transport_v4_2 import _SafeTransportFailure
from .exploratory_live_client_v1 import (_Journal,_Phase,_Capability,_SEAL,_no_secret,
    _observed_cost,_no_provider_reasoning,_no_unsupported_response_activity,_usage_bounds,_cost)
from .wrapper_crossmodel_v1 import parse_response
from .crossmodel_price_v1 import fresh_proof
from .crossmodel_recovery_metadata_v1 import normalize_statistics,response_model_allowed
from . import wrapper_crossmodel_canary_v1 as p
from .wrapper_canary_failure_diagnostic_v1 import write_initial_failure
from pathlib import Path
import hashlib


class OperationGate:
    def __init__(self,packet,*,mono=time.monotonic,now=lambda:datetime.now(timezone.utc),cancelled=lambda:False):
        self.packet=packet;self.mono=mono;self.now=now;self.cancelled=cancelled
        self.start_mono=self.last_mono=mono();self.start_utc=self.last_utc=now()
        self.check()
    def check(self):
        m=self.mono();n=self.now();elapsed=m-self.start_mono
        p.need(not self.cancelled() and m>=self.last_mono and n>=self.last_utc
               and 0<=elapsed<240 and abs((n-self.start_utc).total_seconds()-elapsed)<=2
               and utc(self.packet['valid_from_utc'])<=n<utc(self.packet['valid_until_utc']), 'canary operation deadline/clock/cancel')
        self.last_mono=m;self.last_utc=n
        return n


def validate_release(release,packet,expected_packet_hash,expected_release_hash):
    p.validate_packet(packet,expected_packet_hash)
    p.closed(release,('kind','packet_sha256','code_hash','review_sha256','maximum_POSTs','scope'))
    p.need(canonical_hash(release)==expected_release_hash and release=={
        'kind':'LEAD_WRAPPER_CANARY_RELEASE_V1','packet_sha256':expected_packet_hash,
        'code_hash':canonical_hash(p.contract()),'review_sha256':canonical_hash(packet['review']),
        'maximum_POSTs':1,'scope':'ORIGINAL45_ONLY_NOT_FULL80'},'canary exact lead release')


def execute_mock(packet,*,diagnostic_release,expected_packet_hash,release,expected_release_hash,owner,
            credential,transport,catalog_fetch,journal=None,gate=None,provenance='MOCK',sleep=time.sleep):
    validate_diagnostic_release(diagnostic_release,packet,release)
    p.need(provenance=='MOCK' and type(transport) is InertFailureTransport and type(catalog_fetch) is InertCapturedCatalog,'diagnostic successor is inert offline only')
    validate_release(release,packet,expected_packet_hash,expected_release_hash)
    p.need(provenance=='MOCK','diagnostic explicit MOCK provenance')
    gate=gate or OperationGate(packet)
    gate.check();owner.open_canary(packet,expected_packet_hash)
    receipt=None;known=None;generation=None;billing=None;phase=None
    own_journal=journal is None;stage='JOURNAL'
    try:
        journal=journal or _Journal(owner,packet['run_id'],packet)
        proofs={}
        for role in ('A','B'):
            stage='CATALOG_'+role
            gate.check();owner.intent('CATALOG_'+role,1)
            raw,metadata=catalog_fetch(packet['price_release'][role]['terms']['model'])
            gate.check()
            p.need(type(raw) is bytes and len(raw)<=2000000,'canary catalog bound')
            rel=packet['price_release'][role]
            proof=fresh_proof(raw,metadata,rel['interpretation'],rel['terms'],now=gate.check())
            journal.write('catalog-'+role+'.json',{'body_utf8':raw.decode(),'metadata':metadata,'proof':proof});proofs[role]=proof
        stage='PROOFS';owner.register_proofs(proofs);gate.check()
        terms=packet['price_release']['B']['terms']
        phase=_Phase({'policy':packet,'price_release':packet['price_release']['B']},proofs['B'])
        stage='GRANT';ack=owner.grant();receipt=ack['receipt'];compiled=ack['request'];context=ack['context']
        p.need(compiled['execution_order']==45 and compiled['pair_seed']==p.SEED
               and canonical_hash(compiled['payload'])==context['payload_hash'],'canary acknowledgement payload')
        stage='REQUEST';journal.write(receipt+'-request.json',ack)
        stage='POST';gate.check();phase.gate();owner.intent('POST',1)
        cap=_Capability(_SEAL,journal,phase,transport,ack)
        response=cap.post();gate.check();phase.gate()
        stage='RESPONSE';usage=response.get('usage') if type(response) is dict else None
        if type(usage) is dict and usage.get('cost') is not None:known=_observed_cost(usage['cost'],credential)
        _no_secret(response,credential);_no_provider_reasoning(response);_no_unsupported_response_activity(response)
        parsed=parse_response(response);_no_secret(parsed,credential)
        if type(response.get('id')) is str and re.fullmatch(r'gen-[A-Za-z0-9-]{1,124}',response['id']):generation=response['id']
        journal.write(receipt+'-response.json',response)
        p.need(known is None or known<=context['envelope']['reserved_microusd'],'canary observed overrun')
        p.need(generation is not None and response_model_allowed(response.get('model'),terms['model']),'canary response model/generation')
        output={'status':parsed['status'],'answer':parsed['answer'],'response_raw_sha256':canonical_hash(response)}
        owner.transition(receipt,'RESPONSE_SEEN',generation_id=generation,output_hash=canonical_hash(output),observed_cost=known)
        stage='STATISTICS_CLAIM';owner.claim_statistics_lookup(receipt)
        phase.wait_for_statistics();gate.check()
        statistics=None
        for ordinal in (1,2,3):
            stage='STATISTICS';gate.check();phase.gate();owner.intent('STATISTICS',ordinal)
            journal.write(receipt+f'-statistics-intent-{ordinal}.json',{'receipt':receipt,'ordinal':ordinal,'generation_hash':canonical_hash(generation)})
            try:
                statistics=transport.statistics(generation);break
            except _SafeTransportFailure as error:
                if error.diagnostic()['http_status']!=404 or ordinal==3:raise
                wait=(10,10,20)[ordinal-1]
                phase.gate(reserve_seconds=wait+40);gate.check();sleep(wait);phase.gate(reserve_seconds=40)
        gate.check();phase.gate();_no_secret(statistics,credential)
        journal.write(receipt+'-statistics.json',statistics)
        normalized=normalize_statistics(deepcopy(statistics['data']),generation_id=generation,requested_model=terms['model'],reported_provider=terms['reported_provider'],input_bound=context['envelope']['input_token_bound'],output_bound=256,reserved_microusd=context['envelope']['reserved_microusd'],request_payload=compiled['payload'])
        stage='INVOICE';billing=normalized['billing'];amount=_cost(statistics['data']['total_cost'])
        _usage_bounds(usage,context['envelope'])
        if type(usage) is dict and usage.get('cost') is not None:p.need(Decimal(str(usage['cost']))==Decimal(str(statistics['data']['total_cost'])),'canary response/invoice cost mismatch')
        gate.check();phase.gate()
        owner.transition(receipt,'SETTLED',observed_cost=amount,billing=billing)
        checkpoint={'schema_version':1,'run_id':context['run_id'],'unit_id':context['unit_id'],'phase':'post','receipt':receipt,'request_hash':context['envelope']['request_hash'],'output':output}
        stage='CHECKPOINT';journal.write(receipt+'-checkpoint.json',checkpoint)
        witness={'execution_order':45,'phase':'post','status':parsed['status'],'answer':parsed['answer'],'payload_sha256':compiled['payload_sha256'],'receipt':receipt}
        stage='COMMIT';gate.check();phase.gate();owner.commit_canary(receipt,witness)
        result=p.envelope(packet['parent_key'],[witness],'COMMITTED_ONE_SLOT',provenance)
        stage='SUMMARY';journal.write('summary.json',result)
        return result
    except BaseException as error:
        # First durable error evidence precedes ANY expensive owner cleanup read.
        if journal is not None:
            try:write_initial_failure(journal,error,stage,provenance)
            except BaseException:pass  # Never replace original error or skip cleanup.
        uncertain_verified=False
        if receipt is not None:
            try:
                fields={'observed_cost':known,'generation_id':generation,'error_type':'CanaryStopped'}
                if billing is not None:fields['billing']=billing
                # Real transition verifies before apply/commit; then perform one
                # full terminal read-back (the original _append has no read-back).
                owner.transition(receipt,'UNCERTAIN',**fields)
                terminal=owner.canary_snapshot()
                p.need(terminal['branch']['closed'] is True and terminal['row']['status'] in ('UNCERTAIN','OVERRUN'),'verified terminal hold required')
                uncertain_verified=True
            except BaseException:pass
        # No redundant pre-transition snapshot/CLOSE after verified terminal hold.
        # If transition did not verify, retain the established fallback CLOSE.
        if not uncertain_verified:
            try:owner.close_canary('FAILED')
            except BaseException:pass
        if journal is not None:
            try:journal.write('failure.json',{'kind':'CANARY_STOP_NO_RETRY','error_type':type(error).__name__ if type(error) in {ValueError,ExecutionBlocked,TimeoutError,_SafeTransportFailure} else 'OTHER','old_holds_unchanged':True,'original_full80_analysis':'NOT_RUN_INCOMPLETE'})
            except BaseException:pass
        raise
    finally:
        if own_journal and journal is not None:journal.close()


class InertFailureTransport:
    """No network capability; one authored HTTP-status or timeout failure."""
    def __init__(self,status=429):
        if status not in (402,429,500,503):raise ValueError('fixed inert failure required')
        self.status=status;self.posts=0;self.gets=0
    def post_bytes(self,raw):
        self.posts+=1
        raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',self.status)
    def statistics(self,generation):
        self.gets+=1;raise AssertionError('no statistics after inert POST failure')


class InertCapturedCatalog:
    def __init__(self,records,now):
        if type(records) is not dict or set(records)!=set(('A','B')):raise ValueError('two captured catalogs required')
        self.records=deepcopy(records);self.now=now;self.calls=[]
    def __call__(self,model):
        role={'openai/gpt-4.1-nano':'A','qwen/qwen3-30b-a3b-instruct-2507':'B'}[model]
        self.calls.append(role);record=self.records[role];raw=record['body_utf8'].encode()
        # Explicitly authored MOCK receipt; never edits/redates captured evidence.
        return raw,{'url':record['metadata']['url'],'body_sha256':hashlib.sha256(raw).hexdigest(),'observed_at_utc':self.now().isoformat()}


def diagnostic_contract():
    root=Path(__file__).resolve().parents[3]
    names=('src/civiclab/e02/wrapper_crossmodel_canary_diagnostic_v1_client.py',
           'src/civiclab/e02/wrapper_canary_failure_diagnostic_v1.py')
    return {'kind':'WRAPPER_CANARY_DIAGNOSTIC_MOCK_CODE_V1','predecessor':p.contract(),
            'pins':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}}


def validate_diagnostic_release(record,packet,release):
    p.closed(record,('kind','code_hash','packet_hash','release_hash','scope'))
    p.need(record=={'kind':'DIAGNOSTIC_SUCCESSOR_MOCK_RELEASE_V1','code_hash':canonical_hash(diagnostic_contract()),
           'packet_hash':canonical_hash(packet),'release_hash':canonical_hash(release),
           'scope':'OFFLINE_RETROSPECTIVE_FAILURE_ONLY_NOT_LIVE'},'diagnostic exact offline release')
