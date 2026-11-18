"""Narrow pure diagnostic/sequence tests; no closed state/owner/credential/API."""
import io,json,os,resource,signal,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from civiclab.common import canonical_bytes,canonical_hash
from civiclab.e02 import wrapper_canary_failure_diagnostic_v1 as diagnostic
from civiclab.e02 import wrapper_crossmodel_canary_diagnostic_v1_client as client
from civiclab.e02.exploratory_live_client_v1 import _Journal
from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure


class ErrorPrivacy(unittest.TestCase):
    def test_trusted_HTTP_status_and_no_payload(self):
        value=diagnostic.failure_record(_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',429),'POST')
        self.assertEqual(value['http_status'],429);self.assertEqual(value['error_kind'],'SAFE_TRANSPORT_FAILURE')
        self.assertEqual(value['dispatch_generation_billing'],'NOT_ATTESTED_BY_THIS_MARKER');self.assertFalse(value['retry_allowed']);self.assertLessEqual(len(canonical_bytes(value)),512)
    def test_unknown_error_never_reads_args_repr_or_metaclass_hash(self):
        class Meta(type):
            def __hash__(cls):raise AssertionError('must not hash unknown class')
            def __eq__(cls,other):raise AssertionError('must not compare unknown class')
        class Poison(RuntimeError,metaclass=Meta):
            @property
            def args(self):raise AssertionError('must not read args')
            def __str__(self):raise AssertionError('must not stringify')
            def __repr__(self):raise AssertionError('must not repr')
        value=diagnostic.failure_record(Poison(),'POST');self.assertEqual(value['error_kind'],'OTHER');self.assertIsNone(value['http_status'])
    def test_transport_instance_method_override_is_not_called(self):
        error=_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',503)
        error.diagnostic=lambda: (_ for _ in ()).throw(AssertionError('untrusted instance method'))
        self.assertEqual(diagnostic.failure_record(error,'POST')['http_status'],503)
    def test_malformed_transport_fields_not_iterated_or_disclosed(self):
        class Poison:
            def __iter__(self):raise AssertionError('no arbitrary iteration')
            def __str__(self):raise AssertionError('no arbitrary string')
        for fields in (Poison(),('HTTP_STATUS','HTTP_STATUS',True,False),('BAD','HTTP_STATUS',429,False)):
            error=_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',429);error._fields=fields
            value=diagnostic.failure_record(error,'POST');self.assertEqual(value['error_kind'],'INVALID_TRANSPORT_DIAGNOSTIC');self.assertIsNone(value['http_status'])
        del error._fields
        self.assertEqual(diagnostic.failure_record(error,'POST')['error_kind'],'INVALID_TRANSPORT_DIAGNOSTIC')
    def test_closed_stage_and_provenance(self):
        for stage,provenance in [('PRIVATE_ERROR_TEXT','MOCK'),('POST','NOT_A_PROVENANCE')]:
            with self.assertRaises(ValueError):diagnostic.failure_record(RuntimeError('DO_NOT_LOG'),stage,provenance)
    def test_real_journal_durable_marker_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            journal=_Journal(SimpleNamespace(directory=Path(directory).resolve()), 'AUTHORED_PURE_DIAGNOSTIC',{'MOCK':True})
            try:
                called=[];real_sync=os.fsync
                def sync(fd):called.append(1);return real_sync(fd)
                with patch.object(os,'fsync',side_effect=sync):value=diagnostic.write_initial_failure(journal,TimeoutError('PRIVATE_SENTINEL'),'POST')
                self.assertEqual(len(called),2)
                self.assertEqual(json.loads((journal.path/diagnostic.FILENAME).read_bytes()),value)
                self.assertNotIn(b'PRIVATE_SENTINEL',(journal.path/diagnostic.FILENAME).read_bytes())
                with self.assertRaises(FileExistsError):diagnostic.write_initial_failure(journal,ValueError(),'POST')
            finally:journal.close()
    def test_real_marker_fsync_failure_is_not_reported_durable(self):
        with tempfile.TemporaryDirectory() as directory:
            journal=_Journal(SimpleNamespace(directory=Path(directory).resolve()),'AUTHORED_FSYNC_FAILURE',{'MOCK':True})
            try:
                with patch.object(os,'fsync',side_effect=OSError('AUTHORED_FSYNC_FAILURE')):
                    with self.assertRaises(OSError):diagnostic.write_initial_failure(journal,TimeoutError(),'POST')
                # A created file alone is explicitly not a successful durable return.
                self.assertTrue((journal.path/diagnostic.FILENAME).is_file())
            finally:journal.close()


class CleanupOrder(unittest.TestCase):
    def flow(self,marker_fails=False,transition_fails=False):
        trace=[];original=RuntimeError('DO_NOT_SERIALIZE_OR_REPLACE');receipt='a'*32
        class Journal:
            def write(self,name,value):
                trace.append('write:'+name)
                if name==diagnostic.FILENAME and marker_fails:raise OSError('AUTHORED_MARKER_FAILURE')
            def close(self):trace.append('close_journal')
        class Owner:
            def open_canary(self,*_):trace.append('open')
            def intent(self,*_):pass
            def register_proofs(self,*_):pass
            def grant(self):return {'receipt':receipt,'request':{'execution_order':45,'pair_seed':client.p.SEED,'payload':{}},'context':{'payload_hash':canonical_hash({})}}
            def canary_snapshot(self):raise AssertionError('redundant snapshot forbidden')
            def transition(self,*a,**kw):
                trace.append('real_transition_boundary')
                if transition_fails:raise OSError('AUTHORED_TRANSITION_FAILURE')
            def close_canary(self,*_):trace.append('fallback_close_boundary')
        class Phase:
            def __init__(self,*_):pass
            def gate(self,*a,**k):pass
        class Gate:
            def check(self):pass
        class Capability:
            def __init__(self,*_):pass
            def post(self):trace.append('inert_POST_boundary');raise original
        records={r:{'body_utf8':'{}','metadata':{'url':'MOCK'}} for r in ('A','B')}
        catalog=client.InertCapturedCatalog(records,lambda:__import__('datetime').datetime.now(__import__('datetime').timezone.utc))
        packet={'run_id':'AUTHORED_PURE','parent_key':'b'*64,'price_release':{r:{'terms':{'model':'openai/gpt-4.1-nano' if r=='A' else 'qwen/qwen3-30b-a3b-instruct-2507'},'interpretation':{}} for r in ('A','B')}}
        with patch.object(client,'validate_diagnostic_release'),patch.object(client,'validate_release'),patch.object(client,'fresh_proof',return_value={}),patch.object(client,'_Phase',Phase),patch.object(client,'_Capability',Capability):
            with self.assertRaises(RuntimeError) as seen:client.execute_mock(packet,diagnostic_release={},expected_packet_hash='c'*64,release={},expected_release_hash='d'*64,owner=Owner(),credential=object(),transport=client.InertFailureTransport(),catalog_fetch=catalog,journal=Journal(),gate=Gate(),provenance='MOCK')
        self.assertIs(seen.exception,original)
        self.assertLess(trace.index('write:'+diagnostic.FILENAME),trace.index('real_transition_boundary'))
        return trace
    def test_marker_before_cleanup_and_redundant_close_removed(self):
        trace=self.flow();self.assertNotIn('fallback_close_boundary',trace)
    def test_marker_failure_still_conservative_cleanup_same_original_error(self):
        trace=self.flow(marker_fails=True);self.assertIn('real_transition_boundary',trace)
    def test_transition_failure_retains_original_and_fallback_close(self):
        trace=self.flow(transition_fails=True);self.assertIn('fallback_close_boundary',trace)
    def test_both_failures_still_original_exception(self):
        trace=self.flow(marker_fails=True,transition_fails=True);self.assertIn('fallback_close_boundary',trace)
    def test_no_real_transport_can_be_admitted_by_mock_successor(self):
        with patch.object(client,'validate_diagnostic_release'):
            with self.assertRaises(client.ExecutionBlocked):client.execute_mock({},diagnostic_release={},expected_packet_hash='a',release={},expected_release_hash='b',owner=object(),credential=object(),transport=object(),catalog_fetch=object())
    def test_real_provenance_cannot_enable_mock_successor(self):
        records={r:{'body_utf8':'{}','metadata':{'url':'MOCK'}} for r in ('A','B')}
        with patch.object(client,'validate_diagnostic_release'):
            with self.assertRaises(client.ExecutionBlocked):client.execute_mock({},diagnostic_release={},expected_packet_hash='a',release={},expected_release_hash='b',owner=object(),credential=object(),transport=client.InertFailureTransport(),catalog_fetch=client.InertCapturedCatalog(records,lambda:None),provenance='EXPLORATORY_REAL_MODEL')


if __name__=='__main__':
    import builtins,hashlib,sysconfig
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(599,600))
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(RuntimeError('PURE900SECONDS')));signal.alarm(900)
    root=Path(__file__).resolve().parents[1];scratch=Path(tempfile.gettempdir()).resolve();stdlib=Path(sysconfig.get_path('stdlib')).resolve()
    guardpath=root/'scripts/e01_authored_dirfd_guard_v2_20261112.py';ns={'__name__':'pure_dirfd','__file__':str(guardpath)};exec(compile(guardpath.read_bytes(),str(guardpath),'exec'),ns)
    descriptor=ns['DirectoryFdGuard'](lambda path,flags:None)
    counters={'reads':0,'writes':0,'console':0};limits={'reads':4294967296,'writes':268435456,'console':65536}
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
