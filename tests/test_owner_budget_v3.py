"""Authored approval epochs and financial history; no model/network/key."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import multiprocessing
import os
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import uuid

from civiclab.common import atomic_json,canonical_hash
from civiclab.live_billing_v2 import quote
from civiclab.model import ExecutionBlocked,micros
from civiclab.owner_budget_v3 import OwnerBudgetFixtureV3,SCOPE,create_live_owner,production_owner_directory
from civiclab.reconciled_client_v2 import fixture_terms

T0=datetime(2026,11,3,12,tzinfo=timezone.utc)
PLAN={m:canonical_hash({'AUTHORED_PLAN':m}) for m in ('E01','E02')}


def terms():
    t=fixture_terms();t.update(input_usd_per_token='0',output_usd_per_token='0',request_fee_usd='0.000001');return t


def approval(owner,total=100,now=T0,**changes):
    snapshot=owner.snapshot()
    a={'kind':SCOPE,'approval_id':uuid.uuid4().hex,'owner_id':snapshot['owner_id'],
       'previous_approval_hash':snapshot['approval_hash'],'valid_from_utc':(now-timedelta(minutes=1)).isoformat(),
       'valid_until_utc':(now+timedelta(minutes=1)).isoformat(),'total_microusd':total,
       'module_microusd':{'E01':total,'E02':total},'allowed_plans':{
           PLAN[m]:{'module':m,'terms_sha256':canonical_hash(terms()),'max_tokens':32,'max_input_token_bound':10000}
           for m in ('E01','E02')}}
    a.update(changes);return a


def context(owner,run='run',unit='unit',module='E02',phase=None):
    return {'approval_hash':owner.snapshot()['approval_hash'],'plan_hash':PLAN[module],
            'run_id':run,'unit_id':unit,'phase':phase or ('forecast' if module=='E01' else 'pre'),'module':module,
            'terms':terms(),'envelope':quote([{'role':'user','content':'AUTHORED ONLY'}],32,terms()),
            'sampling':{'seed':12,'temperature':0,'retries':0},'payload_hash':'a'*64}


def response_seen(owner,r):
    answer={'status':'AUTHORED_NUMBERS','parsed':{'democratic_party':60,'republican_party':40},'raw_text':'AUTHORED'}
    identity='gen-'+uuid.uuid4().hex
    owner.transition(r,'RESPONSE_SEEN',generation_id=identity,output_hash=canonical_hash(answer),observed_cost=1)
    return answer,identity


def settled(owner,r,answer,identity):
    t=terms();b={'id':identity,'model':t['model'],'provider_name':t['reported_provider'],'total_cost':0.000001,
                'native_tokens_prompt':1,'native_tokens_completion':1,'native_tokens_reasoning':0,'is_byok':False}
    owner.transition(r,'SETTLED',observed_cost=1,billing=b)


def cp(owner,r,answer):
    row=next(x for x in owner.snapshot()['charges'] if x['id']==r);c=row['context']
    p=owner.directory/('phase-'+r+'.local.json')
    atomic_json(p,{'schema_version':1,**{k:c[k] for k in ('run_id','unit_id','phase')},'receipt':r,
                   'request_hash':c['envelope']['request_hash'],'output':answer})
    return p


def complete(owner,**kwargs):
    r=owner.reserve(context(owner,**kwargs));answer,identity=response_seen(owner,r);settled(owner,r,answer,identity)
    owner.commit_phase(r,cp(owner,r,answer));return r


def child_crash(directory,stage):
    owner=OwnerBudgetFixtureV3.open_fixture(directory,clock=lambda:T0);r=owner.reserve(context(owner,run='child'))
    if stage=='RESERVE':os._exit(91)
    answer,identity=response_seen(owner,r)
    if stage=='RESPONSE':os._exit(92)
    settled(owner,r,answer,identity)
    if stage=='SETTLED':os._exit(93)
    path=cp(owner,r,answer)
    if stage=='CHECKPOINT':os._exit(94)
    owner.commit_phase(r,path);os._exit(95)


def child_race(directory,out,counter):
    try:
        owner=OwnerBudgetFixtureV3.open_fixture(directory,clock=lambda:T0)
        owner.reserve(context(owner,run='race'))
        with counter.get_lock():counter.value+=1
        out.put('RESERVED')
    except ExecutionBlocked:out.put('REFUSED')


def reseal(owner,edit):
    """Coedit internal history for semantic negatives, not authentication claims."""
    with sqlite3.connect(owner.db_path) as db:
        rows=[json.loads(x[0]) for x in db.execute('SELECT data FROM events ORDER BY sequence')]
        edit(rows);previous=None;charges={}
        for i,e in enumerate(rows):
            e['previous']=previous;h=canonical_hash(e);previous=h
            db.execute('UPDATE events SET data=?,digest=? WHERE sequence=?',(json.dumps(e,sort_keys=True),h,i))
            body=e['body']
            if body['kind'] in ('RESERVE','TRANSITION'):
                r=body['payload']['after'];charges[r['id']]=r
        for ident,r in charges.items():db.execute('UPDATE charges SET data=? WHERE id=?',(json.dumps(r,sort_keys=True),ident))
    h=json.loads(owner.anchor.read_text());h.update(sequence=len(rows)-1,head_hash=previous);atomic_json(owner.anchor,h)


class OwnerEpochTests(unittest.TestCase):
    def make(self,t,total=100):
        owner=OwnerBudgetFixtureV3.create_fixture(Path(t)/'owner',clock=lambda:T0)
        owner.grant_fixture(approval(owner,total));return owner

    def test_bootstrap_disabled_create_once_missing_and_changed_identity(self):
        with tempfile.TemporaryDirectory() as t:
            owner=OwnerBudgetFixtureV3.create_fixture(Path(t)/'owner',clock=lambda:T0)
            self.assertIsNone(owner.snapshot()['approval_hash']);self.assertEqual(owner.snapshot()['consumed_microusd']['total'],0)
            c=context(owner);c['approval_hash']='0'*64
            with self.assertRaises(ExecutionBlocked):owner.reserve(c)
            with self.assertRaises(ExecutionBlocked):OwnerBudgetFixtureV3.create_fixture(owner.directory)
            for p in (owner.guard,owner.db_path,owner.anchor):self.assertEqual(p.stat().st_mode&0o777,0o600)
            self.assertEqual(owner.directory.stat().st_mode&0o777,0o700)
        for part in ('guard','db_path','anchor'):
            with tempfile.TemporaryDirectory() as t:
                owner=self.make(t);getattr(owner,part).unlink()
                with self.assertRaises(ExecutionBlocked):OwnerBudgetFixtureV3.open_fixture(owner.directory)
                with self.assertRaises(ExecutionBlocked):OwnerBudgetFixtureV3.create_fixture(owner.directory)

    def test_cross_run_module_renewal_retains_absolute_consumption(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t,total=2);first=owner.snapshot()['approval_hash']
            complete(owner,run='e01',module='E01');complete(owner,run='e02')
            self.assertEqual(owner.snapshot()['consumed_microusd'],{'total':2,'modules':{'E01':1,'E02':1}})
            with self.assertRaises(ExecutionBlocked):owner.reserve(context(owner,run='new-directory-run'))
            second=owner.grant_fixture(approval(owner,total=3))
            self.assertNotEqual(first,second);self.assertEqual(owner.snapshot()['consumed_microusd']['total'],2)
            complete(owner,run='renewed')
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],3)
            self.assertEqual({r['context']['approval_hash'] for r in owner.snapshot()['charges']},{first,second})
            with self.assertRaises(ExecutionBlocked):owner.reserve(context(owner,run='over-renewed'))

    def test_invalid_approvals_parent_owner_caps_times_plans_are_zero_change(self):
        changes=[{'previous_approval_hash':None},{'owner_id':'0'*32},{'kind':'REAL_OWNER_APPROVAL'},
                 {'total_microusd':True},{'total_microusd':0},{'module_microusd':{'E01':1}},
                 {'valid_from_utc':(T0+timedelta(hours=1)).isoformat()},
                 {'valid_until_utc':(T0-timedelta(seconds=1)).isoformat()},
                 {'allowed_plans':{}}]
        for change in changes:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as t:
                owner=self.make(t);before=owner.snapshot()
                with self.assertRaises((ExecutionBlocked,ValueError)):owner.grant_fixture(approval(owner,**change))
                self.assertEqual(owner.snapshot(),before)
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t);complete(owner)
            with self.assertRaises(ExecutionBlocked):owner.grant_fixture(approval(owner,total=1,module_microusd={'E01':1,'E02':0}))
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],1)

    def test_plan_binding_ceiling_module_price_and_stale_authority_refuse(self):
        for mutate in (lambda c:c.__setitem__('approval_hash','0'*64),lambda c:c.__setitem__('plan_hash','1'*64),
                       lambda c:c.__setitem__('plan_hash',PLAN['E01']),
                       lambda c:c['terms'].__setitem__('model','DIFFERENT'),
                       lambda c:c['envelope'].__setitem__('reserved_microusd',0),
                       lambda c:c['sampling'].__setitem__('seed',True)):
            with tempfile.TemporaryDirectory() as t:
                owner=self.make(t);c=context(owner);mutate(c)
                with self.assertRaises((ExecutionBlocked,ValueError)):owner.reserve(c)
                self.assertEqual(owner.snapshot()['charges'],[])
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t);a=approval(owner);a['allowed_plans'][PLAN['E02']]['max_input_token_bound']=1;owner.grant_fixture(a)
            with self.assertRaises(ExecutionBlocked):owner.reserve(context(owner))

    def test_late_accounting_after_expiry_and_valid_new_renewal(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t);original=owner.snapshot()['approval_hash'];r=owner.reserve(context(owner))
            owner.clock=lambda:T0+timedelta(hours=1)
            answer,identity=response_seen(owner,r);settled(owner,r,answer,identity);owner.commit_phase(r,cp(owner,r,answer))
            self.assertEqual(owner.snapshot()['charges'][0]['context']['approval_hash'],original)
            with self.assertRaises(ExecutionBlocked):owner.reserve(context(owner,unit='later'))
            owner.grant_fixture(approval(owner,total=100,now=T0+timedelta(hours=1)))
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],1)
            complete(owner,unit='later');self.assertEqual(owner.snapshot()['consumed_microusd']['total'],2)

    def test_unknown_and_overrun_survive_expiry_and_renewal(self):
        for state in ('UNCERTAIN','OVERRUN'):
            with self.subTest(state=state),tempfile.TemporaryDirectory() as t:
                owner=self.make(t);r=owner.reserve(context(owner));owner.clock=lambda:T0+timedelta(hours=1)
                if state=='OVERRUN':response_seen(owner,r)
                owner.transition(r,state,observed_cost=201)
                self.assertEqual(owner.snapshot()['consumed_microusd']['total'],201)
                with self.assertRaises(ExecutionBlocked):owner.grant_fixture(approval(owner,total=500,now=T0+timedelta(hours=1)))
                with self.assertRaises(ExecutionBlocked):owner.reserve(context(owner,unit='new'))

    def test_rollback_billing_uses_actual_clock_and_keeps_dispatch_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t);r=owner.reserve(context(owner));prior=owner.snapshot()['maximum_observed_utc']
            owner.clock=lambda:T0-timedelta(hours=1)
            answer,identity=response_seen(owner,r);settled(owner,r,answer,identity);owner.commit_phase(r,cp(owner,r,answer))
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],1)
            self.assertEqual(owner.snapshot()['maximum_observed_utc'],prior)
            with sqlite3.connect(owner.db_path) as db:
                body=json.loads(db.execute('SELECT data FROM events ORDER BY sequence DESC LIMIT 1').fetchone()[0])['body']
            self.assertEqual(body['clock_status'],'CLOCK_ROLLBACK')
            self.assertEqual(body['recorded_at_utc'],(T0-timedelta(hours=1)).isoformat())
            with self.assertRaises(ExecutionBlocked):owner.reserve(context(owner,unit='rollback'))
            with self.assertRaises(ExecutionBlocked):owner.grant_fixture(approval(owner,now=T0-timedelta(hours=1)))
            owner.clock=lambda:T0;complete(owner,unit='recovered')

    def test_generation_and_phase_identity_unique_across_approval_epochs(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t);first=complete(owner);old=owner.snapshot()['charges'][0]
            owner.grant_fixture(approval(owner))
            with self.assertRaises(ExecutionBlocked):owner.reserve(context(owner))
            second=owner.reserve(context(owner,unit='different'))
            with self.assertRaises(ValueError):owner.transition(second,'RESPONSE_SEEN',generation_id=old['generation_id'],output_hash='a'*64)
            self.assertEqual(owner.snapshot()['charges'][1]['status'],'STARTED')
            with self.assertRaises(ExecutionBlocked):owner.grant_fixture(approval(owner))

    def test_no_direct_commit_wrong_checkpoint_or_mutable_input_alias(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t);c=context(owner);original=deepcopy(c);lock=owner._lock
            def changed_lock():c['terms']['model']='UNRELEASED';return lock()
            with patch.object(owner,'_lock',side_effect=changed_lock):r=owner.reserve(c)
            self.assertEqual(owner.snapshot()['charges'][0]['context'],original)
            answer,identity=response_seen(owner,r);settled(owner,r,answer,identity)
            with self.assertRaises(ExecutionBlocked):owner.transition(r,'PHASE_COMMITTED',checkpoint_hash='a'*64)
            path=cp(owner,r,answer);x=json.loads(path.read_text());x['unit_id']='other';atomic_json(path,x)
            with self.assertRaises(ValueError):owner.commit_phase(r,path)
            self.assertEqual(owner.snapshot()['charges'][0]['status'],'SETTLED')

    def test_semantic_cost_and_materialized_counter_corruption_refuse(self):
        for mode in ('counter','undercharge','clock'):
            with tempfile.TemporaryDirectory() as t:
                owner=self.make(t);r=owner.reserve(context(owner));owner.transition(r,'UNCERTAIN',observed_cost=201)
                if mode=='counter':
                    with sqlite3.connect(owner.db_path) as db:
                        row=json.loads(db.execute('SELECT data FROM charges').fetchone()[0]);row['charged']=1
                        db.execute('UPDATE charges SET data=?',(json.dumps(row),))
                else:
                    def edit(events):
                        body=events[-1]['body']
                        if mode=='undercharge':body['payload']['after']['charged']=1
                        else:body['clock_status']='CLOCK_ROLLBACK'
                    reseal(owner,edit)
                with self.assertRaises((ExecutionBlocked,ValueError)):OwnerBudgetFixtureV3.open_fixture(owner.directory,clock=lambda:T0)

    def test_historical_caps_not_retroactively_replaced_by_larger_approval(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t,total=3);old=owner.snapshot()['approval_hash'];complete(owner,unit='one');complete(owner,unit='two')
            owner.grant_fixture(approval(owner,total=100))
            def edit(events):
                first=events[1]['body']['payload'];first['total_microusd']=1;first['module_microusd']={'E01':1,'E02':1};changed=canonical_hash(first)
                for e in events[2:]:
                    b=e['body']
                    if b['kind']=='APPROVAL':b['payload']['previous_approval_hash']=changed
                    else:
                        row=b['payload']['after'];row['context']['approval_hash']=changed
                # Reconstruct each semantic before-hash after consistent rekeying.
                known={}
                for e in events:
                    b=e['body']
                    if b['kind'] in ('RESERVE','TRANSITION'):
                        row=b['payload']['after'];b['payload']['before_hash']=canonical_hash(known[row['id']]) if row['id'] in known else None;known[row['id']]=deepcopy(row)
            reseal(owner,edit)
            with self.assertRaises(ExecutionBlocked):OwnerBudgetFixtureV3.open_fixture(owner.directory,clock=lambda:T0)

    def test_torn_head_and_real_process_crash_boundaries(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t)
            with patch('civiclab.owner_budget_v3.atomic_json',side_effect=OSError('AUTHORED disk failure')):
                with self.assertRaises(OSError):owner.reserve(context(owner))
            with self.assertRaises(ExecutionBlocked):OwnerBudgetFixtureV3.open_fixture(owner.directory,clock=lambda:T0)
        for stage,code,status in [('RESERVE',91,'STARTED'),('RESPONSE',92,'RESPONSE_SEEN'),('SETTLED',93,'SETTLED'),('CHECKPOINT',94,'SETTLED'),('COMMITTED',95,'PHASE_COMMITTED')]:
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as t:
                owner=self.make(t);ctx=multiprocessing.get_context('spawn');p=ctx.Process(target=child_crash,args=(str(owner.directory),stage));p.start();p.join(20)
                self.assertFalse(p.is_alive());self.assertEqual(p.exitcode,code)
                reopened=OwnerBudgetFixtureV3.open_fixture(owner.directory,clock=lambda:T0)
                self.assertEqual(reopened.snapshot()['charges'][0]['status'],status)
                if status!='PHASE_COMMITTED':
                    with self.assertRaises(ExecutionBlocked):reopened.grant_fixture(approval(reopened))
                    with self.assertRaises(ExecutionBlocked):reopened.reserve(context(reopened,unit='future'))
                else:complete(reopened,unit='future')

    def test_two_real_processes_single_global_reservation(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t);ctx=multiprocessing.get_context('spawn');out=ctx.Queue();counter=ctx.Value('i',0)
            children=[ctx.Process(target=child_race,args=(str(owner.directory),out,counter)) for _ in range(2)]
            for p in children:p.start()
            for p in children:p.join(20);self.assertFalse(p.is_alive());self.assertEqual(p.exitcode,0)
            self.assertEqual(sorted(out.get(timeout=2) for _ in children),['REFUSED','RESERVED']);self.assertEqual(counter.value,1)
            self.assertEqual(len(owner.snapshot()['charges']),1)

    def test_os_account_path_ignores_environment_and_production_stays_disabled(self):
        with patch('civiclab.owner_budget_v3.pwd.getpwuid',return_value=SimpleNamespace(pw_dir='/AUTHORED-OS-HOME')):
            with patch.dict(os.environ,{'HOME':'/UNTRUSTED-ENV','XDG_DATA_HOME':'/UNTRUSTED-XDG'}):
                with patch('civiclab.owner_budget_v3.sys.platform','darwin'):
                    self.assertEqual(production_owner_directory(),Path('/AUTHORED-OS-HOME/Library/Application Support/SyntheticSocietyLab/openrouter-v3'))
                with patch('civiclab.owner_budget_v3.sys.platform','linux'):
                    self.assertEqual(production_owner_directory(),Path('/AUTHORED-OS-HOME/.local/share/synthetic-society-lab/openrouter-v3'))
        with patch('civiclab.owner_budget_v3.production_owner_directory') as location:
            with self.assertRaises(ExecutionBlocked):create_live_owner()
            location.assert_not_called()

    def test_unavailable_clock_keeps_known_accounting_with_null_time(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t);r=owner.reserve(context(owner));owner.clock=lambda:None
            answer,identity=response_seen(owner,r);settled(owner,r,answer,identity);owner.commit_phase(r,cp(owner,r,answer))
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],1)
            with sqlite3.connect(owner.db_path) as db:
                b=json.loads(db.execute('SELECT data FROM events ORDER BY sequence DESC LIMIT 1').fetchone()[0])['body']
            self.assertIsNone(b['recorded_at_utc']);self.assertEqual(b['clock_status'],'CLOCK_UNAVAILABLE')
            self.assertEqual(b['clock_error'],'UNAVAILABLE_UTC')
            with self.assertRaises(ExecutionBlocked):owner.reserve(context(owner,unit='no-time'))
            with self.assertRaises(ExecutionBlocked):owner.grant_fixture(approval(owner))
            owner.clock=lambda:T0;complete(owner,unit='time-recovered')

    def test_independent_per_request_rounding_with_fractional_micro_prices(self):
        with tempfile.TemporaryDirectory() as t:
            owner=self.make(t,total=2);tiny=terms();tiny.update(input_usd_per_token='0.0000000001',request_fee_usd='0.0000001')
            a=approval(owner,total=2);a['allowed_plans'][PLAN['E02']]['terms_sha256']=canonical_hash(tiny);owner.grant_fixture(a)
            for unit in ('one','two'):
                c=context(owner,unit=unit);c['terms']=tiny;c['envelope']=quote([{'role':'user','content':'AUTHORED ONLY'}],32,tiny)
                self.assertEqual(c['envelope']['reserved_microusd'],1)
                r=owner.reserve(c);answer,identity=response_seen(owner,r)
                b={'id':identity,'model':tiny['model'],'provider_name':tiny['reported_provider'],'total_cost':0.0000001001,
                   'native_tokens_prompt':1,'native_tokens_completion':1,'native_tokens_reasoning':0,'is_byok':False}
                owner.transition(r,'SETTLED',observed_cost=micros(b['total_cost']),billing=b);owner.commit_phase(r,cp(owner,r,answer))
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],2)
            c=context(owner,unit='third');c['terms']=tiny;c['envelope']=quote([{'role':'user','content':'AUTHORED ONLY'}],32,tiny)
            with self.assertRaises(ExecutionBlocked):owner.reserve(c)
