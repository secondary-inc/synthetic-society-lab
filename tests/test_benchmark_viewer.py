"""Authored fixtures only: no Census rows or actual demographic cells."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab import benchmark_viewer as viewer
from civiclab.benchmark_export import project_aggregate, validate_projection
from civiclab.common import RunStore, atomic_json, canonical_hash, sha256_file
from tests.test_benchmark_export import fixture, provenance

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkViewerTests(unittest.TestCase):
    def setup_fixture(self, root):
        payload = project_aggregate(fixture(), provenance())
        trace = {
            'accepted_payload_sha256': 'x',
            'accepted_canonical_sha256': canonical_hash(payload),
            'projection_schema_sha256': sha256_file(ROOT / viewer.SCHEMA),
            'finalization_config_sha256': 'a' * 64,
            'finalization_implementation_sha256': 'b' * 64,
            'finalization_execution_approval_sha256': 'c' * 64,
            'output_disclosure_audit_sha256': 'd' * 64,
            'owner_review_only': True, 'external_publication_authorized': False,
            'source_run_preserved': True,
        }
        with RunStore(root, 'E02', {'stage': 'MOCK_VIEWER_FIXTURE'}, kind='MOCK') as run:
            run.write('demographic-benchmark.json', payload)
            trace['accepted_payload_sha256'] = sha256_file(run.path / 'demographic-benchmark.json')
            run.write('review-finalization.json', trace)
            run.finish({'status': 'MOCK', 'spent_usd': 0})
        row = {'run_id': run.run_id, 'checksums_sha256': sha256_file(run.path / 'checksums.json'),
               'artifact_sha256': sha256_file(run.path / 'demographic-benchmark.json'),
               'artifact_canonical_sha256': canonical_hash(payload),
               'trace_sha256': sha256_file(run.path / 'review-finalization.json')}
        audit = {
            'status': 'PASS_EXACT_WYOMING_FINALIZATION_OWNER_REVIEW_ADMISSION',
            'auditor_role': 'independent_auditor', 'owner_review_only': True,
            'external_publication_authorized': False, 'accepted_runs': [row],
            'projection_schema_sha256': trace['projection_schema_sha256'],
            'config_sha256': trace['finalization_config_sha256'],
            'reviewed_implementation_sha256': trace['finalization_implementation_sha256'],
            'code_execution_approval_sha256': trace['finalization_execution_approval_sha256'],
            'output_disclosure_audit_sha256': trace['output_disclosure_audit_sha256'],
            'admission_scope': 'MOCK fixture only',
        }
        atomic_json(root / viewer.ADMISSION, audit)
        (root / viewer.SCHEMA).parent.mkdir(parents=True, exist_ok=True)
        (root / viewer.SCHEMA).write_bytes((ROOT / viewer.SCHEMA).read_bytes())
        return run.path, audit

    def test_no_admission_and_private_only_runs_never_typed_or_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with RunStore(root, 'E02', {}, kind='MOCK') as run:
                run.write('aggregate-local-only.json', {'DO_NOT_EXPORT': True})
                run.write('demographic-benchmark.local.json', {'DO_NOT_EXPORT': True})
                run.write('demographic-benchmark.json', {'DO_NOT_EXPORT': True})
                run.finish({'status': 'MOCK'})
            with patch.object(viewer, 'bounded_read', side_effect=AssertionError('not admitted')):
                data = viewer.snapshot(root)
            self.assertNotIn('demographic_benchmark', data['runs'][0])
            self.assertNotIn('DO_NOT_EXPORT', json.dumps(data))

    def test_admitted_fixture_table_and_provenance_escape_and_no_private_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); run, audit = self.setup_fixture(root)
            with patch.object(viewer, 'ADMISSION_SHA256', sha256_file(root / viewer.ADMISSION)):
                output = viewer.build(root, root / 'viewer')
            data = json.loads(output.with_name('snapshot.json').read_text())
            self.assertEqual(len(data['runs'][0]['demographic_benchmark']['cells']), 12)
            self.assertEqual(data['runs'][0]['demographic_benchmark']['scientific_population_gate'], 'BLOCKED')
            html = output.read_text()
            for label in ('Count 90% MOE', 'Share 90% MOE (fraction)', 'Unweighted contributors', 'one-state benchmark'):
                self.assertIn(label, html)
            self.assertNotIn('DO_NOT_EXPORT', html)
            self.assertEqual(data['runs'][0]['benchmark_admission']['sha256'], sha256_file(root / viewer.ADMISSION))

    def test_altered_receipt_or_schema_refused_before_output(self):
        for target in ('receipt', 'schema'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); self.setup_fixture(root)
                digest = sha256_file(root / viewer.ADMISSION)
                changed = root / (viewer.ADMISSION if target == 'receipt' else viewer.SCHEMA)
                changed.write_text(changed.read_text() + ' ')
                with patch.object(viewer, 'ADMISSION_SHA256', digest):
                    with self.assertRaises(ValueError): viewer.build(root, root / 'viewer')
                self.assertFalse((root / 'viewer').exists())

    def test_changed_payload_or_trace_resealed_ledger_still_refused(self):
        for name in ('demographic-benchmark.json', 'review-finalization.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); run, _ = self.setup_fixture(root)
                (run / name).write_text((run / name).read_text() + ' ')
                ledger = json.loads((run / 'checksums.json').read_text())
                ledger[name] = sha256_file(run / name); atomic_json(run / 'checksums.json', ledger)
                with patch.object(viewer, 'ADMISSION_SHA256', sha256_file(root / viewer.ADMISSION)):
                    with self.assertRaises(ValueError): viewer.build(root, root / 'viewer')
                self.assertFalse((root / 'viewer').exists())

    def test_change_after_validation_refused_and_old_base_code_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); run, _ = self.setup_fixture(root)
            def mutate(value, schema):
                validate_projection(value, schema)
                (run / 'demographic-benchmark.json').write_text('{}')
            with patch.object(viewer, 'ADMISSION_SHA256', sha256_file(root / viewer.ADMISSION)), patch.object(viewer, 'validate_projection', side_effect=mutate):
                with self.assertRaises(ValueError): viewer.build(root, root / 'viewer')
            self.assertFalse((root / 'viewer').exists())

    def test_injection_in_base_manifest_remains_json_data_and_selection_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with RunStore(root, 'E01', {'title': '</script><script>PRIVATE_TEST</script>'}, kind='MOCK') as run:
                run.finish({'status': 'MOCK'})
            text = viewer.build(root, root / 'viewer').read_text()
            self.assertNotIn('</script><script>PRIVATE_TEST</script>', text)
            self.assertIn('\\u003c/script', text)
            with self.assertRaises(ValueError): viewer.snapshot(root, ['../../outside'])
