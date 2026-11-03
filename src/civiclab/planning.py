"""Cost review for frozen text calls; no transport, credentials or authorization."""
from decimal import Decimal
from .model import Price,Policy,call_envelope,micros
from .common import canonical_hash


def cost_plan(spec):
    if spec.get('schema_version')!=1 or not isinstance(spec.get('calls'),list) or not spec['calls']:
        raise ValueError('a nonempty versioned call specification is required')
    price=Price(**spec['price']);price.validate()
    totals={'E01':0,'E02':0};rows=[]
    for index,call in enumerate(spec['calls']):
        if not isinstance(call,dict) or set(call)!={'module','messages','max_tokens'} or call['module'] not in totals:
            raise ValueError('each call requires module, exact text messages and output ceiling')
        envelope=call_envelope(call['messages'],call['max_tokens'])
        raw=(Decimal(envelope['input_token_bound'])*Decimal(price.input_usd_per_token)+
             Decimal(envelope['max_tokens'])*Decimal(price.output_usd_per_token))
        # The ledger rounds EACH reservation upward to a microdollar. Rounding
        # the aggregate only could understate a large batch's required cap.
        reserved=micros(raw);totals[call['module']]+=reserved
        rows.append({'call_index':index,'module':call['module'],**envelope,'reservation_microusd':reserved})
    return {'schema_version':1,'status':'REVIEW_ONLY_COST_PLAN','spec_sha256':canonical_hash(spec),
            'pricing':dict(spec['price']),'calls':rows,'call_count':len(rows),
            'module_reservation_microusd':totals,'total_reservation_microusd':sum(totals.values()),
            'total_reservation_usd':str(Decimal(sum(totals.values()))/Decimal(1_000_000)),
            'dispatch_authorized':False,'approved_policy':Policy().__dict__,
            'limitations':['No request was dispatched, reserved, or billed; this plan cannot authorize execution.',
                          'Price validation checks official-domain/freshness/positive values, not authenticity of supplied evidence.',
                          'Exact request bytes and output ceilings must be frozen; adaptive requests need a separately justified upper envelope.',
                          'Caps use conservative per-call byte/framing bounds, not an expected usage or scientific sample-size estimate.',
                          'Actual dispatch still needs reviewed inputs/protocol, fresh verified pricing, rotated credentials and explicit owner budget.']}
