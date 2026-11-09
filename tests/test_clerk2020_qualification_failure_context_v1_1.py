"""Exact-type remedy: authored traceback objects only; never a native reprobe."""
from types import ModuleType
import unittest
from unittest.mock import patch

from civiclab.e01.clerk2020_m2_v1_1_contracts import Refused
from civiclab.e01.clerk2020_qualification_failure_context_v1_1 import (
    QUALIFICATION_FILE, failure_context,
)

ROOT = '/AUTHORED_REPO'


def authored_exception(module=None, error_type=ValueError, path=None):
    code = compile('def _runtime_inventory():\n    module = supplied_module\n'
                   '    path = supplied_path\n    raise error_type("AUTHORED_PRIVATE")\n',
                   ROOT + '/' + QUALIFICATION_FILE, 'exec')
    scope = {'supplied_module': module, 'error_type': error_type,
             'supplied_path': path or ROOT + '/.venv/lib/python3.12/site-packages/AUTHORED_EXTRA/__init__.py'}
    exec(code, scope)
    try:
        scope['_runtime_inventory']()
    except BaseException as exc:
        return exc


class FailureContextSuccessorTests(unittest.TestCase):
    def test_exact_module_and_frozen_site(self):
        result = failure_context(authored_exception(ModuleType('AUTHORED_PACKAGE')), ROOT)
        frame = result['qualified_frames'][0]
        self.assertEqual(frame['line'], 4)
        self.assertEqual(frame['last_iteration_module_not_proven_cause'], 'AUTHORED_PACKAGE')
        self.assertFalse(result['permits_retry_or_policy_change'])

    def test_custom_dictionary_descriptor_is_never_invoked(self):
        calls = []
        class Trap:
            @property
            def __dict__(self):
                calls.append('SIDE_EFFECT')
                raise RuntimeError('AUTHORED_DESCRIPTOR')
        result = failure_context(authored_exception(Trap()), ROOT)
        self.assertEqual(calls, [])
        self.assertNotIn('last_iteration_module_not_proven_cause', result['qualified_frames'][0])

    def test_module_subclass_descriptor_is_never_invoked(self):
        calls = []
        class TrapModule(ModuleType):
            @property
            def __dict__(self):
                calls.append('SIDE_EFFECT')
                raise RuntimeError('AUTHORED_DESCRIPTOR')
        result = failure_context(authored_exception(TrapModule('AUTHORED_SUBCLASS')), ROOT)
        self.assertEqual(calls, [])
        self.assertNotIn('last_iteration_module_not_proven_cause', result['qualified_frames'][0])

    def test_custom_exception_traceback_descriptor_is_refused_without_access(self):
        calls = []
        class TrapError(ValueError):
            @property
            def __traceback__(self):
                calls.append('SIDE_EFFECT')
                raise RuntimeError('AUTHORED_DESCRIPTOR')
        exc = TrapError('AUTHORED_PRIVATE')
        with self.assertRaises(ValueError):
            failure_context(exc, ROOT)
        self.assertEqual(calls, [])

    def test_plain_exception_subclass_is_not_admitted(self):
        class ExtraError(ValueError):
            pass
        with self.assertRaises(ValueError):
            failure_context(authored_exception(error_type=ExtraError), ROOT)

    def test_exception_metaclass_hash_is_never_invoked(self):
        calls = []
        class Meta(type):
            def __hash__(cls):
                calls.append('HASH_SIDE_EFFECT')
                raise RuntimeError('AUTHORED_HASH')
        class TrapError(ValueError, metaclass=Meta):
            pass
        with self.assertRaises(ValueError):
            failure_context(TrapError('PRIVATE'), ROOT)
        self.assertEqual(calls, [])

    def test_unknown_path_metaclass_hash_is_never_invoked(self):
        calls = []
        class Meta(type):
            def __hash__(cls):
                calls.append('HASH_SIDE_EFFECT')
                raise RuntimeError('AUTHORED_HASH')
        class TrapPath(metaclass=Meta):
            pass
        result = failure_context(authored_exception(path=TrapPath()), ROOT)
        self.assertEqual(result['qualified_frames'][0]['last_iteration_origin_category_not_proven_cause'], 'UNKNOWN')
        self.assertEqual(calls, [])

    def test_known_refused_and_builtin_exception_types(self):
        for error_type in [Refused, ValueError, OSError, RuntimeError, MemoryError]:
            if error_type is Refused:
                try:
                    raise Refused()
                except Refused as exc:
                    result = failure_context(exc, ROOT)
            else:
                result = failure_context(authored_exception(error_type=error_type), ROOT)
            self.assertFalse(result['exception_message_retained'])

    def test_no_raw_message_or_full_path(self):
        result = failure_context(authored_exception(ModuleType('AUTHORED_PACKAGE')), ROOT)
        self.assertNotIn('AUTHORED_PRIVATE', str(result))
        self.assertNotIn('/AUTHORED_REPO/', str(result))

    def test_no_io_or_probe(self):
        exc = authored_exception(ModuleType('AUTHORED_PACKAGE'))
        def refuse(*args, **kwargs):
            raise AssertionError('NO_IO')
        with patch('builtins.open', refuse), patch('os.stat', refuse), patch('socket.socket', refuse):
            self.assertEqual(failure_context(exc, ROOT)['extra_runtime_or_source_io'], 0)

    def test_lost_original_traceback_remains_unknown(self):
        self.assertEqual(failure_context(ValueError(), ROOT)['qualified_frames'], [])

    def test_invalid_module_name_is_omitted(self):
        result = failure_context(authored_exception(ModuleType('NOT A CODE NAME')), ROOT)
        self.assertNotIn('last_iteration_module_not_proven_cause', result['qualified_frames'][0])

    def test_source_category_without_source_access(self):
        result = failure_context(authored_exception(path=ROOT + '/data/raw/AUTHORED.pdf'), ROOT)
        self.assertEqual(result['qualified_frames'][0]['last_iteration_origin_category_not_proven_cause'],
                         'RESEARCH_DATA_PATH_REFUSED')


if __name__ == '__main__':
    unittest.main()
