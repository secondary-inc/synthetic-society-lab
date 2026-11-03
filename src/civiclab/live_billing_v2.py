"""Versioned global billing state machine. Authored fixtures only; no network.

A durable reservation binds the experimental phase BEFORE its inference request.
All runs/modules share one explicitly opened control directory. Missing/torn state
never creates a fresh allowance. Hostile replacement of every authority file is
outside this local integrity model. Production bootstrap/release is unavailable.
"""
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import fcntl
import json
from pathlib import Path
import sqlite3
import uuid

from .common import atomic_json, canonical_hash, redact, sha256_file, utc_now
from .model import ExecutionBlocked, call_envelope, micros

PHASES = {'pre', 'post', 'forecast'}
_COMMIT_CAPABILITY = object()
TRANSITIONS = {'STARTED': {'RESPONSE_SEEN', 'UNCERTAIN'},
               'RESPONSE_SEEN': {'SETTLED', 'UNCERTAIN', 'OVERRUN'},
               'SETTLED': {'PHASE_COMMITTED', 'UNCERTAIN', 'OVERRUN'},
               'PHASE_COMMITTED': set(), 'UNCERTAIN': set(), 'OVERRUN': set()}
ROW_KEYS = {'id', 'context', 'reserved', 'charged', 'status', 'generation_id',
            'output_hash', 'observed_cost', 'checkpoint_hash', 'error_type', 'billing'}


def integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise ValueError('invalid bounded integer')
    return value


def fixture_policy(total=100_000, e01=50_000, e02=50_000):
    return {'mode': 'AUTHORED_FIXTURE_NOT_OWNER_AUTHORIZATION', 'approval_id': 'MOCK_ONLY',
            'total_microusd': total, 'module_microusd': {'E01': e01, 'E02': e02}}


def validate_policy(policy):
    if (set(policy) != {'mode', 'approval_id', 'total_microusd', 'module_microusd'}
        or policy['mode'] != 'AUTHORED_FIXTURE_NOT_OWNER_AUTHORIZATION'
        or policy['approval_id'] != 'MOCK_ONLY' or set(policy['module_microusd']) != {'E01', 'E02'}):
        raise ExecutionBlocked('only explicitly simulated policy is implemented')
    integer(policy['total_microusd'], 1)
    for amount in policy['module_microusd'].values(): integer(amount)


def validate_terms(terms):
    if set(terms) != {'model', 'requested_route', 'reported_provider', 'input_usd_per_token',
                      'output_usd_per_token', 'request_fee_usd', 'pricing_scope'}:
        raise ValueError('complete versioned endpoint terms required')
    if terms['pricing_scope'] != 'AUTHORED_FIXTURE_NOT_PRICE_EVIDENCE':
        raise ExecutionBlocked('real price/release not implemented')
    for name in ('model', 'requested_route', 'reported_provider'):
        if not isinstance(terms[name], str) or not terms[name] or len(terms[name]) > 128:
            raise ValueError('invalid route/model identifier')
    for name in ('input_usd_per_token', 'output_usd_per_token', 'request_fee_usd'):
        if not isinstance(terms[name], str): raise ValueError('decimal string pricing required')
        if len(terms[name]) > 64: raise ValueError('price exceeds supported decimal precision')
        value = Decimal(terms[name])
        if not value.is_finite() or not 0 <= value <= 100 or value.as_tuple().exponent < -18:
            raise ValueError('price domain unsupported; independent review required')
        micros(terms[name])


def quote(messages, max_tokens, terms):
    validate_terms(terms)
    if redact(messages) != messages: raise ValueError('credential-like messages rejected')
    envelope = {**call_envelope(messages, max_tokens), 'message_count': len(messages)}
    amount = (Decimal(envelope['input_token_bound']) * Decimal(terms['input_usd_per_token'])
              + Decimal(max_tokens) * Decimal(terms['output_usd_per_token'])
              + Decimal(terms['request_fee_usd']))
    return {**envelope, 'reserved_microusd': integer(micros(amount), 1)}


def phase_key(context):
    return canonical_hash({k: context[k] for k in ('run_id', 'unit_id', 'phase', 'module')})


class GlobalFixtureLedger:
    """Explicit create-once fixture bootstrap; open never creates missing state."""
    def __init__(self, directory, policy):
        self.directory = Path(directory).resolve(); self.policy = deepcopy(policy)
        validate_policy(self.policy)
        self.db_path = self.directory / 'owner-ledger.local.sqlite'
        self.anchor = self.directory / 'owner-anchor.local.json'
        self.guard = self.directory / 'owner-guard.local.lock'

    @classmethod
    def create(cls, directory, policy=None):
        obj = cls(directory, policy or fixture_policy())
        obj.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Exclusive bootstrap marker survives even an interrupted initialization.
        with obj.guard.open('xb'):
            pass
        obj.guard.chmod(0o600)
        if obj.db_path.exists() or obj.anchor.exists():
            raise ExecutionBlocked('owner ledger already exists or bootstrap is incomplete')
        ledger_id = uuid.uuid4().hex
        obj.db_path.touch(mode=0o600, exist_ok=False)
        with obj._lock(), obj._connect() as db:
            db.execute('CREATE TABLE header (data TEXT NOT NULL)')
            db.execute('CREATE TABLE charges (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('CREATE TABLE events (sequence INTEGER PRIMARY KEY, data TEXT NOT NULL, digest TEXT NOT NULL)')
            header = {'schema_version': 1, 'ledger_id': ledger_id, 'policy': obj.policy}
            db.execute('INSERT INTO header VALUES (?)', (json.dumps(header, sort_keys=True),))
            event = {'kind': 'GENESIS', 'header_hash': canonical_hash(header), 'previous': None}
            digest = canonical_hash(event)
            db.execute('INSERT INTO events VALUES (0,?,?)', (json.dumps(event, sort_keys=True), digest))
            db.commit()
            atomic_json(obj.anchor, {'ledger_id': ledger_id, 'policy_hash': canonical_hash(obj.policy),
                                     'sequence': 0, 'head': digest})
        return obj

    @classmethod
    def open(cls, directory, policy):
        obj = cls(directory, policy)
        with obj._lock(), obj._connect() as db: obj._verify(db)
        return obj

    @contextmanager
    def _lock(self):
        if not self.guard.is_file(): raise ExecutionBlocked('owner ledger bootstrap missing; no reset')
        with self.guard.open('rb') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _connect(self):
        if not self.db_path.is_file(): raise ExecutionBlocked('owner ledger missing; no reset')
        return sqlite3.connect(self.db_path, timeout=30)

    @staticmethod
    def _validate_context(context):
        if set(context) != {'run_id', 'unit_id', 'phase', 'module', 'terms', 'envelope', 'sampling', 'payload_hash'}:
            raise ValueError('phase context schema mismatch')
        if context['module'] not in ('E01', 'E02') or context['phase'] not in PHASES:
            raise ValueError('unknown module or phase')
        for key in ('run_id', 'unit_id'):
            value = context[key]
            if not isinstance(value, str) or not value or len(value) > 128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in value):
                raise ValueError('unsafe phase identity')
        sampling = context['sampling']
        if (set(sampling) != {'seed', 'temperature', 'retries'} or type(sampling['seed']) is not int
            or not 0 <= sampling['seed'] < 2**32 or type(sampling['temperature']) is not int
            or sampling['temperature'] != 0 or type(sampling['retries']) is not int or sampling['retries'] != 0):
            raise ValueError('unsupported sampling or retry policy')
        if not isinstance(context['payload_hash'], str) or len(context['payload_hash']) != 64 or any(c not in '0123456789abcdef' for c in context['payload_hash']):
            raise ValueError('invalid exact payload hash')
        validate_terms(context['terms']); env = context['envelope']
        if set(env) != {'input_token_bound', 'max_tokens', 'request_hash', 'encoded_message_bytes', 'message_count', 'reserved_microusd'}:
            raise ValueError('phase envelope schema mismatch')
        for key in ('input_token_bound', 'max_tokens', 'encoded_message_bytes', 'message_count', 'reserved_microusd'): integer(env[key], 1)
        if env['input_token_bound'] != env['encoded_message_bytes'] + 1024 * env['message_count']:
            raise ValueError('input bound differs from exact framing envelope')
        if env['max_tokens'] > 4096 or env['encoded_message_bytes'] > 100000:
            raise ValueError('phase envelope limits exceeded')
        if not isinstance(env['request_hash'], str) or len(env['request_hash']) != 64 or any(c not in '0123456789abcdef' for c in env['request_hash']):
            raise ValueError('invalid request hash')
        expected = micros(Decimal(env['input_token_bound']) * Decimal(context['terms']['input_usd_per_token'])
                          + Decimal(env['max_tokens']) * Decimal(context['terms']['output_usd_per_token'])
                          + Decimal(context['terms']['request_fee_usd']))
        if env['reserved_microusd'] != expected: raise ValueError('reservation differs from frozen envelope/terms')
        if redact(context) != context: raise ValueError('credential-like context rejected')

    @classmethod
    def _validate_row(cls, row):
        if set(row) != ROW_KEYS: raise ValueError('charge schema mismatch')
        cls._validate_context(row['context'])
        if not isinstance(row['id'], str) or len(row['id']) != 32 or any(c not in '0123456789abcdef' for c in row['id']): raise ValueError('invalid receipt identity')
        for key in ('output_hash', 'checkpoint_hash'):
            value = row[key]
            if value is not None and (not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value)):
                raise ValueError('invalid stored digest')
        value = row['generation_id']
        if value is not None and (not isinstance(value, str) or not value.startswith('gen-') or len(value) > 128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-' for c in value)):
            raise ValueError('unsafe generation identifier')
        if row['error_type'] is not None and (not isinstance(row['error_type'], str) or not row['error_type'].isidentifier() or len(row['error_type']) > 128): raise ValueError('unsafe error metadata')
        integer(row['reserved'], 1); integer(row['charged'])
        if row['reserved'] != row['context']['envelope']['reserved_microusd'] or row['status'] not in TRANSITIONS:
            raise ValueError('charge terms/status mismatch')
        if row['status'] in ('STARTED', 'RESPONSE_SEEN') and row['charged'] != row['reserved']:
            raise ValueError('unsettled reservation was refunded')
        known = 0 if row['observed_cost'] is None else integer(row['observed_cost'])
        if row['status'] in ('UNCERTAIN', 'OVERRUN') and row['charged'] < max(row['reserved'], known):
            raise ValueError('uncertain reservation or known charge was understated')
        if row['observed_cost'] is not None:
            integer(row['observed_cost'])
            if row['status'] in ('SETTLED', 'PHASE_COMMITTED') and row['charged'] != row['observed_cost']:
                raise ValueError('settled charge differs from billing evidence')
        if row['billing'] is not None:
            b = row['billing']; terms = row['context']['terms']; envelope = row['context']['envelope']
            if (not isinstance(b, dict) or set(b) != {'id', 'model', 'provider_name', 'total_cost', 'native_tokens_prompt', 'native_tokens_completion', 'native_tokens_reasoning', 'is_byok'}
                or b['id'] != row['generation_id'] or b['model'] != terms['model']
                or b['provider_name'] != terms['reported_provider'] or b['is_byok'] is not False
                or micros(b['total_cost']) != row['observed_cost']): raise ValueError('billing proof differs from phase identity or cost')
            for key, bound in (('native_tokens_prompt', envelope['input_token_bound']), ('native_tokens_completion', envelope['max_tokens']), ('native_tokens_reasoning', 0)):
                if type(b[key]) is not int or not 0 <= b[key] <= bound: raise ValueError('billing token proof outside envelope')
        if row['status'] in ('SETTLED', 'PHASE_COMMITTED'):
            if row['billing'] is None: raise ValueError('durable serving/token/cost evidence required')
            if row['observed_cost'] is None or row['charged'] > row['reserved'] or not row['generation_id'] or not row['output_hash']:
                raise ValueError('settlement evidence incomplete')
        if row['status'] == 'PHASE_COMMITTED' and not row['checkpoint_hash']:
            raise ValueError('phase checkpoint missing')

    def _verify(self, db):
        if not self.anchor.is_file(): raise ExecutionBlocked('owner anchor missing; no reset')
        anchor = json.loads(self.anchor.read_text()); headers = db.execute('SELECT data FROM header').fetchall()
        if len(headers) != 1: raise ValueError('owner header count mismatch')
        header = json.loads(headers[0][0])
        if header != {'schema_version': 1, 'ledger_id': anchor['ledger_id'], 'policy': self.policy} or anchor['policy_hash'] != canonical_hash(self.policy):
            raise ExecutionBlocked('owner identity/policy changed; no replenishment')
        state = {}; previous = None; identities = set()
        events = db.execute('SELECT sequence,data,digest FROM events ORDER BY sequence').fetchall()
        for index, (sequence, text, digest) in enumerate(events):
            event = json.loads(text)
            if sequence != index or canonical_hash(event) != digest or event.get('previous') != previous:
                raise ValueError('owner event chain changed')
            if index == 0:
                if event != {'kind': 'GENESIS', 'header_hash': canonical_hash(header), 'previous': None}: raise ValueError('invalid genesis')
            else:
                row = event['after']; self._validate_row(row); old = state.get(row['id'])
                if row['generation_id'] is not None and any(r['id'] != row['id'] and r['generation_id'] == row['generation_id'] for r in state.values()):
                    raise ValueError('generation identity reused across phase receipts')
                if event['before'] != (canonical_hash(old) if old else None): raise ValueError('owner prior-state binding changed')
                if old is None:
                    identity = phase_key(row['context'])
                    if row['status'] != 'STARTED' or identity in identities: raise ValueError('duplicate or unreserved phase')
                    if any(r['status'] != 'PHASE_COMMITTED' for r in state.values()): raise ValueError('historical dispatch crossed unfinished global phase')
                    identities.add(identity)
                    total = sum(r['charged'] for r in state.values()); module = row['context']['module']
                    subtotal = sum(r['charged'] for r in state.values() if r['context']['module'] == module)
                    if total + row['reserved'] > self.policy['total_microusd'] or subtotal + row['reserved'] > self.policy['module_microusd'][module]:
                        raise ValueError('historical reservation exceeded owner policy')
                elif (row['status'] not in TRANSITIONS[old['status']] or row['context'] != old['context'] or row['reserved'] != old['reserved']):
                    raise ValueError('invalid owner state transition')
                if old is not None:
                    for key in ('generation_id', 'output_hash', 'billing'):
                        if old[key] is not None and row[key] != old[key]: raise ValueError('observed identity was erased or replaced')
                    if old['observed_cost'] is not None and (row['observed_cost'] is None or row['observed_cost'] < old['observed_cost']): raise ValueError('observed charge was erased or reduced')
                    if old['status'] == 'SETTLED' and row['status'] == 'PHASE_COMMITTED' and row['charged'] != old['charged']: raise ValueError('checkpoint changed financial settlement')
                state[row['id']] = row
            previous = digest
        if not events or anchor['sequence'] != len(events) - 1 or anchor['head'] != previous:
            raise ExecutionBlocked('owner anchor/database torn or truncated; no dispatch')
        persisted = {i: json.loads(text) for i, text in db.execute('SELECT id,data FROM charges')}
        if persisted != state: raise ValueError('owner counters/charges differ from committed history')
        return state, anchor

    def _write(self, db, state, anchor, row):
        self._validate_row(row); before = state.get(row['id'])
        event = {'kind': row['status'], 'previous': anchor['head'],
                 'before': canonical_hash(before) if before else None, 'after': row, 'at_utc': utc_now()}
        digest = canonical_hash(event); sequence = anchor['sequence'] + 1
        db.execute('INSERT INTO events VALUES (?,?,?)', (sequence, json.dumps(event, sort_keys=True), digest))
        db.execute('INSERT OR REPLACE INTO charges VALUES (?,?)', (row['id'], json.dumps(row, sort_keys=True)))
        db.commit()
        # If this separate persistence fails, the old anchor conservatively blocks reopening.
        atomic_json(self.anchor, {**anchor, 'sequence': sequence, 'head': digest})

    def snapshot(self):
        with self._lock(), self._connect() as db:
            state, _ = self._verify(db)
            return deepcopy(list(state.values()))

    def reserve(self, context):
        self._validate_context(context)
        with self._lock(), self._connect() as db:
            state, anchor = self._verify(db)
            if any(r['status'] != 'PHASE_COMMITTED' for r in state.values()):
                raise ExecutionBlocked('owner-wide unfinished or unknown phase blocks inference')
            if any(phase_key(r['context']) == phase_key(context) for r in state.values()): raise ExecutionBlocked('phase already dispatched; no replay')
            amount = context['envelope']['reserved_microusd']; module = context['module']
            if (sum(r['charged'] for r in state.values()) + amount > self.policy['total_microusd']
                or sum(r['charged'] for r in state.values() if r['context']['module'] == module) + amount > self.policy['module_microusd'][module]):
                raise ExecutionBlocked('owner-wide budget exceeded')
            receipt = uuid.uuid4().hex
            row = {'id': receipt, 'context': deepcopy(context), 'reserved': amount, 'charged': amount,
                   'status': 'STARTED', 'generation_id': None, 'output_hash': None,
                   'observed_cost': None, 'checkpoint_hash': None, 'error_type': None, 'billing': None}
            self._write(db, state, anchor, row)
            return receipt

    def transition(self, receipt, status, *, _phase_capability=None, **fields):
        if status == 'PHASE_COMMITTED' and _phase_capability is not _COMMIT_CAPABILITY:
            raise ExecutionBlocked('durable phase checkpoint validation required')
        if set(fields) - {'generation_id', 'output_hash', 'observed_cost', 'checkpoint_hash', 'error_type', 'billing'}:
            raise ValueError('unknown transition field')
        with self._lock(), self._connect() as db:
            state, anchor = self._verify(db); old = state.get(receipt)
            if old is None or status not in TRANSITIONS[old['status']]: raise ExecutionBlocked('phase transition unavailable')
            row = {**deepcopy(old), **fields, 'status': status}
            if row['generation_id'] is not None and any(r['id'] != receipt and r['generation_id'] == row['generation_id'] for r in state.values()):
                raise ValueError('generation identity already consumed by another phase')
            for key in ('generation_id', 'output_hash', 'billing'):
                if old[key] is not None and row[key] != old[key]: raise ValueError('observed identity cannot change')
            if old['observed_cost'] is not None and (row['observed_cost'] is None or row['observed_cost'] < old['observed_cost']): raise ValueError('observed charge cannot decrease')
            if status == 'SETTLED': row['charged'] = integer(row['observed_cost'])
            elif status in ('UNCERTAIN', 'OVERRUN'):
                row['charged'] = max(old['charged'], old['reserved'], row['observed_cost'] or 0)
            self._write(db, state, anchor, row)
            return deepcopy(row)

    def commit_phase(self, receipt, checkpoint):
        path = Path(checkpoint); raw = path.read_bytes()
        if len(raw) > 2_000_000: raise ValueError('phase checkpoint exceeds limit')
        value = json.loads(raw)
        with self._lock(), self._connect() as db:
            state, _ = self._verify(db); row = state.get(receipt)
            if row is None or row['status'] != 'SETTLED': raise ExecutionBlocked('phase billing not settled')
            expected = {'schema_version': 1, **{k: row['context'][k] for k in ('run_id', 'unit_id', 'phase')},
                        'receipt': receipt, 'request_hash': row['context']['envelope']['request_hash'], 'output': value.get('output')}
            if value != expected or canonical_hash(value.get('output')) != row['output_hash'] or sha256_file(path) != canonical_bytes_hash(raw):
                raise ValueError('durable phase checkpoint binding mismatch')
        return self.transition(receipt, 'PHASE_COMMITTED', _phase_capability=_COMMIT_CAPABILITY, checkpoint_hash=canonical_bytes_hash(raw))


def canonical_bytes_hash(raw):
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def create_live_client(*args, **kwargs):
    raise ExecutionBlocked('live release disabled: owner authorization, source/science/release and concrete price plan missing')
