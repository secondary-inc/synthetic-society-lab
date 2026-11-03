"""Conditionally usable actual-shaped stage runner; genuine production authorities required."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import time
from ..common import canonical_hash, sha256_file, atomic_json
from .national_budget import Blocked
from .full_adult_types_v1_2 import strict_json
from .f_actual_ledger_v1_1 import PilotLedger, Storage
from .f_wy_local_pilot_v1_1 import PartialWYPilot
from .f_wy_actual_bootstrap_v1 import require_context, _inspect_reserved, native_session, owned_json, observation, validate_execution
from .f_wy_actual_bootstrap_control_v1 import Control, stamp, elapsed, ORDER


def _runtime_config(c):
    config=owned_json(c,c.control_root/'runtime-config.local.json')
    config,binding=validate_execution(c,config)
    if Control(c).snapshot().get('release')!=binding: raise Blocked('original release binding differs')
    return config


def _runtime_admission(c):
    config=_runtime_config(c);ctl=Control(c)
    if c.runtime_root.exists() or c.runtime_root.is_symlink(): raise Blocked('new exact native output required')
    cursor=c.realm.root
    for part in c.runtime_root.relative_to(c.realm.root).parts[:-1]:
        cursor=cursor/part
        if cursor.is_symlink(): raise Blocked('native output ancestor symlink')
    # Project native admission+evidence before factory creates the output.
    ctl.storage(extra=2*(len(json.dumps(config).encode())+len(c.binding_json.encode()))+8192,initial=True)
    from .f_actual_admission_v1_1 import admit_actual
    a=admit_actual(config)
    store=Storage(a);o=observation(c);index={}
    names=tuple(o['files'])+('observation.local.json',)
    for name in names:
        blob=(c.control_root/name).read_bytes()
        if name=='events.jsonl':blob=blob[:o['event_prefix_bytes']]
        ctl.storage(extra=len(blob)+4096)
        index[name]=store.write(a.root/'bootstrap_inspection'/name,blob)
    ctl.storage(extra=2*len(json.dumps(index).encode())+4096)
    store.json(a.root/'bootstrap_inspection/index.local.json',{'realm':c.realm.tag,'files':index})
    ctl.storage()
    return a


def _validate_copy(c):
    folder=c.runtime_root/'bootstrap_inspection';o=observation(c)
    index=strict_json((folder/'index.local.json').read_text())
    expected=set(o['files'])|{'observation.local.json'}
    if index.get('realm')!=c.realm.tag or set(index.get('files',{}))!=expected or {p.name for p in folder.iterdir()}!=expected|{'index.local.json'}:
        raise Blocked('closed inspection copy index')
    for name,h in index['files'].items():
        p=folder/name
        if p.is_symlink() or sha256_file(p)!=h: raise Blocked('copied inspection changed')
        original=(c.control_root/name).read_bytes()
        if name=='events.jsonl':original=original[:o['event_prefix_bytes']]
        if p.read_bytes()!=original:raise Blocked('copied evidence differs from original')


def _existing_runtime(c):
    from .f_actual_admission_v1_1 import reopen_actual_for_review
    _validate_copy(c)
    return reopen_actual_for_review(_runtime_config(c))


def _verify_observed_path(c):
    from .f_wy_bootstrap_v1_1 import _open_no_follow, _identity
    o=observation(c)
    original=owned_json(c,c.control_root/'INSPECT.proof.local.json')['result']['inspection']
    stream,directory,chain=_open_no_follow(c.path)
    try:
        with stream:
            if chain != original['directory_chain_identity'] or _identity(os.fstat(stream.fileno())) != o['source_identity']:
                raise Blocked('source no longer has observed lexical lineage')
    finally:os.close(directory)


def _stage(c,key):
    ctl=Control(c)
    if key=='INSPECT':return {'inspection':_inspect_reserved(c,ctl),'native':None}
    with native_session(c):
        a=_runtime_admission(c) if key=='ENROLL' else _existing_runtime(c)
        pilot=PartialWYPilot(a)
        if key=='ENROLL':pilot.enroll()
        elif key in ('PRIMARY','REPLAY'):pilot.parse(key)
        elif key.startswith('FINALIZE_'):pilot.finalize(key.removeprefix('FINALIZE_'))
        else:raise Blocked('fixed native stage only')
        _verify_observed_path(c)
        state=pilot.ledger.snapshot()
        if state['stages'].get(key,{}).get('status')!='COMMITTED':raise Blocked('native checkpoint unclosed')
        ctl.storage()
        return {'inspection':None,'native':state,'resources':pilot.resources,
                'native_worker_closed':'native supervisor joined fixed worker before return'}

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
        self.b = require_context(bundle)
        self.control = Control(bundle)

    @contextmanager
    def owner(self):
        with (self.control.root / 'stage.lock').open('a') as stream:
            try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise Blocked('live launcher already owns attempt') from None
            try: yield
            finally: fcntl.flock(stream, fcntl.LOCK_UN)

    def request_cancel(self):
        require_context(self.b)
        path = self.control.root / 'CANCEL.local'
        if not path.exists():
            with path.open('x') as stream:
                stream.write('COOPERATIVE_CANCEL\n'); stream.flush(); os.fsync(stream.fileno())

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
                    with native_session(self.b):
                        a = _existing_runtime(self.b)
                        native = PilotLedger(a).snapshot()
                    if native != result['native'] or any(v['status'] != 'COMMITTED' for v in native['stages'].values()):
                        raise Blocked('native/outer closure mismatch')
                    self._native_accounting(native)
                # This is normal fixed-code exit evidence, NOT arbitrary-descendant containment.
                value = {'closure': 'VERIFIED_NORMAL_CLOSED', 'stage_pid': process.pid,
                         'stage_exitcode': process.exitcode, 'normal_join_observed': True,
                         'topology': 'PINNED_NATIVE_COOPERATIVE', 'result': result,
                         'observed_end': stamp(), 'realm':self.b.realm.tag, 'real_source_rows':0 if self.b.realm.tag=='TEST_ONLY' else (self.b.manifest['expected_rows'] if key in ('PRIMARY','REPLAY') else 0),
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
        with native_session(self.b):
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
        if self.control.snapshot().get('release') is None:raise Blocked('independent execution release absent')
        for key in ORDER[1:]: self.run_stage(key)
        final = self.control.snapshot()
        if final['failed'] or final['shutdown'] != 'CLOSED' or set(final['stages']) != set(ORDER):
            raise Blocked('bootstrap not normally complete')
        return final


def run_inspection(context):
    c=require_context(context)
    ctl=Control(c,create=True)
    Launcher(c).run_stage('INSPECT')
    state=ctl.snapshot();proof=owned_json(c,c.control_root/'INSPECT.proof.local.json')
    if set(state['stages'])!={'INSPECT'} or state['failed'] or state['shutdown']!='CLOSED':
        raise Blocked('inspection not closed')
    snap=c.control_root/'post-inspection-state.local.json'
    ctl.storage(extra=2*len(json.dumps(state).encode())+8192)
    atomic_json(snap,state)
    names=('genesis.json','ORIGINAL','inspection-admission.local.json','INSPECT.proof.local.json','post-inspection-state.local.json','events.jsonl')
    hashes={name:sha256_file(c.control_root/name) for name in names}
    o={'realm':c.realm.tag,'adapter_design_sha256':c.binding['M'],
       'inspection_sha256':c.binding['refs']['inspection']['sha256'],
       'control_root':str(c.control_root),'source_identity':proof['result']['inspection']['identity'],
       'post_inspection_state_sha256':canonical_hash(state),'t0':state['t0'],
       'files':hashes,'event_prefix_bytes':(c.control_root/'events.jsonl').stat().st_size}
    ctl.storage(extra=2*len(json.dumps(o).encode())+4096)
    path=c.control_root/'observation.local.json'
    if path.exists():raise Blocked('immutable observation exists')
    atomic_json(path,o)
    return observation(c)
