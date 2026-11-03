"""Owner-review reproducibility packages, without credentials or raw source data."""
from pathlib import Path
import hashlib
import json
import re
import zipfile
import tomllib
from .common import canonical_bytes, code_identity, sha256_file
from .dashboard import verified_run

SECRET=re.compile(rb'sk-or-v1-[a-f0-9]{64}|EAA[A-Za-z0-9]{80,}')
ALLOWED_SUFFIXES={'.py','.json','.md','.toml','.csv','.yml','.html','.png','.svg','.txt'}


def build_package(root, output, run_ids):
    root=Path(root).resolve();output=Path(output)
    if output.exists():
        raise FileExistsError('review archive already exists; choose a new snapshot name')
    if not run_ids:
        raise ValueError('select recorded runs explicitly; no broad raw-data export')
    initial_code=code_identity(root)
    inputs={}
    for name in ('pyproject.toml','README.md','AGENTS.md','AUTONOMOUS_RESEARCH_ORCHESTRATION.md',
                 'CODEX_MASTER_EXECUTION.md','.gitignore','.env.example'):
        p=root/name
        if p.is_file():inputs[name]=p
    for folder in ('src','configs','protocols','docs','tests','publications','.github'):
        for p in (root/folder).rglob('*'):
            if p.is_file() and p.suffix in ALLOWED_SUFFIXES and '__pycache__' not in p.parts:
                inputs[str(p.relative_to(root))]=p
    fixture=root/'tests/fixtures/gdelt/20261103090000.gkg.csv.zip'
    if fixture.exists():inputs[str(fixture.relative_to(root))]=fixture
    for pattern in ('AUDIT_*','INDEPENDENT_AUDIT*','STATUS*','COORDINATION.json',
                    'ENGINEERING_EVIDENCE*','PROGRESS*','LOCAL_RESTORE*','E01*','E02*'):
        for p in (root/'reports').glob(pattern):
            if p.is_file() and p.suffix in ('.md','.json'):inputs[str(p.relative_to(root))]=p
    for identity in run_ids:
        path=(root/'data/processed/runs'/identity).resolve()
        if not path.is_relative_to(root/'data/processed/runs'):
            raise ValueError('run path escapes store')
        run=verified_run(path)
        for name in list(run['artifacts'])+['checksums.json']:
            p=path/name;inputs[str(p.relative_to(root))]=p
    payloads={}
    for name,path in sorted(inputs.items()):
        if not path.resolve().is_relative_to(root) or name=='.env' or name.startswith('data/raw/'):
            raise ValueError('unsafe package member')
        content=path.read_bytes()
        if SECRET.search(content):raise ValueError('credential-like value; package refused')
        payloads[name]=content
    runtime_lock='configs/runtime_python312_20261103.txt'
    if runtime_lock in payloads:
        reproduction=['python3.12 -m venv .venv',
                      '.venv/bin/python -m pip install -r '+runtime_lock,
                      '.venv/bin/python -m pip install -e . --no-deps']
    else:
        project=tomllib.loads(payloads.get('pyproject.toml',b'').decode())
        extra=project.get('project',{}).get('optional-dependencies',{}).get('selection')
        reproduction=['python3.11 -m venv .venv',
                      ".venv/bin/python -m pip install -e '.[selection]'" if extra else '.venv/bin/python -m pip install -e .']
    reproduction+=['.venv/bin/python -m unittest discover -s tests -v',
                   '.venv/bin/civiclab validate-sources --fixture-only','.venv/bin/civiclab dashboard']
    manifest={'schema_version':1,'audience':'OWNER_REVIEW_ONLY','publication_authorized':False,
              'code':initial_code,'run_ids':run_ids,
              'files':{name:hashlib.sha256(content).hexdigest() for name,content in payloads.items()},
              'reproduction':reproduction,
              'limits':['Raw ANES/ACS/election inputs excluded; reacquire registered bytes before full source reruns.',
                        'Bundled MOCK/DEMO runs are engineering data, not scientific model effects.',
                        'Review independent audit/status before interpreting any real retrospective run.',
                        'Budget remains zero; this package does not authorize network inference.']}
    for name,path in inputs.items():
        if sha256_file(path)!=manifest['files'][name]:
            raise ValueError('input changed during package assembly; retry from a frozen state')
    if code_identity(root)!=initial_code:
        raise ValueError('source tree changed during package assembly; retry from a frozen state')
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix(output.suffix+'.writing')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,content in sorted({**payloads,'REPRODUCIBILITY_MANIFEST.json':canonical_bytes(manifest)}.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16;archive.writestr(info,content)
    temporary.replace(output)
    return verify_package(output)


def verify_package(path):
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist()
        if len(entries)>10000 or sum(i.file_size for i in entries)>250_000_000:
            raise ValueError('package size limit exceeded')
        names=archive.namelist()
        if len(names)!=len(set(names)) or any(Path(n).is_absolute() or '..' in Path(n).parts for n in names):
            raise ValueError('unsafe package paths')
        manifest=json.loads(archive.read('REPRODUCIBILITY_MANIFEST.json'))
        if set(names)!=(set(manifest['files'])|{'REPRODUCIBILITY_MANIFEST.json'}):
            raise ValueError('package manifest membership mismatch')
        for name,digest in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest:
                raise ValueError('package artifact hash mismatch')
    return {'status':'PASS_PACKAGE_INTEGRITY','files':len(names),'sha256':sha256_file(path),
            'run_ids':manifest['run_ids'],'scope':'Byte integrity only; not scientific or publication acceptance.'}
