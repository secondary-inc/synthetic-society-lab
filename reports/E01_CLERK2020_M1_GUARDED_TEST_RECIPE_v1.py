from pathlib import Path
import hashlib,json,sys,time,unittest
root=Path.cwd().resolve();sys.path[:0]=[str(root),str(root/'src')]
policy=json.loads((root/'configs/e01_clerk2020_m1_v1_disabled.json').read_text());methods=json.loads((root/policy['methods_ref']['path']).read_text())
newpaths=['src/civiclab/e01/clerk2020_contracts_v1.py','src/civiclab/e01/clerk2020_inspection_m1_v1.py','src/civiclab/e01/clerk2020_m1_worker_v1.py','configs/e01_clerk2020_m1_v1_disabled.json','tests/test_e01_clerk2020_m1_v1.py']
protected=[x['path'] for x in methods['authoritative_protocol_code_refs']]+[policy['methods_ref']['path'],policy['methods_audit_ref']['path'],'docs/E01_CLERK_2020_SENATE_INPUT_METHODS_v1.md','src/civiclab/common.py','src/civiclab/reproduction.py','scripts/e01_clerk_documents_capture_v1.py']
paths=sorted(set(newpaths+protected));pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
stdlib=Path(sys.base_prefix).resolve()/('lib/python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor));blocked=[root/'data/raw',root/'data/processed']
def guard(event,args):
 if event in {'open','os.listdir','os.scandir'} and args and isinstance(args[0],(str,bytes)):
  p=Path(args[0]).resolve()
  if any(p==b or b in p.parents for b in blocked) and not (p==stdlib or stdlib in p.parents):raise RuntimeError('ACTUAL_RESEARCH_SOURCE_IO_FORBIDDEN')
 if event.startswith('socket.'):raise RuntimeError('NETWORK_FORBIDDEN')
sys.addaudithook(guard)
start=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_e01_clerk2020_m1_v1','tests.test_e01','tests.test_e01_clerk_documents_capture_v1'])
result=unittest.TextTestRunner(verbosity=1).run(suite)
after={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
print(json.dumps({'label':'MOCK_AUTHORED_ONLY','python':sys.version.split()[0],'tests':result.testsRun,'success':result.wasSuccessful(),'seconds':round(time.monotonic()-start,6),'source_config_test_protocol_hashes_unchanged':pins==after,'pins':pins,'guard':'Deny actual repository data/raw+processed reads/enumerations and sockets; current interpreter stdlib only exception. Child fixed backend separately denies I/O after trusted imports.'},sort_keys=True))
sys.exit(0 if result.wasSuccessful() and pins==after else 1)
