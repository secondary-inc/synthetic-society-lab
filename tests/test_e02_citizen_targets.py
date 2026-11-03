from copy import deepcopy
from decimal import Decimal as D,localcontext
import json
import csv
import io
import hashlib
import zipfile
from pathlib import Path
import tempfile
import unittest
from civiclab.e02.citizen_targets import convert_column,convert_rows,decimal_strings,run_targets
from civiclab.e02.population import FIPS_REGION
from civiclab.common import sha256_file

ROOT=Path(__file__).resolve().parents[1]


class CitizenTargetTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'configs/e02_citizen_targets_v1.json').read_text())

    def row(self,fips='01'):
        row={'GEO_ID':'0400000US'+fips,'NAME':'FICTIONAL FIXTURE'}
        for col,total,adult in (('C02',2000,1400),('C04',1000,700)):
            for i,n in [('001',total),('038',adult)]+list(zip(('007','008','009','010','011','012'),(20,15,10,10,10,5)))+list(zip(('039','040','041','042','043'),(20,30,20,20,10))):
                base=f'S0501_{col}_{i}'
                row[base+'E']=str(n);row[base+'M']='1' if i in ('001','038') else '0.1'
        return row

    def test_hand_denominators_recodes_and_published_mass(self):
        result=convert_column(self.row(),'C02',self.config)
        self.assertEqual(result['age']['raw_denominator'],D(2000))
        self.assertEqual(result['education']['raw_denominator'],D(1400))
        self.assertEqual(result['age']['raw_approximate_counts'],{'25-44':D(400),'45-64':D(500),'65+':D(500)})
        self.assertEqual(result['education']['normalized_approximate_counts'],{'HS_OR_LESS':D(700),'SOME_COLLEGE':D(280),'BA_PLUS':D(420)})
        self.assertEqual(result['source_cells']['039']['moe']['unit'],'percentage points')
        self.assertEqual(result['source_cells']['038']['moe']['unit'],'persons')
        bounds=result['age']['rounding_componentwise_bounds']['25-44']
        self.assertEqual(bounds['share_lower'],D('19.95')/(D('19.95')+D('50.25')))
        self.assertEqual(bounds['share_upper'],D('20.05')/(D('20.05')+D('49.75')))

    def test_declared_normalization_and_rounding_boundary(self):
        row=self.row();row['S0501_C02_007E']='20.1';row['S0501_C02_039E']='20.1'
        result=convert_column(row,'C02',self.config)
        self.assertEqual(result['age']['raw_approximate_total'],D(1402))
        self.assertEqual(result['age']['scale_to_published25plus'],D(1400)/D(1402))
        self.assertLess(abs(sum(result['age']['normalized_approximate_counts'].values())-D(1400)),D('1e-20'))
        self.assertEqual(result['education']['percentage_sum'],D('100.1'))
        self.assertNotEqual(result['education']['scale_to_published25plus'],D(1))
        for field in ('S0501_C02_007E','S0501_C02_039E'):
            bad=self.row();bad[field]='21'
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,'inconsistent'):convert_column(bad,'C02',self.config)

    def test_geography_native_naturalized_and_region_mass(self):
        rows=[self.row(fips) for fips in sorted(FIPS_REGION)]+[self.row('72')]
        # PR deliberately has different mass; exclusion must be explicit and tested.
        rows[-1]['S0501_C02_001E']='2000000';rows[-1]['S0501_C02_038E']='1400000'
        result=convert_rows(rows,self.config)
        self.assertEqual(result['national_published25plus_sum'],D(107100))
        self.assertEqual(result['included_state_dc_rows'],51)
        self.assertEqual(result['excluded_geographies'][0]['geoid'],'0400000US72')
        self.assertTrue(any(s['geoid']=='0400000US11' for s in result['per_state']))
        for section in ('age','education'):
            for data in result['regional'].values():
                self.assertLess(abs(sum(data[section].values())-data['published25plus']),D('1e-20'))
        with localcontext() as ctx:
            ctx.prec=40
            for margins in result['targets'].values():
                self.assertLess(abs(sum(margins.values())-1),D('1e-35'))
        self.assertIsInstance(decimal_strings(result)['national_published25plus_sum'],str)
        for altered in (rows[:-1],rows[:-1]+[rows[0]]):
            with self.assertRaisesRegex(ValueError,'exactly50'):convert_rows(altered,self.config)

    def test_invalid_symbols_counts_mapping_and_moes_rejected(self):
        for field,raw in (('001E','0'),('038E','2100'),('038E','1400.5'),('007E','NaN'),
                          ('007E','(X)'),('007E','20.01'),('007M','N'),('038M','-'),('007E','-1')):
            row=self.row();row['S0501_C02_'+field]=raw
            with self.subTest(field=field,raw=raw):
                with self.assertRaises(ValueError):convert_column(row,'C02',self.config)
        row=self.row();row['S0501_C02_038M']='*****'
        result=convert_column(row,'C02',self.config)
        self.assertEqual(result['source_cells']['038']['moe']['raw'],'*****')
        self.assertNotIn('value',result['source_cells']['038']['moe'])
        rows=[self.row(s) for s in sorted(FIPS_REGION)]+[self.row('72')]
        for edit in ({'dataset':'ACSST1Y2024.S0501'},{'columns':['C02','C03','C04']},
                     {'count_rows':{'all_ages':'038','age25plus':'001'}}):
            with self.assertRaises(ValueError):convert_rows(rows,{**self.config,**edit})

    def test_source_proposal_tamper_is_preserved_as_failed_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'configs').mkdir();(root/'docs').mkdir()
            proposal=root/'docs/E02_CITIZEN_FIT_PROPOSAL.md';proposal.write_text('frozen fixture proposal')
            config=deepcopy(self.config);config['required_files']={'docs/E02_CITIZEN_FIT_PROPOSAL.md':sha256_file(proposal)}
            (root/'configs/e02_citizen_targets_v1.json').write_text(json.dumps(config))
            proposal.write_text('changed proposal')
            with self.assertRaisesRegex(ValueError,'input changed'):run_targets(root)
            runs=list((root/'data/processed/runs').iterdir())
            self.assertEqual(len(runs),1)
            self.assertFalse((runs[0]/'citizen-targets.json').exists())
            self.assertIn('failed',(runs[0]/'events.jsonl').read_text())

    def test_full_fixture_archive_replay_and_source_byte_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'configs').mkdir();(root/'docs').mkdir();(root/'reports').mkdir()
            proposal=root/'docs/E02_CITIZEN_FIT_PROPOSAL.md';proposal.write_text('MOCK methods fixture')
            audit=root/'reports/INDEPENDENT_AUDIT_E02_CITIZEN_FIT_METHODS.json'
            audit.write_text(json.dumps({'status':'PASS_METHODS_FOR_TARGET_ONLY_IMPLEMENTATION','proposal_sha256':sha256_file(proposal)}))
            rows=[self.row(s) for s in sorted(FIPS_REGION)]+[self.row('72')]
            fields=list(rows[0]);labels={f:('Geography' if f=='GEO_ID' else 'Area' if f=='NAME' else 'FIXTURE '+f) for f in fields}
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerow(labels);writer.writerows(rows)
            metadata=io.StringIO();w=csv.writer(metadata);w.writerow(['Column Name','Label']);w.writerows(labels.items())
            prefix='ACSST5Y2024.S0501';contents={prefix+'-Data.csv':stream.getvalue().encode(),
                       prefix+'-Column-Metadata.csv':metadata.getvalue().encode(),prefix+'-Table-Notes.txt':('MOCK '+prefix).encode()}
            raw_path=root/'fixture.zip'
            with zipfile.ZipFile(raw_path,'w') as z:
                for name,data in contents.items():z.writestr(name,data)
            manifest={'dataset':prefix,'local_archive':'fixture.zip','archive_bytes':raw_path.stat().st_size,'archive_sha256':sha256_file(raw_path),
                      'members':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in contents.items()},
                      'variables':{f:{'label':labels[f],'proposed_unit':'persons' if f[-4:-1] in ('001','038') else 'percent'} for f in fields if f.startswith('S0501')}}
            mp=root/'configs/e02_citizen_benchmark_acquisition.json';mp.write_text(json.dumps(manifest))
            config=deepcopy(self.config);config['required_files']={str(p.relative_to(root)):sha256_file(p) for p in (proposal,audit,mp)}
            (root/'configs/e02_citizen_targets_v1.json').write_text(json.dumps(config))
            first=run_targets(root);second=run_targets(root)
            self.assertEqual((first/'citizen-targets.json').read_bytes(),(second/'citizen-targets.json').read_bytes())
            self.assertEqual(json.loads((first/'citizen-targets.json').read_text())['national_published25plus_sum'],'107100')
            raw_path.write_bytes(raw_path.read_bytes()+b'changed source bytes')
            with self.assertRaisesRegex(ValueError,'archive bytes changed'):run_targets(root)
