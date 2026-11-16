from pathlib import Path
import json,hashlib,resource,signal,time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent;local=json.loads((OUT/'local_checks.json').read_text());READS=local['review_referenced_read_bytes_charged'];START=time.monotonic();checks=[];refs={}
remaining=120-local['review_monotonic_elapsed_seconds'];hard=max(2,int(remaining));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(hard-1,hard))
def stop(*a):raise RuntimeError('INCREMENTAL_PUBLIC_REVIEW_DEADLINE')
signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,remaining)
def need(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
def read(rel):
 global READS
 p=ROOT/rel;need(all(not a.is_symlink() for a in (p,*p.parents)),'no_alias:'+rel);READS+=p.stat().st_size+1;need(READS<=67108864,'combined_read_cap:'+rel)
 b=p.read_bytes();refs[rel]={'path':rel,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def pin(r):b=read(r['path']);need(refs[r['path']]==r,'pin:'+r['path']);return b
rp='reports/E01_IPV6_COMPATIBILITY_V1_1_ACTUAL_STOP_20261116.json';rb=read(rp);a=json.loads(rb);need(refs[rp]=={'path':rp,'bytes':7663,'sha256':'f0d45ba7eaf5f23faa017c343ccf026360c818cfa27a55403a35ea415a49de8c'},'frozen_public_report')
need(set(a['original_refs'])==set(a['safe_mirrors'])=={'STARTED.json','TERMINAL.json','guest-payload.json','guest-result.json','guest-refusals.json','1-COMMAND_RESERVED.json','1-COMMAND_RECORDED.json','1-stdout.bin','1-stderr.bin','requirements.txt','packet'},'eleven_original_mirror_entries')
bodies={};total=0
for key,ref in a['original_refs'].items():
 need(ref==local['evidence_refs'][ref['path']],'original_matches_local_review:'+key)
 raw=pin(ref);mirror=a['safe_mirrors'][key];copy=pin(mirror);need(copy==raw and mirror['bytes']==ref['bytes'] and mirror['sha256']==ref['sha256'],'exact_mirror:'+key);copy.decode('utf-8');bodies[key]=raw;total+=len(raw)
need(total==46577 and total-632==45945,'safe_mirror_and_scope_totals')
t=json.loads(bodies['TERMINAL.json']);g=json.loads(bodies['guest-result.json']);j=json.loads(bodies['guest-refusals.json']);st=json.loads(bodies['STARTED.json'])
need(a['terminal_outcome']==t['outcome']=='FAILED_COMPATIBILITY' and a['terminal_reason']==t['reason']=='DIAGNOSTIC_NO_REFUSAL_PROOF','public_terminal_outcome')
need(a['guest_error_code']==g['error_code']=='DIAGNOSTIC_GUEST_ERROR' and a['pip_completed']==g['pip_completed']==False,'public_guest_generic_error')
need(a['recorded_guard_violations']==g['guard_violations']==0 and a['recorded_refusal_events']==j['total_events']==0,'public_zero_recorded_not_stageproof')
need(a['compatibility_receipt']=='ABSENT' and a['socket_override_and_restoration']=='NOT_ESTABLISHED_WITHOUT_COMPATIBILITY_RECEIPT' and a['actual_error_cause']=='UNKNOWN_GENERIC_GUEST_ERROR_ONLY','public_unknown_cause_and_override')
need(a['commands_started']==t['commands_started']==1 and a['tool_observed_exit_code']==t['command']['exit_code']==1,'public_once_exit1')
need(a['closed_scope_file_count']==10 and a['closed_scope_logical_bytes']==45945 and a['combined_owned_logical_bytes_including_terminal']==t['combined_logical_bytes_including_terminal']==25895438,'public_final_storage')
need(a['actual_allocation_fully_consumed']==t['allocation'] and a['old_metadata_snapshot_retained_in_terminal']==t['old_metadata_snapshot'] and a['UTC_started']==st['utc'],'public_full_allocation_snapshot')
for key in ['captured_command_output_bytes','parent_bound_reference_read_bytes_charged','observed_self_and_reaped_CPU_seconds','reaped_child_CPU_seconds']:need(a[key]==t[key],'public_usage:'+key)
need(a['installation_accepted'] is False and a['runtime_or_source_qualification'] is False and a['retry_permitted'] is False and a['cost_USD']==a['model_calls']==0,'public_gates_cost_no_retry')
need(type(a['tool_observed_wall_seconds']) is float and a['tool_observed_wall_seconds']==0.583332292,'tool_wall_reported_only_not_independent_runtime')
result={'status':'PASS_PUBLIC_FAILURE_REPORT_AND_ELEVEN_SAFE_MIRRORS','count':len(checks),'checks':checks,'evidence_refs':refs,'mirror_files':11,'mirror_bytes':46577,'scope_files':10,'scope_bytes':45945,'combined_review_referenced_reads':READS,'combined_measured_read_verifier_elapsed_seconds':local['review_monotonic_elapsed_seconds']+time.monotonic()-START,'privacy':'UTF-8 technical control/config/log text including local paths and package hashes only. No rawrespondent/publisher/package bodies/financialowner/credentials. Root embedded original_refs/safe_mirrors is the manifest; no separate manifest file supplied/required.','lead_commit_and_tool_timing':'Lead-reported code_commit10ef9c6 andtoolwall.583332292 attributedonly; no Git operation or independent actual runtime wall measurement byauditor.','actual_replays':0,'cost_USD':0}
(OUT/'public_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':len(checks),'combined_referenced_bytes':READS,'mirror_bytes':46577}))
