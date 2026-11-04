"""Candidate exact-packet terminal gate. No approval or packet is minted here."""
import hashlib
from pathlib import Path
import sys

from .common import canonical_bytes,canonical_hash,sha256_file
from .model import ExecutionBlocked
from .owner_budget_v3 import freeze,digest
from .additional_compatibility_owner_v1 import validate_bundle,receipt_for,OLD_RECEIPT
from .production_admission_v4 import make_context
from .additional_compatibility_client_v1_1 import code_contract as client_contract,execute_authored

FIELDS=set(('kind release policy review approval owner_assertion_candidate executor_review expected '
    'expected_executor_review_hash launcher_contract_sha256 historical_audit_sha256 limits owner_action '
    'readiness_review').split())
LIMITS={'absolute_lifetime_microusd':1000,'absolute_lifetime_dispatches':2,
    'old_uncertain_hold_microusd':340,'new_reservation_max_microusd':340,
    'new_POSTs':1,'new_statistics_GETs':1,'new_catalog_GETs':1,'retries':0,'purchases':0,
    'shared_authorized_budget_microusd':5000000}
ACTION='ACCEPT_PRIOR_UNKNOWN_BILL_AND_ONE_ADDITIONAL_REQUEST_WITH_ROTATED_DEDICATED_KEY_PREFUNDED'


def code_contract():
    root=Path(__file__).resolve().parents[2]
    from . import common,owner_budget_v3,additional_compatibility_preflight_v1_1
    modules=(sys.modules[__name__],common,owner_budget_v3,additional_compatibility_preflight_v1_1)
    pins={str(Path(m.__file__).relative_to(root)):sha256_file(m.__file__) for m in modules}
    script=root/'scripts/run_additional_json_compatibility_once_v1.py'
    pins[str(script.relative_to(root))]=sha256_file(script)
    return {'kind':'ADDITIONAL_COMPATIBILITY_TERMINAL_CODE_V1','client_contract':client_contract(),
            'pins':pins,'limits':LIMITS,'owner_action':ACTION,
            'same_original_owner':True,'automatic_retry':False}


def validate_packet(packet):
    p=freeze(packet)
    if type(p) is not dict or set(p)!=FIELDS or len(canonical_bytes(p))>524288:
        raise ExecutionBlocked('closed finite terminal packet required')
    if (type(p['limits']) is not dict or set(p['limits'])!=set(LIMITS)
        or any(type(v) is not int for v in p['limits'].values())):
        raise ExecutionBlocked('integer terminal limits required')
    if (p['kind']!='ADDITIONAL_COMPATIBILITY_TERMINAL_PACKET_V1' or p['limits']!=LIMITS
        or p['owner_action']!=ACTION or p['launcher_contract_sha256']!=canonical_hash(code_contract())
        or p['historical_audit_sha256']!='5e998c37e4be53b265527c4df0558ba70ea80e52b7fd0d75a0c8599388e015b0'):
        raise ExecutionBlocked('exact reviewed one-request terminal scope required')
    m,r,a,o=(p[k] for k in ('policy','review','approval','owner_assertion_candidate'))
    if m['predecessor_receipt']!=OLD_RECEIPT:raise ExecutionBlocked('historical predecessor differs')
    terms=p['release']['terms']
    proof={'url':'https://openrouter.ai/api/v1/models/'+terms['model']+'/endpoints',
        'body_sha256':terms['initial_catalog_sha256'],'observed_at_utc':m['valid_from_utc'],
        'metadata_semantic_hash':terms['metadata_semantic_hash']}
    c=make_context(p['release'],canonical_hash(a),proof)
    validate_bundle({'policy':m,'review':r,'approval':a,'owner_assertion':o,'context':c,
                     'receipt':receipt_for(m,r,o,c)},expected=p['expected'])
    er=p['executor_review']
    if (type(er) is not dict or set(er)!=set('kind reviewer_role review_id client_contract_hash policy_hash owner_assertion_hash release_hash'.split())
        or er['kind']!='INDEPENDENT_ADDITIONAL_COMPATIBILITY_CLIENT_REVIEW_V1_1'
        or er['reviewer_role']!='independent_auditor' or er['client_contract_hash']!=canonical_hash(client_contract())
        or er['policy_hash']!=canonical_hash(m) or er['owner_assertion_hash']!=canonical_hash(o)
        or er['release_hash']!=canonical_hash(p['release'])
        or canonical_hash(er)!=p['expected_executor_review_hash']):
        raise ExecutionBlocked('exact independent executor review differs')
    digest(er['review_id'],32)
    rr=p['readiness_review'];core={k:v for k,v in p.items() if k!='readiness_review'}
    if (type(rr) is not dict or set(rr)!=set('kind reviewer_role review_id packet_inputs_hash code_contract_hash'.split())
        or rr['kind']!='INDEPENDENT_ADDITIONAL_TERMINAL_PACKET_REVIEW_V1'
        or rr['reviewer_role']!='independent_auditor' or rr['packet_inputs_hash']!=canonical_hash(core)
        or rr['code_contract_hash']!=canonical_hash(code_contract())):
        raise ExecutionBlocked('exact independent terminal packet review required')
    digest(rr['review_id'],32)
    return p


def _load(raw):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('duplicate packet member')
            d[k]=v
        return d
    import json
    return json.loads(raw,object_pairs_hook=pairs,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite packet')))


def _preparation_base():
    return Path(__file__).resolve().parents[2]/'data/processed/compatibility_operator_handoff/additional-readonly-v1_1'


def prepare_original_metadata(review,expected_review_hash):
    """One reviewed read-only preparation in this checkout; no owner mutation.

    This is separate from dispatch authority. A create-once intent prevents
    automatic repeat in the reviewed checkout, including after read failures.
    Trusted workflow must not duplicate the release in another checkout.
    """
    r=freeze(review);digest(expected_review_hash)
    fields=set('kind reviewer_role review_id code_contract_hash scope predecessor_receipt max_invocations owner_writes credential_reads HTTP_requests'.split())
    if (type(r) is not dict or set(r)!=fields or canonical_hash(r)!=expected_review_hash
        or r['kind']!='INDEPENDENT_ORIGINAL_OWNER_READONLY_RELEASE_V1_1'
        or r['reviewer_role']!='independent_auditor' or r['code_contract_hash']!=canonical_hash(code_contract())
        or r['scope']!='ONE_FINITE_ORIGINAL_OWNER_METADATA_SNAPSHOT_NO_DISPATCH'
        or r['predecessor_receipt']!=OLD_RECEIPT or type(r['max_invocations']) is not int
        or r['max_invocations']!=1 or r['owner_writes'] is not False
        or r['credential_reads'] is not False or type(r['HTTP_requests']) is not int or r['HTTP_requests']!=0):
        raise ExecutionBlocked('exact independent finite read-only release required')
    digest(r['review_id'],32)
    base=_preparation_base()
    for p in (base,*base.parents):
        if p.is_symlink():raise ExecutionBlocked('symlink preparation namespace refused')
    base.mkdir(mode=0o700,parents=True,exist_ok=True)
    intent=base/(r['review_id']+'-intent.local.json')
    with intent.open('xb') as f:
        import os
        os.chmod(intent,0o600);f.write(canonical_bytes({'review_hash':expected_review_hash,'operation':'ONE_READONLY_SNAPSHOT'}))
        f.flush();os.fsync(f.fileno())
    from .additional_compatibility_preflight_v1_1 import _collect_authored_snapshot
    snapshot=_collect_authored_snapshot()
    path=base/(r['review_id']+'-snapshot.local.json')
    raw=canonical_bytes(snapshot)
    if len(raw)>524288:raise ExecutionBlocked('private snapshot exceeds preparation bound')
    with path.open('xb') as f:
        os.chmod(path,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
    return {'snapshot_path':str(path),'snapshot_sha256':hashlib.sha256(raw).hexdigest(),
            'event_count':snapshot['event_count'],'owner_writes':False,'credential_reads':False,'HTTP_requests':0}


def _read_exact_packet(path,expected_packet_sha256):
    if path.is_symlink():raise ExecutionBlocked('symlink packet refused')
    if path.stat().st_size>524288:raise ExecutionBlocked('terminal packet too large')
    with path.open('rb') as f:raw=f.read(524289)
    if len(raw)>524288 or hashlib.sha256(raw).hexdigest()!=expected_packet_sha256:
        raise ExecutionBlocked('externally expected packet bytes differ')
    return validate_packet(_load(raw))


def run_once(packet_path,expected_packet_sha256,*,accept_prior_unknown=False,
             confirm_rotated_dedicated_key=False,confirm_prefunded_no_purchase=False):
    # Only explicit human terminal assertion projects the reviewed owner
    # candidate into the live external assertion. Root never asserts it itself.
    if not all(v is True for v in (accept_prior_unknown,confirm_rotated_dedicated_key,confirm_prefunded_no_purchase)):
        raise ExecutionBlocked('explicit owner uncertainty/setup assertions required')
    digest(expected_packet_sha256)
    root=Path(__file__).resolve().parents[2]
    expected_path=root/'configs/json_compatibility_additional_v1_terminal_packet.json'
    path=Path(packet_path)
    if path!=expected_path or path.is_symlink():raise ExecutionBlocked('fixed terminal packet path required')
    p=_read_exact_packet(path,expected_packet_sha256)
    return execute_authored(p['policy'],p['review'],p['approval'],p['owner_assertion_candidate'],p['release'],
        expected=p['expected'],executor_review=p['executor_review'],
        expected_executor_review_hash=p['expected_executor_review_hash'])
