"""Repository source/manifest assessment only. No research inputs/commands run."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,sys,time
ROOT=Path.cwd();OUT=ROOT/'reports/evidence_e01_independent_work_assessment_20261117';reads=0;refs={};cache={}
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(RuntimeError('ASSESSMENT_WALL_CAP')));signal.alarm(120)
start=time.monotonic()
def read(name):
 global reads
 p=ROOT/name
 roots=('src/','scripts/','configs/','reports/','docs/','protocols/')
 if not str(name).startswith(roots) and not (str(name).startswith('data/processed/runs/') and p.name in {'checksums.json','manifest.json'}):raise RuntimeError('ASSESSMENT_METADATA_ONLY')
 if p.is_symlink() or not p.is_file() or p.stat().st_size>2097152 or reads+p.stat().st_size+1>33554432:raise RuntimeError('ASSESSMENT_READ_BOUND')
 raw=p.read_bytes();reads+=len(raw)+1;refs[name]={'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};cache[name]=raw;return raw
names=['src/civiclab/e01/pipeline.py','src/civiclab/e01/historical.py','src/civiclab/e01/worker.py','src/civiclab/e01/isolation.py',
'src/civiclab/e01/ballots.py','src/civiclab/e01/ballots_v1_9_1.py','src/civiclab/e01/selection.py','src/civiclab/cli.py',
'configs/e01_retrospective.json','configs/e01_senate2018_2024.json','configs/e01_selection_v1.json','configs/e01_selection_source_schema_v1.json',
'configs/e01_typed_readiness_v1_9_1_candidate.json','configs/e01_clerk_2020_senate_input_methods_v1.json','configs/e01_official_sources.json',
'configs/SOURCE_INVENTORY.json','protocols/E01_FEED_TO_BALLOT.md','protocols/E01_RETROSPECTIVE.md','protocols/E01_SENATE_2018_2024_DIAGNOSTIC.md',
'docs/E01_2026_SELECTION_PROPOSAL.md','docs/E01_HISTORICAL_RUNBOOK.md','docs/E01_CLERK_2020_SENATE_INPUT_METHODS_v1.md',
'reports/INDEPENDENT_AUDIT_E01_HISTORICAL.json','reports/E01_HISTORICAL_EVIDENCE.json','reports/INDEPENDENT_AUDIT_E01_SELECTION_METHODS.json',
'reports/INDEPENDENT_AUDIT_E01_SELECTION_V1.json','reports/INDEPENDENT_AUDIT_E01_V1_9_1_ACTUAL_PRIMARY_REPLAY.json',
'reports/INDEPENDENT_AUDIT_E01_AL_V1_1_ACTUAL_PRIMARY_REPLAY.json','reports/E01_2026_READINESS.json','reports/E01_INSIDE_ELECTIONS_ASOF.json']
for name in names:read(name)
source=cache['src/civiclab/e01/ballots_v1_9_1.py'].decode();tree=ast.parse(source)
def literal_assignment(text,name):
 tr=ast.parse(text);return next(n.value for n in tr.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
# The two field declarations contain literal split strings; inspect that data,
# never compile/import the production modules.
classnode=literal_assignment(cache['src/civiclab/e01/ballots.py'].decode(),'CLASS_II_STATES')
class_states=classnode.args[0].func.value.value.split()
legacy_node=literal_assignment(source,'STATES');legacy=legacy_node.args[0].func.value.value.split();covered=set(legacy)|{'ID'}
remaining=[s for s in class_states if s not in covered]
assert len(class_states)==33 and len(legacy)==12 and len(covered)==13 and len(remaining)==20
reader=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='read_verified_public')
readertext=ast.unparse(reader)
assert 'verify_bound_inputs' not in readertext and 'compute(' not in readertext
historical=ast.parse(cache['src/civiclab/e01/historical.py']);run=next(n for n in historical.body if isinstance(n,ast.FunctionDef) and n.name=='run_historical')
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='prepare' for n in ast.walk(run))
accepted=json.loads(cache['reports/INDEPENDENT_AUDIT_E01_HISTORICAL.json']);run_meta=[]
for run_id in ['e01-ed5b716aa76145258ece94c3df6b4188','e01-9a3e3305877f40b3a84e63bd5ca5ed1c']:
 directory=ROOT/'data/processed/runs'/run_id
 row={'run_id':run_id,'directory_present':directory.is_dir(),'numeric_bodies_read':False,'files':{}}
 ledger_path=f'data/processed/runs/{run_id}/checksums.json'
 if (ROOT/ledger_path).is_file():
  ledger=json.loads(read(ledger_path));row['checksum_ledger_ref']=refs[ledger_path]
  for name in ['race_manifest.json','features.json','outcomes.json','S_ZERO.predictions.frozen.json','S0.predictions.frozen.json','S_ZERO.evaluation.json','S0.evaluation.json','paired_comparison.json','eligibility.json','source_receipt.json']:
   p=directory/name;row['files'][name]={'present':p.is_file(),'bytes':p.stat().st_size if p.is_file() else None,'listed_hash':ledger.get(name),'body_read_or_rehashed':False}
 run_meta.append(row)
config=json.loads(cache['configs/e01_retrospective.json']);selection=json.loads(cache['configs/e01_selection_v1.json'])
summary={'kind':'E01_METADATA_ONLY_INDEPENDENT_WORK_INVENTORY','input_refs':refs,
 'typed_readiness':{'class_II_states':class_states,'legacy_states':legacy,'typed_history_state':'ID','remaining_document_states':remaining,'metrics':{'slots':33,'typed_covered':13,'remaining_jobs':20,'final_ballots_accepted':0}},
 'verified_public_reader':{'source_ref':refs['src/civiclab/e01/ballots_v1_9_1.py'],'lines':[reader.lineno,reader.end_lineno],
 'behavior':'Reads saved ledgers/seals/payloads/config andfourdeclaredJSONreferences;noverify_bound_inputs/rawsourceparse/computeinvocationinfunction. Separateactualauditacceptedsavedoutputscope.'},
 'historical_recorded_artifact_metadata':run_meta,
 'historical_run_rebuilds_raw_inputs':True,'generic_REAL_races':config['real_races'],'generic_REAL_status':config['real_race_status'],'selector_REAL_policy':selection['real_selection'],
 'candidate_paths':['src/civiclab/e01/pipeline.py','src/civiclab/e01/ballots_v1_9_1.py'],
 'assessment_read_bytes':reads,'content_read_cap':33554432,'wall_seconds':time.monotonic()-start,
 'raw_PDF_CSV_or_numeric_recorded_bodies_processed':False,'candidate_runs_or_imports':0,'network_models_credentials_liveowner_actions':0,'production_Git_STATUS_edits':0}
raw=json.dumps(summary,indent=2,sort_keys=True).encode()+b'\n';(OUT/'METADATA_INVENTORY.json').write_bytes(raw)
print(json.dumps({'read_bytes':reads,'remaining_jobs':len(remaining),'runs_metadata':len(run_meta),'evidence_bytes':len(raw),'evidence_sha256':hashlib.sha256(raw).hexdigest()},sort_keys=True))
