from pathlib import Path
from datetime import datetime
import hashlib,json,stat
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent
checks=[];refs={}
def need(ok,label):
    if not ok: raise AssertionError(label)
    checks.append(label)
def read(path):
    p=ROOT/path
    need(all(not x.is_symlink() for x in (p,*p.parents)), 'no_alias:'+path)
    b=p.read_bytes();refs[path]={'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def js(path):return json.loads(read(path))
def pin(path,size,sha):
    b=read(path);need(len(b)==size and hashlib.sha256(b).hexdigest()==sha,'pin:'+path);return b
def canon(d):return (json.dumps(d,sort_keys=True,separators=(',',':'))+'\n').encode()
source='scripts/diagnose_e01_pypdf701_guard_v2.py';method='configs/e01_pypdf701_guard_diagnostic_v2_20261116.json'
pin(source,49178,'6582297cd01bc2131a4cc17ea1e0d384c15b56fee6fa07620dada9a2c7c11c49')
mb=pin(method,6817,'c85b5c887aadd88e356e63aaf8864f59f2f10005c9f036804529f95114e877b3');m=json.loads(mb);need(canon(m)==mb,'canonical_methods')
prod=js('reports/INDEPENDENT_AUDIT_E01_GUARD_DIAGNOSTIC_RUNNER_V2_PRODUCTION_20261116.json')
need(refs['reports/INDEPENDENT_AUDIT_E01_GUARD_DIAGNOSTIC_RUNNER_V2_PRODUCTION_20261116.json']['sha256']=='d331186ffbdbd23509add7102fd231a4cfaa97ad66db4105739843757ad33926','production_exact_review')
need(prod['status']=='PASS_EXACT_FINAL_V2_PRODUCTION_AND_104_GUARDED_REVIEW_CHECKS_ACTUAL_PREFLIGHT_PARTICULAR_PENDING','production_PASS')
pin('reports/INDEPENDENT_AUDIT_E01_DIAGNOSTIC_PREFLIGHT_HELPER_V3_20261116.json',7124,'4e8ebffdea70caf07678bc10bf7822419bcada3605246a67d7b12110793ac52c')
pin('data/processed/e01_guard_diagnostic_preflight_v3_20261116.py',9049,'d94d91a6616577bf55d1cf6b191cf24f703a6170ba9a37cad727cf7cf1017291')
rp='reports/E01_GUARD_DIAGNOSTIC_PREFLIGHT_V3_20261116.json';rb=read(rp);r=json.loads(rb)
lp='data/processed/e01_guard_diagnostic_preflight_v3_20261116/RECEIPT.json';need(read(lp)==rb,'closed_report_local_receipt_identical')
sp='data/processed/e01_guard_diagnostic_preflight_v3_20261116/STARTED.json';s=js(sp)
for name,data in [('STARTED.json',read(sp)),('RECEIPT.json',rb)]: (OUT/name).write_bytes(data)
need(r['status']=='PASS_METADATA_ONLY_NO_DIAGNOSTIC' and 'error_type' not in r,'closed_PASS_no_error')
need(s['preflight_invocations']==1 and s['separate_from_diagnostic_child_allocation'] is True,'one_preflight_separate_from_diagnostic')
need(s['pins']==r['pins'],'start_terminal_pins')
for p,(size,h) in r['pins'].items():pin(p,size,h)
for k in ['child_commands','model_calls','network_requests','pip_imports','downloaded_package_imports','research_source_reads','cost_USD']:need(r[k]==0,'zero:'+k)
need(r['installation_accepted'] is False,'no_install_acceptance')
need(s['wall_seconds']==30 and s['CPU_soft_hard']==[7,8] and s['bound_reader_bytes']==536870912 and s['control_write_bytes']==196608,'unchanged_helper_caps')
interval=(datetime.fromisoformat(r['UTC_finished'])-datetime.fromisoformat(s['UTC'])).total_seconds()
need(0<=interval<30 and 0<=r['monotonic_elapsed_seconds']<30 and abs(interval-r['monotonic_elapsed_seconds'])<0.01,'closed_clocks_aligned_under_cap')
need(r['reader_bytes_charged']==43107612 and r['reader_bytes_charged']<s['bound_reader_bytes'],'charged_reader_under_cap')
need(r['verified_wheels']==5 and r['requirements_sha256']=='6cab8b38346fe98158c281a5b93eeb4762958ebab3400e2e22f932023210fa6b','five_wheels_requirements_receipt')
need(r['old_metadata_unchanged'] is True and r['old_metadata_snapshot']=={'entries_including_roots':531,'sha256':'fece1bb00bda7ad26efa4927a66e3d057b9df48bb6de161800656265aebec86b'},'closed_seven_roots_metadata_snapshot')
need(len(m['preserved_roots'])==7 and len(set(m['preserved_roots']))==7,'seven_distinct_preserved_roots')
need(r['prior_owned_logical_bytes']==25813735 and r['combined_upper_bound']==25813735+16777216==42590951 and r['combined_upper_bound']<805306368,'eight_tree_storage_reserved_upper_bound')
need(m['limits']['combined_eight_tree_logical_bytes']==805306368 and m['limits']['each_diagnostic_scope_logical_bytes']==16777216 and m['limits']['combined_tree_entries']==16384,'both_diagnostic_caps_union_cap')
need(r['actual_scope_target_packet_absent'] is True,'closed_scope_absence')
for rel in [m['scope'],m['uncreated_target'],m['packet']]:
    try:(ROOT/rel).lstat()
    except FileNotFoundError:checks.append('current_absent:'+rel)
    else:raise AssertionError('occupied:'+rel)
a={'cumulative_main_commands':11,'cumulative_observed_CPU_seconds':160,'cumulative_wall_seconds':420,'new_main_commands':1,'new_observed_CPU_seconds':20,'new_wall_seconds':30,'prior_main_commands':10,'prior_observed_CPU_seconds':140,'prior_wall_seconds':390}
need(r['diagnostic_allocation']==m['allocation']==a,'full_cumulative_allocation_420_160_11')
pa=r['prior_allocation'];need(pa['actual_prior_commands_started']==7 and pa['actual_prior_captured_output_bytes']==18912 and pa['actual_prior_parent_read_bytes']==267429493 and abs(pa['actual_prior_observed_CPU_seconds']-2.233471)<1e-10,'actual_charges_distinct_from_full_allocations')
need(pa['full_prior_allocation']==pa['diagnostic_v1']['allocation'],'old_full_allocation_preserved')
need(pa['diagnostic_v1']['original_coarse_journal']=={'counter_saturated':False,'dropped_events':0,'events':[{'code':'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED','operation':'SOCKET','sequence':1}],'kind':'BOUNDED_GUEST_REFUSAL_JOURNAL_V1','total_events':1},'old_coarse_refusal_not_relabelled')
for ref in pa['diagnostic_v1']['refs'].values():pin(ref['path'],ref['bytes'],ref['sha256'])
proof=r['configuration_proofs'];base='/Users/joshua/.cache/codex-runtimes/codex-primary-runtime/dependencies/python'
need(proof['current_narrowed_base_paths']==[base+'/lib/python3.12',base+'/lib/python3.12/lib-dynload'],'closed_current_base_paths')
need(proof['stdlib_origin_validated_builtin_MIME']=={'init_files':None,'initialized':True,'knownfiles':[],'mode':'STDLIB_BUILTIN_TYPES_ONLY_DARWIN'},'closed_builtin_MIME_proof')
need(proof['prescribed_child_PATH']==base+'/bin:/usr/bin:/bin' and proof['child_PATH_matches_frozen_and_diagnostic_source_AST'] is True and proof['child_PATH_is_prescribed_not_observed_execution'] is True,'PATH_prescribed_not_observed')
cp='reports/E01_GUARD_DIAGNOSTIC_V2_PACKET_CORE_CANDIDATE_20261116.json';cb=pin(cp,1592,'8c39c5e3c9e83837bd687eb6245c660665699add845f1dd8e39441f2b869fb10');c=json.loads(cb);core=c['core_for_independent_particular_review']
need(set(core)=={'kind','root_sha256','methods_sha256','diagnostic_code_ref','execution_enabled'},'five_core_fields')
need(core['root_sha256']==hashlib.sha256(str(ROOT).encode()).hexdigest()==m['root_sha256'],'exact_root_binding')
need(core['kind']=='E01_GUARD_DIAGNOSTIC_EXECUTION_PACKET_V1' and core['execution_enabled'] is True,'exact_enabled_diagnostic_core')
need(core['diagnostic_code_ref']==refs[source] and core['methods_sha256']==refs[method]['sha256'] and c['methods_ref']==refs[method],'exact_code_methods_binding')
need(hashlib.sha256(canon(core)).hexdigest()==c['canonical_core_sha256']=='36b4b322d54e159b1d9eb984c7769789b7e4f403b3876f4eb52e97588123e9df','canonical_core_hash')
need(c['actual_packet_created'] is False and c['no_fourth_installation_or_P3'] is True,'candidate_not_actual_packet_or_install')
out={'status':'PASS_CLOSED_METADATA_AND_EXACT_CORE_CHECKS','checks':checks,'count':len(checks),'evidence_refs':refs,'closed_UTC_interval_seconds':interval,'reviewed_packet_core_sha256':c['canonical_core_sha256'],'core':core,'limits':m['limits'],'allocation':a,'scope':m['scope'],'uncreated_target':m['uncreated_target'],'packet':m['packet'],'auditor_actual_runner_helper_invocations':0,'auditor_old_target_or_wheel_body_reads':0,'cost_USD':0}
(OUT/'checks.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':out['status'],'checks':len(checks),'UTC_interval_seconds':interval,'read_reference_bytes':sum(x['bytes'] for x in refs.values())}))
