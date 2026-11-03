"""Registry-driven N2a collector. Production source work requires finite release.

Trusted local preserved history; cooperative clocks/RSS, not a hostile-host or
absolute OS containment boundary. No person rows are imported by this module.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import csv
import fcntl
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import stat
import struct
import time
import zipfile
import zlib

from ..common import atomic_json,canonical_hash
from .national_budget import Blocked
from .full_adult_types_v1_2 import strict_json
from .f_actual_admission_v1_1 import detached
from .f_wy_bootstrap_v1_1 import _open_no_follow,_identity

ROOT=Path(__file__).resolve().parents[3]
CONFIG='configs/e02_n2a_dc_collector_v1.json'
_TEST=object()
_CONTEXT=object()
_TEST_ROOTS=set()


def digest(blob):return hashlib.sha256(blob).hexdigest()


def tick():
    # Continuous monotonic+wall mapping detects rollback/reboot discontinuity.
    return {'wall':time.time(),'mono':time.monotonic()}


def delta(first,last):
    if set(first)!={'wall','mono'} or set(last)!=set(first):raise Blocked('clock shape')
    for x in (first,last):
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in x.values()):raise Blocked('clock value')
    dw=last['wall']-first['wall'];dm=last['mono']-first['mono']
    if min(dw,dm)<0 or abs(dw-dm)>2:raise Blocked('clock rollback/discontinuity')
    return max(dw,dm)


def rss_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if platform.system()=='Darwin' else value*1024)


def _lexical(root,relative,prefix):
    p=Path(relative)
    if type(relative) is not str or p.is_absolute() or '..' in p.parts or not relative.startswith(prefix):raise Blocked('fixed owned path required')
    return root/p


def _metadata(root,name,expected=None):
    p=Path(name)
    if type(name) is not str or p.is_absolute() or '..' in p.parts or p.parts[:1] not in (('configs',),('reports',),('src',),('tests',),('docs',)):raise Blocked('metadata domain')
    cursor=root
    for part in p.parts:
        cursor=cursor/part
        if cursor.is_symlink():raise Blocked('metadata symlink')
    with cursor.open('rb') as stream:blob=stream.read(8*1024**2+1)
    if len(blob)>8*1024**2 or expected is not None and digest(blob)!=expected:raise Blocked('metadata bound/hash')
    return blob


def _record(root,ref):
    if type(ref) is not dict or set(ref)!={'path','sha256'}:raise Blocked('closed reference')
    return strict_json(_metadata(root,ref['path'],ref['sha256']))


@dataclass(frozen=True)
class Realm:
    root:Path
    tag:str
    token:object=None


def make_test_realm(root):
    root=Path(root).resolve()
    if root==ROOT or root.is_relative_to(ROOT/'data/raw'):raise Blocked('new isolated realm required')
    root.mkdir(exist_ok=False);(root/'TEST_ONLY_N2A').write_text(str(root)+'\n');_TEST_ROOTS.add(root)
    return Realm(root,'TEST_ONLY',_TEST)


def _realm(r):
    if type(r) is not Realm or type(r.root) is not type(ROOT):raise Blocked('realm type')
    if r.tag=='PRODUCTION' and r.root==ROOT and r.token is None:return r
    if r.tag=='TEST_ONLY' and r.token is _TEST and r.root in _TEST_ROOTS and (r.root/'TEST_ONLY_N2A').read_text()==str(r.root)+'\n':return r
    raise Blocked('realm binding')


def _load(r,config):
    config=detached(config)
    if type(config) is not dict or type(config.get('execution_authority')) is not int or config['execution_authority']!=1 or config.get('realm')!=r.tag:raise Blocked('finite source authority absent/wrong realm')
    refs=config.get('live_refs')
    if type(refs) is not dict or set(refs)!={'code_review','release'} or any(type(v) is not dict for v in refs.values()):raise Blocked('code/release absent')
    r=_realm(r);base=strict_json(_metadata(r.root,CONFIG));excluded={'execution_authority','live_refs','active_state'}
    policy={k:v for k,v in config.items() if k not in excluded}
    if base['execution_authority']!=0 or any(v is not None for v in base['live_refs'].values()) or policy!={k:v for k,v in base.items() if k not in excluded}:raise Blocked('frozen collector policy changed')
    for p,h in config['files'].items():_metadata(r.root,p,h)
    native=strict_json(_metadata(r.root,config['native_reference']['path'],config['native_reference']['sha256']))
    if config['native_limits']!=native['limits'] or config['required_fields']!=native['required_fields'] or len(config['required_fields'])!=91:raise Blocked('native policy/schema changed')
    u=config['unit_limits'];n=config['native_limits']
    if u['GET_attempts']!=1 or u['workers']!=1 or any(u[k]!=0 for k in ('HEADs','redirects','retries','range_resumes','person_rows','analysis_operations')) or u['application_response_bytes']>n['archive_body_bytes'] or u['raw_retained_bytes']>n['retained_bytes'] or u['request_seconds']>n['request_seconds'] or u['metadata_processing_seconds']>n['state_processing_seconds'] or u['unit_elapsed_seconds']>n['batch_elapsed_seconds'] or u['sampled_rss_stop_bytes']>n['rss_stop_bytes'] or u['header_bytes']>n['line_bytes'] or u['companion_declared_bytes']>n['companion_bytes'] or u['combined_declared_bytes']>n['state_uncompressed_bytes']:raise Blocked('source subcaps exceed native policy')
    registry=strict_json(_metadata(r.root,config['registry_reference']['path'],config['registry_reference']['sha256']))['complete_public_metadata']['states']
    records={x['state_fips']:x for x in registry}
    active=config['active_state']
    if type(active) is not str or active not in records or active=='56':raise Blocked('new registered non-WY state required')
    source=records[active]
    expected=f"https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year/csv_p{source['abbreviation']}.zip"
    if source['url']!=expected or source['filename']!=expected.rsplit('/',1)[1]:raise Blocked('registry URL/filename mismatch')
    review=_record(r.root,refs['code_review']);release=_record(r.root,refs['release'])
    P=canonical_hash(policy);D=canonical_hash({'policy_sha256':P,'active_state':active,'source':source,'realm':r.tag,'root':str(r.root)})
    if review.get('status')!='PASS_N2A_COLLECTOR_CODE_AUTHORED_FIXTURES' or review.get('auditor_role')!='independent_auditor' or review.get('realm')!=r.tag or review.get('policy_sha256')!=P or review.get('files')!=config['files'] or active not in review.get('reviewed_states',[]):raise Blocked('independent collector review mismatch')
    scope={'root':str(r.root),'state':active,'url':source['url'],'GETs':1,'HEADs':0,'redirects':0,'retries':0,'person_rows':0,'model_calls':0,'fit':False,'disclosure':False}
    if release.get('status')!='RELEASE_N2A_ONE_ORDINARY_PUBLIC_SOURCE_GET' or release.get('issuer_role')!='lead' or release.get('realm')!=r.tag or release.get('design_sha256')!=D or release.get('code_review_sha256')!=refs['code_review']['sha256'] or canonical_hash(release.get('scope'))!=canonical_hash(scope) or release.get('limits')!=config['unit_limits'] or not release.get('owner_research_authorization_reference'):raise Blocked('particular bounded public source release absent')
    if type(release.get('not_before')) not in (int,float) or type(release.get('expires')) not in (int,float) or not release['not_before']<=time.time()<release['expires']:raise Blocked('release expired/not active')
    for p,h in config['history_references'].items():_metadata(r.root,p,h)
    return {'config':config,'source':source,'policy':policy,'policy_sha256':P,'design_sha256':D,'release':release,'realm':r.tag,'registry':registry}


@dataclass(frozen=True)
class Context:
    realm:Realm
    config_json:str
    binding_json:str
    token:object
    @property
    def binding(self):return strict_json(self.binding_json)
    @property
    def config(self):return self.binding['config']
    @property
    def source(self):return self.binding['source']
    @property
    def registry_root(self):return _lexical(self.realm.root,self.config['registry_directory'],'data/processed/')
    @property
    def core_root(self):return _lexical(self.realm.root,self.config['core_directory'],'data/processed/')
    @property
    def raw_root(self):return _lexical(self.realm.root,self.config['raw_directory'],'data/raw/')
    @property
    def state(self):return self.config['active_state']
    @property
    def part(self):return self.raw_root/self.state/(self.source['filename']+'.part')
    @property
    def archive(self):return self.raw_root/self.state/self.source['filename']


def _admit(r,config):
    try:b=_load(r,config)
    except (OSError,TypeError,ValueError,KeyError):raise Blocked('collector metadata incomplete') from None
    c=Context(r,json.dumps(detached(config),sort_keys=True),json.dumps(b,sort_keys=True),_CONTEXT)
    # Bound lexical output domains only; do not inspect another raw cache.
    c.registry_root;c.core_root;c.raw_root
    return c


def admit(config=None):return _admit(Realm(ROOT,'PRODUCTION'),config)
def admit_fixture(realm,config=None):
    if type(realm) is not Realm or realm.tag!='TEST_ONLY' or realm.token is not _TEST:raise Blocked('test realm only')
    return _admit(realm,config)


def require(c):
    if type(c) is not Context or c.token is not _CONTEXT or type(c.config_json) is not str or type(c.binding_json) is not str:raise Blocked('minted collector context required')
    try:b=_load(c.realm,strict_json(c.config_json))
    except (OSError,TypeError,ValueError,KeyError):raise Blocked('collector authority missing/changed') from None
    if b!=c.binding:raise Blocked('collector context changed')
    return c


def _mkdir(path,root):
    cursor=root
    for part in path.relative_to(root).parts:
        cursor=cursor/part
        if cursor.is_symlink():raise Blocked('owned ancestor symlink')
        cursor.mkdir(exist_ok=True)


class Registry:
    def __init__(self,context,*,create=False):
        self.c=require(context);self.path=self.c.registry_root
        if create:
            # Existing raw/core remnants prohibit rebootstrap of a lost registry.
            if self.path.exists() or self.c.raw_root.exists() or self.c.core_root.exists():raise Blocked('retained source history; no new-root reset')
            _mkdir(self.path,self.c.realm.root);_mkdir(self.c.raw_root,self.c.realm.root);_mkdir(self.c.core_root,self.c.realm.root)
            with self.lock():
                g={'schema':'N2A_ATTEMPT_REGISTRY_V1','policy_sha256':self.c.binding['policy_sha256'],'realm':self.c.realm.tag,'root':str(self.c.realm.root),'created':tick(),'attempts':{},'generation':0,'last':None,'history':self.c.config['history_baseline']}
                g['last']=g['created']
                self.storage(extra_core=2*len(json.dumps(g).encode())+2*len(json.dumps(self.c.binding['policy']).encode())+8192,initial=True)
                atomic_json(self.path/'genesis.json',g);(self.path/'ORIGINAL').write_text(canonical_hash(g)+'\n');atomic_json(self.path/'state.json',g)
                atomic_json(self.path/'policy-binding.local.json',self.c.binding['policy']);self.storage(initial=True)
        if not self.path.is_dir():raise Blocked('original registry required')
        self.snapshot()

    @contextmanager
    def lock(self):
        if self.path!=self.c.registry_root or self.path.is_symlink():raise Blocked('registry root changed')
        with (self.path/'.lock').open('a') as stream:
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Blocked('single collector owner') from None
            try:yield
            finally:fcntl.flock(stream,fcntl.LOCK_UN)

    def storage(self,*,extra_core=0,extra_raw=0,extra_scratch=0,initial=False):
        require(self.c)
        if self.path!=self.c.registry_root or any(type(x) is not int or x<0 for x in (extra_core,extra_raw,extra_scratch)):raise Blocked('storage context/projection')
        cap=self.c.config['unit_limits'];native=self.c.config['native_limits'];totals={'raw':0,'core':0,'scratch':0}
        for root,default in ((self.c.registry_root,'core'),(self.c.core_root,'core'),(self.c.raw_root,'raw')):
            if root.is_symlink():raise Blocked('owned root symlink')
            if not root.exists():continue
            for p in root.rglob('*'):
                if p.is_symlink():raise Blocked('owned file symlink')
                if not p.is_file():continue
                k='scratch' if p.relative_to(root).parts[:1]==('scratch',) else default
                totals[k]+=p.stat().st_size
            if shutil.disk_usage(root).free<max(native['free_disk_bytes'],native['minimum_initial_free_disk_bytes'] if initial else 0)+extra_core+extra_raw+extra_scratch:raise Blocked('free space/atomic headroom')
        totals['core']+=extra_core;totals['raw']+=extra_raw;totals['scratch']+=extra_scratch
        if totals['raw']>cap['raw_retained_bytes'] or totals['core']>cap['core_metadata_bytes'] or totals['scratch']>cap['scratch_bytes'] or sum(totals.values())>cap['all_stage_retained_bytes']:raise Blocked('owned N2a storage cap')
        if totals['core']>native['log_bytes'] or totals['raw']+self.c.config['history_baseline']['prior_WY_retained_bytes']>native['retained_bytes']:raise Blocked('native storage cumulative cap')
        return totals

    def _transition(self,old,event,payload):
        s=detached(old);delta(s['last'],payload['at']);s['last']=payload['at'];s['generation']+=1
        fields={'RESERVE':{'state','at','url','design','pid'},'DISPATCH':{'state','at'},'PROGRESS':{'state','at','received','written'},'COMPLETE':{'state','at','receipt_sha256'},'FAIL':{'state','at','error_type'},'UNKNOWN':{'state','at','error_type'}}
        if event not in fields or set(payload)!=fields[event]:raise Blocked('closed event payload')
        key=payload['state'];attempt=s['attempts'].get(key)
        if event=='RESERVE':
            registered={x['state_fips']:x for x in self.c.binding['registry']}
            if key not in registered or key=='56':raise Blocked('registered source only')
            if key in s['attempts'] or any(x['status']=='PENDING' for x in s['attempts'].values()):raise Blocked('duplicate/pending URL; no retry')
            design=canonical_hash({'policy_sha256':self.c.binding['policy_sha256'],'active_state':key,'source':registered[key],'realm':self.c.realm.tag,'root':str(self.c.realm.root)})
            if payload.get('url')!=registered[key]['url'] or payload.get('design')!=design:raise Blocked('attempt exact source design')
            lim=self.c.config['unit_limits'];started=s['created'] if not s['attempts'] else payload['at']
            if delta(s['created'],payload['at'])>=self.c.config['native_limits']['batch_elapsed_seconds'] or delta(started,payload['at'])>=lim['unit_elapsed_seconds']:raise Blocked('original registry/unit clock expired')
            s['attempts'][key]={'url':payload['url'],'design':payload['design'],'started':started,'status':'PENDING','phase':'RESERVED','received':0,'written':0,'owner_pid':payload['pid'],'reservation':{'requests':1,'body_bytes':lim['application_response_bytes'],'network_seconds':lim['request_seconds'],'processing_seconds':lim['metadata_processing_seconds']},'result':None}
        else:
            if attempt is None or attempt['status']!='PENDING' and not (event=='FAIL' and attempt['status']=='COMPLETED'):raise Blocked('no original pending attempt')
            if event=='DISPATCH':
                if attempt['phase']!='RESERVED':raise Blocked('dispatch exactly once')
                attempt['phase']='DISPATCHED'
            elif event=='PROGRESS':
                if attempt['phase'] not in ('DISPATCHED','RECEIVING'):raise Blocked('response not dispatched')
                received=payload['received'];written=payload['written']
                if type(received) is not int or type(written) is not int or not attempt['received']<=received<=self.c.config['unit_limits']['application_response_bytes'] or not attempt['written']<=written<=received:raise Blocked('monotone metered bytes')
                attempt.update(phase='RECEIVING',received=received,written=written)
            elif event=='COMPLETE':
                if delta(attempt['started'],payload['at'])>=self.c.config['unit_limits']['unit_elapsed_seconds']:raise Blocked('original acquisition deadline')
                receipt=strict_json((self.c.core_root/key/'receipt.local.json').read_text())
                if payload['receipt_sha256']!=digest((self.c.core_root/key/'receipt.local.json').read_bytes()) or receipt.get('state')!=key or receipt.get('url')!=attempt['url'] or receipt.get('received_bytes')!=attempt['received'] or receipt.get('person_rows_read')!=0 or receipt.get('import_admitted') is not False or receipt.get('status')!='ACQUIRED_METADATA_VALIDATED_NOT_PERSON_IMPORTED':raise Blocked('immutable receipt binding')
                if delta(receipt['network_started'],receipt['network_finished'])>self.c.config['unit_limits']['request_seconds'] or delta(receipt['metadata']['processing_started'],payload['at'])>self.c.config['unit_limits']['metadata_processing_seconds']:raise Blocked('recorded network/metadata phase cap')
                attempt.update(status='COMPLETED',phase='CLOSED',result={'receipt_sha256':payload['receipt_sha256']})
            elif event in ('FAIL','UNKNOWN'):
                attempt.update(status='FAILED' if event=='FAIL' else 'UNKNOWN',phase='CLOSED',result={'error_type':payload.get('error_type','UNKNOWN'),'shutdown':'SHUTDOWN_UNKNOWN_NO_RESOURCE_STOP_CLAIM'})
            else:raise Blocked('closed registry event')
        n=self.c.config['native_limits'];history=s['history'];reserved_body=sum(x['reservation']['body_bytes'] for x in s['attempts'].values())
        network_reserved=sum(x['reservation']['network_seconds'] for x in s['attempts'].values());processing_reserved=sum(x['reservation']['processing_seconds'] for x in s['attempts'].values())
        if network_reserved>n['network_seconds'] or processing_reserved>n['processing_seconds']:raise Blocked('native cumulative time reservations')
        if len(s['attempts'])>n['requests'] or reserved_body+history['prior_body_reserved_upper_bound']+history['prior_metadata_received_bytes']>n['body_bytes'] or reserved_body+history['prior_WY_retained_bytes']>n['unique_source_bytes']:raise Blocked('cumulative campaign cap')
        return s

    def _read(self):
        require(self.c)
        for name in ('genesis.json','ORIGINAL','state.json','events.jsonl','policy-binding.local.json'):
            if (self.path/name).is_symlink():raise Blocked('registry symlink')
        try:
            g=strict_json((self.path/'genesis.json').read_text())
            if g['schema']!='N2A_ATTEMPT_REGISTRY_V1' or g['policy_sha256']!=self.c.binding['policy_sha256'] or g['root']!=str(self.c.realm.root) or g['realm']!=self.c.realm.tag or g['history']!=self.c.config['history_baseline'] or g['attempts']!={} or g['generation']!=0 or g['last']!=g['created'] or (self.path/'ORIGINAL').read_text()!=canonical_hash(g)+'\n' or strict_json((self.path/'policy-binding.local.json').read_text())!=self.c.binding['policy']:raise Blocked('immutable original registry')
            s=g;previous=None;log=self.path/'events.jsonl'
            for i,line in enumerate(log.read_text().splitlines() if log.exists() else [],1):
                row=strict_json(line)
                if set(row)!={'seq','prev','before','event','payload','after','hash'} or row['seq']!=i or row['prev']!=previous or row['before']!=canonical_hash(s) or row['hash']!=canonical_hash({k:v for k,v in row.items() if k!='hash'}):raise Blocked('registry chain')
                s=self._transition(s,row['event'],row['payload'])
                if row['after']!=canonical_hash(s):raise Blocked('semantic registry replay')
                previous=row['hash']
            if strict_json((self.path/'state.json').read_text())!=s:raise Blocked('torn registry/state; no reset')
            delta(s['last'],tick());return s,previous
        except (OSError,TypeError,ValueError,KeyError):raise Blocked('unprovable original registry') from None

    def snapshot(self):
        with self.lock():return detached(self._read()[0])

    def advance(self,event,**payload):
        if 'state' in payload or 'at' in payload:raise Blocked('caller event identity/clock override')
        old,previous=self._read();payload={'state':self.c.state,**detached(payload),'at':tick()};new=self._transition(old,event,payload)
        row={'seq':new['generation'],'prev':previous,'before':canonical_hash(old),'event':event,'payload':payload,'after':canonical_hash(new)};row['hash']=canonical_hash(row)
        blob=(json.dumps(row,sort_keys=True)+'\n').encode();self.storage(extra_core=len(blob)+2*len(json.dumps(new).encode())+4096)
        with (self.path/'events.jsonl').open('ab') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        atomic_json(self.path/'state.json',new);return new

    def unknown(self):
        with self.lock():return self.advance('UNKNOWN',error_type='InterruptedOwnerOrUnprovableShutdown')


def _headers(response):
    keep=('date','last-modified','content-length','content-type','content-encoding','etag')
    result={}
    if type(response.status) is not int or type(response.url) is not str:raise Blocked('response metadata type')
    for name in keep:
        value=response.headers.get(name)
        if value is not None:
            if type(value) is not str or len(value.encode())>1024:raise Blocked('bounded response headers')
            result[name]=value
    return result


def _guard(reg,started,phase_started=None,phase_seconds=None):
    c=reg.c;lim=c.config['unit_limits'];now=tick()
    if delta(started,now)>=lim['unit_elapsed_seconds']:raise Blocked('original unit deadline')
    if phase_started is not None and delta(phase_started,now)>phase_seconds:raise Blocked('phase deadline exceeded')
    if rss_bytes()>lim['sampled_rss_stop_bytes']:raise Blocked('sampled RSS stop')
    if (reg.path/('CANCEL_'+c.state)).exists():raise Blocked('cooperative cancellation')
    reg.storage()
    return now


def request_cancel(context):
    c=require(context)
    # Cancellation must not wait for the acquisition's exclusive owner lock.
    # Validate immutable original header, then use the same bounded storage view.
    path=c.registry_root/('CANCEL_'+c.state)
    for p in (c.registry_root,c.registry_root/'genesis.json',c.registry_root/'ORIGINAL'):
        if p.is_symlink():raise Blocked('cancel original path symlink')
    g=strict_json((c.registry_root/'genesis.json').read_text())
    if g['policy_sha256']!=c.binding['policy_sha256'] or g['root']!=str(c.realm.root) or (c.registry_root/'ORIGINAL').read_text()!=canonical_hash(g)+'\n':raise Blocked('cancel original registry mismatch')
    view=object.__new__(Registry);view.c=c;view.path=c.registry_root
    view.storage(extra_core=4096)
    if not path.exists():
        with path.open('x') as f:f.write('COOPERATIVE_CANCEL\n');f.flush();os.fsync(f.fileno())


def _exclusive_part(c):
    # All initial ancestor descriptors are observed; reopen whole lexical chain
    # later rather than stat relative to a retained renamed parent directory.
    _mkdir(c.part.parent,c.realm.root)
    directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY);chain=[];current=Path('/')
    st=os.fstat(directory);chain.append({'path':'/','device':st.st_dev,'inode':st.st_ino})
    try:
        for part in c.part.parts[1:-1]:
            following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=following;current=current/part;st=os.fstat(directory)
            chain.append({'path':str(current),'device':st.st_dev,'inode':st.st_ino})
        fd=os.open(c.part.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
        return os.fdopen(fd,'wb'),chain
    finally:os.close(directory)


def _header_line(stream,info,archive_size,limit,guard):
    stream.seek(info.header_offset);header=stream.read(30)
    if len(header)!=30 or header[:4]!=b'PK\x03\x04':raise Blocked('local CSV header')
    nname,nextra=struct.unpack_from('<HH',header,26)
    if nname+nextra>archive_size or stream.read(nname)!=info.filename.encode('ascii'):raise Blocked('literal local CSV member')
    stream.seek(nextra,1)
    if stream.tell()+info.compress_size>archive_size:raise Blocked('CSV member offset')
    result=bytearray();remaining=info.compress_size;pending=b'';decoder=zlib.decompressobj(-15) if info.compress_type==zipfile.ZIP_DEFLATED else None
    while len(result)<limit:
        if len(result)%256==0:guard()
        if decoder is None:
            piece=stream.read(1) if remaining else b'';remaining-=len(piece)
        else:
            if not pending:
                if remaining==0:break
                pending=stream.read(min(65536,remaining));remaining-=len(pending)
                if not pending:break
            piece=decoder.decompress(pending,1);pending=decoder.unconsumed_tail
            if not piece and decoder.eof:break
        if not piece:break
        result.extend(piece)
        if piece==b'\n':return bytes(result)
    raise Blocked('bounded first header line missing/too long')


def _inspect(reg,expected_identity,expected_chain,stream_hash,started):
    c=reg.c;lim=c.config['unit_limits'];phase=tick();guard=lambda:_guard(reg,started,phase,lim['metadata_processing_seconds'])
    stream,directory,chain=_open_no_follow(c.part)
    try:
        with stream:
            identity=_identity(os.fstat(stream.fileno()))
            if identity!=expected_identity or chain!=expected_chain:raise Blocked('download lexical identity changed')
            if identity['bytes']>lim['application_response_bytes']:raise Blocked('owned archive cap')
            h=hashlib.sha256();n=0
            while True:
                guard();block=stream.read(min(65536,lim['application_response_bytes']-n))
                if not block:break
                n+=len(block);h.update(block)
                if n==lim['application_response_bytes']:break
            if n!=identity['bytes'] or h.hexdigest()!=stream_hash:raise Blocked('downloaded bytes differ from streamed hash')
            stream.seek(0)
            if stream.read(4)!=b'PK\x03\x04':raise Blocked('ordinary ZIP signature required')
            stream.seek(0)
            with zipfile.ZipFile(stream) as z:
                infos=z.infolist();person='psam_p'+c.state+'.csv';companion='ACS2020_2024_PUMS_README.pdf'
                if len(infos)!=2 or {x.filename for x in infos}!={person,companion} or len({x.filename.casefold() for x in infos})!=2:raise Blocked('two literal source members required')
                for x in infos:
                    if '/' in x.filename or '\\' in x.filename or x.flag_bits&1 or stat.S_ISLNK(x.external_attr>>16) or x.is_dir() or x.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):raise Blocked('unsafe member metadata')
                pi=z.getinfo(person);ci=z.getinfo(companion)
                if pi.file_size>lim['person_declared_bytes'] or ci.file_size>lim['companion_declared_bytes'] or pi.file_size+ci.file_size>lim['combined_declared_bytes']:raise Blocked('declared expansion cap')
                header=_header_line(stream,pi,identity['bytes'],lim['header_bytes'],guard)
                fields=next(csv.reader(io.StringIO(header.decode('utf-8-sig')),strict=True))
                if len(fields)!=285 or len(set(fields))!=285 or not set(c.config['required_fields']).issubset(fields):raise Blocked('285/91 source schema mismatch')
                # Companion only; never open the person ZipExtFile or testzip().
                with z.open(companion) as f:
                    comp_hash=hashlib.sha256();count=0
                    while True:
                        guard();block=f.read(min(65536,ci.file_size-count+1))
                        if not block:break
                        count+=len(block)
                        if count>ci.file_size or count>lim['companion_declared_bytes']:raise Blocked('companion delivered bound')
                        comp_hash.update(block)
                if count!=ci.file_size:raise Blocked('companion truncated')
                members=[{'name':x.filename,'bytes':x.file_size,'compressed_bytes':x.compress_size,'crc32':x.CRC,'compression':x.compress_type} for x in infos]
            after=_identity(os.fstat(stream.fileno()))
            current,dfd,current_chain=_open_no_follow(c.part)
            try:
                with current:
                    if current_chain!=chain or identity!=after or _identity(os.fstat(current.fileno()))!=identity:raise Blocked('post-read full lexical identity changed')
            finally:os.close(dfd)
    finally:os.close(directory)
    guard()
    return {'processing_started':phase,'archive_sha256':stream_hash,'archive_bytes':identity['bytes'],'identity_before_promotion':identity,
            'directory_chain_identity':chain,'members':members,'header_bytes':len(header),'header_sha256':digest(header),
            'header_columns':285,'required_columns':len(c.config['required_fields']),'header_matches_WY_reference':digest(header)==c.config['reference_header_sha256'],
            'companion_sha256':comp_hash.hexdigest(),'companion_bytes':count,'expanded_bytes':len(header)+count,
            'person_rows_read':0,'full_person_crc_scan':False,'person_member_sha256':None,'actual_person_rows':None,
            'row_STATE_content_validated':False,'import_admitted':False}


def _collect(context,transport):
    c=require(context)
    # Only a single context-bound operation; no alternate worker/backend loops.
    reg=Registry(c,create=not c.registry_root.exists())
    response=None;partial_hash=hashlib.sha256();received=written=0;metadata={};start=None;reserved_here=False;http_status=None
    with reg.lock():
        try:
            reg.advance('RESERVE',url=c.source['url'],design=c.binding['design_sha256'],pid=os.getpid());reserved_here=True
            state=reg._read()[0];start=state['attempts'][c.state]['started'];lim=c.config['unit_limits'];_guard(reg,start)
            _mkdir(c.core_root/c.state,c.realm.root)
            reg.storage(extra_core=2*len(json.dumps(c.binding).encode())+8192)
            atomic_json(c.core_root/c.state/'attempt-binding.local.json',c.binding)
            reg.storage(extra_raw=lim['application_response_bytes'],extra_core=8192,initial=True)
            reg.advance('DISPATCH');network=tick()
            response=transport.open(c.source['url'],lim['socket_operation_seconds'])
            _guard(reg,start,network,lim['request_seconds']);metadata=_headers(response);http_status=response.status
            if response.status!=200 or response.url!=c.source['url']:raise Blocked('HTTP status/final URL refused')
            if metadata.get('content-encoding','identity').strip().lower() not in ('','identity'):raise Blocked('response encoding refused')
            mime=metadata.get('content-type','').split(';',1)[0].strip().lower()
            if mime not in ('','application/zip','application/octet-stream','application/x-zip-compressed'):raise Blocked('response type refused')
            declared=metadata.get('content-length');length=None
            if declared is not None:
                declared=declared.strip()
                if not declared.isascii() or not declared.isdigit():raise Blocked('invalid content length')
                length=int(declared)
                if length>lim['application_response_bytes']:raise Blocked('declared response cap')
            raw,chain=_exclusive_part(c)
            with raw:
                while True:
                    _guard(reg,start,network,lim['request_seconds'])
                    allowance=lim['application_response_bytes']-received
                    if allowance==0:
                        # No extra-byte probe beyond cap. A known HTTP length
                        # may prove complete; unknown length at cap stays blocked.
                        if length is not None and received==length:break
                        raise Blocked('EOF unproved at exact response cap')
                    block=response.read(min(65536,allowance))
                    if type(block) is not bytes or len(block)>min(65536,allowance):raise Blocked('transport delivered outside bound')
                    if not block:
                        _guard(reg,start,network,lim['request_seconds']);break
                    received+=len(block);partial_hash.update(block)
                    # Persist received lower bound BEFORE write; interruption
                    # retains full allowance even if bytes never reached disk.
                    reg.advance('PROGRESS',received=received,written=written)
                    _guard(reg,start,network,lim['request_seconds'])
                    reg.storage(extra_raw=len(block),extra_core=4096)
                    raw.write(block);raw.flush();os.fsync(raw.fileno());written+=len(block)
                    reg.advance('PROGRESS',received=received,written=written)
                if length is not None and received!=length:raise Blocked('truncated/overlong response')
                raw.flush();os.fsync(raw.fileno());identity=_identity(os.fstat(raw.fileno()))
            response.close();response=None
            network_finished=_guard(reg,start,network,lim['request_seconds'])
            if written!=received or identity['bytes']!=received:raise Blocked('metered/write length mismatch')
            checked=_inspect(reg,identity,chain,partial_hash.hexdigest(),start)
            _guard(reg,start,checked['processing_started'],lim['metadata_processing_seconds'])
            if c.archive.exists() or c.archive.is_symlink():raise Blocked('immutable final archive already exists')
            # Same-directory atomic rename, no duplicate raw source copy.
            c.part.rename(c.archive)
            final,dfd,final_chain=_open_no_follow(c.archive)
            try:
                with final:final_identity=_identity(os.fstat(final.fileno()))
                if final_chain!=chain or any(final_identity[k]!=identity[k] for k in ('device','inode','bytes','mtime_ns')):raise Blocked('promotion identity changed')
            finally:os.close(dfd)
            receipt={'schema':'N2A_SOURCE_RECEIPT_V1','realm':c.realm.tag,'status':'ACQUIRED_METADATA_VALIDATED_NOT_PERSON_IMPORTED','state':c.state,'url':c.source['url'],
                     'received_bytes':received,'written_bytes':written,'archive_relative_path':str(c.archive.relative_to(c.realm.root)),'source_identity':final_identity,
                     'network_started':network,'network_finished':network_finished,'HTTP_status':200,'HTTP_headers':metadata,'requested_at':start,'completed_at':tick(),'metadata':checked,
                     'published_person_rows_historical':c.source['published_person_rows'],'person_rows_read':0,'import_admitted':False,'GETs':1,'model_calls':0,
                     'rights':'Ordinary public Census research acquisition; raw private/ignored, no redistribution/linkage/targeting/external model transmission.',
                     'design_sha256':c.binding['design_sha256'],'code_review_sha256':c.config['live_refs']['code_review']['sha256'],'finite_release_sha256':c.config['live_refs']['release']['sha256'],
                     'limits':'Cooperative local checks; target sampling between bounded operations, blocking socket operations <=30s; no absolute OS termination claim.'}
            path=c.core_root/c.state/'receipt.local.json';blob=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode();reg.storage(extra_core=2*len(blob)+4096)
            with path.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
            _guard(reg,start,checked['processing_started'],lim['metadata_processing_seconds']);reg.advance('COMPLETE',receipt_sha256=digest(blob))
            _guard(reg,start,checked['processing_started'],lim['metadata_processing_seconds'])
            return receipt
        except BaseException as error:
            # Never print payload/error bodies. Partial/archive/quarantine remains.
            try:
                if not reserved_here:raise Blocked('no fresh attempt to fail')
                reg.advance('FAIL',error_type=type(error).__name__)
                failure={'status':'FAILED_OR_UNKNOWN_NO_RETRY','state':c.state,'url':c.source['url'],'error_type':type(error).__name__,'known_received_lower_bound':received,'known_written_lower_bound':written,'stream_prefix_sha256':partial_hash.hexdigest(),'HTTP_status':http_status,'HTTP_headers':metadata,'failed_at':tick(),'full_reservations_retained':True,'person_rows_read':0,'shutdown':'COOPERATIVE_FAILURE_OR_UNKNOWN_NOT_A_RESOURCE_STOP_PROOF'}
                reg.storage(extra_core=2*len(json.dumps(failure).encode())+4096);atomic_json(c.core_root/c.state/'failure.local.json',failure)
            except BaseException:pass
            raise Blocked('N2a stopped; retain original history/bytes/full charges; no retry') from None
        finally:
            if response is not None:
                try:response.close()
                except BaseException:pass


def collect(config=None):
    c=admit(config)
    from .n2a_http_v1 import PublicHTTP
    return _collect(c,PublicHTTP())


@dataclass(frozen=True)
class FixtureHTTP:
    body:bytes
    status:int=200
    headers_json:str='{}'
    url:str=''
    chunk:int=65536
    fail_after:int=-1
    delay:float=0
    token:object=None


def fake_http(body,*,status=200,headers=None,url='',chunk=65536,fail_after=-1,delay=0):
    if type(body) is not bytes:raise Blocked('authored HTTP bytes only')
    return FixtureHTTP(body,status,json.dumps(detached(headers or {})),url,chunk,fail_after,delay,_TEST)


class _FixtureTransport:
    def __init__(self,fixture):self.fixture=fixture;self.calls=0;self.reads=[];self.closed=False;self.offset=0
    def open(self,url,timeout):
        self.calls+=1;self.status=self.fixture.status;self.url=self.fixture.url or url;self.headers=strict_json(self.fixture.headers_json);return self
    def read(self,count):
        self.reads.append(count)
        if self.fixture.delay:time.sleep(self.fixture.delay)
        if self.fixture.fail_after>=0 and self.offset>=self.fixture.fail_after:raise OSError('AUTHORED_TRANSPORT_FAILURE')
        piece=self.fixture.body[self.offset:self.offset+min(count,self.fixture.chunk)];self.offset+=len(piece);return piece
    def close(self):self.closed=True


def collect_fixture(context,fixture):
    c=require(context)
    if c.realm.tag!='TEST_ONLY' or type(fixture) is not FixtureHTTP or fixture.token is not _TEST:raise Blocked('tagged fake HTTP realm required')
    transport=_FixtureTransport(fixture)
    return _collect(c,transport)
