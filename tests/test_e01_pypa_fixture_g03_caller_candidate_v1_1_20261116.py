"""Authored inert supervisor/caller checks. No child/tool/hooks/OS writes."""
import sys

def early_guard():
    def audit(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:
            raise AssertionError('G03_AUTHOR_NO_PROCESS_NETWORK_NATIVE')
        if event=='import' and args and args[0].split('.')[0] in {'installer','pip','ssl_fixture_payload','pypdf','PIL','cryptography','cffi','_cffi_backend'}:
            raise AssertionError('G03_AUTHOR_NO_TOOL_OR_PAYLOAD')
    sys.addaudithook(audit)
if __name__=='__main__':early_guard()

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import unittest

ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/'scripts/e01_pypa_fixture_g03_caller_candidate_v1_1_20261116.py'

def load_own(name,path):
    path=Path(path).resolve();raw=path.read_bytes()
    if path not in {CODE,Path(__file__).resolve()} or len(raw)>131072:raise AssertionError('G03_AUTHOR_OWN_SOURCE_ONLY')
    spec=importlib.util.spec_from_loader(name,loader=None,origin=str(path));module=importlib.util.module_from_spec(spec);module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__);return module
m=load_own('g03_author_candidate',CODE)

class Clock:
    def __init__(self):self.value=0.0
    def __call__(self):return self.value

class FakeBackend:
    mock_only=True
    def __init__(self,clock,events=None,*,step=.05,exit_after=1,returncode=0,cpu=.1,never_reap=False):
        self.clock=clock;self.events=list(events or []);self.step=step;self.exit_after=exit_after;self.returncode=returncode;self.cpu=cpu
        self.never_reap=never_reap;self.started=False;self.output_complete=False;self.kills=0;self.starts=0;self.drains=0;self.closes=0
        self.command=None;self.environment=None
    def start(self,command,environment):
        self.starts+=1;self.started=True;self.command=command;self.environment=environment
    def drain(self,timeout):
        self.drains+=1;self.clock.value+=self.step
        result=self.events.pop(0) if self.events else []
        self.output_complete=not self.events;return result
    def wait_nonblock(self):
        if self.never_reap:return None
        if self.kills or self.drains>=self.exit_after:
            return {'reaped':True,'returncode':-9 if self.kills else self.returncode,
                'CPU_user_seconds':self.cpu,'CPU_system_seconds':.01}
        return None
    def kill_once(self):self.kills+=1
    def pause(self,seconds):self.clock.value+=seconds
    def close(self):self.closes+=1


def authored_context():
    packet=m.preparation_packet({'path':m.CODE,'bytes':1,'sha256':'0'*64})
    packet.update(state='EXACT_FROZEN_CHILD_CANDIDATE',temp_parent='/SSL_G03_AUTHORED_PARENT',
        gates={name:'PASS_EXACT_REVIEWED_BOUNDARY' for name in m.GATES},
        child_adapter_ref={'path':'scripts/e01_pypa_fixture_g03_child_AUTHORED_MOCK.py','bytes':1,'sha256':'1'*64},
        startup_closure_ref={'path':'reports/evidence_e01_pypa_fixture_g03_AUTHORED/closure.json','bytes':1,'sha256':'2'*64},
        child_guard_review_ref={'path':'reports/INDEPENDENT_AUDIT_AUTHORED_MOCK.json','bytes':1,'sha256':'3'*64},
        harness_release_ref={'path':'data/processed/e01_pypa_fixture_release_v1_1_20261116/AUTHORED_MOCK.json','bytes':1,'sha256':'4'*64})
    release={'kind':'E01_G03_EXACT_ONE_CHILD_RELEASE_V1','enabled':True,'packet_sha256':m.digest(m.packed(packet)),
        'scope':m.SCOPE,'maximum_children':1,'retries':0}
    review={'decision':'PASS_EXACT_G03_CALLER_PACKET_CHILD_CLOSURE','packet_sha256':m.digest(m.packed(packet)),
        'release_core_sha256':m.digest(m.packed(release)),'caller_ref':packet['caller_ref'],'gates':packet['gates']}
    return packet,release,review


class PacketAndAuthorityTests(unittest.TestCase):
    def test_preparation_is_disabled_and_all_boundaries_blocked(self):
        p=m.preparation_packet({'path':m.CODE,'bytes':1,'sha256':'0'*64});m.validate_packet(p)
        self.assertFalse(p['execution_enabled']);self.assertEqual(len(p['gates']),7)
        self.assertTrue(all(v=='BLOCKED_MISSING_EVIDENCE' for v in p['gates'].values()))
        with self.assertRaises(m.Refused):m.validate_packet(p,operational=True)
    def test_actual_entry_always_refuses_without_touching_arguments(self):
        class Poison:
            def __getattribute__(self,name):raise AssertionError('ACTUAL_ARGUMENT_ACCESSED')
        with self.assertRaisesRegex(m.Refused,'G03_ACTUAL_ENTRY_BLOCKED'):m.run_actual(Poison(),enabled=True)
    def test_exact_mock_packet_release_review_bind(self):
        p,r,v=authored_context();m.validate_release(p,r,v)
        self.assertFalse(p['execution_enabled']);self.assertTrue(r['enabled'])
    def test_every_pending_gate_refuses_before_mock_start_or_marker(self):
        for gate in m.GATES:
            p,r,v=authored_context();p['gates'][gate]='NOT_RUN';clock=Clock();b=FakeBackend(clock);j=m.MemoryJournal()
            with self.assertRaisesRegex(m.Refused,'G03_PENDING_BOUNDARIES'):m.run_mock(p,r,v,b,j,clock=clock)
            self.assertEqual(b.starts,0);self.assertEqual(j.files,{})
    def test_missing_child_closure_review_and_harness_release_refuse(self):
        for field in ('child_adapter_ref','startup_closure_ref','child_guard_review_ref','harness_release_ref'):
            p,r,v=authored_context();p[field]=None
            with self.assertRaises(m.Refused):m.validate_release(p,r,v)
    def test_runtime_limits_source_and_root_drift_refuse(self):
        for field,value in (('runtime',{}),('limits',{}),('harness_ref',{}),('root_sha256','x'),('tool_ref',{}),('component_review_ref',{})):
            p,r,v=authored_context();p[field]=value
            with self.assertRaises(m.Refused):m.validate_release(p,r,v)
    def test_release_and_review_drift_refuse(self):
        for field,value in (('enabled',False),('maximum_children',2),('retries',1),('packet_sha256','0'*64)):
            p,r,v=authored_context();r[field]=value
            with self.assertRaises(m.Refused):m.validate_release(p,r,v)
        p,r,v=authored_context();v['decision']='PASS_COMPONENT_ONLY'
        with self.assertRaises(m.Refused):m.validate_release(p,r,v)
    def test_paths_and_environment_have_no_site_keys_or_paid_enable(self):
        p,r,v=authored_context();cmd,env=m.command_and_env(p,ROOT/'MOCK_PACKET.json','a'*64)
        self.assertEqual(cmd[1:4],['-I','-B','-S']);self.assertIn('-X',cmd)
        self.assertTrue(cmd[5].startswith('pycache_prefix=/SSL_G03_AUTHORED_PARENT/'))
        self.assertEqual(env['MAX_SPEND_USD'],'0');self.assertEqual(env['PAID_API_ENABLED'],'false')
        self.assertNotIn('OPENROUTER_API_KEY',env);self.assertNotIn('PYTHONPATH',env);self.assertNotIn('VIRTUAL_ENV',env)
    def test_only_first_312_runtime_and_partitioned_caps(self):
        self.assertEqual(m.RUNTIME['version'],'3.12.14');self.assertEqual(m.LIMITS['children'],1)
        self.assertEqual(m.LIMITS['child_write_bytes']+m.LIMITS['parent_write_bytes'],m.LIMITS['combined_write_bytes'])
        self.assertEqual(m.LIMITS['work_seconds']+m.LIMITS['cleanup_reserve_seconds'],120)
    def test_reject_nonmock_backend_or_nonmemory_journal(self):
        p,r,v=authored_context()
        with self.assertRaisesRegex(m.Refused,'G03_MOCK_BACKEND_REQUIRED'):m.run_mock(p,r,v,object())
        with self.assertRaisesRegex(m.Refused,'G03_MEMORY_JOURNAL_REQUIRED'):m.run_mock(p,r,v,FakeBackend(Clock()),object())


class OneShotAndSupervisorTests(unittest.TestCase):
    def run_flow(self,backend,clock,journal=None):return m.run_mock(*authored_context(),backend,journal,clock=clock)
    def test_one_shot_marker_precedes_start_and_replay_refuses(self):
        clock=Clock();j=m.MemoryJournal()
        class VerifyMarker(FakeBackend):
            def start(self,*args):
                if 'STARTED.json' not in j.files:raise AssertionError('NO_MARKER')
                return super().start(*args)
        b=VerifyMarker(clock);result,j=self.run_flow(b,clock,j)
        self.assertEqual(result['spawn_attempts'],1);self.assertTrue(result['reaped']);self.assertEqual(result['status'],'CAPTURED_PARENT_ONLY')
        self.assertFalse(result['G03_acceptance']);self.assertFalse(result['actual_fixture_acceptance'])
        before=dict(j.files)
        with self.assertRaisesRegex(m.Refused,'G03_SPENT_SCOPE'):self.run_flow(b,clock,j)
        self.assertEqual(b.starts,1);self.assertEqual(j.files,before)
    def test_whole_child_cpu_and_wall_observed_from_before_start(self):
        clock=Clock()
        class Bootstrap(FakeBackend):
            def start(self,*args):clock.value+=2;return super().start(*args)
        result,j=self.run_flow(Bootstrap(clock,cpu=3),clock)
        self.assertGreaterEqual(result['wall_seconds_start_to_cleanup'],2);self.assertEqual(result['CPU_seconds_whole_child_observed'],3.01)
    def test_drain_continues_after_exit_until_all_buffered_output_complete(self):
        clock=Clock();b=FakeBackend(clock,events=[[('stdout',b'A'*65536)],[('stdout',b'B'*65536)],[('stderr',b'C')]],exit_after=1)
        result,j=self.run_flow(b,clock)
        self.assertEqual(b.drains,3);self.assertEqual(j.files['STDOUT.bin'],b'A'*65536+b'B'*65536)
        self.assertEqual(j.files['STDERR.bin'],b'C');self.assertEqual(result['console_retained_bytes'],131073)
    def test_console_cap_retains_bounded_prefix_and_refuses(self):
        clock=Clock();b=FakeBackend(clock,events=[[('stdout',b'A'*65536)] for _ in range(5)],exit_after=100)
        result,j=self.run_flow(b,clock)
        self.assertEqual(result['reason'],'CONSOLE_CAP');self.assertEqual(b.kills,1)
        self.assertEqual(result['console_retained_bytes'],262144);self.assertEqual(result['console_observed_bytes'],327680)
        self.assertEqual(len(j.files['STDOUT.bin']),262144)
    def test_117_second_work_stop_kills_once_and_reaps_within_120(self):
        clock=Clock();b=FakeBackend(clock,step=117,exit_after=100)
        result,j=self.run_flow(b,clock)
        self.assertEqual(result['reason'],'WORK_WALL_CAP');self.assertEqual(b.kills,1);self.assertTrue(result['reaped'])
        self.assertLessEqual(result['wall_seconds_start_to_cleanup'],120)
    def test_child_exit_and_cpu_overrun_never_return_success(self):
        for kwargs,reason in (({'returncode':1},'CHILD_EXIT_NONZERO'),({'cpu':121},'CPU_CAP_OBSERVED')):
            clock=Clock();result,j=self.run_flow(FakeBackend(clock,**kwargs),clock)
            self.assertEqual(result['reason'],reason);self.assertEqual(result['status'],'FAILED_UNACCEPTED')
    def test_unreaped_child_remains_explicit_failure(self):
        clock=Clock();b=FakeBackend(clock,step=117,exit_after=100,never_reap=True)
        result,j=self.run_flow(b,clock)
        self.assertEqual(result['reason'],'UNREAPED_CHILD');self.assertFalse(result['reaped']);self.assertEqual(b.kills,1)
        self.assertIsNone(result['CPU_seconds_whole_child_observed'])
    def test_start_failure_consumes_scope_and_preserves_primary(self):
        primary=RuntimeError('AUTHORED_ERROR_NOT_FOR_REPORT');clock=Clock();j=m.MemoryJournal()
        class Fail(FakeBackend):
            def start(self,*args):self.starts+=1;raise primary
        b=Fail(clock)
        with self.assertRaises(RuntimeError) as caught:self.run_flow(b,clock,j)
        self.assertIs(caught.exception,primary);self.assertIn('STARTED.json',j.files);self.assertIn('FAILURE.json',j.files)
        self.assertNotIn(b'AUTHORED_ERROR_NOT_FOR_REPORT',j.files['FAILURE.json'])
    def test_primary_survives_kill_close_and_failure_receipt_errors(self):
        primary=RuntimeError('AUTHORED_PRIMARY');clock=Clock()
        class Fail(FakeBackend):
            def drain(self,*args):raise primary
            def kill_once(self):raise OSError('SECONDARY_KILL')
            def close(self):raise ValueError('SECONDARY_CLOSE')
        class BrokenJournal(m.MemoryJournal):
            def new(self,name,raw):
                if name=='FAILURE.json':raise OSError('SECONDARY_STORAGE')
                return super().new(name,raw)
        p,r,v=authored_context();j=BrokenJournal()
        with self.assertRaises(RuntimeError) as caught:m._one_shot(p,r,v,Fail(clock),j,clock=clock)
        self.assertIs(caught.exception,primary);self.assertIn('STARTED.json',j.files)
    def test_partial_output_is_retained_when_later_drain_raises(self):
        primary=RuntimeError('AUTHORED_DRAIN_FAILURE');clock=Clock();j=m.MemoryJournal()
        class Fail(FakeBackend):
            def drain(self,*args):
                if self.drains:raise primary
                return super().drain(*args)
        b=Fail(clock,events=[[('stdout',b'AUTHORED_PARTIAL')]],exit_after=100)
        with self.assertRaises(RuntimeError) as caught:self.run_flow(b,clock,j)
        self.assertIs(caught.exception,primary);self.assertEqual(j.files['STDOUT.bin'],b'AUTHORED_PARTIAL')
        self.assertIn('FAILURE.json',j.files)
    def test_final_clock_failure_does_not_replace_first_clock_exception(self):
        primary=RuntimeError('AUTHORED_FIRST_CLOCK');secondary=ValueError('AUTHORED_FINAL_CLOCK')
        class FailingClock(Clock):
            def __init__(self):super().__init__();self.calls=0
            def __call__(self):
                self.calls+=1
                if self.calls==2:raise primary
                if self.calls>2:raise secondary
                return 0.0
        clock=FailingClock();j=m.MemoryJournal()
        with self.assertRaises(RuntimeError) as caught:self.run_flow(FakeBackend(clock),clock,j)
        self.assertIs(caught.exception,primary);self.assertIn('FAILURE.json',j.files)
    def test_invalid_wait_cpu_is_rejected_and_preserved(self):
        clock=Clock();j=m.MemoryJournal()
        class Bad(FakeBackend):
            def wait_nonblock(self):return {'reaped':True,'returncode':0,'CPU_user_seconds':float('nan'),'CPU_system_seconds':0}
        with self.assertRaisesRegex(m.Refused,'G03_WAIT_RECEIPT'):self.run_flow(Bad(clock),clock,j)
        self.assertIn('FAILURE.json',j.files)
    def test_poll_bound_prevents_nonadvancing_clock_loop(self):
        clock=Clock();b=FakeBackend(clock,step=0,exit_after=10000)
        result,j=self.run_flow(b,clock)
        self.assertEqual(result['reason'],'POLL_CAP');self.assertEqual(b.drains,2500);self.assertEqual(b.kills,1)
    def test_bad_or_oversized_chunks_refuse_without_unbounded_capture(self):
        for events in ([[('stdout',b'A'*65537)]],[ [('WRONG',b'MOCK')] ]):
            clock=Clock();b=FakeBackend(clock,events=events,exit_after=100);j=m.MemoryJournal()
            with self.assertRaises(m.Refused):self.run_flow(b,clock,j)
            self.assertEqual(b.kills,1);self.assertLessEqual(sum(map(len,j.files.values())),1048576)
    def test_memory_journal_is_exclusive_and_capped(self):
        j=m.MemoryJournal();j.new('STDOUT.bin',b'A')
        with self.assertRaisesRegex(m.Refused,'G03_SPENT_SCOPE'):j.new('STDOUT.bin',b'B')
        with self.assertRaisesRegex(m.Refused,'G03_PARENT_WRITE_CAP'):j.new('STDERR.bin',b'A'*1048576)
        with self.assertRaisesRegex(m.Refused,'G03_RECORD_NAME'):j.new('../OUTSIDE',b'A')


class PostDrainDeadlineRemedyTests(unittest.TestCase):
    def flow(self,backend,clock,journal=None):return m.run_mock(*authored_context(),backend,journal,clock=clock)
    def test_matched_final_drain_work_and_total_boundaries(self):
        rows=[]
        for edge,expected in ((116.999,None),(117.0,'WORK_WALL_CAP'),(118.0,'WORK_WALL_CAP'),
                              (120.0,'WORK_WALL_CAP'),(120.5,'TOTAL_WALL_CAP_OBSERVED')):
            clock=Clock();b=FakeBackend(clock,events=[[('stdout',b'AUTHORED_FINAL_DRAIN')]],step=edge,exit_after=1)
            result,j=self.flow(b,clock)
            self.assertEqual(result['reason'],expected);self.assertTrue(result['reaped']);self.assertEqual(b.kills,0)
            self.assertEqual(result['status'],'CAPTURED_PARENT_ONLY' if expected is None else 'FAILED_UNACCEPTED')
            self.assertEqual(j.files['STDOUT.bin'],b'AUTHORED_FINAL_DRAIN');self.assertEqual(b.closes,1)
            self.assertFalse(result['G03_acceptance']);self.assertFalse(result['actual_fixture_acceptance'])
            rows.append({'edge':edge,'reason':result['reason'],'status':result['status'],'fake_kills':b.kills,
                'reaped':result['reaped'],'elapsed':result['wall_seconds_start_to_cleanup']})
        print(json.dumps({'kind':'G03_V1_1_MATCHED_POST_DRAIN_BOUNDARIES','rows':rows,'actual_children':0},sort_keys=True))
    def test_wait_itself_crossing_threshold_is_sampled_before_capture(self):
        for wait_advance,expected in ((.499,None),(.5,'WORK_WALL_CAP'),(1.5,'WORK_WALL_CAP')):
            clock=Clock()
            class WaitDelay(FakeBackend):
                def wait_nonblock(self):
                    value=super().wait_nonblock();self.clock.value+=wait_advance;return value
            result,j=self.flow(WaitDelay(clock,step=116.5),clock)
            self.assertEqual(result['reason'],expected);self.assertTrue(result['reaped'])
    def test_crossing_threshold_while_unreaped_kills_once_and_preserves_output(self):
        clock=Clock();b=FakeBackend(clock,events=[[('stdout',b'AUTHORED_PARTIAL')]],step=117,exit_after=100)
        result,j=self.flow(b,clock)
        self.assertEqual(result['reason'],'WORK_WALL_CAP');self.assertEqual(b.kills,1);self.assertTrue(result['reaped'])
        self.assertEqual(j.files['STDOUT.bin'],b'AUTHORED_PARTIAL');self.assertEqual(b.drains,1)
        self.assertLessEqual(result['wall_seconds_start_to_cleanup'],120)
    def test_existing_console_refusal_is_not_replaced_by_work_threshold(self):
        clock=Clock();b=FakeBackend(clock,events=[[('stdout',b'A'*65536)] for _ in range(5)],step=23.4,exit_after=100)
        result,j=self.flow(b,clock)
        self.assertEqual(result['reason'],'CONSOLE_CAP');self.assertEqual(b.kills,1)
        self.assertEqual(len(j.files['STDOUT.bin']),262144)
    def test_post_wait_clock_exception_survives_final_clock_and_close_errors(self):
        primary=RuntimeError('AUTHORED_POST_WAIT_PRIMARY');secondary=ValueError('AUTHORED_FINAL_CLOCK')
        class PostWaitClock(Clock):
            def __init__(self):super().__init__();self.calls=0
            def __call__(self):
                self.calls+=1
                if self.calls==3:raise primary
                if self.calls>3:raise secondary
                return self.value
        class CloseError(FakeBackend):
            def close(self):self.closes+=1;raise OSError('AUTHORED_CLOSE_SECONDARY')
        clock=PostWaitClock();b=CloseError(clock,events=[[('stdout',b'AUTHORED_POST_WAIT')]])
        j=m.MemoryJournal()
        with self.assertRaises(RuntimeError) as caught:self.flow(b,clock,j)
        self.assertIs(caught.exception,primary);self.assertEqual(b.closes,1);self.assertEqual(b.kills,0)
        self.assertEqual(j.files['STDOUT.bin'],b'AUTHORED_POST_WAIT');self.assertIn('FAILURE.json',j.files)
        self.assertNotIn(b'AUTHORED_POST_WAIT_PRIMARY',j.files['FAILURE.json'])
    def test_post_wait_clock_regression_refuses_reaped_capture(self):
        clock=Clock()
        class Regress(FakeBackend):
            def wait_nonblock(self):
                value=super().wait_nonblock();self.clock.value=-1;return value
        j=m.MemoryJournal();b=Regress(clock)
        with self.assertRaisesRegex(m.Refused,'G03_CLOCK_REGRESSION'):self.flow(b,clock,j)
        self.assertIn('FAILURE.json',j.files);self.assertEqual(b.kills,0)
    def test_reaped_cleanup_at120_retains_work_failure_above120_total_failure(self):
        for delay,expected in ((3.0,'WORK_WALL_CAP'),(3.5,'TOTAL_WALL_CAP_OBSERVED')):
            clock=Clock()
            class CloseDelay(FakeBackend):
                def close(self):self.clock.value+=delay;super().close()
            result,j=self.flow(CloseDelay(clock,step=117),clock)
            self.assertEqual(result['reason'],expected);self.assertEqual(result['status'],'FAILED_UNACCEPTED')
            self.assertTrue(result['reaped'])


class CollectionAndSafetyTests(unittest.TestCase):
    def test_import_installs_no_hooks_limits_or_child(self):
        calls=[];original=(sys.addaudithook,signal.signal,resource.setrlimit)
        try:
            sys.addaudithook=lambda *args:calls.append('AUDIT');signal.signal=lambda *args:calls.append('SIGNAL')
            resource.setrlimit=lambda *args:calls.append('RESOURCE')
            load_own('ordinary_g03_collection',Path(__file__));self.assertEqual(calls,[])
        finally:sys.addaudithook,signal.signal,resource.setrlimit=original
    def test_candidate_imports_no_tool_or_harness(self):
        tree=ast.parse(CODE.read_bytes())
        for node in tree.body:
            if isinstance(node,ast.Import):self.assertFalse(any(a.name.split('.')[0] in {'installer','pip','subprocess'} for a in node.names))
            if isinstance(node,ast.ImportFrom):self.assertFalse((node.module or '').startswith(('installer','pip')))
        self.assertNotIn('installer',sys.modules)
    def test_actual_entry_is_explicitly_blocked_not_silent_mock_fallback(self):
        tree=ast.parse(CODE.read_bytes());entry=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_actual')
        self.assertEqual(sum(isinstance(n,ast.Raise) for n in ast.walk(entry)),1)
        self.assertNotIn('run_mock',ast.unparse(entry))


def guarded_main():
    reads=[0];console=[0];stdlib=Path(sys.base_prefix)/'lib';allowed={CODE,Path(__file__).resolve()}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.path.realpath(args[0]));flags=args[2]
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('G03_AUTHOR_NO_OS_WRITES')
            if not(p in allowed or(p.is_relative_to(stdlib) and 'site-packages' not in p.parts)):raise AssertionError('G03_AUTHOR_READ_SCOPE')
            try:size=p.stat().st_size
            except FileNotFoundError:size=0
            reads[0]+=size+1
            if reads[0]>67108864:raise AssertionError('G03_AUTHOR_READ_CAP')
        if event in {'os.mkdir','os.rename','os.remove','os.rmdir','os.symlink','os.link','os.chmod','os.truncate'}:raise AssertionError('G03_AUTHOR_NO_MUTATION')
    sys.addaudithook(audit)
    class Output:
        def __init__(self,stream):self.stream=stream
        def __getattr__(self,name):return getattr(self.stream,name)
        def write(self,value):
            console[0]+=len(value.encode())
            if console[0]>262144:raise AssertionError('G03_AUTHOR_CONSOLE_CAP')
            return self.stream.write(value)
    sys.stdout=Output(sys.stdout);sys.stderr=Output(sys.stderr)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    def stop(*_):raise AssertionError('G03_AUTHOR_WALL_CAP')
    signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,120)
    p=unittest.main(failfast=True,verbosity=2,exit=False)
    print(json.dumps({'kind':'G03_AUTHOR_INERT_SUITE','checks':p.result.testsRun,'late_read_bytes':reads[0],
        'console_bytes_before_summary':console[0],'actual_children':0,'actual_tool_imports_compiles_installs':0,
        'OS_writes':0,'G03_actual_integration':'NOT_RUN','startup_reads_not_metered':True},sort_keys=True))
    raise SystemExit(0 if p.result.wasSuccessful() else 1)
if __name__=='__main__':guarded_main()
