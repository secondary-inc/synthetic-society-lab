"""Authored finite E02 client candidate. Actual factory remains denied.

Only a separately reviewed release may activate any production boundary. Tests
replace owner, catalog, credential and transport; no inference is authorized here.
Canonical retained response objects are not original HTTP wire bytes.
"""
from decimal import Decimal
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import time

from ..common import canonical_bytes, canonical_hash, redact
from ..model import ExecutionBlocked
from ..owner_budget_v3 import freeze, utc
from ..production_owner_v4 import new_operation_time
from ..production_admission_v4 import _fetch_public_catalog, _read_environment_key
from ..production_price_v4 import fresh_proof
from ..production_compatibility_transport_v4_2 import _CompatibilityTransportV4_2
from ..production_compatibility_v4_2_1 import (
    _no_secret, _observed_cost, _cost, _usage_bounds, _auxiliary_observation,
    _safe_error_kind, _failure_diagnostic, _SafeExecutionFailure)
from .exploratory_response_v1 import parse_survey_response as parse_survey
from .exploratory_metadata_v1 import normalize_statistics,response_model_allowed
from .exploratory_owner_v1 import AnalysisRepresentationBound
from .exploratory_live_requests_v1 import PROTOCOL_SHA, PROJECTION_SHA, ASSIGNMENT_SHA, _protocol
from .exploratory_sequence_v1 import next_action
from .exploratory_pilot_analysis_v1 import analyze

_SEAL = object()
JOURNAL_BYTES = 268435456
ARTIFACT_BYTES = 2000000
ARTIFACTS = 256
MINIMUM_FREE_BYTES = 536870912
PROVIDER_REPRESENTATION = 'CANONICAL_PARSED_PROVIDER_OBJECT_V1'


def open_actual(*args, **kwargs):
    raise ExecutionBlocked('limited pilot client has no actual terminal release')


def _owner():
    from .exploratory_owner_v1 import StudyOwnerV1
    return StudyOwnerV1()


def _transport(credential):
    return _CompatibilityTransportV4_2(credential)



def _no_provider_reasoning(response):
    """Reject unsupported provider traces before persistence, not as misses.

    Inspect normalized OpenRouter reasoning/reasoning_details and provider text
    aliases, including every returned choice and any unexpected stream delta.
    Do not inspect questionnaire strings as provider metadata. Structured
    reasoning details (text, summary or encrypted) are all out of scope.
    """
    text_fields=('reasoning','reasoning_content','analysis','thinking')
    structured_fields=('reasoning_details','analysis_details','thinking_blocks')
    containers=[response]
    choices=response.get('choices')
    if type(choices) is list:
        for choice in choices:
            if type(choice) is dict:
                containers.append(choice)
                for key in ('message','delta'):
                    if type(choice.get(key)) is dict:containers.append(choice[key])
    for container in containers:
        for key in text_fields:
            if key in container:
                value=container[key]
                if value is not None and not(type(value) is str and value==''):
                    raise ExecutionBlocked('unsupported provider reasoning content')
        for key in structured_fields:
            if key in container:
                value=container[key]
                if value is not None and not(type(value) is list and not value):
                    raise ExecutionBlocked('unsupported provider reasoning content')


def _no_unsupported_response_activity(response):
    """Recovery-only guard for affirmative tools/media/search observations."""
    fields=('tool_calls','function_call','tool_output','tool_outputs','tool_results',
            'audio','images','image','annotations','citations','search_results','web_search_results')
    counts=('num_search_results','num_fetches','num_media_prompt','num_media_completion',
            'num_input_audio_prompt','native_tokens_completion_images','num_tool_calls')
    containers=[response]
    if type(response.get('choices')) is list:
        for choice in response['choices']:
            if type(choice) is dict:
                containers.append(choice)
                for key in ('message','delta'):
                    if type(choice.get(key)) is dict:containers.append(choice[key])
    for item in containers:
        if item.get('role') in ('tool','function'):
            raise ExecutionBlocked('unsupported tool response role')
        for key in fields:
            if key not in item:continue
            value=item[key]
            if value is None or (type(value) in (str,list,dict) and not value):continue
            raise ExecutionBlocked('unsupported response tools/media/search activity')
        for key in counts:
            if key in item and item[key] is not None and not(type(item[key]) is int and item[key]==0):
                raise ExecutionBlocked('unsupported response activity counter')
        content=item.get('content')
        if type(content) is list:
            for part in content:
                if type(part) is dict and part.get('type') in ('image','image_url','input_audio','audio','output_audio',
                    'tool_use','tool_result','function_call','web_search','search_result'):
                    raise ExecutionBlocked('unsupported structured response activity')


def phase_record(compiled, parsed):
    record={'execution_order':compiled['execution_order'],'phase':compiled['phase'],
            'payload_sha256':compiled['payload_sha256'],
            'status':parsed['status'],'answer':parsed['answer']}
    if len(canonical_bytes(record))>3072:
        raise AnalysisRepresentationBound('phase export bound exceeded; analysis NOT_RUN')
    return record


def _regular_directory(path):
    for item in (path,*path.parents):
        if not stat.S_ISDIR(item.lstat().st_mode):
            raise ExecutionBlocked('journal ancestor must be a real directory')


class _Journal:
    def __init__(self,owner,run_id,packet):
        if type(run_id) is not str or re.fullmatch(r'[A-Za-z0-9_-]{1,128}',run_id) is None:
            raise ExecutionBlocked('fixed safe run ID required')
        directory=Path(owner.directory);_regular_directory(directory)
        if shutil.disk_usage(directory).free<MINIMUM_FREE_BYTES:
            raise ExecutionBlocked('full-run free capacity unavailable')
        base=directory/'limited-pilot-v1'
        if base.exists() or base.is_symlink():_regular_directory(base)
        else:base.mkdir(mode=0o700)
        self.path=base/run_id;self.path.mkdir(mode=0o700,exist_ok=False)
        self.lock=None
        try:
            self.lock=(self.path/'run.lock').open('xb');os.chmod(self.path/'run.lock',0o600)
            fcntl.flock(self.lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.write('packet.json',packet)
            self.write('retention.json',{'provider_representation':PROVIDER_REPRESENTATION,
                                        'original_HTTP_wire_bytes_retained':False})
        except BaseException:
            self.close();raise

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
        if len(entries)+1>ARTIFACTS or total+len(raw)>JOURNAL_BYTES or shutil.disk_usage(self.path).free<MINIMUM_FREE_BYTES:
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

    def close(self):
        if self.lock is not None:self.lock.close()


class _Phase:
    def __init__(self,packet,proof):
        self.started=time.monotonic();self.maximum_mono=self.started;self.maximum_utc=new_operation_time()
        self.statistics_waited=False
        self.packet=packet;self.proof=proof
        self.gate(full=True)

    def gate(self,*,full=False,reserve_seconds=0):
        now=new_operation_time();mono=time.monotonic();elapsed=mono-self.started
        policy=self.packet['policy'];terms=self.packet['price_release']['terms']
        remaining=120 if full else reserve_seconds
        deadlines=[utc(policy['valid_until_utc']),utc(terms['valid_until_utc'])]
        observed=utc(self.proof['observed_at_utc'])
        if (not 0<=reserve_seconds<=120 or not 0<=elapsed<120-reserve_seconds or
            mono<self.maximum_mono or now<self.maximum_utc or
            not utc(policy['valid_from_utc'])<=now or not utc(terms['valid_from_utc'])<=now or
            any((end-now).total_seconds()<=remaining for end in deadlines) or
            not 0<=(now-observed).total_seconds()<=900-remaining):
            raise ExecutionBlocked('phase, price or authority deadline; no further dispatch')
        self.maximum_utc=now;self.maximum_mono=mono

    def wait_for_statistics(self):
        """One fixed initial visibility allowance, not a GET retry schedule."""
        if self.statistics_waited:raise ExecutionBlocked('visibility allowance already used')
        self.statistics_waited=True
        self.gate(reserve_seconds=50)  # 10 wait + 30 HTTP + 10 checkpoint.
        start=time.monotonic()
        for _ in range(12):
            remaining=10-(time.monotonic()-start)
            if remaining<=0:
                self.gate(reserve_seconds=40)
                return
            self.gate(reserve_seconds=40+remaining)
            time.sleep(min(1,remaining))
        raise ExecutionBlocked('visibility clock did not progress; no lookup')


class _Capability:
    def __init__(self,seal,journal,phase,transport,ack):
        if seal is not _SEAL:raise ExecutionBlocked('opaque client capability required')
        self.journal=journal;self.phase=phase;self.transport=transport
        self.ack=freeze(ack);self.used=False;self.posts=0

    def post(self):
        self.phase.gate()
        if self.used:raise ExecutionBlocked('one-shot phase capability already consumed')
        self.used=True
        self.journal.write(self.ack['receipt']+'-dispatch.json',
            {'receipt':self.ack['receipt'],'head':self.ack['head'],
             'context_hash':canonical_hash(self.ack['context']),
             'payload_sha256':self.ack['request']['payload_sha256'],
             'status':'ACKNOWLEDGED_POST_INTENT_CONSUMED'})
        self.phase.gate();self.posts=1
        return self.transport.post_bytes(canonical_bytes(self.ack['request']['payload']))


def _validate_packet(packet,*,expected_packet_hash):
    from .exploratory_owner_v1 import validate_packet
    return validate_packet(packet,expected_packet_hash=expected_packet_hash)


def _protocol_bytes():
    return (Path(__file__).resolve().parents[3]/'configs/e02_exploratory_live_pilot_v1_1.json').read_bytes()


def _row(owner,receipt):
    return next(r for r in owner.snapshot()['charges'] if r['id']==receipt)


def _terminal(owner,protocol_bytes,terms,*,response_provenance):
    snapshot=freeze(owner.study_snapshot())
    if snapshot['analysis_status']=='NOT_RUN':
        # The oversized answer was never committed. Authenticate the preceding
        # prefix, then export only the owner's failed/null financial disposition
        # and unattempted tail. Do not call either terminal evaluator.
        transcript=snapshot['transcript']
        if snapshot['status']!='STOPPED' or not transcript:
            raise ExecutionBlocked('stopped financial disposition required for NOT_RUN')
        failed=transcript[-1]
        if (set(failed)!={'execution_order','phase','payload_sha256','status','answer'} or
            failed['status'] not in ('FAILED_UNCERTAIN','CANCELLED') or failed['answer'] is not None):
            raise ExecutionBlocked('uncommitted answer cannot enter NOT_RUN export')
        prefix=next_action(protocol_bytes,terms,canonical_bytes(transcript[:-1]))
        if prefix['status']!='REQUEST_READY_NOT_ADMITTED':
            raise ExecutionBlocked('failed disposition has no expected next request')
        request=prefix['request']
        if any(failed[k]!=request[k] for k in ('execution_order','phase','payload_sha256')):
            raise ExecutionBlocked('failed phase identity differs from authenticated prefix')
        records=prefix['derived_records']+[{k:failed[k] for k in ('execution_order','phase','status','answer')}]
        seen={(r['execution_order'],r['phase']) for r in records}
        for job in _protocol(protocol_bytes)['assignments']:
            for phase in ('pre','post'):
                if (job['execution_order'],phase) not in seen:
                    records.append({'execution_order':job['execution_order'],'phase':phase,
                                    'status':'NOT_ATTEMPTED','answer':None})
        envelope={'response_provenance':response_provenance,'protocol_sha256':PROTOCOL_SHA,
                  'projection_sha256':PROJECTION_SHA,'assignment_sha256':ASSIGNMENT_SHA,'records':records}
        if len(records)!=32 or len(canonical_bytes(envelope))>131072:
            raise AnalysisRepresentationBound('NOT_RUN disposition envelope exceeds bound')
        return {'status':snapshot['status'],'snapshot':snapshot,'response_envelope':envelope,
                'analysis_status':'NOT_RUN','analysis':None}
    derived=next_action(protocol_bytes,terms,canonical_bytes(snapshot['transcript']))
    if derived['status'] not in ('COMPLETE','STOPPED'):
        raise ExecutionBlocked('authenticated snapshot is not terminal')
    # Construct a new envelope from authenticated owner records and independently
    # derived skips/unattempted tail. Never relabel a returned MOCK analysis.
    envelope={'response_provenance':response_provenance,'protocol_sha256':PROTOCOL_SHA,
              'projection_sha256':PROJECTION_SHA,'assignment_sha256':ASSIGNMENT_SHA,
              'records':derived['response_envelope']['records']}
    if len(canonical_bytes(envelope))>131072:
        raise AnalysisRepresentationBound('terminal representation bound; analysis NOT_RUN')
    return {'status':snapshot['status'],'snapshot':snapshot,'analysis_status':'READY',
            'response_envelope':envelope,'analysis':analyze(protocol_bytes,canonical_bytes(envelope))}


def execute_authored(packet,*,expected_packet_hash,response_provenance='MOCK'):
    """Private candidate, with replaceable authored boundaries for tests.

    Actual terminal factory is denied. A separately reviewed caller must verify
    provenance, code and exact release before selecting EXPLORATORY_REAL_MODEL.
    There are no caller-supplied phase, payload, baseline, owner or output paths.
    """
    if response_provenance not in ('MOCK','EXPLORATORY_REAL_MODEL'):
        raise ExecutionBlocked('explicit closed response provenance required')
    # Root validator detaches the whole acyclic packet and exact code closure
    # before owner discovery, output, catalog, credential or transport callbacks.
    packet=_validate_packet(freeze(packet),expected_packet_hash=expected_packet_hash)
    if canonical_hash(packet)!=expected_packet_hash:
        raise ExecutionBlocked('detached packet hash differs')
    protocol_bytes=_protocol_bytes();terms=packet['price_release']['terms']
    recovery=packet['policy'].get('kind')=='LIMITED_PILOT_RECOVERY_POLICY_V1'
    # Verify accepted protocol and full maximum finite envelope before I/O.
    next_action(protocol_bytes,terms,b'[]')
    now=new_operation_time()
    if any(not utc(v['valid_from_utc'])<=now or (utc(v['valid_until_utc'])-now).total_seconds()<=120
           for v in (packet['policy'],terms)):
        raise ExecutionBlocked('full phase does not fit current authority/terms')
    owner=_owner();journal=_Journal(owner,packet['policy']['run_id'],packet)
    credential=None;cap=None;receipt=None;known=None;generation=None;billing=None
    post_attempts=0;statistics_attempts=0;catalog_attempts=0;phase=None
    stage='CATALOG';phase_stats=0
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
        for _ in range(33):
            receipt=None;known=None;generation=None;billing=None;cap=None;phase_stats=0
            provider_bodies={'response':'MISSING','statistics':'MISSING'}
            stage='PHASE_ADMISSION'
            snapshot=owner.study_snapshot()
            if snapshot['status'] in ('COMPLETE','STOPPED'):
                terminal=_terminal(owner,protocol_bytes,terms,response_provenance=response_provenance)
                terminal.update(provider_representation=PROVIDER_REPRESENTATION,model_POST_attempts=post_attempts,statistics_GET_attempts=statistics_attempts,
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
                terminal=_terminal(owner,protocol_bytes,terms,response_provenance=response_provenance)
                terminal.update(provider_representation=PROVIDER_REPRESENTATION,model_POST_attempts=post_attempts,statistics_GET_attempts=statistics_attempts,
                                catalog_GET_attempts=catalog_attempts,path=str(journal.path))
                journal.write('summary.json',terminal)
                return terminal
            if ack['status']!='RESERVED' or post_attempts>=32:
                raise ExecutionBlocked('finite reservation acknowledgement required')
            receipt=ack['receipt'];compiled=freeze(ack['request']);context=freeze(ack['context'])
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
            if recovery:_no_unsupported_response_activity(response)
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
            valid_model=(response_model_allowed(response.get('model'),terms['model']) if recovery
                         else response.get('model')==terms['model'])
            if generation is None or not valid_model:
                raise ValueError('unverified generation/model')
            output={'status':parsed['status'],'answer':parsed['answer'],
                    'response_raw_sha256':hashlib.sha256(response_raw).hexdigest()}
            owner.transition(receipt,'RESPONSE_SEEN',generation_id=generation,
                             output_hash=canonical_hash(output),observed_cost=known)
            if recovery:
                stage='STATISTICS_VISIBILITY_WAIT';phase.wait_for_statistics()
            stage='STATISTICS_CLAIM';phase.gate();owner.claim_statistics_lookup(receipt)
            phase.gate();stage='STATISTICS_GET'
            if statistics_attempts>=32:raise ExecutionBlocked('statistics request count exceeded')
            phase_stats=1;statistics_attempts+=1
            result=transport.statistics(generation);stage='STATISTICS_VALIDATION'
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
            if recovery:
                normalized=normalize_statistics(stats,generation_id=generation,requested_model=terms['model'],
                    reported_provider=terms['reported_provider'],input_bound=context['envelope']['input_token_bound'],
                    output_bound=context['envelope']['max_tokens'],reserved_microusd=context['envelope']['reserved_microusd'])
                billing=normalized['billing'];auxiliary=normalized['telemetry']
            else:
                if (stats.get('model')!=terms['model'] or stats.get('provider_name')!=terms['reported_provider'] or
                    stats.get('is_byok') is not False):
                    raise ValueError('actual provider/billing unverified')
                for field,bound in (('native_tokens_prompt',context['envelope']['input_token_bound']),
                                    ('native_tokens_completion',512),('native_tokens_reasoning',0)):
                    if type(stats.get(field)) is not int or not 0<=stats[field]<=bound:
                        raise ValueError('native usage outside released bound')
                auxiliary,valid=_auxiliary_observation(stats)
                if not valid:raise ExecutionBlocked('unsupported auxiliary activity')
                billing={k:stats[k] for k in ('id','model','provider_name','total_cost','native_tokens_prompt',
                    'native_tokens_completion','native_tokens_reasoning','is_byok')}
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
        failure={'provider_bodies':dict(provider_bodies),
                 'missing_body_semantics':'MISSING means no acknowledged complete durable canonical body; partial or unacknowledged files are not claimed complete','provider_representation':PROVIDER_REPRESENTATION,'status':'STOPPED_NO_RETRY','diagnostic':diagnostic,
                 'model_POST_attempts':post_attempts,'statistics_GET_attempts':statistics_attempts,
                 'catalog_GET_attempts':catalog_attempts,'analysis_status':'NOT_RUN','analysis':None}
        try:
            terminal=_terminal(owner,protocol_bytes,terms,response_provenance=response_provenance)
            failure['authenticated_terminal']=terminal
        except BaseException:pass
        try:journal.write('failure.json',failure)
        except BaseException:pass
        if isinstance(error,(KeyboardInterrupt,SystemExit)):raise KeyboardInterrupt() from None
        raise _SafeExecutionFailure(diagnostic) from None
    finally:journal.close()
