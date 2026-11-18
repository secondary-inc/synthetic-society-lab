"""Preserve first unexecuted candidate and freeze static lifecycle correction."""
from pathlib import Path
import ast,json,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];EV=Path(__file__).resolve().parent
used=34252182
refs=[]
def read(p):
 global used
 p=Path(p);n=p.stat().st_size
 if used+n>67108864:raise RuntimeError('PREPARATION64MIB')
 used+=n;raw=p.read_bytes();refs.append({'path':str(p.relative_to(ROOT)),'bytes':n,'sha256':hashlib.sha256(raw).hexdigest()});return raw
sha=lambda raw:hashlib.sha256(raw).hexdigest()
old=json.loads(read(EV/'handoff-before-EOF-wait-correction.json'))
helper=ROOT/'scripts/qualify_e02_canary_closed_replay_v1_20261117.py';raw=read(helper);ast.parse(raw);hp=refs[-1]
closure=json.loads(read(EV/'EXACT_CLOSURE_WITH_HELPER.json'));cp=refs[-1]
for p in closure['project_pins']:
 raw=read(ROOT/p['path'])
 if len(raw)!=p['bytes'] or sha(raw)!=p['sha256']:raise RuntimeError('PROJECT_PIN_DRIFT')
raw=read(ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py');dp=refs[-1]
raw=read(EV/'execution-contract.candidate.json');contract=json.loads(raw);oldcontract=refs[-1]
contract['helper']={'bytes':hp['bytes'],'sha256':hp['sha256']}
blob=(json.dumps(contract,indent=2,sort_keys=True)+'\n').encode();out=EV/'execution-contract.v1_1.candidate.json'
if out.exists():raise RuntimeError('REFUSE_OVERWRITE')
out.write_bytes(blob);contractsha=sha(blob)
review={'kind':'INDEPENDENT_CLOSED_REPLAY_HELPER_RELEASE_V1','reviewer_role':'independent_auditor','decision':'NOT_REVIEWED_NO_EXECUTION_RELEASE','contract_sha256':contractsha,'helper_sha256':hp['sha256'],'closure_sha256':cp['sha256'],'independent_report_sha256':'NOT_YET_REVIEWED','lead_release':'NOT_RELEASED'}
(EV/'accepted-review.v1_1.UNRELEASED-TEMPLATE.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n')
# No runtime lifecycle/guard test or candidate import is performed.
static=json.loads(read(EV/'STATIC_CHECKS.json'));static['final_helper_AST_parses']=True;static['static_lifecycle_correction']='Ordinary EOF bounded-waits for exit before kill; supervisor interruptions preserve fixed reason and reap; final PASS checks observed CPU/wall and child read/write/guard/cleanup/verify counts.'
(EV/'STATIC_CHECKS_FINAL.json').write_text(json.dumps(static,indent=2,sort_keys=True)+'\n')
artifacts=[]
for p in sorted(EV.iterdir()):
 if p.is_file():read(p);artifacts.append(refs[-1])
old['recorded_at_UTC']=datetime.now(timezone.utc).isoformat();old['FILES_CHANGED']=[hp];old['OUTPUT_ARTIFACTS']=artifacts;old['EXECUTION_CONTRACT']=contract;old['execution_contract_raw_sha256']=contractsha
old['REPRODUCTION_COMMANDS']['proposed_future_only']='.venv/bin/python -I -B -S scripts/qualify_e02_canary_closed_replay_v1_20261117.py --contract-sha256 '+contractsha+' --review-sha256 <FUTURE_EXACT_ACCEPTED_REVIEW_RAW_SHA256>'
old['REPRODUCTION_COMMANDS']['already_executed'].append('python3 -I -B -S reports/evidence_e02_canary_closed_replay_code_v1_20261117/freeze_final_helper_delta.py (AST/hash-only final lifecycle correction freeze)')
old['TESTS_RUN_AND_RESULTS']['static_checks']=static
old['TESTS_RUN_AND_RESULTS']['pre_review_static_lifecycle_finding']='Before reviewer handoff, author found EOF could precede child termination and trigger premature kill. Preserved initial23663B helper and14056B handoff with exact hashes, corrected EOF bounded-wait/interruption/reap/final-resource acceptance, and generated new contract. No helper/runtime/guard/replay invocation occurred.'
old['resource_boundaries']['author_preparation_charged_content_read_bytes']=used
old['resource_boundaries']['generated_evidence_bytes_before_report']=sum(p['bytes'] for p in artifacts)
old['predecessors_preserved']=[p for p in artifacts if p['path'].endswith(('helper-before-EOF-wait-correction.py','handoff-before-EOF-wait-correction.json','STATIC_LIFECYCLE_FINDING.json','execution-contract.candidate.json'))]
old['author_frozen_version']='FINAL_STATIC_LIFECYCLE_CORRECTION_V1_1_NO_EXECUTION'
blob=(json.dumps(old,indent=2,sort_keys=True)+'\n').encode()
if len(blob)+sum(p['bytes'] for p in artifacts)>8388608:raise RuntimeError('PREPARATION8MIB')
# Exact previous report bytes are already preserved under OUTPUT_ARTIFACTS.
p=ROOT/'reports/E02_CANARY_CLOSED_REPLAY_CODE_V1_20261117.json';p.write_bytes(blob)
print(json.dumps({'path':str(p.relative_to(ROOT)),'bytes':len(blob),'sha256':sha(blob),'helper':hp,'closure':cp,'contract_sha256':contractsha,'author_charged_reads':used,'evidence_plus_report_bytes':len(blob)+sum(p['bytes'] for p in artifacts),'runtime_invocations':0,'candidate_imports':0}))
