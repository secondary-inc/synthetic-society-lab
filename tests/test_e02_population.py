import unittest
from civiclab.e02.population import rake, sample_profiles
from civiclab.e02.instrument import score, change


class PopulationTests(unittest.TestCase):
    def test_raking_recovers_known_margins_preserving_joint_support(self):
        cells = [{'a': a, 'b': b, 'weight': w} for a, b, w in [('x','u',1),('x','v',2),('y','u',3),('y','v',4)]]
        result, diagnostics = rake(cells, {'a': {'x': .6, 'y': .4}, 'b': {'u': .3, 'v': .7}})
        self.assertTrue(diagnostics['converged'])
        self.assertAlmostEqual(sum(c['weight'] for c in result if c['a']=='x'), .6, places=7)
        self.assertAlmostEqual(sum(c['weight'] for c in result if c['b']=='u'), .3, places=7)
        # IPF preserves odds ratios, unlike independent sampling of marginals.
        weights = [c['weight'] for c in result]
        self.assertAlmostEqual(weights[0]*weights[3]/(weights[1]*weights[2]), 4/6)

    def test_structural_zeros_and_nonconvergence_fail_closed(self):
        with self.assertRaises(ValueError):
            rake([{'a':'x','weight':1}], {'a':{'x':.5,'y':.5}})
        with self.assertRaises(ValueError):
            rake([{'a':'x','b':'x','weight':1},{'a':'y','b':'y','weight':1}],
                 {'a':{'x':.2,'y':.8},'b':{'x':.8,'y':.2}}, max_iterations=3)

    def test_profile_sampling_is_joint_and_region_stratified(self):
        cells = [{'region':str(r), 'age_bin':'25-44', 'education':'BA_PLUS','party':'D',
                  'race':'OTHER_NH','income':'HIGH','weight':r/10} for r in range(1,5)]
        fit={'cells':cells}
        a=sample_profiles(fit,12,42); b=sample_profiles(fit,12,42)
        self.assertEqual(a,b)
        self.assertEqual({r:sum(p['region']==r for p in a) for r in ('1','2','3','4')},dict.fromkeys(('1','2','3','4'),3))
        self.assertAlmostEqual(sum(p['design_weight'] for p in a),1)
        self.assertTrue(all('V240001' not in p and 'state' not in p for p in a))


class InstrumentTests(unittest.TestCase):
    def test_party_orientation_and_independent_exclusion(self):
        response={'democratic_party':80,'republican_party':20}
        self.assertEqual(score(response,'D')['primary'],60)
        self.assertEqual(score(response,'R')['primary'],-60)
        self.assertIsNone(score(response,'I')['primary'])
        self.assertEqual(score(response,'I')['absolute_gap'],60)
        self.assertEqual(change(response,{'democratic_party':90,'republican_party':10},'D')['primary'],20)

    def test_missing_negative_codes_out_of_range_and_nan_not_imputed(self):
        for v in (None,-9,-8,101,998,float('nan'),True,'50'):
            self.assertNotEqual(score({'democratic_party':v,'republican_party':30},'D')['status'],'VALID')
        self.assertIsNone(change({'democratic_party':None},{'democratic_party':70,'republican_party':30},'D')['primary'])
