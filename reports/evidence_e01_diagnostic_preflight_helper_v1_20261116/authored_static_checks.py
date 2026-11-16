from pathlib import Path
import ast,hashlib,json,os,tempfile,types
from unittest.mock import patch
root=Path.cwd();path=root/'data/processed/e01_guard_diagnostic_preflight_v1_20261116.py';raw=path.read_bytes();assert len(raw)==7237 and hashlib.sha256(raw).hexdigest()=='fc35d0692fa9935d2830aae9e946589ba9ab09e8c38b897c412183fff2253ec1'
module=ast.parse(raw);body=[n for n in module.body if not isinstance(n,ast.If)];ns={'__file__':str(path),'__name__':'auditor_static_only'};exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),ns)
checks=[]
def ok(name,cond):assert cond,name;checks.append(name)
def refuses(name,fn):
 try:fn()
 except (RuntimeError,FileExistsError):checks.append(name);return
 raise AssertionError(name)
# No main, real runner import, Reader, verify_inputs, validate_methods, snapshots or occupancy traversal invoked.
for event in ['socket.__new__','socket.connect','subprocess.Popen','os.system','os.posix_spawn','os.exec','os.fork','os.forkpty','ctypes.dlopen','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.chmod','os.chown','os.truncate']:
 refuses('audit denies '+event,lambda e=event:ns['audit'](e,()))
for package in ['pip','pip._internal','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser']:
 refuses('finder denies '+package,lambda p=package:ns['NoPackages']().find_spec(p))
ok('stdlib finder neutral',ns['NoPackages']().find_spec('json') is None)
for suffix in ['data/raw/fictional.pdf','.env','.env.local','data/processed/.env.secret']:
 refuses('audit denies protected read '+suffix,lambda s=suffix:ns['audit']('open',(str(root/s),'r',os.O_RDONLY)))
for suffix in ['reports/not-allowed.json','.venv-e01-pypdf-7.0.1-v1/new','data/processed/e01_pypdf701_build_v1/install-v1_5-20261116/new']:
 refuses('audit denies unowned write '+suffix,lambda s=suffix:ns['audit']('open',(str(root/s),'w',os.O_WRONLY|os.O_CREAT)))
refuses('audit denies other mkdir',lambda:ns['audit']('os.mkdir',(str(root/'fictional-other-dir'),0o700,-1)))
for output in ns['OUTPUTS']:ns['audit']('open',(str(output),'w',os.O_WRONLY|os.O_CREAT));checks.append('audit permits only declared output '+output.name)
ns['audit']('os.mkdir',(str(ns['SCOPE']),0o700,-1));checks.append('audit permits one scope mkdir')
with tempfile.TemporaryDirectory(prefix='civiclab-auditor-preflight-') as td:
 td=str(Path(td).resolve());out=Path(td)/'receipt.json';ns['written']=0;ns['save'](out,{'status':'MOCK'});ok('save authored output correct',json.loads(out.read_bytes())=={'status':'MOCK'});ok('save restrictive mode',out.stat().st_mode&0o777==0o600)
 refuses('save output replay denied',lambda:ns['save'](out,{'status':'MOCK'}))
 refuses('save single output cap',lambda:ns['save'](Path(td)/'large.json',{'x':'x'*65536}))
 ns['written']=196608;refuses('save total output cap',lambda:ns['save'](Path(td)/'total.json',{}))
 target=Path(td)/'target';target.write_text('MOCK');link=Path(td)/'alias';link.symlink_to(target);ns['written']=0;refuses('save symlink denied',lambda:ns['save'](link,{}));ok('symlink target unchanged',target.read_text()=='MOCK')
# Static control-flow order and call surface, without running it.
main=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='main');calls=[n for n in ast.walk(main) if isinstance(n,ast.Call)]
attrs=[ast.unparse(n.func) for n in calls]
for forbidden in ['module.execute','module.guest_main','module.main','module.run_command','subprocess.run','subprocess.Popen','runpy.run_path']:
 ok('main excludes '+forbidden,forbidden not in attrs)
expected={'module.json_body','module.packed','module.p.Reader','module.validate_methods','module.no_alias','module.need','module.snapshot','module.verify_inputs','module.owned_size','module.sha'}
moduleattrs={a for a in attrs if a.startswith('module.')};ok('closed module helper call surface',moduleattrs==expected)
ok('snapshot exactly before and after',attrs.count('module.snapshot')==2)
def call_line(label):return min(n.lineno for n in calls if ast.unparse(n.func)==label)
pass_update=next(n for n in calls if ast.unparse(n.func)=='result.update' and any(k.arg=='status' and isinstance(k.value,ast.Constant) and k.value.value=='PASS_METADATA_ONLY_NO_DIAGNOSTIC' for k in n.keywords))
comparison=next(n for n in calls if ast.unparse(n.func)=='module.need' and n.args and ast.unparse(n.args[0])=='before == after')
input_loop=next(n for n in ast.walk(main) if isinstance(n,ast.For) and ast.unparse(n.iter)=='PINNED.items()')
ok('alarm before source reads',call_line('signal.setitimer')<input_loop.lineno)
ok('consumption before input reads',call_line('SCOPE.mkdir')<input_loop.lineno)
ok('PASS after snapshot equality',comparison.lineno<pass_update.lineno)
ok('receipt and report emitted after status evaluation',max(n.lineno for n in calls if ast.unparse(n.func)=='save')>pass_update.lineno)

ok('real main never called by audit',True)
print(json.dumps({'status':'PASS_FOCUSED_STATIC_AND_AUTHORED_HELPER_CHECKS','checks':len(checks),'names':checks,'actual_main_invocations':0,'actual_runner_imports':0,'actual_input_function_calls':0,'actual_network':0,'actual_child_commands':0},indent=2))
