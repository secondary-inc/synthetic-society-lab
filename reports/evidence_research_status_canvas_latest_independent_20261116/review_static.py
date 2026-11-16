"""Read-only evidence review. Never runs canvas, browser, model or research code."""
from pathlib import Path
from decimal import Decimal
import hashlib,json,re,resource,struct,time

ROOT=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
OUT=ROOT/'reports/evidence_research_status_canvas_latest_independent_20261116'
CANVAS=Path('/Users/joshua/.cursor/projects/Users-joshua-Documents-ChatGPT-synthetic-society-lab/canvases/research-status-latest-20261116.canvas.tsx')
start=time.monotonic();cpu=time.process_time();cache={};read_bytes=1048576
checks=[];refs={}
def check(name,value):
    checks.append({'name':name,'pass':bool(value)})
    if not value:raise AssertionError(name)
def read(path):
    global read_bytes
    path=Path(path);path=path if path.is_absolute() else ROOT/path
    if path not in cache:
        size=path.stat().st_size
        check('read allowance: '+str(path),read_bytes+size<=8388608)
        raw=path.read_bytes();read_bytes+=len(raw);cache[path]=raw
        refs[str(path)]={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return cache[path]
def doc(path):return json.loads(read(path))
def pin(row):
    raw=read(row['path'])
    check('pin: '+row['path'],len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'])
    return raw
qa=doc('reports/RESEARCH_STATUS_CANVAS_LATEST_QA_20261116.json')
source=pin(qa['canvas']).decode();check('expected managed canvas path',qa['canvas']['path']==str(CANVAS))
for row in qa['safe_mirrors']+[qa['source_checkpoint'],qa['qa_script'],qa['launcher_failure']]+qa['private_screenshots']:pin(row)
mirror=ROOT/'reports/evidence_research_status_canvas_latest_20261116'
check('safe mirror byte-identical',read(mirror/'STATUS.canvas.tsx.txt')==source.encode())
snapshot=doc(qa['source_checkpoint']['path']);render=doc(mirror/'render_receipt.json');width=doc(mirror/'width.json');types=doc(mirror/'typecheck.json')
check('render binds exact canvas',render['canvas']==str(CANVAS) and render['canvas_bytes']==len(source.encode()) and render['canvas_sha256']==qa['canvas']['sha256'])
check('zero recorded TS diagnostics',types['diagnostics']==render['typescript_diagnostics']==[] and qa['observations']['typescript_diagnostics']==0)
check('zero recorded browser errors',render['browser_errors']==[] and qa['observations']['browser_errors']==0)
check('four recorded checks',len(render['checks'])==qa['observations']['render_checks']==4)
check('narrow no document overflow',width['overflow']==0)
for row,expected in zip(qa['private_screenshots'],(1100,390)):
    raw=read(row['path']);check('PNG width: '+str(expected),raw[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>I',raw[16:20])[0]==expected)
check('source action local stub only',render['actions']==[{'type':'openFile','path':str(ROOT/'reports/OPENROUTER_KEY_AND_ACCOUNT_DIAGNOSIS_20261116.json')}] and not qa['observations']['native_host_openfile_tested'])
check('only fixed local recorded requests',[(v['method'],v['url']) for v in render['requests']]==[('GET','/'),('GET','/runtime.js'),('GET','/canvas.js'),('POST','/canvas/status-qa/action')])
script=read(qa['qa_script']['path']).decode()
for needle in ['fs.readFileSync(canvas','canvas_sha256:crypto.createHash','page.route','route.abort()','server.listen(0,\'127.0.0.1\'','source button dispatches']:
    if needle=='source button dispatches':continue
    check('QA mechanism '+needle,needle in script)
failure=doc(qa['launcher_failure']['path']);check('preserved launch failure before script',failure['shell_exit_code']==127 and failure['qa_script_started'] is False)
check('only SDK imports',re.findall(r'from\s+[\"\x27]([^\"\x27]+)',source)==['cursor/canvas'])
for forbidden in [r'\bfetch\s*\(',r'\bXMLHttpRequest\b',r'\bWebSocket\b',r'\beval\s*\(',r'dangerouslySetInnerHTML',r'\b(?:localStorage|sessionStorage|document\.cookie)\b',r'\bsk-or-v\d-',r'Bearer\s+[A-Za-z0-9]',r'EAA[A-Za-z0-9]{30}',r'\.local\.json',r'post-run-owner-export',r'raw_respondent']:
    check('source excludes '+forbidden,re.search(forbidden,source) is None)
check('no external URL literals',not re.search(r'https?://',source))
check('fixed root-prefixed openFile action','dispatch({ type: "openFile", path: ROOT + path })' in source)
paths=set(re.findall(r'(?:path|report):?=?(?:\s*)"((?:reports|data)/[^"\n]+)"',source))
for path in sorted(paths):check('local source action exists: '+path,(ROOT/path).is_file() and '..' not in Path(path).parts)
check('dated not live',all(v in source for v in ['November 16, 2026','10:27 a.m. EST','America/New_York','not a live monitor','source buttons open current local files']))
check('snapshot time matches frozen checkpoint minute',snapshot['updated_at_UTC'].startswith('2026-11-16T15:26:') and '10:27 a.m. EST' in source)
check('frozen head binding',qa['snapshot_code_head']=='94066df15d584f95cf8b22f115492edbbde2283e' and qa['snapshot_code_head'] in source)
manifest=doc(snapshot['git']['final_checkpoint_bundle_manifest'])
check('33 commits at frozen head',manifest['unpublished_commits']==33 and manifest['head']==qa['snapshot_code_head'] and 'localCommits: 33' in source)
check('last remote unchanged',manifest['prerequisite_remote_head']==snapshot['git']['last_remote_verified_head'] and manifest['prerequisite_remote_head'] in source)
pin(manifest['bundle']);check('retained bundle verification scoped',manifest['git_bundle_verify']=='PASS' and manifest['sole_head_verified'] and 'not GitHub delivery or external publication' in source)
studies=snapshot['e02_completed_live_studies'];fifth=snapshot['e02_fifth_study'];closed=fifth['closed_observation']
for row in studies:
    pin(row['report']);pin(row['independent_review'])
    check('study displayed: '+row['study'],row['study'] in source and ('count: '+str(row['model_generations'])) in source and row['verified_model_usage_USD'] in source)
check('first four counts 147',sum(v['model_generations'] for v in studies)==147 and '147 responses / $0.0098213' in source)
check('first four costs exact',sum(Decimal(v['verified_model_usage_USD']) for v in studies)==Decimal('0.0098213'))
check('191 recorded responses',147+closed['successful_responses']==snapshot['e02_total_research_generations']==191 and 'researchResponses: 191' in source)
check('total verified invoices exact',sum(Decimal(v['verified_model_usage_USD']) for v in studies)+Decimal(closed['verified_model_usage_USD'])==Decimal(snapshot['e02_verified_research_model_usage_USD'])==Decimal('0.0129589') and 'invoicedResearchUSD: "0.0129589"' in source)
check('fifth denominator and accounting',closed['successful_responses']==44 and fifth['maximum_model_requests']==80 and closed['model_POST_attempts']==45 and closed['failed_request_hold_microusd']==775 and closed['failed_request_actual_cost'] is None)
check('pre/post per configuration',closed['pre_responses']==16 and closed['post_responses']==28 and closed['per_configuration_successful_responses']=={'A':22,'B':22} and '22 responses per configuration: 16 baselines and 28 post-treatment' in source)
pin(fifth['actual_report']);pin(fifth['independent_actual_review']);pin(snapshot['openrouter_diagnosis']['report'])
check('unknown 402 cause/account balance retained',snapshot['openrouter_diagnosis']['HTTP402_root_cause']=='UNKNOWN' and snapshot['openrouter_diagnosis']['account_prepaid_credit_balance']=='UNKNOWN' and all(v in source for v in ['actual charge is unknown','specific rejection cause remain unknown','has not been independently linked','More key-limit room does not establish an account balance']))
check('conservative exposure different scope',snapshot['owner_conservative_exposure_microusd']==16149 and 'exposureUSD: "0.016149"' in source and 'rounding and retained uncertainty holds' in source and 'local compute and agent labor are excluded' in source)
check('caps unchanged',snapshot['caps_microusd']=={'E01_paid_inference':0,'E02':1000000,'shared':5000000} and '$5 shared, $1 E02, and $0 E01 paid inference' in source)
historical=snapshot['e01']['completed_historical_diagnostic'];pin(historical['evidence']);pin(historical['independent_review'])
check('30 races MAE correctly rounded',historical['scope'].startswith('30 regular Class-I') and round(historical['S0_MAE_percentage_points'],2)==10.20 and round(historical['zero_margin_control_MAE_percentage_points'],2)==18.19 and '10.20 percentage points' in source and '>18.19<' in source)
check('posthoc and not prospective',not snapshot['e01']['accepted_prospective_2026_forecast'] and all(v in source for v in ['selected post hoc','outcomes were seen','not an untouched holdout or prospective 2026 forecast']))
check('source union and no accepted ballots','13-state' in snapshot['e01']['current_source_document_scope'] and '20 unfinished' in snapshot['e01']['current_source_document_scope'] and 'zero accepted final ballots' in source)
check('five acquired files no installation acceptance','five wheel hashes verified' in snapshot['e01']['acquisition'] and 'Five upgraded dependency files are verified. Installation acceptance' in source)
ci=snapshot['ci'];pin(ci['ordinary_namespace_remedy_review']);pin(ci['historical_collection_v1_2_actual_review']);pin(ci['historical_collection_v1_2_actual'])
ci_review=doc(ci['historical_collection_v1_2_actual_review']['path'])
check('collection exact evidence counts',ci_review['checks_passed']==2127 and ci_review['evidence_summary']['collected_unique_cases']==2771 and ci_review['evidence_summary']['excluded_modules']==6 and ci_review['evidence_summary']['monitored_test_setup_framework_entries']==0 and ci_review['evidence_summary']['errors_refusals']==0)
check('collection historical not current CI',all(v in source for v in ['Collection is not test execution','existing pypdf 6.10.0','7.0.1 environment and a new full CI run remain unqualified','29 suite checks and 46 independent adverse assertions','220 focused checks per runtime']))
check('remote CI failure retained',ci['python311']=='FAILURE' and ci['python312']=='SUCCESS' and 'passed Python 3.12 and failed Python 3.11' in source and 'no newer full-suite result is claimed' in source)
pin(snapshot['e01']['pypa_fixture_harness_v1_review']);blocked=doc(snapshot['e01']['pypa_fixture_harness_v1_review']['path'])
check('E01 two blockers and actual NOT_RUN',blocked['decision']=='BLOCKED' and len([v for v in blocked['findings'] if v['decision']=='BLOCKED'])==2 and all(v in source for v in ['rejects required code generation','success after a caught budget refusal','24 mocked checks on each runtime','whole-startup qualification and a fourth installation remain NOT_RUN']))
completion=snapshot['completion_dashboard_observation'];pin(completion['independent_current_receipt'])
check('2/14/7 scoped software status',completion['current_receipt_status_counts']=={'PASS':2,'BLOCKED':14,'NOT_RUN':7} and '2 PASS, 14 BLOCKED, 7 NOT_RUN' in source and 'software milestones' in source)
check('incomplete national/human/scientific gates',snapshot['full_original_completion_contract']=='INCOMPLETE' and all(v in source for v in ['Research contract incomplete','not people','do not demonstrate effects on people','representative electorate','completed human-study replication','E03 and E04 remain gated','National calibration, human anchoring']))
check('full fifth analysis not promoted','full registered analysis is NOT_RUN' in source and 'independently review them, then qualify actual integration before any installation' in source)
check('flat themed presentation',not re.search(r'#[A-Fa-f0-9]{3,8}\b|linear-gradient|radial-gradient|boxShadow|box-shadow',source) and 'useHostTheme()' in source)
check('within own process wall/CPU',time.monotonic()-start<120 and time.process_time()-cpu<120)
receipt={'status':'PASS_STATIC_PRESENTATION_AND_RETAINED_QA_BINDING_ONLY','checks_passed':len(checks),'checks':checks,'input_refs':list(refs.values()),'late_technical_read_bytes_including_1MiB_initial_read_reserve':read_bytes,'initial_read_reserve_bytes':1048576,'wall_seconds':time.monotonic()-start,'CPU_seconds':time.process_time()-cpu,'new_browser_typecheck_model_network_research_runs':0,'cost_USD':0,'limitations':['This verifies static source and retained author QA evidence, not a fresh render or native host openFile behavior.','Frozen bundle bytes and retained manifest verifier claims matched; no new Git verification or commit-graph computation.','No raw data/financial owner/key/account reads. Public technical reports and safe screenshot bytes only.','Snapshot is dated; links intentionally open current local files. No full milestone, current CI, runtime, human effect or prospective forecasting acceptance.']}
raw=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode();check('owned write cap',len(raw)<4194304)
with (OUT/'checks.json').open('xb') as stream:stream.write(raw)
print(json.dumps({'status':receipt['status'],'checks':receipt['checks_passed'],'read_bytes':read_bytes,'receipt_bytes':len(raw),'CPU_seconds':receipt['CPU_seconds'],'wall_seconds':receipt['wall_seconds']}))
