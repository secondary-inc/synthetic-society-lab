import json
import tempfile
import unittest
from pathlib import Path
from civiclab.common import RunStore, canonical_hash, sha256_file
from civiclab.integrity import validate_sources
from civiclab.gates import compare_gate


ROOT = Path(__file__).resolve().parents[1]


class FoundationTests(unittest.TestCase):
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
