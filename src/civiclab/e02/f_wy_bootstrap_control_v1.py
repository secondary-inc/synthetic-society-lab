"""Authored-only cumulative bootstrap journal; cooperative, preserved-history scope."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

from ..common import atomic_json, canonical_hash, sha256_file
from .national_budget import Blocked
from .full_adult_types_v1_2 import strict_json
from .f_actual_admission_v1_1 import require_fixture

ORDER = ('INSPECT', 'ENROLL', 'PRIMARY', 'REPLAY', 'FINALIZE_PRIMARY', 'FINALIZE_REPLAY')


def stamp():
    if platform.system() == 'Darwin':
        result = subprocess.run(['/usr/sbin/sysctl', '-n', 'kern.boottime'], capture_output=True, text=True, timeout=2)
        if result.returncode or not result.stdout.strip():
            raise Blocked('boot continuity unavailable')
        boot = result.stdout.strip()
    elif platform.system() == 'Linux':
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    else:
        raise Blocked('unsupported clock continuity')
    return {'wall': time.time(), 'mono': time.monotonic(), 'boot': boot}


def elapsed(first, last):
    if set(first) != {'wall', 'mono', 'boot'} or set(last) != set(first) or first['boot'] != last['boot']:
        raise Blocked('clock continuity unknown')
    for item in (first, last):
        for key in ('wall', 'mono'):
            if type(item[key]) not in (int, float) or not math.isfinite(item[key]):
                raise Blocked('nonfinite clock')
    dw, dm = last['wall'] - first['wall'], last['mono'] - first['mono']
    if min(dw, dm) < 0 or abs(dw - dm) > 2:
        raise Blocked('rollback or discontinuous clocks')
    return max(dw, dm)


class Control:
    """Original external journal. Full plan charged forever, never a production grant."""
    def __init__(self, bundle, *, create=False):
        from .f_wy_bootstrap_v1 import require_bundle
        self.b = require_bundle(bundle)
        self.root = bundle.root / 'control'
        self.a = require_fixture(bundle.source)
        self.c = self.a.config
        m = self.a.manifest
        companion = next(x for x in m['members'] if x['name'] == m['companion'])
        person = next(x for x in m['members'] if x['name'] == m['person'])
        expansion = m['header_bytes'] + companion['bytes']
        enrollment = self.c['limits']['line_bytes'] + 3 * self.c['limits']['companion_bytes']
        parse = person['bytes'] + 2 * expansion
        self.descriptors = {'INSPECT': {'bytes': enrollment, 'rows': 0, 'ops': 0, 'seconds': 300},
                            'ENROLL': {'bytes': enrollment, 'rows': 0, 'ops': 0, 'seconds': 300}}
        for key in ('PRIMARY', 'REPLAY'):
            self.descriptors[key] = {'bytes': parse, 'rows': m['expected_rows'], 'ops': 0, 'seconds': 300}
            self.descriptors['FINALIZE_' + key] = {'bytes': 0, 'rows': 0, 'ops': 6000000, 'seconds': 300}
        self.charge = {k: sum(d[k] for d in self.descriptors.values()) for k in ('bytes', 'rows', 'ops', 'seconds')}
        limits = self.c['limits']
        if self.charge['bytes'] > limits['two_sweep_uncompressed_bytes'] or self.charge['rows'] > limits['two_sweep_rows'] or self.charge['ops'] > 64000000 or self.charge['seconds'] > limits['processing_seconds'] or parse > min(limits['state_uncompressed_bytes'], limits['sweep_uncompressed_bytes']) or m['expected_rows'] > min(limits['state_rows'], limits['sweep_rows']) or m['archive_bytes'] > min(limits['archive_body_bytes'], limits['unique_source_bytes'], limits['retained_bytes']):
            raise Blocked('native cumulative/state/sweep limits')
        self.design = {'schema': 'E02_F_WY_BOOTSTRAP_AUTHORED_CONTROL_V1', 'kind': 'MOCK',
                       'bundle': bundle.binding, 'root': str(self.root), 'runtime': str(bundle.root / 'runtime'),
                       'descriptors': self.descriptors, 'charge': self.charge,
                       'source_manifest_hash': canonical_hash(m), 'config_hash': canonical_hash(self.c)}
        if create:
            self.root.mkdir(exist_ok=False)
            with self.lock():
                start = stamp()
                g = {'design': self.design, 't0': start, 'last': start, 'stages': {},
                     'shutdown': 'CLOSED', 'failed': False, 'cleanup': [], 'generation': 0,
                     'reserved': self.charge, 'GETs': 0, 'model_calls': 0}
                # Durable full-plan reservation BEFORE inspecting the source filesystem.
                atomic_json(self.root / 'genesis.json', g)
                atomic_json(self.root / 'state.json', g)
                (self.root / 'ORIGINAL').write_text(canonical_hash(g) + '\n')
                self.storage()
        else:
            # Never mkdir/bootstrap a missing or copied journal.
            if not self.root.is_dir():
                raise Blocked('original control missing; no reset')
        self.snapshot()

    @contextmanager
    def lock(self):
        if not self.root.is_dir() or self.root.is_symlink():
            raise Blocked('original control directory required')
        with (self.root / '.lock').open('a') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Blocked('control already owned') from None
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def storage(self, *, category='core', extra=0, initial=False):
        from .f_wy_bootstrap_v1 import require_bundle
        require_bundle(self.b)
        if self.root != self.b.root / 'control' or self.c != self.b.source.config:
            raise Blocked('storage context differs from minted authored bundle')
        if type(extra) is not int or extra < 0:
            raise Blocked('invalid storage projection')
        q = self.c['storage']
        if category not in q['caps']:
            raise Blocked('unknown storage category')
        usage = {}
        # Count original+copies+temporary logical bytes, without hardlink discounts.
        for root in (self.b.root / 'source', self.root, self.b.root / 'runtime'):
            if root.is_symlink():
                raise Blocked('storage root symlink')
            if not root.exists():
                continue
            for p in root.rglob('*'):
                if p.is_symlink():
                    raise Blocked('private workspace symlink')
                if not p.is_file():
                    continue
                parts = p.relative_to(root).parts
                k = 'raw' if parts[0] == 'inputs' else 'scratch' if parts[0] == 'scratch' else parts[0] + ':base' if parts[0] in ('PRIMARY', 'REPLAY') else 'core'
                usage[k] = usage.get(k, 0) + p.stat().st_size
            free = shutil.disk_usage(root).free
            if free < max(q['free'], q['initial_free'] if initial else 0) + extra:
                raise Blocked('combined free space/headroom')
        usage[category] = usage.get(category, 0) + extra
        for key, cap in q['caps'].items():
            if usage.get(key, 0) > cap:
                raise Blocked('combined partition ' + key)
        data = sum(v for k, v in usage.items() if k.startswith(('PRIMARY:', 'REPLAY:')))
        logs = usage.get('core', 0) + usage.get('receipts', 0)
        if data > q['data_both'] or logs > q['logs'] or data + logs > q['all_artifacts']:
            raise Blocked('combined artifact quota')
        if usage.get('raw', 0) > self.c['limits']['retained_bytes']:
            raise Blocked('retained raw quota')
        return usage

    def _transition(self, old, event, payload):
        s = deepcopy(old)
        if set(payload) - {'at', 'key', 'proof', 'reason', 'review'} or 'at' not in payload:
            raise Blocked('closed control event')
        elapsed(s['last'], payload['at'])
        age = elapsed(s['t0'], payload['at'])
        s['last'] = payload['at']
        s['generation'] += 1
        if event == 'START':
            key = payload.get('key')
            if age >= self.c['limits']['batch_elapsed_seconds'] or s['failed'] or s['shutdown'] != 'CLOSED':
                raise Blocked('expired/failed/unknown control; no work')
            if key not in ORDER or key in s['stages'] or set(s['stages']) != set(ORDER[:ORDER.index(key)]):
                raise Blocked('stage order/duplicate')
            if any(v['status'] != 'COMMITTED' for v in s['stages'].values()):
                raise Blocked('unclosed prior work')
            s['stages'][key] = {'status': 'PENDING', 'started': payload['at'], 'proof': None}
            s['shutdown'] = 'ACTIVE'
        elif event == 'COMMIT':
            key = payload.get('key'); stage = s['stages'].get(key, {})
            if stage.get('status') != 'PENDING' or s['shutdown'] != 'ACTIVE' or s['failed']:
                raise Blocked('no exact pending stage')
            if age >= self.c['limits']['batch_elapsed_seconds'] or elapsed(stage['started'], payload['at']) > 300:
                raise Blocked('whole-stage/global elapsed exceeded')
            proof = payload.get('proof')
            if type(proof) is not dict or set(proof) != {'path', 'sha256'}:
                raise Blocked('closed immutable proof')
            name = Path(proof['path'])
            if str(name) != 'control/' + key + '.proof.local.json':
                raise Blocked('proof outside original control')
            path = self.b.root / name
            if path.is_symlink() or sha256_file(path) != proof['sha256']:
                raise Blocked('control checkpoint changed')
            value = strict_json(path.read_text())
            if value.get('stage') != key or value.get('design') != canonical_hash(self.design) or value.get('closure') != 'VERIFIED_NORMAL_CLOSED':
                raise Blocked('normal closure evidence absent')
            stage.update(status='COMMITTED', proof=proof)
            s['shutdown'] = 'CLOSED'
        elif event == 'UNKNOWN':
            if not any(v['status'] == 'PENDING' for v in s['stages'].values()):
                raise Blocked('no retained pending work')
            for v in s['stages'].values():
                if v['status'] == 'PENDING': v['status'] = 'UNKNOWN'
            s['shutdown'] = 'SHUTDOWN_UNKNOWN'; s['failed'] = True
        elif event == 'CLEANUP':
            review = payload.get('review')
            expected = {'kind': 'TEST_ONLY_INDEPENDENT_CLEANUP', 'state_sha256': canonical_hash(old),
                        'original_root': str(self.root), 'shutdown_observed': True, 'authority_granted': False}
            if review != expected or s['shutdown'] != 'SHUTDOWN_UNKNOWN':
                raise Blocked('cleanup must bind exact original unknown state')
            s['cleanup'].append(review); s['shutdown'] = 'CLEANUP_OBSERVED_STILL_BLOCKED'
            # Failed stage/barriers/full charges/t0 unchanged. No retries or new permissions.
        else:
            raise Blocked('unknown event')
        if s['reserved'] != self.charge:
            raise Blocked('full charges changed')
        return s

    def _read(self):
        from .f_wy_bootstrap_v1 import require_bundle
        require_bundle(self.b)
        if self.root != self.b.root / 'control' or self.c != self.b.source.config or self.design['charge'] != self.charge or self.design['descriptors'] != self.descriptors or self.design['bundle'] != self.b.binding:
            raise Blocked('control context changed')
        derived = {k:sum(d[k] for d in self.descriptors.values()) for k in ('bytes','rows','ops','seconds')}
        if derived != self.charge:
            raise Blocked('descriptor charge mismatch')
        for name in ('genesis.json','ORIGINAL','state.json','events.jsonl'):
            if (self.root / name).is_symlink():
                raise Blocked('original journal symlink refused')
        try:
            g = strict_json((self.root / 'genesis.json').read_text())
            if g['design'] != self.design or (self.root / 'ORIGINAL').read_text() != canonical_hash(g) + '\n':
                raise Blocked('original genesis identity changed')
            expected = {'design': self.design, 't0': g['t0'], 'last': g['t0'], 'stages': {}, 'shutdown': 'CLOSED',
                        'failed': False, 'cleanup': [], 'generation': 0, 'reserved': self.charge, 'GETs': 0, 'model_calls': 0}
            if g != expected: raise Blocked('genesis semantic mismatch')
            state = g; previous = None
            log = self.root / 'events.jsonl'
            for i, line in enumerate(log.read_text().splitlines() if log.exists() else [], 1):
                row = strict_json(line)
                if set(row) != {'seq','prev','before','event','payload','after','hash'} or row['seq'] != i or row['prev'] != previous or row['before'] != canonical_hash(state) or row['hash'] != canonical_hash({k:v for k,v in row.items() if k != 'hash'}):
                    raise Blocked('control chain mismatch')
                state = self._transition(state, row['event'], row['payload'])
                if row['after'] != canonical_hash(state): raise Blocked('control transition mismatch')
                previous = row['hash']
            if strict_json((self.root / 'state.json').read_text()) != state:
                raise Blocked('torn state/history; no reset')
            elapsed(state['last'], stamp())
            return state, previous
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise Blocked('original journal unprovable') from None

    def snapshot(self):
        with self.lock(): return deepcopy(self._read()[0])

    def _advance(self, event, **payload):
        old, previous = self._read(); payload['at'] = stamp()
        new = self._transition(old, event, payload)
        row = {'seq': new['generation'], 'prev': previous, 'before': canonical_hash(old), 'event': event,
               'payload': payload, 'after': canonical_hash(new)}
        row['hash'] = canonical_hash(row)
        blob = (json.dumps(row, sort_keys=True, allow_nan=False) + '\n').encode()
        self.storage(extra=len(blob) + 2*len(json.dumps(new).encode()) + 4096)
        with (self.root / 'events.jsonl').open('ab') as stream:
            stream.write(blob); stream.flush(); os.fsync(stream.fileno())
        atomic_json(self.root / 'state.json', new)
        return deepcopy(new)

    def start(self, key):
        with self.lock():
            self.storage(initial=key == 'INSPECT')
            return self._advance('START', key=key)

    def commit(self, key, value):
        with self.lock():
            self.storage(extra=2*len(json.dumps(value).encode()) + 4096)
            path = self.root / (key + '.proof.local.json')
            if path.exists(): raise Blocked('immutable proof exists')
            value = {**value, 'stage': key, 'design': canonical_hash(self.design)}
            path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
            with path.open('rb') as stream: os.fsync(stream.fileno())
            return self._advance('COMMIT', key=key, proof={'path': str(path.relative_to(self.b.root)), 'sha256': sha256_file(path)})

    def unknown(self):
        with self.lock(): return self._advance('UNKNOWN', reason='unverified shutdown; no termination claim')

    def cleanup_fixture(self, review):
        with self.lock(): return self._advance('CLEANUP', review=review)
