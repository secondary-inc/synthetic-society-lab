"""Gated owner-review projection of one accepted local demographic aggregate."""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
from .common import RunStore,canonical_hash,sha256_file
from .dashboard import verified_run

AGES=('18-24','25-44','45-64','65+')
EDUCATION=('HS_OR_LESS','SOME_COLLEGE','BA_PLUS')
CELLS=tuple(a+':'+e for a in AGES for e in EDUCATION)
STATUS='SDR_CONDITIONAL_SAMPLING_ERROR_ONLY'
LIMITS='Owner-review demographic benchmark only. SDR sampling approximation is conditional on the public PUMS release; not full error, ANES transport, political-response validity, a national population, anonymity or differential privacy. No population fit or external publication is authorized.'
SOURCE_EVIDENCE='reports/E02_PUMS_WY_LOCAL_REUSE_ACTUAL_EVIDENCE.json'
SOURCE_URL='https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year/csv_pwy.zip'
RESOURCE_NOTE='Observed source-processing wall time and process highwater RSS, not a per-run memory increment or a hard resource guarantee. Original deadlines were cooperative.'


def integer(value,minimum=0):
    if not isinstance(value,int) or isinstance(value,bool) or value<minimum:raise ValueError('invalid integer benchmark value')
    return value


def number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('invalid finite benchmark value')
    return value


def schema_check(value,schema):
    """Enforce the closed, nonreferential JSON-Schema subset used by this output."""
    kind=schema['type']
    if kind=='object':
        if not isinstance(value,dict) or set(value)!=set(schema['required']) or set(value)-set(schema['properties']):raise ValueError('projection object schema mismatch')
        for key,item in value.items():schema_check(item,schema['properties'][key])
    elif kind=='array':
        if not isinstance(value,list) or not schema['minItems']<=len(value)<=schema['maxItems']:raise ValueError('projection array schema mismatch')
        for item in value:schema_check(item,schema['items'])
    elif kind=='integer':integer(value,schema.get('minimum',0))
    elif kind=='number':number(value)
    elif kind=='boolean':
        if not isinstance(value,bool):raise ValueError('projection boolean schema mismatch')
    elif kind=='string':
        if not isinstance(value,str) or ('pattern' in schema and re.fullmatch(schema['pattern'],value) is None):raise ValueError('projection string schema mismatch')
    else:raise ValueError('unsupported projection schema keyword')
    if 'const' in schema and (type(value)!=type(schema['const']) or value!=schema['const']):raise ValueError('projection constant mismatch')
    if 'enum' in schema and value not in schema['enum']:raise ValueError('projection category mismatch')
    if 'minimum' in schema and value<schema['minimum']:raise ValueError('projection value below schema minimum')
    if 'exclusiveMinimum' in schema and value<=schema['exclusiveMinimum']:raise ValueError('projection value below exclusive minimum')
    if 'maximum' in schema and value>schema['maximum']:raise ValueError('projection value above schema maximum')


def scalar_error(value):
    if not isinstance(value,dict) or set(value)!={'variance_sdr','standard_error','moe90','status'} or value['status']!=STATUS:raise ValueError('unreviewed scalar uncertainty')
    v,se,moe=(number(value[k]) for k in ('variance_sdr','standard_error','moe90'))
    if min(v,se,moe)<=0 or not math.isclose(se*se,v,rel_tol=1e-10,abs_tol=1e-14) or not math.isclose(moe,1.645*se,rel_tol=1e-10,abs_tol=1e-14):raise ValueError('inconsistent scalar uncertainty')
    return {'variance_sdr':v,'standard_error':se,'moe90':moe,'status':STATUS}


def project_aggregate(source,provenance):
    """Literal whitelist; never copies source cells or nested private dictionaries."""
    if source.get('state')!='56' or source.get('period')!='2020-2024five-year' or source.get('population_fit')!='NOT_RUN' or source.get('person_weight_rescaled') is not False:raise ValueError('benchmark universe mismatch')
    if not isinstance(source.get('cells'),dict) or set(source['cells'])!=set(CELLS):raise ValueError('all twelve fixed cells required')
    total=integer(source['point_person_weight_sum'],1);rows=integer(source['total_person_rows'],1)
    if sum(integer(c['weight_sum'],1) for c in source['cells'].values())!=total:raise ValueError('point denominator mismatch')
    if sum(integer(c['count']) for c in source['cells'].values())!=integer(source['retained_unweighted_count'],1):raise ValueError('contributor denominator mismatch')
    if source['retained_unweighted_count']>rows:raise ValueError('contributor count exceeds source rows')
    output=[]
    for label in CELLS:
        cell=source['cells'][label]
        count=integer(cell['count'],30)
        if cell.get('low_support') is not False:raise ValueError('cell disclosure admission failed')
        weight=integer(cell['weight_sum'],1);share=number(cell['point_share'])
        if not 0<share<=1 or not math.isclose(share,weight/total,rel_tol=0,abs_tol=1e-12):raise ValueError('cell share denominator mismatch')
        age,education=label.split(':')
        output.append({'age':age,'education':education,'unweighted_contributors':count,
                       'point_person_weight_count':weight,'point_share':share,
                       'person_count_sampling_error':scalar_error(cell['count_uncertainty']),
                       'share_sampling_error':scalar_error(cell['share_uncertainty'])})
    return {'schema_version':1,'kind':'OWNER_REVIEW_WYOMING_DEMOGRAPHIC_BENCHMARK','state':'56',
            'period':'2020-2024five-year','universe':'Household citizens aged18+ in Wyoming; PUMS person weights are not divided by five.',
            'total_unfiltered_person_rows':rows,'point_person_weight_total':total,'cells':output,
            'provenance':dict(provenance),'owner_review_only':True,'external_publication_authorized':False,
            'minimum_unweighted_contributors':30,'population_fit':'NOT_RUN','scientific_population_gate':'BLOCKED',
            'network_requests':0,'paid_calls':0,'spent_usd':0,'limits':LIMITS}


def validate_projection(result,schema):
    schema_check(result,schema)
    cells=result['cells'];total=result['point_person_weight_total']
    labels=[c['age']+':'+c['education'] for c in cells]
    if len(set(labels))!=12 or set(labels)!=set(CELLS) or sum(c['point_person_weight_count'] for c in cells)!=total:raise ValueError('projection cell/total identity mismatch')
    if sum(c['unweighted_contributors'] for c in cells)>result['total_unfiltered_person_rows']:raise ValueError('projection contributors exceed source rows')
    for c in cells:
        if not 0<c['point_share']<=1 or not math.isclose(c['point_share'],c['point_person_weight_count']/total,rel_tol=0,abs_tol=1e-12):raise ValueError('projection share mismatch')
        scalar_error(c['person_count_sampling_error']);scalar_error(c['share_sampling_error'])


def load_config(root):
    root=Path(root).resolve();path=root/'configs/wyoming_benchmark_projection_v1.json'
    config=json.loads(path.read_text())
    required={'schema_version','stage','source','output_schema','required_files','execution_approval'}
    if set(config)!=required or config['schema_version']!=1 or config['stage']!='OWNER_REVIEW_PROJECTION_ONLY':raise ValueError('projection admission schema mismatch')
    source=config['source']
    if set(source)!={'run_id','checksums_sha256','aggregate_file_sha256','aggregate_canonical_sha256','archive_sha256','member_sha256'}:raise ValueError('source proof schema mismatch')
    if not isinstance(source['run_id'],str) or re.fullmatch('e02-[0-9a-f]{32}',source['run_id']) is None:raise ValueError('invalid source run identity')
    for key,value in source.items():
        if key!='run_id' and (not isinstance(value,str) or re.fullmatch('[0-9a-f]{64}',value) is None):raise ValueError('invalid source proof digest')
    if config['output_schema']!='configs/wyoming_benchmark_projection_schema_v1.json' or not config['required_files']:raise ValueError('fixed projection schema and code pins required')
    for name,expected in config['required_files'].items():
        if not isinstance(name,str) or re.fullmatch('[A-Za-z0-9_./-]+',name) is None or not isinstance(expected,str) or re.fullmatch('[0-9a-f]{64}',expected) is None:raise ValueError('unsafe projection dependency metadata')
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or p.parts[0] not in ('src','tests','docs','reports','configs'):raise ValueError('unsafe projection dependency')
        target=(root/p).resolve()
        if not target.is_relative_to(root) or sha256_file(target)!=expected:raise ValueError('projection dependency changed')
    return config


def require_approval(root,config):
    approval=config['execution_approval']
    if not isinstance(approval,dict) or set(approval)!={'path','sha256'}:raise ValueError('projection BLOCKED: independent code/fixture approval required')
    if not isinstance(approval['path'],str) or re.fullmatch(r'reports/INDEPENDENT_AUDIT_[A-Z0-9_]+\.json',approval['path']) is None or re.fullmatch('[0-9a-f]{64}',approval['sha256']) is None:raise ValueError('unsafe projection approval metadata')
    path=(Path(root)/approval['path']).resolve()
    if not path.is_relative_to(Path(root).resolve()/'reports') or sha256_file(path)!=approval['sha256']:raise ValueError('projection approval changed')
    audit=json.loads(path.read_text());design={k:v for k,v in config.items() if k!='execution_approval'}
    if audit.get('auditor_role')!='independent_auditor' or audit.get('status')!='PASS_WYOMING_OWNER_REVIEW_PROJECTION_CODE_AND_FIXTURES' or audit.get('reviewed_design_sha256')!=canonical_hash(design) or audit.get('reviewed_required_files')!=config['required_files']:raise ValueError('projection approval scope mismatch')


def file_identity(path):
    s=path.stat();return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns


def safe_provenance(root,config,source,aggregate,config_sha):
    proof=config['source'];evidence=json.loads((root/SOURCE_EVIDENCE).read_text())
    matches=[r for r in evidence['runs'] if r['run_id']==proof['run_id']]
    if len(matches)!=1:raise ValueError('source resource evidence identity mismatch')
    observed=matches[0]
    if observed['aggregate_file_sha256']!=proof['aggregate_file_sha256'] or observed['checksums_sha256']!=proof['checksums_sha256'] or evidence['source_archive']['sha256']!=proof['archive_sha256'] or evidence['observed_person_member_sha256']!=proof['member_sha256'] or evidence['observed_person_member_bytes']!=aggregate['source']['actual_uncompressed_bytes']:raise ValueError('source metadata evidence mismatch')
    recorded_at=source['manifest']['started_at_utc'];datetime.fromisoformat(recorded_at)
    result={k:proof[k] for k in proof}
    result.update(source_recorded_at_utc=recorded_at,projection_config_sha256=config_sha,
        projection_schema_sha256=sha256_file(root/config['output_schema']),
        projection_implementation_sha256=config['required_files']['src/civiclab/benchmark_export.py'],
        projection_execution_approval_sha256=config['execution_approval']['sha256'],
        methods_approval_sha256=config['required_files']['reports/INDEPENDENT_AUDIT_WYOMING_DISCLOSURE_PROPOSAL_METHODS.json'],
        source_arithmetic_audit_sha256=config['required_files']['reports/INDEPENDENT_AUDIT_E02_PUMS_WY_ACTUAL.json'],
        source_evidence_sha256=config['required_files'][SOURCE_EVIDENCE],source_public_url=SOURCE_URL,
        source_archive_bytes=integer(evidence['source_archive']['bytes'],1),
        source_member_bytes=integer(evidence['observed_person_member_bytes'],1),
        source_header_sha256=evidence['header']['sha256'],source_header_bytes=integer(evidence['header']['bytes'],1),
        source_header_columns=integer(evidence['header']['columns'],1),
        source_elapsed_seconds=number(observed['elapsed_seconds']),
        source_process_highwater_rss_bytes=integer(observed['process_highwater_rss_bytes_macos'],1),
        source_resource_limits_note=RESOURCE_NOTE)
    return result


def run_projection(root,*,kind='EXPLORATORY'):
    root=Path(root).resolve();config_path=root/'configs/wyoming_benchmark_projection_v1.json';config_sha=sha256_file(config_path)
    config=load_config(root);require_approval(root,config);pending=None
    if sha256_file(config_path)!=config_sha:raise ValueError('projection config changed before admission')
    with RunStore(root,'E02',{'stage':'wyoming-owner-review-benchmark-projection','config_sha256':config_sha},kind=kind) as run:
        run.write('projection-config.json',config)
        try:
            proof=config['source'];source_path=root/'data/processed/runs'/proof['run_id'];aggregate_path=source_path/'aggregate-local-only.json'
            identity=file_identity(aggregate_path);source=verified_run(source_path)
            if source['checksums_sha256']!=proof['checksums_sha256'] or source['artifacts'].get('aggregate-local-only.json')!=proof['aggregate_file_sha256'] or aggregate_path.stat().st_size>2_000_000:raise ValueError('source artifact proof mismatch')
            aggregate=json.loads(aggregate_path.read_text())
            if canonical_hash(aggregate)!=proof['aggregate_canonical_sha256'] or aggregate['source']['archive_sha256']!=proof['archive_sha256'] or aggregate['source']['member_sha256']!=proof['member_sha256']:raise ValueError('source aggregate proof mismatch')
            provenance=safe_provenance(root,config,source,aggregate,config_sha)
            result=project_aggregate(aggregate,provenance);validate_projection(result,json.loads((root/config['output_schema']).read_text()))
            if result['provenance']!=provenance:raise ValueError('projection provenance differs')
            final=verified_run(source_path)
            if final['checksums_sha256']!=proof['checksums_sha256'] or sha256_file(aggregate_path)!=proof['aggregate_file_sha256'] or file_identity(aggregate_path)!=identity:raise ValueError('source changed during projection')
            if sha256_file(config_path)!=config_sha or any(sha256_file(root/name)!=digest for name,digest in config['required_files'].items()):raise ValueError('projection config or dependency changed during processing')
            run.write('demographic-benchmark.local.json',result)
            run.finish({'status':'OWNER_REVIEW_DERIVATIVE_PENDING_INDEPENDENT_OUTPUT_DISCLOSURE_REVIEW','paid_calls':0,'spent_usd':0,'network_requests':0,'population_fit':'NOT_RUN','reproducibility_hash':canonical_hash(result)})
        except BaseException as error:
            pending=error;run.write('failure.json',{'status':'FAILED','error_type':type(error).__name__,'cancelled':isinstance(error,(KeyboardInterrupt,SystemExit)),'cell_values_released':False})
            run.event('projection_failed',error_type=type(error).__name__);run.finish({'status':'FAILED','error_type':type(error).__name__,'paid_calls':0,'spent_usd':0,'network_requests':0})
    if pending is not None:raise pending
    return run.path


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path.cwd())
    print(run_projection(parser.parse_args().root))
