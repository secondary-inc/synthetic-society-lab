"""Guarded generated-fixture candidate. No import-time hooks or tool loading.

Only run_released may load the pinned third-party tool, after an exact reviewed
release. Authored tests use drive_mock and an inert API; wheel payloads/scripts
are never compiled or executed. This is trusted single-owner engineering, not
an OS sandbox. No actual installation/runtime/P3 authority is implied.
"""
import base64
import contextlib
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import stat
import sys
import tempfile
import threading
import time
import zipfile
import zipimport

ROOT = Path(__file__).absolute().parents[1]
CODE = 'scripts/e01_pypa_fixture_harness_candidate_v1_1_20261116.py'
PURE_REF = {'path':'scripts/e01_strict_wheel_source_candidate_v1_20261116.py','bytes':15018,
    'sha256':'ec018402c9d455b723aec33a5ce3beb1404615f6df0c670c1815202413ab0543'}
POLICY_REF = {'path':'scripts/install_e01_pypdf701_runtime_v1_5.py','bytes':64638,
    'sha256':'32162b1ddc0b31637842c3a5ecc0caa36dde6d6f32f2111a94c2336f59c178b4'}
FD_REF = {'path':'scripts/e01_authored_dirfd_guard_v2_20261112.py','bytes':5143,
    'sha256':'431fe340a87bd090f0898c5efef87a5b69f766964eaeb4a53776c3479f3dd000'}
TOOL_REF = {'path':'data/processed/e01_installer_tool_source_v1_20261116/2-RESPONSE.bin','bytes':464466,
    'sha256':'f55f5728ff61d3dd54dbc5a397cf3f7307cb64b180c20b72afbebf01c9e2c8a0'}
SOURCE_AUDIT = {'path':'reports/INDEPENDENT_AUDIT_E01_PYPA_INSTALLER_SOURCE_ACQUISITION_20261116.json',
    'bytes':20875,'sha256':'c6d8086ff740e665b5c8f8181fea040e957c1358873dad4dfa4a0e35ff90f8bd'}
PURE_AUDIT = {'path':'reports/INDEPENDENT_AUDIT_E01_STRICT_WHEEL_SOURCE_PURE_V1_20261116.json',
    'bytes':17325,'sha256':'a91a1a7a4df10fcdacfb4493adb0941745ff93d4c80c8ed4fa207d2e84592fbe'}
BYTES_AUDIT = {'path':'reports/INDEPENDENT_AUDIT_E01_PYPA_INSTALLER_FIXTURE_BYTES_V1_1_20261116.json',
    'bytes':4651,'sha256':'9f92fac01e81b19eece29ecdda52d037326ffeed0e89abfd7164066e05dbb3e0'}
LIMITS = {'wall_seconds':120,'CPU_seconds':120,'read_bytes':67108864,'write_bytes':33554432,
    'console_bytes':262144,'tree_bytes':8388608,'tree_entries':1024,'cases':8,'install_calls':3,
    'terminal_bytes':32768,'control_reserve_bytes':32768}
FILENAME = 'ssl_fixture_payload-1.0.0-py3-none-any.whl'
DIST = 'ssl_fixture_payload-1.0.0.dist-info/'
MARKER = '/SSL_FIXTURE_DO_NOT_EXECUTE/python'
ENTRYPOINT = bytes.fromhex('5b636f6e736f6c655f736372697074735d0a666978747572652d636c69203d2073736c5f666978747572655f7061796c6f61643a6d61696e0a')
INSTALLER = bytes.fromhex('73796e7468657469632d736f63696574792d6c61622d666978747572652d6f6e6c793b20696e7374616c6c65723d312e312e300a')
CASE_IDS = ('VALID','BAD_HASH','ORPHAN_RECORD','UNSAFE_PATH','WRITE_QUOTA',
            'GUARD_EFFECT_SPIES','INTERRUPTED_WRITE','HEADROOM_REPLAY')
PHASES = {'BOOTSTRAP','CONTROL','TOOL_LOAD','VALIDATE','INSTALL','ORACLE','CLOSED'}


class HarnessRefused(RuntimeError):
    def __init__(self,code): self.code=code;super().__init__(code)
class InjectedWriteFailure(RuntimeError): pass
def need(value,code):
    if not value: raise HarnessRefused(code)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def packed(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def canonical(path):
    path=Path(path)
    need(path.is_absolute() and '..' not in path.parts,'FIXTURE_RAW_PATH')
    return path
def no_alias(path):
    need(not any(p.is_symlink() for p in (path,*path.parents)),'FIXTURE_PATH_ALIAS')


def read_pin(root,ref,maximum=1048576,budget=None):
    need(type(ref) is dict and set(ref)=={'path','bytes','sha256'}
         and type(ref['path']) is str and not Path(ref['path']).is_absolute()
         and '..' not in Path(ref['path']).parts and type(ref['bytes']) is int
         and 0<=ref['bytes']<=maximum,'FIXTURE_PIN_SCHEMA')
    path=Path(root)/ref['path'];no_alias(path)
    before=path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and before.st_size==ref['bytes'],'FIXTURE_PIN_SIZE')
    if budget is not None:budget.check();budget.read(ref['bytes']+1)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        opened=os.fstat(stream.fileno());raw=stream.read(ref['bytes']+1)
        after=os.fstat(stream.fileno())
    ident=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns)
    need(ident(before)==ident(opened)==ident(after) and len(raw)==ref['bytes']
         and sha(raw)==ref['sha256'],'FIXTURE_PIN_HASH')
    if budget is not None:budget.check()
    return raw


def own_module(ref,name,budget=None):
    """Own independently reviewed controls only; never tool/payload source."""
    need(ref in (PURE_REF,POLICY_REF,FD_REF),'FIXTURE_OWN_SOURCE_ONLY')
    raw=read_pin(ROOT,ref,budget=budget)
    spec=importlib.util.spec_from_loader(name,loader=None,origin=str(ROOT/ref['path']))
    module=importlib.util.module_from_spec(spec);module.__file__=str(ROOT/ref['path'])
    exec(compile(raw,str(ROOT/ref['path']),'exec'),module.__dict__)
    return module


def fixture_members():
    return {'ssl_fixture_payload/__init__.py':b'raise AssertionError("FIXTURE_PAYLOAD_MUST_NEVER_EXECUTE")\ndef main(): return 0\n',
        DIST+'METADATA':b'Metadata-Version: 2.1\nName: ssl_fixture_payload\nVersion: 1.0.0\nRequires-Python: >=3.10\n\n',
        DIST+'WHEEL':b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
        DIST+'entry_points.txt':ENTRYPOINT}


def make_fixture(case_id):
    need(case_id in CASE_IDS,'FIXTURE_CASE_ID')
    data=fixture_members()
    if case_id=='UNSAFE_PATH':data['../outside.py']=b'NEVER EXECUTE\n'
    rows=[[name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b'=').decode(),str(len(body))]
          for name,body in sorted(data.items())]+[[DIST+'RECORD','','']]
    if case_id=='BAD_HASH':rows[0][1]='sha256='+'A'*43
    if case_id=='ORPHAN_RECORD':rows.append(['orphan.py','sha256='+'A'*43,'1'])
    text=io.StringIO(newline='');csv.writer(text,lineterminator='\n').writerows(rows)
    data[DIST+'RECORD']=text.getvalue().encode();out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,body in sorted(data.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.external_attr=(stat.S_IFREG|0o644)<<16
            archive.writestr(info,body)
    raw=out.getvalue();need(len(raw)<=16384,'FIXTURE_ARCHIVE_CAP')
    return raw


def case_plan():
    return [{'id':name,'archive_sha256':sha(make_fixture(name)),
             'archive_bytes':len(make_fixture(name)),'install':name in {'VALID','WRITE_QUOTA','INTERRUPTED_WRITE'}}
            for name in CASE_IDS]


SCRIPT_BYTES=(b'#!'+MARKER.encode()+b'\n# -*- coding: utf-8 -*-\nimport re\nimport sys\n'
    b'from ssl_fixture_payload import main\nif __name__ == "__main__":\n'
    b'    sys.argv[0] = re.sub(r"(-script\\.pyw|\\.exe)?$", "", sys.argv[0])\n'
    b'    sys.exit(main())\n')


def output_oracle():
    """Frozen expected bytes, not a call to installer script/RECORD code."""
    expected={'site/'+name:body for name,body in fixture_members().items()}
    expected['site/'+DIST+'INSTALLER']=INSTALLER;expected['bin/fixture-cli']=SCRIPT_BYTES
    return expected


class SharedBudget:
    """One sticky operational budget and a bounded final evidence reserve."""
    def __init__(self,pure=None,clock=time.monotonic):
        self.clock=clock;self.started=self.previous=clock()
        self.file_reads=self.writes=self.install_calls=self.refusals=0
        self._failed=False;self.failure=None;self.closing=False
        self.closure_reads=self.closure_writes=0
        self.strict_reads=None;self.strict_refusal_type=None
        if pure is not None:self.attach_strict(pure)
    def attach_strict(self,pure):
        need(self.strict_reads is None and not self._failed and not self.closing,'FIXTURE_STRICT_BUDGET_REENTRY')
        self.strict_reads=pure.ReadBudget(33554432);self.strict_refusal_type=pure.WheelRefused
    @property
    def failed(self):return self._failed or (self.strict_reads is not None and self.strict_reads.failed)
    def trip(self,code):
        if self.failure is None:self.failure=HarnessRefused(code)
        self._failed=True
        if self.strict_reads is not None and not self.strict_reads.failed:
            # Fail the accepted stream budget through its own reservation API;
            # never edit/reset that immutable-source component or its counters.
            try:self.strict_reads._reserve(self.strict_reads.limit-self.strict_reads.used+1)
            except self.strict_refusal_type:pass
        raise self.failure
    def healthy(self):
        if self.failed:self.trip('FIXTURE_STRICT_READ_CAP' if self.failure is None else self.failure.code)
        need(not self.closing,'FIXTURE_OPERATION_AFTER_CLOSURE')
    def check(self,control=False):
        if self.closing and control:return
        self.healthy()
        now=self.clock()
        if now<self.previous:self.trip('FIXTURE_CLOCK_REGRESSION')
        self.previous=now
        if now-self.started>=120:self.trip('FIXTURE_WALL_CAP')
        usage=resource.getrusage(resource.RUSAGE_SELF)
        if usage.ru_utime+usage.ru_stime>=120:self.trip('FIXTURE_CPU_CAP')
    def close_for_evidence(self):
        # Irreversible; ordinary work cannot resume even after healthy closure.
        self.closing=True
    def read(self,n,control=False):
        self.check(control);need(type(n) is int and n>=0,'FIXTURE_READ_AMOUNT')
        if self.closing:
            need(control and self.closure_reads+n<=32768,'FIXTURE_CLOSURE_READ_CAP')
            self.closure_reads+=n
        limit=33554432 if control else 33554432-32768
        if self.file_reads+n>limit:self.trip('FIXTURE_READ_CAP')
        self.file_reads+=n
    def write(self,n,control=False):
        self.check(control);need(type(n) is int and n>=0,'FIXTURE_WRITE_AMOUNT')
        if self.closing:
            need(control and self.closure_writes+n<=32768,'FIXTURE_CLOSURE_WRITE_CAP')
            self.closure_writes+=n
        limit=33554432 if control else 33554432-32768
        if self.writes+n>limit:self.trip('FIXTURE_WRITE_CAP')
        self.writes+=n
    def summary(self):
        strict_used=self.strict_reads.used if self.strict_reads is not None else 0
        return {'file_read_bytes':self.file_reads,'strict_stream_read_bytes':strict_used,
            'combined_read_bytes':self.file_reads+strict_used,'write_bytes':self.writes,
            'install_attempts':self.install_calls,'guard_refusals':self.refusals,'failed':self.failed,
            'failure_code':None if self.failure is None else self.failure.code,
            'closing':self.closing,'closure_read_bytes':self.closure_reads,'closure_write_bytes':self.closure_writes}


# Closed source qualification, not a general permission for dynamic compilation.
RUNTIME_COMPILE_PINS={
    '3.11.17':{'executable':(17344128,'595d73e8b246e5276a3ae0409de4d01dd59fd6ec5f3190cfe28e05bf2de4986f'),
        'dataclasses':(58472,'77a41ea9eb35d959781087b72ef5b452218b57b9d8f2d28688d45a40ca7f8a09')},
    '3.12.14':{'executable':(18058560,'9d1335796350848c36dc2711a3298e096deebee18c85f1ab36edd8747fdf85eb'),
        'dataclasses':(62085,'d242aea5fcf6408b1c1f622442f88f68b9526ce1f8bd2890d74a144677c427d9')}}
# Class schemas are inert data derived from the source-qualified tool; no tool
# source is evaluated to produce the expected strings. Every class uses default
# init/repr/eq, including RecordEntry whose own repr/eq are retained afterward.
DATACLASS_SCHEMAS=(
    ('installer.records','InvalidRecordEntry',22,('elements','issues'),(),(),True),
    ('installer.records','Hash',33,('name','value'),(),(),False),
    ('installer.records','RecordEntry',77,('path','hash_','size'),(),(),False),
    ('installer.scripts','Script',50,('name','module','attr','section'),(),('section',),False),
    ('installer.destinations','SchemeDictionaryDestination',101,
        ('scheme_dict','interpreter','script_kind','hash_algorithm','bytecode_optimization_levels','destdir','overwrite_existing'),
        ('hash_algorithm','bytecode_optimization_levels','destdir','overwrite_existing'),(),False))


def generated_compile_plan(runtime):
    need(runtime in RUNTIME_COMPILE_PINS,'FIXTURE_GENERATED_RUNTIME')
    later=runtime.startswith('3.12.')
    type_name=lambda field:('__dataclass_type_'+field+'__') if later else ('_type_'+field)
    default_name=lambda field:('__dataclass_dflt_'+field+'__') if later else ('_dflt_'+field)
    return_name='__dataclass_return_type__' if later else '_return_type'
    rows=[]
    for module,cls,line,fields,defaults,no_repr,post_init in DATACLASS_SCHEMAS:
        names=[type_name(field) for field in fields]
        names+=['__dataclass_HAS_DEFAULT_FACTORY__','__dataclass_builtins_object__'] if later else ['MISSING','_HAS_DEFAULT_FACTORY','__dataclass_builtins_object__']
        names += [default_name(field) for field in defaults]+[return_name]
        params=['self']+[field+':'+type_name(field)+('='+default_name(field) if field in defaults else '') for field in fields]
        init_body=['self.'+field+'='+field for field in fields]+(['self.__post_init__()'] if post_init else [])
        repr_body=['return self.__class__.__qualname__ + f"('+', '.join(field+'={self.'+field+'!r}' for field in fields if field not in no_repr)+')"']
        self_tuple='('+','.join('self.'+field for field in fields)+',)'
        other_tuple='('+','.join('other.'+field for field in fields)+',)'
        eq_body=['if other.__class__ is self.__class__:', ' return '+self_tuple+'=='+other_tuple,'return NotImplemented']
        for method,args,body,local_names,annotation in (
                ('__init__',params,init_body,names,'->'+return_name),
                ('__repr__',['self'],repr_body,[],''),
                ('__eq__',['self','other'],eq_body,[],'')):
            text='def __create_fn__('+', '.join(local_names)+'):\n def '+method+'('+','.join(args)+')'+annotation+':\n'+'\n'.join('  '+part for part in body)+'\n return '+method
            raw=text.encode('utf-8')
            rows.append({'module':module,'class':cls,'line':line,'method':method,
                'source':raw,'bytes':len(raw),'sha256':sha(raw)})
    need(len(rows)==15,'FIXTURE_GENERATED_PLAN_COUNT')
    return rows


_RUNTIME_BINDING_SEAL=object()
class RuntimeCompileBinding:
    def __init__(self,seal,runtime,stdlib_path,module,codes,executable_ref,stdlib_ref):
        need(seal is _RUNTIME_BINDING_SEAL,'FIXTURE_RUNTIME_BINDING_REQUIRED')
        self.runtime=runtime;self.stdlib_path=stdlib_path;self.module=module;self.codes=codes
        self.executable_ref=executable_ref;self.stdlib_ref=stdlib_ref


def bind_runtime_compile(budget):
    """Hash exact runtime/stdlib files and retain only technical code identities.

    Loaded bytecode/startup closure remains a separate actual-release gate.
    No third-party tool/payload is imported or compiled here.
    """
    runtime=sys.version.split()[0]
    need(sys.implementation.name=='cpython' and runtime in RUNTIME_COMPILE_PINS,'FIXTURE_GENERATED_RUNTIME')
    executable=Path(sys.executable).resolve()
    stdlib=Path(sys.base_prefix)/'lib'/('python%d.%d'%sys.version_info[:2])/'dataclasses.py'
    refs={}
    for kind,path in [('executable',executable),('dataclasses',stdlib)]:
        size,digest=RUNTIME_COMPILE_PINS[runtime][kind]
        read_pin(path.parent,{'path':path.name,'bytes':size,'sha256':digest},maximum=20971520,budget=budget)
        refs[kind]={'path':str(path),'bytes':size,'sha256':digest}
    import dataclasses
    need(Path(dataclasses.__file__)==stdlib and dataclasses.__spec__.origin==str(stdlib)
         and sys.modules.get('dataclasses') is dataclasses,'FIXTURE_DATACLASSES_ORIGIN')
    codes={name:getattr(dataclasses,name).__code__ for name in
        ('_create_fn','_init_fn','_repr_fn','_cmp_fn','_process_class','dataclass')}
    wrap=[code for code in codes['dataclass'].co_consts if hasattr(code,'co_name') and code.co_name=='wrap']
    need(len(wrap)==1 and all(code.co_filename==str(stdlib) for code in codes.values()),'FIXTURE_DATACLASSES_CODE_ORIGIN')
    codes['wrap']=wrap[0]
    return RuntimeCompileBinding(_RUNTIME_BINDING_SEAL,runtime,stdlib,dataclasses,codes,refs['executable'],refs['dataclasses'])


class GeneratedCompileGate:
    """Exactly15 generated dataclass strings in one TOOL_LOAD, never arbitrary exec.

    accept captures the real audit caller. _admit/_origin_matches also support
    inert frame doubles in authored tests; those private methods grant no tool
    execution/release and are not a hostile-private-state security boundary.
    """
    def __init__(self,binding):
        need(type(binding) is RuntimeCompileBinding,'FIXTURE_RUNTIME_BINDING_REQUIRED')
        self.binding=binding;self.plan=generated_compile_plan(binding.runtime);self.index=0;self.failed=False
    def _origin_matches(self,frame,snapshot,row):
        helper={'__init__':'_init_fn','__repr__':'_repr_fn','__eq__':'_cmp_fn'}[row['method']]
        chain=('_create_fn',helper,'_process_class','wrap','dataclass')
        for name in chain:
            if frame is None or frame.f_code is not self.binding.codes[name] or frame.f_globals is not self.binding.module.__dict__:
                return False
            if frame.f_code.co_filename!=str(self.binding.stdlib_path):return False
            frame=frame.f_back
        filename=str(snapshot)+'/'+row['module'].replace('.','/')+'.py'
        if frame is None:return False
        spec=frame.f_globals.get('__spec__')
        return (frame.f_code.co_name=='<module>' and frame.f_code.co_filename==filename
            and frame.f_globals.get('__name__')==row['module'] and frame.f_globals.get('__file__')==filename
            and getattr(spec,'origin',None)==filename and frame.f_lineno==row['line'])
    def _admit(self,source,filename,phase,snapshot,frame):
        try:
            need(not self.failed and self.index<len(self.plan),'FIXTURE_GENERATED_COUNT')
            row=self.plan[self.index]
            raw=source.encode('utf-8') if type(source) is str else source
            need(phase=='TOOL_LOAD' and filename=='<string>','FIXTURE_GENERATED_PHASE_OR_FILENAME')
            need(type(raw) is bytes and raw==row['source'],'FIXTURE_GENERATED_SOURCE')
            need(self._origin_matches(frame,snapshot,row),'FIXTURE_GENERATED_ORIGIN')
            self.index+=1
        except HarnessRefused:self.failed=True;raise
    def accept(self,source,filename,phase,snapshot):
        # accept -> FixturePolicy.audit -> pinned dataclasses._create_fn.
        frame=sys._getframe(2)
        try:return self._admit(source,filename,phase,snapshot,frame)
        finally:del frame
    def finish(self):
        if self.failed or self.index!=15:
            self.failed=True;raise HarnessRefused('FIXTURE_GENERATED_INCOMPLETE')
    def summary(self):
        return {'expected_generated_events':15,'accepted_generated_events':self.index,'failed':self.failed,
            'runtime_ref':self.binding.executable_ref,'stdlib_ref':self.binding.stdlib_ref}


def policy_class(base):
    class FixturePolicy(base):
        def __init__(self,root,budget):
            binding={'base_prefix':sys.base_prefix,'pip_root':'NO_PIP','pip_files':{},
                     'pip_metadata_ref':{'path':'NO_PIP_METADATA'}}
            super().__init__(Path(root),binding,{'wheels':[],'remaining_output_bytes':262144})
            self.stage=Path(root)/'controls';self.target=Path(root)/'prefixes'
            self.base_lib=Path(sys.base_prefix)/'lib'/('python%d.%d'%sys.version_info[:2])
            self.exact_reads={Path('/dev/null')}
            self.shared=budget;self.phase='CONTROL';self.current=None;self.case_states=[];self.sealed=set();self.generated_compile=None;self.tool_compiled=set();self.compile_failed=False
        def refuse(self,code):
            self.shared.refusals+=1
            super().refuse(code)
        def phase_set(self,phase):
            need(phase in PHASES,'FIXTURE_PHASE');self.phase=phase
        def begin(self,name):
            need(name in CASE_IDS and all(s['id']!=name for s in self.case_states),'FIXTURE_SPENT_CASE')
            state={'id':name,'prefix':str(self.target/name),'destination_bytes':0,'write_attempts':0,
                   'quota_failed':False,'injected':InjectedWriteFailure('FIXTURE_INJECTED_WRITE')}
            self.case_states.append(state);self.current=state
        def path(self,value,flags):
            self.shared.check(control=self.phase=='CONTROL')
            super().path(value,flags)
            path=canonical(value);writing=flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
            if writing:
                if path in self.sealed:self.refuse('GUEST_SEALED_SOURCE_WRITE')
                if self.phase=='INSTALL':
                    if self.current is None or not path.is_relative_to(Path(self.current['prefix'])):
                        self.refuse('GUEST_WRITE_OUTSIDE_OWNED')
                elif self.phase!='CONTROL' or not path.is_relative_to(self.stage):
                    self.refuse('GUEST_WRITE_OUTSIDE_OWNED')
        def charge(self,body,output=False):
            n=len(body.encode()) if type(body) is str else len(body)
            if output:
                super().charge(body,True);need(self.output<=262144,'FIXTURE_OUTPUT_CAP');return
            if self.phase=='INSTALL':
                state=self.current;need(state is not None,'FIXTURE_NO_ACTIVE_CASE')
                state['write_attempts']+=1
                if state['id']=='WRITE_QUOTA' and (state['quota_failed'] or state['destination_bytes']+n>64):
                    state['quota_failed']=True;self.refuse('GUEST_WRITE_CAP')
                if state['id']=='INTERRUPTED_WRITE' and state['write_attempts']>=2:raise state['injected']
                state['destination_bytes']+=n
            self.shared.write(n,control=self.phase=='CONTROL')
            super().charge(body,False)
        def audit(self,event,args):
            if event=='os.symlink':self.refuse('GUEST_FIXTURE_SYMLINK_DENIED')
            if event=='compile':
                try:
                    need(not self.compile_failed and len(args)==2,'FIXTURE_COMPILE_EVENT')
                    source,filename=args
                    need(self.phase=='TOOL_LOAD','FIXTURE_COMPILE_PHASE')
                    if filename=='<string>':
                        need(self.generated_compile is not None,'FIXTURE_GENERATED_GATE_REQUIRED')
                        self.generated_compile.accept(source,filename,self.phase,self.stage/'installer-1.1.0-py3-none-any.whl')
                    else:
                        prefix=str(self.stage/'installer-1.1.0-py3-none-any.whl')+'/'
                        need(type(filename) is str and filename.startswith(prefix),'FIXTURE_COMPILE_ORIGIN')
                        member=filename[len(prefix):]
                        need(member in TOOL_PY and member!='installer/__main__.py' and member not in self.tool_compiled,'FIXTURE_COMPILE_MEMBER')
                        raw=source.encode('utf-8') if type(source) is str else source
                        need(type(raw) is bytes and (len(raw),sha(raw))==TOOL_PY[member],'FIXTURE_COMPILE_SOURCE')
                        self.tool_compiled.add(member)
                except HarnessRefused:
                    self.compile_failed=True;self.refuse('GUEST_FIXTURE_COMPILE_DENIED')
            before=self.reads
            try:return super().audit(event,args)
            finally:
                delta=self.reads-before
                if delta:self.shared.read(delta,control=self.phase=='CONTROL')
    return FixturePolicy


class MemoryFS:
    """Inert authored effects only; does not touch an OS prefix or target."""
    is_mock=True
    def __init__(self,root='/SSL_AUTHORED_FIXTURES'):
        self.root=canonical(root);self.files={};self.policy=None
    def bind(self,policy):self.policy=policy
    def _path(self,path):
        path=canonical(path);need(path.is_relative_to(self.root),'FIXTURE_FS_ROOT');return str(path)
    def prepare_prefix(self,prefix):self._path(prefix)
    def exists(self,path):return self._path(path) in self.files
    def write_new(self,path,raw):
        name=self._path(path);need(type(raw) is bytes,'FIXTURE_WRITE_BYTES')
        need(name not in self.files,'FIXTURE_SPENT_SCOPE')
        self.policy.path(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
        self.files[name]=b''
        self.policy.charge(raw);self.files[name]=raw;self.bounds()
    def read(self,path):
        name=self._path(path);self.policy.path(name,os.O_RDONLY)
        raw=self.files[name];self.policy.shared.read(len(raw)+1,control=self.policy.phase=='CONTROL');return raw
    def list(self,prefix):
        prefix=str(canonical(prefix))+'/'
        return {name[len(prefix):]:self.read(name) for name in self.files if name.startswith(prefix)}
    def bounds(self):
        need(len(self.files)<=1024 and sum(map(len,self.files.values()))<=8388608,'FIXTURE_TREE_CAP')


def verify_output(fs,prefix):
    files=fs.list(prefix);expected=output_oracle()
    record_path='site/'+DIST+'RECORD'
    need(set(files)==set(expected)|{record_path},'FIXTURE_OUTPUT_MEMBERSHIP')
    need(all(files[name]==raw for name,raw in expected.items()),'FIXTURE_OUTPUT_BYTES')
    rows=list(csv.reader(io.StringIO(files[record_path].decode(),newline='')))
    need(len(rows)==7 and all(len(row)==3 for row in rows),'FIXTURE_INSTALLED_RECORD_SCHEMA')
    actual={}
    for path,hash_text,size_text in rows:
        # Never open the raw ../bin RECORD name: map only to the frozen oracle.
        relative='bin/fixture-cli' if path=='../bin/fixture-cli' else 'site/'+path
        need(relative in files and relative not in actual,'FIXTURE_INSTALLED_RECORD_MEMBERSHIP')
        if relative==record_path:need(hash_text==size_text=='','FIXTURE_INSTALLED_RECORD_SELF')
        else:
            raw=files[relative];expected_hash='sha256='+base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode()
            need(hash_text==expected_hash and size_text==str(len(raw)),'FIXTURE_INSTALLED_RECORD_HASH')
        actual[relative]=True
    need(set(actual)==set(files),'FIXTURE_INSTALLED_RECORD_COVERAGE')
    return {name:{'bytes':len(raw),'sha256':sha(raw)} for name,raw in sorted(files.items())}


def receipt(fs,name,obj):
    raw=packed(obj);need(len(raw)<=32768,'FIXTURE_RECEIPT_CAP')
    fs.write_new(fs.root/'controls'/name,raw)
    return {'path':name,'bytes':len(raw),'sha256':sha(raw)}


def headroom():
    model={'kind':'FIXTURE_TERMINAL_V1','cases':[{'id':name,'summary':'x'*512,
        'ref':{'path':'x'*128,'bytes':8388608,'sha256':'f'*64}} for name in CASE_IDS],
        'source_ref':TOOL_REF,'limits':LIMITS,'failure_reserve':'x'*4096}
    need(len(packed(model))<=28672,'FIXTURE_TERMINAL_HEADROOM')
    return len(packed(model))


def _closed_error(error,pure,base):
    if type(error) is HarnessRefused:return error.code
    if type(error) is pure.WheelRefused:return error.code
    if type(error) is base.Refused:return 'ORIGINAL_GUARD_REFUSED'
    if type(error) is InjectedWriteFailure:return 'INJECTED_WRITE_FAILURE'
    return 'UNKNOWN_ERROR_TYPE'


def _drive(fs,api,pure,base,fd_module,*,clock=time.monotonic,mode='MOCK',budget=None,policy=None):
    need(mode in {'MOCK','RELEASED_FIXTURE'},'FIXTURE_MODE')
    budget=SharedBudget(pure,clock) if budget is None else budget
    policy=policy_class(base.GuestPolicy)(fs.root,budget) if policy is None else policy
    fs.bind(policy)
    need(not fs.exists(fs.root/'controls'/'STARTED.json'),'FIXTURE_SPENT_SCOPE')
    headroom();receipt(fs,'STARTED.json',{'kind':'FIXTURE_STARTED_V1','mode':mode,'plan_sha256':sha(packed(case_plan())),'no_retry':True})
    results=[];outcome='FAILED_FIXTURE_HARNESS';reason=None;primary=None;closure_error=None;failure_ref=None
    try:
        for index,name in enumerate(CASE_IDS):
            budget.check();policy.phase_set('CONTROL');policy.begin(name)
            before=policy.violations;case={'id':name,'mode':mode,'installation_accepted':False}
            raw=make_fixture(name);case['input_sha256']=sha(raw)
            receipt(fs,name+'-INPUT.json',{'id':name,'sha256':sha(raw),'bytes':len(raw)})
            policy.phase_set('VALIDATE')
            if name=='GUARD_EFFECT_SPIES':
                for event in ('socket.__new__','socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','ctypes.dlopen'):
                    try:policy.audit(event,())
                    except base.Refused:pass
                    else:raise HarnessRefused('FIXTURE_MISSING_GUARD_DENIAL')
                policy.phase_set('INSTALL')
                try:policy.path(str(fs.root/'outside'),os.O_WRONLY)
                except base.Refused:pass
                else:raise HarnessRefused('FIXTURE_MISSING_PATH_DENIAL')
                effects=[]
                guard=fd_module.DirectoryFdGuard(lambda *_:None,raw_open=lambda *a,**k:effects.append(True))
                class MockStat:
                    st_dev=1;st_ino=1;st_mode=stat.S_IFDIR|0o700
                guard.fstat=lambda unused:MockStat()
                try:guard.open('relative',os.O_RDONLY,dir_fd=987654)
                except fd_module.GuardRefused:pass
                else:raise HarnessRefused('FIXTURE_MISSING_DESCRIPTOR_DENIAL')
                class MockOrigin:
                    parents=()
                    def is_symlink(self):return False
                    def stat(self,**kwargs):return MockStat()
                guard.records[41]=(MockOrigin(),(1,1,MockStat.st_mode),1)
                class ReusedStat(MockStat):st_ino=2
                guard.fstat=lambda unused:ReusedStat()
                try:guard.open('relative',os.O_RDONLY,dir_fd=41)
                except fd_module.GuardRefused:pass
                else:raise HarnessRefused('FIXTURE_MISSING_REUSED_DESCRIPTOR_DENIAL')
                class MockAlias:
                    parents=()
                    def is_symlink(self):return True
                guard.absolute=lambda unused:MockAlias()
                try:guard.open('/SSL_MOCK_ALIAS',os.O_WRONLY)
                except fd_module.GuardRefused:pass
                else:raise HarnessRefused('FIXTURE_MISSING_ALIAS_DENIAL')
                need(effects==[] and policy.violations-before==7,'FIXTURE_GUARD_EFFECT')
                case.update(verdict='EXPECTED_GUARD_REFUSALS',guard_counter_delta=7,
                    descriptor_refused=True,reused_descriptor_refused=True,alias_refused=True)
            elif name=='HEADROOM_REPLAY':
                need(headroom()<=28672,'FIXTURE_TERMINAL_HEADROOM');case.update(verdict='HEADROOM_MODEL_PASS',serialized_model_bytes=headroom())
            else:
                try:token=pure.validate_wheel(raw,expected_sha256=sha(raw),filename=FILENAME,budget=budget.strict_reads)
                except pure.WheelRefused as error:
                    expected={'BAD_HASH':'RECORD_HASH','ORPHAN_RECORD':'RECORD_EXTRA_NAME','UNSAFE_PATH':'ZIP_PATH'}
                    need(name in expected and error.code==expected[name],'FIXTURE_UNEXPECTED_VALIDATION_REFUSAL')
                    case.update(verdict='EXPECTED_VALIDATION_REFUSAL',error_code=error.code)
                else:
                    need(name in {'VALID','WRITE_QUOTA','INTERRUPTED_WRITE'},'FIXTURE_BAD_INPUT_ADMITTED')
                    need(token.sha256==sha(raw) and token.filename==FILENAME,'FIXTURE_SOURCE_BINDING')
                    policy.phase_set('INSTALL');fs.prepare_prefix(policy.current['prefix'])
                    with api.source_context(token) as source:
                        destination=api.destination(fs,policy.current['prefix'],MARKER)
                        budget.install_calls+=1;need(budget.install_calls<=3,'FIXTURE_INSTALL_CALL_CAP')
                        policy.phase_set('INSTALL')
                        try:api.install(source,destination,{'INSTALLER':INSTALLER})
                        except BaseException as error:
                            if budget.failed:
                                if budget.failure is not None:raise budget.failure from None
                                raise
                            if name=='WRITE_QUOTA':need(type(error) is base.Refused and policy.current['quota_failed'],'FIXTURE_QUOTA_PRIMARY')
                            elif name=='INTERRUPTED_WRITE':need(error is policy.current['injected'],'FIXTURE_INTERRUPTED_PRIMARY')
                            else:raise
                            case.update(verdict='EXPECTED_INSTALL_REFUSAL',error_code=_closed_error(error,pure,base),
                                primary_identity_preserved=name!='INTERRUPTED_WRITE' or error is policy.current['injected'])
                        else:
                            budget.healthy()
                            need(name=='VALID' and policy.violations==before,'FIXTURE_NEGATIVE_INSTALL_ADMITTED')
                            policy.phase_set('ORACLE');case['output_manifest']=verify_output(fs,policy.current['prefix'])
                            case.update(verdict='VALID_GENERATED_OUTPUT',fixture_only=True)
                    need(token.sha256==sha(raw),'FIXTURE_SOURCE_DRIFT')
            budget.healthy();policy.phase_set('CONTROL')
            case.update(guard_counter_before=before,guard_counter_after=policy.violations,
                destination_bytes=policy.current['destination_bytes'],write_attempts=policy.current['write_attempts'])
            if name in {'WRITE_QUOTA','INTERRUPTED_WRITE'}:
                case['partial_manifest']={n:{'bytes':len(b),'sha256':sha(b)} for n,b in fs.list(policy.current['prefix']).items()}
            ref=receipt(fs,name+'-RESULT.json',case)
            results.append({'id':name,'verdict':case['verdict'],'ref':ref})
        budget.healthy();need(budget.install_calls==3,'FIXTURE_INSTALL_CALL_COUNT');outcome='FIXTURE_ASSERTIONS_PASS_ONLY'
    except BaseException as error:reason=_closed_error(error,pure,base);primary=error
    finally:
        budget.close_for_evidence();policy.phase_set('CONTROL')
        if budget.failed:outcome='FAILED_FIXTURE_HARNESS'
        try:
            for row in results:
                raw=fs.read(fs.root/'controls'/row['ref']['path'])
                need(len(raw)==row['ref']['bytes'] and sha(raw)==row['ref']['sha256'],'FIXTURE_EVIDENCE_DRIFT')
        except BaseException as error:
            closure_error=_closed_error(error,pure,base);outcome='FAILED_FIXTURE_HARNESS'
            if primary is None:primary=error
        if primary is not None and policy.current is not None:
            try:
                partial={n:{'bytes':len(b),'sha256':sha(b)} for n,b in fs.list(policy.current['prefix']).items()}
                failure_ref=receipt(fs,'FAILED_CASE.json',{'id':policy.current['id'],'error_code':_closed_error(primary,pure,base),
                    'partial_manifest':partial,'original_guard_counter':policy.violations,'installation_accepted':False})
            except BaseException:
                closure_error='FAILURE_EVIDENCE_UNAVAILABLE'
        terminal={'kind':'FIXTURE_TERMINAL_V1','mode':mode,'outcome':outcome,'reason':reason,
            'cases':results,'usage':budget.summary(),'original_guard_counter':policy.violations,'closure_error':closure_error,'failure_ref':failure_ref,
            'limits':LIMITS,'no_retry':True,'installation_accepted':False,'runtime_or_P3_accepted':False,
            'actual_installer_imports':0 if mode=='MOCK' else 1,'cost_USD':0}
        try:ref=receipt(fs,'TERMINAL.json',terminal)
        except BaseException:
            if primary is not None:raise primary
            raise
    if primary is not None:raise primary
    return {'terminal':terminal,'terminal_ref':ref,'fs':fs}


def drive_mock(api,fs=None,clock=time.monotonic):
    """Authored API test double only; not a route to production tool loading."""
    need(getattr(api,'mock_only',False) is True,'FIXTURE_MOCK_API_REQUIRED')
    fs=MemoryFS() if fs is None else fs;need(type(fs) is MemoryFS,'FIXTURE_MEMORY_FS_REQUIRED')
    pure=own_module(PURE_REF,'fixture_pure_source');base=own_module(POLICY_REF,'fixture_original_policy')
    fd=own_module(FD_REF,'fixture_original_directory_guard')
    return _drive(fs,api,pure,base,fd,clock=clock,mode='MOCK')


class DiskFS:
    """Future released fixture scope only; not used by authored mock tests."""
    is_mock=False
    def __init__(self,root):self.root=canonical(root);self.policy=None;self.hooks_active=False
    def bind(self,policy):self.policy=policy
    def _path(self,path):
        path=canonical(path);need(path.is_relative_to(self.root),'FIXTURE_FS_ROOT');no_alias(path);return path
    def prepare_prefix(self,prefix):
        need(self.hooks_active,'FIXTURE_GUARDS_REQUIRED');self._path(prefix).mkdir(mode=0o700,exist_ok=False)
        self.bounds()
    def exists(self,path):return self._path(path).exists()
    def write_new(self,path,raw):
        need(self.hooks_active,'FIXTURE_GUARDS_REQUIRED');path=self._path(path)
        need(type(raw) is bytes,'FIXTURE_WRITE_BYTES')
        path.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            need(stream.write(raw)==len(raw),'FIXTURE_SHORT_WRITE');stream.flush();os.fsync(stream.fileno())
        parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(parent)
        finally:os.close(parent)
        self.bounds()
    def read(self,path):
        path=self._path(path);need(path.stat().st_size<=1048576,'FIXTURE_READ_FILE_CAP')
        with path.open('rb') as stream:return stream.read(1048577)
    def list(self,prefix):
        prefix=self._path(prefix)
        if not prefix.exists():return {}
        result={}
        for parent,dirs,names in os.walk(prefix,followlinks=False):
            for name in dirs:no_alias(Path(parent)/name)
            for name in names:
                path=self._path(Path(parent)/name);need(path.is_file(),'FIXTURE_SPECIAL_FILE')
                result[str(path.relative_to(prefix))]=self.read(path)
        return result
    def bounds(self):
        count=total=0
        for parent,dirs,names in os.walk(self.root,followlinks=False):
            for name in dirs+names:
                path=self._path(Path(parent)/name);info=path.lstat();count+=1
                need(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode),'FIXTURE_SPECIAL_FILE')
                if stat.S_ISREG(info.st_mode):total+=info.st_size
                need(count<=1024 and total<=8388608,'FIXTURE_TREE_CAP')
        return total,count


def install_hooks(policy,fs,base,fd_module):
    """One fresh released process. Original guard with narrower case routing.

    Audit hooks cannot be removed. No import-time or mock path calls this.
    High-level io/Path opens get explicit pre-effect alias checks in addition
    to the reviewed directory-descriptor guard; no new read/write exemption.
    """
    import builtins
    guard=fd_module.DirectoryFdGuard(policy.path);policy.fdguard=guard
    sys.addaudithook(policy.audit)
    original_open,original_close=os.open,os.close
    guard.raw_open,guard.raw_close=original_open,original_close
    known={}
    def identity(info):return info.st_dev,info.st_ino,info.st_mode
    def open_fd(*args,**kwargs):
        value=args[0];raw_path=os.fsdecode(os.fspath(value))
        if not os.path.isabs(raw_path) and kwargs.get('dir_fd') is not None:
            path=guard.absolute(guard.directory(kwargs['dir_fd'])[0]/raw_path)
        else:path=guard.absolute(raw_path)
        opened=guard.open(*args,**kwargs)
        known[opened]=(path,identity(os.fstat(opened)));return opened
    def close_fd(fd):known.pop(fd,None);return guard.close(fd)
    os.open,os.close=open_fd,close_fd
    raw_io_open,raw_builtin_open,raw_fdopen=io.open,builtins.open,os.fdopen
    def wrapping(original):
        def opening(file,*args,**kwargs):
            if type(file) is not int:
                path=guard.absolute(file);guard.no_alias(path)
            else:
                need(file in known and identity(os.fstat(file))==known[file][1],'FIXTURE_UNKNOWN_FILE_DESCRIPTOR')
                path=known[file][0];guard.no_alias(path)
            stream=original(file,*args,**kwargs)
            class ScopedFile(base.ChargedFile):
                def write(self,body):
                    policy.path(path,os.O_WRONLY);guard.no_alias(path)
                    return super().write(body)
            return ScopedFile(stream,policy)
        return opening
    io.open,builtins.open,os.fdopen=wrapping(raw_io_open),wrapping(raw_builtin_open),wrapping(raw_fdopen)
    raw_write=os.write
    def write(fd,body):
        if fd not in {1,2}:
            need(fd in known and identity(os.fstat(fd))==known[fd][1],'FIXTURE_UNKNOWN_FILE_DESCRIPTOR')
            policy.path(known[fd][0],os.O_WRONLY);guard.no_alias(known[fd][0])
        policy.charge(body,output=fd in {1,2});return raw_write(fd,body)
    os.write=write
    sys.stdout,sys.stderr=base.ChargedFile(sys.stdout,policy,True),base.ChargedFile(sys.stderr,policy,True)
    class NoTargets:
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in base.BLOCKED_IMPORTS|{'ssl_fixture_payload'}:
                policy.refuse('DOWNLOADED_PACKAGE_IMPORT_DENIED')
    sys.meta_path.insert(0,NoTargets())
    fs.hooks_active=True


TOOL_PY = {
    'installer/__init__.py':(128,'da5afac97745f229a8dcc480f15bf3b6f026b56614580ba0cb42967eff68a1a1'),
    'installer/__main__.py':(3674,'30821a084a972e1734184986a1059b7f50aa3776f228666ceb0a8f88442d1b93'),
    'installer/_core.py':(5234,'9da28e04fbd21cea234f16aec6ea75d24ac063a1a483ccf3abb4d651715011cb'),
    'installer/_scripts/__init__.py':(81,'222fa4998cbf4d2db71c35dfdd0530de947234ca4c66ca75c322f5d38875625f'),
    'installer/destinations.py':(10666,'92853c201d052086220fef5784a2fb6c01dc5812b7f8f9f98590f1b87e5bb1fb'),
    'installer/exceptions.py':(248,'630c75d5da3447e70500b8a6731a6d93fae183b4756c36f8b010ae11b94d94be'),
    'installer/records.py':(7368,'bd26c18b12f2ec3ce8ff534c070f3878a8cf7f25134871ae8cdb93a52835f9cf'),
    'installer/scripts.py':(5538,'971da58eecdee1c64daf9018071f947f37b6c1d01cedd1828b24eb7f488e71f7'),
    'installer/sources.py':(12121,'eef90f50aef04c6faa994a2de04e4e20cb61a659144317e10ba78486b5a694e8'),
    'installer/utils.py':(8114,'c68c38a65e14f6a717845bbc6cf8f1a1307db2b4c5361550a5448ba53f2b92e7')}
_RELEASE_SEAL=object()


def inspect_tool_bytes(raw,*,expected_archive=TOOL_REF,expected_sources=TOOL_PY):
    """Read/hash source only. The mock helper may pass authored expectations.

    Actual activation below always uses the fixed production constants.
    """
    need(type(raw) is bytes and len(raw)==expected_archive['bytes'] and sha(raw)==expected_archive['sha256'],
         'FIXTURE_TOOL_ARCHIVE_HASH')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        need(len(archive.infolist())<=1024,'FIXTURE_TOOL_ENTRY_CAP')
        names={item.filename for item in archive.infolist() if item.filename.endswith('.py')}
        need(names==set(expected_sources),'FIXTURE_TOOL_SOURCE_SET')
        for name,(size,digest) in expected_sources.items():
            info=archive.getinfo(name);need(info.file_size==size and size<=1048576,'FIXTURE_TOOL_MEMBER_SIZE')
            source=archive.read(name);need(len(source)==size and sha(source)==digest,'FIXTURE_TOOL_MEMBER_HASH')
    return tuple(sorted(expected_sources))


class QualifiedAPI:
    def __init__(self,module,sources,destinations):
        self.module,self.sources,self.destinations=module,sources,destinations
    @contextlib.contextmanager
    def source_context(self,token):
        with token.open() as stream:
            with zipfile.ZipFile(stream,mode='r') as archive:
                source=self.sources.WheelFile(archive)
                need(archive.filename==token.filename and source.distribution=='ssl_fixture_payload'
                     and source.version=='1.0.0','FIXTURE_TOOL_SOURCE_IDENTITY')
                yield source
    def destination(self,fs,prefix,marker):
        prefix=canonical(prefix)
        result=self.destinations.SchemeDictionaryDestination(
            scheme_dict={'purelib':str(prefix/'site'),'platlib':str(prefix/'site'),
                'scripts':str(prefix/'bin'),'headers':str(prefix/'headers'),'data':str(prefix/'data')},
            interpreter=marker,script_kind='posix',hash_algorithm='sha256',
            bytecode_optimization_levels=(),destdir=None,overwrite_existing=False)
        need(result.interpreter==MARKER and result.script_kind=='posix'
             and result.bytecode_optimization_levels==() and result.overwrite_existing is False
             and result.destdir is None,'FIXTURE_DESTINATION_SETTINGS')
        return result
    def install(self,source,destination,additional_metadata):
        # No validate_record(False), null-device sink, package patch or CLI.
        return self.module.install(source=source,destination=destination,additional_metadata=additional_metadata)


def activate_tool(seal,snapshot,raw,policy,fs):
    need(seal is _RELEASE_SEAL and type(fs) is DiskFS and fs.hooks_active,'FIXTURE_TOOL_RELEASE_REQUIRED')
    need(not any(name=='installer' or name.startswith('installer.') for name in sys.modules),'FIXTURE_TOOL_PRELOADED')
    inspect_tool_bytes(raw)
    policy.phase_set('TOOL_LOAD')
    need(fs.read(snapshot)==raw,'FIXTURE_TOOL_SNAPSHOT_HASH')
    loader=zipimport.zipimporter(str(snapshot));spec=loader.find_spec('installer')
    need(spec is not None and type(spec.loader) is zipimport.zipimporter,'FIXTURE_STANDARD_ZIP_LOADER')
    module=importlib.util.module_from_spec(spec);sys.modules['installer']=module
    spec.loader.exec_module(module)
    need(module.__version__=='1.1.0','FIXTURE_TOOL_VERSION')
    for name,value in list(sys.modules.items()):
        if name=='installer' or name.startswith('installer.'):
            need(name!='installer.__main__','FIXTURE_TOOL_CLI_IMPORT')
            path=getattr(value,'__file__',None)
            need(type(path) is str and path.startswith(str(snapshot)+'/'),'FIXTURE_TOOL_ORIGIN')
            member=path[len(str(snapshot))+1:]
            need(member in TOOL_PY,'FIXTURE_TOOL_MODULE_SET')
    need(fs.read(snapshot)==raw,'FIXTURE_TOOL_POSTLOAD_HASH')
    need(not policy.compile_failed,'FIXTURE_COMPILE_FAILED')
    policy.generated_compile.finish()
    policy.phase_set('CONTROL')
    return QualifiedAPI(module,sys.modules['installer.sources'],sys.modules['installer.destinations'])


def validate_release(packet,root,candidate_raw,review):
    """Pure exact binding. Real entry reads all evidence through pinned paths."""
    required={'kind','execution_enabled','root_sha256','runtime','candidate_ref','plan_sha256',
              'limits','source_audit_ref','pure_audit_ref','bytes_audit_ref','review_ref','temp_parent'}
    need(type(packet) is dict and set(packet)==required and packet['kind']=='E01_PYPA_FIXTURE_RELEASE_V1_1'
         and packet['execution_enabled'] is True and packet['root_sha256']==sha(str(root).encode())
         and packet['plan_sha256']==sha(packed(case_plan())) and packet['limits']==LIMITS
         and packet['source_audit_ref']==SOURCE_AUDIT and packet['pure_audit_ref']==PURE_AUDIT
         and packet['bytes_audit_ref']==BYTES_AUDIT,'FIXTURE_EXACT_RELEASE_REQUIRED')
    ref=packet['candidate_ref']
    need(type(ref) is dict and ref.get('path')==CODE and ref.get('bytes')==len(candidate_raw)
         and ref.get('sha256')==sha(candidate_raw),'FIXTURE_RELEASE_CODE')
    core={key:value for key,value in packet.items() if key!='review_ref'}
    decision=review.get('decision',review.get('status')) if type(review) is dict else None
    need(type(decision) is str and decision.startswith('PASS_')
         and review.get('reviewed_release_core_sha256')==sha(packed(core))
         and review.get('evidence_refs',{}).get(CODE)==ref,'FIXTURE_EXACT_CONCRETE_REVIEW')
    need(type(packet['runtime']) is str and packet['runtime'] in {'3.11.17','3.12.14'},'FIXTURE_RELEASE_RUNTIME')
    parent=canonical(packet['temp_parent']);need(not parent.is_relative_to(root) and not Path(root).is_relative_to(parent),
        'FIXTURE_RELEASE_TEMP_PARENT')
    return packet


def run_released(packet_ref):
    """No invocation is authorized now. Future exact packet required first.

    A fixed scope derived from root/runtime under reviewed temp_parent is
    consumed once. No random alternate prefix, child, actual runtime or P3.
    """
    need(Path.cwd().absolute()==ROOT and sys.flags.isolated and sys.flags.no_site
         and sys.dont_write_bytecode and os.name=='posix','FIXTURE_ISOLATED_PROCESS_REQUIRED')
    need(threading.current_thread() is threading.main_thread() and threading.active_count()==1,
         'FIXTURE_SINGLE_OWNER')
    budget=SharedBudget()
    need(type(packet_ref) is dict and packet_ref.get('path','').startswith(
        'data/processed/e01_pypa_fixture_release_v1_1_20261116/'),'FIXTURE_RELEASE_PACKET_PATH')
    packet=json.loads(read_pin(ROOT,packet_ref,65536,budget))
    review_ref=packet.get('review_ref') if type(packet) is dict else None
    need(type(review_ref) is dict and review_ref.get('path','').startswith('reports/INDEPENDENT_AUDIT_'),
         'FIXTURE_REVIEW_PATH')
    review=json.loads(read_pin(ROOT,review_ref,1048576,budget))
    need(type(packet.get('candidate_ref')) is dict and packet['candidate_ref'].get('path')==CODE,'FIXTURE_RELEASE_CODE')
    candidate_raw=read_pin(ROOT,packet['candidate_ref'],budget=budget)
    validate_release(packet,ROOT,candidate_raw,review)
    need(packet['runtime']==sys.version.split()[0],'FIXTURE_RUNNING_RUNTIME')
    for ref in (SOURCE_AUDIT,PURE_AUDIT,BYTES_AUDIT):
        value=json.loads(read_pin(ROOT,ref,budget=budget));decision=value.get('decision',value.get('status'))
        need(type(decision) is str and decision.startswith('PASS_'),'FIXTURE_PREREQUISITE_REVIEW')
    pure=own_module(PURE_REF,'released_fixture_pure_source',budget)
    budget.attach_strict(pure)
    base=own_module(POLICY_REF,'released_fixture_original_policy',budget)
    fd=own_module(FD_REF,'released_fixture_original_directory_guard',budget)
    raw=read_pin(ROOT,TOOL_REF,budget=budget);inspect_tool_bytes(raw)
    parent=canonical(packet['temp_parent']);no_alias(parent);need(parent.is_dir(),'FIXTURE_TEMP_PARENT')
    scope=parent/('ssl-fixtures-v1_1-'+packet['root_sha256'][:16]+'-'+packet['runtime'])
    no_alias(scope);need(not scope.exists(),'FIXTURE_SPENT_SCOPE')
    scope.mkdir(mode=0o700,exist_ok=False);(scope/'controls').mkdir(mode=0o700);(scope/'prefixes').mkdir(mode=0o700)
    fs=DiskFS(scope);policy=policy_class(base.GuestPolicy)(scope,budget);fs.bind(policy)
    policy.generated_compile=GeneratedCompileGate(bind_runtime_compile(budget))
    install_hooks(policy,fs,base,fd)
    def stop(*_):raise HarnessRefused('FIXTURE_DEADLINE')
    signal.signal(signal.SIGALRM,stop);signal.signal(signal.SIGXCPU,stop)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    signal.setitimer(signal.ITIMER_REAL,120)
    receipt(fs,'BOOTSTRAP_STARTED.json',{'mode':'RELEASED_FIXTURE','source_ref':TOOL_REF,
        'packet_sha256':packet_ref['sha256'],'limits':LIMITS,'no_retry':True})
    try:
        snapshot=scope/'controls'/'installer-1.1.0-py3-none-any.whl'
        fs.write_new(snapshot,raw);policy.sealed.add(snapshot)
        api=activate_tool(_RELEASE_SEAL,snapshot,raw,policy,fs)
        result=_drive(fs,api,pure,base,fd,mode='RELEASED_FIXTURE',budget=budget,policy=policy)
        return {'outcome':result['terminal']['outcome'],'terminal_ref':result['terminal_ref'],
            'scope':str(scope),'installation_accepted':False,'runtime_or_P3_accepted':False}
    except BaseException as primary:
        budget.close_for_evidence();policy.phase_set('CONTROL')
        try:receipt(fs,'BOOTSTRAP_FAILED.json',{'mode':'RELEASED_FIXTURE','phase':policy.phase,
            'error_code':_closed_error(primary,pure,base),'usage':budget.summary(),'no_retry':True,
            'installation_accepted':False,'runtime_or_P3_accepted':False})
        except BaseException:pass
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    # No default execution path: the lead must provide a separately reviewed
    # explicit caller/packet after this candidate's concrete review.
    print(packed({'status':'CANDIDATE_ONLY_EXACT_RELEASE_REQUIRED','actual_execution':False}).decode())
