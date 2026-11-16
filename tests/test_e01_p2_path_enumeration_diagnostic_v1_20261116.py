"""Authored path-enumeration diagnosis only. No real pip or installer run."""
import builtins
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('p2_frozen_test_context', ROOT/'tests/test_e01_pypdf701_install_v1_3.py')
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)
p = context.p


class PathEnumerationDiagnosis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e01-p2-path-MOCK-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.base = self.root/'MOCK_BASE'
        self.stdlib = self.base/'lib/python3.12'
        self.dynamic = self.stdlib/'lib-dynload'
        self.dynamic.mkdir(parents=True)
        self.site = self.root/p.SITE
        self.site.mkdir(parents=True)
        self.archive = self.base/'lib/python312.zip'
        binding = {'base_prefix': str(self.base), 'pip_root': 'MOCK_OLD_SITE/pip',
                   'pip_files': [], 'pip_metadata_ref': {'path': 'MOCK_OLD_SITE/pip.dist-info/METADATA'}}
        self.policy = p.GuestPolicy(self.root, binding, {'wheels': [], 'remaining_output_bytes': 1024})

    def test_default_style_zip_path_is_outside_exact_stdlib_root(self):
        self.assertFalse(self.archive.exists())
        self.assertFalse(self.archive.is_relative_to(self.stdlib))
        with self.assertRaisesRegex(p.Refused, 'GUEST_READ_OUTSIDE_ALLOWLIST'):
            self.policy.path(self.archive, os.O_RDONLY)

    def test_stdlib_zip_probe_attempts_open_even_when_path_missing(self):
        attempted = []
        original = builtins.open
        def opening(path, *args, **kwargs):
            attempted.append(Path(path))
            self.policy.path(Path(path), os.O_RDONLY)
            return original(path, *args, **kwargs)
        with patch.object(builtins, 'open', opening):
            with self.assertRaisesRegex(p.Refused, 'GUEST_READ_OUTSIDE_ALLOWLIST'):
                zipfile.is_zipfile(self.archive)
        self.assertEqual(attempted, [self.archive])

    def test_explicit_directory_only_candidate_removes_zip_probe(self):
        original = [str(self.archive), str(self.stdlib), str(self.dynamic)]
        candidate = [str(self.site), str(self.stdlib), str(self.dynamic)]
        self.assertIn(str(self.archive), original)
        self.assertNotIn(str(self.archive), candidate)
        self.assertTrue(all(Path(path).is_dir() for path in candidate))
        for path in candidate:
            self.policy.path(Path(path), os.O_RDONLY)

    def test_directory_only_candidate_keeps_old_site_and_project_excluded(self):
        candidate = [self.site, self.stdlib, self.dynamic]
        self.assertNotIn(self.root/'MOCK_OLD_SITE', candidate)
        self.assertNotIn(self.root/'scripts', candidate)
        for path in (self.root/'MOCK_OLD_SITE/OTHER/METADATA', self.root/'scripts/OTHER.py', self.archive):
            with self.assertRaises(p.Refused):
                self.policy.path(path, os.O_RDONLY)


if __name__ == '__main__':
    context.g.old.guarded_test_main()
