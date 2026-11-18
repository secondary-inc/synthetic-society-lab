"""Four exact mocked run_pip cases plus seven real Darwin MIME class cases.

No installer/PDF/data/owner run. Selected test bodies remain byte-for-byte intact.
"""
from pathlib import Path
import importlib.util
import json
import os
import resource
import signal
import sys
import sysconfig
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]


def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.alarm(120)
    assert sys.flags.no_site==1 and not any('site-packages' in path for path in sys.path)
    with tempfile.TemporaryDirectory(prefix='CI_STARTUP_HOST_AUTHOR_') as temporary:
        scratch=Path(temporary).resolve();tempfile.tempdir=str(scratch)
        stdlib=Path(sysconfig.get_path('stdlib')).resolve();read_bytes=[0]
        helper_path=ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py'
        helper_spec=importlib.util.spec_from_file_location('ci_startup_probe_dirfd',helper_path)
        helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
        descriptor=helper.DirectoryFdGuard(lambda path,flags:None)
        def audit(event,args):
            if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.posix_spawn','os.system','ctypes.dlopen','sqlite3.connect'}:
                raise AssertionError('CI_PROBE_NO_NETWORK_PROCESS_OWNER_NATIVE')
            if event=='open' and not isinstance(args[0],int):
                path=descriptor.event_path(args[0]).resolve();flags=args[2]
                if path.name.startswith('.env') or 'SyntheticSocietyLab' in str(path):raise AssertionError('CI_PROBE_NO_PRIVATE_OWNER_KEY')
                writing=flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
                if writing and not path.is_relative_to(scratch):raise AssertionError('CI_PROBE_ONLY_OWNED_SCRATCH')
                if not writing:
                    if not(path.is_relative_to(stdlib) or path.is_relative_to(scratch) or path.is_relative_to(ROOT/'tests') or path.is_relative_to(ROOT/'scripts') or path.is_relative_to(ROOT/'configs') or path==Path(__file__).resolve()):raise AssertionError('CI_PROBE_SOURCE_ONLY_READS')
                    if path.is_file():read_bytes[0]+=path.stat().st_size
                    if read_bytes[0]>67108864:raise AssertionError('CI_PROBE_READ_BOUND')
        sys.addaudithook(audit);os.open=descriptor.open;os.close=descriptor.close
        sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src')]
        result_rows=[]
        for suffix in ('v1','v1_1','v1_2','v1_3','v1_5'):
            name='test_e01_pypdf701_install_'+suffix
            spec=importlib.util.spec_from_file_location(name,ROOT/'tests'/(name+'.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            if suffix=='v1_5':
                suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.ProductionMimeTests)
            else:
                cls=module.InstallerFixtureTests if suffix=='v1' else module.ConsumerFixtureTests
                suite=unittest.TestSuite([cls('test_actual_mock_run_pip_path_excludes_oldsite_and_uses_prefix')])
            result=unittest.TextTestRunner(verbosity=2).run(suite)
            result_rows.append({'module':name,'tests':result.testsRun,'successful':result.wasSuccessful()})
        assert all(row['successful'] for row in result_rows)
        print(json.dumps({'kind':'CI_EXACT_STARTUP_DARWIN_HOST_PROBE','runtime':sys.version.split()[0],
                          'platform':sys.platform,'no_site':bool(sys.flags.no_site),'selected_results':result_rows,
                          'read_reservation_bytes':read_bytes[0],'native_installer_calls':0,'actual_PDF_reads':0,
                          'owner_key_data_access':0,'network_model_calls':0,'cost_usd':0},sort_keys=True))


if __name__=='__main__':main()
