"""Focused refusal-fix regressions through ordinary CI wrapper, not historical CI."""
import sys,os,time,resource,signal
START=time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));signal.alarm(180)
import ast,copy,hashlib,types,io,json,tempfile,unittest,selectors,subprocess
import importlib.abc,importlib.util
from pathlib import Path
ROOT=Path.cwd();TEST=ROOT/'tests/test_e01_source_job_ledger_v1.py';SCRIPT=ROOT/'scripts/run_e01_saved_job_ledger_suite_v1.py'
SOURCE=ROOT/'src/civiclab/e01/source_job_ledger_v1.py';ENTRY=ROOT/'scripts/compile_e01_saved_job_ledger_v1_20261117.py'
STDLIB=Path(os.__file__).resolve().parent
COUNTS={'parent_audited_read_bytes':0,'parent_writes':0,'subprocess_launches':0,'denied':0,'discovery_mutations':[]}
PHASE='DISCOVERY'
originals={'setrlimit':resource.setrlimit,'alarm':signal.alarm,'setitimer':signal.setitimer,'signal':signal.signal,
 'addaudithook':sys.addaudithook,'settrace':sys.settrace,'setprofile':sys.setprofile,'mkdtemp':tempfile.mkdtemp}
def audit(event,args):
    if time.monotonic()-START>=180:raise RuntimeError('INTEGRATION_WALL_CAP')
    if event=='subprocess.Popen':
        executable,argv,cwd,env=args
        expected=[sys.executable,'-I','-B','-S',str(SCRIPT)]
        if PHASE!='EXECUTION' or argv!=expected or str(cwd)!=str(ROOT) or env!={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'} or COUNTS['subprocess_launches']!=0:raise PermissionError('UNEXPECTED_CHILD')
        COUNTS['subprocess_launches']+=1
    elif event.startswith(('socket.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec'}:
        COUNTS['denied']+=1;raise PermissionError('UNEXPECTED_EXTERNAL')
    if event=='open':
        name,mode,flags=args
        if type(name) is int:return # admitted Popen pipe descriptors only
        p=Path(os.fsdecode(name)).absolute()
        # subprocess requires /dev/null for explicit stdin=DEVNULL, not source data.
        if p==Path('/dev/null') and PHASE=='EXECUTION':return
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('PARENT_WRITE_DENIED')
        if p not in {TEST,SCRIPT,SOURCE,ENTRY} and not p.is_relative_to(STDLIB):
            COUNTS['denied']+=1;raise PermissionError('PARENT_READ_DENIED')
        COUNTS['parent_audited_read_bytes']+=p.stat().st_size+1
        if COUNTS['parent_audited_read_bytes']>67108864:raise RuntimeError('PARENT_READ_CAP')
    if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.chmod','os.utime'}:raise PermissionError('PARENT_MUTATION_DENIED')
sys.addaudithook(audit)
class Loader(importlib.abc.Loader):
    def create_module(self,spec):return None
    def exec_module(self,module):module.__file__=str(TEST);exec(compile(TEST.read_bytes(),str(TEST),'exec'),module.__dict__)
class Finder(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name=='test_e01_source_job_ledger_v1':return importlib.util.spec_from_loader(name,Loader(),origin=str(TEST))
finder=Finder();sys.meta_path.insert(0,finder)
def refuse(name):
    def reject(*a,**k):COUNTS['discovery_mutations'].append(name);raise AssertionError('COLLECTOR_MUTATION_'+name)
    return reject
resource.setrlimit=refuse('setrlimit')
for name in ('alarm','setitimer','signal'):setattr(signal,name,refuse(name))
for name in ('addaudithook','settrace','setprofile'):setattr(sys,name,refuse(name))
tempfile.mkdtemp=refuse('mkdtemp')
limits_before={str(k):resource.getrlimit(k) for k in (resource.RLIMIT_CPU,resource.RLIMIT_FSIZE)}
alarm_before=signal.getitimer(signal.ITIMER_REAL);trace_before=sys.gettrace();profile_before=sys.getprofile()
loader=unittest.TestLoader();suite=loader.discover(str(ROOT/'tests'),pattern='test_e01_source_job_ledger_v1.py')
assert suite.countTestCases()==1 and not loader.errors
assert COUNTS['discovery_mutations']==[] and COUNTS['subprocess_launches']==0
assert limits_before=={str(k):resource.getrlimit(k) for k in (resource.RLIMIT_CPU,resource.RLIMIT_FSIZE)}
assert 0<signal.getitimer(signal.ITIMER_REAL)[0]<=alarm_before[0]
assert sys.gettrace() is trace_before and sys.getprofile() is profile_before
module=sys.modules['test_e01_source_job_ledger_v1']
PHASE='EXECUTION'
stream=io.StringIO();captured=io.StringIO();previous=sys.stdout;sys.stdout=captured
try:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
finally:sys.stdout=previous
assert result.wasSuccessful(),stream.getvalue()
assert result.testsRun==1 and COUNTS['subprocess_launches']==1
nestedline=next(x for x in captured.getvalue().splitlines() if x.startswith('E01_SAVED_LEDGER_CI_NESTED_V1='))
nested=json.loads(nestedline.split('=',1)[1]);assert len(nested['nested_cases'])==33
# New wrapper's pure failure admission: no extra child or fixture run.
valid=module.verified_script();case=next(n for n in ast.parse(valid).body if isinstance(n,ast.ClassDef) and n.name=='LedgerTests')
case_names=sorted(n.name for n in case.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
receipt=copy.deepcopy(nested['nested_receipt'])
def authored_output(record,names=None):return ('\n'.join(n+' (MOCK.AUTHORED) ... ok' for n in (case_names if names is None else names))+'\n'+json.dumps(record)).encode()
assert module.validate_nested(authored_output(receipt),valid)[1]==case_names
adverse=0
for key,value in [('tests',29),('tests',True),('failures',1),('model_calls',1),('network_calls',True),('interpreter_startup_read_accounting','CLAIMED'),('wall_seconds',float('nan'))]:
    bad=copy.deepcopy(receipt);bad[key]=value
    try:module.validate_nested(authored_output(bad),valid)
    except AssertionError:adverse+=1
    else:raise AssertionError('ADVERSE_ACCEPTED')
for key,value in [('denied',1),('logical_open_read_bytes',67108865),('fixture_write_bytes',33554433)]:
    bad=copy.deepcopy(receipt);bad['guard'][key]=value
    try:module.validate_nested(authored_output(bad),valid)
    except AssertionError:adverse+=1
    else:raise AssertionError('GUARD_ADVERSE_ACCEPTED')
for raw in (authored_output(receipt,case_names[:-1]),authored_output(receipt,case_names+[case_names[0]]),b'x'*262145):
    try:module.validate_nested(raw,valid)
    except AssertionError:adverse+=1
    else:raise AssertionError('COVERAGE_ADVERSE_ACCEPTED')
assert adverse==13
assert COUNTS['subprocess_launches']==1 and COUNTS['discovery_mutations']==[]
assert limits_before=={str(k):resource.getrlimit(k) for k in (resource.RLIMIT_CPU,resource.RLIMIT_FSIZE)}
assert sys.gettrace() is trace_before and sys.getprofile() is profile_before
assert COUNTS['parent_audited_read_bytes']+nested['nested_receipt']['guard']['logical_open_read_bytes']<=67108864
for name in ('setrlimit',):setattr(resource,name,originals[name])
for name in ('alarm','setitimer','signal'):setattr(signal,name,originals[name])
for name in ('addaudithook','settrace','setprofile'):setattr(sys,name,originals[name])
tempfile.mkdtemp=originals['mkdtemp'];sys.meta_path.remove(finder)
report={'kind':'E01_SAVED_LEDGER_REFUSAL_FIX_V1_1_PROBE','status':'AUTHOR_PASS_PENDING_INDEPENDENT_REVIEW','runtime':sys.version.split()[0],
 'ordinary_cases':1,'nested_cases':33,'pure_wrapper_adverse_cases':adverse,'collector_process_controls_unchanged':True,
 'counts':COUNTS,'nested_evidence':nested,'wall_seconds':time.monotonic()-START,'full_historical_suite':False,
 'source_install_scope_replay':False,'raw_source_calls':0,'real_saved_reader_calls':0,'network_calls':0,'model_calls':0,'cost_usd':0,
 'startup_read_accounting':'NOT_CLAIMED'}
output=stream.getvalue()+json.dumps(report,sort_keys=True)+'\n';assert len(output.encode())<=262144
print(output,end='')
