"""Isolated real stdlib regression; only authored temporary MIME files read."""
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

c = load('builtin_mime_proposal_v2', ROOT/'scripts/e01_p2_builtin_mime_candidate_v2_20261116.py')
t = load('frozen_authored_guard_context_v2', ROOT/'tests/test_e01_pypdf701_install_v1_3.py')


class BuiltinMimeRebuildTests(unittest.TestCase):
    def setUp(self):
        self.module = load('authored_isolated_stdlib_mimetypes_v2', Path(mimetypes.__file__))
        self.assertIs(self.module.inited, False)
        self.tmp = tempfile.TemporaryDirectory(prefix='e01-p2-mime-v2-MOCK-')
        self.addCleanup(self.tmp.cleanup)
        self.fake_file = Path(self.tmp.name).resolve()/'MOCK_MIME_TYPES'
        self.fake_file.write_text('text/html whl\napplication/x-mock txt\n')
        self.module.knownfiles = [str(self.fake_file)]

    def assert_builtin_types(self):
        self.assertEqual(self.module.guess_type('file:///MOCK/index.html', strict=False), ('text/html', None))
        self.assertEqual(self.module.guess_type('file:///MOCK/readme.txt'), ('text/plain', None))
        self.assertEqual(self.module.guess_type('file:///MOCK/unknown.MOCK_UNKNOWN'), (None, None))
        for name in ('pypdf-7.0.1-py3-none-any.whl',
                     'cffi-2.1.1-cp312-cp312-macosx_11_0_arm64.whl',
                     'cryptography-50.0.2-cp311-abi3-macosx_10_9_universal2.whl',
                     'pillow-13.0.0-cp312-cp312-macosx_11_0_arm64.whl',
                     'pycparser-3.12-py3-none-any.whl'):
            with self.subTest(name=name):
                self.assertNotEqual(self.module.guess_type('file:///MOCK/'+name, strict=False)[0], 'text/html')

    def populate_authored_mapping(self):
        # Deliberately read only this authored temp file to model prior state.
        self.module.init(files=[])
        self.assertEqual(self.module.guess_type('file:///MOCK/a.whl', strict=False)[0], 'text/html')
        self.assertEqual(self.module.guess_type('file:///MOCK/a.txt')[0], 'application/x-mock')

    def test_fresh_rebuild_and_classification_need_zero_file_opens(self):
        with patch.object(builtins, 'open', side_effect=AssertionError('NO_MIME_FILE_OPENS')):
            receipt = c.initialize_builtin_mime_types(self.module)
            self.assert_builtin_types()
        self.assertEqual(receipt, {'mode': 'STDLIB_BUILTIN_TYPES_ONLY_DARWIN',
                                  'knownfiles': [], 'init_files': None, 'initialized': True})

    def test_prepopulated_rebuild_removes_machine_specific_mappings_without_io(self):
        self.populate_authored_mapping()
        with patch.object(builtins, 'open', side_effect=AssertionError('NO_MIME_FILE_OPENS')):
            c.initialize_builtin_mime_types(self.module)
            self.assert_builtin_types()

    def test_empty_list_after_clearing_knownfiles_retains_prepopulated_database(self):
        self.populate_authored_mapping()
        self.module.knownfiles = []
        with patch.object(builtins, 'open', side_effect=AssertionError('NO_MIME_FILE_OPENS')):
            self.module.init(files=[])
        self.assertEqual(self.module.guess_type('file:///MOCK/a.whl', strict=False)[0], 'text/html')
        self.assertEqual(self.module.guess_type('file:///MOCK/a.txt')[0], 'application/x-mock')

    def test_fresh_empty_list_still_attempts_knownfile_open(self):
        attempted = []
        original = builtins.open
        def opening(path, *args, **kwargs):
            if Path(path) == self.fake_file:
                attempted.append(str(path))
                raise AssertionError('AUTHORED_KNOWNFILE_READ_DENIED')
            return original(path, *args, **kwargs)
        with patch.object(builtins, 'open', opening):
            with self.assertRaisesRegex(AssertionError, 'AUTHORED_KNOWNFILE_READ_DENIED'):
                self.module.init(files=[])
        self.assertEqual(attempted, [str(self.fake_file)])

    def test_rebuild_is_repeatable_and_resets_public_add_type_changes(self):
        c.initialize_builtin_mime_types(self.module)
        self.module.add_type('application/x-mock', '.html')
        self.module.add_type('text/html', '.whl')
        with patch.object(builtins, 'open', side_effect=AssertionError('NO_MIME_FILE_OPENS')):
            c.initialize_builtin_mime_types(self.module)
            self.assert_builtin_types()

    def test_init_failure_propagates_once_without_fallback(self):
        with patch.object(self.module, 'init', side_effect=RuntimeError('AUTHORED_INIT_STOP')) as init:
            with self.assertRaisesRegex(RuntimeError, 'AUTHORED_INIT_STOP'):
                c.initialize_builtin_mime_types(self.module)
        init.assert_called_once_with(files=None)

    def test_unexpected_state_refuses_before_init(self):
        for attr, value in (('inited', 'MOCK_INVALID'), ('knownfiles', 'MOCK_INVALID')):
            with patch.object(self.module, attr, value), patch.object(self.module, 'init') as init:
                with self.assertRaisesRegex(ValueError, 'MIME_STATE_SCHEMA'):
                    c.initialize_builtin_mime_types(self.module)
                init.assert_not_called()

    def test_no_private_mime_database_or_guard_mutation_in_candidate(self):
        import ast
        tree = ast.parse((ROOT/'scripts/e01_p2_builtin_mime_candidate_v2_20261116.py').read_bytes())
        assigned = [node.targets[0] for node in ast.walk(tree) if isinstance(node, ast.Assign)]
        self.assertEqual([ast.unparse(node) for node in assigned], ['module.knownfiles'])
        self.assertFalse(any(isinstance(node, ast.Attribute) and node.attr.startswith('_') for node in ast.walk(tree)))


if __name__ == '__main__':
    t.g.old.guarded_test_main()
