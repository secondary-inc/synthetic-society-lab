from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from civiclab.common import code_identity,sha256_file
from civiclab.gdelt import ingest_fixture,verify_fixture_export


class ExportTests(unittest.TestCase):
    def test_failed_pointer_update_preserves_prior_verified_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copytree(Path(__file__).resolve().parents[1]/'tests/fixtures/gdelt',root/'tests/fixtures/gdelt')
            ingest_fixture(root)
            out=root/'data/processed/gdelt/fixture.json';csv=root/'data/processed/gdelt/fixture.csv'
            before=(sha256_file(out),sha256_file(csv))
            with patch('civiclab.gdelt.atomic_json',side_effect=OSError('injected final pointer failure')):
                with self.assertRaises(OSError):
                    ingest_fixture(root,summary=Path('data/processed/gdelt/new-summary.csv'))
            self.assertEqual(before,(sha256_file(out),sha256_file(csv)))
            self.assertEqual(verify_fixture_export(root)['records'],868)
            csv.write_text('corrupt')
            with self.assertRaises(ValueError):verify_fixture_export(root)
            with self.assertRaises(FileExistsError):ingest_fixture(root)

    def test_executed_compatibility_script_is_part_of_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);scripts=root/'scripts';scripts.mkdir()
            path=scripts/'gdelt_ingest.py';path.write_text('first version')
            before=code_identity(root)
            path.write_text('changed entry point')
            self.assertNotEqual(before['source_tree_sha256'],code_identity(root)['source_tree_sha256'])
