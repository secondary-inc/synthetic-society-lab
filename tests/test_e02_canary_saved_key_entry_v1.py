"""Inert boundary tests: never read a real credential or call a live launcher."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'canary_saved_key_entry', ROOT / 'scripts/launch_e02_canary_with_saved_key_20261117.py')
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


class SavedKeyEntry(unittest.TestCase):
    def exercise(self, *, previous=None, admission_error=False, main_error=False,
                 credential_error=False):
        events = []
        def read(path, digest):
            events.append(('read', path.name, digest))
            return {'kind': path.name}
        def validate(*args):
            events.append('validate')
            if admission_error:
                raise ValueError('MOCK admission failure')
        def credential(root):
            events.append('credential')
            if credential_error:
                raise ValueError('MOCK private-file refusal')
            return SimpleNamespace(_value='AUTHORED_NOT_A_REAL_KEY_1234')
        def main():
            events.append('main')
            self.assertEqual(os.environ['OPENROUTER_API_KEY'], 'AUTHORED_NOT_A_REAL_KEY_1234')
            self.assertEqual(sys.argv[1:], ['--packet-sha256', 'a'*64, '--release-sha256', 'b'*64])
            if main_error:
                raise TimeoutError('MOCK interrupted launcher')
            return 'MOCK_DONE'
        launcher = SimpleNamespace(SCOPE=ROOT/'MOCK', read_exact=read, main=main)
        def load(path, digest):
            if path == entry.LAUNCHER:
                self.assertEqual(digest, entry.LAUNCHER_SHA)
                events.append('launcher_source')
                return launcher
            self.assertEqual((path, digest), (entry.KEY_READER, entry.KEY_READER_SHA))
            events.append('credential_reader_source')
            return SimpleNamespace(_credential=credential)
        from civiclab.e02 import wrapper_crossmodel_canary_v1_client as client
        with patch.dict(os.environ, {}, clear=True):
            if previous is not None:
                os.environ['OPENROUTER_API_KEY'] = previous
            argv = sys.argv
            with patch.object(entry, '_load_exact', side_effect=load), patch.object(client, 'validate_release', side_effect=validate):
                if admission_error or main_error or credential_error:
                    with self.assertRaises((ValueError, TimeoutError)):
                        entry.run('a'*64, 'b'*64)
                else:
                    self.assertEqual(entry.run('a'*64, 'b'*64), 'MOCK_DONE')
            self.assertIs(sys.argv, argv)
            self.assertEqual(os.environ.get('OPENROUTER_API_KEY'), previous)
        return events

    def test_admission_precedes_saved_key_and_single_main(self):
        self.assertEqual(self.exercise(), ['launcher_source',
            ('read', 'packet.json', 'a'*64), ('read', 'lead-release.json', 'b'*64),
            'validate', 'credential_reader_source', 'credential', 'main'])

    def test_failed_admission_never_loads_credential_reader(self):
        events = self.exercise(admission_error=True)
        self.assertNotIn('credential_reader_source', events)
        self.assertNotIn('main', events)

    def test_key_refusal_never_runs_main(self):
        self.assertNotIn('main', self.exercise(credential_error=True))

    def test_prior_environment_restored_after_success(self):
        self.assertEqual(self.exercise(previous='AUTHORED_PREVIOUS')[-1], 'main')

    def test_interruption_restores_environment_and_does_not_retry(self):
        self.assertEqual(self.exercise(previous='AUTHORED_PREVIOUS', main_error=True).count('main'), 1)

    def test_interruption_removes_temporary_environment(self):
        self.assertEqual(self.exercise(main_error=True).count('main'), 1)

    def test_changed_dependency_rejected_before_source_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d).resolve()/'probe.py'
            p.write_bytes(b'raise AssertionError("must not execute")\n')
            with self.assertRaisesRegex(RuntimeError, 'dependency changed'):
                entry._load_exact(p, '0'*64)

    def test_exact_dependency_compiles_verified_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d).resolve()/'probe.py'; raw = b'answer = 42\n'; p.write_bytes(raw)
            self.assertEqual(entry._load_exact(p, hashlib.sha256(raw).hexdigest()).answer, 42)

    def test_symlink_dependency_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve(); p = root/'probe.py'; raw=b'answer = 42\n'; p.write_bytes(raw)
            alias=root/'alias.py'; alias.symlink_to(p)
            with self.assertRaisesRegex(RuntimeError, 'aliased'):
                entry._load_exact(alias, hashlib.sha256(raw).hexdigest())

    def test_closed_HTTP_diagnostic_retained(self):
        from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
        error = _SafeTransportFailure('HTTP_STATUS', 'HTTP_STATUS', 402)
        self.assertEqual(entry.safe_failure(error)['diagnostic'],
            {'stage': 'HTTP_STATUS', 'category': 'HTTP_STATUS', 'http_status': 402, 'close_failed': False})

    def test_arbitrary_exception_text_not_disclosed(self):
        result = entry.safe_failure(OSError('AUTHORED_PRIVATE_TEXT_MUST_NOT_APPEAR'))
        self.assertEqual(result, {'status': 'STOPPED_NO_RETRY',
                                 'original_full80_analysis': 'NOT_RUN_INCOMPLETE'})

    def test_tampered_transport_fields_refused(self):
        from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
        error = _SafeTransportFailure('READ', 'TIMEOUT')
        error._fields = ('AUTHORED_PRIVATE_TEXT', 'TIMEOUT', None, False)
        self.assertNotIn('diagnostic', entry.safe_failure(error))

    def test_transport_subclass_cannot_supply_diagnostic(self):
        from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
        class UnsafeSubclass(_SafeTransportFailure):
            def diagnostic(self):
                raise AssertionError('must not be called')
        self.assertNotIn('diagnostic', entry.safe_failure(UnsafeSubclass('READ', 'TIMEOUT')))


if __name__ == '__main__':
    unittest.main()
