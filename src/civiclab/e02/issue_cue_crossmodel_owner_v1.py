"""Finite two-model issue-cue study on the existing append-only financial owner.

The completed original study and all historical uncertain rows stay unchanged.
This version adds one reviewed 56-call batch within the existing cumulative caps.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import re

from ..common import canonical_bytes, canonical_hash, sha256_file
from ..model import ExecutionBlocked
from ..owner_budget_v3 import freeze, digest, utc
from ..production_owner_v4 import ProductionOwnerV4, base_context, validate_row, price_proof_key
from ..production_price_v4 import validate_terms, validate_decision
from ..production_compatibility_v4_2_1 import _usage_bounds, _cost
from .exploratory_owner_v1 import ROOT, _closed, _row_for, _phase_row, _next as original_next
from .alignment_anchoring_owner_v1 import AlignmentOwnerV1, code_contract as predecessor_contract, next_action as previous_next
from .crossmodel_metadata_v1 import normalize_statistics, response_model_allowed
from .exploratory_live_client_v1 import _no_provider_reasoning, _no_unsupported_response_activity

START='CROSSMODEL_STUDY_START_V1'
GRANT='CROSSMODEL_STUDY_GRANT_V1'
COMMIT='CROSSMODEL_STUDY_COMMIT_V1'
REFRESH='CROSSMODEL_PRICE_REFRESH_V1'
AUTHORITY='CROSSMODEL_PILOT_AUTHORITY_V1'
PROTOCOL=ROOT/'configs/e02_issue_cue_crossmodel_v1.json'
LIMITS={'new_model_POSTs':56,'new_statistics_GETs':168,'catalog_GETs':4,'catalog_refresh_before_slot':28,'GETs_per_generation':3,
    'POST_retries':0,'GET_retry_statuses':[404],'GET_waits_seconds':[10,10,20],
    'phase_seconds':120,'authority_seconds':7200,'price_age_seconds':900,
    'input_tokens':8192,'output_tokens':256,'per_call_microusd':1785,
    'new_batch_microusd':100000,'cumulative_E02_microusd':1000000,
    'shared_microusd':5000000,'E01_microusd':0,'lifetime_dispatches':112,
    'concurrency':1,'journal_artifacts':768}


def code_contract():
    names=('issue_cue_crossmodel_v1','issue_cue_crossmodel_owner_v1','issue_cue_crossmodel_client_v1')
    paths=[f'src/civiclab/e02/{n}.py' for n in names]+[
        'scripts/run_issue_cue_crossmodel_once.py','scripts/run_e02_continuation_once.py',
        'scripts/collect_connectivity_billing_once.py']
    return {'kind':'CROSSMODEL_STUDY_CODE_V1','predecessor':predecessor_contract(),
        'pins':{p:sha256_file(ROOT/p) for p in paths+['src/civiclab/e02/crossmodel_price_v1.py','src/civiclab/e02/crossmodel_metadata_v1.py']},
        'protocol_sha256':sha256_file(PROTOCOL),'limits':deepcopy(LIMITS)}


def protocol_bytes():
    from .issue_cue_crossmodel_v1 import load_protocol
    raw=PROTOCOL.read_bytes();load_protocol(raw)
    return raw


def next_action(study):
    from .issue_cue_crossmodel_v1 import next_action as plan
    return plan(protocol_bytes(),{k:v['terms'] for k,v in study['packet']['price_release'].items()},
                canonical_bytes([_phase_row(w) for w in study['witnesses']]))


def validate_packet(packet,*,expected_packet_hash):
    q=freeze(packet);digest(expected_packet_hash)
    _closed(q,('kind','policy','authority','price_release','review'))
    if (q['kind']!='CROSSMODEL_STUDY_PACKET_V1' or canonical_hash(q)!=expected_packet_hash
        or len(canonical_bytes(q))>65000):raise ExecutionBlocked('exact finite follow-up packet required')
    p,a,l,r=(q[k] for k in ('policy','authority','price_release','review'))
    _closed(p,('kind','owner_id','run_id','valid_from_utc','valid_until_utc','predecessor',
        'limits','protocol_sha256','code_contract_hash','price_release_hash','consent_evidence_hash'))
    digest(p['owner_id'],32);digest(p['consent_evidence_hash'])
    if (p['kind']!='CROSSMODEL_STUDY_POLICY_V1' or type(p['run_id']) is not str
        or re.fullmatch(r'[A-Za-z0-9_-]{1,128}',p['run_id']) is None
        or p['limits']!=LIMITS or canonical_hash(p['limits'])!=canonical_hash(LIMITS)
        or p['protocol_sha256']!=sha256_file(PROTOCOL)
        or p['code_contract_hash']!=canonical_hash(code_contract())
        or p['price_release_hash']!=canonical_hash(l)):
        raise ExecutionBlocked('frozen follow-up code/protocol/caps differ')
    protocol_bytes()
    _closed(l,('A','B'))
    bindings={'A':('openai/gpt-4.1-nano','azure','Azure','PROVIDER_FAMILY'),
              'B':('qwen/qwen3-30b-a3b-instruct-2507','nebius/fp8','Nebius','ENDPOINT_PREFIX')}
    start,end=utc(p['valid_from_utc']),utc(p['valid_until_utc'])
    for role,release in l.items():
        _closed(release,('kind','terms','interpretation'));terms=release['terms'];d=release['interpretation']
        validate_terms(terms);validate_decision(d)
        if (release['kind']!='LIMITED_PILOT_PRICE_RELEASE_V1'
            or canonical_hash(d)!=terms['interpretation_hash']
            or terms['initial_catalog_sha256']!=d['catalog_sha256']
            or any(terms[k]!=d[k] for k in ('model','requested_route','reported_provider',
                'route_scope','valid_from_utc','valid_until_utc'))
            or tuple(terms[k] for k in ('model','requested_route','reported_provider','route_scope'))!=bindings[role]):
            raise ExecutionBlocked('exact two-model route price releases required')
        if not (120<=(end-start).total_seconds()<=7200
                and utc(terms['valid_from_utc'])<=start<end<=utc(terms['valid_until_utc'])):
            raise ExecutionBlocked('finite two-model lease required')
    prior=_closed(p['predecessor'],('head','history_hash','rows_hash','study_hash','continuation_hash','alignment_hash','claims_hash','consumed'))
    for k in ('history_hash','rows_hash','study_hash','continuation_hash','alignment_hash','claims_hash'):digest(prior[k])
    _closed(a,('kind','approval_id','policy_hash','code_contract_hash'));digest(a['approval_id'],32)
    if a!={**a,'kind':AUTHORITY,'policy_hash':canonical_hash(p),'code_contract_hash':p['code_contract_hash']}:
        raise ExecutionBlocked('follow-up authority binding differs')
    _closed(r,('kind','reviewer_role','review_id','inputs_hash'));digest(r['review_id'],32)
    if r!={**r,'kind':'INDEPENDENT_CROSSMODEL_STUDY_REVIEW_V1','reviewer_role':'independent_auditor',
           'inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='review'})}:
        raise ExecutionBlocked('exact independently reviewed follow-up required')
    return q


class CrossmodelOwnerV1(AlignmentOwnerV1):
    @staticmethod
    def _binding(row,authority):
        if authority.get('kind')!=AUTHORITY:return AlignmentOwnerV1._binding(row,authority)
        base_context(row['context'])
        if row['context']['approval_hash']!=canonical_hash(authority):
            raise ExecutionBlocked('follow-up financial authority differs')

    def _context(self,study,compiled):
        if study['packet']['kind']!='CROSSMODEL_STUDY_PACKET_V1':
            return super()._context(study,compiled)
        q=study['packet'];order=compiled['execution_order'];phase=compiled['phase']
        before=None
        if phase=='post':
            baseline_order=compiled['baseline_execution_order']
            before=next((w for w in study['witnesses']
                if w['execution_order']==baseline_order and w['phase']=='pre'),None)
            if before is None:raise ExecutionBlocked('own authenticated baseline witness required')
        plan={'kind':'CROSSMODEL_PHASE_PLAN_V1','authority_hash':canonical_hash(q['authority']),
            'protocol_sha256':q['policy']['protocol_sha256'],'execution_order':order,'phase':phase,
            'unit_sha256':compiled['unit_sha256'],'payload_sha256':compiled['payload_sha256'],
            'witness_prefix_hash':canonical_hash(study['witnesses']),
            'pre_witness_hash':canonical_hash(before) if before else None}
        c={'approval_hash':plan['authority_hash'],'plan_hash':canonical_hash(plan),
            'release_hash':canonical_hash(q['price_release']),'price_proof':study['proofs'][compiled['model_key']],
            'run_id':q['policy']['run_id'],'unit_id':f'crossmodel-{order:02d}', 'phase':phase,'module':'E02',
            'terms':q['price_release'][compiled['model_key']]['terms'],'envelope':compiled['envelope'],
            'sampling':{'seed':compiled['pair_seed'],'temperature':0,'retries':0},
            'payload_hash':compiled['payload_sha256']}
        base_context(c)
        receipt=canonical_hash({'authority_hash':plan['authority_hash'],'plan_hash':canonical_hash(plan),
            'context_hash':canonical_hash(c)})[:32]
        return plan,c,receipt

    def _transition_view(self,event,state):
        study=state.get('issue_cue_crossmodel')
        if study is None:return super()._transition_view(event,state)
        authority=study['packet']['authority'];h=canonical_hash(authority)
        row=event['payload'].get('after')
        if row is not None and row['context']['approval_hash']!=h:
            raise ExecutionBlocked('foreign follow-up authority')
        view={**state,'approvals':{h:authority}}
        ProductionOwnerV4._apply(self,event,view)
        state.update({k:v for k,v in view.items() if k!='approvals'})

    def _apply(self,event,state):
        kind,payload=event['kind'],event['payload'];study=state.get('issue_cue_crossmodel')
        if kind==START:
            _closed(payload,('packet','fresh_proofs'))
            q=validate_packet(payload['packet'],expected_packet_hash=canonical_hash(payload['packet']))
            p=q['policy'];prior=p['predecessor'];old=state.get('study');aligned=state.get('alignment_followup')
            if (study is not None or old is None or original_next(old)['status']!='COMPLETE'
                or old['stopped'] or len(old['witnesses'])!=32 or state['unfinished']!=3
                or aligned is None or aligned['stopped'] or previous_next(aligned)['status']!='COMPLETE'
                or state['consumed']['dispatches']!=56 or len(state['rows'])!=56
                or p['owner_id']!=self.header['owner_id']
                or canonical_hash(prior)!=canonical_hash({'head':state['_prefix_head'],'history_hash':canonical_hash(state['_prefix_events']),
                    'rows_hash':canonical_hash(state['rows']),'study_hash':canonical_hash(old),
                    'continuation_hash':canonical_hash(state.get('continuation')),
                    'alignment_hash':canonical_hash(aligned),
                    'claims_hash':canonical_hash(sorted(state['statistics_claims'])),'consumed':state['consumed']})
                or any(row['context']['run_id']==p['run_id'] for row in state['rows'].values())
                or state['consumed']['total']>=1000000 or state['consumed']['modules']['E01']!=0):
                raise ExecutionBlocked('exact complete original same-owner ancestry required')
            self._new_proofs_clock(event,state,p,payload['fresh_proofs'],q['price_release'])
            state['issue_cue_crossmodel']={'packet':q,'proofs':payload['fresh_proofs'],'refreshed':False,'witnesses':[],
                'receipts':[],'pending':None,'stopped':False,'failure_reason':None,'phase_started':{},
                'initial':False,'prefix_total':state['consumed']['total'],'historical_unfinished':3}
            return
        if study is None:return super()._apply(event,state)
        if kind==REFRESH:
            _closed(payload,('fresh_proofs','next_execution_order'))
            action=next_action(study)
            if (study['refreshed'] or study['stopped'] or study['pending'] is not None
                or state['unfinished']!=3 or action['status']!='REQUEST_READY_NOT_ADMITTED'
                or action['request']['execution_order']<28
                or payload['next_execution_order']!=action['request']['execution_order']
                or any(int(state['rows'][r]['context']['unit_id'].rsplit('-',1)[1])>=28 for r in study['receipts'])):
                raise ExecutionBlocked('single scheduled halfway refresh required')
            _closed(payload['fresh_proofs'],('A','B'))
            for role,proof in payload['fresh_proofs'].items():
                self._check_proof(proof,study['packet']['price_release'][role]['terms'])
                if utc(proof['observed_at_utc'])<utc(study['proofs'][role]['observed_at_utc']):
                    raise ExecutionBlocked('price observation rollback')
            self._new_proofs_clock(event,state,study['packet']['policy'],payload['fresh_proofs'],
                                   study['packet']['price_release'])
            study['proofs']=deepcopy(payload['fresh_proofs']);study['refreshed']=True
            return
        if kind==GRANT:
            _closed(payload,('plan','context','receipt'))
            if study['pending'] is not None or study['stopped'] or state['unfinished']!=3:
                raise ExecutionBlocked('uncertain or stopped follow-up blocks dispatch')
            action=next_action(study)
            if action['status']!='REQUEST_READY_NOT_ADMITTED':raise ExecutionBlocked('follow-up complete')
            plan,c,receipt=self._context(study,action['request'])
            if canonical_hash(payload)!=canonical_hash({'plan':plan,'context':c,'receipt':receipt}):
                raise ExecutionBlocked('exact next follow-up request and witness prefix required')
            self._new_clock(event,state,study['packet']['policy'],c['price_proof'])
            amount=c['envelope']['reserved_microusd'];used=state['consumed']
            charged=sum(state['rows'][r]['charged'] for r in study['receipts'])
            if (receipt in state['rows'] or len(study['receipts'])>=56 or used['dispatches']>=112
                or (action['request']['execution_order']>=28 and not study['refreshed'])
                or c['envelope']['input_token_bound']>8192 or c['envelope']['max_tokens']!=256
                or amount>1785 or charged+amount>100000 or used['total']+amount>5000000
                or used['modules']['E02']+amount>1000000 or used['modules']['E01']!=0):
                raise ExecutionBlocked('follow-up or cumulative cap exhausted')
            study['pending']=deepcopy(payload);return
        if study['pending'] is not None:
            grant=study['pending'];expected=_row_for(grant['plan'],grant['context'],grant['receipt'])
            if kind!='RESERVE' or canonical_hash(payload)!=canonical_hash({'before_hash':None,'after':expected}):
                raise ExecutionBlocked('grant must atomically precede exact reservation')
            c=expected['context']
            self._new_clock(event,state,study['packet']['policy'],c['price_proof']);validate_row(expected)
            receipt=expected['id'];c=expected['context'];state['rows'][receipt]=deepcopy(expected)
            state['keys'].add(canonical_hash({k:c[k] for k in ('run_id','unit_id','phase','module')}))
            state['price_proofs'].add(price_proof_key(c))
            state['consumed']['total']+=expected['charged'];state['consumed']['modules']['E02']+=expected['charged']
            state['consumed']['dispatches']+=1;state['consumed']['module_dispatches']['E02']+=1
            state['unfinished']+=1;study['receipts'].append(receipt);study['pending']=None
            study['phase_started'][receipt]=event['recorded_at_utc'];return
        target=payload.get('receipt') if kind=='STATISTICS_CLAIM' else payload.get('after',{}).get('id')
        if target not in study['receipts'] or target!=study['receipts'][-1]:
            raise ExecutionBlocked('follow-up cannot alter prior or foreign rows')
        if kind==COMMIT:
            _closed(payload,('before_hash','after','witness'));w=payload['witness']
            _closed(w,('kind','execution_order','phase','receipt','context_hash','payload_sha256','generation_id',
                'response_raw_sha256','statistics_raw_sha256','checkpoint_sha256','status','answer'))
            row=state['rows'][target];c=row['context'];now=utc(event['recorded_at_utc'])
            if (event['clock_status']!='OK' or not 0<=(now-utc(study['phase_started'][target])).total_seconds()<=120
                or not utc(study['packet']['policy']['valid_from_utc'])<=now<utc(study['packet']['policy']['valid_until_utc'])):
                raise ExecutionBlocked('late follow-up commit keeps full hold')
            expected={**deepcopy(row),'status':'PHASE_COMMITTED','checkpoint_hash':w['checkpoint_sha256']}
            output={k:w[k] for k in ('status','answer','response_raw_sha256')}
            if (row['status']!='SETTLED' or payload['before_hash']!=canonical_hash(row)
                or canonical_hash(payload['after'])!=canonical_hash(expected)
                or w['kind']!='CROSSMODEL_COMMITTED_WITNESS_V1' or type(w['execution_order']) is not int
                or c['unit_id']!=f"crossmodel-{w['execution_order']:02d}" or w['phase']!=c['phase']
                or w['receipt']!=target or w['context_hash']!=canonical_hash(c)
                or w['payload_sha256']!=c['payload_hash'] or w['generation_id']!=row['generation_id']
                or w['status'] not in ('ANSWER','PARSE_ERROR')
                or (w['status']=='PARSE_ERROR' and w['answer'] is not None)
                or canonical_hash(output)!=row['output_hash'] or len(canonical_bytes(_phase_row(w)))>3072):
                raise ExecutionBlocked('follow-up checkpoint/witness mismatch')
            for name in ('response_raw_sha256','statistics_raw_sha256','checkpoint_sha256'):digest(w[name])
            self._transition_view({**event,'kind':'TRANSITION','payload':{'before_hash':payload['before_hash'],'after':expected}},state)
            study['witnesses'].append(deepcopy(w));next_action(study);return
        if kind not in ('TRANSITION','STATISTICS_CLAIM') or (kind=='TRANSITION' and payload['after']['status']=='PHASE_COMMITTED'):
            raise ExecutionBlocked('follow-up requires authenticated transitions')
        self._transition_view(event,state)
        if state['rows'][target]['status'] in ('UNCERTAIN','OVERRUN'):
            study['stopped']=True;study['failure_reason']=state['rows'][target]['error_type']

    def _verify(self,db):
        state,head=super()._verify(db)
        if state.get('issue_cue_crossmodel',{}).get('pending') is not None:
            raise ExecutionBlocked('partial follow-up grant refused')
        return state,head

    def start_crossmodel(self,packet,proof,*,expected_packet_hash):
        q=validate_packet(packet,expected_packet_hash=expected_packet_hash);proof=freeze(proof)
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db)
            body=self._event(START,{'packet':q,'fresh_proofs':proof},state,new=True)
            self._apply(body,state);checked,_=self._append_batch(db,[body],state,head)
            return self._snapshot(checked)

    @staticmethod
    def _check_proof(proof,terms):
        _closed(proof,('url','body_sha256','observed_at_utc','metadata_semantic_hash'))
        digest(proof['body_sha256']);utc(proof['observed_at_utc'])
        if (proof['url']!='https://openrouter.ai/api/v1/models/'+terms['model']+'/endpoints'
            or proof['metadata_semantic_hash']!=terms['metadata_semantic_hash']):
            raise ExecutionBlocked('role-specific price proof differs')

    def _new_proofs_clock(self,event,state,policy,proofs,releases):
        """Authenticate one event clock once, then check both observations."""
        _closed(proofs,('A','B'))
        for role,proof in proofs.items():self._check_proof(proof,releases[role]['terms'])
        now=self._new_clock(event,state,policy,proofs['A'])
        if not 0<=(now-utc(proofs['B']['observed_at_utc'])).total_seconds()<=900:
            raise ExecutionBlocked('second model price observation not current')
        return now

    def refresh_prices(self,packet,proofs,*,expected_packet_hash):
        q=validate_packet(packet,expected_packet_hash=expected_packet_hash);proofs=freeze(proofs)
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db);study=state.get('issue_cue_crossmodel')
            if study is None or study['packet']!=q:raise ExecutionBlocked('exact active crossmodel study required')
            action=next_action(study)
            if action['status']!='REQUEST_READY_NOT_ADMITTED':
                raise ExecutionBlocked('price refresh requires an unattempted phase')
            payload={'fresh_proofs':proofs,'next_execution_order':action['request']['execution_order']}
            body=self._event(REFRESH,payload,state,new=True);self._apply(body,state)
            checked,_=self._append_batch(db,[body],state,head)
            return self._snapshot(checked)

    def reserve_next(self,packet,proof,*,expected_packet_hash,transport_ready):
        q=validate_packet(packet,expected_packet_hash=expected_packet_hash);proof=freeze(proof)
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db);study=state.get('issue_cue_crossmodel')
            if study is None or study['packet']!=q or study['proofs']!=proof:
                raise ExecutionBlocked('exact started follow-up required')
            if study['stopped'] or next_action(study)['status']=='COMPLETE':return self._snapshot(state)
            compiled=next_action(study)['request'];plan,c,receipt=self._context(study,compiled)
            if transport_ready(freeze(c)) is not True:raise ExecutionBlocked('transport not ready')
            validate_packet(q,expected_packet_hash=expected_packet_hash)
            bodies=[]
            for kind,payload in ((GRANT,{'plan':plan,'context':c,'receipt':receipt}),
                ('RESERVE',{'before_hash':None,'after':_row_for(plan,c,receipt)})):
                body=self._event(kind,payload,state,new=True);self._apply(body,state);bodies.append(body)
            checked,newhead=self._append_batch(db,bodies,state,head)
            if checked['rows'][receipt]!=_row_for(plan,c,receipt):raise ExecutionBlocked('reservation readback differs')
            return {'status':'RESERVED','receipt':receipt,'head':newhead,'context':c,'request':compiled,'plan':plan}

    def _append_batch(self,db,bodies,state,head):
        # Existing atomic implementation materializes its original COMMIT kind.
        # Add only our distinct commit kind; all earlier event identities stay intact.
        for body in bodies:
            if body['kind']==COMMIT:
                r=body['payload']['after']
                db.execute('INSERT OR REPLACE INTO charges VALUES (?,?)',(r['id'],json.dumps(r,sort_keys=True)))
        return super()._append_batch(db,bodies,state,head)

    def commit_survey(self,receipt):
        from .issue_cue_crossmodel_v1 import parse_response
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db);study=state.get('issue_cue_crossmodel')
            if study is None or not study['receipts'] or receipt!=study['receipts'][-1]:
                raise ExecutionBlocked('current follow-up receipt required')
            row=state['rows'][receipt];c=row['context'];base=self._journal(c['run_id']);raw={};values={}
            for key in ('response','statistics','checkpoint'):
                path=base/(receipt+'-'+key+'.json')
                if path.is_symlink() or not path.is_file() or path.stat().st_size>2000000:
                    raise ExecutionBlocked('bounded follow-up raw evidence required')
                with path.open('rb') as f:raw[key]=f.read(2000001)
                from ..additional_compatibility_owner_v1 import _load
                values[key]=_load(raw[key])
                if len(raw[key])>2000000 or canonical_bytes(values[key])!=raw[key]:
                    raise ExecutionBlocked('canonical follow-up evidence required')
            response=values['response'];stats=values['statistics'].get('data')
            _no_provider_reasoning(response);_no_unsupported_response_activity(response)
            parsed=parse_response(response);output={'status':parsed['status'],'answer':parsed['answer'],
                'response_raw_sha256':hashlib.sha256(raw['response']).hexdigest()}
            expected={'schema_version':1,'run_id':c['run_id'],'unit_id':c['unit_id'],'phase':c['phase'],
                'receipt':receipt,'request_hash':c['envelope']['request_hash'],'output':output}
            projection=normalize_statistics(stats,generation_id=row['generation_id'],requested_model=c['terms']['model'],
                reported_provider=c['terms']['reported_provider'],input_bound=c['envelope']['input_token_bound'],
                output_bound=256,reserved_microusd=row['reserved'])['billing']
            if (row['status']!='SETTLED' or canonical_hash(values['checkpoint'])!=canonical_hash(expected)
                or canonical_hash(output)!=row['output_hash'] or canonical_hash(projection)!=canonical_hash(row['billing'])
                or response.get('id')!=row['generation_id'] or not response_model_allowed(response.get('model'),c['terms']['model'])):
                raise ExecutionBlocked('follow-up retained evidence binding differs')
            validate_row({**row,'billing':projection});usage=response.get('usage');_usage_bounds(usage,c['envelope'])
            amount=_cost(stats['total_cost'])
            if (amount!=row['observed_cost'] or (type(usage) is dict and usage.get('cost') is not None
                and Decimal(str(usage['cost']))!=Decimal(str(stats['total_cost'])))):
                raise ExecutionBlocked('follow-up response/generation cost differs')
            w={'kind':'CROSSMODEL_COMMITTED_WITNESS_V1','execution_order':int(c['unit_id'].rsplit('-',1)[1]),
                'phase':c['phase'],'receipt':receipt,'context_hash':canonical_hash(c),'payload_sha256':c['payload_hash'],
                'generation_id':row['generation_id'],'response_raw_sha256':output['response_raw_sha256'],
                'statistics_raw_sha256':hashlib.sha256(raw['statistics']).hexdigest(),
                'checkpoint_sha256':hashlib.sha256(raw['checkpoint']).hexdigest(),'status':parsed['status'],'answer':parsed['answer']}
            after={**deepcopy(row),'status':'PHASE_COMMITTED','checkpoint_hash':w['checkpoint_sha256']}
            body=self._event(COMMIT,{'before_hash':canonical_hash(row),'after':after,'witness':w},state,new=False)
            self._apply(body,state);checked,_=self._append_batch(db,[body],state,head)
            return deepcopy(checked['rows'][receipt])

    def _snapshot(self,state):
        study=state.get('issue_cue_crossmodel')
        if study is None:return {'status':'NOT_STARTED','transcript':[]}
        transcript=[_phase_row(w) for w in study['witnesses']]
        status='STOPPED' if study['stopped'] else ('COMPLETE' if next_action(study)['status']=='COMPLETE' else 'ACTIVE')
        if study['stopped'] and study['receipts']:
            row=state['rows'][study['receipts'][-1]];c=row['context']
            transcript.append({'execution_order':int(c['unit_id'].rsplit('-',1)[1]),'phase':c['phase'],
                'payload_sha256':c['payload_hash'],'status':'FAILED_UNCERTAIN','answer':None})
        return {'status':status,'transcript':deepcopy(transcript),'failure_reason':study['failure_reason'],
            'consumed_microusd':deepcopy(state['consumed']),'batch_dispatches':len(study['receipts']),
            'batch_charged_microusd':sum(state['rows'][r]['charged'] for r in study['receipts']),
            'original_study_preserved':True,'historical_holds_released':False}

    def study_snapshot(self):
        with self._lock(),self._connect() as db:
            state,_=self._verify(db);return self._snapshot(state)
