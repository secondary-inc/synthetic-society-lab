from copy import deepcopy
import csv
import io
import unittest
from civiclab.e02.population import FIPS_REGION
from civiclab.e02.pums_metadata import reconstruct


class MetadataFixtures(unittest.TestCase):
    def fixture(self):
        # Public-metadata schema with authored counts, never respondent records.
        alphabet='abcdefghijklmnopqrstuvwxyz'
        registry=[{'state_fips':f,'filename':'csv_p'+alphabet[i//26]+alphabet[i%26]+'.zip'} for i,f in enumerate(sorted(FIPS_REGION))]
        # Avoid two special national/PR filenames in authored registry.
        self.assertNotIn('csv_pus.zip',[s['filename'] for s in registry])
        self.assertNotIn('csv_ppr.zip',[s['filename'] for s in registry])
        names=[s['filename'] for s in registry]+['csv_pus.zip','csv_ppr.zip']
        index=''.join('<tr><td></td><td><a href="'+n+'">'+n+'</a></td><td>2026-03-05 07:10</td><td>4.0M</td><td></td></tr>' for n in names)
        rows=[['Person','PSAM_P'+f,f,'Fixture State','1'] for f in sorted(FIPS_REGION)]
        for code,low,high in [('PA',1,15),('PB',16,28),('PC',29,41),('PD',42,56)]:
            rows.append(['Person','PSAM_PUS'+code[-1],code,'Fixture part',str(sum(low<=int(f)<=high for f in FIPS_REGION))])
        rows.extend([['Person','National Persons Records','US','Fixture US','51'],['Person','PSAM_P72','72','Fixture PR','2'],['Person','All Persons Records','PP','Fixture all','53']])
        out=io.StringIO();w=csv.writer(out);w.writerow(['FILE_TYPE','FILE_NAME','STATE','FILE_DESCRIPTION','NUMBER_OF_RECORDS']);w.writerows(rows)
        return index,out.getvalue(),registry

    def test_full_coverage_part_ranges_and_pr_separation(self):
        index,counts,registry=self.fixture();before=deepcopy(registry)
        x=reconstruct(index,counts,registry)
        self.assertEqual(len(x['states']),51);self.assertEqual(x['national']['published_person_rows'],51)
        self.assertEqual(x['excluded_PR']['published_person_rows'],2);self.assertEqual(registry,before)
        self.assertEqual(sum(p['published_person_rows'] for p in x['national']['parts']),51)

    def test_missing_duplicate_bad_member_and_inconsistent_count_rejected(self):
        index,counts,registry=self.fixture()
        cases=[(index,counts.replace('Fixture US,51','Fixture US,52'),registry),
               (index,counts+counts.splitlines()[1]+'\n',registry),
               (index.replace('csv_paa.zip','unapproved.zip'),counts,registry),
               (index+index,counts,registry),(index,counts,registry[:-1]),
               (index,counts.replace('PSAM_P01','PSAM_P02'),registry)]
        for args in cases:
            with self.subTest(args=args[1][-40:]):
                with self.assertRaises(ValueError):reconstruct(*args)

    def test_html_source_scripts_and_external_links_are_inert(self):
        index,counts,registry=self.fixture()
        x=reconstruct('<script>throw "must never execute"</script><a href="https://example.invalid/csv_paa.zip">other</a>'+index,counts,registry)
        self.assertEqual(len(x['states']),51)
