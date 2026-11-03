from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from civiclab.common import RunStore
from civiclab.reproduction import build_package,verify_package


class PackageTests(unittest.TestCase):
    def test_package_determinism_sealed_runs_and_private_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'README.md').write_text('Review only')
            (root/'.env').write_text('DO_NOT_EXPORT=private')
            raw=root/'data/raw/private.csv';raw.parent.mkdir(parents=True);raw.write_text('private source')
            report=root/'reports/ENGINEERING_EVIDENCE_TEST.json';report.parent.mkdir();report.write_text('{}')
            (report.parent/'E02_WORKER_RECEIPT.md').write_text('Observed module receipt')
            with RunStore(root,'E01',{},kind='MOCK') as run:run.finish({'status':'DEMO','cost_usd':0})
            metadata=root/'src/local_project.egg-info';metadata.mkdir(parents=True)
            (metadata/'SOURCES.txt').write_text('generated during install')
            a=build_package(root,root/'a.zip',[run.run_id])
            (metadata/'SOURCES.txt').write_text('regenerated during another install')
            b=build_package(root,root/'b.zip',[run.run_id])
            self.assertEqual(a['sha256'],b['sha256'])
            with self.assertRaises(FileExistsError):build_package(root,root/'a.zip',[run.run_id])
            self.assertEqual(verify_package(root/'a.zip')['sha256'],a['sha256'])
            with zipfile.ZipFile(root/'a.zip') as z:
                self.assertNotIn('.env',z.namelist());self.assertFalse(any(n.startswith('data/raw/') for n in z.namelist()))
                self.assertIn('reports/ENGINEERING_EVIDENCE_TEST.json',z.namelist())
                self.assertIn('reports/E02_WORKER_RECEIPT.md',z.namelist())
                self.assertFalse(any('.egg-info/' in n for n in z.namelist()))
            with zipfile.ZipFile(root/'a.zip','a') as z:z.writestr('unregistered.txt','tampered')
            with self.assertRaises(ValueError):verify_package(root/'a.zip')

    def test_refuses_unselected_or_escaped_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):build_package(tmp,Path(tmp)/'pack.zip',[])
            with self.assertRaises(ValueError):build_package(tmp,Path(tmp)/'pack.zip',['../../outside'])

    def test_local_only_run_artifacts_cannot_enter_review_bundle(self):
        from civiclab.dashboard import verified_run
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,name in enumerate(('aggregate-local-only.json','candidate_rosters.local.json','nested/PRIVATE.LOCAL.JSON')):
                with self.subTest(name=name):
                    with RunStore(root,'E02',{},kind='MOCK') as run:
                        run.write(name,{'private_marker':'RETAIN_ONLY_LOCALLY'});run.finish({'status':'MOCK'})
                    output=root/f'refused-{i}.zip'
                    with self.assertRaisesRegex(ValueError,'local-only'):
                        build_package(root,output,[run.run_id])
                    self.assertFalse(output.exists());self.assertFalse(output.with_suffix('.zip.writing').exists())
                    self.assertEqual(verified_run(run.path)['integrity'],'PASS')
            with RunStore(root,'E02',{},kind='MOCK') as safe:
                safe.write('local-reuse-config.json',{'network_requests':0});safe.finish({'status':'MOCK'})
            self.assertEqual(build_package(root,root/'safe.zip',[safe.run_id])['status'],'PASS_PACKAGE_INTEGRITY')

    def test_source_added_after_enumeration_cannot_create_mixed_snapshot(self):
        from civiclab.dashboard import verified_run
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'src').mkdir()
            (root/'src/initial.py').write_text('initial = True')
            with RunStore(root,'E01',{},kind='MOCK') as run:run.finish({'status':'DEMO'})
            def concurrent_change(path):
                result=verified_run(path)
                (root/'src/added_during_assembly.py').write_text('late = True')
                return result
            with patch('civiclab.reproduction.verified_run',side_effect=concurrent_change):
                with self.assertRaisesRegex(ValueError,'source tree changed'):
                    build_package(root,root/'pack.zip',[run.run_id])
            self.assertFalse((root/'pack.zip').exists())

    def test_local_project_cannot_be_registry_bootstrap_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'pyproject.toml').write_text('[project]\nname="my-local.project"\n')
            config=root/'configs';config.mkdir()
            lock=config/'runtime_python312_20261103.txt';lock.write_text('my_local-project==0.1.0\n')
            with RunStore(root,'E01',{},kind='MOCK') as run:run.finish({'status':'DEMO'})
            with self.assertRaisesRegex(ValueError,'local project'):
                build_package(root,root/'pack.zip',[run.run_id])
            self.assertFalse((root/'pack.zip').exists())
