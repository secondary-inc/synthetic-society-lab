"""Pure limited-pilot request compiler; no live admission, owner or transport.

The future production bridge must reconstruct/verify each own committed pre
before calling the post compiler. A supplied answer here is not such proof.
"""
import hashlib
import json
from decimal import Decimal

from ..common import canonical_bytes,canonical_hash
from ..model import ExecutionBlocked,micros
from ..owner_budget_v3 import freeze
from ..production_price_v4 import validate_terms,quote,decimal_price,financial_context
from ..production_admission_v4 import _payload
from ..survey_execution import pre_request,post_request,messages
from .instrument import score

PROTOCOL_SHA='a76e3f8924c568e58960a99822f6e5665df4c95e38bb6e00e8d3075f71a5847b'
PROJECTION_SHA='1ad387de7ec320720849b1cacbcbbd4291b091cf0541cc43a8b39dc065172a5b'
ASSIGNMENT_SHA='15fbe5b3b87ed800600e5044a31fe970f405165297f63807ea2b8ed04087bafd'


def _protocol(raw):
    if type(raw) is not bytes or len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA:
        raise ExecutionBlocked('exact independently accepted limited protocol bytes required')
    p=json.loads(raw)
    if (set(p['instrument'])!={'instrument_id','items','instructions'}
        or canonical_hash(p['instrument'])!=PROJECTION_SHA
        or canonical_hash(p['assignments'])!=ASSIGNMENT_SHA or len(p['assignments'])!=16):
        raise ExecutionBlocked('projected instrument or frozen assignment binding differs')
    return p


@financial_context
def cost_envelope(protocol_bytes,terms):
    _protocol(protocol_bytes);terms=freeze(terms);validate_terms(terms)
    amount=micros(Decimal(8192)*decimal_price(terms['input_usd_per_token'])
        +Decimal(512)*decimal_price(terms['output_usd_per_token'])+decimal_price(terms['request_fee_usd']))
    if not 0<amount<=31250:raise ExecutionBlocked('per-call all-in reservation exceeds pilot subceiling')
    return {'input_token_bound_per_call':8192,'output_tokens_per_call':512,'max_model_POSTs':32,
        'per_call_reservation_microusd':amount,'study_reservation_max_microusd':32*amount,
        'study_subceiling_microusd':1000000,'shared_authorized_cap_microusd':5000000,
        'old_hold_microusd':340,'actual_authority':False,'context_and_route_release_required':True}


def _compile(protocol_bytes,execution_order,terms,before,phase):
    p=_protocol(protocol_bytes)
    if type(execution_order) is not int or not 0<=execution_order<16:
        raise ExecutionBlocked('one exact frozen arm unit required')
    job=freeze(p['assignments'][execution_order]);terms=freeze(terms)
    plan=cost_envelope(protocol_bytes,terms)
    if phase=='pre':request=pre_request(job,p['instrument'])
    else:
        before=freeze(before)
        if score(before,job['profile']['party'])['status']!='VALID':
            return {'status':'SKIP_INVALID_PRE','execution_order':execution_order,'phase':'post',
                'request':None,'actual_authority':False}
        if any(len(json.dumps(value,allow_nan=False))>32 for value in before.values()):
            raise ExecutionBlocked('valid numeric baseline exceeds reviewed serialization bound')
        request=post_request(job,p['instrument'],before)
    msg=messages(request);env=quote(msg,512,terms)
    if env['input_token_bound']>8192 or env['reserved_microusd']>plan['per_call_reservation_microusd']:
        raise ExecutionBlocked('exact request exceeds frozen common envelope')
    payload=_payload(msg,job['pair_seed'],512,terms)
    if len(canonical_bytes(payload))>262144:raise ExecutionBlocked('complete payload bound exceeded')
    return {'status':'COMPILED_NOT_ADMITTED','execution_order':execution_order,'phase':phase,
        'protocol_sha256':PROTOCOL_SHA,'projection_sha256':PROJECTION_SHA,'assignment_sha256':ASSIGNMENT_SHA,
        'unit_sha256':canonical_hash(job),'pair_seed':job['pair_seed'],'request':request,
        'messages':msg,'envelope':env,'payload':payload,'payload_sha256':canonical_hash(payload),
        'actual_authority':False,'own_committed_pre_witness_required':phase=='post',
        'scope':'PURE_REQUEST_COMPILATION_NO_LIVE_OR_BILLING_AUTHORITY'}


def compile_pre(protocol_bytes,execution_order,terms):
    return _compile(protocol_bytes,execution_order,terms,None,'pre')


def compile_post(protocol_bytes,execution_order,terms,before):
    return _compile(protocol_bytes,execution_order,terms,before,'post')


def create_actual_client(*args,**kwargs):
    raise ExecutionBlocked('production survey owner/admission/HTTP bridge not released')
