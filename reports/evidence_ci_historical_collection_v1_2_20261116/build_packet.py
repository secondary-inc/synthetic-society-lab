"""Prepare metadata and exact input bindings ONLY. Never imports candidate code
or launches a child. launch_once.py separately requires explicit lead release.
"""
from pathlib import Path
import ast
import hashlib
import json
import os

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
READ_BYTES=0


def read(path):
    global READ_BYTES
    body=path.read_bytes();READ_BYTES+=len(body)
    assert READ_BYTES<=268435456,'PREPARATION_TECHNICAL_READ_CAP'
    return body


def ref(path,allow_known_interpreter_alias=False):
    path=path.absolute()
    if not allow_known_interpreter_alias:
        assert path==path.resolve() and not any(p.is_symlink() for p in (path,*path.parents)),'PREPARATION_INPUT_ALIAS'
    raw=read(path)
    return {'path':str(path),'resolved_path':str(path.resolve()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def write_new(path,value):
    data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    with open(path,'xb') as stream:stream.write(data)


assert not any((E/name).exists() for name in ('PACKET.json','LEAD_RELEASE.json','STARTED.json','SUPERVISOR.json','FINAL.json','owned-temp-python312'))
runner=ref(ROOT/'scripts/run_offline_ci_v1.py');test=ref(ROOT/'tests/test_ci_collection_isolation_v1.py')
assert runner['sha256']=='61bdc69cdcf592af213c0e8c357a0a8976a3140bcd8a60a4731a1972f2d6a3ae'
assert test['sha256']=='f3ba0b75b883545194696955d067a11d44a96fe90f9736edbf5fca968d27d631'
for path in (E/'collection_child.py',E/'launch_once.py',Path(__file__)):
    ast.parse(read(path))
code_inputs=[ref(p) for name in ('tests','scripts','src') for p in sorted((ROOT/name).rglob('*.py')) if '__pycache__' not in p.parts]
metadata_paths=[ROOT/p for p in ('pyproject.toml','.github/workflows/offline.yml','.venv/pyvenv.cfg','reports/CI_ORDINARY_COLLECTION_READINESS_20261116.json','reports/CI_HISTORICAL_ORDINARY_COLLECTION_20261116.json','reports/CI_ORDINARY_NAMESPACE_REMEDY_V1_2_HANDOFF_20261116.json')]
site=ROOT/'.venv/lib/python3.12/site-packages'
pth=list(site.glob('*.pth'))
assert pth==[site/'__editable__.synthetic_society_lab-0.1.0.pth']
assert read(pth[0]).decode()==str(ROOT/'src')+'\n'
metadata_paths.extend(pth)
metadata_paths.extend(sorted(site.glob('*.dist-info/METADATA')))
metadata_paths.extend(sorted(site.glob('*.dist-info/direct_url.json')))
assert b'\nVersion: 6.10.0\n' in read(site/'pypdf-6.10.0.dist-info/METADATA')
assert 'version = 3.12.14\n' in read(ROOT/'.venv/pyvenv.cfg').decode()
prior=json.loads(read(ROOT/'reports/evidence_ci_ordinary_collection_20261116/environment-metadata.json'))
old=next(row for row in prior['environments'] if Path(row['environment']).name=='.venv')['interpreter_ref']
runtime=ref(ROOT/'.venv/bin/python',allow_known_interpreter_alias=True)
assert all(runtime[key]==old[key] for key in ('resolved_path','bytes','sha256'))
scratch=E/'owned-temp-python312'
packet={'kind':'HISTORICAL_ORDINARY_COLLECTION_V1_2_PREPARED_PACKET','scope':'ONE_HISTORICAL_312_COLLECTION_ONLY_V1_2','state':'PREPARED_NOT_RELEASED','maximum_children':1,'attempt':1,
 'limits':{'child_wall_seconds':120,'child_cpu_seconds':120,'source_technical_read_bytes':268435456,'owned_temp_write_bytes':33554432,'console_bytes':524288},
 'command':[str(ROOT/'.venv/bin/python'),'-I','-B',str(E/'collection_child.py'),str(scratch)],
 'environment':{'PATH':os.defpath,'HOME':str(scratch),'TMPDIR':str(scratch),'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC','CI':'true','PYTHONHASHSEED':'0','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','PAID_API_ENABLED':'false','MAX_SPEND_USD':'0','MPLCONFIGDIR':str(scratch/'matplotlib')},
 'code_inputs':code_inputs,'metadata_inputs':[ref(p) for p in sorted(set(metadata_paths))],'runtime_inputs':[runtime],
 'harness_sources':[ref(E/name) for name in ('collection_child.py','launch_once.py','build_packet.py')],
 'runner_ref':runner,'ci_test_ref':test,'historical_environment':'Existing .venv CPython3.12.14/pypdf6.10.0 only; no current7.0.1 qualification.',
 'observations_planned':['sanitized sys.path before context','sys.path inside reviewed context before discovery','tests namespace origin/file/search paths and owned finder roots','inside snapshot after discovery or stop','after-context restored path and namespace metadata'],
 'execution_forbidden_during_preparation':True,'requires_separate_component_review_PASS_and_explicit_lead_release':True,
 'old_scope':'reports/evidence_ci_historical_collection_20261116/ remains consumed; never replay or overwrite.',
 'no_test_or_setup_or_framework_execution':True,'research_or_current_ci_qualification':False,'retries':0,'preparation_technical_bytes_read':READ_BYTES}
write_new(E/'PACKET.json',packet)
print(json.dumps({'status':'PREPARED_NOT_RELEASED','packet_bytes':(E/'PACKET.json').stat().st_size,'packet_sha256':hashlib.sha256(read(E/'PACKET.json')).hexdigest(),'actual_children':0,'preparation_read_bytes':READ_BYTES},sort_keys=True))
