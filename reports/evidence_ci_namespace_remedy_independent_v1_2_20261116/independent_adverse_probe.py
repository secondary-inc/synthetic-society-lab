"""Independent namespace-context checks using only harmless temporary modules."""
import sys

def deny(event,args):
    if event.startswith(('socket.','ctypes.')) or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','pty.spawn'}:
        raise AssertionError('NO_REAL_NETWORK_PROCESS_NATIVE')
    if event=='import' and args and args[0].split('.')[0] in {'pip','installer','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:
        raise AssertionError('NO_TOOL_PACKAGE_IMPORT')
sys.addaudithook(deny)
import hashlib,importlib,importlib.util,io,json,os,resource,signal,tempfile,types
from pathlib import Path
from unittest import mock
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def deadline(*_):raise AssertionError('PROBE_120_SECOND_LIMIT')
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,120)
ROOT=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab');SOURCE=ROOT/'scripts/run_offline_ci_v1.py';ME=Path(__file__).resolve();STDLIB=Path(sys.base_prefix)/'lib';technical=[0];writes=[0]
with tempfile.TemporaryDirectory(prefix='civiclab-independent-namespace-') as temporary:
    scratch=Path(temporary).resolve();root=scratch/'owned';(root/'tests').mkdir(parents=True)
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.path.realpath(args[0]));flags=args[2]
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if not p.is_relative_to(scratch):raise AssertionError('WRITE_OUTSIDE_TEMPORARY_TREE')
            else:
                if not(p in {SOURCE,ME} or p.is_relative_to(scratch) or (p.is_relative_to(STDLIB) and 'site-packages' not in p.parts)):raise AssertionError('UNAPPROVED_TECHNICAL_READ')
                try:technical[0]+=p.stat().st_size+1
                except FileNotFoundError:technical[0]+=1
                if technical[0]>67108864:raise AssertionError('TECHNICAL_READ_CAP')
    sys.addaudithook(audit)
    source=SOURCE.read_bytes();assert hashlib.sha256(source).hexdigest()=='61bdc69cdcf592af213c0e8c357a0a8976a3140bcd8a60a4731a1972f2d6a3ae';c=types.ModuleType('independent_namespace_component');c.__file__=str(SOURCE);exec(compile(source,str(SOURCE),'exec'),c.__dict__)
    checks=[]
    def ok(name,value):assert value,name;checks.append(name)
    def put(path,text):
        body=text.encode();writes[0]+=len(body);assert writes[0]<=33554432;path.write_bytes(body)
    put(root/'tests/safe_audit_fixture.py','VALUE=20261116\n')
    put(root/'tests/safe_audit_bridge.py','from safe_audit_fixture import VALUE as BARE\nfrom tests.safe_audit_fixture import VALUE as QUALIFIED\ndef late():\n from tests.safe_audit_fixture import VALUE\n return VALUE\n')
    def state():return (sys.path,sys.path[:],sys.meta_path,sys.meta_path[:],sys.path_importer_cache.copy())
    def restored(before):return sys.path is before[0] and sys.path==before[1] and sys.meta_path is before[2] and sys.meta_path==before[3] and sys.path_importer_cache==before[4] and not any(n=='tests' or n.startswith('tests.') or n in ('safe_audit_fixture','safe_audit_bridge') for n in sys.modules)
    before=state()
    with c.ordinary_import_context(root):
        bridge=importlib.import_module('safe_audit_bridge');ok('bare and qualified authored import values',bridge.BARE==bridge.QUALIFIED==20261116);ok('both origins canonical',Path(sys.modules['safe_audit_fixture'].__file__)==Path(sys.modules['tests.safe_audit_fixture'].__file__)==root/'tests/safe_audit_fixture.py')
    ok('normal context restores paths meta cache and modules',restored(before))
    primary=ValueError('AUTHORED_PRIMARY');before=state()
    try:
        with c.ordinary_import_context(root):importlib.import_module('tests.safe_audit_fixture');raise primary
    except ValueError as error:ok('context preserves exact primary exception',error is primary)
    ok('exception restores namespace context',restored(before))
    callbacks=[]
    class FakeLoader:
        def discover(self,path):importlib.import_module('safe_audit_bridge');return object()
    before=state();suite,barrier=c.collect_ordinary(root,loader=FakeLoader(),install_hook=callbacks.append);ok('mock collection one injected barrier and no global hook',len(callbacks)==1 and barrier.collecting is False);ok('mock collection restores context',restored(before))
    # Actual child API is exercised only with its collector, framework runner and limits mocked.
    observed=[]
    def fake_collect(root):observed.append(importlib.import_module('safe_audit_bridge'));return object(),None
    class FakeRunner:
        def __init__(self,*args,**kwargs):pass
        def run(self,suite):observed.append(observed[0].late());return c.RecordingResult(io.StringIO(),False,0)
    before=state()
    with mock.patch.object(c,'_collect_ordinary',fake_collect),mock.patch.object(c.unittest,'TextTestRunner',FakeRunner),mock.patch.object(c.resource,'setrlimit'),mock.patch.object(c.signal,'signal'),mock.patch.object(c.signal,'setitimer'):
        result=c.child_entry(root,'ordinary','ordinary')
    ok('lazy import works inside mocked child lifetime',observed[1]==20261116 and result['tests_run']==0);ok('mocked child exit restores import context',restored(before))
    # Preloaded foreign modules fail before yielding; all are authored placeholders.
    foreign=scratch/'foreign';(foreign/'tests').mkdir(parents=True);put(foreign/'tests/__init__.py','raise AssertionError("FOREIGN_SOURCE_MUST_NOT_EXECUTE")\n');put(foreign/'safe_audit_fixture.py','raise AssertionError("FOREIGN_BARE_MUST_NOT_EXECUTE")\n')
    def refuses(name,call):
        try:call()
        except c.IsolationError:checks.append(name);return
        raise AssertionError(name+' unexpectedly admitted')
    def enter():
        with c.ordinary_import_context(root):raise AssertionError('UNSAFE_CONTEXT_YIELDED')
    before=state()
    with mock.patch.object(sys,'path',[str(foreign),*sys.path]):refuses('foreign regular tests package refused without execution',enter)
    ok('foreign package failure restores state',restored(before));(foreign/'tests/__init__.py').unlink()
    with mock.patch.object(sys,'path',[str(foreign),*sys.path]):refuses('foreign namespace portion refused',enter)
    bare=importlib.util.module_from_spec(importlib.util.spec_from_file_location('safe_audit_fixture',foreign/'safe_audit_fixture.py'))
    with mock.patch.dict(sys.modules,{'safe_audit_fixture':bare}):refuses('foreign cached bare module refused',enter)
    with mock.patch.dict(sys.modules,{'tests':types.SimpleNamespace(__spec__=None)}):refuses('unbound cached tests namespace refused',enter)
    alias=scratch/'alias';alias.symlink_to(root,target_is_directory=True)
    def enter_alias():
        with c.ordinary_import_context(alias):raise AssertionError('ALIAS_YIELDED')
    refuses('aliased root refused',enter_alias)
    # Every frozen name is blocked under both spellings, without executing even a placeholder.
    for row in c.FROZEN.values():put(root/'tests'/row[0],'raise AssertionError("FROZEN_PLACEHOLDER_MUST_NOT_EXECUTE")\n')
    for row in c.FROZEN.values():
        stem=Path(row[0]).stem
        for name in (stem,'tests.'+stem):
            def import_frozen(name=name):
                with c.ordinary_import_context(root):importlib.import_module(name)
            refuses('frozen import refused '+name,import_frozen)
            module=importlib.util.module_from_spec(importlib.util.spec_from_file_location(name,root/'tests'/row[0]))
            with mock.patch.dict(sys.modules,{name:module}):refuses('preloaded frozen refused '+name,enter)
        barrier=c.CollectionBarrier(root)
        refuses('original filename execution barrier '+stem,lambda b=barrier,row=row:b('exec',(compile('pass',str(root/'tests'/row[0]),'exec'),)))
    ok('all refusal paths left no owned modules',not any(n=='tests' or n.startswith('tests.') or n in ('safe_audit_fixture','safe_audit_bridge') for n in sys.modules))
    output={'kind':'INDEPENDENT_NAMESPACE_ADVERSE_PROBE','status':'PASS','Python':sys.version.split()[0],'runner_sha256':hashlib.sha256(source).hexdigest(),'checks':len(checks),'names':checks,'technical_read_bytes':technical[0],'authored_temp_bytes':writes[0],'real_collection_groups_repo_test_bodies_children_installs_network_owner_key_actions':0};encoded=json.dumps(output,sort_keys=True);assert len(encoded.encode())<=262144;print(encoded)
signal.setitimer(signal.ITIMER_REAL,0)
