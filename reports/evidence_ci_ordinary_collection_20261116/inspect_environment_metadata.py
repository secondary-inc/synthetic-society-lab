"""Read-only qualification inventory; never imports/executes candidate environments.

This is not a collection child and does not execute tests or import project code.
"""
from pathlib import Path
import hashlib
import json
import tomllib

ROOT=Path(__file__).resolve().parents[2]
CACHE={}
READS=0

def body(path):
    global READS
    path=Path(path)
    data=path.read_bytes();READS+=len(data)
    if READS>268435456:raise RuntimeError('TECHNICAL_READ_CAP')
    return data

def ref(path):
    path=Path(path)
    resolved=path.resolve()
    if resolved not in CACHE:
        raw=body(path);CACHE[resolved]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return {'path':str(path),'resolved_path':str(resolved),**CACHE[resolved]}

def dist_rows(site):
    rows=[]
    for p in sorted(site.glob('*.dist-info/METADATA')):
        data=body(p).decode('utf-8')
        fields={}
        for line in data.splitlines():
            if line.startswith(('Name: ','Version: ')):
                key,value=line.split(': ',1);fields.setdefault(key,value)
        rows.append({'name':fields.get('Name'),'version':fields.get('Version'),'metadata_ref':ref(p)})
    return rows

pyproject=tomllib.loads(body(ROOT/'pyproject.toml').decode())
requirements={extra:pyproject['project']['optional-dependencies'][extra] for extra in ('selection','sources','geometry')}
expected={r.split('==')[0].lower():r.split('==')[1] for rows in requirements.values() for r in rows}
environments=[]
for environment in sorted(ROOT.glob('.venv*')):
    cfg=environment/'pyvenv.cfg'
    if not cfg.is_file():continue
    row={'environment':str(environment),'config_ref':ref(cfg),'config_text':body(cfg).decode(),'interpreter_exists':(environment/'bin/python').exists(), 'candidate_imports_or_invocations':0}
    if (environment/'bin/python').exists():row['interpreter_ref']=ref(environment/'bin/python')
    row['distributions']=[record for site in sorted(environment.glob('lib/python*/site-packages')) for record in dist_rows(site)]
    row['pth_files']=[{'ref':ref(p),'text':body(p).decode()} for p in sorted(environment.glob('lib/python*/site-packages/*.pth'))]
    installed={d['name'].lower():d['version'] for d in row['distributions'] if d['name']}
    row['current_ci_direct_requirement_comparison']={name:{'required':version,'metadata_observed':installed.get(name),'matches':installed.get(name)==version} for name,version in expected.items()}
    if environment.name=='.venv':
        row.update(admitted=False,reason='CURRENT_CI_SOURCE_EXTRA_MISMATCH: installed pypdf6.10.0 versus exact7.0.1; historical project environment is not silently promoted to current CI qualification.')
    else:
        row.update(admitted=False,reason='EXCLUDED_UNACCEPTED_E01_TARGET: metadata-only inventory; never invoked, added to sys.path or imported.')
    environments.append(row)
raw311=ROOT/'data/processed/toolchains/cpython-3.11.17-macos-aarch64-none'
raw_record={'runtime_ref':ref(raw311/'bin/python3.11'),'site_distribution_metadata':dist_rows(raw311/'lib/python3.11/site-packages'),'admitted_for_ordinary_collection':False,'reason':'Raw standard-library toolchain has no installed project, scipy, pypdf or pdfplumber distribution metadata. Frozen-group qualification is not project environment qualification.'}
geometry=json.loads(body(ROOT/'reports/ENGINEERING_EVIDENCE_GEOMETRY_RUNTIME_V1_7.json'))
oldworkspace=Path(geometry['temporary_workspace'])
geometry_paths=[oldworkspace/('venv-'+version) for version in ('3.11','3.12')]
old_geometry={'evidence_ref':ref(ROOT/'reports/ENGINEERING_EVIDENCE_GEOMETRY_RUNTIME_V1_7.json'),'scope':geometry['scope'],'historical_status':geometry['status'],'known_environment_paths':[{'path':str(p),'exists':p.exists(),'config_exists':(p/'pyvenv.cfg').is_file()} for p in geometry_paths], 'admission':'NOT_ADMITTED: source-subset geometry helper qualification is not full current project/extras qualification; no candidate executed.'}
result={'kind':'ORDINARY_COLLECTION_READONLY_ENVIRONMENT_METADATA_V1','current_ci_requirements':requirements,'pyproject_ref':ref(ROOT/'pyproject.toml'),'workflow_ref':ref(ROOT/'.github/workflows/offline.yml'),'ci_runner_ref':ref(ROOT/'scripts/run_offline_ci_v1.py'),'environments':environments,'raw311':raw_record,'historical_geometry_environments':old_geometry,'technical_file_bytes_read':READS,'project_imports':0,'candidate_runtime_invocations':0,'test_collections':0,'test_body_or_setup_invocations':0,'network_or_model_calls':0,'qualification_scope_limit':'Bounded known repository environments and exact paths from historical geometry evidence, not exhaustive search of all host directories. Metadata inspection is not a package integrity or importability qualification.'}
print(json.dumps(result,indent=2,sort_keys=True))
