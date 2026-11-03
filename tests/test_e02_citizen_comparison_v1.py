from collections import Counter
from copy import deepcopy
import csv
from decimal import Decimal as D
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civiclab.e02.cohort_reference_v1 import extract_reference
from civiclab.e02.citizen_comparison_v1 import (extract_candidate,assert_identity,MODELS,TARGETS,
    _compute_numeric_comparison,run_comparison,make_draws,paired_summary,distribution_hash,directional_ranges,_run_recorded_comparison)
from civiclab.e02.citizen_scenarios_v1 import TRANSFERS,scenario_targets,_check_result
from civiclab.e02.citizen_targets import convert_rows
from civiclab.e02.population import FIPS_REGION
from civiclab.e02.population_alternatives import LEVELS,calibrate,distributions as fit_distributions

ROOT=Path(__file__).resolve().parents[1]


class ComparisonFixtureTests(unittest.TestCase):
    def setUp(self):
        self.mapping=json.loads((ROOT/'configs/e02_population_mapping.json').read_text())
        self.target_config=json.loads((ROOT/'configs/e02_citizen_targets_v1.json').read_text())

    def source_row(self,**overrides):
        m=self.mapping
        row={m[k]:v for k,v in {'sample':'2','weight':'1.50','age':'25','education':'1',
             'region':'1','party':'1','race':'1','income':'1','stratum':'1','psu':'1'}.items()}
        row.update({m[k]:v for k,v in overrides.items()});return row

    def test_separate_reference_candidate_all_recodes_boundaries_exclusions(self):
        rows=[]
        for i in range(42):
            rows.append(self.source_row(sample=str(2+i%2),age=str((25,44,45,64,65,80)[i%6]),
              education=str(1+i%5),region=str(1+i%4),party=str((1,2,0,3,5,-9)[i%6]),
              race=str((1,2,3,4,5,6,-9)[i%7]),income=str((1,2,3,4,5,6,-9)[i%7]),psu=str(i+1)))
        invalid=[{'sample':'1'},{'weight':'0'},{'weight':'-1'},{'weight':'NaN'},{'weight':'inf'},
                 {'age':'24'},{'age':'81'},{'age':'bad'},{'education':'0'},{'region':'5'},
                 {'stratum':'-1'},{'psu':'bad'},{'psu':'NaN'}]
        rows.extend(self.source_row(**change) for change in invalid)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.csv'
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
            reference,a=extract_reference(path,self.mapping,20261103);candidate,b=extract_candidate(path,self.mapping,20261103)
        result=assert_identity(reference,candidate,a,b)
        self.assertEqual(result['records_checked'],42)
        self.assertEqual(a,{'outside_fresh_weighted_sample':5,'age_education_or_region_missing_outside_universe':5,'invalid_design_cluster':3})
        self.assertEqual(reference[0]['key'],('1','25-44','HS_OR_LESS','D','WHITE_NH','LOW'))
        self.assertEqual({x['key'][1] for x in reference},{'25-44','45-64','65+'})
        self.assertEqual({x['key'][2] for x in reference},{'HS_OR_LESS','SOME_COLLEGE','BA_PLUS'})
        self.assertEqual({x['key'][3] for x in reference},{'D','R','I','UNKNOWN'})
        self.assertEqual({x['key'][4] for x in reference},{'WHITE_NH','BLACK_NH','HISPANIC','OTHER_NH','UNKNOWN'})
        self.assertEqual({x['key'][5] for x in reference},{'LOW','MID','HIGH','UNKNOWN'})
        self.assertEqual({x['heldout'] for x in reference},{True,False})
        serialized=json.dumps(result)
        for field in ('weight_raw','position','design'):self.assertNotIn('"'+field+'":',serialized)
        for field,new in [('position',9999),('key',('tampered',)),('weight_raw','1.500'),('weight',2.),('design',('99','99')),('heldout',not candidate[0]['heldout'])]:
            changed=deepcopy(candidate);changed[0][field]=new
            with self.subTest(field=field):
                with self.assertRaises(ValueError):assert_identity(reference,changed,a,b)
        with self.assertRaises(ValueError):assert_identity(reference,candidate+[candidate[0]],a,b)

    def census_rows(self):
        rows=[]
        for fips in sorted(FIPS_REGION)+['72']:
            row={'GEO_ID':'0400000US'+fips,'NAME':'FICTIONAL FIXTURE'}
            for col in ('C02','C04'):
                pairs=[('001',2000),('038',1400)]+list(zip(('007','008','009','010','011','012'),(20,15,10,10,10,5)))+list(zip(('039','040','041','042','043'),('19.8',30,20,20,10)))
                for index,number in pairs:
                    key=f'S0501_{col}_{index}';row[key+'E']=str(number);row[key+'M']='1' if index in ('001','038') else '.1'
            rows.append(row)
        return rows

    def test_all_eight_fixed_transfers_preserve_rounded_sums_anchors_and_bounds(self):
        rows=self.census_rows();before=deepcopy(rows);central=convert_rows(rows,self.target_config)
        self.assertEqual(central['per_state'][0]['columns']['C02']['education']['percentage_sum'],D('99.8'))
        for name,donor,receiver in TRANSFERS:
            result,audit=scenario_targets(rows,self.target_config,central,name)
            self.assertEqual(len(audit),102);self.assertEqual(rows,before)
            self.assertEqual(result['national_published25plus_sum'],central['national_published25plus_sum'])
            self.assertEqual(audit[0]['delta_pp'],'0.04')
            self.assertEqual(D(audit[0]['perturbed_donor']),D(audit[0]['original_donor'])-D('.04'))
            self.assertEqual(D(audit[0]['perturbed_receiver']),D(audit[0]['original_receiver'])+D('.04'))
            self.assertEqual(D(audit[0]['pair_sum_before']),D(audit[0]['pair_sum_after']))
        with self.assertRaises(ValueError):scenario_targets(rows,self.target_config,central,'EDU_040_TO_041','.05')
        with self.assertRaises(ValueError):scenario_targets(rows,self.target_config,central,'NOT_FROZEN')
        # Central converter must continue rejecting invented two-decimal source observations.
        bad=deepcopy(rows);bad[0]['S0501_C02_007E']='20.04'
        with self.assertRaises(ValueError):scenario_targets(bad,self.target_config,central,'AGE_007_TO_008')

    def test_domain_clipping_and_bad_scenario_mass_are_rejected(self):
        rows=self.census_rows();r=rows[0]
        for index,n in zip(('039','040','041','042','043'),('0','.1','100','0','0')):r[f'S0501_C02_{index}E']=n
        central=convert_rows(rows,self.target_config)
        result,audit=scenario_targets(rows,self.target_config,central,'EDU_040_TO_041')
        self.assertEqual(audit[0]['delta_pp'],'0');self.assertTrue(audit[0]['zero_amplitude'])
        corrupted=deepcopy(result);corrupted['national_published25plus_sum']+=1
        with self.assertRaises(ValueError):_check_result(central,corrupted,audit)
        altered=deepcopy(audit);altered[0]['perturbed_receiver']='100.1'
        with self.assertRaises(ValueError):_check_result(central,result,altered)

    def test_forty_configuration_coverage_reuses_models_and_records_failures(self):
        train=[]
        for r,a,e in product(*LEVELS[:3]):
            for i in range(8):train.append(((r,a,e,'D' if i%2 else 'R','WHITE_NH','LOW'),1.,'cluster'+str(i)))
        targets={'region_age':{r+':'+a:1/12 for r,a in product(LEVELS[0],LEVELS[1])},
                 'region_education':{r+':'+e:1/12 for r,e in product(LEVELS[0],LEVELS[2])}}
        scenarios={name:deepcopy(targets) for name in TARGETS}
        scenarios[TARGETS[-1]]['region_age'].pop('1:25-44')
        model_ids=[]
        def observed(model,target):model_ids.append(id(model));return calibrate(model,target)
        lifecycle=[]
        with patch('civiclab.e02.citizen_comparison_v1.calibrate',side_effect=observed):
            result=_compute_numeric_comparison(train,train,scenarios,observe=lambda event,**fields:lifecycle.append((event,fields)))
        self.assertEqual(sum(e=='configuration_started' for e,_ in lifecycle),40)
        self.assertEqual(sum(e=='configuration_completed' for e,_ in lifecycle),36)
        self.assertEqual(sum(e=='configuration_failed' for e,_ in lifecycle),4)
        self.assertEqual(len(result['configurations']),40)
        self.assertEqual(len(set(model_ids)),4)
        self.assertEqual(sorted(Counter(model_ids).values()),[10]*4)
        self.assertEqual(sum(v['status']=='FAILED_CONFIGURATION' for v in result['configurations'].values()),4)
        self.assertTrue(result['shared_bootstrap_draws'])
        self.assertEqual(set(result['pre_calibration_distribution_sha256']),set(MODELS))
        for key,entry in result['configurations'].items():
            model=key.split('::')[1]
            self.assertEqual(entry['pre_calibration_distribution_sha256'],result['pre_calibration_distribution_sha256'][model])
            if entry['status']=='RECORDED':self.assertEqual(len(entry['fitted_distribution_sha256']),64)
            else:self.assertIsNone(entry['fitted_distribution_sha256'])
        for model,r in result['finite_directional_scenario_ranges'].items():
            self.assertEqual(r['attempted_directions'],8);self.assertEqual(r['recorded_directions'],7)
            self.assertEqual(r['failed_scenario_ids'],[TARGETS[-1]])
            self.assertEqual(r['finite_directional_minus_central_range_nats'],[0,0])
            self.assertEqual(r['minimum_scenario_ids'],sorted(TARGETS[2:-1]))
            self.assertEqual(r['maximum_scenario_ids'],sorted(TARGETS[2:-1]))
            self.assertIn('not a95percent',r['interpretation'])
        self.assertEqual(result['contrasts']['CITIZEN_minus_RESIDENT::I']['mean_loss_difference_nats'],0)
        self.assertEqual(result['contrasts'][TARGETS[-1]+'::H5_minus_I']['status'],'NOT_COMPUTABLE_FAILED_CONFIGURATION')

    def test_shared_bootstrap_draws_and_gating_before_real_loader_or_fit(self):
        losses=[(1.,2.,'a'),(3.,4.,'b')];clusters,draws=make_draws([(None,2.,'a'),(None,4.,'b')])
        result=paired_summary(losses,losses,clusters,draws)
        self.assertEqual(result['repetitions'],500);self.assertEqual(result['descriptive_percentile95'],[0,0])
        with patch('civiclab.e02.citizen_comparison_v1.load_config',return_value={'execution_approval':None}), \
             patch('civiclab.e02.citizen_comparison_v1.extract_candidate',side_effect=AssertionError('real load forbidden')), \
             patch('civiclab.e02.citizen_comparison_v1.distributions',side_effect=AssertionError('real fit forbidden')):
            with self.assertRaisesRegex(ValueError,'real fitting BLOCKED'):run_comparison(ROOT)

    def test_canonical_full_grid_hash_ignores_order_but_detects_probabilities(self):
        from civiclab.e02.population_alternatives import GRID
        sparse={GRID[0]:.25,GRID[-1]:.75}
        explicit={key:sparse.get(key,0.0) for key in reversed(GRID)}
        self.assertEqual(distribution_hash(sparse),distribution_hash(explicit))
        self.assertNotEqual(distribution_hash(sparse),distribution_hash({GRID[0]:.5,GRID[-1]:.5}))
        with self.assertRaises(ValueError):distribution_hash({GRID[0]:float('nan')})

    def test_directional_range_endpoint_ids_failures_and_missing_central(self):
        outputs={target+'::'+model:{'status':'RECORDED','metrics':{'weighted_joint_log_loss_nats':float(i)}}
                 for i,target in enumerate(TARGETS) for model in MODELS}
        outputs[TARGETS[-1]+'::I']={'status':'FAILED_CONFIGURATION'}
        outputs['CITIZEN_CENTRAL::H5']={'status':'FAILED_CONFIGURATION'}
        ranges=directional_ranges(outputs)
        self.assertEqual(ranges['I']['finite_directional_score_range_nats'],[2.,8.])
        self.assertEqual(ranges['I']['finite_directional_minus_central_range_nats'],[1.,7.])
        self.assertEqual(ranges['I']['minimum_scenario_ids'],[TARGETS[2]])
        self.assertEqual(ranges['I']['maximum_scenario_ids'],[TARGETS[-2]])
        self.assertEqual(ranges['I']['failed_scenario_ids'],[TARGETS[-1]])
        self.assertIsNone(ranges['H5']['finite_directional_minus_central_range_nats'])
        for target in TARGETS[2:]:outputs[target+'::H20']={'status':'FAILED_CONFIGURATION'}
        missing=directional_ranges(outputs)['H20']
        self.assertIsNone(missing['finite_directional_score_range_nats'])
        self.assertEqual(missing['minimum_scenario_ids'],[])
        self.assertEqual(len(missing['failed_scenario_ids']),8)

    def test_later_failure_and_cancellation_preserve_manifest_config_and_progress(self):
        train=[((r,a,e,'D','WHITE_NH','LOW'),1.,'synthetic'+str(i%3))
               for i,(r,a,e) in enumerate(product(*LEVELS[:3]))]
        target={'region_age':{r+':'+a:1/12 for r,a in product(LEVELS[0],LEVELS[1])},
                'region_education':{r+':'+e:1/12 for r,e in product(LEVELS[0],LEVELS[2])}}
        targets={name:deepcopy(target) for name in TARGETS}
        config=json.loads((ROOT/'configs/e02_citizen_comparison_v1.json').read_text())
        for error_class in (RuntimeError,KeyboardInterrupt):
            with self.subTest(error_class=error_class.__name__),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'configs').mkdir()
                (root/'configs/e02_citizen_comparison_v1.json').write_text(json.dumps(config))
                count=0
                def fail_later(model,margins):
                    nonlocal count
                    count+=1
                    runs=list((root/'data/processed/runs').iterdir());self.assertEqual(len(runs),1)
                    run=runs[0]
                    for filename in ('manifest.json','comparison-config.json','cohort-identity.json','rounding-scenarios.json','target-sets.json'):
                        self.assertTrue((run/filename).exists(),filename+'must precede fitting')
                    if count==2:raise error_class('injected later compute failure')
                    return calibrate(model,margins)
                def prepare():return train,train,{'status':'MOCK_FIXTURE_IDENTITY'},targets,{'kind':'MOCK_SCENARIO_FIXTURE'}
                def guarded_training(*args,**kwargs):
                    run=list((root/'data/processed/runs').iterdir())[0]
                    self.assertTrue((run/'manifest.json').exists())
                    self.assertTrue((run/'comparison-config.json').exists())
                    self.assertTrue((run/'rounding-scenarios.json').exists())
                    return fit_distributions(*args,**kwargs)
                with patch('civiclab.e02.citizen_comparison_v1.calibrate',side_effect=fail_later), \
                     patch('civiclab.e02.citizen_comparison_v1.distributions',side_effect=guarded_training):
                    with self.assertRaises(error_class):_run_recorded_comparison(root,config,prepare,kind='MOCK')
                run=list((root/'data/processed/runs').iterdir())[0]
                events=[json.loads(line) for line in (run/'events.jsonl').read_text().splitlines()]
                kinds=[e['event'] for e in events]
                self.assertLess(kinds.index('preparation_completed'),kinds.index('training_started'))
                self.assertEqual(kinds.count('configuration_started'),2)
                self.assertEqual(kinds.count('configuration_completed'),1)
                self.assertIn('execution_failed',kinds)
                summary=json.loads((run/'summary.json').read_text());failure=json.loads((run/'failure.json').read_text())
                self.assertEqual(summary['status'],'FAILED');self.assertEqual(failure['status'],'FAILED')
                self.assertEqual(failure['cancelled'],error_class is KeyboardInterrupt)
                self.assertEqual(failure['recorded_configuration_ids'],['RESIDENT::I'])
                self.assertEqual(failure['incomplete_configuration_ids'],['RESIDENT::H5'])
                self.assertTrue((run/'configurations/00.json').exists())
                self.assertTrue((run/'checksums.json').exists());self.assertFalse((run/'comparison.json').exists())
                # Failure metadata contains types/progress only, never exception text.
                self.assertNotIn('injected later compute failure',(run/'failure.json').read_text())
