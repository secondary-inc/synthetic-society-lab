from pathlib import Path
import ast,hashlib,json,types,copy
root=Path.cwd();path=root/'data/processed/e01_ipv6_compatibility_preflight_v1_20261116.py';raw=path.read_bytes();tree=ast.parse(raw);prior=ast.parse((root/'data/processed/e01_guard_diagnostic_preflight_v3_20261116.py').read_bytes());checks=[]
def ok(name,c):assert c,name;checks.append(name)
for name in ['audit','save','NoPackages','no_alias','configuration_proofs']:
 x=next(n for n in prior.body if getattr(n,'name',None)==name);y=next(n for n in tree.body if getattr(n,'name',None)==name);ok('unchanged '+name,ast.dump(x)==ast.dump(y))
for name in ['READ_LIMIT','OUTPUT_LIMIT','CONTROL_LIMIT','written']:
 x=next(n for n in prior.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets));y=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets));ok('unchanged '+name,ast.dump(x)==ast.dump(y))
pins=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED' for t in n.targets)))
for name,(size,sha) in pins.items():
 b=(root/name).read_bytes();ok('declared pin '+name,len(b)==size and hashlib.sha256(b).hexdigest()==sha)
proof=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='compatibility_readonly_proofs');fake_sys=types.SimpleNamespace(modules={});ns={'Path':Path,'sys':fake_sys};exec(compile(ast.Module(body=[proof],type_ignores=[]),str(path),'exec'),ns);fn=ns['compatibility_readonly_proofs'];relative='.MOCK/pip/_vendor/urllib3/util/connection.py';binding={'pip_root':'.MOCK/pip','pip_files':{relative:{'bytes':3,'sha256':'a'*64}}};socket_ref={'bytes':3,'sha256':'b'*64}
class Reader:
 def __init__(self,fail_at=None):self.calls=[];self.fail_at=fail_at
 def read(self,ref,absolute=False):
  self.calls.append((copy.deepcopy(ref),absolute))
  if len(self.calls)==self.fail_at:raise RuntimeError('MOCK_BOUND_READ_REFUSAL')
  return b'---'
def make(ipv6=True,active=None,failed=False,held=False,owner_ok=True,socket_ok=True):
 sock=types.SimpleNamespace(has_ipv6=ipv6,__file__='/MOCK/socket.py');calls=[]
 def checked(b,r):
  calls.append('checked_socket')
  if not socket_ok:raise RuntimeError('MOCK_SOCKET_IDENTITY_SOURCE_REFUSAL')
  r.read({'path':sock.__file__,**socket_ref},absolute=True);return sock
 def owner():calls.append('Owner');return object()
 def single(o):
  calls.append('single_owner')
  if not owner_ok:raise RuntimeError('MOCK_SINGLE_OWNER_REFUSAL')
 a=types.SimpleNamespace(checked_socket=checked,Owner=owner,single_owner=single,_ACTIVE=active,_FAILED=failed,_imp=types.SimpleNamespace(lock_held=lambda:held),SOCKET_REF=socket_ref)
 def need(v,c):
  if not v:raise RuntimeError(c)
 return types.SimpleNamespace(a=a,need=need),sock,calls
m,sock,calls=make();reader=Reader();out=fn(m,binding,reader);ok('authored valid proof returns',out['current_original_has_ipv6'] is True and out['fresh_adapter_state'] is True);ok('actual closure explicitly NOT_RUN',out['actual_import_closure']=='NOT_RUN_ENFORCED_AND_RECORDED_IN_PROSPECTIVE_CHILD');ok('no mutation of fabricated socket',sock.has_ipv6 is True);ok('only readonly adapter methods used',calls==['checked_socket','Owner','single_owner']);ok('genuine reader bindings forwarded',reader.calls==[({'path':'/MOCK/socket.py',**socket_ref},True),({'path':relative,'bytes':3,'sha256':'a'*64},False)]);ok('child recheck and zero overrides',out['child_must_recheck_current_state'] is True and out['real_socket_field_mutations']==out['vendor_imports']==out['import_lock_acquisitions']==0)
def refused(name,options=None,modules=None,b=None,failread=None):
 fake_sys.modules={} if modules is None else modules;m,s,c=make(**(options or {}));r=Reader(failread)
 try:fn(m,binding if b is None else b,r)
 except (RuntimeError,KeyError):checks.append(name);ok(name+' no socket mutation',s.has_ipv6==((options or {}).get('ipv6',True)));return
 raise AssertionError(name)
for value in [False,1,None]:refused('original hasipv6 not literalTrue '+repr(value),{'ipv6':value})
refused('socket identity/source refusal',{'socket_ok':False});refused('active adapter denied',{'active':object()});refused('failed adapter denied',{'failed':True});refused('nonliteralfalse failed denied',{'failed':None});refused('held importlock denied',{'held':True});refused('single owner denial propagated',{'owner_ok':False});refused('module importinitializing denied',modules={'MOCK':types.SimpleNamespace(__spec__=types.SimpleNamespace(_initializing=True))});refused('module count1025 denied',modules={str(n):None for n in range(1025)});refused('pip preloaded denied',modules={'pip':None});refused('pip vendor preloaded denied',modules={'pip._vendor.urllib3':None});refused('probe absent from pins denied',b={'pip_root':'.MOCK/pip','pip_files':{}});refused('socket boundread failure',failread=1);refused('probe boundread failure',failread=2)
callnames={ast.unparse(n.func) for n in ast.walk(proof) if isinstance(n,ast.Call)}
for name in ['adapter.initialize_offline','adapter.scoped','adapter.Closure','adapter._imp.acquire_lock','adapter._imp.release_lock','adapter.find_spec']:
 ok('readonly excludes '+name,name not in callnames)
ok('no writes to socket or adapter attributes',not any(isinstance(n,ast.Attribute) and isinstance(n.ctx,ast.Store) for n in ast.walk(proof)))
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');trybody=next(n for n in main.body if isinstance(n,ast.Try));comp=next(n for n in trybody.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='compatibility_readonly_proofs');passnode=next(n for n in trybody.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and any(k.arg=='status' and isinstance(k.value,ast.Constant) and k.value.value=='PASS_METADATA_ONLY_NO_DIAGNOSTIC' for k in n.value.keywords));ok('compatibility proof before PASS',comp.lineno<passnode.lineno);ok('proof retained',any(k.arg=='compatibility_readonly_proofs' and ast.unparse(k.value)=='compatibility' for k in passnode.value.keywords));ok('same outer error path',len(trybody.handlers)==1 and ast.unparse(trybody.handlers[0].type)=='Exception' and 'status' not in ast.unparse(trybody.handlers[0]));ok('original genuine Reader construction','reader = module.p.Reader(ROOT, READ_LIMIT)' in ast.unparse(main))
# Complete mechanical comparison after removing only the declared additional proof/delta.
normal=copy.deepcopy(tree);normal.body=[n for n in normal.body if getattr(n,'name',None)!='compatibility_readonly_proofs'];oldpins=next(n for n in prior.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED' for t in n.targets))
for n in normal.body:
 if isinstance(n,ast.FunctionDef) and n.name=='main':
  tb=next(t for t in n.body if isinstance(t,ast.Try));tb.body=[t for t in tb.body if not(isinstance(t,ast.Assign) and isinstance(t.value,ast.Call) and ast.unparse(t.value.func)=='compatibility_readonly_proofs')]
  for t in ast.walk(tb):
   if isinstance(t,ast.Call) and ast.unparse(t.func)=='result.update':t.keywords=[k for k in t.keywords if k.arg!='compatibility_readonly_proofs']
for n in ast.walk(normal):
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED' for t in n.targets):n.value=copy.deepcopy(oldpins.value)
renames={'One read-only compatibility-input preflight; no compatibility override, pip or child call.':'One read-only diagnostic-input preflight; no diagnostic, pip or child call.','data/processed/e01_ipv6_compatibility_preflight_v1_20261116':'data/processed/e01_guard_diagnostic_preflight_v3_20261116','reports/E01_IPV6_COMPATIBILITY_PREFLIGHT_V1_20261116.json':'reports/E01_GUARD_DIAGNOSTIC_PREFLIGHT_V3_20261116.json','E01_IPV6_COMPATIBILITY_READONLY_PREFLIGHT_V1':'E01_GUARD_DIAGNOSTIC_READONLY_PREFLIGHT_V3','LEAD_E01_IPV6_COMPATIBILITY_READONLY_PREFLIGHT_V1':'LEAD_E01_GUARD_DIAGNOSTIC_READONLY_PREFLIGHT_V3'}
for n in ast.walk(normal):
 if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value in renames:n.value=renames[n.value]
ok('entire delta accounted for',ast.dump(normal)==ast.dump(prior))
print(json.dumps({'status':'PASS_EXTRACTED_PURE_STATIC_HELPER_REVIEW_NO_REAL_INPUTS','checks':len(checks),'names':checks,'helper':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'main_calls':0,'real_adapter_imports':0,'real_socket_operations':0,'real_input_function_calls':0,'network_child_owner_source_credential_actions':0},indent=2))
