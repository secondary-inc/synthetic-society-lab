from pathlib import Path
import json,hashlib,resource,signal,time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent;START=time.monotonic();READS=0;checks=[];refs={}
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def stop(*a):raise RuntimeError('ACTUAL_STOP_REVIEW_DEADLINE')
signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,120)
def need(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
def read(rel):
 global READS
 p=ROOT/rel;need(all(not q.is_symlink() for q in (p,*p.parents)),'no_alias:'+rel);size=p.stat().st_size;READS+=size+1;need(READS<=67108864,'read_cap:'+rel)
 b=p.read_bytes();need(len(b)==size,'stable_size:'+rel);refs[rel]={'path':rel,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def js(rel):return json.loads(read(rel))
def pin(r):b=read(r['path']);need(refs[r['path']]==r,'pin:'+r['path']);return b
def packed(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
base='data/processed/e01_pypdf701_build_v1/';scope=base+'compatibility-v1_1-20261116/';m=js('configs/e01_offline_ipv6_compatibility_v1_1_20261116.json');pb=pin({'path':base+'compatibility-v1_1-packet-20261116.json','bytes':632,'sha256':'33479bb0ab6cbe3cfb1450dfd4c269def9ca11630a6e2f1303db636cd2f08711'});packet=json.loads(pb);need(pb==packed(packet),'canonical_final_packet')
review=json.loads(pin(packet['review_ref']));need(packet['review_ref']=={'path':'reports/INDEPENDENT_AUDIT_E01_IPV6_COMPATIBILITY_V1_1_PARTICULAR_V2_20261116.json','bytes':41026,'sha256':'c34e736ed5f48be2687ccba53c89426874a2795b181984b415090deb50e8b4f8'},'exact_corrected_particular')
core={k:v for k,v in packet.items() if k!='review_ref'};need(core==review['release']['packet_core'] and hashlib.sha256(packed(core)).hexdigest()==review['reviewed_packet_core_sha256']=='c84426eae707145f90fdbf0dc084b5ec7270eb72ef984493e920e426b80c82ea','only_review_ref_added_correct_core')
pin(packet['diagnostic_code_ref']);pin(m['adapter_ref']);need(review['evidence_refs'][packet['diagnostic_code_ref']['path']]==packet['diagnostic_code_ref'] and review['evidence_refs']['configs/e01_offline_ipv6_compatibility_v1_1_20261116.json']==refs['configs/e01_offline_ipv6_compatibility_v1_1_20261116.json'],'exact_runner_config_bindings')
files={}
for q in sorted((ROOT/scope).iterdir()):
 need(not q.is_symlink(),'new_scope_no_symlink:'+q.name)
 if q.is_file():files[q.name]=read(scope+q.name)
 else:need(q.name in {'home','tmp'} and q.is_dir() and not any(q.iterdir()),'empty_new_directory:'+q.name)
need(set(files)=={'STARTED.json','TERMINAL.json','1-COMMAND_RESERVED.json','1-COMMAND_RECORDED.json','1-stdout.bin','1-stderr.bin','requirements.txt','guest-payload.json','guest-refusals.json','guest-result.json'},'exact_ten_files_no_compatibility_receipt_or_stoprecord')
st=json.loads(files['STARTED.json']);t=json.loads(files['TERMINAL.json']);pl=json.loads(files['guest-payload.json']);g=json.loads(files['guest-result.json']);j=json.loads(files['guest-refusals.json']);cmd=json.loads(files['1-COMMAND_RECORDED.json']);reservation=json.loads(files['1-COMMAND_RESERVED.json'])
need(refs[scope+'TERMINAL.json']['bytes']==21122 and refs[scope+'TERMINAL.json']['sha256']=='b4251d9738f01ee568fab472e63c79df60bd0fcc5fbdfc4585d12e8f44d62af3','exact_terminal')
need(refs[scope+'guest-result.json']['bytes']==430 and refs[scope+'guest-result.json']['sha256']=='fa8303c9bf79e2adaf19f16b901c4fed343824c87c493474c4c2e2921424ef77','exact_guest_result')
for r in t['artifacts']:pin({**r,'path':scope+r['path']})
for r in cmd['output']:pin({**r,'path':scope+r['path']})
need(t['command']==cmd and t['commands_started']==1 and cmd['exit_code']==1 and cmd['pip_helper_descendants_permitted']==0,'once_child_failed_no_helper')
need(reservation['helper_descendants_permitted']==0 and reservation['absolute_interpreter'] is True and 0<reservation['remaining_wall_seconds']<=30,'reserved_finite_child')
need(reservation['argv']==['/Users/joshua/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12','-I','-B','-S',str(ROOT/packet['diagnostic_code_ref']['path']),'--guest','--payload',str(ROOT/(scope+'guest-payload.json')),'--payload-sha256',refs[scope+'guest-payload.json']['sha256']],'exact_bound_isolated_child_argv')
need(pl['kind']=='E01_OFFLINE_COMPATIBILITY_GUEST_PAYLOAD_V1_1' and pl['code_ref']==packet['diagnostic_code_ref'] and pl['root_sha256']==m['root_sha256'] and pl['scope']==m['scope'] and pl['target']==m['uncreated_target'],'payload_exact_code_scope_target_root')
need(pl['remaining_wall_seconds']==reservation['remaining_wall_seconds'] and pl['remaining_output_bytes']==262144,'remaining_caps_exact')
expected=['pip','--isolated','--disable-pip-version-check','--no-input','--use-deprecated=legacy-certs','install','--dry-run','--prefix',str(ROOT/m['uncreated_target']),'--ignore-installed','--no-index','--find-links',str(ROOT/(base+'acquisition-v1_4-20261116/wheels')),'--no-deps','--no-compile','--no-cache-dir','--only-binary=:all:','--require-hashes','-r',str(ROOT/(scope+'requirements.txt'))]
need(pl['pip_arguments']==expected and expected.count('--dry-run')==1 and g['pip_arguments_sha256']==hashlib.sha256(packed(expected)).hexdigest(),'exact_offline_pip_arguments_not_execution_proof')
need(len(pl['wheels'])==5 and {w['name'] for w in pl['wheels']}=={'pypdf','cffi','cryptography','pillow','pycparser'},'five_fixed_wheel_metadata')
req=files['requirements.txt'].decode().splitlines();need(len(req)==5 and all(f"{w['name']}=={w['version']} --hash=sha256:{w['sha256']}" in req for w in pl['wheels']),'requirements_match_payload')
need(g['kind']=='E01_OFFLINE_COMPATIBILITY_GUEST_RESULT_V1_1' and type(g['guard_violations']) is int and g['guard_violations']==0 and g['error_code']=='DIAGNOSTIC_GUEST_ERROR' and g['pip_completed'] is False and g['installation_accepted'] is False and g['target_exists'] is False and g['downloaded_package_imports'] is False,'generic_guest_error_retained_no_stage_or_cause_inference')
need(g['mime_configuration']=={'init_files':None,'initialized':True,'knownfiles':[],'mode':'STDLIB_BUILTIN_TYPES_ONLY_DARWIN'},'guest_builtin_MIME_receipt')
need(j=={'counter_saturated':False,'dropped_events':0,'events':[],'kind':'BOUNDED_GUEST_REFUSAL_JOURNAL_V2','total_events':0} and j==t['refusals'] and len(files['guest-refusals.json'])==117,'zero_recorded_events_no_drop_saturation')
need(t['kind']=='E01_OFFLINE_COMPATIBILITY_TERMINAL_V1_1' and t['outcome']=='FAILED_COMPATIBILITY' and t['reason']=='DIAGNOSTIC_NO_REFUSAL_PROOF' and t['compatibility'] is None,'closed_failed_proof_no_compatibility_receipt')
need(t['installation_accepted'] is False and t['runtime_or_source_qualification'] is False and t['no_retry'] is True and t['model_calls']==t['cost_USD']==0,'no_qualification_no_retry_zero_cost')
pre=js('reports/E01_IPV6_COMPATIBILITY_PREFLIGHT_V1_1_20261116.json')
need(st['prior']==t['prior']==pre['prior_allocation'],'prior_ancestry_same_preflight_start_terminal')
need(st['allocation']==t['allocation']==pre['diagnostic_allocation']==m['allocation'] and m['allocation']['cumulative_wall_seconds']==450 and m['allocation']['cumulative_observed_CPU_seconds']==180 and m['allocation']['cumulative_main_commands']==12,'full_allocation_450_180_12')
need(st['limits']==m['limits'] and st['code_ref']==packet['diagnostic_code_ref'] and st['methods_sha256']==packet['methods_sha256'] and st['packet_sha256']==hashlib.sha256(pb).hexdigest(),'started_exact_release_limits')
need(st['old_metadata_snapshot']==t['old_metadata_snapshot']==pre['old_metadata_snapshot']=={'entries_including_roots':544,'sha256':'0b6747e9eacfabd64af6b6a97591932a4eaae12b75d168e34ddd637d8d16de11'},'closed_eight_root_544_metadata_preservation')
pa=t['prior'];need(pa['actual_prior_commands_started']==8 and pa['actual_prior_captured_output_bytes']==21348 and pa['actual_prior_parent_read_bytes']==353429948 and abs(pa['actual_prior_observed_CPU_seconds']-2.964237)<1e-10,'prior_actual_charges_not_reset')
for r in pa['diagnostic_v2']['refs'].values():pin(r)
for r in pa['prior_through_diagnostic_v1']['diagnostic_v1']['refs'].values():pin(r)
need(t['parent_bound_reference_read_bytes_charged']==86862441<536870912 and t['captured_command_output_bytes']==0 and files['1-stdout.bin']==files['1-stderr.bin']==b'','bounded_read_and_empty_output')
need(t['reaped_child_CPU_seconds']==cmd['observed_reaped_CPU_seconds']==0.063611 and abs(t['observed_self_and_reaped_CPU_seconds']-0.628644)<1e-10 and t['observed_self_and_reaped_CPU_seconds']<20,'closed_CPU_accounting_under_cap')
new=sum(map(len,files.values()));need(new==45945<16777216 and pre['prior_owned_logical_bytes']+new==t['combined_logical_bytes_including_terminal']==25895438<805306368,'self_inclusive_new_scope_and_union_storage')
need(t['maximum_polled_owned_logical_bytes']==25874316 and t['maximum_polled_owned_logical_bytes']+len(files['TERMINAL.json'])==t['combined_logical_bytes_including_terminal'],'polled_plus_terminal_equals_final')
need(len(files['TERMINAL.json'])<=32768,'terminal_under_original_32KiB_cap')
for r in [m['uncreated_target'],*m['superseded_absent']]:
 q=ROOT/r;need(all(not a.is_symlink() for a in (q,*q.parents)),'absent_no_alias:'+r)
 try:q.lstat()
 except FileNotFoundError:checks.append('current_absent_lstat_only:'+r)
 else:raise AssertionError('unexpected_occupied:'+r)
need(not (ROOT/(scope+'guest-compatibility.json')).exists(),'compatibility_receipt_absent_current')
result={'status':'PASS_CLOSED_ACTUAL_FAILURE_INTEGRITY_ONLY','count':len(checks),'checks':checks,'evidence_refs':refs,'scope_bytes':new,'final_owned_bytes':25895438,'derived_final_entries':544+13,'commands_cumulative_actual_started':8+1,'cumulative_actual_parent_read_bytes':353429948+86862441,'cumulative_actual_output_bytes':21348,'cumulative_actual_observed_CPU_seconds':2.964237+t['observed_self_and_reaped_CPU_seconds'],'review_referenced_read_bytes_charged':READS,'review_monotonic_elapsed_seconds':time.monotonic()-START,'no_stage_cause_override_or_pip_absence_inference':True,'actual_replays':0,'cost_USD':0}
(OUT/'local_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':len(checks),'referenced_bytes':READS,'new_scope_bytes':new,'final_bytes':25895438}))
