import csv
import hashlib
import io
import unittest
import zipfile
from civiclab.e02.citizen_benchmark import inspect_archive
from civiclab.e02.population import FIPS_REGION


class CitizenAcquisitionTests(unittest.TestCase):
    def fixture(self,*,omit_pr=False,percent='25.0',label='Estimate!!Native!!Total population'):
        prefix='ACSST5Y2024.S0501';count='S0501_C02_001E';pct='S0501_C02_007E'
        output=io.StringIO();writer=csv.writer(output)
        writer.writerow(['GEO_ID','NAME',count,pct]);writer.writerow(['Geography','Area',label,'Estimate!!Age'])
        codes=sorted(FIPS_REGION)+( [] if omit_pr else ['72'])
        for code in codes:writer.writerow(['0400000US'+code,'FIXTURE AREA',1000,percent])
        contents={prefix+'-Data.csv':output.getvalue().encode(),
                  prefix+'-Column-Metadata.csv':('Column Name,Label\n'+count+','+label+'\n'+pct+',Estimate!!Age\n').encode(),
                  prefix+'-Table-Notes.txt':('FIXTURE '+prefix).encode()}
        manifest={'dataset':prefix,'members':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in contents.items()},
                  'variables':{count:{'label':'Estimate!!Native!!Total population','proposed_unit':'persons'},
                               pct:{'label':'Estimate!!Age','proposed_unit':'percent'}}}
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            for k,v in contents.items():z.writestr(k,v)
        raw=stream.getvalue();manifest.update(archive_bytes=len(raw),archive_sha256=hashlib.sha256(raw).hexdigest())
        return raw,manifest

    def test_integrity_only_never_activates_calibration(self):
        raw,m=self.fixture();result=inspect_archive(raw,m)
        self.assertEqual(result['geography_rows'],52)
        self.assertIn('NOT_USED',result['calibration_activation'])
        self.assertEqual(result['independent_universe_and_unit_review'],'PENDING')
        with self.assertRaisesRegex(ValueError,'bytes changed'):inspect_archive(raw+b'x',m)

    def test_missing_geography_rejected_even_when_rehashed(self):
        raw,m=self.fixture(omit_pr=True)
        with self.assertRaisesRegex(ValueError,'expected50'):inspect_archive(raw,m)

    def test_labels_units_and_suppression_fail_closed(self):
        for kwargs in ({'percent':'(X)'},{'percent':'101'},{'percent':'NaN'},{'label':'Different universe'}):
            raw,m=self.fixture(**kwargs)
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):inspect_archive(raw,m)
