"""L01/L02 MOCK qualifications; no normal owner constructor or live execution.

Reuse exact frozen copied-history fixture for interruption controls only. L03
full inherited integration is deliberately absent. Direct main enforces bounds.
"""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BORROWED=ROOT/'tests/test_wrapper_crossmodel_canary_v1.py'
old=types.ModuleType('frozen_copied_fixture');old.__file__=str(BORROWED)
exec(compile(BORROWED.read_bytes(),str(BORROWED),'exec'),old.__dict__)
p=old.p;m=old.m;c=old.c;frozen=old.frozen
canonical_bytes=old.canonical_bytes;canonical_hash=old.canonical_hash
ExecutionBlocked=old.ExecutionBlocked
METER=None;CHILD_AUTHORIZED=False;CHILD_RESULTS=[]


def authored_packet():
    releases=deepcopy(old.CopiedHistoryCases.old_packet['price_release'])
    start=datetime(2026,11,17,11,18,tzinfo=timezone.utc);end=start+timedelta(seconds=600)
    for release in releases.values():
        for key in ('terms','interpretation'):
            release[key].update(valid_from_utc=start.isoformat(),valid_until_utc=end.isoformat())
        release['terms']['interpretation_hash']=canonical_hash(release['interpretation'])
    q={'kind':'WRAPPER_CANARY_PACKET_V1','owner_id':'a'*32,'parent_key':p.identity('a'*32),'expected_head':{'MOCK_HEAD':True},'parent_binding':{'MOCK_PARENT':True},'run_id':'AUTHORED_L01_CALLER','valid_from_utc':start.isoformat(),'valid_until_utc':end.isoformat(),'bounds':deepcopy(p.BOUNDS),'code_hash':canonical_hash(p.contract()),'price_release':releases}
    q['authority']={'kind':p.AUTHORITY,'scope_hash':canonical_hash(q)}
    q['review']={'kind':'INDEPENDENT_WRAPPER_CANARY_REVIEW_V1','reviewer_role':'independent_auditor','review_id':'a'*32,'inputs_hash':canonical_hash(q)}
    release={'kind':'LEAD_WRAPPER_CANARY_RELEASE_V1','packet_sha256':canonical_hash(q),'code_hash':canonical_hash(p.contract()),'review_sha256':canonical_hash(q['review']),'maximum_POSTs':1,'scope':'ORIGINAL45_ONLY_NOT_FULL80'}
    return q,release


class LauncherCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):old.CopiedHistoryCases.setUpClass()
    def test_exact_main_in_one_disposable_mock_child(self):
        global CHILD_AUTHORIZED
        with tempfile.TemporaryDirectory() as directory:
            scratch=Path(directory).resolve();q,release=authored_packet()
            (scratch/'mock-packet.input.json').write_bytes(canonical_bytes(q));(scratch/'mock-release.input.json').write_bytes(canonical_bytes(release))
            source=ROOT/'scripts/continue_e02_wrapper_crossmodel_canary_v1_20261117.py'
            cmd=[sys.executable,'-I','-B','-S',str(ROOT/'scripts/qualify_e02_canary_launcher_mock_v1_20261117.py'),'--scratch',str(scratch),'--launcher-sha256',hashlib.sha256(source.read_bytes()).hexdigest()]
            if METER is not None:
                METER['reads'][0]+=128*1024*1024;METER['writes'][0]+=8*1024*1024
            CHILD_AUTHORIZED=True
            try:process=subprocess.Popen(cmd,cwd=ROOT,env={'PATH':'/usr/bin:/bin'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            finally:CHILD_AUTHORIZED=False
            started=time.monotonic()
            try:raw,_=process.communicate(timeout=180)
            except subprocess.TimeoutExpired:process.kill();raw,_=process.communicate()
            self.assertLessEqual(len(raw),65536)
            record=json.loads(raw);CHILD_RESULTS.append({'exit':process.returncode,'wall_seconds':time.monotonic()-started,'console_bytes':len(raw),'console_sha256':hashlib.sha256(raw).hexdigest(),'result':record})
            self.assertEqual(process.returncode,0,record)
            self.assertTrue(record['passed']);self.assertTrue(all(x['pass'] for x in record['checks']))
            self.assertEqual(record['real_resource_observation']['CPU'],[59,60]);self.assertEqual(record['real_resource_observation']['core'],[0,0])
            self.assertEqual(record['API_calls'],0);self.assertEqual(record['real_key_reads'],0)


class BoundaryCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):old.CopiedHistoryCases.setUpClass()
    def setUp(self):
        self.f=old.CopiedHistoryCases('test_success_one_slot_preserves_all_history_and_no_reopen');self.f.setUp()
    def tearDown(self):self.f.tearDown()
    def run_client(self,transport=None,catalog=None,gate=None):
        f=self.f;self.transport=transport or old.Transport();self.catalog=catalog or f.catalog
        return c.execute(f.q,expected_packet_hash=canonical_hash(f.q),release=f.release,expected_release_hash=canonical_hash(f.release),owner=f.owner,credential=old._Credential('AUTHORED_MOCK_NOT_REAL_KEY_1234'),transport=self.transport,catalog_fetch=self.catalog,gate=gate or c.OperationGate(f.q,now=f.now),sleep=lambda _:None)
    def stopped(self,posts,gets,catalogs=2,new_row=True):
        state=self.f.preserved();branch=state[m.STATE]
        self.assertEqual((self.transport.posts,self.transport.gets,len(self.catalog.calls)),(posts,gets,catalogs))
        self.assertTrue(branch['closed']);self.assertEqual(len(state['rows']),194+int(new_row))
        self.assertEqual(branch['counts']['POST'],posts)
        with self.assertRaises(ExecutionBlocked):self.f.owner.grant()
        with self.assertRaises(ExecutionBlocked):self.f.owner.open_canary(self.f.q,canonical_hash(self.f.q))
        return state,state['rows'].get(branch['receipt'])
    def test_prePOST_cancellation_keeps_full_hold_and_no_dispatch(self):
        f=self.f;cancel=[False];gate=c.OperationGate(f.q,now=f.now,cancelled=lambda:cancel[0]);write=frozen._Journal.write
        def interrupted(journal,name,value):
            result=write(journal,name,value)
            if name.endswith('-request.json'):cancel[0]=True
            return result
        with patch.object(frozen._Journal,'write',interrupted),self.assertRaises(ExecutionBlocked):self.run_client(gate=gate)
        state,row=self.stopped(0,0);self.assertEqual(row['status'],'UNCERTAIN');self.assertEqual(row['charged'],row['reserved']);self.assertEqual(state['unfinished'],6)
    def test_postPOST_UTC_jump_stops_before_statistics(self):
        f=self.f;jump=[0];gate=c.OperationGate(f.q,now=lambda:f.now()+timedelta(seconds=jump[0]))
        transport=old.Transport();post=transport.post_bytes
        def interrupted(raw):
            response=post(raw);jump[0]=10;return response
        transport.post_bytes=interrupted
        with self.assertRaises(ExecutionBlocked):self.run_client(transport=transport,gate=gate)
        state,row=self.stopped(1,0);self.assertEqual(row['charged'],row['reserved']);self.assertIsNone(row['billing']);self.assertEqual(state['unfinished'],6)
    def test_prestats_intent_write_failure_keeps_spent_POST(self):
        write=frozen._Journal.write
        def interrupted(journal,name,value):
            if name.endswith('-statistics-intent-1.json'):raise OSError('AUTHORED_PRESTATS_WRITE')
            return write(journal,name,value)
        with patch.object(frozen._Journal,'write',interrupted),self.assertRaises(OSError):self.run_client()
        state,row=self.stopped(1,0);self.assertEqual(state[m.STATE]['counts']['statistics_GET'],1);self.assertEqual(row['charged'],row['reserved']);self.assertEqual(row['observed_cost'],10)
    def test_postinvoice_checkpoint_failure_keeps_verified_cost(self):
        write=frozen._Journal.write
        def interrupted(journal,name,value):
            if name.endswith('-checkpoint.json'):raise OSError('AUTHORED_POSTINVOICE_CHECKPOINT')
            return write(journal,name,value)
        with patch.object(frozen._Journal,'write',interrupted),self.assertRaises(OSError):self.run_client()
        state,row=self.stopped(1,1);self.assertEqual(row['status'],'UNCERTAIN');self.assertEqual(row['observed_cost'],10);self.assertIsNotNone(row['billing']);self.assertEqual(row['charged'],row['reserved']);self.assertIsNone(state[m.STATE]['witness'])
    def test_response_fsync_failure_retains_ambiguous_dispatch(self):
        write=frozen._Journal.write;real_sync=os.fsync;response_write=[False]
        def interrupted(journal,name,value):
            response_write[0]=name.endswith('-response.json')
            try:return write(journal,name,value)
            finally:response_write[0]=False
        def sync(fd):
            if response_write[0]:raise OSError('AUTHORED_RESPONSE_FSYNC')
            return real_sync(fd)
        with patch.object(frozen._Journal,'write',interrupted),patch.object(os,'fsync',sync),self.assertRaises(OSError):self.run_client()
        _,row=self.stopped(1,0);self.assertEqual(row['charged'],row['reserved']);self.assertEqual(row['observed_cost'],10)
    def test_insufficient_remaining_phase_lease_before_reserve(self):
        f=self.f;end=(f.base+timedelta(seconds=123)).isoformat();f.q['valid_until_utc']=end
        for release in f.q['price_release'].values():
            release['terms']['valid_until_utc']=end;release['interpretation']['valid_until_utc']=end
            release['terms']['interpretation_hash']=canonical_hash(release['interpretation'])
        f.bind();register=f.owner.register_proofs
        def delayed(proofs):
            result=register(proofs);time.sleep(3.2);return result
        with patch.object(f.owner,'register_proofs',side_effect=delayed),self.assertRaises(ExecutionBlocked):self.run_client()
        _,row=self.stopped(0,0,new_row=False);self.assertIsNone(row)
    def test_oversize_catalog_stops_before_proof_or_reserve(self):
        class Catalog:
            def __init__(self):self.calls=[]
            def __call__(self,model):self.calls.append('A');return b'x'*2000001,{'MOCK':True}
        with self.assertRaises(ExecutionBlocked):self.run_client(catalog=Catalog())
        _,row=self.stopped(0,0,catalogs=1,new_row=False);self.assertIsNone(row)
    def test_stable_journal_boundaries_and_proof_join_refusals(self):
        f=self.f;f.owner.open_canary(f.q,canonical_hash(f.q));journal=frozen._Journal(f.owner,f.q['run_id'],f.q);proofs={}
        try:
            for role in ('A','B'):
                f.owner.intent('CATALOG_'+role,1);raw,metadata=f.catalog(f.q['price_release'][role]['terms']['model']);release=f.q['price_release'][role]
                proof=m.fresh_proof(raw,metadata,release['interpretation'],release['terms'],now=f.now());proofs[role]=proof
                journal.write('catalog-'+role+'.json',{'body_utf8':raw.decode(),'metadata':metadata,'proof':proof})
            target=journal.path/'catalog-B.json';original=target.read_bytes()
            target.unlink()
            with self.assertRaises(ExecutionBlocked):f.owner.register_proofs(proofs)
            target.write_bytes(b' '*2000001)
            with self.assertRaises(ExecutionBlocked):f.owner.register_proofs(proofs)
            target.write_bytes(b' '+original)
            with self.assertRaises(ExecutionBlocked):f.owner.register_proofs(proofs)
            target.write_bytes(original);wrong=deepcopy(proofs);wrong['B']['body_sha256']='0'*64
            with self.assertRaises(ExecutionBlocked):f.owner.register_proofs(wrong)
            size=frozen.ARTIFACT_BYTES;value={'MOCK':'x'*(size-len(canonical_bytes({'MOCK':''})))}
            path=journal.write('authored-max.json',value);self.assertEqual(path.stat().st_size,size)
            with self.assertRaises(ExecutionBlocked):journal.write('authored-oversize.json',{'MOCK':'x'*size})
            f.owner.register_proofs(proofs);state=f.preserved();self.assertEqual(len(state['rows']),194);self.assertIsNone(state[m.STATE]['receipt'])
            f.owner.close_canary('FAILED')
        finally:journal.close()


def bounded_main():
    import builtins,sysconfig
    global METER
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(539,540))
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(AssertionError('AUTHOR900SECONDS')));signal.alarm(900)
    temp=tempfile.TemporaryDirectory(prefix='AUTHORED_L01_L02_');tmp=Path(temp.name).resolve();tempfile.tempdir=str(tmp)
    guardpath=ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py';ns={'__name__':'author_dirfd','__file__':str(guardpath)};exec(compile(guardpath.read_bytes(),str(guardpath),'exec'),ns)
    descriptor=ns['DirectoryFdGuard'](lambda path,flags:None)
    class Counter(list):
        def __init__(self,limit):super().__init__([0]);self.limit=limit
        def __setitem__(self,i,value):
            if value>self.limit:raise AssertionError('AUTHOR_BYTE_LIMIT')
            super().__setitem__(i,value)
    reads=Counter(1073741824);writes=Counter(268435456);console=Counter(524288)
    METER={'reads':reads,'writes':writes,'read_limit':1073741824};old.METER=METER
    closure=json.loads((ROOT/'reports/evidence_e02_canary_closed_replay_code_v1_20261117/EXACT_CLOSURE_WITH_HELPER.json').read_bytes())
    allowed={ROOT/x['path'] for x in closure['project_pins']}|{BORROWED,Path(__file__).resolve(),guardpath,ROOT/'scripts/qualify_e02_canary_launcher_mock_v1_20261117.py'}
    allowed|={old.BASE/n for n in ('post-run-owner-export.local.json','packet.local.json','retained-journal/catalog-4-A.json','retained-journal/catalog-4-B.json')}
    allowed|={old.HISTORICAL_PRICES/f'{prefix}-{role}.json' for prefix in ('catalog','receipt') for role in ('A','B')}
    stdlib=Path(sysconfig.get_path('stdlib')).resolve()
    loaded=set()
    for mod in list(sys.modules.values()):
        for raw in (getattr(mod,'__file__',None),getattr(mod,'__cached__',None)):
            if raw and Path(raw).is_file():loaded.add(Path(raw).resolve())
    reads[0]+=sum(p.stat().st_size for p in loaded)+BORROWED.stat().st_size
    def audit(event,args):
        if event=='subprocess.Popen':
            command=args[1]
            if not CHILD_AUTHORIZED or str(ROOT/'scripts/qualify_e02_canary_launcher_mock_v1_20261117.py') not in command:raise AssertionError('ONLY_EXACT_L01_CHILD')
        if event.startswith('socket.') or event in {'os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:raise AssertionError('NO_NETWORK_OR_EXTRA_PROCESS')
        if event=='sqlite3.connect':
            path=Path(str(args[0]).removeprefix('file:').split('?')[0]).resolve()
            if not path.is_relative_to(tmp):raise AssertionError('ONLY_AUTHORED_COPY_SQLITE')
        if event=='open' and not isinstance(args[0],int):
            path=descriptor.event_path(args[0]);flags=args[2]
            if path.name.startswith('.env') or 'SyntheticSocietyLab' in str(path):raise AssertionError('NO_REAL_KEY_OR_OWNER')
            if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if not path.is_relative_to(tmp):raise AssertionError('ONLY_AUTHORED_TEMP_WRITES')
            else:
                if not (path in allowed or path.is_relative_to(tmp) or path.is_relative_to(stdlib)):raise AssertionError('AUTHOR_EXACT_READ_SCOPE')
                if path.is_file():reads[0]+=path.stat().st_size
    sys.addaudithook(audit);os.open=descriptor.open;os.close=descriptor.close
    class Writer:
        def __init__(self,stream,counter):self.stream=stream;self.counter=counter
        def __getattr__(self,name):return getattr(self.stream,name)
        def __enter__(self):return self
        def __exit__(self,*a):return self.stream.__exit__(*a)
        def write(self,data):self.counter[0]+=len(data.encode() if isinstance(data,str) else data);return self.stream.write(data)
        def writelines(self,values):
            for value in values:self.write(value)
    for obj,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
        original=getattr(obj,name)
        def opened(*a,_original=original,**k):
            stream=_original(*a,**k);mode=k.get('mode',a[1] if len(a)>1 else 'r')
            return Writer(stream,writes) if any(x in mode for x in 'wax+') else stream
        setattr(obj,name,opened)
    sys.stdout=Writer(sys.stdout,console);sys.stderr=Writer(sys.stderr,console)
    try:
        program=unittest.main(verbosity=2,exit=False)
        print(json.dumps({'kind':'AUTHOR_L01_L02_MOCK_BOUNDARIES','python':sys.version.split()[0],'tests_run':program.result.testsRun,'successful':program.result.wasSuccessful(),'charged_read_bytes':reads[0],'charged_write_bytes':writes[0],'console_bytes_before_summary':console[0],'L01_child_results':CHILD_RESULTS,'actual_API_calls':0,'real_key_reads':0,'live_owner_access':0,'L03':'NOT_RUN_PREPARATION_ONLY'},sort_keys=True))
        return 0 if program.result.wasSuccessful() else 1
    finally:temp.cleanup()


if __name__=='__main__':raise SystemExit(bounded_main())
