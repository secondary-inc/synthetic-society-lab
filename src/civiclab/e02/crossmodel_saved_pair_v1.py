"""Pure exact admission of two saved baselines; no GET/POST or settlement.

Only scientific witnesses are recovered. Every historical financial row and hold
remains unchanged. Caller supplies independently reviewed exact closed bytes.
"""
from decimal import Decimal
import hashlib

from ..common import canonical_bytes, canonical_hash
from ..model import ExecutionBlocked
from ..production_owner_v4 import base_context, validate_row
from ..production_admission_v4 import _payload
from ..production_compatibility_v4_2_1 import _usage_bounds, _cost
from .exploratory_pilot_analysis_v1 import _load
from .exploratory_live_client_v1 import _no_provider_reasoning, _no_unsupported_response_activity
from .issue_cue_crossmodel_v1 import next_action, parse_response, PROTOCOL_SHA256
from .crossmodel_recovery_metadata_v1 import normalize_statistics, response_model_allowed

KIND = 'CROSSMODEL_SAVED_PAIR_V1'
FIELDS = ('request', 'response', 'statistics', 'dispatch')


def _body(entry, name):
    raw = entry[name+'_utf8']
    if type(raw) is not str:
        raise ExecutionBlocked('exact saved canonical UTF8 bodies required')
    raw = raw.encode('utf8')
    if len(raw) > 32768 or hashlib.sha256(raw).hexdigest() != entry[name+'_sha256']:
        raise ExecutionBlocked('saved body hash or bound differs')
    value = _load(raw, 32768)
    if canonical_bytes(value) != raw or type(value) is not dict:
        raise ExecutionBlocked('canonical saved object required')
    return value


def admit_saved_pair(protocol_bytes, bundle, old_study, rows, statistics_claims):
    """Validate exact old request/evidence against live-owner ancestry on replay.

    This never mutates supplied rows or uses a new price contract for old requests.
    Exact response output and native generation bill are independently checked.
    """
    if (type(bundle) is not dict or set(bundle) != {'kind','protocol_sha256','source_packet_sha256','source_run_id','pairs'}
            or bundle['kind'] != KIND or bundle['protocol_sha256'] != PROTOCOL_SHA256
            or type(bundle['pairs']) is not list or len(bundle['pairs']) != 2
            or len(canonical_bytes(bundle)) > 48000
            or not old_study['stopped'] or old_study['pending'] is not None
            or len(old_study['receipts']) != 2 or len(old_study['witnesses']) != 1
            or canonical_hash(old_study['packet']) != bundle['source_packet_sha256']
            or old_study['packet']['policy']['run_id'] != bundle['source_run_id']):
        raise ExecutionBlocked('exact stopped two-dispatch ancestry required')
    terms = {k:v['terms'] for k,v in old_study['packet']['price_release'].items()}
    transcript = []; witnesses = []
    for order, entry in enumerate(bundle['pairs']):
        expected_keys = {'receipt','row_sha256'} | {n+s for n in FIELDS for s in ('_utf8','_sha256')}
        if type(entry) is not dict or set(entry) != expected_keys:
            raise ExecutionBlocked('closed saved evidence entry required')
        rid = entry['receipt']
        if rid != old_study['receipts'][order] or rid not in rows:
            raise ExecutionBlocked('saved receipt/order differs')
        row = rows[rid]; validate_row(row); c = row['context']; base_context(c)
        if (canonical_hash(row) != entry['row_sha256'] or rid not in statistics_claims
                or c['run_id'] != bundle['source_run_id'] or c['phase'] != 'pre'
                or c['unit_id'] != f'crossmodel-{order:02d}'
                or (order == 0 and row['status'] != 'PHASE_COMMITTED')
                or (order == 1 and (row['status'] != 'UNCERTAIN' or row['charged'] != row['reserved']))):
            raise ExecutionBlocked('saved row/claim/status/hold differs')
        bodies = {n:_body(entry,n) for n in FIELDS}
        req, response, result, dispatch = (bodies[n] for n in FIELDS)
        action = next_action(protocol_bytes, terms, canonical_bytes(transcript))
        compiled = action['request']; payload = compiled['payload']
        if (action['status'] != 'REQUEST_READY_NOT_ADMITTED' or compiled['execution_order'] != order
                or set(req) != {'request','context','plan'} or req['request'] != compiled
                or req['context'] != c or canonical_hash(req['plan']) != c['plan_hash']
                or c['payload_hash'] != compiled['payload_sha256'] or c['envelope'] != compiled['envelope']
                or c['terms'] != terms[compiled['model_key']]
                or payload != _payload(compiled['messages'],compiled['pair_seed'],256,c['terms'])
                or dispatch.get('receipt') != rid or dispatch.get('context_hash') != canonical_hash(c)
                or dispatch.get('payload_sha256') != compiled['payload_sha256']
                or dispatch.get('status') != 'ACKNOWLEDGED_POST_INTENT_CONSUMED'):
            raise ExecutionBlocked('saved exact request/context/dispatch differs')
        if (response.get('id') != row['generation_id']
                or not response_model_allowed(response.get('model'),c['terms']['model'])):
            raise ExecutionBlocked('saved response identity differs')
        _no_provider_reasoning(response); _no_unsupported_response_activity(response)
        usage = response.get('usage'); _usage_bounds(usage,c['envelope'])
        parsed = parse_response(response)
        if parsed['status'] != 'ANSWER':
            raise ExecutionBlocked('saved baseline must have bounded parsed answer')
        stats = result.get('data')
        normalized = normalize_statistics(stats,generation_id=row['generation_id'],requested_model=c['terms']['model'],
            reported_provider=c['terms']['reported_provider'],input_bound=c['envelope']['input_token_bound'],
            output_bound=256,reserved_microusd=row['reserved'],request_payload=payload)
        if (type(usage) is not dict or usage.get('cost') is None
                or Decimal(str(usage['cost'])) != Decimal(str(stats['total_cost']))
                or _cost(stats['total_cost']) != row['observed_cost']):
            raise ExecutionBlocked('saved response/generation/row cost disagreement')
        output = {'status':parsed['status'],'answer':parsed['answer'],'response_raw_sha256':entry['response_sha256']}
        if canonical_hash(output) != row['output_hash']:
            raise ExecutionBlocked('saved observed output hash differs')
        if order == 0:
            old = old_study['witnesses'][0]
            if (old['receipt'] != rid or old['payload_sha256'] != compiled['payload_sha256']
                    or old['response_raw_sha256'] != entry['response_sha256']
                    or old['statistics_raw_sha256'] != entry['statistics_sha256']
                    or old['status'] != parsed['status'] or old['answer'] != parsed['answer']
                    or canonical_hash(row['billing']) != canonical_hash(normalized['billing'])):
                raise ExecutionBlocked('saved committed witness differs')
        record = {'execution_order':order,'phase':'pre','payload_sha256':compiled['payload_sha256'],
                  'status':parsed['status'],'answer':parsed['answer']}
        transcript.append(record)
        witnesses.append({'kind':'CROSSMODEL_SAVED_BASELINE_WITNESS_V1', **record,
            'receipt':rid,'context_hash':canonical_hash(c),'row_sha256':entry['row_sha256'],
            'response_raw_sha256':entry['response_sha256'],'statistics_raw_sha256':entry['statistics_sha256'],
            'generation_id':row['generation_id'],'telemetry':normalized['telemetry'],
            'financial_state_unchanged':True,'historical_hold_released':False})
    return {'kind':'CROSSMODEL_SAVED_PAIR_ADMISSION_V1','bundle_sha256':canonical_hash(bundle),
            'transcript':transcript,'witnesses':witnesses,'new_POSTs':0,'new_GETs':0,
            'financial_transitions':0,'actual_authority':False}
