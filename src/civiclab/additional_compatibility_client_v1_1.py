"""Unreleased fixed-run client integration. Actual entry is denied.

No caller-supplied payload, workspace/output path or retry operation. Tests patch
only the catalog, credential and transport boundaries in temporary OS homes.
"""
from copy import deepcopy
from decimal import Decimal
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time

from .common import canonical_bytes, canonical_hash, sha256_file, redact
from .model import ExecutionBlocked
from .owner_budget_v3 import utc, digest, freeze
from .production_admission_v4 import (compile_compatibility_release, make_context,
    _fetch_public_catalog, _read_environment_key)
from .production_price_v4 import fresh_proof
from .production_owner_v4 import new_operation_time
from .additional_compatibility_owner_v1 import (_AdditionalOwnerV1, validate_bundle,
    receipt_for, code_contract as owner_contract)
from .production_compatibility_transport_v4_2 import _CompatibilityTransportV4_2
from .production_compatibility_v4_2_1 import (_answer, _observed_cost, _no_secret,
    _usage_bounds, _auxiliary_observation, _cost, _safe_error_kind,
    _failure_diagnostic, _SafeExecutionFailure)

_SEAL=object()


def code_contract():
    from . import (production_compatibility_v4_2_1, production_compatibility_transport_v4_2,
                   openrouter_http_v2, live_billing_v2)
    root=Path(__file__).resolve().parents[2]
    modules=(sys.modules[__name__],production_compatibility_v4_2_1,
             production_compatibility_transport_v4_2,openrouter_http_v2,live_billing_v2)
    return {'kind':'ADDITIONAL_COMPATIBILITY_CLIENT_V1_1','owner_contract':owner_contract(),
        'pins':{str(Path(m.__file__).relative_to(root)):sha256_file(m.__file__) for m in modules},
        'limits':{'whole_phase_seconds':120,'HTTP_seconds':30,'socket_seconds':15,
            'catalog_GETs':1,'POSTs':1,'statistics_GETs':1,'retries':0},
        'actual_entry':'DENIED_UNRELEASED'}


def open_actual(*args,**kwargs):
    raise ExecutionBlocked('additional connectivity client is unreleased; no actual access')


def _transport(credential):
    return _CompatibilityTransportV4_2(credential)


class _Journal:
    def __init__(self,owner,run_id,manifest,*,started):
        self.started=started;self.started_utc=new_operation_time();self.sequence=0;self.previous=None
        base=owner.directory/'additional-test-v1'
        for path in (base,*base.parents):
            if path.is_symlink():raise ExecutionBlocked('fixed run namespace symlink refused')
        base.mkdir(mode=0o700,exist_ok=True)
        self.path=base/run_id; self.path.mkdir(mode=0o700,exist_ok=False)
        self.lock=(self.path/'run.lock').open('xb');os.chmod(self.path/'run.lock',0o600)
        fcntl.flock(self.lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            self.write('manifest',manifest)
            self.event('DURABLE_PHASE_INTENT')
        except BaseException:
            self.lock.close()
            raise

    def write(self,name,value):
        raw=canonical_bytes(value)
        if redact(value)!=value or len(raw)>65536:raise ExecutionBlocked('private journal artifact refused')
        path=self.path/(name+'.local.json')
        entries=list(self.path.iterdir())
        if any(p.is_symlink() or not p.is_file() for p in entries):
            raise ExecutionBlocked('unexpected private run entry')
        if sum(p.stat().st_size for p in entries)+len(raw)>524288:
            raise ExecutionBlocked('private run packet exceeds cumulative bound')
        with path.open('xb') as f:
            os.chmod(path,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
        return path

    def event(self,kind,**fields):
        value={'sequence':self.sequence,'previous':self.previous,
               'at_utc':new_operation_time().isoformat(),'event':kind,**fields}
        path=self.write('event-'+str(self.sequence).zfill(6),value)
        self.previous=sha256_file(path);self.sequence+=1

    def close(self):
        self.lock.close()


class _Phase:
    def __init__(self,journal,m):
        self.journal=journal;self.policy=m;self.maximum_utc=journal.started_utc
    def gate(self):
        elapsed=time.monotonic()-self.journal.started;now=new_operation_time()
        if (not 0<=elapsed<120 or now<self.maximum_utc
            or not utc(self.policy['valid_from_utc'])<=now<utc(self.policy['valid_until_utc'])):
            raise ExecutionBlocked('phase or authority deadline reached; no new HTTP')
        self.maximum_utc=now


class _Capability:
    def __init__(self,seal,journal,phase,transport,body,bundle,head):
        if seal is not _SEAL:raise ExecutionBlocked('opaque dispatch capability required')
        self.journal=journal;self.phase=phase;self.transport=transport;self.body=body
        self.bundle=bundle;self.head=head;self.used=False;self.posts=0
    def post(self):
        self.phase.gate()
        if self.used:raise ExecutionBlocked('one-shot dispatch capability spent')
        self.used=True
        self.journal.write('dispatch-consumed',{'receipt':self.bundle['receipt'],
            'context_hash':canonical_hash(self.bundle['context']),'head':self.head,
            'payload_hash':canonical_hash(json.loads(self.body))})
        self.journal.event('MODEL_POST_INTENT',receipt=self.bundle['receipt'])
        self.phase.gate();self.posts=1
        return self.transport.post_bytes(self.body)


def _row(owner,receipt):
    return next(r for r in owner.snapshot()['charges'] if r['id']==receipt)


def execute_authored(m,r,a,o,release,*,expected,executor_review,expected_executor_review_hash):
    """Private candidate integration only; no reviewed actual factory exists."""
    if expected is None: raise ExecutionBlocked('externally expected hashes required')
    # Capture one detached, internally consistent external snapshot. No caller
    # aliases may survive across catalog, credential or transport callbacks.
    captured=freeze({'policy':m,'review':r,'approval':a,'owner_assertion':o,
        'release':release,'expected':expected,'executor_review':executor_review,
        'expected_executor_review_hash':expected_executor_review_hash})
    if len(canonical_bytes(captured))>524288:
        raise ExecutionBlocked('bounded complete external packet required')
    m,r,a,o,release=(captured[k] for k in ('policy','review','approval','owner_assertion','release'))
    expected=captured['expected'];executor_review=captured['executor_review']
    expected_executor_review_hash=captured['expected_executor_review_hash']
    # Validate all external static bindings before OS-home discovery or output.
    compiled=compile_compatibility_release(release['terms'],release['interpretation'],
                                          run_id=m['new_run_id'],seed=20261103,max_tokens=32)
    if compiled!=release:raise ExecutionBlocked('fixed released bytes/code differ')
    proof={'url':'https://openrouter.ai/api/v1/models/'+release['terms']['model']+'/endpoints',
        'body_sha256':release['terms']['initial_catalog_sha256'],
        'observed_at_utc':m['valid_from_utc'],
        'metadata_semantic_hash':release['terms']['metadata_semantic_hash']}
    c=make_context(release,canonical_hash(a),proof)
    b={'policy':m,'review':r,'approval':a,'owner_assertion':o,'context':c,'receipt':receipt_for(m,r,o,c)}
    b=validate_bundle(b,expected=expected)
    er=executor_review
    if (type(er) is not dict or set(er)!=set('kind reviewer_role review_id client_contract_hash policy_hash owner_assertion_hash release_hash'.split())
        or er['kind']!='INDEPENDENT_ADDITIONAL_COMPATIBILITY_CLIENT_REVIEW_V1_1'
        or er['reviewer_role']!='independent_auditor' or er['client_contract_hash']!=canonical_hash(code_contract())
        or er['policy_hash']!=canonical_hash(m) or er['owner_assertion_hash']!=canonical_hash(o)
        or er['release_hash']!=canonical_hash(release) or canonical_hash(er)!=expected_executor_review_hash):
        raise ExecutionBlocked('exact external client/code review required')
    digest(er['review_id'],32);digest(expected_executor_review_hash)
    now=new_operation_time()
    if not utc(m['valid_from_utc'])<=now or (utc(m['valid_until_utc'])-now).total_seconds()<120:
        raise ExecutionBlocked('full phase cannot fit lease')
    started=time.monotonic()
    owner=_AdditionalOwnerV1()  # Constructor validates fixed original identity.
    journal=_Journal(owner,m['new_run_id'],{'kind':'ADDITIONAL_COMPATIBILITY_V1_1',
        'policy_hash':canonical_hash(m),'review_hash':canonical_hash(r),'owner_assertion_hash':canonical_hash(o),
        'approval_hash':canonical_hash(a),'release_hash':canonical_hash(release),'client_review':er},started=started)
    phase=_Phase(journal,m);receipt=None;known=None;generation=None;stats_attempts=0
    cap=None;stage='OWNER_PREFLIGHT';credential=None
    try:
        phase.gate()
        with owner._lock(),owner._connect() as db:
            state,head=owner._verify(db)
            owner._predecessor(state,m,head=head,history=state['_prefix_events'])
        stage='PUBLIC_METADATA';phase.gate();journal.event('CATALOG_GET_INTENT')
        raw,metadata=_fetch_public_catalog(release['terms']['model'])
        proof=fresh_proof(raw,metadata,release['interpretation'],release['terms'],now=new_operation_time())
        phase.gate();stage='CREDENTIAL_AND_TRANSPORT'
        credential=_read_environment_key();transport=_transport(credential)
        c=make_context(release,canonical_hash(a),proof)
        b={**b,'context':c,'receipt':receipt_for(m,r,o,c)};b=validate_bundle(b,expected=expected)
        body=canonical_bytes(release['request']['payload'])
        if len(body)>262144:raise ExecutionBlocked('payload bound exceeded')
        journal.write('request',{'payload':release['request']['payload'],'context':c})
        stage='RESERVATION';phase.gate()
        # Recheck the complete static review closure at the grant boundary.
        # Price proof/C are runtime observations; approved M/R/A/O/release and
        # their external expected hashes remain the detached entry snapshot.
        if (canonical_hash(er)!=expected_executor_review_hash
            or er['client_contract_hash']!=canonical_hash(code_contract())
            or er['policy_hash']!=canonical_hash(m)
            or er['owner_assertion_hash']!=canonical_hash(o)
            or er['release_hash']!=canonical_hash(release)
            or any(b[k]!=captured[k] for k in ('policy','review','approval','owner_assertion'))):
            raise ExecutionBlocked('full review closure changed before grant')
        b=validate_bundle(b,expected=expected)
        ack=owner.append_authored_batch(b,expected=expected,release=release,credential_shape_check=lambda:True)
        receipt=ack['receipt'];stage='ACKNOWLEDGEMENT'
        with owner._lock(),owner._connect() as db:
            checked,head=owner._verify(db)
            if head!=ack['head'] or checked['rows'][receipt]!=owner._new_row(b):
                raise ExecutionBlocked('exact durable reservation acknowledgement required')
        journal.write('acknowledgement',{'policy_hash':canonical_hash(m),'review_hash':canonical_hash(r),
            'owner_assertion_hash':canonical_hash(o),'context_hash':canonical_hash(c),
            'receipt':receipt,'head':head,'client_contract_hash':canonical_hash(code_contract())})
        cap=_Capability(_SEAL,journal,phase,transport,body,b,head)
        stage='MODEL_POST';response=cap.post();stage='RESPONSE_VALIDATION'
        usage=response.get('usage') if type(response) is dict else None
        if type(usage) is dict and usage.get('cost') is not None:known=_observed_cost(usage['cost'],credential)
        _no_secret(response,credential)
        if type(response) is not dict:raise ValueError('invalid response domain')
        identity=response.get('id')
        if type(identity) is str and len(identity)<=256 and re.fullmatch(r'gen-[0-9A-Za-z-]+',identity):generation=identity
        if known is not None and known>c['envelope']['reserved_microusd']:
            owner.transition(receipt,'UNCERTAIN',observed_cost=known,generation_id=generation,error_type='ObservedChargeOverrun')
            raise ExecutionBlocked('known charge exceeds reservation')
        if generation is None or response.get('model')!=c['terms']['model']:raise ValueError('unverified generation/model')
        answer=_answer(response)
        owner.transition(receipt,'RESPONSE_SEEN',generation_id=generation,output_hash=canonical_hash(answer),observed_cost=known)
        stage='STATISTICS_CLAIM';phase.gate();owner.claim_statistics_lookup(receipt)
        journal.event('STATISTICS_GET_INTENT',receipt=receipt,generation_id=generation)
        phase.gate();stage='STATISTICS_GET';stats_attempts=1
        result=transport.statistics(generation);stage='STATISTICS_VALIDATION'
        stats=result.get('data') if type(result) is dict else None
        if type(stats) is dict and stats.get('id')==generation and stats.get('total_cost') is not None:
            known=max(known or 0,_observed_cost(stats['total_cost'],credential))
        _no_secret(result,credential)
        if type(stats) is not dict or stats.get('id')!=generation:raise ValueError('generation metadata identity unavailable')
        if known is not None and known>c['envelope']['reserved_microusd']:
            owner.transition(receipt,'OVERRUN',observed_cost=known);raise ExecutionBlocked('reported overrun')
        if (stats.get('model')!=c['terms']['model'] or stats.get('provider_name')!=c['terms']['reported_provider']
            or stats.get('is_byok') is not False):raise ValueError('actual provider/billing mode unverified')
        for field,bound in (('native_tokens_prompt',c['envelope']['input_token_bound']),
            ('native_tokens_completion',32),('native_tokens_reasoning',0)):
            if type(stats.get(field)) is not int or not 0<=stats[field]<=bound:raise ValueError('native usage unverified')
        auxiliary,valid=_auxiliary_observation(stats);journal.write('auxiliary-observation',auxiliary)
        if not valid:raise ExecutionBlocked('unsupported auxiliary activity')
        _usage_bounds(usage,c['envelope'])
        if type(usage) is dict and usage.get('cost') is not None and Decimal(str(usage['cost']))!=Decimal(str(stats['total_cost'])):
            raise ValueError('response and generation cost disagree')
        # Preserve the connectivity methods rule: even a verified late bill
        # leaves the full new reservation UNCERTAIN. Retain its observed cost
        # and billing evidence locally; no settlement, checkpoint or more HTTP.
        late=False
        try:phase.gate()
        except ExecutionBlocked:late=True
        amount=_cost(stats['total_cost'])
        billing={k:stats[k] for k in ('id','model','provider_name','total_cost','native_tokens_prompt',
            'native_tokens_completion','native_tokens_reasoning','is_byok')}
        if late:
            owner.transition(receipt,'UNCERTAIN',observed_cost=amount,billing=billing,error_type='TimingFailure')
            journal.write('billing',billing)
            summary={'kind':'ADDITIONAL_COMPATIBILITY_V1_1','status':'TIMING_FAILURE',
                'receipt':receipt,'generation_id':generation,
                'charged_microusd':c['envelope']['reserved_microusd'],
                'reported_provider_cost_microusd':amount,'model_POST_attempts':cap.posts,
                'statistics_GET_attempts':stats_attempts,'old_provider_cost':'UNKNOWN',
                'old_conservative_hold_microusd':340,'automatic_retry':False}
            journal.write('summary',summary);journal.event('TERMINAL',status='TIMING_FAILURE')
            return {'path':str(journal.path),'summary':summary}
        stage='SETTLEMENT';owner.transition(receipt,'SETTLED',observed_cost=amount,billing=billing)
        stage='CHECKPOINT'
        path=journal.write('phase',{'schema_version':1,'run_id':c['run_id'],'unit_id':c['unit_id'],
            'phase':c['phase'],'receipt':receipt,'request_hash':c['envelope']['request_hash'],'output':answer})
        journal.write('billing',billing);stage='OWNER_COMMIT';owner.commit_phase(receipt,path)
        summary={'kind':'ADDITIONAL_COMPATIBILITY_V1_1','status':'TIMING_FAILURE' if late else
            'COMPATIBLE' if answer['status']=='VALID' else 'CHARGED_QUALITY_FAILURE',
            'receipt':receipt,'generation_id':generation,'charged_microusd':amount,
            'model_POST_attempts':cap.posts,'statistics_GET_attempts':stats_attempts,
            'old_provider_cost':'UNKNOWN','old_conservative_hold_microusd':340,'automatic_retry':False}
        journal.write('summary',summary);journal.event('TERMINAL',status=summary['status'])
        return {'path':str(journal.path),'summary':summary}
    except BaseException as error:
        if receipt is not None:
            try:
                row=_row(owner,receipt)
                if row['status'] in ('STARTED','RESPONSE_SEEN','SETTLED'):
                    owner.transition(receipt,'UNCERTAIN',observed_cost=known,generation_id=generation,error_type=_safe_error_kind(error))
            except BaseException:pass
        try:row=_row(owner,receipt) if receipt else None
        except BaseException:row=None
        diagnostic=_failure_diagnostic(error,stage,cap.posts if cap else 0,stats_attempts,receipt,known,row)
        try:
            journal.write('failure',{'status':'STOPPED_NO_RETRY','diagnostic':diagnostic,'error_type':_safe_error_kind(error)})
            journal.event('TERMINAL',status='STOPPED_NO_RETRY')
        except BaseException:pass
        if isinstance(error,(SystemExit,KeyboardInterrupt)):raise KeyboardInterrupt() from None
        raise _SafeExecutionFailure(diagnostic) from None
    finally:journal.close()
