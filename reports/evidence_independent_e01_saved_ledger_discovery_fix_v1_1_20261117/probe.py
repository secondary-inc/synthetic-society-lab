"""Fresh-process discovery-only probe plus mocked standalone setup contract."""
import sys,os,time,resource,signal
START=time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU,(60,60))
resource.setrlimit(resource.RLIMIT_FSIZE,(8388608,8388608))
signal.alarm(60)
import ast,copy,hashlib,types,io,json,tempfile,unittest
import importlib.abc,importlib.util
from pathlib import Path
ROOT=Path.cwd();TEST=ROOT/'tests/test_e01_source_job_ledger_v1.py'
STDLIB=Path(os.__file__).resolve().parent
STATS={'read_bytes':0,'write_bytes':0,'denied':0,'test_body_calls':0,'fixture_calls':0,'source_reader_calls':0,'process_mutation_attempts':[]}
PROFILE_BEFORE=sys.getprofile();TRACE_BEFORE=sys.gettrace()
def profile(frame,event,arg):
    if event=='call' and frame.f_code.co_filename==str(TEST):
        name=frame.f_code.co_name
        if name.startswith('test_'):STATS['test_body_calls']+=1
        if name in {'authored','run_fixture','standalone_guard'}:STATS['fixture_calls']+=1
        if name in {'load_module','read_verified_public'}:STATS['source_reader_calls']+=1
sys.setprofile(profile)
def audit(event,args):
    if time.monotonic()-START>=60:raise RuntimeError('PROBE_WALL_CAP')
    if event.startswith(('socket.','subprocess.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec','os.kill'}:
        STATS['denied']+=1;raise PermissionError('PROBE_EXTERNAL_DENIED')
    if event=='open':
        name,mode,flags=args
        if type(name) is int:raise PermissionError('PROBE_UNDECLARED_DESCRIPTOR')
        p=Path(os.fsdecode(name)).absolute()
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('PROBE_WRITES_DENIED')
        if p!=TEST and not p.is_relative_to(STDLIB):
            STATS['denied']+=1;raise PermissionError('PROBE_READ_DENIED')
        STATS['read_bytes']+=p.stat().st_size+1
        if STATS['read_bytes']>33554432:raise RuntimeError('PROBE_READ_CAP')
    if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.chmod','os.utime'}:raise PermissionError('PROBE_MUTATION_DENIED')
sys.addaudithook(audit)
# Warm stdlib dependencies above. Import only exact source bytes: no pyc lookup.
class ExactLoader(importlib.abc.Loader):
    def create_module(self,spec):return None
    def exec_module(self,module):
        module.__file__=str(TEST)
        exec(compile(TEST.read_bytes(),str(TEST),'exec'),module.__dict__)
class ExactFinder(importlib.abc.MetaPathFinder):
    def find_spec(self,name,path=None,target=None):
        if name=='test_e01_source_job_ledger_v1':return importlib.util.spec_from_loader(name,ExactLoader(),origin=str(TEST))
finder=ExactFinder();sys.meta_path.insert(0,finder)
originals={
 'setrlimit':resource.setrlimit,'alarm':signal.alarm,'setitimer':signal.setitimer,'signal':signal.signal,
 'addaudithook':sys.addaudithook,'settrace':sys.settrace,'setprofile':sys.setprofile,
 'mkdtemp':tempfile.mkdtemp}
def forbidden(name):
    def reject(*args,**kwargs):
        STATS['process_mutation_attempts'].append(name);raise AssertionError('IMPORT_MUTATION_'+name)
    return reject
for name in ('setrlimit',):setattr(resource,name,forbidden(name))
for name in ('alarm','setitimer','signal'):setattr(signal,name,forbidden(name))
for name in ('addaudithook','settrace','setprofile'):setattr(sys,name,forbidden(name))
tempfile.mkdtemp=forbidden('mkdtemp')
limits_before={str(kind):resource.getrlimit(kind) for kind in (resource.RLIMIT_CPU,resource.RLIMIT_FSIZE)}
alarm_before=signal.getitimer(signal.ITIMER_REAL);handler_before=signal.getsignal(signal.SIGALRM)
trace_before=sys.gettrace();profile_before=sys.getprofile();hooks_before=dict(STATS)
loader=unittest.TestLoader()
suite=loader.discover(str(ROOT/'tests'),pattern='test_e01_source_job_ledger_v1.py')
module=sys.modules['test_e01_source_job_ledger_v1']
limits_after={str(kind):resource.getrlimit(kind) for kind in (resource.RLIMIT_CPU,resource.RLIMIT_FSIZE)}
alarm_after=signal.getitimer(signal.ITIMER_REAL)
assert suite.countTestCases()==30 and not loader.errors
assert limits_before==limits_after
assert 0<alarm_after[0]<=alarm_before[0] and alarm_after[1]==alarm_before[1]==0
assert signal.getsignal(signal.SIGALRM)==handler_before
assert sys.gettrace() is trace_before and sys.getprofile() is profile_before
assert STATS['process_mutation_attempts']==[]
assert all(STATS[k]==0 for k in ('denied','test_body_calls','fixture_calls','source_reader_calls'))
assert module.START is None and module.AUTHOR_TMP is None and module.M is None and module.PUBLIC_SAMPLE is None
assert module.GUARD=={'logical_open_read_bytes':0,'fixture_write_bytes':0,'denied':0}
# Focused mock setup: never apply the suite's120s/32MiB settings to this60s probe.
calls=[]
resource.setrlimit=lambda kind,value:calls.append(('setrlimit',kind,value))
signal.alarm=lambda value:calls.append(('alarm',value))
module.setup_direct_runtime()
assert calls==[('setrlimit',resource.RLIMIT_CPU,(120,120)),('setrlimit',resource.RLIMIT_FSIZE,(33554432,33554432)),('alarm',120)]
assert type(module.START) is float and module.START>=START
assert limits_before=={str(kind):resource.getrlimit(kind) for kind in (resource.RLIMIT_CPU,resource.RLIMIT_FSIZE)}
# Confirm actual direct-main control order without executing tests or guard.
tree=ast.parse(TEST.read_bytes());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='guarded_main')
ordered=[n.value.func.id for n in main.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name)]
assert ordered[:2]==['setup_direct_runtime','standalone_guard']
for name in ('setrlimit',):setattr(resource,name,originals[name])
for name in ('alarm','setitimer','signal'):setattr(signal,name,originals[name])
for name in ('addaudithook','settrace','setprofile'):setattr(sys,name,originals[name])
tempfile.mkdtemp=originals['mkdtemp'];sys.meta_path.remove(finder)
originals['setprofile'](PROFILE_BEFORE)
assert sys.gettrace() is TRACE_BEFORE
report={'kind':'E01_SAVED_LEDGER_DISCOVERY_FIX_V1_1_PROBE','runtime':sys.version.split()[0],
 'status':'INDEPENDENT_IMPORT_PURITY_PROBE_PASS','collected_cases':suite.countTestCases(),
 'test_bodies_executed':0,'full_suite_rerun':False,'limits_unchanged_on_discovery':limits_before==limits_after,
 'alarm_not_rearmed_on_discovery':True,'tracing_profiling_unchanged_on_discovery':True,
 'hook_additions_attempted_on_discovery':0,'fixture_creation_on_discovery':False,
 'focused_runtime_setup':'MOCK_CALLS_ONLY_EXACT_120S_CPU_WALL_32MIB_FSIZE_RETAINED',
 'direct_main_order':ordered[:2],'guard_counters':STATS,'wall_seconds':time.monotonic()-START,
 'real_reader_calls':0,'raw_source_calls':0,'network_calls':0,'model_calls':0,'cost_usd':0}
text=json.dumps(report,sort_keys=True)
assert len(text.encode())<=131072
print(text)
