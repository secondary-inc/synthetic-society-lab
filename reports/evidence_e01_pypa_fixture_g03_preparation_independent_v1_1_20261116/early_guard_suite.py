import sys
def deny(event,args):
    if event.startswith(('socket.','ctypes.')) or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','os.kill','os.killpg'}:
        raise AssertionError('INDEPENDENT_NO_NATIVE_BACKEND_EFFECTS')
    if event=='import' and args and args[0].split('.')[0] in {'installer','pip','ssl_fixture_payload','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:
        raise AssertionError('INDEPENDENT_NO_TOOL_OR_TARGET')
sys.addaudithook(deny)
import os,runpy,resource,signal,hashlib
from pathlib import Path
def no_native(*args,**kwargs):raise AssertionError('INDEPENDENT_NO_KILL_WAIT4')
os.kill=os.killpg=os.wait4=no_native
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def deadline(*_):raise AssertionError('INDEPENDENT120SECOND_CAP')
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,120)
root=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
for path,h in [('scripts/e01_pypa_fixture_g03_caller_candidate_v1_1_20261116.py','1d956931da7d11cf58cfc540cd7b6b8634aecffc34e5c9b9aa4373be92879abc'),('tests/test_e01_pypa_fixture_g03_caller_candidate_v1_1_20261116.py','21de70a84f62e2cac962f34baf2a4f3b25c90242d56d390528808def79db7555')]:
    assert hashlib.sha256((root/path).read_bytes()).hexdigest()==h
path=root/'tests/test_e01_pypa_fixture_g03_caller_candidate_v1_1_20261116.py'
sys.argv=[str(path)];runpy.run_path(str(path),run_name='__main__')
