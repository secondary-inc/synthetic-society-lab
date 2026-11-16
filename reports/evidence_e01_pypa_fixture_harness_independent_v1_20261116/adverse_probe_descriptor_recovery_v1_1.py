"""Independent inert-only probe; no real tool loading or OS writes."""
import sys

def early(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','ctypes.dlopen'}:
        raise AssertionError('NO_NETWORK_PROCESS_NATIVE')
    if event == 'import' and args and args[0].split('.')[0] in {'installer','pip','ssl_fixture_payload','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:
        raise AssertionError('NO_TOOL_PAYLOAD_OR_TARGET_IMPORT')
sys.addaudithook(early)

import hashlib
import json
import os
from pathlib import Path
import resource
import runpy
import signal

ROOT=Path(__file__).resolve().parents[2]
ME=Path(__file__).resolve()
TEST=ROOT/'tests/test_e01_pypa_fixture_harness_candidate_v1_20261116.py'
CODE=ROOT/'scripts/e01_pypa_fixture_harness_candidate_v1_20261116.py'
allowed={ME,TEST,CODE,*[ROOT/'scripts'/name for name in (
    'e01_strict_wheel_source_candidate_v1_20261116.py',
    'install_e01_pypdf701_runtime_v1_5.py',
    'e01_authored_dirfd_guard_v2_20261112.py')]}
stdlib=(Path(sys.base_prefix)/'lib').resolve()
reads=0
registered={}
raw_open,raw_close,raw_fdopen=os.open,os.close,os.fdopen
def identity(st):return st.st_dev,st.st_ino,st.st_mode
def audit(event,args):
    global reads
    if event=='open':
        if type(args[0]) is int:
            record=registered.get(args[0])
            if record is None:raise AssertionError('UNKNOWN_FILE_DESCRIPTOR')
            p,expected=record
            if identity(os.fstat(args[0]))!=expected or identity(p.stat(follow_symlinks=False))!=expected:
                raise AssertionError('REUSED_OR_MOVED_FILE_DESCRIPTOR')
            if any(v.is_symlink() for v in (p,*p.parents)):raise AssertionError('ALIASED_FILE_DESCRIPTOR')
        elif isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.path.realpath(args[0]))
        else:raise AssertionError('NO_DESCRIPTOR_IO')
        flags=args[2]
        if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise AssertionError('NO_OS_WRITES')
        if not (p in allowed or (p.is_relative_to(stdlib) and 'site-packages' not in p.parts)):
            raise AssertionError('UNAPPROVED_READ')
        try: reads+=p.stat().st_size+1
        except FileNotFoundError: reads+=1
        if reads>67108864:raise AssertionError('READ_CAP')
    if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.truncate','os.chmod'}:
        raise AssertionError('NO_OS_MUTATIONS')
def tracked_open(path,flags,*args,**kwargs):
    p=Path(path)
    if not p.is_absolute() or p not in allowed or kwargs.get('dir_fd') is not None:
        raise AssertionError('ONLY_EXACT_OWN_SOURCE_DESCRIPTOR')
    if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('NO_DESCRIPTOR_WRITES')
    if any(v.is_symlink() for v in (p,*p.parents)):raise AssertionError('NO_DESCRIPTOR_ALIAS')
    fd=raw_open(path,flags,*args,**kwargs)
    expected=identity(os.fstat(fd))
    if identity(p.stat(follow_symlinks=False))!=expected:
        raw_close(fd);raise AssertionError('OPENED_FILE_IDENTITY')
    registered[fd]=(p,expected)
    return fd
def tracked_close(fd):
    registered.pop(fd,None)
    return raw_close(fd)
class TrackedStream:
    def __init__(self,stream,fd):self.stream,self.fd=stream,fd
    def __getattr__(self,name):return getattr(self.stream,name)
    def __enter__(self):return self
    def close(self):
        registered.pop(self.fd,None)
        return self.stream.close()
    def __exit__(self,*args):self.close()
def tracked_fdopen(fd,*args,**kwargs):
    # Raw fdopen emits the audit event; only its registered identity is admitted.
    return TrackedStream(raw_fdopen(fd,*args,**kwargs),fd)
sys.addaudithook(audit)
os.open,os.close,os.fdopen=tracked_open,tracked_close,tracked_fdopen
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def timeout(*_):raise AssertionError('WALL_CAP')
signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
assert hashlib.sha256(CODE.read_bytes()).hexdigest()=='a00f661e92e79a1ad3ff4010c7a55aeb2d196f2a59232e24d74dc4c19195b2ef'
assert hashlib.sha256(TEST.read_bytes()).hexdigest()=='01e61c98e99789790de7354f542860de123c3c79304e0faa63d5a6b40d0f15ea'
ns=runpy.run_path(str(TEST),run_name='independent_mock_definitions')
m=ns['m'];MockAPI=ns['MockAPI'];findings=[]
pure=m.own_module(m.PURE_REF,'independent_pure')
base=m.own_module(m.POLICY_REF,'independent_original_policy')
budget=m.SharedBudget(pure);policy=m.policy_class(base.GuestPolicy)(Path('/SSL_INDEPENDENT_MOCK'),budget)
policy.phase_set('TOOL_LOAD')
before=policy.violations
try:policy.audit('compile',(b'# fabricated event, not compiled', '<string>'))
except base.Refused:
    assert policy.violations==before+1
else:raise AssertionError('EXPECTED_ORIGINAL_COMPILE_REFUSAL')
findings.append({'id':'F01','observed':'Original callback refuses fabricated dataclass-style <string> compile in TOOL_LOAD','original_counter_delta':policy.violations-before,'actual_third_party_code_compiled':False})

class CaughtCapAPI(MockAPI):
    def __init__(self,kind):super().__init__();self.kind=kind;self.caught=[]
    def install(self,source,destination,additional_metadata):
        fs,prefix=destination
        if self.calls==0:
            shared=fs.policy.shared
            try:getattr(shared,self.kind)(33554432)
            except m.HarnessRefused as error:self.caught.append(error.code)
            else:raise AssertionError('EXPECTED_CAP_REFUSAL')
            assert shared.failed
        return super().install(source,destination,additional_metadata)
for kind in ('read','write'):
    api=CaughtCapAPI(kind);result=m.drive_mock(api);terminal=result['terminal']
    assert api.caught==['FIXTURE_'+kind.upper()+'_CAP']
    assert terminal['outcome']=='FIXTURE_ASSERTIONS_PASS_ONLY'
    assert terminal['usage']['failed'] is True
    assert len(terminal['cases'])==8 and api.calls==3
    findings.append({'id':'F02','kind':kind,'caught_codes':api.caught,'outcome':terminal['outcome'],'usage':terminal['usage'],'mock_calls':api.calls,'completed_cases':len(terminal['cases']),'terminal_sha256':result['terminal_ref']['sha256']})
signal.setitimer(signal.ITIMER_REAL,0)
receipt={'kind':'INDEPENDENT_ADVERSE_MOCK_PROBE','status':'CONFIRMED_TWO_BLOCKERS','Python':sys.version,'findings':findings,'late_meter_read_bytes':reads,'OS_writes':0,'registered_descriptors_remaining':len(registered),'actual_tool_imports':0,'actual_tool_compilations':0,'actual_installs':0,'cost_USD':0}
output=json.dumps(receipt,sort_keys=True)+'\n';assert len(output.encode())<262144
sys.stdout.write(output)
