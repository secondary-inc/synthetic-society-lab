"""Independent authored-only saved JSON component probe, no real inputs."""
import sys,os,time,resource,signal,ast,json,hashlib,io,types,unittest,builtins,importlib.util,symtable
from pathlib import Path
START=time.monotonic()
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('INDEPENDENT180')));signal.alarm(180)
ROOT=Path.cwd();SOURCE=ROOT/'src/civiclab/e01/saved_json_job_ledger_v1.py';TEST=ROOT/'tests/test_e01_saved_json_job_ledger_v1.py';ENTRY=ROOT/'scripts/compile_e01_saved_json_job_ledger_v1_20261117.py'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='684eb291c1d462afe07d994b7c940290fa26e5fb89907212e75dc69085562010'
test_raw=TEST.read_bytes();assert hashlib.sha256(test_raw).hexdigest()=='688d2830e456a7fc77d31ec94c3cbad7a0548a0e9e87b12b355aa25d596a32f8'
spec=importlib.util.spec_from_file_location('frozen_authored_saved_json_cases',TEST);T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T);T.builtins=builtins
holder=[None];outer={'file_read_bytes':0,'logical_fixture_read_bytes':0,'logical_output_bytes':0,'denials':0};stdlib=Path(os.__file__).resolve().parent
def audit(event,args):
    if holder[0] is not None and holder[0]._ACTIVE is not None:return
    if event.startswith(('socket.','subprocess.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec','os.kill'}:
        outer['denials']+=1;raise PermissionError('NO_EXTERNAL_ACTION')
    if event=='open':
        name,mode,flags=args
        if type(name) is int:raise PermissionError('NO_UNDECLARED_FD')
        p=Path(os.fsdecode(name)).absolute()
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('NO_HOST_WRITES')
        if p not in {SOURCE,TEST,ENTRY,Path(sys.executable).absolute()} and not p.is_relative_to(stdlib):
            outer['denials']+=1;raise PermissionError('NO_PRIVATE_OR_UNLISTED_READ')
        outer['file_read_bytes']+=p.stat().st_size+1
        if outer['file_read_bytes']+outer['logical_fixture_read_bytes']>134217728:raise RuntimeError('READ_LIMIT')
sys.addaudithook(audit)
M=types.ModuleType('independent_authored_saved_json');M.__file__=str(SOURCE)
exec(compile(SOURCE.read_bytes(),str(SOURCE),'exec'),M.__dict__);holder[0]=M
original_read=M.Budget.read;original_write=M.Budget.write
def charged_read(b,n,project=False):
    before=b.saved+b.project
    try:return original_read(b,n,project)
    finally:
        outer['logical_fixture_read_bytes']+=b.saved+b.project-before
        if outer['file_read_bytes']+outer['logical_fixture_read_bytes']>134217728:raise RuntimeError('READ_LIMIT')
def charged_write(b,n,control=False):
    before=b.written
    try:return original_write(b,n,control)
    finally:
        outer['logical_output_bytes']+=b.written-before
        if outer['logical_output_bytes']>33554432:raise RuntimeError('WRITE_LIMIT')
M.Budget.read=charged_read;M.Budget.write=charged_write
runtime=M.RuntimePin()
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(T._authored_suite(M,runtime));runtime.verify()
# Extract only exact fixed fixture/reader helpers, no additional suite or child.
factory=next(n for n in ast.parse(test_raw).body if isinstance(n,ast.FunctionDef) and n.name=='_authored_suite')
nodes=[n for n in factory.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'ref','fixture','Reader','run'}]
assert len(nodes)==4
env={'M':M,'runtime':runtime,'Path':Path,'hashlib':hashlib,'json':json,'io':io,'os':os,'builtins':builtins,'sys':sys}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<exact-authored-fixture-helpers>','exec'),env)
OBS=[]
def record(name,passed,**d):OBS.append({'case':name,'pass':bool(passed),**d})
budget=M.Budget();s=M.ReadOnlyStream(b'x',budget)
def io_error():raise OSError('AUTHORED_NATIVE_ERROR_TYPE')
try:s.checked(io_error,())
except M.Refused:pass
record('OSError_checked_latches',budget.primary is not None and budget.primary.code=='INPUT_IO')
for method in ('read','read1','readline','readlines','readinto','readinto1'):
    observed={'caught':None};scope=M.Scope()
    def after(path,root,contract,value):
        f=(path/'typed_document_readiness.json').open('rb');f.close()
        try:getattr(f,method)(bytearray(1)) if method in ('readinto','readinto1') else getattr(f,method)()
        except (M.Refused,OSError,ValueError) as error:observed['caught']=type(error).__name__
    try:
        run=env['run'](reader=env['Reader'](after),scope=scope)
        completed=True;latched=run['budget']['failed'];raised=None
    except M.Refused as error:completed=False;latched=True;raised=error.code
    record('closed_stream_'+method,not completed and latched and 'COMPLETE.json' not in scope.files,completed=completed,latched=latched,caught=observed['caught'],raised=raised)
    runtime.verify()
for method in ('read','read1','readline','readlines','readinto','readinto1'):
    b=M.Budget();f=M.ReadOnlyStream(b'abc\n',b)
    if method in ('readinto','readinto1'):
        target=bytearray(4);first=getattr(f,method)(target);second=getattr(f,method)(target)
        ok=first==4 and second==0 and bytes(target)==b'abc\n'
    else:
        first=getattr(f,method)();second=getattr(f,method)()
        ok=(first==[b'abc\n'] and second==[]) if method=='readlines' else (first==b'abc\n' and second==b'')
    record('positive_EOF_'+method,ok and b.primary is None)
record('guard_restored',M._ACTIVE is None)
record('no_actual_import',not any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules))
report={'kind':'INDEPENDENT_E01_SAVED_JSON_READ_FAMILY_FIX_PROBE','runtime':sys.version.split()[0],
        'exact_author_suite':{'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'diagnostic_sha256':hashlib.sha256(stream.getvalue().encode()).hexdigest()},
        'independent_observations':OBS,'failed_case_names':[x['case'] for x in OBS if not x['pass']],
        'resource_counters':outer,'selected_runtime_read_bytes':runtime.logical_read_bytes,'actual_saved_payload_reads':0,
        'actual_reader_calls':0,'network_calls':0,'model_calls':0,'cost_usd':0,'wall_seconds':time.monotonic()-START,'startup_accounting':'NOT_COMPLETE_COLD_PROFILE'}
if not result.wasSuccessful():report['bounded_first_error']=(result.errors or result.failures)[0][1][:4000]
text=json.dumps(report,sort_keys=True);assert len(text.encode())<=262144;print(text)
