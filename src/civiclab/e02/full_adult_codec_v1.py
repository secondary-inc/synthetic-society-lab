"""Exact F raw-array codec and source/config-bound local manifests."""
import json
from pathlib import Path
from ..common import canonical_hash,sha256_file
from .national_budget import Blocked
from .full_adult_types_v1 import AdultMatrix,FILES,strict_json,keys,hash_value
from .full_adult_control_v1 import Policy,fixture_root
from .full_adult_analysis_v1 import mandatory_analysis
from .full_adult_engine_v1 import merge_F


def primitive_bundle(matrix,spec):
    blobs=matrix.blobs();entries=[]
    import hashlib
    for name in sorted(blobs):
        declaration=spec['output_contract']['binary_files'][name]
        entries.append({'name':name,'dtype':declaration['dtype'],'shape':declaration['shape'],'bytes':len(blobs[name]),'sha256':hashlib.sha256(blobs[name]).hexdigest()})
    return entries,canonical_hash(entries)


def source_bundle(parts,c,manifests):
    if len(parts)!=51 or set(manifests)!={r['state_fips'] for r in c['registry']}:raise Blocked('source bundle keys')
    result=[]
    for part in sorted(parts,key=lambda p:p['state']):
        state=part['state'];m=manifests[state]
        if m['state']!=state or part['source']['manifest_sha256']!=canonical_hash(m) or m['period']!=c['period'] or m['metadata_hashes']!=c['metadata_hashes']:raise Blocked('source-key/manifest/release closure')
        result.append({'state':state,'period':m['period'],'archive_sha256':m['archive_sha256'],'member_sha256':m['members'][m['person_member']]['sha256'],'header_sha256':m['header_sha256'],'metadata_hashes':m['metadata_hashes'],'manifest_sha256':canonical_hash(m)})
    if len({r['state'] for r in result})!=51 or len({r['archive_sha256'] for r in result})!=51:raise Blocked('source duplicate closure')
    return result,canonical_hash(result)


def write_benchmark(ledger,parts,spec,manifests,*,sweep='PRIMARY',query_ledger=None):
    from .national_population import supervise_fixture
    key=ledger.reserve_union(parts,sweep)
    phase=query_ledger.reserve_phase('MANDATORY',sweep) if query_ledger else None
    try:
        def work():
            m=merge_F(parts,ledger.c,spec);uncertainty,summaries=mandatory_analysis(m,spec)
            return m,uncertainty,summaries
        (matrix,uncertainty,summaries),resources=supervise_fixture(work,seconds=ledger.c['limits']['state_processing_seconds'],rss_bytes=ledger.c['limits']['rss_stop_bytes'],poll_seconds=ledger.c['limits']['watchdog_poll_seconds'])
        matrix.validate(spec);root=ledger.policy.root;folder=root/sweep;folder.mkdir(exist_ok=True)
        entries,digest=primitive_bundle(matrix,spec);src,source_digest=source_bundle(parts,ledger.c,manifests)
        written={name:ledger.policy.write(folder/name,blob) for name,blob in matrix.blobs().items()}
        written['uncertainty.json']=ledger.policy.json(folder/'uncertainty.json',uncertainty)
        written['views.json']=ledger.policy.json(folder/'views.json',{'F':'sum six domains','C':'citizen household slice, never added to F','summaries':summaries,'political_priors':'NOT_IDENTIFIED_BY_PUMS','C_count_aliases':{'C_VIEW:'+state+':'+str(a):'CELL:'+str(s*72+a*6) for s,state in enumerate(spec['universe']['state_fips']) for a in range(12)}})
        written['source_receipts.json']=ledger.policy.json(folder/'source_receipts.json',{'sources':src,'manifests':manifests,'all_age_accounting':{p['state']:p['accounting'] for p in parts}})
        manifest={'schema_version':'E02_F_BENCHMARK_V1','scope':'MOCK_AUTHORED_ONLY_NOT_ACTUAL_POPULATION','specification_id':spec['specification_id'],'runtime_config_sha256':canonical_hash(ledger.c),'axes':spec['universe'],'primitive_entries':entries,'primitive_bundle_sha256':digest,'source_bundle_sha256':source_digest,'files':written,'logical_units_observed':uncertainty['logical_units_observed'],'scientific_gate':'BLOCKED','actual_person_rows_processed':0}
        ledger.policy.json(folder/'manifest.json',manifest)
        proof=ledger.path/('F-'+sweep+'-commit.json');ledger.policy.json(proof,{'manifest_sha256':sha256_file(folder/'manifest.json'),'primitive_bundle_sha256':digest,'kind':'MOCK_F'})
        ledger.finish_union(key,proof,sha256_file(proof))
        if query_ledger:query_ledger.finish_phase(phase)
        return matrix,manifest,resources
    except BaseException:
        if query_ledger:query_ledger.finish_phase(phase,failed=True)
        ledger.fail_processing(key);raise


def read_benchmark(c,spec,sweep):
    root=fixture_root(c['fixture_root'],c);folder=root/sweep;manifest=strict_json((folder/'manifest.json').read_text())
    keys(manifest,['schema_version','scope','specification_id','runtime_config_sha256','axes','primitive_entries','primitive_bundle_sha256','source_bundle_sha256','files','logical_units_observed','scientific_gate','actual_person_rows_processed'])
    if manifest['schema_version']!='E02_F_BENCHMARK_V1' or manifest['scope']!='MOCK_AUTHORED_ONLY_NOT_ACTUAL_POPULATION' or manifest['specification_id']!=spec['specification_id'] or manifest['runtime_config_sha256']!=canonical_hash(c) or manifest['axes']!=spec['universe']:raise Blocked('benchmark runtime/spec/hash scope')
    allowed=set(FILES)|{'manifest.json','selectors.json','coefficients.json','query_plan.json','execution_manifest.json','query_result_index.json','covariance_results_v1_1.jsonl','contrast_results_v1_1.jsonl','plan_refusal.json','source_status.u8','support_status.u8','uncertainty.json','views.json','source_receipts.json'}
    if any(p.name not in allowed for p in folder.iterdir() if p.is_file()):raise Blocked('unknown benchmark file')
    expected=set(FILES)|{'source_status.u8','support_status.u8','uncertainty.json','views.json','source_receipts.json'}
    if set(manifest['files'])!=expected:raise Blocked('benchmark manifest vocabulary')
    for name,digest in manifest['files'].items():
        if Path(name).name!=name or sha256_file(folder/name)!=digest:raise Blocked('benchmark file integrity')
    matrix=AdultMatrix.decode({name:(folder/name).read_bytes() for name in set(FILES)|{'source_status.u8','support_status.u8'}},spec)
    entries,digest=primitive_bundle(matrix,spec)
    if digest!=manifest['primitive_bundle_sha256'] or entries!=manifest['primitive_entries']:raise Blocked('primitive dtype/shape/hash closure')
    receipts=strict_json((folder/'source_receipts.json').read_text())
    if len(receipts['sources'])!=51 or {r['state'] for r in receipts['sources']}!=set(spec['universe']['state_fips']) or canonical_hash(receipts['sources'])!=manifest['source_bundle_sha256']:raise Blocked('benchmark source key/hash closure')
    for r in receipts['sources']:
        m=receipts['manifests'].get(r['state'])
        if m is None or m['state']!=r['state'] or canonical_hash(m)!=r['manifest_sha256'] or m['archive_sha256']!=r['archive_sha256'] or m['metadata_hashes']!=c['metadata_hashes']:raise Blocked('source manifest transitive closure')
    # A sealed source-ledger commit binds the produced manifest; semantic checks
    # below do not re-run uncharged whole-benchmark estimation on every query.
    from .full_adult_control_v1 import FResourceLedger
    state=FResourceLedger(c).snapshot();receipt=state['processing'].get('UNION:'+sweep,{})
    proof_path=root/'sources'/receipt.get('artifact','MISSING')
    if receipt.get('status')!='MOCK_UNION_LOCAL_ONLY_PENDING_AUDIT' or not proof_path.is_file() or sha256_file(proof_path)!=receipt.get('sha256'):raise Blocked('uncommitted benchmark')
    proof=strict_json(proof_path.read_text())
    if proof['manifest_sha256']!=sha256_file(folder/'manifest.json'):raise Blocked('manifest commit binding')
    validate_uncertainty_container(strict_json((folder/'uncertainty.json').read_text()),spec)
    return matrix,manifest


class ExecutionBinding:
    def __init__(self,c,spec,plan,ledger):
        self.c=c;self.spec=spec;self.plan=plan;self.ledger=ledger;self.root=fixture_root(c['fixture_root'],c)
        primary,pm=read_benchmark(c,spec,'PRIMARY');replay,rm=read_benchmark(c,spec,'REPLAY')
        if pm['primitive_bundle_sha256']!=rm['primitive_bundle_sha256'] or pm['source_bundle_sha256']!=rm['source_bundle_sha256'] or primary.blobs()!=replay.blobs():raise Blocked('matched input replay required')
        for sweep in ('PRIMARY','REPLAY'):
            folder=self.root/sweep
            if strict_json((folder/'selectors.json').read_text())!={'schema_version':'E02_U1_SELECTOR_CATALOG_V1_1','entries':plan['selectors']} or strict_json((folder/'coefficients.json').read_text())!={'schema_version':'E02_U1_COEFFICIENT_CATALOG_V1_1','entries':plan['coefficients']}:raise Blocked('frozen catalog changed before source binding')
        catalog=plan['catalog_ops'];manifest={'schema_version':'E02_U1_QUERY_EXECUTION_MANIFEST_V1_1','batch_id':canonical_hash(c),'source_period':c['period'],'target_schema_version':spec['specification_id'],'spec_config_file_sha256':c['specification_sha256'],'runtime_config_sha256':canonical_hash(c),'code_tree_sha256':canonical_hash(c['required_files']),
            'source_bundle_sha256':pm['source_bundle_sha256'],'primitive_bundle_sha256':pm['primitive_bundle_sha256'],'target_axes_sha256':canonical_hash(spec['universe']),
            'query_plan_file_sha256':sha256_file(self.root/'PRIMARY/query_plan.json'),'selectors_file_sha256':sha256_file(self.root/'PRIMARY/selectors.json'),'coefficients_file_sha256':sha256_file(self.root/'PRIMARY/coefficients.json'),
            'catalog_operation_bound_per_sweep':catalog,'mandatory_operation_reservation_per_sweep':6000000,'query_operation_bounds':{q['query_id']:q['cost'] for q in plan['queries']},'planned_total_operation_reservation_both_sweeps':plan['total_ops'],'required_execution_approval_ref':'AUTHORED_FIXTURES_ONLY_NO_ACTUAL_APPROVAL','scope_kind':'MOCK_AUTHORED_F'}
        for sweep in ('PRIMARY','REPLAY'):Policy(c).json(self.root/sweep/'execution_manifest.json',manifest)
        self.manifest=manifest;self.digest=sha256_file(self.root/'PRIMARY/execution_manifest.json');ledger.bind(self.digest)
    def verify(self,matrix):
        for sweep in ('PRIMARY','REPLAY'):
            folder=self.root/sweep
            if sha256_file(folder/'execution_manifest.json')!=self.digest:raise Blocked('execution manifest changed')
            for name,field in [('selectors.json','selectors_file_sha256'),('coefficients.json','coefficients_file_sha256'),('query_plan.json','query_plan_file_sha256')]:
                if sha256_file(folder/name)!=self.manifest[field]:raise Blocked('catalog/plan transitive hash changed')
        matrix.validate(self.spec)
        if primitive_bundle(matrix,self.spec)[1]!=self.manifest['primitive_bundle_sha256']:raise Blocked('in-memory/source binding changed')
        _,meta=read_benchmark(self.c,self.spec,'PRIMARY')
        if meta['source_bundle_sha256']!=self.manifest['source_bundle_sha256']:raise Blocked('source bundle changed')
        return True


def validate_uncertainty_container(container,spec):
    from .full_adult_types_v1 import finite,decimal
    import math
    keys(container,['schema_version','records','logical_units_observed','political_priors'])
    if container['schema_version']!='E02_U1_COUNT_RATIO_UNCERTAINTY_V1_1' or container['political_priors']!='NOT_IDENTIFIED_BY_PUMS' or type(container['logical_units_observed']) is not int or not 0<=container['logical_units_observed']<=6000000:raise Blocked('uncertainty container')
    seen=set();contract=spec['uncertainty_record_contract'];expected={}
    for s,state in enumerate(spec['universe']['state_fips']):
        for cohort in ('F','C'):expected[cohort+'_STATE:'+state]=(cohort+'_STATE:'+state,None)
        expected['C_COVERAGE:'+state]=('C_STATE:'+state,'F_STATE:'+state)
        for a in range(12):
            ident='F_VIEW:'+state+':'+str(a);expected[ident]=(ident,None);expected[ident+':share']=(ident,'F_STATE:'+state)
            expected['C_VIEW:'+state+':'+str(a)+':share']=('CELL:'+str(s*72+a*6),'C_STATE:'+state)
        for i in range(s*72,(s+1)*72):expected['CELL:'+str(i)]=('CELL:'+str(i),None);expected['CELL:'+str(i)+':share']=('CELL:'+str(i),'F_STATE:'+state)
    for cohort in ('F','C'):
        expected[cohort+'_NATIONAL']=(cohort+'_NATIONAL',None)
        for region in ('1','2','3','4'):expected[cohort+'_REGION:'+region]=(cohort+'_REGION:'+region,None)
    expected['C_COVERAGE:NATIONAL']=('C_NATIONAL','F_NATIONAL')
    for r in container['records']:
        keys(r,contract['required_fields'])
        if r['quantity_id'] in seen or r['quantity_kind'] not in ('COUNT_TOTAL','PROPORTION') or r['status'] not in contract['status']:raise Blocked('uncertainty kind/id/status')
        seen.add(r['quantity_id'])
        if r['quantity_id'] not in expected or (r['numerator_ref'],r['denominator_ref'])!=expected[r['quantity_id']] or r['quantity_kind']!=('COUNT_TOTAL' if r['denominator_ref'] is None else 'PROPORTION'):raise Blocked('closed mandatory quantity/denominator reference')
        for k in ('point_value','variance_sdr','standard_error','moe90'):
            if r[k] is not None:finite(r[k])
        if r['variance_sdr'] is not None:
            if r['variance_sdr']<0 or r['standard_error']!=math.sqrt(r['variance_sdr']) or r['moe90']!=1.645*r['standard_error']:raise Blocked('uncertainty equation')
            if r['quantity_kind']=='COUNT_TOTAL':
                n=decimal(r['exact_count_variance_numerator_decimal'],signed=False)
                if type(r['exact_count_variance_denominator']) is not int or r['exact_count_variance_denominator']!=20 or r['variance_sdr']!=n/20:raise Blocked('exact count variance')
            elif r['exact_count_variance_numerator_decimal'] is not None or r['exact_count_variance_denominator'] is not None:raise Blocked('ratio is not integer count covariance')
        elif r['standard_error'] is not None or r['moe90'] is not None:raise Blocked('NULL uncertainty not imputed')
    if seen!=set(expected):raise Blocked('missing mandatory quantity')
    return True
