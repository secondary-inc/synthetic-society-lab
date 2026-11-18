from pathlib import Path
import resource,signal,sys,sysconfig,time,json,unittest,runpy,os,ast
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(29,30));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(30)
root=Path.cwd();start=time.monotonic();caller=root/'reports/evidence_e01_fec2020_actual_20261118/read_candidate_once_a02_v1_1.py';tests=root/'tests/test_fec_candidate_failure_diagnostic.py';parser=root/'src/civiclab/e01/fec2020_parser_v1.py';stdlib=Path(sysconfig.get_path('stdlib')).resolve()
def audit(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.fork','os.posix_spawn','os.system','sqlite3.connect','ctypes.dlopen'):raise RuntimeError('NO_EXTERNAL_EFFECTS')
 if event=='open' and not isinstance(args[0],int):
  p=Path(args[0]).resolve();assert not args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND);assert p in (caller,tests,parser) or p.is_relative_to(stdlib)
sys.addaudithook(audit)
class Additional(unittest.TestCase):
 def setUp(self):self.n=runpy.run_path(str(caller),run_name='inert');self.safe=self.n['safe_failure']
 def test_all_owned_codes_and_no_others(self):
  class Exact(ValueError):pass
  self.safe.__globals__['_PARSER_REFUSED_TYPE']=Exact
  for code in self.n['_SAFE_PARSER_CODES']:self.assertEqual(self.safe(Exact(code))['safe_code'],code)
  for code in self.n['_SAFE_GUARD_CODES']:self.assertEqual(self.safe(RuntimeError(code))['safe_code'],code)
  self.assertEqual(self.safe(RuntimeError('ARCHIVE_MEMBER'))['safe_code'],'OMITTED')
 def test_multiple_args_are_not_projected(self):self.assertEqual(self.safe(RuntimeError('FEC_A02_READ_BOUND','AUTHORED'))['safe_code'],'OMITTED')
 def test_str_subclass_is_not_compared_or_coerced(self):
  class Foreign(str):
   def __hash__(self):raise AssertionError('foreignhash')
   def __eq__(self,_):raise AssertionError('foreigneq')
  self.assertEqual(self.safe(RuntimeError(Foreign('FEC_A02_READ_BOUND')))['safe_code'],'OMITTED')
 def test_bound_exact_parser_attrs_and_str_not_touched(self):
  class Exact(ValueError):
   @property
   def args(self):raise AssertionError('foreign args property')
   def __str__(self):raise AssertionError('foreignstr')
  self.safe.__globals__['_PARSER_REFUSED_TYPE']=Exact
  self.assertEqual(self.safe(Exact('ARCHIVE_MEMBER'))['safe_code'],'ARCHIVE_MEMBER')
 def test_parser_subclass_not_identity(self):
  class Exact(ValueError):pass
  class Child(Exact):pass
  self.safe.__globals__['_PARSER_REFUSED_TYPE']=Exact
  self.assertEqual(self.safe(Child('ARCHIVE_MEMBER'))['error_type'],'OTHER')
 def test_allowlist_exact_literal_parser_codes(self):
  tree=ast.parse(parser.read_text());codes=set()
  for x in ast.walk(tree):
   if isinstance(x,ast.Call) and isinstance(x.func,ast.Name):
    if x.func.id=='require' and len(x.args)>1 and isinstance(x.args[1],ast.Constant) and type(x.args[1].value) is str:codes.add(x.args[1].value)
    if x.func.id=='ParserRefused' and x.args and isinstance(x.args[0],ast.Constant) and type(x.args[0].value) is str:codes.add(x.args[0].value)
  self.assertEqual(set(self.n['_SAFE_PARSER_CODES']),codes)
import types
module=types.ModuleType('author_diag');module.__file__=str(tests);exec(compile(tests.read_bytes(),str(tests),'exec'),module.__dict__)
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(module),unittest.defaultTestLoader.loadTestsFromTestCase(Additional)]);r=unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({'kind':'INDEPENDENT_FEC_A02_DIAGNOSTIC_CORRECTION','successful':r.wasSuccessful(),'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'runtime':sys.version.split()[0],'CPU_seconds':sum(resource.getrusage(resource.RUSAGE_SELF)[:2]),'wall_seconds':time.monotonic()-start,'actual_caller_main_reader_workbook_key_owner_network_calls':0},sort_keys=True));signal.alarm(0);raise SystemExit(0 if r.wasSuccessful() else 1)
