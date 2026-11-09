import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab import live_summary_viewer as viewer

ROOT = Path(__file__).resolve().parents[1]


class LiveSummaryTests(unittest.TestCase):
    def test_exact_accepted_audit_projection_excludes_private_evidence(self):
        result = viewer.projection(ROOT)
        self.assertEqual(result['responses'], 32)
        self.assertEqual(result['matched_comparisons'], 8)
        self.assertEqual(result['research_cost_usd'], '0.001434')
        self.assertEqual(result['conservative_total_microusd'], 2857)
        self.assertEqual(result['followup']['status'], 'DESIGN_IN_REVIEW_NOT_RUN')
        encoded = json.dumps(result)
        for private in ('data/processed/', 'generation_id', 'native_tokens', 'request_hash', 'source_files'):
            self.assertNotIn(private, encoded)

    def test_projection_reads_only_one_public_audit(self):
        original = Path.open
        opened = []
        def checked(path, *args, **kwargs):
            opened.append(path)
            if path != ROOT / viewer.AUDIT:
                raise AssertionError('Undeclared file read')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', checked):
            viewer.projection(ROOT)
        self.assertEqual(opened, [ROOT / viewer.AUDIT])

    def test_changed_unreviewed_audit_refuses_before_preview_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / viewer.AUDIT
            audit.parent.mkdir(parents=True)
            audit.write_text('{}')
            out = root / 'preview'
            out.mkdir()
            index = out / 'index.html'
            index.write_text('<main>original</main>')
            with self.assertRaises(ValueError):
                viewer.build(root, out)
            self.assertEqual(index.read_text(), '<main>original</main>')
            self.assertEqual([p.name for p in out.iterdir()], ['index.html'])

    def test_preserves_archive_snapshot_and_rebuild_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            legacy = b'<html><body><main>HISTORICAL</main><script>legacy()</script></body></html>\r\n'
            (out / 'index.html').write_bytes(legacy)
            (out / 'snapshot.json').write_bytes(b'{"historical":true}\n')
            first = viewer.build(ROOT, out).read_bytes()
            self.assertEqual((out / 'historical-preview.html').read_bytes(), legacy)
            self.assertEqual((out / 'snapshot.json').read_bytes(), b'{"historical":true}\n')
            self.assertEqual(first.count(viewer.START.encode()), 1)
            self.assertIn(b'Historical snapshot', first)
            self.assertIn(b'No follow-up results are displayed', first)
            self.assertEqual(viewer.build(ROOT, out).read_bytes(), first)

    def test_projection_fields_are_html_escaped(self):
        s = viewer.projection(ROOT)
        s['model'] = '<script>not-safe()</script>'
        s['followup']['question'] = '<img onerror="bad()">'
        page = viewer.render(s)
        self.assertNotIn('<script>', page)
        self.assertNotIn('<img', page)
        self.assertIn('&lt;script&gt;', page)

    def test_unexpected_archive_shape_refuses_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'index.html').write_text('unrecognized page')
            with self.assertRaises(ValueError):
                viewer.build(ROOT, out)
            self.assertEqual((out / 'index.html').read_text(), 'unrecognized page')


if __name__ == '__main__':
    unittest.main()
