"""Fixed two-source campaign's isolated memory worker. Never opens a source path.

No PDF import on module import. The controller must supply a hash-bound memory
request after durable EXEC reservation. No factory, registry or paid API exists.
"""
import base64
import importlib.util
import os
from pathlib import Path
import resource
import signal
import sys
import time

if __name__=='__main__' and len(sys.argv)==4 and sys.argv[1]=='--source-format-worker':
    sys.path.insert(0,str(Path(sys.argv[2]).absolute()/'src'))

from civiclab.e01 import clerk2020_directories_qualification_v1 as q
from civiclab.e01 import clerk2020_source_format_adapter_v1 as adapter
from civiclab.e01.clerk2020_m2_v1_1_contracts import canonical,decode,digest,exact,hex64,require,sha

ENTRY='src/civiclab/e01/clerk2020_source_worker_v2.py'
OVERLAY=('src/civiclab/e01/clerk2020_native_campaign_v2.py',
         'src/civiclab/e01/clerk2020_source_format_adapter_v1.py',ENTRY,
         'src/civiclab/e01/clerk2020_source_job_v2.py')
CODE_PATHS=q.CODE_PATHS+OVERLAY
INPUT_CAPS={'clerk2020_statistics':950272,'clerk2026_nominees':491520}
INTEGRITY_CAP=133169152
OUTPUT_CAP=262144
CATALOG_CAP=131072


def source_path(path,root):
    if path.is_relative_to(root):
        relative=str(path.relative_to(root))
        if relative in OVERLAY:return True
        if '/__pycache__/' in relative and relative.endswith('.pyc'):
            try:return str(Path(importlib.util.source_from_cache(str(path))).relative_to(root)) in OVERLAY
            except (ValueError,NotImplementedError):return False
    return False


def origin_allowed(path,root,base):
    if path.is_relative_to(root/'data/raw') or path.name=='.env':return False
    return q._origin_allowed(path,root,base) or source_path(path,root)


class SourceWarmup(q.WarmupGuard):
    def __init__(self,root):
        super().__init__(root)
        self.project_modules=frozenset(self.project_modules)|frozenset(
            p[4:-3].replace('/','.') for p in OVERLAY)

    def checked_path(self,value,event,directory=False):
        if type(value) is str and source_path(Path(os.path.abspath(value)),self.root):
            path=Path(os.path.abspath(value))
            if '..' in Path(value).parts:self.deny('ORIGIN_NOT_DECLARED',event)
            try:q.frozen._no_alias(path)
            except (q.Refused,OSError):self.deny('ALIASED_OR_UNAVAILABLE_ORIGIN',event)
            return path
        return super().checked_path(value,event,directory)

    def admit_hash(self,paths):
        require(self.phase=='HASH' and self.hash_candidates is None and type(paths) is set
                and 0<len(paths)<=1024)
        admitted={}
        for path in paths:
            require(origin_allowed(path,self.root,self.base));q.frozen._no_alias(path)
            require(path.is_file());identity=q.frozen._identity(path.stat())
            if path in self.read_files:require(self.read_files[path]==identity)
            admitted[path]=identity
        require(set(self.read_files)<=set(admitted));self.hash_candidates=admitted


def parse_request(raw,expected):
    require(type(raw) is bytes and len(raw)<=950272 and hex64(expected) and sha(raw)==expected)
    p=decode(raw,950272)
    exact(p,{'kind','source_id','source_chunks_b64','runtime_catalog','code_refs',
             'registration_sha256','execution_decision_sha256','reservation_sha256','context_sha256'})
    require(p['kind']=='CLERK_SOURCE_MEMORY_REQUEST_V2_1' and type(p['source_id']) is str and p['source_id'] in INPUT_CAPS
            and len(raw)<=INPUT_CAPS[p['source_id']])
    for key in ['registration_sha256','execution_decision_sha256','reservation_sha256','context_sha256']:
        require(hex64(p[key]))
    chunks=p['source_chunks_b64'];require(type(chunks) is list and 1<=len(chunks)<=13)
    snapshot=bytearray()
    for chunk in chunks:
        require(type(chunk) is str and 0<len(chunk)<=65536)
        try:body=base64.b64decode(chunk,validate=True)
        except (ValueError,TypeError):raise q.Refused() from None
        require(base64.b64encode(body).decode()==chunk)
        snapshot.extend(body);require(len(snapshot)<=602172)
    expected_source=adapter.SOURCES[p['source_id']]
    require(len(snapshot)==expected_source['bytes'] and sha(bytes(snapshot))==expected_source['sha256'])
    exact(p['code_refs'],CODE_PATHS)
    for ref in p['code_refs'].values():
        exact(ref,{'bytes','sha256'});require(type(ref['bytes']) is int and 0<ref['bytes']<=262144 and hex64(ref['sha256']))
    catalog=p['runtime_catalog'];require(type(catalog) is list and 1<=len(catalog)<=1024
                                       and len(canonical(catalog))<=CATALOG_CAP)
    seen=set()
    for row in catalog:
        require(type(row) is list and len(row)==4 and type(row[0]) is str
                and row[0].startswith(('REPO/','PYTHON_BASE/')) and row[0] not in seen
                and all(part not in {'','.','..'} for part in row[0].split('/'))
                and not any(ord(c)<32 or c=='\\' for c in row[0])
                and not row[0].startswith(('REPO/data/','REPO/.env'))
                and type(row[1]) is int and row[1]>=0 and hex64(row[2])
                and type(row[3]) is list and len(row[3])==6
                and all(type(v) is int and 0<=v<=2**63-1 for v in row[3]) and row[3][3]==row[1])
        seen.add(row[0])
    return p,bytes(snapshot)


def runtime_capture(root,warmup,catalog):
    base=Path(sys.base_prefix).resolve();expected={row[0]:(i,row) for i,row in enumerate(catalog)}
    candidates={Path(sys.executable).resolve()}|set(warmup.read_files)
    for module_key,module in tuple(sys.modules.items()):
        for attr in ['__file__','__cached__']:
            value=getattr(module,attr,None)
            if type(value) is not str:continue
            path=Path(os.path.abspath(value))
            require(origin_allowed(path,root,base))
            if type(module_key) is str and module_key=='_cffi_backend' and attr=='__file__':
                require(path==root/q.PROFILE['native_backend']['path'])
            if type(module_key) is str and any(module_key==p[:-1] or module_key.startswith(p[:-1]+'.') for p in q.MODULE_PREFIXES):
                require(path.is_relative_to(root/q.SITE_REF/module_key.split('.')[0]))
            if path.is_file():candidates.add(path)
    require(0<len(candidates)<=1024);warmup.admit_hash(candidates)
    rows=[];indices=[];actual=reserved=0;backend=False
    for path in sorted(candidates):
        label=('PYTHON_BASE/'+str(path.relative_to(base)) if path.is_relative_to(base)
               else 'REPO/'+str(path.relative_to(root)))
        require(label in expected);index,ref=expected[label]
        require(list(q.frozen._identity(path.stat()))==ref[3])
        h,n,charge=q.frozen._stable_hash(path,INTEGRITY_CAP-warmup.read_reserved-reserved)
        require(n==ref[1] and h==ref[2]);actual+=n;reserved+=charge
        if path==root/q.PROFILE['native_backend']['path']:
            require(n==q.PROFILE['native_backend']['bytes'] and h==q.PROFILE['native_backend']['sha256']);backend=True
        rows.append([label,n,h]);indices.append(index)
    require(len(canonical(rows))<=98304 and warmup.read_reserved+reserved<=INTEGRITY_CAP)
    nonproject=lambda label:not label.startswith(('REPO/src/','REPO/tests/'))
    require({row[0] for row in rows if nonproject(row[0])}==
            {row[0] for row in catalog if nonproject(row[0])})
    require(backend is True)
    return rows,indices,actual,reserved,backend


class ResourceSetupStop(RuntimeError):
    pass


def configure_child_limits():
    """Same source-free setup used by production worker and nested CLI tests."""
    try:
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        require(resource.getrlimit(resource.RLIMIT_CORE)==(0,0))
        _,hard=resource.getrlimit(resource.RLIMIT_CPU)
        require(hard==resource.RLIM_INFINITY or hard>=8)
        require(signal.getsignal(signal.SIGXCPU)==signal.SIG_DFL)
        require(signal.SIGXCPU not in signal.pthread_sigmask(signal.SIG_BLOCK,[]))
        resource.setrlimit(resource.RLIMIT_CPU,(7,8))
        require(resource.getrlimit(resource.RLIMIT_CPU)==(7,8))
    except Exception:
        raise ResourceSetupStop('RESOURCE_LIMIT_SETUP') from None


def source_worker(root,expected):
    stage='RESOURCE_LIMIT_SETUP';telemetry=adapter.SourceTelemetry();warmup=SourceWarmup(root);progress={}
    try:
        configure_child_limits();stage='INPUT'
        raw=sys.stdin.buffer.read(950273);p,snapshot=parse_request(raw,expected)
        sys.path[:0]=[str(root/'src'),str(root/'tests'),str(root/q.SITE_REF)]
        sys.addaudithook(warmup.guard);stage='IMPORT_IDENTITY'
        import pypdf
        import PIL
        from pypdf._crypt_providers import crypt_provider
        import test_clerk2020_native_inventory_v1
        require(sys.implementation.name=='cpython' and sys.version.split()[0]=='3.12.14'
                and sys.platform=='darwin' and os.uname().machine=='arm64'
                and pypdf.__version__=='6.10.0' and PIL.__version__=='13.0.0'
                and crypt_provider==('cryptography','50.0.2'))
        stage='GENERATED_WARMUP';warmup.transition('WARMUP')
        q.generated_checks(pypdf.PdfReader,q.guarded.GeneratedTelemetry(),progress)
        require(warmup.first_refusal is None);warmup.transition('HASH');stage='RUNTIME_INTEGRITY'
        rows,indices,actual,reserved,backend=runtime_capture(root,warmup,p['runtime_catalog'])
        warmup.transition('STRICT');sys.addaudithook(telemetry.guard);stage='ACTUAL_SOURCE_FORMAT'
        output=adapter.inspect_source(snapshot,p['source_id'],pypdf.PdfReader,telemetry=telemetry)
        require(warmup.first_refusal is None and telemetry.first_guard is None)
        diagnostics=decode(output['public_diagnostics'],8192)
        require(diagnostics['source_id']==p['source_id'] and diagnostics['page_count']==adapter.SOURCES[p['source_id']]['pages'])
        cpu=resource.getrusage(resource.RUSAGE_SELF)
        metadata={'kind':'CLERK_SOURCE_WORKER_RECEIPT_V2_1','status':'SOURCE_FORMAT_ONLY_COMPLETE',
            'source_id':p['source_id'],'context_sha256':p['context_sha256'],
            'registration_sha256':p['registration_sha256'],'execution_decision_sha256':p['execution_decision_sha256'],
            'reservation_sha256':p['reservation_sha256'],'source_sha256':sha(snapshot),'source_bytes':len(snapshot),
            'runtime_indices':indices,'runtime_manifest_sha256':digest(rows),
            'runtime_hash_bytes_observed':actual,'runtime_hash_bytes_reserved':reserved,
            'warmup':warmup.summary(progress),'warmup_pages':119,'warmup_readers':4,
            'source_readers':1,'source_pages':diagnostics['page_count'],'native_backend_hash_matched':backend,
            'strict_first_refusal':None,'cpu_ms_through_private_projection':int((cpu.ru_utime+cpu.ru_stime)*1000)+1,
            'public_diagnostics':diagnostics,'private_projection_sha256':sha(output['private_projection']),
            'private_projection_bytes':len(output['private_projection']),'source_counts_or_features_adopted':False,
            'model_calls':0,'cost_usd':0}
        require(len(canonical(metadata))<=8192)
        private=output['private_projection']
        chunks=[base64.b64encode(private[i:i+49152]).decode() for i in range(0,len(private),49152)]
        result={'metadata':metadata,'private_projection_chunks_b64':chunks}
    except BaseException:
        result={'kind':'CLERK_SOURCE_WORKER_STOP_V2_1','stage':stage,'source_format_accepted':False,
                'warmup_progress':progress,'warmup_refusal':warmup.first_refusal,
                'source_first_refusal':telemetry.first_guard,'source_exception':telemetry.first_exception,
                'model_calls':0,'cost_usd':0}
    encoded=canonical(result);require(len(encoded)<=OUTPUT_CAP)
    sys.stdout.buffer.write(encoded);sys.stdout.buffer.flush()


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--source-format-worker':
        source_worker(Path(sys.argv[2]).absolute(),sys.argv[3])
    else:raise SystemExit('Memory worker only; controller must issue a finite reviewed source job.')
