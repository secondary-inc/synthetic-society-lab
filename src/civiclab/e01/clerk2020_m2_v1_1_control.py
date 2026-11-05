"""Authored MOCK control model, not a filesystem registrar or actual bootstrap TCB.

Simulated persistence is immutable byte storage under a lock. Crash injection models
unknown delivery, not native process death, fsync, disk durability or OS containment.
"""
from threading import RLock
import json

from civiclab.e01.clerk2020_m2_v1_1_contracts import (
    Counters, Refused, canonical, decode, digest, exact, hex64, identifier,
    relative_path, require, sha, uint,
)

POLICY_SHA = '7e87d6844ca5bec346af91359d38a9c7a612503962d13b4749fd93d3811fb0e6'
LEDGER_FILES = (
    'manifest.json', 'environment.json', 'events.jsonl', 'summary.json',
    'inspection_projection.local.json', 'inspection_diagnostics.json',
    'inspection_provenance.local.json', 'inspection_payload_hashes.json',
    'inspection_commit.json', 'counters.prefix.local.json',
)
DATA_FILES = frozenset(LEDGER_FILES[4:7])
TERMINAL_SLOTS = {'prefix_anchor': 2048, 'seal': 4096, 'tail_VERIFY': 1024,
                  'writer_ACK': 1024, 'tail_ACK': 1024, 'completed_anchor': 2048,
                  'tail_INVALIDATE': 1024, 'invalidated_anchor': 2048,
                  'terminal_failure_sidecars': 4096}


def policy_from_bytes(raw):
    require(sha(raw) == POLICY_SHA)
    # This exact hash-pinned methods document is pretty printed and contains
    # policy floats (poll intervals). It is not a canonical protocol record.
    return json.loads(raw)


class ClosedRecords:
    """Closed fields and concrete predicates; opaque predicates need exact bindings.

    This alone is not authority validation. Runtime/code/fixed-slice predicates must
    be independently supplied exact canonical values; absence refuses rather than
    accepting an arbitrary dict. Fixed path/context/hash relations remain explicit
    admission checks, not inferred from field shape.
    """
    def __init__(self, policy_bytes):
        self._policy = policy_from_bytes(policy_bytes)

    def validate(self, shape, value, bindings=None, *, event=False):
        policy = self._policy['journal_event_payload_schemas' if event else 'closed_schemas']
        require(shape in policy)
        schema = policy[shape]
        value = decode(canonical(value))
        exact(value, schema['required'])
        bindings = {} if bindings is None else decode(canonical(bindings))
        for key, predicate in schema['field_types'].items():
            v = value[key]
            if predicate == 'Ref' or (predicate == 'Ref_or_null' and v is not None):
                self.validate('Ref', v)
            elif predicate == 'CounterState':
                self.validate('CounterState', v, bindings.get(key))
            elif predicate == 'exact_15_named_CounterAxis':
                from civiclab.e01.clerk2020_m2_v1_1_contracts import CEILINGS
                exact(v, CEILINGS)
                for axis_name, axis in v.items():
                    self.validate('CounterAxis', axis)
                    require(axis['ceiling'] == CEILINGS[axis_name])
            elif predicate.endswith('_or_null') and v is None:
                continue
            elif predicate in {'hex64', 'hex64_or_null'}:
                require(hex64(v))
            elif predicate in {'uint', 'uint_or_null', 'positive_uint', 'uint1to3'}:
                require(uint(v) and (predicate != 'positive_uint' or v > 0)
                        and (predicate != 'uint1to3' or 1 <= v <= 3))
            elif predicate in {'id', 'externally_preassigned_id', 'exactregisteredid'}:
                require(identifier(v))
                if predicate == 'exactregisteredid':
                    require(key in bindings and v == bindings[key])
            elif predicate in {'bool', 'bool_or_null'}:
                require(type(v) is bool)
            elif predicate == 'normalized_relative_path':
                require(relative_path(v))
            elif predicate == 'constnull':
                require(v is None)
            elif predicate in {'consttrue', 'constfalse'}:
                require(type(v) is bool and v == (predicate == 'consttrue'))
            elif predicate.startswith('const') and predicate[5:].isdigit():
                require(type(v) is int and v == int(predicate[5:]))
            elif predicate.startswith('M2_') or predicate in {
                    'COMMIT_PREFIX_FINAL', 'PRIOR_COMPLETE_EFFECTS_ONLY'}:
                require(type(v) is str and v == predicate)
            elif predicate == 'fixed_study_name':
                require(v == 'E01_CLERK2020_M2_FORMAT_INSPECTION')
            elif predicate == '81_or38':
                require(type(v) is int and v in {81, 38})
            elif predicate in {'BOOT_or_EXEC', 'BOOT_or_EXEC_ADMISSION',
                    'CREATE_ONCE_or_VERIFY_EXISTING', 'COMPLETE_orFAILED_orUNCERTAIN',
                    'VERIFIED_orFAILED_orUNCERTAIN', 'VERIFIED_or_FAILED_orUNCERTAIN',
                    'VERIFY_OK_orVERIFY_FAILED_orACK_COMMITTED_orINVALIDATE'}:
                options = predicate.replace('_or', '|').split('|')
                require(type(v) is str and v in {x.strip('_') for x in options})
            else:
                # A caller cannot silently broaden a symbolic type. Its exact
                # independently reviewed binding is mandatory and detached.
                require(key in bindings and canonical(v) == canonical(bindings[key]))
        if shape == 'CounterAxis' and not event:
            require(value['held'] + value['reserved'] + value['charged'] <= value['ceiling'])
            require(value['observed_known_sum'] + value['uncertain_charged'] <= value['charged'])
            require(value['observed'] == (None if value['uncertain_charged']
                                         else value['observed_known_sum']))
        if shape == 'Ref' and not event:
            require(value['bytes'] <= 536870912)
        return value


class MockCrash(RuntimeError):
    def __init__(self):
        super().__init__('MOCK_CRASH_UNKNOWN')


class CrashPoint:
    def __init__(self, target=None):
        self.target = target
        self.seen = []

    def __call__(self, name):
        self.seen.append(name)
        if name == self.target:
            raise MockCrash()


class MockRegistrar:
    """One in-memory trusted registrar per fixture; no real/grant persistence."""
    def __init__(self):
        self._lock = RLock()
        self._source_index = {}
        self._source_hash_index = {}
        self._anchor_ids = set()
        self._registrations = {}
        self._issued = {}
        self._consumed = set()
        self._anchors = {}

    def register(self, campaign, source_set, anchor, source_hash):
        require(all(identifier(v) for v in [campaign, source_set, anchor]) and hex64(source_hash))
        with self._lock:
            require(source_set not in self._source_index and campaign not in self._registrations
                    and source_hash not in self._source_hash_index and anchor not in self._anchor_ids)
            # Fixed paths are derived only from preassigned identities.
            record = {'label': 'MOCK', 'campaign_id': campaign, 'source_set_id': source_set,
                      'anchor_id': anchor, 'source_set_sha256': source_hash,
                      'control_namespace': 'data/processed/e01_clerk2020_m2_control/' + campaign,
                      'registry_namespace': 'data/processed/e01_clerk2020_m2_registry/' + campaign}
            raw = canonical(record)
            self._source_index[source_set] = campaign
            self._source_hash_index[source_hash] = campaign
            self._anchor_ids.add(anchor)
            self._registrations[campaign] = raw
            self._anchors[campaign] = None
            return raw

    def issue(self, campaign, phase, attempt_id, decision_hash, expected_anchor):
        require(phase in {'BOOT', 'EXEC'} and identifier(attempt_id) and hex64(decision_hash))
        with self._lock:
            require(campaign in self._registrations and self._anchors[campaign] == expected_anchor)
            key = (campaign, phase)
            require(key not in self._issued)
            if phase == 'EXEC':
                require((campaign, 'BOOT') in self._consumed and expected_anchor is not None)
            raw = canonical({'label': 'MOCK', 'campaign_id': campaign, 'phase': phase,
                             'attempt_id': attempt_id, 'decision_hash': decision_hash,
                             'registration_sha256': sha(self._registrations[campaign]),
                             'expected_anchor': expected_anchor})
            self._issued[key] = raw  # Issuance itself spends the one-shot ordinal.
            return raw

    def consume(self, issued_bytes, external_hash, crash):
        require(type(issued_bytes) is bytes and hex64(external_hash) and sha(issued_bytes) == external_hash)
        packet = decode(issued_bytes)
        exact(packet, {'label', 'campaign_id', 'phase', 'attempt_id', 'decision_hash',
                       'registration_sha256', 'expected_anchor'})
        key = (packet['campaign_id'], packet['phase'])
        with self._lock:
            require(key in self._issued and self._issued[key] == issued_bytes and key not in self._consumed)
            self._consumed.add(key)  # Consumed before simulated reservation persistence.
            crash('reservation.before')
            require(self._anchors[key[0]] == packet['expected_anchor'])
            crash('reservation.after')
            return packet

    def cas(self, campaign, expected, new_anchor):
        require(hex64(new_anchor))
        with self._lock:
            require(campaign in self._anchors and self._anchors[campaign] == expected)
            self._anchors[campaign] = new_anchor

    def current(self, campaign):
        with self._lock:
            require(campaign in self._anchors)
            return self._anchors[campaign]


class MockTCB:
    """Authored snapshot reader; no paths, callbacks, imports, FDs or OS probes."""
    def __init__(self, artifacts):
        require(type(artifacts) is dict and all(identifier(k) and type(v) is bytes
                and len(v) <= 1048576 for k, v in artifacts.items()))
        self._artifacts = dict(artifacts)
        self.reads = []

    def read_reserved(self, artifact, axis, amount, counters, crash):
        require(artifact in self._artifacts and axis in {
            'metadata_read_bytes', 'code_integrity_read_bytes'})
        require(uint(amount) and amount >= len(self._artifacts[artifact]) + 1)
        counters.transition('reserve', {axis: amount})
        try:
            crash('read.reserve')
            raw = self._artifacts[artifact]
            self.reads.append(artifact)
            crash('read.effect')
            counters.settle(axis, amount, len(raw))
            return raw
        except BaseException:
            counters.stop_unknown()
            raise


class MockBootstrap:
    """One-shot finite authored admission; no actual source execution method."""
    def __init__(self, registrar, tcb):
        require(type(registrar) is MockRegistrar and type(tcb) is MockTCB)
        self.registrar, self.tcb = registrar, tcb
        self.counters = Counters()
        self.stopped = False
        self.completed = False

    def run(self, issued, expected_hash, manifest, crash=None):
        require(not self.stopped and not self.completed)
        crash = CrashPoint() if crash is None else crash
        try:
            require(type(issued) is bytes and type(manifest) is bytes
                    and len(issued) + len(manifest) <= 262144)
            records = decode(manifest)
            require(type(records) is list and 1 <= len(records) <= 64)
            # Manifest parsing is memory-only before one-shot reservation.
            for record in records:
                exact(record, {'artifact', 'axis', 'bytes', 'sha256'})
                require(identifier(record['artifact']) and record['axis'] in {
                    'metadata_read_bytes', 'code_integrity_read_bytes'}
                    and uint(record['bytes'], 1048576) and hex64(record['sha256']))
            require(len({r['artifact'] for r in records}) == len(records))
            require(decode(issued)['phase'] == 'BOOT')
            packet = self.registrar.consume(issued, expected_hash, crash)
            self.counters.transition('allocate', {
                'bootstrap_attempts': 1, 'metadata_read_bytes': 262144 + 6291456,
                'code_integrity_read_bytes': 535822336,
                'active_time_ms': 45000, 'cpu_ms': 10000})
            self.counters.transition('precharge', {
                'bootstrap_attempts': 1, 'metadata_read_bytes': 262144})
            for record in records:
                raw = self.tcb.read_reserved(record['artifact'], record['axis'],
                    record['bytes'] + 1, self.counters, crash)
                require(len(raw) == record['bytes'] and sha(raw) == record['sha256'])
            # Resource observations are unknown in this pure fixture, never zero.
            self.counters.stop_unknown()
            receipt = {'label': 'MOCK', 'kind': 'AUTHORED_BOOTSTRAP_RECEIPT',
                       'issued_sha256': sha(issued), 'manifest_sha256': sha(manifest),
                       'counters': self.counters.snapshot(), 'actual_runtime': None,
                       'source_reads': 0}
            self.registrar.cas(packet['campaign_id'], packet['expected_anchor'], digest(receipt))
            crash('bootstrap.anchor')
            self.completed = True
            return receipt
        except BaseException:
            self.stopped = True
            self.counters.stop_unknown()
            raise


class MockStore:
    """Append/create-once byte slots; snapshots cannot alias the stored content."""
    def __init__(self, crash=None):
        self._files = {}
        self._used = set()
        self._written = {'all': 0, 'data': 0, 'control': 0}
        self._partitions = {'precommit': 0, 'terminal': 0, 'journal': 0}
        self.crash = CrashPoint() if crash is None else crash

    def create(self, slot, raw, maximum, category='control'):
        require(identifier(slot.replace('.', '_')) and type(raw) is bytes
                and uint(maximum) and len(raw) <= maximum and category in {'data', 'control'})
        require(slot not in self._used)
        limits = {'all': 524288, 'data': 262144, 'control': 131072}
        require(self._written['all'] + maximum <= limits['all']
                and self._written[category] + maximum <= limits[category])
        if category == 'control':
            partition = 'terminal' if slot in TERMINAL_SLOTS else 'journal' if slot.startswith('journal_') else 'precommit'
            partition_limit = 49152 if partition == 'journal' else 24576
            require(self._partitions[partition] + maximum <= partition_limit)
            if partition == 'terminal':
                require(maximum == TERMINAL_SLOTS[slot])
            self._partitions[partition] += maximum
        self._used.add(slot)
        # Whole slot permission is consumed even on a pre/post-write failure.
        self._written['all'] += maximum
        self._written[category] += maximum
        self.crash(slot + '.before')
        self._files[slot] = raw
        self.crash(slot + '.after')

    def get(self, slot):
        require(slot in self._files)
        return self._files[slot]

    def snapshot(self):
        return dict(self._files)


class MockTerminal:
    """Finite exact-prefix finalizer for authored payloads, never actual runs.

    Inputs are already-closed MOCK run bytes. This component is not a BOOT/EXEC
    launcher; it cannot read source paths or write external controls.
    """
    def __init__(self, store, registrar, campaign, context_hash, initial_head, counters=None):
        require(type(store) is MockStore and type(registrar) is MockRegistrar
                and identifier(campaign) and hex64(context_hash) and hex64(initial_head))
        self.store, self.registrar, self.campaign = store, registrar, campaign
        self.context_hash, self.initial_head = context_hash, initial_head
        require(counters is None or type(counters) is Counters)
        self.counters = Counters() if counters is None else counters
        self._prefix = b''
        self._head = initial_head
        self._sequence = 0
        self._tail = []
        self._finalized = False
        self._stopped = False
        self.caller_returned = False
        self.status = 'MOCK_NOT_RUN'

    def append(self, event_type, payload):
        require(not self._finalized and not self._stopped and self._sequence < 48)
        require(event_type in {'RESERVE_FINALIZATION', 'COMMIT_PREFIX'})
        expected = ({'finalization_reservation_sha256', 'counter_before_reserve_sha256'}
                    if event_type == 'RESERVE_FINALIZATION' else
                    {'context_sha256', 'prefix_ledger_sha256', 'counter_snapshot_sha256',
                     'finalization_reservation_sha256', 'normal_journal_frozen'})
        exact(payload, expected)
        require(all(hex64(v) if k != 'normal_journal_frozen' else v is True
                    for k, v in payload.items()))
        event = {'schema_version': 1, 'kind': 'M2_PREFIX_EVENT_V1_1',
                 'campaign_id': self.campaign, 'phase': 'EXEC', 'effect_id': 'finalize',
                 'sequence': self._sequence + 1, 'previous_event_sha256': self._head,
                 'event_type': event_type, 'payload': payload}
        raw = canonical(event)
        require(len(raw) + 1 <= 1024 and len(self._prefix) + len(raw) + 1 <= 49152)
        self.store.create('journal_' + str(self._sequence + 1), raw + b'\n', 1024)
        self._prefix += raw + b'\n'
        self._sequence += 1
        self._head = sha(raw)
        if event_type == 'COMMIT_PREFIX':
            self._finalized = True

    def _slot(self, name, obj):
        self.store.create(name, canonical(obj), TERMINAL_SLOTS[name])

    def _tail_event(self, kind, seal_hash, reservation_hash, ack_hash=None):
        allowed = ('VERIFY_OK', 'ACK_COMMITTED', 'INVALIDATE')
        require(len(self._tail) < 3 and kind == allowed[len(self._tail)])
        event = {'schema_version': 1, 'kind': 'M2_TERMINAL_TAIL_EVENT_V1_1',
                 'context_sha256': self.context_hash, 'error_type': None if kind != 'INVALIDATE' else 'IO_UNKNOWN',
                 'event_type': kind, 'index': len(self._tail) + 1,
                 'observed_before_this_event': {'record_verification_read_bytes': self._verified_bytes},
                 'previous_sha256': seal_hash if not self._tail else digest(self._tail[-1]),
                 'seal_sha256': seal_hash, 'sealed_prefix_head_sha256': self._head,
                 'terminal_reservation_sha256': reservation_hash, 'writer_ack_sha256': ack_hash}
        slot = {'VERIFY_OK': 'tail_VERIFY', 'ACK_COMMITTED': 'tail_ACK', 'INVALIDATE': 'tail_INVALIDATE'}[kind]
        self._slot(slot, event)
        self._tail.append(decode(canonical(event)))
        return digest(event)

    def finalize(self, payloads, bindings):
        require(not self._finalized and not self._stopped)
        try:
            return self._finalize(payloads, bindings)
        except BaseException:
            self._stopped = True
            self.counters.stop_unknown()
            self.status = 'MOCK_SEALED_OR_ACK_UNKNOWN' if self._finalized else 'MOCK_FAILED_UNKNOWN'
            raise

    def _finalize(self, payloads, bindings):
        exact(payloads, set(LEDGER_FILES) - {'counters.prefix.local.json'})
        require(all(type(raw) is bytes for raw in payloads.values()))
        exact(bindings, {'registration_sha256', 'static_spec_sha256', 'genesis_sha256',
                         'execution_decision_sha256', 'issued_envelope_sha256',
                         'source_set_sha256', 'external_reservation_sha256'})
        require(all(hex64(v) for v in bindings.values()))
        # Reject real/unlabelled content at this authored-only boundary. Payload
        # bodies are MOCK data supplied in memory, never files from an old run.
        for name, raw in payloads.items():
            require(decode(raw).get('label') == 'MOCK')
        before_reserve = digest(self.counters.snapshot())
        self.counters.transition('allocate', {
            'record_verification_read_bytes': 2097152, 'owned_write_bytes': 524288,
            'inspection_data_write_bytes': 262144, 'recorder_control_write_bytes': 131072})
        self.counters.transition('precharge', {
            'record_verification_read_bytes': 2097152, 'owned_write_bytes': 524288,
            'inspection_data_write_bytes': 262144, 'recorder_control_write_bytes': 131072})
        reservation = {'schema_version': 1, 'kind': 'M2_FINALIZATION_RESERVATION_V1_1',
                       'context_sha256': self.context_hash, 'no_source_backend_or_reseal': True,
                       'normal_journal_freeze_rule': 'COMMIT_PREFIX_FINAL',
                       'record_verification_read_bytes': 2097152, 'tail_events_max': 3,
                       'terminal_write_slots_bytes': 24576}
        r_hash = digest(reservation)
        self.append('RESERVE_FINALIZATION', {'finalization_reservation_sha256': r_hash,
                    'counter_before_reserve_sha256': before_reserve})
        self.store.crash('finalization.reserved')
        x = {'schema_version': 1, 'kind': 'M2_COUNTER_STATE_V1_1',
             'campaign_id': self.campaign, 'source_set_sha256': bindings['source_set_sha256'],
             'registration_sha256': bindings['registration_sha256'],
             'static_spec_sha256': bindings['static_spec_sha256'],
             'external_reservation_sha256': bindings['external_reservation_sha256'],
             'journal_head_before_snapshot_sha256': self._head,
             'observed_through_sequence': self._sequence, 'axes': self.counters.snapshot()}
        owned = dict(payloads, **{'counters.prefix.local.json': canonical(x)})
        for name, raw in owned.items():
            maximum = (251904 if name == 'inspection_projection.local.json' else
                       8192 if name == 'inspection_diagnostics.json' else
                       2048 if name == 'inspection_provenance.local.json' else len(raw))
            self.store.create(name, raw, maximum, 'data' if name in DATA_FILES else 'control')
        self.store.crash('payloads.closed')
        ledger = {name: sha(owned[name]) for name in LEDGER_FILES}
        ledger_raw = canonical(ledger)
        self.store.create('checksums.json', ledger_raw, len(ledger_raw))
        self.append('COMMIT_PREFIX', {'context_sha256': self.context_hash,
                    'prefix_ledger_sha256': sha(ledger_raw), 'counter_snapshot_sha256': digest(x),
                    'finalization_reservation_sha256': r_hash, 'normal_journal_frozen': True})
        self.store.crash('prefix.committed')
        expected_anchor = self.registrar.current(self.campaign)
        self._slot('prefix_anchor', {'label': 'MOCK', 'prefix_head': self._head})
        seal = {**{k: v for k, v in bindings.items() if k not in {
                    'source_set_sha256', 'external_reservation_sha256'}},
                'schema_version': 1, 'kind': 'M2_FINAL_SEAL_V1_1',
                'context_sha256': self.context_hash,
                'counter_snapshot_ref': {'path': 'counters.prefix.local.json', 'sha256': digest(x), 'bytes': len(canonical(x))},
                'finalization_reservation_sha256': r_hash,
                'prefix_ledger_ref': {'path': 'checksums.json', 'sha256': sha(ledger_raw), 'bytes': len(ledger_raw)},
                'sealed_prefix_bytes': len(self._prefix), 'sealed_prefix_file_sha256': sha(self._prefix),
                'sealed_prefix_head_sha256': self._head, 'sealed_prefix_last_sequence': self._sequence,
                'terminal_protocol': 'M2_TERMINAL_TAIL_V1_1'}
        self._slot('seal', seal)
        self.store.crash('verification.before')
        self._verified_bytes = len(ledger_raw) + sum(len(v) for v in owned.values()) + len(self._prefix) + len(canonical(seal))
        require(self._verified_bytes <= 2097152)
        require(all(sha(self.store.get(name)) == ledger[name] for name in LEDGER_FILES))
        require(self.store.get('checksums.json') == ledger_raw)
        require(b''.join(self.store.get('journal_' + str(i))
                for i in range(1, self._sequence + 1)) == self._prefix)
        require(self.store.get('seal') == canonical(seal))
        self.store.crash('verification.after')
        s_hash = digest(seal)
        t1_hash = self._tail_event('VERIFY_OK', s_hash, r_hash)
        ack = {'schema_version': 1, 'kind': 'M2_WRITER_ACK_V1_1',
               'context_sha256': self.context_hash, 'counter_snapshot_sha256': digest(x),
               'seal_sha256': s_hash, 'sealed_prefix_head_sha256': self._head,
               'terminal_reservation_sha256': r_hash, 'verified_tail_event_sha256': t1_hash}
        self._slot('writer_ACK', ack)
        t2_hash = self._tail_event('ACK_COMMITTED', s_hash, r_hash, digest(ack))
        anchor = {'label': 'MOCK', 'seal_sha256': s_hash, 'prefix_head': self._head,
                  'tail_head': t2_hash, 'writer_ack_sha256': digest(ack)}
        self._slot('completed_anchor', anchor)
        self.registrar.cas(self.campaign, expected_anchor, digest(anchor))
        self.store.crash('anchor.committed')
        self.store.crash('caller.before')
        self.caller_returned = True
        self.status = 'MOCK_WRITER_COMMITTED_CALLER_OBSERVED'
        return {'label': 'MOCK', 'seal_sha256': s_hash, 'writer_ack_sha256': digest(ack),
                'actual_source_access': False, 'cost_usd': 0}

    def prefix(self):
        return self._prefix

    def tail(self):
        return decode(canonical(self._tail))
