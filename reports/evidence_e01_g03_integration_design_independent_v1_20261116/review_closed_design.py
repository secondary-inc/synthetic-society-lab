"""One closed static/arithmetic review. No candidate helper or runtime invocation."""
import sys
def deny(event,args):
    if event.startswith(('socket.','ctypes.')) or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','os.kill','os.killpg'}:
        raise AssertionError('NO_NETWORK_PROCESS_NATIVE')
sys.addaudithook(deny)
from pathlib import Path
import ast,hashlib,io,json,resource,signal,time,zipfile
ROOT=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
OUT=ROOT/'reports/evidence_e01_g03_integration_design_independent_v1_20261116'
BASE=ROOT/'reports/evidence_e01_pypa_fixture_g03_integration_design_v1_20261116'
REPORT=ROOT/'reports/E01_PYPA_FIXTURE_G03_INTEGRATION_DESIGN_V1_20261116.json'
start=time.monotonic();cpu=time.process_time();reads=1048576;cache={};refs={};checks=[]
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def timeout(*_):raise AssertionError('OWN120SECOND_CAP')
signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
def check(name,value):
    checks.append({'name':name,'pass':bool(value)})
    if not value:raise AssertionError(name)
def read(path):
    global reads
    p=Path(path);p=p if p.is_absolute() else ROOT/p
    if p not in cache:
        n=p.stat().st_size;check('read quota '+p.name,reads+n+1<=67108864)
        raw=p.read_bytes();reads+=len(raw)+1;cache[p]=raw
        refs[str(p)]={'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return cache[p]
def doc(path):return json.loads(read(path))
def pin(row):
    raw=read(row['path']);check('pin '+Path(row['path']).name,len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']);return raw
pin({'path':str(REPORT),'bytes':31238,'sha256':'8c43bc359bbf8a6e6ad71ca1c795aae7463a4effceaaa6f24c65b1c2a3d230d6'})
d=doc(REPORT);freeze=doc(BASE/'FREEZE.json')
pin(freeze['report_ref'])
for row in list(d['INPUT_ARTIFACTS'].values())+list(d['OUTPUT_ARTIFACTS'].values())+freeze['evidence_refs']:pin(row)
facts=doc(BASE/'MEASURED_FACTS.json');allocation=doc(BASE/'READ_ALLOCATION.json');contract=doc(BASE/'CHILD_ADAPTER_CONTRACT.json')
check('exact child contract embedded',contract==d['concrete_smallest_child_adapter'])
check('fixed13 input maps identical',len(facts['fixed_parent_inputs'])==13 and facts['fixed_parent_inputs']==d['INPUT_ARTIFACTS'])
fixed=sum(row['bytes']+1 for row in facts['fixed_parent_inputs'].values())
check('parent fixed18884579',fixed==facts['fixed_parent_logical_read_charge_bytes']==allocation['parent']['initial_measured_fixed_inputs_bytes']==d['measured_budget_assessment']['fixed_parent_inputs_bytes']==18884579)
runtime=facts['fixed_parent_inputs']['runtime_executable']['bytes']+1
rehash=sum(row['bytes']+1 for name,row in facts['fixed_parent_inputs'].items() if name!='runtime_executable')
check('nonruntime rehash826018',rehash==allocation['parent']['post_fixed_nonruntime_rehash_bytes']==826018 and fixed-runtime==rehash)
rows=allocation['parent']['new_artifact_and_console_maxima']
names=['new_actual_parent_entry_source','new_child_adapter_source','bootstrap_qualification_and_code_closure_receipt','child_guard_independent_review','particular_caller_independent_review','frozen_actual_packet','explicit_lead_release','exact_harness_release','captured_console_pipe_bytes']
check('nine exact named parent rows',[row['input'] for row in rows]==names)
for row in rows:
    expected=row['maximum_content_bytes'] if row['input']=='captured_console_pipe_bytes' else (row['maximum_content_bytes']+1)*row['maximum_reads']
    check('named row/count arithmetic '+row['input'],row['reserved_logical_bytes']==expected and type(row['maximum_reads']) is int and row['maximum_reads']>0)
new=sum(row['reserved_logical_bytes'] for row in rows)
check('new capped rows1196042',new==allocation['parent']['new_maximum_logical_bytes']==1196042)
upper=fixed+rehash+new;margin=20*1048576-upper
check('conditional parent upper20906639',upper==allocation['parent']['combined_parent_upper_bound_if_caps_and_read_counts_enforced']==d['measured_budget_assessment']['parent_upper_bound_with_nonruntime_rehashes_new_artifact_maxima_and_console']==20906639)
check('parent margin64881',margin==allocation['parent']['remaining_margin']==d['measured_budget_assessment']['parent_upper_bound_margin']==64881)
check('parent initial remaining2086941',20*1048576-fixed==facts['parent20MiB_remaining_before_unknown_closure_and_child_adapter']==2086941)
child_names=[name for name in facts['fixed_parent_inputs'] if name not in {'parent_caller','parent_review','harness_review'}]
child_lower=sum(facts['fixed_parent_inputs'][name]['bytes']+1 for name in child_names)
check('child known fixed lower18765549',len(child_names)==10 and child_lower==allocation['child_filesystem']['measured_fixed_inputs_lower_bound_bytes']==d['measured_budget_assessment']['child_measured_fixed_input_lower_bound_bytes']==18765549)
check('child remaining14788883',32*1048576-child_lower==allocation['child_filesystem']['remaining_before_reopens_bootstrap_guarded_stdlib_and_controls']==14788883)
parts={'parent_preflight':20*1048576,'trusted_bootstrap_reserve':8*1048576,'child_filesystem':32*1048576,'strict_memory':4*1048576}
check('20+8+32+4MiB exactly64MiB',allocation['partitions']==facts['proposed_partitions_bytes']==d['measured_budget_assessment']['proposed_partitions_bytes']==parts and sum(parts.values())==allocation['sum']==d['measured_budget_assessment']['sum_bytes']==67108864)
check('old deficit preserved',2*(runtime-1)+33554432==69671552 and 69671552-67108864==2562688 and '2,562,688' in d['measured_budget_assessment']['previous_deficit_preserved'])
source=read(d['INPUT_ARTIFACTS']['strict_source']['path']).decode();tree=ast.parse(source)
budget=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ReadBudget');init=next(n for n in budget.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
check('ReadBudget exact source constructor admits4MiB','0 <= limit <= 67108864' in ast.unparse(init) and 'type(limit) is int' in ast.unparse(init) and 0<=4194304<=67108864)
check('streams require exact ReadBudget class','type(budget) is ReadBudget' in source)
check('one shared4MiB pool not duplicate',allocation['memory']['limit']==4194304 and allocation['memory']['single_exact_class']=='ReadBudget' and 'allocated once' in allocation['memory']['binding'] and len(allocation['memory']['shared_consumers'])==3)
memory_step=next(v for v in contract['new_code_only_after_separate_assignment'] if v['block']=='One4MiBmemory input pool')
check('tool cursor/decompression charged same pool','same object' in memory_step['design'] and 'before every returned byte' in memory_step['design'] and 'explicit decompressed member/hash charge' in memory_step['design'] and 'unmetered BytesIO' in memory_step['integration'])
check('memory adapter still absent','not implemented' in d['RISKS_AND_LIMITATIONS'][3] or 'not implemented' in d['measured_budget_assessment']['stream_partition'])
for name,row in facts['explicit_stdlib_source_evidence'].items():
    raw=pin(row['ref']);lines=raw.decode().splitlines()
    for line in row['relevant_lines']:check('stdlib evidence line '+name+':'+str(line['line']),lines[line['line']-1].strip()==line['text'])
explicit=sum(row['ref']['bytes']+1 for row in facts['explicit_stdlib_source_evidence'].values())
check('seven selected stdlib sources213768',len(facts['explicit_stdlib_source_evidence'])==7 and explicit==facts['explicit_stdlib_source_charge_bytes']==213768)
archive=zipfile.ZipFile(io.BytesIO(read(d['INPUT_ARTIFACTS']['tool_archive']['path'])))
members=facts['tool_python_source_members'];observed={}
for name in archive.namelist():
    if name.endswith('.py'):
        raw=archive.read(name);reads+=len(raw);observed[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
check('ten inert tool source member hashes53172',observed==members and len(members)==10 and sum(row['bytes'] for row in members.values())==facts['tool_python_source_total_bytes']==53172)
check('helper read accounting19151519',fixed+explicit+53172==facts['helper_accounting']['content_read_charge_bytes']==d['TESTS_RUN_AND_RESULTS']['content_read_charge_bytes']==19151519)
check('packaging reserve arithmetic20200095',19151519+1048576==d['resource_accounting']['conservative_total_content_charge_including_packaging']==20200095)
registry=facts['helper_builtin_names'];check('retained registry95 unique and requirednames',len(registry)==len(set(registry))==95 and {'sys','posix','time','resource','_sha2','_signal'}<=set(registry))
check('registry not startup proof','UNSUBSTANTIATED' in facts['allocation_status']['bootstrap8MiB'] and 'not a child startup trace' in contract['new_code_only_after_separate_assignment'][0]['missing'])
expected_sources={'Python/pylifecycle.c','Python/initconfig.c','Python/import.c','Modules/main.c','Modules/getpath.py'}
root=Path(d['INPUT_ARTIFACTS']['runtime_executable']['path']).parents[1]
present=facts['local_CPython_startup_source_presence']
check('five specifically named startup paths',set(present)=={str(root/name) for name in expected_sources})
for name,row in present.items():check('current exact local absence '+str(Path(name).relative_to(root)),row=={'exists':False,'body_read':False} and not Path(name).exists())
check('absence scoped not universal','at all five inspected installed-runtime locations' in d['UNRESOLVED_BLOCKERS'][0]['smallest_design_condition']['current_absence'])
check('unsupported startup8MiB explicitly null',allocation['trusted_bootstrap']['actual_known_upper_bound'] is None and allocation['trusted_bootstrap']['status']=='BLOCKED_UNSUBSTANTIATED' and 'not measured usage or a proven maximum' in d['measured_budget_assessment']['bootstrap_partition'])
check('B01 is exact blocking finding',d['decision']=='BLOCKED_B01_EXACT_PRE_SCRIPT_PRE_HOOK_BOOTSTRAP_BOUND_NOT_SUBSTANTIATED' and len(d['UNRESOLVED_BLOCKERS'])==1 and d['UNRESOLVED_BLOCKERS'][0]['id']=='B01')
check('seven gates not accepted',len(d['seven_gate_resolutions'])==7 and all(not row['status'].startswith('PASS') for row in d['seven_gate_resolutions']))
check('new source/release absent',all(v is None for v in contract['source_refs'].values()) and contract['first_actual_run'].startswith('NOT_RELEASED') and freeze['actual_release'] is False)
check('no blanket compile/stdlib/descriptorgrant','No whole stdlib/site tree' in d['seven_gate_resolutions'][1]['resolution'] and 'No arbitrary<string>' in contract['code_origin_manifest_schema']['GENERATED']['required'] and 'No whole stdlib tree' in contract['new_code_only_after_separate_assignment'][2]['design'])
check('dual generated gates independent fifteen','two independent' in contract['new_code_only_after_separate_assignment'][4]['dataclass_gate'] and 'do not share one incrementing index' in contract['new_code_only_after_separate_assignment'][4]['dataclass_gate'])
check('accepted F01 F02 P01 scopes preserved',freeze['component_passes_preserved']==['F01','F02','P01'] and 'does not revoke' in d['RISKS_AND_LIMITATIONS'][-1])
check('old allocation unchanged',d['resource_accounting']['prior_consumed_allocation_unchanged']=={'observed_CPU_seconds':180,'old_children':12,'wall_seconds':450})
check('not proven/actualactivityzero',facts['no_actual_actions']=={'actual_backend_calls':0,'candidate_or_tool_import_compile_execute':0,'fixture_children':0,'global_candidate_hook_installations':0,'network_model_credentials_ledger':0,'old_targets_PDF_research_raw':0,'production_Git_STATUS_changes':0} and d['TESTS_RUN_AND_RESULTS']['tests_run']==0)
check('own read/time budget',reads<67108864 and time.monotonic()-start<120 and time.process_time()-cpu<120)
receipt={'decision':'PASS_CLOSED_ARITHMETIC_AND_TRUTHFUL_BLOCKED_DESIGN_ONLY_ACTUAL_G03_BLOCKED','checks_passed':len(checks),'checks':checks,'input_refs':list(refs.values()),'arithmetic':{'parent_fixed':fixed,'nonruntime_rehash':rehash,'new_capped_rows':new,'conditional_parent_upper':upper,'parent_margin':margin,'child_known_input_lower':child_lower,'child_known_names':child_names,'partitions':parts,'partition_sum':sum(parts.values())},'not_run':['Candidate helper execution','Exact runtime builtin observation rerun','Actual child/backend/PyPA/tool/installer/PDF execution','Bootstrap8MiB bound or full loadedcode/cache/guard/descriptor composition','Network/model/credential/owner/Git/STATUS mutation'],'limitations':['File sizes/readcounts plus caps are conditional arithmetic, not measured successful runtime input counts.','95builtin names are retained producer metadata; no new runtime probe or prehook-read evidence.','Absence applies only five specified installed-runtime paths, no universal source search or availability finding.','One4MiBsharedreader,outerguard/newactivation wiring and all actual gates remain unimplemented.','Helper source inspected only, never imported/executed. Tool Python members hashed as inert bytes only.'],'resource_accounting':{'technical_read_bytes_with1MiBinitialreserve':reads,'CPU_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-start,'new_network_model_runtime_candidate_executions':0,'cost_USD':0}}
raw=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode();check('owned evidence under4MiB',len(raw)<4194304)
with (OUT/'checks.json').open('xb') as f:f.write(raw)
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({'decision':receipt['decision'],'checks':receipt['checks_passed'],'read_bytes':reads,'evidence_bytes':len(raw),'CPU_seconds':receipt['resource_accounting']['CPU_seconds'],'wall_seconds':receipt['resource_accounting']['wall_seconds']}))
