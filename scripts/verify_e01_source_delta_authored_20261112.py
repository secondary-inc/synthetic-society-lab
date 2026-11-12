import os,sys,json,hashlib,unittest,importlib.abc,subprocess
from pathlib import Path
ROOT=Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
class BlockNative(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'pypdf','PIL','cryptography','_cffi_backend'}:raise RuntimeError('AUDITOR_FORBIDS_NATIVE_PDF_STACK')
sys.meta_path.insert(0,BlockNative())
def guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  p=os.path.abspath(os.fsdecode(args[0]));base=str(ROOT/'data')+os.sep;toolchain=str(ROOT/'data/processed/toolchains/cpython-3.11.17-macos-aarch64-none')+os.sep
  if (p.startswith(base) and not p.startswith(toolchain)) or p.startswith(str(ROOT/'.env')):raise RuntimeError('AUDITOR_FORBIDS_ACTUAL_DATA_OWNER_CREDENTIALS')
 if event.startswith('socket.'):raise RuntimeError('AUDITOR_FORBIDS_NETWORK')
sys.addaudithook(guard)
CHILD_GUARD='''import os,sys,importlib.abc
class AuditBlockNative(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'pypdf','PIL','cryptography','_cffi_backend'}:raise RuntimeError('AUDITOR_NO_NATIVE')
sys.meta_path.insert(0,AuditBlockNative())
def _audit_guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  p=os.path.abspath(os.fsdecode(args[0]));root='/Users/joshua/Documents/ChatGPT/synthetic-society-lab'
  if (p.startswith(root+'/data/') and not p.startswith(root+'/data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/')) or p.startswith(root+'/.env'):raise RuntimeError('AUDITOR_NO_REAL_DATA')
 if event.startswith('socket.') or event=='subprocess.Popen':raise RuntimeError('AUDITOR_NO_NETWORK_NESTED_CHILD')
sys.addaudithook(_audit_guard)
'''
original_popen=subprocess.Popen
allowed_children=[]
def gated_popen(args,*a,**kw):
 assert isinstance(args,list) and args[:4]==[sys.executable,'-I','-B','-S'] and args[4]=='-c'
 code=args[5]
 assert (code.startswith('import signal,time;signal.setitimer') or code.startswith('import resource;resource.setrlimit') or "AUTHORED_CRASH_TARGET_NOT_REACHED" in code)
 allowed_children.append(hashlib.sha256(code.encode()).hexdigest())
 return original_popen(args[:5]+[CHILD_GUARD+code]+args[6:],*a,**kw)
subprocess.Popen=gated_popen
from civiclab.e01 import clerk2020_source_job_v1 as j
paths=list(j.CODE_PATHS)+[
 'scripts/prepare_e01_source_phase.py','scripts/prepare_e01_source_phase_v2.py',
 'tests/test_clerk2020_source_job_v1.py','tests/test_clerk2020_source_packet_prepare_v2.py']
def verify():
 return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
before=verify()
mods=['test_clerk2020_source_format_adapter_v1','test_clerk2020_native_campaign_v1','test_clerk2020_source_worker_v1','test_clerk2020_source_job_v1','test_clerk2020_source_signal_v1','test_clerk2020_source_native_crash_v1','test_clerk2020_source_packet_prepare_v1','test_clerk2020_source_packet_prepare_v2']
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in mods)
result=unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({'scope':'WORKER_DELTA_AUTHORED_ONLY_NOT_SOURCE_RELEASE','tests_run':result.testsRun,'successful':result.wasSuccessful(),'code_unchanged':before==verify(),'verified_public_file_count':len(before),'authored_children':allowed_children,'hashes':before},sort_keys=True))
sys.exit(not result.wasSuccessful())
