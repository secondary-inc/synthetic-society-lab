"""Finite fixed-campaign BOOT/EXEC controller; external exact phase packet required.

No source or PDF operation occurs on import. BOOT has zero source access; EXEC
requires independent prepared review and the existing immutable BOOT anchor.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import selectors
import subprocess
import sys
import time

if __name__=='__main__' and len(sys.argv)==4 and sys.argv[1] in {'--boot','--exec'}:
    sys.path.insert(0,str(Path(sys.argv[2]).absolute()/'src'))

from civiclab.e01 import clerk2020_native_campaign_v2 as n
from civiclab.e01 import clerk2020_source_worker_v2 as worker
from civiclab.e01 import clerk2020_source_format_adapter_v1 as adapter
from civiclab.e01.clerk2020_m2_v1_1_contracts import canonical,decode,digest,exact,hex64,require,sha,run_id

ENTRY='src/civiclab/e01/clerk2020_source_job_v2.py'
METHODS='configs/e01_clerk2020_monotone_successor_methods_v2_1_20261112.json'
METHODS_SHA='184aee8fc46985dd607e083b06b607a9daf16004e7008dc87197f9741ea6668d'
JOB='clerk2020_source_format_job2'
DATA_ROOT='data/raw/e01_clerk_documents_capture_v1/'
MAX_AUTHORITY=129024
CODE_PATHS=worker.CODE_PATHS
SOURCE_ORDER=('clerk2020_statistics','clerk2026_nominees')
QUALIFIED_TOTAL=518
QUALIFIED_NONPROJECT=497


class SourceResourceStop(RuntimeError):
    pass


class ResourceWindow:
    def __init__(self,phase):
        self.started=self.prior=time.monotonic();self.cpu_started=self.cpu_prior=self.cpu()
        self.wall=45 if phase=='BOOT' else 75;self.cpu_limit=10000 if phase=='BOOT' else 50000
    @staticmethod
    def cpu():
        own=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
        return (own.ru_utime+own.ru_stime+children.ru_utime+children.ru_stime)*1000
    def check(self):
        now=time.monotonic();cpu=self.cpu()
        if (now<self.prior or cpu<self.cpu_prior or now-self.started>self.wall
                or cpu-self.cpu_started>self.cpu_limit):
            raise SourceResourceStop('SOURCE_RESOURCE_LIMIT')
        self.prior=now;self.cpu_prior=cpu


def source_declarations():
    return [{'source_id':sid,'path':DATA_ROOT+sid+'.pdf',**adapter.SOURCES[sid]} for sid in SOURCE_ORDER]


def source_set_sha():return digest(source_declarations())


def safe_relative(name):
    return (type(name) is str and 0<len(name)<=512 and not name.startswith('/')
        and all(p not in {'','.','..'} for p in name.split('/'))
        and not any(ord(c)<32 or c=='\\' for c in name))


def read_file(path,maximum):
    n.no_alias(path);before=path.stat()
    require(path.is_file() and before.st_size+1<=maximum)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        require(n.file_identity(os.fstat(stream.fileno()))==n.file_identity(before))
        body=stream.read(before.st_size+1)
        require(len(body)==before.st_size and n.file_identity(os.fstat(stream.fileno()))==n.file_identity(before))
    require(n.file_identity(path.stat())==n.file_identity(before))
    return body,len(body)+1


class ReadBudget:
    def __init__(self,maximum):self.maximum=maximum;self.used=0;self.observed=0
    def reserve(self,amount):
        require(type(amount) is int and amount>=0 and self.used+amount<=self.maximum);self.used+=amount
    def observe(self,amount):
        require(type(amount) is int and amount>=0 and self.observed+amount<=self.used);self.observed+=amount
    def read(self,root,ref):
        exact(ref,{'path','bytes','sha256'})
        require(safe_relative(ref['path']) and not ref['path'].startswith(('data/raw/','.env'))
                and type(ref['bytes']) is int and 0<=ref['bytes']<=self.maximum and hex64(ref['sha256']))
        require(self.used+ref['bytes']+1<=self.maximum)
        # Reservation is conservative before the descriptor is opened.
        self.reserve(ref['bytes']+1)
        raw,charge=read_file(root/ref['path'],ref['bytes']+1)
        require(charge==ref['bytes']+1 and sha(raw)==ref['sha256']);self.observe(len(raw));return raw


def metadata_json(raw,maximum):
    require(type(raw) is bytes and len(raw)<=maximum)
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result);result[key]=value
        return result
    def no_float(value):raise n.Refused()
    value=json.loads(raw,object_pairs_hook=pairs,parse_float=no_float,parse_constant=no_float)
    canonical(value);return value


def phase_packet(root,raw,expected,phase):
    require(type(raw) is bytes and len(raw)<=MAX_AUTHORITY and hex64(expected) and sha(raw)==expected)
    p=decode(raw,MAX_AUTHORITY)
    exact(p,{'kind','registration','static_spec','decision','issued'})
    require(p['kind']=='CLERK_SOURCE_PHASE_PACKET_V2_1')
    reg=n.FixedRegistrar(n.FixedStore(root),source_set_sha())
    require(canonical(p['registration'])==canonical(reg.binding()))
    spec=p['static_spec']
    exact(spec,{'kind','root_sha256','source_set_sha256','methods_ref','code_refs','qualified_ref',
                'runtime_review_ref','acquisition_refs','ancestor_refs','past_limits','code_review_ref'})
    require(spec['kind']=='CLERK_SOURCE_STATIC_SPEC_V2_1' and spec['root_sha256']==sha(str(root).encode())
            and spec['source_set_sha256']==source_set_sha() and spec['methods_ref']['path']==METHODS
            and spec['methods_ref']['sha256']==METHODS_SHA)
    exact(spec['code_refs'],CODE_PATHS)
    require(sum(ref['bytes']+1 for ref in spec['code_refs'].values())<=524288)
    for path,ref in spec['code_refs'].items():
        exact(ref,{'bytes','sha256'});require(type(ref['bytes']) is int and 0<ref['bytes']<=262144 and hex64(ref['sha256']))
    decision=p['decision']
    fields={'kind','phase','static_spec_sha256','source_set_sha256','phase_budget','expected_anchor_sha256'}
    if phase=='EXEC':fields|={'prepared_ref','prepared_review_ref','job_id'}
    exact(decision,fields)
    require(decision['kind']=='CLERK_SOURCE_DECISION_V2_1' and decision['phase']==phase
            and decision['static_spec_sha256']==digest(spec) and decision['source_set_sha256']==source_set_sha()
            and canonical(decision['phase_budget'])==canonical(n.PREFIX_BUDGETS[phase]))
    if phase=='BOOT':require(decision['expected_anchor_sha256'] is None)
    else:require(hex64(decision['expected_anchor_sha256']) and decision['job_id']==JOB)
    issued=p['issued'];require(issued['decision_sha256']==digest(decision)
            and issued['expected_anchor_sha256']==decision['expected_anchor_sha256'])
    return p,reg


def compact(slot,ref):return {'slot':slot,'bytes':ref['bytes'],'sha256':ref['sha256']}


def read_slot(store,ref,budget):
    exact(ref,{'slot','bytes','sha256'})
    require(ref['slot'] in n.LAYOUT and type(ref['bytes']) is int and ref['bytes']>=0 and hex64(ref['sha256']))
    if store.read_meter is not budget:budget.reserve(ref['bytes']+1)
    raw,charge=store.read(ref['slot'],ref['bytes']+1)
    require(charge==ref['bytes']+1 and sha(raw)==ref['sha256'])
    if store.read_meter is not budget:budget.observe(len(raw))
    return raw


def path_for_label(root,label):
    require(type(label) is str and label.startswith(('REPO/','PYTHON_BASE/')))
    if label.startswith('REPO/'):path=root/label[5:]
    else:path=Path(sys.base_prefix).resolve()/label[12:]
    require(worker.origin_allowed(path,root,Path(sys.base_prefix).resolve()));return path


def code_check(root,refs,maximum):
    used=0;observed=0
    for name,ref in refs.items():
        require(used+ref['bytes']+1<=maximum)
        raw,charge=read_file(root/name,ref['bytes']+1);used+=charge;observed+=len(raw)
        require(sha(raw)==ref['sha256'])
    return observed,used


def check_qualified_rows(qualified):
    rows=qualified['runtime_manifest']
    require(len(rows)==QUALIFIED_TOTAL and sum(not r[0].startswith(('REPO/src/','REPO/tests/'))
            for r in rows)==QUALIFIED_NONPROJECT)
    return qualified


def boot_catalog(root,spec,qualified,remaining):
    expected={row[0]:row[1:] for row in qualified['runtime_manifest']}
    paths={label:path_for_label(root,label) for label in expected}
    base=Path(sys.base_prefix).resolve()
    for name in CODE_PATHS:
        for path in [root/name,Path(importlib.util.cache_from_source(str(root/name)))]:
            if path.is_file():paths['REPO/'+str(path.relative_to(root))]=path
    rows=[];identities=[];used=0
    for label,path in sorted(paths.items()):
        h,size,charge=worker.q.frozen._stable_hash(path,remaining-used);used+=charge
        if label in expected:require([size,h]==expected[label])
        require(worker.origin_allowed(path,root,base))
        rows.append([label,size,h]);identities.append(list(n.file_identity(path.stat())))
    require(len(rows)<=1024 and len(canonical(rows))<=98304)
    catalog=[row+[identity] for row,identity in zip(rows,identities)]
    require(len(canonical(catalog))<=worker.CATALOG_CAP)
    extras=[row for row in rows if row[0] not in expected]
    cache={'kind':'CLERK_SOURCE_RUNTIME_CACHE_V2_1','identities':identities,'extra_rows':extras,
           'runtime_manifest_sha256':digest(rows),'qualified_worker_sha256':spec['qualified_ref']['sha256']}
    require(len(canonical(cache))<=65536)
    return rows,cache,catalog,used


def check_code_review(review,spec):
    require(type(review) is dict and review.get('status')=='PASS_CLOSED_FIXED_CAMPAIGN_CODE_V2_1'
            and review.get('reviewer_role')=='independent_auditor'
            and canonical(review.get('code_refs'))==canonical(spec['code_refs'])
            and review.get('methods_sha256')==METHODS_SHA
            and review.get('source_set_sha256')==source_set_sha())


def fail_record(store,journal,phase):
    # No exception messages, raw excerpts, traceback locals or source paths.
    if journal is not None:
        journal.counters.stop_unknown()
        snapshot=journal.counters.snapshot()
    else:snapshot=None
    obj={'kind':'CLERK_SOURCE_FAILED_OR_UNKNOWN_V2_1','phase':phase,'credit_restored':0,
         'source_format_accepted':False,'no_retry':True,'state':snapshot,'model_calls':0,'cost_usd':0}
    try:
        if not store.exists('private_stderr'):
            store.create('private_stderr',canonical(obj))
        if store.run_id is not None and not store.exists('terminal_failure'):
            store.create('terminal_failure',canonical({'kind':obj['kind'],'phase':phase,
                'state_sha256':None if snapshot is None else digest(snapshot),'no_retry':True,
                'source_format_accepted':False,'credit_restored':0}))
    except BaseException:pass
    return {'status':'FAILED_OR_UNKNOWN_NO_RETRY','phase':phase,'source_format_accepted':False,
            'model_calls':0,'cost_usd':0}


def run_boot(root,raw,expected):
    root=Path(root).absolute();p,reg=phase_packet(root,raw,expected,'BOOT');store=reg.store
    started=time.monotonic();journal=None;window=ResourceWindow('BOOT');claimed=False
    try:
        issued,reservation,res_ref=reg.consume('BOOT',canonical(p['issued']),digest(p['issued']))
        claimed=True
        c=n.PersistentCounters();c.precharge_writes()
        c.reserve({'bootstrap_attempts':1},'BOOT');c.settle('bootstrap_attempts',1,1,'BOOT')
        c.reserve({'metadata_read_bytes':262144},'DELIVERY');c.settle('metadata_read_bytes',262144,None,'DELIVERY')
        genesis={'kind':'CLERK_SOURCE_GENESIS_V2_1','binding':reg.binding(),'static_spec_sha256':digest(p['static_spec']),
                 'decision_sha256':digest(p['decision']),'issued_sha256':digest(p['issued']),
                 'reservation_sha256':res_ref['sha256'],'initial_state':c.snapshot(),'previous':None}
        gref=store.create('genesis',canonical(genesis))
        store.create('normal_journal',b'');journal=n.NativeJournal(store,gref['sha256'],c)
        journal.append('BOOT','BOOT_RESERVE',{'reservation_token_sha256':res_ref['sha256']},
            reserve={'metadata_read_bytes':5242880,'code_integrity_read_bytes':268435456,
                     'active_time_ms':45000,'cpu_ms':10000})
        window.check()
        budget=ReadBudget(5242880);store.read_meter=budget;spec=p['static_spec']
        predecessor_refs_sha=reg.adopt_successor(digest(p['issued']))
        a0=reg.cas(None,'anchor_initial',{'genesis_sha256':gref['sha256']})
        methods=metadata_json(budget.read(root,spec['methods_ref']),65536)
        require(methods['kind']=='E01_FIXED_SOURCE_FORMAT_MONOTONE_SUCCESSOR_METHODS_V2_1_CANDIDATE')
        require(canonical(spec['ancestor_refs'])==canonical(methods['past_consumed_qualification_records'])
                and canonical(spec['past_limits'])==canonical(methods['past_qualified_limits']))
        require(canonical(spec['qualified_ref'])==canonical(methods['qualified_worker'])
                and canonical(spec['runtime_review_ref'])==canonical(methods['qualified_runtime_actual'])
                and canonical(spec['acquisition_refs'])==canonical([methods['accepted_acquisition'],methods['acquisition_handoff']]))
        review=metadata_json(budget.read(root,spec['code_review_ref']),131072);check_code_review(review,spec)
        runtime_review=metadata_json(budget.read(root,spec['runtime_review_ref']),262144)
        require(runtime_review.get('source_authority') is not True)
        qualified=check_qualified_rows(worker.q.validate_child(budget.read(root,spec['qualified_ref'])))
        for ref in spec['acquisition_refs']:budget.read(root,ref)
        for name,ref in spec['ancestor_refs'].items():budget.read(root,dict(path=name,**ref))
        code_observed,code_bytes=code_check(root,spec['code_refs'],524288)
        rows,cache,catalog,tree_bytes=boot_catalog(root,spec,qualified,268435456-code_bytes)
        window.check()
        cache_ref=store.create('runtime_stat_cache',canonical(cache))
        journal.append('BOOT','READ_SETTLE',{'effect_id':'boot_code','input_hash_verified':True},
                       settle=[['code_integrity_read_bytes',268435456,code_observed+sum(r[1] for r in rows)]])
        journal.append('BOOT','READ_SETTLE',{'effect_id':'boot_metadata','input_hash_verified':True},
                       settle=[['metadata_read_bytes',5242880,None],
                               ['active_time_ms',45000,None],['cpu_ms',10000,None]])
        snap={'kind':'CLERK_SOURCE_BOOT_COUNTERS_V2_1','state':journal.counters.snapshot(),
              'observed_through_sequence':journal.sequence,'head_before_snapshot_sha256':journal.head}
        xref=store.create('boot_counters',canonical(snap))
        window.check()
        journal.append('BOOT','BOOT_COMMIT',{'verified_code_set_sha256':digest(spec['code_refs']),
            'verified_runtime_manifest_sha256':digest(rows),'verified_metadata_set_sha256':digest(spec),
            'counter_snapshot_sha256':xref['sha256']})
        require((time.monotonic()-started)*1000<=45000)
        receipt={'kind':'CLERK_SOURCE_BOOT_RECEIPT_V2_1','outcome':'VERIFIED_NO_SOURCE',
            'registration_sha256':digest(reg.binding()),'static_spec_sha256':digest(spec),
            'decision_sha256':digest(p['decision']),'issued_sha256':digest(p['issued']),
            'reservation_ref':compact('boot_reservation',res_ref),'genesis_ref':compact('genesis',gref),
            'counter_ref':compact('boot_counters',xref),'cache_ref':compact('runtime_stat_cache',cache_ref),
            'runtime_manifest_sha256':digest(rows),'runtime_catalog_sha256':digest(catalog),
            'prefix_sha256':sha(journal.prefix),'prefix_bytes':len(journal.prefix),'prefix_head_sha256':journal.head,
            'source_operations':0,'model_calls':0}
        br=store.create('boot_receipt',canonical(receipt))
        window.check()
        a1=reg.cas(a0['sha256'],'anchor_boot',{'bootstrap_receipt_sha256':br['sha256'],
                     'counter_snapshot_sha256':xref['sha256'],'genesis_sha256':gref['sha256']})
        window.check()
        prepared={'kind':'CLERK_SOURCE_PREPARED_V2_1','binding':reg.binding(),'job_id':JOB,
            'static_spec_sha256':digest(spec),'boot_receipt_ref':compact('boot_receipt',br),
            'completed_bootstrap_anchor_sha256':a1['sha256'],'counter_ref':compact('boot_counters',xref),
            'genesis_ref':compact('genesis',gref),'cache_ref':compact('runtime_stat_cache',cache_ref),
            'runtime_catalog_sha256':digest(catalog),'source_set_sha256':source_set_sha()}
        pr=store.create('prepared_metadata',canonical(prepared))
        window.check()
        return {'status':'BOOT_PREPARED_NO_SOURCE','prepared_ref':compact('prepared_metadata',pr),
                'completed_anchor_sha256':a1['sha256'],'source_operations':0,'model_calls':0,'cost_usd':0}
    except FileExistsError:
        if not claimed:
            return {'status':'FAILED_OR_UNKNOWN_NO_RETRY','phase':'BOOT','replay_refused':True,
                    'source_format_accepted':False,'model_calls':0,'cost_usd':0}
        return fail_record(store,journal,'BOOT')
    except BaseException:return fail_record(store,journal,'BOOT')


def reconstruct_catalog(qualified,cache):
    exact(cache,{'kind','identities','extra_rows','runtime_manifest_sha256','qualified_worker_sha256'})
    require(cache['kind']=='CLERK_SOURCE_RUNTIME_CACHE_V2_1')
    rows=sorted(qualified['runtime_manifest']+cache['extra_rows'])
    require(len({r[0] for r in rows})==len(rows) and len(rows)==len(cache['identities'])
            and digest(rows)==cache['runtime_manifest_sha256'])
    catalog=[row+[identity] for row,identity in zip(rows,cache['identities'])]
    require(len(canonical(catalog))<=worker.CATALOG_CAP);return catalog


def source_snapshot(root,source_id):
    require(source_id in SOURCE_ORDER)
    ref=adapter.SOURCES[source_id];raw,charge=read_file(root/(DATA_ROOT+source_id+'.pdf'),ref['bytes']+1)
    require(len(raw)==ref['bytes'] and sha(raw)==ref['sha256']);return raw,charge


def child_request(source_id,snapshot,catalog,spec,context,res_ref,decision,registration):
    request={'kind':'CLERK_SOURCE_MEMORY_REQUEST_V2_1','source_id':source_id,
        'source_chunks_b64':[base64.b64encode(snapshot[i:i+49152]).decode() for i in range(0,len(snapshot),49152)],
        'runtime_catalog':catalog,'code_refs':spec['code_refs'],
        'registration_sha256':digest(registration),
        'execution_decision_sha256':digest(decision),'reservation_sha256':res_ref['sha256'],'context_sha256':context}
    raw=canonical(request);require(len(raw)<=worker.INPUT_CAPS[source_id]);return raw


def exchange(proc,packet,parent_start,out,err):
    began=time.monotonic();prior=began;offset=peak=0
    def remaining():
        nonlocal prior
        now=time.monotonic();require(now>=prior);prior=now;left=min(35-(now-began),75-(now-parent_start));require(left>0);return left
    with selectors.DefaultSelector() as selector:
        for stream,event in [(proc.stdin,selectors.EVENT_WRITE),(proc.stdout,selectors.EVENT_READ),(proc.stderr,selectors.EVENT_READ)]:
            os.set_blocking(stream.fileno(),False);selector.register(stream,event)
        while selector.get_map():
            left=remaining()
            if proc.poll() is None:
                try:peak=max(peak,worker.q.frozen._sample_rss(proc.pid,min(1,left)))
                except Exception:
                    if proc.poll() is None:raise
            for key,_ in selector.select(min(.05,remaining())):
                stream=key.fileobj
                if stream is proc.stdin:
                    try:count=os.write(stream.fileno(),packet[offset:offset+65536])
                    except BlockingIOError:continue
                    require(count>0);offset+=count
                    if offset==len(packet):selector.unregister(stream);stream.close()
                else:
                    target,cap=(out,262144) if stream is proc.stdout else (err,4096)
                    try:chunk=os.read(stream.fileno(),min(65536,cap-len(target)+1))
                    except BlockingIOError:continue
                    if not chunk:selector.unregister(stream);stream.close()
                    else:target.extend(chunk);require(len(target)<=cap)
        proc.wait(timeout=remaining())
    require(proc.returncode==0 and offset==len(packet) and not err);return peak


class ChildProcessStop(RuntimeError):
    def __init__(self,out,err):
        super().__init__('CLERK_SOURCE_CHILD_PROCESS_STOP')
        self.captured_out=out;self.captured_err=err


def safe_child_failure(raw,sid,context,stderr=b''):
    result={'kind':'CLERK_SOURCE_SAFE_FAILURE_V2_1','source_id':sid,'context_sha256':context,
        'wire_bytes':len(raw),'wire_sha256':sha(raw),'stderr_bytes':len(stderr),'stderr_sha256':sha(stderr),
        'raw_wire_retained':False,'source_format_accepted':False,'diagnostics':None}
    try:
        obj=decode(raw,8192)
        exact(obj,{'kind','stage','source_format_accepted','warmup_progress','warmup_refusal',
                   'source_first_refusal','source_exception','model_calls','cost_usd'})
        require(obj['kind']=='CLERK_SOURCE_WORKER_STOP_V2_1' and obj['source_format_accepted'] is False
                and obj['stage'] in {'RESOURCE_LIMIT_SETUP','INPUT','IMPORT_IDENTITY','GENERATED_WARMUP','RUNTIME_INTEGRITY','ACTUAL_SOURCE_FORMAT'}
                and type(obj['model_calls']) is int and obj['model_calls']==0
                and type(obj['cost_usd']) is int and obj['cost_usd']==0)
        progress=obj['warmup_progress']
        require(type(progress) is dict and set(progress) in [set(),{'reader_attempts_entered','text_marker_pages_checked','negative_failure_stages'}])
        if progress:
            require(type(progress['reader_attempts_entered']) is int and 0<=progress['reader_attempts_entered']<=4
                    and type(progress['text_marker_pages_checked']) is int and 0<=progress['text_marker_pages_checked']<=119
                    and type(progress['negative_failure_stages']) is list and len(progress['negative_failure_stages'])<=2
                    and all(x in {'STRUCTURE','READER_CONSTRUCTION'} for x in progress['negative_failure_stages']))
        refusal=obj['warmup_refusal']
        if refusal is not None:
            require(type(refusal) is dict and set(refusal) in [{'event','phase','predicate'}, {'event','phase','predicate','directory_label'}])
            require(refusal['phase'] in {'BOOTSTRAP','WARMUP','HASH','STRICT'}
                    and refusal['event'] in {'open','import','os.listdir','os.scandir','ctypes.dlopen','os.chdir','phase','socket.*','process'}
                    and refusal['predicate'] in {'PATH_TYPE','ORIGIN_NOT_DECLARED','ALIASED_OR_UNAVAILABLE_ORIGIN',
                    'NETWORK_OR_PROCESS_REFUSED','DLOPEN_OR_CHDIR_REFUSED','IMPORT_EVENT_LIMIT','IMPORT_NAME_TYPE',
                    'IMPORT_NAMESPACE_NOT_DECLARED','NATIVE_BACKEND_PATH_REFUSED','OPEN_ARGUMENT_SHAPE',
                    'WRITE_OR_UNKNOWN_OPEN_REFUSED','OPEN_EVENT_LIMIT','READ_STAT_UNAVAILABLE','READ_NOT_REGULAR_FILE',
                    'READ_BYTE_LIMIT','READ_IDENTITY_DRIFT','CACHE_SOURCE_ALIAS_REFUSED','DIRECTORY_EVENT_LIMIT',
                    'DIRECTORY_ARGUMENT_SHAPE','HASH_IMPORT_REFUSED','HASH_OPEN_LIMIT_OR_UNADMITTED',
                    'HASH_DESCRIPTOR_UNAVAILABLE','HASH_DESCRIPTOR_NOT_ADMITTED','HASH_PATH_NOT_ADMITTED_OR_REOPENED',
                    'HASH_IDENTITY_DRIFT','HASH_READ_BYTE_LIMIT','HASH_DIRECTORY_EVENT_REFUSED',
                    'PHASE_TRANSITION_REFUSED','PRIOR_REFUSAL','HASH_CAPTURE_INCOMPLETE'})
            if 'directory_label' in refusal:require(refusal['directory_label'] in worker.q.DIRECTORY_LABELS)
        guard=obj['source_first_refusal']
        if guard is not None:
            exact(guard,{'event'});require(guard['event'] in adapter.DENIED|{'socket.*','os.exec*'})
        error=obj['source_exception']
        if error is not None:
            exact(error,{'type','stage','page','frames','traceback_truncated'})
            require(error['type'] in {c.__name__ for c in adapter.SAFE_TYPES}|{'UNKNOWN_EXACT_TYPE'}
                    and error['stage'] in {'NOT_STARTED','INPUT_CONTRACT','READER_CONSTRUCTION','READER_CONTRACT',
                        'STRUCTURE','PAGE_EXTRACTION','PAGE_PROJECTION','FINAL_READER_CONTRACT','OUTPUT_CONTRACT','COMPLETE'}
                    and type(error['page']) is int and 0<=error['page']<=81
                    and type(error['frames']) is list and len(error['frames'])<=32 and type(error['traceback_truncated']) is bool)
            for frame in error['frames']:
                exact(frame,{'function','line'})
                require(frame['function'] in {'inspect_source','_check_structure','require','page_projection','parse_guard'}
                        and type(frame['line']) is int and 0<frame['line']<=100000)
        result['diagnostics']=obj
    except BaseException:pass
    require(len(canonical(result))<=8192);return result


def dispatch(root,raw,parent_start):
    proc=None;out=bytearray();err=bytearray()
    try:
        proc=subprocess.Popen([sys.executable,'-I','-B','-S',str(root/worker.ENTRY),
            '--source-format-worker',str(root),sha(raw)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,cwd=root,start_new_session=True,env={'PATH':os.defpath,'LC_ALL':'C'})
        peak=exchange(proc,raw,parent_start,out,err);return bytes(out),bytes(err),peak
    except BaseException:
        raise ChildProcessStop(bytes(out),bytes(err)) from None
    finally:
        if proc is not None:
            if proc.poll() is None:
                try:os.killpg(proc.pid,9)
                except ProcessLookupError:pass
            proc.wait(timeout=1)
            for stream in [proc.stdin,proc.stdout,proc.stderr]:
                if stream is not None:stream.close()


def validate_child(raw,sid,context,catalog):
    obj=decode(raw,262144);exact(obj,{'metadata','private_projection_chunks_b64'});m=obj['metadata']
    exact(m,{'kind','status','source_id','context_sha256','registration_sha256',
        'execution_decision_sha256','reservation_sha256','source_sha256','source_bytes',
        'runtime_indices','runtime_manifest_sha256','runtime_hash_bytes_observed','runtime_hash_bytes_reserved',
        'warmup','warmup_pages','warmup_readers','source_readers','source_pages','native_backend_hash_matched',
        'strict_first_refusal','cpu_ms_through_private_projection','public_diagnostics',
        'private_projection_sha256','private_projection_bytes','source_counts_or_features_adopted',
        'model_calls','cost_usd'})
    require(m['kind']=='CLERK_SOURCE_WORKER_RECEIPT_V2_1' and m['status']=='SOURCE_FORMAT_ONLY_COMPLETE'
            and m['source_id']==sid and m['context_sha256']==context
            and m['source_sha256']==adapter.SOURCES[sid]['sha256'] and m['source_bytes']==adapter.SOURCES[sid]['bytes']
            and m['source_pages']==adapter.SOURCES[sid]['pages'] and m['source_readers']==1
            and m['warmup_readers']==4 and m['warmup_pages']==119 and m['strict_first_refusal'] is None
            and m['warmup']['first_refusal'] is None and m['source_counts_or_features_adopted'] is False
            and m['model_calls']==0 and m['cost_usd']==0 and m['native_backend_hash_matched'] is True
            and type(m['cpu_ms_through_private_projection']) is int
            and 0<m['cpu_ms_through_private_projection']<=8000)
    for key in ['registration_sha256','execution_decision_sha256','reservation_sha256']:
        require(hex64(m[key]))
    for key in ['source_bytes','source_pages','source_readers','warmup_readers','warmup_pages',
                'runtime_hash_bytes_observed','runtime_hash_bytes_reserved','private_projection_bytes','model_calls','cost_usd']:
        require(type(m[key]) is int)
    indices=m['runtime_indices'];require(type(indices) is list and len(indices)==len(set(indices))
        and all(type(i) is int and 0<=i<len(catalog) for i in indices))
    rows=[catalog[i][:3] for i in indices]
    require(digest(rows)==m['runtime_manifest_sha256'] and sum(r[1] for r in rows)==m['runtime_hash_bytes_observed']
            and m['runtime_hash_bytes_reserved']==sum(r[1]+1 for r in rows)
            and m['runtime_hash_bytes_reserved']+m['warmup']['read_bytes_reserved']<=worker.INTEGRITY_CAP)
    expected_nonproject={row[0] for row in catalog if not row[0].startswith('REPO/src/')
                         and not row[0].startswith('REPO/tests/')}
    require({row[0] for row in rows if not row[0].startswith('REPO/src/')
             and not row[0].startswith('REPO/tests/')}==expected_nonproject)
    w=m['warmup']
    exact(w,{'reader_attempts','page_extractions','file_open_events','read_bytes_reserved',
        'directory_events','directory_labels_observed','import_events','read_files','missing_bytecode_probes',
        'first_refusal','hash_open_events','hash_read_bytes_reserved','hash_files_opened','hash_descriptor_events'})
    require(w['reader_attempts']==4 and type(w['reader_attempts']) is int
            and w['page_extractions']==119 and type(w['page_extractions']) is int)
    for key,cap in [('file_open_events',512),('read_bytes_reserved',67108864),
                    ('directory_events',256),('import_events',512),('read_files',512),
                    ('missing_bytecode_probes',512),('hash_open_events',2048),
                    ('hash_files_opened',1024),('hash_descriptor_events',1024),
                    ('hash_read_bytes_reserved',worker.INTEGRITY_CAP)]:
        require(type(w[key]) is int and 0<=w[key]<=cap)
    require(w['hash_files_opened']==len(rows) and w['hash_descriptor_events']<=len(rows)
            and w['hash_open_events']==len(rows)+w['hash_descriptor_events']
            and w['hash_read_bytes_reserved']==m['runtime_hash_bytes_reserved']
            and w['read_files']+w['missing_bytecode_probes']<=w['file_open_events'])
    labels=w['directory_labels_observed'];require(type(labels) is list and len(labels)<=len(worker.q.DIRECTORY_LABELS))
    seen=set()
    for row in labels:
        require(type(row) is list and len(row)==2 and type(row[0]) is str
                and row[0] in worker.q.DIRECTORY_LABELS and row[0] not in seen
                and type(row[1]) is int and 0<row[1]<=256);seen.add(row[0])
    require(sum(r[1] for r in labels)==w['directory_events'])
    public=m['public_diagnostics']
    exact(public,{'label','kind','source_id','source_sha256','source_bytes','source_role','page_count',
        'text_characters','text_utf8_bytes','omitted_text_utf8_bytes','unknown_role_layout_pages',
        'structure_nodes_checked','candidate_or_vote_records_parsed','source_or_feature_adoption','model_calls','cost_usd'})
    require(public['label']=='REAL_SOURCE_FORMAT_INSPECTION_ONLY'
            and public['kind']=='CLERK_NATIVE_FORMAT_DIAGNOSTICS_V1'
            and public['source_id']==sid and public['source_sha256']==adapter.SOURCES[sid]['sha256']
            and public['source_bytes']==adapter.SOURCES[sid]['bytes']
            and public['source_role']==adapter.SOURCES[sid]['role']
            and public['page_count']==adapter.SOURCES[sid]['pages']
            and public['unknown_role_layout_pages']==adapter.SOURCES[sid]['pages']
            and public['candidate_or_vote_records_parsed']==0 and public['source_or_feature_adoption'] is False
            and public['model_calls']==0 and public['cost_usd']==0)
    for key in ['source_bytes','page_count','unknown_role_layout_pages','candidate_or_vote_records_parsed','model_calls','cost_usd']:
        require(type(public[key]) is int)
    for key,cap in [('text_characters',4760000),('text_utf8_bytes',19040000),
                    ('omitted_text_utf8_bytes',19040000),('structure_nodes_checked',16384)]:
        require(type(public[key]) is int and 0<=public[key]<=cap)
    require(public['omitted_text_utf8_bytes']<=public['text_utf8_bytes'])
    data=bytearray();chunks=obj['private_projection_chunks_b64'];require(type(chunks) is list and 1<=len(chunks)<=6)
    for chunk in chunks:
        require(type(chunk) is str and len(chunk)<=65536)
        part=base64.b64decode(chunk,validate=True);require(base64.b64encode(part).decode()==chunk)
        data.extend(part);require(len(data)<=adapter.SOURCES[sid]['worker_output_bytes'])
    private=bytes(data);require(len(private)==m['private_projection_bytes'] and sha(private)==m['private_projection_sha256'])
    p=decode(private,251904)
    exact(p,{'label','kind','source_id','source_sha256','source_bytes','source_role','page_count','pages',
             'candidate_or_vote_records_parsed','printed_dates_or_roles_adopted','retained_full_document'})
    require(p['kind']=='CLERK_NATIVE_FORMAT_INVENTORY_V1' and p['source_bytes']==adapter.SOURCES[sid]['bytes']
            and p['source_role']==adapter.SOURCES[sid]['role'] and type(p['retained_full_document']) is bool)
    require(p['source_id']==sid and p['source_sha256']==adapter.SOURCES[sid]['sha256']
            and p['page_count']==adapter.SOURCES[sid]['pages'] and len(p['pages'])==p['page_count']
            and p['label']=='REAL_SOURCE_FORMAT_INSPECTION_ONLY' and p['candidate_or_vote_records_parsed']==0
            and p['printed_dates_or_roles_adopted'] is False)
    require(len(canonical(m))<=8192);return m,p


def run_exec(root,raw,expected):
    root=Path(root).absolute();p,reg=phase_packet(root,raw,expected,'EXEC');store=reg.store
    started=time.monotonic();journal=None;metadata=ReadBudget(786432);store.read_meter=metadata;projection_stream=None
    window=ResourceWindow('EXEC');writer=None;claimed=False
    usage=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
    start_cpu=usage.ru_utime+usage.ru_stime+children.ru_utime+children.ru_stime
    try:
        _,_,res_ref=reg.consume('EXEC',canonical(p['issued']),digest(p['issued']))
        claimed=True
        require(not store.exists('private_stderr'))
        prepared=decode(read_slot(store,p['decision']['prepared_ref'],metadata),4096)
        require(prepared['binding']==reg.binding() and prepared['source_set_sha256']==source_set_sha()
                and prepared['completed_bootstrap_anchor_sha256']==p['decision']['expected_anchor_sha256']
                and prepared['static_spec_sha256']==digest(p['static_spec']) and prepared['job_id']==JOB)
        predecessor_refs_sha=reg.verify_predecessor()
        pr=metadata_json(metadata.read(root,p['decision']['prepared_review_ref']),131072)
        require(pr.get('reviewer_role')=='independent_auditor' and pr.get('status')=='PASS_PREPARED_EXACT_SOURCE_FORMAT_JOB'
                and pr.get('prepared_sha256')==p['decision']['prepared_ref']['sha256']
                and pr.get('source_set_sha256')==source_set_sha() and pr.get('source_authority')=='EXACT_TWO_SOURCES_FORMAT_ONLY')
        spec=p['static_spec'];qualified=check_qualified_rows(worker.q.validate_child(metadata.read(root,spec['qualified_ref'])))
        cache=decode(read_slot(store,prepared['cache_ref'],metadata),65536)
        require(cache['qualified_worker_sha256']==spec['qualified_ref']['sha256'])
        catalog=reconstruct_catalog(qualified,cache);require(digest(catalog)==prepared['runtime_catalog_sha256'])
        genesis=decode(read_slot(store,prepared['genesis_ref'],metadata),8192)
        receipt=decode(read_slot(store,prepared['boot_receipt_ref'],metadata),2048)
        counter=decode(read_slot(store,prepared['counter_ref'],metadata),4096)
        require(counter['kind']=='CLERK_SOURCE_BOOT_COUNTERS_V2_1' and receipt['outcome']=='VERIFIED_NO_SOURCE'
                and receipt['runtime_catalog_sha256']==digest(catalog))
        prefix,charge=store.read('normal_journal',49153)
        require(sha(prefix)==receipt['prefix_sha256'] and len(prefix)==receipt['prefix_bytes'])
        journal=n.NativeJournal(store,prepared['genesis_ref']['sha256'],
            n.PersistentCounters.restore(genesis['initial_state']),prefix)
        require(journal.head==receipt['prefix_head_sha256'])
        # BOOT snapshot intentionally precedes BOOT_COMMIT, which has no delta.
        require(canonical(journal.counters.snapshot())==canonical(counter['state']))
        rid=run_id(n.CAMPAIGN,JOB,p['decision']);store.bind_run(rid)
        context_obj={'kind':'CLERK_SOURCE_DERIVED_CONTEXT_V2_1','run_id':rid,'job_id':JOB,
            'registration':reg.binding(),'static_spec_sha256':digest(spec),
            'execution_decision_sha256':digest(p['decision']),'issued_sha256':digest(p['issued']),
            'reservation_sha256':res_ref['sha256'],'prepared_sha256':p['decision']['prepared_ref']['sha256']}
        context=digest(context_obj);store.create('derived_context',canonical(context_obj))
        journal.append('EXEC','EXEC_ADMISSION',{'context_sha256':context,'reservation_token_sha256':res_ref['sha256']},
            activate_source=True,reserve={'execution_admission_attempts':1,'source_jobs':1,'metadata_read_bytes':2883584,
                     'active_time_ms':75000,'cpu_ms':50000},
            settle=[['execution_admission_attempts',1,1],['source_jobs',1,1]])
        reg.cas(p['decision']['expected_anchor_sha256'],'anchor_active',{'context_sha256':context,
                'counter_snapshot_sha256':digest(journal.counters.snapshot())})
        for name,ref in spec['ancestor_refs'].items():metadata.read(root,dict(path=name,**ref))
        journal.append('EXEC','DATA_WRITE_SLOT',{'slot_id':'private_projection'})
        projection_stream=n.ProjectionStream(store)
        documents=[];diagnostics=[];receipts=[];child_refs=[];wire=0;peak=0
        for i,sid in enumerate(SOURCE_ORDER):
            window.check()
            if i==0:
                journal.append('EXEC','CODE_RUNTIME_RESERVE',{'effect_id':'hot_before'},reserve={'code_integrity_read_bytes':524288})
                observed,used=code_check(root,spec['code_refs'],524288)
                journal.append('EXEC','READ_SETTLE',{'effect_id':'hot_before','input_hash_verified':True},settle=[['code_integrity_read_bytes',524288,observed]])
            ref=adapter.SOURCES[sid]
            journal.append('EXEC','SOURCE_RESERVE',{'source_id':sid},reserve={'source_read_attempts':1,'source_read_bytes':ref['bytes']+1})
            snapshot,charge=source_snapshot(root,sid)
            journal.append('EXEC','SOURCE_SETTLE',{'source_id':sid,'source_sha256':sha(snapshot)},
                settle=[['source_read_attempts',1,1],['source_read_bytes',ref['bytes']+1,len(snapshot)]])
            store.create('source_receipt_'+str(i),canonical({'source_id':sid,'bytes':len(snapshot),'sha256':sha(snapshot),
                         'role':ref['role'],'source_role_or_count_adopted':False}))
            journal.append('EXEC','BACKEND_RESERVE',{'source_id':sid},reserve={'backend_attempts':1,
                'page_extractions':ref['pages'],'warmup_backend_attempts':4,'warmup_page_extractions':119,
                'total_backend_attempts':5,'total_page_extractions':119+ref['pages'],
                'code_integrity_read_bytes':worker.INTEGRITY_CAP})
            request=child_request(sid,snapshot,catalog,spec,context,res_ref,p['decision'],reg.binding())
            wire+=len(request);require(wire+worker.OUTPUT_CAP<=2097152)
            try:
                response,stderr,child_peak=dispatch(root,request,started)
            except BaseException as dispatch_error:
                captured=dispatch_error.captured_out if type(dispatch_error) is ChildProcessStop else b''
                captured_err=dispatch_error.captured_err if type(dispatch_error) is ChildProcessStop else b''
                safe=safe_child_failure(captured,sid,context,captured_err)
                mr=store.create('child_metadata_'+str(i),canonical(safe))
                store.create('child_ref_'+str(i),canonical(compact('child_metadata_'+str(i),mr)))
                raise
            window.check()
            wire+=len(response)+len(stderr);require(wire<=2097152);peak=max(peak,child_peak)
            try:m,projection=validate_child(response,sid,context,catalog)
            except BaseException:
                safe=safe_child_failure(response,sid,context,stderr)
                mr=store.create('child_metadata_'+str(i),canonical(safe))
                store.create('child_ref_'+str(i),canonical(compact('child_metadata_'+str(i),mr)))
                raise
            require(m['registration_sha256']==digest(reg.binding())
                    and m['execution_decision_sha256']==digest(p['decision']) and m['reservation_sha256']==res_ref['sha256'])
            worker_used=m['runtime_hash_bytes_reserved']+m['warmup']['read_bytes_reserved']
            journal.append('EXEC','BACKEND_SETTLE',{'source_id':sid,'outcome':'COMPLETE',
                'observed_source_pages':ref['pages'],'observed_warmup_pages':119,
                'runtime_manifest_sha256':m['runtime_manifest_sha256']},settle=[['backend_attempts',1,1],
                ['page_extractions',ref['pages'],ref['pages']],['warmup_backend_attempts',4,4],
                ['warmup_page_extractions',119,119],['total_backend_attempts',5,5],
                ['total_page_extractions',119+ref['pages'],119+ref['pages']],
                ['code_integrity_read_bytes',worker.INTEGRITY_CAP,None]])
            mr=store.create('child_metadata_'+str(i),canonical(m))
            child_refs.append(compact('child_metadata_'+str(i),mr))
            store.create('child_ref_'+str(i),canonical(compact('child_metadata_'+str(i),mr)))
            projection_stream.add(canonical(projection),sid)
            documents.append(projection);diagnostics.append(m['public_diagnostics']);receipts.append(m)
            del snapshot,request,response
        journal.append('EXEC','CODE_RUNTIME_RESERVE',{'effect_id':'hot_after'},reserve={'code_integrity_read_bytes':524288})
        observed,used=code_check(root,spec['code_refs'],524288)
        journal.append('EXEC','READ_SETTLE',{'effect_id':'hot_after','input_hash_verified':True},settle=[['code_integrity_read_bytes',524288,observed]])
        require(metadata.used<=786432)
        if not 0<=(time.monotonic()-started)*1000<=75000:
            raise SourceResourceStop('SOURCE_RESOURCE_LIMIT')
        journal.append('EXEC','READ_SETTLE',{'effect_id':'exec_metadata','input_hash_verified':True},
            settle=[['metadata_read_bytes',2883584,metadata.observed+wire],['active_time_ms',75000,None],['cpu_ms',50000,None]])
        projection_ref=projection_stream.finish()
        label='REAL_SOURCE_FORMAT_INSPECTION_ONLY'
        projection=canonical({'label':label,'documents':documents,'candidate_or_vote_records_parsed':0})
        public=canonical({'label':label,'sources':diagnostics,'source_counts_or_features_adopted':False,'model_calls':0,'cost_usd':0})
        provenance=canonical({'label':'SOURCE_FORMAT_ONLY','context_sha256':context,'source_hashes':[adapter.SOURCES[s]['sha256'] for s in SOURCE_ORDER],
            'qualified_worker_ref':spec['qualified_ref'],'stat_cache_ref':prepared['cache_ref'],
            'child_metadata_refs':child_refs,'boot_receipt_ref':prepared['boot_receipt_ref'],
            'predecessor_refs_sha256':predecessor_refs_sha,'predecessor_state_sha256':n.PREDECESSOR_STATE_SHA,
            'prepared_ref':p['decision']['prepared_ref'],'methods_sha256':METHODS_SHA})
        require(len(projection)<=251904 and len(public)<=8192 and len(provenance)<=2048)
        payloads={'inspection_projection.local.json':projection,'inspection_diagnostics.json':public,
                  'inspection_provenance.local.json':provenance}
        payload_hashes={name:sha(body) for name,body in payloads.items()}
        for name,obj in [('manifest.json',{'source_ids':list(SOURCE_ORDER),'source_hashes':[adapter.SOURCES[s]['sha256'] for s in SOURCE_ORDER]}),
            ('environment.json',{'backend_id':'CLERK_PYPDF_6_10_0_TEXT_DIAGNOSTIC_V1',
                'python':'3.12.14','pypdf':'6.10.0','crypto_provider':['cryptography','50.0.2'],
                'runtime_manifest_hashes':[m['runtime_manifest_sha256'] for m in receipts],'peak_rss_bytes_sampled':peak}),
            ('summary.json',{'status':'PAYLOADS_CLOSED_AWAITING_SEAL','source_pages':[81,38],'source_counts_or_features_adopted':False}),
            ('inspection_payload_hashes.json',{'hashes':payload_hashes}),
            ('inspection_commit.json',{'context_sha256':context,'payload_hashes_sha256':digest(payload_hashes)})]:
            payloads[name]=canonical({'label':'SOURCE_FORMAT_ONLY',**obj})
        writer=n.NativeTerminal(store,reg,journal,context,window.check)
        result=writer.finalize(payloads,{
            'registration_sha256':digest(reg.binding()),'static_spec_sha256':digest(spec),
            'genesis_sha256':prepared['genesis_ref']['sha256'],'execution_decision_sha256':digest(p['decision']),
            'issued_envelope_sha256':digest(p['issued'])},
            prewritten={'inspection_projection.local.json':projection_ref})
        window.check()
        store.crash('caller.before')
        caller={'kind':'CLERK_SOURCE_CALLER_OBSERVATION_V2_1','context_sha256':context,
                'seal_sha256':result['seal_ref']['sha256'],'writer_ack_sha256':result['writer_ack_ref']['sha256'],
                'terminal_anchor_sha256':result['completed_anchor_ref']['sha256'],
                'writer_return_observed':True,'returned_normally':True,'error_type':None,
                'outer_delivery_observed':False}
        caller_ref=store.create('caller_observation',canonical(caller))
        window.check()
        result['status']='WRITER_COMMITTED_CALLER_OBSERVED'
        result['caller_observation_ref']=caller_ref
        if not 0<=(time.monotonic()-started)*1000<=75000:
            raise SourceResourceStop('SOURCE_RESOURCE_LIMIT')
        usage=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu_ms=int((usage.ru_utime+usage.ru_stime+children.ru_utime+children.ru_stime-start_cpu)*1000)+1
        if not 0<=cpu_ms<=50000:
            raise SourceResourceStop('SOURCE_RESOURCE_LIMIT')
        result['cpu_ms_through_final_anchor']=cpu_ms
        return result
    except BaseException as exc:
        if isinstance(exc,FileExistsError) and not claimed:
            return {'status':'FAILED_OR_UNKNOWN_NO_RETRY','phase':'EXEC','replay_refused':True,
                    'source_format_accepted':False,'model_calls':0,'cost_usd':0}
        if isinstance(exc,SourceResourceStop) and writer is not None and writer.completed_result is not None:
            try:writer.invalidate_committed()
            except BaseException:pass
        if projection_stream is not None and not projection_stream.closed:
            try:projection_stream.finish()
            except BaseException:pass
        return fail_record(store,journal,'EXEC')


def configure_cli_limits(phase):
    """Fail before input; no attempt to raise an inherited hard limit."""
    try:
        require(phase in {'BOOT','EXEC'})
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        require(resource.getrlimit(resource.RLIMIT_CORE)==(0,0))
        desired=(9,10) if phase=='BOOT' else (7,8)
        _,hard=resource.getrlimit(resource.RLIMIT_CPU)
        require(hard==resource.RLIM_INFINITY or hard>=desired[1])
        require(signal.getsignal(signal.SIGXCPU)==signal.SIG_DFL)
        require(signal.SIGXCPU not in signal.pthread_sigmask(signal.SIG_BLOCK,[]))
        resource.setrlimit(resource.RLIMIT_CPU,desired)
        require(resource.getrlimit(resource.RLIMIT_CPU)==desired)
    except Exception:
        raise worker.ResourceSetupStop('RESOURCE_LIMIT_SETUP') from None


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1] in {'--boot','--exec'}:
        root=Path(sys.argv[2]).absolute()
        import signal
        signal.setitimer(signal.ITIMER_REAL,45 if sys.argv[1]=='--boot' else 75)
        try:configure_cli_limits('BOOT' if sys.argv[1]=='--boot' else 'EXEC')
        except worker.ResourceSetupStop:
            print(canonical({'status':'RESOURCE_LIMIT_SETUP_STOP_NO_INPUT','phase':'BOOT' if sys.argv[1]=='--boot' else 'EXEC',
                'source_format_accepted':False,'model_calls':0,'cost_usd':0}).decode());raise SystemExit(2)
        raw=sys.stdin.buffer.read(MAX_AUTHORITY+1)
        result=(run_boot if sys.argv[1]=='--boot' else run_exec)(root,raw,sys.argv[3])
        signal.setitimer(signal.ITIMER_REAL,0)
        print(canonical(result).decode())
    else:raise SystemExit('Exact externally reviewed BOOT or EXEC packet required; no default source job.')
