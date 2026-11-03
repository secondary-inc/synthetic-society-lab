"""Read-only extraction of pinned original25+ loader semantics, pending equivalence audit.

No fitting, suppression, calibration or respondent export occurs here. The source
of truth is the separately hash-pinned population.py loading loop, not this copy.
"""
import csv
from collections import Counter
from .population import number
from ..common import canonical_hash


def extract_reference(path,mapping,seed):
    records=[];exclusions=Counter()
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if any(mapping[k] not in reader.fieldnames for k in ('sample','weight','age','education','race','income','party','region','psu','stratum')):
            raise ValueError('reference mapped variable missing')
        for position,row in enumerate(reader,1):
            sample=number(row[mapping['sample']]);weight=number(row[mapping['weight']])
            if sample not in mapping['sample_values'] or weight is None or weight<=0:
                exclusions['outside_fresh_weighted_sample']+=1;continue
            age_value,edu=number(row[mapping['age']]),number(row[mapping['education']])
            region_value=number(row[mapping['region']])
            if age_value is None or not 25<=age_value<=80 or edu not in range(1,6) or region_value not in range(1,5):
                exclusions['age_education_or_region_missing_outside_universe']+=1;continue
            region=str(int(region_value));age_bin='25-44' if age_value<45 else '45-64' if age_value<65 else '65+'
            party_value=number(row[mapping['party']])
            party='D' if party_value==1 else 'R' if party_value==2 else 'I' if party_value in (0,3,5) else 'UNKNOWN'
            race_value=number(row[mapping['race']]);income_value=number(row[mapping['income']])
            race='WHITE_NH' if race_value==1 else 'BLACK_NH' if race_value==2 else 'HISPANIC' if race_value==3 else 'OTHER_NH' if race_value in (4,5,6) else 'UNKNOWN'
            income='LOW' if income_value in (1,2) else 'MID' if income_value in (3,4) else 'HIGH' if income_value in (5,6) else 'UNKNOWN'
            education_bin=mapping['education_recode'][str(int(edu))]
            key=(region,age_bin,education_bin,party,race,income)
            cluster=(row[mapping['stratum']],row[mapping['psu']])
            if any(number(x) is None or number(x)<0 for x in cluster):
                exclusions['invalid_design_cluster']+=1;continue
            heldout=int(canonical_hash([seed,cluster])[:8],16)%5==0
            records.append({'position':position,'key':key,'weight_raw':row[mapping['weight']],
                            'weight':weight,'design':cluster,'heldout':heldout})
    return records,dict(exclusions)
