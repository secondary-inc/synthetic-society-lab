import sys

def deny(event,args):
    if event.startswith(('socket.','ctypes.')) or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','os.exec','os.spawn','pty.spawn'}:
        raise AssertionError('INDEPENDENT_NO_REAL_NETWORK_PROCESS_NATIVE')
    if event=='import' and args and args[0].split('.')[0] in {'installer','pip','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:
        raise AssertionError('INDEPENDENT_NO_REAL_TOOL_PACKAGE_IMPORT')
sys.addaudithook(deny)
import hashlib,resource,signal,runpy
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def deadline(*_):raise AssertionError('INDEPENDENT_120_SECOND_LIMIT')
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,120)
root=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
for name,expected in [('scripts/run_offline_ci_v1.py','61bdc69cdcf592af213c0e8c357a0a8976a3140bcd8a60a4731a1972f2d6a3ae'),('tests/test_ci_collection_isolation_v1.py','f3ba0b75b883545194696955d067a11d44a96fe90f9736edbf5fca968d27d631')]:
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
sys.argv=[str(root/'tests/test_ci_collection_isolation_v1.py')]
runpy.run_path(sys.argv[0],run_name='__main__')
