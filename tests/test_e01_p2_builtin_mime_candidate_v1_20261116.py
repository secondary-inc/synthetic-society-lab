"""Isolated stdlib MIME fixtures; no pip or actual system MIME files read."""
import builtins
import importlib.util
import mimetypes
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

c = load('builtin_mime_proposal', ROOT/'scripts/e01_p2_builtin_mime_candidate_v1_20261116.py')
t = load('frozen_authored_guard_context', ROOT/'tests/test_e01_pypdf701_install_v1_3.py')


class BuiltinMimeCandidateTests(unittest.TestCase):
    def setUp(self):
        # Separate module state, real stdlib implementation for this runtime.
        # Loading the module defines tables; it does not call init().
        self.module = load('authored_isolated_stdlib_mimetypes', Path(mimetypes.__file__))
        self.assertIs(self.module.inited, False)
        self.tmp = tempfile.TemporaryDirectory(prefix='e01-p2-mime-MOCK-')
        self.addCleanup(self.tmp.cleanup)
        self.fake_file = Path(self.tmp.name).resolve()/'MOCK_MIME_TYPES'
        self.fake_file.write_text('text/html whl\napplication/x-mock txt\n')
        self.module.knownfiles = [str(self.fake_file)]

    def test_empty_files_alone_still_attempts_knownfile_read(self):
        attempted = []
        original = builtins.open
        def opening(path, *args, **kwargs):
            if Path(path) == self.fake_file:
                attempted.append(str(path))
                raise AssertionError('AUTHORED_MIME_FILE_READ_DENIED')
            return original(path, *args, **kwargs)
        with patch.object(builtins, 'open', opening):
            with self.assertRaisesRegex(AssertionError, 'AUTHORED_MIME_FILE_READ_DENIED'):
                self.module.init(files=[])
        self.assertEqual(attempted, [str(self.fake_file)])

    def test_public_knownfiles_clear_and_empty_init_need_no_file_open(self):
        def no_open(*args, **kwargs):
            raise AssertionError('MIME_CONFIGURATION_MUST_NOT_OPEN_FILES')
        with patch.object(builtins, 'open', no_open):
            receipt = c.initialize_builtin_mime_types(self.module)
            self.assertEqual(self.module.guess_type('file:///MOCK/data.txt'), ('text/plain', None))
            self.assertEqual(self.module.guess_type('file:///MOCK/index.html', strict=False), ('text/html', None))
        self.assertEqual(receipt, {'mode': 'STDLIB_BUILTIN_TYPES_ONLY_DARWIN',
                                  'knownfiles': [], 'explicit_files': [], 'initialized': True})

    def test_all_five_wheel_names_remain_non_html_without_io(self):
        with patch.object(builtins, 'open', side_effect=AssertionError('NO_MIME_FILE_READ')):
            c.initialize_builtin_mime_types(self.module)
            filenames = ['pypdf-7.0.1-py3-none-any.whl',
                         'cffi-2.1.1-cp312-cp312-macosx_11_0_arm64.whl',
                         'cryptography-50.0.2-cp311-abi3-macosx_10_9_universal2.whl',
                         'pillow-13.0.0-cp312-cp312-macosx_11_0_arm64.whl',
                         'pycparser-3.12-py3-none-any.whl']
            for name in filenames:
                with self.subTest(name=name):
                    self.assertNotEqual(self.module.guess_type('file:///MOCK/'+name, strict=False)[0], 'text/html')

    def test_already_initialized_module_refuses_without_state_reset(self):
        c.initialize_builtin_mime_types(self.module)
        before = self.module.knownfiles
        with self.assertRaisesRegex(ValueError, 'MIME_ALREADY_INITIALIZED'):
            c.initialize_builtin_mime_types(self.module)
        self.assertIs(self.module.knownfiles, before)

    def test_initialization_exception_propagates_without_retry_or_fallback(self):
        with patch.object(self.module, 'init', side_effect=RuntimeError('AUTHORED_INIT_STOP')) as init:
            with self.assertRaisesRegex(RuntimeError, 'AUTHORED_INIT_STOP'):
                c.initialize_builtin_mime_types(self.module)
        init.assert_called_once_with(files=[])

    def test_unexpected_knownfiles_schema_refuses(self):
        self.module.knownfiles = 'MOCK_NOT_A_LIST'
        with self.assertRaisesRegex(ValueError, 'MIME_KNOWNFILES_SCHEMA'):
            c.initialize_builtin_mime_types(self.module)
        self.assertIs(self.module.inited, False)


if __name__ == '__main__':
    t.g.old.guarded_test_main()
