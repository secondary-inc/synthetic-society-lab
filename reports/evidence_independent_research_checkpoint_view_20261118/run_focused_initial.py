"""Offline focused viewer review; public records and scratch only."""
import os,sys,resource,signal,unittest,json,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CPU,(899,900));signal.alarm(900)
root=Path.cwd();t=time.monotonic();events={'network_attempts':0,'private_read_attempts':0}
def audit(event,args):
 if event.startswith('socket.') or event.startswith('ctypes.') or event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','os.exec'):
  events['network_attempts']+=1;raise PermissionError('EXTERNAL_EXECUTION_DENIED')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=Path(os.fsdecode(args[0])).absolute()
  if p.is_relative_to(root/'data') or p.name in ('.env','openrouter-v4-bootstrap.local.json'):
   events['private_read_attempts']+=1;raise PermissionError('PRIVATE_INPUT_DENIED')
sys.addaudithook(audit);sys.path[:0]=[str(root/'src'),str(root/'tests')]
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in ('test_research_checkpoint_view','test_live_summary_viewer'))
r=unittest.TextTestRunner(verbosity=1).run(suite)
print('INDEPENDENT_VIEWER_FOCUSED='+json.dumps({'tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'wall_seconds':time.monotonic()-t,**events},sort_keys=True))
raise SystemExit(0 if r.wasSuccessful() else 1)
