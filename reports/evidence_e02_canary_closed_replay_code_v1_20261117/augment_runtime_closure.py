"""Extend exact prewarm origins for helper+descriptor guard; stdlib only."""
from pathlib import Path
import ast,sys,sysconfig,hashlib,json,importlib
ROOT=Path(__file__).resolve().parents[2];EV=Path(__file__).resolve().parent
used=32111014
p=EV/'EXACT_CLOSURE.json';raw=p.read_bytes();used+=len(raw);q=json.loads(raw)
modules=set(q['prewarm_modules'])
for name in ['scripts/qualify_e02_canary_closed_replay_v1_20261117.py','scripts/e01_authored_dirfd_guard_v2_20261112.py']:
 raw=(ROOT/name).read_bytes();used+=len(raw)
 for node in ast.walk(ast.parse(raw)):
  if isinstance(node,ast.Import):names=[a.name for a in node.names]
  elif isinstance(node,ast.ImportFrom) and not node.level:names=[node.module] if node.module else []
  else:continue
  modules.update(n for n in names if n.split('.')[0] in sys.stdlib_module_names)
for n in sorted(modules):importlib.import_module(n)
if any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules):raise RuntimeError('CANDIDATE_IMPORT')
seen={p['path'] for p in q['stdlib_pins']};stdroot=Path(sysconfig.get_path('stdlib')).resolve();added=[]
for name,m in sorted(sys.modules.items()):
 f=getattr(m,'__file__',None)
 if f:
  src=Path(f).resolve()
  if src.is_relative_to(stdroot):
   for candidate in [src,Path(getattr(m,'__cached__','/nonexistent'))]:
    if candidate.is_file():
     candidate=candidate.resolve()
     if str(candidate) not in seen:
      size=candidate.stat().st_size
      if used+size>67108864:raise RuntimeError('PREPARATION64MIB')
      used+=size;raw=candidate.read_bytes();seen.add(str(candidate));pin={'path':str(candidate),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'reason':'helper/descriptor explicit stdlib prewarm origin or existing cache'};q['stdlib_pins'].append(pin);added.append(pin)
q['prewarm_modules']=sorted(modules);q['read_bytes_including_prior_preparation']=used;q['helper_stdlib_boundary']='Includes literal stdlib imports from qualification helper and DirectoryFdGuard. No project modules imported.'
out=EV/'EXACT_CLOSURE_WITH_HELPER.json'
if out.exists():raise RuntimeError('REFUSE_OVERWRITE')
blob=(json.dumps(q,indent=2,sort_keys=True)+'\n').encode();out.write_bytes(blob)
print(json.dumps({'path':str(out.relative_to(ROOT)),'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'content_read_bytes_cumulative':used,'stdlib_pins':len(q['stdlib_pins']),'prewarm_modules':len(modules),'added':len(added)}))
