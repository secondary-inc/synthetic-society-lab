from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent;checks=[];refs={}
def need(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
def read(p):
 q=ROOT/p;need(all(not x.is_symlink() for x in (q,*q.parents)),'no_alias:'+p)
 b=q.read_bytes();refs[p]={'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def js(p):return json.loads(read(p))
a=js('reports/E01_GUARD_DIAGNOSTIC_V2_ACTUAL_20261116.json');need(refs['reports/E01_GUARD_DIAGNOSTIC_V2_ACTUAL_20261116.json']['bytes']==4232 and refs['reports/E01_GUARD_DIAGNOSTIC_V2_ACTUAL_20261116.json']['sha256']=='0ba43cae46a56ff1c08c71d8e3741ebc23db8c310201521f39b116b4cf691e0f','frozen_public_receipt')
for key in ['actual_packet','guest_result','refusal_journal','terminal','particular_review','preflight']:
 r=a[key];b=read(r['path']);need(refs[r['path']]==r,'public_ref:'+key)
t=json.loads(read(a['terminal']['path']));g=json.loads(read(a['guest_result']['path']));j=json.loads(read(a['refusal_journal']['path']))
need(a['status']==t['outcome']=='REFUSAL_OBSERVED' and a['actual_commands_started']==t['commands_started']==1 and a['actual_exit_code']==t['command']['exit_code']==1,'public_outcome_matches')
need(a['recorded_refusal']==j==t['refusals'] and a['guest_guard_violations']==g['guard_violations']==1,'public_refusal_matches')
need(a['MIME_receipt']==g['mime_configuration'] and a['pip_completed_dry_run']==g['pip_completed'] and a['fictional_target_exists']==g['target_exists']==False,'public_guest_matches')
need(a['old_metadata_snapshot']==t['old_metadata_snapshot'] and a['limits_and_usage']['allocation']==t['allocation'],'public_snapshot_allocation_matches')
for k,v in a['limits_and_usage'].items():need(t[k]==v,'public_usage:'+k)
need(a['installation_accepted'] is False and a['runtime_or_source_qualification'] is False and a['fourth_installation_attempted'] is False and a['actual_model_calls']==a['cost_USD']==0,'public_no_qualification_or_cost')
need(a['tool_reported_elapsed_seconds']==0.601726875 and 'not an independently measured runtime' in a['elapsed_scope'],'tool_timing_only_attributed_not_independent')
mirror_totals={}
for folder,count,total in [('reports/evidence_e01_guard_diagnostic_v2_actual_20261116',11,36353),('reports/evidence_e01_guard_diagnostic_v2_preflight_20261116',3,29994)]:
 m=js(folder+'/manifest.json');need(len(m['files'])==count,'mirror_count:'+folder);n=0
 for r in m['files']:
  b=read(r['source']);copy=read(r['copy']);need(b==copy and len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],'mirror_exact:'+r['copy']);b.decode('utf-8');n+=len(b)
 need(n==total,'mirror_total:'+folder);mirror_totals[folder]={'files':count,'bytes':n}
result={'status':'PASS_PUBLIC_RECEIPT_AND_SAFE_TEXT_MIRRORS_CONSISTENT','count':len(checks),'checks':checks,'evidence_refs':refs,'mirror_totals':mirror_totals,'privacy_review':'Technical code/control/log text only: package names/versions and local paths visible; no respondent/publisher data, package bodies, credentials or owner financial material.','interpretation_caveat':'Construction failed before subsequent operations could occur is valid only for completion of this denied construction path. Absence of later labels does not prove absence of intention or all other attempted operations; no callsite/family/address/destination/history attribution.','tool_timing_independently_measured':False}
(OUT/'public_mirror_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':len(checks),'reference_bytes':sum(x['bytes'] for x in refs.values()),'mirror_totals':mirror_totals}))
