"""One original slot46 continuation; pure bindings, no owner/IO/paid authority."""
from copy import deepcopy
from pathlib import Path
import re

from ..common import canonical_bytes, canonical_hash, sha256_file
from ..model import ExecutionBlocked
from ..owner_budget_v3 import digest, utc
from ..production_price_v4 import validate_terms, validate_decision
from . import wrapper_crossmodel_v1 as original

ROOT=Path(__file__).resolve().parents[3]
PROTOCOL=ROOT/'configs/e02_wrapper_crossmodel_v1_20261115.json'
PARENT_PACKET_SHA='3b29761579efaabee4ef03c6c71ae5f476ced64980fa6d362c5eea55489457ec'
SLOT=46
SEED=2315288556
BOUNDS={'POST':1,'statistics_GET':3,'catalog_GET':2,'parent_POST':80,'parent_statistics_GET':240,
        'parent_catalog_GET':16,'lifetime_dispatches':229,'shared_microusd':5000000,
        'E02_microusd':1000000,'study_microusd':200000,'E01_microusd':0,
        'phase_seconds':120,'operation_seconds':240,'CPU_seconds':125,'CPU_soft_seconds':120,'price_age_seconds':900}
AUTHORITY='WRAPPER_SLOT46_AUTHORITY_V2'


def need(value,code):
    if not value:raise ExecutionBlocked(code)


def closed(value,keys):
    need(type(value) is dict and set(value)==set(keys),'canary closed schema')


def contract():
    from .wrapper_crossmodel_canary_v1 import contract as predecessor_contract
    names=('src/civiclab/e02/wrapper_crossmodel_slot46_v2.py',
           'src/civiclab/e02/wrapper_crossmodel_slot46_v2_owner.py',
           'src/civiclab/e02/wrapper_crossmodel_slot46_v2_client.py',
           'scripts/launch_e02_slot46_v2_20261118.py',
           'configs/e02_wrapper_slot46_v2_20261118.json',
           'reports/E02_SLOT46_RESOURCE_DECISION_20261118.json',
           'src/civiclab/e02/wrapper_canary_failure_diagnostic_v1.py',
           'scripts/collect_connectivity_billing_once.py')
    return {'kind':'WRAPPER_SLOT46_CODE_V2','predecessor':predecessor_contract(),
            'pins':{name:sha256_file(ROOT/name) for name in names},'bounds':deepcopy(BOUNDS)}


def identity(owner_id):
    digest(owner_id,32)
    return canonical_hash({'owner':owner_id,'parent_packet':PARENT_PACKET_SHA,
                           'protocol':original.PROTOCOL_SHA256,'original_order':SLOT})


def validate_packet(q,expected_hash):
    closed(q,('kind','owner_id','parent_key','expected_head','parent_binding','run_id',
              'valid_from_utc','valid_until_utc','bounds','code_hash','price_release','review','authority'))
    need(canonical_hash(q)==expected_hash and len(canonical_bytes(q))<=60000,'canary exact packet')
    need(q['kind']=='WRAPPER_SLOT46_PACKET_V2' and q['bounds']==BOUNDS,'canary fixed scope')
    need(q['parent_key']==identity(q['owner_id']),'canary canonical parent identity')
    need(q['code_hash']==canonical_hash(contract()),'canary code contract')
    need(type(q['run_id']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',q['run_id']), 'canary run identity')
    start,end=utc(q['valid_from_utc']),utc(q['valid_until_utc'])
    need(120<(end-start).total_seconds()<=900,'canary finite authority')
    closed(q['price_release'],('A','B'))
    routes={'A':('openai/gpt-4.1-nano','azure','Azure','PROVIDER_FAMILY'),
            'B':('qwen/qwen3-30b-a3b-instruct-2507','nebius/fp8','Nebius','ENDPOINT_PREFIX')}
    for role,release in q['price_release'].items():
        closed(release,('kind','terms','interpretation'));t=release['terms'];d=release['interpretation']
        validate_terms(t);validate_decision(d)
        need(release['kind']=='LIMITED_PILOT_PRICE_RELEASE_V1'
             and tuple(t[k] for k in ('model','requested_route','reported_provider','route_scope'))==routes[role]
             and canonical_hash(d)==t['interpretation_hash'] and d['catalog_sha256']==t['initial_catalog_sha256']
             and all(t[k]==d[k] for k in ('model','requested_route','reported_provider','route_scope','valid_from_utc','valid_until_utc'))
             and utc(t['valid_from_utc'])<=start<end<=utc(t['valid_until_utc']), 'canary route/price lease')
    authority=q['authority'];closed(authority,('kind','scope_hash'))
    need(authority['kind']==AUTHORITY and authority['scope_hash']==canonical_hash({k:v for k,v in q.items() if k not in ('authority','review')}),'canary authority binding')
    r=q['review'];closed(r,('kind','reviewer_role','review_id','inputs_hash'))
    digest(r['review_id'],32)
    need(r['kind']=='INDEPENDENT_WRAPPER_SLOT46_REVIEW_V2' and r['reviewer_role']=='independent_auditor'
         and r['inputs_hash']==canonical_hash({k:v for k,v in q.items() if k!='review'}),'canary independent review')
    return deepcopy(q)



def lease_historical_catalog(raw,historical_release,*,expected_release_hash,valid_from,valid_until):
    """New reviewed lease of preserved semantics, NOT a new observation/fetch.

    Historical raw hash and every price/component stay identical. Caller must
    obtain independent packet review. Runtime still spends two counted GETs
    and verifies both fresh raw receipts before any reservation.
    """
    from .crossmodel_price_v1 import contract_from_catalog
    import hashlib
    need(canonical_hash(historical_release)==expected_release_hash,'canary historical release pin')
    old=historical_release['terms'];decision=deepcopy(historical_release['interpretation'])
    need(type(raw) is bytes and len(raw)<=2000000 and hashlib.sha256(raw).hexdigest()==old['initial_catalog_sha256']==decision['catalog_sha256'],'canary historical catalog bytes')
    validate_terms(old);validate_decision(decision)
    need(canonical_hash(decision)==old['interpretation_hash'],'canary historical decision pin')
    decision.update(valid_from_utc=valid_from,valid_until_utc=valid_until)
    terms=contract_from_catalog(raw,decision,expected_decision_hash=canonical_hash(decision))
    immutable=[k for k in old if k not in ('valid_from_utc','valid_until_utc','interpretation_hash')]
    need(all(terms[k]==old[k] for k in immutable),'canary unchanged historical price contract')
    return {'kind':'LIMITED_PILOT_PRICE_RELEASE_V1','terms':terms,'interpretation':decision}


def compile_slot(parent,terms):
    p=original.load_protocol(PROTOCOL.read_bytes());job=p['jobs'][SLOT]
    need((job['model_key'],job['phase'],job['visibility'],job['baseline_execution_order'],job['pair_seed'])
         ==('B','post','SHOWN',13,SEED),'canary original slot identity')
    before=next((w for w in parent['witnesses'] if w['execution_order']==13 and w['phase']=='pre'),None)
    need(before is not None,'canary authenticated baseline13')
    return original._compile(p,terms,job,before['answer']),canonical_hash(before)


def envelope(parent_key,records,status,provenance):
    digest(parent_key)
    need(provenance in ('MOCK','EXPLORATORY_REAL_MODEL'),'canary explicit provenance')
    need(type(records) is list and len(records)<=1 and status in ('COMMITTED_ONE_SLOT','STOPPED'),'canary zero/one terminal')
    for row in records:
        closed(row,('execution_order','phase','status','answer','payload_sha256','receipt'))
        need(type(row['execution_order']) is int and row['execution_order']==46 and row['phase']=='post'
             and row['status'] in ('ANSWER','PARSE_ERROR','FAILED_UNCERTAIN'),'canary record identity')
        digest(row['payload_sha256']);digest(row['receipt'],32)
        if row['status']=='ANSWER':original._checked_answer(row['answer'])
        else:need(row['answer'] is None,'canary invalid answer exclusion')
    need(status!='COMMITTED_ONE_SLOT' or (len(records)==1 and records[0]['status'] in ('ANSWER','PARSE_ERROR')),'canary success witness')
    return {'kind':'WRAPPER_SLOT46_ENVELOPE_V2','parent_key':parent_key,'original_protocol_sha256':original.PROTOCOL_SHA256,
            'records':deepcopy(records),'status':status,'response_provenance':provenance,
            'parent_stopped':True,'original_slot44':'FAILED_UNCERTAIN','original_slot45':'FAILED_UNCERTAIN','original_full80_analysis':'NOT_RUN_INCOMPLETE'}
