"""Author V1.1 regressions; adapted from frozen independent authored probe_v1.py.
No qualification child, owner, closed payload or network execution.
"""
import os,sys,time,resource,signal,ast,json,hashlib,io,sqlite3,tempfile,types,importlib.util,shutil
from pathlib import Path
from unittest.mock import patch
START=time.monotonic()
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_CPU,(119,120))
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('INDEPENDENT180')))
signal.alarm(180)
ROOT=Path.cwd();HELPER=ROOT/'scripts/qualify_e02_canary_closed_replay_v1_1_20261117.py'
# Outer authored-only guard and counters, installed before helper definitions.
import builtins,sysconfig
AUTHOR={'reads':0,'writes':0,'console':0}
AUTHOR_SCRATCH=Path(sys.argv[1]).resolve()
AUTHOR_STDLIB=Path(sysconfig.get_path('stdlib')).resolve()
AUTHOR_FILES={HELPER.resolve(),Path(__file__).resolve(),(ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py').resolve()}
prewarm=set()
for mod in list(sys.modules.values()):
    for value in (getattr(mod,'__file__',None),getattr(mod,'__cached__',None)):
        if value:
            path=Path(value)
            if path.is_file():prewarm.add(path.resolve())
AUTHOR['reads']=sum(path.stat().st_size for path in prewarm)
assert AUTHOR['reads']<134217728

def authored_audit(event,args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:raise RuntimeError('AUTHOR_NETWORK_OR_PROCESS_DENIED')
    if event=='sqlite3.connect' and str(args[0])!=':memory:':
        path=Path(str(args[0]).removeprefix('file:').split('?')[0]).resolve()
        if not path.is_relative_to(AUTHOR_SCRATCH):raise RuntimeError('AUTHOR_NONAUTHORED_SQLITE')
    if event=='open' and not isinstance(args[0],int):
        rawpath=os.fsdecode(args[0]);path=Path(os.path.abspath(rawpath))
        # Inner reviewed descriptor guard resolves its relative cleanup operations;
        # probe performs no relative file opens outside that inner guard.
        write=bool(args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if write:
            if not path.resolve().is_relative_to(AUTHOR_SCRATCH):raise RuntimeError('AUTHOR_WRITE_SCOPE')
        else:
            resolved=path.resolve()
            if not (resolved in AUTHOR_FILES or resolved.is_relative_to(AUTHOR_SCRATCH) or resolved.is_relative_to(AUTHOR_STDLIB)):raise RuntimeError('AUTHOR_READ_SCOPE')
            if resolved.is_file():AUTHOR['reads']+=resolved.stat().st_size
            if AUTHOR['reads']>134217728:raise RuntimeError('AUTHOR128MIB_READ_LIMIT')
sys.addaudithook(authored_audit)
class AuthorWrites:
    def __init__(self,stream):self.stream=stream
    def __getattr__(self,n):return getattr(self.stream,n)
    def __enter__(self):return self
    def __exit__(self,*a):return self.stream.__exit__(*a)
    def write(self,data):
        AUTHOR['writes']+=len(data.encode() if isinstance(data,str) else data)
        if AUTHOR['writes']>33554432:raise RuntimeError('AUTHOR32MIB_WRITE_LIMIT')
        return self.stream.write(data)
    def writelines(self,data):
        for part in data:self.write(part)
for obj,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
    original=getattr(obj,name)
    def authored_open(*a,_original=original,**k):
        stream=_original(*a,**k);mode=k.get('mode',a[1] if len(a)>1 else 'r')
        return AuthorWrites(stream) if any(c in mode for c in 'wax+') else stream
    setattr(obj,name,authored_open)
class AuthorConsole:
    def __init__(self,stream):self.stream=stream
    def __getattr__(self,n):return getattr(self.stream,n)
    def write(self,s):
        AUTHOR['console']+=len(s.encode())
        if AUTHOR['console']>262144:raise RuntimeError('AUTHOR256KIB_CONSOLE_LIMIT')
        return self.stream.write(s)
    def flush(self):return self.stream.flush()
sys.stdout=AuthorConsole(sys.stdout);sys.stderr=AuthorConsole(sys.stderr)
raw=HELPER.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='c1f4b27e7717830acc6ab7aa01859a06d698b3c0ee860de68c4edc36fa9564d7'
h=types.ModuleType('reviewed_helper');h.__file__=str(HELPER)
exec(compile(raw,str(HELPER),'exec'),h.__dict__)
scratch=Path(sys.argv[1]).resolve();assert scratch.is_dir()
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
    return {'mode':mode,'exit':rc,'reason':receipt['reason'],'status':receipt['status'],'spawns':len(spawns),'kills':process.kills,'wait_calls':len(waits),'pipe_closed':process.stdout.closed}
for mode in ('EOF_exit','EOF_hang','EOF_interrupt','cancel','deadline','overflow'):
    result=lifecycle(mode)
    expected='PASS_PARENT_ONLY' if mode=='EOF_exit' else 'STOPPED_NOT_QUALIFIED'
    record('lifecycle_'+mode,result['status']==expected and result['spawns']==1 and result['pipe_closed'] and (mode=='EOF_exit' or result['kills']==1),**result)

# Canonical regression matrix: exact original JSON defaults, no civiclab import.
for i,value in enumerate([{'ASCII':'only'}, {'é':'東京😀'}, {'nested':['é',{'ключ':'значение'}]}, {'line':'\\n / \"','number':0.00001}]):
    expected=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    record('canonical_matrix_'+str(i),h.canonical(value)==expected and hashlib.sha256(h.canonical(value)).digest()==hashlib.sha256(expected).digest() and json.loads(h.canonical(value))==value)
qscope=scratch/'quarantine';qscope.mkdir();qtmp=qscope/'temporary-fixture';qtmp.mkdir()
q=h.fixture_disposition(qscope,None)
record('forced_kill_private_quarantine',q['disposition']=='QUARANTINED_PRIVATE_NO_RETRY' and q['supervisor_cleanup_attempted'] is False and q['followup']=='SEPARATE_BOUNDED_LEAD_CLEANUP_REQUIRED' and qtmp.is_dir())
qtmp.rmdir();q=h.fixture_disposition(qscope,{'temporary_fixture_removed':True})
record('confirmed_absent_fixture',q['disposition']=='NO_FIXTURE_PRESENT' and q['child_cleanup_reported'] is True and q['path_present'] is False)
# Final irreversible guard tests in the disposable outer process. All data are
# authored and under scratch; outside means outside helper's authorized tmp.
allowed=scratch/'guard-inside';allowed.mkdir();outside=scratch/'guard-outside';outside.mkdir()
# Establish effect controls independently of the denied traversal operations.
(outside/'rmdir-target').mkdir();(outside/'outside.txt').write_bytes(b'AUTHORED_OUTSIDE')
(allowed/'positive-delete').mkdir();(allowed/'positive-remove.txt').write_bytes(b'AUTHORED_INSIDE')
(allowed/'alias').symlink_to(outside,target_is_directory=True)
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
# Independent pre-existing outside effect controls were created before guard.
fd=os.open(allowed,os.O_RDONLY)
def guarded_refusal(name,fn,effect_unchanged):
    before=guard_budget.denials;blocked=refusal(fn)
    record(name,blocked and effect_unchanged() and guard_budget.denials>before,sticky_denial=guard_budget.denials>before)
try:
    guarded_refusal('absolute_parent_mkdir',lambda:os.mkdir(allowed/'..'/'guard-outside'/'escaped'),lambda:not (outside/'escaped').exists())
    guarded_refusal('relative_dirfd_parent_rmdir',lambda:os.rmdir('../guard-outside/rmdir-target',dir_fd=fd),lambda:(outside/'rmdir-target').is_dir())
    guarded_refusal('relative_dirfd_parent_mkdir',lambda:os.mkdir('../guard-outside/escaped-relative',dir_fd=fd),lambda:not (outside/'escaped-relative').exists())
    guarded_refusal('absolute_parent_remove',lambda:os.remove(allowed/'..'/'guard-outside'/'outside.txt'),lambda:(outside/'outside.txt').is_file())
    guarded_refusal('relative_dirfd_parent_remove',lambda:os.remove('../guard-outside/outside.txt',dir_fd=fd),lambda:(outside/'outside.txt').is_file())
    guarded_refusal('absolute_alias_mkdir',lambda:os.mkdir(allowed/'alias'/'escaped-alias'),lambda:not (outside/'escaped-alias').exists())
    guarded_refusal('relative_dirfd_alias_mkdir',lambda:os.mkdir('alias/escaped-alias-relative',dir_fd=fd),lambda:not (outside/'escaped-alias-relative').exists())
    guarded_refusal('unknown_dirfd_rmdir',lambda:os.rmdir('positive-delete',dir_fd=90),lambda:(allowed/'positive-delete').is_dir())
    oldmode=(outside/'outside.txt').stat().st_mode
    guarded_refusal('relative_dirfd_parent_chmod',lambda:os.chmod('../guard-outside/outside.txt',0o777,dir_fd=fd),lambda:(outside/'outside.txt').stat().st_mode==oldmode)
    absolute=allowed/'positive-absolute';os.mkdir(absolute);os.chmod(absolute,0o700);os.rmdir(absolute)
    record('positive_absolute_mutations',not absolute.exists())
    os.mkdir('positive-relative',dir_fd=fd);os.chmod('positive-relative',0o700,dir_fd=fd);os.rmdir('positive-relative',dir_fd=fd)
    record('positive_relative_dirfd_mutations',not (allowed/'positive-relative').exists())
    os.remove('positive-remove.txt',dir_fd=fd);os.rmdir('positive-delete',dir_fd=fd)
    record('positive_relative_remove_rmdir',not (allowed/'positive-remove.txt').exists() and not (allowed/'positive-delete').exists())
finally:os.close(fd)
# Closing tracked fd invalidates it; stale use must be denied before filesystem effect.
guarded_refusal('stale_dirfd_rmdir',lambda:os.rmdir('read.txt',dir_fd=fd),lambda:inside.is_file())
record('guard_SQL_wrong_path',refusal(lambda:sqlite3.connect(str(allowed/'foreign.sqlite'))))
# Report only fixed observations/counters. Guard fixture is deliberately kept
# for parent-owned cleanup after this disposable process exits.
assert not any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules)
report={'kind':'AUTHOR_CORRECTED_CLOSED_HELPER_AUTHORED_PROBE','runtime':sys.version.split()[0],'observations':OBS,'checks':len(OBS),'failed_case_names':[o['case'] for o in OBS if not o['pass']],'guard_counters':{'reads':guard_budget.reads,'writes':guard_budget.writes,'console':guard_budget.console,'denials':guard_budget.denials},'scratch':str(scratch),'actual_closed_inputs':0,'candidate_owner_imports':0,'real_subprocesses':0,'network_calls':0,'cost_usd':0,'wall_seconds':time.monotonic()-START,'author_resource_counters':AUTHOR}
text=json.dumps(report,sort_keys=True)
assert len(text.encode())<262144
print(text)
raise SystemExit(1 if report['failed_case_names'] else 0)
