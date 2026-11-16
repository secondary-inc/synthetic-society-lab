"""One fresh bounded child, sanitized legacy environment, no retry/test runner."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
RUNNER=ROOT/'scripts/run_offline_ci_v1.py'
raw=RUNNER.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='9882cc86841b222f436c3210dd597bcf8d22623f08b31bdf95c5e691c940131b'
spec=importlib.util.spec_from_file_location('reviewed_collection_supervisor',RUNNER)
c=importlib.util.module_from_spec(spec);exec(compile(raw,str(RUNNER),'exec'),c.__dict__)

def ref(path):
    data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

# Preserve exact code/config/environment metadata before the single invocation.
code_inputs=[]
for directory in ('tests','scripts','src'):
    code_inputs.extend(ref(p) for p in sorted((ROOT/directory).rglob('*.py')) if '__pycache__' not in p.parts)
refs=[ref(ROOT/p) for p in ('pyproject.toml','.github/workflows/offline.yml','.venv/pyvenv.cfg',
 '.venv/lib/python3.12/site-packages/pypdf-6.10.0.dist-info/METADATA',
 '.venv/lib/python3.12/site-packages/synthetic_society_lab-0.1.0.dist-info/METADATA',
 '.venv/lib/python3.12/site-packages/__editable__.synthetic_society_lab-0.1.0.pth',
 'reports/CI_ORDINARY_COLLECTION_READINESS_20261116.json')]
scratch=E/'owned-temp-python312'
scratch.mkdir(mode=0o700,exist_ok=False)
command=[str(ROOT/'.venv/bin/python'),'-I','-B',str(E/'collection_child.py'),str(scratch)]
env={'PATH':os.defpath,'HOME':str(scratch),'TMPDIR':str(scratch),'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC','CI':'true','PYTHONHASHSEED':'0','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','PAID_API_ENABLED':'false','MAX_SPEND_USD':'0','MPLCONFIGDIR':str(scratch/'matplotlib')}
plan={'kind':'HISTORICAL_ORDINARY_COLLECTION_ONLY_RELEASE_V1','attempt':1,'maximum_children':1,'command':command,'environment':env,'historical_pypdf':'6.10.0','no_current_ci_qualification':True,'test_execution_allowed':False,'limits':{'child_wall_seconds':120,'child_cpu_seconds':120,'source_technical_read_bytes':268435456,'owned_temp_write_bytes':33554432,'console_bytes':524288},'code_inputs':code_inputs,'metadata_inputs':refs,'harness_sources':[ref(E/'collection_child.py'),ref(Path(__file__))]}
c.save_new(E/'RELEASE.json',plan)
job={'id':'historical-python312-collection','wall_seconds':120,'output_bytes':524288}
execution=c.supervise(command,env,job,E)
c.save_new(E/'SUPERVISOR.json',execution)
print(json.dumps(execution,sort_keys=True))
raise SystemExit(0 if execution['reason'] is None and execution['reaped'] and execution['returncode']==0 else 1)
