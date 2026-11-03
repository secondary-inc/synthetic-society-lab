"""New partial-pilot ledger: deterministic transition replay, native caps unchanged.

Trusted execution/preserved history boundary; not hostile-history authentication.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import math
import os
from pathlib import Path
import shutil
import time
from ..common import atomic_json,canonical_hash,sha256_file
from .national_budget import Blocked
from .f_actual_admission_v1 import require_admission
from .full_adult_types_v1_2 import strict_json


class Storage:
    def __init__(self,a):self.a=require_admission(a);self.root=a.root;self.c=a.config
    def category(self,p):
        r=p.relative_to(self.root);parts=r.parts
        if parts[0]=='inputs':return 'raw'
        if parts[0]=='scratch':return 'scratch'
        if parts[0] in ('PRIMARY','REPLAY'):return parts[0]+':base'
        return 'core'
    def check(self,category=None,extra=0,*,initial=False):
        q=self.c['storage'];usage={}
        if self.a.origin=='ACTUAL':usage['raw']=self.a.manifest['archive_bytes']
        for p in self.root.rglob('*'):
            if p.is_symlink():raise Blocked('symlink in private pilot workspace')
            if p.is_file():k=self.category(p);usage[k]=usage.get(k,0)+p.stat().st_size
        if extra<0:raise Blocked('negative storage projection')
        if category:usage[category]=usage.get(category,0)+extra
        if shutil.disk_usage(self.root).free<max(q['free'],q['initial_free'] if initial else 0)+extra:raise Blocked('private free/atomic headroom')
        for k,cap in q['caps'].items():
            if usage.get(k,0)>cap:raise Blocked('native storage partition '+k)
        data=sum(v for k,v in usage.items() if k.startswith(('PRIMARY:','REPLAY:')))
        logs=usage.get('core',0)+usage.get('receipts',0)
        if data>q['data_both'] or logs>q['logs'] or data+logs>q['all_artifacts']:raise Blocked('native cumulative data/log artifact quota')
        return usage
    def write(self,path,blob):
        p=Path(path).resolve()
        if not p.is_relative_to(self.root) or p.exists():raise Blocked('immutable private artifact')
        self.check(self.category(p),len(blob));p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        return sha256_file(p)
    def json(self,path,value):return self.write(path,(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())


class PilotLedger:
    def __init__(self,a,*,clock=time.time):
        self.a=require_admission(a);self.c=a.config;self.m=a.manifest;self.root=a.root;self.path=a.root/'ledger';self.path.mkdir(exist_ok=True);self.clock=clock;self.storage=Storage(a);self._validated_parts=set()
        self.design=canonical_hash({'config':self.c,'manifest':self.m,'root':str(a.root),'scope':a.origin+'_PARTIAL_WY_ONLY'})
        comp=next(x for x in self.m['members'] if x['name']==self.m['companion']);person=next(x for x in self.m['members'] if x['name']==self.m['person']);self.expanded=self.m['header_bytes']+comp['bytes'];self.parse_bytes=person['bytes']+2*self.expanded
        self.descriptors={'ENROLL':{'bytes':self.c['limits']['line_bytes']+3*self.c['limits']['companion_bytes'],'rows':0,'ops':0}}
        for w in ('PRIMARY','REPLAY'):
            self.descriptors[w]={'bytes':self.parse_bytes,'rows':self.m['expected_rows'],'ops':0}
            self.descriptors['FINALIZE_'+w]={'bytes':0,'rows':0,'ops':6000000}
        self.genesis={'schema':'E02_F_PARTIAL_WY_LEDGER_V1','origin':a.origin,'design':self.design,'created':None,'stages':{},'source_halted':False,'analysis_halted':False,'continuations':[],'generation':0,'last_clock':None,'ops':0,'expanded_bytes':0,'rows':0,'seconds':0,'unique_source_bytes':self.m['archive_bytes'],'retained_source_bytes':self.m['archive_bytes'],'GETs':0,'BODY_bytes':0,'network_seconds':0}
        with self.lock():
            marker=self.root/'.F_WY_LEDGER_INITIALIZED'
            if not (self.path/'state.json').exists():
                if marker.exists() or any((self.root/n).exists() for n in ('ENROLL.local.json','PRIMARY.local.json','REPLAY.local.json','PRIMARY','REPLAY')):raise Blocked('retained run cannot reset a lost ledger')
                if any(p.name!='.lock' for p in self.path.iterdir()):raise Blocked('no initialization over retained ledger history')
                self.storage.check(initial=True);g=deepcopy(self.genesis);g['created']=g['last_clock']=clock();self.storage.json(self.path/'genesis.json',g);self.storage.json(self.path/'state.json',g)
                self.storage.write(marker,(self.design+'\n').encode())
            if not marker.is_file() or marker.read_text()!=self.design+'\n':raise Blocked('ledger marker missing/changed; no reset')
            self._verified()
    @contextmanager
    def lock(self):
        with (self.path/'.lock').open('a') as f:
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise Blocked('pilot ledger single owner') from None
            try:yield
            finally:fcntl.flock(f,fcntl.LOCK_UN)
    def _proof(self,key,proof):
        if set(proof)!={'path','sha256'}:raise Blocked('closed checkpoint proof')
        path=(self.root/proof['path']).resolve()
        if not path.is_relative_to(self.root) or path.is_symlink() or sha256_file(path)!=proof['sha256']:raise Blocked('checkpoint changed/missing')
        value=strict_json(path.read_text())
        if key=='ENROLL':
            if value['manifest_sha256']!=canonical_hash(self.m) or value['validation_expanded_bytes']!=self.expanded or value['person_rows_read']!=0:raise Blocked('enrollment proof binding')
        elif key in ('PRIMARY','REPLAY'):
            from .f_wy_source_v1 import validate_part
            cache_key=(key,proof['sha256'])
            if cache_key not in self._validated_parts:
                validate_part(value,self.a);self._validated_parts.add(cache_key)
            if value['source_identity']!=strict_json((self.root/'ENROLL.local.json').read_text())['identity']:raise Blocked('parse/enrolled source identity differs')
            if value['expanded_bytes']!=self.parse_bytes:raise Blocked('delivered parse expansion')
        else:
            if value['schema']!='E02_F_PARTIAL_WY_FINAL_PROOF_V1' or value['origin']!=self.a.origin or value['source_manifest_sha256']!=canonical_hash(self.m) or value['sweep']!=key.removeprefix('FINALIZE_') or type(value['observed_logical_ops']) is not int or not 0<=value['observed_logical_ops']<=6000000:raise Blocked('partial finalization proof')
            manifest=(self.root/value['manifest_path']).resolve()
            if not manifest.is_relative_to(self.root) or sha256_file(manifest)!=value['manifest_sha256']:raise Blocked('partial manifest proof')
            m=strict_json(manifest.read_text())
            for name,h in m['files'].items():
                if Path(name).name!=name or sha256_file(manifest.parent/name)!=h:raise Blocked('partial referenced artifact integrity')
        return value
    def _recount(self,s):
        limit=self.c['limits'];ops=0;nb=0;nr=0;seconds=0
        for key,p in s['stages'].items():
            d=self.descriptors[key];ops+=d['ops']
            if p['status']=='COMMITTED':
                self._proof(key,p['proof']);nb+=self.expanded if key=='ENROLL' else d['bytes'];nr+=d['rows'];seconds+=p['elapsed']
            else:nb+=d['bytes'];nr+=d['rows'];seconds+=limit['state_processing_seconds']
        s.update(ops=ops,expanded_bytes=nb,rows=nr,seconds=seconds)
        if ops>64000000 or nb>limit['two_sweep_uncompressed_bytes'] or nr>limit['two_sweep_rows'] or seconds>limit['processing_seconds'] or self.m['archive_bytes']>min(limit['unique_source_bytes'],limit['retained_bytes']):raise Blocked('native cumulative pilot quota')
        if self.parse_bytes>limit['state_uncompressed_bytes'] or self.m['expected_rows']>min(limit['state_rows'],limit['sweep_rows']) or self.parse_bytes>limit['sweep_uncompressed_bytes']:raise Blocked('native state/sweep quota')
    def _transition(self,old,event,payload):
        s=deepcopy(old);limit=self.c['limits']
        if type(payload['at']) not in (int,float) or not math.isfinite(payload['at']) or payload['at']<s['last_clock']:raise Blocked('pilot clock monotonicity')
        s['generation']+=1;s['last_clock']=payload['at']
        if event=='CONTINUE_SOURCE':
            if self.a.origin!='AUTHORED':raise Blocked('actual continuation requires separately reviewed authority; unavailable')
            audit=payload['audit']
            if set(audit)!={'kind','design','state_sha256','preserve_charges'} or audit!={'kind':'AUTHORED_EXACT_SOURCE_CONTINUATION','design':self.design,'state_sha256':canonical_hash(old),'preserve_charges':True} or not old['source_halted']:raise Blocked('exact-state authored source continuation required')
            if any(p['status']=='RESERVED' for p in old['stages'].values()):raise Blocked('pending source recovery first')
            s['source_halted']=False;s['continuations'].append(audit)
        else:
            key=payload['key']
            if key not in self.descriptors:raise Blocked('work identity closed')
            if event=='RESERVE':
                if key in s['stages'] or any(p['status']=='RESERVED' for p in s['stages'].values()):raise Blocked('duplicate/pending work')
                if key.startswith('FINALIZE_'):
                    if s['analysis_halted'] or s['stages'].get(key.removeprefix('FINALIZE_'),{}).get('status')!='COMMITTED':raise Blocked('partial finalization dependency/analysis barrier')
                elif s['source_halted']:raise Blocked('source failure needs exact continuation')
                if key in ('PRIMARY','REPLAY') and s['stages'].get('ENROLL',{}).get('status')!='COMMITTED':raise Blocked('source not enrolled')
                s['stages'][key]={'status':'RESERVED','started':payload['at'],'elapsed':None,'proof':None}
            elif event in ('COMMIT','FAIL','UNKNOWN'):
                p=s['stages'].get(key,{})
                if p.get('status')!='RESERVED':raise Blocked('terminal requires exact pending stage')
                if event=='COMMIT':
                    elapsed=payload['at']-p['started']
                    if elapsed>limit['state_processing_seconds']:raise Blocked('work deadline')
                    self._proof(key,payload['proof']);p.update(status='COMMITTED',elapsed=elapsed,proof=payload['proof'])
                else:
                    p.update(status='FAILED' if event=='FAIL' else 'UNKNOWN')
                    s['analysis_halted' if key.startswith('FINALIZE_') else 'source_halted']=True
            else:raise Blocked('unknown pilot transition')
        self._recount(s);return s
    def _verified(self):
        try:
            g=strict_json((self.path/'genesis.json').read_text());expected=deepcopy(self.genesis);expected['created']=expected['last_clock']=g['created']
            if g!=expected:raise Blocked('immutable genesis/design changed')
            s=g;previous=None;path=self.path/'events.jsonl';events=[strict_json(x) for x in path.read_text().splitlines()] if path.exists() else []
            for seq,row in enumerate(events,1):
                if set(row)!={'seq','prev','before','event','payload','after','h'} or row['seq']!=seq or row['prev']!=previous or row['before']!=canonical_hash(s) or row['h']!=canonical_hash({k:v for k,v in row.items() if k!='h'}):raise Blocked('pilot event chain')
                s=self._transition(s,row['event'],row['payload'])
                if row['after']!=canonical_hash(s):raise Blocked('pilot replayed transition differs')
                previous=row['h']
            if strict_json((self.path/'state.json').read_text())!=s:raise Blocked('torn/current counter/barrier differs from retained history')
            if self.clock()<s['last_clock'] or self.clock()-s['created']>self.c['limits']['batch_elapsed_seconds']:raise Blocked('pilot expired/clock rollback')
            return s
        except (OSError,KeyError,TypeError,ValueError):raise Blocked('unprovable pilot ledger; no reset') from None
    def snapshot(self):
        with self.lock():return deepcopy(self._verified())
    def _advance(self,event,payload,hook=lambda event:None):
        s=self._verified();payload={**payload,'at':self.clock()};new=self._transition(s,event,payload)
        path=self.path/'events.jsonl';rows=[strict_json(x) for x in path.read_text().splitlines()] if path.exists() else []
        r={'seq':len(rows)+1,'prev':rows[-1]['h'] if rows else None,'before':canonical_hash(s),'event':event,'payload':payload,'after':canonical_hash(new)};r['h']=canonical_hash(r)
        blob=(json.dumps(r,sort_keys=True,allow_nan=False)+'\n').encode();self.storage.check('core',len(blob)+2*len(json.dumps(new).encode())+4096)
        with path.open('ab') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        hook('after_event_before_state');atomic_json(self.path/'state.json',new);return new
    def reserve(self,key,*,hook=lambda event:None):
        with self.lock():return self._advance('RESERVE',{'key':key},hook)
    def commit(self,key,path,*,hook=lambda event:None):
        p=Path(path).resolve()
        if not p.is_relative_to(self.root):raise Blocked('proof outside private workspace')
        with self.lock():return self._advance('COMMIT',{'key':key,'proof':{'path':str(p.relative_to(self.root)),'sha256':sha256_file(p)}},hook)
    def fail(self,key):
        with self.lock():return self._advance('FAIL',{'key':key})
    def recover_unknown(self):
        with self.lock():
            s=self._verified();pending=[k for k,p in s['stages'].items() if p['status']=='RESERVED']
            if len(pending)!=1:raise Blocked('one provable pending reservation required')
            return self._advance('UNKNOWN',{'key':pending[0]})
    def continue_source(self,audit):
        with self.lock():return self._advance('CONTINUE_SOURCE',{'audit':audit})
