"""One consumed fail-fast 66-test authored scope per runtime; no actual data."""
import ast
import builtins
import hashlib
import importlib.abc
import io
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import unittest
from e01_authored_dirfd_guard_20261112 import DirectoryFdGuard

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
MODULES=['e01_authored_dirfd_checks_20261112','test_clerk2020_native_campaign_v2','test_clerk2020_source_worker_v2',
         'test_clerk2020_source_job_v2','test_clerk2020_source_packet_prepare_v3']
RUNTIME=str(sys.version_info.major)+str(sys.version_info.minor)
assert RUNTIME in {'311','312'}
READ_CAP=536870912;WRITE_CAP=134217728;OUTPUT_CAP=262144
PREFIX=ROOT/'reports'/('clerk2020_monotone_offline_v2_'+RUNTIME+'_20261112')
START=Path(str(PREFIX)+'_STARTED.json');RECEIPT=Path(str(PREFIX)+'_RECEIPT.json')
clock=time.monotonic;usage=resource.getrusage
started=clock();initial_cpu=usage(resource.RUSAGE_SELF)
counts={'reserved_read_bytes':0,'reserved_write_bytes':0,'output_bytes':0}
class ScopeStop(BaseException):pass

def reserve(key,amount,cap):
    if type(amount) is not int or amount<0 or counts[key]+amount>cap:raise ScopeStop('FIXED_AUTHORED_SCOPE_EXHAUSTED')
    counts[key]+=amount

class NoNative(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'pypdf','PIL','cryptography','_cffi_backend'}:
            raise ScopeStop('NO_PDF_NATIVE_IMPORT')
sys.meta_path.insert(0,NoNative())

def allowed_path(path,flags):
    path=Path(os.path.realpath(path))
    toolchain=ROOT/'data/processed/toolchains/cpython-3.11.17-macos-aarch64-none'
    if (path.is_relative_to(ROOT/'data') and not path.is_relative_to(toolchain)) or path.name.startswith('.env'):
        raise ScopeStop('NO_ACTUAL_DATA_OR_CREDENTIALS')
    writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
    if writing and path.is_relative_to(ROOT) and path not in {START,RECEIPT}:
        raise ScopeStop('NO_REPOSITORY_MUTATION')

dirfds=DirectoryFdGuard(allowed_path)
def guard(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        path=dirfds.event_path(args[0])
        flags=args[2] if len(args)>2 and type(args[2]) is int else 0
        allowed_path(path,flags)
        if not(flags&os.O_WRONLY):
            try:size=path.stat().st_size
            except FileNotFoundError:size=0
            reserve('reserved_read_bytes',size+1,READ_CAP)
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','ctypes.dlopen'}:
        raise ScopeStop('NO_PROCESS_NETWORK_OR_NATIVE_LOAD')
sys.addaudithook(guard)
os.open=dirfds.open;os.close=dirfds.close

class MeteredFile:
    def __init__(self,stream):self.stream=stream
    def __getattr__(self,name):return getattr(self.stream,name)
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*args):return self.stream.__exit__(*args)
    def __iter__(self):return self
    def __next__(self):return next(self.stream)
    def write(self,data):
        size=len(data.encode(self.stream.encoding or 'utf8')) if isinstance(data,str) else memoryview(data).nbytes
        reserve('reserved_write_bytes',size,WRITE_CAP)
        return self.stream.write(data)
    def writelines(self,lines):
        for line in lines:self.write(line)

def wrap_open(original):
    def opening(*args,**kwargs):
        stream=original(*args,**kwargs)
        return stream if isinstance(stream,MeteredFile) else MeteredFile(stream)
    return opening
builtins.open=wrap_open(builtins.open);io.open=wrap_open(io.open);os.fdopen=wrap_open(os.fdopen)
raw_write=os.write

def write_fd(fd,data):
    reserve('reserved_write_bytes',memoryview(data).nbytes,WRITE_CAP)
    return raw_write(fd,data)
os.write=write_fd

class BoundedOutput:
    def __init__(self,stream):self.stream=stream
    def __getattr__(self,name):return getattr(self.stream,name)
    def write(self,data):
        reserve('output_bytes',len(data.encode('utf8')),OUTPUT_CAP)
        return self.stream.write(data)
sys.stdout=BoundedOutput(sys.stdout);sys.stderr=BoundedOutput(sys.stderr)
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def expired(*args):raise ScopeStop('FIXED_AUTHORED_WALL_EXHAUSTED')
signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,120)
with START.open('x') as f:json.dump({'kind':'TECHNICAL_AUTHORED_66_TESTS_STARTED','runtime':RUNTIME,'no_retry':True,
    'caps':{'reads':READ_CAP,'writes':WRITE_CAP,'output':OUTPUT_CAP,'wall_seconds':120,'cpu_seconds':120},
    'subprocesses':0,'actual_sources':0,'native_imports':0,'network_model_calls':0},f,sort_keys=True)

# Explicit task-code refs only, not actual source/runtime binary hashes.
source_paths=['src/civiclab/e01/clerk2020_native_campaign_v2.py','src/civiclab/e01/clerk2020_source_worker_v2.py',
              'src/civiclab/e01/clerk2020_source_job_v2.py','scripts/prepare_e01_source_phase_v3.py']
source_paths += ['tests/'+name+'.py' for name in MODULES if name!='e01_authored_dirfd_checks_20261112']
source_paths += ['scripts/e01_authored_dirfd_guard_20261112.py','scripts/e01_authored_dirfd_checks_20261112.py']
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths}
before=hashes();result=None;error=None
try:
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in MODULES)
    if suite.countTestCases()!=66:raise ScopeStop('FIXED_TEST_COUNT_MISMATCH')
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
except BaseException as exc:
    error=type(exc).__name__
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
    after=hashes();end_cpu=usage(resource.RUSAGE_SELF)
    record={'kind':'TECHNICAL_AUTHORED_66_TESTS_RECEIPT','runtime':RUNTIME,
        'tests_run':0 if result is None else result.testsRun,
        'successful':result is not None and result.wasSuccessful() and before==after and error is None,
        'error_type':error,'code_unchanged':before==after,'source_hashes':after,
        'counts':dict(counts),'wall_milliseconds':int((clock()-started)*1000)+1,
        'CPU_milliseconds':int(((end_cpu.ru_utime+end_cpu.ru_stime)-(initial_cpu.ru_utime+initial_cpu.ru_stime))*1000)+1,
        'no_retry':True,'actual_sources':0,'subprocesses':0,'PDF_native_imports':0,'network_model_calls':0,'cost_usd':0}
    with RECEIPT.open('x') as f:json.dump(record,f,sort_keys=True)
    print(json.dumps(record,sort_keys=True))
if not record['successful']:raise SystemExit(1)
