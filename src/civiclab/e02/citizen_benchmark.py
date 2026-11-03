"""Verify acquired public S0501 bytes; never derive or activate calibration margins."""
from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
from decimal import Decimal,InvalidOperation
import zipfile
from ..common import sha256_file
from .population import FIPS_REGION


def inspect_archive(raw,manifest):
    if len(raw)!=manifest['archive_bytes'] or hashlib.sha256(raw).hexdigest()!=manifest['archive_sha256']:
        raise ValueError('Census archive bytes changed')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(manifest['members']):
            raise ValueError('unexpected or duplicate Census archive members')
        contents={}
        for name,expected in manifest['members'].items():
            if Path(name).name!=name or expected['bytes']>2_000_000:
                raise ValueError('invalid or oversized Census member')
            data=archive.read(name)
            if len(data)!=expected['bytes'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:
                raise ValueError('Census member bytes changed')
            contents[name]=data.decode('utf-8-sig')
    prefix=manifest['dataset']
    if prefix!='ACSST5Y2024.S0501' or prefix not in contents[prefix+'-Table-Notes.txt']:
        raise ValueError('matching five-year dataset identity required')
    reader=csv.DictReader(io.StringIO(contents[prefix+'-Data.csv']))
    labels=next(reader);rows=list(reader)
    expected_geos={'0400000US'+f for f in FIPS_REGION}|{'0400000US72'}
    if len(rows)!=52 or {r['GEO_ID'] for r in rows}!=expected_geos or labels['GEO_ID']!='Geography':
        raise ValueError('expected50 states,DC,PR and descriptive row')
    metadata={r['Column Name']:r['Label'] for r in csv.DictReader(io.StringIO(contents[prefix+'-Column-Metadata.csv']))}
    for variable,definition in manifest['variables'].items():
        if labels[variable]!=definition['label'] or metadata[variable]!=definition['label']:
            raise ValueError('Census variable label mismatch')
        for row in rows:
            try:value=Decimal(row[variable])
            except InvalidOperation:raise ValueError('missing or suppressed selected benchmark value')
            if not value.is_finite() or value<0:
                raise ValueError('invalid selected benchmark value')
            if definition['proposed_unit']=='persons':
                if value!=value.to_integral_value():raise ValueError('noninteger count estimate')
            elif value>100:raise ValueError('selected percentage or percentage MOE outside range')
    return {'status':'PASS_ACQUISITION_INTEGRITY_ONLY','dataset':prefix,'geography_rows':len(rows),
            'states_plus_dc':51,'puerto_rico_rows_preserved':1,'selected_estimate_and_moe_variables':len(manifest['variables']),
            'independent_universe_and_unit_review':'PENDING',
            'calibration_activation':'NOT_USED; separate amendment and independent review required',
            'paid_calls':0,'api_spend_usd':0}


def verify(root):
    root=Path(root).resolve();manifest_path=root/'configs/e02_citizen_benchmark_acquisition.json'
    manifest=json.loads(manifest_path.read_text());archive=(root/manifest['local_archive']).resolve()
    if not archive.is_relative_to(root):raise ValueError('source path escapes repository')
    result=inspect_archive(archive.read_bytes(),manifest)
    return {**result,'manifest_sha256':sha256_file(manifest_path),'archive_sha256':sha256_file(archive)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args();print(json.dumps(verify(args.root),indent=2))


if __name__=='__main__':main()
