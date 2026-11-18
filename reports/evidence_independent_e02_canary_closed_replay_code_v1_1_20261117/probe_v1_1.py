"""Authored helper/guard checks only. Never call helper child or any owner."""
import os,sys,time,resource,signal,ast,json,hashlib,io,sqlite3,tempfile,types,importlib.util,shutil
from pathlib import Path
from unittest.mock import patch
START=time.monotonic()
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_CPU,(119,120))
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('INDEPENDENT180')))
signal.alarm(180)
ROOT=Path.cwd();HELPER=ROOT/'scripts/qualify_e02_canary_closed_replay_v1_1_20261117.py'
raw=HELPER.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c1f4b27e7717830acc6ab7aa01859a06d698b3c0ee860de68c4edc36fa9564d7'
spec=importlib.util.spec_from_file_location('reviewed_helper',HELPER)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
scratch=Path(tempfile.mkdtemp(prefix='INDEPENDENT_HELPER_')).resolve()
OBS=[]
def record(name,passed,**details):OBS.append({'case':name,'pass':bool(passed),**details})
def refusal(fn):
    try:fn()
    except (h.Refused,ValueError,OSError,RuntimeError):return True
    return False

# Pure counters/streams/control files; no actual qualification gate or payload.
b=h.Budget();b.charge('read_bytes',12)
record('budget_positive',b.reads==12)
record('budget_limit_refusal',refusal(lambda:b.charge('read_bytes',h.LIMITS['read_bytes'])))
record('negative_charge_refusal',refusal(lambda:h.Budget().charge('read_bytes',-1)))
stream_budget=h.Budget();s=h.Stream(io.BytesIO(b'abc\n'),stream_budget)
assert s.readline()==b'abc\n';assert s.read()==b''
record('stream_content_and_EOF',stream_budget.reads==4,charged_bytes=stream_budget.reads,EOF_content_bytes=0)
record('stream_raw_bypass_denied',refusal(lambda:s.raw) and stream_budget.denials==1)
control=scratch/'authored-control.json';control.write_bytes(b'{"MOCK":true}')
cb=h.Budget();value=h.read_control(control,hashlib.sha256(control.read_bytes()).hexdigest(),cb)
record('control_positive',value=={'MOCK':True} and cb.reads==13)
record('control_bad_hash',refusal(lambda:h.read_control(control,'0'*64,h.Budget())))
large=scratch/'large.json';large.write_bytes(b' '*262145)
record('control_size_refusal',refusal(lambda:h.read_control(large,'0'*64,h.Budget())))
created=scratch/'once';h.private_write(created,b'x',h.Budget())
record('create_once_gate',refusal(lambda:h.private_write(created,b'x',h.Budget())))
db=sqlite3.connect(':memory:');db.execute('CREATE TABLE header(data TEXT)');db.execute('INSERT INTO header VALUES (?)',('MOCK',))
sql_budget=h.Budget();proxy=h.ReadOnlySQL(db,sql_budget)
record('SQL_SELECT_charge',proxy.execute('SELECT data FROM header').fetchall()==[('MOCK',)] and sql_budget.reads==4)
record('SQL_mutation_refusal',refusal(lambda:proxy.execute('DELETE FROM header')) and sql_budget.denials==1);db.close()
# Explicitly distinguish serializer behavior from the project's canonical hash.
value={'authored':'é'}
record('canonical_ascii_compatibility',h.canonical(value)==json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode(),helper_ensure_ascii=True,project_ensure_ascii=True)

# Supervisor uses inert selector/process doubles, no actual subprocess or child.
valid={'kind':'CLOSED_PARENT_REPLAY_RESULT_V1','status':'PASS_PARENT_ONLY','charged_read_bytes':1,'charged_write_bytes':1,'guard_denials':0,'temporary_fixture_removed':True,'verify_calls':1}
args=types.SimpleNamespace(contract_sha256='a'*64,review_sha256='b'*64)
def lifecycle(mode):
    scope=scratch/('supervisor-'+mode);scope.mkdir()
    if mode=='EOF_exit_fixture':(scope/'temporary-fixture').mkdir()
    payload=json.dumps(valid).encode() if mode!='overflow' else b'x'*65537
    ticks=[0.0];chunks=[payload,b''];waits=[]
    class Pipe:
        closed=False
        def fileno(self):return 97
        def close(self):self.closed=True
    class Process:
        def __init__(self):self.stdout=Pipe();self.returncode=None;self.kills=0
        def poll(self):return self.returncode
        def kill(self):self.kills+=1;self.returncode=-9
        def wait(self,timeout=None):
            waits.append(timeout)
            if self.returncode is not None:return self.returncode
            if mode=='EOF_hang':raise h.subprocess.TimeoutExpired('INERT',timeout)
            if mode=='EOF_interrupt':raise KeyboardInterrupt()
            self.returncode=0;return 0
    process=Process();spawns=[]
    class Selector:
        def __init__(self):self.mapping={}
        def register(self,file,event):self.mapping[97]=types.SimpleNamespace(fileobj=file)
        def get_map(self):return self.mapping
        def unregister(self,key):self.mapping.clear()
        def select(self,timeout=None):
            if mode=='cancel':raise KeyboardInterrupt()
            return [(v,1) for v in list(self.mapping.values())]
        def close(self):self.mapping.clear()
    def spawned(*a,**k):spawns.append(1);return process
    def read(fd,n):
        if mode=='deadline':ticks[0]=301;return b'x'
        if not chunks:return b''
        chunk=chunks.pop(0)
        if len(chunk)>n:chunks.insert(0,chunk[n:]);chunk=chunk[:n]
        return chunk
    q={'helper':{'sha256':'c'*64}}
    with patch.object(h,'SCOPE',scope),patch.object(h,'gate',return_value=(q,{})),patch.object(h,'preflight',return_value=None),patch.object(h.signal,'signal'),patch.object(h.signal,'setitimer'),patch.object(h.subprocess,'Popen',side_effect=spawned),patch.object(h.selectors,'DefaultSelector',Selector),patch.object(h.os,'read',side_effect=read),patch.object(h.time,'monotonic',side_effect=lambda: ticks[0]),patch.object(sys,'stdout',io.StringIO()):
        rc=h.supervise(args)
    receipt=json.loads((scope/'safe-supervisor-receipt.json').read_bytes())
    return {'mode':mode,'exit':rc,'reason':receipt['reason'],'status':receipt['status'],'spawns':len(spawns),'kills':process.kills,'wait_calls':len(waits),'pipe_closed':process.stdout.closed,'CPU_scope':receipt['CPU_scope'],'parent_CPU_observed':receipt['supervisor_CPU_seconds']>=0,'fixture_disposition':receipt['fixture_disposition']['disposition']}
for mode in ('EOF_exit','EOF_hang','EOF_interrupt','cancel','deadline','overflow','EOF_exit_fixture'):
    result=lifecycle(mode)
    expected='PASS_PARENT_ONLY' if mode=='EOF_exit' else 'STOPPED_NOT_QUALIFIED'
    record('lifecycle_'+mode,result['status']==expected and result['spawns']==1 and result['pipe_closed'] and (mode in ('EOF_exit','EOF_exit_fixture') or result['kills']==1) and result['CPU_scope']=='CHILD_LIMIT_120_PARENT_OBSERVED_SEPARATELY' and result['parent_CPU_observed'],**result)

# Final irreversible guard tests in the disposable outer process. All data are
# authored and under scratch; outside means outside helper's authorized tmp.
for i,value in enumerate([{'ASCII':'ok'}, {'authored':'é','nested':['汉字','😀']}, {'escape':'\n\t\"'}, {'n':0,'v':[False,None,1.25]}]):
    record('canonical_matrix_'+str(i),h.canonical(value)==json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
quarantine=scratch/'quarantine-test';quarantine.mkdir();(quarantine/'temporary-fixture').mkdir()
q=h.fixture_disposition(quarantine,{'temporary_fixture_removed':False})
record('quarantine_present_no_delete',q['disposition']=='QUARANTINED_PRIVATE_NO_RETRY' and q['followup']=='SEPARATE_BOUNDED_LEAD_CLEANUP_REQUIRED' and not q['supervisor_cleanup_attempted'] and (quarantine/'temporary-fixture').is_dir())
record('quarantine_absent',h.fixture_disposition(scratch/'absent',None)['disposition']=='NO_FIXTURE_PRESENT')
allowed=scratch/'guard-inside';allowed.mkdir();outside=scratch/'guard-outside';outside.mkdir();(outside/'escaped').mkdir();(outside/'escaped').chmod(0o700)
(allowed/'outside-alias').symlink_to(outside,target_is_directory=True)
db_path=allowed/'owned.sqlite'
dirfd=ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py';dirraw=dirfd.read_bytes()
closure={'project_pins':[],'stdlib_pins':[]}
guard_budget=h.Budget()
oldstdout=sys.stdout
h.install_guard(closure,allowed,db_path,guard_budget,{'bytes':len(dirraw),'sha256':hashlib.sha256(dirraw).hexdigest()})
inside=allowed/'read.txt'
h.private_write(inside,b'AUTHORED',guard_budget)
record('guard_owned_IO',inside.read_bytes()==b'AUTHORED')
record('guard_unlisted_read',refusal(lambda:control.read_bytes()))
record('guard_outside_write',refusal(lambda:(outside/'blocked.txt').write_bytes(b'x')))
record('guard_unknown_descriptor',refusal(lambda:os.read(90,1)))
# Create targets before installing the guard is not possible here; exercise
# mutation escape through directory creation then remove the empty marker.
def guarded_case(name,fn,effect_absent):
    before=guard_budget.denials
    denied=refusal(fn)
    record(name,denied and guard_budget.denials==before+1 and effect_absent(),sticky_denial=guard_budget.denials==before+1)
guarded_case('original_absolute_parent_mkdir',lambda:(allowed/'..'/'guard-outside'/'NEW_ESCAPE').mkdir(),lambda:not (outside/'NEW_ESCAPE').exists())
fd=os.open(allowed,os.O_RDONLY)
try:
    guarded_case('original_dirfd_parent_rmdir',lambda:os.rmdir('../guard-outside/escaped',dir_fd=fd),lambda:(outside/'escaped').is_dir())
    guarded_case('dirfd_parent_mkdir',lambda:os.mkdir('../guard-outside/NEW_ESCAPE',dir_fd=fd),lambda:not (outside/'NEW_ESCAPE').exists())
    guarded_case('dirfd_parent_chmod',lambda:os.chmod('../guard-outside/escaped',0o777,dir_fd=fd),lambda:(outside/'escaped').stat().st_mode & 0o777 != 0o777)
    guarded_case('absolute_alias_mkdir',lambda:(allowed/'outside-alias'/'ALIAS_ESCAPE').mkdir(),lambda:not (outside/'ALIAS_ESCAPE').exists())
    guarded_case('relative_alias_mkdir',lambda:os.mkdir('outside-alias/ALIAS_ESCAPE',dir_fd=fd),lambda:not (outside/'ALIAS_ESCAPE').exists())
    before=guard_budget.denials
    os.mkdir('relative-positive',dir_fd=fd)
    os.chmod('relative-positive',0o700,dir_fd=fd)
    record('positive_tracked_dirfd_mkdir_chmod',(allowed/'relative-positive').is_dir() and guard_budget.denials==before)
    os.rmdir('relative-positive',dir_fd=fd)
    record('positive_tracked_dirfd_rmdir',not (allowed/'relative-positive').exists() and guard_budget.denials==before)
    h.private_write(allowed/'remove-positive',b'x',guard_budget)
    os.remove('remove-positive',dir_fd=fd)
    record('positive_tracked_dirfd_remove',not (allowed/'remove-positive').exists() and guard_budget.denials==before)
finally:os.close(fd)
guarded_case('stale_dirfd',lambda:os.rmdir('uncreated',dir_fd=fd),lambda:True)
guarded_case('unknown_dirfd',lambda:os.mkdir('uncreated',dir_fd=999999),lambda:not (allowed/'uncreated').exists())
record('guard_SQL_wrong_path',refusal(lambda:sqlite3.connect(str(allowed/'foreign.sqlite'))))
# Report only fixed observations/counters. Guard fixture is deliberately kept
# for parent-owned cleanup after this disposable process exits.
assert not any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules)
report={'kind':'INDEPENDENT_CLOSED_HELPER_V1_1_CORRECTION_PROBE','runtime':sys.version.split()[0],'observations':OBS,'checks':len(OBS),'failed_case_names':[o['case'] for o in OBS if not o['pass']],'guard_counters':{'reads':guard_budget.reads,'writes':guard_budget.writes,'console':guard_budget.console,'denials':guard_budget.denials},'scratch':str(scratch),'actual_closed_inputs':0,'candidate_owner_imports':0,'real_subprocesses':0,'network_calls':0,'cost_usd':0,'wall_seconds':time.monotonic()-START}
text=json.dumps(report,sort_keys=True)
assert len(text.encode())<262144
print(text)
