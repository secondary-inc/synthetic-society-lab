"""Freeze a source-only qualification proposal; never import candidate/owner."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,ast
ROOT=Path(__file__).resolve().parents[2]
EV=ROOT/'reports/evidence_e02_canary_full_replay_preparation_v1_20261117'
PRIOR_READS=16829595
used=0
pins=[]
def read(name):
 global used
 p=ROOT/name;n=p.stat().st_size
 if PRIOR_READS+used+n>32*1024*1024:raise RuntimeError('PREPARATION_32MIB_READ_LIMIT')
 used+=n;raw=p.read_bytes()
 if len(raw)!=n:raise RuntimeError('INPUT_CHANGED')
 pins.append({'path':name,'bytes':n,'sha256':hashlib.sha256(raw).hexdigest()});return raw
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
sha=lambda x:hashlib.sha256(x).hexdigest()
def ref(p):
 raw=p.read_bytes();return {'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)}
base='data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/'
raw=read(base+'post-run-owner-export.local.json')
if len(raw)!=3893676 or sha(raw)!='ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66':raise RuntimeError('CLOSED_EXPORT_PIN')
e=json.loads(raw);prev=None
for n,event in enumerate(e['history']):
 if event['sequence']!=n or event['previous']!=prev:raise RuntimeError('CLOSED_EVENT_CHAIN')
 prev=sha(canon(event))
if len(e['history'])!=1180 or len(e['rows'])!=194 or e['head']['head_hash']!=prev or e['head']['sequence']!=1179:raise RuntimeError('CLOSED_HEAD_COUNTS')
dep=json.loads(read(str((EV/'DEPENDENCY_MANIFEST.json').relative_to(ROOT))))
graph=json.loads(read(str((EV/'REPLAY_CALL_GRAPH.json').relative_to(ROOT))))
handoff=json.loads(read('reports/E02_WRAPPER_CROSSMODEL_CANARY_V1_CODE_HANDOFF_20261117.json'))
for item in handoff['FILES_CHANGED']:
 raw=read(item['path'])
 if len(raw)!=item['bytes'] or sha(raw)!=item['sha256']:raise RuntimeError('AUDITED_SOURCE_CHANGED')
 # No import or candidate invocation.
 ast.parse(raw,filename=item['path'])
index=json.loads(read(base+'retained-journal-index.local.json'))
indexref=pins[-1]
if indexref['sha256']!='38e778190c7b6f0e0689247cc97513b599cfb4c26df5c3958e2a12d8d0444148':raise RuntimeError('FIFTH_INDEX_PIN')
closed=ROOT/base/'retained-journal'
members=index['files']
if any(Path(name).name!=name or name in ('.','..') for name in members):raise RuntimeError('INDEX_NAME')
member_ok=set(p.name for p in closed.iterdir())==set(members) and all((closed/name).is_file() and not (closed/name).is_symlink() and (closed/name).stat().st_size==v['bytes'] for name,v in members.items())
current={'index':indexref,'closed_directory':str(closed.relative_to(ROOT)),'files':len(members),'declared_bytes':sum(v['bytes'] for v in members.values()),'closed_directory_regular_membership_and_size_match':member_ok,'payload_content_read_or_rehashed':False}
report={
'TASK_ID':'E02_CANARY_FULL_REPLAY_PREPARATION_V1_20261117',
'kind':'BOUNDED_STATIC_MINIMAL_INHERITED_REPLAY_FIXTURE_PROPOSAL',
'date_UTC':datetime.now(timezone.utc).isoformat(),
'decision':'PREPARATION_COMPLETE_QUALIFICATION_NOT_RUN_REGISTRATION_PREREQUISITE_UNLOCATED',
'activity':{'source_AST_and_closed_metadata_only':True,'owner_imports':0,'owner_verifier_invocations':0,'candidate_tests':0,'new_author_suite_attempts':0,'network_calls':0,'credential_reads':0,'current_live_owner_access':0,'Git_mutations':0,'model_cost_USD':0},
'resource_accounting':{'authorized_metadata_read_limit_bytes':33554432,'prior_metered_reads_bytes':PRIOR_READS,'this_freeze_metadata_reads_bytes':used,'cumulative_metadata_reads_before_final_evidence_hashing_bytes':PRIOR_READS+used,'write_limit_bytes':2097152,'read_method':'Each content read reserved exact stat size before read. Directory membership/stat checks are metadata only. Final report evidence hash reads separately counted below; no private journal bodies read.'},
'inputs':pins,
'facts':{'closed_export_events':1180,'closed_export_rows':194,'head_sequence':1179,'hash_chain_and_terminal_head_structurally_match':True,'semantic_row_replay_performed':False,'conservative_exposure_microusd':16149,'unfinished_holds':5,'existing_audited_source_files_unchanged':True,'actual_initial_study_recovery_branch':True},
'actual_inheritance':{'verification_order':['CanaryOwnerV1._verify','WrapperCrossmodelOwnerV1._verify','WrapperVisibilityOwnerV1._verify','CrossmodelRecoveryOwnerV1._verify','CrossmodelOwnerV1._verify','AlignmentOwnerV1._verify','StudyOwnerV1._verify','_AdditionalOwnerV1._verify'],'authoritative_loop':'_AdditionalOwnerV1._verify calls real self._empty(), then self._apply() for each event in original order with original hashchain and prefix state, and finally compares actual charges table with replayed rows. It does not adopt the exported final state.','required_constructor_checks':'ProductionOwnerV4.__init__ reads and validates guard/header, calls _location and _registration. _registration reads external bootstrap body, validates original namespace/UID/assertion/zero allowance/digests/time interval, and binds canonical body hash to header.registration_sha256.','scope_of_existing_tests':'CopiedOwner from author suite overrides _verify and _registration and seeds final state. It cannot establish this inherited loop or constructor behavior.'},
'registration':{'required_relative_to_fixture_owner_parent':'openrouter-v4-bootstrap.local.json','required_original_file_and_canonical_value_sha256':'920278f3258c856f60959cf7bd380a944cc09d797084552698dd7ae7024a54e9','availability':'Body not present in the inspected closed export, original actual scope listing or historical journal indexes; no matching retained registration body located in the bounded inspection. This is not an exhaustive disk-absence claim.','never_acceptable':'Do not invent original registration_id/review_hash/release_hash/UID/times, create fresh zero-bootstrap, alter owner/header/hash or bypass _registration. A digest alone cannot supply the missing original bytes.','prerequisite':'Lead must locate an already retained exact body or separately authorize a tightly scoped read-only closed capture of that one registration artifact. Current preparation explicitly did not access the live owner/registration.','UID':'Original account_uid must equal actual os.getuid() under unchanged validator; do not monkeypatch UID or rewrite original registration if it differs.'},
'reconstruction':[
{'artifact':'guard/header','source':'Pinned export.header','instruction':'Write canonical header into derived temporary owner-v4-guard.local.json and single-row SQLite header table. Canonical serialization was checked to equal recorded original guard file SHA256.','original_guard_sha256':'9f2ab0b4e44e10191fbad96dc5fca41eb79aaba6ca3066a2d9351de57d3f6d0a'},
{'artifact':'head','source':'Pinned export.head and recomputed terminal event hash','instruction':'Write a semantically identical derived owner-v4-head.local.json; let unchanged verifier compare parsed value. Do not assert original raw serialization.','derived_canonical_sha256':'48568b715a48fe92a93efc74b4768bd9ba72242d9a69e5c3852fd41ac9768ef7','recorded_original_raw_sha256':'548e631ee52f2dee735ea634b0cea870418066e272687479ecccab5491e31527','raw_hashes_equal':False},
{'artifact':'SQLite','source':'Pinned export.header, complete history and rows','instruction':'Create only required header(data TEXT), events(sequence INTEGER PRIMARY KEY,data TEXT,digest TEXT), charges(id TEXT PRIMARY KEY,data TEXT) tables in owned temp. Populate all1180 original event objects in original sequence with canonical hash digest and previous bindings, plus all194 original row values. This is a derived fixture DB; canonical event/row/head identity matters.','recorded_original_db_raw_sha256':'f3f6f64047960e42272d73f6f7dfe74d4766a220f85e0c9fa4cafd9c3d08dadf','cannot_claim_original_db_bytes':True},
{'artifact':'approvals/claims/keys/generations/projections','source':'Original event payloads and real _empty/_apply reducers','instruction':'Do not seed/export-import any of these final structures. Four original APPROVAL events and all studies/claims/transitions must rebuild them under unchanged inherited logic.'},
{'artifact':'location routing','source':'Original production_owner_directory and _location source checks','instruction':'Propose an explicit test-only patch of production_owner_v4.production_owner_directory returning the exact temp owner path. Preserve __init__, _location, _registration, _empty, _apply, _verify and all financial validators unchanged. Construct the actual CanaryOwnerV1 normally after route redirection. Reject any access to the original fixed OS home namespace. This route patch is a fixture boundary, not qualification of actual OS-home routing.'}
],
'journal_dependencies':{'minimal_historical_replay':'Source call graph and actual first study recovery=True indicate no historical raw journal required by the selected pre-canary event replay path. _entry returns via _recovery_entry, which uses original event-contained recovery metadata; the normal additional-test-v1 phase.local.json path is not selected. Historical continuation admission and commit factories read journal bodies, but those factories are not invoked merely by replaying their already committed events. This is static dependency evidence, not a successful full replay; unexpected reads must fail closed.','do_not_weaken':'Do not synthesize phase/checkpoint/response bodies to fill missing evidence or invoke admission/commit factories as a shortcut. Keep precise deny-on-unlisted I/O and log any unexpected fixed dependency as a blocker.','new_canary_events':'If a later qualification appends actual typed MOCK canary events, its _proofs/_check_commit do reopen the new temp journal. That is a separate extension of full historical replay and must use correctly joined mock raw/hash/proof/checkpoint files.','broader_historical_integrity':'All seven already-retained closed journal inventories are identified below; file membership and sizes match. Bodies were not read/rehashed in this preparation. Full raw-body admission/recommit revalidation is distinct from inherited event replay.'},
'closed_journal_inventory':dep['closed_journal_indexes']+[current],
'qualified_source_inputs':'Use exact unchanged source files/contracts/protocols bound to historical packet events. Protocol/compiler and source pin reads during reducer replay must be allowed narrowly from repo. No old code-contract checks may be mocked or refreshed. Current preparation pins source and frozen candidate; transitive closure must be reviewed before qualification.',
'proposed_one_bounded_qualification':{'status':'PROPOSAL_ONLY_NOT_AUTHORIZED_BY_THIS_PREPARATION','children_maximum':1,'runtime':'Python3.12.14 initially; other runtime is a separately scoped qualification if needed. Not an extra3.11 author-suite attempt.','limits':{'wall_seconds':300,'CPU_seconds':120,'logical_read_bytes':536870912,'temporary_write_bytes':67108864,'console_bytes':65536,'network_requests':0,'model_POSTs':0,'credential_reads':0},'steps':['Resolve exact registration-body prerequisite and obtain separate lead-reviewed qualification contract; preserve all prior frozen source and logs.','Before any child, pin original export, registration and all transitive source/config/review inputs. Deny sockets/subprocess/credential/live-owner access, allow only exact closed inputs and owned temporary writes; no environment credential inheritance.','Create derived DB/guard/head plus exact original registration under no-symlink temp layout. Explicitly redirect only production_owner_directory. No CopiedOwner, _verify/_registration/_empty overrides or preseeded final state.','Call normal CanaryOwnerV1 constructor and inherited _verify once against read-only/query_only derived DB. Do not append any new event, consume I/O allowance or create an actual release.','Require all1180 events accepted, semantic terminal head/194rows/fiveholds/conservative exposure/all7priorstudyprojections and192claims match closed export; assert parent stop remains true and canary branch absent.','Retain safe pass/fail stage labels, hashes/counters/resources and initial source pins only; private fixture data stays temporary/Git-ignored and is removed. No traceback locals, IDs, responses or raw exception text in public logs. Stop at first missing dependency/integrity error/bound; no retries or budget increase inferred.'],'limitations':['Resource caps are a bounded proposal, not measured feasibility; full loop timing/read needs remain unknown.','One untouched parent replay does not prove every new canary transition, final billing join or actual operational limits.','Temporary path routing is explicit; actual OS namespace, current ancestry and fresh real prices remain future live release gates.']},
'acceptance_criteria':[{'criterion':'Static dependency and retained-artifact preparation','status':'AUTHOR_PREPARATION_COMPLETE_NOT_INDEPENDENTLY_REVIEWED'},{'criterion':'Exact registration body available','status':'BLOCKED_NOT_LOCATED_IN_INSPECTED_CLOSED_ARTIFACTS'},{'criterion':'Full inherited1180event verification','status':'NOT_RUN'},{'criterion':'New canary source acceptance and live release','status':'NOT_RUN_SEPARATE_REVIEW_IN_PROGRESS'}],
'UNRESOLVED_BLOCKERS':['Exact original registration body and permitted temp-routing qualification scope absent.','Transitive read closure and one untouched full historical verifier pass remain unqualified.','Current live-owner ancestry/account/provider/price evidence not established; no live authority.'],
'NEXT_UNBLOCKED_TASK':'Lead resolves original registration availability under a separate bounded evidence scope, reviews minimal fixture proposal, then assigns implementation/qualification. Audited canary code/tests stay frozen.',
'COST_USD_ACTUAL_OR_ZERO':0,
'REPRODUCTION_COMMANDS':['Executed static source-only inspect_closed_replay.py; it imports stdlib AST/JSON/hashlib only.','Executed freeze_preparation.py to validate exact closed event hashchain/metadata and freeze proposal; it does not import owner or execute candidate.','Read retained metadata evidence first; re-running helpers requires own bounded preparation scope and must not become an author-suite attempt.']}
# Account final public evidence reads exactly, with total write guard.
evidence=[]
for p in sorted(EV.iterdir()):
 if p.is_file():
  raw=read(str(p.relative_to(ROOT)));evidence.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)})
report['OUTPUT_ARTIFACTS']=evidence
report['resource_accounting']['cumulative_metadata_content_read_bytes']=PRIOR_READS+used
report['resource_accounting']['public_evidence_bytes_before_report']=sum(v['bytes'] for v in evidence)
blob=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
if sum(v['bytes'] for v in evidence)+len(blob)>2097152:raise RuntimeError('PREPARATION_WRITE_LIMIT')
out=ROOT/'reports/E02_CANARY_FULL_REPLAY_PREPARATION_V1_20261117.json'
if out.exists():raise RuntimeError('REFUSE_OVERWRITE')
out.write_bytes(blob)
print(json.dumps({'path':str(out.relative_to(ROOT)),'bytes':len(blob),'sha256':sha(blob),'cumulative_metadata_content_read_bytes':PRIOR_READS+used,'evidence_plus_report_bytes':sum(v['bytes'] for v in evidence)+len(blob),'candidate_execution':0,'owner_imports':0}))
