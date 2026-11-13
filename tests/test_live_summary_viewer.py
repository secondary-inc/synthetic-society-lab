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

    def test_wrapper_candidate_allowlist_matches_signed_magnitude_and_topics(self):
        # Candidate projection only; independent actual acceptance is separate.
        a = json.loads((ROOT / 'reports/E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json').read_bytes())
        s = viewer.wrapper_summary(a)
        self.assertEqual((s['actual_responses'],s['planned_slots']), (40,40))
        self.assertEqual((s['primary']['mean'],s['shown']['mean'],s['interaction']['mean'],s['magnitude']['mean']), (.625,-3.125,-3.75,2.5))
        self.assertEqual((s['expansion_count'],s['contraction_count'],s['unchanged_magnitude_count'],s['reversal_count']), (1,1,6,0))
        self.assertEqual([r['omitted'] for r in s['units']], [0,5,0,0,0,0,0,0])
        self.assertEqual([r['shown'] for r in s['units']], [-25,0,0,0,0,0,0,0])
        self.assertEqual([t['mean'] for t in s['primary_by_topic']], [0,1.25])
        self.assertEqual(s['factual'],dict(correct=40,asked=40,planned=40,errors=0,missing_invalid=0,unasked=0))
        self.assertTrue(s['all_items_valid'])
        self.assertEqual(s['all_research_generations'],147)
        self.assertEqual(s['conservative_exposure_usd'],'0.012221')
        a['PRIVATE_UNRELATED']={'generation_id':'never-export','source_files':['data/processed/private'],'response':'not-for-viewer'}
        self.assertEqual(viewer.wrapper_summary(a),s)
        for field in ('profile_id','scored_phases','generation_id','data/processed/','native_tokens','request_hash','PRIVATE_UNRELATED'):
            self.assertNotIn(field,json.dumps(s))

    def test_wrapper_renderer_preserves_denominators_nulls_and_does_not_call_signed_decrease_attenuation(self):
        a=json.loads((ROOT/'reports/E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json').read_bytes())
        s=viewer.wrapper_summary(a)
        s.update(source_audit='<script>audit</script>',source_audit_sha256='AUTHORED',source_aggregate='<private>',source_aggregate_sha256='AUTHORED')
        page=viewer.render_wrapper(s)
        self.assertIn('+0.625',page);self.assertIn('-3.125',page);self.assertIn('-3.75',page);self.assertIn('+2.5',page)
        self.assertIn('Negative signed interaction does not establish attenuation',page)
        self.assertIn('Mean absolute wrapper magnitude increased',page)
        self.assertIn('8 / 8 matched units',page);self.assertIn('40/40',page)
        self.assertIn('1 expansion',page);self.assertIn('1 contraction',page);self.assertIn('6 unchanged',page)
        self.assertIn('November 13 UTC',page);self.assertIn('147 generations',page)
        self.assertNotIn('<script>',page);self.assertNotIn('<private>',page)
        self.assertIn('&lt;script&gt;',page)
        s['primary']['mean']=None;s['primary']['complete']=0
        s['matched_omitted']['mean']=None;s['matched_omitted']['complete']=0
        s['matched_shown']['complete']=3;s['interaction']['complete']=3;s['magnitude']['complete']=3
        s['all_items_valid']=False;s['units'][0]['omitted']=None
        page=viewer.render_wrapper(s)
        self.assertIn('Not estimable',page);self.assertIn('3 / 8 matched units',page)
        self.assertIn('valid survey items have distinct denominators',page)

    def test_wrapper_candidate_refuses_unknown_dispositions_duplicate_or_foreign_units(self):
        from copy import deepcopy
        original=json.loads((ROOT/'reports/E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json').read_bytes())
        for change in ('phase','factual','negative','total','duplicate','foreign','topic'):
            a=deepcopy(original)
            if change=='phase':a['analysis']['phase_counts']['UNKNOWN']=1
            if change=='factual':a['all_planned_factual_dispositions']={'UNKNOWN':40}
            if change=='negative':a['analysis']['phase_counts']={'ANSWER':-1}
            if change=='total':a['all_planned_factual_dispositions']={'CORRECT':39}
            if change=='duplicate':a['analysis']['wrapper_contrasts']['SHOWN']['unit_values'][1]=deepcopy(a['analysis']['wrapper_contrasts']['SHOWN']['unit_values'][0])
            if change=='foreign':a['analysis']['visibility_interaction']['unit_values'][0]['profile_id']='foreign'
            if change=='topic':
                for key in ('primary_wrapper_omitted','visibility_interaction','absolute_wrapper_magnitude_change'):
                    a['analysis'][key]['unit_values'][0]['topic_id']='OTHER'
                a['analysis']['wrapper_contrasts']['SHOWN']['unit_values'][0]['topic_id']='OTHER'
            with self.subTest(change=change),self.assertRaises(ValueError):viewer.wrapper_summary(a)

    def test_wrapper_candidate_same_unit_join_ignores_input_order(self):
        a=json.loads((ROOT/'reports/E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json').read_bytes())
        expected=viewer.wrapper_summary(a)
        for x in (a['analysis']['wrapper_contrasts']['SHOWN'],a['analysis']['visibility_interaction'],a['analysis']['absolute_wrapper_magnitude_change']):x['unit_values'].reverse()
        self.assertEqual(viewer.wrapper_summary(a),expected)

    def test_wrapper_unaccepted_pins_refuse_without_any_file_access(self):
        with patch.object(viewer,'WRAPPER_AUDIT_SHA256',None),patch.object(Path,'open',side_effect=AssertionError('premature evidence read')):
            with self.assertRaises(ValueError):viewer.wrapper_projection(ROOT)

    def test_three_prior_study_projections_and_rendered_sections_unchanged(self):
        from civiclab.common import canonical_bytes
        expected = [('projection','render','f5adf220196ee50871a9f00c1b7a96bd00ae75dfc822ea9e67846844888af2c8','127250987b21b4777bf8277f830da1b152e3a6ea17bc91f26af7f087fd383fe5'),
                    ('followup_projection','render_followup','c3b50e726ed63c9c19793dfafe738d278a562c47e85ea8fb553c37a5b5d6afe3','8cbb673157df11656c4be18a646e3d158af2905d94d41a8b2bbc835a2bbb35d9'),
                    ('crossmodel_projection','render_crossmodel','db5abfc3c85d55044be902e0811ee942ab4f6ed26d9239719268d236f65b77d9','d9eff56dd88739bc23bf47cd7518106ba6617159ca18fe49afd095b3df977687')]
        for project,render,projection_hash,html_hash in expected:
            value=getattr(viewer,project)(ROOT)
            self.assertEqual(hashlib.sha256(canonical_bytes(value)).hexdigest(),projection_hash)
            self.assertEqual(hashlib.sha256(getattr(viewer,render)(value).encode()).hexdigest(),html_hash)

    def test_wrapper_missing_wrong_unasked_quality_denominators_stay_distinct(self):
        # Authored public-field mapping oracle, not an admitted altered result.
        a=json.loads((ROOT/'reports/E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json').read_bytes())
        a['analysis']['phase_counts']={'ANSWER':39,'NOT_ATTEMPTED':1}
        a['all_planned_factual_dispositions']={'CORRECT':37,'INCORRECT':1,'MISSING_NULL':1,'UNASKED':1}
        s=viewer.wrapper_summary(a)
        self.assertEqual(s['factual'],dict(correct=37,asked=39,planned=40,errors=1,missing_invalid=1,unasked=1))
        self.assertEqual((s['actual_responses'],s['unattempted_slots']),(39,1))
        self.assertFalse(s['all_items_valid'])
        s.update(source_audit='AUTHORED',source_audit_sha256='AUTHORED',source_aggregate='AUTHORED',source_aggregate_sha256='AUTHORED')
        page=viewer.render_wrapper(s)
        self.assertIn('37/39',page);self.assertIn('37/40',page)
        self.assertIn('Observed wrong: 1',page);self.assertIn('unasked: 1',page)

    def test_wrapper_two_public_file_admission_and_tamper_guards_authored_receipt(self):
        # A fake receipt tests engineering admission mechanics only.
        from copy import deepcopy
        aggregate=(ROOT/'reports/E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json').read_bytes()
        receipt={'overall_status':'AUTHORED_TEST_PASS','input_pins':{viewer.WRAPPER_AGGREGATE:{'bytes':len(aggregate),'sha256':hashlib.sha256(aggregate).hexdigest()}},'PRIVATE_UNRELATED':{'generation_id':'never-export','source_files':['data/processed/private']}}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);audit_path=root/viewer.WRAPPER_AUDIT;agg_path=root/viewer.WRAPPER_AGGREGATE
            audit_path.parent.mkdir();agg_path.write_bytes(aggregate)
            for change in ('none','audit_bytes','aggregate_bytes','status','binding','oversize','symlink'):
                rec=deepcopy(receipt);body=aggregate
                if change=='status':rec['overall_status']='NOT_ACCEPTED'
                if change=='binding':rec['input_pins'][viewer.WRAPPER_AGGREGATE]['sha256']='0'*64
                raw=json.dumps(rec,sort_keys=True).encode();audit_path.write_bytes(raw)
                if agg_path.is_symlink():agg_path.unlink()
                agg_path.write_bytes(body)
                if change=='audit_bytes':audit_path.write_bytes(raw+b' ')
                if change=='aggregate_bytes':agg_path.write_bytes(aggregate+b' ')
                if change=='oversize':agg_path.write_bytes(b' '*1_000_001)
                if change=='symlink':agg_path.unlink();agg_path.symlink_to(ROOT/viewer.WRAPPER_AGGREGATE)
                opened=[];original=Path.open
                def checked(path,*args,**kwargs):
                    self.assertIn(path,[audit_path,agg_path]);opened.append(path);return original(path,*args,**kwargs)
                with patch.multiple(viewer,WRAPPER_AUDIT_SHA256=hashlib.sha256(raw).hexdigest(),WRAPPER_AGGREGATE_SHA256=hashlib.sha256(aggregate).hexdigest(),WRAPPER_AUDIT_STATUS='AUTHORED_TEST_PASS'),patch.object(Path,'open',checked):
                    if change=='none':
                        result=viewer.wrapper_projection(root)
                        self.assertEqual(opened,[audit_path,agg_path]);self.assertEqual(result['primary']['mean'],.625)
                        self.assertNotIn('PRIVATE_UNRELATED',json.dumps(result));self.assertNotIn('generation_id',json.dumps(result))
                    else:
                        with self.subTest(change=change),self.assertRaises(ValueError):viewer.wrapper_projection(root)

    def test_wrapper_refusal_preserves_existing_outputs_before_any_new_write(self):
        # Force only the new admission gate; no accepted fourth-study receipt.
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);original=b'<main>ORIGINAL</main>\r\n';snapshot=b'{"old":true}\n'
            (out/'index.html').write_bytes(original);(out/'snapshot.json').write_bytes(snapshot)
            with patch.object(viewer,'WRAPPER_AUDIT_SHA256','AUTHORED_ONLY'),patch.object(viewer,'wrapper_projection',side_effect=ValueError('authored refusal')):
                with self.assertRaises(ValueError):viewer.build(ROOT,out)
            self.assertEqual((out/'index.html').read_bytes(),original)
            self.assertEqual((out/'snapshot.json').read_bytes(),snapshot)
            self.assertEqual(sorted(p.name for p in out.iterdir()),['index.html','snapshot.json'])

    def test_wrapper_reads_exact_accepted_public_pair_only(self):
        opened=[];original=Path.open
        def checked(path,*args,**kwargs):
            self.assertIn(path,[ROOT/viewer.WRAPPER_AUDIT,ROOT/viewer.WRAPPER_AGGREGATE]);opened.append(path);return original(path,*args,**kwargs)
        with patch.object(Path,'open',checked):result=viewer.wrapper_projection(ROOT)
        self.assertEqual(opened,[ROOT/viewer.WRAPPER_AUDIT,ROOT/viewer.WRAPPER_AGGREGATE])
        self.assertEqual(result['source_audit_sha256'],viewer.WRAPPER_AUDIT_SHA256)
        self.assertEqual(result['source_aggregate_sha256'],viewer.WRAPPER_AGGREGATE_SHA256)

    def test_changed_wrapper_real_evidence_refuses_before_any_output(self):
        names=(viewer.AUDIT,viewer.FOLLOWUP_AUDIT,viewer.CROSSMODEL_AUDIT,viewer.CROSSMODEL_AGGREGATE,viewer.WRAPPER_AUDIT,viewer.WRAPPER_AGGREGATE)
        for changed in (viewer.WRAPPER_AUDIT,viewer.WRAPPER_AGGREGATE):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for name in names:
                    target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(b'{}' if name==changed else (ROOT/name).read_bytes())
                out=root/'preview';out.mkdir();(out/'index.html').write_bytes(b'<main>BEFORE</main>')
                with self.assertRaises(ValueError):viewer.build(root,out)
                self.assertEqual((out/'index.html').read_bytes(),b'<main>BEFORE</main>')
                self.assertEqual([p.name for p in out.iterdir()],['index.html'])

    def test_four_study_build_opens_six_public_evidence_files_and_preserves_history(self):
        public={ROOT/name for name in (viewer.AUDIT,viewer.FOLLOWUP_AUDIT,viewer.CROSSMODEL_AUDIT,viewer.CROSSMODEL_AGGREGATE,viewer.WRAPPER_AUDIT,viewer.WRAPPER_AGGREGATE)}
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);(out/'index.html').write_bytes(b'<main>HISTORICAL</main>\r\n');(out/'snapshot.json').write_bytes(b'{"old":1}\n')
            opened=[];original=Path.open
            def checked(path,*args,**kwargs):
                self.assertTrue(path in public or path.parent==out,'undeclared input/output path');opened.append(path);return original(path,*args,**kwargs)
            with patch.object(Path,'open',checked):viewer.build(ROOT,out)
            self.assertEqual(set(path for path in opened if path in public),public)
            self.assertEqual(sum(path in public for path in opened),6)
            page=(out/'index.html').read_text();summary=json.loads((out/'live-summary.json').read_bytes())
            for section in ('wrapper-visibility-summary','crossmodel-summary','followup-summary'):
                self.assertEqual(page.count('id="'+section+'"'),1)
            self.assertEqual(summary['wrapper_result']['primary']['mean'],.625)
            self.assertEqual((out/'historical-preview.html').read_bytes(),b'<main>HISTORICAL</main>\r\n')
            self.assertEqual((out/'snapshot.json').read_bytes(),b'{"old":1}\n')
            for forbidden in ('generation_id','scored_phases','native_tokens','data/processed/'):
                self.assertNotIn(forbidden,json.dumps(summary))


if __name__ == '__main__':
    unittest.main()
