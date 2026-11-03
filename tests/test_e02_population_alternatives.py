from itertools import product
import math
import unittest
from civiclab.e02.population_alternatives import (
    GRID,LEVELS,distributions,calibrate,score,paired_interval)


class PopulationAlternativeTests(unittest.TestCase):
    def cohort(self):
        rows=[]
        for r,a,e in product(*LEVELS[:3]):
            for i in range(8):
                p,race,income=('D','HISPANIC','LOW') if i%2 else ('R','WHITE_NH','HIGH')
                rows.append(((r,a,e,p,race,income),1.,str(i)))
        return rows

    def test_positive_full_joint_scale_invariance_and_association_recovery(self):
        train=self.cohort();ind,hier=distributions(train)
        self.assertEqual(len(GRID),2880)
        self.assertEqual(set(ind),set(GRID));self.assertEqual(set(hier),set(GRID))
        self.assertAlmostEqual(sum(hier.values()),1)
        self.assertTrue(all(p>0 for p in hier.values()))
        self.assertLess(score(hier,train)[0]['weighted_joint_log_loss_nats'],
                        score(ind,train)[0]['weighted_joint_log_loss_nats'])
        ind2,hier2=distributions([(k,w*17,c) for k,w,c in train])
        for k in GRID:
            self.assertAlmostEqual(ind[k],ind2[k]);self.assertAlmostEqual(hier[k],hier2[k])

    def test_matched_calibration_and_common_score_floor(self):
        ind,hier=distributions(self.cohort())
        targets={'region_age':{r+':'+a:1/12 for r,a in product(LEVELS[0],LEVELS[1])},
                 'region_education':{r+':'+e:1/12 for r,e in product(LEVELS[0],LEVELS[2])}}
        for model in (ind,hier):
            calibrated,d=calibrate(model,targets)
            self.assertLess(d['max_absolute_margin_residual'],1e-8)
            self.assertEqual(set(calibrated),set(GRID))
        test=[(GRID[0],1.,'a'),(GRID[-1],3.,'b')]
        sparse={GRID[0]:1.}
        result,losses=score(sparse,test)
        expected=-(math.log(1-1e-9+1e-9/2880)+3*math.log(1e-9/2880))/4
        self.assertAlmostEqual(result['weighted_joint_log_loss_nats'],expected)
        self.assertEqual(result['raw_weighted_joint_support_coverage'],.25)
        self.assertEqual(paired_interval(losses,losses,12,20)['percentile_95_cluster_bootstrap'],[0,0])
        with self.assertRaises(ValueError):score(sparse,test,0)
        with self.assertRaises(ValueError):distributions([],5)
        with self.assertRaises(ValueError):distributions(self.cohort(),0)
        with self.assertRaises(ValueError):paired_interval(losses,losses[:-1],1,20)
