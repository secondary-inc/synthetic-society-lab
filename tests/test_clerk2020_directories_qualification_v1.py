"""Fresh closure checks use authored files/modules/readers and stub worker only."""
import base64
import ast
import subprocess
import copy
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from io import BytesIO
import builtins
import unittest
from unittest.mock import patch

from civiclab.e01 import clerk2020_directories_qualification_v1 as c
from civiclab.e01.clerk2020_m2_v1_1_contracts import Refused, canonical, decode, digest, sha
from test_clerk2020_native_qualification_v1 import FakeProcess, fake_response
from test_clerk2020_native_inventory_v1 import Page, Reader

REPO = Path(__file__).resolve().parents[1]
PUBLIC_OLD = json.loads((REPO / 'reports/clerk2020_native_qualification_v1_actual_stop_20261109.json').read_bytes())
PUBLIC_WARMUP = json.loads((REPO / 'reports/clerk2020_warmup_qualification_v1_actual_stop_20261110.json').read_bytes())
PUBLIC_GUARD = json.loads((REPO / 'reports/clerk2020_guard_qualification_v1_actual_stop_20261110.json').read_bytes())
PUBLIC_CRYPTO = json.loads((REPO / 'reports/clerk2020_crypto_qualification_v1_actual_stop_20261110.json').read_bytes())
PUBLIC_DIAG = json.loads((REPO / 'reports/clerk2020_runtime_diagnostic_v1_actual_20261110.json').read_bytes())


def prepare(root):
    refs = {}
    for name in c.CODE_PATHS:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = ((REPO / name).read_bytes() if name.endswith('clerk2020_native_qualification_v1.py')
               or name.endswith('clerk2020_crypto_qualification_v1.py')
               or name.endswith('clerk2020_generated_guard_inventory_v1.py')
               or name.endswith('clerk2020_guard_qualification_v1.py')
               or name.endswith('clerk2020_warmup_qualification_v1.py')
               else ('# AUTHORED CODE ' + name).encode())
        p.write_bytes(raw)
        refs[name] = {'bytes': len(raw), 'sha256': sha(raw)}
    for r in (PUBLIC_OLD['OUTPUT_ARTIFACTS']['read_only_copied_control_records'] + PUBLIC_DIAG['OUTPUT_ARTIFACTS'] + PUBLIC_CRYPTO['OUTPUT_ARTIFACTS'] + PUBLIC_GUARD['OUTPUT_ARTIFACTS'] + PUBLIC_WARMUP['OUTPUT_ARTIFACTS']):
        p = root / r['path']
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(r['raw_utf8'].encode())
    for name, r in c.PROFILE['static_files'].items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = ('AUTHORED STATIC FILE ' + name).encode()
        p.write_bytes(raw)
        assert sha(raw) == r['sha256']
    review = {'kind': 'CLERK2020_DIRECTORIES_QUALIFICATION_CODE_BINDING_V1',
              'status': 'PASS_EXACT_FRESH_GENERATED_QUALIFICATION_ONLY', 'reviewer_role': 'independent_auditor',
              'code_refs': refs, 'profile_sha256': c.PROFILE_SHA, 'ancestor_records': c.ANCESTOR_RECORDS,
              'past_limits': c.PAST_LIMITS, 'credit_restored': 0, 'limits': c.LIMITS, 'source_authority': False}
    r = canonical(review)
    packet = {'schema_version': 1, 'kind': c.KIND, 'phase_id': 'qualification-directories-v1',
              'root_sha256': sha(str(root).encode()), 'code_refs': refs, 'profile_sha256': c.PROFILE_SHA,
              'ancestor_records': c.ANCESTOR_RECORDS, 'past_limits': c.PAST_LIMITS, 'credit_restored': 0,
              'limits': c.LIMITS, 'review_bytes_b64': base64.b64encode(r).decode(), 'review_sha256': sha(r)}
    raw = canonical(packet)
    return raw, sha(raw)


def child():
    obj = fake_response()
    obj.update({'dependency_profile_sha256': c.PROFILE_SHA, 'selected_crypto_provider': ['cryptography', '50.0.2'],
                'eager_pillow_version': '13.0.0', 'text_marker_pages_checked': 119,
                'native_backend_loaded_and_hash_matched': False,
                'guard_first_event': None,
                'preloaded_module_origin': 'REPO/.venv/lib/python3.12/site-packages/pypdf/_codecs/core_font_metrics.py',
                'negative_failure_stages': ['STRUCTURE', 'READER_CONSTRUCTION']})
    obj['runtime_manifest'].append([obj['preloaded_module_origin'], 1, sha(b'X')])
    obj['runtime_manifest_sha256'] = digest(obj['runtime_manifest'])
    obj['runtime_hash_bytes_observed'] += 1
    obj['runtime_hash_bytes_reserved'] += 2
    obj['warmup'] = {'reader_attempts': 4, 'page_extractions': 119,
        'file_open_events': 0, 'read_bytes_reserved': 0, 'directory_events': 0, 'directory_labels_observed': [],
        'import_events': 0, 'read_files': 0, 'missing_bytecode_probes': 0, 'first_refusal': None,
        'hash_open_events': 4, 'hash_read_bytes_reserved': obj['runtime_hash_bytes_reserved'],
        'hash_files_opened': 2, 'hash_descriptor_events': 2}
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


class DirectoryQualificationTests(unittest.TestCase):
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
            self.assertEqual(len(p['ancestor_records']), 15)
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
        self.assertEqual(c.generated_checks(factory, c.guarded.GeneratedTelemetry(), {}), 119)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(x == {'strict': True} for x in calls))

    def test_generated_text_marker_allows_only_declared_terminal_newline(self):
        factory, _ = authored_reader('AUTHORED DEMO FORMAT FIXTURE\n')
        self.assertEqual(c.generated_checks(factory, c.guarded.GeneratedTelemetry(), {}), 119)

    def test_generated_wrong_text_does_not_pass_page_count_only(self):
        factory, _ = authored_reader('AUTHORED_WRONG_TEXT')
        with self.assertRaises(Refused):
            c.generated_checks(factory, c.guarded.GeneratedTelemetry(), {})

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
        obj['warmup'].update(hash_files_opened=3, hash_descriptor_events=3, hash_open_events=6,
            hash_read_bytes_reserved=obj['runtime_hash_bytes_reserved'])
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
            self.assertEqual(result['ancestor_bytes_reserved'], 23286)
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

    def test_latest_scope_limits_and_all_fifteen_exact_records_preserved(self):
        latest = next(r for r in PUBLIC_WARMUP['OUTPUT_ARTIFACTS'] if r['path'].endswith('/STARTED.json'))
        self.assertEqual(c.PAST_LIMITS['qualification-warmup-v1'], latest['decoded']['limits'])
        self.assertEqual(len(c.ANCESTOR_RECORDS), 15)
        self.assertEqual(c.LIMITS['ancestor_read_bytes_reserved'],
                         2 * sum(r['bytes'] + 1 for r in c.ANCESTOR_RECORDS.values()))
        self.assertEqual(c.LIMITS['ancestor_record_reads'], 30)
        self.assertEqual(c.LIMITS['reader_attempts'], 8)
        self.assertEqual(c.LIMITS['page_extractions'], 238)

    def test_latest_ancestor_drift_stops_before_process(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            target = next(name for name in c.ANCESTOR_RECORDS if '/qualification-warmup-v1/' in name)
            (root / target).write_bytes(b'AUTHORED_DRIFT')
            with patch.object(c.subprocess, 'Popen') as launch:
                with self.assertRaises(c.frozen.QualificationStopped):
                    c.run_phase(root, raw, h)
                launch.assert_not_called()

    def test_guard_refusal_cannot_pass_malformed_negative(self):
        telemetry = c.guarded.GeneratedTelemetry()
        factory, calls = authored_reader()
        def blocked(stream, **kwargs):
            if b'not a PDF object graph' in stream.getvalue():
                telemetry.guard('import', ('SECRET_NAME',))
            return factory(stream, **kwargs)
        progress = {}
        with self.assertRaises(Refused):
            c.generated_checks(blocked, telemetry, progress)
        self.assertEqual(progress['reader_attempts_entered'], 4)
        self.assertEqual(progress['text_marker_pages_checked'], 119)
        self.assertEqual(progress['negative_failure_stages'], ['STRUCTURE'])
        self.assertEqual(telemetry.first_guard, {'event': 'import'})

    def test_swallowed_guard_refusal_still_fails_negative(self):
        telemetry = c.guarded.GeneratedTelemetry()
        factory, calls = authored_reader()
        def swallowed(stream, **kwargs):
            if b'not a PDF object graph' in stream.getvalue():
                try: telemetry.guard('open', ('SECRET_PATH',))
                except c.frozen.QualificationStopped: pass
            return factory(stream, **kwargs)
        with self.assertRaises(Refused):
            c.generated_checks(swallowed, telemetry, {})
        self.assertEqual(telemetry.first_guard, {'event': 'open'})

    def test_child_requires_preloaded_origin_in_manifest_and_no_guard(self):
        for key, value in [('preloaded_module_origin', 'REPO/arbitrary.py'),
                           ('guard_first_event', {'event': 'import'}),
                           ('negative_failure_stages', ['READER_CONSTRUCTION', 'READER_CONSTRUCTION'])]:
            obj = child(); obj[key] = value
            with self.assertRaises(Refused): c.validate_child(canonical(obj))
        obj = child()
        obj['runtime_manifest'] = obj['runtime_manifest'][:-1]
        obj['runtime_manifest_sha256'] = digest(obj['runtime_manifest'])
        with self.assertRaises(Refused): c.validate_child(canonical(obj))

    def test_worker_failure_context_retains_exact_own_function_line_only(self):
        factory, _ = authored_reader('WRONG_TEXT_SECRET')
        try:
            c.generated_checks(factory, c.guarded.GeneratedTelemetry(), {})
        except Refused as exc:
            context = c.worker_failure_context(exc)
        self.assertEqual(context['type'], 'Refused')
        self.assertTrue(any(r['function'] == 'generated_checks' for r in context['frames']))
        self.assertTrue(any(r['function'] == 'require' for r in context['frames']))
        self.assertNotIn('SECRET', json.dumps(context))
        self.assertFalse(context['traceback_truncated'])

    def test_mock_worker_orders_preload_inventory_and_guard_without_native_import(self):
        root = Path('/AUTHORED_REPO')
        reader, _ = authored_reader()
        pypdf = ModuleType('pypdf'); pypdf.__version__ = '6.10.0'; pypdf.PdfReader = reader
        pillow = ModuleType('PIL'); pillow.__version__ = '13.0.0'
        provider = ModuleType('pypdf._crypt_providers'); provider.crypt_provider = ('cryptography', '50.0.2')
        codecs = ModuleType('pypdf._codecs')
        metrics = ModuleType('pypdf._codecs.core_font_metrics')
        metrics.__file__ = str(root / '.venv/lib/python3.12/site-packages/pypdf/_codecs/core_font_metrics.py')
        codecs.core_font_metrics = metrics
        order = []
        original_import = builtins.__import__
        modules = {'pypdf': pypdf, 'PIL': pillow,
                   'pypdf._crypt_providers': provider, 'pypdf._codecs': codecs}
        def importing(name, *args, **kwargs):
            if name == 'pypdf._codecs': order.append('PRELOAD')
            return modules[name] if name in modules else original_import(name, *args, **kwargs)
        def inventory(root, warmup):
            self.assertEqual(order, ['WARMUP'])
            self.assertEqual(warmup.phase, 'HASH')
            order.append('INVENTORY')
            warmup.hash_candidates = {Path('/AUTHORED_BASE/one'): (1,), Path('/AUTHORED_BASE/two'): (2,)}
            warmup.hash_seen = set(warmup.hash_candidates)
            warmup.hash_opens = 4; warmup.hash_fd_opens = 2
            obj = child()
            warmup.hash_reserved = obj['runtime_hash_bytes_reserved']
            return obj['runtime_manifest'], obj['runtime_hash_bytes_observed'], obj['runtime_hash_bytes_reserved'], False
        def hook(fn):
            if type(getattr(fn, '__self__', None)) is c.guarded.GeneratedTelemetry:
                order.append('PARSE_GUARD')
        generated = c.generated_checks
        def generated_checked(*args):
            order.append('WARMUP' if not order else 'STRICT')
            return generated(*args)
        output = BytesIO()
        with (patch('builtins.__import__', side_effect=importing),
              patch.object(c.sys, 'stdin', SimpleNamespace(buffer=BytesIO(canonical({'profile_sha256': c.PROFILE_SHA})))),
              patch.object(c.sys, 'stdout', SimpleNamespace(buffer=output)),
              patch.object(c.sys, 'version', '3.12.14 AUTHORED'),
              patch.object(c.sys, 'platform', 'darwin'),
              patch.object(c.sys, 'path', list(c.sys.path)),
              patch.object(c.sys, 'addaudithook', side_effect=hook),
              patch.dict(c.sys.modules, {'pypdf._codecs.core_font_metrics': metrics}),
              patch.object(c, 'generated_checks', side_effect=generated_checked),
              patch.object(c.os, 'uname', return_value=SimpleNamespace(machine='arm64')),
              patch('resource.setrlimit'), patch.object(c, 'runtime_inventory', side_effect=inventory)):
            c._worker(root)
        self.assertEqual(order, ['WARMUP', 'INVENTORY', 'PARSE_GUARD', 'STRICT'])
        obj = c.validate_child(output.getvalue())
        self.assertEqual(obj['text_marker_pages_checked'], 119)
        self.assertIsNone(obj['guard_first_event'])

    def make_guard(self, root):
        base = root / 'AUTHORED_BASE'
        base.mkdir(exist_ok=True)
        with patch.object(c.sys, 'base_prefix', str(base)):
            return c.WarmupGuard(root)

    def test_readonly_declared_file_is_counted_and_union_hashed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            guard = self.make_guard(root)
            data = root / '.venv/lib/python3.12/site-packages/pypdf/AUTHORED.txt'
            data.parent.mkdir(parents=True); data.write_bytes(b'AUTHORED_RESOURCE_NOT_A_MODULE')
            guard.transition('WARMUP')
            guard.guard('open', (str(data), 'r', os.O_RDONLY))
            self.assertEqual(guard.read_reserved, data.stat().st_size + 1)
            self.assertEqual(set(guard.read_files), {data})
            exe = guard.base / 'python'; exe.write_bytes(b'AUTHORED_INTERPRETER')
            guard.transition('HASH')
            with patch.object(c.sys, 'base_prefix', str(guard.base)), patch.object(c.sys, 'executable', str(exe)), patch.object(c.sys, 'modules', {}):
                rows, actual, reserved, _ = c.runtime_inventory(root, guard)
            self.assertTrue(any('AUTHORED.txt' in r[0] for r in rows))
            self.assertEqual(set(guard.hash_candidates), {data, exe})
            self.assertEqual(reserved, actual + 2)
            # No actual audit hook was registered in this authored test.
            self.assertFalse(guard.hash_seen)

    def test_guard_denies_source_env_unlisted_file_and_unknown_fd(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            values = [str(root/'data/raw/source.pdf'), str(root/'.env'),
                str(root/'src/private.py'), str(root/'.venv/lib/python3.12/site-packages/unknown/x.py'), 7, b'PATH']
            for value in values:
                guard = self.make_guard(root)
                with self.assertRaises(c.frozen.QualificationStopped):
                    guard.guard('open', (value, 'r', os.O_RDONLY))
                self.assertIsNotNone(guard.first_refusal)
                self.assertNotIn('source.pdf', json.dumps(guard.first_refusal))

    def test_guard_denies_all_write_modes_and_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            for mode, flags in [('w',os.O_WRONLY),('a',os.O_APPEND),('r+',os.O_RDWR),
                    ('r',os.O_CREAT),('r',os.O_TRUNC),('r',True),('UNKNOWN',0)]:
                guard = self.make_guard(root)
                with self.assertRaises(c.frozen.QualificationStopped):
                    guard.guard('open', (str(guard.base/'file'), mode, flags))
                self.assertEqual(guard.first_refusal['predicate'], 'WRITE_OR_UNKNOWN_OPEN_REFUSED')

    def test_symlink_and_dotdot_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); guard = self.make_guard(root)
            target = guard.base/'target';target.write_bytes(b'AUTHORED')
            alias = guard.base/'alias';alias.symlink_to(target)
            for value in [str(alias), str(guard.base/'..'/'AUTHORED_BASE'/'target')]:
                state=self.make_guard(root)
                with self.assertRaises(c.frozen.QualificationStopped):
                    state.guard('open', (value, 'r', 0))

    def test_imports_are_closed_namespace_and_origin(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve(); guard=self.make_guard(root)
            for name in ['encodings.cp1252','pypdf._codecs.core_font_metrics',
                         'cryptography.x', 'civiclab.e01.clerk2020_generated_guard_inventory_v1',
                         'test_clerk2020_native_inventory_v1']:
                guard.guard('import', (name,None))
            self.assertEqual(guard.imports, 5)
            for args in [('unreviewed.library', None), ('pypdf.x',str(root/'data/raw/x.py')),
                         ('civiclab.e01.UNLISTED',None), ('bad name',None), (object(),None)]:
                state=self.make_guard(root)
                with self.assertRaises(c.frozen.QualificationStopped):state.guard('import',args)

    def test_finite_open_import_directory_and_byte_caps(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve(); data=root/'AUTHORED_BASE/file'
            guard=self.make_guard(root);data.write_bytes(b'1234')
            for counter,event,args,limit in [
                ('opens','open',(str(data),'r',0),'warmup_file_open_attempts'),
                ('imports','import',('encodings.cp1252',None),'warmup_import_events'),
                ('directories','os.listdir',(str(guard.base),),'warmup_directory_events')]:
                state=self.make_guard(root);setattr(state,counter,c.LIMITS[limit])
                with self.assertRaises(c.frozen.QualificationStopped):state.guard(event,args)
            guard.read_reserved=c.LIMITS['warmup_read_bytes_reserved']-4
            with self.assertRaises(c.frozen.QualificationStopped):guard.guard('open',(str(data),'r',0))
            self.assertEqual(guard.first_refusal['predicate'],'READ_BYTE_LIMIT')

    def test_network_process_dlopen_and_chdir_refused_in_every_phase(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            for phase in ['BOOTSTRAP','WARMUP','HASH','STRICT']:
                for event in ['socket.connect','os.execve','subprocess.Popen','ctypes.dlopen','os.chdir']:
                    state=self.make_guard(root);state.phase=phase
                    with self.assertRaises(c.frozen.QualificationStopped):state.guard(event,())
                    self.assertEqual(state.first_refusal['phase'],phase)

    def test_hash_only_exact_once_admitted_read_and_matching_descriptor(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            data=guard.base/'data';data.write_bytes(b'AUTHORED')
            guard.transition('WARMUP');guard.transition('HASH');guard.admit_hash({data})
            guard.guard('open',(str(data),'r',0))
            fd=os.open(data,os.O_RDONLY)
            try:guard.guard('open',(fd,'r',0))
            finally:os.close(fd)
            self.assertEqual(guard.hash_fd_opens,1)
            self.assertEqual(guard.hash_opens,2)
            guard.transition('STRICT')
            self.assertEqual(guard.phase,'STRICT')
            with self.assertRaises(c.frozen.QualificationStopped):guard.transition('WARMUP')

    def test_hash_unadmitted_path_fd_reopen_or_import_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            for event,kind in [('open','unknown'),('open','fd'),('open','reopen'),('import','import'),('os.listdir','directory')]:
                guard=self.make_guard(root);data=guard.base/'one';data.write_bytes(b'ONE')
                other=guard.base/'two';other.write_bytes(b'TWO')
                guard.transition('WARMUP');guard.transition('HASH');guard.admit_hash({data})
                fd=None
                if kind=='unknown':args=(str(other),'r',0)
                elif kind=='fd':fd=os.open(other,os.O_RDONLY);args=(fd,'r',0)
                elif kind=='reopen':guard.guard('open',(str(data),'r',0));args=(str(data),'r',0)
                elif kind=='import':args=('encodings.cp1252',None)
                else:args=(str(guard.base),)
                try:
                    with self.assertRaises(c.frozen.QualificationStopped):guard.guard(event,args)
                finally:
                    if fd is not None:os.close(fd)

    def test_incomplete_or_drifted_warmup_capture_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            data=guard.base/'one';data.write_bytes(b'ONE')
            other=guard.base/'two';other.write_bytes(b'TWO')
            guard.guard('open',(str(data),'r',0))
            guard.transition('WARMUP');guard.transition('HASH')
            with self.assertRaises(Refused):guard.admit_hash({other})
            data.write_bytes(b'DRIFTED')
            with self.assertRaises(Refused):guard.admit_hash({data})

    def test_one_way_phases_and_refusal_cannot_be_erased_by_transition(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            for target in ['HASH','STRICT','BOOTSTRAP']:
                guard=self.make_guard(root)
                with self.assertRaises(c.frozen.QualificationStopped):guard.transition(target)
            guard=self.make_guard(root)
            with self.assertRaises(c.frozen.QualificationStopped):guard.guard('socket.connect',())
            first=guard.first_refusal.copy()
            with self.assertRaises(c.frozen.QualificationStopped):guard.transition('WARMUP')
            self.assertEqual(guard.first_refusal,first)

    def test_child_rejects_incomplete_or_exhausted_warmup_and_hash_capture(self):
        for key,value in [('reader_attempts',3),('page_extractions',118),('first_refusal',{'event':'open'}),
                ('file_open_events',513),('import_events',513),('directory_events',257),
                ('read_bytes_reserved',67108865),('hash_files_opened',1),('hash_read_bytes_reserved',1),
                ('hash_descriptor_events',3)]:
            obj=child();obj['warmup'][key]=value
            with self.assertRaises(Refused):c.validate_child(canonical(obj))

    def test_authored_hash_with_guarded_open_and_fd_events_completes_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            data=guard.base/'AUTHORED_RESOURCE';data.write_bytes(b'RESOURCE')
            exe=guard.base/'AUTHORED_PYTHON';exe.write_bytes(b'INTERPRETER')
            guard.guard('open',(str(data),'r',0))
            guard.transition('WARMUP');guard.transition('HASH')
            original_open,original_fdopen=os.open,os.fdopen
            def opening(path,flags,*args,**kwargs):
                guard.guard('open',(str(path),None,flags))
                return original_open(path,flags,*args,**kwargs)
            def fdopening(fd,mode,*args,**kwargs):
                guard.guard('open',(fd,mode,0))
                return original_fdopen(fd,mode,*args,**kwargs)
            with (patch.object(c.sys,'base_prefix',str(guard.base)),
                  patch.object(c.sys,'executable',str(exe)),patch.object(c.sys,'modules',{}),
                  patch.object(c.frozen.os,'open',side_effect=opening),
                  patch.object(c.frozen.os,'fdopen',side_effect=fdopening)):
                rows,actual,reserved,_=c.runtime_inventory(root,guard)
            guard.transition('STRICT')
            self.assertEqual(guard.hash_seen,{data,exe})
            self.assertEqual(guard.hash_opens,4)
            self.assertEqual(guard.hash_fd_opens,2)
            self.assertEqual(guard.hash_reserved,reserved)
            self.assertEqual(len(rows),2)
            self.assertIsNone(guard.first_refusal)

    def test_warmup_refusal_cannot_be_hidden_as_expected_negative(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            guard.transition('WARMUP')
            factory,_=authored_reader()
            def hidden(stream,**kwargs):
                if b'not a PDF object graph' in stream.getvalue():
                    try:guard.guard('import',('unlisted_package',None))
                    except c.frozen.QualificationStopped:pass
                return factory(stream,**kwargs)
            progress={}
            self.assertEqual(c.generated_checks(hidden,c.guarded.GeneratedTelemetry(),progress),119)
            self.assertIsNotNone(guard.first_refusal)
            with self.assertRaises(c.frozen.QualificationStopped):guard.transition('HASH')

    def test_hash_bytes_and_open_limits_stop_without_refund(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            for exhausted in ['events','bytes']:
                guard=self.make_guard(root);data=guard.base/'file';data.write_bytes(b'AUTHORED')
                guard.transition('WARMUP');guard.transition('HASH');guard.admit_hash({data})
                if exhausted=='events':guard.hash_opens=c.LIMITS['hash_open_events']
                else:guard.hash_reserved=c.LIMITS['runtime_hash_bytes']
                with self.assertRaises(c.frozen.QualificationStopped):guard.guard('open',(str(data),'r',0))
                self.assertIsNotNone(guard.first_refusal)
                with self.assertRaises(c.frozen.QualificationStopped):guard.transition('STRICT')

    def test_missing_cache_probe_requires_existing_declared_source_and_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            source=guard.base/'AUTHORED_CODEC.py';source.write_bytes(b'# AUTHORED CODEC')
            cache=Path(c.importlib.util.cache_from_source(str(source)))
            self.assertFalse(cache.exists())
            guard.guard('open',(str(cache),'r',0))
            self.assertEqual(guard.opens,1)
            self.assertEqual(guard.missing_bytecode_probes,1)
            self.assertEqual(guard.read_reserved,1)
            self.assertEqual(guard.read_files,{})
            other=Path(c.importlib.util.cache_from_source(str(guard.base/'ABSENT.py')))
            with self.assertRaises(c.frozen.QualificationStopped):guard.guard('open',(str(other),'r',0))

    def test_cache_source_alias_sets_sticky_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            target=guard.base/'target.py';target.write_bytes(b'# AUTHORED')
            source=guard.base/'alias.py';source.symlink_to(target)
            cache=Path(c.importlib.util.cache_from_source(str(source)))
            with self.assertRaises(c.frozen.QualificationStopped):
                guard.guard('open',(str(cache),'r',0))
            self.assertEqual(guard.first_refusal['predicate'],'CACHE_SOURCE_ALIAS_REFUSED')
            with self.assertRaises(c.frozen.QualificationStopped):guard.transition('WARMUP')

    def test_exact_declared_cffi_backend_namespace_and_path_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            guard.guard('import',('_cffi_backend',None))
            guard.guard('import',('_cffi_backend',str(root/c.PROFILE['native_backend']['path'])))
            self.assertEqual(guard.imports,2)
            for name,path in [('_cffi_backend',str(guard.base/'wrong.so')),
                              ('_cffi_backend.other',None),('_cffi_backend_unreviewed',None)]:
                state=self.make_guard(root)
                with self.assertRaises(c.frozen.QualificationStopped):state.guard('import',(name,path))
                self.assertIsNotNone(state.first_refusal)

    def test_exact_directory_closure_excludes_repository_root_and_unlisted_project(self):
        self.assertEqual(c.PROJECT_DIRECTORY_REFS, ('src', 'src/civiclab', 'src/civiclab/e01', 'tests'))
        self.assertEqual(len(c.EXACT_FINDER_DIRECTORY_REFS), 10)
        self.assertNotIn('.', c.EXACT_FINDER_DIRECTORY_REFS)
        self.assertNotIn('src/unlisted', c.EXACT_FINDER_DIRECTORY_REFS)

    def test_declared_project_and_package_roots_list_only_with_safe_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            for ref in c.EXACT_FINDER_DIRECTORY_REFS:
                directory=root/ref;directory.mkdir(parents=True,exist_ok=True)
                for event in ['os.listdir','os.scandir']:
                    guard.guard(event,(str(directory),))
                self.assertEqual(guard.directory_labels_observed['DECLARED:'+ref],2)
            self.assertEqual(guard.directories,20)
            self.assertEqual(guard.opens,0)
            self.assertEqual(guard.read_files,{})
            self.assertIsNone(guard.first_refusal)

    def test_added_listing_directories_do_not_grant_file_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            for ref in ['src/civiclab','src/civiclab/e01',c.SITE_REF+'/pypdf',c.SITE_REF+'/cryptography']:
                guard=self.make_guard(root);directory=root/ref;directory.mkdir(parents=True,exist_ok=True)
                guard.guard('os.listdir',(str(directory),))
                with self.assertRaises(c.frozen.QualificationStopped):guard.guard('open',(str(directory),'r',0))
                self.assertEqual(guard.first_refusal['predicate'],'ORIGIN_NOT_DECLARED')
            for name in ['src/civiclab/UNLISTED.py','tests/UNLISTED.py','data/raw/SOURCE.pdf','.env']:
                guard=self.make_guard(root)
                with self.assertRaises(c.frozen.QualificationStopped):guard.guard('open',(str(root/name),'r',0))

    def test_refused_directory_diagnostics_are_closed_and_no_arbitrary_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            for value,label in [(str(root),'OTHER_PROJECT_DIRECTORY_REFUSED'),
                    (str(root/'src'/'SECRET_UNLISTED'),'UNDECLARED_PROJECT_CODE_DIRECTORY'),
                    (str(root/'tests'/'SECRET_UNLISTED'),'UNDECLARED_PROJECT_CODE_DIRECTORY'),
                    (str(root/'data/raw'/'SECRET_UNLISTED'),'ACQUIRED_SOURCE_REFUSED'),
                    (str(root/'.env'),'CREDENTIAL_PATH_REFUSED'),
                    ('/SECRET_OUTSIDE_PATH','OUTSIDE_DECLARED_ROOTS'),
                    (5,'UNKNOWN_DIRECTORY_ARGUMENT')]:
                guard=self.make_guard(root)
                with self.assertRaises(c.frozen.QualificationStopped):guard.guard('os.listdir',(value,))
                self.assertEqual(guard.first_refusal['directory_label'],label)
                self.assertNotIn('SECRET',json.dumps(guard.first_refusal))
                self.assertIn(label,c.DIRECTORY_LABELS)

    def test_file_origin_policy_ast_is_unchanged(self):
        old=ast.parse((REPO/'src/civiclab/e01/clerk2020_warmup_qualification_v1.py').read_text())
        new=ast.parse((REPO/c.ENTRY).read_text())
        original=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='_origin_allowed')
        successor=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='_origin_allowed')
        self.assertEqual(ast.dump(original,include_attributes=False),ast.dump(successor,include_attributes=False))

    def test_real_filefinder_lists_authored_declared_trees_without_source_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            for ref in c.EXACT_FINDER_DIRECTORY_REFS:
                directory=root/ref;directory.mkdir(parents=True,exist_ok=True)
                (directory/'__authored_probe__.py').write_text('AUTHORED_MARKER = 1\n')
            script=r'''
import importlib.machinery,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[2])/'src'))
from civiclab.e01 import clerk2020_directories_qualification_v1 as c
root=Path(sys.argv[1]).resolve()
state=c.WarmupGuard(root)
sys.addaudithook(state.guard)
found=0
for ref in c.EXACT_FINDER_DIRECTORY_REFS:
    finder=importlib.machinery.FileFinder(str(root/ref),
        (importlib.machinery.SourceFileLoader,['.py']))
    spec=finder.find_spec('__authored_probe__')
    if spec is None:raise RuntimeError('AUTHORED_FINDER_MISSING')
    found+=1
assert found==10 and state.directories==10 and state.opens==0
assert '__authored_probe__' not in sys.modules and 'pypdf' not in sys.modules
print(json.dumps({'found':found,'directory_events':state.directories,
    'file_opens':state.opens,'labels':state.directory_labels_observed,
    'source_module_executed':False,'actual_pdf_library_imported':False}))
'''
            result=subprocess.run([sys.executable,'-I','-B','-S','-c',script,str(root),str(REPO)],
                                  capture_output=True,text=True,timeout=10,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            observation=json.loads(result.stdout)
            self.assertEqual(observation['found'],10)
            self.assertEqual(observation['file_opens'],0)
            self.assertEqual(set(observation['labels']),{'DECLARED:'+p for p in c.EXACT_FINDER_DIRECTORY_REFS})

    def test_child_directory_labels_reject_unknown_duplicate_and_incomplete_capture(self):
        for labels,count in [([['SECRET_PATH',1]],1),
                ([['PYTHON_BASE',1],['PYTHON_BASE',1]],2),([['PYTHON_BASE',1]],2),
                ([['PYTHON_BASE',True]],1),([['PYTHON_BASE',257]],257)]:
            obj=child();obj['warmup']['directory_labels_observed']=labels;obj['warmup']['directory_events']=count
            with self.assertRaises(Refused):c.validate_child(canonical(obj))

    def test_hash_directory_denial_retains_safe_category(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();guard=self.make_guard(root)
            guard.transition('WARMUP');guard.transition('HASH')
            with self.assertRaises(c.frozen.QualificationStopped):guard.guard('os.listdir',(str(root/'src/civiclab'),))
            self.assertEqual(guard.first_refusal['directory_label'],'DECLARED:src/civiclab')
            self.assertEqual(guard.first_refusal['phase'],'HASH')

    def test_alias_and_malformed_cache_failures_survive_expected_negative(self):
        for kind, expected in [('alias', 'CACHE_SOURCE_ALIAS_REFUSED'),
                               ('absent_source', 'READ_STAT_UNAVAILABLE'),
                               ('malformed_cache', 'READ_STAT_UNAVAILABLE')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                base = root / 'AUTHORED_BASE'
                base.mkdir()
                with patch.object(c.sys, 'base_prefix', str(base)):
                    guard = c.WarmupGuard(root)
                guard.transition('WARMUP')
                if kind == 'alias':
                    target = base / 'target.py'
                    target.write_bytes(b'# AUTHORED')
                    source = base / 'alias.py'
                    source.symlink_to(target)
                    cache = Path(c.importlib.util.cache_from_source(str(source)))
                elif kind == 'absent_source':
                    cache = Path(c.importlib.util.cache_from_source(str(base / 'ABSENT.py')))
                else:
                    cache = base / '__pycache__' / 'INVALID_CACHE_NAME.pyc'
                reader, _ = authored_reader()
                def swallowed(stream, **kwargs):
                    if b'not a PDF object graph' in stream.getvalue():
                        try:
                            guard.guard('open', (str(cache), 'r', 0))
                        except c.frozen.QualificationStopped:
                            pass  # Intentionally simulate a parser swallowing it.
                    return reader(stream, **kwargs)
                progress = {}
                self.assertEqual(c.generated_checks(swallowed, c.guarded.GeneratedTelemetry(), progress), 119)
                self.assertEqual(progress['reader_attempts_entered'], 4)
                self.assertEqual(guard.first_refusal['predicate'], expected)
                self.assertEqual(guard.first_refusal['phase'], 'WARMUP')
                with self.assertRaises(c.frozen.QualificationStopped):
                    guard.transition('HASH')
                self.assertEqual(guard.phase, 'WARMUP')


    def test_no_genuine_pypdf_or_cryptography_import(self):
        self.assertNotIn('pypdf', sys.modules)
        self.assertNotIn('cryptography', sys.modules)


if __name__ == '__main__':
    unittest.main()
