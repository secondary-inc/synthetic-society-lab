"""Bounded authored-only CI causes; no actual PDFs/installer/owner/model."""
import sys,time,resource,signal
resource.setrlimit(resource.RLIMIT_CPU,(119,120));signal.alarm(180)
from pathlib import Path
import importlib.util,io,json,types,unittest
ROOT=Path.cwd();sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
def load(name,path):
 module=types.ModuleType(name);module.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__);return module
rows=[]
for version in ('v1','v2'):
 module=load('ci_authored_mime_'+version,ROOT/f'scripts/e01_p2_builtin_mime_candidate_{version}_20261116.py')
 module.sys=types.SimpleNamespace(platform='linux')
 try:module.initialize_builtin_mime_types(types.SimpleNamespace(inited=False,knownfiles=[]))
 except ValueError as error:
  assert error.args==('MIME_PLATFORM',);rows.append({'source':'mime_'+version,'mode':'AUTHORED_LINUX_BRANCH_CONTROL','reason':'MIME_PLATFORM','host_qualification':False})
 else:raise AssertionError('LINUX_EXPECTED_REJECTION')
m=load('ci_authored_cpu_age',ROOT/'scripts/e01_pypa_fixture_harness_candidate_v1_1_20261116.py')
for cpu in (0,121):
 m.resource=types.SimpleNamespace(getrusage=lambda _,cpu=cpu:types.SimpleNamespace(ru_utime=cpu,ru_stime=0),RUSAGE_SELF=0)
 budget=m.SharedBudget(clock=lambda:0)
 if cpu==0:budget.check();rows.append({'source':'pypa_shared_budget','mode':'AUTHORED_FRESH_PROCESS_CPU','status':'PASS'})
 else:
  try:budget.check()
  except m.HarnessRefused as error:
   assert error.code=='FIXTURE_CPU_CAP';rows.append({'source':'pypa_shared_budget','mode':'AUTHORED_OLDER_PROCESS_CPU','reason':error.code,'absolute_process_CPU':cpu})
  else:raise AssertionError('HOT_PROCESS_NOT_REJECTED')
loader=unittest.TestLoader();suite=loader.loadTestsFromNames([
 'test_e01_clerk2020_m1_v1.InspectionHarness.test_fixed_backend_real_subprocess_positive_replay_and_metrics',
 'test_e01_clerk2020_m1_v1.InspectionHarness.test_response_semantic_coedit_resource_unknown_or_spoof_and_backend_refused'])
result=unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({'kind':'CI_FOCUSED_CAUSE_PROBE','runtime':sys.version.split()[0],'platform':sys.platform,'pure_models':rows,
 'fresh_clerk_cases':result.testsRun,'fresh_clerk_errors':len(result.errors),'fresh_clerk_failures':len(result.failures),
 'actual_research_sources':0,'actual_installer_calls':0,'model_calls':0,'cost_usd':0},sort_keys=True))
raise SystemExit(0 if result.wasSuccessful() else 1)
