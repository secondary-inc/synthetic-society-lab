"""Separately versioned Qwen reported-null tier policy; never financial authority.

The caller must bind the released text-only/no-tools request, retained metadata
bytes and policy review separately. Optional unknown counts do not prove zero
hidden activity. This module does not read files, credentials or a ledger.
"""
import re

from ..common import canonical_hash
from ..model import ExecutionBlocked
from ..production_compatibility_v4_2_1 import _cost

BASE_MODEL='openai/gpt-4.1-nano'
DATED_MODEL='openai/gpt-4.1-nano-2025-04-14'
MODEL_ALIAS_EVIDENCE_SHA256='e234cd7362756b3bfe4411471f6966bec6a2be7ef81bff131f6a4c30ea9164be'
SCHEMA_EVIDENCE_SHA256='33c53c85504e0f3a314d834a179c731597493d24ad68d4f0ba0193824184012e'
POLICY_ID='E02_CROSSMODEL_RECOVERY_METADATA_V1'
QWEN_MODEL='qwen/qwen3-30b-a3b-instruct-2507'
QWEN_EVIDENCE_SHA256='7ac46d2beb770a466cf11220cacd8b770dc1dbbd25262348c7eeec289ae45a8f'
COUNTERS=('native_tokens_completion_images','num_media_prompt','num_media_completion',
          'num_input_audio_prompt','num_search_results','num_fetches')
BILLING_FIELDS=('id','model','provider_name','total_cost','native_tokens_prompt',
                'native_tokens_completion','native_tokens_reasoning','is_byok')


def response_model_allowed(model,requested_model):
    if type(model) is not str or type(requested_model) is not str:return False
    return ((requested_model==BASE_MODEL and model in (BASE_MODEL,DATED_MODEL))
            or (requested_model==QWEN_MODEL and model==QWEN_MODEL))


def normalize_statistics(stats,*,generation_id,requested_model,reported_provider,
                         input_bound,output_bound,reserved_microusd,request_payload):
    """Return an explicitly NORMALIZED eight-field projection plus raw telemetry.

    No arbitrary suffix removal, null-to-zero conversion, invented model prices,
    financial transition or proof of human/operator permission is performed.
    """
    validate_request(request_payload, requested_model)
    if type(stats) is not dict:
        raise ExecutionBlocked('generation metadata object required')
    if (type(generation_id) is not str or len(generation_id)>128 or
        re.fullmatch(r'gen-[A-Za-z0-9-]+',generation_id) is None or
        type(stats.get('id')) is not str or stats['id']!=generation_id):
        raise ExecutionBlocked('exact safe generation identity required')
    if (not response_model_allowed(stats.get('model'),requested_model) or
        type(reported_provider) is not str or
        reported_provider!={BASE_MODEL:'Azure',QWEN_MODEL:'Nebius'}.get(requested_model) or
        stats.get('provider_name')!=reported_provider or type(stats.get('provider_name')) is not str or
        stats.get('is_byok') is not False):
        raise ExecutionBlocked('reviewed exact model/provider/non-BYOK required')
    for value,limit in ((input_bound,8192),(output_bound,512),(reserved_microusd,31250)):
        if type(value) is not int or not 1<=value<=limit:
            raise ExecutionBlocked('released bounded request envelope required')
    for key,bound in (('native_tokens_prompt',input_bound),('native_tokens_completion',output_bound),('native_tokens_reasoning',0)):
        if type(stats.get(key)) is not int or not 0<=stats[key]<=bound:
            raise ExecutionBlocked('mandatory observed native usage outside bound')
    if 'service_tier' not in stats:
        raise ExecutionBlocked('service tier field must be reported')
    tier = stats['service_tier']
    if not ((type(tier) is str and tier == 'default') or
            (requested_model == QWEN_MODEL and reported_provider == 'Nebius' and tier is None)):
        raise ExecutionBlocked('only default or fixed Qwen reported-null tier admitted')
    if type(stats.get('streamed')) is not bool or stats.get('cancelled') is not False:
        raise ExecutionBlocked('literal streaming and false cancellation observations required')
    counters={}
    for key in COUNTERS:
        if key not in stats:
            counters[key]={'status':'NOT_REPORTED_UNKNOWN','present':False}
        elif stats[key] is None:
            counters[key]={'status':'REPORTED_NULL_UNKNOWN','present':True,'value':None}
        elif type(stats[key]) is int and stats[key]==0:
            counters[key]={'status':'OBSERVED_ZERO','present':True,'value':0}
        else:
            raise ExecutionBlocked('unsupported activity or malformed optional counter')
    if stats.get('web_search_engine') is not None:
        raise ExecutionBlocked('unsupported search engine observation')
    search={'status':'REPORTED_NULL_UNKNOWN','present':True,'value':None} if 'web_search_engine' in stats else {'status':'NOT_REPORTED_UNKNOWN','present':False}
    try:amount=_cost(stats.get('total_cost'))
    except (ValueError,TypeError,ArithmeticError) as error:
        raise ExecutionBlocked('finite nonnegative total bill required') from None
    if amount>reserved_microusd:
        raise ExecutionBlocked('all-in reported bill exceeds released reservation')
    billing={key:stats[key] for key in BILLING_FIELDS}
    billing['model']=requested_model
    telemetry={'policy_id':POLICY_ID,'billing_representation':'NORMALIZED_INTERNAL_PROJECTION_NOT_RAW',
        'reported_model':stats['model'],'requested_model':requested_model,
        'model_mapping':'EXACT_BASE_ID' if stats['model']==requested_model else 'EXACT_REVIEWED_DATED_ALIAS',
        'model_alias_evidence_sha256':MODEL_ALIAS_EVIDENCE_SHA256 if requested_model==BASE_MODEL else QWEN_EVIDENCE_SHA256,'schema_evidence_sha256':SCHEMA_EVIDENCE_SHA256,
        'reported_service_tier':tier,
        'service_tier_status':'REPORTED_NULL_UNKNOWN' if tier is None else 'OBSERVED_LITERAL_DEFAULT',
        'service_tier_limitation':'Reported null means upstream did not report; no default-tier, zero-fee or tier identity inference. Full observed all-in bill still mandatory.',
        'request_no_tier_override':True,'reported_streamed':stats['streamed'],
        'requested_stream':False,'streamed_discrepancy':stats['streamed'] is True,
        'streaming_scope':'Client request/complete JSON transport controlled separately; provider telemetry meaning unresolved.',
        'reported_cancelled':stats['cancelled'],'optional_counters':counters,'web_search_engine':search,
        'input_metadata_canonical_sha256':canonical_hash(stats),
        'unknown_activity_limitation':'Unknown optional counts are not observed zeros; admission requires separately reviewed text-only/no-tools and all-in bill applicability.',
        'actual_authority':False}
    return {'billing':billing,'telemetry':telemetry,'observed_cost_microusd':amount}


def validate_request(payload, model):
    """Only the unchanged released nonstreaming text request can use this policy."""
    keys={'model','messages','stream','seed','temperature','max_completion_tokens',
          'response_format','plugins','tools','tool_choice','provider'}
    if (type(payload) is not dict or set(payload)!=keys or payload['model']!=model
            or payload['stream'] is not False or type(payload['seed']) is not int
            or type(payload['temperature']) is not int or payload['temperature']!=0
            or type(payload['max_completion_tokens']) is not int or payload['max_completion_tokens']!=256
            or payload['response_format']!={'type':'json_object'} or payload['plugins']!=[]
            or payload['tools']!=[] or payload['tool_choice']!='none'
            or type(payload['messages']) is not list or len(payload['messages'])!=2):
        raise ExecutionBlocked('exact text-only request without tier override required')
    provider=payload['provider']
    route={BASE_MODEL:'azure',QWEN_MODEL:'nebius/fp8'}.get(model)
    if (route is None or type(provider) is not dict
            or set(provider)!={'only','allow_fallbacks','require_parameters','max_price'}
            or provider['only']!=[route] or provider['allow_fallbacks'] is not False
            or provider['require_parameters'] is not True):
        raise ExecutionBlocked('fixed no-fallback route required')
