"""Authored proposal tests; zero actual pip, native, venv or network work."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
c = load('absent_zip_candidate', ROOT/'scripts/e01_p2_absent_zip_path_candidate_v1_20261116.py')
t = load('frozen_p2_context', ROOT/'tests/test_e01_pypdf701_install_v1_3.py')


class AbsentZipCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e01-p2-zip-MOCK-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()/'MOCK_BASE'
        self.stdlib = self.base/'lib/python3.12'
        self.dynamic = self.stdlib/'lib-dynload'
        self.dynamic.mkdir(parents=True)
        self.archive = self.base/'lib/python312.zip'
        self.original = [str(self.archive), str(self.stdlib), str(self.dynamic)]

    def test_exact_absent_conventional_entry_only_is_removed(self):
        self.assertEqual(c.narrowed_paths(self.original, self.base), self.original[1:])
        self.assertEqual(len(self.original), 3)

    def test_existing_zip_file_or_directory_refuses(self):
        for directory in (False, True):
            if directory: self.archive.mkdir()
            else: self.archive.write_bytes(b'MOCK_NOT_A_ZIP')
            with self.assertRaisesRegex(ValueError, 'PIP_ZIP_PRESENT'):
                c.narrowed_paths(self.original, self.base)
            if directory: self.archive.rmdir()
            else: self.archive.unlink()

    def test_dangling_or_present_zip_alias_refuses(self):
        for target in (self.base/'MISSING', self.stdlib):
            self.archive.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'PIP_PATH_ALIAS'):
                c.narrowed_paths(self.original, self.base)
            self.archive.unlink()

    def test_aliased_stdlib_root_refuses(self):
        self.dynamic.rmdir()
        actual = self.stdlib/'MOCK_REAL_DYNAMIC'; actual.mkdir()
        self.dynamic.symlink_to(actual)
        with self.assertRaisesRegex(ValueError, 'PIP_PATH_ALIAS'):
            c.narrowed_paths(self.original, self.base)

    def test_extra_missing_reordered_and_duplicate_entries_refuse(self):
        for paths in (self.original+[str(self.base/'UNKNOWN')], self.original[1:],
                      list(reversed(self.original)), self.original+[self.original[0]]):
            with self.assertRaisesRegex(ValueError, 'PIP_UNEXPECTED_PATHS'):
                c.narrowed_paths(paths, self.base)

    def test_missing_dynamic_directory_refuses(self):
        self.dynamic.rmdir()
        with self.assertRaisesRegex(ValueError, 'PIP_STDLIB_DIRECTORY'):
            c.narrowed_paths(self.original, self.base)


if __name__ == '__main__':
    t.g.old.guarded_test_main()
