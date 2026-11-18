"""L03 authored full inherited MOCK integration and isolated tamper views.

No overridden verifier/state seed. No live namespace, key or model transport.
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
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/'scripts/qualify_e02_canary_inherited_mock_v1_20261117.py'
h=types.ModuleType('authored_inherited_fixture');h.__file__=str(HELPER)
exec(compile(HELPER.read_bytes(),str(HELPER),'exec'),h.__dict__)
OLD_SOURCE=ROOT/'tests/test_wrapper_crossmodel_canary_v1.py'
old=types.ModuleType('inert_transport_definitions');old.__file__=str(OLD_SOURCE)
exec(compile(OLD_SOURCE.read_bytes(),str(OLD_SOURCE),'exec'),old.__dict__)
from civiclab import production_owner_v4 as production
from civiclab.e02 import wrapper_crossmodel_canary_v1_client as client
from civiclab.e02 import wrapper_crossmodel_canary_v1_owner as owner_module
from civiclab.e02 import exploratory_live_client_v1 as frozen
from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked

METER=None;OBS=[]


class InheritedIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not h.EXPORT.is_file() or not h.REGISTRATION.is_file():
            raise unittest.SkipTest('Exact closed history/registration unavailable; L03 NOT_RUN')
    def test_normal_inherited_positive_and_isolated_adverse_views(self):
        export=json.loads(h.read_pinned(h.EXPORT,h.EXPORT_PIN));registration=h.read_pinned(h.REGISTRATION,h.REGISTRATION_PIN)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();baseline=root/'positive';owner_path=h.reconstruct(baseline,export,registration,METER)
            start=time.monotonic();base=datetime(2026,11,17,11,18,tzinfo=timezone.utc)
            now=lambda:base+timedelta(seconds=time.monotonic()-start)
            q,release=h.packet(export,now());transport=old.Transport()
            records={role:json.loads((old.BASE/f'retained-journal/catalog-4-{role}.json').read_bytes()) for role in ('A','B')}
            catalog=old.Catalog(records,now);phase_seen=[];protected=h.protected_methods()
            def skip_visibility_wait(phase):phase_seen.append(phase);return None
            def verify(owner):
                with owner._lock(),owner._connect() as db:return owner._verify(db)
            with patch.object(production,'production_owner_directory',return_value=owner_path),patch.object(production,'_utc_now',side_effect=now),patch.object(frozen,'new_operation_time',side_effect=now),patch.object(frozen._Phase,'wait_for_statistics',skip_visibility_wait):
                cpu=resource.getrusage(resource.RUSAGE_SELF);operation_start=time.monotonic()
                owner=h.CanaryOwnerV1()
                result=client.execute(q,expected_packet_hash=canonical_hash(q),release=release,expected_release_hash=canonical_hash(release),owner=owner,credential=old._Credential('AUTHORED_MOCK_NOT_REAL_KEY_1234'),transport=transport,catalog_fetch=catalog,gate=client.OperationGate(q,now=now),sleep=lambda _:None,provenance='MOCK')
                operation_wall=time.monotonic()-operation_start;after=resource.getrusage(resource.RUSAGE_SELF)
                operation_cpu=after.ru_utime+after.ru_stime-cpu.ru_utime-cpu.ru_stime
                phase_wall=time.monotonic()-phase_seen[0].started
                self.assertLessEqual(operation_cpu,60);self.assertLess(operation_wall,240);self.assertLess(phase_wall,120)
                state,head=verify(owner);branch=state[owner_module.STATE];receipt=branch['receipt'];row=state['rows'][receipt]
                checks={'result_MOCK':result['response_provenance']=='MOCK','one_committed_slot':result['status']=='COMMITTED_ONE_SLOT' and len(result['records'])==1 and result['records'][0]['execution_order']==45,'parent_stopped':state['wrapper_crossmodel']['stopped'] is True,'full80_NOT_RUN':result['original_full80_analysis']=='NOT_RUN_INCOMPLETE','old_rows':canonical_hash({k:state['rows'][k] for k in export['rows']})==canonical_hash(export['rows']),'old_history':canonical_hash(state['_prefix_events'][:1180])==canonical_hash(export['history']),'old_claims':set(export['statistics_claims']).issubset(state['statistics_claims']),'five_holds':sorted(r['charged'] for r in state['rows'].values() if r['status']!='PHASE_COMMITTED')==[340,340,775,788,1008],'unfinished5':state['unfinished']==5,'one_new_row':len(state['rows'])==195,'conservative16159':state['consumed']['total']==16159,'new_committed':row['status']=='PHASE_COMMITTED' and row['charged']==10,'exact_counts':(transport.posts,transport.gets,catalog.calls)==(1,1,['A','B']),'new_claim':receipt in state['statistics_claims'] and len(state['statistics_claims'])==193,'all_inherited_methods_intact':h.assert_methods_same(protected)}
                for key in ('study','continuation','alignment_followup','issue_cue_crossmodel','issue_cue_crossmodel_recovery','wrapper_visibility','wrapper_crossmodel'):checks['old_'+key]=canonical_hash(state[key])==canonical_hash(export[key])
                compiled,baseline_hash=owner_module.p.compile_slot(export['wrapper_crossmodel'],q['price_release']['B']['terms'])
                checks.update({'original_seed':row['context']['sampling']['seed']==2315288556,
                               'original_baseline13':baseline_hash==owner_module.ANCHOR['baseline13'],
                               'original_payload':row['context']['payload_hash']==compiled['payload_sha256'],
                               'one_new_witness':branch['witness']['execution_order']==45 and branch['witness']['phase']=='post'})
                self.assertTrue(all(checks.values()))
                OBS.append({'case':'NORMAL_INHERITED_MOCK_POSITIVE','pass':True,'checks':checks,'operation_CPU_seconds':operation_cpu,'operation_wall_seconds':operation_wall,'phase_wall_seconds':phase_wall,'fixed10second_billing_visibility_wait':'MOCK_SKIPPED','clock':'MOCK_UTC_TRACKS_REAL_MONOTONIC','transport':'INERT','API_calls':0})
            self.assertTrue(h.assert_methods_same(protected))
            self.assertFalse(any(Path(str(owner_path/'owner-v4.local.sqlite')+x).exists() for x in ('-wal','-shm','-journal')))
            # Every negative view is a private physical clone, never a seeded state.
            for kind in ('DUPLICATE_SLOT','DUPLICATE_STATISTICS_CLAIM','DIRECT_COMMIT','CHECKPOINT_JOIN','RESPONSE_IDENTITY','MATERIALIZED_ROW','PARENT_ANCHOR'):
                with self.subTest(case=kind):
                    copy=root/kind;target=h.clone_completed(baseline,copy,METER);database=target/'owner-v4.local.sqlite'
                    if kind=='CHECKPOINT_JOIN':
                        path=target/'limited-pilot-v1'/q['run_id']/(receipt+'-checkpoint.json');value=json.loads(path.read_bytes());value['request_hash']='0'*64;path.write_bytes(canonical_bytes(value))
                    if kind=='RESPONSE_IDENTITY':
                        path=target/'limited-pilot-v1'/q['run_id']/(receipt+'-response.json');value=json.loads(path.read_bytes());value['id']='gen-AUTHORED_TAMPER';path.write_bytes(canonical_bytes(value))
                    if kind=='MATERIALIZED_ROW':
                        METER['writes'][0]+=48*1024*1024
                        with sqlite3.connect(database) as db:
                            value=deepcopy(row);value['charged']+=1;db.execute('UPDATE charges SET data=? WHERE id=?',(canonical_bytes(value).decode(),receipt))
                        db.close()
                    if kind=='PARENT_ANCHOR':
                        path=target/'owner-v4-head.local.json';value=json.loads(path.read_bytes());value['head_hash']='0'*64;path.write_bytes(canonical_bytes(value))
                    # Route only the namespace. All constructor/verifier methods stay real.
                    with patch.object(production,'production_owner_directory',return_value=target),patch.object(production,'_utc_now',side_effect=now),patch.object(frozen,'new_operation_time',side_effect=now):
                        candidate=h.CanaryOwnerV1()
                        with self.assertRaises((ExecutionBlocked,ValueError)):
                            if kind=='DUPLICATE_SLOT':candidate.grant()
                            elif kind=='DUPLICATE_STATISTICS_CLAIM':candidate.claim_statistics_lookup(receipt)
                            elif kind=='DIRECT_COMMIT':candidate.transition(receipt,'PHASE_COMMITTED',checkpoint_hash=row['checkpoint_hash'])
                            else:verify(candidate)
                    self.assertEqual((transport.posts,transport.gets,len(catalog.calls)),(1,1,2))
                    self.assertTrue(h.assert_methods_same(protected))
                    OBS.append({'case':kind,'pass':True,'external_operations_after_refusal':0,'inherited_methods_intact':True})
            # Untampered baseline remains byte-identical after all destructive views.
            with patch.object(production,'production_owner_directory',return_value=owner_path):
                baseline_owner=h.CanaryOwnerV1();final,final_head=verify(baseline_owner)
            self.assertEqual(canonical_hash(final['rows']),canonical_hash(state['rows']));self.assertEqual(canonical_hash(final_head),canonical_hash(head))
            OBS.append({'case':'UNTOUCHED_BASELINE_AFTER_VIEWS','pass':True})


class AvailabilityGate(unittest.TestCase):
    def test_missing_private_inputs_are_NOT_RUN(self):
        with tempfile.TemporaryDirectory() as directory:
            absent=Path(directory)/'absent.json'
            with patch.object(h,'EXPORT',absent),patch.object(h,'REGISTRATION',absent):
                with self.assertRaises(unittest.SkipTest):InheritedIntegration.setUpClass()


def bounded_main():
    import builtins,sysconfig
    global METER
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(599,600))
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(AssertionError('AUTHOR900SECONDS')));signal.alarm(900)
    temp=tempfile.TemporaryDirectory(prefix='AUTHORED_L03_INHERITED_');tmp=Path(temp.name).resolve();tempfile.tempdir=str(tmp)
    guardpath=ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py';namespace={'__name__':'inherited_author_dirfd','__file__':str(guardpath)};exec(compile(guardpath.read_bytes(),str(guardpath),'exec'),namespace)
    descriptor=namespace['DirectoryFdGuard'](lambda path,flags:None)
    class Counter(list):
        def __init__(self,limit):super().__init__([0]);self.limit=limit
        def __setitem__(self,i,n):
            if n>self.limit:raise AssertionError('AUTHOR_BOUNDED_BYTES')
            super().__setitem__(i,n)
    reads=Counter(4294967296);writes=Counter(268435456);console=Counter(524288);METER={'reads':reads,'writes':writes,'read_limit':4294967296}
    closure=json.loads((ROOT/'reports/evidence_e02_canary_closed_replay_code_v1_20261117/EXACT_CLOSURE_WITH_HELPER.json').read_bytes())
    permitted={ROOT/x['path'] for x in closure['project_pins']}|{HELPER,OLD_SOURCE,Path(__file__).resolve(),guardpath,h.EXPORT,h.REGISTRATION}|{old.BASE/f'retained-journal/catalog-4-{role}.json' for role in ('A','B')}
    stdlib=Path(sysconfig.get_path('stdlib')).resolve();loaded=set()
    for mod in list(sys.modules.values()):
        for file in (getattr(mod,'__file__',None),getattr(mod,'__cached__',None)):
            if file and Path(file).is_file():loaded.add(Path(file).resolve())
    reads[0]+=sum(p.stat().st_size for p in loaded)+HELPER.stat().st_size+OLD_SOURCE.stat().st_size
    def audit(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:raise AssertionError('NO_NETWORK_PROCESS')
        if event=='sqlite3.connect':
            path=Path(str(args[0]).removeprefix('file:').split('?')[0]).resolve()
            if not path.is_relative_to(tmp):raise AssertionError('NO_CURRENT_OWNER_SQLITE')
            if path.is_file():reads[0]+=path.stat().st_size
        if event=='open' and not isinstance(args[0],int):
            path=descriptor.event_path(args[0]);flags=args[2]
            if path.name.startswith('.env') or 'SyntheticSocietyLab' in str(path):raise AssertionError('NO_KEY_OR_CURRENT_OWNER')
            if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if not path.is_relative_to(tmp):raise AssertionError('ONLY_AUTHORED_WRITES')
            else:
                if not(path in permitted or path.is_relative_to(tmp) or path.is_relative_to(stdlib)):raise AssertionError('EXACT_READ_SCOPE')
                if path.is_file():reads[0]+=path.stat().st_size
    sys.addaudithook(audit);os.open=descriptor.open;os.close=descriptor.close
    class Writer:
        def __init__(self,stream,counter):self.stream=stream;self.counter=counter
        def __getattr__(self,n):return getattr(self.stream,n)
        def __enter__(self):return self
        def __exit__(self,*a):return self.stream.__exit__(*a)
        def write(self,data):self.counter[0]+=len(data.encode() if isinstance(data,str) else data);return self.stream.write(data)
        def writelines(self,values):
            for v in values:self.write(v)
    for obj,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
        original=getattr(obj,name)
        def opened(*a,_original=original,**kw):
            stream=_original(*a,**kw);mode=kw.get('mode',a[1] if len(a)>1 else 'r')
            return Writer(stream,writes) if any(v in mode for v in 'wax+') else stream
        setattr(obj,name,opened)
    sys.stdout=Writer(sys.stdout,console);sys.stderr=Writer(sys.stderr,console)
    class ChargedCursor(sqlite3.Cursor):
        def measured(self,rows):
            reads[0]+=sum(len(v.encode()) if isinstance(v,str) else len(v) if isinstance(v,bytes) else 8 for row in rows for v in row)
            return rows
        def fetchall(self):return self.measured(super().fetchall())
        def fetchone(self):
            row=super().fetchone()
            if row is not None:self.measured([row])
            return row
    class ChargedConnection(sqlite3.Connection):
        def execute(self,sql,parameters=()):return self.cursor(factory=ChargedCursor).execute(sql,parameters)
        def executemany(self,sql,parameters):return self.cursor(factory=ChargedCursor).executemany(sql,parameters)
    actual_connect=sqlite3.connect
    def charged_connect(*a,**kw):kw['factory']=ChargedConnection;return actual_connect(*a,**kw)
    sqlite3.connect=charged_connect
    try:
        program=unittest.main(verbosity=2,exit=False)
        qualified=program.result.wasSuccessful() and len(OBS)==9 and all(row['pass'] for row in OBS)
        print(json.dumps({'kind':'AUTHOR_L03_NORMAL_INHERITED_MOCK','python':sys.version.split()[0],'tests_run':program.result.testsRun,'successful':qualified,'test_framework_successful':program.result.wasSuccessful(),'qualification_status':'PASS_MOCK' if qualified else 'NOT_QUALIFIED_OR_PRIVATE_INPUTS_NOT_RUN','observations':OBS,'charged_read_bytes':reads[0],'charged_write_bytes':writes[0],'console_bytes_before_summary':console[0],'current_owner_access':0,'real_key_reads':0,'API_calls':0,'source_scope':'NORMAL_CONSTRUCTOR_AND_INHERITED_REDUCERS_TEMP_ROUTING_ONLY','clock_and_billing_visibility':'EXPLICIT_MOCK_SEAMS','private_fixture_removed_before_summary':not any(tmp.iterdir())},sort_keys=True))
        return 0 if qualified else 1
    finally:
        sqlite3.connect=actual_connect
        temp.cleanup()


if __name__=='__main__':raise SystemExit(bounded_main())
