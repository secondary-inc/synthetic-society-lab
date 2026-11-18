"""Pure slot46 identity and original-error preservation. No closed owner inputs."""
import io,json,os,sys,tempfile,time
from pathlib import Path
import resource
import signal
import unittest
from unittest.mock import patch
from civiclab.common import canonical_hash
from civiclab.e02 import wrapper_crossmodel_slot46_v2 as p
from civiclab.e02 import wrapper_crossmodel_slot46_v2_client as client


class Finalization(unittest.TestCase):
    def flow(self,error,*,owned=True,close_fails=True,marker_fails=False):
        trace=[];receipt='a'*32
        class Journal:
            def write(self,name,value):
                trace.append(name)
                if marker_fails:raise OSError('authored marker failure')
            def close(self):
                trace.append('close')
                if close_fails:raise OSError('authored close failure')
        journal=Journal()
        class Owner:
            def open_canary(self,*a):pass
            def intent(self,*a):pass
            def register_proofs(self,*a):pass
            def grant(self):return {'receipt':receipt,'request':{'execution_order':46,'pair_seed':p.SEED,'payload':{}},'context':{'payload_hash':canonical_hash({})}}
            def transition(self,*a,**kw):trace.append('transition')
            def canary_snapshot(self):
                trace.append('readback');return {'branch':{'closed':True},'row':{'status':'UNCERTAIN'}}
            def close_canary(self,*a):trace.append('fallback')
        class Phase:
            def __init__(self,*a):pass
            def gate(self,*a,**kw):pass
        class Capability:
            def __init__(self,*a):pass
            def post(self):raise error
        class Gate:
            def check(self):pass
        packet={'run_id':'PURE_SLOT46','parent_key':'b'*64,'price_release':{k:{'terms':{'model':k},'interpretation':{}} for k in ('A','B')}}
        with patch.object(client,'validate_release'),patch.object(client,'fresh_proof',return_value={}),patch.object(client,'_Phase',Phase),patch.object(client,'_Capability',Capability),patch.object(client,'_Journal',return_value=journal):
            with self.assertRaises(BaseException) as seen:
                client.execute(packet,expected_packet_hash='c'*64,release={},expected_release_hash='d'*64,owner=Owner(),credential=object(),transport=object(),catalog_fetch=lambda _: (b'{}',{}),journal=None if owned else journal,gate=Gate())
        self.assertIs(seen.exception,error)
        self.assertEqual(trace.count('close'),int(owned))
        self.assertLess(trace.index('transition'),trace.index('readback'))
        self.assertNotIn('fallback',trace)
        if not marker_fails:self.assertLess(trace.index('failure-initial-v1.json'),trace.index('transition'))
        return trace
    def test_owned_close_does_not_replace_original_error(self):self.flow(RuntimeError())
    def test_owned_close_does_not_replace_keyboard_cancel(self):self.flow(KeyboardInterrupt())
    def test_owned_close_does_not_replace_system_exit(self):self.flow(SystemExit(1))
    def test_marker_and_close_failure_preserve_original(self):self.flow(RuntimeError(),marker_fails=True)
    def test_normal_owned_close_once(self):self.flow(RuntimeError(),close_fails=False)
    def test_borrowed_journal_not_closed(self):self.flow(RuntimeError(),owned=False)
    def test_success_close_failure_propagates_same_close_error(self):
        original=OSError();trace=[]
        class Journal:
            def close(self):trace.append('close');raise original
            def write(self,*a):trace.append('marker')
        with self.assertRaises(OSError) as seen:client.finalize_owned_journal(Journal(),failed=False)
        self.assertIs(seen.exception,original);self.assertEqual(trace,['close','marker'])
    def test_success_close_marker_failure_still_close_error(self):
        original=OSError()
        class Journal:
            def close(self):raise original
            def write(self,*a):raise RuntimeError()
        with self.assertRaises(OSError) as seen:client.finalize_owned_journal(Journal(),failed=False)
        self.assertIs(seen.exception,original)


class Identity(unittest.TestCase):
    def test_identity_is_new_and_stable(self):
        from civiclab.e02.wrapper_crossmodel_canary_v1 import identity
        self.assertEqual(p.identity('a'*32),p.identity('a'*32));self.assertNotEqual(p.identity('a'*32),identity('a'*32))
    def test_envelope_refuses_consumed_slot45(self):
        row={'execution_order':45,'phase':'post','status':'FAILED_UNCERTAIN','answer':None,'payload_sha256':'b'*64,'receipt':'c'*32}
        with self.assertRaises(client.ExecutionBlocked):p.envelope('a'*64,[row],'STOPPED','MOCK')
    def test_empty_mock_keeps_both_failed_slots_and_incomplete_parent(self):
        result=p.envelope('a'*64,[],'STOPPED','MOCK')
        self.assertEqual(result['original_slot45'],'FAILED_UNCERTAIN');self.assertEqual(result['original_full80_analysis'],'NOT_RUN_INCOMPLETE')
    def test_limits_unchanged_except_new_cpu_scope(self):
        from civiclab.e02.wrapper_crossmodel_canary_v1 import BOUNDS
        self.assertEqual({k:v for k,v in p.BOUNDS.items() if k not in ('CPU_seconds','CPU_soft_seconds')},{k:v for k,v in BOUNDS.items() if k!='CPU_seconds'})
        self.assertEqual((p.BOUNDS['CPU_soft_seconds'],p.BOUNDS['CPU_seconds']),(120,125))


if __name__=='__main__':
    import builtins,hashlib,sysconfig
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(29,30))
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(RuntimeError('PURE30SECONDS')));signal.alarm(30)
    root=Path(__file__).resolve().parents[1];scratch=Path(tempfile.gettempdir()).resolve();stdlib=Path(sysconfig.get_path('stdlib')).resolve()
    guardpath=root/'scripts/e01_authored_dirfd_guard_v2_20261112.py';ns={'__name__':'pure_dirfd','__file__':str(guardpath)};exec(compile(guardpath.read_bytes(),str(guardpath),'exec'),ns)
    descriptor=ns['DirectoryFdGuard'](lambda path,flags:None)
    counters={'reads':0,'writes':0,'console':0};limits={'reads':268435456,'writes':1048576,'console':65536}
    seen=set()
    for mod in list(sys.modules.values()):
        for value in (getattr(mod,'__file__',None),getattr(mod,'__cached__',None)):
            if value and Path(value).is_file():seen.add(Path(value).resolve())
    counters['reads']=sum(path.stat().st_size for path in seen)
    def charge(k,n):
        counters[k]+=n
        if counters[k]>limits[k]:raise AssertionError('PURE_RESOURCE_BOUND')
    def no_external(event,args):
        if event.startswith('socket.') or event in ('subprocess.Popen','os.fork','os.system','sqlite3.connect','os.exec','ctypes.dlopen'):raise AssertionError('PURE_NO_EXTERNAL')
        if event=='open' and not isinstance(args[0],int):
            path=descriptor.event_path(args[0]);flags=args[2]
            if path.name.startswith('.env') or 'SyntheticSocietyLab' in str(path) or path.is_relative_to(root/'data/processed'):raise AssertionError('PURE_NO_CLOSED_OR_CURRENT_STATE')
            write=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if write and not path.is_relative_to(scratch):raise AssertionError('PURE_OWNED_TEMP_ONLY')
            if not write:
                if not(path.is_relative_to(scratch) or path.is_relative_to(root/'src') or path==Path(__file__).resolve() or path.is_relative_to(stdlib)):raise AssertionError('PURE_READ_SCOPE')
                if path.is_file():charge('reads',path.stat().st_size)
    sys.addaudithook(no_external);os.open=descriptor.open;os.close=descriptor.close
    class Output:
        def __init__(self,stream,k):self.stream=stream;self.k=k
        def __getattr__(self,n):return getattr(self.stream,n)
        def __enter__(self):return self
        def __exit__(self,*a):return self.stream.__exit__(*a)
        def write(self,value):charge(self.k,len(value.encode() if isinstance(value,str) else value));return self.stream.write(value)
        def writelines(self,values):
            for value in values:self.write(value)
    for obj,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
        original=getattr(obj,name)
        def opened(*a,_original=original,**k):
            stream=_original(*a,**k);mode=k.get('mode',a[1] if len(a)>1 else 'r')
            return Output(stream,'writes') if any(v in mode for v in 'wax+') else stream
        setattr(obj,name,opened)
    sys.stdout=Output(sys.stdout,'console');sys.stderr=Output(sys.stderr,'console')
    program=unittest.main(verbosity=2,exit=False)
    print(json.dumps({'kind':'PURE_ERROR_REMEDY_CONTROLS','runtime':sys.version.split()[0],'tests':program.result.testsRun,'successful':program.result.wasSuccessful(),'resource_counters_before_summary':counters,'closed_inputs':0,'normal_owner_calls':0,'network_calls':0},sort_keys=True))
    raise SystemExit(0 if program.result.wasSuccessful() else 1)
