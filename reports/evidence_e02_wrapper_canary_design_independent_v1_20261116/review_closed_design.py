"""Closed static JSON/hash/AST methods review. No owner/client execution."""
from pathlib import Path
import ast
import hashlib
import json
import os
import resource
import signal
import stat
import sys
import time
ROOT=Path.cwd();OUT=ROOT/'reports/evidence_e02_wrapper_canary_design_independent_v1_20261116'
START=time.monotonic();CPU=time.process_time();reads=0;checks=[];refs={};cache={}
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def timeout(*_):raise RuntimeError('AUDIT_TIME_CAP')
signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
def audit(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','ctypes.dlopen'}:raise RuntimeError('AUDIT_NO_EXTERNAL_EFFECT')
 if event=='import' and args and args[0].split('.')[0]=='civiclab':raise RuntimeError('AUDIT_NO_PRODUCTION_IMPORT')
sys.addaudithook(audit)
def check(name,condition,evidence):checks.append({'id':name,'result':'PASS' if condition else 'BLOCKED','evidence':evidence})
def raw(path,expected=None):
 global reads
 path=Path(path);path=path if path.is_absolute() else ROOT/path
 allowed=path.is_relative_to(ROOT/'reports') or path.is_relative_to(ROOT/'src') or path==ROOT/'configs/e02_wrapper_crossmodel_v1_20261115.json'
 closedbase=ROOT/'data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01'
 allowed=allowed or path in {closedbase/'retained-journal/failure.json',closedbase/'post-run-owner-export.local.json',closedbase/'packet.local.json'}
 if not allowed or path.name.startswith('.env') or any(p.is_symlink() for p in (path,*path.parents)):raise RuntimeError('AUDIT_READ_SCOPE')
 if path not in cache:
  before=path.stat()
  if not stat.S_ISREG(before.st_mode) or before.st_size>4194304 or reads+before.st_size+1>67108864:raise RuntimeError('AUDIT_READ_CAP')
  reads+=before.st_size+1
  with path.open('rb') as stream:
   opened=os.fstat(stream.fileno());body=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
  ident=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
  if ident(before)!=ident(opened) or ident(opened)!=ident(after) or len(body)!=before.st_size:raise RuntimeError('AUDIT_READ_DRIFT')
  cache[path]=body
 body=cache[path];ref={'path':str(path.relative_to(ROOT)),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()};refs[ref['path']]=ref
 if expected is not None:check('PIN:'+ref['path'],(len(body),ref['sha256'])==(expected['bytes'],expected['sha256']),ref)
 return body
load=lambda path,expected=None:json.loads(raw(path,expected))
canonical=lambda obj:json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
hashobj=lambda obj:hashlib.sha256(canonical(obj)).hexdigest()
p='reports/E02_WRAPPER_CROSSMODEL_CANARY_V1_PREPARATION_20261116.json'
r=load(p,{'bytes':17276,'sha256':'fd5a03a250ff21c12c14ca082627ce1d494160e0fb8049ceeedfe86494649a93'})
for row in r['OUTPUT_ARTIFACTS']:raw(row['path'],row)
d=load(r['minimal_reviewable_design_ref']['path'],r['minimal_reviewable_design_ref'])
c=load(r['retained_evidence']['closed_preflight_ref']['path'],r['retained_evidence']['closed_preflight_ref'])
stop=load(r['retained_evidence']['existing_stop_report_ref']['path'],r['retained_evidence']['existing_stop_report_ref'])
prior=load(r['retained_evidence']['independent_partial_review_ref']['path'],r['retained_evidence']['independent_partial_review_ref'])
check('PRIOR_RETAINED_SCOPE',prior['decision']=='PASS_PARTIAL_RETAINED_EVIDENCE_ACCOUNTING_AND_REPLAY_ONLY','Independent partial review exact pinned; no new full owner replay claimed')
inputs={row['path']:load(row['path'],row) for row in c['input_refs']}
base='data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/'
failure=inputs[base+'retained-journal/failure.json'];export=inputs[base+'post-run-owner-export.local.json'];packet=inputs[base+'packet.local.json'];protocol=inputs['configs/e02_wrapper_crossmodel_v1_20261115.json']
# Raw private fields remain transient only. Emit aggregate metadata/booleans,
# never owner IDs, receipts, generation IDs, responses, prompt or header values.
owner=export['wrapper_crossmodel'];rows=export['rows'];witnesses=owner['witnesses']
attempts=[]
for receipt in owner['receipts']:
 row=rows[receipt];attempts.append((int(row['context']['unit_id'].rsplit('-',1)[1]),row))
attempts.sort(key=lambda v:v[0])
check('CLOSED_COUNTS',len(rows)==194 and len(export['history'])==1180 and len(attempts)==45 and len(witnesses)==44,'194rows/1180events/45fifthreservations/44committedwitnesses')
check('ORIGINAL_ORDER_PREFIX',[i for i,row in attempts]==list(range(45)) and [w['execution_order'] for w in witnesses]==list(range(44)),'No skipped/reordered0..44; witness0..43')
check('ORIGINAL_COMMIT_STATUSES',all(row['status']=='PHASE_COMMITTED' for i,row in attempts[:44]),'All44priorcommittedrows retained')
failed=attempts[-1][1]
check('FAILED_SLOT44_HOLD',attempts[-1][0]==44 and failed['status']=='UNCERTAIN' and failed['reserved']==failed['charged']==775 and failed.get('generation_id') is None,'Uncertain775;generation/costnotinvented')
check('CUMULATIVE_IO_COUNTS',tuple(failure[k] for k in ['model_POST_attempts','statistics_GET_attempts','catalog_GET_attempts'])==(45,44,10),'Failed-phase diagnostic1POST is not full batch count')
check('OLD_STOP_STATE',owner['stopped'] is True and export['unfinished']==5 and owner['historical_unfinished']==4 and owner['pending'] is None,'Stoppedoriginalwith5protectedunfinished; no fake reset to4/0')
check('UNKNOWN402_CAUSE',failure['diagnostic']['transport']['http_status']==402 and failure['diagnostic']['reported_provider_cost_microusd'] is None and failure['diagnostic']['reserved_microusd']==775,'No account cause/provider cost inferred')
limits=packet['policy']['limits'];check('ORIGINAL_CAPS',(limits['new_model_POSTs'],limits['new_statistics_GETs'],limits['catalog_GETs'],limits['lifetime_dispatches'])==(80,240,16,229),'Originalabsolutehardcaps80/240/16/lifetime229')
check('ORIGINAL_FINANCIAL_CAPS',(limits['shared_microusd'],limits['cumulative_E02_microusd'],limits['new_batch_microusd'],limits['E01_microusd'])==(5000000,1000000,200000,0),'Existing$5/$1/$0.20/$0E01; not replenished')
check('OWNER_LIFETIME_SEED',export['consumed']['dispatches']==194 and len(rows)==194,'Reservations/lifetime194remainconservativeevenifPOSTwasambiguous')
check('SLOT45_METADATA',tuple(protocol['jobs'][45][k] for k in ['execution_order','model_key','phase','visibility','baseline_execution_order','base_execution_order','pair_seed'])==(45,'B','post','OMITTED',13,22,2315288556),'Only45/B/post/OMITTED/baseline13/base22/frozenseed')
check('BASELINE13_AUTHENTICATED',any(w['execution_order']==13 and w['phase']=='pre' and w['status']=='ANSWER' and rows[w['receipt']]['status']=='PHASE_COMMITTED' and hashobj(rows[w['receipt']]['context'])==w['context_hash'] and rows[w['receipt']]['context']['payload_hash']==w['payload_sha256'] and rows[w['receipt']]['generation_id']==w['generation_id'] for w in witnesses),'Closedwitness+rowcontext+payload+generationbindingsmatch; noanswercontentemitted')
check('SLOT45_NOT_RESERVED',not any(i==45 for i,row in attempts) and c['frozen_dispositions'][45]['disposition']=='NOT_ATTEMPTED','No old45row; not authority to generate new baseline')
protected=[row for row in rows.values() if row['status']!='PHASE_COMMITTED']
check('PROTECTED_HOLD_SET',len(protected)==5 and failed in protected,'5exactunfinishedderivedfrompinnedfullrowmap; identitiesnotpubliclycopied')
fifth=sum(row['charged'] for i,row in attempts);used=export['consumed']
check('CLOSED_CHARGES',fifth==3928 and used['total']==used['modules']['E02']==16149 and used['modules']['E01']==0,'Conservativeroundedchargesandholds;notproviderinvoiceequivalence')
check('HYPOTHETICAL_RESERVE',limits['per_call_microusd']==1785 and fifth+1785==5713 and used['total']+1785==17934,'Hypotheticalnewmaxnotfreshquote/reservation')
check('ONE_SLOT_AGGREGATES',d['aggregate_arithmetic']['one_canary']=={'POSTs':46,'statistics_GET_max':47,'catalog_GET_max':12,'owner_lifetime_dispatches':195},'45+1,44+3,10+2,194+1withinoriginalabsolutehardcaps')
check('FULL_SUFFIX_CATALOG_CONFLICT',[n for n in limits['catalog_refresh_before_slots'] if n>=45]==[50,60,70] and 10+2+2*3==18>16,'Full35requires18catalogunderunchangedschedule;outofscope')
check('COUNTER_SEED',d['typed_continuation_scope_schema']['parent_binding']['original_counter_seed']=={'POST':45,'catalog_GET':10,'statistics_GET':44},'Preserveoldphysicalattemptcountsasimmutableowner-wideseed')
check('CANARY_SCOPE',d['smallest_scope']['sole_allowed_order']==[45] and d['smallest_scope']['baseline_global_slot']==13 and d['smallest_scope']['canary_after_one_dispatch']=='TERMINAL_NO_IMPLICIT_SLOT46','Exactlyoneoriginalglobalposition;no44retry/no46authority')
check('NO_AUTHORITY_OR_CODE',d['actual_authority'] is False and r['actual_dispatch_authority'] is False and d['kind'].startswith('PRECODE_'),'Methodsproposalonly; noimplementation/mocks/releaseinferred')
source_evidence={}
for name,row in c['source_refs'].items():
 source=raw(row['path'],row);tree=ast.parse(source);source_evidence[name]={'ref':refs[row['path']],'tree':tree,'text':source.decode()}
owner_tree=source_evidence['wrapper_crossmodel_v1_owner']['tree'];owner_class=next(n for n in owner_tree.body if isinstance(n,ast.ClassDef) and n.name=='WrapperCrossmodelOwnerV1');methods={n.name:n for n in owner_class.body if isinstance(n,ast.FunctionDef)}
for label,node,needle in [('LEGACY_STOPPED_RESERVE',methods['reserve_next'],"study['stopped']"),('LEGACY_GRANT_UNFINISHED',methods['_apply'],"state['unfinished'] != 4"),('LEGACY_START149',methods['_apply'],"state['consumed']['dispatches'] != 149")]:
 snippets=[{'line':n.lineno,'condition':ast.unparse(n.test)} for n in ast.walk(node) if isinstance(n,ast.If) and needle in ast.unparse(n.test)]
 check(label,bool(snippets),snippets)
reserve_text=ast.unparse(methods['reserve_next'])
check('ATOMIC_BATCH_PRIMITIVE_PRESENT',"BEGIN IMMEDIATE" in reserve_text and '_append_batch' in reserve_text and "('RESERVE'" in reserve_text and 'GRANT' in reserve_text,'Existinggrant+reserveatomicbatchexistsasreusablestoragepattern;nolegacyhandlerstopbypass')
core_tree=source_evidence['wrapper_crossmodel_v1']['tree']
for name,needle in [('_walk','FAILED_UNCERTAIN'),('_validate_records',"halt and status != 'NOT_ATTEMPTED'")]:
 node=next(n for n in core_tree.body if isinstance(n,ast.FunctionDef) and n.name==name);check('LEGACY_ENVELOPE:'+name,needle in ast.unparse(node),'Originalabsorbinghaltvalidationremainsunchanged')
production=raw('src/civiclab/production_owner_v4.py').decode();common=raw('src/civiclab/common.py').decode()
for needle in ['generation already consumed owner-wide','known cost reduced','checkpoint changed settled charge','owner lifetime dispatch count exhausted','owner lifetime ceiling exceeded','single statistics intent required for settlement']:
 check('BASE_FINANCE:'+needle,needle in production,'Requiredexistingrow/generation/statistics/cost/lifetimeinvariant;newtypedbranchmustreusewithoutweakening')
check('CANONICAL_HASH_MATCH_SOURCE',"sort_keys=True" in common and 'allow_nan=False' in common and 'separators=(",", ":")' in common,'ReviewonlyreimplementedcanonicalJSONhashforclosedbindings;noimport')
# Methods-level invariants are commitments in the design; no financial event
# interpreter, DB, owner class, executable mock or transport is run here.
text=json.dumps(d,sort_keys=True)
clauses=[('SAME_OWNER_NO_RESET','same existing owner identity; never create/reset an owner'),
 ('EXACT_PROTECTED_SET','exact protected set'),('GLOBAL_ALIAS_SLOT_INDEX','Global duplicate index keyed by original study binding+order'),
 ('ATOMIC_GRANT_RESERVE','Same owner lock+transaction'),('DURABLE_ATTEMPTS_BEFORE_IO','Durably consume each catalog/billing GET attempt before transport'),
 ('ALL_BRANCH_AGGREGATES','all attempts across branches exactly once'),('NO_PARENT_UNSTOP','Never serialize a fabricated full80protocol/envelope or unstop parent'),
 ('NO_POST_RETRY','noPOSTretry'),('UNIQUE_GENERATION_CLAIMS','Unique generation/statistics claims'),('ORIGINAL_COMPILER_BINDING','Exact original compiler/payload/baseline/seed'),
 ('NO_UNCHANGED_LEGACY_COMMIT','Legacy commit_survey cannot be called unchanged'),('EXACT_CUMULATIVE_FINANCE','combined settled+holds and parent study cumulative spend')]
for label,needle in clauses:check('DESIGN:'+label,needle in text,'Exactdesignclausepresent;implementationsafetyremainsNOT_RUN')
bounds=d['typed_continuation_scope_schema']['bounds']
check('TYPED_CAPS',bounds=={'E01_microusd':0,'E02_cumulative_microusd':1000000,'fifth_cumulative_microusd':200000,'new_POST':1,'new_catalog_GET':2,'new_statistics_GET':3,'parent_POST_total':80,'parent_catalog_GET_total':16,'parent_statistics_GET_total':240,'shared_cumulative_microusd':5000000},'Closednewandparentcaps; originalreferencedlifetime229mustalsoapply')
runtime=d['proposed_future_runtime_bounds_not_released']
expected={'model_POST':1,'POST_retries':0,'statistics_GET':3,'catalog_GET':2,'catalog_retries':0,'operation_wall_seconds_proposed':240,'operation_CPU_seconds_proposed':60,'phase_wall_seconds':120,'price_age_seconds':900,'input_token_bound':8192,'output_token_bound':256,'per_call_reservation_ceiling_microusd':1785}
for name,value in expected.items():check('FUTURE_LIMIT:'+name,runtime[name]==value,'Designconstraintonly; notexecuted/enforcedbythisreview')
check('404_ONLY_FINITE_BILLING',runtime['billing_retry_statuses']==[404] and runtime['billing_wait_schedule_seconds']==[10,10,20],'Atmost3GETs;maxnotguaranteeallfit120s;eachphasegatecanstopconservatively')
check('FRESH_AND_CANCEL','before every external operation' in runtime['cancellation'] and 'full required phase' in runtime['cancellation'] and 'Preserve new hold' in runtime['cancellation'],'Noexpiredlease/price/fallback/timeout/resend;actualproofsnotacquired')
check('NO_NEW_HUMAN_GRANT','not a new human spending grant' in d['authority_interpretation'],'Standingownerlimitsapply;independentdesignPASSisnotleadexecutionrelease')
check('CONTINUATION_ONLY_ENVELOPE',d['continuation_envelope_schema']['records'].startswith('at most one original order45') and d['continuation_envelope_schema']['original_full80_analysis']=='NOT_RUN_INCOMPLETE','Onecontinuation-onlyenvelope;original80haltstillrejectsattemptafter44')
check('AUTHOR_APPLICATION_BYTE_COUNT',sum(row['bytes'] for row in c['input_refs'])+sum(row['bytes'] for row in c['source_refs'].values())==r['test_and_resource_bounds']['preflight_application_bytes_read']==4144868,'Exactdeclaredclosedinputsum;authorhelpernotrerun')
failed_checks=[check for check in checks if check['result']=='BLOCKED']
result={'kind':'INDEPENDENT_CLOSED_CANARY_METHODS_REVIEW','decision':'BLOCKED_CLOSED_DESIGN_EVIDENCE_MISMATCH' if failed_checks else 'PASS_EXACT_ONE_SLOT_DESIGN_ONLY_IMPLEMENTATION_NOT_RUN_NO_EXECUTION_RELEASE',
 'checks':checks,'checks_total':len(checks),'checks_passed':len(checks)-len(failed_checks),'blocking_evidence_checks':failed_checks,
 'input_refs':refs,'safe_closed_summary':{'POST':45,'stats':44,'catalog':10,'rows':194,'history_events':1180,'responses':44,'protected_unfinished':5,'slot44_uncertain_hold':775,
 'canary_slot':45,'baseline':13,'configuration':'B','phase':'post','visibility':'OMITTED','original_lifetime_cap':229,'new_max_totals':{'POST':46,'stats':47,'catalog':12,'lifetime':195},'full35catalog':18,'catalog_cap':16,
 'financials_hypothetical_only':{'old_fifth_including_hold':3928,'old_global_including_holds':16149,'one_call_max':1785,'fifth_after_max_reserve':5713,'global_after_max_reserve':17934}},
 'critical_implementation_obligations_not_tested':[
  'Canonical parent identity is original owner+original stopped study/packet/protocol+slot45, never a mutable current head, branch/run ID or output directory. Atomic OPEN/current-head admission and attempt/grant reducers must reject or share consumed state across aliases; nofresh2GETbudgetperalias.',
  'One owner-wide reducer seeds45/44/10exactlyonce and adds everynewtypedintent once beforeIO. Per-canary1/3/2andparent80/240/16plusoriginalowner229lifetimeallapply across aliases, failures, retries and reopen attempts. Declared ordinal cannot be reused to re-enable transport.',
  'Underexistingownerlock+BEGINIMMEDIATE, grant/global-slot claim/exact reserve and durable row/counter publication commit in one batch; crash before commit publishesnone, crash after commit cannot retransmit. Single-use POSTcap/journal intent and durable GETintent precede everytransport.',
  'Re-derive five protected unfinished row identities/charges from current same-owner verified replay; preserve all oldrows/study stop/claims/witnesses, allowonlynewrow/witness. Fresh current owner ancestry is mandatory; closedexportisnotliveattestation.',
  'Dispatchnewtypedtransitions/commit beforelegacyoriginalstoppedhandler; delegate financial row/generation/claim/rounding/overrun rules without fabricatingunfinished0/4orreactivatingparent. Materializedcharges and event replay must agree.',
  'Fresh fixedmodel/provider/route price terms/proofs, exactcompiler/payload/baseline13andseed, finite240/60operationand120phase,900priceage;429/402/timeouts/malformed/unknownbilling/providerdriftstopwithconservativeholds;404onlyfinitevisibilitylookup retries.',
  'Stopafteroneattempt; continuationenvelopeonlyslot45orzeroifpre-dispatchstop. Neitherold80envelope/fullanalysisnorAzureAavailability/402cause/humanpoliticaleffectsareinferred.'
 ],
 'not_run':['Noowner/client/executorimportorinstance/DBeventreplay/mocks/concurrency/crashfaultinjection.','Nofreshprices/API/statistics/catalog/model/credential/liveowner/accountaccess.','Nopaidexecution/currentownerreservationorexecutionrelease.'],
 'review_resources':{'content_read_bytes':reads,'cap_bytes':67108864,'CPU_seconds':time.process_time()-CPU,'wall_seconds':time.monotonic()-START,'CPU_wall_cap_seconds':120},
 'privacy':'PrivateclosedJSONheldtransientlyonly;noownerIDs/receipts/generationIDs/prompts/answers/providerheaderscopied. Safeaggregatesandtechnicalsourcepins/ASTconditionsonly.',
 'cost_USD':0}
body=json.dumps(result,indent=2,sort_keys=True).encode()+b'\n'
with (OUT/'CLOSED_REVIEW_CHECKS.json').open('xb') as stream:stream.write(body)
print(json.dumps({'decision':result['decision'],'checks':len(checks),'blocked':len(failed_checks),'read_bytes':reads,'CPU_seconds':time.process_time()-CPU,
 'evidence_bytes':len(body),'evidence_sha256':hashlib.sha256(body).hexdigest()},sort_keys=True))
