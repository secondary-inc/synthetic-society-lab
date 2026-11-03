"""Owner-budget approval epochs, authored controls only; production factory off.

Protected local writer/header/history/head are trusted authority. This is not
hostile-host authentication, owner consent, a live pricing or model release.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import sqlite3
import sys
import uuid

from .common import atomic_json, canonical_bytes, canonical_hash, redact, sha256_file
from .live_billing_v2 import GlobalFixtureLedger, TRANSITIONS, integer, phase_key
from .model import ExecutionBlocked

NAMESPACE = 'SYNTHETIC_SOCIETY_LAB_OPENROUTER_V3'
SCOPE = 'AUTHORED_CONTROL_NOT_OWNER_AUTHORITY'
_COMMIT = object()


def freeze(value):
    """Detach into built-ins BEFORE admitting that exact snapshot."""
    out = json.loads(canonical_bytes(value))
    if redact(out) != out: raise ValueError('credential-like control input refused')
    return out


def digest(value, size=64):
    if type(value) is not str or re.fullmatch('[a-f0-9]{'+str(size)+'}', value) is None:
        raise ValueError('invalid digest or identity')
    return value


def utc(value):
    if type(value) is not str or len(value)>40: raise ValueError('invalid UTC timestamp')
    d = datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.utcoffset() is None or d.utcoffset().total_seconds()!=0: raise ValueError('explicit UTC required')
    return d


def production_owner_directory():
    """OS account home, never HOME/XDG/project/output overrides; writes nothing."""
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    if not home.is_absolute(): raise ExecutionBlocked('OS account home unavailable')
    if sys.platform=='darwin': return home/'Library/Application Support/SyntheticSocietyLab/openrouter-v3'
    if sys.platform.startswith('linux'): return home/'.local/share/synthetic-society-lab/openrouter-v3'
    raise ExecutionBlocked('supported POSIX owner location required')


def validate_approval(a, owner):
    if (type(a) is not dict or set(a)!={'kind','approval_id','owner_id','previous_approval_hash',
          'valid_from_utc','valid_until_utc','total_microusd','module_microusd','allowed_plans'}
        or a['kind']!=SCOPE or a['owner_id']!=owner):
        raise ExecutionBlocked('only exact authored owner approval fixtures are implemented')
    digest(a['approval_id'],32);digest(a['owner_id'],32)
    if a['previous_approval_hash'] is not None:digest(a['previous_approval_hash'])
    start,end=utc(a['valid_from_utc']),utc(a['valid_until_utc'])
    if start>=end:raise ValueError('approval time interval invalid')
    integer(a['total_microusd'],1)
    if type(a['module_microusd']) is not dict or set(a['module_microusd'])!={'E01','E02'}:
        raise ValueError('exact module lifetime caps required')
    for n in a['module_microusd'].values():integer(n)
    plans=a['allowed_plans']
    if type(plans) is not dict or not 1<=len(plans)<=256:raise ValueError('bounded released plan map required')
    for h,p in plans.items():
        digest(h)
        if (type(p) is not dict or set(p)!={'module','terms_sha256','max_tokens','max_input_token_bound'}
            or p['module'] not in ('E01','E02')):raise ValueError('invalid released plan binding')
        digest(p['terms_sha256']);integer(p['max_tokens'],1);integer(p['max_input_token_bound'],1)
        if p['max_tokens']>4096 or p['max_input_token_bound']>1_000_000:raise ValueError('unsupported plan ceiling')


def base_context(context):
    if type(context) is not dict or set(context)!={'approval_hash','plan_hash','run_id','unit_id','phase','module','terms','envelope','sampling','payload_hash'}:
        raise ValueError('owner phase context schema mismatch')
    digest(context['approval_hash']);digest(context['plan_hash'])
    out={k:v for k,v in context.items() if k not in ('approval_hash','plan_hash')}
    GlobalFixtureLedger._validate_context(out)
    if (context['module']=='E01' and context['phase']!='forecast') or (context['module']=='E02' and context['phase'] not in ('pre','post')):
        raise ValueError('phase outside research module')
    return out


def validate_row(row):
    value=deepcopy(row);value['context']=base_context(row['context'])
    GlobalFixtureLedger._validate_row(value)
    if row['generation_id'] is not None and re.fullmatch(r'gen-[0-9A-Za-z-]+',row['generation_id']) is None:
        raise ValueError('generation identity shape invalid')
    if row['status']=='RESPONSE_SEEN' and (row['generation_id'] is None or row['output_hash'] is None):
        raise ValueError('response identity and answer digest required')
    if redact(row)!=row:raise ValueError('credential-like row refused')


class OwnerBudgetFixtureV3:
    """One typed test owner, renewable absolute caps, no transport or credentials."""
    def __init__(self,directory,*,clock=None):
        self.directory=Path(directory).resolve();self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.guard=self.directory/'owner-v3-guard.local.json'
        self.db_path=self.directory/'owner-v3.local.sqlite'
        self.anchor=self.directory/'owner-v3-head.local.json'
        if not self.guard.is_file() or self.guard.is_symlink():raise ExecutionBlocked('owner guard missing; no bootstrap/reset')
        self.header=freeze(json.loads(self.guard.read_text()))
        if (set(self.header)!={'schema_version','namespace','scope','owner_id'} or self.header['schema_version']!=1
            or type(self.header['schema_version']) is not int or self.header['namespace']!=NAMESPACE or self.header['scope']!=SCOPE):
            raise ExecutionBlocked('owner header/fixture scope invalid')
        digest(self.header['owner_id'],32)

    @classmethod
    def create_fixture(cls,directory,*,clock=None):
        path=Path(directory).resolve()
        if path==production_owner_directory().resolve():raise ExecutionBlocked('fixture cannot initialize production owner location')
        path.mkdir(mode=0o700,parents=True,exist_ok=True)
        if any(path.iterdir()):raise ExecutionBlocked('fixture owner directory not empty; no overwrite/reset')
        path.chmod(0o700)
        header={'schema_version':1,'namespace':NAMESPACE,'scope':SCOPE,'owner_id':uuid.uuid4().hex}
        guard=path/'owner-v3-guard.local.json'
        with guard.open('xb') as stream:stream.write(canonical_bytes(header));stream.flush();os.fsync(stream.fileno())
        guard.chmod(0o600)
        obj=cls(path,clock=clock);obj.db_path.touch(mode=0o600,exist_ok=False)
        with obj._lock(),obj._connect() as db:
            db.execute('CREATE TABLE header(data TEXT NOT NULL)')
            db.execute('CREATE TABLE events(sequence INTEGER PRIMARY KEY,data TEXT NOT NULL,digest TEXT NOT NULL)')
            db.execute('CREATE TABLE charges(id TEXT PRIMARY KEY,data TEXT NOT NULL)')
            db.execute('INSERT INTO header VALUES (?)',(json.dumps(header,sort_keys=True),))
            state=obj._empty();event=obj._event('GENESIS',{'header_sha256':canonical_hash(header)},state,new=True)
            obj._apply(event,state);obj._append(db,event,None)
        return obj

    @classmethod
    def open_fixture(cls,directory,*,clock=None):
        obj=cls(directory,clock=clock)
        with obj._lock(),obj._connect() as db:obj._verify(db)
        return obj

    @contextmanager
    def _lock(self):
        if not self.guard.is_file() or self.guard.is_symlink():raise ExecutionBlocked('owner guard lost; no reset')
        with self.guard.open('rb') as f:
            try:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ExecutionBlocked('owner store busy; no dispatch') from None
            try:yield
            finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)

    def _connect(self):
        if not self.db_path.is_file() or self.db_path.is_symlink():raise ExecutionBlocked('owner store missing; no reset')
        return sqlite3.connect(self.db_path.as_uri()+'?mode=rw',uri=True,timeout=10)

    def _empty(self):
        return {'rows':{},'approvals':{},'active':None,'max_clock':None,'keys':set(),'generations':{},'approval_ids':set(),
                'consumed':{'total':0,'modules':{'E01':0,'E02':0}},'unfinished':0}

    def _event(self,kind,payload,state,*,new):
        prior=state['max_clock']
        try:
            observed=self.clock()
            if not isinstance(observed,datetime) or observed.utcoffset() is None or observed.utcoffset().total_seconds()!=0:
                raise ValueError('invalid UTC clock')
        except Exception:
            if new:raise ExecutionBlocked('unavailable UTC blocks new approval/dispatch') from None
            return {'kind':kind,'recorded_at_utc':None,'prior_clock_max_utc':prior.isoformat() if prior else None,
                    'clock_status':'CLOCK_UNAVAILABLE','clock_error':'UNAVAILABLE_UTC','payload':payload}
        rollback=prior is not None and observed<prior
        if new and rollback:raise ExecutionBlocked('clock rollback blocks new approval/dispatch')
        return {'kind':kind,'recorded_at_utc':observed.isoformat(),
                'prior_clock_max_utc':prior.isoformat() if prior else None,
                'clock_status':'CLOCK_ROLLBACK' if rollback else 'OK','clock_error':None,'payload':payload}

    def _clock(self,event,state):
        if set(event)!={'kind','recorded_at_utc','prior_clock_max_utc','clock_status','clock_error','payload'}:raise ValueError('owner event schema changed')
        prior=state['max_clock']
        if event['prior_clock_max_utc']!=(prior.isoformat() if prior else None):raise ValueError('prior clock maximum changed')
        if event['clock_status']=='CLOCK_UNAVAILABLE':
            if event['kind']!='TRANSITION' or event['recorded_at_utc'] is not None or event['clock_error']!='UNAVAILABLE_UTC':
                raise ValueError('invalid missing-clock bookkeeping')
            return None
        now=utc(event['recorded_at_utc']);rollback=prior is not None and now<prior
        if event['clock_error'] is not None or event['clock_status']!=('CLOCK_ROLLBACK' if rollback else 'OK'):
            raise ValueError('clock-error evidence changed')
        if rollback and event['kind'] in ('GENESIS','APPROVAL','RESERVE'):raise ValueError('new operation crossed clock rollback')
        state['max_clock']=max(now,prior) if prior else now
        return now

    @staticmethod
    def _consumed(state):
        return deepcopy(state['consumed'])

    @staticmethod
    def _binding(row,approval):
        c=row['context'];p=approval['allowed_plans'].get(c['plan_hash'])
        if (p is None or c['module']!=p['module'] or canonical_hash(c['terms'])!=p['terms_sha256']
            or c['envelope']['max_tokens']>p['max_tokens'] or c['envelope']['input_token_bound']>p['max_input_token_bound']):
            raise ExecutionBlocked('phase differs from released plan terms/module/ceilings')

    def _apply(self,event,state):
        now=self._clock(event,state);kind=event['kind'];p=event['payload']
        if kind=='GENESIS':
            if state['rows'] or state['approvals'] or p!={'header_sha256':canonical_hash(self.header)}:raise ValueError('invalid owner genesis')
            return
        if kind=='APPROVAL':
            validate_approval(p,self.header['owner_id'])
            if p['previous_approval_hash']!=state['active'] or p['approval_id'] in state['approval_ids']:
                raise ExecutionBlocked('approval parent or identity stale; no replenishment')
            if not utc(p['valid_from_utc'])<=now<utc(p['valid_until_utc']):raise ExecutionBlocked('approval not currently valid')
            if state['unfinished']!=0:raise ExecutionBlocked('unfinished global phase blocks renewal')
            used=self._consumed(state)
            if used['total']>p['total_microusd'] or any(used['modules'][m]>p['module_microusd'][m] for m in used['modules']):
                raise ExecutionBlocked('absolute lifetime cap below retained charges')
            h=canonical_hash(p);state['approvals'][h]=p;state['active']=h;state['approval_ids'].add(p['approval_id']);return
        if kind not in ('RESERVE','TRANSITION') or type(p) is not dict or set(p)!={'before_hash','after'}:
            raise ValueError('unknown owner event')
        row=p['after'];validate_row(row);old=state['rows'].get(row['id'])
        if p['before_hash']!=(canonical_hash(old) if old else None):raise ValueError('owner prior row changed')
        approval=state['approvals'].get(row['context']['approval_hash'])
        if approval is None:raise ExecutionBlocked('phase authority unknown')
        self._binding(row,approval)
        generation=row['generation_id']
        if generation is not None and state['generations'].get(generation,row['id'])!=row['id']:
            raise ValueError('generation already consumed owner-wide')
        if old is None:
            c=row['context'];key=phase_key(base_context(c))
            if kind!='RESERVE' or row['status']!='STARTED' or key in state['keys'] or c['approval_hash']!=state['active']:
                raise ExecutionBlocked('unreserved/duplicate/stale approval phase')
            if not utc(approval['valid_from_utc'])<=now<utc(approval['valid_until_utc']):raise ExecutionBlocked('reservation authority expired/not started')
            if state['unfinished']!=0:raise ExecutionBlocked('unfinished owner phase blocks dispatch')
            used=self._consumed(state)
            if used['total']+row['reserved']>approval['total_microusd'] or used['modules'][c['module']]+row['reserved']>approval['module_microusd'][c['module']]:
                raise ExecutionBlocked('owner lifetime ceiling exceeded')
            if any(row[k] is not None for k in ('generation_id','output_hash','observed_cost','checkpoint_hash','error_type','billing')):
                raise ValueError('reservation already contains unobserved evidence')
            state['keys'].add(key)
        else:
            if kind!='TRANSITION' or row['status'] not in TRANSITIONS[old['status']] or row['context']!=old['context'] or row['reserved']!=old['reserved']:
                raise ValueError('invalid owner phase transition')
            for k in ('generation_id','output_hash','billing'):
                if old[k] is not None and row[k]!=old[k]:raise ValueError('observed evidence replaced')
            if old['observed_cost'] is not None and (row['observed_cost'] is None or row['observed_cost']<old['observed_cost']):
                raise ValueError('known cost reduced')
            if old['status']=='SETTLED' and row['status']=='PHASE_COMMITTED' and row['charged']!=old['charged']:
                raise ValueError('checkpoint changed settled charge')
        if generation is not None:state['generations'][generation]=row['id']
        delta=row['charged']-(old['charged'] if old else 0)
        state['consumed']['total']+=delta;state['consumed']['modules'][row['context']['module']]+=delta
        state['unfinished']+=int(row['status']!='PHASE_COMMITTED')-int(old is not None and old['status']!='PHASE_COMMITTED')
        state['rows'][row['id']]=row

    def _verify(self,db):
        if not self.anchor.is_file() or self.anchor.is_symlink():raise ExecutionBlocked('owner head missing; no reset')
        if freeze(json.loads(self.guard.read_text()))!=self.header:raise ExecutionBlocked('owner guard identity changed')
        headers=db.execute('SELECT data FROM header').fetchall()
        if len(headers)!=1 or json.loads(headers[0][0])!=self.header:raise ExecutionBlocked('owner header changed')
        state=self._empty();previous=None
        rows=db.execute('SELECT sequence,data,digest FROM events ORDER BY sequence').fetchall()
        for i,(sequence,data,h) in enumerate(rows):
            event=json.loads(data)
            if set(event)!={'sequence','previous','body'} or type(sequence) is not int or type(event['sequence']) is not int or sequence!=i or event['sequence']!=i or event['previous']!=previous or canonical_hash(event)!=h:
                raise ValueError('owner history changed')
            if (i==0)!=(event['body'].get('kind')=='GENESIS'):raise ValueError('genesis location invalid')
            self._apply(event['body'],state);previous=h
        expected={'namespace':NAMESPACE,'owner_id':self.header['owner_id'],'header_sha256':canonical_hash(self.header),
                  'sequence':len(rows)-1,'head_hash':previous}
        if not rows or json.loads(self.anchor.read_text())!=expected:raise ExecutionBlocked('owner store/head torn or truncated')
        actual={i:json.loads(data) for i,data in db.execute('SELECT id,data FROM charges')}
        if actual!=state['rows']:raise ValueError('materialized charges differ from protected history')
        return state,expected

    def _append(self,db,body,head):
        seq=0 if head is None else head['sequence']+1
        event={'sequence':seq,'previous':None if head is None else head['head_hash'],'body':body};h=canonical_hash(event)
        db.execute('INSERT INTO events VALUES (?,?,?)',(seq,json.dumps(event,sort_keys=True),h))
        if body['kind'] in ('RESERVE','TRANSITION'):
            r=body['payload']['after'];db.execute('INSERT OR REPLACE INTO charges VALUES (?,?)',(r['id'],json.dumps(r,sort_keys=True)))
        db.commit()  # Head failure leaves the durable store ahead and reopening refuses.
        atomic_json(self.anchor,{'namespace':NAMESPACE,'owner_id':self.header['owner_id'],'header_sha256':canonical_hash(self.header),'sequence':seq,'head_hash':h})

    def grant_fixture(self,approval):
        value=freeze(approval);validate_approval(value,self.header['owner_id'])
        with self._lock(),self._connect() as db:
            state,head=self._verify(db);event=self._event('APPROVAL',value,state,new=True)
            self._apply(event,state);self._append(db,event,head)
            return canonical_hash(value)

    def reserve(self,context):
        c=freeze(context);base_context(c)
        r={'id':uuid.uuid4().hex,'context':c,'reserved':c['envelope']['reserved_microusd'],'charged':c['envelope']['reserved_microusd'],
           'status':'STARTED','generation_id':None,'output_hash':None,'observed_cost':None,'checkpoint_hash':None,'error_type':None,'billing':None}
        with self._lock(),self._connect() as db:
            state,head=self._verify(db);event=self._event('RESERVE',{'before_hash':None,'after':r},state,new=True)
            self._apply(event,state);self._append(db,event,head)
            return r['id']

    def transition(self,receipt,status,*,_capability=None,**fields):
        if status=='PHASE_COMMITTED' and _capability is not _COMMIT:raise ExecutionBlocked('durable phase validation required')
        if set(fields)-{'generation_id','output_hash','observed_cost','checkpoint_hash','error_type','billing'}:raise ValueError('unknown phase field')
        fields=freeze(fields)
        with self._lock(),self._connect() as db:
            state,head=self._verify(db);old=state['rows'].get(receipt)
            if old is None or status not in TRANSITIONS[old['status']]:raise ExecutionBlocked('phase transition unavailable')
            r={**deepcopy(old),**fields,'status':status}
            if status=='SETTLED':r['charged']=integer(r['observed_cost'])
            elif status in ('UNCERTAIN','OVERRUN'):r['charged']=max(old['charged'],old['reserved'],r['observed_cost'] or 0)
            event=self._event('TRANSITION',{'before_hash':canonical_hash(old),'after':r},state,new=False)
            self._apply(event,state);self._append(db,event,head)
            return deepcopy(r)

    def commit_phase(self,receipt,checkpoint):
        path=Path(checkpoint)
        with path.open('rb') as f:raw=f.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('checkpoint exceeds limit')
        value=json.loads(raw)
        with self._lock(),self._connect() as db:
            state,_=self._verify(db);row=state['rows'].get(receipt)
            if row is None or row['status']!='SETTLED':raise ExecutionBlocked('billing not settled')
            expected={'schema_version':1,**{k:row['context'][k] for k in ('run_id','unit_id','phase')},
                      'receipt':receipt,'request_hash':row['context']['envelope']['request_hash'],'output':value.get('output')}
            h=hashlib.sha256(raw).hexdigest()
            if canonical_hash(value)!=canonical_hash(expected) or canonical_hash(value.get('output'))!=row['output_hash'] or sha256_file(path)!=h:
                raise ValueError('durable checkpoint binding mismatch')
        return self.transition(receipt,'PHASE_COMMITTED',_capability=_COMMIT,checkpoint_hash=h)

    def snapshot(self):
        with self._lock(),self._connect() as db:
            state,_=self._verify(db)
            return {'scope':SCOPE,'owner_id':self.header['owner_id'],'approval_hash':state['active'],
                    'approval':deepcopy(state['approvals'].get(state['active'])),'consumed_microusd':self._consumed(state),
                    'maximum_observed_utc':state['max_clock'].isoformat(),'charges':deepcopy(list(state['rows'].values()))}


def create_live_owner(*args,**kwargs):
    raise ExecutionBlocked('production owner admission unavailable; no owner/study/price/credential authority')
