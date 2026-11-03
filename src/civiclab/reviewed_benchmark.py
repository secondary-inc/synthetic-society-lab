"""New owner-review run from exact independently accepted projection bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from .common import RunStore,canonical_hash,sha256_file
from .dashboard import verified_run
from .benchmark_export import file_identity,validate_projection

AUDIT='reports/INDEPENDENT_AUDIT_WYOMING_PROJECTION_OUTPUT_DISCLOSURE.json'
SCHEMA='configs/wyoming_benchmark_projection_schema_v1.json'
CONFIG='configs/wyoming_benchmark_review_v1.json'


def load_config(root):
    config=json.loads((root/CONFIG).read_text())
    if set(config)!={'schema_version','stage','source','required_files','execution_approval'} or config['schema_version']!=1 or config['stage']!='OWNER_REVIEW_BYTE_EXACT_FINALIZATION':raise ValueError('review finalization admission mismatch')
    proof=config['source']
    if set(proof)!={'run_id','checksums_sha256','payload_sha256','canonical_sha256'}:raise ValueError('review source proof mismatch')
    if not isinstance(proof['run_id'],str) or re.fullmatch('e02-[0-9a-f]{32}',proof['run_id']) is None:raise ValueError('unsafe review source identity')
    for k,v in proof.items():
        if k!='run_id' and (not isinstance(v,str) or re.fullmatch('[0-9a-f]{64}',v) is None):raise ValueError('unsafe review source digest')
    if not config['required_files']:raise ValueError('review code/dependency pins required')
    for name,digest in config['required_files'].items():
        if not isinstance(name,str) or re.fullmatch('[A-Za-z0-9_./-]+',name) is None or not isinstance(digest,str) or re.fullmatch('[0-9a-f]{64}',digest) is None:raise ValueError('unsafe review dependency metadata')
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or p.parts[0] not in ('src','tests','configs','docs','reports'):raise ValueError('unsafe review dependency')
        target=(root/p).resolve()
        if not target.is_relative_to(root) or sha256_file(target)!=digest:raise ValueError('review dependency changed')
    audit=json.loads((root/AUDIT).read_text())
    admitted={'run_id':proof['run_id'],'checksums_sha256':proof['checksums_sha256'],'artifact_sha256':proof['payload_sha256'],'artifact_canonical_sha256':proof['canonical_sha256']}
    if audit.get('auditor_role')!='independent_auditor' or audit.get('status')!='PASS_EXACT_WYOMING_OWNER_REVIEW_PROJECTION_OUTPUT' or audit.get('accepted_payload_sha256')!=proof['payload_sha256'] or audit.get('accepted_payload_canonical_sha256')!=proof['canonical_sha256'] or not any(all(row.get(k)==v for k,v in admitted.items()) for row in audit.get('accepted_runs',[])):raise ValueError('exact payload lacks independent output/disclosure acceptance')
    if config['required_files'].get(AUDIT)!=sha256_file(root/AUDIT) or config['required_files'].get(SCHEMA)!=audit['projection_schema_sha256']:raise ValueError('reviewed audit/schema identity mismatch')
    return config


def require_code_approval(root,config):
    a=config['execution_approval']
    if not isinstance(a,dict) or set(a)!={'path','sha256'}:raise ValueError('review finalization BLOCKED: independent code/fixture approval required')
    if not isinstance(a['path'],str) or re.fullmatch(r'reports/INDEPENDENT_AUDIT_[A-Z0-9_]+\.json',a['path']) is None or not isinstance(a['sha256'],str) or re.fullmatch('[0-9a-f]{64}',a['sha256']) is None:raise ValueError('unsafe review approval metadata')
    p=(root/a['path']).resolve()
    if not p.is_relative_to(root/'reports') or sha256_file(p)!=a['sha256']:raise ValueError('review approval bytes changed')
    audit=json.loads(p.read_text());design={k:v for k,v in config.items() if k!='execution_approval'}
    if audit.get('auditor_role')!='independent_auditor' or audit.get('status')!='PASS_WYOMING_REVIEW_FINALIZATION_CODE_AND_FIXTURES' or audit.get('reviewed_design_sha256')!=canonical_hash(design) or audit.get('reviewed_required_files')!=config['required_files']:raise ValueError('review approval design mismatch')


def run_finalization(root,*,kind='EXPLORATORY'):
    root=Path(root).resolve();cp=root/CONFIG;config_sha=sha256_file(cp)
    config=load_config(root);require_code_approval(root,config);pending=None
    if sha256_file(cp)!=config_sha:raise ValueError('review config changed before admission')
    with RunStore(root,'E02',{'stage':'wyoming-owner-review-benchmark-finalization','config_sha256':config_sha},kind=kind) as run:
        run.write('review-config.json',config)
        try:
            proof=config['source'];source=root/'data/processed/runs'/proof['run_id'];payload=source/'demographic-benchmark.local.json'
            identity=file_identity(payload);verified=verified_run(source)
            if verified['checksums_sha256']!=proof['checksums_sha256'] or verified['artifacts'].get('demographic-benchmark.local.json')!=proof['payload_sha256'] or payload.stat().st_size>2_000_000:raise ValueError('accepted review payload source changed')
            with payload.open('rb') as f:raw=f.read(2_000_001)
            if len(raw)>2_000_000 or hashlib.sha256(raw).hexdigest()!=proof['payload_sha256']:raise ValueError('accepted review payload bytes changed')
            value=json.loads(raw)
            if canonical_hash(value)!=proof['canonical_sha256']:raise ValueError('accepted review payload canonical identity changed')
            validate_projection(value,json.loads((root/SCHEMA).read_text()))
            final=verified_run(source)
            if final['checksums_sha256']!=proof['checksums_sha256'] or sha256_file(payload)!=proof['payload_sha256'] or file_identity(payload)!=identity:raise ValueError('source changed during review finalization')
            if sha256_file(cp)!=config_sha or any(sha256_file(root/n)!=h for n,h in config['required_files'].items()):raise ValueError('review config/dependency changed during finalization')
            trace={'source_projection_run_id':proof['run_id'],'source_projection_checksums_sha256':proof['checksums_sha256'],
                   'accepted_payload_sha256':proof['payload_sha256'],'accepted_canonical_sha256':proof['canonical_sha256'],
                   'output_disclosure_audit_sha256':config['required_files'][AUDIT],'projection_schema_sha256':config['required_files'][SCHEMA],
                   'finalization_config_sha256':config_sha,'finalization_implementation_sha256':config['required_files']['src/civiclab/reviewed_benchmark.py'],
                   'finalization_execution_approval_sha256':config['execution_approval']['sha256'],
                   'owner_review_only':True,'external_publication_authorized':False,'source_run_preserved':True}
            run.write('review-finalization.json',trace)
            temporary=run.path/'pending-payload.local.json'
            with temporary.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.link(temporary,run.path/'demographic-benchmark.json');temporary.unlink()
            run.finish({'status':'OWNER_REVIEW_FINALIZED_PENDING_INDEPENDENT_ADMISSION_CHECK','payload_sha256':proof['payload_sha256'],
                        'population_fit':'NOT_RUN','scientific_population_gate':'BLOCKED','network_requests':0,'paid_calls':0,'spent_usd':0})
        except BaseException as error:
            final_payload=run.path/'demographic-benchmark.json'
            if final_payload.exists():final_payload.rename(run.path/'failed-payload.local.json')
            pending=error;run.write('failure.json',{'status':'FAILED','error_type':type(error).__name__,'cancelled':isinstance(error,(KeyboardInterrupt,SystemExit))})
            run.event('review_finalization_failed',error_type=type(error).__name__);run.finish({'status':'FAILED','error_type':type(error).__name__,'network_requests':0,'paid_calls':0,'spent_usd':0})
    if pending is not None:raise pending
    return run.path


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd())
    print(run_finalization(parser.parse_args().root))
