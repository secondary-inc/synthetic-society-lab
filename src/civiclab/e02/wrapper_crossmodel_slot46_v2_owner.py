"""Typed same-owner single-slot branch. Never clears the parent's terminal stop.

Existing owner lock, replay, atomic batch and financial row arithmetic are reused.
No bootstrap, credential, account, transport or automatic recovery authority.
"""
from copy import deepcopy
import hashlib
import json

from ..common import canonical_bytes, canonical_hash
from ..model import ExecutionBlocked
from ..owner_budget_v3 import utc
from ..production_owner_v4 import ProductionOwnerV4,base_context,validate_row,price_proof_key
from .wrapper_crossmodel_canary_v1_owner import CanaryOwnerV1, STATE as PREDECESSOR_STATE
from .exploratory_owner_v1 import _row_for
from .crossmodel_price_v1 import fresh_proof
from . import wrapper_crossmodel_slot46_v2 as p

OPEN='WRAPPER_SLOT46_OPEN_V2'
IO='WRAPPER_SLOT46_IO_V2'
PROOFS='WRAPPER_SLOT46_PROOFS_V2'
GRANT='WRAPPER_SLOT46_GRANT_V2'
FINISH='WRAPPER_SLOT46_COMMIT_V2'
CLOSE='WRAPPER_SLOT46_CLOSE_V2'
STATE='wrapper_crossmodel_slot46_v2'
ANCHOR={'baseline13': '19929177f13089ccfa5137b588632895280491f5b22eb155d58de197b65b681e', 'claims': 'ba46c00b6e493026993b07bac6d3afc4b6ce62f278b35f03593efb7a5a408689', 'protected': 'ac7ae7d73e02f8c1e2edb2624a7d81a058db22142f55838456e8f1de15e8efb6', 'rows': 'b3391e7ec1b901df17185c3bd33984f31b109dc050a34f09cbb7edabfb09ec63', 'study': '5c7da88a01de6f65a54b86d658e1f8c7fb3ad90011624c9bce0d450b6bbf5f2a'}
EXPECTED_HEAD_SHA256='540abd91b7a6cd2fd0e9d0fe6ff9b517e54396f6b62ec3dce34235963b0f95a2'

def parent_binding(state):
    rows=state['rows'];study=state['wrapper_crossmodel']
    baseline=next(w for w in study['witnesses'] if w['execution_order']==13)
    return {'rows':canonical_hash(rows),'study':canonical_hash(study),
            'claims':canonical_hash(sorted(state['statistics_claims'])),
            'protected':canonical_hash({k:canonical_hash(v) for k,v in rows.items() if v['status']!='PHASE_COMMITTED'}),
            'baseline13':canonical_hash(baseline)}


def _jsonable(value):
    if isinstance(value,set):return sorted(value)
    if isinstance(value,dict):return {k:_jsonable(v) for k,v in value.items()}
    if isinstance(value,list):return [_jsonable(v) for v in value]
    return value


def _static(state):
    mutable={'rows','consumed','unfinished','keys','generations','statistics_claims','price_proofs','max_clock','_prefix_events','_prefix_head',STATE}
    return canonical_hash(_jsonable({k:v for k,v in state.items() if k not in mutable}))


class Slot46OwnerV2(CanaryOwnerV1):
    @staticmethod
    def _binding(row,authority):
        if authority.get('kind')==p.AUTHORITY:
            base_context(row['context'])
            p.need(row['context']['approval_hash']==canonical_hash(authority),'canary financial authority')
            return
        return CanaryOwnerV1._binding(row,authority)

    def _protect(self,state,b):
        if b['packet']['kind']!='WRAPPER_SLOT46_PACKET_V2':
            if STATE not in state:return CanaryOwnerV1._protect(self,state,b)
            b=state[STATE]
        old={k:state['rows'][k] for k in b['old_ids']}
        p.need(canonical_hash(old)==ANCHOR['rows'] and canonical_hash(state['wrapper_crossmodel'])==ANCHOR['study']
               and _static(state)==b['old_static'],'canary immutable parent rows/study')
        p.need(set(state['rows'])==set(b['old_ids'])|({b['receipt']} if b['receipt'] else set()),'canary foreign row')
        p.need(set(b['old_claims']).issubset(state['statistics_claims'])
               and state['statistics_claims']<=set(b['old_claims'])|({b['receipt']} if b['receipt'] else set()),'canary prior claims')
        protected={k:canonical_hash(v) for k,v in old.items() if v['status']!='PHASE_COMMITTED'}
        p.need(len(protected)==6 and canonical_hash(protected)==ANCHOR['protected'],'canary six protected holds')
        extra=state['rows'].get(b['receipt']) if b['receipt'] else None
        expected_keys=set(b['old_keys'])
        expected_generations=deepcopy(b['old_generations'])
        if extra is not None:
            expected_keys.add(canonical_hash({k:extra['context'][k] for k in ('run_id','unit_id','phase','module')}))
            if extra['generation_id'] is not None:expected_generations[extra['generation_id']]=extra['id']
        p.need(state['keys']==expected_keys and state['generations']==expected_generations,'canary prior global identities')
        p.need(state['unfinished']==6+int(extra is not None and extra['status']!='PHASE_COMMITTED'),'canary unfinished accounting')
        expected=17152+(extra['charged'] if extra else 0)
        p.need(state['consumed']['total']==expected and state['consumed']['modules']=={'E01':0,'E02':expected}
               and state['consumed']['dispatches']==195+int(extra is not None)
               and state['consumed']['module_dispatches']=={'E01':0,'E02':195+int(extra is not None)},'canary cumulative accounting')

    def _time(self,event,state,b,*,phase=False):
        prior=state['max_clock'];now=self._clock(event,state);q=b['packet']
        p.need(event['clock_status']=='OK' and now is not None and (prior is None or now>=prior)
               and utc(q['valid_from_utc'])<=now<utc(q['valid_until_utc'])
               and 0<=(now-utc(b['opened'])).total_seconds()<240,'canary operation clock/window')
        if phase:p.need(0<=(now-utc(b['phase_started'])).total_seconds()<120,'canary phase deadline')
        return now

    def _journal_read(self,b,name):
        path=self._journal(b['packet']['run_id'])/name
        p.need(not any(x.is_symlink() for x in (path,*path.parents)) and path.is_file() and path.stat().st_size<=2000000,'canary bounded journal file')
        raw=path.read_bytes();value=json.loads(raw)
        p.need(len(raw)<=2000000 and canonical_bytes(value)==raw,'canary canonical journal')
        return raw,value

    def _proofs(self,b,proofs,now):
        p.closed(proofs,('A','B'))
        for role in ('A','B'):
            _,record=self._journal_read(b,'catalog-'+role+'.json')
            p.closed(record,('body_utf8','metadata','proof'))
            release=b['packet']['price_release'][role]
            checked=fresh_proof(record['body_utf8'].encode(),record['metadata'],release['interpretation'],release['terms'],now=now)
            p.need(checked==proofs[role]==record['proof'],'canary price source join')

    def _canary_context(self,state,b):
        if b['packet']['kind']!='WRAPPER_SLOT46_PACKET_V2':return CanaryOwnerV1._canary_context(self,state,b)
        q=b['packet'];compiled,baseline=p.compile_slot(state['wrapper_crossmodel'],q['price_release']['B']['terms'])
        p.need(baseline==ANCHOR['baseline13'],'canary baseline identity')
        plan={'kind':'WRAPPER_SLOT46_PLAN_V2','parent_key':q['parent_key'],'execution_order':46,
              'baseline_sha256':baseline,'payload_sha256':compiled['payload_sha256'],'scope_hash':canonical_hash(q)}
        c={'approval_hash':canonical_hash(q['authority']),'plan_hash':canonical_hash(plan),
           'release_hash':canonical_hash(q['price_release']),'price_proof':b['proofs']['B'],
           'run_id':q['run_id'],'unit_id':'wrapper-slot46-original-46','phase':'post','module':'E02',
           'terms':q['price_release']['B']['terms'],'envelope':compiled['envelope'],
           'sampling':{'seed':p.SEED,'temperature':0,'retries':0},'payload_hash':compiled['payload_sha256']}
        base_context(c)
        receipt=canonical_hash({'parent_key':q['parent_key'],'context':c})[:32]
        return {'request':compiled,'plan':plan,'context':c,'receipt':receipt}

    def _financial(self,event,state,b):
        authority=b['packet']['authority'];view={**state,'approvals':{canonical_hash(authority):authority}}
        ProductionOwnerV4._apply(self,event,view)
        state.update({k:v for k,v in view.items() if k!='approvals'})

    def _apply(self,event,state):
        kind,body=event['kind'],event['payload'];b=state.get(STATE)
        if kind==OPEN:
            p.closed(body,('packet',));q=body['packet'];p.validate_packet(q,canonical_hash(q))
            p.need(b is None,'canary parent+slot already opened across aliases')
            p.need(q['owner_id']==self.header['owner_id']==state['wrapper_crossmodel']['packet']['policy']['owner_id']
                   and canonical_hash(state['wrapper_crossmodel']['packet'])==p.PARENT_PACKET_SHA
                   and q['expected_head']==state['_prefix_head'] and canonical_hash(q['expected_head'])==EXPECTED_HEAD_SHA256 and len(state['_prefix_events'])==1189 and q['parent_binding']==ANCHOR==parent_binding(state), 'canary exact live parent/head')
            old=state['wrapper_crossmodel']
            for role in ('A','B'):
                prior=old['packet']['price_release'][role];new=q['price_release'][role]
                p.need(all(new['terms'][k]==v for k,v in prior['terms'].items() if k not in ('valid_from_utc','valid_until_utc','interpretation_hash'))
                       and all(new['interpretation'][k]==v for k,v in prior['interpretation'].items() if k not in ('valid_from_utc','valid_until_utc')),'canary historical semantics not loose ceilings')
            p.need(old['stopped'] is True and old['pending'] is None and len(old['receipts'])==45
                   and len(old['witnesses'])==44 and state['unfinished']==6 and len(state['rows'])==195
                   and state[PREDECESSOR_STATE]['closed'] is True and state[PREDECESSOR_STATE]['pending'] is None
                   and sorted(state['rows'][r]['charged'] for r in state['rows'] if state['rows'][r]['status']!='PHASE_COMMITTED')==[340,340,775,788,1003,1008]
                   and not any(row['context']['run_id']==q['run_id'] for row in state['rows'].values()),'canary stopped ancestry/holds')
            b={'packet':deepcopy(q),'opened':event['recorded_at_utc'],'old_ids':sorted(state['rows']),
               'old_claims':sorted(state['statistics_claims']),'old_static':_static(state),
               'old_keys':sorted(state['keys']),'old_generations':deepcopy(state['generations']),
               'io':[],'counts':{'POST':0,'statistics_GET':0,'catalog_GET':0},'proofs':None,
               'pending':None,'receipt':None,'phase_started':None,'witness':None,'closed':False}
            self._time(event,state,b);state[STATE]=b;self._protect(state,b);return
        if b is None:return super()._apply(event,state)
        self._protect(state,b)
        if kind==IO:
            p.closed(body,('parent_key','phase','ordinal'))
            phase,ordinal=body['phase'],body['ordinal']
            p.need(body['parent_key']==b['packet']['parent_key'] and not b['closed'] and type(ordinal) is int,'canary IO identity')
            phases={'CATALOG_A':'catalog_GET','CATALOG_B':'catalog_GET','POST':'POST','STATISTICS':'statistics_GET'}
            p.need(phase in phases,'canary fixed IO route')
            key=phases[phase]
            p.need(key=='catalog_GET' or b['receipt'] is not None,'canary reservation before IO')
            self._time(event,state,b,phase=key!='catalog_GET')
            p.need([phase,ordinal] not in b['io'] and ordinal==(b['counts'][key]+1 if key=='statistics_GET' else 1),'canary IO ordinal consumed')
            if key=='catalog_GET':p.need(b['receipt'] is None and b['proofs'] is None,'canary catalog order')
            else:
                p.need(b['receipt'] is not None,'canary reservation before IO')
                row=state['rows'][b['receipt']]
                if key=='POST':p.need(row['status']=='STARTED','canary post status')
                else:p.need(row['status']=='RESPONSE_SEEN' and b['receipt'] in state['statistics_claims'] and b['counts']['POST']==1,'canary billing intent')
            bound=p.BOUNDS[key];seed={'POST':46,'statistics_GET':44,'catalog_GET':12}[key]
            p.need(b['counts'][key]+1<=bound and seed+b['counts'][key]+1<=p.BOUNDS['parent_'+key],'canary IO aggregate cap')
            b['counts'][key]+=1;b['io'].append([phase,ordinal]);return
        if kind==PROOFS:
            p.closed(body,('proofs',));now=self._time(event,state,b)
            p.need(not b['closed'] and b['proofs'] is None and b['counts']['catalog_GET']==2 and b['receipt'] is None,'canary proof order')
            self._proofs(b,body['proofs'],now);b['proofs']=deepcopy(body['proofs']);return
        if kind==GRANT:
            p.closed(body,('ack',));now=self._time(event,state,b)
            p.need(not b['closed'] and b['pending'] is None and b['receipt'] is None and b['proofs'] is not None,'canary slot already claimed')
            self._proofs(b,b['proofs'],now)
            ack=self._canary_context(state,b);p.need(body['ack']==ack,'canary exact slot/payload/baseline grant')
            for release in b['packet']['price_release'].values():
                p.need((utc(release['terms']['valid_until_utc'])-now).total_seconds()>120,'canary full phase lease')
            amount=ack['context']['envelope']['reserved_microusd'];used=state['consumed']
            p.need(amount<=1785 and 4931+amount<=200000 and used['total']+amount<=5000000
                   and used['modules']['E02']+amount<=1000000 and used['modules']['E01']==0
                   and used['dispatches']+1<=229,'canary finite financial caps')
            b['pending']=deepcopy(ack);b['phase_started']=event['recorded_at_utc'];return
        if b['pending'] is not None:
            ack=b['pending'];row=_row_for(ack['plan'],ack['context'],ack['receipt'])
            p.need(kind=='RESERVE' and body=={'before_hash':None,'after':row},'canary grant/reserve atomic pair')
            self._time(event,state,b,phase=True);validate_row(row)
            p.need(row['id'] not in state['rows'],'canary duplicate receipt')
            state['rows'][row['id']]=deepcopy(row);state['keys'].add(canonical_hash({k:row['context'][k] for k in ('run_id','unit_id','phase','module')}))
            state['price_proofs'].add(price_proof_key(row['context']))
            state['consumed']['total']+=row['charged'];state['consumed']['modules']['E02']+=row['charged']
            state['consumed']['dispatches']+=1;state['consumed']['module_dispatches']['E02']+=1
            state['unfinished']+=1;b['receipt']=row['id'];b['pending']=None;self._protect(state,b);return
        if kind==CLOSE:
            p.closed(body,('reason',));p.need(body['reason'] in {'CANCELLED','FAILED','COMMITTED'},'canary closed reason')
            self._clock(event,state)
            row=state['rows'].get(b['receipt'])
            p.need(row is None or row['status'] in {'UNCERTAIN','OVERRUN','PHASE_COMMITTED'},'canary retain full uncertain hold before close')
            b['closed']=True;return
        target=body.get('receipt') if kind=='STATISTICS_CLAIM' else body.get('after',{}).get('id')
        p.need(b['receipt'] is not None and target==b['receipt'],'canary cannot alter original rows')
        if kind==FINISH:
            p.closed(body,('before_hash','after','witness'))
            self._check_commit(event,state,b,body)
            self._financial({**event,'kind':'TRANSITION','payload':{k:body[k] for k in ('before_hash','after')}},state,b)
            b['witness']=deepcopy(body['witness']);b['closed']=True
        else:
            p.need(kind in {'TRANSITION','STATISTICS_CLAIM'},'canary typed transitions only')
            p.need(kind!='TRANSITION' or body['after']['status']!='PHASE_COMMITTED','canary authenticated commit required')
            if kind=='STATISTICS_CLAIM':p.need(b['counts']['POST']==1,'canary claim before POST refused')
            self._financial(event,state,b)
            if state['rows'][b['receipt']]['status'] in {'UNCERTAIN','OVERRUN'}:b['closed']=True
        self._protect(state,b)

    def _check_commit(self,event,state,b,body):
        if b['packet']['kind']!='WRAPPER_SLOT46_PACKET_V2':return CanaryOwnerV1._check_commit(self,event,state,b,body)
        from .wrapper_crossmodel_v1 import parse_response
        from .crossmodel_recovery_metadata_v1 import normalize_statistics
        from .exploratory_live_client_v1 import _no_provider_reasoning,_no_unsupported_response_activity,_usage_bounds,_cost
        row=state['rows'][b['receipt']];c=row['context']
        now=utc(event['recorded_at_utc'])
        p.need(event['clock_status']=='OK' and not b['closed'] and 0<=(now-utc(b['phase_started'])).total_seconds()<120
               and 0<=(now-utc(b['opened'])).total_seconds()<240 and now<utc(b['packet']['valid_until_utc'])
               and b['counts']['POST']==1 and 1<=b['counts']['statistics_GET']<=3,'canary timely committed phase')
        rr,response=self._journal_read(b,b['receipt']+'-response.json')
        sr,statistics=self._journal_read(b,b['receipt']+'-statistics.json')
        cr,checkpoint=self._journal_read(b,b['receipt']+'-checkpoint.json')
        _no_provider_reasoning(response);_no_unsupported_response_activity(response)
        parsed=parse_response(response);compiled=self._canary_context(state,b)['request']
        bill=normalize_statistics(deepcopy(statistics['data']),generation_id=row['generation_id'],requested_model=c['terms']['model'],reported_provider=c['terms']['reported_provider'],input_bound=c['envelope']['input_token_bound'],output_bound=256,reserved_microusd=row['reserved'],request_payload=compiled['payload'])['billing']
        _usage_bounds(response.get('usage'),c['envelope'])
        amount=_cost(statistics['data']['total_cost'])
        p.need(row['status']=='SETTLED' and row['billing']==bill and amount==row['observed_cost'],'canary billing join')
        if response.get('usage',{}).get('cost') is not None:p.need(_cost(response['usage']['cost'])==amount,'canary response billing disagreement')
        from .crossmodel_recovery_metadata_v1 import response_model_allowed
        p.need(response.get('id')==row['generation_id'] and response_model_allowed(response.get('model'),c['terms']['model']),'canary response identity')
        output={'status':parsed['status'],'answer':parsed['answer'],'response_raw_sha256':hashlib.sha256(rr).hexdigest()}
        expected={'schema_version':1,'run_id':c['run_id'],'unit_id':c['unit_id'],'phase':'post','receipt':row['id'],'request_hash':c['envelope']['request_hash'],'output':output}
        witness={'execution_order':46,'phase':'post','status':parsed['status'],'answer':parsed['answer'],'payload_sha256':c['payload_hash'],'receipt':row['id']}
        p.need(checkpoint==expected and canonical_hash(output)==row['output_hash'] and body['witness']==witness
               and body['before_hash']==canonical_hash(row) and body['after']=={**row,'status':'PHASE_COMMITTED','checkpoint_hash':hashlib.sha256(cr).hexdigest()},'canary checkpoint/witness join')

    def _verify(self,db):
        state,head=super()._verify(db)
        if STATE in state:
            p.need(state[STATE]['pending'] is None,'canary torn grant')
            self._protect(state,state[STATE])
        return state,head

    def _append_batch(self,db,bodies,state,head):
        for body in bodies:
            if body['kind']==FINISH:
                row=body['payload']['after'];db.execute('INSERT OR REPLACE INTO charges VALUES (?,?)',(row['id'],json.dumps(row,sort_keys=True)))
        return super()._append_batch(db,bodies,state,head)

    def _fault(self,label):pass  # Test-only fault injection; no configurable live callback.

    def _atomic(self,kind,body,*,expected_head=None,new=True):
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db)
            if expected_head is not None:p.need(head==expected_head,'canary stale current head')
            event=self._event(kind,deepcopy(body),state,new=new);self._apply(event,state)
            self._fault('before_append')
            checked,newhead=self._append_batch(db,[event],state,head)
            self._fault('after_append')
            return deepcopy(checked[STATE]),newhead

    def open_canary(self,packet,expected_hash):
        q=p.validate_packet(packet,expected_hash)
        return self._atomic(OPEN,{'packet':q},expected_head=q['expected_head'])

    def intent(self,phase,ordinal):
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db);b=state[STATE]
            event=self._event(IO,{'parent_key':b['packet']['parent_key'],'phase':phase,'ordinal':ordinal},state,new=True)
            self._apply(event,state);checked,newhead=self._append_batch(db,[event],state,head)
            return {'head':newhead,'counts':deepcopy(checked[STATE]['counts'])}

    def register_proofs(self,proofs):return self._atomic(PROOFS,{'proofs':proofs})

    def grant(self):
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db);b=state[STATE]
            p.need(not b['closed'] and b['proofs'] is not None and b['receipt'] is None and b['pending'] is None,'canary grant unavailable')
            ack=self._canary_context(state,b)
            events=[]
            for kind,body in ((GRANT,{'ack':ack}),('RESERVE',{'before_hash':None,'after':_row_for(ack['plan'],ack['context'],ack['receipt'])})):
                event=self._event(kind,body,state,new=True);self._apply(event,state);events.append(event)
            self._fault('before_append');checked,newhead=self._append_batch(db,events,state,head);self._fault('after_append')
            p.need(checked[STATE]['receipt']==ack['receipt'],'canary reservation readback')
            return {**deepcopy(ack),'head':newhead,'status':'RESERVED'}

    def commit_canary(self,receipt,witness):
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE');state,head=self._verify(db);b=state[STATE]
            p.need(receipt==b['receipt'],'canary commit receipt')
            row=state['rows'][receipt];raw,_=self._journal_read(b,receipt+'-checkpoint.json')
            body={'before_hash':canonical_hash(row),'after':{**deepcopy(row),'status':'PHASE_COMMITTED','checkpoint_hash':hashlib.sha256(raw).hexdigest()},'witness':witness}
            event=self._event(FINISH,body,state,new=False);self._apply(event,state)
            checked,newhead=self._append_batch(db,[event],state,head);return deepcopy(checked[STATE])

    def close_canary(self,reason):return self._atomic(CLOSE,{'reason':reason},new=False)

    def canary_snapshot(self):
        with self._lock(),self._connect() as db:
            state,head=self._verify(db);b=state[STATE]
            return {'branch':deepcopy(b),'head':head,'row':deepcopy(state['rows'].get(b['receipt'])),'parent_stopped':True}
