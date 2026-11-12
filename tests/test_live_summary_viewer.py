import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab import live_summary_viewer as viewer

ROOT = Path(__file__).resolve().parents[1]


class LiveSummaryTests(unittest.TestCase):
    def test_crossmodel_allowlist_candidate_preserves_dispositions_not_phase_rows(self):
        # Mapping check only; the candidate receipt does not confer acceptance.
        a = json.loads((ROOT / 'reports/E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json').read_text())
        s = viewer.crossmodel_summary(a)
        self.assertEqual((s['actual_responses'], s['skipped_slots'], s['failed_slots'], s['unattempted_slots']), (53, 3, 0, 0))
        first, second = s['models']
        self.assertEqual((first['interaction']['complete'], second['interaction']['complete']), (3, 4))
        self.assertEqual((first['factual_asked'], second['factual_asked']), (25, 28))
        self.assertEqual((first['support_missing_null'], second['support_missing_null']), (3, 0))
        self.assertEqual(sum(m['factual_missing_invalid'] for m in s['models']), 0)
        self.assertAlmostEqual(s['crossmodel']['mean'], -20 / 3)
        self.assertEqual([r['value'] for r in s['crossmodel']['context_values']], [-30, -10, None, 20])
        self.assertFalse(s['full_pattern_met'])
        self.assertEqual(s['research_cost_usd'], '0.0038870')
        for forbidden in ('scored_phases', 'profile_id', 'generation_id', 'data/processed/', 'party_gap'):
            self.assertNotIn(forbidden, json.dumps(s))
        a['analysis']['phase_counts'] = dict(ANSWER=50, SKIPPED_INVALID_PRE=1,
                                            FAILED_UNCERTAIN=1, PARSE_ERROR=1,
                                            CANCELLED=1, NOT_ATTEMPTED=2)
        partial = viewer.crossmodel_summary(a)
        self.assertEqual([partial[k] for k in ('actual_responses', 'skipped_slots',
                         'failed_slots', 'parse_error_slots', 'cancelled_slots',
                         'unattempted_slots')], [50, 1, 1, 1, 1, 2])
        a['analysis']['phase_counts']['UNKNOWN_STATUS'] = 1
        with self.assertRaises(ValueError):
            viewer.crossmodel_summary(a)

    def test_crossmodel_signed_reversal_and_common_context_denominators(self):
        # Authored display oracle: no empirical third-study result is implied.
        def model(name, omitted, shown, interaction, count):
            return dict(name=name, omitted=dict(mean=omitted, complete=4),
                        shown=dict(mean=shown, complete=count),
                        interaction=dict(mean=interaction, complete=count),
                        factual_correct=20, factual_asked=22, factual_errors=1,
                        factual_missing_invalid=1,
                        unasked_slots=2)
        summary = dict(sample_dates='AUTHORED TEST ONLY', actual_responses=52,
                       planned_slots=56, skipped_slots=2, failed_slots=1,
                       unattempted_slots=1, parse_error_slots=0, cancelled_slots=0,
                       research_cost_usd='0.01',
                       conservative_exposure_usd='0.02',
                       all_research_cost_usd='0.02',
                       source_audit='<script>audit</script>', source_audit_sha256='fixture',
                       recovery_note='Two saved baselines; <private> excluded.',
                       models=[model('A <unsafe>', 60, -20, -80, 4),
                               model('B', 40, 10, -30, 2)],
                       crossmodel=dict(mean=25, complete=2,
                                       context_values=[dict(A_value=-55, B_value=-30, value=25),
                                                       dict(A_value=None, B_value=10, value=None)]))
        page = viewer.render_crossmodel(summary)
        self.assertIn('-20', page)
        self.assertIn('-80', page)
        self.assertIn('reversal of the content contrast', page)
        self.assertIn('2 / 4 contexts', page)
        self.assertIn('4 / 4 contexts', page)
        self.assertIn('+25 points', page)  # Common-case oracle, not -30 - (-80).
        self.assertIn('Not estimable', page)
        self.assertIn('20 / 22', page)
        self.assertIn('2 skipped', page)
        self.assertIn('1 failed', page)
        self.assertIn('1 unattempted', page)
        self.assertIn('Missing / invalid factual items among asked', page)
        self.assertNotIn('<script>', page)
        self.assertNotIn('<private>', page)
        self.assertIn('&lt;unsafe&gt;', page)
        self.assertIn('No human-persuasion', page)

    def test_crossmodel_reads_only_pinned_public_audit_and_aggregate(self):
        original = Path.open
        opened = []
        def checked(path, *args, **kwargs):
            opened.append(path)
            self.assertIn(path, [ROOT / viewer.CROSSMODEL_AUDIT, ROOT / viewer.CROSSMODEL_AGGREGATE])
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', checked):
            s = viewer.crossmodel_projection(ROOT)
        self.assertEqual(len(opened), 2)
        self.assertEqual(s['source_audit_sha256'], viewer.CROSSMODEL_AUDIT_SHA256)
        self.assertEqual(s['actual_responses'], 53)

    def test_changed_crossmodel_evidence_refuses_before_any_output(self):
        for changed in (viewer.CROSSMODEL_AUDIT, viewer.CROSSMODEL_AGGREGATE):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in (viewer.AUDIT, viewer.FOLLOWUP_AUDIT, viewer.CROSSMODEL_AUDIT, viewer.CROSSMODEL_AGGREGATE):
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b'{}' if name == changed else (ROOT / name).read_bytes())
                out = root / 'preview'
                out.mkdir()
                (out / 'index.html').write_text('<main>original</main>')
                with self.assertRaises(ValueError):
                    viewer.build(root, out)
                self.assertEqual((out / 'index.html').read_text(), '<main>original</main>')
                self.assertEqual([p.name for p in out.iterdir()], ['index.html'])

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
            self.assertIn(b'First pilot retained separately', first)
            self.assertNotIn(b'DESIGN IN REVIEW', first)
            self.assertIn(b'COMPLETE WITH SKIPS', first)
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

    def test_followup_keeps_matched_denominators_and_missingness(self):
        s = viewer.followup_projection(ROOT)
        self.assertEqual((s['actual_responses'], s['skipped_posts']), (22, 6))
        self.assertEqual(s['primary_mean'], 56.25)
        self.assertEqual(s['paired_omitted_mean'], 62.5)
        self.assertEqual(s['paired_interaction_mean'], -62.5)
        self.assertEqual((s['primary_contexts'], s['paired_contexts']), (4, 2))
        self.assertEqual(s['asked_comprehension_correct'], 22)
        self.assertFalse(s['anchoring_pattern_met'])
        page = viewer.render_followup(s)
        self.assertIn('six skipped posts are missing planned answers', page)
        self.assertIn('four-context +56.25 mean is not the comparator', page)
        self.assertIn('full prespecified anchoring pattern was not met', page)
        self.assertNotIn('data/processed/', json.dumps(s))

    def test_followup_reads_only_accepted_public_audit(self):
        original = Path.open
        opened = []
        def checked(path, *args, **kwargs):
            opened.append(path)
            if path != ROOT / viewer.FOLLOWUP_AUDIT:
                raise AssertionError('Undeclared file read')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', checked):
            viewer.followup_projection(ROOT)
        self.assertEqual(opened, [ROOT / viewer.FOLLOWUP_AUDIT])

    def test_changed_followup_refuses_before_preview_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / viewer.AUDIT
            original.parent.mkdir(parents=True)
            original.write_bytes((ROOT / viewer.AUDIT).read_bytes())
            (root / viewer.FOLLOWUP_AUDIT).write_text('{}')
            out = root / 'preview'
            out.mkdir()
            (out / 'index.html').write_text('<main>original</main>')
            with self.assertRaises(ValueError):
                viewer.build(root, out)
            self.assertEqual((out / 'index.html').read_text(), '<main>original</main>')
            self.assertEqual([p.name for p in out.iterdir()], ['index.html'])


if __name__ == '__main__':
    unittest.main()
