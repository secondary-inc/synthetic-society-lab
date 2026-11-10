"""Fresh closure checks use authored files/modules/readers and stub worker only."""
import base64
import copy
import json
from pathlib import Path
import re
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from civiclab.e01 import clerk2020_crypto_qualification_v1 as c
from civiclab.e01.clerk2020_m2_v1_1_contracts import Refused, canonical, decode, digest, sha
from test_clerk2020_native_qualification_v1 import FakeProcess, fake_response
from test_clerk2020_native_inventory_v1 import Page, Reader

REPO = Path(__file__).resolve().parents[1]
PUBLIC_OLD = json.loads((REPO / 'reports/clerk2020_native_qualification_v1_actual_stop_20261109.json').read_bytes())
PUBLIC_DIAG = json.loads((REPO / 'reports/clerk2020_runtime_diagnostic_v1_actual_20261110.json').read_bytes())


def prepare(root):
    refs = {}
    for name in c.CODE_PATHS:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = ((REPO / name).read_bytes() if name.endswith('clerk2020_native_qualification_v1.py')
               else ('# AUTHORED CODE ' + name).encode())
        p.write_bytes(raw)
        refs[name] = {'bytes': len(raw), 'sha256': sha(raw)}
    for r in (PUBLIC_OLD['OUTPUT_ARTIFACTS']['read_only_copied_control_records'] + PUBLIC_DIAG['OUTPUT_ARTIFACTS']):
        p = root / r['path']
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(r['raw_utf8'].encode())
    for name, r in c.PROFILE['static_files'].items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = ('AUTHORED STATIC FILE ' + name).encode()
        p.write_bytes(raw)
        assert sha(raw) == r['sha256']
    review = {'kind': 'CLERK2020_CRYPTO_QUALIFICATION_CODE_BINDING_V1',
              'status': 'PASS_EXACT_FRESH_GENERATED_QUALIFICATION_ONLY', 'reviewer_role': 'independent_auditor',
              'code_refs': refs, 'profile_sha256': c.PROFILE_SHA, 'ancestor_records': c.ANCESTOR_RECORDS,
              'past_limits': c.PAST_LIMITS, 'credit_restored': 0, 'limits': c.LIMITS, 'source_authority': False}
    r = canonical(review)
    packet = {'schema_version': 1, 'kind': c.KIND, 'phase_id': 'qualification-crypto-v1',
              'root_sha256': sha(str(root).encode()), 'code_refs': refs, 'profile_sha256': c.PROFILE_SHA,
              'ancestor_records': c.ANCESTOR_RECORDS, 'past_limits': c.PAST_LIMITS, 'credit_restored': 0,
              'limits': c.LIMITS, 'review_bytes_b64': base64.b64encode(r).decode(), 'review_sha256': sha(r)}
    raw = canonical(packet)
    return raw, sha(raw)


def child():
    obj = fake_response()
    obj.update({'dependency_profile_sha256': c.PROFILE_SHA, 'selected_crypto_provider': ['cryptography', '50.0.2'],
                'eager_pillow_version': '13.0.0', 'text_marker_pages_checked': 119,
                'native_backend_loaded_and_hash_matched': False})
    return obj


def exchange(proc, packet, start, out, err):
    out.extend(canonical(child()))
    return 0


def authored_reader(marker='AUTHORED DEMO FORMAT FIXTURE'):
    calls = []
    def factory(stream, **kwargs):
        raw = stream.getvalue()
        calls.append(kwargs)
        if b'not a PDF object graph' in raw:
            raise ValueError('AUTHORED_BAD_PDF')
        count = int(re.search(rb'/Count ([0-9]+)', raw).group(1))
        root = {'/Type': '/Catalog'}
        if b'/OpenAction' in raw:
            root['/OpenAction'] = 'AUTHORED_ACTIVE'
        return Reader([Page(marker) for _ in range(count)], root=root).factory(stream, **kwargs)
    return factory, calls


class CryptoQualificationTests(unittest.TestCase):
    def setUp(self):
        # All profiles/permissions in these unit fixtures are explicitly authored.
        # No installed library or private static-cache data is needed by tests.
        profile = copy.deepcopy(c.PROFILE)
        for name in profile['static_files']:
            raw = ('AUTHORED STATIC FILE ' + name).encode()
            profile['static_files'][name] = {'bytes': len(raw), 'sha256': sha(raw)}
        profile['native_backend']['bytes'] = len(b'AUTHORED_NOT_A_NATIVE_BINARY')
        profile['native_backend']['sha256'] = sha(b'AUTHORED_NOT_A_NATIVE_BINARY')
        self.patches = [patch.object(c, 'PROFILE', profile), patch.object(c, 'PROFILE_SHA', digest(profile))]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()

    def test_named_closure_only_not_any_venv(self):
        root = Path('/AUTHORED_REPO')
        base = Path('/AUTHORED_BASE')
        for package in ['cryptography', 'cffi', 'pycparser', 'PIL', 'pypdf']:
            self.assertTrue(c._origin_allowed(root / ('.venv/lib/python3.12/site-packages/' + package + '/module.py'), root, base))
        for package in ['unreviewed', 'cryptography_sneaky', 'Crypto', 'bcrypt']:
            self.assertFalse(c._origin_allowed(root / ('.venv/lib/python3.12/site-packages/' + package + '/module.py'), root, base))
        self.assertFalse(c._origin_allowed(root / 'data/raw/source.pdf', root, base))

    def test_exact_native_backend_not_arbitrary_extension(self):
        root = Path('/AUTHORED_REPO')
        self.assertTrue(c._origin_allowed(root / c.PROFILE['native_backend']['path'], root, Path('/BASE')))
        self.assertFalse(c._origin_allowed(root / '.venv/lib/python3.12/site-packages/other.so', root, Path('/BASE')))

    def test_closed_profile_release_and_zero_refund(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            p = c.validate_packet(root, raw, h)
            self.assertEqual(p['credit_restored'], 0)
            self.assertEqual(len(p['ancestor_records']), 6)
            self.assertEqual(p['past_limits']['qualification-v1']['reader_attempts'], 4)
            self.assertEqual(p['past_limits']['runtime-diagnostic-v1']['reader_attempts'], 0)

    def test_release_profile_ancestry_limits_and_hash_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            for key, value in [('profile_sha256', 'f' * 64), ('credit_restored', True),
                               ('phase_id', 'qualification-v1'), ('root_sha256', 'f' * 64)]:
                p = decode(raw)
                p[key] = value
                changed = canonical(p)
                with self.assertRaises(Refused):
                    c.validate_packet(root, changed, sha(changed))

    def test_no_source_authority_in_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            p = decode(raw)
            r = decode(base64.b64decode(p['review_bytes_b64']))
            r['source_authority'] = True
            b = canonical(r)
            p['review_bytes_b64'], p['review_sha256'] = base64.b64encode(b).decode(), sha(b)
            b = canonical(p)
            with self.assertRaises(Refused):
                c.validate_packet(root, b, sha(b))

    def test_generated_text_marker_checks_all_119_pages(self):
        factory, calls = authored_reader()
        self.assertEqual(c.generated_checks(factory), 119)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(x == {'strict': True} for x in calls))

    def test_generated_text_marker_allows_only_declared_terminal_newline(self):
        factory, _ = authored_reader('AUTHORED DEMO FORMAT FIXTURE\n')
        self.assertEqual(c.generated_checks(factory), 119)

    def test_generated_wrong_text_does_not_pass_page_count_only(self):
        factory, _ = authored_reader('AUTHORED_WRONG_TEXT')
        with self.assertRaises(Refused):
            c.generated_checks(factory)

    def test_child_cannot_silently_switch_provider_or_skip_text(self):
        self.assertEqual(c.validate_child(canonical(child())), child())
        for key, value in [('selected_crypto_provider', ['fallback', '0']),
                           ('eager_pillow_version', 'UNKNOWN'), ('text_marker_pages_checked', 0),
                           ('dependency_profile_sha256', 'f' * 64)]:
            obj = child()
            obj[key] = value
            with self.assertRaises(Refused):
                c.validate_child(canonical(obj))

    def test_child_native_hash_must_match_declared_record_if_loaded(self):
        obj = child()
        native = c.PROFILE['native_backend']
        obj['runtime_manifest'].append(['REPO/' + native['path'], native['bytes'], native['sha256']])
        obj['runtime_manifest_sha256'] = digest(obj['runtime_manifest'])
        obj['runtime_hash_bytes_observed'] += native['bytes']
        obj['runtime_hash_bytes_reserved'] += native['bytes'] + 1
        obj['native_backend_loaded_and_hash_matched'] = True
        c.validate_child(canonical(obj))
        obj['runtime_manifest'][-1][2] = 'f' * 64
        obj['runtime_manifest_sha256'] = digest(obj['runtime_manifest'])
        with self.assertRaises(Refused):
            c.validate_child(canonical(obj))

    def test_runtime_hashes_authored_package_and_backend_not_real_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            base = root / 'AUTHORED_BASE'
            exe = base / 'bin/python'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'AUTHORED_INTERPRETER_STUB')
            native = root / c.PROFILE['native_backend']['path']
            native.parent.mkdir(parents=True)
            native.write_bytes(b'AUTHORED_NOT_A_NATIVE_BINARY')
            module = ModuleType('_cffi_backend')
            module.__file__ = str(native)
            with (patch.object(c.sys, 'base_prefix', str(base)), patch.object(c.sys, 'executable', str(exe)),
                  patch.object(c.sys, 'modules', {'_cffi_backend': module})):
                rows, actual, reserved, seen = c.runtime_inventory(root)
            self.assertTrue(seen)
            self.assertEqual(len(rows), 2)
            self.assertEqual(reserved, actual + 2)

    def test_native_module_cannot_bind_unexpected_base_prefix_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            base = root / 'AUTHORED_BASE'
            exe = base / 'bin/python'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'AUTHORED_INTERPRETER')
            module = ModuleType('_cffi_backend')
            module.__file__ = str(base / 'wrong_backend.so')
            with (patch.object(c.sys, 'base_prefix', str(base)), patch.object(c.sys, 'executable', str(exe)),
                  patch.object(c.sys, 'modules', {'_cffi_backend': module})):
                with self.assertRaises(c.OriginRefused):
                    c.runtime_inventory(root)

    def test_loaded_native_backend_wrong_hash_is_specific_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            base = root / 'AUTHORED_BASE'
            exe = base / 'bin/python'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'AUTHORED_INTERPRETER')
            path = root / c.PROFILE['native_backend']['path']
            path.parent.mkdir(parents=True)
            path.write_bytes(b'AUTHORED_CHANGED_BINARY')
            module = ModuleType('_cffi_backend')
            module.__file__ = str(path)
            with (patch.object(c.sys, 'base_prefix', str(base)), patch.object(c.sys, 'executable', str(exe)),
                  patch.object(c.sys, 'modules', {'_cffi_backend': module})):
                with self.assertRaises(c.OriginRefused) as caught:
                    c.runtime_inventory(root)
            self.assertEqual(caught.exception.predicate, 'NATIVE_BACKEND_HASH')

    def test_source_or_crypto_package_cannot_come_from_unpinned_base_location(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            base = root / 'AUTHORED_BASE'
            exe = base / 'bin/python'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'AUTHORED_INTERPRETER')
            module = ModuleType('cryptography.__about__')
            module.__file__ = str(base / 'cryptography/__about__.py')
            with (patch.object(c.sys, 'base_prefix', str(base)), patch.object(c.sys, 'executable', str(exe)),
                  patch.object(c.sys, 'modules', {'cryptography.__about__': module})):
                with self.assertRaises(c.OriginRefused) as caught:
                    c.runtime_inventory(root)
            self.assertEqual(caught.exception.predicate, 'PROFILE_PACKAGE_ROOT')

    def test_network_and_spawn_events_stop(self):
        for event in ['socket.connect', 'subprocess.Popen', 'os.exec', 'os.fork']:
            with self.assertRaises(Refused):
                c._guard(event, ())

    def test_parent_reads_static_and_both_ancestors_after_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            old = {name: (root / name).read_bytes() for name in c.ANCESTOR_RECORDS}
            original = c.frozen._stable_hash
            def reserved(path, allowance):
                self.assertTrue((root / c.SCOPE / 'STARTED.json').exists())
                return original(path, allowance)
            with (patch.object(c.frozen, '_stable_hash', side_effect=reserved),
                  patch.object(c.subprocess, 'Popen', return_value=FakeProcess()),
                  patch.object(c.frozen, '_exchange', side_effect=exchange)):
                result = c.run_phase(root, raw, h)
            self.assertEqual(result['ancestor_bytes_reserved'], 8696)
            self.assertTrue(result['ancestor_unchanged'])
            self.assertEqual(result['source_reads'], 0)
            self.assertEqual(old, {name: (root / name).read_bytes() for name in c.ANCESTOR_RECORDS})

    def test_static_dependency_drift_blocks_before_import(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            path = next(iter(c.PROFILE['static_files']))
            (root / path).write_bytes(b'AUTHORED_DRIFT')
            with patch.object(c.subprocess, 'Popen') as launch:
                with self.assertRaises(c.frozen.QualificationStopped):
                    c.run_phase(root, raw, h)
                self.assertFalse(launch.called)
            with self.assertRaises(FileExistsError):
                c.run_phase(root, raw, h)

    def test_both_spent_ancestors_remain_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            target = next(name for name in c.ANCESTOR_RECORDS if '/runtime-diagnostic-v1/' in name)
            (root / target).write_bytes(b'AUTHORED_ANCESTOR_DRIFT')
            with patch.object(c.subprocess, 'Popen') as launch:
                with self.assertRaises(c.frozen.QualificationStopped):
                    c.run_phase(root, raw, h)
                self.assertFalse(launch.called)

    def test_partial_failure_no_retry_no_reader_credit_restoration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            def stop(proc, packet, start, out, err):
                out.extend(b'AUTHORED_PARTIAL')
                raise TimeoutError()
            with (patch.object(c.subprocess, 'Popen', return_value=FakeProcess()),
                  patch.object(c.frozen, '_exchange', side_effect=stop)):
                with self.assertRaises(c.frozen.QualificationStopped):
                    c.run_phase(root, raw, h)
            result = json.loads((root / c.SCOPE / 'OUTCOME.json').read_bytes())
            self.assertIsNone(result['reader_attempts_observed'])
            self.assertEqual(result['credit_restored'], 0)
            self.assertTrue(result['ancestor_limits_not_reduced'])
            self.assertEqual((root / c.SCOPE / 'partial_stdout.local.bin').read_bytes(), b'AUTHORED_PARTIAL')

    def test_no_genuine_pypdf_or_cryptography_import(self):
        self.assertNotIn('pypdf', sys.modules)
        self.assertNotIn('cryptography', sys.modules)


if __name__ == '__main__':
    unittest.main()
