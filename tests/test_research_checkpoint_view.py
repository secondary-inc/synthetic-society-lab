import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab import live_summary_viewer, research_checkpoint_view as view

ROOT = Path(__file__).resolve().parents[1]


class CheckpointViewTests(unittest.TestCase):
    def test_reads_only_public_pins_and_preserves_unknown_billing(self):
        opened = []
        original = Path.open
        expected = [ROOT / path for path, _ in view.SOURCES.values()]
        def checked(path, *args, **kwargs):
            self.assertIn(path, expected)
            opened.append(path)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', checked):
            result = view.projection(ROOT)
        self.assertEqual(opened, expected)
        self.assertEqual(result['provider_charge'], 'UNKNOWN')
        self.assertEqual(result['provider_outcome'], 'UNKNOWN')
        self.assertFalse(result['fifth_complete'])
        self.assertEqual((result['verified_responses'], result['fifth_responses']), (191, 44))
        self.assertEqual((result['verified_usage_usd'], result['exposure_usd']), ('0.0129589', '0.017152'))
        self.assertEqual(result['e01']['final_ballots_accepted'], 0)
        for private in ('data/processed/', 'generation_id', 'receipt', 'native_tokens', 'request_hash'):
            self.assertNotIn(private, json.dumps(result))

    def test_each_changed_pin_prevents_all_preview_writes(self):
        old_sources = [live_summary_viewer.AUDIT, live_summary_viewer.FOLLOWUP_AUDIT,
                       live_summary_viewer.CROSSMODEL_AUDIT, live_summary_viewer.CROSSMODEL_AGGREGATE,
                       live_summary_viewer.WRAPPER_AUDIT, live_summary_viewer.WRAPPER_AGGREGATE]
        for changed, _ in view.SOURCES.values():
            with self.subTest(path=changed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in old_sources + [x[0] for x in view.SOURCES.values()]:
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'{}' if name == changed else (ROOT / name).read_bytes())
                out = root / 'output'
                out.mkdir()
                (out / 'index.html').write_bytes(b'<main>old</main>')
                with self.assertRaises(ValueError):
                    live_summary_viewer.build(root, out)
                self.assertEqual((out / 'index.html').read_bytes(), b'<main>old</main>')
                self.assertEqual([p.name for p in out.iterdir()], ['index.html'])

    def test_rebuild_preserves_old_studies_and_historical_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            legacy = b'<html><body><main>historical</main></body></html>\r\n'
            (out / 'index.html').write_bytes(legacy)
            (out / 'snapshot.json').write_bytes(b'{}\n')
            first = live_summary_viewer.build(ROOT, out).read_bytes()
            result = json.loads((out / 'live-summary.json').read_bytes())
            self.assertEqual(result['latest_checkpoint'], view.projection(ROOT))
            self.assertEqual(result['wrapper_result'], live_summary_viewer.wrapper_projection(ROOT))
            self.assertEqual(result['crossmodel_result'], live_summary_viewer.crossmodel_projection(ROOT))
            self.assertEqual(result['followup_result'], live_summary_viewer.followup_projection(ROOT))
            self.assertEqual((out / 'historical-preview.html').read_bytes(), legacy)
            self.assertEqual((out / 'snapshot.json').read_bytes(), b'{}\n')
            self.assertEqual(live_summary_viewer.build(ROOT, out).read_bytes(), first)
            self.assertEqual(first.count(b'id="checkpoint-title"'), 1)

    def test_render_escapes_fields_and_separates_scope(self):
        result = view.projection(ROOT)
        result['provider_charge'] = '<script>bad()</script>'
        result['sources'][0]['path'] = '<img onerror="bad()">'
        html = view.render(result)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('not a treatment-effect estimate', html)
        self.assertIn('not a live account balance', html)
        self.assertIn('does not accept ballots', html)
        self.assertIn('Consumed attempts must not be replayed', html)


if __name__ == '__main__':
    unittest.main()
