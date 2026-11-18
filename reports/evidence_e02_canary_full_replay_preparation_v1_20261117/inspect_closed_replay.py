"""Bounded static source and pinned CLOSED evidence inspection; no owner import."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BUDGET=32*1024*1024
used=0
pins=[]
def read(name):
 global used
 path=ROOT/name
 size=path.stat().st_size
 if used+size>BUDGET:raise RuntimeError('CLOSED_PREPARATION_READ_LIMIT')
 used+=size
 raw=path.read_bytes()
 if len(raw)!=size:raise RuntimeError('CLOSED_INPUT_CHANGED')
 pins.append({'path':name,'bytes':size,'sha256':hashlib.sha256(raw).hexdigest()})
 return raw
sources=['src/civiclab/production_owner_v4.py','src/civiclab/owner_budget_v3.py','src/civiclab/additional_compatibility_owner_v1.py']+['src/civiclab/e02/'+n+'.py' for n in ['exploratory_owner_v1','exploratory_continuation_owner_v1','alignment_anchoring_owner_v1','issue_cue_crossmodel_owner_v1','issue_cue_crossmodel_recovery_owner_v1','wrapper_visibility_owner_v1','wrapper_crossmodel_v1_owner','wrapper_crossmodel_canary_v1_owner']]
selected={}
for name in sources:
 raw=read(name);tree=ast.parse(raw,filename=name)
 chosen={}
 for node in ast.walk(tree):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in {'__init__','_verify','_registration','_connect','_journal','_binding','_entry','_check_commit','_apply'}:
   if node.name=='_apply':
    # First-pass relevant dependency lines; full source is hash pinned.
    lines=raw.decode().splitlines()[node.lineno-1:node.end_lineno]
    picked=[line for line in lines if any(v in line for v in ('read_', 'open(', '_journal','_binding','_entry','super()', 'approvals','snapshot','history','registration','header'))]
    chosen[node.name]='\n'.join(picked)
   else:chosen[node.name]=ast.get_source_segment(raw.decode(),node)
 selected[name]=chosen
base='data/processed/e02_wrapper_crossmodel_v1_20261115_actual_01/'
raw=read(base+'post-run-owner-export.local.json')
if len(raw)!=3893676 or hashlib.sha256(raw).hexdigest()!='ba726232dbc1375f5e7c48d5f96f3bdec70a9812a25cacfe3c00640197aa6f66':raise RuntimeError('CLOSED_EXPORT_PIN')
e=json.loads(raw)
shape={'keys':sorted(e),'header_field_names':sorted(e['header']),'head_field_names':sorted(e['head']),'rows_count':len(e['rows']),'events_count':len(e['history']),'statistics_claims_count':len(e['statistics_claims']),'event_kinds':{},'event_payload_field_names':{}}
for event in e['history']:
 b=event['body'];kind=b['kind'];shape['event_kinds'][kind]=shape['event_kinds'].get(kind,0)+1
 shape['event_payload_field_names'].setdefault(kind,set()).update(b['payload'])
shape['event_payload_field_names']={k:sorted(v) for k,v in shape['event_payload_field_names'].items()}
for name in ['reports/E02_WRAPPER_CROSSMODEL_STOPPED_ACTUAL_20261116.json','reports/INDEPENDENT_AUDIT_E02_WRAPPER_CROSSMODEL_STOPPED_ACTUAL_20261116.json','reports/evidence_e02_wrapper_crossmodel_canary_v1_preparation_20261116/closed-preflight.json']:
 r=json.loads(read(name));selected[name]=r
result={'kind':'STATIC_CLOSED_REPLAY_DEPENDENCY_INSPECTION','read_limit_bytes':BUDGET,'content_read_bytes':used,'source_and_closed_pins':pins,'export_safe_shape':shape,'selected_source_and_public_evidence':selected,'owner_imports':0,'owner_verifier_invocations':0,'API_calls':0,'credential_reads':0}
out=ROOT/'reports/evidence_e02_canary_full_replay_preparation_v1_20261117/STATIC_INSPECTION.json'
blob=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode()
if len(blob)>1048576:raise RuntimeError('PREPARATION_REPORT_LIMIT')
if out.exists():raise RuntimeError('REFUSE_OVERWRITE')
out.write_bytes(blob)
print(json.dumps({'content_read_bytes':used,'output_bytes':len(blob),'output_sha256':hashlib.sha256(blob).hexdigest(),'export_safe_shape':shape}))
for name,chosen in selected.items():
 if name.startswith('src/'):
  print(name)
  for key in ('__init__','_registration','_verify','_journal','_connect'):
   if key in chosen:print(chosen[key])
