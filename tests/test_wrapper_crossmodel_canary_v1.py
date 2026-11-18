"""Focused MOCK and temporary copied-history checks, never a live owner/key.

No test hook or closed-data read on import. Direct main enforces author bounds.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.owner_budget_v3 import utc
from civiclab.production_admission_v4 import _Credential
from civiclab.production_owner_v4 import price_proof_key
from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
from civiclab.e02 import wrapper_crossmodel_canary_v1 as p
from civiclab.e02 import wrapper_crossmodel_canary_v1_owner as m
from civiclab.e02 import wrapper_crossmodel_canary_v1_client as c
from civiclab.e02 import exploratory_live_client_v1 as frozen
from civiclab import production_owner_v4 as production

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01'
HISTORICAL_PRICES=ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_price_01'
METER=None
FORK_AUTHORIZED=False


def read_pinned(path,size,digest):
    raw=path.read_bytes()
    if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=digest:raise AssertionError('CLOSED_INPUT_PIN')
    return json.loads(raw)


class CopiedOwner(m.CanaryOwnerV1):
    """Test-only copied accepted seed; not a bootstrap/replay admission factory.

    Prefix event objects/hash chain checked against immutable closed export.
    Only newly appended typed events replay through production canary reducer.
    No old live journal, registration or financial owner location is read.
    """
    def __init__(self,directory,export):
        self.directory=directory;self.directory.mkdir();self.header=deepcopy(export['header'])
        self.guard=directory/'guard.json';self.guard.write_bytes(canonical_bytes(self.header))
        self.db_path=directory/'copy.sqlite';self.anchor=directory/'head.json'
        self.seed=deepcopy(export)
        self.seed['statistics_claims']=set(export['statistics_claims'])
        self.seed['keys']={canonical_hash({k:row['context'][k] for k in ('run_id','unit_id','phase','module')}) for row in export['rows'].values()}
        self.seed['generations']={row['generation_id']:key for key,row in export['rows'].items() if row['generation_id'] is not None}
        self.seed['price_proofs']={price_proof_key(row['context']) for row in export['rows'].values()}
        self.seed['max_clock']=max(utc(event['body']['recorded_at_utc']) for event in export['history'] if event['body']['recorded_at_utc'])
        self.seed['approvals']={};self.seed['active']=export['active_approval_hash'];self.seed['approval_ids']=set()
        # Export-only observations cannot be mutable state/hash inputs.
        for key in ('history','head','HTTP_requests','credential_reads','owner_writes','control_file_hashes_before','control_file_hashes_after','history_hash'):
            self.seed.pop(key,None)
        self.prefix=[(event['sequence'],canonical_bytes(event).decode(),canonical_hash(event)) for event in export['history']]
        if METER is not None:METER['writes'][0]+=16*1024*1024  # Conservative SQLite/journal reservation.
        with sqlite3.connect(self.db_path) as db:
            db.execute('PRAGMA max_page_count=2048')
            db.execute('CREATE TABLE events(sequence INTEGER PRIMARY KEY,data TEXT,digest TEXT)')
            db.execute('CREATE TABLE charges(id TEXT PRIMARY KEY,data TEXT)')
            db.executemany('INSERT INTO events VALUES (?,?,?)',self.prefix)
            db.executemany('INSERT INTO charges VALUES (?,?)',[(key,json.dumps(row,sort_keys=True)) for key,row in export['rows'].items()])
        self.anchor.write_bytes(canonical_bytes(export['head']))
    def _registration(self):
        if not self.directory.name.startswith('AUTHORED_CANARY_COPY'):raise AssertionError('NOT_AUTHORED_LOCATION')
    def _verify(self,db):
        self._registration();rows=db.execute('SELECT sequence,data,digest FROM events ORDER BY sequence').fetchall()
        if METER is not None:
            METER['reads'][0]+=sum(len(data.encode()) for _,data,_ in rows)
            if METER['reads'][0]>METER['read_limit']:raise AssertionError('LOGICAL_SQL_READ_CAP')
        if rows[:len(self.prefix)]!=self.prefix:raise ExecutionBlocked('copied historical prefix changed')
        state=deepcopy(self.seed);history=[json.loads(data) for _,data,_ in self.prefix]
        previous=self.prefix[-1][2]
        head=json.loads(self.anchor.read_bytes())
        for sequence,data,digest in rows[len(self.prefix):]:
            event=json.loads(data)
            if event['sequence']!=sequence or event['previous']!=previous or canonical_hash(event)!=digest:raise ExecutionBlocked('new copied chain')
            state['_prefix_head']={**head,'sequence':sequence-1,'head_hash':previous};state['_prefix_events']=history[:]
            self._apply(event['body'],state);history.append(event);previous=digest
        expected={**head,'sequence':len(rows)-1,'head_hash':previous}
        if head!=expected:raise ExecutionBlocked('copied store/head torn')
        actual={key:json.loads(data) for key,data in db.execute('SELECT id,data FROM charges')}
        if actual!=state['rows']:raise ExecutionBlocked('copied materialized rows mismatch')
        state['_prefix_head']=head;state['_prefix_events']=history
        if m.STATE in state:
            p.need(state[m.STATE]['pending'] is None,'copied partial grant')
            self._protect(state,state[m.STATE])
        return state,head


class Catalog:
    def __init__(self,records,now):self.records=records;self.now=now;self.calls=[]
    def __call__(self,model):
        role='A' if model=='openai/gpt-4.1-nano' else 'B';self.calls.append(role)
        record=self.records[role];raw=record['body_utf8'].encode()
        return raw,{'url':record['metadata']['url'],'body_sha256':hashlib.sha256(raw).hexdigest(),'observed_at_utc':self.now().isoformat()}


class Transport:
    def __init__(self,mode='OK'):self.mode=mode;self.posts=0;self.gets=0
    def post_bytes(self,raw):
        self.posts+=1;self.payload=json.loads(raw)
        if self.mode=='402':raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',402)
        if self.mode=='UNKNOWN':raise TimeoutError('MOCK_ONLY')
        response={'id':'gen-canary-mock-1','model':'qwen/qwen3-30b-a3b-instruct-2507',
          'choices':[{'message':{'content':json.dumps({'democratic_party':50,'republican_party':50,'policy_support':50,'factual_answer':'INCREASE_40'})}}],
          'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150,'cost':0.00001}}
        if self.mode=='MODEL':response['model']='foreign/model'
        if self.mode=='OVER':response['usage']['cost']=1
        return response
    def statistics(self,generation):
        self.gets+=1
        if self.mode in {'404','DELAY'} and (self.mode=='404' or self.gets==1):raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
        if self.mode=='429':raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',429)
        stats={'id':generation,'model':'qwen/qwen3-30b-a3b-instruct-2507','provider_name':'Nebius',
               'total_cost':0.00001,'native_tokens_prompt':100,'native_tokens_completion':50,'native_tokens_reasoning':0,
               'is_byok':False,'service_tier':None,'streamed':False,'cancelled':False}
        if self.mode=='PROVIDER':stats['provider_name']='Other'
        if self.mode=='BILL':stats['total_cost']=None
        if self.mode=='BYOK':stats['is_byok']=True
        return {'data':stats}


class CopiedHistoryCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (BASE/'post-run-owner-export.local.json').is_file():raise unittest.SkipTest('Pinned closed history unavailable; copied-history checks NOT_RUN')
        cls.export=read_pinned(BASE/'post-run-owner-export.local.json',3893676,'ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66')
        cls.old_packet=read_pinned(BASE/'packet.local.json',7339,'3b29761579efaabee4ef03c6c71ae5f476ced64980fa6d362c5eea55489457ec')
        cls.records={role:json.loads((BASE/f'retained-journal/catalog-4-{role}.json').read_text()) for role in ('A','B')}
        cls.historical_raw={role:(HISTORICAL_PRICES/f'catalog-{role}.json').read_bytes() for role in ('A','B')}
        cls.historical_receipts={role:json.loads((HISTORICAL_PRICES/f'receipt-{role}.json').read_text()) for role in ('A','B')}
        for role in ('A','B'):
            assert hashlib.sha256(cls.historical_raw[role]).hexdigest()==cls.old_packet['price_release'][role]['terms']['initial_catalog_sha256']
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name).resolve()
        self.owner=CopiedOwner(root/'AUTHORED_CANARY_COPY',self.export)
        self.real_mono=time.monotonic;self.start=self.real_mono();self.base=datetime(2026,11,17,11,18,tzinfo=timezone.utc)
        self.now=lambda:self.base+timedelta(seconds=self.real_mono()-self.start)
        self.clockpatch=patch.object(production,'_utc_now',side_effect=self.now);self.clockpatch.start()
        self.phasepatch=patch.object(frozen,'new_operation_time',side_effect=self.now);self.phasepatch.start()
        self.waitpatch=patch.object(frozen._Phase,'wait_for_statistics',return_value=None);self.waitpatch.start()
        self.q={'kind':'WRAPPER_CANARY_PACKET_V1','owner_id':self.export['header']['owner_id'],
                'parent_key':p.identity(self.export['header']['owner_id']),'expected_head':deepcopy(self.export['head']),
                'parent_binding':deepcopy(m.ANCHOR),'run_id':'AUTHORED_CANARY_RUN','valid_from_utc':self.base.isoformat(),
                'valid_until_utc':(self.base+timedelta(seconds=600)).isoformat(),'bounds':deepcopy(p.BOUNDS),
                'code_hash':canonical_hash(p.contract()),'price_release':deepcopy(self.old_packet['price_release'])}
        self.q['price_release']={role:p.lease_historical_catalog(self.historical_raw[role],self.old_packet['price_release'][role],expected_release_hash=canonical_hash(self.old_packet['price_release'][role]),valid_from=self.base.isoformat(),valid_until=(self.base+timedelta(seconds=600)).isoformat()) for role in ('A','B')}
        self.bind()
        self.catalog=Catalog(self.records,self.now)
    def tearDown(self):
        self.waitpatch.stop();self.phasepatch.stop();self.clockpatch.stop();self.tmp.cleanup()
    def bind(self):
        self.q['authority']={'kind':p.AUTHORITY,'scope_hash':canonical_hash({k:v for k,v in self.q.items() if k not in ('authority','review')})}
        self.q['review']={'kind':'INDEPENDENT_WRAPPER_CANARY_REVIEW_V1','reviewer_role':'independent_auditor','review_id':'a'*32,'inputs_hash':canonical_hash({k:v for k,v in self.q.items() if k!='review'})}
        self.release={'kind':'LEAD_WRAPPER_CANARY_RELEASE_V1','packet_sha256':canonical_hash(self.q),'code_hash':canonical_hash(p.contract()),'review_sha256':canonical_hash(self.q['review']),'maximum_POSTs':1,'scope':'ORIGINAL45_ONLY_NOT_FULL80'}
    def execute(self,mode='OK'):
        t=Transport(mode);self.transport=t
        return c.execute(self.q,expected_packet_hash=canonical_hash(self.q),release=self.release,expected_release_hash=canonical_hash(self.release),owner=self.owner,
                         credential=_Credential('AUTHORED_MOCK_NOT_REAL_KEY_1234'),transport=t,catalog_fetch=self.catalog,
                         gate=c.OperationGate(self.q,now=self.now),sleep=lambda seconds:None)
    def preserved(self):
        with self.owner._lock(),self.owner._connect() as db:state,head=self.owner._verify(db)
        self.assertEqual(canonical_hash({k:state['rows'][k] for k in self.export['rows']}),canonical_hash(self.export['rows']))
        self.assertEqual(canonical_hash(state['wrapper_crossmodel']),canonical_hash(self.export['wrapper_crossmodel']))
        self.assertEqual(canonical_hash(state['_prefix_events'][:1180]),canonical_hash(self.export['history']))
        self.assertEqual(sorted(row['charged'] for key,row in state['rows'].items() if key in self.export['rows'] and row['status']!='PHASE_COMMITTED'),[340,340,775,788,1008])
        return state
    def ready(self):
        self.owner.open_canary(self.q,canonical_hash(self.q));journal=frozen._Journal(self.owner,self.q['run_id'],self.q)
        proofs={}
        for role in ('A','B'):
            self.owner.intent('CATALOG_'+role,1);raw,metadata=self.catalog(self.q['price_release'][role]['terms']['model']);rel=self.q['price_release'][role]
            proof=m.fresh_proof(raw,metadata,rel['interpretation'],rel['terms'],now=self.now())
            journal.write('catalog-'+role+'.json',{'body_utf8':raw.decode(),'metadata':metadata,'proof':proof});proofs[role]=proof
        self.owner.register_proofs(proofs);return journal
    def test_success_one_slot_preserves_all_history_and_no_reopen(self):
        r=self.execute();self.assertEqual(r['status'],'COMMITTED_ONE_SLOT');self.assertEqual(r['original_full80_analysis'],'NOT_RUN_INCOMPLETE')
        self.assertEqual((self.transport.posts,self.transport.gets,self.catalog.calls),(1,1,['A','B']))
        state=self.preserved();self.assertEqual(state['consumed']['dispatches'],195);self.assertEqual(state['unfinished'],5)
        with self.assertRaises(ExecutionBlocked):self.owner.open_canary(self.q,canonical_hash(self.q))
    def test_402_preserves_full_new_and_five_old_holds(self):
        with self.assertRaises(_SafeTransportFailure):self.execute('402')
        state=self.preserved();row=state['rows'][state[m.STATE]['receipt']]
        self.assertEqual(row['status'],'UNCERTAIN');self.assertEqual(row['charged'],row['reserved'])
        self.assertEqual(state['unfinished'],6);self.assertEqual(self.transport.posts,1)
    def test_provider_drift_stops_without_refund(self):
        with self.assertRaises(ExecutionBlocked):self.execute('PROVIDER')
        self.assertEqual(self.transport.gets,1);state=self.preserved();self.assertEqual(state['unfinished'],6)
    def test_unknown_bill_stops_and_keeps_full_hold(self):
        with self.assertRaises(ExecutionBlocked):self.execute('BILL')
        state=self.preserved();r=state['rows'][state[m.STATE]['receipt']];self.assertEqual(r['charged'],r['reserved'])
    def test_404_only_three_gets_no_post_retry(self):
        with self.assertRaises(_SafeTransportFailure):self.execute('404')
        state=self.preserved();self.assertEqual((self.transport.posts,self.transport.gets),(1,3));self.assertEqual(state[m.STATE]['counts']['statistics_GET'],3)
    def test_atomic_before_and_after_commit_crash(self):
        j=self.ready()
        try:
            with patch.object(self.owner,'_fault',side_effect=lambda label: (_ for _ in ()).throw(RuntimeError('MOCK_CRASH')) if label=='before_append' else None):
                with self.assertRaises(RuntimeError):self.owner.grant()
            state=self.preserved();self.assertIsNone(state[m.STATE]['receipt']);self.assertEqual(len(state['rows']),194)
            with patch.object(self.owner,'_fault',side_effect=lambda label: (_ for _ in ()).throw(RuntimeError('MOCK_CRASH')) if label=='after_append' else None):
                with self.assertRaises(RuntimeError):self.owner.grant()
            state=self.preserved();self.assertEqual(len(state['rows']),195)
            with self.assertRaises(ExecutionBlocked):self.owner.grant()
        finally:j.close()
    def test_alias_head_slot_and_io_ordinals_refuse(self):
        original=deepcopy(self.q)
        for change in ('head','owner','parent','hold'):
            q=deepcopy(original)
            if change=='head':q['expected_head']['head_hash']='0'*64
            if change=='owner':q['owner_id']='0'*32;q['parent_key']=p.identity(q['owner_id'])
            if change=='parent':q['parent_key']='0'*64
            if change=='hold':q['parent_binding']['protected']='0'*64
            q['authority']={'kind':p.AUTHORITY,'scope_hash':canonical_hash({k:v for k,v in q.items() if k not in ('authority','review')})}
            q['review']={**q['review'],'inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='review'})}
            with self.subTest(change=change),self.assertRaises(ExecutionBlocked):self.owner.open_canary(q,canonical_hash(q))
        self.owner.open_canary(self.q,canonical_hash(self.q));self.owner.intent('CATALOG_A',1)
        with self.assertRaises(ExecutionBlocked):self.owner.intent('CATALOG_A',1)
        with self.assertRaises(ExecutionBlocked):self.owner.intent('CATALOG_B',2)
        q=deepcopy(self.q);q['run_id']='ALIAS_NEW_RUN';q['authority']={'kind':p.AUTHORITY,'scope_hash':canonical_hash({k:v for k,v in q.items() if k not in ('authority','review')})};q['review']={**q['review'],'inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='review'})}
        with self.assertRaises(ExecutionBlocked):self.owner.open_canary(q,canonical_hash(q))
        self.assertEqual(self.owner.canary_snapshot()['branch']['counts']['catalog_GET'],1)


    def test_overrun_preserves_known_charge_and_stops(self):
        with self.assertRaises(ExecutionBlocked):self.execute('OVER')
        state=self.preserved();row=state['rows'][state[m.STATE]['receipt']]
        self.assertGreater(row['charged'],row['reserved']);self.assertEqual(self.transport.gets,0)

    def test_copied_parent_payload_slot_and_original_halt_negatives(self):
        state=deepcopy(self.owner.seed);state['_prefix_head']=deepcopy(self.export['head']);state['_prefix_events']=deepcopy(self.export['history'])
        for field in ('unfinished','baseline','hold'):
            altered=deepcopy(state)
            if field=='unfinished':altered['unfinished']=6
            elif field=='baseline':altered['wrapper_crossmodel']['witnesses'][13]['answer']=None
            else:
                rid=altered['wrapper_crossmodel']['receipts'][-1];altered['rows'][rid]['charged']=774
            event=self.owner._event(m.OPEN,{'packet':self.q},altered,new=True)
            with self.subTest(field=field),self.assertRaises(ExecutionBlocked):self.owner._apply(event,altered)
        for order in (44,46):
            q=dict(self.q,slot=order)
            with self.assertRaises(ExecutionBlocked):p.validate_packet(q,canonical_hash(q))
        raw=read_pinned(BASE/'retained-journal/failure.json',100561,'c01dcb0c1a8c3737bce68c419e810c004230c3dd0923102065ea01ded54e7de7')
        from civiclab.e02 import wrapper_crossmodel_v1 as old
        envelope=deepcopy(raw['authenticated_terminal']['response_envelope'])
        envelope['records'][45]['status']='PARSE_ERROR'
        with self.assertRaises(ExecutionBlocked):old._validate_records(old.load_protocol(p.PROTOCOL.read_bytes()),envelope)
        j=self.ready()
        try:
            ack=self.owner._canary_context(self.owner.seed,self.owner.canary_snapshot()['branch'])
            ack['context']['payload_hash']='0'*64
            with self.assertRaises(ExecutionBlocked):self.owner._atomic(m.GRANT,{'ack':ack})
            self.assertEqual(len(self.preserved()['rows']),194)
        finally:j.close()

    def test_stale_future_catalog_and_usage_provider_fields_refuse(self):
        raw,metadata=self.catalog(self.q['price_release']['B']['terms']['model']);rel=self.q['price_release']['B']
        for seconds in (-901,1):
            changed=dict(metadata,observed_at_utc=(self.now()+timedelta(seconds=seconds)).isoformat())
            with self.subTest(seconds=seconds),self.assertRaises(ExecutionBlocked):m.fresh_proof(raw,changed,rel['interpretation'],rel['terms'],now=self.now())
        compiled,_=p.compile_slot(self.export['wrapper_crossmodel'],rel['terms'])
        transport=Transport();transport.post_bytes(canonical_bytes(compiled['payload']));stats=transport.statistics('gen-canary-mock-1')['data']
        for key,value in [('provider_name','OTHER'),('model','other/model'),('is_byok',True),('total_cost',None),('total_cost',float('nan')),('native_tokens_prompt',9000),('native_tokens_reasoning',1)]:
            from civiclab.e02.crossmodel_recovery_metadata_v1 import normalize_statistics
            changed=dict(stats,**{key:value})
            with self.subTest(field=key,value=str(value)),self.assertRaises((ExecutionBlocked,ValueError)):
                normalize_statistics(changed,generation_id='gen-canary-mock-1',requested_model=rel['terms']['model'],reported_provider='Nebius',input_bound=compiled['envelope']['input_token_bound'],output_bound=256,reserved_microusd=compiled['envelope']['reserved_microusd'],request_payload=compiled['payload'])
        self.assertEqual(len(self.preserved()['rows']),194)
        from decimal import Decimal
        for role in ('A','B'):
            release=self.q['price_release'][role];old=self.old_packet['price_release'][role]
            self.assertNotEqual(release['terms']['interpretation_hash'],old['terms']['interpretation_hash'])
            self.assertEqual(release['terms']['initial_catalog_sha256'],old['terms']['initial_catalog_sha256'])
            # Old genuine observation cannot be reclassified as fresh Nov17.
            with self.assertRaises(ExecutionBlocked):m.fresh_proof(self.historical_raw[role],self.historical_receipts[role],release['interpretation'],release['terms'],now=self.now())
            value=json.loads(self.historical_raw[role]);value['MOCK_ignored_nonce']='NONSEMANTIC_BYTES_ONLY'
            fresh=canonical_bytes(value);metadata={'url':self.historical_receipts[role]['url'],'body_sha256':hashlib.sha256(fresh).hexdigest(),'observed_at_utc':self.now().isoformat()}
            self.assertNotEqual(metadata['body_sha256'],release['terms']['initial_catalog_sha256'])
            m.fresh_proof(fresh,metadata,release['interpretation'],release['terms'],now=self.now())
            for factor in ('0.5','2'):
                changed=deepcopy(value)
                for endpoint in changed['data']['endpoints']:
                    if endpoint.get('tag','')==release['terms']['requested_route'] or endpoint.get('tag','').startswith(release['terms']['requested_route']+'/'):
                        endpoint['pricing']['prompt']=str(Decimal(endpoint['pricing']['prompt'])*Decimal(factor))
                raw_changed=canonical_bytes(changed);receipt_changed=dict(metadata,body_sha256=hashlib.sha256(raw_changed).hexdigest())
                with self.subTest(role=role,factor=factor),self.assertRaises(ExecutionBlocked):m.fresh_proof(raw_changed,receipt_changed,release['interpretation'],release['terms'],now=self.now())
            with self.assertRaises(ExecutionBlocked):m.fresh_proof(fresh,metadata,release['interpretation'],release['terms'],now=self.base+timedelta(seconds=601))
        self.owner.open_canary(self.q,canonical_hash(self.q))
        with self.assertRaises((ExecutionBlocked,TypeError)):self.owner.grant()
        self.assertEqual(len(self.preserved()['rows']),194)

    def test_two_processes_cannot_grant_same_original_slot(self):
        global FORK_AUTHORIZED
        j=self.ready();children=[]
        try:
            if METER is not None:
                METER['reads'][0]+=64*1024*1024;METER['writes'][0]+=32*1024*1024
            for _ in range(2):
                FORK_AUTHORIZED=True
                pid=os.fork()
                if pid==0:
                    FORK_AUTHORIZED=False
                    import resource,signal
                    resource.setrlimit(resource.RLIMIT_CPU,(4,5));signal.alarm(10)
                    if METER is not None:METER['reads'][0]=0;METER['read_limit']=32*1024*1024
                    try:self.owner.grant()
                    except ExecutionBlocked:os._exit(2)
                    except BaseException:os._exit(3)
                    os._exit(0)
                children.append(pid);FORK_AUTHORIZED=False
            outcomes=[];started=self.real_mono()
            while children and self.real_mono()-started<12:
                for pid in children[:]:
                    done,status=os.waitpid(pid,os.WNOHANG)
                    if done:outcomes.append(os.waitstatus_to_exitcode(status));children.remove(pid)
                if children:time.sleep(.01)
            self.assertFalse(children);self.assertEqual(sorted(outcomes),[0,2])
            state=self.preserved();self.assertEqual(len(state['rows']),195)
            self.owner.intent('POST',1)
            with self.assertRaises(ExecutionBlocked):self.owner.intent('POST',1)
        finally:
            FORK_AUTHORIZED=False
            for pid in children:
                import signal
                os.kill(pid,signal.SIGKILL);os.waitpid(pid,0)
            j.close()


class PureCases(unittest.TestCase):
    def test_identity_independent_of_head_alias(self):
        self.assertEqual(p.identity('a'*32),p.identity('a'*32));self.assertNotEqual(p.identity('a'*32),p.identity('b'*32))
    def test_envelope_rejects_44_46_or_extra_records(self):
        r={'execution_order':45,'phase':'post','status':'FAILED_UNCERTAIN','answer':None,'payload_sha256':'a'*64,'receipt':'b'*32}
        e=p.envelope('c'*64,[r],'STOPPED','MOCK');self.assertTrue(e['parent_stopped'])
        for rows in ([dict(r,execution_order=44)],[dict(r,execution_order=46)],[r,r]):
            with self.assertRaises(ExecutionBlocked):p.envelope('c'*64,rows,'STOPPED','MOCK')
    def test_clock_rollback_jump_deadline_cancel(self):
        base=datetime(2026,1,1,tzinfo=timezone.utc);q={'valid_from_utc':base.isoformat(),'valid_until_utc':(base+timedelta(seconds=900)).isoformat()}
        for mode in ('rollback','jump','deadline','cancel'):
            tick=[0];utc_offset=[0];cancel=[False]
            g=c.OperationGate(q,mono=lambda:tick[0],now=lambda:base+timedelta(seconds=tick[0]+utc_offset[0]),cancelled=lambda:cancel[0])
            if mode=='rollback':tick[0]=-1
            elif mode=='jump':utc_offset[0]=10
            elif mode=='deadline':tick[0]=241
            else:cancel[0]=True
            with self.subTest(mode=mode),self.assertRaises(ExecutionBlocked):g.check()
    def test_full35_catalog_still_exceeds_original16(self):self.assertEqual(10+2+3*2,18);self.assertGreater(18,p.BOUNDS['parent_catalog_GET'])


def bounded_main():
    import builtins,resource,signal,sys,sysconfig
    global METER
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(589,590))
    def deadline(*_):raise AssertionError('AUTHOR900SECOND_LIMIT')
    signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,900)
    scratch=tempfile.TemporaryDirectory(prefix='AUTHORED_CANARY_TESTS_');tmp=Path(scratch.name).resolve();tempfile.tempdir=str(tmp)
    import importlib.util
    helper_spec=importlib.util.spec_from_file_location('canary_author_dirfd',ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py')
    helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
    descriptor_guard=helper.DirectoryFdGuard(lambda path,flags:None)
    reads=[0];writes=[0];output=[0];METER={'reads':reads,'writes':writes,'read_limit':1073741824}
    stdlib=Path(sysconfig.get_path('stdlib')).resolve()
    def audit(event,args):
        if event=='os.fork' and not FORK_AUTHORIZED:raise AssertionError('UNAPPROVED_TEST_FORK')
        if event.startswith('socket.') or event in {'subprocess.Popen','os.forkpty','os.posix_spawn','os.system','ctypes.dlopen'}:raise AssertionError('NO_REAL_NETWORK_PROCESS_NATIVE')
        if event=='sqlite3.connect':
            if not Path(str(args[0]).split('?')[0].removeprefix('file:')).resolve().is_relative_to(tmp):raise AssertionError('NO_LIVE_SQLITE')
        if event=='open' and not isinstance(args[0],int):
            path=Path(os.path.realpath(descriptor_guard.event_path(args[0])));flags=args[2]
            if path.name.startswith('.env') or 'Application Support/SyntheticSocietyLab' in str(path):raise AssertionError('NO_KEY_OR_LIVE_OWNER')
            if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if not path.is_relative_to(tmp):raise AssertionError('ONLY_OWNED_TEMP_WRITES')
            else:
                reviewed_parent_files={ROOT/'docs/E02_RECOVERY_ADMISSION_V1_PROPOSAL.md',ROOT/'reports/INDEPENDENT_AUDIT_E02_RECOVERY_ADMISSION_V1_METHODS.json'}
                if not (path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts') or path==Path(__file__).resolve() or path.is_relative_to(ROOT/'configs') or path.is_relative_to(BASE) or path in reviewed_parent_files or path in {HISTORICAL_PRICES/f'{prefix}-{role}.json' for prefix in ('catalog','receipt') for role in ('A','B')} or path.is_relative_to(stdlib) or path.is_relative_to(tmp)):raise AssertionError('READ_OUTSIDE_CLOSED_TEST_SCOPE')
                try:reads[0]+=path.stat().st_size+1
                except FileNotFoundError:pass
                if reads[0]>1073741824:raise AssertionError('AUTHOR_LOGICAL_READ_LIMIT')
    sys.addaudithook(audit)
    os.open=descriptor_guard.open;os.close=descriptor_guard.close
    class Writer:
        def __init__(self,stream,counter,limit):self.stream=stream;self.counter=counter;self.limit=limit
        def __getattr__(self,name):return getattr(self.stream,name)
        def __enter__(self):self.stream.__enter__();return self
        def __exit__(self,*a):return self.stream.__exit__(*a)
        def write(self,data):
            self.counter[0]+=len(data.encode() if isinstance(data,str) else data)
            if self.counter[0]>self.limit:raise AssertionError('AUTHOR_WRITE_OR_OUTPUT_LIMIT')
            return self.stream.write(data)
        def writelines(self,items):
            for item in items:self.write(item)
    for module,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
        original=getattr(module,name)
        def opened(*args,_original=original,**kwargs):
            stream=_original(*args,**kwargs);mode=kwargs.get('mode',args[1] if len(args)>1 else 'r')
            return Writer(stream,writes,268435456) if any(v in mode for v in 'wax+') else stream
        setattr(module,name,opened)
    sys.stdout=Writer(sys.stdout,output,524288);sys.stderr=Writer(sys.stderr,output,524288)
    try:
        program=unittest.main(verbosity=2,exit=False)
        print(json.dumps({'kind':'CANARY_AUTHOR_OFFLINE_V1','python':sys.version.split()[0],'tests_run':program.result.testsRun,'successful':program.result.wasSuccessful(),'read_reservation_bytes':reads[0],'write_reservation_bytes':writes[0],'console_bytes':output[0],'real_API_requests':0,'live_owner_actions':0,'credentials_read':0}))
        return 0 if program.result.wasSuccessful() else 1
    finally:scratch.cleanup()


if __name__=='__main__':raise SystemExit(bounded_main())
