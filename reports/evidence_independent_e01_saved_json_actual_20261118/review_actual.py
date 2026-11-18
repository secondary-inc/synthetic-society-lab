"""One bounded read-only retained-output review; no reader/entry execution."""
from pathlib import Path
import os,sys,json,hashlib,time,resource,signal,types,ast
resource.setrlimit(resource.RLIMIT_CPU,(30,30));signal.alarm(60);t=time.monotonic()
root=Path.cwd();out=root/'reports/evidence_independent_e01_saved_json_actual_20261118';actual=root/'data/processed/e01_saved_json_actual_20261118_01';control=root/'data/processed/e01_saved_json_one_call_control_v1/e01-saved-json-0f14f1bcd9364b49a88ebd4271954a02';packetpath=root/'data/processed/e01_saved_json_one_call_packets/packet_20261118_01.json';releasepath=root/'reports/E01_SAVED_JSON_ONE_CALL_LEAD_RELEASE_20261118.json';helperpath=root/'src/civiclab/e01/saved_json_entry_v1.py';receiptpath=actual/'process-exit.local.json'
allowed={packetpath,releasepath,helperpath};reads=0;checks={};refs=[];diagnostics={};errors=[]
def audit(event,args):
 if event.startswith(('socket.','ctypes.')) or event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','os.exec'):raise PermissionError('EXTERNAL_DENIED')
 if event=='import' and (args[0]=='civiclab' or args[0].startswith('civiclab.')):raise PermissionError('PROJECT_IMPORT_DENIED')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(os.fsdecode(args[0])).absolute();flags=args[2]
  if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
   if p.parent!=out:raise PermissionError('WRITE_SCOPE')
  elif p.is_relative_to(root) and p not in allowed and not p.is_relative_to(actual) and not p.is_relative_to(control):raise PermissionError('ACTUAL16_OR_OWNER_READ_FORBIDDEN')
sys.addaudithook(audit)
def read(p):
 global reads
 assert p in allowed or p.is_relative_to(actual) or p.is_relative_to(control)
 b=p.read_bytes();reads+=len(b);assert reads<=67108864;return b
def h(b):return hashlib.sha256(b).hexdigest()
def packed(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def check(k,v):checks[k]=bool(v)
def load(p):return json.loads(read(p))
def strings(x):
 if isinstance(x,str):return [x]
 if isinstance(x,dict):return sum((strings(v) for v in x.values()),[])
 if isinstance(x,list):return sum((strings(v) for v in x),[])
 return []
def metadatarefs(x):
 if isinstance(x,dict):
  if {'path','bytes','sha256'}<=set(x):yield x
  for v in x.values():yield from metadatarefs(v)
 elif isinstance(x,list):
  for v in x:yield from metadatarefs(v)
try:
 receipt_raw=read(receiptpath);check('receipt_pin',len(receipt_raw)==2785 and h(receipt_raw)=='4cf7e88cbc79ab0e0c378c4666091c7f4b246ede4d108c36f2212ec90f9d22ba');receipt=json.loads(receipt_raw)
 release_raw=read(releasepath);check('release_pin',h(release_raw)=='e2ef885a35fca3a64c3a334e6002db14947647922fb04664c18a98d9aab362ff');release=json.loads(release_raw)
 packet_raw=read(packetpath);check('packet_pin',len(packet_raw)==8238 and h(packet_raw)=='745f6531ebf35e8fbd47595558a21fd8755334ef3b64cb070011d741220e7e74');p=json.loads(packet_raw)
 check('release_binds_packet',h(packet_raw) in strings(release))
 check('release_binds_independent_particular_review','f72ba0b9cc4a70f4d1e4efb3deb5d3bb37a02af02143fc4a0be6231407a74229' in strings(release))
 for r in metadatarefs(receipt):
  path=Path(r['path']);path=path if path.is_absolute() else root/path
  if not(path in allowed or path.is_relative_to(actual) or path.is_relative_to(control)):
   diagnostics.setdefault('out_of_scope_receipt_refs',[]).append(r['path']);continue
  b=read(path);check('receipt_ref:'+path.name,len(b)==r['bytes'] and h(b)==r['sha256']);refs.append(r)
 helper_raw=read(helperpath);check('accepted_helper_pin',h(helper_raw)=='50700d8c5d288a626731e1bd230f9718ddac2e1cdacc2110127cad0979ac9677')
 E=types.ModuleType('independent_closed_output');E.__file__=str(helperpath);exec(compile(helper_raw,E.__file__,'exec'),E.__dict__)
 ledger_raw=read(control/'source_job_ledger.json');ledger=json.loads(ledger_raw);E.validate_ledger(ledger,p,False);check('exact_closed_real_ledger_validator',True)
 check('exact_ledger_hash',h(ledger_raw)=='7d001f7d1839fa41204e333f766180baf4c227fc97038ecbbc520eddbbcce9ff')
 start=load(control/'STARTED.json');worker=load(control/'WORKER_STARTED.json');complete=load(control/'COMPLETE.json')
 check('exact_control_members',{q.name for q in control.iterdir()}=={'STARTED.json','WORKER_STARTED.json','source_job_ledger.json','COMPLETE.json'})
 check('complete_ledger_binding',complete['ledger_sha256']==h(ledger_raw))
 usage=complete['usage'];check('usage_bounds',usage['saved_JSON_bytes']<=8388608 and usage['project_source_bytes']<=1048576 and usage['write_bytes']<=2097152)
 check('one_reader_no_failure',usage['reader_calls']==1 and usage['failed'] is False)
 check('exact_usage',usage['saved_JSON_bytes']==522395 and usage['project_source_bytes']==374638 and usage['write_bytes']==41249)
 check('start_binds_scope_and_packet',p['scope_id'] in strings(start) and h(packed(p)) in strings(start))
 check('worker_binds_scope_and_packet',p['scope_id'] in strings(worker) and h(packed(p)) in strings(worker))
 # Preserve only metadata fields; no source payload re-read.
 diagnostics['receipt']=receipt;diagnostics['start']=start;diagnostics['worker']=worker;diagnostics['complete']=complete;diagnostics['ledger_metrics']=ledger['metrics'];diagnostics['ledger_flags']={k:v for k,v in ledger.items() if isinstance(v,bool)}
 diagnostics['entry_return_constant_fields']=[{k.value:v.value for k,v in zip(n.keys,n.values) if isinstance(k,ast.Constant) and isinstance(v,ast.Constant)} for f in ast.parse(helper_raw).body if isinstance(f,ast.FunctionDef) and f.name=='production_parent' for n in ast.walk(f) if isinstance(n,ast.Dict)]
except BaseException as e:errors.append(type(e).__name__)
result={'kind':'INDEPENDENT_RETAINED_E01_OUTPUT_REVIEW','status':'PASS' if checks and all(checks.values()) and not errors else 'BLOCKED','checks':checks,'errors_types_only':errors,'refs':refs,'metadata':diagnostics,'logical_read_bytes':reads,'wall_seconds':time.monotonic()-t,'actual16_body_reads':0,'actual_reader_calls':0,'entry_executions':0,'network_calls':0,'model_calls':0,'current_owner_reads':0}
(out/'ACTUAL_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
