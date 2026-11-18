"""Saved schema2 JSON adapter; actual admission/entry remains unreleased.

Authored execution uses a real-shaped contract, immutable bytes and the same
Path/io API as the accepted reader. No civiclab/PDF/production reader import.
Process-wide guards belong only in an isolated single-threaded child.
"""
import builtins
from collections import Counter
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import threading
import time
from types import MappingProxyType

STATES=tuple('AK AL AR CO DE GA IA ID IL KS KY LA MA ME MI MN MS MT NC NE NH NJ NM OK OR RI SC SD TN TX VA WV WY'.split())
LEGACY_STATES=tuple('AK CO DE IA KS ME NC NE NH NJ VA WY'.split())
LEGACY='LEGACY_ROSTER_DOCUMENT';HISTORY='GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY';MISSING='NO_DOCUMENT_ADMITTED_FOR_ANY_REVIEWED_KIND'
FLAGS=('source_adoption','actual_selection','accepted_coverage_promoted','forecast_consumption')
DATA=('legacy_readiness_v1_7.json','candidate_rosters.local.json','id_status_records.local.json','typed_document_readiness.json')
LEDGER=DATA+('typed_payload_hashes.json','typed_commit.json','manifest.json','environment.json','events.jsonl','summary.json')
SAVED=LEDGER+('checksums.json','typed_release.json')
ROLES=('id_diagnostics','id_records','legacy_public','legacy_rosters')
CONFIG='configs/e01_typed_readiness_v1_9_1_candidate.json';READER='src/civiclab/e01/ballots_v1_9_1.py'
REVIEW='reports/INDEPENDENT_AUDIT_E01_V1_9_1_ACTUAL_PRIMARY_REPLAY.json'
CONTRACT='dc4f585d47c2c6d88a9ce3a33be34ff1ff2c87ee93636f61f55b263562652222'
DIAGNOSTIC='5d05c4ce15b704da8cdf5730a4c866609bbce8373fd0b1cfe877dada5248e21c'
CONTEXT='feb92afb1fea60e0aba8a14b433464a7f3d1bb3f9d529bf3f936bbcb8bb241f7'
SCOPE='TYPED_SOURCE_DOCUMENT_READINESS_ONLY_NOT_SAMPLE_OR_FINAL_BALLOT_ACCEPTANCE'
AUTHORED='AUTHORED_SAVED_JSON_FIXTURE';RECORDED='RECORDED_SAVED_READINESS_METADATA'
LIMITS={'saved_JSON_bytes':8388608,'project_source_bytes':1048576,'output_bytes':2097152,'public_bytes':131072,
 'console_bytes':16384,'wall_seconds':60,'CPU_seconds':30,'reader_calls':1,'retries':0}
CONFIG_KEYS=('base_config_path','code_config_audit_pins','context_contests_canonical_sha256','geometry_runtime','id_contract_path',
 'id_diagnostics_canonical_sha256','pipeline_release','references','schema_version','scope','source_adoption','sources')
ROOT=Path('/__ssl_authored_saved_json__')
_ACTIVE=None
_HOOK=False
_ORIGINAL={}


class Refused(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)
def require(ok,code):
    if not ok:raise Refused(code)
def packed(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def hash_ok(v):return type(v) is str and re.fullmatch('[0-9a-f]{64}',v) is not None
def closed(v,keys):return type(v) is dict and set(v)==set(keys)
def strict_json(raw):
    require(type(raw) is bytes and len(raw)<=4194304,'JSON_BOUND')
    def pairs(items):
        result={}
        for k,v in items:require(k not in result,'JSON_DUPLICATE');result[k]=v
        return result
    def invalid(_):raise Refused('JSON_NONFINITE')
    def number(token):
        value=float(token);require(math.isfinite(value),'JSON_NONFINITE');return value
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid,parse_float=number)
    except (ValueError,UnicodeError,RecursionError):raise Refused('JSON_INVALID') from None

def relative(v):
    require(type(v) is str and v and '\\' not in v and ':' not in v and '\x00' not in v,'PATH')
    p=Path(v);require(not p.is_absolute() and '..' not in p.parts and str(p)==v,'PATH');return v

def ref_ok(v):
    return closed(v,('path','bytes','sha256')) and type(v['bytes']) is int and 0<=v['bytes']<=4194304 and hash_ok(v['sha256']) and type(v['path']) is str


class Budget:
    def __init__(self,clock=time.monotonic,cancel=lambda:False):
        self.clock=clock;self.cancel=cancel;self.start=self.previous=clock();self.cpu=time.process_time()
        require(type(self.start) in {int,float} and math.isfinite(self.start),'CLOCK')
        self.saved=self.project=self.written=self.calls=0;self.primary=None;self.closed=False
    def fail(self,code):
        if self.primary is None:self.primary=Refused(code)
        raise self.primary
    def check(self):
        if self.primary is not None:raise self.primary
        if self.closed:self.fail('CLOSED')
        value=self.clock()
        if type(value) not in {int,float} or not math.isfinite(value) or value<self.previous:self.fail('CLOCK')
        self.previous=value
        if value-self.start>=60 or time.process_time()-self.cpu>=30:self.fail('DEADLINE')
        cancelled=self.cancel()
        if type(cancelled) is not bool or cancelled:self.fail('CANCELLED')
    def read(self,n,project=False):
        self.check()
        if type(n) is not int or n<0:self.fail('READ_AMOUNT')
        name='project' if project else 'saved';limit=1048576 if project else 8388608
        if getattr(self,name)+n>limit:self.fail('PROJECT_CAP' if project else 'SAVED_CAP')
        setattr(self,name,getattr(self,name)+n)
    def write(self,n,control=False):
        if not control:self.check()
        #8KiB remains available for final redacted failure closure.
        if type(n) is not int or n<0 or self.written+n>2097152-(0 if control else 8192):self.fail('OUTPUT_CAP')
        self.written+=n
    def summary(self):return {'saved_JSON_bytes':self.saved,'project_source_bytes':self.project,'output_bytes':self.written,'reader_calls':self.calls,'failed':self.primary is not None}


class Scope:
    def __init__(self):self.spent=False;self.files={}
    def claim(self):require(not self.spent,'SPENT_SCOPE');self.spent=True
    def put(self,name,value,budget,control=False):
        require(name in {'STARTED.json','source_job_ledger.json','COMPLETE.json','FAILURE.json'} and name not in self.files,'OUTPUT_NAME')
        raw=packed(value);require(len(raw)<=131072,'PUBLIC_CAP');budget.write(len(raw),control);self.files[name]=raw


def manifest_shape(raw):
    m=strict_json(raw)
    require(closed(m,('kind','provenance','run_id','config_ref','contract_sha256','reader_ref','acceptance_ref','project_refs','saved_refs','reference_refs','runtime_sha256','limits')),'MANIFEST_SCHEMA')
    require(m['kind']=='SAVED_JSON_ADAPTER_MANIFEST_V1' and m['provenance'] in {AUTHORED,RECORDED},'PROVENANCE')
    require(type(m['run_id']) is str and re.fullmatch('e01-[0-9a-f]{32}',m['run_id']),'RUN_ID')
    require(packed(m['limits'])==packed(LIMITS) and hash_ok(m['contract_sha256']) and hash_ok(m['runtime_sha256']),'LIMITS_OR_HASH')
    require(type(m['project_refs']) is dict and set(m['project_refs'])==set(REAL_PROJECT_PINS),'PROJECT_SET')
    require(type(m['saved_refs']) is dict and set(m['saved_refs'])==set(SAVED),'SAVED_SET')
    require(type(m['reference_refs']) is dict and set(m['reference_refs'])==set(ROLES),'REFERENCE_SET')
    refs=list(m['project_refs'].values())+[m['config_ref'],m['acceptance_ref']]+list(m['saved_refs'].values())+list(m['reference_refs'].values())
    require(all(ref_ok(r) for r in refs),'REFERENCE_SCHEMA')
    for r in refs:relative(r['path'])
    require(len({r['path'] for r in refs})==len(refs),'DUPLICATE_REFERENCE')
    require(m['reader_ref']==m['project_refs'][READER],'READER_REF')
    for name,r in m['project_refs'].items():require(r['path']==name,'PROJECT_PATH')
    require(m['config_ref']['path']==CONFIG and m['acceptance_ref']['path']==REVIEW,'CONTROL_PATH')
    prefix='data/processed/runs/'+m['run_id']
    for name,r in m['saved_refs'].items():require(r['path']==prefix+'/'+name,'SAVED_PATH')
    return m,refs,prefix


def validate_actual_metadata(raw):
    """Pure exact metadata check, no body admission or call authority."""
    m,_,_=manifest_shape(raw)
    require(m['provenance']==RECORDED and m['run_id']==REAL_RUN,'ACTUAL_METADATA')
    require(m['project_refs']==REAL_PROJECT_PINS and m['config_ref']==REAL_CONFIG_PIN and m['acceptance_ref']==REAL_REVIEW_PIN,'ACTUAL_CODE_PINS')
    require(m['reader_ref']==REAL_PROJECT_PINS[READER] and m['contract_sha256']==CONTRACT,'ACTUAL_CONTRACT')
    require(m['saved_refs']==REAL_SAVED_PINS and m['reference_refs']==REAL_REFERENCE_PINS,'ACTUAL_INPUT_PINS')
    return {'status':'METADATA_ONLY_ACTUAL_ENTRY_DISABLED','actual_reader_calls':0}


class Bundle:
    """Immutable admitted authored byte tree. Real body admission is unreleased."""
    def __init__(self,manifest_raw,files,budget,runtime):
        m,refs,prefix=manifest_shape(manifest_raw)
        require(m['provenance']==AUTHORED,'ACTUAL_ADMISSION_NOT_RELEASED')
        require(type(files) is dict and all(type(k) is str and type(v) is bytes for k,v in files.items()),'BYTE_TREE')
        require(set(files)=={r['path'] for r in refs},'CLOSED_MEMBERSHIP')
        require(m['runtime_sha256']==runtime.sha256,'RUNTIME_BINDING');runtime.verify()
        detached={}
        for r in refs:
            raw=files[r['path']];budget.read(len(raw)+1,r['path'] in m['project_refs'])
            require(len(raw)==r['bytes'] and digest(raw)==r['sha256'],'INPUT_HASH')
            detached[r['path']]=raw
        config=strict_json(detached[CONFIG]);require(closed(config,CONFIG_KEYS),'CONFIG_SCHEMA')
        require(type(config['schema_version']) is int and config['schema_version']==1 and config['source_adoption'] is False,'CONFIG_POLICY')
        require(config['scope']=='TYPED_READINESS_V1_9_1_CANDIDATE_ONLY' and digest(packed(config))==m['contract_sha256'],'CONFIG_CONTRACT')
        require(type(config['sources']) is list and len(config['sources'])==40,'SOURCE_SET')
        require(all(closed(x,('source_id','path','bytes','sha256')) and type(x['source_id']) is str and hash_ok(x['sha256']) for x in config['sources']),'SOURCE_SCHEMA')
        require(len({x['source_id'] for x in config['sources']})==40,'SOURCE_ID_DUPLICATE')
        require(type(config['references']) is dict and set(config['references'])==set(ROLES),'CONFIG_REFERENCES')
        for role,r in m['reference_refs'].items():require(config['references'][role]=={'path':r['path'],'sha256':r['sha256']},'REFERENCE_JOIN')
        for k in ('id_diagnostics_canonical_sha256','context_contests_canonical_sha256'):require(hash_ok(config[k]),'CONFIG_HASH')
        # Strict finite JSON precheck applies to all JSON files, including sealed
        # private references, without exporting their values. Events are hash-only.
        for path,raw in detached.items():
            if path.endswith('.json'):strict_json(raw)
        ledger=strict_json(detached[prefix+'/checksums.json'])
        require(type(ledger) is dict and set(ledger)==set(LEDGER),'CHECKSUM_SET')
        require(all(ledger[n]==m['saved_refs'][n]['sha256'] for n in LEDGER),'CHECKSUM_JOIN')
        seal=strict_json(detached[prefix+'/typed_release.json'])
        require(seal=={'status':'LOCAL_TYPED_LEDGER_COMPLETE_PENDING_INDEPENDENT_REVIEW','config_sha256':m['contract_sha256'],
            'checksums_sha256':m['saved_refs']['checksums.json']['sha256'],'wrapper_sha256':m['reader_ref']['sha256']},'SEAL_JOIN')
        run=strict_json(detached[prefix+'/manifest.json'])
        require(run.get('module')=='E01' and run.get('kind')=='EXPLORATORY' and run.get('run_id')==m['run_id'],'RUN_JOIN')
        require(run.get('config')=={'role':'TYPED_SOURCE_DOCUMENT_READINESS_V1_9_1','schema_version':2,'config_sha256':m['contract_sha256'],'wrapper_sha256':m['reader_ref']['sha256']},'RUN_CONTRACT')
        expected_summary={'status':'SEALED_TYPED_OBSERVATIONS_PENDING_INDEPENDENT_POST_RUN_REVIEW','schema_version':2,'final_ballots_accepted':0,'source_adoption':False,'accepted_coverage_promoted':False,'cost_usd':0}
        require(packed(strict_json(detached[prefix+'/summary.json']))==packed(expected_summary),'SUMMARY_JOIN')
        hashes=strict_json(detached[prefix+'/typed_payload_hashes.json'])
        require(hashes=={n:m['saved_refs'][n]['sha256'] for n in DATA},'PAYLOAD_JOIN')
        commit=strict_json(detached[prefix+'/typed_commit.json'])
        require(commit=={'status':'PAYLOADS_WRITTEN_SOURCE_RECHECKED_AWAITING_FINAL_LEDGER','schema_version':2,'config_sha256':m['contract_sha256'],'required_payloads':list(DATA)},'COMMIT_JOIN')
        require(m['saved_refs'][DATA[0]]['sha256']==m['reference_refs']['legacy_public']['sha256'] and m['saved_refs'][DATA[1]]['sha256']==m['reference_refs']['legacy_rosters']['sha256'],'LEGACY_JOIN')
        require(packed(strict_json(detached[prefix+'/id_status_records.local.json']))==packed(strict_json(detached[m['reference_refs']['id_records']['path']])),'ID_JOIN')
        self.raw=manifest_raw;self.manifest=m;self.config=config;self.prefix=prefix;self.files=MappingProxyType(detached)
        self.budget=budget;self.runtime=runtime
        self.dirs={ROOT,*ROOT.parents}
        for path in detached:self.dirs.update((ROOT/path).parents)


# Original functions are captured on explicit module load, not replaced here.
for owner,names in ((builtins,('open',)),(io,('open',)),(os,('open','read','write','fdopen','stat','lstat','listdir','scandir','remove','unlink','rmdir','mkdir','makedirs','rename','replace','link','symlink','chdir','chmod','utime','truncate','ftruncate')),
                    (Path,('open','stat','lstat','iterdir','resolve','is_symlink'))):
    for name in names:
        if hasattr(owner,name):_ORIGINAL[(owner,name)]=getattr(owner,name)


class RuntimePin:
    """Explicit selected-origin pin, not complete cold-start accounting."""
    def __init__(self):
        require(sys.implementation.name=='cpython' and sys.version_info[:2] in {(3,11),(3,12)},'RUNTIME_VERSION')
        observed={};total=0
        for name,module in [('__executable__',None)]+[(n,sys.modules[n]) for n in ('builtins','io','os','pathlib','hashlib','json','time','threading','types','stat','re','math')]:
            origin=sys.executable if module is None else getattr(getattr(module,'__spec__',None),'origin',None)
            require(type(origin) is str,'RUNTIME_ORIGIN')
            if origin in {'built-in','frozen'}:observed[name]={'origin':origin};continue
            path=Path(origin);require(path.is_absolute() and not path.is_symlink(),'RUNTIME_ORIGIN')
            n=_ORIGINAL[(os,'stat')](path).st_size;total+=n+1;require(total<=33554432,'RUNTIME_PIN_READ_CAP')
            with _ORIGINAL[(io,'open')](path,'rb') as f:raw=f.read(n+1)
            require(len(raw)==n,'RUNTIME_PIN_DRIFT')
            observed[name]={'origin':str(path),'bytes':n,'sha256':digest(raw)}
        self.raw=packed({'implementation':'CPython','version':sys.version.split()[0],'selected_origins':observed,'cold_startup_complete':False})
        self.sha256=digest(self.raw);self.logical_read_bytes=total;self.origins=observed
    def verify(self):
        require(digest(self.raw)==self.sha256,'RUNTIME_PIN_DRIFT')
        for (owner,name),value in _ORIGINAL.items():require(getattr(owner,name) is value,'RUNTIME_FUNCTION_DRIFT')
        for name,pin in self.origins.items():
            origin=sys.executable if name=='__executable__' else getattr(getattr(sys.modules.get(name),'__spec__',None),'origin',None)
            require(origin==pin['origin'],'RUNTIME_ORIGIN_DRIFT')
        require(threading.active_count()==1 and threading.current_thread() is threading.main_thread(),'SINGLE_THREAD_REQUIRED')


class ReadOnlyStream(io.BytesIO):
    def __init__(self,raw,budget):super().__init__(raw);self.budget=budget
    def checked(self,method,args):
        self.budget.check()
        try:return method(*args)
        except (OSError,ValueError):self.budget.fail('INPUT_IO')
    def read(self,*args):return self.checked(super().read,args)
    def readinto(self,*args):return self.checked(super().readinto,args)
    def readline(self,*args):return self.checked(super().readline,args)
    def write(self,*args):self.budget.fail('WRITE_DENIED')
    def writelines(self,*args):self.budget.fail('WRITE_DENIED')
    def truncate(self,*args):self.budget.fail('WRITE_DENIED')


def _audit(event,args):
    guard=_ACTIVE
    if guard is None:return
    if event.startswith(('socket.','subprocess.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec','os.kill','compile','exec','sys.addaudithook','sys.settrace','sys.setprofile','resource.setrlimit'}:guard.budget.fail('EXTERNAL_OR_CODE_DENIED')
    if event=='import':guard.budget.fail('LATE_IMPORT_DENIED')
    if event=='open':guard.budget.fail('UNMEDIATED_OPEN_DENIED')


class Guard:
    """Virtual immutable FS for trusted, preloaded reader code. No hostdata IO."""
    def __init__(self,bundle):self.bundle=bundle;self.budget=bundle.budget;self.restored=False
    def path(self,value):
        if not isinstance(value,(str,Path)):self.budget.fail('PATH_TYPE')
        p=Path(value)
        if not p.is_absolute():self.budget.fail('ABSOLUTE_PATH_REQUIRED')
        if '..' in p.parts or str(p)!=str(value):self.budget.fail('PATH')
        return p
    def file(self,path):
        p=self.path(path)
        if not p.is_relative_to(ROOT):self.budget.fail('READ_SCOPE')
        key=str(p.relative_to(ROOT))
        if key not in self.bundle.files:self.budget.fail('READ_SCOPE')
        return key
    def opened(self,path,mode='r',*args,**kwargs):
        self.budget.check()
        if mode!='rb' or args or kwargs:self.budget.fail('OPEN_MODE')
        key=self.file(path);raw=self.bundle.files[key]
        self.budget.read(len(raw)+1,key in self.bundle.manifest['project_refs'])
        return ReadOnlyStream(raw,self.budget)
    def metadata(self,path,*args,**kwargs):
        self.budget.check();p=self.path(path)
        if p in self.bundle.dirs:mode=stat.S_IFDIR|0o500;n=0
        elif p.is_relative_to(ROOT) and str(p.relative_to(ROOT)) in self.bundle.files:mode=stat.S_IFREG|0o400;n=len(self.bundle.files[str(p.relative_to(ROOT))])
        else:
            # Only the accepted reader's three explicit absent-failure paths and
            # optional .lock may be queried as missing. Unknown metadata poisons.
            allowed={ROOT/self.bundle.prefix/n for n in ('failure.json','terminal_failure.local.json','failure_checksums.local.json','.lock')}
            if p not in allowed:self.budget.fail('METADATA_SCOPE')
            raise FileNotFoundError('ABSENT_SEALED_CONTROL')
        return os.stat_result((mode,1,1,1,0,0,n,0,0,0))
    def listing(self,path):
        self.budget.check();p=self.path(path)
        if p not in self.bundle.dirs:self.budget.fail('DIRECTORY_SCOPE')
        children=set()
        for file in self.bundle.files:
            q=ROOT/file
            if q.is_relative_to(p) and q!=p:children.add(q.relative_to(p).parts[0])
        return sorted(children)
    def denied(self,*args,**kwargs):self.budget.fail('DESCRIPTOR_OR_MUTATION_DENIED')
    def resolve(self,path,*args,**kwargs):
        p=self.path(path)
        if p not in self.bundle.dirs and not (p.is_relative_to(ROOT) and str(p.relative_to(ROOT)) in self.bundle.files):self.budget.fail('RESOLVE_SCOPE')
        return p
    def symlink(self,path):
        p=self.path(path)
        allowed={ROOT/self.bundle.prefix/n for n in ('failure.json','terminal_failure.local.json','failure_checksums.local.json','.lock')}
        if p not in self.bundle.dirs and p not in allowed and not (p.is_relative_to(ROOT) and str(p.relative_to(ROOT)) in self.bundle.files):self.budget.fail('METADATA_SCOPE')
        return False # All virtual file/ancestor nodes immutable.
    def __enter__(self):
        global _ACTIVE,_HOOK
        require(_ACTIVE is None,'NESTED_GUARD');self.bundle.runtime.verify();self.budget.check()
        if not _HOOK:sys.addaudithook(_audit);_HOOK=True
        _ACTIVE=self
        replacements={}
        for owner,name in _ORIGINAL:replacements[(owner,name)]=self.denied
        for owner in (builtins,io):replacements[(owner,'open')]=self.opened
        replacements[(Path,'open')]=lambda path,mode='r',*a,**k:self.opened(path,mode,*a,**k)
        for name in ('stat','lstat'):
            replacements[(os,name)]=self.metadata
            replacements[(Path,name)]=lambda path,*a,**k:self.metadata(path,*a,**k)
        replacements[(os,'listdir')]=self.listing
        replacements[(Path,'iterdir')]=lambda path:iter(path/name for name in self.listing(path))
        replacements[(Path,'resolve')]=lambda path,*a,**k:self.resolve(path,*a,**k)
        replacements[(Path,'is_symlink')]=lambda path:self.symlink(path)
        try:
            for (owner,name),value in replacements.items():setattr(owner,name,value)
        except BaseException:
            self.__exit__(None,None,None);raise
        return self
    def __exit__(self,*_):
        global _ACTIVE
        for (owner,name),value in _ORIGINAL.items():setattr(owner,name,value)
        _ACTIVE=None;self.restored=True


def project(value,bundle):
    m=bundle.manifest;c=bundle.config
    require(closed(value,('schema_version','scope','config_sha256','legacy_payload_ref','document_observations','metrics','context_contests',*FLAGS,'cost_usd','model_calls')),'PUBLIC_SCHEMA')
    require(type(value['schema_version']) is int and value['schema_version']==2 and value['scope']==SCOPE and value['config_sha256']==m['contract_sha256'],'PUBLIC_CONTRACT')
    require(value['legacy_payload_ref']==DATA[0] and all(value[k] is False for k in FLAGS),'PUBLIC_ADOPTION')
    require(all(type(value[k]) is int and value[k]==0 for k in ('cost_usd','model_calls')),'PUBLIC_COST')
    rows=value['document_observations'];require(type(rows) is list and len(rows)==33,'ROWS');counts=Counter();output=[]
    for i,(state,row) in enumerate(zip(STATES,rows)):
        kind=LEGACY if state in LEGACY_STATES else HISTORY if state=='ID' else MISSING
        require(type(row) is dict and row.get('state')==state and row.get('kind')==kind,'STATE_OR_KIND');counts[kind]+=1
        if kind==LEGACY:require(closed(row,('state','kind','legacy_observation_index')) and type(row['legacy_observation_index']) is int and row['legacy_observation_index']==i,'LEGACY_ROW')
        elif kind==HISTORY:
            require(closed(row,('state','kind','record_role','local_record_artifact_ref','source_status_record_count','Approved_status_record_count','Withdrawn_status_record_count','safe_diagnostics')),'ID_ROW')
            require(row['record_role']=='OBSERVED_GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY' and row['local_record_artifact_ref']==DATA[2],'ID_ROLE')
            require(all(type(row[k]) is int for k in ('source_status_record_count','Approved_status_record_count','Withdrawn_status_record_count')) and tuple(row[k] for k in ('source_status_record_count','Approved_status_record_count','Withdrawn_status_record_count'))==(5,4,1),'ID_COUNTS')
            require(digest(packed(row['safe_diagnostics']))==c['id_diagnostics_canonical_sha256'],'ID_DIAGNOSTIC')
        else:require(closed(row,('state','kind')),'MISSING_ROW')
        output.append({'state':state,'document_kind':kind,'disposition':'NO_DOCUMENT_ADMITTED' if kind==MISSING else 'SAVED_DOCUMENT_OBSERVATION_ONLY',
            'evidence':{'typed_public_sha256':m['saved_refs'][DATA[3]]['sha256'],'observation_index':i},
            'unresolved_conditions':{'DOCUMENT_ACQUISITION':'NO_ADMITTED_DOCUMENT' if kind==MISSING else 'DOCUMENT_OBSERVED_ONLY',**{k:'NOT_ASSESSED' for k in ('LEGAL_CANDIDATE_STATUS','LATEST_AMENDMENT_COMPLETENESS','HISTORICAL_ASOF','GEOGRAPHY','RACE_SELECTION','FINAL_BALLOT')}}})
    metrics={'regular_frame_slots':len(rows),'legacy_roster_state_count':counts[LEGACY],'typed_status_history_state_count':counts[HISTORY],'document_state_coverage_count':counts[LEGACY]+counts[HISTORY],
        'remaining_document_acquisition_jobs':counts[MISSING],'distinct_source_representation_count':len(c['sources']),'final_ballots_accepted':0}
    require(type(value['metrics']) is dict and packed(value['metrics'])==packed(metrics),'METRICS')
    require(type(value['context_contests']) is list and len(value['context_contests'])==3 and digest(packed(value['context_contests']))==c['context_contests_canonical_sha256'],'CONTEXT')
    result={'kind':'E01_SAVED_JSON_SOURCE_JOB_LEDGER_V1','provenance':m['provenance'],'schema_version':1,'metrics':metrics,'state_dispositions':output,
        'bindings':{'config_file_sha256':m['config_ref']['sha256'],'config_contract_sha256':m['contract_sha256'],'reader_sha256':m['reader_ref']['sha256'],
                    'reader_acceptance_sha256':m['acceptance_ref']['sha256'],'input_manifest_sha256':digest(bundle.raw),'runtime_selected_origins_sha256':m['runtime_sha256']},
        **{k:False for k in FLAGS},'final_ballots_accepted':0,'cost_usd':0,'model_calls':0,
        'interpretation':'Missing admitted document is not evidence that candidates do not exist. No AL promotion, final ballot or forecasting acceptance.'}
    require(len(packed(result))<=131072,'PUBLIC_CAP');return result


def compile_authored_once(manifest_raw,files,reader,runtime,scope=None,*,clock=time.monotonic,cancel=lambda:False):
    require(getattr(reader,'mock_only',False) is True and type(runtime) is RuntimePin,'AUTHORED_READER_ONLY')
    scope=Scope() if scope is None else scope;require(type(scope) is Scope,'SCOPE_TYPE');scope.claim()
    budget=Budget(clock,cancel);primary=None;result=None
    try:
        scope.put('STARTED.json',{'kind':'AUTHORED_ADAPTER_STARTED','manifest_sha256':digest(manifest_raw),'no_retry':True},budget)
        bundle=Bundle(manifest_raw,files,budget,runtime);budget.check();budget.calls+=1
        with Guard(bundle):value=reader(ROOT/bundle.prefix,root=ROOT,contract=strict_json(bundle.files[CONFIG]))
        budget.check()
        require(packed(value)==packed(strict_json(bundle.files[bundle.prefix+'/'+DATA[3]])),'READER_RESULT_DRIFT')
        result=project(value,bundle);budget.check()
        scope.put('source_job_ledger.json',result,budget)
        scope.put('COMPLETE.json',{'status':'AUTHORED_SAVED_JSON_ONLY','ledger_sha256':digest(packed(result)),'budget':budget.summary(),'no_actual_reader':True},budget)
    except BaseException as error:primary=budget.primary if budget.primary is not None else error
    finally:
        if primary is not None:
            record={'status':'FAILED_UNACCEPTED','error_type':'Refused' if isinstance(primary,Refused) else 'OTHER_ERROR','budget':budget.summary(),'no_retry':True,'model_calls':0,'cost_usd':0}
            try:scope.put('FAILURE.json',record,budget,control=True)
            except BaseException:pass
        budget.closed=True
    if primary is not None:raise primary
    return {'ledger':result,'scope':scope,'budget':budget.summary()}


def actual_entry(*args,**kwargs):raise Refused('ACTUAL_DISABLED_PENDING_EXACT_REVIEWED_RELEASE')

REAL_PROJECT_PINS={'src/civiclab/__init__.py': {'bytes': 106, 'path': 'src/civiclab/__init__.py', 'sha256': '23bd3100ad3fd5ef94e459572a286f3f87b321c9676b36507c859bcf7dfadd50'}, 'src/civiclab/common.py': {'bytes': 8476, 'path': 'src/civiclab/common.py', 'sha256': '566c5f3947e3048a1521d1edfa2ee6e7ade7b66502e3b4ee6ee440573eb885fa'}, 'src/civiclab/e01/__init__.py': {'bytes': 422, 'path': 'src/civiclab/e01/__init__.py', 'sha256': 'aff117761fad19eec67ce32b5eae12c9b84921a71f0458e854a55c0237f77e83'}, 'src/civiclab/e01/ballot_capture_formats_v1_4.py': {'bytes': 4781, 'path': 'src/civiclab/e01/ballot_capture_formats_v1_4.py', 'sha256': '0c8cc0be58b249c9d31968a439025e5025f42949abdfe15214496f63fddbf370'}, 'src/civiclab/e01/ballot_formats_v1_3.py': {'bytes': 6860, 'path': 'src/civiclab/e01/ballot_formats_v1_3.py', 'sha256': '281ae5eb4f3a71ab29b22b8944256c68a513712b4e4c289b7c2b6d09f1534916'}, 'src/civiclab/e01/ballot_formats_v1_6.py': {'bytes': 5856, 'path': 'src/civiclab/e01/ballot_formats_v1_6.py', 'sha256': 'fb5fb665225dfdef782eef3f8ba712cd0eb67816e9b69632323e39310a19faa9'}, 'src/civiclab/e01/ballots.py': {'bytes': 25981, 'path': 'src/civiclab/e01/ballots.py', 'sha256': '67108d9641cabc04eb17b55896122bce31413059e8682dd9a358dc81d328d8ec'}, 'src/civiclab/e01/ballots_v1_7.py': {'bytes': 8887, 'path': 'src/civiclab/e01/ballots_v1_7.py', 'sha256': 'b45746439df1e50469f76a7d6ff9acb8bb0536e2f1d605eb116a28460b169062'}, 'src/civiclab/e01/ballots_v1_9_1.py': {'bytes': 18754, 'path': 'src/civiclab/e01/ballots_v1_9_1.py', 'sha256': '30e02bfa068f400846c8feff612695c3ba2c12497d6bc1567ad4c75858788f8b'}, 'src/civiclab/e01/delaware_v1_7.py': {'bytes': 8546, 'path': 'src/civiclab/e01/delaware_v1_7.py', 'sha256': '929ecadc08bdcb3cfad881f68443951a339f56731c2ab72101f1cda45f4d74c6'}, 'src/civiclab/e01/idaho_v1_8_1.py': {'bytes': 20513, 'path': 'src/civiclab/e01/idaho_v1_8_1.py', 'sha256': '1413f9a6e784e88d82b0ffe0beb2e8323775c5a8b55a1f5fc223f4a2505c2bb7'}, 'src/civiclab/e01/maine_v1_5.py': {'bytes': 9833, 'path': 'src/civiclab/e01/maine_v1_5.py', 'sha256': 'e07da3eeb097fe5ed85f4d9445a6d1dc50c28c5b87c97dc7a153e866770ca179'}, 'src/civiclab/e01/nebraska_v1_7.py': {'bytes': 6137, 'path': 'src/civiclab/e01/nebraska_v1_7.py', 'sha256': '7ccd0a19bc015440587b93283956b27b958a1f1530d5551d6bb23fb463607e5e'}, 'src/civiclab/e01/pipeline.py': {'bytes': 22533, 'path': 'src/civiclab/e01/pipeline.py', 'sha256': 'caf1b19dd62aab8541c740868b20b618ac62213b8b6be3d597cef14f9b6cd763'}}

REAL_CONFIG_PIN={'bytes': 14122, 'path': 'configs/e01_typed_readiness_v1_9_1_candidate.json', 'sha256': 'f017d3b4ceb1647add88eeb66a8d4d386f156f98169ac3807f7d800083fb2997'}

REAL_REVIEW_PIN={'bytes': 15513, 'path': 'reports/INDEPENDENT_AUDIT_E01_V1_9_1_ACTUAL_PRIMARY_REPLAY.json', 'sha256': '31bb4e389aad209d24a276347023de5f2eab3ed03a3e91d8745128dcfc8115e2'}

REAL_RUN='e01-f398afc9b07c495290f0a55262ac016c'

REAL_SAVED_PINS={'candidate_rosters.local.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/candidate_rosters.local.json', 'bytes': 37650, 'sha256': 'fe7a127fb2d847debfa2bc3135c31a82dbefe11c1dac71092633cb25f617d46c'}, 'checksums.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/checksums.json', 'bytes': 949, 'sha256': '6921ea2488602ad07bc1198a3cf63e9d5ef6a74f1e4892025e87d8cf156409db'}, 'environment.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/environment.json', 'bytes': 466, 'sha256': '9b22725f5980481c4437fc60772250818d34989bbb3f473e68b307609c3068f4'}, 'events.jsonl': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/events.jsonl', 'bytes': 183, 'sha256': 'f4439d46881940fe828759960557a79565b3d28fe8b5f7f13df1a4b0568dfbde'}, 'id_status_records.local.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/id_status_records.local.json', 'bytes': 6572, 'sha256': '8f40935424ef077b89d9a7f53382e36b0a25fa1afa257654339bf64d421bc2ea'}, 'legacy_readiness_v1_7.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/legacy_readiness_v1_7.json', 'bytes': 13287, 'sha256': 'be0db00d16758793d6a726c4a780c2c98ee1e6cfe2825bed84edf522998be997'}, 'manifest.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/manifest.json', 'bytes': 729, 'sha256': '6d5211859573a4b8991cc41616cbde4402675ecb2a2541a101f562b09e88adab'}, 'summary.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/summary.json', 'bytes': 218, 'sha256': '89ca96d6548260aff7e90bc093976ebd4da8adac44f72aed68e66cd76b014dff'}, 'typed_commit.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/typed_commit.json', 'bytes': 356, 'sha256': '3e6e18e16969456170024d26b53d1364e46d38235894162373e6ca973494a6a8'}, 'typed_document_readiness.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/typed_document_readiness.json', 'bytes': 9467, 'sha256': '201ef67bf7d9db14d7997d65bc7ec848802916c1dabbb5b3ee066b994e08ce71'}, 'typed_payload_hashes.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/typed_payload_hashes.json', 'bytes': 410, 'sha256': '7927a8ebeff8000dbd7daa7d920a454b3b63bbe4336f876c53ada6ed80ae5817'}, 'typed_release.json': {'path': 'data/processed/runs/e01-f398afc9b07c495290f0a55262ac016c/typed_release.json', 'bytes': 338, 'sha256': 'ce21ee6260f080d203d2a77b7f2a40e7f9ca2ebb483eda3e56b7b61d6a35938e'}}

REAL_REFERENCE_PINS={'id_diagnostics': {'path': 'data/processed/e01_id_standalone_preflight_v1_8_1/e01-id-standalone-v1_8_1-582d30d28eca493993ef692b5ed12cc1/primary_diagnostics.local.json', 'bytes': 3119, 'sha256': '02a02643f3dded40faec287ba18eb8c5a8fbeaecf2d9e203d9f4c2d3a88a26a7'}, 'id_records': {'path': 'data/processed/e01_id_standalone_preflight_v1_8_1/e01-id-standalone-v1_8_1-582d30d28eca493993ef692b5ed12cc1/primary_records.local.json', 'bytes': 6572, 'sha256': '8f40935424ef077b89d9a7f53382e36b0a25fa1afa257654339bf64d421bc2ea'}, 'legacy_public': {'path': 'data/processed/runs/e01-6a2b9fded13e4bb48d15985d98c7bb34/ballot_readiness.json', 'bytes': 13287, 'sha256': 'be0db00d16758793d6a726c4a780c2c98ee1e6cfe2825bed84edf522998be997'}, 'legacy_rosters': {'path': 'data/processed/runs/e01-6a2b9fded13e4bb48d15985d98c7bb34/candidate_rosters.local.json', 'bytes': 37650, 'sha256': 'fe7a127fb2d847debfa2bc3135c31a82dbefe11c1dac71092633cb25f617d46c'}}
