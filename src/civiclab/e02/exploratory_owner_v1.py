"""Candidate original-owner study successor. Authored admission only.

Actual release/factory is denied. The original owner, prefix, UNKNOWN charge and
true unfinished counts are never replaced or hidden. Local hash bindings assume
the declared trusted workflow, not hostile complete-store replacement security.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from ..common import canonical_bytes, canonical_hash, sha256_file, atomic_json
from ..model import ExecutionBlocked
from ..owner_budget_v3 import freeze, digest, utc
from ..production_owner_v4 import (ProductionOwnerV4, base_context, validate_row,
                                    new_operation_time, price_proof_key)
from ..additional_compatibility_owner_v1 import _AdditionalOwnerV1, OLD_RECEIPT
from ..production_price_v4 import validate_terms, validate_decision
from ..production_compatibility_v4_2_1 import _answer, _cost, _usage_bounds, _auxiliary_observation
from .exploratory_live_requests_v1 import PROTOCOL_SHA, PROJECTION_SHA, ASSIGNMENT_SHA
from .exploratory_sequence_v1 import next_action
from .exploratory_response_v1 import parse_survey_response

START = 'LIMITED_STUDY_START'
GRANT = 'LIMITED_STUDY_GRANT'
COMMIT = 'LIMITED_STUDY_COMMIT'
ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT/'configs/e02_exploratory_live_pilot_v1_1.json'
LIMITS = dict(zip(('shared_microusd study_microusd module_microusd lifetime_dispatches '
    'study_dispatches study_statistics_GETs catalog_GETs per_call_microusd input_bound '
    'output_tokens retries concurrency phase_seconds HTTP_seconds socket_seconds '
    'authority_seconds price_age_seconds event_limit row_limit event_bytes journal_bytes '
    'journal_artifacts artifact_bytes minimum_free_bytes').split(),
    (5000000,1000000,{'E01':0,'E02':5000000},34,32,32,1,31250,8192,512,0,1,
     120,30,15,7200,900,10000,1024,65536,268435456,256,2000000,536870912)))
P_FIELDS = set(('kind owner_id predecessor compatibility_receipt run_id protocol_sha256 '
    'projection_sha256 assignment_sha256 code_contract_hash price_release_hash limits '
    'valid_from_utc valid_until_utc').split())
W_FIELDS = set(('kind execution_order phase receipt context_hash payload_sha256 generation_id '
    'response_raw_sha256 statistics_raw_sha256 checkpoint_sha256 status answer').split())
RECOVERY_METHODS_SHA = '97ed5a2f20f38b357983b37ecc5eb27d571e3952a684670ed09903d16a7a2db9'
RECOVERY_REVIEW_SHA = 'c87d3063e61d14015efdca3a4090b08bb37d9d52ca46a8fd9727ba48fe8f0586'
MODEL_IDENTITY_SHA = 'e234cd7362756b3bfe4411471f6966bec6a2be7ef81bff131f6a4c30ea9164be'
R_FIELDS = set(('kind source_export_sha256 predecessor_hash compatibility_receipt '
    'generation_id statistics_raw_sha256 statistics decoded_output_witness '
    'original_response_retained historical_unfinished historical_consumed_microusd '
    'model_identity_source_sha256 methods_sha256 evidence_audit_sha256').split())


def recovery_mode(policy):
    return policy.get('kind') == 'LIMITED_PILOT_RECOVERY_POLICY_V1'


def _recovery_shape(recovery, policy):
    r = _closed(recovery, R_FIELDS)
    for name in ('source_export_sha256', 'predecessor_hash', 'statistics_raw_sha256',
                 'model_identity_source_sha256', 'methods_sha256', 'evidence_audit_sha256'):
        digest(r[name])
    if (r['kind'] != 'CONNECTIVITY_RECOVERY_EVIDENCE_V1'
        or r['predecessor_hash'] != canonical_hash(policy['predecessor'])
        or r['compatibility_receipt'] != policy['compatibility_receipt']
        or r['original_response_retained'] is not False
        or type(r['historical_unfinished']) is not int or r['historical_unfinished'] != 2
        or type(r['historical_consumed_microusd']) is not int or r['historical_consumed_microusd'] != 680
        or r['model_identity_source_sha256'] != MODEL_IDENTITY_SHA
        or r['methods_sha256'] != RECOVERY_METHODS_SHA
        or hashlib.sha256(canonical_bytes(r['statistics'])).hexdigest() != r['statistics_raw_sha256']):
        raise ExecutionBlocked('exact reviewed recovery evidence required')
    return r


class AnalysisRepresentationBound(ExecutionBlocked):
    """Explicit export failure; retained finance/raw evidence must not be erased."""


def _closed(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ExecutionBlocked('closed study object required')
    return value


def code_contract():
    names = ('common model owner_budget_v3 live_billing_v2 production_owner_v4 '
             'additional_compatibility_owner_v1 production_admission_v4 production_price_v4 '
             'production_compatibility_v4_2_1 production_compatibility_transport_v4_2 '
             'openrouter_http_v2 survey_execution').split()
    files = ['src/civiclab/'+name+'.py' for name in names]
    files += ['src/civiclab/e02/'+name+'.py' for name in (
        'instrument', 'exploratory_owner_v1', 'exploratory_live_client_v1',
        'exploratory_response_v1', 'exploratory_sequence_v1',
        'exploratory_live_requests_v1', 'exploratory_pilot_analysis_v1', 'exploratory_metadata_v1')]
    if (sha256_file(ROOT/'docs/E02_RECOVERY_ADMISSION_V1_PROPOSAL.md') != RECOVERY_METHODS_SHA
        or sha256_file(ROOT/'reports/INDEPENDENT_AUDIT_E02_RECOVERY_ADMISSION_V1_METHODS.json') != RECOVERY_REVIEW_SHA):
        raise ExecutionBlocked('recovery methods or independent acceptance changed')
    return {'kind':'LIMITED_PILOT_CODE_V1', 'pins':{p:sha256_file(ROOT/p) for p in files},
            'methods':{
                'base_composite_review':'de2bb25aba3e0e8ba6c8653de60ef15e8f723586afa8b70ad3ac6c05e571993b',
                'provider_representation_review':'265a343466405aa606bb9d46004590bd7bcc288b8ecd302f3cbaea5bb406684a',
                'recovery_methods':RECOVERY_METHODS_SHA, 'recovery_review':RECOVERY_REVIEW_SHA,
                'representation':'CANONICAL_PARSED_PROVIDER_OBJECT_V1'},
            'protocol_sha256':PROTOCOL_SHA, 'projection_sha256':PROJECTION_SHA,
            'assignment_sha256':ASSIGNMENT_SHA, 'limits':deepcopy(LIMITS)}


def validate_packet(packet, *, expected_packet_hash):
    """Check detached canonical packet, not human identity or raw-file bytes."""
    digest(expected_packet_hash)
    q = freeze(packet)
    _closed(q, 'kind policy review owner_assertion authority price_release terminal_review'.split())
    if len(canonical_bytes(q))>524288 or canonical_hash(q)!=expected_packet_hash or q['kind']!='LIMITED_PILOT_PACKET_V1':
        raise ExecutionBlocked('externally expected exact study packet required')
    p,r,o,a,l,t = (q[k] for k in ('policy','review','owner_assertion','authority','price_release','terminal_review'))
    _closed(p, P_FIELDS | ({'recovery'} if recovery_mode(p) else set()))
    if recovery_mode(p): _recovery_shape(p['recovery'], p)
    _closed(l,('kind','terms','interpretation'))
    validate_terms(l['terms']); validate_decision(l['interpretation'])
    terms, decision = l['terms'], l['interpretation']
    if (l['kind']!='LIMITED_PILOT_PRICE_RELEASE_V1'
        or canonical_hash(decision)!=terms['interpretation_hash']
        or terms['initial_catalog_sha256']!=decision['catalog_sha256']
        or any(terms[k]!=decision[k] for k in ('model','requested_route','reported_provider',
            'route_scope','valid_from_utc','valid_until_utc'))):
        raise ExecutionBlocked('complete matching price release required')
    digest(p['owner_id'],32); digest(p['compatibility_receipt'],32)
    if (p['kind'] not in ('LIMITED_PILOT_POLICY_V1','LIMITED_PILOT_RECOVERY_POLICY_V1') or type(p['run_id']) is not str
        or re.fullmatch(r'[0-9A-Za-z_-]{1,128}',p['run_id']) is None
        or p['protocol_sha256']!=PROTOCOL_SHA or p['projection_sha256']!=PROJECTION_SHA
        or p['assignment_sha256']!=ASSIGNMENT_SHA
        or p['code_contract_hash']!=canonical_hash(code_contract())
        or p['price_release_hash']!=canonical_hash(l)
        or canonical_hash(p['limits'])!=canonical_hash(LIMITS)):
        raise ExecutionBlocked('exact code, protocol, price and fixed caps required')
    start,end=utc(p['valid_from_utc']),utc(p['valid_until_utc'])
    if not (120 <= (end-start).total_seconds() <= 7200
            and utc(terms['valid_from_utc'])<=start<end<=utc(terms['valid_until_utc'])):
        raise ExecutionBlocked('finite study lease outside price release')
    prior=_closed(p['predecessor'],('header_hash','head','history_hash','active_approval_hash','rows_hash','statistics_claims_hash'))
    for key in ('header_hash','history_hash','active_approval_hash','rows_hash','statistics_claims_hash'):digest(prior[key])
    _closed(prior['head'],('namespace','owner_id','header_sha256','sequence','head_hash'))
    if type(prior['head']['sequence']) is not int or prior['head']['sequence']<0:
        raise ExecutionBlocked('integer predecessor head sequence required')
    _closed(r,('kind','reviewer_role','review_id','policy_hash','code_contract_hash'))
    digest(r['review_id'],32)
    if r!={**r,'kind':'INDEPENDENT_LIMITED_PILOT_REVIEW_V1','reviewer_role':'independent_auditor',
           'policy_hash':canonical_hash(p),'code_contract_hash':p['code_contract_hash']}:
        raise ExecutionBlocked('independent exact methods/code review required')
    _closed(o,('kind','policy_hash','review_hash','consent_evidence_hash','assertion','credential_state'))
    digest(o['consent_evidence_hash'])
    if o!={**o,'kind':'EXTERNAL_LIMITED_PILOT_OWNER_ASSERTION_V1','policy_hash':canonical_hash(p),
           'review_hash':canonical_hash(r),
           'assertion':'RETAIN_OLD_UNKNOWN_CHARGE_ALLOW_ONE_32_PHASE_PILOT_WITHIN_SHARED_5_USD',
           'credential_state':'OWNER_ASSERTED_ROTATED_DEDICATED_KEY_AND_PREFUNDED'}:
        raise ExecutionBlocked('external retained-unknown and credential assertion required')
    _closed(a,('kind','approval_id','policy_hash','review_hash','owner_assertion_hash','code_contract_hash'))
    digest(a['approval_id'],32)
    if a!={**a,'kind':'LIMITED_PILOT_AUTHORITY_V1','policy_hash':canonical_hash(p),
           'review_hash':canonical_hash(r),'owner_assertion_hash':canonical_hash(o),
           'code_contract_hash':p['code_contract_hash']}:
        raise ExecutionBlocked('exact acyclic study authority required')
    _closed(t,('kind','reviewer_role','review_id','packet_inputs_hash','code_contract_hash'))
    digest(t['review_id'],32)
    if t!={**t,'kind':'INDEPENDENT_LIMITED_PILOT_TERMINAL_REVIEW_V1',
           'reviewer_role':'independent_auditor',
           'packet_inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='terminal_review'}),
           'code_contract_hash':p['code_contract_hash']}:
        raise ExecutionBlocked('exact independent terminal review required')
    return q


def _protocol():
    raw=PROTOCOL_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA:raise ExecutionBlocked('protocol file changed')
    return raw


def _phase_row(w):
    return {k:w[k] for k in ('execution_order','phase','payload_sha256','status','answer')}


def _next(study):
    return next_action(_protocol(),study['packet']['price_release']['terms'],
                       canonical_bytes([_phase_row(w) for w in study['witnesses']]))


def _row_for(plan,context,receipt):
    return {'id':receipt,'context':context,'reserved':context['envelope']['reserved_microusd'],
            'charged':context['envelope']['reserved_microusd'],'status':'STARTED',
            'generation_id':None,'output_hash':None,'observed_cost':None,'checkpoint_hash':None,
            'error_type':None,'billing':None}


class StudyOwnerV1(_AdditionalOwnerV1):
    """Candidate successor; use only isolated authored OS accounts until release."""

    @staticmethod
    def _binding(row,authority):
        if authority.get('kind')!='LIMITED_PILOT_AUTHORITY_V1':
            return ProductionOwnerV4._binding(row,authority)
        base_context(row['context'])
        if row['context']['approval_hash']!=canonical_hash(authority):
            raise ExecutionBlocked('study context authority differs')

    def _entry(self,state,p):
        prior=p['predecessor']; old=state['rows'].get(OLD_RECEIPT)
        extra=state.get('additional',{})
        compat=state['rows'].get(p['compatibility_receipt'])
        if (p['owner_id']!=self.header['owner_id'] or prior['header_hash']!=canonical_hash(self.header)
            or prior['head']!=state['_prefix_head'] or prior['history_hash']!=canonical_hash(state['_prefix_events'])
            or prior['active_approval_hash']!=state['active'] or prior['rows_hash']!=canonical_hash(state['rows'])
            or prior['statistics_claims_hash']!=canonical_hash(sorted(state['statistics_claims']))
            or set(state['rows'])!={OLD_RECEIPT,p['compatibility_receipt']}
            or extra.get('batch_stage')!='COMPLETE' or extra.get('receipt')!=p['compatibility_receipt']
            or old is None or old['status']!='UNCERTAIN' or old['reserved']!=340 or old['charged']!=340
            or canonical_hash(old)!=state['_amendment_bundle']['policy']['predecessor_row_hash']
            or compat is None or state['consumed']['dispatches']!=2
            or p['run_id'] in (old['context']['run_id'],compat['context']['run_id'])
            or len(state['_prefix_events'])+193>10000 or len(state['rows'])+32>1024):
            raise ExecutionBlocked('exact immutable unknown plus committed connectivity prefix required')
        if recovery_mode(p):
            self._recovery_entry(state, p, compat)
            return
        if (compat['status']!='PHASE_COMMITTED' or compat['billing'] is None
            or compat['observed_cost'] is None or state['unfinished']!=1):
            raise ExecutionBlocked('committed compatibility prefix required')
        # A charged, committed compatibility failure is not successful JSON
        # compatibility. Read only the accepted client's fixed, bounded path and
        # authenticate its complete checkpoint against the original owner row.
        c=compat['context'];base=self.directory/'additional-test-v1'/c['run_id']
        for parent in (base,*base.parents):
            if parent.is_symlink():raise ExecutionBlocked('symlink compatibility journal refused')
        path=base/'phase.local.json'
        if path.is_symlink() or not path.is_file() or path.stat().st_size>65536:
            raise ExecutionBlocked('fixed compatibility checkpoint missing or oversized')
        with path.open('rb') as stream:raw=stream.read(65537)
        if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=compat['checkpoint_hash']:
            raise ExecutionBlocked('compatibility checkpoint bytes differ')
        from ..additional_compatibility_owner_v1 import _load
        value=_load(raw);answer=value.get('output') if type(value) is dict else None
        expected={'schema_version':1,**{k:c[k] for k in ('run_id','unit_id','phase')},
                  'receipt':compat['id'],'request_hash':c['envelope']['request_hash'],'output':answer}
        if (canonical_hash(value)!=canonical_hash(expected) or type(answer) is not dict
            or canonical_hash(answer)!=compat['output_hash'] or answer.get('status')!='VALID'
            or canonical_hash(answer.get('parsed'))!=canonical_hash({'ok':True})
            or canonical_hash(_answer({'choices':[{'message':{'content':answer.get('raw_text')}}]}))
               !=canonical_hash(answer)):
            raise ExecutionBlocked('successful bound JSON compatibility is required')

    def _recovery_entry(self, state, p, compat):
        """Admit separate evidence; never settle/reopen either historical row."""
        from .exploratory_metadata_v1 import normalize_statistics
        r = _recovery_shape(p['recovery'], p)
        c = compat['context']; witness = r['decoded_output_witness']
        if (compat['status'] != 'UNCERTAIN' or compat['reserved'] != 340 or compat['charged'] != 340
            or compat['billing'] is not None or compat['checkpoint_hash'] is not None
            or state['unfinished'] != 2
            or state['consumed'] != {'total':680, 'modules':{'E01':0,'E02':680},
                'dispatches':2,'module_dispatches':{'E01':0,'E02':2}}
            or set(state['statistics_claims']) != {compat['id']}
            or r['generation_id'] != compat['generation_id']
            or canonical_hash(witness) != compat['output_hash']
            or type(witness) is not dict or witness.get('status') != 'VALID'
            or canonical_hash(witness.get('parsed')) != canonical_hash({'ok':True})
            or canonical_hash(_answer({'choices':[{'message':{'content':witness.get('raw_text')}}]}))
                != canonical_hash(witness)):
            raise ExecutionBlocked('historical recovery identity, holds, claims or output witness differs')
        stats = r['statistics'].get('data') if type(r['statistics']) is dict else None
        normalized = normalize_statistics(stats, generation_id=compat['generation_id'],
            requested_model=c['terms']['model'], reported_provider=c['terms']['reported_provider'],
            input_bound=c['envelope']['input_token_bound'], output_bound=c['envelope']['max_tokens'],
            reserved_microusd=compat['reserved'])
        if (type(compat['observed_cost']) is not int or compat['observed_cost'] != 7
            or normalized['observed_cost_microusd'] != compat['observed_cost']):
            raise ExecutionBlocked('recovery bill and earlier rounded observation disagree')

    def _study_transition(self,event,state):
        """Reuse original predicates with an explicit study-only authority view.

        The predecessor's approvals, active epoch and approval IDs stay intact.
        The original validator only receives the already resolved study authority
        for this transition; no study authority is installed in its persisted map.
        """
        row=event['payload'].get('after')
        if row is None:  # Statistics claims do not look up an approval.
            return ProductionOwnerV4._apply(self,event,state)
        authority_hash=row['context']['approval_hash']
        authority=state['study_authorities'].get(authority_hash)
        if authority is None:raise ExecutionBlocked('study authority unknown')
        view={**state,'approvals':{authority_hash:authority}}
        ProductionOwnerV4._apply(self,event,view)
        state.update({k:v for k,v in view.items() if k!='approvals'})

    def _new_clock(self,event,state,p,proof):
        prior=state['max_clock']; now=self._clock(event,state)
        if (event['clock_status']!='OK' or now is None or (prior is not None and now<prior)
            or not utc(p['valid_from_utc'])<=now
            or (utc(p['valid_until_utc'])-now).total_seconds()<120
            or not 0<=(now-utc(proof['observed_at_utc'])).total_seconds()<=900):
            raise ExecutionBlocked('new study authority clock, lease or price age invalid')
        return now

    def _context(self,study,compiled):
        q=study['packet']; i=compiled['execution_order']; phase=compiled['phase']; before=None
        if phase=='post':
            before=next((w for w in study['witnesses'] if w['execution_order']==i and w['phase']=='pre'),None)
            if before is None:raise ExecutionBlocked('own committed baseline missing')
        plan={'kind':'LIMITED_PILOT_PHASE_PLAN_V1','authority_hash':canonical_hash(q['authority']),
            'protocol_sha256':PROTOCOL_SHA,'execution_order':i,'phase':phase,
            'unit_sha256':compiled['unit_sha256'],'payload_sha256':compiled['payload_sha256'],
            'pre_witness_hash':canonical_hash(before) if before else None}
        c={'approval_hash':plan['authority_hash'],'plan_hash':canonical_hash(plan),
            'release_hash':canonical_hash(q['price_release']),'price_proof':study['proof'],
            'run_id':q['policy']['run_id'],'unit_id':f'exploratory-{i:02d}','phase':phase,'module':'E02',
            'terms':q['price_release']['terms'],'envelope':compiled['envelope'],
            'sampling':{'seed':compiled['pair_seed'],'temperature':0,'retries':0},
            'payload_hash':compiled['payload_sha256']}
        base_context(c)
        receipt=canonical_hash({'authority_hash':plan['authority_hash'],'plan_hash':canonical_hash(plan),
                                'context_hash':canonical_hash(c)})[:32]
        return plan,c,receipt

    def _apply(self,event,state):
        kind,payload=event['kind'],event['payload']; study=state.get('study')
        if kind==START:
            _closed(payload,('packet','code_contract','fresh_proof'))
            if study is not None:raise ExecutionBlocked('study already started; no renewal')
            q=validate_packet(payload['packet'],expected_packet_hash=canonical_hash(payload['packet']))
            if payload['code_contract']!=code_contract():raise ExecutionBlocked('study code contract changed')
            self._entry(state,q['policy']); self._new_clock(event,state,q['policy'],payload['fresh_proof'])
            study={'packet':q,'proof':payload['fresh_proof'],'witnesses':[], 'receipts':[],
                   'pending':None,'initial':True,'stopped':False,'failure_reason':None,
                   'prefix_total':state['consumed']['total'],'phase_started':{},
                   'historical_unfinished':state['unfinished']}
            state['study']=study
            state['study_authorities']={canonical_hash(q['authority']):q['authority']}
            return
        if study is None:return super()._apply(event,state)
        if kind==GRANT:
            _closed(payload,('plan','context','receipt'))
            if study['pending'] is not None or study['stopped'] or state['unfinished']!=study['historical_unfinished']:
                raise ExecutionBlocked('unfinished or stopped study forbids another grant')
            compiled=_next(study)
            if compiled['status']!='REQUEST_READY_NOT_ADMITTED':raise ExecutionBlocked('study complete')
            plan,c,receipt=self._context(study,compiled['request'])
            if payload!={'plan':plan,'context':c,'receipt':receipt}:
                raise ExecutionBlocked('next phase, own witness or exact request differs')
            now=self._new_clock(event,state,study['packet']['policy'],study['proof'])
            terms=c['terms']
            if not (utc(terms['valid_from_utc'])<=now and (utc(terms['valid_until_utc'])-now).total_seconds()>=120):
                raise ExecutionBlocked('full phase outside price lease')
            amount=c['envelope']['reserved_microusd']; used=state['consumed']
            charged=sum(state['rows'][r]['charged'] for r in study['receipts'])
            if (receipt in state['rows'] or len(study['receipts'])>=32 or used['dispatches']>=34
                or amount>31250 or charged+amount>1000000 or used['total']+amount>5000000
                or used['modules']['E02']+amount>5000000 or used['modules']['E01']!=0):
                raise ExecutionBlocked('study or lifetime allowance exhausted')
            study['pending']=deepcopy(payload)
            return
        if study['pending'] is not None:
            if kind!='RESERVE':raise ExecutionBlocked('grant must atomically precede exact reservation')
            grant=study['pending']; expected=_row_for(grant['plan'],grant['context'],grant['receipt'])
            if payload!={'before_hash':None,'after':expected}:raise ExecutionBlocked('reservation differs from pending grant')
            self._new_clock(event,state,study['packet']['policy'],study['proof']);validate_row(expected)
            receipt=expected['id']; state['rows'][receipt]=deepcopy(expected)
            state['keys'].add(canonical_hash({k:expected['context'][k] for k in ('run_id','unit_id','phase','module')}))
            state['price_proofs'].add(price_proof_key(expected['context']))
            state['consumed']['total']+=expected['charged'];state['consumed']['modules']['E02']+=expected['charged']
            state['consumed']['dispatches']+=1;state['consumed']['module_dispatches']['E02']+=1
            state['unfinished']+=1;study['receipts'].append(receipt);study['pending']=None
            study['initial']=False
            study['phase_started'][receipt]=event['recorded_at_utc']
            return
        target=(payload.get('receipt') if kind=='STATISTICS_CLAIM' else payload.get('after',{}).get('id'))
        if target not in study['receipts'] or target!=study['receipts'][-1]:
            raise ExecutionBlocked('study cannot alter historical or foreign phase')
        if kind==COMMIT:
            _closed(payload,('before_hash','after','witness'));w=payload['witness'];_closed(w,W_FIELDS)
            row=state['rows'][target]; c=row['context']; after=payload['after']
            if event['clock_status']!='OK' or event['recorded_at_utc'] is None:
                raise ExecutionBlocked('successful commit requires timely verified clock')
            observed=utc(event['recorded_at_utc']); started=utc(study['phase_started'][target])
            if (not 0<=(observed-started).total_seconds()<=120
                or not utc(study['packet']['policy']['valid_from_utc'])<=observed<utc(study['packet']['policy']['valid_until_utc'])):
                raise ExecutionBlocked('late commit retains uncertain hold')
            expected={**deepcopy(row),'status':'PHASE_COMMITTED','checkpoint_hash':w['checkpoint_sha256']}
            output={k:w[k] for k in ('status','answer','response_raw_sha256')}
            if (row['status']!='SETTLED' or payload['before_hash']!=canonical_hash(row) or after!=expected
                or w['kind']!='LIMITED_PILOT_COMMITTED_WITNESS_V1' or type(w['execution_order']) is not int
                or c['unit_id']!=f"exploratory-{w['execution_order']:02d}" or w['phase']!=c['phase']
                or w['receipt']!=target or w['context_hash']!=canonical_hash(c)
                or w['payload_sha256']!=c['payload_hash'] or w['generation_id']!=row['generation_id']
                or w['status'] not in ('ANSWER','PARSE_ERROR')
                or (w['status']=='PARSE_ERROR' and w['answer'] is not None)
                or canonical_hash(output)!=row['output_hash']):
                raise ExecutionBlocked('committed witness/checkpoint/output binding differs')
            for name in ('response_raw_sha256','statistics_raw_sha256','checkpoint_sha256'):digest(w[name])
            projected={k:w[k] for k in ('execution_order','phase','status','answer')}
            if len(canonical_bytes(projected))>3072:raise AnalysisRepresentationBound('phase record exceeds reviewed bound')
            # Original row math checks statistics intent, immutable output/context,
            # generation uniqueness and no charge change. COMMIT bookkeeping has
            # the original TRANSITION missing/rollback-clock semantics.
            self._study_transition({**event,'kind':'TRANSITION',
                'payload':{'before_hash':payload['before_hash'],'after':after}},state)
            study['witnesses'].append(deepcopy(w))
            _next(study)  # Recheck exact prefix and final export under accepted evaluator.
            return
        if kind not in ('TRANSITION','STATISTICS_CLAIM'):
            raise ExecutionBlocked('study forbids renewal or unrecognized events')
        if kind=='TRANSITION' and payload.get('after',{}).get('status')=='PHASE_COMMITTED':
            raise ExecutionBlocked('study requires authenticated commit witness')
        self._study_transition(event,state)
        if state['rows'][target]['status'] in ('UNCERTAIN','OVERRUN'):
            study['stopped']=True;study['failure_reason']=state['rows'][target]['error_type']

    def _verify(self,db):
        state,head=super()._verify(db)
        if (state.get('study',{}).get('pending') is not None
            or state.get('study',{}).get('initial',False)):
            raise ExecutionBlocked('partial study batch refused')
        return state,head

    def _append_batch(self,db,bodies,state,head):
        previous=head['head_hash']
        if head['sequence']+len(bodies)>=10000:raise ExecutionBlocked('owner history capacity exhausted')
        for offset,body in enumerate(bodies,1):
            event={'sequence':head['sequence']+offset,'previous':previous,'body':body}; h=canonical_hash(event)
            encoded=json.dumps(event,sort_keys=True)
            if len(encoded.encode())>65536:raise ExecutionBlocked('owner event byte bound exceeded')
            db.execute('INSERT INTO events VALUES (?,?,?)',(event['sequence'],encoded,h))
            if body['kind'] in ('RESERVE',COMMIT):
                row=body['payload']['after']
                db.execute('INSERT OR REPLACE INTO charges VALUES (?,?)',(row['id'],json.dumps(row,sort_keys=True)))
            previous=h
        db.commit()
        newhead={**head,'sequence':head['sequence']+len(bodies),'head_hash':previous}
        atomic_json(self.anchor,newhead)
        checked,actual=self._verify(db)
        if actual!=newhead:raise ExecutionBlocked('study acknowledgement readback differs')
        return checked,newhead

    def reserve_next(self,packet,proof,*,expected_packet_hash,transport_ready):
        q=validate_packet(packet,expected_packet_hash=expected_packet_hash);proof=freeze(proof)
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db);bodies=[]
            study=state.get('study')
            if study is None:
                payload={'packet':q,'code_contract':code_contract(),'fresh_proof':proof}
                body=self._event(START,payload,state,new=True);self._apply(body,state);bodies.append(body)
                study=state['study']
            elif study['packet']!=q or study['proof']!=proof:
                raise ExecutionBlocked('study packet/proof cannot renew or change')
            if study['stopped']:return self._snapshot(state)
            next_state=_next(study)
            if next_state['status']!='REQUEST_READY_NOT_ADMITTED':return self._snapshot(state)
            compiled=next_state['request'];plan,c,receipt=self._context(study,compiled)
            if transport_ready(freeze(c)) is not True:raise ExecutionBlocked('transport readiness unavailable')
            # Recheck all static bindings after the only authored callback and
            # before any financial insert; never trust caller aliases over I/O.
            validate_packet(q,expected_packet_hash=expected_packet_hash)
            for kind,payload in ((GRANT,{'plan':plan,'context':c,'receipt':receipt}),
                ('RESERVE',{'before_hash':None,'after':_row_for(plan,c,receipt)})):
                body=self._event(kind,payload,state,new=True);self._apply(body,state);bodies.append(body)
            checked,newhead=self._append_batch(db,bodies,state,head)
            if checked['rows'][receipt]!=_row_for(plan,c,receipt):raise ExecutionBlocked('reserved row readback differs')
            return {'status':'RESERVED','receipt':receipt,'head':newhead,'context':c,'request':compiled,'plan':plan}

    def _journal(self,run_id):
        path=self.directory/'limited-pilot-v1'/run_id
        for parent in (path,*path.parents):
            if parent.is_symlink():raise ExecutionBlocked('symlink journal refused')
        return path

    def commit_survey(self,receipt):
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db);study=state.get('study')
            if study is None or not study['receipts'] or receipt!=study['receipts'][-1]:
                raise ExecutionBlocked('current study receipt required')
            row=state['rows'][receipt];c=row['context'];base=self._journal(c['run_id']); raw={};values={}
            for key in ('response','statistics','checkpoint'):
                path=base/(receipt+'-'+key+'.json')
                if path.is_symlink() or not path.is_file() or path.stat().st_size>2000000:
                    raise ExecutionBlocked('bounded fixed checkpoint/body missing')
                with path.open('rb') as stream: raw[key]=stream.read(2000001)
                if len(raw[key])>2000000:raise ExecutionBlocked('body changed beyond bound')
                from ..additional_compatibility_owner_v1 import _load
                values[key]=_load(raw[key]);canonical_bytes(values[key])
                if canonical_bytes(values[key])!=raw[key]:
                    raise ExecutionBlocked('retained body/checkpoint must use exact canonical representation')
            if type(values['response']) is not dict:
                raise ExecutionBlocked('retained response object required')
            # Runtime import avoids a module cycle while reusing the client's
            # exact pinned text-only activity guard at the final commit boundary.
            from .exploratory_live_client_v1 import _no_provider_reasoning
            _no_provider_reasoning(values['response'])
            if recovery_mode(study['packet']['policy']):
                from .exploratory_live_client_v1 import _no_unsupported_response_activity
                _no_unsupported_response_activity(values['response'])
            answer=parse_survey_response(values['response'])
            output={'status':answer['status'],'answer':answer['answer'],
                    'response_raw_sha256':hashlib.sha256(raw['response']).hexdigest()}
            expected={'schema_version':1,'run_id':c['run_id'],'unit_id':c['unit_id'],'phase':c['phase'],
                'receipt':receipt,'request_hash':c['envelope']['request_hash'],'output':output}
            stats=values['statistics'].get('data') if type(values['statistics']) is dict else None
            recovery = recovery_mode(study['packet']['policy'])
            if recovery:
                from .exploratory_metadata_v1 import normalize_statistics, response_model_allowed
                if not response_model_allowed(values['response'].get('model'), c['terms']['model']):
                    raise ExecutionBlocked('unreviewed response model identity')
                projection = normalize_statistics(stats, generation_id=row['generation_id'],
                    requested_model=c['terms']['model'], reported_provider=c['terms']['reported_provider'],
                    input_bound=c['envelope']['input_token_bound'], output_bound=512,
                    reserved_microusd=row['reserved'])['billing']
            else:
                projection = ({k:stats[k] for k in row['billing']}
                    if type(stats) is dict and row['billing'] is not None
                    and set(row['billing']) <= set(stats) else None)
            if (row['status']!='SETTLED' or canonical_hash(values['checkpoint'])!=canonical_hash(expected)
                or canonical_hash(output)!=row['output_hash'] or type(stats) is not dict
                or row['billing'] is None or projection is None
                or canonical_hash(projection)!=canonical_hash(row['billing'])
                or values['response'].get('id')!=row['generation_id']
                or (not recovery and values['response'].get('model')!=c['terms']['model'])):
                raise ExecutionBlocked('raw response/billing/checkpoint binding differs')
            # Independently recheck complete retained observations. In particular,
            # Python value equality must not equate JSON true with 1 or 0 with false,
            # and an added auxiliary counter cannot hide outside the billing subset.
            validate_row({**row,'billing':projection})
            if not recovery and not _auxiliary_observation(stats)[1]:
                raise ExecutionBlocked('unsupported retained auxiliary activity')
            usage=values['response'].get('usage')
            _usage_bounds(usage,c['envelope'])
            amount=_cost(stats['total_cost'])
            if (amount!=row['observed_cost'] or (type(usage) is dict and usage.get('cost') is not None
                and (_cost(usage['cost'])!=amount
                     or Decimal(str(usage['cost']))!=Decimal(str(stats['total_cost']))))):
                raise ExecutionBlocked('retained response and generation cost disagree')
            order=int(c['unit_id'].rsplit('-',1)[1])
            w={'kind':'LIMITED_PILOT_COMMITTED_WITNESS_V1','execution_order':order,'phase':c['phase'],
                'receipt':receipt,'context_hash':canonical_hash(c),'payload_sha256':c['payload_hash'],
                'generation_id':row['generation_id'],'response_raw_sha256':output['response_raw_sha256'],
                'statistics_raw_sha256':hashlib.sha256(raw['statistics']).hexdigest(),
                'checkpoint_sha256':hashlib.sha256(raw['checkpoint']).hexdigest(),
                'status':answer['status'],'answer':answer['answer']}
            after={**deepcopy(row),'status':'PHASE_COMMITTED','checkpoint_hash':w['checkpoint_sha256']}
            body=self._event(COMMIT,{'before_hash':canonical_hash(row),'after':after,'witness':w},state,new=False)
            self._apply(body,state)
            checked,_=self._append_batch(db,[body],state,head)
            return deepcopy(checked['rows'][receipt])

    def commit_phase(self,*args,**kwargs):
        raise ExecutionBlocked('study uses fixed authenticated commit_survey only')

    def _append(self,db,body,head):
        if head is not None:
            event={'sequence':head['sequence']+1,'previous':head['head_hash'],'body':body}
            if head['sequence']+1>=10000 or len(json.dumps(event,sort_keys=True).encode())>65536:
                raise ExecutionBlocked('financial tail capacity exhausted')
        return ProductionOwnerV4._append(self,db,body,head)

    def _snapshot(self,state):
        study=state.get('study');transcript=[];status='NOT_STARTED';reason=None
        if study:
            transcript=[_phase_row(w) for w in study['witnesses']]
            status='STOPPED' if study['stopped'] else 'ACTIVE';reason=study['failure_reason']
            if study['stopped']:
                row=state['rows'][study['receipts'][-1]];c=row['context']
                transcript.append({'execution_order':int(c['unit_id'].rsplit('-',1)[1]),'phase':c['phase'],
                    'payload_sha256':c['payload_hash'],'status':'FAILED_UNCERTAIN','answer':None})
            elif _next(study)['status']=='COMPLETE':status='COMPLETE'
        return {'status':status,'transcript':deepcopy(transcript),
            'consumed_microusd':deepcopy(state['consumed']),
            'study_charged_microusd':sum(state['rows'][r]['charged'] for r in study['receipts']) if study else 0,
            'study_dispatches':len(study['receipts']) if study else 0,
            'analysis_status':'NOT_RUN' if reason=='AnalysisRepresentationBound' else 'READY',
            'failure_reason':reason}

    def study_snapshot(self):
        with self._lock(),self._connect() as db:
            state,_=self._verify(db);return self._snapshot(state)


def open_actual(*args,**kwargs):
    raise ExecutionBlocked('study owner has no independently released actual factory')
