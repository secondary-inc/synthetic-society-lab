"""Unreleased, one-shot uncertainty amendment control. No HTTP or live factory.

Authored tests use isolated mocked OS homes. A separately reviewed terminal
release is required before any actual owner access; actual entry stays denied.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

from .common import canonical_bytes, canonical_hash, sha256_file, atomic_json, redact
from .model import ExecutionBlocked
from .owner_budget_v3 import digest, freeze, utc
from .live_billing_v2 import integer, phase_key
from .production_owner_v4 import (ProductionOwnerV4, NAMESPACE, base_context,
    validate_approval, validate_row, request_binding, price_proof_key)

OLD_RECEIPT = '4fc8f40cbc434a308f11e1094fae5d7a'
EVENT = 'ADDITIONAL_COMPATIBILITY_AMENDMENT_V1'
M_FIELDS = set(('kind owner_id header_hash prior_head prior_active_approval prior_history_hash '
    'predecessor_receipt predecessor_row_hash predecessor_context_hash prior_statistics_claims_hash '
    'release_hash request_binding_hash new_run_id new_unit_id new_phase new_module new_plan_hash '
    'terms_hash total_microusd module_microusd total_dispatches module_dispatches '
    'added_reservation_max valid_from_utc valid_until_utc assertion').split())
R_FIELDS = set('kind reviewer_role policy_hash release_hash code_contract_hash review_id'.split())
O_FIELDS = set('kind policy_hash review_hash approval_hash code_contract_hash assertion credential_state'.split())
HEAD_FIELDS = set('namespace owner_id header_sha256 sequence head_hash'.split())
BUNDLE_FIELDS = set('policy review approval owner_assertion context receipt'.split())


def _load(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: raise ValueError('duplicate owner JSON member')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def _closed(value, fields):
    if type(value) is not dict or set(value) != fields or len(canonical_bytes(value)) > 65536:
        raise ExecutionBlocked('closed bounded amendment artifact required')
    if redact(value) != value:
        raise ExecutionBlocked('credential-like amendment artifact refused')
    return value


def code_contract():
    from . import (common, model, owner_budget_v3, live_billing_v2,
                   production_owner_v4, production_admission_v4, production_price_v4)
    root = Path(__file__).resolve().parents[2]
    mods = (sys.modules[__name__], common, model, owner_budget_v3, live_billing_v2,
            production_owner_v4, production_admission_v4, production_price_v4)
    return {'kind': 'ADDITIONAL_COMPATIBILITY_OWNER_CODE_V1',
            'pins': {str(Path(m.__file__).relative_to(root)): sha256_file(m.__file__) for m in mods},
            'methods': '4053bff6833993a01e9d0dd58e82fa2fa840ba3ae5dbf690449200100418960e',
            'live_factory': 'DENIED_UNRELEASED', 'extra_POSTs': 1}


def receipt_for(m, r, o, c):
    return canonical_hash({'policy_hash': canonical_hash(m), 'review_hash': canonical_hash(r),
        'owner_assertion_hash': canonical_hash(o), 'context_hash': canonical_hash(c)})[:32]


def validate_bundle(bundle, *, expected=None):
    b = freeze(bundle); _closed(b, BUNDLE_FIELDS)
    m, r, a, o, c = (b[k] for k in ('policy', 'review', 'approval', 'owner_assertion', 'context'))
    _closed(m, M_FIELDS); _closed(r, R_FIELDS); _closed(o, O_FIELDS)
    base_context(c); validate_approval(a, m['owner_id'])
    for key in ('header_hash', 'prior_active_approval', 'prior_history_hash', 'predecessor_row_hash',
                'predecessor_context_hash', 'prior_statistics_claims_hash', 'release_hash',
                'request_binding_hash', 'new_plan_hash', 'terms_hash'):
        digest(m[key])
    digest(m['owner_id'], 32); digest(r['review_id'], 32)
    _closed(m['prior_head'], HEAD_FIELDS)
    h = m['prior_head']; digest(h['head_hash']); digest(h['header_sha256']); integer(h['sequence'])
    if h['namespace'] != NAMESPACE or h['owner_id'] != m['owner_id'] or h['header_sha256'] != m['header_hash']:
        raise ExecutionBlocked('prior owner identity mismatch')
    if (m['kind'] != 'ADDITIONAL_COMPATIBILITY_POLICY_V1'
        or m['assertion'] != 'RETAIN_UNKNOWN_OLD_CHARGE_ONE_ADDITIONAL_DISPATCH'
        or m['predecessor_receipt'] != OLD_RECEIPT
        or (m['new_phase'], m['new_module']) != ('compatibility', 'E02')
        or m['total_microusd'] != 1000 or type(m['total_microusd']) is not int
        or m['total_dispatches'] != 2 or type(m['total_dispatches']) is not int
        or m['added_reservation_max'] != 340 or type(m['added_reservation_max']) is not int
        or m['module_microusd'] != {'E01': 0, 'E02': 1000}
        or m['module_dispatches'] != {'E01': 0, 'E02': 2}
        or any(type(v) is not int for k in ('module_microusd','module_dispatches') for v in m[k].values())):
        raise ExecutionBlocked('one-shot fixed limits differ')
    start, end = utc(m['valid_from_utc']), utc(m['valid_until_utc'])
    if not 120 <= (end-start).total_seconds() <= 600:
        raise ExecutionBlocked('bounded amendment lease required')
    if not utc(c['terms']['valid_from_utc']) <= start < end <= utc(c['terms']['valid_until_utc']):
        raise ExecutionBlocked('amendment outside released price window')
    if (r['kind'] != 'ADDITIONAL_COMPATIBILITY_REVIEW_V1' or r['reviewer_role'] != 'independent_auditor'
        or r['policy_hash'] != canonical_hash(m) or r['release_hash'] != m['release_hash']
        or r['code_contract_hash'] != canonical_hash(code_contract())):
        raise ExecutionBlocked('exact independent amendment/code review required')
    if (o != {'kind': 'EXTERNAL_ADDITIONAL_COMPATIBILITY_OWNER_ASSERTION_V1',
        'policy_hash': canonical_hash(m), 'review_hash': canonical_hash(r), 'approval_hash': canonical_hash(a),
        'code_contract_hash': r['code_contract_hash'],
        'assertion': 'EXPLICITLY_ALLOW_ONE_NEW_REQUEST_WHILE_PRIOR_BILLING_UNKNOWN',
        'credential_state': 'OWNER_ASSERTED_ROTATED_DEDICATED_KEY_AND_PREFUNDED'}):
        raise ExecutionBlocked('explicit external uncertainty exception required')
    if expected is not None:
        _closed(expected, set('policy review approval owner_assertion'.split()))
        if any(expected[k] != canonical_hash(b[k]) for k in expected):
            raise ExecutionBlocked('externally expected amendment hash differs')
    for key in ('owner_id', 'valid_from_utc', 'valid_until_utc', 'total_microusd',
                'module_microusd', 'total_dispatches', 'module_dispatches'):
        if a[key] != m[key]: raise ExecutionBlocked('approval differs from bounded policy')
    if (a['previous_approval_hash'] != m['prior_active_approval'] or a['review_hash'] != canonical_hash(r)
        or a['release_hash'] != m['release_hash'] or c['approval_hash'] != canonical_hash(a)
        or c['release_hash'] != m['release_hash'] or c['plan_hash'] != m['new_plan_hash']
        or c['run_id'] != m['new_run_id'] or c['unit_id'] != m['new_unit_id']
        or c['phase'] != m['new_phase'] or c['module'] != m['new_module']
        or canonical_hash(c['terms']) != m['terms_hash'] or request_binding(c) != m['request_binding_hash']):
        raise ExecutionBlocked('exact request/approval mapping differs')
    e = c['envelope']
    if (e['reserved_microusd'] > 340 or e['input_token_bound'] > 2276 or e['max_tokens'] != 32
        or c['terms']['model'] != 'openai/gpt-4.1-nano' or c['terms']['requested_route'] != 'azure'
        or c['terms']['reported_provider'] != 'Azure'
        or c['sampling'] != {'seed': 20261103, 'temperature': 0, 'retries': 0}):
        raise ExecutionBlocked('fixed compatibility request bound differs')
    plan = {'module': 'E02', 'terms_sha256': m['terms_hash'], 'max_tokens': 32,
            'max_input_token_bound': e['input_token_bound'], 'request_binding_hash': request_binding(c)}
    if a['allowed_plans'] != {m['new_plan_hash']: plan}:
        raise ExecutionBlocked('one exact plan required')
    if b['receipt'] != receipt_for(m, r, o, c):
        raise ExecutionBlocked('deterministic one-shot receipt differs')
    return b


def open_actual(*args, **kwargs):
    raise ExecutionBlocked('additional-test actual factory unreleased; no owner/key access')


class _AdditionalOwnerV1(ProductionOwnerV4):
    """Private candidate owner, used only in isolated authored tests until review."""
    @classmethod
    def initialize(cls, *args, **kwargs):
        raise ExecutionBlocked('successor cannot bootstrap or replace an owner')

    def _predecessor(self, state, m, *, head, history):
        old = state['rows'].get(OLD_RECEIPT)
        if (set(state['rows']) != {OLD_RECEIPT} or old is None or state['unfinished'] != 1
            or state['active'] != m['prior_active_approval'] or head != m['prior_head']
            or canonical_hash(self.header) != m['header_hash'] or self.header['owner_id'] != m['owner_id']
            or canonical_hash(history) != m['prior_history_hash']
            or canonical_hash(old) != m['predecessor_row_hash']
            or canonical_hash(old['context']) != m['predecessor_context_hash']
            or canonical_hash(sorted(state['statistics_claims'])) != m['prior_statistics_claims_hash']
            or state['statistics_claims'] or old['status'] != 'UNCERTAIN'
            or old['charged'] != 340 or old['reserved'] != 340
            or any(old[k] is not None for k in ('observed_cost','generation_id','output_hash','billing','checkpoint_hash'))
            or state['consumed'] != {'total':340,'modules':{'E01':0,'E02':340},
                'dispatches':1,'module_dispatches':{'E01':0,'E02':1}}
            or m['new_run_id'] == old['context']['run_id']):
            raise ExecutionBlocked('exact retained uncertain predecessor/history required')

    def _apply(self, event, state):
        kind, p = event['kind'], event['payload']
        extra = state.get('additional')
        if kind == EVENT:
            if extra is not None: raise ExecutionBlocked('one-shot amendment already consumed')
            b = validate_bundle(p); m = b['policy']
            prior = state['max_clock']
            now = self._clock(event, state)
            if (event['clock_status'] != 'OK' or now is None or (prior is not None and now < prior)
                or not utc(m['valid_from_utc']) <= now < utc(m['valid_until_utc'])):
                raise ExecutionBlocked('new amendment authority clock unavailable/rollback/expired')
            self._predecessor(state, m, head=state['_prefix_head'], history=state['_prefix_events'])
            state['additional'] = {'policy_hash':canonical_hash(m),'receipt':b['receipt'],
                                   'batch_stage':'APPROVAL','spent':False}
            state['_amendment_bundle'] = b
            return
        if extra is None:
            return super()._apply(event, state)
        b = state['_amendment_bundle']; m = b['policy']; c = b['context']; a = b['approval']
        if extra['batch_stage'] != 'COMPLETE':
            if kind != extra['batch_stage']:
                raise ExecutionBlocked('amendment must contain exact atomic four-event grammar')
            prior = state['max_clock']; now = self._clock(event, state)
            if (now is None or event['clock_status'] != 'OK' or (prior and now < prior)
                or not utc(m['valid_from_utc']) <= now < utc(m['valid_until_utc'])):
                raise ExecutionBlocked('new batch authority clock invalid')
            if kind == 'APPROVAL':
                if p != a or a['approval_id'] in state['approval_ids'] or a['previous_approval_hash'] != state['active']:
                    raise ExecutionBlocked('amendment approval differs')
                state['active'] = canonical_hash(a); state['approvals'][state['active']] = deepcopy(a)
                state['approval_ids'].add(a['approval_id']); extra['batch_stage'] = 'PRICE_PROOF'
            elif kind == 'PRICE_PROOF':
                if p != {'context':c}: raise ExecutionBlocked('amendment price proof differs')
                self._binding({'context':c},a)
                age = (now-utc(c['price_proof']['observed_at_utc'])).total_seconds()
                if not 0 <= age <= 900: raise ExecutionBlocked('price evidence stale/future')
                state['price_proofs'].add(price_proof_key(c)); extra['batch_stage'] = 'RESERVE'
            else:
                _closed(p, {'before_hash','after'}); row=p['after']; validate_row(row)
                if (p['before_hash'] is not None or row != self._new_row(b) or row['id'] in state['rows']
                    or phase_key(c) in state['keys'] or price_proof_key(c) not in state['price_proofs']
                    or state['unfinished'] != 1 or state['consumed']['dispatches'] != 1
                    or state['consumed']['total'] + row['reserved'] > 680):
                    raise ExecutionBlocked('one-shot reservation differs or consumed')
                self._binding(row,a)
                state['rows'][row['id']] = deepcopy(row); state['keys'].add(phase_key(c))
                state['consumed']['total'] += row['reserved']; state['consumed']['modules']['E02'] += row['reserved']
                state['consumed']['dispatches'] += 1; state['consumed']['module_dispatches']['E02'] += 1
                state['unfinished'] += 1; extra['spent'] = True; extra['batch_stage'] = 'COMPLETE'
            return
        if kind not in ('TRANSITION','STATISTICS_CLAIM'):
            raise ExecutionBlocked('additional reservation permanently consumed; no renewal')
        target = p.get('receipt') if kind == 'STATISTICS_CLAIM' else p.get('after',{}).get('id')
        if target != extra['receipt']:
            raise ExecutionBlocked('historical predecessor cannot change under exception')
        # Original accounting transitions do not relax unfinished checks and can
        # operate directly on the true two-row state. Never mask that state.
        return super()._apply(event, state)

    @staticmethod
    def _new_row(b):
        c=b['context']; amount=c['envelope']['reserved_microusd']
        return {'id':b['receipt'],'context':deepcopy(c),'reserved':amount,'charged':amount,
            'status':'STARTED','generation_id':None,'output_hash':None,'observed_cost':None,
            'checkpoint_hash':None,'error_type':None,'billing':None}

    def _verify(self, db):
        self._registration()
        if not self.anchor.is_file() or self.anchor.is_symlink():
            raise ExecutionBlocked('owner head missing; no reset')
        if freeze(_load(self.guard.read_text())) != self.header:
            raise ExecutionBlocked('owner guard identity changed')
        headers=db.execute('SELECT data FROM header').fetchall()
        if len(headers)!=1 or _load(headers[0][0])!=self.header: raise ValueError('owner header changed')
        rows=db.execute('SELECT sequence,data,digest FROM events ORDER BY sequence LIMIT 10001').fetchall()
        if not 1 <= len(rows) <= 10000: raise ExecutionBlocked('bounded owner history required')
        state=self._empty(); previous=None; history=[]
        for i,(sequence,data,h) in enumerate(rows):
            if len(data.encode())>65536: raise ExecutionBlocked('owner event exceeds bound')
            event=_load(data)
            if (set(event)!={'sequence','previous','body'} or type(sequence) is not int
                or type(event['sequence']) is not int or sequence!=i or event['sequence']!=i
                or event['previous']!=previous or canonical_hash(event)!=h
                or (i==0)!=(event['body'].get('kind')=='GENESIS')):
                raise ValueError('owner history changed')
            state['_prefix_head']={'namespace':NAMESPACE,'owner_id':self.header['owner_id'],
                'header_sha256':canonical_hash(self.header),'sequence':i-1,'head_hash':previous}
            state['_prefix_events']=history
            self._apply(event['body'],state); history.append(event); previous=h
        if state.get('additional',{}).get('batch_stage','COMPLETE')!='COMPLETE':
            raise ExecutionBlocked('partial amendment journal refused')
        head={'namespace':NAMESPACE,'owner_id':self.header['owner_id'],
              'header_sha256':canonical_hash(self.header),'sequence':len(rows)-1,'head_hash':previous}
        if _load(self.anchor.read_text())!=head: raise ExecutionBlocked('owner store/head torn or truncated')
        actual_rows=db.execute('SELECT id,data FROM charges LIMIT 1025').fetchall()
        if len(actual_rows)>1024: raise ExecutionBlocked('owner rows exceed limit')
        actual={i:_load(data) for i,data in actual_rows}
        if actual!=state['rows']: raise ValueError('materialized charges differ from protected history')
        state['_prefix_head']=head; state['_prefix_events']=history
        return state,head

    def append_authored_batch(self, bundle, *, expected, release, credential_shape_check):
        """Candidate atomic control only. No network; no actual release entry."""
        if expected is None: raise ExecutionBlocked('externally expected hashes required')
        b=validate_bundle(bundle,expected=expected); m=b['policy']; c=b['context']
        from .production_admission_v4 import compile_compatibility_release, make_context
        compiled=compile_compatibility_release(release['terms'],release['interpretation'],
                    run_id=m['new_run_id'],seed=20261103,max_tokens=32)
        if (release!=compiled or canonical_hash(release)!=m['release_hash']
            or c!=make_context(release,canonical_hash(b['approval']),c['price_proof'])):
            raise ExecutionBlocked('exact released system/user bytes and context required')
        with self._lock(),self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state,head=self._verify(db)
            self._predecessor(state,m,head=head,history=state['_prefix_events'])
            if len(state['_prefix_events'])+4>10000:
                raise ExecutionBlocked('four-event batch does not fit history cap')
            from .production_owner_v4 import new_operation_time
            now=new_operation_time()
            if not utc(m['valid_from_utc'])<=now or (utc(m['valid_until_utc'])-now).total_seconds()<120:
                raise ExecutionBlocked('full phase does not fit authority window')
            # This callback validates an opaque authored transport/credential;
            # actual release must supply a sealed non-caller-controlled factory.
            if credential_shape_check() is not True:
                raise ExecutionBlocked('credential/transport shape unavailable')
            bodies=[]
            for kind,payload in ((EVENT,b),('APPROVAL',b['approval']),
                ('PRICE_PROOF',{'context':c}),('RESERVE',{'before_hash':None,'after':self._new_row(b)})):
                body=self._event(kind,payload,state,new=True)
                self._apply(body,state); bodies.append(body)
            tail=[]; previous=head['head_hash']
            for offset,body in enumerate(bodies,1):
                sequence=head['sequence']+offset
                event={'sequence':sequence,'previous':previous,'body':body}; h=canonical_hash(event)
                if len(canonical_bytes(event))>65536:
                    raise ExecutionBlocked('batch event exceeds immutable history bound')
                db.execute('INSERT INTO events VALUES (?,?,?)',(sequence,json.dumps(event,sort_keys=True),h))
                tail.append(event); previous=h
            row=state['rows'][b['receipt']]
            db.execute('INSERT INTO charges VALUES (?,?)',(row['id'],json.dumps(row,sort_keys=True)))
            db.commit()  # An anchor failure intentionally leaves a refusing store.
            newhead={**head,'sequence':head['sequence']+4,'head_hash':previous}
            atomic_json(self.anchor,newhead)
            checked,actual_head=self._verify(db)
            if actual_head!=newhead or checked['rows'][row['id']]!=row:
                raise ExecutionBlocked('postcommit acknowledgement verification failed')
            # This is accounting evidence, NOT a POST capability. The future
            # separately reviewed fixed-run client must persist ACK/intent and
            # construct a single-use capability. No transport exists here.
            return {'receipt':row['id'],'head':newhead,'dispatch_capability':False}
