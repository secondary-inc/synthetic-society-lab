"""One reviewed3.11-only MOCK continuation; no actual research/owner/model work."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
BASE='data/processed/e02_wrapper_crossmodel_v1_20261115_authored_03_python311'
FIXTURE='data/processed/e02_wrapper_crossmodel_v1_20261115_authored_02_python312/prefix'
FIXTURE_SHA='62f4633ea61fe04789ed247d55480bfb3165d8a7cafe9a0daf5e7f297e9a2798'
TESTS=('test_wrapper_crossmodel_v1_pure_20261115','test_wrapper_crossmodel_v1_controls_20261115',
       'test_wrapper_crossmodel_v1_caller_20261115','test_wrapper_crossmodel_v1_execution_20261115')
class Stop(RuntimeError):pass

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')

def bounded_read(path,limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>limit:raise Stop('INPUT_TYPE_SIZE')
        with os.fdopen(fd,'rb') as stream:
            fd=None;raw=stream.read(limit+1)
        if len(raw)!=info.st_size or len(raw)>limit:raise Stop('INPUT_CHANGED')
        return raw
    finally:
        if fd is not None:os.close(fd)


class ClockBudget:
    def __init__(self,mono=time.monotonic,utc=time.time,seconds=3600,output_cap=1048576):
        self.mono,self.utc,self.seconds,self.output_cap=mono,utc,seconds,output_cap
        self.start_m,self.start_u=mono(),utc();self.last_m,self.last_u=self.start_m,self.start_u;self.output=0
        self.check()
    def check(self):
        m,u=self.mono(),self.utc()
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (m,u,self.start_m,self.start_u)):
            raise Stop('CLOCK_NONFINITE')
        if m<self.last_m or u<self.last_u:raise Stop('CLOCK_ROLLBACK')
        dm,du=m-self.start_m,u-self.start_u
        if dm>=self.seconds or du>=self.seconds:raise Stop('DUAL_CLOCK_DEADLINE')
        if abs(dm-du)>2:raise Stop('CLOCK_DISCONTINUITY')
        self.last_m,self.last_u=m,u
        return {'monotonic_seconds':dm,'UTC_seconds':du}
    def consume(self,n):
        if type(n) is not int or n<0 or self.output+n>self.output_cap:raise Stop('OUTPUT_CAP')
        self.output+=n

def stop_child(process,killpg=os.killpg):
    if process.poll() is None:
        try:killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    try:return process.wait(timeout=5)
    except subprocess.TimeoutExpired:raise Stop('CHILD_REAP_UNKNOWN') from None

def capture(process,log,budget,selector_factory=selectors.DefaultSelector,read=os.read,killpg=os.killpg):
    selector=selector_factory();selector.register(process.stdout,selectors.EVENT_READ);reason=None
    try:
        while selector.get_map():
            budget.check()
            for key,_ in selector.select(.1):
                budget.check();chunk=read(key.fileobj.fileno(),65536)
                if not chunk:selector.unregister(key.fileobj);continue
                budget.consume(len(chunk));log.write(chunk);log.flush()
        budget.check()
        try:process.wait(timeout=.1)
        except subprocess.TimeoutExpired:
            while process.poll() is None:
                budget.check();time.sleep(.05)
        budget.check()
    except BaseException as error:
        reason=str(error) if type(error) is Stop else type(error).__name__
        try:stop_child(process,killpg)
        except Stop as reaping:reason+=';'+str(reaping)
    finally:selector.close();process.stdout.close()
    return {'exit_code':process.returncode,'stop_reason':reason,'captured_bytes':budget.output}

def contract():
    paths=['configs/e02_wrapper_crossmodel_v1_20261115.json',
        *[str(p.relative_to(ROOT)) for p in sorted((ROOT/'src/civiclab/e02').glob('wrapper_crossmodel_v1*.py'))],
        'scripts/run_wrapper_crossmodel_v1_20261115_once.py','scripts/run_wrapper_crossmodel_v1_authored_utc_20261116.py',
        *[str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests').glob('*wrapper_crossmodel_v1*20261115.py'))],
        'tests/test_wrapper_crossmodel_v1_clock_runner_20261116.py']
    return {p:{'bytes':(ROOT/p).stat().st_size,'sha256':sha(ROOT/p)} for p in paths}

def preserve_partial(base):
    # Child writes this trusted authored-only scope before tests; no broad scan.
    scope_file=base/'active-authored-scope.json'
    if not scope_file.exists():return {'status':'NO_CHILD_SCOPE_RETAINED'}
    if scope_file.is_symlink() or scope_file.stat().st_size>4096:raise Stop('PARTIAL_SCOPE_REFUSED')
    scope=json.loads(bounded_read(scope_file,4096));home=Path(scope['home'])
    if (scope.get('kind')!='MOCK_AUTHORED_ACTIVE_SCOPE' or not home.is_absolute()
        or home!=home.resolve() or home.name!='AUTHORED_OS_HOME'
        or any(p.is_symlink() for p in (home,*home.parents))):raise Stop('PARTIAL_SCOPE_REFUSED')
    if not home.exists():return {'status':'CHILD_SCOPE_ALREADY_CLEANED'}
    directory=Path(scope['directory'])
    if not directory.is_relative_to(home):raise Stop('PARTIAL_SCOPE_REFUSED')
    if json.loads(bounded_read(directory/'owner-v4-guard.local.json',4096))!=scope['owner_header']:
        raise Stop('PARTIAL_GUARD_REFUSED')
    import shutil
    target=base/'STOPPED_PARTIAL_AUTHORED_HOME';shutil.copytree(home,target,symlinks=True)
    return {'status':'PARTIAL_MOCK_HOME_RETAINED_UNVERIFIED','path':str(target.relative_to(ROOT)),
            'source_retained':True}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reviewed-contract-sha256',required=True)
    args=parser.parse_args();pins=contract();raw=json.dumps(pins,sort_keys=True,separators=(',',':')).encode()
    if hashlib.sha256(raw).hexdigest()!=args.reviewed_contract_sha256:raise Stop('REVIEWED_CONTRACT_REQUIRED')
    fixture=ROOT/FIXTURE
    if hashlib.sha256(bounded_read(fixture/'index.json',1048576)).hexdigest()!=FIXTURE_SHA:raise Stop('FIXTURE_PIN')
    base=ROOT/BASE;base.mkdir(exist_ok=False);budget=ClockBudget()
    command=[str(ROOT/'data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11'),'-B','-m','unittest','-f','-v',*TESTS]
    env={'PATH':os.defpath,'PYTHONPATH':'src:tests','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','PYTHONUNBUFFERED':'1',
         'SSL_WRAPPER_CROSSMODEL_V1_EVIDENCE':str(base),'SSL_WRAPPER_CROSSMODEL_V1_REUSE_PREFIX':str(fixture),
         'SSL_WRAPPER_CROSSMODEL_V1_REUSE_SHA256':FIXTURE_SHA}
    write(base/'STARTED.json',{'kind':'MOCK_REVIEWED_DUAL_CLOCK_311_ONLY','source_pins':pins,'argv':command,
        'UTC_started':datetime.now(timezone.utc).isoformat(),'clock_UTC_start':budget.start_u,'clock_mono_start':budget.start_m,
        'both_deadlines_seconds':3600,'clock_difference_max_seconds':2,'output_bytes_cap':1048576,'retries':0,'actual_model_calls':0})
    process=None;result={}
    try:
        budget.check();process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        with (base/'stdout-stderr.log').open('xb') as log:result=capture(process,log,budget)
        if result['stop_reason'] is not None or result['exit_code']!=0:
            try:result['partial_retention']=preserve_partial(base)
            except BaseException as error:result['partial_retention']={'status':'RETENTION_UNKNOWN','error_type':type(error).__name__}
    except BaseException as error:
        result={'status':'FAILED','reason':str(error) if type(error) is Stop else type(error).__name__}
        if process is not None:
            try:stop_child(process)
            except Stop as reaping:result['reap_error']=str(reaping)
        try:result['partial_retention']=preserve_partial(base)
        except BaseException as copying:result['partial_retention']={'status':'RETENTION_UNKNOWN','error_type':type(copying).__name__}
    du,dm=budget.utc()-budget.start_u,budget.mono()-budget.start_m
    result.update(UTC_ended=datetime.now(timezone.utc).isoformat(),UTC_elapsed=du if math.isfinite(du) else None,
        monotonic_elapsed=dm if math.isfinite(dm) else None,source_pins_unchanged=contract()==pins,actual_model_calls=0,cost_USD=0)
    import re
    raw=(base/'stdout-stderr.log').read_text() if (base/'stdout-stderr.log').exists() else ''
    result['functional_tests_pass']=bool(re.search(r'Ran 21 tests in [0-9.]+s\s+OK\s*$',raw))
    result['status']='PASS' if (result.get('exit_code')==0 and result.get('stop_reason') is None
        and result['functional_tests_pass'] and result['source_pins_unchanged']
        and type(result['UTC_elapsed']) in (int,float) and type(result['monotonic_elapsed']) in (int,float)
        and 0<=result['UTC_elapsed']<3600 and 0<=result['monotonic_elapsed']<3600) else 'FAILED'
    write(base/'RECEIPT.json',result);print(json.dumps(result,sort_keys=True));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
