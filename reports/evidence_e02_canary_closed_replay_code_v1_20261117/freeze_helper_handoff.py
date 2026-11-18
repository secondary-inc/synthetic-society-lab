"""AST/hash-only code handoff. Does not import or invoke qualification helper."""
from pathlib import Path
import ast,json,hashlib,sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];EV=Path(__file__).resolve().parent
# Includes earlier bounded inspection, failed collector conservative reservation,
# final collector/prewarm and augmentation. Extra AST-display reads charged here.
used=32319597+23513+180395
LIMIT=67108864
inputs=[]
def read(p):
 global used
 p=Path(p);n=p.stat().st_size
 if used+n>LIMIT:raise RuntimeError('AUTHOR64MIB')
 used+=n;raw=p.read_bytes();inputs.append({'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'bytes':n,'sha256':hashlib.sha256(raw).hexdigest()});return raw
sha=lambda b:hashlib.sha256(b).hexdigest()
p=ROOT/'scripts/qualify_e02_canary_closed_replay_v1_20261117.py';raw=read(p);tree=ast.parse(raw,filename=str(p));helperpin=inputs[-1]
closure=json.loads(read(EV/'EXACT_CLOSURE_WITH_HELPER.json'));closurepin=inputs[-1]
dirfd=read(ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py');dirfdpin=inputs[-1]
for pin in closure['project_pins']:
 body=read(ROOT/pin['path'])
 if len(body)!=pin['bytes'] or sha(body)!=pin['sha256']:raise RuntimeError('PROJECT_CLOSURE_DRIFT')
 # Project code is parsed, never imported.
 if pin['path'].endswith('.py'):ast.parse(body)
source=raw.decode();functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
verify_calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='_verify']
constructors=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='CanaryOwnerV1']
popens=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Popen']
mutations=[]
for n in ast.walk(tree):
 if isinstance(n,ast.Assign):
  for t in n.targets:
   if isinstance(t,ast.Attribute) and isinstance(t.value,ast.Name) and t.value.id in ('production','owner','CanaryOwnerV1'):mutations.append(ast.unparse(t))
checks={'helper_AST_parses':True,'one_static_owner_verify_call':len(verify_calls)==1,'one_static_normal_constructor':len(constructors)==1,'one_static_Popen':len(popens)==1,'only_production_path_route_mutations':mutations==['production.production_owner_directory','production.production_owner_directory'],'real_preflight_before_candidate_import':source.index("stage='PREFLIGHT'")<source.index("from civiclab import production_owner_v4"),'no_CopiedOwner':'CopiedOwner' not in source,'no_live_scope_creation_during_preparation':not (ROOT/'data/processed/e02_canary_closed_replay_v1_20261117_01').exists(),'recursive_project_source_pins_match_now':True,'both_required_recovery_evidence_exact_paths':all(n in {q['path'] for q in closure['project_pins']} for n in ['docs/E02_RECOVERY_ADMISSION_V1_PROPOSAL.md','reports/INDEPENDENT_AUDIT_E02_RECOVERY_ADMISSION_V1_METHODS.json'])}
if not all(checks.values()):raise RuntimeError('STATIC_HANDOFF_CHECK')
constants={}
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LIMITS' for t in n.targets):constants['limits']=ast.literal_eval(n.value)
contract={'kind':'E02_CLOSED_REPLAY_EXECUTION_CONTRACT_V1','helper':{'bytes':helperpin['bytes'],'sha256':helperpin['sha256']},'closure':{'bytes':closurepin['bytes'],'sha256':closurepin['sha256']},'dirfd':{'bytes':dirfdpin['bytes'],'sha256':dirfdpin['sha256']},'limits':constants['limits'],'runtime':'3.12.14','scope':'PARENT_ONLY_1180_NO_NEW_EVENTS'}
contractraw=(json.dumps(contract,indent=2,sort_keys=True)+'\n').encode();cp=EV/'execution-contract.candidate.json'
if cp.exists():raise RuntimeError('REFUSE_OVERWRITE')
cp.write_bytes(contractraw)
review={'kind':'INDEPENDENT_CLOSED_REPLAY_HELPER_RELEASE_V1','reviewer_role':'independent_auditor','decision':'NOT_REVIEWED_NO_EXECUTION_RELEASE','contract_sha256':sha(contractraw),'helper_sha256':helperpin['sha256'],'closure_sha256':closurepin['sha256'],'independent_report_sha256':'NOT_YET_REVIEWED','lead_release':'NOT_RELEASED'}
(EV/'accepted-review.UNRELEASED-TEMPLATE.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n')
static={'kind':'AUTHOR_STATIC_AST_AND_INPUT_PIN_CHECKS_ONLY','checks':checks,'source_mutations':mutations,'candidate_imports':0,'candidate_verifier_calls':0,'helper_runtime_invocations':0,'guard_runtime_tests':0,'project_pin_count':len(closure['project_pins']),'stdlib_pin_count':len(closure['stdlib_pins']),'prewarm_module_count':len(closure['prewarm_modules'])}
(EV/'STATIC_CHECKS.json').write_text(json.dumps(static,indent=2,sort_keys=True)+'\n')
evidence=[]
for file in sorted(EV.iterdir()):
 if file.is_file():
  b=read(file);evidence.append(inputs[-1])
report={
'TASK_ID':'E02_CANARY_CLOSED_REPLAY_CODE_V1_20261117',
'kind':'FROZEN_UNEXECUTED_QUALIFICATION_HELPER_FOR_INDEPENDENT_CODE_GUARD_REVIEW',
'recorded_at_UTC':datetime.now(timezone.utc).isoformat(),
'decision':'AUTHOR_STATIC_PREPARATION_COMPLETE_HELPER_AND_REPLAY_NOT_RUN_NOT_RELEASED',
'FILES_CHANGED':[helperpin],
'OUTPUT_ARTIFACTS':evidence,
'INPUT_REFS':inputs[:4],
'REPRODUCTION_COMMANDS':{'already_executed':['.venv/bin/python -I -B -S reports/evidence_e02_canary_closed_replay_code_v1_20261117/collect_exact_closure.py (stdlib prewarm and AST/hash metadata only; original sibling-import resolver failure retained)','.venv/bin/python -I -B -S reports/evidence_e02_canary_closed_replay_code_v1_20261117/augment_runtime_closure.py (stdlib-only exact helper/descriptor prewarm closure augmentation)','python3 -B reports/evidence_e02_canary_closed_replay_code_v1_20261117/freeze_helper_handoff.py (AST/hash-only handoff)'],'proposed_future_only':'.venv/bin/python -I -B -S scripts/qualify_e02_canary_closed_replay_v1_20261117.py --contract-sha256 '+sha(contractraw)+' --review-sha256 <FUTURE_EXACT_ACCEPTED_REVIEW_RAW_SHA256>','gate':'No fixed actual scope/control/review exists. Root must obtain separate independent helper/guard PASS and exact lead execution assignment before staging future private controls. No invocation released by this handoff.'},
'TESTS_RUN_AND_RESULTS':{'static_checks':static,'qualification_helper_execution':0,'guard_runtime_or_mock_tests':0,'candidate_imports':0,'normal_constructor_calls':0,'owner_verify_calls':0,'new_author_suite_attempts':0,'static_collector_initial_stop':'Exact sibling script import collect_connectivity_billing_once was initially not resolved. Failure/source preserved; conservative6,696,865B read reservation counted. Corrected resolver adds only exact sibling .py path and AST-recurses it. No script or project package imported.','stdlib_prewarm':'43 literal standard-library modules prewarmed on3.12.14;247 exact origin/cache/executable files pinned,24,055,941 bytes. Imported project/candidate0.','closure':'69 exact project/config/script/evidence refs,1,125,733 bytes. Recursively resolves literal project imports across all AST scopes, explicit nested code_contract seeds and sibling script imports; no directory-wide source allowlist. Static closure may still miss dynamic data access; such access must stop future child.'},
'EXECUTION_CONTRACT':contract,
'execution_contract_raw_sha256':sha(contractraw),
'helper_architecture':{'supervisor':'300-second timer starts before preflight, external exact contract/review gate, rehash closure and closed input pins, reserve parent output before one O_EXCL invocation claim and single isolated child. Empty credential environment except PATH. Deadline/output cap kills and reaps same child; no retries.','child':'Exact3.12.14, core0, CPU119/120, wall bounded by remaining parent deadline. O_EXCL child marker prevents another child. Charges supervisor reads/output reservation into child shared counters. Rehashes exact sources/runtime/export/registration before any candidate import; standard-library-only prewarm is explicit review boundary.','guard':'Before private fixture creation/candidate import, installs exact-path Python audit guard, DirectoryFdGuard source compiled directly from reviewed bytes (not stale cache), wrapped Python streams and restricted descriptor operations. Denies sockets/process/exec/ctypes/mmap/environment changes, unlisted files/native extension imports, alias paths and non-temp writes. Only two exact SQLite opens allowed (materialization and immutable read-only). Exact uncreated cache projections avoid stale project bytecode.','SQLite':'Reserve48MiB logical write capacity for <=24MiB main DB plus rollback and24MiB native construction-read capacity before SQLite connect. PRAGMA max_page_count6144/page_size4096, DELETE journal, MEMORY temp, original bounded export only and parameterized inserts. Explicitly close materialization connection before chmod0400/freeze. Actual physical OS syscall volumes are not claimed from these logical reservations. Query-only immutable verifier connection has native file read reservation plus a SELECT-only proxy that charges all serialized returned payload bytes without altering rows.','actual_replay':'Normal CanaryOwnerV1 constructor and single original owner._verify call; all inherited class methods remain intact. Only production_owner_v4.production_owner_directory temporarily redirected, restored in finally. Derived header/events/charges rebuilt from closed export; no final replay state adopted. No new event, request, packet, price proof, financial mutation or historical journal setup.','acceptance':'Exact head/history/194rows/192claims/consumed/fiveholds,7studyprojections/study_authorities/active approval/parentstop/no newcanarybranch; protected method identities, frozen derived file hashes and project input hashes unchanged. All guards/caps accepted, fixture cleanup required.','safe_result':'Fixed stage/type/status/counters/boolean comparison data only; no exception args/locals, raw IDs/prompts/responses/registration or owner contents printed. Temporary data remain Git-ignored and removed. Supervisor captures bounded private safe JSON output/receipt.'},
'resource_boundaries':{'qualification_limits':constants['limits'],'content_read_scope':'Parent preflight read charges are inherited by child budget before further work; supervisor terminal reservations likewise included in child write counter. SQL native capacity reservations and serialized query result accounting are explicit.','prewarm':'Exact imported stdlib source/cache/native origins and executable are pinned and charged by whole-file preflight. Implicit interpreter/native-loader OS files and physical syscalls are outside Python-open accounting. No claim of complete whole-process measured I/O.','author_preparation_read_limit':67108864,'author_preparation_charged_content_read_bytes':used,'generated_evidence_write_limit':8388608,'generated_evidence_bytes_before_report':sum(x['bytes'] for x in evidence)},
'SOURCE_DATA_AND_LICENSE_NOTES':'Only source/AST and already retained closed metadata references used during author work; no raw respondent/publisher data or private registration/export contents copied into public evidence. Exact closed registration546B and export3,893,676B are only future fixed input refs; currentliveowner and credentials not read.',
'COST_USD_ACTUAL_OR_ZERO':0,
'activity':{'network_calls':0,'credential_reads':0,'current_live_owner_access':0,'candidate_execution':0,'qualification_children':0,'Git_mutations':0,'audited_canary_code_or_test_edits':0,'actual_qualification_scope_created':False},
'RISKS_AND_LIMITATIONS':['This is a static author handoff; helper guard, SQL accounting, child lifecycle, resource refusal and cleanup behavior have NOT been exercised. Independent reviewer must test these within separately assigned scope before any closed parent replay.','Python audit and trusted-code restrictions address accidental access, not arbitrary native adversarial code. Native SQLite logical reservations are distinct from physical I/O measurements.','Exact closure is finite/static; unknown dynamic reads or environmental drift stop without expanding allowances.','One full parent replay cannot accept new canary events, actual live launcher controls, fresh owner/price evidence or live authority. Original production canary implementation/test bytes stay frozen.','Original author3.11suite allowance remains consumed; this is a separate unexecuted3.12-only qualification proposal.'],
'UNRESOLVED_BLOCKERS':['Independent helper/guard/closure acceptance and exact one-child lead execution assignment missing.','Full inherited1180event semantic replay remainsNOT_RUN.','Actual canary launcher resource closure, current owner/price proofs and exact live release remain separateBLOCKED gates.'],
'NEXT_UNBLOCKED_TASK':'Independent auditor reviews exact helper, closure, descriptor/SQLite read/write accounting and source-only handoff. Lead retains Git/STATUS ownership and separately assigns one actual offline qualification only after acceptance.',
'acceptance_criteria':[{'criterion':'Author static helper/dependency freeze','status':'AUTHOR_STATIC_CHECKS_PASS'},{'criterion':'Independent helper and guard qualification','status':'NOT_RUN'},{'criterion':'Untouched inherited1180event actual replay','status':'NOT_RUN'},{'criterion':'Live execution authority','status':'NOT_RELEASED'}]
}
out=ROOT/'reports/E02_CANARY_CLOSED_REPLAY_CODE_V1_20261117.json'
if out.exists():raise RuntimeError('REFUSE_OVERWRITE')
blob=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
if len(blob)+sum(x['bytes'] for x in evidence)>8388608:raise RuntimeError('AUTHOR8MIB')
out.write_bytes(blob)
print(json.dumps({'path':str(out.relative_to(ROOT)),'bytes':len(blob),'sha256':sha(blob),'helper':helperpin,'closure':closurepin,'contract_raw_sha256':sha(contractraw),'static_checks':checks,'author_charged_reads':used,'evidence_plus_report_bytes':len(blob)+sum(x['bytes'] for x in evidence)}))
