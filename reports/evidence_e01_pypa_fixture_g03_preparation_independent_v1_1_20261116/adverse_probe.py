"""Independent inert parent contract probes. Native backend paths forbidden."""
import sys
def early(event,args):
    if event.startswith(('socket.','ctypes.')) or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','os.kill','os.killpg'}:
        raise AssertionError('NO_NATIVE_BACKEND_NETWORK_EFFECTS')
    if event=='import' and args and args[0].split('.')[0] in {'installer','pip','ssl_fixture_payload','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:
        raise AssertionError('NO_TOOL_OR_TARGET_IMPORT')
sys.addaudithook(early)
import ast,copy,hashlib,json,os,resource,runpy,signal
from pathlib import Path
ROOT=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
ME=Path(__file__).resolve();CODE=ROOT/'scripts/e01_pypa_fixture_g03_caller_candidate_v1_1_20261116.py'
TEST=ROOT/'tests/test_e01_pypa_fixture_g03_caller_candidate_v1_1_20261116.py'
PLAN=ROOT/'reports/evidence_e01_pypa_fixture_g03_preparation_v1_20261116/INTEGRATION_PLAN.json'
PACKET=ROOT/'reports/evidence_e01_pypa_fixture_g03_preparation_v1_1_20261116/PREPARATION_PACKET.json'
OLD_CODE=ROOT/'scripts/e01_pypa_fixture_g03_caller_candidate_v1_20261116.py'
OLD_TEST=ROOT/'tests/test_e01_pypa_fixture_g03_caller_candidate_v1_20261116.py'
allowed={ME,CODE,TEST,PLAN,PACKET,OLD_CODE,OLD_TEST};stdlib=(Path(sys.base_prefix)/'lib').resolve();reads=0
def audit(event,args):
    global reads
    if event=='open':
        if not isinstance(args[0],(str,bytes,os.PathLike)):raise AssertionError('NO_UNKNOWN_DESCRIPTOR_IO')
        p=Path(os.path.realpath(args[0]));flags=args[2]
        if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('NO_OS_WRITES')
        if not(p in allowed or(p.is_relative_to(stdlib) and 'site-packages' not in p.parts)):raise AssertionError('UNAPPROVED_READ')
        try:reads+=p.stat().st_size+1
        except FileNotFoundError:reads+=1
        if reads>67108864:raise AssertionError('READ_CAP')
    if event in {'os.mkdir','os.rmdir','os.remove','os.rename','os.link','os.symlink','os.chmod','os.truncate'}:raise AssertionError('NO_OS_MUTATION')
sys.addaudithook(audit)
def no_native(*args,**kwargs):raise AssertionError('NO_REAL_KILL_WAIT4')
os.kill=os.killpg=os.wait4=no_native
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def deadline(*_):raise AssertionError('OWN_WALL_CAP')
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,120)
assert hashlib.sha256(CODE.read_bytes()).hexdigest()=='1d956931da7d11cf58cfc540cd7b6b8634aecffc34e5c9b9aa4373be92879abc'
assert hashlib.sha256(TEST.read_bytes()).hexdigest()=='21de70a84f62e2cac962f34baf2a4f3b25c90242d56d390528808def79db7555'
ns=runpy.run_path(str(TEST),run_name='independent_inert_definitions');m=ns['m'];checks=[];findings=[]
assert hashlib.sha256(OLD_CODE.read_bytes()).hexdigest()=='a1f03d2ad23526748d3784d71541df39c782449bb5e8315d8f1e0deedebe2514'
assert hashlib.sha256(OLD_TEST.read_bytes()).hexdigest()=='cd4eff8f1d4777e3e7e369a8e493520dca77c138c659ed346ac98496d271f3e7'
old_m=runpy.run_path(str(OLD_TEST),run_name='independent_predecessor_definitions_only')['m']
def check(name,value):
    checks.append({'name':name,'pass':bool(value)})
    if not value:raise AssertionError(name)
def refused(name,call,kind=m.Refused,code=None,identity=None):
    try:call()
    except kind as error:
        check(name,(code is None or getattr(error,'code',None)==code) and(identity is None or error is identity));return error
    raise AssertionError(name+': missing refusal')
class Clock:
    def __init__(self):self.value=0.;self.calls=0
    def __call__(self):self.calls+=1;return self.value
class Backend:
    mock_only=True
    def __init__(self,clock,events=(),step=.1,exit_at=1,never_reap=False,cpu=.5,returncode=0):
        self.clock=clock;self.events=list(events);self.step=step;self.exit_at=exit_at;self.never_reap=never_reap;self.cpu=cpu;self.returncode=returncode
        self.started=False;self.output_complete=False;self.starts=self.drains=self.kills=self.closes=self.waits=0
    def start(self,command,env):self.starts+=1;self.started=True;self.command=command;self.env=env
    def drain(self,timeout):
        self.drains+=1;self.clock.value+=self.step
        row=self.events.pop(0) if self.events else [];self.output_complete=not self.events;return row
    def wait_nonblock(self):
        self.waits+=1
        if self.never_reap or(not self.kills and self.drains<self.exit_at):return None
        return {'reaped':True,'returncode':-9 if self.kills else self.returncode,'CPU_user_seconds':self.cpu,'CPU_system_seconds':0.}
    def kill_once(self):self.kills+=1
    def pause(self,seconds):self.clock.value+=seconds
    def close(self):self.closes+=1
def context():
    packet=m.preparation_packet({'path':m.CODE,'bytes':18224,'sha256':'1d956931da7d11cf58cfc540cd7b6b8634aecffc34e5c9b9aa4373be92879abc'})
    def pin(path,n):return {'path':path,'bytes':n,'sha256':str(n)*64}
    packet.update(state='EXACT_FROZEN_CHILD_CANDIDATE',temp_parent='/SSL_G03_INDEPENDENT_INERT',gates={name:'PASS_EXACT_REVIEWED_BOUNDARY' for name in m.GATES},child_adapter_ref=pin('scripts/e01_pypa_fixture_g03_child_INDEPENDENT_INERT.py',1),startup_closure_ref=pin('reports/evidence_e01_pypa_fixture_g03_INDEPENDENT/closure.json',2),child_guard_review_ref=pin('reports/INDEPENDENT_AUDIT_INERT_ONLY.json',3),harness_release_ref=pin('data/processed/e01_pypa_fixture_release_v1_1_20261116/INERT_ONLY.json',4))
    release={'kind':'E01_G03_EXACT_ONE_CHILD_RELEASE_V1','enabled':True,'packet_sha256':m.digest(m.packed(packet)),'scope':m.SCOPE,'maximum_children':1,'retries':0}
    review={'decision':'PASS_EXACT_G03_CALLER_PACKET_CHILD_CLOSURE','packet_sha256':release['packet_sha256'],'release_core_sha256':m.digest(m.packed(release)),'caller_ref':packet['caller_ref'],'gates':packet['gates']}
    return packet,release,review
def flow(backend,clock,journal=None):return m.run_mock(*context(),backend,journal,clock=clock)
disabled=json.loads(PACKET.read_bytes());plan=json.loads(PLAN.read_bytes());m.validate_packet(disabled)
check('disabled exact seven blocked gates',disabled['execution_enabled'] is False and len(disabled['gates'])==7 and all(v=='BLOCKED_MISSING_EVIDENCE' for v in disabled['gates'].values()))
check('disabled child/closure/release paths null',all(disabled[k] is None for k in ('child_adapter_ref','startup_closure_ref','child_guard_review_ref','harness_release_ref','temp_parent')))
class Poison:
    def __getattribute__(self,name):raise AssertionError('POISON_ARGUMENT_TOUCHED')
refused('actual entry unconditional refusal',lambda:m.run_actual(Poison(),enabled=True),code='G03_ACTUAL_ENTRY_BLOCKED_MISSING_CHILD_GUARD_AND_STARTUP_CLOSURE')
for gate in m.GATES:
    p,r,v=context();p['gates'][gate]='NOT_RUN';c=Clock();b=Backend(c);j=m.MemoryJournal()
    refused('pending gate '+gate,lambda:m.run_mock(p,r,v,b,j,clock=c),code='G03_PENDING_BOUNDARIES')
    check('no marker or start pending '+gate,b.starts==0 and j.files=={})
for field in ('child_adapter_ref','startup_closure_ref','child_guard_review_ref','harness_release_ref'):
    p,r,v=context();p[field]=None;refused('missing ref '+field,lambda:m.validate_release(p,r,v))
for field,value in [('enabled',False),('maximum_children',2),('retries',1),('packet_sha256','0'*64)]:
    p,r,v=context();r[field]=value;refused('release binding '+field,lambda:m.validate_release(p,r,v),code='G03_EXACT_RELEASE_REQUIRED')
c=Clock();j=m.MemoryJournal()
class Marked(Backend):
    def start(self,*args):
        check('marker before start','STARTED.json' in j.files)
        return super().start(*args)
b=Marked(c);result,j=flow(b,c,j)
check('one start captured not integration',b.starts==1 and b.kills==0 and b.closes==1 and result['status']=='CAPTURED_PARENT_ONLY' and not result['G03_acceptance'] and not result['actual_fixture_acceptance'])
check('fixed isolated zero-paid command',b.command[1:4]==['-I','-B','-S'] and b.env['MAX_SPEND_USD']=='0' and b.env['PAID_API_ENABLED']=='false' and not any(k in b.env for k in ('OPENROUTER_API_KEY','PYTHONPATH','VIRTUAL_ENV')))
before=dict(j.files);refused('spent scope no second start',lambda:flow(b,c,j),code='G03_SPENT_SCOPE');check('replay no writes or start',j.files==before and b.starts==1)
primary=RuntimeError('INDEPENDENT_PRIMARY_TEXT_NOT_FOR_RECEIPT');c=Clock();j=m.MemoryJournal()
class StartFail(Backend):
    def start(self,*args):self.starts+=1;raise primary
b=StartFail(c);refused('start failure primary',lambda:flow(b,c,j),RuntimeError,identity=primary)
check('failed start consumed and redacted','STARTED.json' in j.files and 'FAILURE.json' in j.files and b.starts==1 and b.kills==0 and b.closes==1 and b'INDEPENDENT_PRIMARY_TEXT' not in j.files['FAILURE.json'])
refused('failed start cannot replay',lambda:flow(b,c,j),code='G03_SPENT_SCOPE')
c=Clock();b=Backend(c,events=[[('stdout',b'A')],[('stderr',b'B')],[('stdout',b'C')]],exit_at=1);result,j=flow(b,c)
check('drain after early reap until EOF',b.drains==3 and j.files['STDOUT.bin']==b'AC' and j.files['STDERR.bin']==b'B' and result['console_observed_bytes']==3 and result['status']=='CAPTURED_PARENT_ONLY')
c=Clock();b=Backend(c,events=[[('stdout',b'A'*65536)] for _ in range(5)],exit_at=100);result,j=flow(b,c)
check('console limit bounded retained prefix',result['reason']=='CONSOLE_CAP' and result['console_retained_bytes']==262144 and result['console_observed_bytes']==327680 and b.kills==1 and result['reaped'])
check('parent journal console within quota',sum(map(len,j.files.values()))<=1048576 and len(j.files['STDOUT.bin'])==262144)
for events in ([('stdout',b'A'*65537)],[('unknown',b'A')],[('stdout',b'A'),('stderr',b'B'),('stdout',b'C')]):
    c=Clock();b=Backend(c,events=[events],exit_at=100);j=m.MemoryJournal();refused('malformed output event',lambda:flow(b,c,j))
    check('malformed output single kill',b.kills==1 and b.starts==1 and b.closes==1 and 'FAILURE.json' in j.files)
c=Clock();b=Backend(c,step=117,exit_at=100);result,j=flow(b,c)
check('work stop single kill and bounded reap',result['reason']=='WORK_WALL_CAP' and b.kills==1 and result['reaped'] and result['wall_seconds_start_to_cleanup']<=120)
timing_edges=[]
for step in (116.999,117,118,120,120.5):
    c=Clock();b=Backend(c,step=step,exit_at=1);result,j=flow(b,c)
    old_c=Clock();old_b=Backend(old_c,step=step,exit_at=1)
    predecessor,old_output=old_m.supervise_backend(old_b,['INERT_NO_DISPATCH'],{},clock=old_c)
    expected=None if step<117 else 'TOTAL_WALL_CAP_OBSERVED' if step>120 else 'WORK_WALL_CAP'
    check('matched final drain '+str(step),result['reason']==expected and result['status']==('CAPTURED_PARENT_ONLY' if expected is None else 'FAILED_UNACCEPTED'))
    check('matched no actual acceptance '+str(step),not result['G03_acceptance'] and not result['actual_fixture_acceptance'] and b.kills==0 and result['reaped'])
    if step in (117,118,120):check('original work discrepancy retained '+str(step),predecessor['reason'] is None and predecessor['status']=='CAPTURED_PARENT_ONLY')
    timing_edges.append({'edge':step,'successor':result,'predecessor':predecessor,'fake_starts':b.starts,'fake_kills':b.kills})
for edge in (116.999,117,118):
    c=Clock()
    class WaitCross(Backend):
        def wait_nonblock(self):self.clock.value=edge;return super().wait_nonblock()
    b=WaitCross(c,step=116.5);result,j=flow(b,c)
    check('wait itself crosses boundary '+str(edge),result['reason']==(None if edge<117 else 'WORK_WALL_CAP') and b.kills==0 and result['reaped'])
c=Clock();b=Backend(c,events=[[('stdout',b'INDEPENDENT_DEADLINE_PARTIAL')]],step=117,exit_at=100);result,j=flow(b,c)
check('unreaped deadline retains partial and kills once',result['reason']=='WORK_WALL_CAP' and b.kills==1 and result['reaped'] and j.files['STDOUT.bin']==b'INDEPENDENT_DEADLINE_PARTIAL')
c=Clock();b=Backend(c,events=[[('stdout',b'A'*65536)] for _ in range(5)],step=24,exit_at=100);result,j=flow(b,c)
check('existing console reason survives new work check',result['reason']=='CONSOLE_CAP' and result['console_retained_bytes']==262144 and b.kills==1 and result['wall_seconds_start_to_cleanup']==120)
primary=RuntimeError('INDEPENDENT_POST_WAIT_PRIMARY');secondary=ValueError('INDEPENDENT_FINAL_CLOCK_SECONDARY')
class PostWaitClock(Clock):
    def __call__(self):
        self.calls+=1
        if self.calls==3:raise primary
        if self.calls>3:raise secondary
        return self.value
class CloseError(Backend):
    def close(self):self.closes+=1;raise OSError('INDEPENDENT_CLOSE_SECONDARY')
c=PostWaitClock();b=CloseError(c,events=[[('stdout',b'POST_WAIT_PARTIAL')]]);j=m.MemoryJournal()
refused('post-wait clock primary survives final/close faults',lambda:flow(b,c,j),RuntimeError,identity=primary)
check('post-wait exception preserves captured bytes/reap',j.files['STDOUT.bin']==b'POST_WAIT_PARTIAL' and 'FAILURE.json' in j.files and b.kills==0 and b.closes==1)
class RegressionClock(Clock):
    def __call__(self):
        self.calls+=1
        return -1. if self.calls==3 else self.value
c=RegressionClock();b=Backend(c);j=m.MemoryJournal()
refused('post-wait clock regression',lambda:flow(b,c,j),code='G03_CLOCK_REGRESSION')
check('regression cannot captured-pass','FAILURE.json' in j.files and 'FINAL.json' not in j.files and b.kills==0 and b.closes==1)
for cleanup_delay in (3,3.5):
    c=Clock()
    class CloseDelay(Backend):
        def close(self):self.clock.value+=cleanup_delay;super().close()
    b=CloseDelay(c,step=117,exit_at=100);result,j=flow(b,c)
    check('cleanup120/120.5 preserves deadline precedence '+str(cleanup_delay),result['reason']==('WORK_WALL_CAP' if cleanup_delay==3 else 'TOTAL_WALL_CAP_OBSERVED') and b.kills==1 and result['reaped'])
for kwargs,reason in [({'returncode':7},'CHILD_EXIT_NONZERO'),({'cpu':120.25},'CPU_CAP_OBSERVED')]:
    c=Clock();b=Backend(c,**kwargs);result,j=flow(b,c);check('failed child receipt '+reason,result['reason']==reason and result['status']=='FAILED_UNACCEPTED')
for bad in (float('nan'),float('inf'),-1,True,'1'):
    c=Clock();j=m.MemoryJournal()
    class BadCPU(Backend):
        def wait_nonblock(self):return {'reaped':True,'returncode':0,'CPU_user_seconds':bad,'CPU_system_seconds':0}
    b=BadCPU(c);refused('malformed wait CPU',lambda:flow(b,c,j),code='G03_WAIT_RECEIPT')
    check('malformed wait never integration accepted','FAILURE.json' in j.files and b.starts==1 and b.closes==1)
c=Clock();b=Backend(c,step=0,exit_at=10000,never_reap=True);result,j=flow(b,c)
check('nonadvancing clock finite polls/reap failure',b.drains==2500 and b.kills==1 and b.waits<=2600 and result['reason']=='UNREAPED_CHILD' and not result['reaped'] and result['CPU_seconds_whole_child_observed'] is None)
primary=RuntimeError('INDEPENDENT_DRAIN_PRIMARY');c=Clock();j=m.MemoryJournal();ordinary_new=j.new
def failed_receipt(name,raw):
    if name=='FAILURE.json':raise OSError('INDEPENDENT_SECONDARY_STORAGE')
    return ordinary_new(name,raw)
j.new=failed_receipt
class ManyFailures(Backend):
    def drain(self,*args):raise primary
    def kill_once(self):self.kills+=1;raise OSError('INDEPENDENT_SECONDARY_KILL')
    def close(self):self.closes+=1;raise ValueError('INDEPENDENT_SECONDARY_CLOSE')
b=ManyFailures(c);refused('primary survives kill close storage faults',lambda:flow(b,c,j),RuntimeError,identity=primary)
check('one cleanup attempt and scope consumed',b.starts==1 and b.kills==1 and b.closes==1 and 'STARTED.json' in j.files)
primary=RuntimeError('INDEPENDENT_LATE_DRAIN');c=Clock();j=m.MemoryJournal()
class Partial(Backend):
    def drain(self,*args):
        if self.drains:raise primary
        return super().drain(*args)
b=Partial(c,events=[[('stdout',b'INERT_PARTIAL')]],exit_at=100)
refused('partial capture first exception',lambda:flow(b,c,j),RuntimeError,identity=primary);check('partial output retained',j.files['STDOUT.bin']==b'INERT_PARTIAL' and 'FAILURE.json' in j.files)
primary=RuntimeError('INDEPENDENT_FIRST_CLOCK');secondary=ValueError('INDEPENDENT_LATE_CLOCK')
class BrokenClock(Clock):
    def __call__(self):
        self.calls+=1
        if self.calls==2:raise primary
        if self.calls>2:raise secondary
        return 0.
c=BrokenClock();b=Backend(c);j=m.MemoryJournal();refused('clock primary not replaced during cleanup',lambda:flow(b,c,j),RuntimeError,identity=primary)
check('clock failure closed/consumed',b.kills==1 and b.closes==1 and 'STARTED.json' in j.files and 'FAILURE.json' in j.files)
j=m.MemoryJournal();j.new('STDOUT.bin',b'A');before=dict(j.files)
refused('journal duplicate',lambda:j.new('STDOUT.bin',b'B'),code='G03_SPENT_SCOPE')
refused('journal overflow',lambda:j.new('STDERR.bin',b'A'*1048576),code='G03_PARENT_WRITE_CAP')
refused('journal traversal',lambda:j.new('../ESCAPE',b'A'),code='G03_RECORD_NAME');check('journal preserves on refusal',j.files==before)
check('write quota exact arithmetic',m.LIMITS['child_write_bytes']+m.LIMITS['parent_write_bytes']==m.LIMITS['combined_write_bytes']==33554432)
check('wall reserve arithmetic',m.LIMITS['work_seconds']+m.LIMITS['cleanup_reserve_seconds']==m.LIMITS['child_wall_seconds']==120)
budget_sum=2*m.RUNTIME['bytes']+33554432
check('runtime rehashes plus full stream budget do not fit',budget_sum>m.LIMITS['technical_read_bytes'])
check('integration plan acknowledges missing allocation','cannot simply be asserted within64MiB' in plan['required_child_adapter_steps'][4]['required_evidence'] and plan['G03_acceptance']=='NOT_RUN_BLOCKED_FOR_ACTUAL_RELEASE' and len(plan['unsubstantiated_boundaries'])==7)
source=CODE.read_bytes();tree=ast.parse(source)
entry=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_actual')
check('actual entry one unconditional raise',len([n for n in entry.body if not isinstance(n,ast.Expr)])==1 and isinstance(entry.body[-1],ast.Raise))
check('no top-level native process import',not any(isinstance(n,ast.Import) and any(a.name in {'subprocess','installer'} for a in n.names) for n in tree.body))
signal.setitimer(signal.ITIMER_REAL,0)
receipt={'status':'PASS_EXACT_P01_REMEDY_INERT_COMPONENT_ONLY_ACTUAL_G03_NOT_RUN','runtime':sys.version.split()[0],'checks':len(checks),'assertions':checks,'findings':findings,'timing_edges':timing_edges,'budget_arithmetic':{'two_runtime_hashes_plus32MiB_stream_bytes':budget_sum,'cap_bytes':67108864,'excess_before_other_reads':budget_sum-67108864,'nominal18MiBplus18MiBplus32MiB':71303168},'late_read_bytes':reads,'OS_writes':0,'actual_backend_process_kill_wait4_tool_calls':0,'actual_G03_acceptance':False,'cost_USD':0}
text=json.dumps(receipt,sort_keys=True)+'\n';assert len(text.encode())<=262144;sys.stdout.write(text)
