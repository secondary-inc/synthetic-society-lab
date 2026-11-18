from pathlib import Path
import json,hashlib,datetime
base=Path('reports/evidence_independent_ci_allocation_v2_20261118')
def ref(p):
 p=Path(p);v=p.read_bytes();return {'path':str(p),'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}
handoff=Path('reports/CI_WORKLOAD_ALLOCATION_V2_HANDOFF_20261118.json');h=json.loads(handoff.read_bytes())
for r in h['source_refs']:assert ref(r['path'])==r
runs=[];controls=[]
for runtime in ('311','312'):
 lines=(base/('pure_corrected_'+runtime+'.log')).read_text().splitlines();result=json.loads(lines[-1]);assert result['tests_run']==66 and result['successful'] is False and 'FAILED (errors=2)' in lines
 assert sum(x.endswith(' ... ok') or x=='ok' for x in lines)==65
 runs.append({'runtime':runtime,'receipt':result,'full_suite_verdict':'FAILED_TWO_REVIEWER_EXPECTATION_SUBTEST_ERRORS','cases_passed':65,'tests_run':66,'failed_case':'IndependentAllocationControls.test_bad_job_clocks_refuse_before_any_dispatch','reason':'NaN/Inf rejected by canonical serializer ValueError before custom IsolationError. Reviewer asserted wrong exception class. No dispatch.','full66_green_claim':False})
 lines=(base/('nonfinite_'+runtime+'.log')).read_text().splitlines();control=next(json.loads(x) for x in lines if x.startswith('{') and json.loads(x).get('kind')=='INDEPENDENT_NONFINITE_REFUSAL_ONLY');receipt=json.loads(lines[-1]);assert control['status']=='PASS' and receipt['tests_run']==1 and receipt['successful'] is True;controls.append({'runtime':runtime,'control':control,'receipt':receipt})
r={'kind':'INDEPENDENT_AUDIT_CI_WORKLOAD_ALLOCATION_V2_20261118','status':'PASS_SCOPED_IMPLEMENTATION_AND_ACCOUNTING','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Exact4sourcepins; planning,coverage,startup,host,budget methods and inert controls. No fullhosted/heavy/native research execution.','handoff':ref(handoff),'source_refs':h['source_refs'],'static_baseline':json.loads((base/'STATIC_BASELINE_CHECKS.json').read_text()),'verified_host_and_artifact_refs':ref(base/'HANDOFF_AND_HOST_REF_CHECKS.json'),'implementation_findings':[
 '198ordinary modules assignedonce across8Linuxlanes plus6portable+4historical jobs=208. All197preallocation841 names retained, including all194ata3e plus3subsequentlyaccepted modules. One acceptedFECdiagnostic added dynamically. No originalresearchtest removed.',
 'Frozen groups,pins,socket_observation,historical_admission,run_frozen AST unchanged. Four no-site profiles bind exact test+installer source and actualchild no_site; otherordinary modules retain site. AddedfourDarwinMIME cases source-bound; threeportableorigin refusals cannot be forgedintoNOT_RUN.',
 'Only43of44priorCI modelbodies unchanged; one expectedhost-partition literal test legitimately includes newlyaddedfourthrule. Realfrozen/historical testsourcepins unchanged.',
 'SinglePython3.11/3.12 x9job matrix=18jobs,maxparallel4globally. Exactworkflowhardtimeouts sum27600seconds/runtime including27000Linux+600Darwin;55200both. No separateDarwinstrategy addsconcurrency.',
 'Linux reserves120seconds/artifacts perlane. Workflowclockrecordedbeforecheckout/setup; CLIrequiresfinite nonfuture jobclock; setupdeducted, childwallclampedremainingminus3;<=3remaining recordsERRORwithout dispatch. NaN/Inf canonicalserialization refusesbeforecustomvalidation. Existinggroupkill/reap preserved.',
 'Configbytes/SHA,6heavyrefs,fullbaseline and unique globaljobcoverage bound. Changed/unmeasuredfastsource uses explicit30secondplanningweight; no censoredtimeout treated as completion. LanePASS labels neverfullsuitePASS.',
 '27handoff/source/evidencerefs and16host/startup refs verified. Publicquarantine metadata hashchecked; V3 active test absent. Quarantinedcontents neitherreadnor executed.'
 ],'independent_full_pure_runs':runs,'corrected_nonfinite_only_controls':controls,'recovery_history':{
 'zero_test_wrappers':'Initial2processesran0cases due execnamespace mismatch; no acceptance claimed. Originalwrapper/logspreserved. Lead explicitlyauthorized2correctedfullsuiteprocesses.',
 'two_subtest_errors':'Corrected66runseach have65successfulcases and2errors inonewrongexpectationcase. Existingallow_nanFalseValueError isfailclosed. Lead authorized2smallrefusal-onlyprocesses;both PASSexacttype/stack/noPLAN/noRESERVATION/nodispatch. Full66failedlogsunmodified; nofullsuite rerun.',
 'static_review_assumptions':'Initiallyassumedall44oldCImodelbodiesidentical and197modulesata3e. Correctedexplicitgit/ASTevidence preserves43+1bodychange and194ata3e/197at841; no productdefectfromreviewerassertions.',
 'implementation_edits':0},'allocation':{'initial_zero_test_processes':2,'corrected_full_suite_processes':2,'full_suite_limits_each':'120CPU/120wall/64MiBread/32MiBscratch/256KiBconsole','additional_nonfinite_only_processes':2,'nonfinite_limits_each':'30CPU/30wall,samefile/scratchguards','actual_child_or_frozen_groups':0,'native_heavy_or_hosted_jobs':0,'currentowner_key_network_model_V3_calls':0,'cost_usd':0,'billing_note':'No hostedrun/purchase byreviewer; GitHubcompute bills notestimated orassertedzero.'},'acceptance':{'exact_scheduler_component':'PASS_SCOPED','coverage_host_startup_accounting':'PASS_SCOPED','full_hosted_matrix':'NOT_RUN','heavy_completion':'NOT_RUN','historical_runtime_qualification':'UNCHANGED_NOT_NEWLY_CERTIFIED','E02V3':'BLOCKED_QUARANTINED_UNEXECUTED','full_research_contract':'INCOMPLETE'},'limitations':[
 'Full66logs remainFAILED duewrongreviewerexceptionexpectation; separatelycorrectedcontrol establishes intendedrefusal. No66PASS history claimed.',
 'No actualGitHubLinux/Darwin,installerorheavylifecycle executed inreview. Largerfinitecaps are planningjudgments, notcompletionguarantees.',
 'Finalhostedacceptance requires allappropriatejobs andmatchingmanifests. PerlanePASS alone cannotprovefullsuite. Setup/timeout/unknownresults stayfailed.',
 'CLIrequiresjobclock; puremodels do not establish physicalstartup/syscall/native/process-tree closure. Fixedworkflowjobcaps and existing supervisor supplyouterbounds.',
 'QuarantinedV3 is notactiveorcertified. Thisreviewcannotresumeorcertify blockedcontinuation orfullresearchcontract.',
 'HostNOT_RUN remains explicit. No scientific/source-adoption/prospectiveforecast/persuasion ornewfinancialauthority follows fromCIreview.'
 ],'next':'Lead may commit exactaccepted4files andsafeclosedreviewevidence then trigger the one separatelyauthorized hostedmatrix; inspect complete receipts before claiming fullCIpass.','evidence':[ref(p) for p in sorted(base.iterdir()) if p.is_file()]}
p=Path('reports/INDEPENDENT_AUDIT_CI_WORKLOAD_ALLOCATION_V2_20261118.json');p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(ref(p)))
