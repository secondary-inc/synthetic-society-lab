"""One bounded stdlib/static CLOSED stop diagnosis. No owner/model import."""
import ast,hashlib,json,os,resource,signal,sqlite3,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
CAPTURE=ROOT/'data/processed/e02_wrapper_crossmodel_canary_v1_20261117_actual_01/stop-capture-01'
MANIFEST=CAPTURE/'manifest.local.json'
OUT=ROOT/'reports/E02_CANARY_STOP_SOURCE_DIAGNOSIS_20261117.json'
LIMIT=134217728
used=4533  # Earlier manifest-only schema preflight, explicitly included.
writes=0;pins=[];start=time.monotonic()
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60))
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(RuntimeError('DIAGNOSIS120SECONDS')));signal.alarm(120)
canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
sha=lambda v:hashlib.sha256(v).hexdigest()
def safe(path):
 if not path.is_absolute() or '..' in path.parts or any(p.is_symlink() for p in (path,*path.parents)):raise RuntimeError('DIAGNOSIS_ALIAS_OR_TRAVERSAL')
 return path
def read(path,pin=None,label=None):
 global used
 safe(path)
 allowed=path.is_relative_to(CAPTURE) or path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts') or path==ROOT/'reports/STATUS.md' or path==ROOT/'reports/E02_CANARY_INHERITED_MOCK_V1_CODE_HANDOFF_20261117.json'
 if not allowed:raise RuntimeError('DIAGNOSIS_CLOSED_OR_FROZEN_SOURCE_ONLY')
 n=path.stat().st_size
 if used+n>LIMIT:raise RuntimeError('DIAGNOSIS128MIB')
 if pin and n!=pin['bytes']:raise RuntimeError('CLOSED_SIZE_MISMATCH')
 used+=n;raw=path.read_bytes()
 if len(raw)!=n or pin and sha(raw)!=pin['sha256']:raise RuntimeError('CLOSED_HASH_MISMATCH')
 pins.append({'label':label or str(path.relative_to(ROOT)),'bytes':n,'sha256':sha(raw)})
 return raw
manifest=json.loads(read(MANIFEST,{'bytes':4533,'sha256':'4cc86b9df8c149923eafc3fd8641c1445555f30b1e806045ca9a9f40883d8481'}))
# Manifest reference metadata names are never written to public output if they
# contain private receipt/generation identities. Join by ordinal and SHA instead.
pool=[]
def walk(directory):
 for path in directory.iterdir():
  safe(path)
  if path.is_dir():walk(path)
  elif path.is_file():pool.append(path)
  else:raise RuntimeError('NONREGULAR_CAPTURE_ENTRY')
  if len(pool)>64:raise RuntimeError('CAPTURE_FILE_COUNT')
walk(CAPTURE)
refs=manifest['refs'];items=list(refs.items()) if isinstance(refs,dict) else [(None,v) for v in refs]
loaded=[]
for index,(key,item) in enumerate(items):
 if not isinstance(item,dict):raise RuntimeError('CLOSED_REF_SCHEMA')
 metadata=item.get('ref',item)
 if not isinstance(metadata,dict):raise RuntimeError('CLOSED_REF_METADATA')
 pin={'bytes':metadata.get('bytes',metadata.get('size_bytes')),'sha256':metadata.get('sha256')}
 if type(pin['bytes']) is not int or type(pin['sha256']) is not str:raise RuntimeError('CLOSED_REF_PIN_REQUIRED')
 candidates=[metadata.get(n) for n in ('path','closed_path','captured_path','copy_path','relative_path','filename','name')]+[key]
 choices=[]
 for name in candidates:
  if not isinstance(name,str):continue
  p=Path(name)
  for q in ([p] if p.is_absolute() else [ROOT/p,CAPTURE/p]):
   if q.is_relative_to(CAPTURE) and '..' not in q.parts and q in pool:choices.append(q)
  if not choices:
   matches=[q for q in pool if q.name==p.name]
   if len(matches)==1:choices+=matches
  if choices:break
 if len(set(choices))!=1:raise RuntimeError('CLOSED_REF_NO_UNIQUE_CAPTURE_MATCH')
 path=choices[0];raw=read(path,pin,label='capture-ref-'+str(index))
 role=('sqlite_snapshot' if raw.startswith(b'SQLite format 3\x00') else 'new_dispatch' if path.name.endswith('-dispatch.json') else 'new_request' if path.name.endswith('-request.json') else path.name if len(path.name)<30 and not path.name.startswith('gen-') else 'other_closed_json')
 value=None
 if raw[:1] in (b'{',b'['):value=json.loads(raw)
 loaded.append({'index':index,'path':path,'raw':raw,'json':value,'role':role,'pin':pins[-1]})
databases=[q for q in loaded if q['role']=='sqlite_snapshot']
if len(databases)!=1:raise RuntimeError('ONE_CAPTURE_SQLITE_REQUIRED')
db_path=databases[0]['path'];used+=db_path.stat().st_size
if used>LIMIT:raise RuntimeError('DIAGNOSIS_SQL_NATIVE_READ_LIMIT')
with sqlite3.connect(db_path.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
 db.execute('PRAGMA query_only=ON')
 eventrows=db.execute('SELECT sequence,data,digest FROM events ORDER BY sequence LIMIT 1190').fetchall()
 chargerows=db.execute('SELECT id,data FROM charges LIMIT 196').fetchall()
 headerrows=db.execute('SELECT data FROM header LIMIT 2').fetchall()
 used+=sum(len(x.encode()) if isinstance(x,str) else 8 for row in eventrows+chargerows+headerrows for x in row)
if used>LIMIT:raise RuntimeError('DIAGNOSIS_SQL_LOGICAL_READ_LIMIT')
if len(eventrows)!=1189 or len(chargerows)!=195 or len(headerrows)!=1:raise RuntimeError('CAPTURE_COUNTS')
header=json.loads(headerrows[0][0]);events=[];previous=None
for i,(seq,data,digest_) in enumerate(eventrows):
 event=json.loads(data)
 if seq!=i or event['sequence']!=i or event['previous']!=previous or sha(canon(event))!=digest_:raise RuntimeError('CLOSED_CHAIN_MISMATCH')
 previous=digest_;events.append(event)
rows={key:json.loads(data) for key,data in chargerows}
new=events[1180:];kinds=[e['body']['kind'] for e in new]
expected=['WRAPPER_CANARY_OPEN_V1','WRAPPER_CANARY_IO_V1','WRAPPER_CANARY_IO_V1','WRAPPER_CANARY_PROOFS_V1','WRAPPER_CANARY_GRANT_V1','RESERVE','WRAPPER_CANARY_IO_V1','TRANSITION','WRAPPER_CANARY_CLOSE_V1']
if kinds!=expected:raise RuntimeError('NEW_KIND_SEQUENCE')
# Structural after/before projection only; no owner validators/reducer run.
projection={};old_projection=None;before_join=True
for i,event in enumerate(events):
 body=event['body'];payload=body['payload']
 if isinstance(payload.get('after'),dict) and 'id' in payload['after']:
  row=payload['after'];prior=projection.get(row['id'])
  before_join=before_join and payload.get('before_hash')==(sha(canon(prior)) if prior is not None else None)
  projection[row['id']]=row
 if i==1179:old_projection=dict(projection)
new_ids=set(rows)-set(old_projection)
if len(new_ids)!=1:raise RuntimeError('ONE_NEW_ROW')
new_id=next(iter(new_ids));row=rows[new_id]
packet=new[0]['body']['payload']['packet']
ack=new[4]['body']['payload']['ack']
json_records=[q for q in loaded if isinstance(q['json'],dict)]
heads=[q for q in json_records if set(q['json'])=={'namespace','owner_id','header_sha256','sequence','head_hash'}]
head_match=bool(heads) and heads[0]['json']=={'namespace':header['namespace'],'owner_id':header['owner_id'],'header_sha256':sha(canon(header)),'sequence':1188,'head_hash':previous}
request=[q for q in loaded if q['role']=='new_request'];dispatch=[q for q in loaded if q['role']=='new_dispatch']
if len(request)!=1 or len(dispatch)!=1:raise RuntimeError('CLOSED_REQUEST_DISPATCH_REQUIRED')
req=request[0]['json'];dispatch_value=dispatch[0]['json']
request_join=bool(req['receipt']==new_id and req['context']==row['context'] and sha(canon(req['request']['payload']))==row['context']['payload_hash'])
dispatch_join=bool(dispatch_value['receipt']==new_id and dispatch_value['context_hash']==sha(canon(row['context'])) and dispatch_value['payload_sha256']==row['context']['payload_hash'])
anchor_node=None;sources={};source_pins=[]
source_paths=['scripts/continue_e02_wrapper_crossmodel_canary_v1_20261117.py','src/civiclab/e02/wrapper_crossmodel_canary_v1_client.py','src/civiclab/e02/wrapper_crossmodel_canary_v1_owner.py','src/civiclab/e02/exploratory_live_client_v1.py','src/civiclab/e02/exploratory_owner_v1.py','src/civiclab/production_owner_v4.py','src/civiclab/production_compatibility_transport_v4_2.py','src/civiclab/production_admission_v4.py','src/civiclab/openrouter_http_v2.py','src/civiclab/common.py']
source_paths += [str(p.relative_to(ROOT)) for p in (ROOT/'scripts').iterdir() if p.suffix=='.py' and 'canary' in p.name and any(t in p.name for t in ('saved','key'))]
for name in source_paths:
 raw=read(ROOT/name);source_pins.append(pins[-1]);text=raw.decode();tree=ast.parse(text);sources[name]={'text':text,'tree':tree}
 if name.endswith('wrapper_crossmodel_canary_v1_owner.py'):
  anchor_node=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ANCHOR' for t in n.targets))
anchor=ast.literal_eval(anchor_node)
old_rows_unchanged=bool(old_projection and len(old_projection)==194 and {k:rows[k] for k in old_projection}==old_projection and sha(canon(old_projection))==anchor['rows'])
signal_assignments=[]
for name,source in sources.items():
 for call in ast.walk(source['tree']):
  if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr in ('signal','setrlimit','setitimer'):
   signal_assignments.append({'source':name,'line':call.lineno,'expression':ast.unparse(call)})
no_source_SIGXCPU_handler=not any('SIGXCPU' in x['expression'] for x in signal_assignments)
def utc(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
opened=utc(new[0]['body']['recorded_at_utc']);phase=utc(new[4]['body']['recorded_at_utc'])
timeline=[]
for event in new:
 b=event['body'];at=utc(b['recorded_at_utc']);timeline.append({'kind':b['kind'],'recorded_at_UTC':b['recorded_at_utc'],'seconds_after_OPEN':(at-opened).total_seconds(),'seconds_after_GRANT':(at-phase).total_seconds(),'clock_status':b.get('clock_status'),'IO_phase':b['payload'].get('phase') if b['kind']=='WRAPPER_CANARY_IO_V1' else None})
prior_handoff=json.loads(read(ROOT/'reports/E02_CANARY_INHERITED_MOCK_V1_CODE_HANDOFF_20261117.json'))
mock_measured=[{'runtime':r['execution']['runtime'],'attempt':r['execution']['attempt'],'positive':{k:v for k,v in r['summary']['observations'][0].items() if k in ('operation_CPU_seconds','operation_wall_seconds','phase_wall_seconds','fixed10second_billing_visibility_wait')}} for r in prior_handoff['TESTS_RUN_AND_RESULTS']['runs'] if r['execution']['attempt']==2]
status_context_pin=sha(read(ROOT/'reports/STATUS.md'))
charged=sum(r['charged'] for r in rows.values() if type(r['charged']) is int)
unfinished=[r for r in rows.values() if r['status']!='PHASE_COMMITTED']
missing_names={'failure_json':not any(q['path'].name=='failure.json' for q in loaded),'response_json':not any(q['path'].name.endswith('-response.json') for q in loaded),'statistics_json':not any(q['path'].name.endswith('-statistics.json') for q in loaded),'checkpoint_json':not any(q['path'].name.endswith('-checkpoint.json') for q in loaded),'summary_json':not any(q['path'].name=='summary.json' for q in loaded)}
report={
'TASK_ID':'E02_CANARY_STOP_SOURCE_DIAGNOSIS_20261117',
'kind':'CLOSED_COPY_STATIC_SOURCE_DIAGNOSIS_NOT_OWNER_REPLAY_OR_NEW_EXECUTION',
'recorded_at_UTC':datetime.now(timezone.utc).isoformat(),
'decision':'CAUGHT_CLIENT_FAILURE_THEN_NATIVE_CPU_STOP_SUPPORTED_HTTP_ENTRY_AND_INITIAL_ERROR_UNKNOWN',
'capture_manifest':{'path':str(MANIFEST.relative_to(ROOT)),'bytes':4533,'sha256':'4cc86b9df8c149923eafc3fd8641c1445555f30b1e806045ca9a9f40883d8481'},
'root_terminal_observation_not_rerun':{'source':'Root instruction for exact candidate02 at0ae4d85','exit':152,'reported_signal':'SIGXCPU','stdout_bytes':0,'stderr_bytes':0,'source_note':'This diagnosis does not reproduce process exit or infer an HTTP error from shell status.'},
'closed_checks':{'events':len(events),'rows':len(rows),'complete_hash_chain':True,'head_anchor_matches_terminal_chain':head_match,'structural_after_projection_matches_materialization':projection==rows,'structural_before_hash_joins':before_join,'original194rows_hash_matches_frozen_parent_and_unchanged':old_rows_unchanged,'new_request_context_payload_join':request_join,'new_dispatch_context_payload_join':dispatch_join,'no_semantic_owner_verification':True},
'new_row_without_identity':{'status':row['status'],'reserved_microusd':row['reserved'],'charged_microusd':row['charged'],'generation_present':row['generation_id'] is not None,'billing_present':row['billing'] is not None,'observed_cost_microusd':row['observed_cost'],'output_hash_present':row['output_hash'] is not None,'checkpoint_hash_present':row['checkpoint_hash'] is not None,'error_type':row['error_type'],'requested_model':row['context']['terms']['model'],'requested_route':row['context']['terms']['requested_route'],'actual_serving_provider':'UNKNOWN_NO_RESPONSE_OR_BILLING'},
'conservative_accounting':{'sum_row_charges_microusd':charged,'unfinished_count':len(unfinished),'unfinished_charges_microusd':sorted(r['charged'] for r in unfinished),'new_actual_charge':'UNKNOWN','new_full_hold_retained':row['charged']==row['reserved']==1003,'new_hold_is_not_actual_invoice':True,'caps_unchanged':True},
'new_event_timeline':timeline,
'closed_artifacts_missing':missing_names,
'what_TRANSITION_and_CLOSE_prove':[
'Given exact frozen client source, new receipt already assigned and its try block entered. A caught exception after reservation caused the client to attempt failure cleanup; successfully recorded UNCERTAIN/CanaryStopped with unknown generation/billing/observed cost is its conservative failure transition. This is not a billing reconciliation or successful model completion.',
'The following CLOSE payload is FAILED. Its recorded publication shows the close event reached storage. A matching head anchors that event if closed_checks.head_anchor_matches_terminal_chain is true; no claim is made that the live owner has been newly verified.',
'Owner append helpers publish database event/row, commit and anchor before mandatory _verify read-back. Thus a durable CLOSE does not prove close_canary returned, read-back completed, failure.json was written, or generic main failure output ran.',
'Original launcher installs CPU soft59/hard60 and wall240 handler, with no SIGXCPU handler in inspected source. Under the reported native SIGXCPU/default-handler interpretation, Python cleanup events precede the native termination and require an earlier caught failure. SIGXCPU alone does not explain which original error caused UNCERTAIN.'],
'HTTP_attempt_localization':{
'durable_intents':'POST IO intent and matching dispatch journal are present. Source _Capability marks used and writes dispatch before a second phase.gate, assigning posts and entering transport.post_bytes only afterward. Treat this allowance as consumed even if transport never started.',
'possible_pre_transport_stop':'The phase gate immediately after durable dispatch may refuse before post_bytes. Dispatch record alone therefore does not establish actual HTTP entry.',
'possible_transport_or_post_return_stop':'If transport began, HTTP/network/decoding/transport validation may have raised; or the client gate/phase after return may have refused before retaining response/observing cost. A response lacking/invalid cost or generation could also fail before a response journal. Source-compatible possibilities, not observed causes.',
'bounded_unknowns':'No retained response/statistics/checkpoint or failure.json identifies error type, HTTP status, provider handling, generation or bill. New row.error_type CanaryStopped is generic. No assertion of another402, successful API call, zero charge, or original parent402 cause.',
'prohibited_inference':'Do not resend originalslot45, re-open aliases, clear1003hold or infer a returned generation from a request hash.'},
'CPU_scope_diagnosis':{
'observed_mock_measurements':mock_measured,
'absolute_process_limit':'RLIMIT_CPU applies cumulative process CPU, not a stopwatch reset at setrlimit. Frozen originalmain sets59/60 after its packet validation. The saved-key bridge also performs admission/key-loading before originalmain; all earlier process CPU remains counted. Prior L03 positive measurement began before normal constructor/client but after fixture creation/import/control construction; it is not whole entry-process CPU.',
'failure_path_work':'Failure handler performs a full canary_snapshot verification, UNCERTAIN transition verification/append read-back and CLOSE verification/append read-back before writing failure.json. These inherited full-history replays consume CPU and can be interrupted after event publication. Prior happy-path timing is not an error-path or all-input CPU upper bound.',
'what_is_not_explained':'Missing per-stage getrusage/monotonic/error record prevents attributing the actual difference to imports, repeated replay, exact live metadata, transport processing or cleanup. No claim any particular component caused59CPU or consumed a computed amount. Mock skipped10s billing wait is wall-time seam and was not reached by this new event prefix; it is not evidence of this CPU cause.',
'likely_interruption_region_inference':'CLOSE published while failure.json and generic stdout are absent is consistent with native CPU stop during CLOSE post-commit verification or following error finalization. This is an inference from ordering, not a localized stack trace.',
'signal_and_limit_source_refs':signal_assignments,'no_inspected_SIGXCPU_handler':no_source_SIGXCPU_handler},
'minimal_future_recovery_proposal':[
{'step':1,'scope':'Keep original attempt stopped and1003 plus all five old holds. Treat generation/billing and physical POST entry unknown. No retry, largerCPUcap, new allowance, new owner or edits to old packet/journal/head.'},
{'step':2,'scope':'Separate bounded closed-copy structural/semantic stop review and, if lead assigns it, one offline profiling qualification using normal inherited verifier, exact captured packet/catalog shapes and inert transport failures at dispatch/pre-response. Record per-stage selfCPU/wall with bounded safe enums; do not call current owner/API or retransmit actualslot45.'},
{'step':3,'scope':'For a separately versioned future client, consider persisting one bounded secret-free original failure diagnostic BEFORE expensive cleanup/read-back (allowlisted error class and trusted HTTP status only), while retaining reservation. Independently test interruption and CPU boundaries before any future release. This is proposal only; production was not edited.'},
{'step':4,'scope':'Unknown generation cannot be reconciled by inventing anID or approximate cost. Any permitted provider-log/account correlation needs separately bounded access and exact identity evidence; otherwise preserve full hold. No authenticated recovery query is proposed as already supported.'},
{'step':5,'scope':'Any future modelwork must be a separately approved never-attempted scope with existing financial and request caps, after evidence/review and measured feasible caller/failure CPU budget. Do not reuse spent45 or silently raise59/60; stop if existing cap cannot be met.'}],
'INPUT_REFS':pins,
'SOURCE_DATA_AND_LICENSE_NOTES':'Only exact captured raw control/journal files and frozen project source/public prior metadata read. Captured owner/receipt/header/request values stayed transient; report contains deidentified technical counts/hashes and source locations only. No currentowner/key/env/publisher/respondent access. Structural projection is not semantic validation.',
'COST_USD_ACTUAL_OR_ZERO':0,
'activity':{'candidate_imports':0,'owner_verifier_calls':0,'current_owner_access':0,'credentials_read':0,'network_calls':0,'model_requests':0,'Git_mutations':0,'production_edits':0},
'UNRESOLVED_BLOCKERS':['Underlying caught error/HTTP status and actual provider dispatch/bill unknown.','Stop semantic acceptance and any future bounded recovery/execution require separate lead assignment/review.','No prospective/humanpersuasion/full80study claim follows.'],
'NEXT_UNBLOCKED_TASK':'Lead/auditor review exact closed diagnosis; preserve all holds and consumed scope. No rerun authorized by this report.'}
report['resource_accounting']={'bounded_diagnosis_invocations':1,'manifest_only_preflight_reads_included':4533,'logical_read_bytes':used,'read_limit_bytes':LIMIT,'wall_seconds':time.monotonic()-start,'CPU_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,'wall_limit_seconds':120,'CPU_limit_seconds':60,'write_limit_bytes':4194304,'console_limit_bytes':65536,'startup_boundary':'Stdlib/interpreter startup not claimed fully metered. Closed file bytes, SQLite native file reservation and returned serialized payloads explicitly charged.'}
blob=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
if len(blob)>4194304 or OUT.exists():raise RuntimeError('DIAGNOSIS_OUTPUT_LIMIT_OR_EXISTS')
OUT.write_bytes(blob)
print(json.dumps({'report':str(OUT.relative_to(ROOT)),'bytes':len(blob),'sha256':sha(blob),'logical_read_bytes':used,'wall_seconds':time.monotonic()-start,'events':1189,'rows':195,'new_row_status':row['status'],'new_hold_microusd':row['charged'],'head_match':head_match,'old_rows_unchanged':old_rows_unchanged,'new_event_timeline':timeline,'missing':missing_names,'closed_journal_role_sizes':[{'role':q['role'],'bytes':len(q['raw'])} for q in loaded if q['role'] in ('new_dispatch','new_request') or q['path'].name.startswith('catalog')],'candidate_imports':0,'API_calls':0},sort_keys=True))
