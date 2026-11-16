"""PREPARED V1.2 successor: historical collection only; lead release required."""
from pathlib import Path
import ast
import builtins
import hashlib
import importlib.util
import io
import json
import os
import resource
import signal
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRATCH=Path(sys.argv[1]).resolve()
WALL_START=time.monotonic()
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_CPU,(119,120))

class CollectionStop(BaseException):pass

state={'phase':'SETUP','refusals':[],'reads_reserved':0,'writes':0,'console':0,
       'test_or_setup_entries':0,'execution_entries':0,'collection_calls':0,
       'open_files':{},'collection_errors':[],'expected_barrier_registration':False}

def stop(code,detail=None):
    event={'code':code}
    if detail is not None:event['detail']=detail
    state['refusals'].append(event)
    raise CollectionStop(code)

def deadline(*_):stop('HISTORICAL_COLLECTION_120_SECOND_LIMIT')
signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline)
signal.setitimer(signal.ITIMER_REAL,120)

RUNNER=ROOT/'scripts/run_offline_ci_v1.py'
EXPECTED_RUNNER_SHA='61bdc69cdcf592af213c0e8c357a0a8976a3140bcd8a60a4731a1972f2d6a3ae'
EXPECTED_TEST_SHA='f3ba0b75b883545194696955d067a11d44a96fe90f9736edbf5fca968d27d631'
raw=RUNNER.read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED_RUNNER_SHA:stop('RUNNER_SOURCE_BINDING')
if hashlib.sha256((ROOT/'tests/test_ci_collection_isolation_v1.py').read_bytes()).hexdigest()!=EXPECTED_TEST_SHA:stop('CI_TEST_SOURCE_BINDING')
spec=importlib.util.spec_from_file_location('reviewed_ci_collection_only',RUNNER)
c=importlib.util.module_from_spec(spec)
# Exact already-reviewed bytes; no mutable cache/source loader substituted.
exec(compile(raw,str(RUNNER),'exec'),c.__dict__)
helper_path=ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py'
helper_spec=importlib.util.spec_from_file_location('historical_collection_dirfd',helper_path)
helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
fdguard=helper.DirectoryFdGuard(lambda path,flags:None)
STDLIB=Path(sys.base_prefix)/f'lib/python{sys.version_info.major}.{sys.version_info.minor}'
SITE=ROOT/'.venv/lib/python3.12/site-packages'
TEST_PREFIX=str(ROOT/'tests')+os.sep
REPO_PREFIX=str(ROOT)+os.sep

# The real legacy project environment must be selected, not a bare runtime or
# E01 target. Inspect metadata, not import optional PDF/native dependencies.
if sys.version.split()[0]!='3.12.14' or Path(sys.prefix).resolve()!=(ROOT/'.venv').resolve():stop('HISTORICAL_ENVIRONMENT_IDENTITY')
metadata=SITE/'pypdf-6.10.0.dist-info/METADATA'
text=metadata.read_text()
if '\nVersion: 6.10.0\n' not in text:stop('HISTORICAL_PYPDF_METADATA')
if not any(Path(p).resolve()==(ROOT/'src').resolve() for p in sys.path if p):stop('EXISTING_EDITABLE_PROJECT_PATH_MISSING')
if any('.venv-e01' in p for p in sys.path):stop('UNACCEPTED_TARGET_PATH')

# Profile functions BEFORE the first bytecode of forbidden test/setup bodies.
# BaseException propagates out of unittest's normal import-error catch. This
# trusted-code guard is not an adversarial Python sandbox.
execution_codes=set()
for cls,names in ((unittest.TestCase,('run','debug','__call__')), (unittest.TestSuite,('run','debug','__call__')), (unittest.BaseTestSuite,('run','__call__')), (unittest.TextTestRunner,('run',)),(unittest.TestProgram,('__init__',))):
    for name in names:
        fn=getattr(cls,name,None)
        if hasattr(fn,'__code__'):execution_codes.add(fn.__code__)

def profile(frame,event,arg):
    if event=='call':
        code=frame.f_code;filename=code.co_filename;name=code.co_name
        if code in execution_codes:
            state['execution_entries']+=1;stop('UNITTEST_EXECUTION_PROHIBITED',name)
        if filename.startswith(TEST_PREFIX) and (name.startswith('test_') or name in {'setUp','tearDown','setUpClass','tearDownClass','setUpModule','tearDownModule','asyncSetUp','asyncTearDown'}):
            state['test_or_setup_entries']+=1
            stop('TEST_OR_SETUP_BODY_PROHIBITED',{'file':filename[len(REPO_PREFIX):],'function':name})
    elif event=='c_call' and getattr(arg,'__module__',None)=='_thread' and getattr(arg,'__name__',None) in {'start_new_thread','start_joinable_thread'}:
        stop('COLLECTION_THREAD_CREATION_PROHIBITED')

allowed_roots=(ROOT/'src',ROOT/'scripts',ROOT/'tests',ROOT/'configs',ROOT/'reports',STDLIB,SITE,SCRATCH)

def audit(event,args):
    if state['phase']=='COLLECTION' and state['refusals']:
        raise CollectionStop('STICKY_COLLECTION_REFUSAL')
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','os.kill','os.killpg','ctypes.dlopen','ctypes.dlsym'}:
        stop('NETWORK_PROCESS_NATIVE_OPERATION_PROHIBITED',event)
    if event=='sys.addaudithook' and state['phase']=='COLLECTION':
        if state['expected_barrier_registration']:
            state['expected_barrier_registration']=False
        else:stop('UNEXPECTED_GLOBAL_HOOK_REGISTRATION')
    if event in {'sys.setprofile','sys.settrace'} and state['phase']=='COLLECTION':
        stop('COLLECTION_GUARD_REPLACEMENT_PROHIBITED',event)
    if event=='open':
        value,mode,flags=args
        if isinstance(value,int):
            if flags & (os.O_WRONLY|os.O_RDWR):
                if value not in owned_fds:stop('UNBOUND_WRITE_DESCRIPTOR')
                return
            size=os.fstat(value).st_size
        else:
            path=Path(os.path.realpath(fdguard.event_path(value)))
            writing=bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing:
                if not path.is_relative_to(SCRATCH):stop('WRITE_OUTSIDE_OWNED_SCRATCH')
                return
            if '.venv-e01' in str(path):stop('UNACCEPTED_E01_TARGET_READ')
            if path.is_relative_to(ROOT/'data') or path.name.startswith('.env'):
                stop('SOURCE_DATA_OWNER_OR_CREDENTIAL_READ_PROHIBITED')
            if not (any(path.is_relative_to(p) for p in allowed_roots) or path in {ROOT/'pyproject.toml',ROOT/'README.md'}):
                stop('READ_OUTSIDE_TECHNICAL_SOURCE_SCOPE')
            try:
                st=path.stat();size=st.st_size
                state['open_files'][str(path)]={'dev':st.st_dev,'ino':st.st_ino,'size':st.st_size,'mtime_ns':st.st_mtime_ns}
            except FileNotFoundError:size=0
        state['reads_reserved']+=size+1
        if state['reads_reserved']>268435456:stop('TECHNICAL_SOURCE_READ_CAP')
    mutation_positions={'os.mkdir':(0,), 'os.remove':(0,), 'os.rmdir':(0,), 'os.rename':(0,1),'os.link':(0,1),'os.symlink':(1,), 'os.chmod':(0,), 'os.truncate':(0,), 'os.utime':(0,)}
    if event in mutation_positions:
        for position in mutation_positions[event]:
            value=args[position]
            if isinstance(value,int):
                if value not in owned_fds:stop('UNBOUND_MUTATION_DESCRIPTOR')
            elif not Path(os.path.realpath(value)).is_relative_to(SCRATCH):
                stop('MUTATION_OUTSIDE_OWNED_SCRATCH')

owned_fds=set()
raw_open=os.open;raw_close=os.close
# The existing helper maps dir_fd opens without widening file policy.
def tracked_open(*args,**kwargs):
    fd=fdguard.open(*args,**kwargs)
    if len(args)>1 and args[1] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT):owned_fds.add(fd)
    return fd

def tracked_close(fd,*args,**kwargs):
    owned_fds.discard(fd);return fdguard.close(fd,*args,**kwargs)

class Writer:
    def __init__(self,stream,kind):self.stream=stream;self.kind=kind
    def __getattr__(self,name):return getattr(self.stream,name)
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*args):return self.stream.__exit__(*args)
    def __iter__(self):return self
    def __next__(self):return next(self.stream)
    def write(self,value):
        size=len(value.encode('utf-8')) if isinstance(value,str) else memoryview(value).nbytes
        key='console' if self.kind=='console' else 'writes'
        state[key]+=size
        if state[key]>(524288 if self.kind=='console' else 33554432):stop('CONSOLE_OR_TEMP_WRITE_CAP')
        return self.stream.write(value)
    def writelines(self,items):
        for item in items:self.write(item)

for owner,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
    original=getattr(owner,name)
    def wrapped(*args,_original=original,**kwargs):
        stream=_original(*args,**kwargs)
        mode=kwargs.get('mode',args[1] if len(args)>1 else 'r')
        return Writer(stream,'file') if any(letter in mode for letter in 'wax+') else stream
    setattr(owner,name,wrapped)
raw_write=os.write

def write(fd,value):
    if fd not in owned_fds:stop('UNBOUND_OS_WRITE_DESCRIPTOR')
    state['writes']+=len(value)
    if state['writes']>33554432:stop('TEMP_WRITE_CAP')
    return raw_write(fd,value)

def path_metadata(value):
    if not isinstance(value,str):return {'kind':'NON_STRING_PATH','type':type(value).__name__}
    if value=='':return {'kind':'CWD_ENTRY','cwd':str(ROOT)}
    path=Path(value)
    if path.is_absolute() and (path.is_relative_to(ROOT) or path.is_relative_to(Path(sys.base_prefix))):
        return {'kind':'TECHNICAL_PATH','path':value,'resolved':str(path.resolve())}
    return {'kind':'UNEXPECTED_PATH_REDACTED','sha256':hashlib.sha256(value.encode()).hexdigest()}


def import_snapshot():
    namespace=sys.modules.get('tests')
    spec=getattr(namespace,'__spec__',None) if namespace is not None else None
    origin=getattr(spec,'origin',None)
    return {'sys_path':[path_metadata(value) for value in sys.path],
            'tests_namespace':{'present':namespace is not None,
              'origin':None if origin is None else path_metadata(origin),
              'file':None if getattr(namespace,'__file__',None) is None else path_metadata(namespace.__file__),
              'search_locations':[path_metadata(value) for value in list(getattr(namespace,'__path__',[]))],
              'spec_search_locations':[path_metadata(value) for value in list(getattr(spec,'submodule_search_locations',None) or [])],
              'loader_type':type(getattr(spec,'loader',None)).__name__},
            'owned_namespace_finders':[{'type':type(finder).__name__,'root':str(finder.root),'tests':str(finder.tests)} for finder in sys.meta_path if getattr(finder,'offline_ci_owned_tests_namespace_v1_2',False)]}


class StopOnImportErrorLoader(c.OrdinaryLoader):
    def discover(self,*args,**kwargs):
        result['import_context_snapshots']['inside_before_discovery']=import_snapshot()
        try:
            return super().discover(*args,**kwargs)
        finally:
            try:result['import_context_snapshots']['inside_after_discovery_or_stop']=import_snapshot()
            except BaseException:result['import_context_snapshots']['inside_after_discovery_or_stop']={'status':'CAPTURE_UNAVAILABLE_AFTER_STOP'}
    def _find_test_path(self,*args,**kwargs):
        before=len(self.errors)
        result=super()._find_test_path(*args,**kwargs)
        if len(self.errors)>before:
            state['collection_errors'].extend(self.errors[before:])
            stop('COLLECTION_IMPORT_ERROR_STOP')
        return result

loader=StopOnImportErrorLoader(ROOT)
os.open=tracked_open;os.close=tracked_close;os.write=write
sys.stdout=Writer(sys.stdout,'console');sys.stderr=Writer(sys.stderr,'console')
sys.addaudithook(audit)
sys.setprofile(profile)
result={'kind':'HISTORICAL_312_ORDINARY_COLLECTION_ONLY_V1_2','status':'ERROR_BEFORE_COLLECTION','historical_environment_only':True,'current_ci_qualification':False,'runner_sha256':EXPECTED_RUNNER_SHA,'python':sys.version.split()[0], 'sys_prefix':sys.prefix,'pypdf_metadata_version':'6.10.0', 'test_run_count':0,'setups_executed':0}
result['ci_test_sha256']=EXPECTED_TEST_SHA
result['import_context_snapshots']={'pre_context':import_snapshot(),'inside_before_discovery':{'status':'NOT_REACHED'},'inside_after_discovery_or_stop':{'status':'NOT_REACHED'}}
try:
    state['phase']='COLLECTION'
    state['expected_barrier_registration']=True
    state['collection_calls']+=1
    suite,barrier=c.collect_ordinary(ROOT,loader=loader)
    cases=list(c.flatten(suite))
    ids=[];failed=[];skipped=[]
    for case in cases:
        method=getattr(case,'_testMethodName',None)
        row={'module':type(case).__module__,'class':type(case).__qualname__,'method':method}
        ids.append(row)
        if type(case).__name__=='_FailedTest':failed.append(row)
        if getattr(type(case),'__unittest_skip__',False):skipped.append(row)
    if loader.errors:
        state['collection_errors'].extend(loader.errors);stop('COLLECTION_IMPORT_ERRORS_RETAINED')
    if failed:stop('FAILED_TEST_PLACEHOLDER_RETAINED')
    excluded=sorted(barrier.excluded)
    imported_frozen=[str(Path(getattr(module,'__file__','')).resolve()) for module in list(sys.modules.values()) if getattr(module,'__file__',None) and str(Path(module.__file__).resolve()) in barrier.excluded]
    if imported_frozen:stop('FROZEN_MODULE_WAS_IMPORTED')
    if any('.venv-e01' in p for p in sys.path):stop('UNACCEPTED_TARGET_PATH_AFTER_COLLECTION')
    result.update(status='PASS_HISTORICAL_COLLECTION_ONLY',collected_case_count=len(ids),case_ids=ids,failed_test_placeholders=failed,skipped_case_placeholders=skipped, six_frozen_excluded=excluded,imported_frozen_modules=imported_frozen,barrier_collecting_after_return=barrier.collecting)
except BaseException as error:
    # Preserve original collection tracebacks from loader; guard failures are
    # closed codes only, without raw exception arguments/locals or data.
    result.update(status='STOPPED_COLLECTION_ERROR_OR_GUARD',stop_type=type(error).__name__,collected_case_count=None)
finally:
    state['phase']='CLOSED'
    sys.setprofile(None)
    result['import_context_snapshots']['after_context']=import_snapshot()
    signal.setitimer(signal.ITIMER_REAL,0)
result.update(state=state,elapsed_seconds=time.monotonic()-WALL_START,project_modules=[{'name':name,'path':getattr(module,'__file__',None)} for name,module in sorted(sys.modules.items()) if name=='civiclab' or name.startswith('civiclab.')])
artifact=json.dumps(result,sort_keys=True).encode()
artifact_path=SCRATCH/'collection-receipt.json'
with open(artifact_path,'xb') as stream:stream.write(artifact)
print('HISTORICAL_COLLECTION_RECEIPT_V1_2='+json.dumps({'status':result['status'],'artifact_sha256':hashlib.sha256(artifact).hexdigest(),'artifact_bytes':len(artifact),'collected_case_count':result.get('collected_case_count'),'test_run_count':0,'setup_executions':0,'guarded_write_bytes_including_artifact':state['writes'],'refusal_count':len(state['refusals']),'elapsed_seconds':result['elapsed_seconds']},sort_keys=True),flush=True)
raise SystemExit(0 if result['status']=='PASS_HISTORICAL_COLLECTION_ONLY' else 1)
