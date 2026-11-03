"""Fixed owner ledger with externally asserted operator approval, no network.

No cryptographic human identity or hostile complete-store replacement claim.
Only the separate release factory may be used for actual workflow admission.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
import fcntl,hashlib,json,os,pwd,re,sqlite3,sys,uuid
from pathlib import Path

from .common import atomic_json,canonical_bytes,canonical_hash,redact,sha256_file
from .live_billing_v2 import GlobalFixtureLedger,TRANSITIONS,integer,phase_key
from .model import ExecutionBlocked,micros
from .owner_budget_v3 import digest,freeze,utc
from .production_price_v4 import validate_terms,decimal_price,financial_context

NAMESPACE='SYNTHETIC_SOCIETY_LAB_OPENROUTER_V4'
SCOPE='PRODUCTION_OPERATOR_CONTROL_V4'
_COMMIT=object()


def _utc_now():
    return datetime.now(timezone.utc)


def new_operation_time():
    try:
        value=_utc_now()
        if not isinstance(value,datetime) or value.utcoffset() is None or value.utcoffset().total_seconds()!=0:
            raise ValueError('invalid UTC')
        return value
    except Exception:
        raise ExecutionBlocked('valid UTC unavailable for new authority/dispatch') from None


def production_owner_directory():
    home=Path(pwd.getpwuid(os.getuid()).pw_dir)
    if not home.is_absolute():raise ExecutionBlocked('OS account home unavailable')
    if sys.platform=='darwin':return home/'Library/Application Support/SyntheticSocietyLab/openrouter-v4'
    if sys.platform.startswith('linux'):return home/'.local/share/synthetic-society-lab/openrouter-v4'
    raise ExecutionBlocked('supported POSIX account required')


def validate_registration(value):
    if (type(value) is not dict or set(value)!={'kind','namespace','owner_id','registration_id','account_uid',
         'review_hash','release_hash','valid_from_utc','valid_until_utc','initial_allowance','assertion'}
        or value['kind']!='EXTERNAL_ZERO_BOOTSTRAP_ASSERTION_V4' or value['namespace']!=NAMESPACE
        or value['assertion']!='EXPLICIT_OPERATOR_BOOTSTRAP' or type(value['initial_allowance']) is not int
        or value['initial_allowance']!=0 or type(value['account_uid']) is not int or value['account_uid']!=os.getuid()):
        raise ExecutionBlocked('external zero-bootstrap assertion invalid')
    for k in ('owner_id','registration_id'):digest(value[k],32)
    for k in ('review_hash','release_hash'):digest(value[k])
    if utc(value['valid_from_utc'])>=utc(value['valid_until_utc']):raise ValueError('bootstrap interval invalid')


def validate_approval(a,owner):
    if (type(a) is not dict or set(a)!={'kind','approval_id','owner_id','previous_approval_hash','valid_from_utc',
        'valid_until_utc','review_hash','release_hash','credential_state','statistics_policy','total_microusd','module_microusd','total_dispatches','module_dispatches','allowed_plans'}
        or a['kind']!='EXTERNAL_OPERATOR_DISPATCH_ASSERTION_V4' or a['owner_id']!=owner):
        raise ExecutionBlocked('exact external dispatch assertion required')
    digest(a['approval_id'],32);digest(a['owner_id'],32)
    digest(a['review_hash']);digest(a['release_hash'])
    if a['credential_state']!='OWNER_ASSERTED_ROTATED_DEDICATED_KEY' or a['statistics_policy']!='ONE_LOOKUP_ORIGINAL_AUTHORITY':
        raise ExecutionBlocked('credential setup and bounded accounting assertion required')
    if a['previous_approval_hash'] is not None:digest(a['previous_approval_hash'])
    if utc(a['valid_from_utc'])>=utc(a['valid_until_utc']):raise ValueError('approval interval invalid')
    integer(a['total_microusd'],1);integer(a['total_dispatches'],1)
    for key in ('module_microusd','module_dispatches'):
        if type(a[key]) is not dict or set(a[key])!={'E01','E02'}:raise ValueError('module limits required')
        for v in a[key].values():integer(v)
    if type(a['allowed_plans']) is not dict or not 1<=len(a['allowed_plans'])<=512:raise ValueError('released plan map required')
    for h,p in a['allowed_plans'].items():
        digest(h)
        if type(p) is not dict or set(p)!={'module','terms_sha256','max_tokens','max_input_token_bound','request_binding_hash'} or p['module'] not in ('E01','E02'):
            raise ValueError('exact request binding required')
        digest(p['terms_sha256']);digest(p['request_binding_hash']);integer(p['max_tokens'],1);integer(p['max_input_token_bound'],1)
        if p['max_tokens']>4096 or p['max_input_token_bound']>1_000_000:raise ValueError('unsupported request ceiling')


def request_binding(context):
    return canonical_hash({k:v for k,v in context.items() if k not in ('approval_hash','price_proof')})


def price_proof_key(context):
    return canonical_hash({'approval_hash':context['approval_hash'],
        'request_binding_hash':request_binding(context),'price_proof':context['price_proof']})


@financial_context
def base_context(c):
    if type(c) is not dict or set(c)!={'approval_hash','plan_hash','release_hash','price_proof','run_id','unit_id','phase','module','terms','envelope','sampling','payload_hash'}:
        raise ValueError('production context schema mismatch')
    for k in ('approval_hash','plan_hash','release_hash','payload_hash'):digest(c[k])
    if c['module'] not in ('E01','E02') or (c['module']=='E01' and c['phase']!='forecast') or (c['module']=='E02' and c['phase'] not in ('pre','post','compatibility')):
        raise ValueError('invalid research phase')
    for key in ('run_id','unit_id'):
        if type(c[key]) is not str or not re.fullmatch(r'[0-9A-Za-z_-]{1,128}',c[key]):raise ValueError('invalid request identity')
    s=c['sampling']
    if type(s) is not dict or set(s)!={'seed','temperature','retries'} or type(s['seed']) is not int or not 0<=s['seed']<2**32 or type(s['temperature']) is not int or s['temperature']!=0 or type(s['retries']) is not int or s['retries']!=0:
        raise ValueError('fixed sampling/no retry required')
    validate_terms(c['terms']);e=c['envelope']
    if type(e) is not dict or set(e)!={'input_token_bound','max_tokens','request_hash','encoded_message_bytes','message_count','reserved_microusd'}:raise ValueError('envelope schema')
    for k in ('input_token_bound','max_tokens','encoded_message_bytes','message_count','reserved_microusd'):integer(e[k],1)
    digest(e['request_hash'])
    if e['input_token_bound']!=e['encoded_message_bytes']+1024*e['message_count'] or e['max_tokens']>4096 or e['encoded_message_bytes']>100000:
        raise ValueError('framing/output bound invalid')
    expected=micros(Decimal(e['input_token_bound'])*decimal_price(c['terms']['input_usd_per_token'])+Decimal(e['max_tokens'])*decimal_price(c['terms']['output_usd_per_token'])+decimal_price(c['terms']['request_fee_usd']))
    if e['reserved_microusd']!=expected:raise ValueError('price reservation differs')
    p=c['price_proof']
    if type(p) is not dict or set(p)!={'url','body_sha256','observed_at_utc','metadata_semantic_hash'}:raise ValueError('price evidence shape')
    digest(p['body_sha256']);utc(p['observed_at_utc'])
    if p['url']!='https://openrouter.ai/api/v1/models/'+c['terms']['model']+'/endpoints' or p['metadata_semantic_hash']!=c['terms']['metadata_semantic_hash']:
        raise ExecutionBlocked('price proof differs from contract')
    if redact(c)!=c:raise ValueError('credential-like context refused')
    return c


class _ProductionRowMath(GlobalFixtureLedger):
    # Pure validation reuse only: no fixture factory, terms or allowance promotion.
    _validate_context=staticmethod(base_context)


@financial_context
def validate_row(row):
    _ProductionRowMath._validate_row(row)
    if row['generation_id'] is not None and re.fullmatch(r'gen-[0-9A-Za-z-]+',row['generation_id']) is None:raise ValueError('generation shape')
    if row['status']=='RESPONSE_SEEN' and (row['generation_id'] is None or row['output_hash'] is None):raise ValueError('response proof missing')
    if redact(row)!=row:raise ValueError('credential-like row refused')


class ProductionOwnerV4:
    """One fixed operator-controlled owner; no transport or identity authentication."""
    def __init__(self):
        self.directory = production_owner_directory()
        self.registration = self.directory.parent/'openrouter-v4-bootstrap.local.json'
        self.guard=self.directory/'owner-v4-guard.local.json'
        self.db_path=self.directory/'owner-v4.local.sqlite'
        self.anchor=self.directory/'owner-v4-head.local.json'
        self._location()
        if not self.guard.is_file() or self.guard.is_symlink():
            raise ExecutionBlocked('production owner guard missing; no bootstrap/reset')
        self.header=freeze(json.loads(self.guard.read_text()))
        if (set(self.header)!={'schema_version','namespace','scope','owner_id','registration_sha256'}
            or type(self.header['schema_version']) is not int or self.header['schema_version']!=1
            or self.header['namespace']!=NAMESPACE or self.header['scope']!=SCOPE):
            raise ExecutionBlocked('production owner identity invalid')
        digest(self.header['owner_id'],32);digest(self.header['registration_sha256'])
        self._registration()

    def _location(self):
        if self.directory!=production_owner_directory():raise ExecutionBlocked('production owner location changed')
        if (self.guard!=self.directory/'owner-v4-guard.local.json' or self.db_path!=self.directory/'owner-v4.local.sqlite'
            or self.anchor!=self.directory/'owner-v4-head.local.json'
            or self.registration!=self.directory.parent/'openrouter-v4-bootstrap.local.json'):
            raise ExecutionBlocked('production state paths differ from fixed namespace')
        for path in (self.directory, *self.directory.parents):
            if path.is_symlink():raise ExecutionBlocked('symlink in owner namespace refused')

    def _registration(self):
        self._location()
        if not self.registration.is_file() or self.registration.is_symlink():
            raise ExecutionBlocked('outside owner registration missing; no reset')
        value=freeze(json.loads(self.registration.read_text()))
        validate_registration(value)
        if canonical_hash(value)!=self.header['registration_sha256'] or value['owner_id']!=self.header['owner_id']:
            raise ExecutionBlocked('outside registration differs from owner')

    @classmethod
    def initialize(cls, registration, *, expected_registration_hash, release, review, expected_review_hash):
        # External operator assertion under trusted execution; not human identity.
        value=freeze(registration);validate_registration(value);digest(expected_registration_hash)
        if canonical_hash(value)!=expected_registration_hash:raise ExecutionBlocked('bootstrap assertion changed')
        now=new_operation_time()
        from .production_admission_v4 import precheck_bootstrap
        precheck_bootstrap(value,expected_registration_hash,release,review,expected_review_hash,now=now)
        if not utc(value['valid_from_utc'])<=now<utc(value['valid_until_utc']):
            raise ExecutionBlocked('bootstrap assertion not current')
        path=production_owner_directory();outside=path.parent/'openrouter-v4-bootstrap.local.json'
        for candidate in (path,*path.parents):
            if candidate.is_symlink():raise ExecutionBlocked('symlink owner namespace refused')
        if outside.exists() or outside.is_symlink() or path.exists() or path.is_symlink():
            raise ExecutionBlocked('owner registration/path already exists; no reset')
        path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        with outside.open('xb') as f:
            f.write(canonical_bytes(value));f.flush();os.fsync(f.fileno())
        outside.chmod(0o600)  # Survives missing/failed inner bootstrap.
        path.mkdir(mode=0o700)
        header={'schema_version':1,'namespace':NAMESPACE,'scope':SCOPE,'owner_id':value['owner_id'],
                'registration_sha256':canonical_hash(value)}
        guard=path/'owner-v4-guard.local.json'
        with guard.open('xb') as f:f.write(canonical_bytes(header));f.flush();os.fsync(f.fileno())
        guard.chmod(0o600)
        obj=cls();obj.db_path.touch(mode=0o600,exist_ok=False)
        with obj._lock(),obj._connect() as db:
            db.execute('CREATE TABLE header(data TEXT NOT NULL)')
            db.execute('CREATE TABLE events(sequence INTEGER PRIMARY KEY,data TEXT NOT NULL,digest TEXT NOT NULL)')
            db.execute('CREATE TABLE charges(id TEXT PRIMARY KEY,data TEXT NOT NULL)')
            db.execute('INSERT INTO header VALUES (?)',(json.dumps(header,sort_keys=True),))
            state=obj._empty();event=obj._event('GENESIS',{'header_sha256':canonical_hash(header)},state,new=True)
            obj._apply(event,state);obj._append(db,event,None)
        return obj

    @classmethod
    def open(cls):
        obj=cls()
        with obj._lock(),obj._connect() as db:obj._verify(db)
        return obj

    @contextmanager
    def _lock(self):
        self._registration()
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
                'consumed':{'total':0,'modules':{'E01':0,'E02':0},'dispatches':0,'module_dispatches':{'E01':0,'E02':0}},'unfinished':0,'statistics_claims':set(),'price_proofs':set()}

    def _event(self,kind,payload,state,*,new):
        prior=state['max_clock']
        try:
            observed=_utc_now()
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
            if event['kind'] not in ('TRANSITION','STATISTICS_CLAIM') or event['recorded_at_utc'] is not None or event['clock_error']!='UNAVAILABLE_UTC':
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
            or c['release_hash']!=approval['release_hash']
            or c['envelope']['max_tokens']>p['max_tokens'] or c['envelope']['input_token_bound']>p['max_input_token_bound']
            or request_binding(c)!=p['request_binding_hash']):
            raise ExecutionBlocked('request differs from released identity/terms/ceilings')

    def _apply(self,event,state):
        now=self._clock(event,state);kind=event['kind'];p=event['payload']
        if kind=='GENESIS':
            if state['rows'] or state['approvals'] or p!={'header_sha256':canonical_hash(self.header)}:raise ValueError('invalid owner genesis')
            registration=json.loads(self.registration.read_text())
            if not utc(registration['valid_from_utc'])<=now<utc(registration['valid_until_utc']):
                raise ExecutionBlocked('genesis outside original bootstrap authorization interval')
            return
        if kind=='STATISTICS_CLAIM':
            if type(p) is not dict or set(p)!={'receipt','generation_id'}:
                raise ValueError('statistics claim shape')
            row=state['rows'].get(p['receipt'])
            if (row is None or row['status']!='RESPONSE_SEEN' or row['generation_id']!=p['generation_id']
                or p['receipt'] in state['statistics_claims']):
                raise ExecutionBlocked('statistics lookup unavailable or already claimed')
            state['statistics_claims'].add(p['receipt']);return
        if kind=='PRICE_PROOF':
            if type(p) is not dict or set(p)!={'context'}:raise ValueError('price observation shape')
            c=p['context'];base_context(c);a=state['approvals'].get(c['approval_hash'])
            if a is None or c['approval_hash']!=state['active']:raise ExecutionBlocked('price observation epoch stale')
            self._binding({'context':c},a)
            observed=utc(c['price_proof']['observed_at_utc']);terms=c['terms'];used=self._consumed(state)
            if (not utc(a['valid_from_utc'])<=now<utc(a['valid_until_utc'])
                or not utc(terms['valid_from_utc'])<=now<utc(terms['valid_until_utc'])
                or not 0<=(now-observed).total_seconds()<=900):raise ExecutionBlocked('price observation not current')
            if (state['unfinished'] or phase_key(c) in state['keys']
                or used['total']+c['envelope']['reserved_microusd']>a['total_microusd']
                or used['modules'][c['module']]+c['envelope']['reserved_microusd']>a['module_microusd'][c['module']]
                or used['dispatches']+1>a['total_dispatches']
                or used['module_dispatches'][c['module']]+1>a['module_dispatches'][c['module']]):
                raise ExecutionBlocked('price preparation cannot bypass owner request/fund/count barriers')
            state['price_proofs'].add(price_proof_key(c));return
        if kind=='APPROVAL':
            validate_approval(p,self.header['owner_id'])
            if p['previous_approval_hash']!=state['active'] or p['approval_id'] in state['approval_ids']:
                raise ExecutionBlocked('approval parent or identity stale; no replenishment')
            if not utc(p['valid_from_utc'])<=now<utc(p['valid_until_utc']):raise ExecutionBlocked('approval not currently valid')
            if state['unfinished']!=0:raise ExecutionBlocked('unfinished global phase blocks renewal')
            used=self._consumed(state)
            if used['total']>p['total_microusd'] or any(used['modules'][m]>p['module_microusd'][m] for m in used['modules']):
                raise ExecutionBlocked('absolute lifetime cap below retained charges')
            if used['dispatches']>p['total_dispatches'] or any(used['module_dispatches'][m]>p['module_dispatches'][m] for m in used['modules']):
                raise ExecutionBlocked('absolute dispatch cap below retained reservations')
            h=canonical_hash(p);state['approvals'][h]=p;state['active']=h;state['approval_ids'].add(p['approval_id']);return
        if kind not in ('RESERVE','TRANSITION') or type(p) is not dict or set(p)!={'before_hash','after'}:
            raise ValueError('unknown owner event')
        row=p['after'];validate_row(row);old=state['rows'].get(row['id'])
        if row['status'] in ('SETTLED','PHASE_COMMITTED') and row['id'] not in state['statistics_claims']:
            raise ExecutionBlocked('single statistics intent required for settlement')
        if p['before_hash']!=(canonical_hash(old) if old else None):raise ValueError('owner prior row changed')
        approval=state['approvals'].get(row['context']['approval_hash'])
        if approval is None:raise ExecutionBlocked('phase authority unknown')
        self._binding(row,approval)
        generation=row['generation_id']
        if generation is not None and state['generations'].get(generation,row['id'])!=row['id']:
            raise ValueError('generation already consumed owner-wide')
        if old is None:
            c=row['context'];key=phase_key(base_context(c))
            if price_proof_key(c) not in state['price_proofs']:
                raise ExecutionBlocked('unregistered price proof; prepared data is not authority')
            if kind!='RESERVE' or row['status']!='STARTED' or key in state['keys'] or c['approval_hash']!=state['active']:
                raise ExecutionBlocked('unreserved/duplicate/stale approval phase')
            if not utc(approval['valid_from_utc'])<=now<utc(approval['valid_until_utc']):raise ExecutionBlocked('reservation authority expired/not started')
            if state['unfinished']!=0:raise ExecutionBlocked('unfinished owner phase blocks dispatch')
            used=self._consumed(state)
            if used['total']+row['reserved']>approval['total_microusd'] or used['modules'][c['module']]+row['reserved']>approval['module_microusd'][c['module']]:
                raise ExecutionBlocked('owner lifetime ceiling exceeded')
            if used['dispatches']+1>approval['total_dispatches'] or used['module_dispatches'][c['module']]+1>approval['module_dispatches'][c['module']]:
                raise ExecutionBlocked('owner lifetime dispatch count exhausted')
            terms=c['terms'];proof=c['price_proof'];observed=utc(proof['observed_at_utc'])
            if not utc(terms['valid_from_utc'])<=now<utc(terms['valid_until_utc']) or not 0<=(now-observed).total_seconds()<=900:
                raise ExecutionBlocked('new dispatch price evidence expired/future')
            if any(row[k] is not None for k in ('generation_id','output_hash','observed_cost','checkpoint_hash','error_type','billing')):
                raise ValueError('reservation already contains unobserved evidence')
            state['keys'].add(key)
            state['consumed']['dispatches']+=1;state['consumed']['module_dispatches'][c['module']]+=1
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
        self._registration()
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

    def grant_operator_authorization(self,approval,*,expected_approval_hash,release,review,expected_review_hash):
        value=freeze(approval);validate_approval(value,self.header['owner_id']);digest(expected_approval_hash)
        if canonical_hash(value)!=expected_approval_hash:raise ExecutionBlocked('external approval hash changed')
        from .production_admission_v4 import precheck_dispatch_approval
        precheck_dispatch_approval(value,expected_approval_hash,release,review,expected_review_hash,now=new_operation_time())
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

    def check_dispatch(self,context):
        c=freeze(context);base_context(c)
        row={'id':uuid.uuid4().hex,'context':c,'reserved':c['envelope']['reserved_microusd'],
            'charged':c['envelope']['reserved_microusd'],'status':'STARTED','generation_id':None,
            'output_hash':None,'observed_cost':None,'checkpoint_hash':None,'error_type':None,'billing':None}
        with self._lock(),self._connect() as db:
            state,_=self._verify(db)
            self._apply(self._event('RESERVE',{'before_hash':None,'after':row},state,new=True),state)
        return {'owner_id':self.header['owner_id'],'approval_hash':c['approval_hash'],'scope':SCOPE}

    def check_price_preparation(self,context):
        c=freeze(context);base_context(c)
        with self._lock(),self._connect() as db:
            state,_=self._verify(db)
            self._apply(self._event('PRICE_PROOF',{'context':c},state,new=True),state)
        return price_proof_key(c)

    def _register_price_proof(self,context):
        # Called only by the reviewed factory after its fixed HTTPS source read.
        c=freeze(context);base_context(c);key=price_proof_key(c)
        with self._lock(),self._connect() as db:
            state,head=self._verify(db);exists=key in state['price_proofs']
            event=self._event('PRICE_PROOF',{'context':c},state,new=True)
            self._apply(event,state)
            if not exists:self._append(db,event,head)
        return key

    def claim_statistics_lookup(self,receipt):
        with self._lock(),self._connect() as db:
            state,head=self._verify(db);row=state['rows'].get(receipt)
            if row is None:raise ExecutionBlocked('unknown accounting phase')
            payload={'receipt':receipt,'generation_id':row['generation_id']}
            event=self._event('STATISTICS_CLAIM',payload,state,new=False)
            self._apply(event,state);self._append(db,event,head)
            return payload['generation_id']

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
                    'maximum_observed_utc':state['max_clock'].isoformat(),'charges':deepcopy(list(state['rows'].values())),
                    'statistics_claimed_receipts':sorted(state['statistics_claims']),
                    'price_proof_keys':sorted(state['price_proofs'])}

