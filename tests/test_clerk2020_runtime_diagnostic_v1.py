"""Authored modules/temp artifacts and stub child only; no real runtime probe."""
import base64
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from civiclab.e01 import clerk2020_runtime_diagnostic_v1 as d
from civiclab.e01.clerk2020_m2_v1_1_contracts import Refused, canonical, decode, sha
from test_clerk2020_native_qualification_v1 import FakeProcess

REPO = Path(__file__).resolve().parents[1]
PUBLIC_STOP = json.loads((REPO / 'reports/clerk2020_native_qualification_v1_actual_stop_20261109.json').read_bytes())


def prepare(root):
    refs = {}
    for name in d.CODE_PATHS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = ((REPO / name).read_bytes() if name in d.CRITICAL_REFS
               else ('# AUTHORED DIAGNOSTIC CODE ' + name).encode())
        path.write_bytes(raw)
        refs[name] = {'sha256': sha(raw), 'bytes': len(raw)}
    old = root / d.ANCESTOR['scope']
    old.mkdir(parents=True)
    for record in PUBLIC_STOP['OUTPUT_ARTIFACTS']['read_only_copied_control_records']:
        (old / Path(record['path']).name).write_bytes(record['raw_utf8'].encode())
    review = {'kind': 'CLERK2020_RUNTIME_DIAGNOSTIC_CODE_BINDING_V1',
              'status': 'PASS_EXACT_RUNTIME_DIAGNOSTIC_ONLY', 'reviewer_role': 'independent_auditor',
              'code_refs': refs, 'limits': d.LIMITS, 'ancestor': d.ANCESTOR,
              'project_overlay': list(d.OVERLAY), 'source_authority': False, 'qualification_authority': False}
    r = canonical(review)
    packet = {'schema_version': 1, 'kind': d.KIND, 'phase_id': 'runtime-diagnostic-v1',
              'root_sha256': sha(str(root).encode()), 'ancestor': d.ANCESTOR, 'limits': d.LIMITS,
              'code_refs': refs, 'project_overlay': list(d.OVERLAY),
              'review_bytes_b64': base64.b64encode(r).decode(), 'review_sha256': sha(r)}
    raw = canonical(packet)
    return raw, sha(raw)


def child_record():
    return {'kind': 'CLERK2020_RUNTIME_DIAGNOSTIC_RESULT_V1', 'ancestor_plan_sha256': d.OLD_PLAN,
            'source_reads': 0, 'reader_attempts': 0, 'page_extractions': 0, 'model_calls': 0,
            'network_requests': 0, 'project_overlay': list(d.OVERLAY), 'external_origin_rules_changed': False,
            'excluded_modules': 0, 'qualification_or_source_admission': False,
            'status': 'REJECTION_RECORDED', 'stage': 'COLLECTOR', 'collector_passes_attempted': 1,
            'error_type': 'Refused',
            'site': {'function': '_runtime_inventory', 'line': 366, 'predicate': 'ORIGIN_ALLOWLIST'},
            'context': {'kind': 'PROPOSED_FUTURE_FAILURE_CONTEXT_V1_1_NOT_ORIGINAL_RUN_DIAGNOSIS',
                        'frozen_source': 'src/civiclab/e01/clerk2020_native_qualification_v1.py',
                        'qualified_frames': [{'function': '_runtime_inventory', 'line': 366,
                                             'last_iteration_module_not_proven_cause': 'AUTHORED_EXTRA',
                                             'last_iteration_origin_category_not_proven_cause': 'VENV_OTHER_PACKAGE'}],
                        'traceback_truncated': False, 'extra_runtime_or_source_io': 0,
                        'exception_message_retained': False, 'permits_retry_or_policy_change': False},
            'manifest': None, 'runtime_bytes_observed': None, 'runtime_bytes_reserved': None}


def exchange(process, packet, start, out, err):
    out.extend(canonical(child_record()))
    return 0


class RuntimeDiagnosticTests(unittest.TestCase):
    def test_diagnostic_network_and_process_events_refuse_before_effect(self):
        for event in ['socket.__new__', 'socket.connect', 'subprocess.Popen', 'os.system',
                      'os.fork', 'os.exec', 'os.posix_spawn']:
            with self.assertRaises(Refused):
                d._diagnostic_guard(event, ())
        d._diagnostic_guard('open', ())  # Reviewed runtime-origin hashing still needs reads.

    def test_release_is_closed_zero_parse_and_preserves_old_full_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            packet = d.validate_packet(root, raw, h)
            self.assertEqual(packet['limits']['reader_attempts'], 0)
            self.assertEqual(packet['ancestor']['full_consumed_limits']['reader_attempts'], 4)
            self.assertEqual(packet['ancestor']['credit_restored'], 0)

    def test_no_new_qualification_or_caller_selected_overlay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            for field, value in [('phase_id', 'qualification-v2'), ('project_overlay', ['allow-everything'])]:
                p = decode(raw)
                p[field] = value
                changed = canonical(p)
                with self.assertRaises(Refused):
                    d.validate_packet(root, changed, sha(changed))

    def test_no_ancestor_reset_or_refund(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            p = decode(raw)
            p['ancestor']['full_consumed_limits']['reader_attempts'] = 0
            changed = canonical(p)
            with self.assertRaises(Refused):
                d.validate_packet(root, changed, sha(changed))

    def test_no_bool_limit_coercion(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            p = decode(raw)
            p['limits']['collector_passes'] = True
            changed = canonical(p)
            with self.assertRaises(Refused):
                d.validate_packet(root, changed, sha(changed))

    def test_frozen_collector_and_helper_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            p = decode(raw)
            p['code_refs'][next(iter(d.CRITICAL_REFS))]['sha256'] = 'f' * 64
            changed = canonical(p)
            with self.assertRaises(Refused):
                d.validate_packet(root, changed, sha(changed))

    def test_review_must_refuse_source_and_qualification_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, _ = prepare(root)
            for key in ['source_authority', 'qualification_authority']:
                p = decode(raw)
                review = decode(base64.b64decode(p['review_bytes_b64']))
                review[key] = True
                r = canonical(review)
                p['review_bytes_b64'], p['review_sha256'] = base64.b64encode(r).decode(), sha(r)
                changed = canonical(p)
                with self.assertRaises(Refused):
                    d.validate_packet(root, changed, sha(changed))

    def test_current_frozen_sites_match_public_code_not_a_runtime_probe(self):
        lines = (REPO / 'src/civiclab/e01/clerk2020_native_qualification_v1.py').read_text().splitlines()
        self.assertIn('require(allowed(path))', lines[365])
        self.assertIn('require(len(candidates)', lines[369])
        self.assertIn('require(len(canonical(rows))', lines[381])

    def test_exact_rejecting_site_from_real_frozen_code_with_authored_metadata_only(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            exe = base / 'bin/python'
            exe.parent.mkdir()
            exe.write_bytes(b'AUTHORED_NOT_AN_INTERPRETER')
            module = ModuleType('AUTHORED_EXTRA')
            module.__file__ = str(REPO / '.venv/lib/python3.12/site-packages/AUTHORED_EXTRA/__init__.py')
            original = d.frozen.CODE_PATHS
            with (patch.object(d.frozen.sys, 'base_prefix', str(base)),
                  patch.object(d.frozen.sys, 'executable', str(exe)),
                  patch.object(d.frozen.sys, 'modules', {'AUTHORED_EXTRA': module}),
                  patch.object(d.frozen, '_stable_hash') as hasher):
                result = d.collect_diagnostic(REPO)
            self.assertFalse(hasher.called)
            self.assertEqual(result['site'], {'function': '_runtime_inventory', 'line': 366,
                                             'predicate': 'ORIGIN_ALLOWLIST'})
            self.assertEqual(result['context']['qualified_frames'][0]['last_iteration_module_not_proven_cause'], 'AUTHORED_EXTRA')
            self.assertEqual(d.frozen.CODE_PATHS, original)

    def test_collector_called_once_with_exact_project_overlay_only(self):
        original = d.frozen.CODE_PATHS
        def collector(root):
            self.assertEqual(d.frozen.CODE_PATHS, original + d.OVERLAY)
            return [['PYTHON_BASE/AUTHORED', 1, 'a' * 64]], 1, 2
        with patch.object(d.frozen, '_runtime_inventory', side_effect=collector) as call:
            result = d.collect_diagnostic(REPO)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(result['status'], 'REJECTION_NOT_REPRODUCED')
        self.assertEqual(d.frozen.CODE_PATHS, original)

    def test_project_overlay_is_admitted_without_other_origin_expansion(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            base = root / 'AUTHORED_BASE'
            exe = base / 'bin/python'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'AUTHORED_NOT_AN_INTERPRETER')
            path = root / d.ENTRY
            path.parent.mkdir(parents=True)
            path.write_bytes(b'AUTHORED_DIAGNOSTIC_PROJECT_CODE')
            module = ModuleType('AUTHORED_DIAGNOSTIC')
            module.__file__ = str(path)
            with (patch.object(d.frozen.sys, 'base_prefix', str(base)),
                  patch.object(d.frozen.sys, 'executable', str(exe)),
                  patch.object(d.frozen.sys, 'modules', {'AUTHORED_DIAGNOSTIC': module})):
                result = d.collect_diagnostic(root)
            self.assertEqual(result['status'], 'REJECTION_NOT_REPRODUCED')
            self.assertEqual(len(result['manifest']), 2)

    def test_spoofed_filename_without_frozen_code_identity_has_no_site(self):
        namespace = {'Refused': Refused}
        exec(compile('def _runtime_inventory():\n    raise Refused()\n',
                     str(REPO / 'src/civiclab/e01/clerk2020_native_qualification_v1.py'), 'exec'), namespace)
        try:
            namespace['_runtime_inventory']()
        except Refused as exc:
            site, context = d._site(exc, REPO)
        self.assertIsNone(site)
        self.assertEqual(context['qualified_frames'][0]['function'], '_runtime_inventory')

    def test_collector_policy_restored_after_unclassified_exception(self):
        original = d.frozen.CODE_PATHS
        class ExtraError(Exception):
            pass
        with patch.object(d.frozen, '_runtime_inventory', side_effect=ExtraError('PRIVATE')):
            result = d.collect_diagnostic(REPO)
        self.assertEqual(result['error_type'], 'UNCLASSIFIED')
        self.assertIsNone(result['site'])
        self.assertEqual(d.frozen.CODE_PATHS, original)
        self.assertNotIn('PRIVATE', str(result))

    def test_unknown_exception_metaclass_name_descriptor_is_not_called(self):
        calls = []
        class Meta(type):
            def __getattribute__(cls, name):
                if name == '__name__':
                    calls.append('DESCRIPTOR_SIDE_EFFECT')
                    raise RuntimeError('AUTHORED_META')
                return super().__getattribute__(name)
        class ExtraError(Exception, metaclass=Meta):
            pass
        with patch.object(d.frozen, '_runtime_inventory', side_effect=ExtraError('PRIVATE')):
            result = d.collect_diagnostic(REPO)
        self.assertEqual(result['error_type'], 'UNCLASSIFIED')
        self.assertEqual(calls, [])

    def test_child_schema_and_no_source_or_qualification(self):
        self.assertEqual(d._validate_child(canonical(child_record())), child_record())
        for key, value in [('reader_attempts', 1), ('source_reads', False), ('excluded_modules', 1),
                           ('external_origin_rules_changed', True), ('qualification_or_source_admission', True)]:
            child = child_record()
            child[key] = value
            with self.assertRaises(Refused):
                d._validate_child(canonical(child))

    def test_child_cannot_assert_unmatched_site(self):
        child = child_record()
        child['site']['line'] = 370
        child['site']['predicate'] = 'RUNTIME_FILE_COUNT'
        with self.assertRaises(Refused):
            d._validate_child(canonical(child))

    def test_child_raw_paths_and_messages_are_closed_out(self):
        for field in ['raw_path', 'message', 'traceback']:
            child = child_record()
            child['context']['qualified_frames'][0][field] = 'AUTHORED_PRIVATE'
            with self.assertRaises(Refused):
                d._validate_child(canonical(child))

    def test_precondition_cannot_claim_a_collector_rejection_site(self):
        child = child_record()
        child.update({'status': 'PRECONDITION_STOP', 'stage': 'IDENTITY', 'collector_passes_attempted': 0})
        with self.assertRaises(Refused):
            d._validate_child(canonical(child))

    def test_parent_reserves_before_ancestor_and_code_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            previous = d.frozen._stable_hash
            def reserved(path, allowance):
                self.assertTrue((root / d.SCOPE / 'STARTED.json').exists())
                return previous(path, allowance)
            original = {p.name: p.read_bytes() for p in (root / d.ANCESTOR['scope']).iterdir()}
            with (patch.object(d.frozen, '_stable_hash', side_effect=reserved),
                  patch.object(d.subprocess, 'Popen', return_value=FakeProcess()) as launch,
                  patch.object(d.frozen, '_exchange', side_effect=exchange)):
                out = d.run_phase(root, raw, h)
            self.assertEqual(launch.call_count, 1)
            self.assertEqual(launch.call_args.args[0][1:4], ['-I', '-B', '-S'])
            self.assertEqual(out['ancestor_metadata_bytes_reserved'], 3104)
            self.assertEqual(out['reader_attempts'], 0)
            self.assertEqual(original, {p.name: p.read_bytes() for p in (root / d.ANCESTOR['scope']).iterdir()})

    def test_ancestor_tamper_blocks_child_and_consumes_only_new_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            (root / d.ANCESTOR['scope'] / 'OUTCOME.json').write_bytes(b'AUTHORED_DRIFT')
            with patch.object(d.subprocess, 'Popen') as launch:
                with self.assertRaises(d.frozen.QualificationStopped):
                    d.run_phase(root, raw, h)
                self.assertFalse(launch.called)
            with self.assertRaises(FileExistsError):
                d.run_phase(root, raw, h)

    def test_new_diagnostic_cannot_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            with (patch.object(d.subprocess, 'Popen', return_value=FakeProcess()),
                  patch.object(d.frozen, '_exchange', side_effect=exchange)):
                d.run_phase(root, raw, h)
            with self.assertRaises(FileExistsError):
                d.run_phase(root, raw, h)

    def test_lost_child_result_retains_partial_without_new_pdf_attempts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            def stop(proc, packet, start, out, err):
                out.extend(b'AUTHORED_PARTIAL')
                raise TimeoutError()
            with (patch.object(d.subprocess, 'Popen', return_value=FakeProcess()),
                  patch.object(d.frozen, '_exchange', side_effect=stop)):
                with self.assertRaises(d.frozen.QualificationStopped):
                    d.run_phase(root, raw, h)
            self.assertEqual((root / d.SCOPE / 'partial_stdout.local.bin').read_bytes(), b'AUTHORED_PARTIAL')
            outcome = json.loads((root / d.SCOPE / 'OUTCOME.json').read_bytes())
            self.assertEqual(outcome['new_full_limits_consumed']['reader_attempts'], 0)
            self.assertTrue(outcome['ancestor_full_limits_remain_consumed'])

    def test_ancestor_changed_after_child_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            raw, h = prepare(root)
            def tamper(proc, packet, start, out, err):
                exchange(proc, packet, start, out, err)
                (root / d.ANCESTOR['scope'] / 'OUTCOME.json').write_bytes(b'AUTHORED_POST_CHILD_DRIFT')
                return 0
            with (patch.object(d.subprocess, 'Popen', return_value=FakeProcess()),
                  patch.object(d.frozen, '_exchange', side_effect=tamper)):
                with self.assertRaises(d.frozen.QualificationStopped):
                    d.run_phase(root, raw, h)
            self.assertFalse((root / d.SCOPE / 'worker.json').exists())

    def test_successful_manifest_is_not_qualification(self):
        child = child_record()
        child.update({'status': 'REJECTION_NOT_REPRODUCED', 'error_type': None, 'site': None,
                      'context': None, 'manifest': [['PYTHON_BASE/AUTHORED', 1, 'a' * 64]],
                      'runtime_bytes_observed': 1, 'runtime_bytes_reserved': 2})
        self.assertFalse(d._validate_child(canonical(child))['qualification_or_source_admission'])

    def test_no_real_pypdf_import_in_authored_suite(self):
        self.assertNotIn('pypdf', sys.modules)


if __name__ == '__main__':
    unittest.main()
