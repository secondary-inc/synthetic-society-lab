"""Six fixed source-free nested CPU oracles, not source/native qualification.

Extract the exact production limiter function source once, execute those bytes
in isolated processes, and check actual CLI/worker call placement by AST.
This avoids importing/reading any actual runtime/PDF/source/owner data.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
PATHS={'parent':ROOT/'src/civiclab/e01/clerk2020_source_job_v2.py',
       'child':ROOT/'src/civiclab/e01/clerk2020_source_worker_v2.py',
       'old_child':ROOT/'src/civiclab/e01/clerk2020_source_worker_v1.py'}
SOURCES={k:p.read_text() for k,p in PATHS.items()}
assert sum(len(v.encode())+1 for v in SOURCES.values())<=2097152

def extract(source,name):
    node=next(n for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
    return ast.get_source_segment(source,node)+'\n'

FUNCTIONS=(extract(SOURCES['child'],'ResourceSetupStop')+
           extract(SOURCES['parent'],'configure_cli_limits')+
           extract(SOURCES['child'],'configure_child_limits'))
# Exact production code, not a separately maintained imitation of its conditions.
BASE='''import os,sys,json,resource,signal,importlib.abc
class BlockNative(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'pypdf','PIL','cryptography','_cffi_backend'}:raise RuntimeError('NO_NATIVE')
sys.meta_path.insert(0,BlockNative())
def _guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  p=os.path.abspath(os.fsdecode(args[0]));root=ROOT_LITERAL
  if (p.startswith(root+'/data/') and not p.startswith(root+'/data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/')) or p.startswith(root+'/.env'):raise RuntimeError('NO_ACTUAL_DATA')
 if event.startswith('socket.'):raise RuntimeError('NO_NETWORK')
sys.addaudithook(_guard)
def require(condition):
 if not condition:raise ValueError('AUTHORED_CONDITION_REFUSED')
'''.replace('ROOT_LITERAL',repr(str(ROOT)))+FUNCTIONS+'''
class WorkerNamespace:ResourceSetupStop=ResourceSetupStop
worker=WorkerNamespace()
'''


def wiring_check(parent,child):
    """Limiter calls must precede stdin in the actual production entry paths."""
    pt=ast.parse(parent);ct=ast.parse(child)
    main=next(n for n in reversed(pt.body) if isinstance(n,ast.If))
    cli=[n.lineno for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='configure_cli_limits']
    inputs=[n.lineno for n in ast.walk(main) if isinstance(n,ast.Call) and ast.unparse(n.func)=='sys.stdin.buffer.read']
    assert len(cli)==1 and inputs and cli[0]<min(inputs)
    fn=next(n for n in ct.body if isinstance(n,ast.FunctionDef) and n.name=='source_worker')
    setup=[n.lineno for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='configure_child_limits']
    reads=[n.lineno for n in ast.walk(fn) if isinstance(n,ast.Call) and ast.unparse(n.func)=='sys.stdin.buffer.read']
    assert len(setup)==1 and reads and setup[0]<min(reads)


class CPUInheritanceTests(unittest.TestCase):
    def run_case(self,case):
        child=BASE+'''
result={'label':'AUTHORED_CPU_ONLY','case':CASE_LITERAL}
try:
 if CASE_LITERAL=='OLD_COMPOSITION_REFUSES':resource.setrlimit(resource.RLIMIT_CPU,(20,21))
 elif CASE_LITERAL=='CHILD_CANNOT_RAISE_HARD':resource.setrlimit(resource.RLIMIT_CPU,(7,9))
 else:configure_child_limits()
 result.update(status='SETUP_ACCEPTED',cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),core=list(resource.getrlimit(resource.RLIMIT_CORE)))
 if CASE_LITERAL=='DEFAULT_UNBLOCKED_SIGXCPU':
  result.update(default_signal=signal.getsignal(signal.SIGXCPU)==signal.SIG_DFL,unblocked=signal.SIGXCPU not in signal.pthread_sigmask(signal.SIG_BLOCK,[]))
 if CASE_LITERAL=='FINITE_EXHAUSTION_LOWER_AUTHORED_CAP':
  resource.setrlimit(resource.RLIMIT_CPU,(1,2))
  while True:pass
except (ValueError,ResourceSetupStop) as exc:
 result.update(status='SETUP_REFUSED',error_type=type(exc).__name__,cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),core=list(resource.getrlimit(resource.RLIMIT_CORE)))
print(json.dumps(result,sort_keys=True))
'''.replace('CASE_LITERAL',repr(case))
        parent=BASE+'''
import subprocess
configure_cli_limits('EXEC')
if CASE_LITERAL=='INSUFFICIENT_INHERITED_HARD':resource.setrlimit(resource.RLIMIT_CPU,(6,7))
p=subprocess.run([sys.executable,'-I','-B','-S','-c',CHILD_LITERAL],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3)
assert len(p.stdout)<=2048 and len(p.stderr)<=2048
print(json.dumps({'label':'AUTHORED_NESTED_CLI_CPU_ONLY','case':CASE_LITERAL,'parent_cpu':list(resource.getrlimit(resource.RLIMIT_CPU)),'parent_core':list(resource.getrlimit(resource.RLIMIT_CORE)),'child_returncode':p.returncode,'child_stdout':p.stdout.decode(),'child_stderr_bytes':len(p.stderr)},sort_keys=True))
'''.replace('CASE_LITERAL',repr(case)).replace('CHILD_LITERAL',repr(child))
        with tempfile.TemporaryDirectory() as folder:
            completed=subprocess.run([sys.executable,'-I','-B','-S','-c',parent],
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                cwd=folder,timeout=5,check=True,env={'PATH':os.defpath,'LC_ALL':'C'})
            self.assertEqual(list(Path(folder).iterdir()),[])
        self.assertLessEqual(len(completed.stdout)+len(completed.stderr),4096)
        self.assertEqual(completed.stderr,b'');result=json.loads(completed.stdout)
        self.assertEqual(result['parent_core'],[0,0]);self.assertEqual(result['child_stderr_bytes'],0)
        if case=='FINITE_EXHAUSTION_LOWER_AUTHORED_CAP':
            self.assertLess(result['child_returncode'],0);self.assertEqual(result['child_stdout'],'')
        else:
            self.assertEqual(result['child_returncode'],0);body=json.loads(result['child_stdout'])
            self.assertEqual(body['core'],[0,0])
            expected='SETUP_REFUSED' if case in {'OLD_COMPOSITION_REFUSES','CHILD_CANNOT_RAISE_HARD','INSUFFICIENT_INHERITED_HARD'} else 'SETUP_ACCEPTED'
            self.assertEqual(body['status'],expected)
            if expected=='SETUP_ACCEPTED':self.assertEqual(body['cpu'],[7,8])
            if case=='DEFAULT_UNBLOCKED_SIGXCPU':self.assertTrue(body['default_signal'] and body['unblocked'])
            if case=='INSUFFICIENT_INHERITED_HARD':self.assertEqual(body['error_type'],'ResourceSetupStop')
        return result

    def test_old_composition_refuses(self):self.run_case('OLD_COMPOSITION_REFUSES')
    def test_new_composition_accepts_and_cli_wiring_is_required(self):
        wiring_check(SOURCES['parent'],SOURCES['child'])
        for parent,child in [(SOURCES['parent'].replace("try:configure_cli_limits(","try:UNWIRED("),SOURCES['child']),
                             (SOURCES['parent'],SOURCES['child'].replace("configure_child_limits();stage=","UNWIRED();stage="))]:
            with self.assertRaises(AssertionError):wiring_check(parent,child)
        self.run_case('NEW_COMPOSITION_ACCEPTS')
    def test_child_cannot_raise_hard(self):self.run_case('CHILD_CANNOT_RAISE_HARD')
    def test_insufficient_inherited_hard_refuses(self):self.run_case('INSUFFICIENT_INHERITED_HARD')
    def test_default_unblocked_signal_and_zero_core(self):self.run_case('DEFAULT_UNBLOCKED_SIGXCPU')
    def test_finite_exhaustion_stops_without_core(self):self.run_case('FINITE_EXHAUSTION_LOWER_AUTHORED_CAP')

if __name__=='__main__':unittest.main()
