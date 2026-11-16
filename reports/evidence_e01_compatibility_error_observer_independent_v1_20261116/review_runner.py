from pathlib import Path
import hashlib,importlib.abc,json,os,resource,runpy,signal,sys,time,unittest
ROOT=Path(__file__).resolve().parents[2];START=time.monotonic();READS=0
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def deadline(*a):raise RuntimeError('INDEPENDENT_REVIEW_WALL_CPU_CAP')
signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline);signal.setitimer(signal.ITIMER_REAL,120)
class NoPackages(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'pip','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:raise RuntimeError('INDEPENDENT_NO_PACKAGE_IMPORT')
sys.meta_path.insert(0,NoPackages())
BASE=Path(sys.base_prefix).resolve()
def early(event,args):
 global READS
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.exec','os.spawn','os.fork','os.forkpty','ctypes.dlopen','os.kill','os.killpg'}:raise RuntimeError('INDEPENDENT_NO_ACTUAL_OPERATION')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  resolver=getattr(os.open,'__self__',None)
  if resolver is not None and type(resolver).__name__=='DirectoryFdGuard' and type(resolver).__module__=='e01_authored_dirfd_guard_v2_20261112':
   p=resolver.event_path(args[0])
  else:
   p=Path(os.fsdecode(args[0]))
   if not p.is_absolute():raise RuntimeError('INDEPENDENT_UNBOUND_RELATIVE_OPEN')
   p=p.resolve()
  flags=args[2]
  actual_target=p.is_relative_to(ROOT) and p.relative_to(ROOT).parts and p.relative_to(ROOT).parts[0].startswith('.venv-e01-')
  if ((p.is_relative_to(ROOT/'data') and not p.is_relative_to(BASE)) or p.name.startswith('.env') or actual_target):raise RuntimeError('INDEPENDENT_NO_REAL_INPUT_TARGET_OWNER_CREDENTIAL')
  if p.is_relative_to(ROOT) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise RuntimeError('INDEPENDENT_NO_REPOSITORY_WRITE')
  if not flags&os.O_WRONLY:
   try:size=p.stat().st_size
   except FileNotFoundError:size=0
   READS+=size+1
   if READS>67108864:raise RuntimeError('INDEPENDENT_STARTUP_AND_TEST_READ_CAP')
sys.addaudithook(early)
ns=runpy.run_path(str(ROOT/'tests/test_e01_compatibility_error_observer_candidate_v1_20261116.py'),run_name='independent_original_error_observer_suite')
m,p=ns['m'],ns['p'];patch=ns['patch']
for name in ['ErrorObserverTests','ObserverValidationTests','GuardAndStaticModelTests']:globals()[name]=ns[name]
class IndependentObserver(unittest.TestCase):
 def test_poisoned_exception_metadata_never_accessed(self):
  touches=[]
  class Poison(RuntimeError):
   def __getattribute__(self,n):touches.append(n);raise AssertionError('ATTR_READ')
   def __str__(self):touches.append('str');raise AssertionError('STR_READ')
   def __repr__(self):touches.append('repr');raise AssertionError('REPR_READ')
  observer=m.ErrorObserver(((Poison,'COMPATIBILITY_REFUSED'),));observer.record_exception(Poison('AUTHORED_PRIVATE_MESSAGE'),'COMPATIBILITY_VENDOR_RESULT');raw=observer.encode()
  self.assertEqual(touches,[]);self.assertNotIn(b'AUTHORED_PRIVATE',raw);self.assertEqual(m.decode(raw)['first_error']['exception_type'],'COMPATIBILITY_REFUSED')
 def test_phase_and_code_str_subclasses_never_compare_or_stringify(self):
  touches=[]
  class Text(str):
   def __eq__(self,x):touches.append('eq');raise AssertionError('COMPARE')
   def __hash__(self):touches.append('hash');raise AssertionError('HASH')
   def __len__(self):touches.append('len');raise AssertionError('LEN')
   def __str__(self):touches.append('str');raise AssertionError('STR')
  observer=m.ErrorObserver();observer.mark_phase(Text('MIME_READY'));observer.record_exception(RuntimeError('AUTHORED_PRIVATE'),Text('INPUT_HASH'));v=m.decode(observer.encode())
  self.assertEqual(touches,[]);self.assertEqual(v['last_phase'],'UNKNOWN_PHASE');self.assertEqual(v['latest_error']['code'],m.UNAVAILABLE)
 def test_observer_baseexception_preserves_callback_systemexit_identity(self):
  observer=m.ErrorObserver();primary=SystemExit('AUTHORED_PRIMARY');calls=[]
  def callback():calls.append(1);raise primary
  with patch.object(observer,'record_exception',side_effect=KeyboardInterrupt('AUTHORED_OBSERVER_FAILURE')):
   try:observer.observe_call('PIP_DRY_RUN_START',callback,code='PIP_NONZERO_EXIT')
   except SystemExit as caught:self.assertIs(caught,primary)
   else:self.fail('PRIMARY_NOT_PROPAGATED')
  self.assertEqual(calls,[1]);self.assertTrue(m.decode(observer.encode())['observer_failed']);self.assertEqual(observer.failure_total,0)
 def test_emitter_exact_saturation_boundary(self):
  observer=m.ErrorObserver()
  for _ in range(m.MAX_COUNTER):observer.mark_phase('GUEST_ENTRY')
  before=m.decode(observer.encode());self.assertFalse(before['phase_saturated']);self.assertEqual(before['phase_dropped'],65519)
  observer.mark_phase('MIME_READY');after=m.decode(observer.encode());self.assertTrue(after['phase_saturated']);self.assertEqual(after['phase_dropped'],65520);self.assertEqual(after['phase_total'],65535)
  print(json.dumps({'kind':'INDEPENDENT_OBSERVER_EMITTER_SATURATION_BOUNDARY','at_total':65535,'unsaturated_dropped':before['phase_dropped'],'first_saturated_dropped':after['phase_dropped'],'stored':16},sort_keys=True))
 def test_impossible_saturated_dropped_counts_are_currently_accepted_blocker(self):
  observer=m.ErrorObserver()
  for _ in range(m.MAX_PHASES):observer.mark_phase('GUEST_ENTRY')
  original=observer.snapshot();accepted=[]
  for dropped in (0,65519):
   value=ns['copy'].deepcopy(original);value.update(phase_total=m.MAX_COUNTER,phase_dropped=dropped,phase_saturated=True)
   result=m.decode(m.packed(value));self.assertEqual(result['phase_dropped'],dropped);accepted.append(dropped)
  print(json.dumps({'kind':'INDEPENDENT_OBSERVER_SCHEMA_BLOCKER','code':'IMPOSSIBLE_SATURATED_DROPPED_COUNT_ACCEPTED','accepted_impossible_dropped':accepted,'required_minimum':65520,'total':65535,'prefix_entries':16,'payload':{**original,'phase_total':65535,'phase_dropped':0,'phase_saturated':True}},sort_keys=True))
 def test_nested_duplicate_json_record_keys_refused(self):
  observer=m.ErrorObserver();observer.record_exception(RuntimeError());raw=observer.encode();raw=raw.replace(b'"exception_type":"RUNTIME_ERROR"',b'"exception_type":"RUNTIME_ERROR","exception_type":"IMPORT_ERROR"',1)
  with self.assertRaises(m.ObserverPayloadRefused):m.decode(raw)
 def test_custom_metaclass_registration_refuses_before_metadata(self):
  class Meta(type):
   def __getattribute__(self,name):raise AssertionError('CLASS_METADATA')
  class Error(RuntimeError,metaclass=Meta):pass
  with self.assertRaises(m.ObserverPayloadRefused):m.ErrorObserver(((Error,'COMPATIBILITY_REFUSED'),))
 def test_exception_return_value_is_not_retained_or_classified_as_failure(self):
  primary=RuntimeError('AUTHORED_PRIVATE');observer=m.ErrorObserver();result=observer.observe_call('GUEST_ENTRY',lambda:primary)
  self.assertIs(result,primary);self.assertEqual(observer.snapshot()['failure_total'],0);self.assertNotIn(b'AUTHORED_PRIVATE',observer.encode());self.assertFalse(any(x is primary for x in vars(observer).values()))
 def test_failed_later_recording_leaves_explicit_partial_history(self):
  observer=m.ErrorObserver();observer.record_exception(ImportError('AUTHORED_FIRST'));primary=RuntimeError('AUTHORED_PRIMARY')
  def fails():raise primary
  with patch.object(observer,'record_exception',side_effect=MemoryError('AUTHORED_RECORDER')):
   try:observer.observe_call('GUEST_ENTRY',fails)
   except RuntimeError as caught:self.assertIs(caught,primary)
   else:self.fail('MISSING_PRIMARY')
  v=m.decode(observer.encode());self.assertTrue(v['observer_failed']);self.assertEqual(v['latest_error']['exception_type'],'IMPORT_ERROR');self.assertNotIn(b'AUTHORED_',observer.encode())
 def test_schema_counter_boolean_negative_and_overflow_rejected(self):
  for key,value in [('phase_total',True),('phase_dropped',-1),('failure_total',65536)]:
   row=m.ErrorObserver().snapshot();row[key]=value
   with self.assertRaises(m.ObserverPayloadRefused):m.decode(m.packed(row))
try:ns['t'].g.old.guarded_test_main()
except SystemExit as stopped:EXIT=stopped.code or 0
sock=sys.modules.get('socket');expected=BASE/'lib'/('python'+'.'.join(map(str,sys.version_info[:2])))/'socket.py'
assert sock is not None and Path(sock.__file__).resolve()==expected.resolve()
assert not any(n=='pip' or n.startswith('pip.') for n in sys.modules)
print(json.dumps({'kind':'INDEPENDENT_ERROR_OBSERVER_PURE_V1_REVIEW','python':sys.version.split()[0],'original_checks':34,'independent_checks':10,'expected_checks':44,'exit_code':EXIT,'wall_seconds':time.monotonic()-START,'logical_open_read_bytes_including_startup':READS,'transitive_stdlib_socket_import':True,'socket_origin':str(expected),'socket_source_sha256':hashlib.sha256(expected.read_bytes()).hexdigest(),'actual_socket_functions_or_globals_or_pip':0,'original_authored_bounds':'120sCPUwall_64MiBread_32MiBtempwrite_256KiBconsole','independent_no_rerun':True,'passing_characterization_does_not_accept_known_schema_blocker':True}))
raise SystemExit(EXIT)
