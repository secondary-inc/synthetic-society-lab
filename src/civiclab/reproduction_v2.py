"""Versioned owner-review builder with six exact public evidence receipts.

Candidate only until independent review; no current package is certified here.
The historical builder and accepted archives remain unchanged.
"""
from pathlib import Path
import hashlib
import json
import re
import zipfile
import tomllib
import os
from .common import canonical_bytes, code_identity, sha256_file
from .dashboard import verified_run

SECRET=re.compile(rb'sk-or-v1-[a-f0-9]{64}|EAA[A-Za-z0-9]{80,}')
ALLOWED_SUFFIXES={'.py','.json','.md','.toml','.csv','.yml','.html','.png','.svg','.txt'}


# This version leaves the accepted historical builder byte-identical.
from .reproduction import source_inputs as historical_source_inputs

PUBLIC_RECEIPTS = {
    'reports/CLEAN_RESTORE_722E63A_767_FIXTURES_LEAD.json': 'ca3e215e90ba394d587604631b2f14da49fca83922a407aa1e0ecba6a480bb61',
    'reports/CLEAN_RESTORE_722E63A_767_FIXTURES_LOG.txt': 'b565aa140b44ec922a994712c2d54102eda4be0087c518f418c1649b1fd3107b',
    'reports/CLEAN_RESTORE_A856B96_767_FIXTURES_FAILURE.json': 'cecc81f66e5785a294c78acebd0acb5a741e7223066688cef5ff157e132b425d',
    'reports/CLEAN_RESTORE_A856B96_767_FIXTURES_FAILURE_LOG.txt': 'b25a2c57337e36d94ccfdb0e729660e0272412ce559819839c50ddf224f4e108',
    'reports/JSON_COMPATIBILITY_ACTUAL_PRE_POST_STOP_V1.json': 'cec0c62c912d09f7ff8648268fc3b93366865e9ff64aa9ab1d3026a54af744ce',
    'reports/JSON_COMPATIBILITY_CONTINUATION_ACTUAL_STOP_V1.json': 'fec410cecae68a73a9faf42c93568a46b92681026eea026dea6762e7e5751898',
}
PUBLIC_RECEIPT_LIMIT = 1024 * 1024


def source_inputs(root):
    """Historical public set plus six exact, independently reviewed receipts.

    References inside reports are documentary only: never follow them into
    raw, owner, respondent or private control storage.
    """
    root = Path(root).absolute()
    if root.is_symlink():
        raise ValueError('package root alias')
    inputs = historical_source_inputs(root)
    for name, expected in PUBLIC_RECEIPTS.items():
        path = root
        for part in Path(name).parts:
            path = path / part
            if path.is_symlink():
                raise ValueError('public receipt alias')
        if not path.is_file():
            raise ValueError('required public receipt missing')
        with path.open('rb') as stream:
            content = stream.read(PUBLIC_RECEIPT_LIMIT + 1)
        if len(content) > PUBLIC_RECEIPT_LIMIT or hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('public receipt changed or oversized')
        inputs[name] = path
    return inputs


def build_package(root, output, run_ids):
    root=Path(root).absolute();output=Path(output)
    for ancestor in (root, *root.parents):
        if ancestor.is_symlink():raise ValueError('package root alias')
    root=root.resolve()
    if output.exists():
        raise FileExistsError('review archive already exists; choose a new snapshot name')
    if not run_ids:
        raise ValueError('select recorded runs explicitly; no broad raw-data export')
    initial_code=code_identity(root)
    inputs=source_inputs(root);source_names=set(inputs);selected_seals={}
    for identity in run_ids:
        path=(root/'data/processed/runs'/identity).resolve()
        if not path.is_relative_to(root/'data/processed/runs'):
            raise ValueError('run path escapes store')
        run=verified_run(path)
        # Capture the verifier's original expectations before any payload read.
        # Re-reading the live run later would admit a coordinated reseal.
        expected_artifacts=json.loads(json.dumps(run['artifacts']))
        expected_seal=run['checksums_sha256']
        if (not isinstance(expected_artifacts,dict) or
            any(not isinstance(name,str) or Path(name).is_absolute() or
                '..' in Path(name).parts or '\\' in name or
                not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{64}',value)
                for name,value in expected_artifacts.items())):
            raise ValueError('invalid selected run seal')
        selected_seals[str(path.relative_to(root))]=(expected_artifacts,expected_seal)
        if any(marker in name.casefold() for name in run['artifacts']
               for marker in ('-local-only.','.local.')):
            raise ValueError('run contains local-only artifacts; a separately reviewed disclosure-safe derived run is required')
        for name in list(run['artifacts'])+['checksums.json']:
            p=path/name;inputs[str(p.relative_to(root))]=p
    payloads={}
    for name,path in sorted(inputs.items()):
        if any(marker in name.casefold() for marker in ('-local-only.','.local.')):
            raise ValueError('package input marked local-only; independent disclosure-safe derivative required')
        if not path.resolve().is_relative_to(root) or name=='.env' or name.startswith('data/raw/'):
            raise ValueError('unsafe package member')
        if any(p.is_symlink() for p in (path,*path.parents)):
            raise ValueError('package input alias')
        content=path.read_bytes()
        if SECRET.search(content):raise ValueError('credential-like value; package refused')
        payloads[name]=content
    for prefix,(expected_artifacts,expected_seal) in selected_seals.items():
        seal_bytes=payloads[prefix+'/checksums.json']
        if hashlib.sha256(seal_bytes).hexdigest()!=expected_seal:
            raise ValueError('selected run seal changed during capture')
        # Equality against the original admitted map also closes coordinated
        # artifact+checksum replacement and added/removed seal members.
        if json.loads(seal_bytes)!=expected_artifacts:
            raise ValueError('selected run seal membership changed during capture')
        for name,expected in expected_artifacts.items():
            if hashlib.sha256(payloads[prefix+'/'+name]).hexdigest()!=expected:
                raise ValueError('selected run payload changed during capture')
    runtime_lock=('configs/runtime_python312_geometry_20261103.txt'
                  if 'configs/runtime_python312_geometry_20261103.txt' in payloads
                  else 'configs/runtime_python312_20261103.txt')
    project=tomllib.loads(payloads.get('pyproject.toml',b'').decode())
    if runtime_lock in payloads:
        local_name=re.sub(r'[-_.]+','-',project.get('project',{}).get('name','')).lower()
        for line in payloads[runtime_lock].decode().splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            requirement=re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)',line)
            if not requirement:raise ValueError('runtime lock must contain exact third-party registry pins only')
            if local_name and re.sub(r'[-_.]+','-',requirement[1]).lower()==local_name:
                raise ValueError('local project must not be resolved from a registry runtime lock')
        reproduction=['python3.12 -m venv .venv',
                      '.venv/bin/python -m pip install -r '+runtime_lock,
                      '.venv/bin/python -m pip install -e . --no-deps']
    else:
        extra=project.get('project',{}).get('optional-dependencies',{}).get('selection')
        reproduction=['python3.11 -m venv .venv',
                      ".venv/bin/python -m pip install -e '.[selection]'" if extra else '.venv/bin/python -m pip install -e .']
    reproduction+=['.venv/bin/python -m unittest discover -s tests -v',
                   '.venv/bin/civiclab validate-sources --fixture-only','.venv/bin/civiclab dashboard']
    manifest={'schema_version':2,'public_evidence_receipts':dict(PUBLIC_RECEIPTS),'audience':'OWNER_REVIEW_ONLY','publication_authorized':False,
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
    if set(source_inputs(root))!=source_names:
        raise ValueError('source/report file set changed during package assembly; retry from a frozen state')
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix(output.suffix+'.writing')
    with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,content in sorted({**payloads,'REPRODUCIBILITY_MANIFEST.json':canonical_bytes(manifest)}.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16;archive.writestr(info,content)
    # Publish without clobbering an output created after the initial check.
    os.chmod(temporary,0o600)
    os.link(temporary,output)
    temporary.unlink()
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
