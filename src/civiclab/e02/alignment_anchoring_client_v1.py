"""One finite alignment/anchoring follow-up; existing transports and controls reused."""
from decimal import Decimal
import hashlib
import os
import re
import shutil
import stat
import time

from ..common import canonical_bytes,canonical_hash,redact
from ..model import ExecutionBlocked
from ..owner_budget_v3 import freeze,utc
from ..production_price_v4 import fresh_proof
from ..production_compatibility_transport_v4_2 import _SafeTransportFailure
from . import exploratory_live_client_v1 as frozen
from .alignment_anchoring_owner_v1 import validate_packet,protocol_bytes
from .alignment_anchoring_v1 import next_action,parse_response as parse_survey,analyze,response_envelope
from .exploratory_metadata_v1 import normalize_statistics,response_model_allowed
from .exploratory_live_client_v1 import (
    _Journal as _BaseJournal,_Phase,_Capability,_SEAL,_row,
    _no_secret,_observed_cost,_cost,_usage_bounds,_no_provider_reasoning,
    _no_unsupported_response_activity,phase_record,
    _safe_error_kind,_failure_diagnostic,_SafeExecutionFailure,
    AnalysisRepresentationBound,PROVIDER_REPRESENTATION,ARTIFACT_BYTES,
    _regular_directory,JOURNAL_BYTES,MINIMUM_FREE_BYTES)

MAX_NEW_POSTS=28
MAX_NEW_GETS=84
LOOKUP_WAITS=(10,10,20)


def _owner():
    from .alignment_anchoring_owner_v1 import AlignmentOwnerV1
    return AlignmentOwnerV1()

def _fetch_public_catalog(model):return frozen._fetch_public_catalog(model)
def _read_environment_key():return frozen._read_environment_key()
def _transport(credential):return frozen._transport(credential)
def new_operation_time():return frozen.new_operation_time()


class _Journal(_BaseJournal):
    """Same closed journal semantics, finite 384-file capacity for 28x3 lookups."""
    def write(self,name,value):
        if type(name) is not str or re.fullmatch(r'[A-Za-z0-9_-]+\.json',name) is None:
            raise ExecutionBlocked('closed journal filename required')
        raw=canonical_bytes(value)
        if len(raw)>ARTIFACT_BYTES or redact(value)!=value:
            raise ExecutionBlocked('private artifact size or credential refusal')
        _regular_directory(self.path)
        entries=list(self.path.iterdir());total=0
        for entry in entries:
            mode=entry.lstat().st_mode
            if not stat.S_ISREG(mode):raise ExecutionBlocked('unexpected journal entry')
            size=entry.stat().st_size
            if size>ARTIFACT_BYTES:raise ExecutionBlocked('existing artifact exceeds bound')
            total+=size
        if len(entries)+1>384 or total+len(raw)>JOURNAL_BYTES or shutil.disk_usage(self.path).free<MINIMUM_FREE_BYTES:
            raise ExecutionBlocked('finite journal/free capacity exceeded')
        path=self.path/name
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        # Persist directory entry too; failure stops, file remains for inspection.
        directory_fd=os.open(self.path,os.O_RDONLY)
        try:os.fsync(directory_fd)
        finally:os.close(directory_fd)
        return path


def _terminal(owner,raw,terms,*,response_provenance):
    snapshot=freeze(owner.study_snapshot())
    envelope=response_envelope(raw,canonical_bytes(snapshot['transcript']),
        response_provenance=response_provenance,stopped=snapshot['status']=='STOPPED',terms=terms)
    analysis=analyze(raw,canonical_bytes(envelope))
    return {'status':snapshot['status'],'snapshot':snapshot,'response_envelope':envelope,
        'analysis_status':'READY','analysis':analysis}

def _visibility_wait(phase,seconds):
    """Initial/recovery waits consume the same 120s phase, never extend it."""
    phase.gate(reserve_seconds=seconds+40)  # 30 HTTP plus 10 checkpoint allowance.
    started=time.monotonic()
    for _ in range(seconds+2):
        left=seconds-(time.monotonic()-started)
        if left<=0:
            phase.gate(reserve_seconds=40);return
        phase.gate(reserve_seconds=left+40)
        time.sleep(min(1,left))
    raise ExecutionBlocked('billing wait clock failed to progress')


def _poll_statistics(transport,generation,*,journal,phase,receipt,counters):
    """One logical claim, at most three physical GETs; only closed 404 retry."""
    for attempt,wait in enumerate(LOOKUP_WAITS,1):
        _visibility_wait(phase,wait)
        if counters['total']>=MAX_NEW_GETS:raise ExecutionBlocked('follow-up lookup count exhausted')
        journal.write(f'{receipt}-statistics-{attempt:02d}-intent.json',
            {'receipt':receipt,'generation_id':generation,'attempt':attempt,'wait_seconds':wait,
             'operation':'ONE_BOUNDED_GENERATION_GET_NO_MODEL_POST'})
        phase.gate(reserve_seconds=40)
        counters['total']+=1;counters['phase']+=1
        try:return transport.statistics(generation)
        except _SafeTransportFailure as error:
            if type(error) is not _SafeTransportFailure:raise
            diagnostic=error.diagnostic()
            journal.write(f'{receipt}-statistics-{attempt:02d}-failure.json',diagnostic)
            retry=(type(error) is _SafeTransportFailure and diagnostic=={
                'stage':'HTTP_STATUS','category':'HTTP_STATUS','http_status':404,'close_failed':False})
            if not retry or attempt==3:raise
    raise ExecutionBlocked('billing lookup schedule exhausted')


def execute_followup(packet,*,expected_packet_hash,response_provenance='MOCK'):
    """Private candidate, with replaceable authored boundaries for tests.

    Actual terminal factory is denied. A separately reviewed caller must verify
    provenance, code and exact release before selecting EXPLORATORY_REAL_MODEL.
    There are no caller-supplied phase, payload, baseline, owner or output paths.
    """
    if response_provenance not in ('MOCK','EXPLORATORY_REAL_MODEL'):
        raise ExecutionBlocked('explicit closed response provenance required')
    packet=validate_packet(freeze(packet),expected_packet_hash=expected_packet_hash)
    raw_protocol=protocol_bytes();terms=packet['price_release']['terms']
    next_action(raw_protocol,terms,b'[]')
    now=new_operation_time()
    if any(not utc(v['valid_from_utc'])<=now or (utc(v['valid_until_utc'])-now).total_seconds()<=120
           for v in (packet['policy'],terms)):
        raise ExecutionBlocked('full phase does not fit current authority/terms')
    owner=_owner();journal=_Journal(owner,packet['policy']['run_id'],packet)
    credential=None;cap=None;receipt=None;known=None;generation=None;billing=None
    post_attempts=0;statistics_attempts=0;catalog_attempts=0;phase=None
    stage='CATALOG';phase_stats=0
    counters={'total':0,'phase':0};expected_request=None
    provider_bodies={'response':'MISSING','statistics':'MISSING'}
    try:
        # Exactly one fresh observation for the entire run. No refresh, retry or
        # reconstruction on expiry; the phase gate and owner recheck its age.
        catalog_attempts=1
        raw,metadata=_fetch_public_catalog(terms['model'])
        proof=fresh_proof(raw,metadata,packet['price_release']['interpretation'],terms,now=new_operation_time())
        if type(raw) is not bytes or len(raw)>ARTIFACT_BYTES:
            raise ExecutionBlocked('catalog artifact bound exceeded')
        journal.write('catalog.json',{'canonical_source_sha256':hashlib.sha256(raw).hexdigest(),
            'body_utf8':raw.decode('utf-8'),'metadata':metadata,'proof':proof})
        stage='CREDENTIAL';credential=_read_environment_key();transport=_transport(credential)
        stage='FOLLOWUP_START'
        owner.start_followup(packet,proof,expected_packet_hash=expected_packet_hash)
        initial=freeze(owner.study_snapshot())
        if initial['status']!='ACTIVE' or initial['transcript']:
            raise ExecutionBlocked('new follow-up must start with no new outcomes')
        journal.write('ancestry.json',{'predecessor':packet['policy']['predecessor'],
            'original_study_preserved':True,'historical_holds_released':False,
            'followup_started_at_utc':new_operation_time().isoformat()})
        for _ in range(29):
            receipt=None;known=None;generation=None;billing=None;cap=None;phase_stats=0
            provider_bodies={'response':'MISSING','statistics':'MISSING'}
            stage='PHASE_ADMISSION';counters['phase']=0
            snapshot=freeze(owner.study_snapshot())
            action=next_action(raw_protocol,terms,canonical_bytes(snapshot['transcript']))
            expected_request=action.get('request')
            if snapshot['status'] in ('COMPLETE','STOPPED'):
                terminal=_terminal(owner,raw_protocol,terms,response_provenance=response_provenance)
                terminal.update(original_study_preserved=True,provider_representation=PROVIDER_REPRESENTATION,model_POST_attempts=post_attempts,statistics_GET_attempts=statistics_attempts,
                                catalog_GET_attempts=catalog_attempts,path=str(journal.path))
                journal.write('summary.json',terminal)
                return terminal
            phase=_Phase(packet,proof)
            def ready(context):
                phase.gate(full=True)
                # Credential and transport have been admitted before the sealed
                # callback reaches the owner transaction; no I/O in callback.
                return credential is not None and transport is not None
            stage='RESERVATION'
            ack=owner.reserve_next(packet,proof,expected_packet_hash=expected_packet_hash,transport_ready=ready)
            stage='ACKNOWLEDGEMENT'
            if ack['status'] in ('COMPLETE','STOPPED'):
                terminal=_terminal(owner,raw_protocol,terms,response_provenance=response_provenance)
                terminal.update(original_study_preserved=True,provider_representation=PROVIDER_REPRESENTATION,model_POST_attempts=post_attempts,statistics_GET_attempts=statistics_attempts,
                                catalog_GET_attempts=catalog_attempts,path=str(journal.path))
                journal.write('summary.json',terminal)
                return terminal
            if ack['status']!='RESERVED' or post_attempts>=MAX_NEW_POSTS:
                raise ExecutionBlocked('finite reservation acknowledgement required')
            receipt=ack['receipt'];compiled=freeze(ack['request']);context=freeze(ack['context'])
            if compiled!=expected_request or not 0<=compiled['execution_order']<28:
                raise ExecutionBlocked('reservation differs from exact unattempted follow-up slot')
            if type(receipt) is not str or re.fullmatch(r'[a-f0-9]{32}',receipt) is None:
                raise ExecutionBlocked('closed reservation receipt required')
            # Owner is the authority; client independently cross-checks the ACK
            # object against compiled bytes before granting its opaque capability.
            if (canonical_hash(compiled['payload'])!=compiled['payload_sha256'] or
                context['payload_hash']!=compiled['payload_sha256'] or
                context['phase']!=compiled['phase'] or context['run_id']!=packet['policy']['run_id'] or
                context['envelope']!=compiled['envelope'] or context['terms']!=terms):
                raise ExecutionBlocked('acknowledged request/context mismatch')
            journal.write(receipt+'-request.json',{'request':compiled,'context':context,'plan':ack['plan']})
            cap=_Capability(_SEAL,journal,phase,transport,ack)
            stage='MODEL_POST';post_attempts+=1
            # Attempt counter records the durable one-use capability's actual
            # transport entry, even when failure occurs before/at POST intent.
            try:response=cap.post()
            finally:post_attempts-=1-cap.posts
            stage='RESPONSE_VALIDATION'
            usage=response.get('usage') if type(response) is dict else None
            if type(usage) is dict and usage.get('cost') is not None:
                known=_observed_cost(usage['cost'],credential)
            _no_secret(response,credential)
            if type(response) is not dict:raise ValueError('response must be an object')
            _no_provider_reasoning(response)
            _no_unsupported_response_activity(response)
            identity=response.get('id')
            if type(identity) is str and re.fullmatch(r'gen-[A-Za-z0-9-]{1,124}',identity) and len(identity)<=128:
                generation=identity
            # Questionnaire JSON can encode sensitive strings with unicode
            # escapes that were invisible in the outer provider object. Check
            # the exact decoded quality record before hashing or retaining it.
            parsed=parse_survey(response)
            _no_secret(parsed,credential)
            response_raw=canonical_bytes(response)
            journal.write(receipt+'-response.json',response)
            provider_bodies['response']='RETAINED_CANONICAL_COMPLETE'
            # Harvest known cost before any downstream identity/content refusal.
            if known is not None and known>context['envelope']['reserved_microusd']:
                owner.transition(receipt,'UNCERTAIN',observed_cost=known,generation_id=generation,error_type='ObservedChargeOverrun')
                raise ExecutionBlocked('known response overrun; no lookup')
            valid_model=response_model_allowed(response.get('model'),terms['model'])
            if generation is None or not valid_model:
                raise ValueError('unverified generation/model')
            output={'status':parsed['status'],'answer':parsed['answer'],
                    'response_raw_sha256':hashlib.sha256(response_raw).hexdigest()}
            owner.transition(receipt,'RESPONSE_SEEN',generation_id=generation,
                             output_hash=canonical_hash(output),observed_cost=known)
            stage='STATISTICS_CLAIM';phase.gate();owner.claim_statistics_lookup(receipt)
            stage='STATISTICS_GET'
            try:result=_poll_statistics(transport,generation,journal=journal,phase=phase,receipt=receipt,counters=counters)
            finally:statistics_attempts=counters['total'];phase_stats=counters['phase']
            stage='STATISTICS_VALIDATION'
            stats=result.get('data') if type(result) is dict else None
            if type(stats) is dict and stats.get('id')==generation and stats.get('total_cost') is not None:
                known=max(known or 0,_observed_cost(stats['total_cost'],credential))
            _no_secret(result,credential)
            journal.write(receipt+'-statistics.json',result)
            provider_bodies['statistics']='RETAINED_CANONICAL_COMPLETE'
            if type(stats) is not dict or stats.get('id')!=generation:
                raise ValueError('statistics generation mismatch')
            if known is not None and known>context['envelope']['reserved_microusd']:
                owner.transition(receipt,'OVERRUN',observed_cost=known)
                raise ExecutionBlocked('reported generation overrun')
            normalized=normalize_statistics(stats,generation_id=generation,requested_model=terms['model'],
                reported_provider=terms['reported_provider'],input_bound=context['envelope']['input_token_bound'],
                output_bound=context['envelope']['max_tokens'],reserved_microusd=context['envelope']['reserved_microusd'])
            billing=normalized['billing'];auxiliary=normalized['telemetry']
            _usage_bounds(usage,context['envelope'])
            amount=_cost(stats['total_cost'])
            if type(usage) is dict and usage.get('cost') is not None and Decimal(str(usage['cost']))!=Decimal(str(stats['total_cost'])):
                raise ValueError('response/generation billing disagreement')
            journal.write(receipt+'-quality.json',{'diagnostic':parsed['diagnostic'],'auxiliary':auxiliary,
                'provider_representation':PROVIDER_REPRESENTATION})
            stage='REPRESENTATION';phase_record(compiled,parsed)
            stage='TIMING';phase.gate()
            stage='SETTLEMENT';owner.transition(receipt,'SETTLED',observed_cost=amount,billing=billing)
            checkpoint={'schema_version':1,'run_id':context['run_id'],'unit_id':context['unit_id'],
                'phase':context['phase'],'receipt':receipt,'request_hash':context['envelope']['request_hash'],'output':output}
            stage='CHECKPOINT';journal.write(receipt+'-checkpoint.json',checkpoint)
            phase.gate();stage='OWNER_COMMIT';owner.commit_survey(receipt)
        raise ExecutionBlocked('finite phase iteration bound exceeded')
    except BaseException as error:
        if receipt is not None:
            try:
                row=_row(owner,receipt)
                if row['status'] in ('STARTED','RESPONSE_SEEN','SETTLED'):
                    kind='AnalysisRepresentationBound' if isinstance(error,AnalysisRepresentationBound) else _safe_error_kind(error)
                    fields={'observed_cost':known,'generation_id':generation,'error_type':kind}
                    if billing is not None:fields['billing']=billing
                    owner.transition(receipt,'UNCERTAIN',**fields)
            except BaseException:pass
        try:row=_row(owner,receipt) if receipt else None
        except BaseException:row=None
        diagnostic=_failure_diagnostic(error,stage,cap.posts if cap else 0,phase_stats,receipt,known,row)
        failure={'original_study_preserved':True,'historical_holds_released':False,
                 'provider_bodies':dict(provider_bodies),
                 'missing_body_semantics':'MISSING means no acknowledged complete durable canonical body; partial or unacknowledged files are not claimed complete','provider_representation':PROVIDER_REPRESENTATION,'status':'STOPPED_NO_RETRY','diagnostic':diagnostic,
                 'model_POST_attempts':post_attempts,'statistics_GET_attempts':statistics_attempts,
                 'catalog_GET_attempts':catalog_attempts,'analysis_status':'NOT_RUN','analysis':None}
        try:
            terminal=_terminal(owner,raw_protocol,terms,response_provenance=response_provenance)
            failure['authenticated_terminal']=terminal
        except BaseException:pass
        try:journal.write('failure.json',failure)
        except BaseException:pass
        if isinstance(error,(KeyboardInterrupt,SystemExit)):raise KeyboardInterrupt() from None
        raise _SafeExecutionFailure(diagnostic) from None
    finally:journal.close()
