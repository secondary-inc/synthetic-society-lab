"""Append-only, same-owner continuation of one stopped half-complete pilot.

Original rows and holds are immutable. A separately authenticated recovered
answer may enter the analytical prefix without pretending the original phase
committed on time. Only the original remaining sixteen slots may be reserved.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json

from ..common import canonical_bytes, canonical_hash, sha256_file
from ..model import ExecutionBlocked
from ..owner_budget_v3 import freeze, digest
from ..production_compatibility_v4_2_1 import _usage_bounds, _cost
from .exploratory_owner_v1 import (StudyOwnerV1, ROOT, code_contract, validate_packet,
    _closed, _next, _phase_row, _protocol)
from .exploratory_sequence_v1 import next_action
from .exploratory_metadata_v1 import normalize_statistics, response_model_allowed
from .exploratory_response_v1 import parse_survey_response
from .exploratory_live_client_v1 import _no_provider_reasoning, _no_unsupported_response_activity

CONTINUE = 'LIMITED_STUDY_CONTINUATION_V1'
LIMITS = {'new_POSTs':16,'new_statistics_GETs':48,'GETs_per_generation':3,
    'POST_retries':0,'GET_retry_statuses':[404],'GET_waits_seconds':[10,10,20],
    'phase_seconds':120,'shared_microusd':5000000,'study_microusd':1000000,
    'lifetime_dispatches':34,'concurrency':1}


def continuation_contract():
    paths=['src/civiclab/e02/exploratory_continuation_owner_v1.py',
           'src/civiclab/e02/exploratory_continuation_v1.py']
    return {'kind':'E02_CONTINUATION_CODE_V1','base':code_contract(),
            'pins':{p:sha256_file(ROOT/p) for p in paths},'limits':deepcopy(LIMITS)}


def validate_bundle(bundle, *, expected_bundle_hash):
    b=freeze(bundle);digest(expected_bundle_hash)
    _closed(b,('kind','packet','predecessor','recovery','code_contract_hash','review'))
    if (canonical_hash(b)!=expected_bundle_hash or b['kind']!='E02_CONTINUATION_BUNDLE_V1'
        or len(canonical_bytes(b))>50000 or b['code_contract_hash']!=canonical_hash(continuation_contract())):
        raise ExecutionBlocked('exact bounded continuation contract required')
    validate_packet(b['packet'],expected_packet_hash=canonical_hash(b['packet']))
    p=_closed(b['predecessor'],('head','history_hash','rows_hash','study_hash','claims_hash'))
    for k in ('history_hash','rows_hash','study_hash','claims_hash'):digest(p[k])
    r=_closed(b['recovery'],('receipt','response','statistics','response_sha256','statistics_sha256'))
    digest(r['receipt'],32)
    for k in ('response','statistics'):
        digest(r[k+'_sha256'])
        if canonical_hash(r[k])!=r[k+'_sha256']:
            raise ExecutionBlocked('recovered raw evidence hash differs')
    v=_closed(b['review'],('kind','reviewer_role','review_id','inputs_hash'))
    digest(v['review_id'],32)
    if (v['kind']!='INDEPENDENT_E02_CONTINUATION_REVIEW_V1'
        or v['reviewer_role']!='independent_auditor'
        or v['inputs_hash']!=canonical_hash({k:x for k,x in b.items() if k!='review'})):
        raise ExecutionBlocked('exact independent continuation review required')
    return b


def recovered_witness(row, evidence):
    response=evidence['response'];raw_stats=evidence['statistics'];c=row['context']
    if (row['id']!=evidence['receipt'] or row['status']!='UNCERTAIN'
        or row['charged']!=row['reserved'] or row['billing'] is not None
        or row['checkpoint_hash'] is not None or c['unit_id']!='exploratory-07' or c['phase']!='post'
        or response.get('id')!=row['generation_id']
        or not response_model_allowed(response.get('model'),c['terms']['model'])):
        raise ExecutionBlocked('same failed sixteenth response required')
    _no_provider_reasoning(response);_no_unsupported_response_activity(response)
    _usage_bounds(response.get('usage'),c['envelope'])
    parsed=parse_survey_response(response)
    output={'status':parsed['status'],'answer':parsed['answer'],
            'response_raw_sha256':evidence['response_sha256']}
    if canonical_hash(output)!=row['output_hash']:
        raise ExecutionBlocked('retained failed response differs from original owner output')
    s=raw_stats.get('data')
    normalize_statistics(s,generation_id=row['generation_id'],requested_model=c['terms']['model'],
        reported_provider=c['terms']['reported_provider'],input_bound=c['envelope']['input_token_bound'],
        output_bound=c['envelope']['max_tokens'],reserved_microusd=row['reserved'])
    if (row['observed_cost']!=_cost(s['total_cost'])
        or Decimal(str(response['usage']['cost']))!=Decimal(str(s['total_cost']))):
        raise ExecutionBlocked('recovered response/billing/observed cost differs')
    return {'kind':'LIMITED_PILOT_RECOVERED_ANSWER_WITNESS_V1','execution_order':7,
        'phase':'post','receipt':row['id'],'context_hash':canonical_hash(c),
        'payload_sha256':c['payload_hash'],'generation_id':row['generation_id'],
        'response_raw_sha256':evidence['response_sha256'],
        'statistics_raw_sha256':evidence['statistics_sha256'],'checkpoint_sha256':None,
        'status':parsed['status'],'answer':parsed['answer']}


class ContinuationOwnerV1(StudyOwnerV1):
    def _apply(self,event,state):
        if event['kind']!=CONTINUE:return super()._apply(event,state)
        payload=_closed(event['payload'],('bundle','fresh_proof'))
        b=validate_bundle(payload['bundle'],expected_bundle_hash=canonical_hash(payload['bundle']))
        q=b['packet'];prior=b['predecessor'];s=state.get('study');r=b['recovery']
        if (state.get('continuation') is not None or s is None or not s['stopped']
            or s['pending'] is not None or len(s['receipts'])!=16 or len(s['witnesses'])!=15
            or state['unfinished']!=3 or state['consumed']['dispatches']!=18
            or len(state['rows'])!=18 or r['receipt']!=s['receipts'][-1]
            or q['policy']['owner_id']!=self.header['owner_id']
            or q['policy']['run_id']==s['packet']['policy']['run_id']
            or prior['head']!=state['_prefix_head']
            or prior['history_hash']!=canonical_hash(state['_prefix_events'])
            or prior['rows_hash']!=canonical_hash(state['rows'])
            or prior['study_hash']!=canonical_hash(s)
            or prior['claims_hash']!=canonical_hash(sorted(state['statistics_claims']))):
            raise ExecutionBlocked('exact stopped same-owner sixteen-phase prefix required')
        oldq=s['packet'];oldterms=oldq['price_release']['terms'];newterms=q['price_release']['terms']
        refreshed={'valid_from_utc','valid_until_utc','interpretation_hash','initial_catalog_sha256'}
        if (any(oldterms[k]!=newterms[k] for k in oldterms if k not in refreshed)
            or q['authority']['approval_id']==oldq['authority']['approval_id']
            or q['policy']['kind']!='LIMITED_PILOT_RECOVERY_POLICY_V1'
            or q['policy']['recovery']!=oldq['policy']['recovery']
            or q['policy']['predecessor']!=oldq['policy']['predecessor']
            or q['policy']['compatibility_receipt']!=oldq['policy']['compatibility_receipt']):
            raise ExecutionBlocked('only refreshed continuation authority and unchanged request terms allowed')
        row=state['rows'][r['receipt']]
        if r['receipt'] not in state['statistics_claims']:
            raise ExecutionBlocked('original generation lookup claim missing')
        w=recovered_witness(row,r);witnesses=deepcopy(s['witnesses'])+[w]
        sequence=next_action(_protocol(),newterms,canonical_bytes([_phase_row(x) for x in witnesses]))
        if (sequence['status']!='REQUEST_READY_NOT_ADMITTED'
            or sequence['request']['execution_order']!=8 or sequence['request']['phase']!='pre'):
            raise ExecutionBlocked('continuation must start at first unattempted original slot')
        self._new_clock(event,state,q['policy'],payload['fresh_proof'])
        state['continuation']={'bundle':b,'original_study':deepcopy(s),
            'original_rows_hash':canonical_hash(state['rows']),'ancestor_witnesses_hash':canonical_hash(witnesses)}
        state['study']={**deepcopy(s),'packet':q,'proof':payload['fresh_proof'],
            'witnesses':witnesses,'stopped':False,'failure_reason':None,'initial':False,
            'historical_unfinished':3}
        state['study_authorities'][canonical_hash(q['authority'])]=q['authority']

    def start_continuation(self,bundle,proof,*,expected_bundle_hash):
        b=validate_bundle(bundle,expected_bundle_hash=expected_bundle_hash);proof=freeze(proof)
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db)
            if state.get('continuation') is not None:
                raise ExecutionBlocked('continuation start already consumed')
            # Recheck all retained original successful bodies once before adopting
            # ancestry. Replay remains bound to the original authenticated events.
            s=state.get('study')
            if s is None:raise ExecutionBlocked('original study absent')
            base=self._journal(s['packet']['policy']['run_id'])
            for w in s['witnesses']:
                for kind,hashkey in (('response','response_raw_sha256'),('statistics','statistics_raw_sha256'),
                                     ('checkpoint','checkpoint_sha256')):
                    path=base/(w['receipt']+'-'+kind+'.json')
                    if path.is_symlink() or not path.is_file() or path.stat().st_size>2000000:
                        raise ExecutionBlocked('bounded ancestral body required')
                    with path.open('rb') as stream:raw=stream.read(2000001)
                    if len(raw)>2000000 or hashlib.sha256(raw).hexdigest()!=w[hashkey]:
                        raise ExecutionBlocked('ancestral body differs from committed witness')
            failed=base/(b['recovery']['receipt']+'-response.json')
            if (failed.is_symlink() or not failed.is_file() or failed.stat().st_size>2000000
                or sha256_file(failed)!=b['recovery']['response_sha256']):
                raise ExecutionBlocked('original failed response differs')
            body=self._event(CONTINUE,{'bundle':b,'fresh_proof':proof},state,new=True)
            self._apply(body,state)
            checked,_=self._append_batch(db,[body],state,head)
            return self._snapshot(checked)

    def reserve_next(self,packet,proof,*,expected_packet_hash,transport_ready):
        with self._lock(),self._connect() as db:
            state,_=self._verify(db)
            if state.get('continuation') is None:
                raise ExecutionBlocked('explicit reviewed continuation start required')
        return super().reserve_next(packet,proof,expected_packet_hash=expected_packet_hash,
                                    transport_ready=transport_ready)
