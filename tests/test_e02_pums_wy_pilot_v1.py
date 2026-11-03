from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
import zipfile
from urllib.error import HTTPError
from civiclab.e02.pums_wy_pilot_v1 import (aggregate_rows,aggregate_archive,acquire_pilot,stream_download,validate_config)

ROOT=Path(__file__).resolve().parents[1]


class PumsPilotFixtures(unittest.TestCase):
    def setUp(self):self.config=json.loads((ROOT/'configs/e02_pums_wy_pilot_v1.json').read_text())

    def row(self,**kwargs):
        r={'RT':'P','STATE':'56','AGEP':'18','CIT':'1','SCHL':'17','RELSHIPP':'20','PWGTP':'2'}
        r.update({'PWGTP'+str(i):'1' for i in range(1,81)})
        r.update({f:'0' for f in self.config['allocation_flags']});r.update(kwargs);return r

    def test_hand_weight_sdr_covariance_and_ratio_replicate_denominators(self):
        a=self.row();b=self.row(AGEP='65',SCHL='21',PWGTP='3')
        b.update({'PWGTP'+str(i):'4' for i in range(1,81)})
        r=aggregate_rows([a,b],self.config)
        self.assertEqual(r['point_person_weight_sum'],5);self.assertFalse(r['person_weight_rescaled'])
        cell=r['cells']['18-24:HS_OR_LESS'];self.assertEqual(cell['count_uncertainty']['variance_sdr'],4)
        self.assertAlmostEqual(cell['count_uncertainty']['moe90'],3.29)
        self.assertEqual(r['count_covariance_sdr']['18-24:HS_OR_LESS']['65+:BA_PLUS'],-4)
        self.assertAlmostEqual(cell['share_uncertainty']['variance_sdr'],.16)
        self.assertIn('ZERO_ESTIMATE',r['cells']['25-44:BA_PLUS']['count_uncertainty']['status'])

    def test_signed_replicates_and_identical_eligibility_are_preserved(self):
        a=self.row(PWGTP1='-1',PWGTP2='0');b=self.row(CIT='5',PWGTP='7')
        c=self.row(RELSHIPP='37');d=self.row(RELSHIPP='38');e=self.row(AGEP='17')
        r=aggregate_rows([a,b,c,d,e],self.config)
        self.assertEqual(r['retained_unweighted_count'],1)
        self.assertEqual(r['cells']['18-24:HS_OR_LESS']['replicate_sums'][:2],[-1,0])
        self.assertEqual(r['exclusion_counts'],{'noncitizen':1,'group_quarters':2,'under18':1})
        self.assertEqual(r['cells']['18-24:HS_OR_LESS']['share_uncertainty']['status'],'BLOCKED_NONPOSITIVE_REPLICATE_DENOMINATOR')
        for cit in ('1','2','3','4'):
            self.assertEqual(aggregate_rows([self.row(CIT=cit)],self.config)['retained_unweighted_count'],1)

    def test_age_education_boundaries_allocations_and_no_identifier_export(self):
        rows=[self.row(AGEP=str(a),SCHL=str(e),FAGEP='1',SERIALNO='DO_NOT_EXPORT') for a,e in ((18,1),(24,17),(25,18),(44,20),(45,21),(64,24),(65,21),(99,21))]
        r=aggregate_rows(rows,self.config);text=json.dumps(r)
        self.assertEqual(r['retained_unweighted_count'],8)
        self.assertNotIn('DO_NOT_EXPORT',text);self.assertNotIn('SERIALNO',text)
        self.assertEqual(r['cells']['25-44:SOME_COLLEGE']['count'],2)
        self.assertEqual(r['cells']['65+:BA_PLUS']['allocated_counts']['FAGEP'],2)
        self.assertTrue(all(c['low_support'] for c in r['cells'].values()))

    def test_domains_missing_values_and_resource_limits_fail_closed(self):
        for update in ({'STATE':'01'},{'RT':'H'},{'CIT':'0'},{'AGEP':'NaN'},{'SCHL':''},{'RELSHIPP':'19'},{'PWGTP':'0'},{'PWGTP1':'-10000'},{'FSCHLP':'2'}):
            with self.subTest(update=update):
                with self.assertRaises(ValueError):aggregate_rows([self.row(**update)],self.config)
        c=deepcopy(self.config);c['limits']['maximum_rows']=1
        with self.assertRaisesRegex(ValueError,'row ceiling'):aggregate_rows([self.row(),self.row()],c)
        ticks=iter([0,121])
        with self.assertRaisesRegex(ValueError,'deadline'):aggregate_rows([self.row()],self.config,clock=lambda:next(ticks))
        c=deepcopy(self.config);c['limits']['compressed_bytes']=0
        with self.assertRaises(ValueError):validate_config(c)

    def zip_fixture(self,path,*,member='psam_p56.csv',rows=None):
        rows=rows or [self.row()];s=io.StringIO();w=csv.DictWriter(s,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
        with zipfile.ZipFile(path,'w') as z:z.writestr(member,s.getvalue())

    def test_archive_headers_path_safety_count_and_actual_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.zip';self.zip_fixture(p)
            c=deepcopy(self.config);c['limits']['expected_person_rows']=1
            result=aggregate_archive(p,c)
            self.assertGreater(result['source']['actual_uncompressed_bytes'],0)
            self.assertEqual(result['source']['required_projection'],c['required_fields'])
            with self.assertRaisesRegex(ValueError,'record count'):aggregate_archive(p,self.config)
            for member in ('../psam_p56.csv','psam_p01.csv'):
                self.zip_fixture(p,member=member)
                with self.assertRaises(ValueError):aggregate_archive(p,c)
            bad=self.row();bad.pop('PWGTP80');self.zip_fixture(p,rows=[bad])
            with self.assertRaisesRegex(ValueError,'header'):aggregate_archive(p,c)

    def test_download_byte_deadline_gate_and_no_person_get(self):
        class Response(io.BytesIO):headers={}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'download';limits=deepcopy(self.config['limits']);limits['compressed_bytes']=3
            with self.assertRaisesRegex(ValueError,'byte ceiling'):stream_download(Response(b'1234'),p,limits)
            p.unlink();ticks=iter([0,121])
            with self.assertRaisesRegex(ValueError,'deadline'):stream_download(Response(b'1'),p,limits,clock=lambda:next(ticks))
        opener=Mock()
        with patch('civiclab.e02.pums_wy_pilot_v1.require_predownload_approval',side_effect=ValueError('personGET BLOCKED')):
            with self.assertRaisesRegex(ValueError,'BLOCKED'):acquire_pilot(ROOT,self.config,opener=opener)
        opener.open.assert_not_called()

    def test_synthetic_transport_immutable_cache_drift_and_quarantine(self):
        class Response(io.BytesIO):
            status=200
            def __init__(self,data):super().__init__(data);self.headers={'Content-Length':str(len(data))}
            def geturl(self):return self_url
        self_url=self.config['url']
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture=root/'fixture.zip';self.zip_fixture(fixture)
            payload=fixture.read_bytes();c=deepcopy(self.config);c['limits']['expected_person_rows']=1
            opener=Mock();opener.open.side_effect=lambda *args,**kwargs:Response(payload)
            with patch('civiclab.e02.pums_wy_pilot_v1.require_predownload_approval'):
                path=acquire_pilot(root,c,opener=opener)
                self.assertEqual(path.read_bytes(),payload)
                self.assertEqual(acquire_pilot(root,c,opener=opener),path)
                self.assertEqual(opener.open.call_count,1)
                receipt=json.loads(path.with_suffix('.receipt.json').read_text())
                self.assertIn('retrieved_at_utc',receipt)
                path.write_bytes(payload+b'changed')
                with self.assertRaisesRegex(ValueError,'quarantined'):acquire_pilot(root,c,opener=opener)
                self.assertTrue(list(path.parent.glob('QUARANTINED-CACHE-*')))
            # A wrong first-acquisition pin preserves new bytes without promoting them.
            root2=root/'second';c['archive_sha256']='0'*64
            with patch('civiclab.e02.pums_wy_pilot_v1.require_predownload_approval'):
                with self.assertRaisesRegex(ValueError,'drifted'):acquire_pilot(root2,c,opener=opener)
            self.assertFalse((root2/c['local_archive']).exists())
            self.assertTrue(list((root2/c['local_archive']).parent.glob('QUARANTINED-*')))

    def test_attempt_manifest_precedes_http_and_terminal_failure_metadata_survives(self):
        marker='RAW_ROWS_OR_ERROR_BODY_MUST_NOT_APPEAR'
        for mode,error_class in (('http',HTTPError),('read',OSError),('validation',zipfile.BadZipFile),('crash',RuntimeError),('cancel',KeyboardInterrupt)):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);fixture=root/'fixture.zip';self.zip_fixture(fixture,rows=[self.row(SERIALNO=marker)])
                payload=fixture.read_bytes() if mode!='validation' else marker.encode()
                config=deepcopy(self.config);config['limits']['expected_person_rows']=1
                class Response(io.BytesIO):
                    status=200
                    def __init__(self,data):super().__init__(data);self.headers={};self.reads=0
                    def geturl(self):return config['url']
                    def read(self,n=-1):
                        self.reads+=1
                        if mode=='read' and self.reads==2:raise OSError(marker)
                        if mode=='read':return super().read(min(n,12))
                        return super().read(n)
                def fake_open(*args,**kwargs):
                    attempts=list((root/'data/raw/e02_pums_wy/attempts').iterdir())
                    self.assertEqual(len(attempts),1)
                    manifest=json.loads((attempts[0]/'attempt.json').read_text())
                    self.assertEqual(manifest['status'],'STARTED')
                    self.assertTrue((attempts[0]/'control-config.json').exists())
                    self.assertEqual(manifest['source_url'],config['url'])
                    events=[json.loads(line)['event'] for line in (attempts[0]/'events.jsonl').read_text().splitlines()]
                    self.assertEqual(events,['attempt_created','network_request_started'])
                    if mode=='http':raise HTTPError(config['url'],503,marker,{},io.BytesIO(marker.encode()))
                    return Response(payload)
                opener=Mock();opener.open.side_effect=fake_open
                with patch('civiclab.e02.pums_wy_pilot_v1.require_predownload_approval'):
                    if mode in ('crash','cancel'):
                        with patch('civiclab.e02.pums_wy_pilot_v1.aggregate_archive',side_effect=error_class(marker)):
                            with self.assertRaises(error_class):acquire_pilot(root,config,opener=opener)
                    else:
                        with self.assertRaises(error_class):acquire_pilot(root,config,opener=opener)
                attempt=list((root/'data/raw/e02_pums_wy/attempts').iterdir())[0]
                summary=json.loads((attempt/'summary.json').read_text());failure=json.loads((attempt/'failure.json').read_text())
                self.assertEqual(summary['status'],'FAILED');self.assertEqual(failure['error_type'],error_class.__name__)
                self.assertEqual(summary['cancelled'],mode=='cancel')
                self.assertFalse((root/config['local_archive']).exists())
                self.assertFalse((root/config['local_archive']).with_suffix('.receipt.json').exists())
                if mode=='http':
                    self.assertEqual(summary['http_status'],503);self.assertEqual(summary['quarantined_artifacts'],[])
                else:
                    self.assertEqual(len(summary['quarantined_artifacts']),1)
                    quarantine=summary['quarantined_artifacts'][0]
                    self.assertGreater(quarantine['bytes'],0);self.assertEqual(len(quarantine['sha256']),64)
                    self.assertTrue((root/quarantine['path']).exists())
                for metadata in attempt.iterdir():self.assertNotIn(marker,metadata.read_text())
                opener.open.assert_called_once()
