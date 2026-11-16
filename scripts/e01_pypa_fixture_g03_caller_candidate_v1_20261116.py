"""G03 one-shot parent candidate. No hooks, child or third-party load on import.

The disabled preparation packet lacks a reviewed startup/child guard adapter.
This parent cannot make those gates true. Mock tests never start a real child.
Actual use requires a new exact packet/release/review and missing child adapter.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import sys
import time

ROOT=Path(__file__).absolute().parents[1]
CODE='scripts/e01_pypa_fixture_g03_caller_candidate_v1_20261116.py'
SCOPE='ONE_FRESH_312_GENERATED_FIXTURE_CHILD_G03_V1'
LIMITS={'child_wall_seconds':120,'child_CPU_seconds':120,'technical_read_bytes':67108864,
    'combined_write_bytes':33554432,'child_write_bytes':32505856,'parent_write_bytes':1048576,
    'console_bytes':262144,'cases':8,'fixture_calls':3,'children':1,'retries':0,
    'work_seconds':117,'cleanup_reserve_seconds':3,'polls':2500,'read_chunk_bytes':65536}
GATES=('STARTUP_LOGICAL_READ_BOUND','SOURCE_AND_LOADED_CODE_CLOSURE','FRESH_BYTECODE_CACHE_POLICY',
    'EARLY_NETWORK_IO_COMPILE_GUARD','REAL_AUDIT_STACK_AND_DESCRIPTOR_INTEGRATION',
    'OPERATIONAL_CONTROL_BUDGET_INTEGRATION','EXACT_CHILD_ADAPTER_REVIEW')
HARNESS_REF={'path':'scripts/e01_pypa_fixture_harness_candidate_v1_1_20261116.py','bytes':52778,
 'sha256':'1c55c942b061452f741d1242640fd1b85a8f11b398a30fea6c391525006b20b8'}
COMPONENT_REVIEW={'path':'reports/INDEPENDENT_AUDIT_E01_PYPA_FIXTURE_HARNESS_V1_1_20261116.json','bytes':47690,
 'sha256':'b05c35ca8df6dedf0cb43508a0fd43422efbdccd35c3e7d7aeed4d1597ce88c4'}
RUNTIME={'version':'3.12.14','executable':'/Users/joshua/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12',
 'bytes':18058560,'sha256':'9d1335796350848c36dc2711a3298e096deebee18c85f1ab36edd8747fdf85eb'}
TOOL_REF={'path':'data/processed/e01_installer_tool_source_v1_20261116/2-RESPONSE.bin','bytes':464466,
 'sha256':'f55f5728ff61d3dd54dbc5a397cf3f7307cb64b180c20b72afbebf01c9e2c8a0'}

class Refused(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise Refused(code)
def packed(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def pin_shape(ref):
    return (type(ref) is dict and set(ref)=={'path','bytes','sha256'} and type(ref['path']) is str
        and type(ref['bytes']) is int and 0<=ref['bytes']<=20971520 and type(ref['sha256']) is str
        and len(ref['sha256'])==64 and all(c in '0123456789abcdef' for c in ref['sha256']))
def exact_path(value):
    need(type(value) is str and Path(value).is_absolute() and '..' not in Path(value).parts,'G03_RAW_PATH')
    path=Path(value);need(not any(p.is_symlink() for p in (path,*path.parents)),'G03_PATH_ALIAS');return path


def preparation_packet(caller_ref):
    need(pin_shape(caller_ref) and caller_ref['path']==CODE,'G03_CALLER_PIN')
    return {'kind':'E01_G03_PREPARATION_PACKET_V1','state':'PREPARED_NOT_RELEASED','execution_enabled':False,
        'scope':SCOPE,'root_sha256':digest(str(ROOT).encode()),'limits':dict(LIMITS),'runtime':dict(RUNTIME),
        'caller_ref':caller_ref,'harness_ref':dict(HARNESS_REF),'component_review_ref':dict(COMPONENT_REVIEW),
        'tool_ref':dict(TOOL_REF),'gates':{gate:'BLOCKED_MISSING_EVIDENCE' for gate in GATES},
        'child_adapter_ref':None,'startup_closure_ref':None,'child_guard_review_ref':None,
        'harness_release_ref':None,'temp_parent':None,'no_old_targets':True,
        'scientific_or_runtime_acceptance':False,'network_model_requests':0}


def validate_packet(packet,*,operational=False):
    required=set(preparation_packet({'path':CODE,'bytes':0,'sha256':'0'*64}))
    need(type(packet) is dict and set(packet)==required,'G03_PACKET_SCHEMA')
    need(packet['kind']=='E01_G03_PREPARATION_PACKET_V1' and packet['scope']==SCOPE
        and packet['root_sha256']==digest(str(ROOT).encode()) and packet['limits']==LIMITS
        and packet['runtime']==RUNTIME and packet['harness_ref']==HARNESS_REF
        and packet['component_review_ref']==COMPONENT_REVIEW and packet['tool_ref']==TOOL_REF
        and packet['no_old_targets'] is True and packet['scientific_or_runtime_acceptance'] is False
        and packet['network_model_requests']==0,'G03_PACKET_BINDING')
    need(pin_shape(packet['caller_ref']) and packet['caller_ref']['path']==CODE,'G03_CALLER_PIN')
    need(type(packet['gates']) is dict and set(packet['gates'])==set(GATES),'G03_GATES_SCHEMA')
    if operational:
        need(packet['state']=='EXACT_FROZEN_CHILD_CANDIDATE' and packet['execution_enabled'] is False,'G03_PACKET_IS_NOT_AUTHORITY')
        need(all(value=='PASS_EXACT_REVIEWED_BOUNDARY' for value in packet['gates'].values()),'G03_PENDING_BOUNDARIES')
        for name in ('child_adapter_ref','startup_closure_ref','child_guard_review_ref','harness_release_ref'):
            need(pin_shape(packet[name]),'G03_MISSING_'+name.upper())
        need(packet['child_adapter_ref']['path'].startswith('scripts/e01_pypa_fixture_g03_child_')
             and packet['child_adapter_ref']['path'].endswith('.py'),'G03_CHILD_ADAPTER_PATH')
        need(packet['startup_closure_ref']['path'].startswith('reports/evidence_e01_pypa_fixture_g03_')
             and packet['child_guard_review_ref']['path'].startswith('reports/INDEPENDENT_AUDIT_')
             and packet['harness_release_ref']['path'].startswith('data/processed/e01_pypa_fixture_release_v1_1_20261116/'),
             'G03_CLOSURE_REFERENCE_PATHS')
        path=exact_path(packet['temp_parent'])
        need(not path.is_relative_to(ROOT) and not ROOT.is_relative_to(path),'G03_TEMP_PARENT')
    else:
        need(packet['state']=='PREPARED_NOT_RELEASED' and packet['execution_enabled'] is False,'G03_PREPARATION_ONLY')
    return packet


def validate_release(packet,release,review):
    validate_packet(packet,operational=True)
    need(type(release) is dict and set(release)=={'kind','enabled','packet_sha256','scope','maximum_children','retries'}
        and release=={'kind':'E01_G03_EXACT_ONE_CHILD_RELEASE_V1','enabled':True,'packet_sha256':digest(packed(packet)),
                     'scope':SCOPE,'maximum_children':1,'retries':0},'G03_EXACT_RELEASE_REQUIRED')
    need(type(review) is dict and review.get('decision')=='PASS_EXACT_G03_CALLER_PACKET_CHILD_CLOSURE'
        and review.get('packet_sha256')==digest(packed(packet)) and review.get('release_core_sha256')==digest(packed(release))
        and review.get('caller_ref')==packet['caller_ref'] and review.get('gates')==packet['gates'],'G03_EXACT_PARTICULAR_REVIEW')


def scope_path(packet):
    return Path(packet['temp_parent'])/('ssl-g03-v1-'+packet['root_sha256'][:16]+'-312')
def command_and_env(packet,packet_file,packet_sha256):
    scope=scope_path(packet);cache=scope/'child'/'never-write-bytecode'
    command=[RUNTIME['executable'],'-I','-B','-S','-X','pycache_prefix='+str(cache),
        str(ROOT/packet['child_adapter_ref']['path']),'--g03-packet',str(packet_file),'--g03-packet-sha256',packet_sha256,
        '--owned-scope',str(scope/'child')]
    env={'PATH':os.defpath,'HOME':str(scope/'child'),'TMPDIR':str(scope/'child'),'LANG':'C','LC_ALL':'C','TZ':'UTC',
         'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','PAID_API_ENABLED':'false','MAX_SPEND_USD':'0'}
    return command,env


class MemoryJournal:
    """Authored create-once storage; never creates OS targets."""
    def __init__(self):self.files={};self.used=0
    def new(self,name,raw):
        need(name in {'STARTED.json','STDOUT.bin','STDERR.bin','FINAL.json','FAILURE.json'},'G03_RECORD_NAME')
        need(name not in self.files,'G03_SPENT_SCOPE');need(type(raw) is bytes,'G03_RECORD_BYTES')
        need(self.used+len(raw)<=1048576,'G03_PARENT_WRITE_CAP')
        self.used+=len(raw);self.files[name]=raw
    def exists(self,name):return name in self.files


class DiskJournal:
    """Future exact new external scope only; not instantiated in author tests."""
    def __init__(self,scope):
        self.scope=exact_path(str(scope));need(not self.scope.exists(),'G03_SPENT_SCOPE')
        self.scope.mkdir(mode=0o700,exist_ok=False);(self.scope/'child').mkdir(mode=0o700);self.used=0
    def new(self,name,raw):
        need(name in {'STARTED.json','STDOUT.bin','STDERR.bin','FINAL.json','FAILURE.json'} and type(raw) is bytes,'G03_RECORD_SCHEMA')
        need(self.used+len(raw)<=1048576,'G03_PARENT_WRITE_CAP');self.used+=len(raw)
        path=self.scope/name;fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            need(stream.write(raw)==len(raw),'G03_SHORT_WRITE');stream.flush();os.fsync(stream.fileno())
        fd=os.open(self.scope,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    def exists(self,name):return (self.scope/name).exists()


def _finite(value):return type(value) in {int,float} and not isinstance(value,bool) and math.isfinite(value) and value>=0

def supervise_backend(backend,command,environment,*,clock=time.monotonic):
    """Backend is the only process boundary. Mock tests use inert scripted events.

    Clock starts BEFORE start(). wait4 returns that exact child's whole-lifetime
    CPU, including interpreter startup. Work stops at117s, cleanup by120s.
    The child adapter must independently install CPU/early IO guards; this
    parent's after-reap CPU observation does not itself enforce an early RLIMIT.
    """
    start=previous=clock();need(_finite(start),'G03_CLOCK');out={'stdout':bytearray(),'stderr':bytearray()}
    wait=None;reason=None;primary=None;spawn_attempts=0;kills=0;observed=0
    def now():
        nonlocal previous
        value=clock();need(_finite(value) and value>=previous,'G03_CLOCK_REGRESSION');previous=value;return value
    try:
        spawn_attempts=1;backend.start(command,environment)
        for _ in range(2500):
            if now()-start>=117:reason='WORK_WALL_CAP';break
            events=backend.drain(.05)
            need(type(events) is list and len(events)<=2,'G03_EVENT_BATCH')
            for channel,raw in events:
                need(channel in out and type(raw) is bytes and len(raw)<=65536,'G03_OUTPUT_CHUNK')
                observed+=len(raw);room=max(0,262144-sum(map(len,out.values())))
                out[channel].extend(raw[:room])
                if observed>262144:reason='CONSOLE_CAP';break
            candidate=backend.wait_nonblock()
            if candidate is not None:
                need(type(candidate) is dict and candidate.get('reaped') is True,'G03_WAIT_RECEIPT')
                wait=candidate
            if reason or (wait is not None and backend.output_complete):break
        else:reason='POLL_CAP'
    except BaseException as error:primary=error;reason='SUPERVISOR_PRIMARY_ERROR'
    finally:
        if wait is None and getattr(backend,'started',False):
            try:
                kills=1;backend.kill_once()
                for _ in range(100):
                    wait=backend.wait_nonblock()
                    if wait is not None:break
                    if now()-start>=120:break
                    backend.pause(.01)
            except BaseException as error:
                if primary is None:primary=error
                reason='CLEANUP_ERROR'
        try:backend.close()
        except BaseException as error:
            if primary is None:primary=error
            reason='CLOSE_ERROR'
    reaped=type(wait) is dict and wait.get('reaped') is True
    cpu=None;returncode=None
    try:
        if reaped:
            need(set(wait)=={'reaped','returncode','CPU_user_seconds','CPU_system_seconds'}
                and type(wait['returncode']) is int and _finite(wait['CPU_user_seconds'])
                and _finite(wait['CPU_system_seconds']),'G03_WAIT_RECEIPT')
            cpu=wait['CPU_user_seconds']+wait['CPU_system_seconds'];returncode=wait['returncode']
            if cpu>120:reason='CPU_CAP_OBSERVED'
            elif returncode!=0 and reason is None:reason='CHILD_EXIT_NONZERO'
        else:reason='UNREAPED_CHILD'
    except BaseException as error:
        if primary is None:primary=error
        reason='INVALID_WAIT_RECEIPT'
    try:elapsed=now()-start
    except BaseException as error:
        if primary is None:primary=error
        reason='FINAL_CLOCK_ERROR';elapsed=max(0,previous-start)
    if elapsed>120:reason='TOTAL_WALL_CAP_OBSERVED'
    result={'scope':SCOPE,'spawn_attempts':spawn_attempts,'kill_attempts':kills,'reaped':reaped,'returncode':returncode,
        'CPU_seconds_whole_child_observed':cpu,'wall_seconds_start_to_cleanup':elapsed,'console_observed_bytes':observed,
        'console_retained_bytes':sum(map(len,out.values())),'reason':reason,'status':'CAPTURED_PARENT_ONLY' if reason is None else 'FAILED_UNACCEPTED',
        'actual_fixture_acceptance':False,'G03_acceptance':False}
    backend.failure_result=result;backend.failure_output={channel:bytes(raw) for channel,raw in out.items()}
    if primary is not None:
        # Parent preserves exact exception identity; safe outer receipt reads
        # closed type/code only, never exception args/text/traceback.
        backend.failure_result=result;raise primary
    return result,{channel:bytes(raw) for channel,raw in out.items()}


class PosixBackend:
    """Future native supervisor; never instantiated/called by authored tests."""
    mock_only=False
    def __init__(self):self.started=False;self.process=None;self.selector=None;self.waited=None;self.killed=False
    def start(self,command,environment):
        import selectors
        import subprocess
        need(os.name=='posix' and not self.started,'G03_POSIX_ONE_START')
        self.process=subprocess.Popen(command,env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,cwd=str(ROOT),start_new_session=True,close_fds=True)
        self.started=True;self.output_complete=False;self.selector=selectors.DefaultSelector()
        for channel,stream in [('stdout',self.process.stdout),('stderr',self.process.stderr)]:
            os.set_blocking(stream.fileno(),False);self.selector.register(stream,selectors.EVENT_READ,channel)
    def drain(self,timeout):
        rows=[]
        for key,_ in self.selector.select(timeout):
            raw=os.read(key.fileobj.fileno(),65536)
            if raw:rows.append((key.data,raw))
            else:self.selector.unregister(key.fileobj)
        self.output_complete=not self.selector.get_map()
        return rows
    def wait_nonblock(self):
        if self.waited is not None:return self.waited
        pid,status,usage=os.wait4(self.process.pid,os.WNOHANG)
        if pid:
            self.process.returncode=os.waitstatus_to_exitcode(status)
            self.waited={'reaped':True,'returncode':self.process.returncode,'CPU_user_seconds':usage.ru_utime,'CPU_system_seconds':usage.ru_stime}
        return self.waited
    def kill_once(self):
        need(not self.killed,'G03_KILL_REENTRY');self.killed=True
        if self.wait_nonblock() is None:os.kill(self.process.pid,signal.SIGKILL)
    def pause(self,seconds):time.sleep(seconds)
    def close(self):
        if self.selector is not None:self.selector.close()
        if self.process is not None:
            for stream in (self.process.stdout,self.process.stderr):
                if stream is not None:stream.close()


def _one_shot(packet,release,review,backend,journal,*,clock=time.monotonic):
    validate_release(packet,release,review)
    need(not journal.exists('STARTED.json'),'G03_SPENT_SCOPE')
    journal.new('STARTED.json',packed({'kind':'G03_CONSUMED_BEFORE_START_V1','packet_sha256':digest(packed(packet)),
        'maximum_children':1,'retries':0,'scope':SCOPE,'limits':LIMITS}))
    # Actual reads use a separately hash-bound immutable packet file. Mock
    # execution only passes authored arguments, never opens that path.
    command,environment=command_and_env(packet,ROOT/'data/processed/e01_g03_release_v1/PACKET.json',digest(packed(packet)))
    try:
        result,output=supervise_backend(backend,command,environment,clock=clock)
        for channel in ('stdout','stderr'):journal.new(channel.upper()+'.bin',output[channel])
        journal.new('FINAL.json',packed(result));return result
    except BaseException as primary:
        for channel,raw in getattr(backend,'failure_output',{}).items():
            try:
                name=channel.upper()+'.bin'
                if not journal.exists(name):journal.new(name,raw)
            except BaseException:pass
        record={'kind':'G03_PARENT_FAILURE_V1','scope':SCOPE,'error_type':type(primary).__name__,
            'error_code':primary.code if type(primary) is Refused else 'UNKNOWN_ERROR_TYPE',
            'supervisor':getattr(backend,'failure_result',None),'retry_allowed':False,'G03_acceptance':False}
        try:journal.new('FAILURE.json',packed(record))
        except BaseException:pass
        raise


def run_mock(packet,release,review,backend,journal=None,*,clock=time.monotonic):
    need(getattr(backend,'mock_only',False) is True,'G03_MOCK_BACKEND_REQUIRED')
    journal=MemoryJournal() if journal is None else journal
    need(type(journal) is MemoryJournal,'G03_MEMORY_JOURNAL_REQUIRED')
    return _one_shot(packet,release,review,backend,journal,clock=clock),journal


def run_actual(*args,**kwargs):
    """No actual adapter/release is prepared or qualified in this candidate.

    PosixBackend and DiskJournal remain unexecuted reference integration. The
    current parent packet lacks early guard/loaded-code/startup evidence. A
    separately versioned reviewed concrete entry must connect them only after
    those boundaries are implemented, not turn this refusal into an exception.
    """
    raise Refused('G03_ACTUAL_ENTRY_BLOCKED_MISSING_CHILD_GUARD_AND_STARTUP_CLOSURE')


if __name__=='__main__':
    print(packed({'status':'G03_PREPARATION_ONLY_NO_DISPATCH','actual_child':False,'G03':'BLOCKED'}).decode())
