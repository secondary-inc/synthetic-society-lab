from pathlib import Path
import sys,resource,signal,time,json,unittest,sysconfig,os
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120));signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(120)
root=Path.cwd();sys.path.insert(0,str(root/'src'));start=time.monotonic()
from civiclab.e01 import fec2020_parser_v1
stdlib=Path(sysconfig.get_path('stdlib')).resolve();tests=root/'tests/test_fec2020_parser_v1.py';extra=root/'reports/evidence_independent_fec2020_parser_v1_2_20261118/additional_controls.py';contract=root/'configs/e01_fec2020_senate_mapping_v1.json'
def audit(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.fork','os.posix_spawn','os.system','sqlite3.connect','ctypes.dlopen'):raise RuntimeError('NO_NETWORK_PROCESS_OWNER')
 if event=='open' and not isinstance(args[0],int):
  p=Path(args[0]).resolve();flags=args[2]
  assert not flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
  assert p in (tests,extra,contract) or p.is_relative_to(stdlib)
sys.addaudithook(audit);suite=unittest.TestSuite()
for path in (tests,extra):
 import types
 mod=types.ModuleType('_independent_'+path.stem);mod.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),mod.__dict__);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
r=unittest.TextTestRunner(verbosity=2).run(suite);print(json.dumps({'kind':'INDEPENDENT_FEC_V1_3_FOCUSED','tests':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'successful':r.wasSuccessful(),'runtime':sys.version.split()[0],'CPU_seconds':sum(resource.getrusage(resource.RUSAGE_SELF)[:2]),'wall_seconds':time.monotonic()-start,'actual_workbook_reader_network_key_owner_calls':0},sort_keys=True));signal.alarm(0);raise SystemExit(0 if r.wasSuccessful() else 1)
