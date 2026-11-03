"""Guarded authored-only Alabama v1/v1.1 regression; zero actual-source I/O."""
import hashlib,json,pathlib,sys,time,unittest
root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/'src'))
blocked=(root/'data/raw',root/'data/processed')
# The separately installed 3.11 stdlib lives under processed/toolchains.
# Permit only this interpreter's lib tree, never research sources or runs.
runtime_lib=pathlib.Path(sys.base_prefix).resolve()/('lib/python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor))
def audit(event,args):
    if event=='open' and args and isinstance(args[0],(str,bytes)):
        p=pathlib.Path(args[0]).resolve()
        if any(p==b or b in p.parents for b in blocked) and not (p==runtime_lib or runtime_lib in p.parents):raise RuntimeError('FORBIDDEN_ACTUAL_SOURCE_OR_RUN_IO')
    if event in ['os.scandir','os.listdir'] and args and isinstance(args[0],(str,bytes)):
        p=pathlib.Path(args[0]).resolve()
        if any(p==b or b in p.parents for b in blocked) and not (p==runtime_lib or runtime_lib in p.parents):raise RuntimeError('FORBIDDEN_ACTUAL_SOURCE_OR_RUN_ENUMERATION')
    if event.startswith('socket.'):raise RuntimeError('FORBIDDEN_NETWORK')
# Interpreter itself is loaded before guards; fixtures cannot access actual data.
paths=[root/p for p in [
 'src/civiclab/e01/alabama_documents_v1.py','src/civiclab/e01/alabama_source_release_v1.py',
 'src/civiclab/e01/alabama_recorded_preflight_v1.py','src/civiclab/common.py','src/civiclab/dashboard.py',
 'tests/test_e01_alabama_documents_v1.py','tests/test_e01_alabama_source_release_v1.py','tests/test_e01_alabama_recorded_preflight_v1.py',
 'configs/e01_al_source_release_v1_candidate.json','configs/e01_al_standalone_runtime_contract_v1_candidate.json',
 'configs/e01_al_office_label_equivalence_v1_1_methods_proposal.json',
 'reports/INDEPENDENT_AUDIT_E01_AL_OFFICE_LABEL_EQUIVALENCE_V1_1_METHODS.json',
 'src/civiclab/e01/alabama_office_context_v1_1.py','src/civiclab/e01/alabama_source_release_v1_1.py',
 'src/civiclab/e01/alabama_recorded_preflight_v1_1.py','configs/e01_al_office_family_rule_v1_1.json',
 'configs/e01_al_office_context_schema_v1_1.json','configs/e01_al_source_release_v1_1_candidate.json',
 'tests/test_e01_alabama_office_context_v1_1.py','tests/test_e01_alabama_source_release_v1_1.py',
 'tests/test_e01_alabama_recorded_preflight_v1_1.py','scripts/e01_al_office_context_v1_1_fixture_check.py']]
before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
sys.addaudithook(audit)
modules=['tests.test_e01_alabama_office_context_v1_1','tests.test_e01_alabama_source_release_v1_1','tests.test_e01_alabama_recorded_preflight_v1_1','tests.test_e01_alabama_documents_v1','tests.test_e01_alabama_source_release_v1','tests.test_e01_alabama_recorded_preflight_v1']
start=time.monotonic();result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
after={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
print(json.dumps({'python':sys.version.split()[0],'tests':result.testsRun,'success':result.wasSuccessful(),'seconds':round(time.monotonic()-start,6),'protected_files_unchanged':before==after,'protected_pins':before,'guard':'DENY_ACTUAL_REPO_DATA_RAW_PROCESSED_READS_ENUMERATION_AND_ALL_SOCKET_EVENTS'},sort_keys=True))
sys.exit(0 if result.wasSuccessful() and before==after else 1)
