"""Verify the frozen E02 plan without confusing version control with preregistration."""
import argparse
import json
from pathlib import Path
from ..common import sha256_file


def verify_analysis_lock(root):
    root=Path(root).resolve()
    lock=json.loads((root/'configs/e02_analysis_lock.json').read_text())
    if lock.get('schema_version') != 1 or not lock.get('files'):
        raise ValueError('nonempty analysis lock required')
    checks=[]
    for name, expected in sorted(lock['files'].items()):
        path=(root/name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('analysis lock path escapes repository')
        checks.append({'path':name,'status':'PASS' if path.is_file() and sha256_file(path)==expected else 'MISSING_OR_CHANGED'})
    return {'status':'PASS_DEFINITION_INTEGRITY' if all(c['status']=='PASS' for c in checks) else 'BLOCKED',
            'checks':checks,'lock_sha256':sha256_file(root/'configs/e02_analysis_lock.json'),
            'independent_audit':'PENDING; a hash lock is not independent scientific approval',
            'external_preregistration':'NOT_RUN',
            'paid_execution':'BLOCKED; lock verification cannot authorize spending or credential use'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args();result=verify_analysis_lock(args.root)
    print(json.dumps(result,indent=2))
    if result['status']=='BLOCKED':raise SystemExit(2)


if __name__=='__main__':main()
