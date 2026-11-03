"""Independent formula, validity and leakage-boundary checks; fictional fixtures."""
import copy
from pathlib import Path
import tempfile
import unittest

from civiclab.common import canonical_hash
from civiclab.e01.pipeline import (validate_race, validate_pair, predict,
                                  freeze_predictions, evaluate, compare,
                                  aggregate_race, audit_returns)

H = 'a' * 64


def race(year=2024, office='HOUSE', seat=None, vintage='DEMO-map'):
    district = '01' if office == 'HOUSE' else 'STATEWIDE'
    return {'race_id': f'{year}-PA-{office}-{district}' + (f'-C{seat}' if office == 'SENATE' else ''),
            'year': year, 'state': 'PA', 'office': office, 'district': district,
            'seat_class': seat, 'stage': 'GEN', 'special': False,
            'election_date': f'{year}-11-05', 'cutoff': f'{year}-11-01', 'status': 'RETROSPECTIVE',
            'geography': {'vintage': vintage, 'official_source': 'DEMO verified fixture', 'sha256': H, 'verified': True},
            'candidates': [{'candidate_id': p, 'name': f'DEMO {p}', 'party': p,
                            'official_ballot_source': 'DEMO official ballot', 'sha256': H, 'verified': True}
                           for p in ('DEMOCRAT', 'REPUBLICAN')]}


def feature(office='HOUSE'):
    return {'race_id': f'DEMO-{office}', 'office': office, 'prior_margin_pp': 10,
            'national_shift_pp': -3, 'incumbency_adjustment_pp': 2,
            'feature_as_of': '2023-01-01', 'cutoff': '2024-11-01', 'source_hashes': [H]}


def row(candidate='D', party='DEMOCRAT', votes='60', mode='TOTAL', **kw):
    return {'year': '2024', 'state_po': 'PA', 'office': 'US HOUSE', 'district': '01',
            'stage': 'GEN', 'date': '2024-11-05', 'special': 'FALSE', 'county_fips': '42001',
            'precinct': 'DEMO-1', 'candidate': candidate, 'party_detailed': party,
            'votes': votes, 'mode': mode, **kw}


class ManifestTests(unittest.TestCase):
    def test_verified_manifest_and_house_pair(self):
        validate_race(race())
        validate_pair(race(2022), race(2024))

    def test_missing_ballot_evidence(self):
        r = race()
        r['candidates'][0]['verified'] = False
        with self.assertRaisesRegex(ValueError, 'ballot'):
            validate_race(r)

    def test_uncontested_and_duplicate_ids(self):
        for r in (race(), race()):
            if len(r['candidates']) == 2:
                r['candidates'].pop()
            with self.assertRaises(ValueError):
                validate_race(r)
        r = race()
        r['candidates'][1]['candidate_id'] = r['candidates'][0]['candidate_id']
        with self.assertRaises(ValueError):
            validate_race(r)

    def test_senate_different_classes_rejected(self):
        with self.assertRaisesRegex(ValueError, 'seat mismatch'):
            validate_pair(race(2022, 'SENATE', 3), race(2024, 'SENATE', 1))
        with self.assertRaisesRegex(ValueError, '6-year'):
            validate_pair(race(2022, 'SENATE', 1), race(2024, 'SENATE', 1))
        validate_pair(race(2018, 'SENATE', 1), race(2024, 'SENATE', 1))

    def test_changed_geography_requires_reaggregation(self):
        with self.assertRaisesRegex(ValueError, 'changed maps'):
            validate_pair(race(2022, vintage='old'), race(2024))
        x = {'verified': True, 'source_vintage': 'old', 'target_vintage': 'DEMO-map',
             'sha256': H, 'method': 'exact_reaggregation', 'reaggregated_returns_sha256': H}
        validate_pair(race(2022, vintage='old'), race(2024), x)
        x['method'] = 'population_weighted_guess'
        with self.assertRaises(ValueError):
            validate_pair(race(2022, vintage='old'), race(2024), x)

    def test_date_stage_status_guards(self):
        for key, value in [('stage', 'RUNOFF'), ('special', True), ('status', 'PROSPECTIVE'), ('cutoff', '2024-11-05')]:
            r = race()
            r[key] = value
            with self.assertRaises(ValueError):
                validate_race(r)


class ForecastTests(unittest.TestCase):
    def test_real_execution_is_blocked_without_evidence(self):
        with self.assertRaisesRegex(ValueError, 'REAL forecast execution blocked'):
            freeze_predictions([feature()], dataset_kind='REAL', config={})

    def test_formula_and_clamp(self):
        self.assertEqual(predict(feature())['predicted_margin_pp'], 9)
        f = feature()
        f['prior_margin_pp'] = 100
        f['national_shift_pp'] = 5
        self.assertEqual(predict(f)['predicted_margin_pp'], 100)

    def test_feature_leak_and_invalid_values_rejected(self):
        for key, val in [('observed_margin_pp', 100), ('live_returns', {})]:
            f = {**feature(), key: val}
            with self.assertRaisesRegex(ValueError, 'extra'):
                predict(f)
        for val in (float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                predict({**feature(), 'prior_margin_pp': val})
        with self.assertRaisesRegex(ValueError, 'post-cutoff'):
            predict({**feature(), 'feature_as_of': '2024-11-06'})

    def test_freeze_and_independent_evaluation(self):
        frozen = freeze_predictions([feature()], dataset_kind='DEMO', config={'method': 'S0'})
        o = [{'race_id': 'DEMO-HOUSE', 'office': 'HOUSE', 'observed_margin_pp': 5}]
        result = evaluate(frozen, o, outcome_source_sha256=H)
        self.assertEqual(result['by_office']['HOUSE']['macro_mae_pp'], 4)
        frozen['predictions'][0]['predicted_margin_pp'] = 5
        with self.assertRaisesRegex(ValueError, 'freeze hash'):
            evaluate(frozen, o, outcome_source_sha256=H)

    def test_holdout_same_races_and_offices(self):
        frozen = freeze_predictions([feature()], dataset_kind='DEMO', config={})
        for o in ([{'race_id': 'OTHER', 'office': 'HOUSE', 'observed_margin_pp': 0}],
                  [{'race_id': 'DEMO-HOUSE', 'office': 'SENATE', 'observed_margin_pp': 0}]):
            with self.assertRaises(ValueError):
                evaluate(frozen, o, outcome_source_sha256=H)

    def test_matched_comparison(self):
        f = freeze_predictions([feature()], dataset_kind='DEMO', config={})
        r = evaluate(f, [{'race_id': 'DEMO-HOUSE', 'office': 'HOUSE', 'observed_margin_pp': 0}], outcome_source_sha256=H)
        conditions = {'race_ids': ['DEMO-HOUSE'], 'historical_cutoff': '2024-11-01',
                      'selection_rule': 'fixed DEMO', 'feature_access': 'same prior', 'compute_policy': 'S0 deterministic'}
        self.assertEqual(compare(r, r, simple_conditions=conditions, advanced_conditions=conditions)['paired_differences'][0]['advanced_minus_simple_absolute_error_pp'], 0)
        with self.assertRaises(ValueError):
            compare(r, r, simple_conditions=conditions, advanced_conditions={**conditions, 'compute_policy': 'different'})
        with self.assertRaises(ValueError):
            compare(r, r, simple_conditions={}, advanced_conditions={})


class ReturnsTests(unittest.TestCase):
    def aggregate(self, rows, **kw):
        mapping = {'D|DEMOCRAT': 'DEMOCRAT', 'D|WORKING FAMILIES': 'DEMOCRAT', 'R|REPUBLICAN': 'REPUBLICAN'}
        return aggregate_race(rows, race(), accepted_modes={'TOTAL'}, party_line_map=mapping,
                              unit_fields=('county_fips', 'precinct'), **kw)

    def test_formula_fusion_and_denominator(self):
        result = self.aggregate([row(), row('D', 'WORKING FAMILIES', '10'), row('R', 'REPUBLICAN', '30')])
        self.assertEqual(result['democratic_votes'], 70)
        self.assertEqual(result['two_party_denominator'], 100)
        self.assertEqual(result['observed_margin_pp'], 40)

    def test_no_total_plus_component_double_count(self):
        with self.assertRaises(ValueError):
            self.aggregate([row(), row(mode='ELECTION DAY'), row('R', 'REPUBLICAN', '40')])

    def test_duplicates_and_unresolved_fusion(self):
        for rows in ([row(), row()], [row(party='UNKNOWN')]):
            with self.assertRaises(ValueError):
                self.aggregate(rows)

    def test_redaction_sentinel_runoff(self):
        for bad in (row(votes='*'), row(votes='-1'), row(votes='1'), row(stage='RUNOFF'), row(date='2024-12-01')):
            with self.assertRaises(ValueError):
                self.aggregate([bad, row('R', 'REPUBLICAN', '40')])
        # Genuine precinct counts of 1 are legal only after source-specific adjudication.
        self.aggregate([row(votes='1'), row('R', 'REPUBLICAN', '40')], one_vote_policy='documented_real_count')

    def test_real_schema_audit_not_aggregation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'DEMO.csv'
            import csv
            rows = [row(), row(votes='*', mode='ELECTION DAY')]
            with p.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0])
                writer.writeheader()
                writer.writerows(rows)
            report = audit_returns(p)
            self.assertEqual(report['counts']['rows'], 2)
            self.assertEqual(report['counts']['redacted_or_missing_votes'], 1)
            self.assertEqual(report['states_with_TOTAL_and_components'], ['PA'])
            self.assertNotIn('observed_margin_pp', report)


class HistoricalSourceTests(unittest.TestCase):
    """Fictional parser fixtures exercise actual source-specific failure modes."""
    def test_fec_general_column_fusion_and_party(self):
        from civiclab.e01.historical import official_candidate_votes
        rows=[{'line':'(I) Example, Amy  Combined Parties:'.ljust(80)+'100 60.00%', 'general_start':80,'pdf_page':2},
              {'line':'Example, Amy  D  50 90.00%'.ljust(80)+'[80] [48.00%]', 'general_start':80,'pdf_page':2},
              {'line':'Example, Amy  WF'.ljust(80)+'[20] [12.00%]', 'general_start':80,'pdf_page':2}]
        match=official_candidate_votes(rows,'Amy Example',2018,expected_party='DEMOCRAT')
        self.assertEqual(match['votes'],100)
        with self.assertRaisesRegex(ValueError,'party mismatch'):
            official_candidate_votes(rows,'Amy Example',2018,expected_party='REPUBLICAN')

    def test_clerk_fusion_does_not_add_blanks_or_other_votes(self):
        from civiclab.e01.historical import official_candidate_votes
        rows=[{'line':line,'pdf_page':4} for line in [
            'Amy Example, Democrat ........ 100', 'Working Families ........ 20',
            'Blanks ........ 500', 'All Others ........ 10',
            'Bob Other, Republican ........ 90']]
        self.assertEqual(official_candidate_votes(rows,'Amy Example',2024,expected_party='DEMOCRAT')['votes'],120)
        self.assertEqual(official_candidate_votes(rows,'Bob Other',2024,expected_party='REPUBLICAN')['votes'],90)

    def test_explicit_alias_not_fuzzy_matching(self):
        from civiclab.e01.historical import official_candidate_votes
        rows=[{'line':'Typo, Tony  R'.ljust(80)+'12 30.00%', 'general_start':80,'pdf_page':2}]
        with self.assertRaisesRegex(ValueError,'not unique'):
            official_candidate_votes(rows,'Tony Correct',2018)
        self.assertEqual(official_candidate_votes(rows,'Tony Correct',2018,official_family='TYPO',expected_party='REPUBLICAN')['votes'],12)

    def test_scope_excludes_house_and_rejects_ambiguous_candidate(self):
        from civiclab.e01.historical import official_sections,official_candidate_votes
        pages=[{'pdf_page':1,'text':'MAINE\nFOR UNITED STATES SENATOR\nAmy Example, Democrat .... 20\nFOR UNITED STATES REPRESENTATIVE\nAmy Example, Democrat .... 500'}]
        section=official_sections(pages,2024)['ME']
        self.assertEqual(official_candidate_votes(section,'Amy Example',2024)['votes'],20)
        with self.assertRaisesRegex(ValueError,'not unique'):
            official_candidate_votes(section+section,'Amy Example',2024)

    def test_discovery_party_lines_sum_without_reallocating_independent(self):
        from civiclab.e01.historical import major_candidates
        rows=[{'candidate':n,'party':p,'count':v} for n,p,v in [('Amy','democrat',10),('Amy','working families',2),('Bob','republican',8),('Other','independent',50)]]
        self.assertEqual([r['votes'] for r in major_candidates(rows)],[12,8])
        with self.assertRaises(ValueError):major_candidates(rows+[{'candidate':'Third','party':'democrat','count':1}])

    def test_scoped_runner_rejects_duplicates_and_changed_inputs(self):
        from civiclab.e01.historical import _frozen_real
        f=feature('SENATE');f['race_id']=race(2024,'SENATE',1)['race_id']
        prepared={'manifest':[{'prior':race(2018,'SENATE',1),'target':race(2024,'SENATE',1)}],'features':[f]}
        with self.assertRaisesRegex(ValueError,'coverage'):_frozen_real([f,f],prepared,'S0')
        changed={**f,'prior_margin_pp':77}
        with self.assertRaisesRegex(ValueError,'differ'):_frozen_real([changed],prepared,'S0')
        with self.assertRaisesRegex(ValueError,'unapproved'):_frozen_real([f],prepared,'TUNED')


if __name__ == '__main__':
    unittest.main()
