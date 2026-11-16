from pathlib import Path
import hashlib,json,stat
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
refs={};checks=[]
def need(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
def read(rel):
 p=ROOT/rel;need(all(not x.is_symlink() for x in (p,*p.parents)),'no_alias:'+rel)
 b=p.read_bytes();refs[rel]={'path':rel,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def js(rel):return json.loads(read(rel))
def pin(ref):
 b=read(ref['path']);need(len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256'],'hash:'+ref['path']);return b
def packed(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
base='data/processed/e01_pypdf701_build_v1/';scope=base+'diagnostic-v2-20261116/'
m=js('configs/e01_pypdf701_guard_diagnostic_v2_20261116.json');packetpath=base+'diagnostic-v2-packet-20261116.json';pb=read(packetpath);p=json.loads(pb)
need(len(pb)==595 and hashlib.sha256(pb).hexdigest()=='a38f32592d410d8f117b6345dac6efb3bf177c3443a36dd4b76cf34c40903c12' and pb==packed(p),'exact_final_packet')
a=json.loads(pin(p['review_ref']));need(p['review_ref']=={'path':'reports/INDEPENDENT_AUDIT_E01_GUARD_DIAGNOSTIC_V2_PARTICULAR_20261116.json','bytes':21665,'sha256':'410055439875f8f2583d67c162d0852f0f4739c2a52774a57255fa0d8c859bdc'},'exact_particular_review')
core={k:v for k,v in p.items() if k!='review_ref'};need(core==a['release']['packet_core'] and hashlib.sha256(packed(core)).hexdigest()==a['reviewed_packet_core_sha256']=='36b4b322d54e159b1d9eb984c7769789b7e4f403b3876f4eb52e97588123e9df','only_review_ref_added')
pin(p['diagnostic_code_ref']);meth='configs/e01_pypdf701_guard_diagnostic_v2_20261116.json';need(refs[meth]==a['evidence_refs'][meth] and p['methods_sha256']==refs[meth]['sha256'],'exact_code_methods')
files={}
for item in sorted((ROOT/scope).iterdir()):
 need(not item.is_symlink(),'new_scope_no_symlink:'+item.name)
 if item.is_file():files[item.name]=read(scope+item.name)
 else:need(item.name in {'home','tmp'} and item.is_dir() and not any(item.iterdir()),'new_scope_empty_directory:'+item.name)
need(set(files)=={'STARTED.json','TERMINAL.json','1-COMMAND_RESERVED.json','1-COMMAND_RECORDED.json','1-stdout.bin','1-stderr.bin','requirements.txt','guest-payload.json','guest-result.json','guest-refusals.json'},'ten_closed_files_no_stopped_or_extra')
st=json.loads(files['STARTED.json']);t=json.loads(files['TERMINAL.json']);pl=json.loads(files['guest-payload.json']);j=json.loads(files['guest-refusals.json']);g=json.loads(files['guest-result.json']);cmd=json.loads(files['1-COMMAND_RECORDED.json']);reservation=json.loads(files['1-COMMAND_RESERVED.json'])
need(refs[scope+'TERMINAL.json']['sha256']=='6898bbea458abfd769fcd6bcef2418afd50f76c7db7b0e83181340b8218a030b' and len(files['TERMINAL.json'])==14847,'exact_terminal')
for r in t['artifacts']:pin({**r,'path':scope+r['path']})
for r in cmd['output']:pin({**r,'path':scope+r['path']})
need(t['command']==cmd and t['commands_started']==1 and cmd['exit_code']==1 and cmd['pip_helper_descendants_permitted']==0,'one_child_nonzero_no_helpers')
need(reservation['helper_descendants_permitted']==0 and reservation['absolute_interpreter'] is True and 0<reservation['remaining_wall_seconds']<=30,'bounded_reserved_child')
argv=reservation['argv'];need(argv==['/Users/joshua/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12','-I','-B','-S',str(ROOT/'scripts/diagnose_e01_pypdf701_guard_v2.py'),'--guest','--payload',str(ROOT/(scope+'guest-payload.json')),'--payload-sha256',refs[scope+'guest-payload.json']['sha256']],'exact_isolated_absolute_child_payload_binding')
need(pl['code_ref']==p['diagnostic_code_ref'] and pl['root_sha256']==m['root_sha256'] and pl['scope']==m['scope'] and pl['target']==m['uncreated_target'],'payload_exact_scope_code_root')
need(pl['remaining_wall_seconds']==reservation['remaining_wall_seconds'] and pl['remaining_output_bytes']==262144,'payload_unchanged_remaining_caps')
expected=['pip','--isolated','--disable-pip-version-check','--no-input','--use-deprecated=legacy-certs','install','--dry-run','--prefix',str(ROOT/m['uncreated_target']),'--ignore-installed','--no-index','--find-links',str(ROOT/(base+'acquisition-v1_4-20261116/wheels')),'--no-deps','--no-compile','--no-cache-dir','--only-binary=:all:','--require-hashes','-r',str(ROOT/(scope+'requirements.txt'))]
need(pl['pip_arguments']==expected and expected.count('--dry-run')==1 and g['pip_arguments_sha256']==hashlib.sha256(packed(expected)).hexdigest(),'exact_offline_five_wheel_dry_run_argv')
need(len(pl['wheels'])==5 and {w['name'] for w in pl['wheels']}=={'pypdf','cffi','cryptography','pillow','pycparser'},'five_fixed_wheel_metadata_only')
req=files['requirements.txt'].decode().splitlines();need(len(req)==5 and all(f"{w['name']}=={w['version']} --hash=sha256:{w['sha256']}" in req for w in pl['wheels']),'requirements_match_five_payload_pins')
need(j=={'counter_saturated':False,'dropped_events':0,'events':[{'code':'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED','operation':'SOCKET_CONSTRUCT','sequence':1}],'kind':'BOUNDED_GUEST_REFUSAL_JOURNAL_V2','total_events':1} and j==t['refusals'] and len(files['guest-refusals.json'])==209,'one_fine_construct_original_refusal_no_drop_saturation')
need(g['guard_violations']==1 and g['pip_completed'] is True and g['error_code']=='GUEST_CAUGHT_VIOLATION' and g['target_exists'] is False and g['installation_accepted'] is False and g['downloaded_package_imports'] is False,'guard_postcondition_preserved_after_pip_completed')
need(g['mime_configuration']=={'init_files':None,'initialized':True,'knownfiles':[],'mode':'STDLIB_BUILTIN_TYPES_ONLY_DARWIN'},'actual_builtin_MIME_receipt')
need(t['outcome']=='REFUSAL_OBSERVED' and t['reason']=='GUEST_CAUGHT_VIOLATION' and t['installation_accepted'] is False and t['runtime_or_source_qualification'] is False and t['no_retry'] is True,'closed_refusal_no_qualification')
need(t['cost_USD']==0 and t['model_calls']==0,'zero_cost_models')
pre=js('reports/E01_GUARD_DIAGNOSTIC_PREFLIGHT_V3_20261116.json')
need(st['prior']==t['prior']==pre['prior_allocation'],'prior_control_chain_same_preflight_start_terminal')
need(st['allocation']==t['allocation']==pre['diagnostic_allocation']==m['allocation'],'full_420_160_11_allocation_unchanged')
need(st['limits']==m['limits'] and st['code_ref']==p['diagnostic_code_ref'] and st['methods_sha256']==p['methods_sha256'] and st['packet_sha256']==refs[packetpath]['sha256'],'started_exact_release_limits')
need(st['old_metadata_snapshot']==t['old_metadata_snapshot']==pre['old_metadata_snapshot']=={'entries_including_roots':531,'sha256':'fece1bb00bda7ad26efa4927a66e3d057b9df48bb6de161800656265aebec86b'},'closed_531_old_snapshot_unchanged')
for old in t['prior']['diagnostic_v1']['refs'].values():pin(old)
for stage in t['prior']['installations']['older_stages']['stages']:
 for k in ['code_ref','methods_ref','packet_ref','started_ref','terminal_ref']:pin(stage[k])
pin(t['prior']['installations']['latest_terminal_ref'])
need(t['parent_bound_reference_read_bytes_charged']==86000455<536870912 and t['captured_command_output_bytes']==sum(r['bytes'] for r in cmd['output'])==2436<262144,'read_output_under_cap')
need(t['reaped_child_CPU_seconds']==cmd['observed_reaped_CPU_seconds']==0.198571 and t['observed_self_and_reaped_CPU_seconds']==0.730766<20,'CPU_closed_accounting')
new=sum(map(len,files.values()));old_diag=sum(x['bytes'] for x in t['prior']['diagnostic_v1']['refs'].values() if x['path'].startswith(base+'diagnostic-v1-20261116/'))
need(new==35758<16777216 and old_diag==23870<16777216,'both_final_diagnostic_scopes_under_16MiB')
need(pre['prior_owned_logical_bytes']+new==t['combined_logical_bytes_including_terminal']==25849493<805306368,'self_inclusive_final_storage')
need(t['maximum_polled_owned_logical_bytes']==25834646 and t['maximum_polled_owned_logical_bytes']+len(files['TERMINAL.json'])==t['combined_logical_bytes_including_terminal'],'polled_vs_self_inclusive_terminal_storage')
try:(ROOT/m['uncreated_target']).lstat()
except FileNotFoundError:checks.append('fictional_target_still_absent_lstat_only')
else:raise AssertionError('unexpected_target_exists')
need(b'Would install ' in files['1-stdout.bin'] and b'GUEST_CAUGHT_VIOLATION' in files['1-stderr.bin'],'pip_stdout_dry_run_and_guard_traceback')
result={'status':'PASS_CLOSED_ACTUAL_BINDING_INTEGRITY_REFUSAL_ONLY','checks':checks,'count':len(checks),'evidence_refs':refs,'scope_file_bytes':new,'old_diagnostic_scope_file_bytes':old_diag,'final_combined_owned_bytes':25849493,'auditor_actual_runner_helper_or_package_invocations':0,'auditor_target_or_wheel_body_reads':0,'cost_USD':0}
(OUT/'checks.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'reference_bytes':sum(x['bytes'] for x in refs.values()),'newscope_bytes':new,'oldscope_bytes':old_diag}))
