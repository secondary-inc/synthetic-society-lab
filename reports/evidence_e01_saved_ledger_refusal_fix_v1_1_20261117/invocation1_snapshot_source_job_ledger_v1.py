"""Saved typed-document job ledger; no source adoption or import-time reader.

Pure projection and authored saved-fixture workload only. The actual entry is
closed until a separate reviewed packet/lead release and guarded reader binding.
No raw PDF/CSV path, real saved reader or production executor is imported here.
"""
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

REGULAR_STATES=tuple('AK AL AR CO DE GA IA ID IL KS KY LA MA ME MI MN MS MT NC NE NH NJ NM OK OR RI SC SD TN TX VA WV WY'.split())
LEGACY_STATES=tuple('AK CO DE IA KS ME NC NE NH NJ VA WY'.split())
LEGACY='LEGACY_ROSTER_DOCUMENT'
HISTORY='GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY'
MISSING='NO_DOCUMENT_ADMITTED_FOR_ANY_REVIEWED_KIND'
TYPED_SCOPE='TYPED_SOURCE_DOCUMENT_READINESS_ONLY_NOT_SAMPLE_OR_FINAL_BALLOT_ACCEPTANCE'
FLAGS=('source_adoption','actual_selection','accepted_coverage_promoted','forecast_consumption')
DATA_FILES=('legacy_readiness_v1_7.json','candidate_rosters.local.json','id_status_records.local.json','typed_document_readiness.json')
LEDGER_FILES=DATA_FILES+('typed_payload_hashes.json','typed_commit.json','manifest.json','environment.json','events.jsonl','summary.json')
SAVED_FILES=LEDGER_FILES+('checksums.json','typed_release.json')
REFERENCE_ROLES=('legacy_public','legacy_rosters','id_records','id_diagnostics')
LIMITS={'wall_seconds':120,'CPU_seconds':120,'logical_read_bytes':67108864,'write_bytes':33554432,
 'console_bytes':262144,'file_bytes':4194304,'manifest_bytes':1048576,'output_bytes':131072,
 'closure_read_bytes':32768,'closure_write_bytes':32768,'reader_calls':1,'retries':0}
CODE_PATH='src/civiclab/e01/source_job_ledger_v1.py'
READER_PATH='src/civiclab/e01/ballots_v1_9_1.py'
CONFIG_PATH='configs/e01_typed_readiness_v1_9_1_candidate.json'
REVIEW_PATH='reports/INDEPENDENT_AUDIT_E01_V1_9_1_ACTUAL_PRIMARY_REPLAY.json'
# Exact accepted source metadata is appended below. No referenced source is
# opened/imported by module import or by actual_entry.


def packed(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest_ok(value):return type(value) is str and bool(re.fullmatch('[0-9a-f]{64}',value))
def closed(value,keys):return type(value) is dict and set(value)==set(keys)

class LedgerRefused(RuntimeError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise LedgerRefused(code)
def exact_json(raw):
    need(type(raw) is bytes and len(raw)<=4194304,'JSON_BOUND')
    def pairs(items):
        d={}
        for k,v in items:
            need(k not in d,'JSON_DUPLICATE');d[k]=v
        return d
    def constant(_):raise LedgerRefused('JSON_NONFINITE')
    def finite_float(token):
        value=float(token)
        need(math.isfinite(value),'JSON_NONFINITE');return value
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant,parse_float=finite_float)
    except (UnicodeError,json.JSONDecodeError):raise LedgerRefused('JSON_INVALID') from None

def relative(value):
    need(type(value) is str and value and '\\' not in value and ':' not in value,'PATH_SCHEMA')
    p=Path(value);need(not p.is_absolute() and '..' not in p.parts and str(p)==value,'PATH_SCHEMA');return value

def ref_ok(ref):
    return (closed(ref,('path','bytes','sha256')) and type(ref['path']) is str and type(ref['bytes']) is int
        and 0<=ref['bytes']<=4194304 and digest_ok(ref['sha256']))
def expected_kind(state):return LEGACY if state in LEGACY_STATES else HISTORY if state=='ID' else MISSING


class Budget:
    def __init__(self,clock=time.monotonic,cancel=lambda:False):
        self.clock=clock;self.started=self.previous=clock();self.cancel=cancel
        need(type(self.started) in {int,float} and math.isfinite(self.started),'CLOCK')
        self.cpu_start=time.process_time();self.reads=self.writes=self.reader_calls=0
        self.failed=False;self.primary=None;self.closing=False;self.control_reads=self.control_writes=0
    def trip(self,code):
        if self.primary is None:self.primary=LedgerRefused(code)
        self.failed=True;raise self.primary
    def check(self,control=False):
        if self.closing and control:return
        if self.failed:raise self.primary
        need(not self.closing,'AFTER_CLOSURE')
        value=self.clock()
        if type(value) not in {int,float} or not math.isfinite(value) or value<self.previous:self.trip('CLOCK')
        self.previous=value
        if value-self.started>=120 or time.process_time()-self.cpu_start>=120:self.trip('DEADLINE')
        cancelled=self.cancel()
        if type(cancelled) is not bool or cancelled:self.trip('CANCELLED')
    def read(self,n,control=False):
        self.check(control);need(type(n) is int and n>=0,'READ_AMOUNT')
        if self.closing:
            if not control or self.control_reads+n>32768:self.trip('CONTROL_READ_CAP')
            self.control_reads+=n
        if self.reads+n>67108864-(0 if control else 32768):self.trip('READ_CAP')
        self.reads+=n
    def write(self,n,control=False):
        self.check(control);need(type(n) is int and n>=0,'WRITE_AMOUNT')
        if self.closing:
            if not control or self.control_writes+n>32768:self.trip('CONTROL_WRITE_CAP')
            self.control_writes+=n
        if self.writes+n>33554432-(0 if control else 32768):self.trip('WRITE_CAP')
        self.writes+=n
    def finish(self):self.closing=True
    def summary(self):return {'logical_read_bytes':self.reads,'written_bytes':self.writes,'reader_calls':self.reader_calls,
        'failed':self.failed,'closing':self.closing,'control_read_bytes':self.control_reads,'control_write_bytes':self.control_writes}


class MemoryFixture:
    mock_only=True
    def __init__(self,files):self.files=dict(files)
    def size(self,name):return len(self.files[name])
    def read(self,name,limit):return self.files[name][:limit]
    def members(self,prefix):return sorted(name for name in self.files if name.startswith(prefix+'/'))


class DiskFixture:
    """Only authored test trees outside the repository; no real input adapter."""
    mock_only=True
    def __init__(self,root):
        root=Path(root).absolute();repo=Path(__file__).absolute().parents[3]
        need(root.name.startswith('ssl-job-ledger-fixture-') and not root.is_relative_to(repo),'FIXTURE_ROOT')
        need(not any(p.is_symlink() for p in (root,*root.parents)),'FIXTURE_ALIAS');self.root=root
    def path(self,name):
        p=self.root/relative(name)
        need(not any(x.is_symlink() for x in (p,*p.parents)),'FIXTURE_ALIAS')
        need(p.is_file(),'FIXTURE_FILE');return p
    def size(self,name):return self.path(name).stat().st_size
    def read(self,name,limit):
        p=self.path(name);before=p.stat();fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:
            opened=os.fstat(stream.fileno());raw=stream.read(limit);after=os.fstat(stream.fileno())
        ident=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
        need(ident(before)==ident(opened)==ident(after),'FIXTURE_DRIFT');return raw
    def members(self,prefix):
        parent=self.root/relative(prefix);need(parent.is_dir() and not parent.is_symlink(),'FIXTURE_DIRECTORY')
        out=[]
        for p in parent.iterdir():
            need(p.is_file() and not p.is_symlink(),'FIXTURE_MEMBER')
            out.append(str(p.relative_to(self.root)))
        return sorted(out)


class ReadView:
    def __init__(self,store,budget,refs):self.store=store;self.budget=budget;self.refs={r['path']:r for r in refs}
    def read(self,name):
        self.budget.check()
        try:
            relative(name)
            if name not in self.refs:self.budget.trip('READ_OUTSIDE_SCOPE')
            ref=self.refs[name];size=self.store.size(name)
            if size!=ref['bytes']:self.budget.trip('INPUT_SIZE')
            self.budget.read(size+1);raw=self.store.read(name,size+1)
            if type(raw) is not bytes or len(raw)!=size or sha(raw)!=ref['sha256']:self.budget.trip('INPUT_HASH')
            self.budget.check();return raw
        except (KeyError,FileNotFoundError):self.budget.trip('MISSING_INPUT')
        except OSError:self.budget.trip('INPUT_IO')
        except LedgerRefused as error:self.budget.trip(error.code)
    def json(self,name):
        try:return exact_json(self.read(name))
        except LedgerRefused as error:self.budget.trip(error.code)


class MemoryOutput:
    mock_only=True
    def __init__(self):self.files={};self.claimed=False
    def claim(self):
        need(not self.claimed and 'STARTED.json' not in self.files,'SPENT_OUTPUT');self.claimed=True
    def has(self,name):return name in self.files
    def new(self,name,raw,budget,control=False):
        need(name in {'STARTED.json','job_ledger.json','COMPLETE.json','FAILURE.json'} and name not in self.files,'SPENT_OUTPUT')
        need(type(raw) is bytes and len(raw)<=131072,'OUTPUT_BOUND');budget.write(len(raw),control)
        self.files[name]=raw


def _validate_manifest(manifest):
    need(closed(manifest,('kind','provenance','run_id','code_refs','config_ref','review_ref','saved_refs','reference_refs')),'MANIFEST_SCHEMA')
    need(manifest['kind']=='SAVED_TYPED_INPUT_MANIFEST_V1' and manifest['provenance']=='MOCK_AUTHORED','MOCK_MANIFEST_REQUIRED')
    need(type(manifest['run_id']) is str and re.fullmatch('e01-[0-9a-f]{32}',manifest['run_id']),'RUN_ID')
    need(type(manifest['code_refs']) is dict and set(manifest['code_refs'])==set(ACCEPTED_CODE_PINS),'CODE_REF_SET')
    need(type(manifest['saved_refs']) is dict and set(manifest['saved_refs'])==set(SAVED_FILES),'SAVED_REF_SET')
    need(type(manifest['reference_refs']) is dict and set(manifest['reference_refs'])==set(REFERENCE_ROLES),'REFERENCE_SET')
    groups=list(manifest['code_refs'].values())+[manifest['config_ref'],manifest['review_ref']]+list(manifest['saved_refs'].values())+list(manifest['reference_refs'].values())
    need(all(ref_ok(ref) for ref in groups),'REFERENCE_SCHEMA')
    for ref in groups:relative(ref['path'])
    need(len({ref['path'] for ref in groups})==len(groups),'DUPLICATE_REFERENCE')
    for path,ref in manifest['code_refs'].items():need(ref['path']==path,'CODE_REF_PATH')
    need(manifest['config_ref']['path']==CONFIG_PATH and manifest['review_ref']['path']==REVIEW_PATH,'BINDING_PATH')
    prefix='data/processed/runs/'+manifest['run_id']
    for name,ref in manifest['saved_refs'].items():need(ref['path']==prefix+'/'+name,'SAVED_REF_PATH')
    for role,ref in manifest['reference_refs'].items():need(ref['path']=='authored_references/'+role+'.json','REFERENCE_PATH')
    return groups,prefix


def _admit_mock_source(plan,store,budget):
    need(closed(plan,('kind','provenance','input_manifest_ref','limits')) and plan['kind']=='SAVED_JOB_LEDGER_MOCK_PLAN_V1'
        and plan['provenance']=='MOCK_AUTHORED' and packed(plan['limits'])==packed(LIMITS),'PLAN_SCHEMA')
    ref=plan['input_manifest_ref'];need(ref_ok(ref) and ref['path']=='metadata/input_manifest.json' and ref['bytes']<=1048576,'MANIFEST_REF')
    initial=ReadView(store,budget,[ref]);manifest=initial.json(ref['path']);groups,prefix=_validate_manifest(manifest)
    view=ReadView(store,budget,groups+[ref])
    need(store.members(prefix)==sorted([prefix+'/'+name for name in SAVED_FILES]+([prefix+'/.lock'] if prefix+'/.lock' in store.members(prefix) else [])),'SAVED_MEMBERSHIP')
    for item in groups:view.read(item['path'])
    config=view.json(CONFIG_PATH);review=view.json(REVIEW_PATH)
    need(closed(config,('kind','source_ids','id_diagnostics_sha256','context_contests_sha256')) and config['kind']=='MOCK_TYPED_READER_CONFIG_V1','CONFIG_SCHEMA')
    need(config['source_ids']==list(SOURCE_IDS) and digest_ok(config['id_diagnostics_sha256']) and digest_ok(config['context_contests_sha256']),'CONFIG_POLICY')
    need(review=={'kind':'MOCK_READER_ACCEPTANCE_V1','status':'PASS_AUTHORED_BINDINGS_ONLY',
        'reader_sha256':manifest['code_refs'][READER_PATH]['sha256'],'config_sha256':manifest['config_ref']['sha256']},'REVIEW_BINDING')
    ledger=view.json(prefix+'/checksums.json');seal=view.json(prefix+'/typed_release.json')
    need(type(ledger) is dict and set(ledger)==set(LEDGER_FILES),'CHECKSUM_SET')
    need(all(ledger[name]==manifest['saved_refs'][name]['sha256'] for name in LEDGER_FILES),'CHECKSUM_HASH')
    need(seal=={'kind':'MOCK_TYPED_RELEASE_V1','status':'SEALED_AUTHORED_ONLY','checksums_sha256':manifest['saved_refs']['checksums.json']['sha256'],
        'reader_sha256':manifest['code_refs'][READER_PATH]['sha256']},'SEAL')
    summary=view.json(prefix+'/summary.json')
    need(summary=={'status':'SEALED_AUTHORED_TYPED_OBSERVATIONS','final_ballots_accepted':0,**{flag:False for flag in FLAGS}}
        and type(summary['final_ballots_accepted']) is int and all(summary[flag] is False for flag in FLAGS),'SAVED_STATUS')
    return manifest,config,view,prefix


def project_public(value,config,binding):
    """Closed producer shape, approved role layout; project hashes/enums only."""
    need(closed(binding,('reader_sha256','config_sha256','reader_acceptance_sha256','manifest_sha256','typed_public_sha256'))
        and all(digest_ok(v) for v in binding.values()),'BINDING_HASH')
    need(closed(config,('kind','source_ids','id_diagnostics_sha256','context_contests_sha256')) and config['kind']=='MOCK_TYPED_READER_CONFIG_V1'
        and config['source_ids']==list(SOURCE_IDS) and digest_ok(config['id_diagnostics_sha256']) and digest_ok(config['context_contests_sha256']),'CONFIG_POLICY')
    need(closed(value,('schema_version','scope','config_sha256','legacy_payload_ref','document_observations','metrics','context_contests',*FLAGS,'cost_usd','model_calls')),'TYPED_SCHEMA')
    need(type(value['schema_version']) is int and value['schema_version']==2 and value['scope']==TYPED_SCOPE
        and value['config_sha256']==binding['config_sha256'] and value['legacy_payload_ref']=='legacy_readiness_v1_7.json','TYPED_BINDING')
    need(all(value[flag] is False for flag in FLAGS) and type(value['cost_usd']) is int and value['cost_usd']==0
        and type(value['model_calls']) is int and value['model_calls']==0,'ADOPTION_OR_COST')
    source=value['document_observations'];need(type(source) is list and len(source)==len(REGULAR_STATES),'STATE_COVERAGE')
    counts=Counter();out=[]
    for index,(state,row) in enumerate(zip(REGULAR_STATES,source)):
        need(type(row) is dict and row.get('state')==state and row.get('kind')==expected_kind(state),'STATE_OR_KIND')
        kind=row['kind'];counts[kind]+=1
        if kind==LEGACY:
            need(closed(row,('state','kind','legacy_observation_index')) and type(row['legacy_observation_index']) is int
                and row['legacy_observation_index']==index,'LEGACY_ROW')
        elif kind==HISTORY:
            need(closed(row,('state','kind','record_role','local_record_artifact_ref','source_status_record_count','Approved_status_record_count','Withdrawn_status_record_count','safe_diagnostics')),'HISTORY_ROW')
            need(row['record_role']=='OBSERVED_GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY' and row['local_record_artifact_ref']=='id_status_records.local.json','HISTORY_ROLE')
            need(all(type(row[n]) is int and row[n]>=0 for n in ('source_status_record_count','Approved_status_record_count','Withdrawn_status_record_count'))
                and tuple(row[n] for n in ('source_status_record_count','Approved_status_record_count','Withdrawn_status_record_count'))==(5,4,1),'HISTORY_COUNTS')
            need(sha(packed(row['safe_diagnostics']))==config['id_diagnostics_sha256'],'DIAGNOSTIC_BINDING')
        else:need(closed(row,('state','kind')),'MISSING_ROW')
        conditions=[{'condition':'DOCUMENT_ACQUISITION','status':'NO_ADMITTED_DOCUMENT' if kind==MISSING else 'DOCUMENT_OBSERVED_ONLY'},
            *[{'condition':name,'status':'NOT_ASSESSED_BY_THIS_LEDGER'} for name in
                ('LEGAL_CANDIDATE_STATUS','LATEST_AMENDMENT_COMPLETENESS','HISTORICAL_ASOF','GEOGRAPHY','RACE_SELECTION','FINAL_BALLOT')]]
        out.append({'state':state,'document_kind':kind,'disposition':'NO_DOCUMENT_ADMITTED' if kind==MISSING else 'SAVED_DOCUMENT_OBSERVATION_ONLY',
            'evidence_refs':[{'role':'SAVED_TYPED_PUBLIC','sha256':binding['typed_public_sha256'],'observation_index':index},
                             {'role':'SAVED_INPUT_MANIFEST','sha256':binding['manifest_sha256']}],
            'unresolved_conditions':conditions})
    expected={'regular_frame_slots':len(source),'legacy_roster_state_count':counts[LEGACY],'typed_status_history_state_count':counts[HISTORY],
        'document_state_coverage_count':counts[LEGACY]+counts[HISTORY],'remaining_document_acquisition_jobs':counts[MISSING],
        'distinct_source_representation_count':len(config['source_ids']),'final_ballots_accepted':0}
    need(type(value['metrics']) is dict and value['metrics']==expected and all(type(v) is int for v in value['metrics'].values()),'METRIC_DRIFT')
    need(type(value['context_contests']) is list and sha(packed(value['context_contests']))==config['context_contests_sha256'],'CONTEXT_BINDING')
    result={'schema_version':1,'kind':'E01_SAVED_TYPED_SOURCE_JOB_LEDGER_V1','provenance':'MOCK_AUTHORED','scope':'SOURCE_JOB_METADATA_ONLY_NOT_ACCEPTANCE',
        'metrics':expected,'state_dispositions':out,'context_contests_count':len(value['context_contests']),
        'bindings':binding,**{flag:False for flag in FLAGS},'final_ballots_accepted':0,'cost_usd':0,'model_calls':0,
        'interpretation':'Missing document means no admitted document in this saved kind, not evidence that real candidates do not exist. No Alabama context coverage promotion.'}
    need(len(packed(result))<=131072,'OUTPUT_BOUND');return result


SAFE_TYPES={'LedgerRefused','ValueError','TypeError','KeyError','OSError','PermissionError','FileNotFoundError','RuntimeError','KeyboardInterrupt','SystemExit'}

def compile_mock_once(plan,store,reader,output=None,*,expected_plan_sha256,clock=time.monotonic,cancel=lambda:False):
    need(type(store) in {MemoryFixture,DiskFixture} and getattr(store,'mock_only',False) is True and getattr(reader,'mock_only',False) is True,'MOCK_ONLY')
    need(digest_ok(expected_plan_sha256) and sha(packed(plan))==expected_plan_sha256,'PLAN_HASH')
    output=MemoryOutput() if output is None else output;need(type(output) is MemoryOutput,'MOCK_OUTPUT_ONLY')
    output.claim();budget=Budget(clock,cancel)
    primary=None;result=None
    try:
        output.new('STARTED.json',packed({'kind':'MOCK_LEDGER_STARTED','plan_sha256':expected_plan_sha256,'no_retry':True}),budget)
        manifest,config,view,prefix=_admit_mock_source(plan,store,budget)
        budget.check();budget.reader_calls+=1;need(budget.reader_calls<=1,'READER_CALL_CAP')
        value=reader.read_verified_public(view,prefix,config)
        budget.check()
        binding={'reader_sha256':manifest['code_refs'][READER_PATH]['sha256'],'config_sha256':manifest['config_ref']['sha256'],
            'reader_acceptance_sha256':manifest['review_ref']['sha256'],'manifest_sha256':plan['input_manifest_ref']['sha256'],
            'typed_public_sha256':manifest['saved_refs']['typed_document_readiness.json']['sha256']}
        need(all(digest_ok(v) for v in binding.values()),'BINDING_HASH')
        # Do not let a mock callback substitute a different admitted source.
        need(packed(value)==packed(view.json(prefix+'/typed_document_readiness.json')),'READER_RESULT_DRIFT')
        result=project_public(value,config,binding);budget.check()
        output.new('job_ledger.json',packed(result),budget);budget.check()
        output.new('COMPLETE.json',packed({'status':'MOCK_LEDGER_COMPILED_ONLY','job_ledger_sha256':sha(packed(result)),
            'no_actual_reader':True,'budget_before_complete_write':budget.summary()}),budget)
    except BaseException as error:
        primary=budget.primary if budget.failed and budget.primary is not None else error
    finally:
        budget.finish()
        if primary is not None:
            safe_type=type(primary).__name__;safe_type=safe_type if safe_type in SAFE_TYPES else 'UNKNOWN_ERROR_TYPE'
            # No exception text/args/code/path is copied, even for own refusal.
            record={'status':'FAILED_UNACCEPTED','error_type':safe_type,'budget':budget.summary(),'no_retry':True,
                'source_adoption':False,'final_ballots_accepted':0,'cost_usd':0,'model_calls':0}
            try:output.new('FAILURE.json',packed(record),budget,control=True)
            except BaseException:pass
    if primary is not None:raise primary
    return {'ledger':result,'output':output,'budget':budget.summary()}


def validate_eventual_binding(packet):
    """Pure metadata gate only; never loads any real reader or private body."""
    need(closed(packet,('kind','execution_enabled','reader_ref','config_ref','review_ref','code_refs','input_manifest_ref','limits')),'ACTUAL_PACKET_SCHEMA')
    need(packet['kind']=='E01_SAVED_JOB_LEDGER_PREPARATION_ONLY_V1' and packet['execution_enabled'] is False,'ACTUAL_DISABLED')
    need(packet['reader_ref']==ACCEPTED_CODE_PINS[READER_PATH] and packet['config_ref']==ACCEPTED_CONFIG_PIN
        and packet['review_ref']==ACCEPTED_REVIEW_PIN and packet['code_refs']==ACCEPTED_CODE_PINS and packed(packet['limits'])==packed(LIMITS),'ACTUAL_BINDINGS')
    need(packet['input_manifest_ref'] is None,'NO_ACTUAL_INPUT_MANIFEST_YET')
    return {'status':'ACTUAL_DISABLED_PENDING_INDEPENDENT_CODE_PACKET_LEAD_RELEASE','real_reader_calls':0}


def actual_entry(*args,**kwargs):
    # No actual plan, private manifest or lead release exists in this candidate.
    raise LedgerRefused('ACTUAL_DISABLED_PENDING_REVIEWED_PACKET_AND_LEAD_RELEASE')


ACCEPTED_CODE_PINS={'src/civiclab/__init__.py': {'path': 'src/civiclab/__init__.py', 'bytes': 106, 'sha256': '23bd3100ad3fd5ef94e459572a286f3f87b321c9676b36507c859bcf7dfadd50'}, 'src/civiclab/common.py': {'path': 'src/civiclab/common.py', 'bytes': 8476, 'sha256': '566c5f3947e3048a1521d1edfa2ee6e7ade7b66502e3b4ee6ee440573eb885fa'}, 'src/civiclab/e01/__init__.py': {'path': 'src/civiclab/e01/__init__.py', 'bytes': 422, 'sha256': 'aff117761fad19eec67ce32b5eae12c9b84921a71f0458e854a55c0237f77e83'}, 'src/civiclab/e01/pipeline.py': {'path': 'src/civiclab/e01/pipeline.py', 'bytes': 22533, 'sha256': 'caf1b19dd62aab8541c740868b20b618ac62213b8b6be3d597cef14f9b6cd763'}, 'src/civiclab/e01/ballots_v1_9_1.py': {'path': 'src/civiclab/e01/ballots_v1_9_1.py', 'bytes': 18754, 'sha256': '30e02bfa068f400846c8feff612695c3ba2c12497d6bc1567ad4c75858788f8b'}, 'src/civiclab/e01/ballots_v1_7.py': {'path': 'src/civiclab/e01/ballots_v1_7.py', 'bytes': 8887, 'sha256': 'b45746439df1e50469f76a7d6ff9acb8bb0536e2f1d605eb116a28460b169062'}, 'src/civiclab/e01/ballots.py': {'path': 'src/civiclab/e01/ballots.py', 'bytes': 25981, 'sha256': '67108d9641cabc04eb17b55896122bce31413059e8682dd9a358dc81d328d8ec'}, 'src/civiclab/e01/idaho_v1_8_1.py': {'path': 'src/civiclab/e01/idaho_v1_8_1.py', 'bytes': 20513, 'sha256': '1413f9a6e784e88d82b0ffe0beb2e8323775c5a8b55a1f5fc223f4a2505c2bb7'}, 'src/civiclab/e01/delaware_v1_7.py': {'path': 'src/civiclab/e01/delaware_v1_7.py', 'bytes': 8546, 'sha256': '929ecadc08bdcb3cfad881f68443951a339f56731c2ab72101f1cda45f4d74c6'}, 'src/civiclab/e01/nebraska_v1_7.py': {'path': 'src/civiclab/e01/nebraska_v1_7.py', 'bytes': 6137, 'sha256': '7ccd0a19bc015440587b93283956b27b958a1f1530d5551d6bb23fb463607e5e'}, 'src/civiclab/e01/maine_v1_5.py': {'path': 'src/civiclab/e01/maine_v1_5.py', 'bytes': 9833, 'sha256': 'e07da3eeb097fe5ed85f4d9445a6d1dc50c28c5b87c97dc7a153e866770ca179'}, 'src/civiclab/e01/ballot_formats_v1_3.py': {'path': 'src/civiclab/e01/ballot_formats_v1_3.py', 'bytes': 6860, 'sha256': '281ae5eb4f3a71ab29b22b8944256c68a513712b4e4c289b7c2b6d09f1534916'}, 'src/civiclab/e01/ballot_capture_formats_v1_4.py': {'path': 'src/civiclab/e01/ballot_capture_formats_v1_4.py', 'bytes': 4781, 'sha256': '0c8cc0be58b249c9d31968a439025e5025f42949abdfe15214496f63fddbf370'}, 'src/civiclab/e01/ballot_formats_v1_6.py': {'path': 'src/civiclab/e01/ballot_formats_v1_6.py', 'bytes': 5856, 'sha256': 'fb5fb665225dfdef782eef3f8ba712cd0eb67816e9b69632323e39310a19faa9'}}
ACCEPTED_CONFIG_PIN={'path': 'configs/e01_typed_readiness_v1_9_1_candidate.json', 'bytes': 14122, 'sha256': 'f017d3b4ceb1647add88eeb66a8d4d386f156f98169ac3807f7d800083fb2997'}
ACCEPTED_REVIEW_PIN={'path': 'reports/INDEPENDENT_AUDIT_E01_V1_9_1_ACTUAL_PRIMARY_REPLAY.json', 'bytes': 15513, 'sha256': '31bb4e389aad209d24a276347023de5f2eab3ed03a3e91d8745128dcfc8115e2'}
SOURCE_IDS=('nj_senate', 'nj_nominee_certification', 'nc_federal_general', 'fl_vacancy_law', 'senate_class_III', 'senate_appointments', 'fl_broward_notice', 'fl_palm_notice', 'senate_class_II', 'co_general', 'va_index', 'va_federal', 'wy_index', 'wy_general', 'ks_general_dom', 'ks_general_browser', 'ak_senate_dom', 'ak_general_browser', 'me_general', 'me_withdrawals', 'me_writeins', 'me_index_browser', 'me_office_key', 'ia_general', 'ia_index_browser', 'nh_general', 'nh_index_browser', 'nh_post_primary_vacancies', 'nh_withdrawals', 'de_index', 'de_general', 'de_writeins', 'de_general_xlsx', 'ne_index', 'ne_general', 'id_general_index', 'id_candidate_search', 'id_browser_visible', 'id_browser_federal', 'id_browser_senate')
