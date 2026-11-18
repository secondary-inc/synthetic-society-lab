#!/usr/bin/env python3
"""V1.1 corrected future reviewed one-child CLOSED replay. No prepare/bootstrap/live mode.

Only production_owner_directory is redirected. Private state is reconstructed
for comparison, never adopted as replay state. No candidate execution by author.
"""
import argparse
import builtins
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import selectors
import shutil
import signal
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
SCOPE=ROOT/'data/processed/e02_canary_closed_replay_v1_20261117_01'
CLOSURE=ROOT/'reports/evidence_e02_canary_closed_replay_code_v1_20261117/EXACT_CLOSURE_WITH_HELPER.json'
EXPORT=ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/post-run-owner-export.local.json'
REGISTRATION=ROOT/'data/processed/e02_canary_closed_registration_20261117_01/openrouter-v4-bootstrap.local.json'
DIRFD=ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py'
LIMITS={'wall_seconds':300,'CPU_seconds':120,'read_bytes':536870912,'write_bytes':67108864,'console_bytes':65536,'children':1,'verify_calls':1,'retries':0}
EXPORT_PIN={'bytes':3893676,'sha256':'ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66'}
REGISTRATION_PIN={'bytes':546,'sha256':'920278f3258c856f60959cf7bd380a944cc09d797084552698dd7ae7024a54e9'}
SQL_WRITE_RESERVE=48*1024*1024  # main DB <=24MiB plus rollback <=24MiB
SQL_READ_RESERVE=24*1024*1024   # native materialization reads, charged in addition to Python/SQL rows


class Refused(Exception):pass

def need(value,code):
    if not value:raise Refused(code)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def no_alias(path):
    need(path.is_absolute() and not any(p.is_symlink() for p in (path,*path.parents)),'ALIASED_PATH')


class Budget:
    def __init__(self):self.reads=0;self.writes=0;self.console=0;self.denials=0
    def charge(self,kind,n):
        need(type(n) is int and n>=0,'INVALID_BYTE_CHARGE')
        attr={'read_bytes':'reads','write_bytes':'writes','console_bytes':'console'}[kind]
        value=getattr(self,attr)+n;setattr(self,attr,value)
        need(value<=LIMITS[kind],'RESOURCE_LIMIT')
    def deny(self):self.denials+=1;raise Refused('GUARD_DENIAL')


def read_pinned(path,pin,budget):
    no_alias(path);need(path.is_file() and path.stat().st_size==pin['bytes'],'PIN_SIZE')
    # These pre-guard/preflight reads reserve whole-file content explicitly.
    budget.charge('read_bytes',pin['bytes'])
    raw=path.read_bytes();need(len(raw)==pin['bytes'] and digest(raw)==pin['sha256'],'PIN_HASH')
    return raw


def read_control(path,expected_sha,budget):
    no_alias(path);need(path.is_file() and path.stat().st_size<=262144,'CONTROL_FILE_BOUND')
    budget.charge('read_bytes',path.stat().st_size)
    raw=path.read_bytes();need(digest(raw)==expected_sha,'EXACT_CONTROL_HASH')
    return json.loads(raw)


def gate(args,budget):
    q=read_control(SCOPE/'execution-contract.json',args.contract_sha256,budget)
    need(set(q)=={'kind','helper','closure','dirfd','limits','runtime','scope'},'CONTRACT_SCHEMA')
    need(q['kind']=='E02_CLOSED_REPLAY_EXECUTION_CONTRACT_V1' and q['limits']==LIMITS
         and q['runtime']=='3.12.14' and q['scope']=='PARENT_ONLY_1180_NO_NEW_EVENTS','CONTRACT_SCOPE')
    read_pinned(Path(__file__).resolve(),q['helper'],budget)
    read_pinned(DIRFD,q['dirfd'],budget)
    closure=json.loads(read_pinned(CLOSURE,q['closure'],budget))
    review=read_control(SCOPE/'accepted-review.json',args.review_sha256,budget)
    need(set(review)=={'kind','reviewer_role','decision','contract_sha256','helper_sha256','closure_sha256','independent_report_sha256','lead_release'},'REVIEW_SCHEMA')
    need(review['kind']=='INDEPENDENT_CLOSED_REPLAY_HELPER_RELEASE_V1'
         and review['reviewer_role']=='independent_auditor' and review['decision']=='PASS_EXACT_HELPER_AND_GUARDS'
         and review['contract_sha256']==args.contract_sha256 and review['helper_sha256']==q['helper']['sha256']
         and review['closure_sha256']==q['closure']['sha256'] and review['lead_release']=='ONE_CHILD_ONE_VERIFY_ONLY'
         and type(review['independent_report_sha256']) is str and len(review['independent_report_sha256'])==64,'REVIEW_AND_LEAD_RELEASE')
    need(sys.version.split()[0]=='3.12.14' and closure['python']=='3.12.14','EXACT_RUNTIME')
    return q,closure


def private_write(path,raw,budget):
    no_alias(path);budget.charge('write_bytes',len(raw))
    with path.open('xb') as stream:
        os.chmod(path,0o600);stream.write(raw);stream.flush();os.fsync(stream.fileno())


def preflight(closure,budget):
    need(set(closure)>={'project_pins','stdlib_pins','prewarm_modules'},'CLOSURE_SCHEMA')
    seen=set()
    for pin in closure['project_pins']:
        path=ROOT/pin['path'];need(path.is_relative_to(ROOT) and '..' not in path.parts,'PROJECT_PATH')
        need(str(path) not in seen,'DUPLICATE_CLOSURE');seen.add(str(path));read_pinned(path,pin,budget)
    for pin in closure['stdlib_pins']:
        path=Path(pin['path']);need(str(path) not in seen,'DUPLICATE_RUNTIME');seen.add(str(path));read_pinned(path,pin,budget)
    read_pinned(EXPORT,EXPORT_PIN,budget);read_pinned(REGISTRATION,REGISTRATION_PIN,budget)


class Stream:
    """Charge Python stream reads/writes as well as conservative open reservations."""
    def __init__(self,stream,budget):self.stream=stream;self.budget=budget
    def __getattr__(self,n):
        if n in ('buffer','raw','detach'):self.budget.deny()
        return getattr(self.stream,n)
    def __enter__(self):return self
    def __exit__(self,*a):return self.stream.__exit__(*a)
    def measured(self,data):
        self.budget.charge('read_bytes',len(data.encode() if isinstance(data,str) else data));return data
    def read(self,*a):return self.measured(self.stream.read(*a))
    def read1(self,*a):return self.measured(self.stream.read1(*a))
    def readline(self,*a):return self.measured(self.stream.readline(*a))
    def readlines(self,*a):
        values=self.stream.readlines(*a)
        for value in values:self.measured(value)
        return values
    def readinto(self,b):
        n=self.stream.readinto(b);self.budget.charge('read_bytes',n or 0);return n
    def __iter__(self):return self
    def __next__(self):
        line=self.readline()
        if not line:raise StopIteration
        return line
    def write(self,data):
        self.budget.charge('write_bytes',len(data.encode() if isinstance(data,str) else data));return self.stream.write(data)
    def writelines(self,items):
        for item in items:self.write(item)


class Console:
    def __init__(self,stream,budget):self.stream=stream;self.budget=budget
    def write(self,s):self.budget.charge('console_bytes',len(s.encode()));return self.stream.write(s)
    def flush(self):return self.stream.flush()


def install_guard(closure,tmp,db_path,budget,dirfd_pin):
    # Execute the reviewed source bytes, never an unchecked cached .pyc.
    raw=read_pinned(DIRFD,dirfd_pin,budget)
    namespace={'__name__':'closed_replay_dirfd_guard','__file__':str(DIRFD)}
    exec(compile(raw,str(DIRFD),'exec'),namespace)
    permitted={ROOT/p['path'] for p in closure['project_pins']}|{Path(p['path']) for p in closure['stdlib_pins']}|{EXPORT,REGISTRATION,DIRFD,Path(__file__).resolve()}
    permitted_directories={p.parent for p in permitted}|{ROOT/'src'}
    sqlite_opens=[0]
    # -B disallows writes; a dedicated uncreated prefix prevents reading stale project caches.
    sys.pycache_prefix=str(tmp/'UNCREATED_PYC_CACHE')
    missing_caches={Path(importlib.util.cache_from_source(str(p))) for p in permitted if p.suffix=='.py'}
    def policy(path,flags):
        try:no_alias(path)
        except Refused:budget.deny()
        write=bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if write:
            if not path.is_relative_to(tmp):budget.deny()
        elif path in missing_caches:
            if path.exists():budget.deny()
        elif path.is_relative_to(tmp):
            if path.is_file():budget.charge('read_bytes',path.stat().st_size)
        elif path in permitted:budget.charge('read_bytes',path.stat().st_size)
        else:budget.deny()
    descriptor=namespace['DirectoryFdGuard'](policy)
    def mutation_path(event,args):
        value=args[0]
        if isinstance(value,int):budget.deny()
        raw=os.fsdecode(value)
        # Reject raw parent components before normalization or any syscall.
        if '..' in Path(raw).parts:budget.deny()
        if os.path.isabs(raw):path=descriptor.absolute(raw)
        else:
            index={'os.mkdir':2,'os.chmod':2,'os.remove':1,'os.rmdir':1}.get(event)
            fd=args[index] if index is not None and len(args)>index else None
            if fd in (None,-1):path=descriptor.absolute(raw)
            else:
                origin=descriptor.directory(fd)[0]
                path=descriptor.absolute(origin/raw)
        if not path.is_relative_to(tmp):budget.deny()
        try:no_alias(path)
        except Refused:budget.deny()
        return path
    def guarded_audit(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.spawn','os.system','os.putenv','os.unsetenv','ctypes.dlopen','ctypes.dlsym','mmap.__new__'}:budget.deny()
        if event=='import' and len(args)>1 and args[1] and str(args[1]).endswith(('.so','.dylib')):
            if Path(args[1]).resolve() not in permitted:budget.deny()
        if event=='open':
            if isinstance(args[0],int):
                # Existing owned descriptors are admitted only by fdopen after fixed path open.
                if args[0] not in descriptor.records:budget.deny()
            else:policy(descriptor.event_path(args[0]),args[2])
        if event=='sqlite3.connect':
            sqlite_opens[0]+=1
            expected=str(db_path) if sqlite_opens[0]==1 else db_path.as_uri()+'?mode=ro&immutable=1'
            if sqlite_opens[0]>2 or str(args[0])!=expected:budget.deny()
        if event in {'os.listdir','os.scandir'}:
            value=args[0]
            path=descriptor.directory(value)[0] if type(value) is int else descriptor.absolute(value)
            if not path.is_relative_to(tmp) and path not in permitted_directories:budget.deny()
        if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.link','os.symlink','os.chmod','os.truncate'}:
            if event in {'os.link','os.symlink','os.rename'}:budget.deny()
            mutation_path(event,args)
    def audit(event,args):
        try:guarded_audit(event,args)
        except namespace['GuardRefused']:budget.deny()
    sys.addaudithook(audit)
    def descriptor_open(*args,**kwargs):
        try:return descriptor.open(*args,**kwargs)
        except namespace['GuardRefused']:budget.deny()
    os.open=descriptor_open;os.close=descriptor.close
    for obj,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
        original=getattr(obj,name)
        def opened(*a,_original=original,**k):return Stream(_original(*a,**k),budget)
        setattr(obj,name,opened)
    def denied_descriptor(*a,**k):budget.deny()
    for name in ('read','pread','readv','writev','pwrite','lseek','ftruncate','sendfile'):
        if hasattr(os,name):setattr(os,name,denied_descriptor)
    raw_write=os.write
    def write(fd,data):
        if fd not in (1,2):budget.deny()
        budget.charge('console_bytes',len(data));return raw_write(fd,data)
    os.write=write
    sys.stdout=Console(sys.stdout,budget);sys.stderr=Console(sys.stderr,budget)


class ReadOnlySQL:
    """Preserve SELECT semantics and charge logical serialized native results."""
    QUERIES={'SELECT data FROM header','SELECT sequence,data,digest FROM events ORDER BY sequence LIMIT 10001','SELECT id,data FROM charges LIMIT 1025'}
    def __init__(self,db,budget):self.db=db;self.budget=budget
    def execute(self,sql):
        if sql not in self.QUERIES:self.budget.deny()
        cursor=self.db.execute(sql);budget=self.budget
        class Result:
            def fetchall(self):
                rows=cursor.fetchall()
                budget.charge('read_bytes',sum(len(v.encode()) if isinstance(v,str) else 8 for row in rows for v in row))
                return rows
        return Result()


def child(args):
    budget=Budget();stage='GATE';tmp=SCOPE/'temporary-fixture';created=False;result=None;verify_calls=0
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(Refused('WALL_LIMIT')))
    signal.setitimer(signal.ITIMER_REAL,300);start=time.monotonic()
    try:
        q,closure=gate(args,budget)
        claim=read_control(SCOPE/'invocation.claim.json',args.claim_sha256,budget)
        need(claim['parent_pid']==os.getppid() and claim['contract_sha256']==args.contract_sha256,'SINGLE_PARENT_CLAIM')
        budget.charge('read_bytes',claim['supervisor_charged_read_bytes'])
        budget.charge('write_bytes',claim['supervisor_write_reservation_bytes'])
        remaining=claim['parent_deadline_monotonic']-time.monotonic()
        need(0<remaining<=300,'PARENT_DEADLINE')
        signal.setitimer(signal.ITIMER_REAL,remaining)
        private_write(SCOPE/'child.claim.json',canonical({'kind':'ONE_CHILD_CONSUMED','pid':os.getpid()}),budget)
        stage='PREFLIGHT';preflight(closure,budget)
        # Explicit, reviewed stdlib prewarm is charged by exact module/cache/native pins.
        for name in closure['prewarm_modules']:importlib.import_module(name)
        need(not any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules),'NO_PREIMPORTED_CANDIDATE')
        stage='GUARD';no_alias(tmp);db_path=tmp/'owner'/'owner-v4.local.sqlite'
        install_guard(closure,tmp,db_path,budget,q['dirfd'])
        tmp.mkdir(mode=0o700);created=True;owner_path=tmp/'owner';owner_path.mkdir(mode=0o700)
        stage='RECONSTRUCT'
        export=json.loads(EXPORT.read_bytes());registration=REGISTRATION.read_bytes()
        guard=owner_path/'owner-v4-guard.local.json';head=owner_path/'owner-v4-head.local.json'
        private_write(guard,canonical(export['header']),budget);private_write(head,canonical(export['head']),budget)
        private_write(tmp/'openrouter-v4-bootstrap.local.json',registration,budget)
        budget.charge('write_bytes',SQL_WRITE_RESERVE);budget.charge('read_bytes',SQL_READ_RESERVE)
        with sqlite3.connect(db_path) as db:
            db.execute('PRAGMA page_size=4096');db.execute('PRAGMA max_page_count=6144')
            db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA temp_store=MEMORY')
            db.execute('CREATE TABLE header(data TEXT)');db.execute('CREATE TABLE events(sequence INTEGER PRIMARY KEY,data TEXT,digest TEXT)');db.execute('CREATE TABLE charges(id TEXT PRIMARY KEY,data TEXT)')
            db.execute('INSERT INTO header VALUES (?)',(canonical(export['header']).decode(),))
            db.executemany('INSERT INTO events VALUES (?,?,?)',[(e['sequence'],canonical(e).decode(),digest(canonical(e))) for e in export['history']])
            db.executemany('INSERT INTO charges VALUES (?,?)',[(key,canonical(row).decode()) for key,row in export['rows'].items()])
        db.close()
        os.chmod(db_path,0o400);os.chmod(guard,0o400);os.chmod(head,0o400);os.chmod(tmp/'openrouter-v4-bootstrap.local.json',0o400)
        need(not any(Path(str(db_path)+s).exists() for s in ('-wal','-shm','-journal')),'NO_SQL_SIDECARS')
        frozen={str(p):digest(p.read_bytes()) for p in (db_path,guard,head,tmp/'openrouter-v4-bootstrap.local.json')}
        stage='IMPORT';sys.path.insert(0,str(ROOT/'src'))
        from civiclab import production_owner_v4 as production
        from civiclab.e02.wrapper_crossmodel_canary_v1_owner import CanaryOwnerV1
        protected={(cls.__module__,cls.__name__,name):getattr(cls,name) for cls in CanaryOwnerV1.__mro__ for name in ('__init__','_location','_registration','_empty','_verify','_apply') if hasattr(cls,name)}
        original_route=production.production_owner_directory
        production.production_owner_directory=lambda:owner_path
        try:
            stage='CONSTRUCTOR';owner=CanaryOwnerV1()
            stage='VERIFY_ONCE'
            budget.charge('read_bytes',db_path.stat().st_size)
            with sqlite3.connect(db_path.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
                db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
                verify_calls+=1
                state,actual_head=owner._verify(ReadOnlySQL(db,budget))
            db.close()
            stage='COMPARE'
            checks={'head':actual_head==export['head'],'events':state['_prefix_events']==export['history'],'rows':state['rows']==export['rows'],'claims':sorted(state['statistics_claims'])==export['statistics_claims'],'consumed':state['consumed']==export['consumed'],'unfinished':state['unfinished']==export['unfinished']==5,'active':state['active']==export['active_approval_hash'],'study_authorities':state['study_authorities']==export['study_authorities'],'parent_stopped':state['wrapper_crossmodel']['stopped'] is True,'no_canary_branch':'wrapper_crossmodel_canary_v1' not in state,'five_holds':sorted(row['charged'] for row in state['rows'].values() if row['status']!='PHASE_COMMITTED')==[340,340,775,788,1008]}
            for key in ('study','continuation','alignment_followup','issue_cue_crossmodel','issue_cue_crossmodel_recovery','wrapper_visibility','wrapper_crossmodel'):checks[key]=state[key]==export[key]
            checks['protected_methods_unchanged']=all(getattr(cls,name) is protected[(cls.__module__,cls.__name__,name)] for cls in CanaryOwnerV1.__mro__ for name in ('__init__','_location','_registration','_empty','_verify','_apply') if hasattr(cls,name))
            checks['derived_files_unchanged']=all(digest(Path(p).read_bytes())==h for p,h in frozen.items())
            checks['project_inputs_unchanged']=all(digest((ROOT/p['path']).read_bytes())==p['sha256'] for p in closure['project_pins'])
            checks['no_denials']=budget.denials==0
            need(all(checks.values()),'CLOSED_REPLAY_COMPARISON')
            result={'kind':'CLOSED_PARENT_REPLAY_RESULT_V1','status':'PASS_PARENT_ONLY','checks':checks,'events':1180,'rows':194,'verify_calls':1,'conservative_exposure_microusd':16149,'API_calls':0,'credentials_read':0,'current_owner_access':0,'new_canary_events':0}
        finally:production.production_owner_directory=original_route
    except BaseException as error:
        result={'kind':'CLOSED_PARENT_REPLAY_RESULT_V1','status':'STOPPED_NOT_QUALIFIED','stage':stage,'error_type':type(error).__name__ if type(error) in (Refused,ValueError,TypeError,OSError,ImportError,ModuleNotFoundError,RuntimeError) else 'OTHER','verify_calls':verify_calls,'API_calls':0,'credentials_read':0,'current_owner_access':0}
    finally:
        cleanup=False
        if created:
            try:shutil.rmtree(tmp);cleanup=not tmp.exists()
            except BaseException:cleanup=False
        if result is None:result={'kind':'CLOSED_PARENT_REPLAY_RESULT_V1','status':'STOPPED_NOT_QUALIFIED'}
        if not cleanup:result['status']='STOPPED_NOT_QUALIFIED'
        result.update({'temporary_fixture_removed':cleanup,'charged_read_bytes':budget.reads,'charged_write_bytes':budget.writes,'guard_denials':budget.denials,'console_bytes_before_result':budget.console,'wall_seconds':time.monotonic()-start,'CPU_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,'prewarm_and_native_boundary':'Exact reviewed stdlib/cache/native input pins charged conservatively. Implicit interpreter/native-loader OS reads and physical syscalls are not claimed as whole-process measured I/O; SQLite native reads/writes reserved separately and SELECT payload bytes charged.'})
        print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='PASS_PARENT_ONLY' else 1


def fixture_disposition(scope,child_record):
    """Metadata only: never follow/delete a leftover fixture after forced kill."""
    path=scope/'temporary-fixture';alias=path.is_symlink()
    present=alias or path.exists()
    return {'disposition':'QUARANTINED_PRIVATE_NO_RETRY' if present else 'NO_FIXTURE_PRESENT',
            'path_present':present,'path_is_alias':alias,
            'child_cleanup_reported':bool(child_record and child_record.get('temporary_fixture_removed') is True),
            'supervisor_cleanup_attempted':False,
            'followup':'SEPARATE_BOUNDED_LEAD_CLEANUP_REQUIRED' if present else 'NONE'}


def supervise(args):
    started=time.monotonic()
    parent_cpu_started=resource.getrusage(resource.RUSAGE_SELF)
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(Refused('SUPERVISOR_WALL_LIMIT')))
    signal.setitimer(signal.ITIMER_REAL,300)
    budget=Budget();q,closure=gate(args,budget);preflight(closure,budget)
    budget.charge('write_bytes',131072)  # reserve parent terminal/receipt before spawning
    claim=canonical({'kind':'ONE_CLOSED_REPLAY_INVOCATION_CONSUMED','parent_pid':os.getpid(),'contract_sha256':args.contract_sha256,'helper_sha256':q['helper']['sha256'],'supervisor_charged_read_bytes':budget.reads,'supervisor_write_reservation_bytes':budget.writes+4096,'parent_deadline_monotonic':started+300})
    private_write(SCOPE/'invocation.claim.json',claim,budget)
    cmd=[sys.executable,'-I','-B','-S',str(Path(__file__).resolve()),'--child','--contract-sha256',args.contract_sha256,'--review-sha256',args.review_sha256,'--claim-sha256',digest(claim)]
    before=resource.getrusage(resource.RUSAGE_CHILDREN)
    process=subprocess.Popen(cmd,cwd=ROOT,env={'PATH':'/usr/bin:/bin'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    output=bytearray();selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ);reason='EXIT'
    try:
        while selector.get_map():
            if time.monotonic()-started>=300:reason='PARENT_WALL_STOP';process.kill();break
            for key,_ in selector.select(timeout=1):
                part=os.read(key.fileobj.fileno(),min(4096,65537-len(output)))
                if not part:selector.unregister(key.fileobj);continue
                output.extend(part)
                if len(output)>65536:reason='PARENT_CONSOLE_STOP';process.kill();break
            if reason!='EXIT':break
    except BaseException:
        reason='PARENT_INTERRUPTED'
    finally:
        selector.close()
        if reason=='EXIT' and process.poll() is None:
            try:process.wait(timeout=max(.001,min(5,300-(time.monotonic()-started))))
            except subprocess.TimeoutExpired:reason='PARENT_EXIT_WAIT_STOP'
            except BaseException:reason='PARENT_INTERRUPTED'
        if process.poll() is None:process.kill()
        process.wait(timeout=10);process.stdout.close()
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    # Charge supervisor preflight in the common qualification read ceiling too.
    parsed=None
    try:
        parsed=json.loads(output.decode());need(type(parsed) is dict,'CHILD_RECORD')
    except BaseException:parsed=None
    aggregate_reads=parsed.get('charged_read_bytes',budget.reads) if parsed else budget.reads
    valid=parsed is not None and parsed.get('kind')=='CLOSED_PARENT_REPLAY_RESULT_V1'
    quarantine=fixture_disposition(SCOPE,parsed if valid else None)
    cpu=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime
    success=reason=='EXIT' and process.returncode==0 and valid and parsed.get('status')=='PASS_PARENT_ONLY' and aggregate_reads<=LIMITS['read_bytes'] and parsed.get('charged_write_bytes',LIMITS['write_bytes']+1)<=LIMITS['write_bytes'] and parsed.get('guard_denials')==0 and parsed.get('temporary_fixture_removed') is True and parsed.get('verify_calls')==1 and cpu<=120 and time.monotonic()-started<300 and not quarantine['path_present']
    receipt={'kind':'CLOSED_PARENT_REPLAY_SUPERVISOR_V1','status':'PASS_PARENT_ONLY' if success else 'STOPPED_NOT_QUALIFIED','child_exit':process.returncode,'reason':reason,'wall_seconds':time.monotonic()-started,'child_CPU_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'console_bytes':len(output),'console_sha256':digest(output),'aggregate_charged_read_bytes':aggregate_reads,'supervisor_charged_write_bytes':budget.writes,'child_record':parsed if valid else None,'one_child':True,'retries':0,'contract_sha256':args.contract_sha256,'review_sha256':args.review_sha256}
    parent_cpu_now=resource.getrusage(resource.RUSAGE_SELF)
    receipt.update({'CPU_scope':'CHILD_LIMIT_120_PARENT_OBSERVED_SEPARATELY',
                    'supervisor_CPU_seconds':parent_cpu_now.ru_utime+parent_cpu_now.ru_stime-parent_cpu_started.ru_utime-parent_cpu_started.ru_stime,
                    'fixture_disposition':quarantine})
    private_write(SCOPE/'safe-child-console.jsonl',bytes(output),budget)
    private_write(SCOPE/'safe-supervisor-receipt.json',canonical(receipt),budget)
    print(json.dumps({'status':receipt['status'],'child_exit':process.returncode,'one_child':True,'live_release':False},sort_keys=True))
    return 0 if success else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract-sha256',required=True);parser.add_argument('--review-sha256',required=True)
    parser.add_argument('--child',action='store_true',help=argparse.SUPPRESS);parser.add_argument('--claim-sha256',help=argparse.SUPPRESS)
    args=parser.parse_args();return child(args) if args.child else supervise(args)


if __name__=='__main__':
    try:raise SystemExit(main())
    except SystemExit:raise
    except BaseException:
        print(json.dumps({'status':'STOPPED_NOT_QUALIFIED','stage':'SUPERVISOR_GATE','live_release':False}))
        raise SystemExit(1)
