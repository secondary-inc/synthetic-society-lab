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
ns=runpy.run_path(str(ROOT/'tests/test_e01_offline_ipv6_compatibility_v1_1_20261116.py'),run_name='independent_original_concrete_suite')
d,A=ns['d'],ns['A'];patch=ns['patch'];ModuleType=ns['ModuleType']
for name in ['ControllerTests','AdapterTests','PublicFacadeMockTests','ClosureTests','FrozenStructureTests']:globals()[name]=ns[name]
class IndependentAdapter(unittest.TestCase):
 setUp=ns['AdapterTests'].setUp
 run_scope=ns['AdapterTests'].run_scope
 def test_exact_module_subclass_refuses_before_poison(self):
  class Fake(ModuleType):pass
  owner=A.Owner();A._ACTIVE=owner
  with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_EXACT_SOCKET_MODULE'):A.scoped(Fake('MOCK'),lambda:None,lambda x:None)
  self.assertFalse(owner.poisoned)
 def test_caught_reentry_different_mock_module_poison_survives_reset(self):
  other=ModuleType('MOCK_OTHER');other.has_ipv6=True;owners=[]
  def init():
   owners.append(A._ACTIVE)
   try:A.scoped(other,lambda:None,lambda x:None)
   except A.CompatibilityRefused:pass
   A._FAILED=False
  with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_STICKY_FAILURE'):self.run_scope(init)
  self.assertTrue(owners[0].poisoned);self.assertTrue(A._FAILED);self.assertIsNone(A._ACTIVE);self.assertIs(self.socket.has_ipv6,True);self.assertIs(other.has_ipv6,True)
 def test_result_check_baseexception_identity_and_restore(self):
  primary=KeyboardInterrupt('AUTHORED_CHECK_PRIMARY')
  def check(value):raise primary
  with self.assertRaises(KeyboardInterrupt) as caught:self.run_scope(lambda:None,check)
  self.assertIs(caught.exception,primary);self.assertTrue(A._FAILED);self.assertIsNone(A._ACTIVE);self.assertIs(self.socket.has_ipv6,True)
 def test_owner_identity_replacement_at_exit_fails_and_restores(self):
  def init():A._ACTIVE=A.Owner()
  with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_SCOPE_DRIFT'):self.run_scope(init)
  self.assertTrue(A._FAILED);self.assertIsNone(A._ACTIVE);self.assertIs(self.socket.has_ipv6,True)
class IndependentClosure(unittest.TestCase):
 setUp=ns['ClosureTests'].setUp
 def test_origin_drift_for_same_name_refuses(self):
  first=A.importlib.util.spec_from_file_location('MOCK',self.source);self.closure.spec('MOCK',first)
  second=A.importlib.machinery.ModuleSpec('MOCK',A.importlib.machinery.BuiltinImporter,origin='built-in')
  with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_IMPORT_ORIGIN_DRIFT'):self.closure.spec('MOCK',second)
 def test_reload_refused_before_finder(self):
  class Never:
   def find_spec(self,*a):raise AssertionError('FINDER_MUST_NOT_RUN')
  self.closure.previous_finders=(Never(),)
  with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_RELOAD_DENIED'):self.closure.find_spec('MOCK',target=object())
 def test_absence_preserves_normal_name_and_message_without_execution(self):
  self.closure.previous_finders=()
  with self.assertRaises(ModuleNotFoundError) as caught:self.closure.find_spec('AUTHORED_MISSING')
  self.assertEqual(self.closure.names['AUTHORED_MISSING'],{'name':'AUTHORED_MISSING','origin':'not-found'})
  self.assertEqual(caught.exception.name,'AUTHORED_MISSING');self.assertEqual(str(caught.exception),"No module named 'AUTHORED_MISSING'")
class IndependentReceipt(unittest.TestCase):
 def test_pinned_target_cannot_be_replaced_with_builtin_label(self):
  with ns['tempfile'].TemporaryDirectory() as temp:
   root=Path(temp).resolve();name='MOCK_PIP/_vendor/urllib3/util/connection.py';binding={'base_prefix':str(root/'base'),'pip_root':'MOCK_PIP','pip_files':{name:{'bytes':1,'sha256':'0'*64}}}
   value=ns['receipt'](root,binding);value['import_closure']=[{'name':A.TARGET,'origin':'built-in'}]
   with self.assertRaisesRegex(d.Refused,'COMPATIBILITY_RECEIPT_TARGET'):d.validate_compatibility_receipt(d.packed(value),binding,root)
 def test_duplicate_module_names_refused(self):
  with ns['tempfile'].TemporaryDirectory() as temp:
   root=Path(temp).resolve();name='MOCK_PIP/_vendor/urllib3/util/connection.py';binding={'base_prefix':str(root/'base'),'pip_root':'MOCK_PIP','pip_files':{name:{'bytes':1,'sha256':'0'*64}}}
   value=ns['receipt'](root,binding);value['import_closure']*=2
   with self.assertRaisesRegex(d.Refused,'COMPATIBILITY_RECEIPT_CLOSURE'):d.validate_compatibility_receipt(d.packed(value),binding,root)
class IndependentController(unittest.TestCase):
 setUpClass=classmethod(ns['ControllerTests'].setUpClass.__func__)
 setUp=ns['ControllerTests'].setUp
 tearDown=ns['ControllerTests'].tearDown
 rebind=ns['ControllerTests'].rebind
 launcher=ns['ControllerTests'].launcher
 execute=ns['ControllerTests'].execute
 def test_receipt_content_drift_after_first_capture_forces_failed_terminal(self):
  original=d.capture_compatibility;calls=[]
  def capture(*args):
   result=original(*args);calls.append(result)
   if len(calls)==1:
    path=args[0]/'guest-compatibility.json';v=d.json_body(path.read_bytes());v['vendor_cached_ipv6']=True;path.write_bytes(d.packed(v))
   return result
  with patch.object(d,'capture_compatibility',side_effect=capture):result=self.execute()
  self.assertEqual(result['outcome'],'FAILED_COMPATIBILITY');self.assertEqual(result['reason'],'COMPATIBILITY_RECEIPT_CHANGED');self.assertEqual(len(self.calls),1)
  terminal=d.json_body((self.root/d.OUTPUT/'TERMINAL.json').read_bytes());self.assertEqual(terminal['outcome'],'FAILED_COMPATIBILITY');self.assertLessEqual((self.root/d.OUTPUT/'TERMINAL.json').stat().st_size,32768)
  self.assertGreaterEqual(len(calls),2)
 def test_oversize_receipt_still_closes_failed_terminal(self):
  raw=b'X'*131073
  def oversize(*args):result=self.launcher(*args);(self.root/d.OUTPUT/'guest-compatibility.json').write_bytes(raw);return result
  result=self.execute(oversize)
  self.assertEqual(result['outcome'],'FAILED_COMPATIBILITY');self.assertEqual(result['reason'],'DIAGNOSTIC_RESULT_SIZE');self.assertEqual(len(self.calls),1)
  terminal=d.json_body((self.root/d.OUTPUT/'TERMINAL.json').read_bytes());self.assertIsNone(terminal['compatibility']);self.assertLessEqual((self.root/d.OUTPUT/'TERMINAL.json').stat().st_size,32768)
  self.assertEqual((self.root/d.OUTPUT/'guest-compatibility.json').read_bytes(),raw)
class IndependentCapture(unittest.TestCase):
 def test_maximum_invalid_raw_retained_with_compact_invalid_binding(self):
  with ns['tempfile'].TemporaryDirectory(prefix='independent-invalid-MOCK-') as temp:
   root=Path(temp).resolve();scope=root/'scope';scope.mkdir();raw=b'X'*131072;path=scope/'guest-compatibility.json';path.write_bytes(raw)
   bound=d.capture_compatibility(scope,{},root)
   self.assertFalse(bound['validated']);self.assertIsNone(bound['summary']);self.assertEqual(bound['ref'],{'path':'guest-compatibility.json','bytes':131072,'sha256':d.sha(raw)});self.assertLessEqual(len(d.packed(bound)),1536);self.assertEqual(path.read_bytes(),raw)
 def test_full_closure_hash_checked_even_when_summary_fields_unchanged(self):
  with ns['tempfile'].TemporaryDirectory(prefix='independent-fullclosure-MOCK-') as temp:
   root=Path(temp).resolve();scope=root/'scope';scope.mkdir();name='MOCK_PIP/_vendor/urllib3/util/connection.py';binding={'base_prefix':str(root/'base'),'pip_root':'MOCK_PIP','pip_files':{name:{'bytes':1,'sha256':'0'*64}}}
   value=ns['receipt'](root,binding);alias=ns['copy'].deepcopy(value['import_closure'][0]);alias['name']='aaa_MOCK_ALIAS';alias['source_ref']['sha256']='1'*64;value['import_closure'].append(alias);value['import_closure'].sort(key=lambda r:r['name'])
   (scope/'guest-compatibility.json').write_bytes(d.packed(value));bound=d.capture_compatibility(scope,binding,root)
   self.assertFalse(bound['validated']);self.assertEqual(bound['error_code'],'COMPATIBILITY_RECEIPT_PIP_PIN');self.assertIsNone(bound['summary'])
 def test_terminal_ancestry_exact_boundary_and_one_byte_over(self):
  prefix=len(d.packed({'prior':{'MOCK':''},'old_metadata_snapshot':{}}));prior={'MOCK':'x'*(20480-prefix)}
  proof=d.terminal_headroom(prior,{})
  self.assertEqual(proof['maximum_supported_total'],32768)
  prior['MOCK']+='x'
  with self.assertRaisesRegex(d.Refused,'COMPATIBILITY_TERMINAL_ANCESTRY_HEADROOM'):d.terminal_headroom(prior,{})
try:ns['g'].f.old.g.old.guarded_test_main()
except SystemExit as stopped:EXIT=stopped.code or 0
sock=sys.modules.get('socket');expected=BASE/'lib'/('python'+'.'.join(map(str,sys.version_info[:2])))/'socket.py'
assert sock is not None and Path(sock.__file__).resolve()==expected.resolve()
assert not any(n=='pip' or n.startswith('pip.') for n in sys.modules)
print(json.dumps({'kind':'INDEPENDENT_CONCRETE_IPV6_V1_1_REVIEW','python':sys.version.split()[0],'original_checks':53,'independent_checks':14,'expected_checks':67,'exit_code':EXIT,'wall_seconds':time.monotonic()-START,'logical_open_read_bytes_including_startup':READS,'transitive_stdlib_socket_import':True,'socket_origin':str(expected),'socket_source_sha256':hashlib.sha256(expected.read_bytes()).hexdigest(),'actual_socket_functions_or_globals_or_pip':0,'original_authored_bounds':'120sCPUwall_64MiBread_32MiBtempwrite_256KiBconsole','independent_no_rerun':True}))
raise SystemExit(EXIT)
