"""Independent inert-only probe; no real tool loading or OS writes."""
import sys

def early(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','ctypes.dlopen'}:
        raise AssertionError('NO_NETWORK_PROCESS_NATIVE')
    if event == 'import' and args and args[0].split('.')[0] in {'installer','pip','ssl_fixture_payload','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:
        raise AssertionError('NO_TOOL_PAYLOAD_OR_TARGET_IMPORT')
sys.addaudithook(early)

import ast
import builtins
import io
import zipfile
from types import SimpleNamespace
import hashlib
import json
import os
from pathlib import Path
import resource
import runpy
import signal

ROOT=Path(__file__).resolve().parents[2]
ME=Path(__file__).resolve()
TEST=ROOT/'tests/test_e01_pypa_fixture_harness_candidate_v1_1_20261116.py'
CODE=ROOT/'scripts/e01_pypa_fixture_harness_candidate_v1_1_20261116.py'
allowed={ME,TEST,CODE,*[ROOT/'scripts'/name for name in (
    'e01_strict_wheel_source_candidate_v1_20261116.py',
    'install_e01_pypdf701_runtime_v1_5.py',
    'e01_authored_dirfd_guard_v2_20261112.py')]}
TOOL=ROOT/'data/processed/e01_installer_tool_source_v1_20261116/2-RESPONSE.bin'
STDLIB_SOURCE=Path(sys.base_prefix)/'lib'/('python%d.%d'%sys.version_info[:2])/'dataclasses.py'
SCHEMA_FILE=ROOT/'reports/evidence_e01_pypa_fixture_harness_independent_v1_1_20261116/STATIC_TOOL_DATACLASS_SCHEMAS.json'
allowed.update({TOOL,STDLIB_SOURCE,SCHEMA_FILE,Path(sys.executable).resolve()})
stdlib=(Path(sys.base_prefix)/'lib').resolve()
reads=0
registered={}
raw_open,raw_close,raw_fdopen=os.open,os.close,os.fdopen
def identity(st):return st.st_dev,st.st_ino,st.st_mode
def audit(event,args):
    global reads
    if event=='open':
        if type(args[0]) is int:
            record=registered.get(args[0])
            if record is None:raise AssertionError('UNKNOWN_FILE_DESCRIPTOR')
            p,expected=record
            if identity(os.fstat(args[0]))!=expected or identity(p.stat(follow_symlinks=False))!=expected:
                raise AssertionError('REUSED_OR_MOVED_FILE_DESCRIPTOR')
            if any(v.is_symlink() for v in (p,*p.parents)):raise AssertionError('ALIASED_FILE_DESCRIPTOR')
        elif isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.path.realpath(args[0]))
        else:raise AssertionError('NO_DESCRIPTOR_IO')
        flags=args[2]
        if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise AssertionError('NO_OS_WRITES')
        if not (p in allowed or (p.is_relative_to(stdlib) and 'site-packages' not in p.parts)):
            raise AssertionError('UNAPPROVED_READ')
        try: reads+=p.stat().st_size+1
        except FileNotFoundError: reads+=1
        if reads>67108864:raise AssertionError('READ_CAP')
    if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.truncate','os.chmod'}:
        raise AssertionError('NO_OS_MUTATIONS')
def tracked_open(path,flags,*args,**kwargs):
    p=Path(path)
    if not p.is_absolute() or p not in allowed or kwargs.get('dir_fd') is not None:
        raise AssertionError('ONLY_EXACT_OWN_SOURCE_DESCRIPTOR')
    if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('NO_DESCRIPTOR_WRITES')
    if any(v.is_symlink() for v in (p,*p.parents)):raise AssertionError('NO_DESCRIPTOR_ALIAS')
    fd=raw_open(path,flags,*args,**kwargs)
    expected=identity(os.fstat(fd))
    if identity(p.stat(follow_symlinks=False))!=expected:
        raw_close(fd);raise AssertionError('OPENED_FILE_IDENTITY')
    registered[fd]=(p,expected)
    return fd
def tracked_close(fd):
    registered.pop(fd,None)
    return raw_close(fd)
class TrackedStream:
    def __init__(self,stream,fd):self.stream,self.fd=stream,fd
    def __getattr__(self,name):return getattr(self.stream,name)
    def __enter__(self):return self
    def close(self):
        registered.pop(self.fd,None)
        return self.stream.close()
    def __exit__(self,*args):self.close()
def tracked_fdopen(fd,*args,**kwargs):
    # Raw fdopen emits the audit event; only its registered identity is admitted.
    return TrackedStream(raw_fdopen(fd,*args,**kwargs),fd)
sys.addaudithook(audit)
os.open,os.close,os.fdopen=tracked_open,tracked_close,tracked_fdopen
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def timeout(*_):raise AssertionError('WALL_CAP')
signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
assert hashlib.sha256(CODE.read_bytes()).hexdigest()=='1c55c942b061452f741d1242640fd1b85a8f11b398a30fea6c391525006b20b8'
assert hashlib.sha256(TEST.read_bytes()).hexdigest()=='8236f2fcaaf325af67bf1c134fb98a4f18445e18af18330ce7f34fdb96e1bedc'
ns=runpy.run_path(str(TEST),run_name='independent_remedy_mock_definitions')
m=ns['m'];MockAPI=ns['MockAPI'];checks=[]
def check(name,value):
    checks.append({'name':name,'pass':bool(value)})
    if not value:raise AssertionError(name)
def refuses(name,call,kind,code=None,identity=None):
    try:call()
    except kind as error:
        check(name, (code is None or getattr(error,'code',None)==code) and (identity is None or error is identity))
        return error
    raise AssertionError(name+': did not refuse')
pure=m.own_module(m.PURE_REF,'independent_remedy_pure')
base=m.own_module(m.POLICY_REF,'independent_remedy_policy')
fd=m.own_module(m.FD_REF,'independent_remedy_dirfd')
binding=m.bind_runtime_compile(m.SharedBudget())
check('runtime binding matches interpreter',binding.runtime==sys.version.split()[0])

# Inert schemas were independently recorded by static source inspection.
# No third-party source is compiled to bytecode or executed. Probe loads only
# the owned technical schema record and archive bytes for callback arguments.
raw=TOOL.read_bytes()
check('pinned archive',len(raw)==464466 and m.sha(raw)=='f55f5728ff61d3dd54dbc5a397cf3f7307cb64b180c20b72afbebf01c9e2c8a0')
archive=zipfile.ZipFile(io.BytesIO(raw));schemas=[]
for row in json.loads(SCHEMA_FILE.read_bytes()):
    defaults={}
    no_repr=[]
    for name,text in row['default_field_AST'].items():
        if name=='section':
            check('source-derived repr=False field',text=="Call(func=Name(id='field', ctx=Load()), args=[], keywords=[keyword(arg='repr', value=Constant(value=False))])")
            no_repr.append(name)
        else:
            expected={'hash_algorithm':("Constant(value='sha256')",'sha256'),'bytecode_optimization_levels':('Tuple(elts=[], ctx=Load())',()),'destdir':('Constant(value=None)',None),'overwrite_existing':('Constant(value=False)',False)}
            check('source-derived default '+name,name in expected and text==expected[name][0])
            defaults[name]=expected[name][1]
    schemas.append({'module':row['member'][:-3].replace('/','.'),'class':row['class'],'line':row['decorator_line'],'fields':row['fields'],'defaults':defaults,'no_repr':no_repr,'methods':set(row['methods'])})
check('five source derived classes',len(schemas)==5)
for independent,declared in zip(schemas,m.DATACLASS_SCHEMAS):
    check('schema '+independent['class'],(independent['module'],independent['class'],independent['line'],tuple(independent['fields']),tuple(name for name in independent['fields'] if name in independent['defaults']),tuple(independent['no_repr']),'__post_init__' in independent['methods'])==declared)

captured=[];dc=binding.module;original_exec=builtins.exec
def intercept(source,globals=None,locals=None,**kwargs):
    check('stdlib generator origin',sys._getframe(1).f_code is binding.codes['_create_fn'] and type(source) is str)
    captured.append(source.encode())
    locals['__create_fn__']=lambda **kw:(lambda *a,**k:None)
try:
    builtins.exec=intercept
    for schema in schemas:
        attributes={'__module__':__name__,'__doc__':'Independent authored inert schema','__annotations__':{v:object for v in schema['fields']}}
        attributes.update(schema['defaults'])
        for name in schema['no_repr']:attributes[name]=dc.field(repr=False)
        for name in schema['methods']&{'__post_init__','__repr__','__eq__'}:attributes[name]=lambda *args:None
        dc.dataclass(type('IndependentInertSchema',(Exception,) if '__post_init__' in schema['methods'] else (object,),attributes))
finally:builtins.exec=original_exec
plan=m.generated_compile_plan(binding.runtime)
check('all fifteen generated texts exact without execution',len(captured)==15 and captured==[row['source'] for row in plan])
def frames(row,snapshot):
    filename=str(snapshot)+'/'+row['module'].replace('.','/')+'.py'
    def inert():pass
    tool=SimpleNamespace(f_code=inert.__code__.replace(co_name='<module>',co_filename=filename),f_lineno=row['line'],f_globals={'__name__':row['module'],'__file__':filename,'__spec__':SimpleNamespace(origin=filename)},f_back=None)
    helper={'__init__':'_init_fn','__repr__':'_repr_fn','__eq__':'_cmp_fn'}[row['method']]
    frame=tool
    for name in reversed(('_create_fn',helper,'_process_class','wrap','dataclass')):
        frame=SimpleNamespace(f_code=binding.codes[name],f_globals=binding.module.__dict__,f_back=frame)
    return frame,tool
snapshot=Path('/SSL_INDEPENDENT_COMPILE/controls/installer-1.1.0-py3-none-any.whl')
gate=m.GeneratedCompileGate(binding)
for row in plan:
    frame,tool=frames(row,snapshot)
    gate._admit(row['source'],'<string>','TOOL_LOAD',snapshot,frame)
gate.finish();check('finite ordered admission',gate.index==15 and not gate.failed)
refuses('sixteenth compile denied',lambda:gate._admit(plan[-1]['source'],'<string>','TOOL_LOAD',snapshot,frames(plan[-1],snapshot)[0]),m.HarnessRefused,'FIXTURE_GENERATED_COUNT')
for mutation in ('append','phase','filename','out_of_order','copied_code','copied_globals','short_stack','wrong_helper','tool_line','tool_spec','tool_file','tool_name','tool_code','wrong_snapshot'):
    gate=m.GeneratedCompileGate(binding);row=gate.plan[0];frame,tool=frames(row,snapshot)
    source=row['source']+b'\n' if mutation=='append' else gate.plan[1]['source'] if mutation=='out_of_order' else row['source']
    if mutation=='copied_code':frame.f_code=frame.f_code.replace()
    if mutation=='copied_globals':frame.f_globals=dict(frame.f_globals)
    if mutation=='short_stack':frame.f_back=None
    if mutation=='wrong_helper':frame.f_back.f_code=binding.codes['_repr_fn']
    if mutation=='tool_line':tool.f_lineno+=1
    if mutation=='tool_spec':tool.f_globals['__spec__'].origin='/WRONG'
    if mutation=='tool_file':tool.f_globals['__file__']='/WRONG'
    if mutation=='tool_name':tool.f_globals['__name__']='WRONG'
    if mutation=='tool_code':tool.f_code=tool.f_code.replace(co_filename='/WRONG')
    actual_snapshot=Path('/WRONG') if mutation=='wrong_snapshot' else snapshot
    refuses('generated refusal '+mutation,lambda:gate._admit(source,'OTHER' if mutation=='filename' else '<string>','INSTALL' if mutation=='phase' else 'TOOL_LOAD',actual_snapshot,frame),m.HarnessRefused)
    check('generated latch '+mutation,gate.failed and gate.index==0)
    refuses('generated no recovery '+mutation,lambda:gate._admit(row['source'],'<string>','TOOL_LOAD',snapshot,frames(row,snapshot)[0]),m.HarnessRefused,'FIXTURE_GENERATED_COUNT')
gate=m.GeneratedCompileGate(binding);refuses('missing events finish',gate.finish,m.HarnessRefused,'FIXTURE_GENERATED_INCOMPLETE')
check('incomplete permanently latched',gate.failed)
for name in ('installer/records.py','installer/scripts.py','installer/destinations.py'):
    policy=m.policy_class(base.GuestPolicy)(snapshot.parent.parent,m.SharedBudget(pure));policy.phase_set('TOOL_LOAD')
    body=archive.read(name)
    policy.audit('compile',(body,str(snapshot)+'/'+name))
    check('pinned tool source callback '+name,name in policy.tool_compiled)
    refuses('tool duplicate callback '+name,lambda:policy.audit('compile',(body,str(snapshot)+'/'+name)),base.Refused)
    check('tool duplicate sticky '+name,policy.compile_failed)
for content,filename,phase in [(b'ARBITRARY',str(snapshot)+'/installer/records.py','TOOL_LOAD'),(plan[0]['source'],'<string>','TOOL_LOAD'),(plan[0]['source'],'<string>','INSTALL'),(b'','#not-a-tool','TOOL_LOAD')]:
    policy=m.policy_class(base.GuestPolicy)(snapshot.parent.parent,m.SharedBudget(pure));policy.generated_compile=m.GeneratedCompileGate(binding);policy.phase_set(phase)
    refuses('real callback denies forged/altered compile',lambda:policy.audit('compile',(content,filename)),base.Refused)
    check('original compile violation retained',policy.violations==1 and policy.compile_failed)

counterexamples=[]
for kind in ('read','write'):
    for behavior in ('resume_writer','masked_return','secondary_error'):
        class CatchingAPI(MockAPI):
            first=None
            def install(self,source,destination,additional_metadata):
                shared=destination[0].policy.shared
                try:getattr(shared,kind)(33554432)
                except m.HarnessRefused as error:self.first=error
                if behavior=='resume_writer':return super().install(source,destination,additional_metadata)
                self.calls+=1
                if behavior=='secondary_error':raise RuntimeError('INDEPENDENT_SECONDARY')
        fs=m.MemoryFS();api=CatchingAPI()
        error=refuses('caught budget '+kind+'/'+behavior,lambda:m.drive_mock(api,fs),m.HarnessRefused,'FIXTURE_'+kind.upper()+'_CAP')
        terminal=json.loads(fs.files[str(fs.root/'controls/TERMINAL.json')]);failure=json.loads(fs.files[str(fs.root/'controls/FAILED_CASE.json')])
        check('first budget identity '+kind+'/'+behavior,error is api.first)
        check('no success '+kind+'/'+behavior,terminal['outcome']=='FAILED_FIXTURE_HARNESS' and terminal['usage']['failed'] and terminal['cases']==[] and api.calls==1)
        check('bounded failure evidence '+kind+'/'+behavior,len(fs.files[str(fs.root/'controls/TERMINAL.json')])<=32768 and failure['partial_manifest']=={} and not terminal['installation_accepted'])
        counterexamples.append({'kind':kind,'behavior':behavior,'outcome':terminal['outcome'],'cases':len(terminal['cases']),'mock_calls':api.calls,'preserved_first_identity':error is api.first,'usage':terminal['usage']})
    budget=m.SharedBudget(pure);raw_fixture=m.make_fixture('VALID')
    token=pure.validate_wheel(raw_fixture,expected_sha256=m.sha(raw_fixture),filename=m.FILENAME,budget=budget.strict_reads)
    stream=token.open();first=refuses('initial cap '+kind,lambda:getattr(budget,kind)(33554432),m.HarnessRefused)
    for call in (budget.check,budget.healthy,lambda:budget.read(0),lambda:budget.write(0),lambda:budget.write(1,control=True)):
        refuses('sticky identity '+kind,call,m.HarnessRefused,identity=first)
    refuses('held stream poisoned '+kind,lambda:stream.read(1),pure.WheelRefused,'READ_BUDGET_FAILED');stream.close()
    refuses('new stream poisoned '+kind,token.open,pure.WheelRefused,'READ_BUDGET_FAILED')
    budget.close_for_evidence();budget.read(32768,control=True);budget.write(32768,control=True)
    before=(budget.closure_reads,budget.closure_writes,budget.file_reads,budget.writes)
    refuses('closure read cap '+kind,lambda:budget.read(1,control=True),m.HarnessRefused,'FIXTURE_CLOSURE_READ_CAP')
    refuses('closure write cap '+kind,lambda:budget.write(1,control=True),m.HarnessRefused,'FIXTURE_CLOSURE_WRITE_CAP')
    check('closure counters never overflow '+kind,before==(budget.closure_reads,budget.closure_writes,budget.file_reads,budget.writes))
    refuses('operational closure cannot reopen '+kind,budget.healthy,m.HarnessRefused,identity=first)
    refuses('strict cannot reattach '+kind,lambda:budget.attach_strict(pure),m.HarnessRefused,'FIXTURE_STRICT_BUDGET_REENTRY')
healthy=m.drive_mock(MockAPI());terminal=healthy['terminal']
check('healthy eight cases three mock calls',len(terminal['cases'])==8 and terminal['usage']['install_attempts']==3 and terminal['outcome']=='FIXTURE_ASSERTIONS_PASS_ONLY' and not terminal['usage']['failed'])
check('seven file output oracle',len(m.verify_output(healthy['fs'],healthy['fs'].root/'prefixes/VALID'))==7)
check('healthy terminal bounded',healthy['terminal_ref']['bytes']<=32768 and terminal['original_guard_counter']==8)
check('descriptor registry empty',not registered)
signal.setitimer(signal.ITIMER_REAL,0)
result={'kind':'INDEPENDENT_F01_F02_REMEDY_ADVERSE_MOCK_PROBE','status':'PASS_COMPONENT_SCOPE_ONLY_G03_NOT_RUN','runtime':binding.runtime,'checks':len(checks),'assertions':checks,'generated_event_hashes':[{'class':r['class'],'method':r['method'],'bytes':r['bytes'],'sha256':r['sha256']} for r in plan],'counterexamples':counterexamples,'runtime_ref':binding.executable_ref,'stdlib_ref':binding.stdlib_ref,'late_meter_read_bytes':reads,'OS_writes':0,'actual_tool_imports_bytecode_compiles_calls_installs':0,'generated_code_executed':False,'cost_USD':0}
text=json.dumps(result,sort_keys=True)+'\n';assert len(text.encode())<=262144;sys.stdout.write(text)
