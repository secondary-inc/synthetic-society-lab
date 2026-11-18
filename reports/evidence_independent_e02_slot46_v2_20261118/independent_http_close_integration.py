#!/usr/bin/env python3
"""Four allocated OFFLINE whole-entry integrations. Never current owner/key/network.

Every mode copies the exact current1189-event state; consumed44/45 remain immutable.
"""
import argparse,cProfile,hashlib,io,json,os,pstats,resource,shutil,signal,sqlite3,sys,sysconfig,tempfile,time
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
ROOT=Path.cwd().resolve()
CAPTURE=ROOT/'data/processed/e02_wrapper_crossmodel_canary_v1_20261117_actual_01/stop-capture-01'
MANIFEST=CAPTURE/'manifest.local.json'
LAST_STAGE='BOOT';QUALIFY_TEMP=None
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
 global LAST_STAGE,QUALIFY_TEMP
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(599,600))
 signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(RuntimeError('PROFILE900SECONDS')));signal.alarm(900)
 started=time.monotonic();LAST_STAGE='CLOSED_INPUTS';records=capture();before_pins={p['path']:p['sha256'] for p in records}
 temp=tempfile.TemporaryDirectory(prefix='AUTHORED_E02_SLOT46_V2_');tmp=Path(temp.name).resolve();QUALIFY_TEMP=tmp;namespace=tmp/'fixture';namespace.mkdir(mode=0o700);owner_dir=namespace/'owner';owner_dir.mkdir(mode=0o700)
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
 journal=owner_dir/'limited-pilot-v1'/q['run_id'];journal.mkdir(parents=True,mode=0o700)
 for record in records:
  if record['path'].parent.name in ('journal','retained-journal') or record['path'].name in ('catalog-A.json','catalog-B.json','packet.json','retention.json','run.lock') or record['path'].name.endswith(('-request.json','-dispatch.json')):
   (journal/record['path'].name).write_bytes(record['raw'])
 # Guard before candidate imports. No actual owner/key/network path admitted.
 closure=json.loads(read(ROOT/'reports/evidence_e02_canary_closed_replay_code_v1_20261117/EXACT_CLOSURE_WITH_HELPER.json'))
 allowed={ROOT/p['path'] for p in closure['project_pins']}|{ROOT/'src/civiclab/e02/wrapper_canary_failure_diagnostic_v1.py',ROOT/'src/civiclab/e02/wrapper_crossmodel_canary_diagnostic_v1_client.py',ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py'}|set(before_pins)
 allowed.update(ROOT/name for name in ('src/civiclab/e02/wrapper_crossmodel_slot46_v2.py','src/civiclab/e02/wrapper_crossmodel_slot46_v2_owner.py','src/civiclab/e02/wrapper_crossmodel_slot46_v2_client.py','scripts/launch_e02_slot46_v2_20261118.py','configs/e02_wrapper_slot46_v2_20261118.json','reports/E02_SLOT46_RESOURCE_DECISION_20261118.json','scripts/collect_connectivity_billing_once.py'))
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
 # Measure the entire process separately; exact main installs real120/125CPU.
 entry_cpu0=resource.getrusage(resource.RUSAGE_SELF);entry_wall0=time.monotonic();LAST_STAGE='IMPORT_AND_PACKET'
 from civiclab import production_owner_v4 as production
 from civiclab.e02 import wrapper_crossmodel_slot46_v2 as pure
 from civiclab.e02 import wrapper_crossmodel_slot46_v2_owner as owner_module
 from civiclab.e02 import wrapper_crossmodel_slot46_v2_client as client
 from civiclab.e02 import exploratory_live_client_v1 as phase_module
 from civiclab.production_admission_v4 import _Credential
 from civiclab.common import canonical_hash,canonical_bytes
 from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
 epoch=datetime(2026,11,18,4,10,tzinfo=__import__('datetime').timezone.utc);mono0=time.monotonic()
 now=lambda:epoch+timedelta(seconds=time.monotonic()-mono0)
 # MOCK-only fresh lease of captured semantic terms, not a redated observation.
 packet={'kind':'WRAPPER_SLOT46_PACKET_V2','owner_id':q['owner_id'],
         'parent_key':pure.identity(q['owner_id']),'expected_head':head['value'],
         'parent_binding':owner_module.ANCHOR,'run_id':'AUTHORED_SLOT46_'+mode,
         'valid_from_utc':epoch.isoformat(),'valid_until_utc':(epoch+timedelta(seconds=900)).isoformat(),
         'bounds':pure.BOUNDS,'code_hash':canonical_hash(pure.contract())}
 packet['price_release']={r:pure.lease_preserved_semantics(q['price_release'][r],expected_release_hash=canonical_hash(q['price_release'][r]),valid_from=packet['valid_from_utc'],valid_until=packet['valid_until_utc']) for r in ('A','B')}
 packet['authority']={'kind':pure.AUTHORITY,'scope_hash':canonical_hash(packet)}
 packet['review']={'kind':'INDEPENDENT_WRAPPER_SLOT46_REVIEW_V2','reviewer_role':'independent_auditor','review_id':'a'*32,'inputs_hash':canonical_hash(packet)}
 release={'kind':'LEAD_WRAPPER_SLOT46_RELEASE_V2','packet_sha256':canonical_hash(packet),'code_hash':packet['code_hash'],'review_sha256':canonical_hash(packet['review']),'maximum_POSTs':1,'scope':'ORIGINAL46_ONLY_NOT_FULL80'}
 scope=tmp/'MOCK_PACKET_NOT_LIVE_RELEASE';scope.mkdir()
 for name,value in [('packet.json',packet),('lead-release.json',release)]:
  (scope/name).write_bytes(canonical_bytes(value))
  add('writes',len(canonical_bytes(value)))
 entrypath=ROOT/'scripts/launch_e02_slot46_v2_20261118.py'
 entry_ns={'__name__':'_whole_entry_mock','__file__':str(entrypath)};exec(compile(read(entrypath),str(entrypath),'exec'),entry_ns)
 entry_ns['SCOPE']=scope
 calls={'inert_key_boundary':0,'POST':0,'statistics_GET':0,'catalog_GET':0};verify_metrics=[]
 assert mode=='failure'
 original_error=_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',429)
 close_calls=[]
 original_close=client._Journal.close
 def close_then_error(self):
  close_calls.append(1);original_close(self);raise OSError('AUTHORED_CLOSE_ERROR_NOT_PRIMARY')
 class Transport:
  def post_bytes(self,raw):
   calls['POST']+=1
   payload=json.loads(raw)
   assert payload['model']=='qwen/qwen3-30b-a3b-instruct-2507'
   if mode!='success':raise original_error
   return {'id':'gen-slot46-authored-only','model':payload['model'],
    'choices':[{'message':{'content':json.dumps({'democratic_party':50,'republican_party':50,'policy_support':50,'factual_answer':'INCREASE_40'})}}],
    'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150,'cost':0.00001}}
  def statistics(self,generation):
   calls['statistics_GET']+=1
   if calls['statistics_GET']<3:raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
   return {'data':{'id':generation,'model':'qwen/qwen3-30b-a3b-instruct-2507','provider_name':'Nebius','total_cost':0.00001,'native_tokens_prompt':100,'native_tokens_completion':50,'native_tokens_reasoning':0,'is_byok':False,'service_tier':None,'streamed':False,'cancelled':False}}
 def catalog(model):
  calls['catalog_GET']+=1;role='A' if model=='openai/gpt-4.1-nano' else 'B';record=catalogs[role];raw=record['body_utf8'].encode()
  return raw,{'url':record['metadata']['url'],'body_sha256':sha(raw),'observed_at_utc':now().isoformat()}
 def credential():
  assert resource.getrlimit(resource.RLIMIT_CPU)==(120,125) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
  assert 0<signal.getitimer(signal.ITIMER_REAL)[0]<=240
  calls['inert_key_boundary']+=1;return _Credential('AUTHORED_ONLY_NOT_A_REAL_KEY')
 entry_ns['_credential']=credential;entry_ns['_make_transport']=lambda _:Transport();entry_ns['_catalog']=catalog
 original_execute=client.execute
 def explicit_mock(*a,**kw):
  assert kw['provenance']=='EXPLORATORY_REAL_MODEL'
  kw['provenance']='MOCK';kw['gate']=client.OperationGate(packet,now=now)
  return original_execute(*a,**kw)
 old_argv=sys.argv;sys.argv=[str(entrypath),'--packet-sha256',sha(canonical_bytes(packet)),'--release-sha256',sha(canonical_bytes(release))]
 # Physical file hashes and canonical hashes coincide for authored controls.
 old_verify=owner_module.Slot46OwnerV2._verify
 marker=owner_dir/'limited-pilot-v1'/packet['run_id']/'failure-initial-v1.json'
 def measured(self,db):
  t=time.monotonic();u=resource.getrusage(resource.RUSAGE_SELF);visible=marker.is_file()
  try:return old_verify(self,db)
  finally:
   end=resource.getrusage(resource.RUSAGE_SELF);verify_metrics.append({'CPU_seconds':end.ru_utime+end.ru_stime-u.ru_utime-u.ru_stime,'wall_seconds':time.monotonic()-t,'failure_marker_visible':visible})
 LAST_STAGE='EXACT_MAIN';result=None;seen=None
 main_start=time.monotonic();main_cpu=resource.getrusage(resource.RUSAGE_SELF)
 with patch.object(production,'production_owner_directory',return_value=owner_dir),patch.object(production,'_utc_now',side_effect=now),patch.object(phase_module,'new_operation_time',side_effect=now),patch.object(client,'execute',side_effect=explicit_mock),patch.object(owner_module.Slot46OwnerV2,'_verify',measured),patch.object(client._Journal,'close',close_then_error):
  try:result=entry_ns['main']()
  except BaseException as error:seen=error
  finally:sys.argv=old_argv
  main_end=resource.getrusage(resource.RUSAGE_SELF);main_wall=time.monotonic()-main_start
  main_CPU=main_end.ru_utime+main_end.ru_stime-main_cpu.ru_utime-main_cpu.ru_stime
  assert signal.getitimer(signal.ITIMER_REAL)[0]==0
  # Full normal terminal readback belongs to qualification, not a seeded verifier.
  owner=owner_module.Slot46OwnerV2()
  with owner._lock(),owner._connect() as db:state,checked_head=owner._verify(db)
  branch=state[owner_module.STATE];row=state['rows'][branch['receipt']]
  oldrows={k:state['rows'][k] for k in branch['old_ids']}
  assert canonical_hash(oldrows)==owner_module.ANCHOR['rows']
  assert len(oldrows)==195 and len(state['rows'])==196 and branch['closed'] is True
  holds={k:canonical_hash(v) for k,v in oldrows.items() if v['status']!='PHASE_COMMITTED'}
  assert len(holds)==6 and canonical_hash(holds)==owner_module.ANCHOR['protected']
  assert state['wrapper_crossmodel_canary_v1']['closed'] is True and state['wrapper_crossmodel']['stopped'] is True
  assert calls['inert_key_boundary']==1 and calls['POST']==1 and calls['catalog_GET']==2
  if mode=='success':
   assert seen is None and result['response_provenance']=='MOCK' and result['records'][0]['execution_order']==46
   assert row['status']=='PHASE_COMMITTED' and state['unfinished']==6 and state['consumed']['total']==17162 and calls['statistics_GET']==3
  else:
   assert seen is original_error and result is None and calls['statistics_GET']==0
   assert row['status']=='UNCERTAIN' and row['charged']==row['reserved'] and state['unfinished']==7 and state['consumed']['total']==17152+row['reserved']
   diagnostic=json.loads(marker.read_bytes());assert diagnostic['response_provenance']=='MOCK'
   assert diagnostic['error_kind']=='SAFE_TRANSPORT_FAILURE' and diagnostic['http_status']==429
   assert len(close_calls)==1
   finalization=json.loads((marker.parent/'journal-finalization-failure-v2.json').read_bytes())
   assert finalization=={'kind':'JOURNAL_FINALIZATION_FAILED_V2','original_error_preserved':True,'retry_allowed':False}
   assert any(v['failure_marker_visible'] for v in verify_metrics)
 LAST_STAGE='PRESERVE_INPUTS'
 assert all(sha(read(path))==digest for path,digest in before_pins.items())
 summary={'kind':'E02_SLOT46_V2_WHOLE_ENTRY_MOCK_QUALIFICATION','status':'PASS_OFFLINE','mode':mode,'runtime':sys.version.split()[0],
          'fixture':'EXACT_CAPTURE_1189_EVENTS_195_ROWS_6_HOLDS','calls':calls,'main_CPU_seconds':main_CPU,'main_wall_seconds':main_wall,
          'all_main_resource_limits_real':True,'main_includes':'Exact new saved-key entry main, packet/code/review/lead admission, normal constructor, inert credential boundary, normal client and finalization',
          'mocks':'Copied namespace; real-elapsed authored UTC; inert key/HTTP/catalog; explicit MOCK provenance only. Actual fixed10second statistics waits retained.',
          'terminal_status':row['status'],'terminal_unfinished':state['unfinished'],'terminal_conservative_exposure_microusd':state['consumed']['total'],
          'old195rows_and6holds_unchanged':True,'actual_capture_unchanged':True,'verify_metrics':verify_metrics,'charged_logical_bytes':M,
          'current_owner_access':0,'actual_key_reads':0,'network_calls':0,'actual_model_requests':0,'cost_usd':0,
          'original_failure_cause':'UNKNOWN','live_release':False,'authored_primary_error':'SAFE_HTTP_429','owned_journal_close_attempts':len(close_calls),'owned_close_error_preserves_primary':seen is original_error,'finalization_marker':finalization,'whole_child_startup_CPU_separately_reported':True}
 LAST_STAGE='CLEANUP';sqlite3.connect=actual_connect;temp.cleanup();summary['private_fixture_removed']=not tmp.exists()
 u=resource.getrusage(resource.RUSAGE_SELF);summary['whole_child_CPU_seconds']=u.ru_utime+u.ru_stime;summary['whole_child_wall_seconds']=time.monotonic()-started
 text=json.dumps(summary,sort_keys=True);add('console',len(text.encode()));print(text)
 return 0


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=['success','failure','cancel'],required=True);args=parser.parse_args()
 try:raise SystemExit(main(args.mode))
 except SystemExit:raise
 except BaseException as error:
  removed=False
  if QUALIFY_TEMP is not None:
   try:shutil.rmtree(QUALIFY_TEMP);removed=not QUALIFY_TEMP.exists()
   except BaseException:pass
  frames=[];tb=error.__traceback__
  while tb is not None and len(frames)<16:
   frames.append({'file':Path(tb.tb_frame.f_code.co_filename).name,'line':tb.tb_lineno,'function':tb.tb_frame.f_code.co_name});tb=tb.tb_next
  print(json.dumps({'safe_frames_no_locals_or_error_text':frames,'kind':'E02_SLOT46_V2_WHOLE_ENTRY_MOCK_QUALIFICATION','status':'FAILED_OFFLINE_NO_RETRY','stage':LAST_STAGE,'private_fixture_removed':removed,'error_type':type(error).__name__ if any(type(error) is c for c in (RuntimeError,ValueError,TypeError,AssertionError,OSError)) else 'OTHER','charged_logical_bytes':M,'actual_model_requests':0,'network_calls':0},sort_keys=True));raise SystemExit(1)
