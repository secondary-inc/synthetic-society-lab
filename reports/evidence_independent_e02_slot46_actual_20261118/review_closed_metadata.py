"""Direct bounded closed metadata/hash-chain review; no policy reducer replay."""
from pathlib import Path
import json,sqlite3,hashlib,signal,resource,sys,time
resource.setrlimit(resource.RLIMIT_CPU,(119,120));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(120)
root=Path.cwd();start=time.monotonic();used=0
cap=root/'data/processed/e02_wrapper_slot46_v2_20261118_actual_01/closed-capture-03';old=root/'data/processed/e02_wrapper_crossmodel_canary_v1_20261117_actual_01/stop-capture-01'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def charge(n):
 global used
 used+=n;assert used<=134217728
allowed={cap/'owner-v4.local.sqlite',old/'owner-v4.local.sqlite'}
def audit(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','ctypes.dlopen'):raise RuntimeError('NO_NETWORK_PROCESS')
 if event=='sqlite3.connect':assert Path(str(args[0]).removeprefix('file:').split('?')[0]) in allowed
sys.addaudithook(audit)
def read(p):
 assert p.is_file() and not p.is_symlink();raw=p.read_bytes();charge(len(raw));return raw
manifest_raw=read(cap/'manifest.local.json');manifest=json.loads(manifest_raw);data={}
for ref in manifest['files']:
 p=cap/ref['name'];assert p.is_relative_to(cap) and '..' not in p.parts
 raw=read(p);assert len(raw)==ref['bytes'] and sha(raw)==ref['sha256'];data[ref['name']]=raw
summary=json.loads(data['summary.local.json']);state=json.loads(data['verified-state.local.json']);head=json.loads(data['verified-head.local.json']);anchor=json.loads(data['owner-v4-head.local.json']);b=state['wrapper_crossmodel_slot46_v2']
public=json.loads(read(root/'reports/E02_SLOT46_ACTUAL_CLOSED_OUTCOME_V1_1_20261118.json'));checks={'all12_pins':len(data)==12,'public_exact':summary==public}
oldmanifest=json.loads(read(old/'manifest.local.json'));old_dbref=next(r for r in oldmanifest['refs'] if r['path'].endswith('/owner-v4.local.sqlite'));assert sha(read(old/'owner-v4.local.sqlite'))==old_dbref['sha256']
def sql(path):
 charge(path.stat().st_size)
 with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:rows=db.execute('SELECT sequence,data,digest FROM events ORDER BY sequence').fetchall()
 charge(sum(len(row[1].encode())+len(row[2])+8 for row in rows));return rows
oldrows=sql(old/'owner-v4.local.sqlite');rows=sql(cap/'owner-v4.local.sqlite');checks['1192_events']=len(rows)==1192;checks['1189_prefix_exact']=len(oldrows)==1189 and rows[:1189]==oldrows
previous='0'*64
for i,(sequence,raw,digest) in enumerate(rows):
 event=json.loads(raw)
 assert sequence==i==event['sequence'] and event['previous']==previous and sha(canonical(event))==digest
 previous=digest
checks['all_event_hashes_and_links']=True
checks['head_binding']=head['head_hash']==anchor['head_hash']==previous and head['sequence']==anchor['sequence']==1191
new=[json.loads(raw)['body'] for _,raw,_ in rows[1189:]];checks['three_exact_events']=[e['kind'] for e in new]==['WRAPPER_SLOT46_OPEN_V2','WRAPPER_SLOT46_IO_V2','WRAPPER_SLOT46_CLOSE_V2']
checks['one_catalog_A_intent']=new[1]['payload']=={'channel':'catalog_GET','unit':'A'}
checks['no_reservation_or_POST_or_statistics']=b['counts']=={'POST':0,'catalog_GET':1,'statistics_GET':0} and b['receipt'] is None and b['witness'] is None
checks['closed_failed']=b['closed'] is True and new[-1]['payload']=={'reason':'FAILED'}
checks['old195rows_exact']=len(state['rows'])==195 and sha(canonical(state['rows']))=='b3391e7ec1b901df17185c3bd33984f31b109dc050a34f09cbb7edabfb09ec63'
holds={k:sha(canonical(v)) for k,v in state['rows'].items() if v['status']!='PHASE_COMMITTED'}
checks['six_holds_exact']=len(holds)==state['unfinished']==6 and sha(canonical(holds))=='ac7ae7d73e02f8c1e2edb2624a7d81a058db22142f55838456e8f1de15e8efb6'
checks['exposure17152']=state['consumed']['total']==17152 and state['consumed']['modules']=={'E01':0,'E02':17152}
failure=json.loads(data['journal/failure-initial-v1.json']);checks['safe_initial_catalog_A_failure']=failure['stage']=='CATALOG_A' and failure['retry_allowed'] is False and failure['dispatch_generation_billing']=='NOT_ATTESTED_BY_THIS_MARKER'
checks['no_catalog_body_response_request_or_dispatch_artifact']=set(k for k in data if k.startswith('journal/'))=={'journal/failure-initial-v1.json','journal/failure.json','journal/packet.json','journal/retention.json','journal/run.lock'}
checks['exact_reviewed_packet']=sha(data['journal/packet.json'])=='ce3888cbff40d401b778e40f3877b187067bbf70c3237a01baca43c977483d6d'
assert all(checks.values()),[k for k,v in checks.items() if not v]
assert read(cap/'manifest.local.json')==manifest_raw
for ref in manifest['files']:assert sha(read(cap/ref['name']))==ref['sha256']
print(json.dumps({'kind':'INDEPENDENT_SLOT46_DIRECT_CLOSED_OUTCOME','status':'PASS_SCOPED','checks':checks,'capture_manifest_bytes':len(manifest_raw),'capture_manifest_sha256':sha(manifest_raw),'new_events':new[1:],'initial_failure':failure,'read_bytes':used,'wall_seconds':time.monotonic()-start,'CPU_seconds':sum(resource.getrusage(resource.RUSAGE_SELF)[:2]),'normal_reducer_replay':'REVIEWER_GUARD_REFUSAL_SEPARATELY_PRESERVED','physical_GET':'NOT_PROVEN_BY_INTENT','actual_owner_key_network_model_access':0,'cost_usd':0},sort_keys=True));signal.alarm(0)
