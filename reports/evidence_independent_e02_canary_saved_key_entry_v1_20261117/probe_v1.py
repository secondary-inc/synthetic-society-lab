"""Inert bridge qualification, never real key reader or real launcher main."""
import os,sys,time,resource,signal,hashlib,json,types,io,tempfile,shutil,unittest,importlib.util
from pathlib import Path
from unittest.mock import patch
START=time.monotonic();resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(59,60))
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('INDEPENDENT120')));signal.alarm(120)
ROOT=Path.cwd();BRIDGE=ROOT/'scripts/launch_e02_canary_with_saved_key_20261117.py';TEST=ROOT/'tests/test_e02_canary_saved_key_entry_v1.py'
assert hashlib.sha256(BRIDGE.read_bytes()).hexdigest()=='80bbeafa473662ce4075de74e36f8ac31fd397c3f5c3cf8fad65d941721ebb58'
assert hashlib.sha256(TEST.read_bytes()).hexdigest()=='781c4edf7cf8bd6cb4b48f99fc2ddd5305d1be2266cc0bbb395aef17b0940d5c'
scratch=Path(tempfile.mkdtemp(prefix='INDEPENDENT_SAVED_KEY_')).resolve();tempfile.tempdir=str(scratch)
COUNTERS={'file_reads':0,'file_write_reservations':0,'denials':0}
stdlib=Path(os.__file__).resolve().parent
def audit(event,args):
    if event.startswith(('socket.','subprocess.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec'}:
        COUNTERS['denials']+=1;raise PermissionError('NO_EXTERNAL')
    if event=='open' and type(args[0]) is not int:
        p=Path(os.fsdecode(args[0])).absolute();flags=args[2]
        if p.name.startswith('.env') or 'Application Support/SyntheticSocietyLab' in str(p):raise PermissionError('NO_REAL_CREDENTIAL_OR_OWNER')
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            if not p.is_relative_to(scratch):raise PermissionError('OWNED_WRITES_ONLY')
            COUNTERS['file_write_reservations']+=65537
            if COUNTERS['file_write_reservations']>4194304:raise RuntimeError('WRITE_RESERVATION_LIMIT')
        else:
            if p not in {BRIDGE,TEST} and not p.is_relative_to(scratch) and not p.is_relative_to(stdlib):raise PermissionError('UNLISTED_READ')
            if p.is_file():COUNTERS['file_reads']+=p.stat().st_size+1
            if COUNTERS['file_reads']>33554432:raise RuntimeError('READ_LIMIT')
sys.addaudithook(audit)
# The bridge's validation import is an explicit inert boundary; no production
# package is imported by this test allocation.
pkg=types.ModuleType('civiclab');pkg.__path__=[]
e02=types.ModuleType('civiclab.e02');e02.__path__=[]
client=types.ModuleType('civiclab.e02.wrapper_crossmodel_canary_v1_client')
client.validate_release=lambda *args:None;e02.wrapper_crossmodel_canary_v1_client=client;pkg.e02=e02
sys.modules.update({'civiclab':pkg,'civiclab.e02':e02,'civiclab.e02.wrapper_crossmodel_canary_v1_client':client})
spec=importlib.util.spec_from_file_location('independent_saved_key_tests',TEST);T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T);entry=T.entry
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(T.SavedKeyEntry))
OBS=[]
def record(name,passed,**kw):OBS.append({'case':name,'pass':bool(passed),**kw})
for error_type in (KeyboardInterrupt,SystemExit):
    events=[];oldargv=sys.argv
    def read(path,d):events.append('read');return {}
    def credential(root):events.append('credential');return types.SimpleNamespace(_value='AUTHORED_INERT_ONLY_1234')
    def main():events.append('main');raise error_type()
    launcher=types.SimpleNamespace(SCOPE=scratch,read_exact=read,main=main)
    def load(path,d):return launcher if path==entry.LAUNCHER else types.SimpleNamespace(_credential=credential)
    with patch.dict(os.environ,{'OPENROUTER_API_KEY':'AUTHORED_PRIOR'},clear=True),patch.object(entry,'_load_exact',side_effect=load):
        try:entry.run('a'*64,'b'*64)
        except error_type:pass
        record('cleanup_'+error_type.__name__,sys.argv is oldargv and os.environ.get('OPENROUTER_API_KEY')=='AUTHORED_PRIOR' and events.count('main')==events.count('credential')==1)
for failing_name in ('packet.json','lead-release.json'):
    events=[]
    def read(path,d):
        events.append(path.name)
        if path.name==failing_name:raise ValueError('AUTHORED_GATE')
        return {}
    launcher=types.SimpleNamespace(SCOPE=scratch,read_exact=read,main=lambda:events.append('main'))
    def load(path,d):
        events.append('launcher' if path==entry.LAUNCHER else 'KEY_READER_UNEXPECTED')
        return launcher
    with patch.object(entry,'_load_exact',side_effect=load):
        try:entry.run('a'*64,'b'*64)
        except ValueError:pass
    record('file_gate_'+failing_name,'KEY_READER_UNEXPECTED' not in events and 'main' not in events)
oversized=scratch/'oversized.py';oversized.write_bytes(b'x'*65537)
try:entry._load_exact(oversized,hashlib.sha256(oversized.read_bytes()).hexdigest());refused=False
except RuntimeError:refused=True
record('oversize_correct_hash_refused',refused)
real=scratch/'real-parent';real.mkdir();source=real/'p.py';raw=b'answer=42\n';source.write_bytes(raw)
alias=scratch/'alias-parent';alias.symlink_to(real,target_is_directory=True)
try:entry._load_exact(alias/'p.py',hashlib.sha256(raw).hexdigest());refused=False
except RuntimeError:refused=True
record('ancestor_alias_refused',refused)
events=[]
def load(path,d):
    if path==entry.LAUNCHER:return types.SimpleNamespace(SCOPE=scratch,read_exact=lambda *a:{},main=lambda:events.append('main'))
    events.append('key_source_refused');raise RuntimeError('PIN_REFUSAL')
with patch.object(entry,'_load_exact',side_effect=load):
    try:entry.run('a'*64,'b'*64)
    except RuntimeError:pass
record('key_source_hash_refusal_no_main',events==['key_source_refused'])
report={'kind':'INDEPENDENT_SAVED_KEY_BRIDGE_INERT_PROBE','runtime':sys.version.split()[0],
 'original_suite':{'tests':result.testsRun,'errors':len(result.errors),'failures':len(result.failures)},'additional_observations':OBS,'failed_case_names':[x['case'] for x in OBS if not x['pass']],
 'counters':COUNTERS,'real_credential_reads':0,'real_launcher_main_calls':0,'actual_owner_calls':0,'network_calls':0,'model_calls':0,'cost_usd':0,'scratch':str(scratch),'wall_seconds':time.monotonic()-START}
if not result.wasSuccessful():report['bounded_first_error']=(result.errors or result.failures)[0][1][:3000]
text=json.dumps(report,sort_keys=True);assert len(text.encode())<131072;print(text)
