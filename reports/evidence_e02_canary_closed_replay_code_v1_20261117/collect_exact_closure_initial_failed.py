"""Static project/contract closure + explicit stdlib-only prewarm; no civiclab import."""
from pathlib import Path
import ast,hashlib,json,sys,sysconfig,importlib,os
ROOT=Path(__file__).resolve().parents[2]
EV=Path(__file__).resolve().parent
used=225409
LIMIT=67108864
cache={};reasons={}
def read(p):
 global used
 p=Path(p).resolve();size=p.stat().st_size
 if used+size>LIMIT:raise RuntimeError('PREPARATION64MIB')
 used+=size;raw=p.read_bytes()
 if len(raw)!=size:raise RuntimeError('CHANGED')
 return raw
def add(p,why):
 p=Path(p).resolve()
 if not p.is_file():raise RuntimeError('MISSING_STATIC_DEPENDENCY')
 reasons.setdefault(p,set()).add(why)
 if p not in cache:cache[p]=read(p)
 return p
src=ROOT/'src';queue=[]
def project(p,why):
 p=add(p,why)
 if p.suffix=='.py' and p not in queue:queue.append(p)
 # Package initializers are import inputs too.
 for parent in p.parents:
  if parent==src:break
  if parent.is_relative_to(src) and (parent/'__init__.py').is_file():
   x=add(parent/'__init__.py','package initializer')
   if x not in queue:queue.append(x)
def module(name):
 p=src/Path(*name.split('.'))
 if p.with_suffix('.py').is_file():return p.with_suffix('.py')
 if (p/'__init__.py').is_file():return p/'__init__.py'
 return None
contract_seeds=['common','model','owner_budget_v3','live_billing_v2','production_owner_v4','additional_compatibility_owner_v1','production_admission_v4','production_price_v4','production_compatibility_v4_2_1','production_compatibility_transport_v4_2','openrouter_http_v2','survey_execution']
for n in contract_seeds:project(src/'civiclab'/f'{n}.py','original nested code_contract file')
for n in ['instrument','exploratory_owner_v1','exploratory_live_client_v1','exploratory_response_v1','exploratory_sequence_v1','exploratory_live_requests_v1','exploratory_pilot_analysis_v1','exploratory_metadata_v1','exploratory_continuation_owner_v1','exploratory_continuation_v1','alignment_anchoring_v1','alignment_anchoring_owner_v1','alignment_anchoring_client_v1','issue_cue_crossmodel_v1','issue_cue_crossmodel_owner_v1','issue_cue_crossmodel_client_v1','issue_cue_crossmodel_recovery_owner_v1','issue_cue_crossmodel_recovery_client_v1','crossmodel_recovery_metadata_v1','crossmodel_saved_pair_v1','wrapper_visibility_v1','wrapper_visibility_owner_v1','wrapper_visibility_client_v1','wrapper_crossmodel_v1','wrapper_crossmodel_v1_owner','wrapper_crossmodel_v1_client','wrapper_crossmodel_canary_v1','wrapper_crossmodel_canary_v1_owner','wrapper_crossmodel_canary_v1_client','crossmodel_price_v1','crossmodel_metadata_v1']:
 project(src/'civiclab/e02'/f'{n}.py','nested contract or candidate import seed')
for n in ['run_alignment_anchoring_once.py','run_e02_continuation_once.py','collect_connectivity_billing_once.py','run_issue_cue_crossmodel_once.py','run_issue_cue_crossmodel_recovery_once.py','run_wrapper_visibility_once.py','run_wrapper_crossmodel_v1_20261115_once.py','continue_e02_wrapper_crossmodel_canary_v1_20261117.py']:
 project(ROOT/'scripts'/n,'nested code_contract script pin')
for n in ['docs/E02_RECOVERY_ADMISSION_V1_PROPOSAL.md','reports/INDEPENDENT_AUDIT_E02_RECOVERY_ADMISSION_V1_METHODS.json']:add(ROOT/n,'original required recovery evidence')
stdlib=set();processed=set();edges=[]
while queue:
 p=queue.pop(0)
 if p in processed:continue
 processed.add(p);tree=ast.parse(cache[p],filename=str(p))
 package='.'.join(p.relative_to(src).parts[:-1]) if p.is_relative_to(src) else None
 for node in ast.walk(tree):
  names=[]
  if isinstance(node,ast.Import):names=[a.name for a in node.names]
  elif isinstance(node,ast.ImportFrom):
   if node.level:
    if package is None:raise RuntimeError('RELATIVE_SCRIPT_IMPORT')
    base=package.split('.')[:len(package.split('.'))-node.level+1]
    if node.module:base+=node.module.split('.')
    name='.'.join(base);names=[name]+[name+'.'+a.name for a in node.names if a.name!='*']
   else:names=[node.module] if node.module else []
  for n in names:
   if n.startswith('civiclab'):
    dep=module(n)
    if dep:
     edges.append({'from':str(p.relative_to(ROOT)),'module':n,'to':str(dep.relative_to(ROOT))});project(dep,'recursive literal project import')
   elif n and n.split('.')[0] in sys.stdlib_module_names:stdlib.add(n)
   elif n and n not in ('__future__',):raise RuntimeError('NON_STDLIB_IMPORT:'+n)
  if isinstance(node,ast.Constant) and isinstance(node.value,str):
   text=node.value
   if text.startswith(('configs/','docs/','reports/')) and (ROOT/text).is_file():add(ROOT/text,'literal read dependency')
# Only stdlib is imported here, in the exact intended runtime and isolated mode.
for n in sorted(stdlib):importlib.import_module(n)
if any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules):raise RuntimeError('CANDIDATE_IMPORTED')
stdroot=Path(sysconfig.get_path('stdlib')).resolve();runtime=[]
for n,m in sorted(sys.modules.items()):
 file=getattr(m,'__file__',None)
 if file:
  path=Path(file).resolve()
  if path.is_relative_to(stdroot) and path.is_file():
   for candidate in [path,Path(getattr(m,'__cached__','/nonexistent'))]:
    if candidate.is_file():
     candidate=candidate.resolve()
     if not any(x['path']==str(candidate) for x in runtime):
      raw=read(candidate);runtime.append({'path':str(candidate),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'reason':'explicit stdlib/prewarm module or its existing bytecode'})
# Exact native extension origins above are pinned; executable metadata is explicit.
exe=Path(sys.executable).resolve();raw=read(exe);runtime.append({'path':str(exe),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'reason':'qualification interpreter executable'})
projectrefs=[{'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'reasons':sorted(reasons[p])} for p,raw in sorted(cache.items())]
q={'kind':'EXACT_STATIC_PROJECT_AND_REVIEWED_STDLIB_PREWARM_CLOSURE_V1','python':sys.version.split()[0],'project_pins':projectrefs,'stdlib_pins':runtime,'prewarm_modules':sorted(stdlib),'import_edges':edges,'read_bytes_including_prior_preparation':used,'project_or_candidate_imports':0,'owner_verifier_calls':0,'notes':['Project AST recursively includes literal imports in all scopes plus manual exact nested code_contract seed paths. Static closure is not proof of runtime feasibility.','Standard-library-only prewarm performed in isolated Python3.12.14. Imported module origins and existing cached bytecode are exact pins; startup/native loader implicit OS reads are outside Python-open accounting and must be disclosed.','No source/config/script directory allowlist. Only these exact file refs may be read by candidate. Unexpected reads fail closed.']}
p=EV/'EXACT_CLOSURE.json'
if p.exists():raise RuntimeError('REFUSE_OVERWRITE')
raw=(json.dumps(q,indent=2,sort_keys=True)+'\n').encode();p.write_bytes(raw)
print(json.dumps({'python':q['python'],'project_files':len(projectrefs),'stdlib_files':len(runtime),'prewarm_modules':len(stdlib),'content_reads':used,'closure_bytes':len(raw),'closure_sha256':hashlib.sha256(raw).hexdigest()}))
