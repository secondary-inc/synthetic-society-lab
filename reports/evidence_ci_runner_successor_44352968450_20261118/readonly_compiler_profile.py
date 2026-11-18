"""One 60s read-only MOCK compiler profile, no owner or lifecycle execution."""
from pathlib import Path
import cProfile
import importlib.util
import json
import os
import pstats
import resource
import signal
import sys
import sysconfig
import time

ROOT=Path(__file__).resolve().parents[2]


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60))
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(60)
    stdlib=Path(sysconfig.get_path('stdlib')).resolve();charged=[0]
    def guard(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.posix_spawn','os.system','sqlite3.connect','ctypes.dlopen'}:raise AssertionError('PROFILE_READONLY_NO_EXTERNAL')
        if event=='open' and not isinstance(args[0],int):
            path=Path(args[0]).resolve();flags=args[2]
            if path.name.startswith('.env') or 'SyntheticSocietyLab' in str(path):raise AssertionError('PROFILE_NO_OWNER_KEY')
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('PROFILE_NO_WRITES')
            if not(path.is_relative_to(stdlib) or path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'tests') or path.is_relative_to(ROOT/'configs') or path==Path(__file__).resolve()):raise AssertionError('PROFILE_SOURCE_ONLY')
            if path.is_file():charged[0]+=path.stat().st_size
            if charged[0]>67108864:raise AssertionError('PROFILE_READ_BOUND')
    sys.addaudithook(guard);sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
    path=ROOT/'tests/test_wrapper_crossmodel_v1_pure_20261115.py'
    spec=importlib.util.spec_from_file_location('unchanged_pure_compiler_fixture',path)
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    print(json.dumps({'stage':'PURE_BUILD_80_AUTHORED_REQUESTS','owner_calls':0,'network_calls':0}),flush=True)
    profiler=cProfile.Profile();start=time.perf_counter();cpu0=time.process_time();profiler.enable()
    state,requests,rows=fixture.build()
    assert len(requests)==len(rows)==80 and state['status']=='COMPLETE'
    times=[];terms=fixture.terms()
    for prefix in (0,20,40,60,80):
        begin=time.process_time()
        for _ in range(3):fixture.m.next_action(fixture.RAW,terms,fixture.canonical_bytes(rows[:prefix]))
        times.append({'prior_authored_rows':prefix,'calls':3,'CPU_seconds':time.process_time()-begin})
    profiler.disable();stats=pstats.Stats(profiler).stats;hot=[]
    for (file,line,name),(primitive,calls,self_time,cumulative,_) in sorted(stats.items(),key=lambda item:item[1][3],reverse=True)[:18]:
        hot.append({'file':str(Path(file).relative_to(ROOT)) if file.startswith(str(ROOT)) else Path(file).name,
                    'line':line,'function':name,'calls':calls,'self_seconds':self_time,'cumulative_seconds':cumulative})
    print(json.dumps({'kind':'READONLY_AUTHORED_COMPILER_PROFILE','status':'PASS_PROFILE_ONLY','runtime':sys.version.split()[0],
                      'authored_requests_built':80,'sample_prefix_calls':times,'CPU_seconds':time.process_time()-cpu0,
                      'wall_seconds':time.perf_counter()-start,'read_reservation_bytes':charged[0],'hot_cumulative':hot,
                      'owner_calls':0,'actual_lifecycle_runs':0,'model_network_calls':0,'writes':0,'cost_usd':0,
                      'limitation':'Pure compiler scaling only; cProfile overhead, no financial replay/setup/full-lifecycle completion or scientific result.'},sort_keys=True))


if __name__=='__main__':main()
