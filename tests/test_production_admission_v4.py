"""Authored external assertions in a mocked OS home; no real owner/key/network."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import hashlib,json,multiprocessing,os,sqlite3,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from civiclab.common import atomic_json,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import (compile_compatibility_release,code_pins,
    make_context,prepare_new_dispatch,prepare_existing_statistics,_Credential,run_live_compatibility)
from civiclab.production_owner_v4 import ProductionOwnerV4,NAMESPACE,request_binding,production_owner_directory
from test_production_price_v4 import fixture_contract,T0
from test_owner_budget_v3 import reseal


@contextmanager
def account(home,now=None):
    current=now or [T0]
    def clock():
        if isinstance(current[0],BaseException):raise current[0]
        return current[0]
    with patch('civiclab.production_owner_v4.pwd.getpwuid',return_value=SimpleNamespace(pw_dir=str(home))),patch('civiclab.production_owner_v4._utc_now',side_effect=clock):
        yield current


def materials(run='AUTHORED-PRODUCTION-COMPAT'):
    raw,d,terms,receipt=fixture_contract()
    release=compile_compatibility_release(terms,d,run_id=run)
    review={'kind':'INDEPENDENT_PRODUCTION_RELEASE_REVIEW_V4','scope':'CODE_PRICE_REQUEST_READY_FOR_OWNER',
        'review_id':uuid.uuid4().hex,'release_hash':canonical_hash(release),'source_pins':code_pins(),
        'reviewer_role':'independent_auditor','limitations_sha256':canonical_hash('AUTHORED_NOT_REAL_REVIEW')}
    return release,review,raw,receipt


def registration(release,review,now=T0):
    return {'kind':'EXTERNAL_ZERO_BOOTSTRAP_ASSERTION_V4','namespace':NAMESPACE,'owner_id':uuid.uuid4().hex,
        'registration_id':uuid.uuid4().hex,'account_uid':os.getuid(),'review_hash':canonical_hash(review),
        'release_hash':canonical_hash(release),'valid_from_utc':(now-timedelta(seconds=1)).isoformat(),
        'valid_until_utc':(now+timedelta(minutes=1)).isoformat(),'initial_allowance':0,
        'assertion':'EXPLICIT_OPERATOR_BOOTSTRAP'}


def initialize(release,review):
    r=registration(release,review)
    return ProductionOwnerV4.initialize(r,expected_registration_hash=canonical_hash(r),release=release,
        review=review,expected_review_hash=canonical_hash(review))


def approval(owner,release,review,*,total=100000,count=1,now=T0):
    terms=release['terms'];r=release['request'];snap=owner.snapshot()
    proof={'url':'https://openrouter.ai/api/v1/models/'+terms['model']+'/endpoints',
        'body_sha256':terms['initial_catalog_sha256'],'observed_at_utc':now.isoformat(),
        'metadata_semantic_hash':terms['metadata_semantic_hash']}
    c=make_context(release,'0'*64,proof);env=c['envelope']
    return {'kind':'EXTERNAL_OPERATOR_DISPATCH_ASSERTION_V4','approval_id':uuid.uuid4().hex,
        'owner_id':snap['owner_id'],'previous_approval_hash':snap['approval_hash'],
        'review_hash':canonical_hash(review),'release_hash':canonical_hash(release),
        'valid_from_utc':(now-timedelta(seconds=1)).isoformat(),'valid_until_utc':(now+timedelta(minutes=1)).isoformat(),
        'credential_state':'OWNER_ASSERTED_ROTATED_DEDICATED_KEY','statistics_policy':'ONE_LOOKUP_ORIGINAL_AUTHORITY',
        'total_microusd':total,'module_microusd':{'E01':0,'E02':total},
        'total_dispatches':count,'module_dispatches':{'E01':0,'E02':count},
        'allowed_plans':{r['plan_hash']:{'module':'E02','terms_sha256':canonical_hash(terms),
            'max_tokens':env['max_tokens'],'max_input_token_bound':env['input_token_bound'],
            'request_binding_hash':request_binding(c)}}}


def grant(owner,a,release,review):
    return owner.grant_operator_authorization(a,expected_approval_hash=canonical_hash(a),
        release=release,review=review,expected_review_hash=canonical_hash(review))


def context_for(release,epoch,receipt):
    return make_context(release,epoch,{**receipt,'metadata_semantic_hash':release['terms']['metadata_semantic_hash']})


def seen(owner,r,cost=1):
    answer={'status':'PARSED_OBJECT','parsed':{'ok':True},'raw_text':'{"ok":true}'}
    identity='gen-'+uuid.uuid4().hex
    owner.transition(r,'RESPONSE_SEEN',generation_id=identity,output_hash=canonical_hash(answer),observed_cost=cost)
    return answer,identity


def settle(owner,r,identity,cost=1):
    row=next(x for x in owner.snapshot()['charges'] if x['id']==r);t=row['context']['terms']
    owner.transition(r,'SETTLED',observed_cost=cost,billing={'id':identity,'model':t['model'],
        'provider_name':t['reported_provider'],'total_cost':cost/1000000,'native_tokens_prompt':1,
        'native_tokens_completion':1,'native_tokens_reasoning':0,'is_byok':False})


def checkpoint(owner,r,answer):
    row=next(x for x in owner.snapshot()['charges'] if x['id']==r);c=row['context']
    path=owner.directory/('phase-'+r+'.local.json')
    atomic_json(path,{'schema_version':1,'run_id':c['run_id'],'unit_id':c['unit_id'],'phase':c['phase'],
        'receipt':r,'request_hash':c['envelope']['request_hash'],'output':answer})
    return path


def reserve(owner,c):
    owner._register_price_proof(c)
    return owner.reserve(c)


def complete(owner,c):
    r=reserve(owner,c);answer,identity=seen(owner,r)
    owner.claim_statistics_lookup(r);settle(owner,r,identity);owner.commit_phase(r,checkpoint(owner,r,answer))
    return r


def crash(home,c,stage):
    with account(home):
        owner=ProductionOwnerV4.open();r=reserve(owner,c)
        if stage=='RESERVE':os._exit(91)
        answer,identity=seen(owner,r)
        if stage=='RESPONSE':os._exit(92)
        owner.claim_statistics_lookup(r)
        if stage=='STATISTICS':os._exit(93)
        settle(owner,r,identity)
        if stage=='SETTLED':os._exit(94)
        p=checkpoint(owner,r,answer)
        if stage=='CHECKPOINT':os._exit(95)
        owner.commit_phase(r,p);os._exit(96)


def race(home,c,q,counter):
    with account(home):
        try:
            reserve(ProductionOwnerV4.open(),c)
            with counter.get_lock():counter.value+=1
            q.put('RESERVED')
        except ExecutionBlocked:q.put('REFUSED')


class ProductionAdmissionTests(unittest.TestCase):
    @contextmanager
    def case(self,*,approved=True,total=100000,count=1):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve()/'AUTHORED_OS_HOME'
            with account(home) as now:
                release,review,raw,receipt=materials();owner=initialize(release,review)
                a=approval(owner,release,review,total=total,count=count)
                epoch=grant(owner,a,release,review) if approved else '0'*64
                yield home,now,owner,release,review,a,epoch,raw,receipt

    def prepare(self,c,**changes):
        home,now,owner,release,review,a,epoch,raw,receipt=c
        body=changes.pop('catalog_body',raw);proof=changes.pop('catalog_receipt',receipt)
        args={'expected_review_hash':canonical_hash(review),'expected_approval_hash':epoch};args.update(changes)
        with patch('civiclab.production_admission_v4._fetch_public_catalog',return_value=(body,proof)):
            return prepare_new_dispatch(release,review,a,**args)

    def test_zero_bootstrap_static_release_and_one_exact_prepared_request(self):
        with self.case() as c:
            home,now,owner,release,review,a,epoch,raw,receipt=c
            with patch('civiclab.production_admission_v4._read_environment_key',return_value=_Credential('AUTHORED_FAKE_CREDENTIAL')) as key:
                prepared=self.prepare(c)
            self.assertEqual(key.call_count,1);self.assertEqual(owner.snapshot()['charges'],[])
            payload=prepared.payload
            self.assertIn('max_completion_tokens',payload);self.assertNotIn('max_tokens',payload)
            self.assertEqual(payload['plugins'],[]);self.assertEqual(payload['tools'],[])
            self.assertEqual(payload['provider']['only'],['fixture']);self.assertFalse(payload['provider']['allow_fallbacks'])
            payload['messages'][0]['content']='MUTATED_CALLER_COPY'
            self.assertNotEqual(prepared.payload['messages'][0]['content'],'MUTATED_CALLER_COPY')
            self.assertNotIn('AUTHORED_FAKE_CREDENTIAL',repr(prepared))
            r=prepared.reserve();answer,identity=seen(owner,r);owner.claim_statistics_lookup(r);settle(owner,r,identity)
            owner.commit_phase(r,checkpoint(owner,r,answer))
            self.assertEqual(owner.snapshot()['consumed_microusd'],{'total':1,'modules':{'E01':0,'E02':1},'dispatches':1,'module_dispatches':{'E01':0,'E02':1}})
            with self.assertRaises(ExecutionBlocked):prepared.reserve()
            with self.assertRaises(ExecutionBlocked):run_live_compatibility()

    def test_bootstrap_has_no_allowance_and_cannot_open_create_or_relocate(self):
        with self.case(approved=False) as c:
            home,now,owner,release,review,a,epoch,raw,receipt=c
            s=owner.snapshot();self.assertIsNone(s['approval_hash']);self.assertEqual(s['consumed_microusd']['dispatches'],0)
            with patch('civiclab.production_admission_v4._read_environment_key',side_effect=AssertionError('credential touched')):
                with self.assertRaises(ExecutionBlocked):self.prepare(c,expected_approval_hash=canonical_hash(a))
            with self.assertRaises(TypeError):ProductionOwnerV4.open(directory=Path('arbitrary'))
            with self.assertRaises(TypeError):ProductionOwnerV4.open(clock=lambda:T0)
            with self.assertRaises(ExecutionBlocked):initialize(release,review)
            self.assertTrue(owner.directory.is_relative_to(home))
            self.assertEqual(owner.directory.stat().st_mode&0o777,0o700)
            for p in (owner.registration,owner.guard,owner.db_path,owner.anchor):self.assertEqual(p.stat().st_mode&0o777,0o600)
            for name in ('guard','db_path','anchor','registration'):
                old=getattr(owner,name);setattr(owner,name,old.parent/('relocated-'+old.name))
                with self.assertRaises(ExecutionBlocked):owner.snapshot()
                setattr(owner,name,old)

    def test_incomplete_review_bootstrap_and_changed_code_refuse_before_owner_files(self):
        for mode in ('review','release','hash','allowance','uid','expired'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                home=Path(t).resolve()/'NO_OWNER'
                with account(home):
                    release,review,raw,receipt=materials();r=registration(release,review)
                    if mode=='review':review['reviewer_role']='implementer'
                    elif mode=='release':release['request']['payload']['messages'][0]['content']='CHANGED'
                    elif mode=='allowance':r['initial_allowance']=1
                    elif mode=='uid':r['account_uid']+=1
                    elif mode=='expired':r['valid_until_utc']=(T0-timedelta(seconds=1)).isoformat()
                    expected='0'*64 if mode=='hash' else canonical_hash(r)
                    with self.assertRaises((ExecutionBlocked,ValueError)):
                        ProductionOwnerV4.initialize(r,expected_registration_hash=expected,release=release,review=review,expected_review_hash=canonical_hash(review))
                    self.assertFalse(home.exists())
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve()/'NO_OWNER'
            with account(home):
                release,review,raw,receipt=materials();review['source_pins'][next(iter(review['source_pins']))]='0'*64
                with self.assertRaises(ExecutionBlocked):initialize(release,review)
                self.assertFalse(home.exists())

    def test_invalid_dispatch_and_missing_key_do_not_reserve_or_read_unapproved_key(self):
        for mode in ('expired','review','price','payload','plan','approval','funds'):
            with self.subTest(mode=mode),self.case(total=1 if mode=='funds' else 100000) as c:
                home,now,owner,release,review,a,epoch,raw,receipt=c
                before=(owner.db_path.read_bytes(),owner.anchor.read_bytes())
                if mode=='expired':now[0]=T0+timedelta(minutes=2)
                elif mode=='review':review['scope']='AUTHORED_UNRELEASED'
                elif mode=='payload':release['request']['payload']['temperature']=1
                elif mode=='plan':release['request']['envelope']['reserved_microusd']=1
                elif mode=='approval':a['allowed_plans'][next(iter(a['allowed_plans']))]['request_binding_hash']='0'*64
                args={'catalog_receipt':{**receipt,'observed_at_utc':(T0-timedelta(seconds=901)).isoformat()}} if mode=='price' else {}
                with patch('civiclab.production_admission_v4._read_environment_key',side_effect=AssertionError('unapproved key read')) as key:
                    with self.assertRaises((ExecutionBlocked,ValueError)):self.prepare(c,**args)
                    self.assertEqual(key.call_count,0)
                self.assertEqual((owner.db_path.read_bytes(),owner.anchor.read_bytes()),before)
        with self.case() as c:
            before=c[2].db_path.read_bytes()
            with patch('civiclab.production_admission_v4._read_environment_key',side_effect=ExecutionBlocked('missing dedicated key')):
                with self.assertRaises(ExecutionBlocked):self.prepare(c)
            self.assertEqual(c[2].snapshot()['charges'],[])
            self.assertEqual(c[2].snapshot()['consumed_microusd']['dispatches'],0)
            self.assertTrue(c[2].snapshot()['price_proof_keys'])

    def test_lifetime_dispatch_caps_across_new_runs_cheap_answers_and_renewals(self):
        with self.case() as c:
            home,now,owner,release,review,a,epoch,raw,receipt=c
            complete(owner,context_for(release,epoch,receipt))
            release2,review2,raw2,receipt2=materials('AUTHORED-SECOND-RUN')
            now[0]=T0+timedelta(minutes=2)
            a2=approval(owner,release2,review2,count=1,now=now[0]);epoch2=grant(owner,a2,release2,review2)
            kwargs={'expected_review_hash':canonical_hash(review2),'expected_approval_hash':epoch2}
            with patch('civiclab.production_admission_v4._read_environment_key',side_effect=AssertionError('cap must precede key')),patch('civiclab.production_admission_v4._fetch_public_catalog',return_value=(raw2,receipt2)):
                with self.assertRaises(ExecutionBlocked):prepare_new_dispatch(release2,review2,a2,**kwargs)
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],1)
            a3=approval(owner,release2,review2,count=2,now=now[0]);epoch3=grant(owner,a3,release2,review2)
            r=reserve(owner,context_for(release2,epoch3,receipt2));answer,identity=seen(owner,r,cost=0)
            owner.claim_statistics_lookup(r);settle(owner,r,identity,cost=0);owner.commit_phase(r,checkpoint(owner,r,answer))
            s=owner.snapshot();self.assertEqual(s['consumed_microusd']['total'],1);self.assertEqual(s['consumed_microusd']['dispatches'],2)
            self.assertEqual({r['context']['approval_hash'] for r in s['charges']},{epoch,epoch3})
            bad=approval(owner,release2,review2,count=1,now=now[0])
            with self.assertRaises(ExecutionBlocked):grant(owner,bad,release2,review2)

    def test_expired_or_failed_clock_does_not_strand_existing_billing(self):
        for late in (T0+timedelta(days=2),T0-timedelta(seconds=1),RuntimeError('PRIVATE_CLOCK_TEXT')):
            with self.subTest(late=type(late).__name__),self.case() as c:
                home,now,owner,release,review,a,epoch,raw,receipt=c
                r=reserve(owner,context_for(release,epoch,receipt));now[0]=late
                answer,identity=seen(owner,r)
                with patch('civiclab.production_admission_v4._read_environment_key',return_value=_Credential('AUTHORED_FAKE')) as key:
                    found=prepare_existing_statistics(owner,r)
                self.assertEqual(found['generation_id'],identity);self.assertEqual(key.call_count,1)
                with patch('civiclab.production_admission_v4._read_environment_key',side_effect=AssertionError('duplicate lookup touched key')):
                    with self.assertRaises(ExecutionBlocked):prepare_existing_statistics(owner,r)
                settle(owner,r,identity);owner.commit_phase(r,checkpoint(owner,r,answer))
                s=owner.snapshot();self.assertEqual(s['consumed_microusd']['total'],1);self.assertEqual(s['consumed_microusd']['dispatches'],1)
                self.assertEqual(s['charges'][0]['context']['approval_hash'],epoch)
                with patch('civiclab.production_admission_v4._read_environment_key',side_effect=AssertionError('late dispatch key')):
                    with self.assertRaises((ExecutionBlocked,ValueError)):self.prepare(c)
                if isinstance(late,RuntimeError):
                    with sqlite3.connect(owner.db_path) as db:
                        bodies=[json.loads(row[0])['body'] for row in db.execute('SELECT data FROM events')]
                    self.assertTrue(any(b['kind']=='STATISTICS_CLAIM' and b['recorded_at_utc'] is None for b in bodies))
                    self.assertNotIn('PRIVATE_CLOCK_TEXT',owner.db_path.read_bytes().decode('utf-8',errors='ignore'))

    def test_unknown_overrun_and_duplicate_generations_conserve_funds_and_block(self):
        for status,cost in (('UNCERTAIN',None),('OVERRUN',200000)):
            with self.subTest(status=status),self.case() as c:
                home,now,owner,release,review,a,epoch,raw,receipt=c
                r=reserve(owner,context_for(release,epoch,receipt));now[0]=T0+timedelta(minutes=2)
                if status=='OVERRUN':seen(owner,r,cost=cost)
                owner.transition(r,status,observed_cost=cost,error_type='AuthoredFailure')
                row=owner.snapshot()['charges'][0]
                self.assertGreaterEqual(row['charged'],max(row['reserved'],cost or 0))
                new=approval(owner,release,review,total=1000000,count=2,now=now[0])
                with self.assertRaises(ExecutionBlocked):grant(owner,new,release,review)
                with self.assertRaises(ExecutionBlocked):owner.claim_statistics_lookup(r)
        with self.case() as c:
            home,now,owner,release,review,a,epoch,raw,receipt=c
            first=complete(owner,context_for(release,epoch,receipt));generation=owner.snapshot()['charges'][0]['generation_id']
            release2,review2,raw2,receipt2=materials('AUTHORED-SECOND')
            a2=approval(owner,release2,review2,count=2);epoch2=grant(owner,a2,release2,review2)
            r=reserve(owner,context_for(release2,epoch2,receipt2))
            with self.assertRaises(ValueError):owner.transition(r,'RESPONSE_SEEN',generation_id=generation,output_hash='a'*64,observed_cost=1)
            self.assertEqual(owner.snapshot()['charges'][-1]['status'],'STARTED')

    def test_checkpoint_requires_statistics_claim_and_exact_output_binding(self):
        with self.case() as c:
            owner,release,epoch,receipt=c[2],c[3],c[6],c[8]
            r=reserve(owner,context_for(release,epoch,receipt));answer,identity=seen(owner,r)
            with self.assertRaises(ExecutionBlocked):settle(owner,r,identity)
            owner.claim_statistics_lookup(r);settle(owner,r,identity)
            with self.assertRaises(ExecutionBlocked):owner.transition(r,'PHASE_COMMITTED',checkpoint_hash='a'*64)
            p=checkpoint(owner,r,answer);value=json.loads(p.read_text());value['output']['parsed']['ok']=False;atomic_json(p,value)
            with self.assertRaises(ValueError):owner.commit_phase(r,p)
            self.assertEqual(owner.snapshot()['charges'][0]['status'],'SETTLED')

    def test_missing_outer_inner_state_and_torn_head_never_bootstrap_or_reset(self):
        for part in ('registration','guard','db_path','anchor'):
            with self.subTest(part=part),self.case() as c:
                home,now,owner,release,review,a,epoch,raw,receipt=c
                getattr(owner,part).unlink()
                with self.assertRaises(ExecutionBlocked):ProductionOwnerV4.open()
                with self.assertRaises(ExecutionBlocked):initialize(release,review)
        with self.case() as c:
            owner=c[2]
            owner._register_price_proof(context_for(c[3],c[6],c[8]))
            with patch('civiclab.production_owner_v4.atomic_json',side_effect=OSError('AUTHORED_HEAD_FAILURE')):
                with self.assertRaises(OSError):owner.reserve(context_for(c[3],c[6],c[8]))
            with self.assertRaises(ExecutionBlocked):ProductionOwnerV4.open()

    def test_fully_committed_bootstrap_with_lost_ack_is_not_an_empty_reset(self):
        with tempfile.TemporaryDirectory() as t:
            home=Path(t).resolve()/'AUTHORED_OS_HOME'
            with account(home):
                release,review,raw,receipt=materials()
                from civiclab import production_owner_v4 as runtime
                original=runtime.atomic_json
                def lost(path,value):original(path,value);raise OSError('AUTHORED_LOST_ACK')
                with patch.object(runtime,'atomic_json',side_effect=lost):
                    with self.assertRaises(OSError):initialize(release,review)
                owner=ProductionOwnerV4.open();self.assertIsNone(owner.snapshot()['approval_hash'])
                self.assertEqual(owner.snapshot()['consumed_microusd']['dispatches'],0)
                with self.assertRaises(ExecutionBlocked):initialize(release,review)

    def test_semantic_replay_rejects_historical_caps_despite_new_larger_approval(self):
        with self.case() as c:
            owner,release,review,epoch,receipt=c[2],c[3],c[4],c[6],c[8]
            complete(owner,context_for(release,epoch,receipt))
            next_release,next_review,raw2,receipt2=materials('SECOND-RESERVATION')
            a2=approval(owner,next_release,next_review,count=2);epoch2=grant(owner,a2,next_release,next_review)
            complete(owner,context_for(next_release,epoch2,receipt2))
            release3,review3,raw3,receipt3=materials('LARGER-RENEWAL')
            grant(owner,approval(owner,release3,review3,total=1000000,count=10),release3,review3)
            def edit(events):
                approvals=[e['body']['payload'] for e in events if e['body']['kind']=='APPROVAL']
                approvals[1]['total_dispatches']=1;approvals[1]['module_dispatches']['E02']=1
            reseal(owner,edit)
            with self.assertRaises((ValueError,ExecutionBlocked)):owner.snapshot()

    def test_real_process_deaths_and_competing_exact_request_reservation(self):
        for stage in ('RESERVE','RESPONSE','STATISTICS','SETTLED','CHECKPOINT','COMMITTED'):
            with self.subTest(stage=stage),self.case() as c:
                home,now,owner,release,review,a,epoch,raw,receipt=c
                ctx=multiprocessing.get_context('spawn');child=ctx.Process(target=crash,args=(str(home),context_for(release,epoch,receipt),stage))
                child.start();child.join(30);self.assertFalse(child.is_alive());self.assertEqual(child.exitcode,91+('RESERVE','RESPONSE','STATISTICS','SETTLED','CHECKPOINT','COMMITTED').index(stage))
                rows=owner.snapshot()['charges'];self.assertEqual(len(rows),1);self.assertEqual(owner.snapshot()['consumed_microusd']['dispatches'],1)
                if stage!='COMMITTED':
                    with self.assertRaises(ExecutionBlocked):owner.check_dispatch(context_for(release,epoch,receipt))
                else:self.assertEqual(rows[0]['status'],'PHASE_COMMITTED')
        with self.case() as c:
            ctx=multiprocessing.get_context('spawn');q=ctx.Queue();counter=ctx.Value('i',0)
            args=(str(c[0]),context_for(c[3],c[6],c[8]),q,counter)
            children=[ctx.Process(target=race,args=args) for _ in range(2)]
            for child in children:child.start()
            for child in children:child.join(30);self.assertFalse(child.is_alive());self.assertEqual(child.exitcode,0)
            self.assertEqual(counter.value,1);self.assertEqual(sorted(q.get(timeout=5) for _ in children),['REFUSED','RESERVED'])

    def test_prepared_payload_and_price_aliases_cannot_change_registered_authority(self):
        for mode in ('payload','coedited_payload','price_time','price_hash'):
            with self.subTest(mode=mode),self.case() as c:
                with patch('civiclab.production_admission_v4._read_environment_key',return_value=_Credential('AUTHORED_FAKE')):
                    p=self.prepare(c)
                payload=p.payload;context=p.context;before=c[2].db_path.read_bytes()
                if mode in ('payload','coedited_payload'):
                    payload['provider']['allow_fallbacks']=True
                    p._payload=json.dumps(payload).encode()
                    if mode=='coedited_payload':context['payload_hash']=canonical_hash(payload)
                elif mode=='price_time':context['price_proof']['observed_at_utc']=(T0-timedelta(seconds=1)).isoformat()
                else:context['price_proof']['body_sha256']='0'*64
                p._context=json.dumps(context).encode()
                with self.assertRaises((ExecutionBlocked,ValueError)):p.reserve()
                self.assertEqual(c[2].db_path.read_bytes(),before)
                self.assertEqual(c[2].snapshot()['charges'],[])


class _Response:
    def __init__(self,raw,*,step=65536,status=200,headers=None,read_error=None,close_error=None):
        from email.message import Message
        self.raw=raw;self.offset=0;self.step=step;self.status=status;self.closed=False;self.reads=[]
        self.read_error=read_error;self.close_error=close_error;self.headers=Message()
        for k,v in (headers or [('Content-Type','application/json'),('Content-Length',str(len(raw)))]):self.headers.add_header(k,v)
    def getheader(self,key,default=None):return self.headers.get(key,default)
    def read(self,n):
        self.reads.append(n)
        if self.read_error:raise self.read_error
        block=self.raw[self.offset:self.offset+min(n,self.step)];self.offset+=len(block);return block
    def close(self):
        self.closed=True
        if self.close_error:raise self.close_error


class _Connection:
    def __init__(self,response):self.response=response;self.calls=[];self.closed=False
    def request(self,*args,**kwargs):self.calls.append((args,kwargs))
    def getresponse(self):return self.response
    def close(self):self.closed=True


class PublicCatalogPolicyTests(unittest.TestCase):
    def test_fixed_unauthenticated_https_short_reads_and_full_cleanup(self):
        import ssl
        from civiclab.production_admission_v4 import _fetch_public_catalog
        raw,d,t,receipt=fixture_contract();response=_Response(raw,step=1);connection=_Connection(response)
        with account('/AUTHORED_UNUSED_HOME'),patch('civiclab.production_admission_v4.http.client.HTTPSConnection',return_value=connection) as make:
            body,proof=_fetch_public_catalog('fixture/model-v4')
        self.assertEqual(body,raw);self.assertEqual(proof['body_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertTrue(connection.closed and response.closed);self.assertEqual(len(connection.calls),1)
        args,kwargs=connection.calls[0];self.assertEqual(args,('GET','/api/v1/models/fixture/model-v4/endpoints'))
        self.assertEqual(kwargs['headers'],{'Accept':'application/json','Accept-Encoding':'identity'})
        self.assertEqual(make.call_args.args,('openrouter.ai',));self.assertEqual(make.call_args.kwargs['timeout'],15)
        tls=make.call_args.kwargs['context'];self.assertTrue(tls.check_hostname);self.assertEqual(tls.verify_mode,ssl.CERT_REQUIRED)

    def test_bad_metadata_framing_body_status_and_close_errors_refuse_once(self):
        from civiclab.production_admission_v4 import _fetch_public_catalog
        variants=[_Response(b'{}',status=302),_Response(b'{}',headers=[('Content-Type','text/html')]),
            _Response(b'{}',headers=[('Content-Type','application/json'),('Content-Encoding','gzip')]),
            _Response(b'{}',headers=[('Content-Type','application/json'),('Content-Length','2'),('Content-Length','2')]),
            _Response(b'{}',headers=[('Content-Type','application/json'),('Content-Length','3')]),
            _Response(b'{}',headers=[('Content-Type','application/json'),('Transfer-Encoding','gzip')]),
            _Response(b'X'*2_000_001,headers=[('Content-Type','application/json')]),
            _Response(b'{}',close_error=RuntimeError('PRIVATE_CLOSE_ERROR'))]
        for response in variants:
            with self.subTest(headers=str(response.headers)):
                connection=_Connection(response)
                with patch('civiclab.production_admission_v4.http.client.HTTPSConnection',return_value=connection):
                    with self.assertRaises(ExecutionBlocked) as caught:_fetch_public_catalog('fixture/model-v4')
                self.assertNotIn('PRIVATE',str(caught.exception));self.assertTrue(response.closed and connection.closed)
                self.assertEqual(len(connection.calls),1)

    def test_metadata_cancel_and_elapsed_limits_close_without_retry(self):
        from civiclab.production_admission_v4 import _fetch_public_catalog
        response=_Response(b'{}',read_error=KeyboardInterrupt('AUTHORED_CANCEL'));connection=_Connection(response)
        with patch('civiclab.production_admission_v4.http.client.HTTPSConnection',return_value=connection):
            with self.assertRaises(KeyboardInterrupt):_fetch_public_catalog('fixture/model-v4')
        self.assertTrue(response.closed and connection.closed);self.assertEqual(len(connection.calls),1)
        response=_Response(b'{}');connection=_Connection(response)
        with patch('civiclab.production_admission_v4.http.client.HTTPSConnection',return_value=connection),patch('civiclab.production_admission_v4.time.monotonic',side_effect=[0,31]):
            with self.assertRaises(ExecutionBlocked):_fetch_public_catalog('fixture/model-v4')
        self.assertTrue(response.closed and connection.closed);self.assertEqual(response.reads,[])
        with patch('civiclab.production_admission_v4.http.client.HTTPSConnection',side_effect=AssertionError('invalid model opened network')):
            with self.assertRaises(ExecutionBlocked):_fetch_public_catalog('fixture/unsafe?query')
