"""v1.9.1 candidate: narrow native Nebraska tuple/JSON comparison correction.

Existing twelve roster objects remain unchanged. Idaho is separate status history.
Real-source execution requires independent review and lead authorization.
"""
from __future__ import annotations
import json
from pathlib import Path
from civiclab.common import RunStore,canonical_hash,redact,utc_now,sha256_file
from civiclab.e01 import ballots_v1_7 as legacy
from civiclab.e01 import idaho_v1_8_1 as idaho

CONTRACT_SHA='dc4f585d47c2c6d88a9ce3a33be34ff1ff2c87ee93636f61f55b263562652222'
ID_DIAG_SHA='5d05c4ce15b704da8cdf5730a4c866609bbce8373fd0b1cfe877dada5248e21c'
CONTEXT_SHA='feb92afb1fea60e0aba8a14b433464a7f3d1bb3f9d529bf3f936bbcb8bb241f7'
STATES=tuple('AK CO DE IA KS ME NC NE NH NJ VA WY'.split())
KINDS={'LEGACY_ROSTER_DOCUMENT','GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY','NO_DOCUMENT_ADMITTED_FOR_ANY_REVIEWED_KIND'}
SCOPE='TYPED_SOURCE_DOCUMENT_READINESS_ONLY_NOT_SAMPLE_OR_FINAL_BALLOT_ACCEPTANCE'
DATA_FILES=('legacy_readiness_v1_7.json','candidate_rosters.local.json','id_status_records.local.json','typed_document_readiness.json')


def require(ok):
    if not ok:raise ValueError('TYPED_READINESS_CONTRACT_MISMATCH')


def encoded(value):return (json.dumps(redact(value),indent=2,sort_keys=True,allow_nan=False)+'\n').encode()


def snapshot(config):
    c=idaho._closed_snapshot(config)
    require(canonical_hash(c)==CONTRACT_SHA)
    return c


def root_guard(root):
    p=Path(root).absolute();require('..' not in p.parts and p.is_dir())
    require(not any(x.is_symlink() for x in (p,*p.parents)))
    require(Path(__file__).resolve()==p.resolve()/'src/civiclab/e01/ballots_v1_9_1.py')
    return p.resolve()


def read_bound(root,relative,digest,area=None,size=None):
    q=Path(relative);require(not q.is_absolute() and '..' not in q.parts)
    p=root/q;require(not any(x.is_symlink() for x in (p,*p.parents) if x.is_relative_to(root)))
    require(p.is_file() and p.resolve().is_relative_to(root))
    if area:require(p.resolve().is_relative_to(root/area))
    n=p.stat().st_size;require(n<=4194304 and (size is None or type(size) is int and n==size))
    with p.open('rb') as f:data=f.read(4194304)
    require(p.stat().st_size==n and len(data)==n and idaho.digest(data)==digest)
    return data


def verify_bound_inputs(root,c):
    for module,relative in [(legacy,'src/civiclab/e01/ballots_v1_7.py'),(idaho,'src/civiclab/e01/idaho_v1_8_1.py')]:
        require(Path(module.__file__).resolve()==root/relative)
    for p,h in c['code_config_audit_pins'].items():read_bound(root,p,h)
    sources=c['sources'];require(len(sources)==40 and len({s['source_id'] for s in sources})==40 and len({s['path'] for s in sources})==40)
    require(sum(s['bytes'] for s in sources)<=33554432)
    require(tuple(s['source_id'] for s in sources[-5:])==idaho.SOURCE_IDS)
    for s in sources:read_bound(root,s['path'],s['sha256'],'data/raw',s['bytes'])
    refs={k:idaho.strict_json(read_bound(root,v['path'],v['sha256'],'data/processed')) for k,v in c['references'].items()}
    require(set(refs)=={'legacy_public','legacy_rosters','id_records','id_diagnostics'})
    return refs


def validate_public(value):
    """Explicit schema2 discriminator admission; never a generic-roster fallback."""
    require(type(value) is dict and set(value)=={'schema_version','scope','config_sha256','legacy_payload_ref','document_observations','metrics','context_contests','source_adoption','actual_selection','accepted_coverage_promoted','forecast_consumption','cost_usd','model_calls'})
    require(type(value['schema_version']) is int and value['schema_version']==2 and value['scope']==SCOPE)
    require(value['legacy_payload_ref']=='legacy_readiness_v1_7.json' and value['config_sha256']==CONTRACT_SHA)
    require(all(value[k] is False for k in ['source_adoption','actual_selection','accepted_coverage_promoted','forecast_consumption']))
    require(type(value['cost_usd']) is int and value['cost_usd']==0 and type(value['model_calls']) is int and value['model_calls']==0)
    rows=value['document_observations'];require(type(rows) is list and [r.get('state') for r in rows]==list(legacy.base.CLASS_II_STATES))
    for row in rows:
        state=row['state'];kind=row['kind'];require(kind in KINDS)
        if state in STATES:
            require(kind=='LEGACY_ROSTER_DOCUMENT' and set(row)=={'state','kind','legacy_observation_index'})
            require(type(row['legacy_observation_index']) is int and row['legacy_observation_index']==legacy.base.CLASS_II_STATES.index(state))
        elif state=='ID':
            require(kind=='GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY' and set(row)=={'state','kind','record_role','local_record_artifact_ref','source_status_record_count','Approved_status_record_count','Withdrawn_status_record_count','safe_diagnostics'})
            require(row['record_role']=='OBSERVED_GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY' and row['local_record_artifact_ref']=='id_status_records.local.json')
            require(all(type(row[k]) is int for k in ['source_status_record_count','Approved_status_record_count','Withdrawn_status_record_count']))
            require((row['source_status_record_count'],row['Approved_status_record_count'],row['Withdrawn_status_record_count'])==(5,4,1))
            d=row['safe_diagnostics'];require(canonical_hash(d)==ID_DIAG_SHA);require(d['typed_unknown_reasons']==idaho.UNKNOWN_REASONS and d['source_local_row_count']==5 and d['Approved_count']==4 and d['Withdrawn_count']==1)
            require(d['status_checkbox_evidence'][0]=={'kind':'UNKNOWN','reason':'INITIAL_ARTIFACT_HAS_NO_CHECKBOX_STATE_ARRAY'})
            require(d['candidate_name_input_evidence']==[{'kind':'UNKNOWN','reason':'INPUT_VALUE_NOT_CAPTURED'}]*3)
        else:require(kind=='NO_DOCUMENT_ADMITTED_FOR_ANY_REVIEWED_KIND' and set(row)=={'state','kind'})
    require(all(type(x) is int for x in value['metrics'].values()))
    require(value['metrics']=={'regular_frame_slots':33,'legacy_roster_state_count':12,'typed_status_history_state_count':1,'document_state_coverage_count':13,'remaining_document_acquisition_jobs':20,'distinct_source_representation_count':40,'final_ballots_accepted':0})
    require(canonical_hash(value['context_contests'])==CONTEXT_SHA)
    require(len(value['context_contests'])==3 and {x['contest_id'] for x in value['context_contests']}==legacy.base.CONTEXT_IDS)
    return value


NE_TUPLE_BOUNDS={'district':(151,200),'term':(200,225),'vote':(225,253),
                 'party':(253,317),'name':(317,430),'city':(430,484),'incumbency':(484,540)}


def _legacy_json_projection(value,*,native=False):
    """Comparison only: permit exactly the old Nebraska native BOUNDS tuples.

    Writers still serialize the original payload and require its original whole
    byte hash. Other tuple paths and scalar/type coercions are not permitted.
    """
    budget=[0]
    def clone(item,path,depth):
        budget[0]+=1;require(budget[0]<=65536 and depth<=64)
        kind=type(item)
        if kind is tuple:
            require(native and len(path)==3 and path[:2]==('NE','physical_column_bounds'))
            require(path[2] in NE_TUPLE_BOUNDS and len(item)==2 and all(type(x) is int for x in item))
            require(item==NE_TUPLE_BOUNDS[path[2]])
            return list(item)
        if kind is dict:
            require(all(type(k) is str for k in item))
            return {k:clone(v,(*path,k),depth+1) for k,v in item.items()}
        if kind is list:return [clone(v,(*path,i),depth+1) for i,v in enumerate(item)]
        if kind is float:
            import math
            require(math.isfinite(item))
        else:require(kind in (str,int,bool,type(None)))
        return item
    return clone(value,(),0)


def assemble(c,base,bundle,refs):
    require(set(base['local_only_rosters'])==set(STATES))
    rosters=base['local_only_rosters'];public={k:v for k,v in base.items() if k!='local_only_rosters'}
    require(canonical_hash(_legacy_json_projection(rosters,native=True))==canonical_hash(_legacy_json_projection(refs['legacy_rosters'])))
    require(canonical_hash(_legacy_json_projection(public))==canonical_hash(_legacy_json_projection(refs['legacy_public'])))
    require(idaho.digest(encoded(rosters))==c['references']['legacy_rosters']['sha256'])
    require(idaho.digest(encoded(public))==c['references']['legacy_public']['sha256'])
    records=list(bundle.local_records);diag=bundle.public_diagnostics()
    require(canonical_hash(records)==canonical_hash(refs['id_records']) and canonical_hash(diag)==canonical_hash(refs['id_diagnostics']))
    require(json.loads(encoded(records))==records and json.loads(encoded(diag))==diag)
    require(len(records)==5)
    for r in records:
        require(all(r[k]=={'kind':'UNKNOWN','reason':reason} for k,reason in idaho.UNKNOWN_REASONS.items()))
        require(not any(k in r for k in ['printed_on_ballot','declared_write_in','legal_nominee','party_class']))
        require(r['source_district_literal']==r['source_write_in_cell_literal']=='')
    require([r['source_status_literal'] for r in records]==['Withdrawn']+['Approved']*4)
    require([r['source_party_label'] for r in records]==['Democratic','Independent','Independent','Libertarian','Republican'])
    require([r['state'] for r in public['candidate_observations']]==list(legacy.base.CLASS_II_STATES))
    observations=[]
    for state in legacy.base.CLASS_II_STATES:
        if state in STATES:observations.append({'state':state,'kind':'LEGACY_ROSTER_DOCUMENT','legacy_observation_index':legacy.base.CLASS_II_STATES.index(state)})
        elif state=='ID':observations.append({'state':'ID','kind':'GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY','record_role':'OBSERVED_GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY','local_record_artifact_ref':'id_status_records.local.json','source_status_record_count':5,'Approved_status_record_count':4,'Withdrawn_status_record_count':1,'safe_diagnostics':diag})
        else:observations.append({'state':state,'kind':'NO_DOCUMENT_ADMITTED_FOR_ANY_REVIEWED_KIND'})
    result={'schema_version':2,'scope':SCOPE,'config_sha256':canonical_hash(c),'legacy_payload_ref':'legacy_readiness_v1_7.json','document_observations':observations,
        'metrics':{'regular_frame_slots':33,'legacy_roster_state_count':12,'typed_status_history_state_count':1,'document_state_coverage_count':13,'remaining_document_acquisition_jobs':20,'distinct_source_representation_count':40,'final_ballots_accepted':0},
        'context_contests':public['context_contests'],'source_adoption':False,'actual_selection':False,'accepted_coverage_promoted':False,'forecast_consumption':False,'cost_usd':0,'model_calls':0}
    validate_public(result)
    return dict(zip(DATA_FILES,[public,rosters,records,result]))


def compute(root,c):
    refs=verify_bound_inputs(root,c)
    base_config=idaho.strict_json(read_bound(root,c['base_config_path'],c['code_config_audit_pins'][c['base_config_path']]))
    id_config=idaho.strict_json(read_bound(root,c['id_contract_path'],c['code_config_audit_pins'][c['id_contract_path']]))
    require(c['geometry_runtime']=={'engine':'pdfplumber','version':'0.11.9'})
    base=legacy.validate_readiness(root,base_config)  # Pure validator; no child RunStore.
    bundle=idaho.read_sources(root,id_config)
    payloads=assemble(c,base,bundle,refs)
    verify_bound_inputs(root,c)
    return payloads


def _error_type(exc):
    t=exc.error_type if isinstance(exc,idaho.CaptureRejected) else type(exc).__name__
    return t if t in idaho.SAFE_ERROR_TYPES|{'KeyboardInterrupt','SystemExit'} else 'Exception'


def _raise_failure(kind):
    if kind=='KeyboardInterrupt':raise KeyboardInterrupt()
    if kind=='SystemExit':raise SystemExit()
    raise idaho.CaptureRejected(kind)


def _seal_failure(run,kind,config):
    # A finish failure may have already written a success summary/ledger. Never
    # overwrite either. A failure event invalidates any earlier ledger; retain a
    # separate terminal failure ledger and default-deny the run.
    run.finished=False
    try:
        if not (run.path/'manifest.json').exists():
            run.write('manifest.json',{'schema_version':1,'run_id':run.run_id,'module':'E01','kind':'EXPLORATORY','started_at_utc':utc_now(),'config':config,'status':'FAILED_DURING_CONSTRUCTOR'})
        run.event('typed_failed',error_type=kind)
        if not (run.path/'failure.json').exists():run.write('failure.json',{'status':'FAILED','error_type':kind,'source_adoption':False,'final_ballots_accepted':0})
        if not (run.path/'summary.json').exists() and not (run.path/'checksums.json').exists():run.finish({'status':'FAILED','error_type':kind,'final_ballots_accepted':0,'cost_usd':0})
        else:
            run.write('terminal_failure.local.json',{'status':'FAILED','error_type':kind,'reason':'PRESERVED_PARTIAL_PUBLICATION_NOT_ELIGIBLE_SUCCESS'})
            run.write('failure_checksums.local.json',{p.name:sha256_file(p) for p in sorted(run.path.iterdir()) if p.is_file() and p.name!='.lock'})
    finally:run.finished=True


def run_readiness(root,config):
    # No data/RunStore reads occur before closed-snapshot admission.
    try:c=snapshot(config);root=root_guard(root)
    except BaseException as exc:kind=_error_type(exc)
    else:kind=None
    if kind:_raise_failure(kind)
    wrapper_sha=sha256_file(Path(__file__))
    run_config={'role':'TYPED_SOURCE_DOCUMENT_READINESS_V1_9_1','schema_version':2,'config_sha256':canonical_hash(c),'wrapper_sha256':wrapper_sha}
    run=RunStore.__new__(RunStore);failure=None
    try:
        RunStore.__init__(run,root,'E01',run_config,kind='EXPLORATORY')
        payloads=compute(root,c)
        for name,value in payloads.items():run.write(name,value)
        for name,value in payloads.items():require((run.path/name).read_bytes()==encoded(value))
        verify_bound_inputs(root,c)  # Also after writes, before completion.
        run.write('typed_payload_hashes.json',{name:idaho.digest(encoded(value)) for name,value in payloads.items()})
        run.write('typed_commit.json',{'status':'PAYLOADS_WRITTEN_SOURCE_RECHECKED_AWAITING_FINAL_LEDGER','schema_version':2,'config_sha256':canonical_hash(c),'required_payloads':list(DATA_FILES)})
        require(sha256_file(Path(__file__))==wrapper_sha)
        run.finish({'status':'SEALED_TYPED_OBSERVATIONS_PENDING_INDEPENDENT_POST_RUN_REVIEW','schema_version':2,'final_ballots_accepted':0,'source_adoption':False,'accepted_coverage_promoted':False,'cost_usd':0})
        verify_bound_inputs(root,c)  # Hold frozen identities through finalization.
        require(sha256_file(Path(__file__))==wrapper_sha)
        # A consumer cannot admit the parent ledger while the post-finish
        # recheck is still pending. This terminal seal binds that complete ledger.
        run.finished=False
        run.write('typed_release.json',{'status':'LOCAL_TYPED_LEDGER_COMPLETE_PENDING_INDEPENDENT_REVIEW','config_sha256':canonical_hash(c),'checksums_sha256':sha256_file(run.path/'checksums.json'),'wrapper_sha256':wrapper_sha})
        run.finished=True
        read_verified_public(run.path,root=root,contract=c)
    except BaseException as exc:
        failure=_error_type(exc)
        if getattr(run,'path',None) and run.path.is_dir():
            try:_seal_failure(run,failure,run_config)
            except BaseException:run.finished=True  # Persistently unavailable FS cannot be certified sealed.
    finally:run._release_lock()
    if failure:_raise_failure(failure)
    return run.path


def read_verified_public(path,*,root=None,contract=None):
    """Local schema2 consumer only; failed/unsealed/extra-file runs are denied."""
    path=Path(path).absolute()
    require(len(path.parents)>=4 and '..' not in path.parts)
    root=Path(root).absolute() if root is not None else path.parents[3]
    require(not any(p.is_symlink() for p in (path,*path.parents)))
    require(path.parent==root/'data/processed/runs' and path.is_dir())
    if contract is None:contract=idaho.strict_json((root/'configs/e01_typed_readiness_v1_9_1_candidate.json').read_bytes())
    c=snapshot(contract)
    refs={k:idaho.strict_json(read_bound(root,v['path'],v['sha256'],'data/processed')) for k,v in c['references'].items()}
    require(not any((path/n).exists() for n in ['failure.json','terminal_failure.local.json','failure_checksums.local.json']))
    ledger=idaho.strict_json((path/'checksums.json').read_bytes())
    files={p.name for p in path.iterdir() if p.is_file() and p.name!='.lock'}
    require(files==set(ledger)|{'checksums.json','typed_release.json'})
    release=idaho.strict_json((path/'typed_release.json').read_bytes())
    require(release=={'status':'LOCAL_TYPED_LEDGER_COMPLETE_PENDING_INDEPENDENT_REVIEW','config_sha256':canonical_hash(c),'checksums_sha256':sha256_file(path/'checksums.json'),'wrapper_sha256':sha256_file(root/'src/civiclab/e01/ballots_v1_9_1.py')})
    require(set(DATA_FILES)|{'typed_payload_hashes.json','typed_commit.json','manifest.json','environment.json','events.jsonl','summary.json'}==set(ledger))
    for name,h in ledger.items():read_bound(path,name,h)
    manifest=idaho.strict_json((path/'manifest.json').read_bytes())
    require(manifest['module']=='E01' and manifest['kind']=='EXPLORATORY' and manifest['run_id']==path.name)
    require(manifest['config']=={'role':'TYPED_SOURCE_DOCUMENT_READINESS_V1_9_1','schema_version':2,'config_sha256':canonical_hash(c),'wrapper_sha256':release['wrapper_sha256']})
    summary=idaho.strict_json((path/'summary.json').read_bytes())
    require(canonical_hash(summary)==canonical_hash({'status':'SEALED_TYPED_OBSERVATIONS_PENDING_INDEPENDENT_POST_RUN_REVIEW','schema_version':2,'final_ballots_accepted':0,'source_adoption':False,'accepted_coverage_promoted':False,'cost_usd':0}))
    commit=idaho.strict_json((path/'typed_commit.json').read_bytes());require(commit=={'status':'PAYLOADS_WRITTEN_SOURCE_RECHECKED_AWAITING_FINAL_LEDGER','schema_version':2,'config_sha256':idaho.strict_json((path/'typed_document_readiness.json').read_bytes())['config_sha256'],'required_payloads':list(DATA_FILES)})
    payload_hashes=idaho.strict_json((path/'typed_payload_hashes.json').read_bytes());require(set(payload_hashes)==set(DATA_FILES))
    for name,h in payload_hashes.items():require(sha256_file(path/name)==h)
    require(sha256_file(path/'legacy_readiness_v1_7.json')==c['references']['legacy_public']['sha256'])
    require(sha256_file(path/'candidate_rosters.local.json')==c['references']['legacy_rosters']['sha256'])
    require(canonical_hash(idaho.strict_json((path/'id_status_records.local.json').read_bytes()))==canonical_hash(refs['id_records']))
    return validate_public(idaho.strict_json((path/'typed_document_readiness.json').read_bytes()))
