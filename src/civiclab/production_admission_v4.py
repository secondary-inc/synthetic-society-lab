"""Release/owner preflight for a fixed one-request compatibility plan.

No model transport or account mutation is implemented. External review and
operator assertions are trusted workflow evidence, not human authentication.
Real approvals/price releases are absent; tests use isolated fake OS homes.
"""
from datetime import datetime,timezone
from decimal import Decimal
import http.client,json,os,re,ssl,sys,time
from pathlib import Path

from .common import canonical_bytes,canonical_hash,sha256_file
from .model import ExecutionBlocked
from .owner_budget_v3 import digest,freeze,utc
from .production_price_v4 import quote,validate_terms,validate_decision,fresh_proof,decimal_price,financial_context
from . import production_owner_v4 as owner_runtime
from .production_owner_v4 import (ProductionOwnerV4,validate_registration,validate_approval,
    request_binding,base_context)

PROMPT='Return exactly one JSON object with the key ok and the boolean value true. Do not add text.'


def _fetch_public_catalog(model):
    """One fixed unauthenticated metadata GET; never inference or a retry."""
    if type(model) is not str or len(model)>128 or re.fullmatch(r'[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*',model) is None:
        raise ExecutionBlocked('invalid released catalog model')
    path='/api/v1/models/'+model+'/endpoints';response=None;connection=None;start=time.monotonic()
    try:
        connection=http.client.HTTPSConnection('openrouter.ai',timeout=15,context=ssl.create_default_context())
        connection.request('GET',path,headers={'Accept':'application/json','Accept-Encoding':'identity'})
        response=connection.getresponse()
        if (response.status!=200 or response.getheader('Location') is not None
            or response.getheader('Content-Encoding','identity').lower()!='identity'
            or not response.getheader('Content-Type','').lower().startswith('application/json')):
            raise ExecutionBlocked('public endpoint metadata response refused')
        lengths=response.headers.get_all('Content-Length',[])
        transfer=response.getheader('Transfer-Encoding')
        if transfer is not None and transfer.lower()!='chunked':
            raise ExecutionBlocked('unsupported metadata transfer framing')
        if len(lengths)>1:raise ExecutionBlocked('ambiguous metadata framing')
        length=None
        if lengths:
            if re.fullmatch(r'[0-9]{1,8}',lengths[0]) is None:raise ExecutionBlocked('invalid metadata length')
            length=int(lengths[0])
            if length>2_000_000 or response.getheader('Transfer-Encoding') is not None:
                raise ExecutionBlocked('metadata length outside bound')
        data=bytearray()
        while True:
            if time.monotonic()-start>30:raise ExecutionBlocked('metadata elapsed bound exceeded')
            block=response.read(min(65536,2_000_001-len(data)))
            if type(block) is not bytes:raise ExecutionBlocked('invalid metadata read')
            if not block:break
            data.extend(block)
            if len(data)>2_000_000:raise ExecutionBlocked('metadata body exceeds bound')
        if (length is not None and length!=len(data)) or time.monotonic()-start>30:
            raise ExecutionBlocked('metadata framing/time incomplete')
        import hashlib
        raw=bytes(data)
        return raw,{'url':'https://openrouter.ai'+path,'body_sha256':hashlib.sha256(raw).hexdigest(),
                    'observed_at_utc':owner_runtime.new_operation_time().isoformat()}
    except Exception:
        raise ExecutionBlocked('public metadata unavailable/unbounded; no retry') from None
    finally:
        failures=[]
        for resource in (response,connection):
            if resource is not None:
                try:resource.close()
                except BaseException as error:failures.append(error)
        for error in failures:
            if not isinstance(error,Exception):raise error
        if failures and sys.exc_info()[0] is None:
            raise ExecutionBlocked('metadata shutdown unverified; no retry') from None


def code_pins():
    from . import common,model,live_billing_v2,owner_budget_v3,production_price_v4,production_owner_v4
    return {str(Path(m.__file__).relative_to(Path(__file__).parents[1])):sha256_file(m.__file__)
            for m in (sys.modules[__name__],common,model,live_billing_v2,owner_budget_v3,
                      production_price_v4,production_owner_v4)}


@financial_context
def _payload(messages,seed,max_tokens,terms):
    components=terms['components_by_tag']
    prices={'prompt':max(decimal_price(v['prompt']) for v in components.values())*1_000_000,
            'completion':max(decimal_price(v['completion']) for v in components.values())*1_000_000,
            'request':decimal_price(terms['request_fee_usd'])}
    if any(Decimal(str(float(v)))!=v for v in prices.values()):
        raise ExecutionBlocked('provider price filter cannot serialize exactly')
    return {'model':terms['model'],'messages':messages,'stream':False,'seed':seed,'temperature':0,
        'max_completion_tokens':max_tokens,'response_format':{'type':'json_object'},
        'plugins':[],'tools':[],'tool_choice':'none',
        'provider':{'only':[terms['requested_route']],'allow_fallbacks':False,'require_parameters':True,
                    'max_price':{k:float(v) for k,v in prices.items()}}}


def compile_compatibility_release(terms,interpretation,*,run_id,seed=20261103,max_tokens=32):
    terms,interpretation=freeze(terms),freeze(interpretation)
    validate_terms(terms);validate_decision(interpretation)
    if canonical_hash(interpretation)!=terms['interpretation_hash']:
        raise ExecutionBlocked('interpretation differs from contract')
    if (any(terms[k]!=interpretation[k] for k in ('model','requested_route','reported_provider','route_scope','valid_from_utc','valid_until_utc'))
        or terms['initial_catalog_sha256']!=interpretation['catalog_sha256']):
        raise ExecutionBlocked('contract identities differ from interpreted source')
    if type(run_id) is not str or re.fullmatch(r'[0-9A-Za-z_-]{1,128}',run_id) is None:
        raise ValueError('safe preassigned run ID required')
    if type(seed) is not int or not 0<=seed<2**32 or type(max_tokens) is not int or not 16<=max_tokens<=128:
        raise ValueError('bounded compatibility seed/output required')
    messages=[{'role':'system','content':'This is a nonpolitical API compatibility check. Respond only in JSON.'},
              {'role':'user','content':PROMPT}]
    payload=_payload(messages,seed,max_tokens,terms);envelope=quote(messages,max_tokens,terms)
    request={'run_id':run_id,'unit_id':'json-compatibility-v4','phase':'compatibility','module':'E02',
             'payload':payload,'envelope':envelope,'sampling':{'seed':seed,'temperature':0,'retries':0}}
    request['plan_hash']=canonical_hash(request)
    return {'schema_version':1,'kind':'NONPOLITICAL_JSON_COMPATIBILITY_RELEASE_V4',
            'terms':terms,'interpretation':interpretation,'request':request,'source_pins':code_pins()}


def precheck_review(release,review,expected_review_hash):
    release,review=freeze(release),freeze(review);digest(expected_review_hash)
    if (type(review) is not dict or set(review)!={'kind','scope','review_id','release_hash','source_pins','reviewer_role','limitations_sha256'}
        or review['kind']!='INDEPENDENT_PRODUCTION_RELEASE_REVIEW_V4'
        or review['scope']!='CODE_PRICE_REQUEST_READY_FOR_OWNER'
        or review['reviewer_role']!='independent_auditor' or canonical_hash(review)!=expected_review_hash):
        raise ExecutionBlocked('exact external production review required')
    digest(review['review_id'],32);digest(review['limitations_sha256']);digest(review['release_hash'])
    if (type(release) is not dict or set(release)!={'schema_version','kind','terms','interpretation','request','source_pins'}
        or type(release['schema_version']) is not int or release['schema_version']!=1
        or release['kind']!='NONPOLITICAL_JSON_COMPATIBILITY_RELEASE_V4'):
        raise ExecutionBlocked('complete compatibility release required')
    if canonical_hash(release)!=review['release_hash'] or review['source_pins']!=code_pins():
        raise ExecutionBlocked('released plan/code differs')
    req=release['request']
    if (type(req) is not dict or set(req)!={'run_id','unit_id','phase','module','payload','envelope','sampling','plan_hash'}
        or type(req['envelope']) is not dict or 'max_tokens' not in req['envelope']
        or type(req['sampling']) is not dict or 'seed' not in req['sampling']):
        raise ExecutionBlocked('complete static request required')
    rebuilt=compile_compatibility_release(release['terms'],release['interpretation'],run_id=req['run_id'],
                                         seed=req['sampling']['seed'],max_tokens=req['envelope']['max_tokens'])
    if canonical_hash(rebuilt)!=review['release_hash']:
        raise ExecutionBlocked('release differs from exact compatibility derivation')
    return release,review


def precheck_bootstrap(registration,expected_registration_hash,release,review,expected_review_hash,*,now):
    registration=freeze(registration);release,review=precheck_review(release,review,expected_review_hash)
    validate_registration(registration);digest(expected_registration_hash)
    if (canonical_hash(registration)!=expected_registration_hash
        or registration['review_hash']!=expected_review_hash or registration['release_hash']!=canonical_hash(release)
        or not utc(registration['valid_from_utc'])<=now<utc(registration['valid_until_utc'])):
        raise ExecutionBlocked('external bootstrap assertion not bound/current')
    return registration


def make_context(release,approval_hash,price_proof):
    r=release['request']
    context={'approval_hash':approval_hash,'plan_hash':r['plan_hash'],'release_hash':canonical_hash(release),
        'price_proof':freeze(price_proof),'run_id':r['run_id'],'unit_id':r['unit_id'],'phase':r['phase'],
        'module':r['module'],'terms':release['terms'],'envelope':r['envelope'],'sampling':r['sampling'],
        'payload_hash':canonical_hash(r['payload'])}
    base_context(context)
    return freeze(context)


def precheck_dispatch_approval(approval,expected_approval_hash,release,review,expected_review_hash,*,now):
    approval=freeze(approval);release,review=precheck_review(release,review,expected_review_hash)
    validate_approval(approval,approval['owner_id']);digest(expected_approval_hash)
    if (canonical_hash(approval)!=expected_approval_hash or approval['review_hash']!=expected_review_hash
        or approval['release_hash']!=canonical_hash(release)
        or not utc(approval['valid_from_utc'])<=now<utc(approval['valid_until_utc'])):
        raise ExecutionBlocked('external dispatch assertion not bound/current')
    # Dynamic fresh receipt bytes/timestamps are not the static request binding.
    proof={'url':'https://openrouter.ai/api/v1/models/'+release['terms']['model']+'/endpoints',
        'body_sha256':release['terms']['initial_catalog_sha256'],'observed_at_utc':approval['valid_from_utc'],
        'metadata_semantic_hash':release['terms']['metadata_semantic_hash']}
    c=make_context(release,expected_approval_hash,proof);env=c['envelope']
    expected={c['plan_hash']:{'module':c['module'],'terms_sha256':canonical_hash(c['terms']),
        'max_tokens':env['max_tokens'],'max_input_token_bound':env['input_token_bound'],
        'request_binding_hash':request_binding(c)}}
    if canonical_hash(approval['allowed_plans'])!=canonical_hash(expected):
        raise ExecutionBlocked('approval differs from the one released request')
    return approval


class _Credential:
    __slots__=('_value',)
    def __init__(self,value):self._value=value
    def __repr__(self):return '<OpenRouter credential redacted>'
    __str__=__repr__


def _read_environment_key():
    # No dotenv, fallback key, command-line secret or account modification.
    value=os.environ.get('OPENROUTER_API_KEY')
    if type(value) is not str or not 16<=len(value)<=4096 or any(c.isspace() for c in value):
        raise ExecutionBlocked('owner-injected dedicated credential unavailable')
    return _Credential(value)


class PreparedDispatch:
    """Prepared data, not spending consent or an enabled transport."""
    __slots__=('_payload','_context','_owner','_credential')
    def __init__(self,payload,context,owner,credential):
        self._payload=canonical_bytes(payload);self._context=canonical_bytes(context)
        self._owner=owner;self._credential=credential
    @property
    def payload(self):return json.loads(self._payload)
    @property
    def context(self):return json.loads(self._context)
    def reserve(self):
        p,c=self.payload,self.context
        if (canonical_hash(p)!=c['payload_hash']
            or quote(p['messages'],p['max_completion_tokens'],c['terms'])!=c['envelope']):
            raise ExecutionBlocked('prepared payload/quote changed')
        return self._owner.reserve(c)  # Atomic recheck; no POST is implemented.
    def __repr__(self):return '<Prepared compatibility request; no transport enabled>'


def prepare_new_dispatch(release,review,approval,*,expected_review_hash,expected_approval_hash):
    now=owner_runtime.new_operation_time()
    release,review=precheck_review(release,review,expected_review_hash)
    approval=precheck_dispatch_approval(approval,expected_approval_hash,release,review,expected_review_hash,now=now)
    catalog_body,catalog_receipt=_fetch_public_catalog(release['terms']['model'])
    now=owner_runtime.new_operation_time()
    precheck_dispatch_approval(approval,expected_approval_hash,release,review,expected_review_hash,now=now)
    proof=fresh_proof(catalog_body,catalog_receipt,release['interpretation'],release['terms'],now=now)
    # No production-state resolution or key read occurs above this boundary.
    owner=ProductionOwnerV4.open();snap=owner.snapshot()
    if snap['owner_id']!=approval['owner_id'] or snap['approval_hash']!=expected_approval_hash:
        raise ExecutionBlocked('existing owner/current epoch differs')
    c=make_context(release,expected_approval_hash,proof);owner.check_price_preparation(c)
    owner._register_price_proof(c);owner.check_dispatch(c)
    credential=_read_environment_key()
    return PreparedDispatch(release['request']['payload'],c,owner,credential)


def prepare_existing_statistics(owner,receipt):
    """Already-dispatched accounting only; no new-price/approval-expiry gate."""
    if type(owner) is not ProductionOwnerV4:raise ExecutionBlocked('exact production owner required')
    snap=owner.snapshot();rows=[r for r in snap['charges'] if r['id']==receipt]
    if len(rows)!=1 or rows[0]['status']!='RESPONSE_SEEN' or receipt in snap['statistics_claimed_receipts']:
        raise ExecutionBlocked('existing statistics read unavailable/already claimed')
    credential=_read_environment_key()
    generation=owner.claim_statistics_lookup(receipt)
    return {'generation_id':generation,'credential':credential,'receipt':receipt,
            'scope':'ONE_ALREADY_DISPATCHED_ACCOUNTING_LOOKUP_NO_INFERENCE'}


def run_live_compatibility(*args,**kwargs):
    raise ExecutionBlocked('transport/execution integration and actual owner release not enabled')
