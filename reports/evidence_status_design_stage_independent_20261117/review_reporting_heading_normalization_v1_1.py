"""Closed reporting audit only; private owner references remain unopened."""
import sys
def deny(event,args):
    if event.startswith(('socket.','ctypes.')) or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec','os.system','os.spawn','os.kill','os.killpg'}:
        raise AssertionError('NO_NETWORK_PROCESS_NATIVE')
sys.addaudithook(deny)
from pathlib import Path
import hashlib,json,re,resource,signal,time
ROOT=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
OUT=ROOT/'reports/evidence_status_design_stage_independent_20261117'
start=time.monotonic();cpu=time.process_time();reads=1048576;cache={};refs={};checks=[]
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def deadline(*_):raise AssertionError('OWN120SECOND_CAP')
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,120)
def check(name,value):
    checks.append({'name':name,'pass':bool(value)})
    if not value:raise AssertionError(name)
def read(path):
    global reads
    p=Path(path);p=p if p.is_absolute() else ROOT/p;p=p.resolve()
    if p not in cache:
        size=p.stat().st_size;check('finite read '+p.name,reads+size<=67108864)
        z=p.read_bytes();reads+=len(z);cache[p]=z
        refs[str(p)]={'path':str(p),'bytes':len(z),'sha256':hashlib.sha256(z).hexdigest()}
    return cache[p]
def doc(path):return json.loads(read(path))
def pin(row):
    z=read(row['path']);check('typedpin '+Path(row['path']).name,len(z)==row['bytes'] and hashlib.sha256(z).hexdigest()==row['sha256']);return z
statusraw=pin({'path':'reports/STATUS.md','bytes':169168,'sha256':'3a92752de981ca2bccb1e13f665f80ea646d1a641278f253ef2e930b2c3ec2fb'})
cpraw=pin({'path':'reports/RESEARCH_CHECKPOINT_20261117.json','bytes':59219,'sha256':'8904c013e4451a73acc4e43d49f94e1fe96b0eabbca533cc28ff6c3b10f1b72d'})
s=statusraw.decode();cp=json.loads(cpraw);oldraw=pin(cp['previous_checkpoint']);old=json.loads(oldraw)
check('previoushash and dates',cp['previous_checkpoint_sha256']==hashlib.sha256(oldraw).hexdigest() and cp['reporting_date_local']=='2026-11-17' and cp['reporting_timezone']=='America/New_York' and cp['updated_at_UTC'].startswith('2026-11-17'))
baseline=pin({'path':str(OUT/'status_at_52c1aa4.md'),'bytes':166656,'sha256':'fbf7f361d7807ffac7af33d093ab5eaabae998855ebe80e2955001f9c5ad6f0c'}).decode()
check('Nov16 historical body preserved verbatim',s.split('## November 16 checkpoint (preserved history)\n\n',1)[1]==baseline.split('## November 16 current checkpoint\n\n',1)[1])
check('intro only clientdate changed',s.split('\n\n',2)[1].replace('November 17, 2026','November 16, 2026')==baseline.split('\n\n',2)[1])
check('historicalscopeexplicit','Historical reports retain their original dates and scoped acceptance' in cp['inherited_evidence_scope'] and 'no new model result' in cp['inherited_evidence_scope'])
typed=[]
def collect(v,path=''):
    if isinstance(v,dict):
        if {'path','bytes','sha256'}<=set(v):typed.append((path,v))
        for k,x in v.items():collect(x,path+'/'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):collect(x,path+'/'+str(i))
collect(cp)
private_paths={'/e02_fifth_study/closed_observation/private_export','/e02_fifth_study/closed_observation/private_index'}
deferred=[]
def lookup(v,path):
    for name in path.split('/')[1:]:v=v[int(name)] if isinstance(v,list) else v[name]
    return v
for path,row in typed:
    if path in private_paths:
        check('private owner ref unchanged '+path,lookup(old,path)==row)
        deferred.append({'json_path':path,'ref':row,'decision':'NOT_OPENED_PRIVATE_OWNER_SCOPE','unchanged_from_previous_checkpoint':True})
    else:
        check('public direct ref is safe reporting artifact',row['path'].startswith('reports/'))
        pin(row)
check('all152directrefsclassified',len(typed)==152 and len(deferred)==2)
for name in ('caps_microusd','e02_total_research_generations','e02_verified_research_model_usage_USD','owner_conservative_exposure_microusd','retained_uncertain_holds_microusd','e02_completed_live_studies','completion_dashboard_observation','full_original_completion_contract','new_model_calls_during_this_checkpoint','observed_at_UTC'):
    check('unchanged inherited '+name,cp[name]==old[name])
fifth=dict(cp['e02_fifth_study']);continuation=fifth.pop('one_slot_continuation')
check('fifth historical receipt unchanged',fifth==old['e02_fifth_study'])
check('E01 historical result unchanged',cp['e01']['completed_historical_diagnostic']==old['e01']['completed_historical_diagnostic'])
check('historical static review renamed not current acceptance',cp['historical_public_checkpoint_static_review']==old['public_checkpoint_static_review'] and cp['current_reporting_delta_review']=='PENDING_SEPARATE_INDEPENDENT_REVIEW')
newsection=s.split('## November 17 current checkpoint\n\n',1)[1].split('## November 16 checkpoint (preserved history)',1)[0]
check('threecurrentparagraphs',newsection.count('**')==6 and all(v in newsection for v in ['E02 recovery design accepted','E01 integration remains blocked','Results, costs and delivery']))
canary=doc(continuation['design_review']['path']);prep=doc(continuation['preparation']['path']);facts=canary['accepted_closed_facts']
check('E02design81only',canary['checks_passed']==canary['checks_total']==81 and 'passed 81 closed-evidence and static checks' in newsection and continuation['implementation_status']=='ASSIGNED_IN_PROGRESS_NOT_ACCEPTED' and continuation['execution_status']=='NOT_RELEASED_NOT_RUN')
check('single neverattempted slot45',facts['canary_slot']==45 and facts['configuration']=='B' and facts['phase']=='post' and facts['visibility']=='OMITTED' and facts['baseline']==13 and 'never-attempted slot 45' in newsection)
check('onePOST3stats2catalog limits',continuation['new_call_maxima']=={'catalog_GET':2,'model_POST':1,'statistics_GET':3} and 'these are limits, not calls made' in newsection)
check('hypothetical aggregate not actual',continuation['hypothetical_aggregate_maxima_not_actual']=={'fifth_POST':facts['POST']+1,'fifth_catalog_GET':facts['catalog']+2,'fifth_statistics_GET':facts['stats']+3,'lifetime_dispatches':facts['rows']+1})
check('44responses5holdsfailed775preserved',facts['responses']==44 and facts['protected_unfinished']==5 and facts['slot44_uncertain_hold']==775 and len(cp['retained_uncertain_holds_microusd'])==5 and 'all 44 saved responses' in newsection and 'all five unresolved holds' in newsection)
schedule=prep['count_cost_lineage_resolution_before_code']['full35_schedule_problem']
check('full35catalog18exceeds16',schedule['already_consumed']+schedule['new_fresh_both_route_catalogs']+schedule['original_refresh_GETs_remaining']==facts['full35catalog']==18 and facts['catalog_cap']==16 and '18 catalog lookups against the original limit of 16' in newsection and 'outside this scope' in newsection)
check('no canaryexecution accepted','No executable continuation has been accepted or released' in newsection)
design=doc(cp['e01']['g03_integration_design']['path']);review=doc(cp['e01']['g03_integration_design_review']['path'])
check('E01design152truthfulblockedonly',review['TESTS_RUN_AND_RESULTS']['static_checks_passed']==152 and design['decision']=='BLOCKED_B01_EXACT_PRE_SCRIPT_PRE_HOOK_BOOTSTRAP_BOUND_NOT_SUBSTANTIATED' and '152 static checks of accounting and truthful reporting' in newsection)
check('8MiBreserveunsubstantiatednotqualification','8 MiB allowance' in newsection and 'has not been substantiated' in newsection and 'remain unimplemented' in newsection and 'actual installer/runtime qualification is NOT_RUN' in newsection)
check('totals/exposure/capsunchanged',cp['e02_total_research_generations']==191 and cp['e02_verified_research_model_usage_USD']=='0.0129589' and cp['owner_conservative_exposure_microusd']==16149 and cp['caps_microusd']=={'E01_paid_inference':0,'E02':1000000,'shared':5000000} and 'fifth-study $0.20' in newsection)
check('designreviewsnotactualcallsorcharge','No new model request or charge occurred in these design reviews' in newsection)
check('ownerstatesnotremoteproof','owner reports that OpenRouter works' in newsection and 'neither statement rewrites the earlier failures or establishes a new verified remote head' in newsection)
check('fullcontractincomplete',cp['full_original_completion_contract']=='INCOMPLETE' and 'full research contract remains INCOMPLETE' in newsection)
manifest=doc('data/processed/github_delivery_checkpoint_20261116_23/manifest.json')
check('bundle23head36lastremote',manifest['head']==cp['git']['last_code_and_evidence_commit_before_final_checkpoint']=='52c1aa435e6258a6ce8333a937325ddf58536703' and manifest['unpublished_commit_count']==cp['git']['local_unpublished_commits_before_final_checkpoint']==36 and manifest['prerequisite_commit']==cp['git']['last_remote_verified_head']=='25d51254e5547cecf345a10c76ee22a7e83d9c18')
check('retained bundle23 verification scoped',manifest['verification']['git_bundle_verify_exit']==0 and manifest['verification']['prerequisite_present_in_checkout'] and manifest['verification']['sole_bundle_head']==manifest['head']+' HEAD' and 'not GitHub delivery' in manifest['scope'])
pin(manifest['bundle'])
future=cp['git']['final_checkpoint_bundle_manifest'];check('futureNov17bundle01plannedabsent',future=='data/processed/github_delivery_checkpoint_20261117_01/manifest.json' and cp['git']['final_checkpoint_bundle_status_at_report_freeze']=='PLANNED_POST_COMMIT_NOT_YET_VERIFIED' and not (ROOT/future).exists())
for link in re.findall(r'\]\(([^)]+)\)',newsection):
    check('currentlocalreferenceexists '+Path(link).name,not link.startswith('http') and (ROOT/'reports'/link).resolve().is_file())
check('finalfilepinsunchanged',(ROOT/'reports/STATUS.md').read_bytes()==statusraw and (ROOT/'reports/RESEARCH_CHECKPOINT_20261117.json').read_bytes()==cpraw)
check('ownboundedreview',reads<67108864 and time.monotonic()-start<120 and time.process_time()-cpu<120)
receipt={'decision':'PASS_DESIGN_STAGE_REPORTING_ONLY_PRIVATE_OWNER_REFS_UNOPENED_ACTUAL_EXECUTION_NOT_RUN','checks_passed':len(checks),'checks':checks,'input_refs':list(refs.values()),'direct_refs':{'total':len(typed),'public_verified':len(typed)-len(deferred),'private_deferred':deferred},'scope':'CurrentNov17section and inherited checkpoint snapshot only. No methods/implementation/experiment re-review.','limits_vs_actual':{'new_limits':continuation['new_call_maxima'],'new_actual_network_model_calls':0,'full35catalog':18,'catalog_cap':16},'future_bundle':{'path':future,'verification':'NOT_RUN_PLANNED_NOT_VERIFIED'},'limitations':['Twoprivate ownerexport/index contentrefs intentionally unopened; identicaltoinheritedNov16references only.','Retained design reviews accepted only at stated81/152static scope; no newmethods orimplementation qualification.','Old45modelcalls_during_this_checkpoint andNov16observed_at remain inheritedhistoricalcounters, not newNov17dispatches.','Bundle23bytes/hash/head/countmatchretainedmanifest; no newGitbundleverify orremoteaccess test.','No candidate/helper/test/model/network/credential/ownerdata orresearchsource execution/access.'],'accounting':{'content_read_bytes_including1MiBinitialreserve':reads,'CPU_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-start,'new_network_model_owner_credential_actions':0,'cost_USD':0}}
raw=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode()
with (OUT/'checks.json').open('xb') as f:f.write(raw)
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({'decision':receipt['decision'],'checks':receipt['checks_passed'],'read_bytes':reads,'evidence_bytes':len(raw),'CPU_seconds':receipt['accounting']['CPU_seconds'],'wall_seconds':receipt['accounting']['wall_seconds']}))
