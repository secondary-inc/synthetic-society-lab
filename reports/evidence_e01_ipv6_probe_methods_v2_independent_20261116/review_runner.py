from pathlib import Path
import ast,builtins,hashlib,importlib.abc,io,json,os,resource,runpy,signal,sys,tempfile,time,unittest
ROOT=Path(__file__).resolve().parents[2]
REPORT_ALLOW={ROOT/'reports/E01_IPV6_OPTIONAL_PROBE_COMPATIBILITY_METHODS_V1_20261116.json', ROOT/'reports/INDEPENDENT_AUDIT_E01_IPV6_PROBE_COMPATIBILITY_METHODS_V1_20261116.json'}
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
   allowed=(p in REPORT_ALLOW or p.is_relative_to(BASE) or p.is_relative_to(ROOT/'scripts') or p.is_relative_to(ROOT/'tests') or (p.is_relative_to(TMP) and not p.is_relative_to(ROOT)))
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
ns=runpy.run_path(str(ROOT/'tests/test_e01_offline_ipv6_probe_mock_candidate_v2_20261116.py'),run_name='independent_original_ipv6_suite')
m,p,o=ns['m'],ns['p'],ns['o'];C=ns['MockIpv6ConfigurationTests']
class Adverse(unittest.TestCase):
 setUp=C.setUp
 initialize=C.initialize
 def test_original_caught_reset_reentry_counterexample_now_poisoned(self):
  def catches(s,v):
   try:m.scoped_mock_initialization(s,v,self.initialize)
   except m.MockConfigurationRefused:pass
   v.failed=False;self.initialize(s,v)
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_STICKY_FAILURE'):m.scoped_mock_initialization(self.socket,self.vendor,catches)
  self.assertTrue(self.vendor.failed);self.assertIs(self.socket.has_ipv6,True);self.assertIsNone(self.vendor._active_failure)
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_VENDOR_NOT_FRESH'):m.scoped_mock_initialization(self.socket,self.vendor,self.initialize)
 def test_same_vendor_different_socket_poison_exact_owner(self):
  other=m.MockSocketState();saved=[]
  def nested(s,v):
   saved.append(v._active_failure)
   try:m.scoped_mock_initialization(other,v,self.initialize)
   except m.MockConfigurationRefused:pass
   self.assertTrue(v._active_failure.poisoned);self.assertIs(other.has_ipv6,True)
   v.failed=False;self.initialize(s,v)
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_STICKY_FAILURE'):m.scoped_mock_initialization(self.socket,self.vendor,nested)
  self.assertTrue(saved[0].poisoned);self.assertTrue(self.vendor.failed);self.assertIs(self.socket.has_ipv6,True)
 def test_invalid_type_reentry_does_not_poison_valid_owner(self):
  from types import SimpleNamespace
  def nested(s,v):
   token=v._active_failure
   with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_STATE_TYPE'):m.scoped_mock_initialization(SimpleNamespace(has_ipv6=True),v,self.initialize)
   self.assertFalse(token.poisoned);self.assertFalse(v.failed);self.initialize(s,v)
  m.scoped_mock_initialization(self.socket,self.vendor,nested)
  self.assertFalse(self.vendor.failed);self.assertIs(self.socket.has_ipv6,True)
 def test_replaced_owner_token_still_drifts_despite_caught_reset(self):
  tokens=[]
  def replaces(s,v):
   tokens.append(v._active_failure);replacement=m._MockScopeFailure();tokens.append(replacement);v._active_failure=replacement
   try:m.scoped_mock_initialization(s,v,self.initialize)
   except m.MockConfigurationRefused:pass
   v.failed=False;self.initialize(s,v)
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_SCOPE_DRIFT'):m.scoped_mock_initialization(self.socket,self.vendor,replaces)
  self.assertTrue(tokens[0].poisoned);self.assertTrue(tokens[1].poisoned);self.assertIsNone(self.vendor._active_failure);self.assertTrue(self.vendor.failed)
 def test_primary_baseexception_identity_after_caught_reentry_and_drift(self):
  primary=KeyboardInterrupt('AUTHORED_PRIMARY')
  def fails(s,v):
   try:m.scoped_mock_initialization(s,v,self.initialize)
   except m.MockConfigurationRefused:pass
   s.has_ipv6='AUTHORED_DRIFT';v.scope_active=0;raise primary
  with self.assertRaises(KeyboardInterrupt) as caught:m.scoped_mock_initialization(self.socket,self.vendor,fails)
  self.assertIs(caught.exception,primary);self.assertIs(self.socket.has_ipv6,True);self.assertIs(self.vendor.scope_active,False);self.assertIsNone(self.vendor._active_failure);self.assertTrue(self.vendor.failed)
 def test_independent_mock_owners_do_not_cross_poison(self):
  other_s,other_v=m.MockSocketState(),m.MockVendorState()
  def separate(s,v):m.scoped_mock_initialization(other_s,other_v,self.initialize);self.initialize(s,v)
  m.scoped_mock_initialization(self.socket,self.vendor,separate)
  self.assertFalse(self.vendor.failed);self.assertFalse(other_v.failed);self.assertIs(other_s.has_ipv6,True);self.assertIs(self.socket.has_ipv6,True)
 def test_reentry_keeps_preexisting_and_new_residual_counters(self):
  try:self.guard.audit('socket.gethostname',())
  except p.Refused:pass
  def nested(s,v):
   try:m.scoped_mock_initialization(s,v,self.initialize)
   except m.MockConfigurationRefused:pass
   try:self.guard.audit('socket.__new__',())
   except p.Refused:pass
   v.failed=False;self.initialize(s,v)
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_STICKY_FAILURE'):m.scoped_mock_initialization(self.socket,self.vendor,nested)
  self.assertEqual(self.guard.violations,2);self.assertEqual(self.guard.refusal_journal.total,2)
  with self.assertRaisesRegex(p.Refused,'GUEST_CAUGHT_VIOLATION'):p.need(self.guard.violations==0,'GUEST_CAUGHT_VIOLATION')
 def test_bad_cached_result_cannot_clear_owner_failure(self):
  def wrong(s,v):v.initialized=True;v.cached_ipv6=0
  with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_INITIALIZATION_RESULT'):m.scoped_mock_initialization(self.socket,self.vendor,wrong)
  self.assertTrue(self.vendor.failed);self.assertIs(self.socket.has_ipv6,True);self.assertIsNone(self.vendor._active_failure)
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(C),unittest.defaultTestLoader.loadTestsFromTestCase(Adverse)])
result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
sock=sys.modules.get('socket');expected=BASE/'lib'/('python'+'.'.join(map(str,sys.version_info[:2])))/'socket.py'
if sock is None or Path(sock.__file__).resolve()!=expected.resolve():raise RuntimeError('REVIEW_SOCKET_IMPORT_ORIGIN')
if 'pip' in sys.modules:raise RuntimeError('REVIEW_PIP_IMPORTED')
print(json.dumps({'kind':'INDEPENDENT_IPV6_V2_PURE_REVIEW','python':sys.version.split()[0],'tests':result.testsRun,'successful':result.wasSuccessful(),'transitive_stdlib_socket_import':True,'socket_origin':str(expected),'socket_source_sha256':hashlib.sha256(expected.read_bytes()).hexdigest(),'actual_socket_operations':0,'pip_import':False,'wall_seconds':time.monotonic()-START,'logical_open_read_bytes':reads,'authored_written_bytes':writes,'console_bytes_before_receipt':output,'cached_false_and_nonhostile_sticky_reentry_scope_explicit':True}))
signal.setitimer(signal.ITIMER_REAL,0)
raise SystemExit(0 if result.wasSuccessful() else 1)
