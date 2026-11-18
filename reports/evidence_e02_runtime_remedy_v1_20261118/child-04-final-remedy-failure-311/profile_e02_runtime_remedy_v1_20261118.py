#!/usr/bin/env python3
"""Four finite OFFLINE profiling modes. Never current owner/key/network.

failure modes reconstruct a private retrospective pre-attempt1180-event view;
this cannot resume any real consumed launcher. Original capture remains intact.
"""
import argparse,cProfile,hashlib,io,json,os,pstats,resource,shutil,signal,sqlite3,sys,sysconfig,tempfile,time
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
CAPTURE=ROOT/'data/processed/e02_wrapper_crossmodel_canary_v1_20261117_actual_01/stop-capture-01'
MANIFEST=CAPTURE/'manifest.local.json'
LAST_STAGE='BOOT';PROFILE_TEMP=None
M={'reads':0,'writes':0,'console':0};LIMIT={'reads':4294967296,'writes':268435456,'console':65536}

def add(k,n):
 M[k]+=n
 if M[k]>LIMIT[k]:raise RuntimeError('PROFILE_BOUND_EXHAUSTED')
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def read(path,pin=None):
 n=path.stat().st_size;add('reads',n);raw=path.read_bytes()
 if pin and (len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']):raise RuntimeError('CAPTURE_PIN')
 return raw

def capture():
 raw=read(MANIFEST,{'bytes':4533,'sha256':'4cc86b9df8c149923eafc3fd8641c1445555f30b1e806045ca9a9f40883d8481'});manifest=json.loads(raw)
 pool=[p for p in CAPTURE.rglob('*') if p.is_file() and not p.is_symlink()]
 if len(pool)>64:raise RuntimeError('CAPTURE_MEMBERSHIP_BOUND')
 refs=manifest['refs'];items=list(refs.items()) if isinstance(refs,dict) else [(None,x) for x in refs]
 records=[]
 for key,item in items:
  data=item.get('ref',item);candidates=[data.get(n) for n in ('path','closed_path','captured_path','copy_path','relative_path','filename','name')]+[key];choices=[]
  for name in candidates:
   if not isinstance(name,str):continue
   path=Path(name)
   choices=[p for p in ([path] if path.is_absolute() else [ROOT/path,CAPTURE/path]) if p.is_relative_to(CAPTURE) and '..' not in p.parts and p in pool]
   if not choices:
    matching=[p for p in pool if p.name==path.name]
    if len(matching)==1:choices=matching
   if choices:break
  if len(set(choices))!=1:raise RuntimeError('CAPTURE_REFERENCE_JOIN')
  path=choices[0]
  if any(p.is_symlink() for p in (path,*path.parents)):raise RuntimeError('CAPTURE_ALIAS')
  raw=read(path,{'bytes':data.get('bytes',data.get('size_bytes')),'sha256':data['sha256']})
  value=json.loads(raw) if raw[:1] in (b'{',b'[') else None
  records.append({'path':path,'raw':raw,'value':value,'bytes':len(raw),'sha256':sha(raw)})
 return records


def main(mode):
 global LAST_STAGE,PROFILE_TEMP
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(599,600))
 signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(RuntimeError('PROFILE900SECONDS')));signal.alarm(900)
 started=time.monotonic();LAST_STAGE='CLOSED_INPUTS';records=capture();before_pins={p['path']:p['sha256'] for p in records}
 temp=tempfile.TemporaryDirectory(prefix='AUTHORED_E02_RUNTIME_PROFILE_');tmp=Path(temp.name).resolve();PROFILE_TEMP=tmp;namespace=tmp/'fixture';namespace.mkdir(mode=0o700);owner_dir=namespace/'owner';owner_dir.mkdir(mode=0o700)
 dbrecord=next(p for p in records if p['raw'].startswith(b'SQLite format 3\x00'))
 jsons=[p for p in records if isinstance(p['value'],dict)]
 q=next(p['value'] for p in jsons if p['value'].get('kind')=='WRAPPER_CANARY_PACKET_V1')
 header=next(p for p in jsons if set(p['value'])=={'schema_version','namespace','scope','owner_id','registration_sha256'})
 registration=next(p for p in jsons if p['value'].get('kind')=='EXTERNAL_ZERO_BOOTSTRAP_ASSERTION_V4')
 head=next(p for p in jsons if set(p['value'])=={'namespace','owner_id','header_sha256','sequence','head_hash'})
 catalogs={role:next(p['value'] for p in jsons if p['path'].name=='catalog-'+role+'.json') for role in ('A','B')}
 db_path=owner_dir/'owner-v4.local.sqlite'
 add('writes',48*1024*1024);add('reads',24*1024*1024)
 for path,raw in [(db_path,dbrecord['raw']),(owner_dir/'owner-v4-guard.local.json',header['raw']),(owner_dir/'owner-v4-head.local.json',head['raw']),(namespace/'openrouter-v4-bootstrap.local.json',registration['raw'])]:
  path.write_bytes(raw);os.chmod(path,0o600)
 if mode=='stop_verify':
  journal=owner_dir/'limited-pilot-v1'/q['run_id'];journal.mkdir(parents=True,mode=0o700)
  for record in records:
   if record['path'].parent.name in ('journal','retained-journal') or record['path'].name in ('catalog-A.json','catalog-B.json','packet.json','retention.json','run.lock') or record['path'].name.endswith(('-request.json','-dispatch.json')):
    (journal/record['path'].name).write_bytes(record['raw'])
 else:
  # Explicit retrospective simulation of the SAME past attempt, never an actual
  # old-owner reset. Only owned derived copy changes; original six holds intact.
  with sqlite3.connect(db_path) as db:
   data=db.execute('SELECT data FROM events WHERE sequence=1185').fetchone()[0];row=json.loads(data)['body']['payload']['after']
   db.execute('DELETE FROM events WHERE sequence>=1180');db.execute('DELETE FROM charges WHERE id=?',(row['id'],))
  db.close();(owner_dir/'owner-v4-head.local.json').write_bytes(canonical(q['expected_head']))
 # Guard before candidate imports. No actual owner/key/network path admitted.
 closure=json.loads(read(ROOT/'reports/evidence_e02_canary_closed_replay_code_v1_20261117/EXACT_CLOSURE_WITH_HELPER.json'))
 allowed={ROOT/p['path'] for p in closure['project_pins']}|{ROOT/'src/civiclab/e02/wrapper_canary_failure_diagnostic_v1.py',ROOT/'src/civiclab/e02/wrapper_crossmodel_canary_diagnostic_v1_client.py',ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py'}|set(before_pins)
 stdlib=Path(sysconfig.get_path('stdlib')).resolve();guardpath=ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py';guard_ns={'__name__':'profile_dirfd','__file__':str(guardpath)};exec(compile(read(guardpath),str(guardpath),'exec'),guard_ns)
 descriptor=guard_ns['DirectoryFdGuard'](lambda path,flags:None)
 def audit(event,args):
  if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:raise RuntimeError('NO_NETWORK_OR_PROCESS')
  if event=='sqlite3.connect':
   path=Path(str(args[0]).removeprefix('file:').split('?')[0]).resolve()
   if not path.is_relative_to(tmp):raise RuntimeError('NO_CURRENT_OWNER_SQLITE')
   if path.is_file():add('reads',path.stat().st_size)
  if event=='open' and not isinstance(args[0],int):
   path=descriptor.event_path(args[0]);flags=args[2]
   if path.name.startswith('.env') or 'SyntheticSocietyLab' in str(path):raise RuntimeError('NO_CURRENT_OWNER_OR_KEY')
   if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
    if not path.is_relative_to(tmp):raise RuntimeError('ONLY_PROFILE_TEMP_WRITES')
   else:
    if not(path in allowed or path.is_relative_to(tmp) or path.is_relative_to(stdlib)):raise RuntimeError('EXACT_PROFILE_READ_SCOPE')
    if path.is_file():add('reads',path.stat().st_size)
 sys.addaudithook(audit);os.open=descriptor.open;os.close=descriptor.close
 import builtins
 class Writes:
  def __init__(self,stream):self.stream=stream
  def __getattr__(self,n):return getattr(self.stream,n)
  def __enter__(self):return self
  def __exit__(self,*a):return self.stream.__exit__(*a)
  def write(self,value):add('writes',len(value.encode() if isinstance(value,str) else value));return self.stream.write(value)
  def writelines(self,values):
   for value in values:self.write(value)
 for obj,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
  original=getattr(obj,name)
  def opened(*a,_original=original,**k):
   stream=_original(*a,**k);mode_=k.get('mode',a[1] if len(a)>1 else 'r')
   return Writes(stream) if any(c in mode_ for c in 'wax+') else stream
  setattr(obj,name,opened)
 class CCursor(sqlite3.Cursor):
  def fetchall(self):
   rows=super().fetchall();add('reads',sum(len(v.encode()) if isinstance(v,str) else 8 for row in rows for v in row));return rows
  def fetchone(self):
   row=super().fetchone()
   if row is not None:add('reads',sum(len(v.encode()) if isinstance(v,str) else 8 for v in row))
   return row
 class CConnection(sqlite3.Connection):
  def execute(self,sql,parameters=()):return self.cursor(factory=CCursor).execute(sql,parameters)
  def executemany(self,sql,parameters):return self.cursor(factory=CCursor).executemany(sql,parameters)
 actual_connect=sqlite3.connect
 def connect(*a,**kw):kw['factory']=CConnection;return actual_connect(*a,**kw)
 sqlite3.connect=connect
 sys.pycache_prefix=str(tmp/'UNCREATED_PYC_CACHE');sys.path.insert(0,str(ROOT/'src'))
 entry_cpu0=resource.getrusage(resource.RUSAGE_SELF);entry_wall0=time.monotonic();LAST_STAGE='IMPORT_AND_ADMISSION'
 from civiclab import production_owner_v4 as production
 from civiclab.e02.wrapper_crossmodel_canary_v1_owner import CanaryOwnerV1,STATE
 from civiclab.e02 import wrapper_crossmodel_canary_v1_client as legacy
 from civiclab.e02 import wrapper_crossmodel_canary_diagnostic_v1_client as successor
 from civiclab.e02.wrapper_canary_failure_diagnostic_v1 import FILENAME
 from civiclab.production_admission_v4 import _Credential
 from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
 from civiclab.common import canonical_hash
 # Captured OPEN timestamp is fixed retained metadata. MOCK clock tracks real elapsed.
 epoch=datetime(2026,11,18,4,5,12,882206,tzinfo=__import__('datetime').timezone.utc);mono0=time.monotonic()
 now=lambda:epoch+timedelta(seconds=time.monotonic()-mono0)
 verify_metrics=[];profile_top=[];failure=None;error_record=None;initial_record_before_cleanup=[]
 with patch.object(production,'production_owner_directory',return_value=owner_dir),patch.object(production,'_utc_now',side_effect=now):
  # Phase's imported UTC sampler is the explicit same real-elapsed MOCK seam.
  from civiclab.e02 import exploratory_live_client_v1 as phase_module
  with patch.object(phase_module,'new_operation_time',side_effect=now):
   owner=CanaryOwnerV1();original_verify=owner._verify
   marker=owner_dir/'limited-pilot-v1'/q['run_id']/FILENAME
   def measured(db):
    cpu=resource.getrusage(resource.RUSAGE_SELF);t=time.monotonic();visible=marker.is_file()
    try:return original_verify(db)
    finally:
     end=resource.getrusage(resource.RUSAGE_SELF);verify_metrics.append({'CPU_seconds':end.ru_utime+end.ru_stime-cpu.ru_utime-cpu.ru_stime,'wall_seconds':time.monotonic()-t,'initial_failure_marker_present':visible})
   owner._verify=measured
   if mode=='stop_verify':
    LAST_STAGE='CPROFILE_FULL_STOP_VERIFY';profile=cProfile.Profile();profile.enable()
    with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
    profile.disable()
    stats=pstats.Stats(profile).stats
    for (file,line,name),entry in sorted(stats.items(),key=lambda item:item[1][3],reverse=True)[:40]:
     cc,nc,tt,ct,callers=entry;profile_top.append({'file':str(Path(file).relative_to(ROOT)) if file.startswith(str(ROOT)) else Path(file).name,'line':line,'function':name,'primitive_calls':cc,'calls':nc,'self_CPU_seconds':tt,'cumulative_CPU_seconds':ct})
    assert len(state['rows'])==195 and state['unfinished']==6 and state['consumed']['total']==17152
   else:
    LAST_STAGE='MOCK_ENTRY_VALIDATE_AND_FAILURE'
    release={'kind':'LEAD_WRAPPER_CANARY_RELEASE_V1','packet_sha256':canonical_hash(q),'code_hash':q['code_hash'],'review_sha256':canonical_hash(q['review']),'maximum_POSTs':1,'scope':'ORIGINAL45_ONLY_NOT_FULL80'}
    # Real original packet/release admission, inert catalog/credential/POST only.
    legacy.validate_release(release,q,canonical_hash(q),canonical_hash(release))
    transport=successor.InertFailureTransport(429);catalog=successor.InertCapturedCatalog(catalogs,now)
    kwargs=dict(expected_packet_hash=canonical_hash(q),release=release,expected_release_hash=canonical_hash(release),owner=owner,credential=_Credential('AUTHORED_ONLY_NOT_A_REAL_KEY'),transport=transport,catalog_fetch=catalog,gate=legacy.OperationGate(q,now=now),sleep=lambda _:None,provenance='MOCK')
    try:
     if mode=='legacy_failure':legacy.execute(q,**kwargs)
     else:
      diagnostic_release={'kind':'DIAGNOSTIC_SUCCESSOR_MOCK_RELEASE_V1','code_hash':canonical_hash(successor.diagnostic_contract()),'packet_hash':canonical_hash(q),'release_hash':canonical_hash(release),'scope':'OFFLINE_RETROSPECTIVE_FAILURE_ONLY_NOT_LIVE'}
      successor.execute_mock(q,diagnostic_release=diagnostic_release,**kwargs)
    except _SafeTransportFailure as error:failure={'kind':'AUTHORED_SAFE_HTTP_FAILURE','http_status':error.diagnostic()['http_status']}
    assert failure and failure['http_status']==429 and transport.posts==1 and transport.gets==0 and catalog.calls==['A','B']
    entry_end=resource.getrusage(resource.RUSAGE_SELF);entry_wall=time.monotonic()-entry_wall0
    entry_CPU=entry_end.ru_utime+entry_end.ru_stime-entry_cpu0.ru_utime-entry_cpu0.ru_stime
    if marker.is_file():error_record=json.loads(marker.read_bytes())
    before_final=len(verify_metrics)
    with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
    branch=state[STATE];row=state['rows'][branch['receipt']]
    assert state['unfinished']==6 and state['consumed']['total']==17152 and row['status']=='UNCERTAIN' and row['charged']==row['reserved']==1003 and branch['closed'] is True
    if mode=='remedy_failure':
     assert error_record and error_record['error_kind']=='SAFE_TRANSPORT_FAILURE' and error_record['http_status']==429 and error_record['stage']=='POST'
     assert any(v['initial_failure_marker_present'] for v in verify_metrics[:before_final])
    failure.update({'transport_posts':transport.posts,'statistics_GETs':transport.gets,'catalog_GETs':len(catalog.calls),'entry_CPU_seconds_including_import_admission_cleanup':entry_CPU,'entry_wall_seconds_including_import_admission_cleanup':entry_wall,'verify_calls_before_final_assertion':before_final})
 entry_end=resource.getrusage(resource.RUSAGE_SELF)
 # Preserve original captured bytes, including all six real holds and consumed state.
 assert all(sha(read(path))==digest for path,digest in before_pins.items())
 LAST_STAGE='CLEANUP';owner._verify=original_verify;sqlite3.connect=actual_connect;temp.cleanup();removed=not tmp.exists()
 entry_end=resource.getrusage(resource.RUSAGE_SELF)
 result={'kind':'E02_OFFLINE_RUNTIME_PROFILE_V1','mode':mode,'runtime':sys.version.split()[0],'status':'PASS_OFFLINE','fixture_mode':'EXACT_CAPTURE_1189' if mode=='stop_verify' else 'RETROSPECTIVE_MOCK_1180_PREFIX_NOT_REAL_RETRY','actual_capture_unchanged':True,'current_owner_access':0,'key_reads':0,'network_calls':0,'actual_model_requests':0,'failure_simulation':failure,'initial_failure_record':error_record,'top_owner_verify_metrics':verify_metrics,'profile_top_cumulative':profile_top,'charged_logical_bytes':M,'whole_process_CPU_seconds':entry_end.ru_utime+entry_end.ru_stime,'wall_seconds':time.monotonic()-started,'private_fixture_removed':removed,'profiling_overhead':'cProfile enabled only forstop_verify; top _verify timing delegates original exactlyonce, no cache or validation skipped.','original_failure_cause':'REMAINS_UNKNOWN'}
 text=json.dumps(result,sort_keys=True);add('console',len(text.encode()));print(text)
 return 0


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=['stop_verify','legacy_failure','remedy_failure'],required=True);args=parser.parse_args()
 try:raise SystemExit(main(args.mode))
 except SystemExit:raise
 except BaseException as error:
  removed=False
  if PROFILE_TEMP is not None:
   try:shutil.rmtree(PROFILE_TEMP);removed=not PROFILE_TEMP.exists()
   except BaseException:pass
  print(json.dumps({'kind':'E02_OFFLINE_RUNTIME_PROFILE_V1','status':'FAILED_OFFLINE_NO_RETRY','stage':LAST_STAGE,'private_fixture_removed':removed,'error_type':type(error).__name__ if type(error) in (RuntimeError,ValueError,TypeError,AssertionError,OSError) else 'OTHER','charged_logical_bytes':M,'actual_model_requests':0,'network_calls':0},sort_keys=True));raise SystemExit(1)
