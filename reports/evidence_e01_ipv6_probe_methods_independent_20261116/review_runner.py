from pathlib import Path
import ast,builtins,hashlib,importlib.abc,io,json,os,resource,runpy,signal,sys,tempfile,time,unittest
ROOT=Path(__file__).resolve().parents[2]
START=time.monotonic();reads=writes=output=0
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(7,8))
def timeout(*args):raise RuntimeError('REVIEW_WALL_CPU_LIMIT')
signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGXCPU,timeout);signal.setitimer(signal.ITIMER_REAL,30)
TMP=Path(tempfile.gettempdir()).resolve();BASE=Path(sys.base_prefix).resolve()
class NoPackages(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'pip','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:raise RuntimeError('REVIEW_PACKAGE_IMPORT_DENIED')
sys.meta_path.insert(0,NoPackages())
def audit(event,args):
 global reads
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.exec','os.spawn','os.fork','os.forkpty','ctypes.dlopen','os.kill','os.killpg'}:raise RuntimeError('REVIEW_ACTUAL_OPERATION_DENIED')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  p=Path(os.fsdecode(args[0])).resolve();flags=args[2]
  writing=flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
  if writing:
   if not p.is_relative_to(TMP) or p.is_relative_to(ROOT):raise RuntimeError('REVIEW_WRITE_SCOPE_DENIED')
  else:
   allowed=(p.is_relative_to(BASE) or p.is_relative_to(ROOT/'scripts') or p.is_relative_to(ROOT/'tests') or (p.is_relative_to(TMP) and not p.is_relative_to(ROOT)))
   if not allowed or p.name.startswith('.env'):raise RuntimeError('REVIEW_READ_SCOPE_DENIED')
   try:size=p.stat().st_size
   except FileNotFoundError:size=0
   reads+=size+1
   if reads>67108864:raise RuntimeError('REVIEW_READ_CAP')
 if event in {'os.mkdir','os.remove','os.rmdir','os.chmod','os.truncate'}:
  if isinstance(args[0],(str,bytes,os.PathLike)):
   p=Path(os.fsdecode(args[0])).resolve()
   if not p.is_relative_to(TMP) or p.is_relative_to(ROOT):raise RuntimeError('REVIEW_MUTATION_SCOPE_DENIED')
 if event in {'os.link','os.symlink','os.rename'}:raise RuntimeError('REVIEW_LINK_RENAME_DENIED')
sys.addaudithook(audit)
def charge(data):
 global writes
 writes+=len(data.encode()) if isinstance(data,str) else len(data)
 if writes>16777216:raise RuntimeError('REVIEW_AUTHORED_OUTPUT_CAP')
class File:
 def __init__(self,s):self.s=s
 def __getattr__(self,n):return getattr(self.s,n)
 def __enter__(self):self.s.__enter__();return self
 def __exit__(self,*a):return self.s.__exit__(*a)
 def __iter__(self):return iter(self.s)
 def write(self,data):charge(data);return self.s.write(data)
 def writelines(self,items):
  for x in items:self.write(x)
def wrap(fn):
 def opening(*a,**kw):return File(fn(*a,**kw))
 return opening
builtins.open=wrap(builtins.open);io.open=wrap(io.open);os.fdopen=wrap(os.fdopen)
orig_write=os.write
def fdwrite(fd,data):charge(data);return orig_write(fd,data)
os.write=fdwrite
class Console:
 def __init__(self,s):self.s=s
 def __getattr__(self,n):return getattr(self.s,n)
 def write(self,data):
  global output
  output+=len(data.encode())
  if output>262144:raise RuntimeError('REVIEW_CONSOLE_CAP')
  return self.s.write(data)
sys.stdout=Console(sys.stdout);sys.stderr=Console(sys.stderr)
ns=runpy.run_path(str(ROOT/'tests/test_e01_offline_ipv6_probe_mock_candidate_v1_20261116.py'),run_name='independent_original_ipv6_suite')
m,p,o=ns['m'],ns['p'],ns['o'];C=ns['MockIpv6ConfigurationTests']
class Adverse(unittest.TestCase):
 setUp=C.setUp
 initialize=C.initialize
 def test_exact_mock_subclass_rejected(self):
  class Derived(m.MockSocketState):pass
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_STATE_TYPE'):m.scoped_mock_initialization(Derived(),self.vendor,self.initialize)
 def test_noncallable_keeps_fresh_state(self):
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_INITIALIZER_TYPE'):m.scoped_mock_initialization(self.socket,self.vendor,None)
  self.assertIs(self.socket.has_ipv6,True);self.assertEqual(self.vendor,m.MockVendorState())
 def test_scope_active_drift_restores_and_poison_vendor(self):
  def drift(s,v):self.initialize(s,v);v.scope_active=1
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_SCOPE_DRIFT'):m.scoped_mock_initialization(self.socket,self.vendor,drift)
  self.assertIs(self.socket.has_ipv6,True);self.assertIs(self.vendor.scope_active,False);self.assertIs(self.vendor.failed,True)
 def test_noop_initializer_refuses_after_restore(self):
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_INITIALIZATION_RESULT'):m.scoped_mock_initialization(self.socket,self.vendor,lambda *a:None)
  self.assertIs(self.socket.has_ipv6,True);self.assertTrue(self.vendor.failed)
 def test_residual_metadata_unknown_and_exec_counters(self):
  for event in ['socket.gethostname','socket.UNRECOGNIZED','socket.connect_ex','os.exec','os.spawn']:
   s,v=m.MockSocketState(),m.MockVendorState()
   with self.assertRaises(p.Refused):m.scoped_mock_initialization(s,v,lambda *a:self.guard.audit(event,()))
   self.assertIs(s.has_ipv6,True)
  self.assertEqual(self.guard.violations,5)
  self.assertEqual(self.guard.refusal_journal.total,5)
 def test_matched_comparator_fresh_same_callback(self):
  self.assertFalse(self.initialize(self.socket,self.vendor));self.assertEqual(self.guard.violations,1)
  self.assertEqual(self.guard.refusal_journal.events[0]['operation'],'SOCKET_CONSTRUCT')
  s,v=m.MockSocketState(),m.MockVendorState();prior=self.guard.violations
  receipt=m.scoped_mock_initialization(s,v,self.initialize)
  self.assertEqual(self.guard.violations,prior);self.assertIs(receipt['vendor_cached_ipv6'],False);self.assertIs(s.has_ipv6,True)
 def test_caught_precondition_reentry_is_not_sticky_documented_limit(self):
  def catches(s,v):
   try:m.scoped_mock_initialization(s,v,self.initialize)
   except m.MockConfigurationRefused:pass
   self.initialize(s,v)
  receipt=m.scoped_mock_initialization(self.socket,self.vendor,catches)
  self.assertIs(receipt['restored_has_ipv6'],True);self.assertFalse(self.vendor.failed)
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(C),unittest.defaultTestLoader.loadTestsFromTestCase(Adverse)])
result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
sock=sys.modules.get('socket');expected=BASE/'lib'/('python'+'.'.join(map(str,sys.version_info[:2])))/'socket.py'
if sock is None or Path(sock.__file__).resolve()!=expected.resolve():raise RuntimeError('REVIEW_SOCKET_IMPORT_ORIGIN')
if 'pip' in sys.modules:raise RuntimeError('REVIEW_PIP_IMPORTED')
print(json.dumps({'kind':'INDEPENDENT_IPV6_PURE_REVIEW','python':sys.version.split()[0],'tests':result.testsRun,'successful':result.wasSuccessful(),'transitive_stdlib_socket_import':True,'socket_origin':str(expected),'socket_source_sha256':hashlib.sha256(expected.read_bytes()).hexdigest(),'actual_socket_operations':0,'pip_import':False,'wall_seconds':time.monotonic()-START,'logical_open_read_bytes':reads,'authored_written_bytes':writes,'console_bytes_before_receipt':output,'cached_false_and_caught_reentry_limit_explicit':True}))
signal.setitimer(signal.ITIMER_REAL,0)
raise SystemExit(0 if result.wasSuccessful() else 1)
