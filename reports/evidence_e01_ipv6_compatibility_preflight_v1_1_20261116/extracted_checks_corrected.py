from pathlib import Path
import ast,copy,hashlib,json,signal,resource,time,sys
started=time.monotonic();signal.alarm(120);resource.setrlimit(resource.RLIMIT_CPU,(110,120));resource.setrlimit(resource.RLIMIT_CORE,(0,0));root=Path.cwd();readbytes=0;checks=[];refs={}
def read(name):
 global readbytes
 b=(root/name).read_bytes();readbytes+=len(b);assert readbytes<=67108864;refs[name]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def ok(name,condition):assert condition,name;checks.append(name)
newpath='data/processed/e01_ipv6_compatibility_preflight_v1_1_20261116.py';oldpath='data/processed/e01_ipv6_compatibility_preflight_v1_20261116.py';raw=read(newpath);oldraw=read(oldpath);ok('exact helper pin',len(raw)==11611 and hashlib.sha256(raw).hexdigest()=='98c6b25d72b201f633d11add7719b9ee16707704e8c569dd8af2d5fe9294011f');a,b=ast.parse(oldraw),ast.parse(raw)
for name in ['audit','save','NoPackages','no_alias','configuration_proofs','compatibility_readonly_proofs']:
 x=next(n for n in a.body if getattr(n,'name',None)==name);y=next(n for n in b.body if getattr(n,'name',None)==name);ok('unchanged '+name,ast.dump(x)==ast.dump(y))
for name in ['READ_LIMIT','OUTPUT_LIMIT','CONTROL_LIMIT','written']:
 x=next(n for n in a.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets));y=next(n for n in b.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets));ok('unchanged '+name,ast.dump(x)==ast.dump(y))
pins=ast.literal_eval(next(n.value for n in b.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED' for t in n.targets)));bodies={}
for name,(size,digest) in pins.items():
 z=read(name);ok('exact declared pin '+name,len(z)==size and hashlib.sha256(z).hexdigest()==digest);bodies[name]=z
runner_path=next(iter(pins));runner=ast.parse(bodies[runner_path]);head=next(n for n in runner.body if isinstance(n,ast.FunctionDef) and n.name=='terminal_headroom')
def packed(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def need(c,name):
 if not c:raise RuntimeError(name)
ns={'packed':packed,'need':need};exec(compile(ast.Module(body=[head],type_ignores=[]),'<EXTRACTED_PURE_TERMINAL_HEADROOM>','exec'),ns);headfn=ns['terminal_headroom']
prior={'MOCK':1};before={'sha256':'a'*64,'entries_including_roots':8};orig=copy.deepcopy((prior,before));result=headfn(prior,before);ok('headroom valid exact bytes',result['ancestry_bytes']==len(packed({'prior':prior,'old_metadata_snapshot':before})) and result['other_reserved_bytes']==12288 and result['terminal_bytes_cap']==32768);ok('headroom does not mutate inputs',(prior,before)==orig)
basebytes=len(packed({'prior':'','old_metadata_snapshot':{}}));n=20480-basebytes;edge=headfn('x'*n,{});ok('headroom exact boundary accepted',edge['ancestry_bytes']==20480 and edge['maximum_supported_total']==32768)
for label,value in [('one over','x'*(n+1)),('large','x'*32768),('unicode expansion','\u00e9'*(n//2))]:
 try:headfn(value,{});raise AssertionError(label+' unexpectedly accepted')
 except RuntimeError:checks.append('headroom rejects '+label)
try:headfn(float('nan'),{});raise AssertionError('nonfinite accepted')
except ValueError:checks.append('nonfinite cannot claim headroom PASS')
main=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='main');trybody=next(n for n in main.body if isinstance(n,ast.Try));loop=next(n for n in trybody.body if isinstance(n,ast.For) and 'module.SUPERSEDED_ABSENT' in ast.unparse(n.iter));sup=ast.literal_eval(next(n.value for n in runner.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUPERSEDED_ABSENT' for t in n.targets)))
ok('superseded exact three paths',sup==['data/processed/e01_pypdf701_build_v1/compatibility-v1-20261116','data/processed/e01_pypdf701_build_v1/compatibility-v1-packet-20261116.json','.venv-e01-pypdf-7.0.1-COMPATIBILITY-NOT-INSTALL-v1'])
# Execute only the extracted absence loop with fabricated path objects, no filesystem calls.
class FakePath:
 def __init__(self,name,state):self.name=name;self.state=state
 def exists(self):return self.name in self.state['existing']
class FakeRoot:
 def __init__(self,state):self.state=state
 def __truediv__(self,name):return FakePath(name,self.state)
class FakeModule:
 OUTPUT='MOCK/new-scope';TARGET='MOCK/new-target';SUPERSEDED_ABSENT=sup
 def __init__(self,state):self.state=state
 def no_alias(self,path):need(path.name not in self.state['aliases'],'MOCK_ALIAS')
 need=staticmethod(need)
allnames=['MOCK/new-scope','MOCK/new-target','MOCK/new-packet']+sup
code=compile(ast.Module(body=[loop],type_ignores=[]),'<EXTRACTED_ABSENCE_LOOP>','exec')
state={'existing':set(),'aliases':set()};env={'ROOT':FakeRoot(state),'module':FakeModule(state),'methods':{'packet':'MOCK/new-packet'}};exec(code,env);checks.append('all six absent accepted without filesystem')
for category in ['existing','aliases']:
 for name in allnames:
  state={'existing':set(),'aliases':set()};state[category].add(name);env={'ROOT':FakeRoot(state),'module':FakeModule(state),'methods':{'packet':'MOCK/new-packet'}}
  try:exec(code,env);raise AssertionError(name+' not denied')
  except RuntimeError:checks.append('absence rejects '+category+' '+name)
headcall=next(n for n in trybody.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='module.terminal_headroom');passnode=next(n for n in trybody.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and any(k.arg=='status' and isinstance(k.value,ast.Constant) and k.value.value=='PASS_METADATA_ONLY_NO_DIAGNOSTIC' for k in n.value.keywords));ok('headroom mandatory before PASS',headcall.lineno<passnode.lineno);ok('headroom uses validated ancestry and before snapshot',ast.unparse(headcall.value)=="module.terminal_headroom(inputs['prior'], before)");ok('headroom proof retained',any(k.arg=='terminal_headroom' and ast.unparse(k.value)=='headroom' for k in passnode.value.keywords));ok('absence proof retained',any(k.arg=='superseded_v1_scope_packet_target_absent' and isinstance(k.value,ast.Constant) and k.value.value is True for k in passnode.value.keywords));ok('outer errors keep failure',len(trybody.handlers)==1 and ast.unparse(trybody.handlers[0].type)=='Exception' and 'status' not in ast.unparse(trybody.handlers[0]))
normal=copy.deepcopy(b);oldpins=next(n for n in a.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED' for t in n.targets));oldmain=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name=='main');oldtry=next(n for n in oldmain.body if isinstance(n,ast.Try));oldloop=next(n for n in oldtry.body if isinstance(n,ast.For) and 'module.OUTPUT' in ast.unparse(n.iter))
for node in normal.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED' for t in node.targets):node.value=copy.deepcopy(oldpins.value)
 if isinstance(node,ast.FunctionDef) and node.name=='main':
  tb=next(n for n in node.body if isinstance(n,ast.Try));tb.body=[n for n in tb.body if not(isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='module.terminal_headroom')]
  for n in ast.walk(tb):
   if isinstance(n,ast.For) and 'module.SUPERSEDED_ABSENT' in ast.unparse(n.iter):n.iter=copy.deepcopy(oldloop.iter)
   if isinstance(n,ast.Call) and ast.unparse(n.func)=='result.update':n.keywords=[k for k in n.keywords if k.arg not in ('terminal_headroom','superseded_v1_scope_packet_target_absent')]
renames={'data/processed/e01_ipv6_compatibility_preflight_v1_1_20261116':'data/processed/e01_ipv6_compatibility_preflight_v1_20261116','reports/E01_IPV6_COMPATIBILITY_PREFLIGHT_V1_1_20261116.json':'reports/E01_IPV6_COMPATIBILITY_PREFLIGHT_V1_20261116.json','E01_IPV6_COMPATIBILITY_READONLY_PREFLIGHT_V1_1':'E01_IPV6_COMPATIBILITY_READONLY_PREFLIGHT_V1','LEAD_E01_IPV6_COMPATIBILITY_READONLY_PREFLIGHT_V1_1':'LEAD_E01_IPV6_COMPATIBILITY_READONLY_PREFLIGHT_V1'}
for n in ast.walk(normal):
 if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value in renames:n.value=renames[n.value]
ok('whole delta exactly accounted for',ast.dump(normal)==ast.dump(a));signal.alarm(0)
result={'decision':'PASS_EXACT_V1_1_STATIC_DELTA_AND_EXTRACTED_ADVERSE_CHECKS_ONLY','checks':len(checks),'names':checks,'refs':refs,'runtime':sys.version,'elapsed_seconds':time.monotonic()-started,'review_allowance':{'suite_invocations_this_runtime':1,'runtimes_used':2,'wall_limit_seconds':120,'CPU_soft_hard_seconds':[110,120],'application_source_read_bytes':readbytes,'application_read_cap':67108864,'temp_write_cap':33554432,'per_invocation_output_cap':262144},'actual_main_real_inputs_socket_pip_child_owner_credential_network_calls':0};out=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode();assert len(out)<262144;Path('/tmp/civiclab-auditor-ipv6-preflight-v1_1-20261116.json').write_bytes(out);print(json.dumps({'decision':result['decision'],'checks':len(checks),'bytes_read':readbytes,'elapsed_seconds':result['elapsed_seconds']}))
