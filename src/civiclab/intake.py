"""Restore registered user downloads without executing files or overwriting bytes.

This is a local importer, not proof of upstream rights or a substitute for missing
source-specific download URLs. New official sources have their own pinned importers.
"""
from pathlib import Path
import json
import os
import shutil
import zipfile
from .common import sha256_file


def restore_inputs(root, source_directory, apply=False):
    root=Path(root).resolve();source_directory=Path(source_directory).resolve()
    inventory=json.loads((root/'configs/SOURCE_INVENTORY.json').read_text())
    checks=[]
    def destination(name):
        p=(root/name).resolve()
        if not p.is_relative_to(root/'data/raw'):
            raise ValueError('registered raw destination escapes data/raw')
        return p
    def retain(source,target,expected,label):
        if target.exists():
            status='VERIFIED_EXISTING' if target.is_file() and sha256_file(target)==expected else 'BLOCKED_EXISTING_DRIFT'
        elif not source.is_file():status='BLOCKED_MISSING_DOWNLOAD'
        elif sha256_file(source)!=expected:status='BLOCKED_DOWNLOAD_DRIFT'
        elif not apply:status='READY_TO_IMPORT'
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            with source.open('rb') as src,target.open('xb') as dst:
                shutil.copyfileobj(src,dst);dst.flush();os.fsync(dst.fileno())
            status='IMPORTED'
        checks.append({'path':str(target.relative_to(root)),'status':status,'kind':label})
        return status in ('VERIFIED_EXISTING','IMPORTED')
    for entry in inventory['archives']+inventory.get('documents',[]):
        name=entry.get('local_archive',entry.get('local_path'))
        if not name:continue
        target=destination(name)
        supplied=Path(entry['supplied_filename'])
        if supplied.name!=str(supplied):raise ValueError('unsafe supplied filename')
        source=source_directory/supplied
        if not retain(source,target,entry['sha256'],'source'):continue
        if target.suffix.lower()=='.zip':
            with zipfile.ZipFile(target) as archive:
                if archive.testzip():raise ValueError('corrupt registered ZIP')
                for member in entry.get('members',[]):
                    path=destination(str(target.relative_to(root).parent/'extracted'/member['name']))
                    if not path.is_relative_to((target.parent/'extracted').resolve()):raise ValueError('archive member escapes extraction directory')
                    if path.exists():
                        status='VERIFIED_EXISTING' if path.is_file() and sha256_file(path)==member['sha256'] else 'BLOCKED_EXISTING_DRIFT'
                    elif not apply:status='READY_TO_EXTRACT'
                    else:
                        raw=archive.read(member['name'])
                        import hashlib
                        if hashlib.sha256(raw).hexdigest()!=member['sha256']:raise ValueError('registered member digest mismatch')
                        path.parent.mkdir(parents=True,exist_ok=True)
                        with path.open('xb') as dst:dst.write(raw);dst.flush();os.fsync(dst.fileno())
                        status='EXTRACTED'
                    checks.append({'path':str(path.relative_to(root)),'kind':'member','status':status})
    return {'status':'BLOCKED' if any(c['status'].startswith('BLOCKED') for c in checks) else 'PASS_LOCAL_RESTORE' if apply else 'PLAN',
            'apply':apply,'checks':checks,
            'limits':'Local registered-download restoration only. It does not establish upstream release authenticity, rights, or complete public reacquisition.'}
