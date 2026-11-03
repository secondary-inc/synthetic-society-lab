"""N2b trusted-history journal, immutable deadlines and conservative reservations."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import platform
import resource
import shutil
from ..common import canonical_hash
from . import n2b_admission_v1_2 as a
from . import n2b_window_v1_2 as window
from .f_actual_admission_v1_1 import detached
from .full_adult_types_v1_2 import strict_json
from .national_budget import Blocked
from . import n2b_metrics_v1_1_1 as metrics

PARTITIONS=('core','DC_PRIMARY_part','DC_REPLAY_part','ASSEMBLE_PRIMARY_canonical_data','ASSEMBLE_REPLAY_canonical_data','scratch')

def mkdir(path,root):
 p=root
 for q in path.relative_to(root).parts:
  p=p/q
  if p.is_symlink():raise Blocked('output ancestor symlink')
  p.mkdir(exist_ok=True)

def no_link_ancestors(path,root):
 from .n2b_storage_v1_1_1 import directory
 return directory(path,root,required=False)

def rss():
 n=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 return int(n if platform.system()=='Darwin' else n*1024)

class Control:
 def __init__(self,context,*,create=False):
  self.c=a.require(context);self.path=self.c.output
  if create:
   if self.path.exists() or self.path.is_symlink() or self.c.registry.exists() or self.c.registry.is_symlink():raise Blocked('original owner/output exists; no reset')
   t=a.tick();old=self.c.config['history'];native=self.c.config['native_limits'];grant=self.c.binding['prospective_grant'];deadline=window.admission_deadline(grant,t)
   if deadline-t['wall']<1500:raise Blocked('complete original remaining window cannot fit')
   if old['WY_full_outer_reservation']['seconds']+old['N2a_DC_full_reservation']['processing_seconds']+1500>native['processing_seconds']:raise Blocked('cumulative time cap')
   self.storage(initial=True,extra={'core':16384})
   mkdir(self.c.registry.parent,self.c.root)
   try:self.c.registry.mkdir(exist_ok=False)
   except FileExistsError:raise Blocked('prospective first-use owner already claimed') from None
   marker={'design':self.c.binding['design_sha256'],'root':str(self.c.root),'created':t,'session':self.c.session,'grant_sha256':self.c.config['window_grant']['sha256'],'reservation':{'seconds':1500,'rows':65010,'expanded_bytes':134724553,'ops':24000000},'history_sha256':canonical_hash(old)}
   with (self.c.registry/'ORIGINAL_OWNER.json').open('x') as f:json.dump(marker,f,sort_keys=True);f.flush();os.fsync(f.fileno())
   mkdir(self.path/'core',self.c.root);a.register_owner(self.c,t)
   with self.lock():
    g={'realm':self.c.realm.kind,'schema':'E02_N2B_PROSPECTIVE_CONTROL_V1_2','design':self.c.binding['design_sha256'],'created':t,'deadline':deadline,'session':self.c.session,'prospective_grant':grant,'window_grant_ref':self.c.config['window_grant'],'clock_accounting_at_creation':window.history_observations(grant,old,t,t),'last':t,'history':old,'reservation':{'seconds':1500,'rows':65010,'expanded_bytes':134724553,'ops':24000000},'stages':{},'sequence':0,'halted':False}
    self._replace('genesis.json',g);self._replace('state.json',g);self._replace('ORIGINAL.json',{'genesis_sha256':canonical_hash(g)})
  a.require_owner(self.c)
  if not self.path.is_dir():raise Blocked('original control missing')
  self.snapshot()

 @contextmanager
 def lock(self):
  a.require_owner(self.c)
  if self.path!=self.c.output or self.path.is_symlink():raise Blocked('control path changed')
  with (self.path/'core/.lock').open('a') as f:
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise Blocked('single N2b owner') from None
   self._owner_pid=os.getpid()
   try:yield
   finally:self._owner_pid=None;fcntl.flock(f,fcntl.LOCK_UN)

 @contextmanager
 def owner(self):
  if getattr(self,'_owner_pid',None)==os.getpid():yield
  else:
   with self.lock():yield

 def access(self,stage,kind):
  with self.owner():return self.advance('ACCESS',stage,{'kind':kind})

 def storage(self,*,initial=False,extra=None):
  a.require(self.c);extra=extra or {};caps=self.c.config['caps'];native=self.c.config['native_limits'];oldstorage=self.c.config['native_storage']
  if self.path!=self.c.output or set(extra)-set(PARTITIONS) or any(type(v) is not int or v<0 for v in extra.values()):raise Blocked('fixed projection domain')
  amounts={p:extra.get(p,0) for p in PARTITIONS};old_data=old_core=old_raw=0
  from .n2b_storage_v1_1_1 import directory
  registry_present=directory(self.c.registry,self.c.root,required=False)
  output_present=directory(self.path,self.c.root,required=registry_present)
  if output_present and not registry_present:raise Blocked('owned output missing original owner registry')
  for name in PARTITIONS:directory(self.path/name,self.c.root,required=registry_present and name=='core')
  if self.path.is_symlink():raise Blocked('output symlink')
  if self.path.exists():
   for f in self.path.rglob('*'):
    if f.is_symlink():raise Blocked('owned symlink')
    if not f.is_file():
     if not f.is_dir():raise Blocked('unexpected new special entry')
     continue
    rel=f.relative_to(self.path);partition=rel.parts[0]
    if partition not in amounts:raise Blocked('unexpected output partition')
    amounts[partition]+=metrics.stat_size(f)
  if self.c.registry.is_symlink():raise Blocked('registry root symlink')
  if self.c.registry.exists():
   for f in self.c.registry.rglob('*'):
    if f.is_symlink():raise Blocked('registry file symlink')
    if not f.is_file() and not f.is_dir():raise Blocked('unexpected registry special entry')
    if f.is_file():amounts['core']+=metrics.stat_size(f)
  from .n2b_storage_v1_1_1 import scan
  prior=scan(self.c);old_data=prior['old_data'];old_core=prior['old_core'];old_raw=prior['old_raw'];old_scratch=prior['old_scratch']
  if any(amounts[p]>caps[p] for p in PARTITIONS) or sum(amounts.values())>caps['total']:raise Blocked('owned partition/total cap')
  data=sum(amounts[p] for p in PARTITIONS if p not in ('core','scratch'))
  if old_data+data>oldstorage['data_both'] or old_core+amounts['core']>native['log_bytes'] or old_raw>native['retained_bytes'] or old_core+old_data+old_scratch+sum(amounts.values())>oldstorage['all_artifacts'] or old_scratch+amounts['scratch']>oldstorage['caps']['scratch']:raise Blocked('whole old/new storage cap')
  free=shutil.disk_usage(self.c.root).free
  if free<max(native['free_disk_bytes'],native['minimum_initial_free_disk_bytes'] if initial else 0)+sum(extra.values()):raise Blocked('free disk and atomic headroom')
  return {'new':amounts,**prior}

 def _replace(self,name,value):
  b=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();self.storage(extra={'core':len(b)})
  p=self.path/'core'/name;temp=p.with_name(p.name+'.atomic')
  if p.is_symlink() or temp.exists() or temp.is_symlink():raise Blocked('control atomic path')
  with temp.open('xb') as f:f.write(b);metrics.written(len(b));f.flush();os.fsync(f.fileno())
  temp.replace(p)

 def write(self,partition,name,blob):
  a.require(self.c)
  if partition not in PARTITIONS or Path(name).name!=name or name in ('.','..') or type(blob) is not bytes:raise Blocked('fixed output write')
  self.storage(extra={partition:len(blob)})
  directory=self.path/partition;mkdir(directory,self.c.root);p=directory/name
  if p.exists() or p.is_symlink():raise Blocked('immutable artifact')
  with p.open('xb') as f:f.write(blob);metrics.written(len(blob));f.flush();os.fsync(f.fileno())
  self.storage();return {'partition':partition,'name':name,'bytes':len(blob),'sha256':a.sha(blob)}

 def json(self,partition,name,v):return self.write(partition,name,(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())

 def transition(self,s,event,p):
  s=detached(s);a.elapsed(s['last'],p['at']);s['last']=p['at'];s['sequence']+=1
  if set(p)!={'at','stage','result'} or p['stage'] not in [x['id'] for x in self.c.config['stages']]:raise Blocked('closed stage event')
  key=p['stage'];entry=s['stages'].get(key);stages=self.c.config['stages'];index=[x['id'] for x in stages].index(key)
  if event=='RESERVE':
   if p['result'] is not None:raise Blocked('reservation has no caller proof')
   if s['halted'] or entry is not None or any(s['stages'].get(x['id'],{}).get('status')!='COMPLETED' for x in stages[:index]) or any(x['status']=='RESERVED' for x in s['stages'].values()):raise Blocked('stage order/retry/halt')
   if p['at']['wall']>=s['deadline'] or a.elapsed(s['created'],p['at'])>=1500:raise Blocked('immutable sequence deadline')
   s['stages'][key]={'status':'RESERVED','started':p['at'],'reservation':stages[index],'result':None,'source_reads':{'metadata':0,'person':0}}
  elif event=='ACCESS':
   if s['halted'] or entry is None or entry['status']!='RESERVED' or type(p['result']) is not dict or set(p['result'])!={'kind'}:raise Blocked('access requires original reserved stage')
   kind=p['result']['kind'];caps={'BIND':{'metadata':1,'person':0},'DC_PRIMARY':{'metadata':2,'person':1},'DC_REPLAY':{'metadata':2,'person':1}}
   if kind not in ('metadata','person') or key not in caps or entry['source_reads'][kind]>=caps[key][kind]:raise Blocked('source pass quota, no third scan')
   entry['source_reads'][kind]+=1
  elif event in ('COMPLETE','FAIL','UNKNOWN'):
   if entry is None or entry['status']!='RESERVED' and not (event=='FAIL' and entry['status']=='COMPLETED'):raise Blocked('no original active stage')
   if event=='COMPLETE':
    if a.elapsed(entry['started'],p['at'])>300 or a.elapsed(s['created'],p['at'])>=1500 or p['at']['wall']>=s['deadline']:raise Blocked('late stage closure')
    ref=p['result']
    if type(ref) is not dict or set(ref)!={'partition','name','bytes','sha256'} or ref['partition']!='core' or ref['name']!=key+'.receipt.json':raise Blocked('stage immutable proof')
    raw=metrics.read_bytes(self.path/'core'/ref['name'])
    if len(raw)!=ref['bytes'] or a.sha(raw)!=ref['sha256']:raise Blocked('stage proof hash')
    proof=strict_json(raw)
    if proof.get('realm')!=self.c.realm.kind or proof.get('stage')!=key or proof.get('design')!=s['design'] or proof.get('status')!='ENGINEERING_STAGE_ONLY_PRIVATE':raise Blocked('stage proof design')
   if event!='COMPLETE' and (type(p['result']) is not dict or set(p['result'])!={'error_type'} or type(p['result']['error_type']) is not str or len(p['result']['error_type'])>128):raise Blocked('safe failure schema')
   entry['status']={'COMPLETE':'COMPLETED','FAIL':'FAILED','UNKNOWN':'UNKNOWN'}[event];entry['result']=p['result']
   if event!='COMPLETE':s['halted']=True
  else:raise Blocked('closed control event')
  return s

 def _read(self):
  a.require_owner(self.c)
  if self.path!=self.c.output:raise Blocked('fixed control path')
  no_link_ancestors(self.path,self.c.root);no_link_ancestors(self.c.registry,self.c.root)
  for name in ('genesis.json','state.json','ORIGINAL.json','events.jsonl'):
   if (self.path/'core'/name).is_symlink():raise Blocked('control symlink')
  try:
   g=strict_json(metrics.read_text((self.path/'core/genesis.json')));s=detached(g)
   owner=self.c.registry/'ORIGINAL_OWNER.json';session=a.require_owner(self.c)
   expected_owner={'design':g['design'],'root':str(self.c.root),'created':g['created'],'session':self.c.session,'grant_sha256':self.c.config['window_grant']['sha256'],'reservation':{'seconds':1500,'rows':65010,'expanded_bytes':134724553,'ops':24000000},'history_sha256':canonical_hash(self.c.config['history'])}
   if owner.is_symlink() or strict_json(metrics.read_text(owner))!=expected_owner or session['created']!=g['created']:raise Blocked('original prospective session/owner marker')
   if set(g)!={'realm','schema','design','created','deadline','session','prospective_grant','window_grant_ref','clock_accounting_at_creation','last','history','reservation','stages','sequence','halted'} or g['realm']!=self.c.realm.kind or g['schema']!='E02_N2B_PROSPECTIVE_CONTROL_V1_2' or g['design']!=self.c.binding['design_sha256'] or g['history']!=self.c.config['history'] or g['stages']!={} or g['sequence']!=0 or g['halted'] is not False or g['last']!=g['created'] or g['reservation']!={'seconds':1500,'rows':65010,'expanded_bytes':134724553,'ops':24000000} or g['deadline']!=window.admission_deadline(g['prospective_grant'],g['created']) or g['session']!=self.c.session or g['prospective_grant']!=self.c.binding['prospective_grant'] or g['window_grant_ref']!=self.c.config['window_grant'] or g['clock_accounting_at_creation']!=window.history_observations(g['prospective_grant'],g['history'],g['created'],g['created']) or strict_json(metrics.read_text((self.path/'core/ORIGINAL.json')))!={'genesis_sha256':canonical_hash(g)}:raise Blocked('original control genesis')
   previous=None;log=self.path/'core/events.jsonl'
   for i,line in enumerate(metrics.read_text(log).splitlines() if log.exists() else [],1):
    row=strict_json(line)
    if set(row)!={'seq','previous','before','event','payload','after','hash'} or row['seq']!=i or row['previous']!=previous or row['before']!=canonical_hash(s) or row['hash']!=canonical_hash({k:v for k,v in row.items() if k!='hash'}):raise Blocked('control chain')
    s=self.transition(s,row['event'],row['payload'])
    if row['after']!=canonical_hash(s):raise Blocked('semantic history')
    previous=row['hash']
   if strict_json(metrics.read_text((self.path/'core/state.json')))!=s:raise Blocked('torn state no reset')
   a.elapsed(s['last'],a.tick());return s,previous
  except (OSError,KeyError,TypeError,ValueError) as e:
   if isinstance(e,Blocked):raise
   raise Blocked('unprovable history') from None

 def snapshot(self):
  with self.lock():return detached(self._read()[0])

 def advance(self,event,stage,result=None):
  s,previous=self._read();p={'at':a.tick(),'stage':stage,'result':detached(result)};new=self.transition(s,event,p)
  row={'seq':new['sequence'],'previous':previous,'before':canonical_hash(s),'event':event,'payload':p,'after':canonical_hash(new)};row['hash']=canonical_hash(row)
  b=(json.dumps(row,sort_keys=True)+'\n').encode();self.storage(extra={'core':len(b)+2*len(json.dumps(new).encode())+8192})
  with (self.path/'core/events.jsonl').open('ab') as f:f.write(b);metrics.written(len(b));f.flush();os.fsync(f.fileno())
  self._replace('state.json',new);return new

 def guard(self,stage):
  a.require(self.c);s,_=self._read();entry=s['stages'].get(stage);now=a.tick()
  if s['halted'] or entry is None or now['wall']>=s['deadline'] or a.elapsed(s['created'],now)>=1500 or a.elapsed(entry['started'],now)>300:raise Blocked('stage/whole deadline or halt')
  if rss()>self.c.config['native_limits']['rss_stop_bytes'] or (self.path/'core/CANCEL').exists():raise Blocked('sampled RSS/cancel stop')
  self.storage()

 def clock_accounting(self):
  state=self._read()[0];return window.history_observations(state['prospective_grant'],state['history'],state['created'],a.tick())

 def cancel(self):
  # No owner lock needed; standalone caller validates captured admission first.
  a.require(self.c);self.storage(extra={'core':128});p=self.path/'core/CANCEL'
  if not p.exists():
   with p.open('x') as f:f.write('CANCEL\n');f.flush();os.fsync(f.fileno())

 def unknown(self):
  with self.lock():
   active=[k for k,v in self._read()[0]['stages'].items() if v['status']=='RESERVED']
   if len(active)!=1:raise Blocked('one interrupted stage required')
   return self.advance('UNKNOWN',active[0],{'error_type':'InterruptedUnknown'})

 def run_stage(self,key,work):
  reserved=False
  with self.lock():
   try:
    self.advance('RESERVE',key);reserved=True;self.guard(key);result=work();self.guard(key)
    proof=self.json('core',key+'.receipt.json',{'realm':self.c.realm.kind,'contract':self.c.config['contract'],'stage':key,'design':self.c.binding['design_sha256'],'status':'ENGINEERING_STAGE_ONLY_PRIVATE','clock_accounting':self.clock_accounting(),'result':result})
    self.advance('COMPLETE',key,proof);self.guard(key);return result
   except BaseException as e:
    if reserved:
     try:self.advance('FAIL',key,{'error_type':type(e).__name__})
     except BaseException:pass
    raise Blocked('N2b stage stopped, preserve bytes/history/full reservations') from None
