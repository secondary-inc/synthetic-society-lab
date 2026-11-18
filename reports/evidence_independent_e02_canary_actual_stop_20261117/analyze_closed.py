"""Bounded read-only closed-copy audit; no project code import or reducer execution."""
from pathlib import Path
import json,hashlib,sqlite3,resource,signal,time
resource.setrlimit(resource.RLIMIT_CPU,(120,120));signal.alarm(180)
root=Path.cwd();base=root/'data/processed/e02_wrapper_crossmodel_canary_v1_20261117_actual_01/stop-capture-01';out=root/'reports/evidence_independent_e02_canary_actual_stop_20261117';t=time.monotonic();reads=0;checks={}
def read(p):
 global reads
 b=p.read_bytes();reads+=len(b);assert reads<=536870912;return b
def load(p):return json.loads(read(p))
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def check(k,v):checks[k]=bool(v)
m=load(base/'manifest.local.json')
for r in m['refs']:
 b=read(root/r['path']);check('pin:'+Path(r['path']).name,len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'])
oldpath=root/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/post-run-owner-export.local.json';oldraw=read(oldpath);assert len(oldraw)==3893676 and hashlib.sha256(oldraw).hexdigest()=='ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66';old=json.loads(oldraw)
parsed=load(base/'parsed-rows.local.json');rawsql=load(base/'sql-rows.local.json');head=load(base/'owner-v4-head.local.json');guard=load(base/'owner-v4-guard.local.json')
# Immutable/query-only connection to the captured database only.
con=sqlite3.connect('file:'+str(base/'owner-v4.local.sqlite')+'?mode=ro&immutable=1',uri=True);con.execute('PRAGMA query_only=ON')
headers=con.execute('SELECT data FROM header').fetchall();events=con.execute('SELECT sequence,data,digest FROM events ORDER BY sequence').fetchall();charges=con.execute('SELECT id,data FROM charges ORDER BY id').fetchall();con.close();reads+=4956160
history=[json.loads(v) for _,v,_ in events];rows={k:json.loads(v) for k,v in charges}
check('capture_export_matches_sql_headers',[json.loads(v[0]) for v in headers]==parsed['header'])
check('capture_export_matches_sql_history',history==parsed['history']);check('capture_export_matches_sql_rows',rows==parsed['rows'])
check('raw_sql_matches_database',rawsql=={'header':[list(r) for r in headers],'events':[list(r) for r in events],'charges':[list(r) for r in charges]})
previous=None;chain=True
for i,(seq,s,h) in enumerate(events):
 e=json.loads(s);chain &= seq==i and e['sequence']==i and e['previous']==previous and digest(e)==h;previous=h
check('full_event_hash_chain',chain)
check('head_joins_final_event',head['head_hash']==previous and head['sequence']==1188 and head['header_sha256']==digest(guard))
check('old_header_unchanged',old['header']==guard==parsed['header'][0]);check('old_1180_events_unchanged',history[:1180]==old['history'])
check('old_194_rows_unchanged',len(old['rows'])==194 and all(rows.get(k)==v for k,v in old['rows'].items()))
check('packet_joins_old_head',load(base/'journal/packet.json')['expected_head']==old['head'])
newids=set(rows)-set(old['rows']);check('exactly_one_new_row',len(newids)==1 and len(rows)==195)
row=rows[next(iter(newids))];rid=next(iter(newids));new=history[1180:]
check('new_events_exact_order',[e['body']['kind'] for e in new]==m['new_event_kinds'])
check('full_hold_retained',row['status']=='UNCERTAIN' and row['reserved']==row['charged']==1003 and row['observed_cost'] is None and row['generation_id'] is None and row['billing'] is None)
newrowevent=[e['body']['payload']['after'] for e in new if e['body']['kind'] in ('RESERVE','TRANSITION')]
check('new_row_materialization_matches_last_transition',len(newrowevent)==2 and newrowevent[-1]==row)
check('reserve_no_prior_and_transition_bound',new[5]['body']['payload']['before_hash'] is None and new[7]['body']['payload']['before_hash']==digest(newrowevent[0]))
check('old_five_holds_unchanged',sorted(v['charged'] for v in old['rows'].values() if v['status']!='PHASE_COMMITTED')==[340,340,775,788,1008])
request=load(base/'journal'/f'{rid}-request.json');dispatch=load(base/'journal'/f'{rid}-dispatch.json')
check('request_receipt_context_joins',request['receipt']==dispatch['receipt']==rid and request['context']==row['context'] and dispatch['context_hash']==digest(row['context']))
check('payload_hash_joins',dispatch['payload_sha256']==request['request']['payload_sha256']==digest(request['request']['payload'])==row['context']['payload_hash'])
check('request_head_dispatch_head_equal',request['head']==dispatch['head'])
check('dispatch_intent_only',dispatch['status']=='ACKNOWLEDGED_POST_INTENT_CONSUMED')
io=[e['body']['payload'] for e in new if e['body']['kind']=='WRAPPER_CANARY_IO_V1']
check('io_intents_two_catalog_one_post_no_statistics',[v['phase'] for v in io]==['CATALOG_A','CATALOG_B','POST'])
check('no_response_statistics_or_success_file',not any('response' in p.name or 'statistics' in p.name or p.name=='summary.json' for p in (base/'journal').iterdir()))
check('all_prior_generation_and_billing_fields_unchanged',all(rows[k]['generation_id']==v['generation_id'] and rows[k]['billing']==v['billing'] for k,v in old['rows'].items()))
exposure_old=sum(v['charged'] for v in old['rows'].values());exposure_new=sum(v['charged'] for v in rows.values())
check('conservative_exposure_16149_to_17152',exposure_old==16149 and exposure_new==17152)
# Independent finite clock join, not a full policy-reducer verification.
prior=None;clock=True
from datetime import datetime
for e in history:
 b=e['body'];stamp=b['recorded_at_utc'];clock &= b['prior_clock_max_utc']==(prior.isoformat() if prior else None)
 if stamp is not None:
  dt=datetime.fromisoformat(stamp);prior=max(prior,dt) if prior else dt
check('prior_clock_chain',clock)
summary={'kind':'INDEPENDENT_CLOSED_STOP_EVIDENCE_ANALYSIS','invocation':2,'checks':checks,'all_checks_pass':all(checks.values()),'event_count':len(history),'row_count':len(rows),'new_event_metadata':[{'kind':e['body']['kind'],'recorded_at_utc':e['body']['recorded_at_utc'],'payload_keys':list(e['body']['payload'])} for e in new],'new_row_status':row['status'],'new_row_error_type':row.get('error_type'),'old_conservative_exposure_microusd':exposure_old,'new_conservative_exposure_microusd':exposure_new,'verified_new_responses':0,'new_provider_charge':'UNKNOWN','dispatch_HTTP_completion':'UNKNOWN','earlier_exception':'UNKNOWN','normal_reducer_replay':'NOT_RUN','logical_read_bytes':reads,'wall_seconds':time.monotonic()-t,'current_owner_reads':0,'network_calls':0,'key_reads':0,'financial_writes':0}
(out/'CLOSED_ANALYSIS.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,sort_keys=True))
