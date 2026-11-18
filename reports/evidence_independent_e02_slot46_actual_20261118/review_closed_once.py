"""One independent closed-copy normal replay; no current owner, keys or network."""
from pathlib import Path
import sys,os,json,hashlib,sqlite3,resource,signal,tempfile,time,sysconfig,shutil
from unittest.mock import patch
from datetime import datetime
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(120)
root=Path.cwd();sys.path.insert(0,str(root/'src'));start=time.monotonic();used=0
from civiclab import production_owner_v4 as production
from civiclab.e02.wrapper_crossmodel_slot46_v2_owner import Slot46OwnerV2,STATE,ANCHOR,_jsonable
from civiclab.common import canonical_hash,canonical_bytes
cap=root/'data/processed/e02_wrapper_slot46_v2_20261118_actual_01/closed-capture-03'
old=root/'data/processed/e02_wrapper_crossmodel_canary_v1_20261117_actual_01/stop-capture-01'
refs=[]
def charge(n):
 global used
 used+=n
 if used>134217728:raise RuntimeError('READ128MIB')
def read(path):
 assert not path.is_symlink() and path.is_file();charge(path.stat().st_size);raw=path.read_bytes();return raw
manifest_raw=read(cap/'manifest.local.json');manifest=json.loads(manifest_raw);data={}
for ref in manifest['files']:
 path=cap/ref['name'];assert path.is_relative_to(cap) and '..' not in path.parts
 raw=read(path);assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'];data[ref['name']]=raw;refs.append(ref)
assert len(refs)==12
summary=json.loads(data['summary.local.json']);public=json.loads(read(root/'reports/E02_SLOT46_ACTUAL_CLOSED_OUTCOME_V1_1_20261118.json'));assert summary==public
oldmanifest=json.loads(read(old/'manifest.local.json'));olddata={}
for ref in oldmanifest['refs']:
 path=root/ref['path']
 if path.parent.name=='journal' or path.name in ('owner-v4-head.local.json','owner-v4.local.sqlite'):
  raw=read(path);assert hashlib.sha256(raw).hexdigest()==ref['sha256'];olddata[path.name]=raw
with tempfile.TemporaryDirectory(prefix='INDEPENDENT_CLOSED_SLOT46_') as temp:
 tmp=Path(temp).resolve();namespace=tmp/'fixture';directory=namespace/'owner';directory.mkdir(parents=True,mode=0o700)
 for name in ('owner-v4.local.sqlite','owner-v4-head.local.json','owner-v4-guard.local.json'):(directory/name).write_bytes(data[name]);os.chmod(directory/name,0o600)
 (namespace/'openrouter-v4-bootstrap.local.json').write_bytes(data['openrouter-v4-bootstrap.local.json']);os.chmod(namespace/'openrouter-v4-bootstrap.local.json',0o600)
 oldpacket=json.loads(olddata['packet.json']);newpacket=json.loads(data['journal/packet.json'])
 for packet,files in ((oldpacket,{k:v for k,v in olddata.items() if k in ('packet.json','catalog-A.json','catalog-B.json','retention.json','run.lock') or k.endswith(('-request.json','-dispatch.json'))}),(newpacket,{k.removeprefix('journal/'):v for k,v in data.items() if k.startswith('journal/')})):
  j=directory/'limited-pilot-v1'/packet['run_id'];j.mkdir(parents=True,mode=0o700)
  for name,raw in files.items():(j/name).write_bytes(raw);os.chmod(j/name,0o600)
 guardpath=root/'scripts/e01_authored_dirfd_guard_v2_20261112.py';ns={'__name__':'independent_dirfd','__file__':str(guardpath)};exec(compile(read(guardpath),str(guardpath),'exec'),ns);descriptor=ns['DirectoryFdGuard'](lambda p,f:None)
 stdlib=Path(sysconfig.get_path('stdlib')).resolve()
 allowed={root/'reports/E02_SLOT46_RESOURCE_DECISION_20261118.json',root/'scripts/launch_e02_slot46_v2_20261118.py',root/'scripts/collect_connectivity_billing_once.py'}
 def audit(event,args):
  if event.startswith('socket.') or event in ('subprocess.Popen','os.fork','os.posix_spawn','os.system','ctypes.dlopen'):raise RuntimeError('NO_NETWORK_PROCESS')
  if event=='sqlite3.connect':
   p=Path(str(args[0]).removeprefix('file:').split('?')[0]).resolve();assert p.is_relative_to(tmp);charge(p.stat().st_size)
  if event=='open' and not isinstance(args[0],int):
   p=descriptor.event_path(args[0]);flags=args[2]
   if p.name.startswith('.env') or 'SyntheticSocietyLab' in str(p):raise RuntimeError('NO_OWNER_KEY')
   if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):assert p.is_relative_to(tmp)
   else:
    assert p.is_relative_to(tmp) or p.is_relative_to(stdlib) or p.is_relative_to(root/'src') or p.is_relative_to(root/'configs') or p in allowed
    if p.is_file():charge(p.stat().st_size)
 sys.addaudithook(audit);os.open=descriptor.open;os.close=descriptor.close
 class Cursor(sqlite3.Cursor):
  def fetchall(self):
   rows=super().fetchall();charge(sum(len(v.encode()) if isinstance(v,str) else 8 for row in rows for v in row));return rows
  def fetchone(self):
   row=super().fetchone()
   if row is not None:charge(sum(len(v.encode()) if isinstance(v,str) else 8 for v in row))
   return row
 class Connection(sqlite3.Connection):
  def execute(self,*a,**k):return self.cursor(factory=Cursor).execute(*a,**k)
 actual_connect=sqlite3.connect
 def connect(*a,**kw):kw['factory']=Connection;return actual_connect(*a,**kw)
 before=hashlib.sha256(data['owner-v4.local.sqlite']).hexdigest();sqlite3.connect=connect
 with patch.object(production,'production_owner_directory',return_value=directory):
  owner=Slot46OwnerV2()
  with owner._lock(),sqlite3.connect(owner.db_path.as_uri()+'?mode=ro',uri=True) as db:
   state,head=owner._verify(db)
   events=db.execute('SELECT data FROM events ORDER BY sequence').fetchall()
 b=state[STATE];new=[json.loads(row[0]) for row in events[1189:]]
 checks={'all12_capture_pins':True,'public_summary_exact':True,'normal_verifier_replay':True,'head_exact':head==json.loads(data['verified-head.local.json']),'1192_events':len(events)==1192,'only_three_new_events':[x['body']['kind'] for x in new]==['WRAPPER_SLOT46_OPEN_V2','WRAPPER_SLOT46_IO_V2','WRAPPER_SLOT46_CLOSE_V2'],'old195_rows_exact':len(state['rows'])==195 and canonical_hash(state['rows'])==ANCHOR['rows'],'six_holds_unchanged':state['unfinished']==6 and canonical_hash({k:canonical_hash(v) for k,v in state['rows'].items() if v['status']!='PHASE_COMMITTED'})==ANCHOR['protected'],'exposure_unchanged':state['consumed']['total']==17152,'no_model_or_statistics_intent':b['counts']=={'POST':0,'statistics_GET':0,'catalog_GET':1},'closed_no_receipt_witness':b['closed'] is True and b['receipt'] is None and b['witness'] is None,'captured_database_unchanged':hashlib.sha256(owner.db_path.read_bytes()).hexdigest()==before}
 def serial(value):
  if isinstance(value,datetime):return value.isoformat()
  raise TypeError()
 normalized=json.loads(json.dumps(_jsonable(state),sort_keys=True,default=serial));checks['saved_state_matches_independent_replay']=normalized==json.loads(data['verified-state.local.json'])
 failure=json.loads(data['journal/failure-initial-v1.json']);checks['early_failure_catalog_A']=failure['stage']=='CATALOG_A' and failure['retry_allowed'] is False
 checks['no_catalog_or_dispatch_artifacts']=not any(k.startswith('journal/catalog-') or k.endswith(('-request.json','-dispatch.json')) for k in data)
 assert all(checks.values()),[k for k,v in checks.items() if not v]
 safe_new=[{'kind':x['body']['kind'],'sequence':x.get('sequence'),'body_keys':sorted(x['body'])} for x in new]
 sqlite3.connect=actual_connect
 # Allow only exact original captures again for immutable post-check, no current state.
 allowed.update(cap/ref['name'] for ref in refs)
 allowed.add(cap/'manifest.local.json')
 for ref in refs:assert hashlib.sha256(read(cap/ref['name'])).hexdigest()==ref['sha256']
 assert read(cap/'manifest.local.json')==manifest_raw
result={'kind':'INDEPENDENT_CLOSED_SLOT46_OUTCOME_REPLAY','status':'PASS','checks':checks,'new_event_metadata':safe_new,'initial_failure':failure,'closed_manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'captured_input_files':12,'logical_read_bytes':used,'wall_seconds':time.monotonic()-start,'CPU_seconds':sum(resource.getrusage(resource.RUSAGE_SELF)[:2]),'private_fixture_removed':not tmp.exists(),'actual_owner_key_network_model_access':0,'cost_usd':0,'physical_catalog_GET':'NOT_ESTABLISHED_BY_INTENT','model_result':'NO_NEW_RESPONSE_OR_FORECAST'}
print(json.dumps(result,sort_keys=True));signal.alarm(0)
