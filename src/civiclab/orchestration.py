"""Evidence-based completion, never an inference of success from test counts."""
from pathlib import Path
import json
from datetime import datetime,timezone
from .common import sha256_file, atomic_json, utc_now

STATUSES={'PASS','BLOCKED','NOT_RUN'}


def completion_status(root):
    root=Path(root).resolve()
    contract=json.loads((root/'configs/completion_contract.json').read_text())
    entries=contract.get('requirements')
    if not isinstance(entries,list) or not entries or any(not isinstance(r,dict) or not isinstance(r.get('id'),str) or not r['id'].strip() for r in entries):
        raise ValueError('completion contract must have nonempty identified requirements')
    if len({r['id'] for r in entries})!=len(entries):
        raise ValueError('duplicate completion requirement IDs')
    requirements={r['id']:{**r,'status':'NOT_RUN','reason':'No current independent audit receipt',
                            'audit_receipt':None,'evidence':[]} for r in contract['requirements']}
    rejected=[]
    def check_file(item):
        path=(root/item['path']).resolve()
        return path.is_relative_to(root) and path.is_file() and sha256_file(path)==item['sha256']
    accepted=[]
    for path in sorted((root/'reports').glob('AUDIT_COMPLETION_*.json')):
        try:
            audit=json.loads(path.read_text())
            if audit.get('schema_version')!=1 or audit.get('auditor_role')!='independent_auditor':
                raise ValueError('receipt not an independent audit')
            code=audit.get('code_files',{})
            if not code or not all(check_file({'path':name,'sha256':digest}) for name,digest in code.items()):
                raise ValueError('audit code scope missing or stale')
            when=datetime.fromisoformat(audit.get('audited_at_utc',''))
            if when.tzinfo is None or when>datetime.now(timezone.utc):
                raise ValueError('audit date missing')
            for row in audit.get('requirements',[]):
                if row['id'] not in requirements or row['status'] not in STATUSES or not row.get('reason'):
                    raise ValueError('unknown or malformed requirement')
                evidence=row.get('evidence',[])
                if row['status']=='PASS' and (not evidence or not all(check_file(item) for item in evidence)):
                    raise ValueError('PASS lacks intact supporting artifacts')
            accepted.append((when,str(path.relative_to(root)),audit))
        except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as error:
            rejected.append({'path':str(path.relative_to(root)),'reason':str(error)})
    for when,name,audit in sorted(accepted,key=lambda item:(item[0],item[1])):
        for row in audit['requirements']:
            requirements[row['id']].update(status=row['status'],reason=row['reason'],
                evidence=row.get('evidence',[]),audit_receipt=name,audited_at_utc=when.isoformat())
    rows=list(requirements.values())
    return {'schema_version':1,'generated_at_utc':utc_now(),'contract_sha256':sha256_file(root/'configs/completion_contract.json'),
            'status':'COMPLETE' if all(r['status']=='PASS' for r in rows) else 'INCOMPLETE',
            'requirements':rows,'rejected_audits':rejected,
            'independence_limit':'Auditor role is a workflow assertion, not a cryptographic identity. The lead does not author audit PASS findings.',
            'publication_authorized':False,'paid_spend_authorized_usd':0}


def write_completion(root, output):
    result=completion_status(root)
    atomic_json(output,result)
    return result
