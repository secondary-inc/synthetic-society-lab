"""One-call offline saved-JSON entry; root supplies the reviewed armed packet.

No API creates an armed production packet. Authored execution is confined to an
owned fixture root and reader double. Core component/old entries stay unchanged.
Trusted interpreter/stdlib prewarm is outside the logical saved/project IO caps.
"""
import errno
import hashlib
import importlib.abc
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
from types import MappingProxyType,ModuleType

LIMITS={'wall_seconds':60,'work_seconds':57,'cleanup_seconds':2,'finalization_seconds':1,'CPU_seconds':30,
 'saved_JSON_bytes':8388608,'project_source_bytes':1048576,'write_bytes':2097152,'public_bytes':131072,'console_bytes':16384,'reader_calls':1,'retries':0}
CORE='src/civiclab/e01/saved_json_job_ledger_v1.py'
HELPER='src/civiclab/e01/saved_json_entry_v1.py'
LAUNCHER='scripts/run_e01_saved_json_entry_v1_20261117.py'
CONTROL='data/processed/e01_saved_json_one_call_control_v1'


class Refused(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise Refused(code)
def packed(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def closed(v,keys):return type(v) is dict and set(v)==set(keys)
def hash_ok(v):return type(v) is str and re.fullmatch('[0-9a-f]{64}',v) is not None
def strict(raw):
    need(type(raw) is bytes and len(raw)<=4194304,'JSON_BOUND')
    def pairs(items):
        result={}
        for k,v in items:need(k not in result,'JSON_DUPLICATE');result[k]=v
        return result
    def number(token):
        value=float(token);need(math.isfinite(value),'JSON_NONFINITE');return value
    def invalid(_):raise Refused('JSON_NONFINITE')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_float=number,parse_constant=invalid)
    except (UnicodeError,ValueError,RecursionError):raise Refused('JSON_INVALID') from None

def relative(v):
    need(type(v) is str and v and '\x00' not in v and '\\' not in v and ':' not in v,'PATH')
    p=Path(v);need(not p.is_absolute() and '..' not in p.parts and str(p)==v,'PATH');return v

def reference(v):
    need(closed(v,('path','bytes','sha256')) and type(v['bytes']) is int and 0<=v['bytes']<=4194304 and hash_ok(v['sha256']),'REFERENCE')
    relative(v['path'])


class Budget:
    """Shared logical counters;57s work,2s cleanup,1s finalization."""
    def __init__(self,start=None,clock=time.monotonic,cancel=lambda:False,initial=None):
        self.clock=clock;self.cancel=cancel;self.start=clock() if start is None else start;self.previous=self.start
        need(type(self.start) in {int,float} and math.isfinite(self.start),'CLOCK')
        self.saved=self.project=self.written=self.calls=0;self.primary=None;self.closed=False
        if initial is not None:
            need(closed(initial,('saved_JSON_bytes','project_source_bytes','write_bytes')) and all(type(v) is int and v>=0 for v in initial.values()),'INITIAL_USAGE')
            self.saved=initial['saved_JSON_bytes'];self.project=initial['project_source_bytes'];self.written=initial['write_bytes']
            need(self.saved<=8388608 and self.project<=1048576 and self.written<=2097152,'INITIAL_CAP')
    def fail(self,code):
        if self.primary is None:self.primary=Refused(code)
        raise self.primary
    def now(self):
        value=self.clock()
        if type(value) not in {int,float} or not math.isfinite(value) or value<self.previous:self.fail('CLOCK')
        self.previous=value;return value
    def check(self):
        if self.primary:raise self.primary
        if self.closed:self.fail('CLOSED')
        value=self.now();cancelled=self.cancel()
        if type(cancelled) is not bool or cancelled:self.fail('CANCELLED')
        if value>=self.start+57:self.fail('WORK_DEADLINE')
    def read(self,n,project=False):
        self.check()
        if type(n) is not int or n<0:self.fail('READ_AMOUNT')
        name='project' if project else 'saved';limit=1048576 if project else 8388608
        if getattr(self,name)+n>limit:self.fail('PROJECT_CAP' if project else 'SAVED_CAP')
        setattr(self,name,getattr(self,name)+n)
    def write(self,n,control=False):
        if not control:self.check()
        elif self.now()>=self.start+60:raise Refused('FINALIZATION_DEADLINE')
        if type(n) is not int or n<0 or self.written+n>2097152-(0 if control else 8192):self.fail('WRITE_CAP')
        self.written+=n
    def summary(self):return {'saved_JSON_bytes':self.saved,'project_source_bytes':self.project,'write_bytes':self.written,'reader_calls':self.calls,'failed':self.primary is not None}


def root_fd(root):
    root=Path(root).absolute();need('..' not in root.parts,'ROOT')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in root.parts[1:]:
            new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new
        return fd
    except BaseException:os.close(fd);raise

def directory_fd(root,path,create=False):
    relative(path);fd=root_fd(root)
    try:
        for part in Path(path).parts:
            if create:
                try:os.mkdir(part,0o700,dir_fd=fd)
                except FileExistsError:pass
            new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new
        return fd
    except BaseException:os.close(fd);raise


def read_bound(root,ref,budget,project=False):
    reference(ref);fd=None;parent=None
    try:
        p=Path(ref['path']);parent=directory_fd(root,str(p.parent))
        fd=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent);before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size==ref['bytes'],'FILE_SIZE_OR_TYPE')
        budget.read(before.st_size+1,project)
        with os.fdopen(fd,'rb') as f:
            fd=None;raw=f.read(before.st_size+1);after=os.fstat(f.fileno())
        identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(identity(before)==identity(after) and len(raw)==ref['bytes'] and sha(raw)==ref['sha256'],'FILE_HASH_OR_DRIFT')
        return raw
    except OSError:budget.fail('INPUT_IO')
    except Refused as error:budget.fail(error.code)
    finally:
        if fd is not None:os.close(fd)
        if parent is not None:os.close(parent)


def membership(root,prefix,names,budget):
    fd=None
    try:
        budget.check();fd=directory_fd(root,prefix);entries=os.listdir(fd)
        need(set(entries) in (set(names),set(names)|{'.lock'}),'DIRECTORY_MEMBERSHIP')
        for name in entries:
            s=os.stat(name,dir_fd=fd,follow_symlinks=False)
            need(stat.S_ISREG(s.st_mode) and (name!='.lock' or s.st_size<=4096),'DIRECTORY_MEMBER_TYPE')
        budget.check()
    except OSError:budget.fail('INPUT_IO')
    except Refused as error:budget.fail(error.code)
    finally:
        if fd is not None:os.close(fd)


def packet(raw,expected_sha,authored=False,now=time.time):
    need(hash_ok(expected_sha) and sha(raw)==expected_sha,'PACKET_HASH');p=strict(raw)
    need(closed(p,('kind','armed','issued_by','scope_id','issued_at','expires_at','limits','manifest','code_refs','review_refs','runtime_sha256')),'PACKET_SCHEMA')
    need(p['kind']=='E01_SAVED_JSON_ROOT_ONE_CALL_V1' and p['armed'] is True,'UNARMED')
    need(p['issued_by']==('AUTHORED_TEST_ONLY' if authored else 'ROOT_REVIEWED_ONE_CALL'),'ROOT_RELEASE')
    need(type(p['scope_id']) is str and re.fullmatch('e01-saved-json-[0-9a-f]{32}',p['scope_id']),'SCOPE_ID')
    need(type(p['issued_at']) is int and type(p['expires_at']) is int and p['issued_at']<=now()<p['expires_at']<=p['issued_at']+3600,'RELEASE_WINDOW')
    need(packed(p['limits'])==packed(LIMITS) and hash_ok(p['runtime_sha256']),'LIMITS')
    need(type(p['manifest']) is dict and p['manifest'].get('runtime_sha256')==p['runtime_sha256'],'MANIFEST_RUNTIME')
    need(type(p['code_refs']) is dict and set(p['code_refs'])=={CORE,HELPER,LAUNCHER},'CODE_SET')
    need(type(p['review_refs']) is dict and set(p['review_refs'])=={'component','entry'},'REVIEW_SET')
    for name,r in p['code_refs'].items():reference(r);need(r['path']==name,'CODE_PATH')
    for r in p['review_refs'].values():reference(r);need(r['path'].startswith('reports/'),'REVIEW_PATH')
    return p


def authored_root(root):
    need(Path(root).name.startswith('ssl-saved-json-entry-fixture-'),'AUTHORED_ROOT_REQUIRED')


def verify_controls(root,p,budget):
    code={}
    for name,r in p['code_refs'].items():code[name]=read_bound(root,r,budget,True)
    for r in p['review_refs'].values():strict(read_bound(root,r,budget))
    return code


def load_core(raw,filename):
    module=ModuleType('ssl_saved_json_core');module.__file__=str(filename)
    exec(compile(raw,str(filename),'exec'),module.__dict__);return module


class Control:
    def __init__(self,root,p,budget):
        self.root=root;self.packet=p;self.budget=budget;self.fd=None;self.spent=False;self.consumed=False
        self.path=CONTROL+'/'+p['scope_id']
    def new(self,name,value,control=False):
        need(name in {'STARTED.json','source_job_ledger.json','COMPLETE.json','FAILURE.json'},'OUTPUT_NAME')
        raw=packed(value);need(len(raw)<=131072,'PUBLIC_CAP');self.budget.write(len(raw),control)
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
        try:
            view=memoryview(raw)
            while view:
                n=os.write(fd,view);need(n>0,'OUTPUT_SHORT_WRITE');view=view[n:]
            os.fsync(fd)
        finally:os.close(fd)
    def consume(self):
        need(not self.spent,'SPENT_CONTROL');self.spent=True;self.budget.check()
        self.fd=directory_fd(self.root,self.path,True)
        self.new('STARTED.json',{'kind':'SAVED_JSON_ONE_CALL_STARTED','packet_sha256':sha(packed(self.packet)),
            'scope_id':self.packet['scope_id'],'no_retry':True,'start_monotonic':self.budget.start,'initial_usage':self.budget.summary()})
        self.consumed=True
    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None


class Admitted:
    """Real provenance snapshot; no relabeling through core's authored Bundle."""
    def __init__(self,root,p,core,runtime,budget,authored=False):
        m,refs,prefix=core.manifest_shape(packed(p['manifest']))
        if authored:
            authored_root(root);need(m['provenance']==core.AUTHORED,'AUTHORED_PROVENANCE')
        else:core.validate_actual_metadata(packed(m));need(m['provenance']==core.RECORDED,'RECORDED_PROVENANCE')
        need(runtime.sha256==p['runtime_sha256'],'RUNTIME_PIN');runtime.verify()
        membership(root,prefix,core.SAVED,budget)
        files={}
        for r in refs:
            files[r['path']]=read_bound(root,r,budget,r['path'] in m['project_refs'])
            if r['path'].endswith('.json'):core.strict_json(files[r['path']])
        c=core.strict_json(files[core.CONFIG]);need(core.digest(core.packed(c))==m['contract_sha256'],'CONTRACT_HASH')
        need(c['source_adoption'] is False,'CONFIG_ADOPTION')
        for role,r in m['reference_refs'].items():need(c['references'][role]=={'path':r['path'],'sha256':r['sha256']},'REFERENCE_JOIN')
        self.raw=packed(m);self.manifest=m;self.config=c;self.prefix=prefix;self.files=MappingProxyType(files);self.runtime=runtime;self.budget=budget
        self.dirs={core.ROOT,*core.ROOT.parents}
        for name in files:self.dirs.update((core.ROOT/name).parents)


class SourceLoader(importlib.abc.MetaPathFinder,importlib.abc.Loader):
    """Only fourteen already hashed project sources; trusted stdlib fallback."""
    def __init__(self,files,root):
        self.root=Path(root);self.sources={};self.loaded=set()
        for path,raw in files.items():
            if path.startswith('src/civiclab/') and path.endswith('.py'):
                parts=Path(path).relative_to('src').with_suffix('').parts
                package=parts[-1]=='__init__';name='.'.join(parts[:-1] if package else parts)
                self.sources[name]=(path,raw,package)
    def find_spec(self,name,path=None,target=None):
        if name=='civiclab' or name.startswith('civiclab.'):
            need(name in self.sources,'PROJECT_IMPORT_SCOPE')
            rel,_,package=self.sources[name]
            return importlib.util.spec_from_loader(name,self,origin=str(self.root/rel),is_package=package)
    def create_module(self,spec):return None
    def exec_module(self,module):
        rel,raw,package=self.sources[module.__name__];module.__file__=str(self.root/rel)
        if package:module.__path__=[str((self.root/rel).parent)]
        exec(compile(raw,module.__file__,'exec'),module.__dict__);self.loaded.add(module.__name__)
    def reader(self):
        need(not any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules),'PROJECT_ALREADY_IMPORTED')
        sys.meta_path.insert(0,self)
        try:
            import importlib
            module=importlib.import_module('civiclab.e01.ballots_v1_9_1')
            for name in self.loaded:
                obj=sys.modules[name];need(obj.__loader__ is self and obj.__spec__.origin==str(self.root/self.sources[name][0]),'PROJECT_ORIGIN')
            fn=module.read_verified_public
            need(fn.__module__=='civiclab.e01.ballots_v1_9_1' and fn.__code__.co_filename==str(self.root/'src/civiclab/e01/ballots_v1_9_1.py'),'READER_ORIGIN')
            return fn
        finally:sys.meta_path.remove(self)


def calculate(root,p,core,runtime,budget,authored=False,reader_double=None):
    bundle=Admitted(root,p,core,runtime,budget,authored)
    if authored:
        need(getattr(reader_double,'mock_only',False) is True,'AUTHORED_READER');reader=reader_double
    else:
        need(reader_double is None,'NO_READER_OVERRIDE');reader=SourceLoader({k:v for k,v in bundle.files.items() if k in bundle.manifest['project_refs']},root).reader()
    budget.check();need(budget.calls==0,'READER_SPENT');budget.calls=1
    with core.Guard(bundle):value=reader(core.ROOT/bundle.prefix,root=core.ROOT,contract=core.strict_json(bundle.files[core.CONFIG]))
    budget.check();need(packed(value)==packed(core.strict_json(bundle.files[bundle.prefix+'/typed_document_readiness.json'])),'READER_RESULT')
    ledger=core.project(value,bundle);budget.check();raw=packed(ledger);need(len(raw)<=131072,'PUBLIC_CAP');budget.write(len(raw))
    return ledger


def safe_error(error):
    code=getattr(error,'code',None)
    return code if type(code) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,63}',code) else 'UNCLASSIFIED_FAILURE'


def execute_authored(root,raw,expected_sha,core,runtime,reader_double,*,clock=time.monotonic,now=time.time,cancel=lambda:False):
    """Physical authored files + component VFS; never actual source reader."""
    authored_root(root);p=packet(raw,expected_sha,True,now);budget=Budget(clock=clock,cancel=cancel);budget.read(len(raw)+1)
    verify_controls(root,p,budget);need(runtime.sha256==p['runtime_sha256'],'RUNTIME_PIN');control=Control(root,p,budget);primary=None
    try:
        control.consume();ledger=calculate(root,p,core,runtime,budget,True,reader_double);validate_ledger(ledger,p,True)
        control.new('source_job_ledger.json',ledger);control.new('COMPLETE.json',{'status':'AUTHORED_ENTRY_ONLY','ledger_sha256':sha(packed(ledger)),'usage':budget.summary()});return ledger
    except BaseException as error:
        primary=budget.primary or error
        if control.consumed:
            try:control.new('FAILURE.json',{'status':'FAILED_UNACCEPTED','error_code':safe_error(primary),'usage':budget.summary(),'model_calls':0,'cost_usd':0},True)
            except BaseException:pass
        raise primary
    finally:control.close()


def cleanup(child,budget):
    if child.poll() is None:
        child.terminate()
        try:child.wait(timeout=max(0,min(1,budget.start+58-budget.now())))
        except subprocess.TimeoutExpired:
            child.kill();child.wait(timeout=max(0,budget.start+59-budget.now()))
    need(child.poll() is not None,'CHILD_NOT_REAPED');need(budget.now()<budget.start+60,'CLEANUP_DEADLINE')


def collect(child,budget):
    streams={'artifact':bytearray(),'console':bytearray()};caps={'artifact':131072,'console':16384};primary=None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout,selectors.EVENT_READ,'artifact');selector.register(child.stderr,selectors.EVENT_READ,'console')
            while selector.get_map():
                budget.check();left=budget.start+57-budget.previous
                for key,_ in selector.select(min(left,0.1)):
                    name=key.data;remaining=caps[name]-len(streams[name]);part=os.read(key.fd,min(4096,remaining+1))
                    if not part:selector.unregister(key.fileobj);continue
                    if len(part)>remaining:budget.fail('ARTIFACT_CAP' if name=='artifact' else 'CONSOLE_CAP')
                    streams[name].extend(part)
            budget.check();child.wait(timeout=max(0,budget.start+57-budget.previous));budget.check();need(child.returncode==0,'CHILD_EXIT')
    except BaseException as error:primary=budget.primary or error
    finally:
        try:cleanup(child,budget)
        except BaseException as error:
            if primary is None:primary=error
        child.stdout.close();child.stderr.close()
    if primary:raise primary
    return bytes(streams['artifact']),bytes(streams['console'])


def root_packet_file(root,path,expected_sha,budget):
    # Existing root-issued0600packet only; no arm/createfunction in this module.
    relative(path);need(path.startswith('data/processed/e01_saved_json_one_call_packets/'),'PACKET_DIRECTORY')
    fd=directory_fd(root,str(Path(path).parent));stream=None
    try:
        packetfd=os.open(Path(path).name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
        with os.fdopen(packetfd,'rb') as stream:
            before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_uid==os.getuid() and stat.S_IMODE(before.st_mode)==0o600 and before.st_size<=131072,'ROOT_PACKET_MODE')
            budget.read(before.st_size+1);raw=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
        need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'PACKET_DRIFT')
        return raw,packet(raw,expected_sha)
    finally:os.close(fd)



def validate_ledger(value,p,authored=False):
    keys=('kind','provenance','schema_version','metrics','state_dispositions','bindings','source_adoption','actual_selection','accepted_coverage_promoted','forecast_consumption','final_ballots_accepted','cost_usd','model_calls','interpretation')
    need(closed(value,keys),'LEDGER_SCHEMA')
    need(value['kind']=='E01_SAVED_JSON_SOURCE_JOB_LEDGER_V1' and value['provenance']==('AUTHORED_SAVED_JSON_FIXTURE' if authored else 'RECORDED_SAVED_READINESS_METADATA') and type(value['schema_version']) is int and value['schema_version']==1,'LEDGER_PROVENANCE')
    metrics={'regular_frame_slots':33,'legacy_roster_state_count':12,'typed_status_history_state_count':1,'document_state_coverage_count':13,'remaining_document_acquisition_jobs':20,'distinct_source_representation_count':40,'final_ballots_accepted':0}
    need(packed(value['metrics'])==packed(metrics),'LEDGER_METRICS')
    for k in ('source_adoption','actual_selection','accepted_coverage_promoted','forecast_consumption'):need(value[k] is False,'LEDGER_FLAGS')
    for k in ('final_ballots_accepted','cost_usd','model_calls'):need(type(value[k]) is int and value[k]==0,'LEDGER_COST')
    m=p['manifest'];expected={'config_file_sha256':m['config_ref']['sha256'],'config_contract_sha256':m['contract_sha256'],'reader_sha256':m['reader_ref']['sha256'],
       'reader_acceptance_sha256':m['acceptance_ref']['sha256'],'input_manifest_sha256':sha(packed(m)),'runtime_selected_origins_sha256':m['runtime_sha256']}
    need(value['bindings']==expected,'LEDGER_BINDINGS')
    states='AK AL AR CO DE GA IA ID IL KS KY LA MA ME MI MN MS MT NC NE NH NJ NM OK OR RI SC SD TN TX VA WV WY'.split()
    legacy='AK CO DE IA KS ME NC NE NH NJ VA WY'.split();rows=value['state_dispositions'];need(type(rows) is list and len(rows)==33,'LEDGER_ROWS')
    for i,(state,row) in enumerate(zip(states,rows)):
        kind='LEGACY_ROSTER_DOCUMENT' if state in legacy else 'GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY' if state=='ID' else 'NO_DOCUMENT_ADMITTED_FOR_ANY_REVIEWED_KIND'
        missing=state not in legacy and state!='ID'
        expected_row={'state':state,'document_kind':kind,'disposition':'NO_DOCUMENT_ADMITTED' if missing else 'SAVED_DOCUMENT_OBSERVATION_ONLY',
           'evidence':{'typed_public_sha256':m['saved_refs']['typed_document_readiness.json']['sha256'],'observation_index':i},
           'unresolved_conditions':{'DOCUMENT_ACQUISITION':'NO_ADMITTED_DOCUMENT' if missing else 'DOCUMENT_OBSERVED_ONLY',**{k:'NOT_ASSESSED' for k in ('LEGAL_CANDIDATE_STATUS','LATEST_AMENDMENT_COMPLETENESS','HISTORICAL_ASOF','GEOGRAPHY','RACE_SELECTION','FINAL_BALLOT')}}}
        need(packed(row)==packed(expected_row),'LEDGER_ROW')
    need(value['interpretation']=='Missing admitted document is not evidence that candidates do not exist. No AL promotion, final ballot or forecasting acceptance.','LEDGER_INTERPRETATION')
    need(len(packed(value))<=131072,'PUBLIC_CAP');return value


def production_parent(root,packet_path,expected_sha,start=None):
    """Rootaloneissuespacket. Thisfunctionnotusedbyauthoredqualification."""
    budget=Budget(start=start);raw,p=root_packet_file(root,packet_path,expected_sha,budget)
    code=verify_controls(root,p,budget);control=Control(root,p,budget)
    try:
        control.consume()
        initial={'saved_JSON_bytes':budget.saved,'project_source_bytes':budget.project,'write_bytes':budget.written}
        command=[sys.executable,'-I','-B','-S',str(Path(root)/LAUNCHER),'--worker','--root',str(Path(root).absolute()),'--packet',packet_path,'--packet-sha256',expected_sha,
                 '--start',repr(budget.start),'--initial',json.dumps(initial,separators=(',',':'))]
        child=subprocess.Popen(command,cwd=root,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        output,console=collect(child,budget);result=strict(output)
        need(closed(result,('status','ledger','usage')) and result['status']=='RECORDED_ONE_READER_CALL','CHILD_RESULT')
        usage=result['usage'];need(closed(usage,('saved_JSON_bytes','project_source_bytes','write_bytes','reader_calls','failed')),'CHILD_USAGE')
        need(all(type(usage[k]) is int and usage[k]>=getattr(budget,{'saved_JSON_bytes':'saved','project_source_bytes':'project','write_bytes':'written'}[k]) for k in ('saved_JSON_bytes','project_source_bytes','write_bytes')),'CHILD_USAGE_REGRESSION')
        need(usage['saved_JSON_bytes']<=8388608 and usage['project_source_bytes']<=1048576 and usage['write_bytes']<=2097152 and type(usage['reader_calls']) is int and usage['reader_calls']==1 and usage['failed'] is False,'CHILD_USAGE_CAP')
        budget.saved=usage['saved_JSON_bytes'];budget.project=usage['project_source_bytes'];budget.written=usage['write_bytes'];budget.calls=1
        ledger=validate_ledger(result['ledger'],p)
        budget.check();control.new('source_job_ledger.json',ledger);control.new('COMPLETE.json',{'status':'RECORDED_SAVED_METADATA_ONLY','ledger_sha256':sha(packed(ledger)),'usage':budget.summary(),'console_bytes':len(console),'model_calls':0,'cost_usd':0})
        return {'status':'RECORDED_SAVED_METADATA_ONLY','public_ledger_sha256':sha(packed(ledger)),'reader_calls':1,'model_calls':0,'cost_usd':0}
    except BaseException as error:
        primary=budget.primary or error
        if control.consumed:
            try:control.new('FAILURE.json',{'status':'FAILED_UNACCEPTED','error_code':safe_error(primary),'reader_call_status':'UNKNOWN_IF_CHILD_FAILED','usage':budget.summary(),'model_calls':0,'cost_usd':0},True)
            except BaseException:pass
        raise primary
    finally:control.close()


def claim_worker(fd,record,p,start,initial,n,budget,expected_sha):
    need(record['packet_sha256']==sha(packed(p)) and record['scope_id']==p['scope_id'] and record['no_retry'] is True and record['start_monotonic']==start,'CONSUME_JOIN')
    prior=record['initial_usage']
    need(initial=={'saved_JSON_bytes':prior['saved_JSON_bytes'],'project_source_bytes':prior['project_source_bytes'],'write_bytes':prior['write_bytes']+n},'SHARED_USAGE_JOIN')
    marker=packed({'kind':'WORKER_ONE_CALL_CONSUMED','packet_sha256':expected_sha,'scope_id':p['scope_id']})
    budget.write(len(marker));claim=os.open('WORKER_STARTED.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
    try:
        view=memoryview(marker)
        while view:
            count=os.write(claim,view);need(count>0,'WORKER_MARKER_WRITE');view=view[count:]
        os.fsync(claim)
    finally:os.close(claim)


def production_worker(root,packet_path,expected_sha,start,initial):
    budget=Budget(start=start,initial=initial);raw,p=root_packet_file(root,packet_path,expected_sha,budget)
    control_path=CONTROL+'/'+p['scope_id']+'/STARTED.json'
    # Rootpacket+consume are independently required; never create/reconsumehere.
    fd=directory_fd(root,str(Path(control_path).parent))
    try:
        with os.fdopen(os.open('STARTED.json',os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd),'rb') as stream:
            n=os.fstat(stream.fileno()).st_size;need(n<=8192,'STARTED_SIZE');budget.read(n+1);record=strict(stream.read(n+1))
        claim_worker(fd,record,p,start,initial,n,budget,expected_sha)
    finally:os.close(fd)
    code=verify_controls(root,p,budget);core=load_core(code[CORE],Path(root)/CORE);runtime=core.RuntimePin();need(runtime.sha256==p['runtime_sha256'],'RUNTIME_PIN')
    ledger=calculate(root,p,core,runtime,budget);budget.check();budget.write(4096);result=packed({'status':'RECORDED_ONE_READER_CALL','ledger':ledger,'usage':budget.summary()});need(len(result)<=131072 and len(result)-len(packed(ledger))<=4096,'PUBLIC_CAP')
    return result
