"""Authored exceptions only; no original qualification or runtime reprobe."""
import unittest
from unittest.mock import patch

from civiclab.e01.clerk2020_qualification_failure_context_v1 import (
    QUALIFICATION_FILE, failure_context,
)

ROOT = '/AUTHORED_REPO'


def authored_exception(module_name='AUTHORED_OPTIONAL_PACKAGE', path=None):
    # Deliberately simulated frame metadata; never the original run traceback.
    code = compile('def _runtime_inventory():\n    module = type("M", (), {})()\n'
                   '    module.__name__ = module_name\n    path = origin\n'
                   '    raise ValueError("AUTHORED_PRIVATE_ERROR")\n',
                   ROOT + '/' + QUALIFICATION_FILE, 'exec')
    scope = {'module_name': module_name,
             'origin': path or ROOT + '/.venv/lib/python3.12/site-packages/AUTHORED_EXTRA/__init__.py'}
    exec(code, scope)
    try:
        scope['_runtime_inventory']()
    except ValueError as exc:
        return exc


class FailureContextTests(unittest.TestCase):
    def test_simulated_frame_records_site_not_a_cause_claim(self):
        result = failure_context(authored_exception(), ROOT)
        self.assertEqual(len(result['qualified_frames']), 1)
        frame = result['qualified_frames'][0]
        self.assertEqual(frame['function'], '_runtime_inventory')
        self.assertEqual(frame['line'], 5)
        self.assertEqual(frame['last_iteration_module_not_proven_cause'], 'AUTHORED_OPTIONAL_PACKAGE')
        self.assertEqual(frame['last_iteration_origin_category_not_proven_cause'], 'VENV_OTHER_PACKAGE')
        self.assertFalse(result['permits_retry_or_policy_change'])

    def test_no_raw_message_full_path_or_non_code_name(self):
        result = failure_context(authored_exception('PRIVATE NAME VALUE'), ROOT)
        text = str(result)
        self.assertNotIn('AUTHORED_PRIVATE_ERROR', text)
        self.assertNotIn('PRIVATE NAME VALUE', text)
        self.assertNotIn('/AUTHORED_REPO/', text)

    def test_no_file_socket_probe_or_source_lookup(self):
        exc = authored_exception()
        def refuse(*args, **kwargs):
            raise AssertionError('NO_IO_PERMITTED')
        with patch('builtins.open', refuse), patch('os.stat', refuse), patch('socket.socket', refuse):
            self.assertEqual(failure_context(exc, ROOT)['extra_runtime_or_source_io'], 0)

    def test_original_saved_output_cannot_be_reconstructed(self):
        exc = ValueError('An exception object without a saved traceback')
        self.assertEqual(failure_context(exc, ROOT)['qualified_frames'], [])

    def test_other_source_frame_not_claimed(self):
        self.assertEqual(failure_context(authored_exception(), '/DIFFERENT_ROOT')['qualified_frames'], [])

    def test_source_category_does_not_open_source(self):
        result = failure_context(authored_exception(path=ROOT + '/data/raw/AUTHORED.pdf'), ROOT)
        self.assertEqual(result['qualified_frames'][0]['last_iteration_origin_category_not_proven_cause'],
                         'RESEARCH_DATA_PATH_REFUSED')

    def test_contract_refuses_non_exception(self):
        with self.assertRaises(ValueError):
            failure_context('raw text', ROOT)


if __name__ == '__main__':
    unittest.main()
