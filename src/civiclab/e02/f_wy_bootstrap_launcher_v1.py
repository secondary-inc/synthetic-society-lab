"""Minimal authored cooperative stage launcher. No live inspection/runtime release."""
from contextlib import contextmanager
import fcntl
import json
import multiprocessing
import os
import signal
import subprocess
import time

from ..common import canonical_hash, sha256_file
from .national_budget import Blocked
from .full_adult_types_v1_2 import strict_json
from .f_actual_admission_v1_1 import create_fixture
from .f_actual_ledger_v1_1 import PilotLedger, Storage
from .f_wy_local_pilot_v1_1 import PartialWYPilot
from .f_wy_bootstrap_v1 import require_bundle, inspect_fixture
from .f_wy_bootstrap_control_v1 import Control, stamp, elapsed, ORDER


def execute_actual(*args, **kwargs):
    raise Blocked('actual bootstrap/runtime release unavailable; authored implementation only')


def _runtime_admission(bundle):
    """DEMO admission generates second authored archive; both copies counted."""
    runtime = bundle.root / 'runtime'
    if runtime.exists() or runtime.is_symlink():
        raise Blocked('new runtime admission required')
    # This is ONLY authored admission, not a fake real-source authority.
    control = Control(bundle)
    control.storage(category='raw', extra=bundle.source.manifest['archive_bytes']+4096, initial=True)
    control.storage(extra=2*(len(bundle.source.config_json)+len(bundle.source.manifest_json))+8192, initial=True)
    a = create_fixture(runtime, strict_json(bundle.rows_json))
    if a.manifest['archive_sha256'] != bundle.source.manifest['archive_sha256']:
        raise Blocked('authored admission content differs')
    store = Storage(a)
    index = {}
    for name in ('genesis.json', 'ORIGINAL', 'state.json', 'events.jsonl', 'INSPECT.proof.local.json'):
        original = control.root / name
        blob = original.read_bytes()
        control.storage(extra=len(blob) + 4096)
        index[name] = store.write(runtime / 'inspection_copy' / name, blob)
    control.storage(extra=2*len(json.dumps(index).encode()) + 4096)
    store.json(runtime / 'inspection_copy' / 'index.local.json', {'kind': 'MOCK_FROZEN_COPY_NOT_ORIGINAL_AUTHORITY', 'files': index})
    control.storage()
    return a


def _validate_copy(bundle):
    control = Control(bundle)
    folder = bundle.root / 'runtime/inspection_copy'
    expected = {'genesis.json','ORIGINAL','state.json','events.jsonl','INSPECT.proof.local.json'}
    index = strict_json((folder / 'index.local.json').read_text())
    if set(index) != {'kind','files'} or index['kind'] != 'MOCK_FROZEN_COPY_NOT_ORIGINAL_AUTHORITY' or set(index['files']) != expected or {p.name for p in folder.iterdir()} != expected | {'index.local.json'}:
        raise Blocked('closed inspection-copy index')
    for name,h in index['files'].items():
        path = folder / name
        if path.is_symlink() or sha256_file(path) != h:
            raise Blocked('inspection copy changed')
    for name in ('genesis.json','ORIGINAL','INSPECT.proof.local.json'):
        if (folder/name).read_bytes() != (control.root/name).read_bytes():
            raise Blocked('frozen copy differs from original')
    prefix = (folder/'events.jsonl').read_bytes()
    if not (control.root/'events.jsonl').read_bytes().startswith(prefix):
        raise Blocked('copied history not original prefix')
    state = strict_json((folder/'genesis.json').read_text())
    for line in prefix.splitlines():
        row = strict_json(line)
        state = control._transition(state,row['event'],row['payload'])
    if state != strict_json((folder/'state.json').read_text()) or state['stages'].get('ENROLL',{}).get('status') != 'PENDING' or state['stages'].get('INSPECT',{}).get('status') != 'COMMITTED':
        raise Blocked('copied admission checkpoint does not precede ENROLL')


def _existing_runtime(bundle):
    # Same minted fixture token retained only inside fixed invocation lineage.
    # Reconstruct from the native source capability's class/token, with all fields
    # rederived from immutable fixture-admission record, never caller flags.
    from .f_actual_admission_v1_1 import FixtureAdmission, require_fixture
    root = bundle.root / 'runtime'
    _validate_copy(bundle)
    record = strict_json((root / 'fixture-admission.local.json').read_text())
    if record.get('kind') != 'MOCK_AUTHORED_CAPABILITY_NOT_ACTUAL_APPROVAL' or record['config_sha256'] != canonical_hash(bundle.source.config):
        raise Blocked('authored runtime admission record changed')
    m = record['manifest']
    expected = bundle.source.manifest
    if {k:v for k,v in m.items()} != expected:
        # create_fixture manifests do not include per-file stat identity; content is exact.
        raise Blocked('runtime authored manifest differs')
    a = FixtureAdmission(root, root / 'inputs/authored-WY.zip', json.dumps(m, sort_keys=True),
                         bundle.source.config_json, bundle.source.token)
    return require_fixture(a)


def _stage(bundle, key):
    control = Control(bundle)
    if key == 'INSPECT':
        return {'inspection': inspect_fixture(bundle, control), 'native': None}
    a = _runtime_admission(bundle) if key == 'ENROLL' else _existing_runtime(bundle)
    pilot = PartialWYPilot(a)
    if key == 'ENROLL': pilot.enroll()
    elif key in ('PRIMARY', 'REPLAY'): pilot.parse(key)
    elif key.startswith('FINALIZE_'): pilot.finalize(key.removeprefix('FINALIZE_'))
    else: raise Blocked('fixed stages only')
    state = pilot.ledger.snapshot()
    if state['stages'].get(key, {}).get('status') != 'COMMITTED':
        raise Blocked('native checkpoint not closed')
    control.storage()
    return {'inspection': None, 'native': state,
            'native_worker_closed': 'native supervise_fixture joined worker before returning',
            'resources': pilot.resources}


def _child(bundle, key, send):
    def cancel(signum, frame): raise Blocked('cooperative parent cancellation')
    signal.signal(signal.SIGTERM, cancel)
    try:
        os.setsid()
        result = _stage(bundle, key)
        send.send({'status': 'OK', 'result': result})
    except BaseException as error:
        # No source values or exception messages.
        try: send.send({'status': 'ERROR', 'error_type': type(error).__name__})
        except BaseException: pass
    finally:
        send.close()


def _processes():
    result = subprocess.run(['ps', '-axo', 'pid=,ppid=,pgid=,rss=,lstart='], capture_output=True, text=True, timeout=2)
    if result.returncode: raise Blocked('process identities/RSS unknown')
    values = {}
    for line in result.stdout.splitlines():
        columns = line.split(None, 4)
        if len(columns) != 5: raise Blocked('process identity format unknown')
        pid, parent, group, rss = map(int, columns[:4])
        values[pid] = {'ppid':parent, 'pgid':group, 'rss':rss*1024, 'start':columns[4]}
    return values


def _sample(pid, known, rss_limit):
    table = _processes()
    family = {pid}
    while True:
        larger = family | {p for p,v in table.items() if v['ppid'] in family}
        if family == larger: break
        family = larger
    peak = 0
    for p in family:
        if p not in table: continue
        v = table[p]
        if p in known and known[p] != v['start']:
            raise Blocked('process identity ambiguous')
        known[p] = v['start']; peak = max(peak, v['rss'])
        if v['rss'] > rss_limit: raise Blocked('sampled RSS stop threshold')
    return peak


class Launcher:
    def __init__(self, bundle):
        self.b = require_bundle(bundle)
        self.control = Control(bundle)

    @contextmanager
    def owner(self):
        with (self.control.root / 'stage.lock').open('a') as stream:
            try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise Blocked('live launcher already owns attempt') from None
            try: yield
            finally: fcntl.flock(stream, fcntl.LOCK_UN)

    def request_cancel_fixture(self):
        require_bundle(self.b)
        path = self.control.root / 'CANCEL.local'
        if not path.exists():
            with path.open('x') as stream:
                stream.write('MOCK_COOPERATIVE_CANCEL\n'); stream.flush(); os.fsync(stream.fileno())

    def run_stage(self, key, *, backend='PINNED_NATIVE_COOPERATIVE'):
        # Only fixed backend/known operations, no caller callback/work/path override.
        if backend != 'PINNED_NATIVE_COOPERATIVE' or key not in ORDER:
            raise Blocked('unsupported operation/topology refused before work')
        with self.owner():
            started = self.control.start(key)
            begin = started['stages'][key]['started']
            receive, send = multiprocessing.get_context('fork').Pipe(False)
            process = multiprocessing.get_context('fork').Process(target=_child, args=(self.b, key, send))
            message = None; known = {}; sampled_peak = 0
            try:
                process.start(); send.close()
                while True:
                    if (self.control.root / 'CANCEL.local').exists():
                        raise Blocked('cooperative cancellation requested')
                    now = stamp()
                    if elapsed(begin, now) > 300 or elapsed(started['t0'], now) >= 10800:
                        raise Blocked('sampled whole-stage/global deadline')
                    self.control.storage()
                    sampled_peak = max(sampled_peak, _sample(process.pid, known, self.control.c['limits']['rss_stop_bytes']))
                    if receive.poll(0.1):
                        message = receive.recv(); process.join(1)
                        if process.is_alive() or process.exitcode != 0 or message.get('status') != 'OK':
                            raise Blocked('stage not normally closed')
                        break
                    if not process.is_alive():
                        process.join(); raise Blocked('stage death with pending reservation')
                table = _processes()
                if any(pid in table for pid in known):
                    raise Blocked('known work still live/ambiguous after normal exit')
                result = message['result']
                if key != 'INSPECT':
                    a = _existing_runtime(self.b)
                    native = PilotLedger(a).snapshot()
                    if native != result['native'] or any(v['status'] != 'COMMITTED' for v in native['stages'].values()):
                        raise Blocked('native/outer closure mismatch')
                    self._native_accounting(native)
                # This is normal fixed-code exit evidence, NOT arbitrary-descendant containment.
                value = {'closure': 'VERIFIED_NORMAL_CLOSED', 'stage_pid': process.pid,
                         'stage_exitcode': process.exitcode, 'normal_join_observed': True,
                         'topology': 'PINNED_NATIVE_COOPERATIVE', 'result': result,
                         'observed_end': stamp(), 'actual_source_rows': 0,
                         'sampled_peak_rss_bytes': sampled_peak, 'observed_process_identities': known,
                         'limits': 'SAMPLED_COOPERATIVE_NOT_ABSOLUTE_OS'}
                self.control.commit(key, value)
                return value
            except BaseException:
                # Live-controller cooperative unwind can run inner native finally.
                if process.pid is not None and process.is_alive():
                    process.terminate(); process.join(2)
                    if process.is_alive():
                        process.kill(); process.join(1)
                    # Even if outer process reaped, inner session closure may be unknown.
                try: self.control.unknown()
                except BaseException: pass  # original pending/torn state retained, never reset.
                raise Blocked('stage failed; full charges retained; shutdown may be unknown') from None
            finally:
                receive.close(); send.close()

    def _native_accounting(self, native):
        # Exact native descriptors plus INSPECT; no double charging or refunds.
        a = _existing_runtime(self.b); ledger = PilotLedger(a)
        expected_rows = expected_bytes = expected_ops = 0
        for key, item in native['stages'].items():
            d = ledger.descriptors[key]
            expected_rows += d['rows']; expected_ops += d['ops']
            expected_bytes += ledger.expanded if key == 'ENROLL' and item['status'] == 'COMMITTED' else d['bytes']
        if (native['rows'], native['expanded_bytes'], native['ops']) != (expected_rows, expected_bytes, expected_ops):
            raise Blocked('native charges do not match fixed work')
        if expected_rows > self.control.charge['rows'] or expected_bytes + self.control.descriptors['INSPECT']['bytes'] > self.control.charge['bytes'] or expected_ops > self.control.charge['ops']:
            raise Blocked('cumulative envelope exceeded')

    def run(self):
        for key in ORDER: self.run_stage(key)
        final = self.control.snapshot()
        if final['failed'] or final['shutdown'] != 'CLOSED' or set(final['stages']) != set(ORDER):
            raise Blocked('bootstrap not normally complete')
        return final
