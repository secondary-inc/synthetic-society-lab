import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from civiclab.common import RunStore, canonical_hash, sha256_file
from civiclab.integrity import validate_sources
from civiclab.gates import compare_gate


ROOT = Path(__file__).resolve().parents[1]


class FoundationTests(unittest.TestCase):
    def test_interrupted_finalization_recovers_without_overwriting_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=RunStore(tmp,'E02',{'seed':1})
            original=run.write
            def interrupted(name,value):
                if name=='checksums.json':raise OSError('injected finalization failure')
                return original(name,value)
            with self.assertRaises(OSError),patch.object(run,'write',side_effect=interrupted):
                with run:run.finish({'status':'PASS'})
            self.assertTrue((run.path/'summary.json').exists())
            self.assertFalse((run.path/'checksums.json').exists())
            before=sha256_file(run.path/'summary.json')
            with RunStore.resume(tmp,run.path,{'seed':1}) as recovered:
                pass
            self.assertEqual(before,sha256_file(run.path/'summary.json'))
            checks=json.loads((run.path/'checksums.json').read_text())
            for name,digest in checks.items():self.assertEqual(sha256_file(run.path/name),digest)
    def test_fixture_and_tamper(self):
        self.assertEqual(validate_sources(ROOT, True)["status"], "PASS")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "tests/fixtures/gdelt"
            folder.mkdir(parents=True)
            f = folder / "fixture.zip"
            f.write_bytes(b"original")
            (folder / "manifest.json").write_text(json.dumps({"path": str(f.relative_to(root)), "sha256": sha256_file(f)}))
            self.assertEqual(validate_sources(root, True)["status"], "PASS")
            f.write_bytes(b"tampered")
            self.assertEqual(validate_sources(root, True)["status"], "BLOCKED")

    def test_inventory_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tests/fixtures/gdelt"
            p.mkdir(parents=True)
            (p / "manifest.json").write_text(json.dumps({"path": "../../outside", "sha256": "x"}))
            self.assertEqual(validate_sources(tmp, True)["checks"][0]["status"], "UNSAFE_PATH")

    def test_declared_module_source_cannot_be_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'tests/fixtures/gdelt';folder.mkdir(parents=True)
            fixture=folder/'fixture.zip';fixture.write_bytes(b'fixture')
            (folder/'manifest.json').write_text(json.dumps({'path':str(fixture.relative_to(root)),'sha256':sha256_file(fixture)}))
            configs=root/'configs';configs.mkdir()
            (configs/'SOURCE_INVENTORY.json').write_text(json.dumps({'archives':[]}))
            (configs/'e02_citizen_benchmark_acquisition.json').write_text('{}')
            self.assertEqual(validate_sources(root,True)['status'],'PASS')
            result=validate_sources(root)
            self.assertEqual(result['status'],'BLOCKED')
            self.assertEqual(result['checks'][-1]['type'],'module_source_verifier')

    def test_run_immutable_reproducible_and_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = RunStore(tmp, "E02", {"seed": 4, "api_key": "secret"})
            b = RunStore(tmp, "E02", {"seed": 4, "api_key": "secret"})
            self.assertEqual(a.experiment_id, b.experiment_id)
            self.assertNotEqual(a.run_id, b.run_id)
            a.write("responses.json", {"answer": 2})
            with self.assertRaises(FileExistsError):
                a.write("responses.json", {})
            a.finish({"status": "PASS"})
            b.finish({"status": "PASS"})
            self.assertNotIn('"secret"', (a.path / "manifest.json").read_text())
            environment=json.loads((a.path/'environment.json').read_text())
            self.assertTrue(environment['core_uses_standard_library'])
            self.assertIsInstance(environment['installed_relevant_packages'],dict)
            for path, digest in json.loads((a.path / "checksums.json").read_text()).items():
                self.assertEqual(sha256_file(a.path / path), digest)

    def test_run_lock_and_resume_code_config_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=RunStore(tmp,'E02',{'seed':1})
            with self.assertRaises(RuntimeError):
                RunStore.resume(tmp,a.path,{'seed':1})
            with self.assertRaises(ValueError):
                RunStore.resume(tmp,a.path,{'seed':2})
            a._release_lock()
            resumed=RunStore.resume(tmp,a.path,{'seed':1})
            resumed.finish({'status':'PASS'})
            with self.assertRaises(RuntimeError):
                resumed.write('after.json',{})

    def test_gate_rejects_mismatched_conditions_and_swarm_compute(self):
        run = {k: "same" for k in ("evaluation_units", "outcome", "split_hash", "input_cutoff", "instrument_hash")}
        run.update(status="PASS", artifact_sha256="abc", token_budget=100)
        self.assertEqual(compare_gate(run, run)["status"], "PASS")
        self.assertEqual(compare_gate(run, {**run, "evaluation_units": "different"})["status"], "BLOCKED")
        self.assertEqual(compare_gate(run, {**run, "token_budget": 200}, require_equal_compute=True)["status"], "BLOCKED")
