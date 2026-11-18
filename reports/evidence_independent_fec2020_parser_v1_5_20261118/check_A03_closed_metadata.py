"""Closed A02 receipt/claim/log metadata only; never workbook or caller main."""
from pathlib import Path
import os,sys,json,hashlib,time,resource,signal,datetime
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(29,30));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(30)
root=Path.cwd();start=time.monotonic();used=0;refs=[]
scope=root/'data/processed/e01_fec2020_candidate_actual_20261118_03'
allowed={root/'reports/E01_FEC2020_A03_ACTUAL_20261118.json',root/'reports/E01_FEC2020_A03_RUN_PLAN_20261118.json',scope/'stdout.log',scope/'stderr.log',scope/'reader-claim.local.json',scope/'attempt.local.json',scope/'observation.local.json'}
def audit(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','sqlite3.connect','ctypes.dlopen'):raise RuntimeError('NO_NETWORK_OWNER_PROCESS')
 if event=='open' and not isinstance(args[0],int):
  p=Path(args[0]).resolve();assert not args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND);assert p in allowed
sys.addaudithook(audit)
def read(path):
 global used
 assert not any(x.is_symlink() for x in (path,*path.parents));raw=path.read_bytes();used+=len(raw);assert used<=8388608;refs.append({'path':str(path.relative_to(root)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()});return raw
obs=json.loads(read(root/'reports/E01_FEC2020_A03_ACTUAL_20261118.json'));plan=json.loads(read(root/'reports/E01_FEC2020_A03_RUN_PLAN_20261118.json'))
historical_parser=root/'reports/evidence_independent_fec2020_parser_v1_4_20261118/frozen_fec2020_parser_v1.py'
for ref in plan['files']:allowed.add(historical_parser if ref['path']=='src/civiclab/e01/fec2020_parser_v1.py' else root/ref['path'])
for ref in plan['files']:
 raw=read(historical_parser if ref['path']=='src/civiclab/e01/fec2020_parser_v1.py' else root/ref['path']);assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
for ref in obs['logs']:
 raw=read(root/ref['path']);assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
stdout=json.loads(read(scope/'stdout.log'));stderr=read(scope/'stderr.log');claim=json.loads(read(scope/'reader-claim.local.json'));names=sorted(p.name for p in scope.iterdir())
checks={'closed_plan_and_observation_commit_binding':obs['source_commit']==plan['source_commit']=='ace3b170c4135003f83d895689e9b48453466f17','all_four_plan_code_review_pins_historical_parser_snapshot':len(plan['files'])==4,'both_logs_exact':len(obs['logs'])==2,'safe_stdout_exact':stdout==obs['summary']=={'status':'STOPPED_NO_RETRY','error_type':'ParserRefused','safe_code':'STATE_CONTEST_CONTEXT'},'stderr_empty':stderr==b'','one_exclusive_claim_reserved':claim=={'reader_calls_reserved':1,'retries':0},'exact_five_closed_files':names==['attempt.local.json','observation.local.json','reader-claim.local.json','stderr.log','stdout.log'],'private_public_plan_exact':json.loads(read(scope/'attempt.local.json'))==plan,'private_public_observation_exact':json.loads(read(scope/'observation.local.json'))==obs,'no_candidate_output':not (scope/'candidate-audit.local.json').exists(),'bounded_terminal_failure':obs['exit_code']==1 and obs['outer_stop_reason'] is None and 0<obs['elapsed_seconds']<120 and 0<obs['waited_child_CPU_seconds']<120,'no_retry_or_adoption':obs['retry_allowed'] is False and obs['adoption'] is False and obs['forecast_consumption'] is False and plan['retries']==0 and plan['adoption'] is False,'fixed_nonpaid_allocation':plan['reader_calls_max']==1 and plan['network_calls_max']==plan['model_calls_max']==plan['cost_usd']==0,'chronology':datetime.datetime.fromisoformat(obs['started_at_utc'])<datetime.datetime.fromisoformat(obs['finished_at_utc'])}
assert all(checks.values()),[k for k,v in checks.items() if not v]
print(json.dumps({'kind':'INDEPENDENT_FEC_A03_CLOSED_METADATA','status':'PASS','checks':checks,'refs':refs,'claim':claim,'directory_names':names,'fixed_failure':stdout,'elapsed_seconds_observed':obs['elapsed_seconds'],'child_CPU_seconds_observed':obs['waited_child_CPU_seconds'],'review_logical_read_bytes':used,'review_wall_seconds':time.monotonic()-start,'review_CPU_seconds':sum(resource.getrusage(resource.RUSAGE_SELF)[:2]),'actual_workbook_caller_main_reader_key_owner_network_calls':0,'cost_usd':0},sort_keys=True));signal.alarm(0)
