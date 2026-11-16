"""Closed JSON/hash/stat/AST evidence review only; never import reviewed code."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,sys,time
START=time.monotonic();CPU=time.process_time();ROOT=Path.cwd();E=ROOT/'reports/evidence_ci_historical_collection_v1_2_20261116'
OUT=ROOT/'reports/evidence_ci_historical_collection_v1_2_independent_20261116'
REPORT=ROOT/'reports/INDEPENDENT_AUDIT_CI_HISTORICAL_COLLECTION_V1_2_ACTUAL_20261116.json'
reads=0;checks=[];pins={};source_report_path=ROOT/'reports/CI_HISTORICAL_COLLECTION_V1_2_ACTUAL_20261116.json'
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def timeout(*_):raise RuntimeError('REVIEW_TIME_CAP')
signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
def no_effect(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:raise RuntimeError('REVIEW_EFFECT_DENIED')
sys.addaudithook(no_effect)
def check(name,ok,evidence):checks.append({'id':name,'result':'PASS' if ok else 'BLOCKED','evidence':evidence})
def read(path):
 global reads
 path=Path(path);path=path if path.is_absolute() else ROOT/path
 if '.venv-e01' in str(path) or path.is_relative_to(ROOT/'data') or any(p.name.startswith('.env') for p in [path]):raise RuntimeError('FORBIDDEN_REVIEW_INPUT')
 before=path.stat();reads+=before.st_size+1
 if reads>67108864:raise RuntimeError('REVIEW_READ_CAP')
 raw=path.read_bytes();after=path.stat()
 if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise RuntimeError('REVIEW_INPUT_DRIFT')
 return raw
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(read(path))
def pin(path,expected=None):
 raw=read(path);p=Path(path);p=p if p.is_absolute() else ROOT/p
 ref={'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'bytes':len(raw),'sha256':sha(raw)}
 pins[ref['path']]=ref
 if expected is not None:check('PIN:'+ref['path'],(len(raw),sha(raw))==(expected['bytes'],expected['sha256']),ref)
 return raw
raw=pin(source_report_path,{'bytes':5146,'sha256':'6f0303b1b30aa0d0f7889afd290a670bdb7635495eee3b69d35c54d23ffea071'});r=json.loads(raw)
for ref in r['evidence']:pin(ref['path'],ref)
p=load(E/'PACKET.json');release=load(E/'LEAD_RELEASE.json');started=load(E/'STARTED.json');final=load(E/'FINAL.json');supervisor=load(E/'SUPERVISOR.json')
receipt=load(E/'owned-temp-python312/collection-receipt.json');post=load(E/'lead-post-binding-verification.json');state=receipt['state']
check('EXACT_SCOPE',all(d.get('scope',d.get('approved_scope'))=='ONE_HISTORICAL_312_COLLECTION_ONLY_V1_2' for d in [p,release,started,final,r]),'PACKET/LEAD_RELEASE/STARTED/FINAL/source report')
check('DISPATCH_ONE_NO_RETRY',p['maximum_children']==release['maximum_children']==started['maximum_children']==final['actual_dispatch_attempts']==r['actual_child_dispatches']==1 and p['retries']==0 and final['retry_allowed'] is False and started['state']=='CONSUMED_BEFORE_DISPATCH_NO_RETRY','One retained STARTED/SUPERVISOR/FINAL; no replay invoked by reviewer')
check('PACKET_RELEASE_HASH',sha(read(E/'PACKET.json'))==release['packet_sha256']==started['packet_sha256'] and sha(read(E/'LEAD_RELEASE.json'))==started['lead_release_sha256'],'Exact retained packet and release bytes')
review_ref=release['component_review']['report_ref'];review=json.loads(pin(review_ref['path'],review_ref))
check('COMPONENT_REVIEW',review['decision']==release['component_review']['decision']=='PASS_EXACT_NAMESPACE_COMPONENT_ONLY_NO_COLLECTION_RELEASE' and release['component_review']==started['component_review'],'Component acceptance binds namespace remedy only; explicit lead release is separate')
check('LIMITS_BINDING',p['limits']==release['limits']==r['limits']=={'child_wall_seconds':120,'child_cpu_seconds':120,'source_technical_read_bytes':268435456,'owned_temp_write_bytes':33554432,'console_bytes':524288},'All three limit dictionaries identical')
expected_code=sorted(str(path) for group in ['tests','scripts','src'] for path in (ROOT/group).rglob('*.py') if '__pycache__' not in path.parts)
check('EXACT_CURRENT_CODE_SET',expected_code==sorted(row['path'] for row in p['code_inputs']) and len(expected_code)==470,'470 exact Python source inputs across tests/scripts/src; no execution')
all_rows=[]
for group,count in [('code_inputs',470),('metadata_inputs',30),('runtime_inputs',1),('harness_sources',3)]:
 rows=p[group];check('COUNT:'+group,len(rows)==count and len({row['path'] for row in rows})==count,{'count':len(rows)})
 for row in rows:
  path=Path(row['path']);check('RESOLUTION:'+row['path'],str(path.resolve())==row['resolved_path'],row['resolved_path']);pin(path,row);all_rows.append((group,row))
post_rows={(v['group'],v['path']):v for v in post['references']}
check('POST_BINDING_SET',len(post['references'])==len(all_rows)==504,'470code+30metadata+1runtime+3harness')
for group,row in all_rows:
 path=Path(row['path']);key=(group,str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path));v=post_rows.get(key)
 check('POST_REF:'+key[1],v is not None and v['bytes']==row['bytes'] and v['sha256']==row['sha256'],{'group':group,'path':key[1]})
check('RUNNER_TEST_BINDINGS',receipt['runner_sha256']==p['runner_ref']['sha256']==release['component_review']['runner_sha256']=='61bdc69cdcf592af213c0e8c357a0a8976a3140bcd8a60a4731a1972f2d6a3ae' and receipt['ci_test_sha256']==p['ci_test_ref']['sha256']==release['component_review']['test_sha256']=='f3ba0b75b883545194696955d067a11d44a96fe90f9736edbf5fca968d27d631','Exact reviewed runner/test bytes also independently rehashed')
runner=read(ROOT/'scripts/run_offline_ci_v1.py');tree=ast.parse(runner);frozen=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FROZEN' for t in n.targets)))
exclusions=sorted(str((ROOT/'tests'/row[0]).resolve()) for row in frozen.values())
check('SIX_EXCLUSIONS',len(exclusions)==6 and receipt['six_frozen_excluded']==exclusions and receipt['imported_frozen_modules']==[] and r['frozen_modules_imported']==0,'AST literal compared with exact six retained exclusion paths')
for name,row in frozen.items():pin(ROOT/'tests'/row[0],{'bytes':row[1],'sha256':row[2]})
case_ids=receipt['case_ids'];ids=[(v['module'],v['class'],v['method']) for v in case_ids]
check('COLLECTION_COUNT',len(case_ids)==receipt['collected_case_count']==r['collected_case_count']==2771 and len(set(ids))==2771,'2771 unique module/class/method identifiers, not executed results')
check('EXCLUDED_CASES_ABSENT',not any(any(Path(f).stem in row['module'].split('.') for f in exclusions) for row in case_ids),'No case identifier uses a frozen excluded module stem')
check('NO_EXECUTION_OR_IMPORT_ERRORS',state['collection_calls']==1 and state['execution_entries']==state['test_or_setup_entries']==receipt['test_run_count']==receipt['setups_executed']==r['test_body_executions']==r['setup_or_framework_execution_entries']==0 and state['refusals']==state['collection_errors']==receipt['failed_test_placeholders']==r['guard_refusals']==r['import_errors']==[] and state['expected_barrier_registration'] is False,'Retained profiler/audit/loader counters; trusted-code observation, not adversarial proof')
snap=receipt['import_context_snapshots'];check('CONTEXT_RESTORED',snap['pre_context']==snap['after_context'] and r['namespace_context_restored'] is True,'Exact full recorded sys.path/tests namespace/owned-finder snapshots identical before/after')
for key in ['inside_before_discovery','inside_after_discovery_or_stop']:
 s=snap[key];ns=s['tests_namespace'];check('INSIDE_NAMESPACE:'+key,ns['present'] and ns['search_locations']==ns['spec_search_locations']==[{'kind':'TECHNICAL_PATH','path':str(ROOT/'tests'),'resolved':str(ROOT/'tests')}] and len(s['owned_namespace_finders'])==1,'Verified owned tests namespace present inside context')
check('BARRIER_CLOSED',receipt['barrier_collecting_after_return'] is False and state['phase']=='CLOSED','Retained child barrier/context final state')
stdout=read(E/'historical-python312-collection-v1_2.stdout');stderr=read(E/'historical-python312-collection-v1_2.stderr');prefix=b'HISTORICAL_COLLECTION_RECEIPT_V1_2='
summary=json.loads(stdout.removeprefix(prefix).strip());receipt_raw=read(E/'owned-temp-python312/collection-receipt.json')
check('STDOUT_RECEIPT_BINDING',stdout.startswith(prefix) and len(stdout.splitlines())==1 and summary['artifact_bytes']==len(receipt_raw)==569875 and summary['artifact_sha256']==sha(receipt_raw) and summary['status']==receipt['status']=='PASS_HISTORICAL_COLLECTION_ONLY' and summary['collected_case_count']==2771 and summary['test_run_count']==summary['setup_executions']==summary['refusal_count']==0 and stderr==b'','Single safe stdout summary hashes full retained JSON receipt; empty stderr')
check('SUPERVISOR_CONSISTENT',supervisor==final['execution']==r['supervisor'] and supervisor['returncode']==0 and supervisor['reason'] is None and supervisor['reaped'] is True and supervisor['captured_bytes']==len(stdout)+len(stderr)==r['console_bytes']==376,'Exit0, reaped and recorded captured console bytes agree')
check('ACTUAL_BOUNDS',0<receipt['elapsed_seconds']<supervisor['elapsed_seconds']<120 and state['reads_reserved']==r['late_guard_reads_reserved_bytes']==32921178<268435456 and state['writes']==0 and summary['guarded_write_bytes_including_artifact']==len(receipt_raw)<33554432 and len(stdout)+len(stderr)<524288,'CPU120 enforced by reviewed child RLIMIT; actual CPU duration is unrecorded/null, not invented. Late IO counters exclude bootstrap.')
opened=state['open_files'];post_open={v['path']:v for v in post['opened_identity_checks']}
check('OPENED_IDENTITY_SET',len(opened)==len(post_open)==r['binding_checks']['opened_stat_identities']==567 and set(opened)==set(post_open),'All567 retained opened-file identities correspond to post-check entries')
for path,identity in opened.items():
 pp=Path(path);st=pp.stat();now={'dev':st.st_dev,'ino':st.st_ino,'size':st.st_size,'mtime_ns':st.st_mtime_ns}
 check('OPEN_STAT:'+path,now==identity and post_open[path]['identity_matches'] is True,'Stat-only identity match; no opened bytecode body read/rehashed')
check('NO_FORBIDDEN_OPEN_PATHS',not any('.venv-e01' in path or Path(path).is_relative_to(ROOT/'data') or Path(path).name.startswith('.env') for path in opened),'Captured paths contain no unaccepted E01 target, raw data or credential files')
check('HISTORICAL_ONLY',receipt['python']=='3.12.14' and receipt['pypdf_metadata_version']=='6.10.0' and receipt['sys_prefix']==str(ROOT/'.venv') and receipt['historical_environment_only'] is True and receipt['current_ci_qualification'] is r['current_ci_qualification'] is False and final['research_or_current_ci_acceptance'] is False,'No qualification for pypdf7.0.1, current full CI, test execution or E01 runtime')
metadata_text=read(ROOT/'.venv/lib/python3.12/site-packages/pypdf-6.10.0.dist-info/METADATA').decode();check('HISTORICAL_METADATA','\nVersion: 6.10.0\n' in metadata_text,'Registered historical dependency metadata only')
check('NO_NEW_MODEL_INSTALL',r['new_model_calls']==r['installation_calls']==0 and r['model_cost_USD']=='0','Retained child guarded source and observed zero-refusal collection; reviewer performs only data reads/stat/AST')
check('E01_CANDIDATE_COLLECTION_ONLY',sum(v['module'].split('.')[-1]=='test_e01_pypa_fixture_harness_candidate_v1_20261116' for v in case_ids)==24,'Own E01 candidate has24 collected methods, no test-body entries; this audit certifies no E01 execution or harness correctness')
limits={'review_read_bytes_cap':67108864,'review_wall_CPU_seconds_cap':120,'review_console_bytes_cap':262144,'review_evidence_write_bytes_cap':4194304}
summary_out={'kind':'INDEPENDENT_CLOSED_COLLECTION_REVIEW_CHECKS','checks':checks,'review_logical_read_bytes':reads,'review_elapsed_seconds':time.monotonic()-START,'review_CPU_seconds':time.process_time()-CPU,'limits':limits,'reviewed_source_refs':pins,'no_child_or_test_rerun':True}
raw=json.dumps(summary_out,indent=2,sort_keys=True).encode()+b'\n';assert len(raw)<4194304
(OUT/'checks.json').write_bytes(raw)
failed=[v for v in checks if v['result']!='PASS']
report={'TASK_ID':'INDEPENDENT_CI_HISTORICAL_COLLECTION_V1_2_ACTUAL_20261116','decision':'BLOCKED_CLOSED_EVIDENCE_BINDINGS' if failed else 'PASS_EXACT_HISTORICAL_COLLECTION_EVIDENCE_ONLY_NO_TEST_EXECUTION_OR_CURRENT_CI_QUALIFICATION',
 'scope':'Closed retained evidence from one historical Python3.12.14/pypdf6.10.0 collection child; reviewer reruns zero children/tests.',
 'checks_passed':len(checks)-len(failed),'checks_total':len(checks),'blocking_findings':failed,
 'source_report_ref':pins[str(source_report_path.relative_to(ROOT))],
 'evidence_ref':{'path':str((OUT/'checks.json').relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)},
 'evidence_summary':{'child_dispatches':1,'collected_unique_cases':2771,'monitored_test_setup_framework_entries':0,'errors_refusals':0,'excluded_modules':6,'imported_exclusions':0,'full_snapshot_restored':True,'receipt_bytes':569875,'child_elapsed_seconds':receipt['elapsed_seconds'],'supervisor_elapsed_seconds':supervisor['elapsed_seconds'],'actual_child_CPU_seconds':None,'console_bytes':376,'late_guard_read_bytes':32921178,'guarded_receipt_write_bytes':569875,'independent_input_hash_checks':504,'opened_identity_stat_checks':567},
 'NOT_RUN':['No test-body execution/full ordinary suite/full current CI/Linux qualification.','No PyPA fixture harness execution, installation, current E01 target or runtime qualification.','No independent historical child rerun or new source/model/network/key/owner activity.'],
 'limitations':['Trusted authored profiler/audit guards do not provide an adversarial sandbox.','Full captured namespace/path/finder snapshots match; historical receipt does not independently expose every restored importer-cache entry or preexisting module identity. Static finally code restores those structures; component acceptance is separate.','Actual child CPU duration is null;120-second RLIMIT is source-enforced, not a measured CPU claim.','Late read/write counters exclude process bootstrap. Post-open567 stat identities are not retrospective hashes of every imported bytecode body.','Counts show collected methods only. Own E01 source was included but this independent CI audit does not certify its correctness or test execution.','Historical pypdf6.10.0 cannot satisfy the separate current7.0.1 dependency contract.'],
 'review_accounting':{'logical_read_bytes':reads,'wall_seconds':time.monotonic()-START,'CPU_seconds':time.process_time()-CPU,'limits':limits,'model_cost_USD':0,'child_reruns':0,'test_runs':0},
 'FILES_CHANGED':[str(REPORT.relative_to(ROOT)),str((OUT/'checks.json').relative_to(ROOT)),str((OUT/'review_closed_evidence.py').relative_to(ROOT))],
 'REPRODUCTION_COMMANDS':['Read and rehash the exact source report, packet/release/control/receipt files and504 pinned inputs; stat-check567 captured paths. No launcher or collection/test invocation.'],
 'NEXT_UNBLOCKED_TASK':'Lead may record this scoped historical collection result. Full CI/test execution and E01 concrete harness qualification remain separate gated tasks.'}
rr=json.dumps(report,indent=2,sort_keys=True).encode()+b'\n';assert len(rr)+len(raw)<4194304;REPORT.write_bytes(rr)
print(json.dumps({'decision':report['decision'],'checks':len(checks),'blocked':len(failed),'read_bytes':reads,'report_bytes':len(rr),'report_sha256':sha(rr),'evidence_bytes':len(raw),'evidence_sha256':sha(raw)},sort_keys=True))
