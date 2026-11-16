from pathlib import Path
import json,hashlib,ast,subprocess,os,time
ROOT=Path.cwd();OUT=Path('/tmp/civiclab-auditor-e02-w03-diagnostic-20261116');OUT.mkdir(exist_ok=False)
def ref(n):
 b=(ROOT/n).read_bytes();return {'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
report=json.loads((ROOT/'reports/E02_W03_CI_DIAGNOSTIC_RESULTS_20261116.json').read_text());pins=report['source_pins'];T='tests/test_e02_f_wy_actual_bootstrap_v1.py'
refs={n:ref(n) for n in list(pins)+['reports/E02_W03_CI_DIAGNOSTIC_DRAFT_20261116.json','reports/E02_W03_CI_DIAGNOSTIC_RESULTS_20261116.json']}
for n,h in pins.items():assert refs[n]['sha256']==h
old=subprocess.run(['git','show','25d51254e5547cecf345a10c76ee22a7e83d9c18:'+T],cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout
assert hashlib.sha256(old).hexdigest()=='b211a2cca49b02ebefeb39b3d2c738170796ed83aafcc254abf8ee34ff606e1f'
now=ast.parse((ROOT/T).read_bytes());prior=ast.parse(old)
now.body=[n for n in now.body if not(isinstance(n,ast.FunctionDef) and n.name=='_run_positive_with_diagnostics')]
for node in now.body:
 if isinstance(node,ast.ClassDef) and node.name=='ConditionalWiringTests':
  node.body=[n for n in node.body if not(isinstance(n,ast.FunctionDef) and n.name=='test_W03_failure_note_is_bounded_redacted_and_preserves_exception')]
  for n in ast.walk(node):
   if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_run_positive_with_diagnostics':
    n.func=ast.Attribute(value=ast.Name(id='api',ctx=ast.Load()),attr='run_authorized',ctx=ast.Load());n.args=n.args[:1]
assert ast.dump(now,include_attributes=False)==ast.dump(prior,include_attributes=False)
for n,h in pins.items():
 if n==T:continue
 git=subprocess.run(['git','show','25d51254e5547cecf345a10c76ee22a7e83d9c18:'+n],cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout
 assert hashlib.sha256(git).hexdigest()==h
for r in report['results']:
 n=r['log'];refs[n]=ref(n);assert refs[n]['bytes']==r['bytes']==1061 and refs[n]['sha256']==r['sha256']
 text=(ROOT/n).read_text();assert 'Ran 5 tests in ' in text and '\nOK\n' in text and text.count(' ... ok')==5
 assert r['exit_code']==0 and 0<r['UTC_elapsed_seconds']<120 and 0<r['monotonic_seconds']<120 and abs(r['UTC_elapsed_seconds']-r['monotonic_seconds'])<2
child=r'''import sys,os,signal,resource,unittest,json,ast
from pathlib import Path
from unittest.mock import patch,Mock
root=Path.cwd();sys.path[:0]=[str(root/'src'),str(root/'tests')]
def guard(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn'):raise RuntimeError('NO_NETWORK_OR_CHILD_PROCESS')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=os.path.abspath(os.fsdecode(args[0]))
  if p.startswith(str(root/'data')) and not p.startswith(str(root/'data/processed/toolchains')+'/'):raise RuntimeError('NO_ACTUAL_DATA_OWNER_SOURCE')
  if '/.codex/' in p or p.endswith('/.env'):raise RuntimeError('NO_SECRET')
sys.addaudithook(guard);resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(30,30));signal.alarm(60)
import test_e02_f_wy_actual_bootstrap_v1 as m
class Adverse(unittest.TestCase):
 def test_success_return_and_snapshot_not_called(self):
  result=object();control=Mock()
  with patch.object(m.api,'run_authorized',return_value=result):self.assertIs(m._run_positive_with_diagnostics(None,control),result)
  control.snapshot.assert_not_called()
 def test_all_original_exception_types_and_snapshot_failure(self):
  for typ in (m.Blocked,RuntimeError,AssertionError,OSError,KeyboardInterrupt,SystemExit):
   with self.subTest(typ=typ):
    original=typ('PRIVATE PATH respondent token-secret');control=Mock();control.snapshot.side_effect=OSError('OTHER PRIVATE')
    with patch.object(m.api,'run_authorized',side_effect=original):
     try:m._run_positive_with_diagnostics(None,control)
     except BaseException as caught:self.assertIs(caught,original)
     else:self.fail('did not preserve original')
    self.assertEqual(len(original.__notes__),1);note=original.__notes__[0];self.assertLessEqual(len(note),2048);v=json.loads(note)
    self.assertEqual(v['error']['reason'],'REDACTED');self.assertEqual(v['state_error']['reason'],'REDACTED')
    for secret in ('PRIVATE','respondent','token-secret'):self.assertNotIn(secret,note)
 def test_note_failure_preserves_original(self):
  class BadNote(RuntimeError):
   def add_note(self,*args):raise ValueError('PRIVATE')
  original=BadNote('PRIVATE');control=Mock();control.snapshot.side_effect=RuntimeError('PRIVATE')
  with patch.object(m.api,'run_authorized',side_effect=original):
   with self.assertRaises(BadNote) as caught:m._run_positive_with_diagnostics(None,control)
  self.assertIs(caught.exception,original)
 def test_allowlisted_state_only_and_context_preserved(self):
  context=RuntimeError('PRIVATE');original=m.Blocked('rollback or discontinuous clocks');original.__context__=context
  control=Mock();control.snapshot.return_value={'shutdown':'CLOSED','failed':True,'stages':{k:{'status':'UNKNOWN' if i%2 else 'PENDING'} for i,k in enumerate(m.ORDER)},'raw':'PRIVATE'}
  with patch.object(m.api,'run_authorized',side_effect=original):
   with self.assertRaises(m.Blocked) as caught:m._run_positive_with_diagnostics(None,control)
  self.assertIs(caught.exception,original);self.assertIs(original.__context__,context)
  note=original.__notes__[0];value=json.loads(note);self.assertLessEqual(len(note),2048);self.assertNotIn('PRIVATE',note)
  self.assertEqual(value['error']['reason'],'rollback or discontinuous clocks');self.assertEqual(value['context']['reason'],'REDACTED')
suite=unittest.defaultTestLoader.loadTestsFromTestCase(Adverse)
suite.addTests(unittest.defaultTestLoader.loadTestsFromNames(['test_e02_f_wy_actual_bootstrap_v1.ConditionalWiringTests.test_W03_failure_note_is_bounded_redacted_and_preserves_exception','test_e02_f_wy_actual_bootstrap_v1.ConditionalWiringTests.test_W01_production_rejects_null_or_test_authority_before_filesystem']))
r=unittest.TextTestRunner(verbosity=2).run(suite);signal.alarm(0);sys.exit(0 if r.wasSuccessful() and r.testsRun==6 else 1)
'''
(OUT/'runner.py').write_text(child);(OUT/'STARTED.json').write_text(json.dumps({'source_pins':pins,'maximum_invocations_each':1,'tests_each':6,'UTC_and_monotonic_seconds_each':60,'CPU_each':30,'no_fullsuite_or_positive_native_replay':True},indent=2)+'\n')
results=[]
for tag,exe in [('312',ROOT/'.venv/bin/python'),('311',ROOT/'data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11')]:
 mono=time.monotonic();utc=time.time();r=subprocess.run([str(exe),'-I','-B','-S',str(OUT/'runner.py')],cwd=ROOT,env={},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
 result={'runtime':tag,'exit_code':r.returncode,'UTC_elapsed_seconds':time.time()-utc,'monotonic_seconds':time.monotonic()-mono,'bytes':len(r.stdout),'sha256':hashlib.sha256(r.stdout).hexdigest()};results.append(result)
 (OUT/('python-'+tag+'.log')).write_bytes(r.stdout);(OUT/'RECEIPT.json').write_text(json.dumps(results,indent=2)+'\n')
 assert r.returncode==0 and len(r.stdout)<=262144 and b'Ran 6 tests in ' in r.stdout and b'\nOK\n' in r.stdout,r.stdout[-2500:]
 assert 0<=result['UTC_elapsed_seconds']<60 and 0<=result['monotonic_seconds']<60 and abs(result['UTC_elapsed_seconds']-result['monotonic_seconds'])<2
for n,h in pins.items():assert ref(n)['sha256']==h
value={'status':'PASS_DIAGNOSTIC_ONLY_SCOPE','refs':refs,'results':results,'original_positive_and_other_tests_AST_unchanged_except_wrapper':True,'production_matches_exact_source_commit':True,'retained_five_tests_each':report['results'],'remote_root_cause':'UNKNOWN'}
(OUT/'verification.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');print(json.dumps({k:v for k,v in value.items() if k!='refs'}))
