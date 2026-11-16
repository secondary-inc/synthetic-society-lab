from pathlib import Path
import ast,hashlib,json,types
root=Path.cwd();old=root/'data/processed/e01_guard_diagnostic_preflight_v1_20261116.py';new=root/'data/processed/e01_guard_diagnostic_preflight_v2_20261116.py';raw=new.read_bytes();assert len(raw)==9049 and hashlib.sha256(raw).hexdigest()=='773bc7aa4a18ecdd211f040bc5ed4116285a39fa1ad2f1f38c242ac6aa38e81f';assert hashlib.sha256(old.read_bytes()).hexdigest()=='fc35d0692fa9935d2830aae9e946589ba9ab09e8c38b897c412183fff2253ec1'
a,b=ast.parse(old.read_bytes()),ast.parse(raw);nodes=[n for n in b.body if not isinstance(n,ast.If)];ns={'__file__':str(new),'__name__':'auditor_v2_static_only'};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(new),'exec'),ns)
checks=[]
def ok(name,condition):assert condition,name;checks.append(name)
def fail(name,fn):
 try:fn()
 except (RuntimeError,SyntaxError,KeyError,AttributeError):checks.append(name);return
 raise AssertionError(name)
for n in ['audit','save','no_alias','NoPackages']:
 x=next(x for x in a.body if getattr(x,'name',None)==n);y=next(x for x in b.body if getattr(x,'name',None)==n);ok(n+' unchanged',ast.dump(x)==ast.dump(y))
for n in ['PINNED','OUTPUT_LIMIT','CONTROL_LIMIT','READ_LIMIT','written']:
 x=next(x for x in a.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==n for t in x.targets));y=next(x for x in b.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==n for t in x.targets));ok(n+' unchanged',ast.dump(x)==ast.dump(y))
base='/MOCK/frozen-python';binding={'base_prefix':base};paths=[base+'/lib/python3.12',base+'/lib/python3.12/lib-dynload'];mime={'mode':'STDLIB_BUILTIN_TYPES_ONLY_DARWIN','knownfiles':[],'init_files':None,'initialized':True}
rsource=b"env={'PATH':str(Path(inputs['binding']['base_prefix'])/'bin')+':/usr/bin:/bin'}";fsource=b"env={'PATH':str(Path(binding['base_prefix'])/'bin')+':/usr/bin:/bin'}"
class PureP:
 MIME_RECEIPT=mime
 def __init__(self,p=paths,m=mime,raise_path=False,raise_mime=False):self.paths=p;self.mime=m;self.calls=[];self.raise_path=raise_path;self.raise_mime=raise_mime
 def narrowed_paths(self,original,base):
  self.calls.append(('paths',original,base))
  if self.raise_path:raise RuntimeError('MOCK_PATH_REFUSAL')
  return self.paths
 def prepare_builtin_mime(self,binding):
  self.calls.append(('mime',binding))
  if self.raise_mime:raise RuntimeError('MOCK_MIME_ORIGIN_REFUSAL')
  return self.mime
p=PureP();out=ns['configuration_proofs'](types.SimpleNamespace(p=p),binding,rsource,fsource)
ok('valid authored proof exact',out=={'current_narrowed_base_paths':paths,'stdlib_origin_validated_builtin_MIME':mime,'prescribed_child_PATH':base+'/bin:/usr/bin:/bin','child_PATH_matches_frozen_and_diagnostic_source_AST':True,'child_PATH_is_prescribed_not_observed_execution':True})
ok('only pure methods invoked',len(p.calls)==2 and p.calls[0][0]=='paths' and p.calls[1][0]=='mime')
for name,rs,fs in [('runner missing',b'x=1',fsource),('frozen missing',rsource,b'x=1'),('runner duplicated',rsource+b'\n'+rsource,fsource),('frozen duplicated',rsource,fsource+b'\n'+fsource),('runner changed route',rsource.replace(b'/usr/bin:/bin',b'/MOCK/other'),fsource),('frozen changed base',rsource,fsource.replace(b"/'bin'",b"/'other'")),('runner syntax',b'??',fsource),('frozen syntax',rsource,b'??'),('expression not evaluated',b"env={'PATH':__import__('subprocess').run(['MOCK'])}",fsource)]:
 p=PureP();fail(name,lambda p=p,rs=rs,fs=fs:ns['configuration_proofs'](types.SimpleNamespace(p=p),binding,rs,fs));ok(name+' refused before configuration functions',p.calls==[])
for name,wrong in [('empty',[]),('extra',paths+['/MOCK/extra']),('wrongbase',['/OTHER/lib/python3.12',paths[1]]),('missing',None),('tuple',tuple(paths))]:
 p=PureP(p=wrong);fail('bad narrowed paths '+name,lambda p=p:ns['configuration_proofs'](types.SimpleNamespace(p=p),binding,rsource,fsource));ok('bad paths '+name+' before MIME',len(p.calls)==1)
for name,wrong in [('empty',{}),('missing',None),('uninitialized',{**mime,'initialized':False}),('system-files',{**mime,'knownfiles':['/MOCK/system']}),('wrong-mode',{**mime,'mode':'SYSTEM'})]:
 fail('bad MIME '+name,lambda wrong=wrong:ns['configuration_proofs'](types.SimpleNamespace(p=PureP(m=wrong)),binding,rsource,fsource))
for flag in ['raise_path','raise_mime']:
 fail('frozen refusal propagates '+flag,lambda flag=flag:ns['configuration_proofs'](types.SimpleNamespace(p=PureP(**{flag:True})),binding,rsource,fsource))
# Source text inspection only; importing the real runner or real input functions is forbidden.
runner=(root/'scripts/diagnose_e01_pypdf701_guard_v1.py').read_bytes();frozen=(root/'scripts/install_e01_pypdf701_runtime_v1_5.py').read_bytes();out=ns['configuration_proofs'](types.SimpleNamespace(p=PureP()),binding,runner,frozen);ok('exact pinned production source PATH AST agrees',out['child_PATH_matches_frozen_and_diagnostic_source_AST'])
main=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='main');trybody=next(n for n in main.body if isinstance(n,ast.Try));proof=next(n for n in trybody.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='configuration_proofs');passcall=next(n for n in trybody.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and any(k.arg=='status' and isinstance(k.value,ast.Constant) and k.value.value=='PASS_METADATA_ONLY_NO_DIAGNOSTIC' for k in n.value.keywords));ok('mandatory proof before PASS',proof.lineno<passcall.lineno);ok('frozen source via charged reader',ast.unparse(proof.value.args[3])=='reader.read(module.FROZEN_REF)');ok('proof retained in PASS receipt',any(k.arg=='configuration_proofs' and isinstance(k.value,ast.Name) and k.value.id=='proofs' for k in passcall.value.keywords));ok('one outer exception path no PASS fallback',len(trybody.handlers)==1 and ast.unparse(trybody.handlers[0].type)=='Exception' and "status" not in ast.unparse(trybody.handlers[0]));ok('fresh v2 names',str(ns['SCOPE']).endswith('e01_guard_diagnostic_preflight_v2_20261116') and ns['REPORT'].name=='E01_GUARD_DIAGNOSTIC_PREFLIGHT_V2_20261116.json')
print(json.dumps({'status':'PASS_V2_CONFIGURATION_PROOF_STATIC_AND_AUTHORED_ADVERSE_CHECKS','checks':len(checks),'names':checks,'actual_main_invocations':0,'actual_real_runner_imports':0,'actual_real_input_functions':0,'actual_target_or_source_data_reads':0,'actual_network_or_child':0},indent=2))
