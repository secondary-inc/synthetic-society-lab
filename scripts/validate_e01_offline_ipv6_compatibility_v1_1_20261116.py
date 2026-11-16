"""One-child offline capability compatibility candidate. Actual invocation is root-reviewed only.

This runner cannot install or accept a runtime. It preserves every failed target,
uses the original PATH, and executes exactly one explicit pip --dry-run child.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import runpy
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).absolute().parents[1]
CODE_PATH = 'scripts/validate_e01_offline_ipv6_compatibility_v1_1_20261116.py'
METHODS = 'configs/e01_offline_ipv6_compatibility_v1_1_20261116.json'
OUTPUT = 'data/processed/e01_pypdf701_build_v1/compatibility-v1_1-20261116'
TARGET = '.venv-e01-pypdf-7.0.1-COMPATIBILITY-NOT-INSTALL-v1_1'
SITE = TARGET+'/lib/python3.12/site-packages'
PRESERVED_ROOTS = (
    'data/processed/e01_pypdf701_build_v1/install-v1_3-20261116', '.venv-e01-pypdf-7.0.1-v1',
    'data/processed/e01_pypdf701_build_v1/install-v1_4-20261116', '.venv-e01-pypdf-7.0.1-v2',
    'data/processed/e01_pypdf701_build_v1/install-v1_5-20261116', '.venv-e01-pypdf-7.0.1-v3',
    'data/processed/e01_pypdf701_build_v1/diagnostic-v1-20261116',
    'data/processed/e01_pypdf701_build_v1/diagnostic-v2-20261116')
FROZEN_REF = {'path': 'scripts/install_e01_pypdf701_runtime_v1_5.py', 'bytes': 64638,
              'sha256': '32162b1ddc0b31637842c3a5ecc0caa36dde6d6f32f2111a94c2336f59c178b4'}
CANDIDATE_REF = {'path': 'scripts/e01_p2_refusal_observability_candidate_v3_20261116.py', 'bytes': 8165,
                 'sha256': 'e7670b2d56866f0050c892d4406260c860df0158af2848a2f1061179f96e36d9'}
PROPOSAL_REF = {'path': 'configs/e01_pypdf701_guard_diagnostic_v1_proposal_20261116.json', 'bytes': 9126,
                'sha256': 'ed357cbe714ff3d137ac95aa1b9500f45f93b1b9a8fa2286ef6e911507078c81'}
COMPONENT_REVIEW_REF = {'path': 'reports/INDEPENDENT_AUDIT_E01_SOCKET_OBSERVER_V3_COMPONENT_METHODS_20261116.json',
                        'bytes': 12652, 'sha256': '41dd19725ad0e8ba2148d1f2edb2541b4e07a5f1aabf3ad7c5516e4461300f4d'}
PRIOR_DIAGNOSTIC_REF = {'path': 'scripts/diagnose_e01_pypdf701_guard_v1.py', 'bytes': 37439,
                        'sha256': 'c71209bcb3a8d0ec485c28dd5f3249d6b34faafd30677dcc908cbf1a656f3f31'}
RATIONALE_REF = {'path': 'reports/E01_DIAGNOSTIC_SUCCESSOR_RATIONALE_20261116.json', 'bytes': 2747,
                 'sha256': '8b2abcd2b72750fb8fbf58d0214995c287a20e6533492c860e5e86406f5fdf77'}
MAPPING_REF = {'path': 'reports/E01_SOCKET_STATIC_MAPPING_AND_OBSERVER_V3_METHODS_20261116.json', 'bytes': 11669,
               'sha256': 'b38147f6698d621a3a32abc505466970b8197291dac0183716600607962886d6'}
PRIOR_ACTUAL_REVIEW_REF = {'path': 'reports/INDEPENDENT_AUDIT_E01_GUARD_DIAGNOSTIC_V1_ACTUAL_20261116.json',
                           'bytes': 9892, 'sha256': '5aaff6cbb5c97ee9d3a614f207fd18a0822f0dd77680106defda6ac3ff91f5d7'}
DIAGNOSTIC_SCOPE_BYTES = 16777216
ALLOCATION = {'prior_wall_seconds': 420, 'prior_observed_CPU_seconds': 160, 'prior_main_commands': 11,
              'new_wall_seconds': 30, 'new_observed_CPU_seconds': 20, 'new_main_commands': 1,
              'cumulative_wall_seconds': 450, 'cumulative_observed_CPU_seconds': 180,
              'cumulative_main_commands': 12}

PRIOR_V2_REF = {'path': 'scripts/diagnose_e01_pypdf701_guard_v2.py', 'bytes': 49178, 'sha256': '6582297cd01bc2131a4cc17ea1e0d384c15b56fee6fa07620dada9a2c7c11c49'}
PRIOR_V2_METHODS_REF = {'path': 'configs/e01_pypdf701_guard_diagnostic_v2_20261116.json', 'bytes': 6817, 'sha256': 'c85b5c887aadd88e356e63aaf8864f59f2f10005c9f036804529f95114e877b3'}
ADAPTER_REF = {'path': 'scripts/e01_offline_ipv6_adapter_v1_1_20261116.py', 'bytes': 12343, 'sha256': 'e65cacfef0cbfd59acabbf4d97e63ebfd5a866d01e1228fb53d1c78cdb5531fc'}
DECISION_REF = {'path': 'reports/E01_OFFLINE_COMPATIBILITY_V1_1_FINITE_DECISION_20261116.json', 'bytes': 6563, 'sha256': '12d40cf7f6889c66c734fc76617bada9aadf2ec4e620d2c452adeb43363d6857'}
PURE_REVIEW_REF = {'path': 'reports/INDEPENDENT_AUDIT_E01_IPV6_PROBE_COMPATIBILITY_METHODS_V2_20261116.json', 'bytes': 14670, 'sha256': '4d26a32aa0cf32c1d48703842424556303fae9be08a0c92beb24a0044edcd4f1'}
V2_ACTUAL_REF = {'path': 'reports/INDEPENDENT_AUDIT_E01_GUARD_DIAGNOSTIC_V2_ACTUAL_20261116.json', 'bytes': 40800, 'sha256': '28292ad21097cc638c181e10a1f9fe90d3c3fac7c39b0e20e63c81116c87cf37'}

V1_REVIEW_REF = {'path': 'reports/INDEPENDENT_AUDIT_E01_OFFLINE_IPV6_CONCRETE_V1_PRODUCTION_20261116.json', 'bytes': 14213, 'sha256': 'cc60b32f12a143b13b88aefd866b1fd40711035d5c27342caa362944d1ee0162'}
V1_PRESERVED_REFS = [{'path': 'scripts/e01_offline_ipv6_adapter_v1_20261116.py', 'bytes': 12302, 'sha256': 'd9be4f5fc3efde061ae881df8def47999580a6217c0100c7db213ea7e8e1b22f'}, {'path': 'scripts/validate_e01_offline_ipv6_compatibility_v1_20261116.py', 'bytes': 49669, 'sha256': 'de9393077340aa7f5cb537cddb9c93d9628773da245f255f47c2f9e84529586a'}, {'path': 'configs/e01_offline_ipv6_compatibility_v1_20261116.json', 'bytes': 4818, 'sha256': '5f2dbd8111eb1e5657526a894e21316a3d20c95a198c6a11c70eef6fafa75382'}, {'path': 'tests/test_e01_offline_ipv6_compatibility_v1_20261116.py', 'bytes': 28254, 'sha256': '61358fc6b1f2285dac745bf207908372fd2525cf4a3cb169008b5feb4a6affb8'}, {'path': 'reports/e01_offline_ipv6_compatibility_v1_312_attempt1_20261116.txt', 'bytes': 2826, 'sha256': '419f41e58de8fcd94209cad9312ad252345f43be8f3a3170d4cd90a779c809c1'}, {'path': 'reports/e01_offline_ipv6_compatibility_v1_312_attempt2_20261116.txt', 'bytes': 5812, 'sha256': '4a25bf6498bf77150da01913ef0d24a99344f24f8c3b6cb8ff549127cf752b5a'}, {'path': 'reports/e01_offline_ipv6_compatibility_v1_312_attempt3_20261116.txt', 'bytes': 6172, 'sha256': '508f5d22dc21dbac7aa8b391ac1440100031d80e2ccac7a48384e1ea07a0ae1f'}, {'path': 'reports/e01_offline_ipv6_compatibility_v1_311_attempt1_20261116.txt', 'bytes': 2826, 'sha256': '419f41e58de8fcd94209cad9312ad252345f43be8f3a3170d4cd90a779c809c1'}, {'path': 'reports/e01_offline_ipv6_compatibility_v1_311_attempt2_20261116.txt', 'bytes': 5849, 'sha256': 'd1e6cb35b0054bd652869ee1fab830aad7a5604dc2bc0ce8325846fa7e1a779d'}, {'path': 'reports/e01_offline_ipv6_compatibility_v1_311_attempt3_20261116.txt', 'bytes': 6209, 'sha256': '45a00e11fb0d626a2cfbd490fcfa90e5f604f4f859d6dbff93b2eeaf2793e650'}, {'path': 'reports/E01_OFFLINE_IPV6_COMPATIBILITY_CONCRETE_V1_HANDOFF_20261116.json', 'bytes': 12375, 'sha256': 'ed6559beac66523309c23ae5e9212de04399cee264035c9998de3dc8c39dcd78'}]
SUPERSEDED_ABSENT = ['data/processed/e01_pypdf701_build_v1/compatibility-v1-20261116', 'data/processed/e01_pypdf701_build_v1/compatibility-v1-packet-20261116.json', '.venv-e01-pypdf-7.0.1-COMPATIBILITY-NOT-INSTALL-v1']


def load_source(root, ref, name, reader=None):
    path = Path(root)/ref['path']
    if reader is None:
        if any(item.is_symlink() for item in (path, *path.parents)):
            raise RuntimeError('DIAGNOSTIC_SOURCE_ALIAS')
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size != ref['bytes'] or ref['bytes'] > 1048576:
            raise RuntimeError('DIAGNOSTIC_SOURCE_SIZE')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                    opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns):
                raise RuntimeError('DIAGNOSTIC_SOURCE_CHANGED')
            raw = stream.read(ref['bytes']+1)
    else: raw = reader.read(ref)
    if len(raw) != ref['bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise RuntimeError('DIAGNOSTIC_SOURCE_HASH')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Compile the already verified bytes, avoiding a second unchecked loader read.
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


r = load_source(ROOT, PRIOR_V2_REF, 'compatibility_reviewed_prior_runner_v2')
q = r.q
a = load_source(ROOT, ADAPTER_REF, 'compatibility_bound_ipv6_adapter')
p = q.p
c = load_source(ROOT, CANDIDATE_REF, 'diagnostic_reviewed_observer_v3')
Refused = p.Refused
need, sha, packed, json_body = p.need, p.sha, p.packed, p.json_body
no_alias, relative = p.no_alias, p.relative
CAPS = dict(p.CAPS, wall_seconds=30, observed_aggregate_CPU_seconds=20, main_commands=1)
LIMITS = {'combined_tree_entries': 16384, 'command_output_bytes': 262144, 'control_write_bytes': 8388608, 'diagnostic_scope_logical_bytes': 16777216, 'each_diagnostic_scope_logical_bytes': 16777216, 'guest_cumulative_write_bytes': 805306368, 'guest_read_bytes': 268435456, 'helper_descendants': 0, 'journal_events': 16, 'journal_serialized_bytes': 4096, 'main_children': 1, 'model_calls': 0, 'network': 0, 'observed_aggregate_CPU_seconds': 20, 'parent_child_CPU_hard_seconds': 8, 'parent_child_CPU_soft_seconds': 7, 'parent_reference_read_bytes': 536870912, 'single_file_bytes': 67108864, 'stage_wall_seconds': 30, 'combined_nine_tree_logical_bytes': 805306368}


def owned_size(root):
    total = count = 0
    for tree in tuple(root/name for name in PRESERVED_ROOTS)+(root/OUTPUT,):
        if not tree.exists(): continue
        no_alias(tree)
        before_tree = total
        for parent, dirs, names in os.walk(tree, followlinks=False):
            for name in dirs+names:
                path = Path(parent)/name
                info = path.lstat()
                count += 1
                need(count <= CAPS['tree_entries'], 'OWNED_ENTRY_CAP')
                if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode): total += info.st_size
                else: need(stat.S_ISDIR(info.st_mode), 'OWNED_SPECIAL_FILE')
                need(total <= CAPS['owned_logical_bytes'], 'OWNED_LOGICAL_BYTES_CAP')
        if tree in (root/q.OUTPUT, root/r.OUTPUT, root/OUTPUT):
            need(total-before_tree <= DIAGNOSTIC_SCOPE_BYTES, 'DIAGNOSTIC_SCOPE_LOGICAL_CAP')
    return total



class StageBudget:
    def __init__(self, root, clock=time.monotonic):
        self.root, self.clock = root, clock
        self.started = self.prior = clock()
        self.output = self.commands = 0
        self.reaped_cpu = 0.0
        self.max_owned = 0

    def check(self):
        now = self.clock()
        need(now >= self.prior, 'P2_CLOCK_REGRESSION')
        self.prior = now
        need(now-self.started < 30, 'P2_WALL_LIMIT')
        usage = resource.getrusage(resource.RUSAGE_SELF)
        observed = usage.ru_utime+usage.ru_stime+self.reaped_cpu
        need(observed < 20, 'P2_OBSERVED_AGGREGATE_CPU_LIMIT')
        self.max_owned = max(self.max_owned, owned_size(self.root))
        return observed



class Journal:
    def __init__(self, root): self.root, self.bytes, self.refs = root, 0, []
    def save(self, name, obj):
        raw = obj if type(obj) is bytes else packed(obj)
        # Reserve final terminal space within the combined old/new logical cap.
        # Final record includes its own bytes, without relying on a later poll.
        occupied = owned_size(self.root)
        scope_occupied = logical_scope_size(self.root)
        if name == 'TERMINAL.json' and type(obj) is dict:
            obj = dict(obj)
            obj['combined_logical_bytes_including_terminal'] = occupied+len(raw)
            for _ in range(4):
                raw = packed(obj)
                total = occupied+len(raw)
                if obj['combined_logical_bytes_including_terminal'] == total: break
                obj['combined_logical_bytes_including_terminal'] = total
            else: raise Refused('P2_TERMINAL_SIZE_FIXPOINT')
            need(len(raw) <= 32768, 'P2_TERMINAL_HEADROOM')
        need(occupied+len(raw)+(0 if name == 'TERMINAL.json' else 32768)
             <= CAPS['owned_logical_bytes'], 'P2_COMBINED_JOURNAL_LOGICAL_CAP')
        need(scope_occupied+len(raw)+(0 if name == 'TERMINAL.json' else 32768)
             <= DIAGNOSTIC_SCOPE_BYTES, 'DIAGNOSTIC_SCOPE_JOURNAL_CAP')
        self.bytes += len(raw)
        need(self.bytes+(0 if name == 'TERMINAL.json' else 32768) <= CAPS['control_write_bytes'], 'P2_CONTROL_WRITE_CAP')
        path = relative(self.root/OUTPUT, name)
        no_alias(path)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            need(stream.write(raw) == len(raw), 'P2_SHORT_WRITE'); stream.flush(); os.fsync(stream.fileno())
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(parent)
        finally: os.close(parent)
        ref = {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}
        self.refs.append(ref)
        return ref



class CommandStopped(Refused):
    def __init__(self, reason, record):
        super().__init__(reason)
        self.record = record



def run_command(command, env, root, budget, number):
    """One direct child; wait4 retains CPU. Never poll-reap through Popen."""
    budget.check()
    paths = [root/OUTPUT/(f'{number}-{suffix}.bin') for suffix in ('stdout', 'stderr')]
    streams = [path.open('xb') for path in paths]
    hashes, sizes = [hashlib.sha256(), hashlib.sha256()], [0, 0]
    proc = None
    selector = selectors.DefaultSelector()
    status = usage = None
    next_tree_check = 0.0
    try:
        proc = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        for i, stream in enumerate((proc.stdout, proc.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, i)
        while selector.get_map() or status is None:
            now = budget.clock()
            if now >= next_tree_check:
                budget.check(); next_tree_check = now+.1
            else:
                need(now >= budget.prior and now-budget.started < 30, 'P2_COMMAND_DEADLINE')
            for key, _ in selector.select(.05):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj); key.fileobj.close(); continue
                budget.output += len(chunk)
                need(budget.output <= CAPS['command_output_bytes'], 'P2_COMMAND_OUTPUT_CAP')
                streams[key.data].write(chunk); hashes[key.data].update(chunk); sizes[key.data] += len(chunk)
            if status is None:
                pid, candidate, observed = os.wait4(proc.pid, os.WNOHANG)
                if pid:
                    status, usage = candidate, observed
                    proc.returncode = os.waitstatus_to_exitcode(status)
        budget.reaped_cpu += usage.ru_utime+usage.ru_stime
        budget.check()
        return {'exit_code': proc.returncode, 'observed_reaped_CPU_seconds': usage.ru_utime+usage.ru_stime,
                'pip_helper_descendants_permitted': 0,
                'output': [{'path': str(path.relative_to(root/OUTPUT)), 'bytes': size, 'sha256': digest.hexdigest()}
                           for path, size, digest in zip(paths, sizes, hashes)]}
    except BaseException as exc:
        if proc is not None and status is None:
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            _, status, usage = os.wait4(proc.pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
            budget.reaped_cpu += usage.ru_utime+usage.ru_stime
        record = {'exit_code': None if proc is None else proc.returncode,
            'observed_reaped_CPU_seconds': 0 if usage is None else usage.ru_utime+usage.ru_stime,
            'pip_helper_descendants_permitted': 0, 'stopped': True,
            'output': [{'path': str(path.relative_to(root/OUTPUT)), 'bytes': size, 'sha256': digest.hexdigest()}
                       for path, size, digest in zip(paths, sizes, hashes)]}
        raise CommandStopped(str(exc) if type(exc) is Refused else type(exc).__name__, record) from None
    finally:
        selector.close()
        if proc is not None:
            for stream in (proc.stdout, proc.stderr):
                if stream is not None: stream.close()
        for stream in streams: stream.flush(); os.fsync(stream.fileno()); stream.close()


def snapshot(root):
    return p.prior_metadata_snapshot(root, tuple(root/name for name in PRESERVED_ROOTS))


def validate_methods(root, methods, reader):
    decision = json_body(reader.read(DECISION_REF))
    pure_review = json_body(reader.read(PURE_REVIEW_REF))
    actual_review = json_body(reader.read(V2_ACTUAL_REF))
    v1_review = json_body(reader.read(V1_REVIEW_REF))
    need(v1_review.get('status') == 'BLOCKED_AUDITOR_HARNESS_SCOPE_ERROR_PRODUCTION_REVIEW_NOT_COMPLETE',
         'COMPATIBILITY_RETAINED_V1_BLOCK')
    for ref in V1_PRESERVED_REFS: reader.read(ref)
    old_methods = json_body(reader.read(PRIOR_V2_METHODS_REF))
    r.validate_methods(root, old_methods, reader)
    need(methods.get('kind') == 'E01_OFFLINE_IPV6_COMPATIBILITY_METHODS_V1_1'
         and methods.get('schema_version') == 1
         and methods.get('root_sha256') == sha(str(root).encode())
         and methods.get('scope') == OUTPUT and methods.get('uncreated_target') == TARGET
         and methods.get('preserved_roots') == list(PRESERVED_ROOTS)
         and methods.get('allocation') == ALLOCATION
         and methods.get('limits') == LIMITS
         and methods.get('prior_v2_methods_ref') == PRIOR_V2_METHODS_REF
         and methods.get('adapter_ref') == ADAPTER_REF
         and methods.get('v1_review_ref') == V1_REVIEW_REF
         and methods.get('v1_preserved_refs') == V1_PRESERVED_REFS
         and methods.get('superseded_absent') == SUPERSEDED_ABSENT
         and methods.get('decision_ref') == DECISION_REF
         and methods.get('pure_review_ref') == PURE_REVIEW_REF
         and methods.get('v2_actual_review_ref') == V2_ACTUAL_REF
         and methods.get('installation_accepted') is False
         and methods.get('execution_enabled') is False
         and methods.get('packet') == 'data/processed/e01_pypdf701_build_v1/compatibility-v1_1-packet-20261116.json',
         'COMPATIBILITY_METHODS_IDENTITY')
    need(decision.get('execution_enabled') is False
         and decision.get('scope') == OUTPUT and decision.get('uncreated_target') == TARGET
         and decision.get('fully_retained_prior_allocations') == {
             'wall_seconds':420, 'observed_CPU_seconds':160, 'commands':11}
         and decision.get('prospective_cumulative_allocations') == {
             'wall_seconds':450, 'observed_CPU_seconds':180, 'commands':12}
         and decision.get('maximum_new_allocation') == {
             'main_children':1, 'observed_CPU_seconds':20,
             'parent_child_CPU_soft_hard':[7,8], 'wall_seconds':30},
         'COMPATIBILITY_DECISION_LIMITS')
    need(type(pure_review.get('status')) is str and pure_review['status'].startswith('PASS_')
         and actual_review.get('status') ==
             'PASS_EXACT_V2_DIAGNOSTIC_EVIDENCE_CONSTRUCTION_REFUSAL_RECORDED_P2_P3_REMAIN_BLOCKED',
         'COMPATIBILITY_PRIOR_REVIEWS')
    reader.read(PRIOR_V2_REF); reader.read(ADAPTER_REF)


def validate_release(root, methods, packet, reader):
    need(type(packet) is dict and set(packet) == {'kind', 'root_sha256', 'methods_sha256',
         'diagnostic_code_ref', 'execution_enabled', 'review_ref'}
         and packet['kind'] == 'E01_OFFLINE_COMPATIBILITY_EXECUTION_PACKET_V1_1'
         and packet['root_sha256'] == methods['root_sha256']
         and packet['methods_sha256'] == sha(packed(methods))
         and packet['execution_enabled'] is True, 'DIAGNOSTIC_EXPLICIT_RELEASE_REQUIRED')
    ref = packet['diagnostic_code_ref']
    need(type(ref) is dict and ref.get('path') == CODE_PATH, 'DIAGNOSTIC_CODE_REF')
    raw = reader.read(ref)
    need(sha(raw) == sha(Path(__file__).read_bytes()), 'DIAGNOSTIC_RUNNING_CODE')
    review_ref = packet['review_ref']
    need(type(review_ref) is dict and type(review_ref.get('path')) is str
         and review_ref['path'].startswith('reports/INDEPENDENT_AUDIT_'), 'DIAGNOSTIC_REVIEW_REF')
    review = json_body(reader.read(review_ref))
    core = {key: value for key, value in packet.items() if key != 'review_ref'}
    refs = review.get('evidence_refs', {})
    need(type(review.get('status')) is str and review['status'].startswith('PASS_')
         and review.get('reviewed_packet_core_sha256') == sha(packed(core))
         and refs.get(CODE_PATH) == ref
         and type(refs.get(METHODS)) is dict
         and refs[METHODS] == {'path': METHODS, 'bytes': len(packed(methods)),
                              'sha256': sha(packed(methods))}, 'DIAGNOSTIC_EXACT_PARTICULAR_REVIEW')


def verify_prior_v2(root, methods, inputs, reader):
    need(methods['prior_v2_methods_ref']['path'] == r.METHODS, 'COMPATIBILITY_PRIOR_V2_METHODS_PATH')
    refs = methods['prior_v2_refs']
    expected = {'packet', 'TERMINAL.json', 'STARTED.json', 'requirements.txt', 'guest-payload.json',
                '1-COMMAND_RESERVED.json', '1-COMMAND_RECORDED.json', '1-stdout.bin', '1-stderr.bin',
                'guest-refusals.json', 'guest-result.json'}
    need(type(refs) is dict and set(refs) == expected, 'COMPATIBILITY_PRIOR_V2_REF_SET')
    for name, ref in refs.items():
        path = ('data/processed/e01_pypdf701_build_v1/diagnostic-v2-packet-20261116.json'
                if name == 'packet' else r.OUTPUT+'/'+name)
        need(type(ref) is dict and ref.get('path') == path, 'COMPATIBILITY_PRIOR_V2_REF_PATH')
    bodies = {name: reader.read(ref) for name, ref in refs.items()}
    old_methods_raw = reader.read(methods['prior_v2_methods_ref'])
    old_methods = json_body(old_methods_raw)
    old_packet = json_body(bodies['packet'])
    r.validate_methods(root, old_methods, reader)
    r.validate_release(root, old_methods, old_packet, reader)
    need(old_packet['diagnostic_code_ref'] == PRIOR_V2_REF, 'COMPATIBILITY_PRIOR_V2_INPUT_CHAIN')
    started, terminal = json_body(bodies['STARTED.json']), json_body(bodies['TERMINAL.json'])
    old_snapshot = r.snapshot(root)
    need(started.get('kind') == 'E01_GUARD_DIAGNOSTIC_STARTED_V2'
         and started.get('methods_sha256') == sha(old_methods_raw)
         and started.get('packet_sha256') == sha(bodies['packet'])
         and started.get('code_ref') == PRIOR_V2_REF
         and started.get('prior') == inputs['prior'] and started.get('allocation') == r.ALLOCATION
         and started.get('limits') == old_methods['limits']
         and started.get('old_metadata_snapshot') == old_snapshot
         and started.get('installation_accepted') is False and started.get('no_retry') is True,
         'COMPATIBILITY_PRIOR_V2_STARTED')
    need(terminal.get('kind') == 'E01_GUARD_DIAGNOSTIC_TERMINAL_V2'
         and terminal.get('outcome') == 'REFUSAL_OBSERVED'
         and terminal.get('reason') == 'GUEST_CAUGHT_VIOLATION'
         and terminal.get('commands_started') == 1 and terminal.get('no_retry') is True
         and terminal.get('installation_accepted') is False
         and terminal.get('runtime_or_source_qualification') is False
         and terminal.get('model_calls') == 0 and terminal.get('cost_USD') == 0
         and terminal.get('prior') == inputs['prior'] and terminal.get('allocation') == r.ALLOCATION
         and terminal.get('old_metadata_snapshot') == old_snapshot, 'COMPATIBILITY_PRIOR_V2_TERMINAL')
    artifact_names = {'STARTED.json', 'requirements.txt', 'guest-payload.json',
                      '1-COMMAND_RESERVED.json', '1-COMMAND_RECORDED.json'}
    artifacts = terminal.get('artifacts')
    need(type(artifacts) is list and len(artifacts) == len(artifact_names), 'COMPATIBILITY_PRIOR_V2_ARTIFACTS')
    seen = set()
    for ref in artifacts:
        need(type(ref) is dict and type(ref.get('path')) is str and ref['path'] in artifact_names
             and ref['path'] not in seen, 'COMPATIBILITY_PRIOR_V2_ARTIFACTS')
        seen.add(ref['path'])
        need({**ref, 'path': r.OUTPUT+'/'+ref['path']} == refs[ref['path']], 'COMPATIBILITY_PRIOR_V2_ARTIFACT_REF')
    need(bodies['requirements.txt'] == inputs['requirements'], 'COMPATIBILITY_PRIOR_V2_REQUIREMENTS')
    payload = json_body(bodies['guest-payload.json'])
    expected_args = r.c.dry_run_arguments(p.pip_arguments('install', root/r.TARGET, root/r.OUTPUT/'requirements.txt'))
    need(set(payload) == {'kind', 'root_sha256', 'code_ref', 'binding_ref', 'scope', 'target', 'wheels',
                         'pip_arguments', 'remaining_wall_seconds', 'remaining_output_bytes'}
         and payload['kind'] == 'E01_GUARD_DIAGNOSTIC_GUEST_PAYLOAD_V2'
         and payload['root_sha256'] == methods['root_sha256'] and payload['scope'] == r.OUTPUT
         and payload['target'] == r.TARGET and payload['code_ref'] == PRIOR_V2_REF
         and payload['binding_ref'] == inputs['binding_ref'] and payload['wheels'] == inputs['wheels']
         and payload['pip_arguments'] == expected_args
         and type(payload['remaining_wall_seconds']) in {int, float}
         and 0 < payload['remaining_wall_seconds'] <= 30
         and type(payload['remaining_output_bytes']) is int
         and 0 < payload['remaining_output_bytes'] <= r.CAPS['command_output_bytes'], 'COMPATIBILITY_PRIOR_V2_PAYLOAD')
    reserved = json_body(bodies['1-COMMAND_RESERVED.json'])
    expected_command = [inputs['binding']['executable_ref']['path'], '-I', '-B', '-S', str(root/r.CODE_PATH),
                        '--guest', '--payload', str(root/r.OUTPUT/'guest-payload.json'),
                        '--payload-sha256', refs['guest-payload.json']['sha256']]
    need(set(reserved) == {'argv', 'helper_descendants_permitted', 'remaining_wall_seconds', 'absolute_interpreter'}
         and reserved['argv'] == expected_command and reserved['helper_descendants_permitted'] == 0
         and reserved['remaining_wall_seconds'] == payload['remaining_wall_seconds']
         and reserved['absolute_interpreter'] is True, 'COMPATIBILITY_PRIOR_V2_COMMAND')
    command = json_body(bodies['1-COMMAND_RECORDED.json'])
    need(command == terminal.get('command') and type(command.get('exit_code')) is int
         and command['exit_code'] == 1 and command.get('pip_helper_descendants_permitted') == 0
         and type(command.get('output')) is list and len(command['output']) == 2,
         'COMPATIBILITY_PRIOR_V2_COMMAND_RESULT')
    output_bytes = 0
    for name, ref in zip(('1-stdout.bin', '1-stderr.bin'), command['output']):
        need(ref.get('path') == name and {**ref, 'path': r.OUTPUT+'/'+name} == refs[name],
             'COMPATIBILITY_PRIOR_V2_OUTPUT_REF')
        output_bytes += len(bodies[name])
    need(output_bytes == terminal.get('captured_command_output_bytes')
         and output_bytes <= r.CAPS['command_output_bytes']
         and b'GUEST_CAUGHT_VIOLATION' in bodies['1-stderr.bin'], 'COMPATIBILITY_PRIOR_V2_OUTPUT_ACCOUNTING')
    original_journal = r.validate_journal(bodies['guest-refusals.json'])
    need(original_journal == terminal.get('refusals')
         and original_journal == {'kind': 'BOUNDED_GUEST_REFUSAL_JOURNAL_V2',
             'events': [{'sequence': 1, 'code': 'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED', 'operation': 'SOCKET_CONSTRUCT'}],
             'total_events': 1, 'dropped_events': 0, 'counter_saturated': False}, 'COMPATIBILITY_PRIOR_V2_COARSE_JOURNAL')
    guest = json_body(bodies['guest-result.json'])
    need(type(guest) is dict and set(guest) == {'kind', 'pip_arguments_sha256', 'guard_violations',
         'pip_completed', 'error_code', 'mime_configuration', 'installation_accepted',
         'downloaded_package_imports', 'target_exists'}
         and guest['kind'] == 'E01_GUARD_DIAGNOSTIC_GUEST_RESULT_V2'
         and guest['pip_arguments_sha256'] == sha(packed(expected_args))
         and type(guest['guard_violations']) is int and guest['guard_violations'] == 1
         and guest['pip_completed'] is True and guest['error_code'] == 'GUEST_CAUGHT_VIOLATION'
         and guest['mime_configuration'] == p.MIME_RECEIPT and guest['installation_accepted'] is False
         and guest['downloaded_package_imports'] is False and guest['target_exists'] is False,
         'COMPATIBILITY_PRIOR_V2_GUEST_RESULT')
    no_alias(root/r.TARGET); need(not (root/r.TARGET).exists(), 'COMPATIBILITY_PRIOR_V2_TARGET_CREATED')
    return {'refs': refs, 'runner_ref': PRIOR_V2_REF,
            'methods_ref': methods['prior_v2_methods_ref'], 'packet_review_ref': old_packet['review_ref'],
            'original_fine_journal': original_journal, 'full_stage_caps': r.CAPS,
            'actual_commands_started': terminal['commands_started'],
            'actual_captured_output_bytes': output_bytes,
            'actual_parent_read_bytes': terminal['parent_bound_reference_read_bytes_charged'],
            'actual_observed_CPU_seconds': terminal['observed_self_and_reaped_CPU_seconds'],
            'allocation': r.ALLOCATION, 'installation_accepted': False}


def verify_inputs(root, methods, reader):
    old_methods = json_body(reader.read(methods['prior_v2_methods_ref']))
    inputs = r.verify_inputs(root, old_methods, reader)
    previous = inputs['prior']
    prior_v2 = verify_prior_v2(root, methods, inputs, reader)
    inputs['prior'] = {'prior_through_diagnostic_v1': previous, 'diagnostic_v2': prior_v2,
        'full_prior_allocation': r.ALLOCATION,
        'full_prior_stage_caps': [p.CAPS, p.CAPS, p.CAPS, q.CAPS, r.CAPS],
        'actual_prior_commands_started': previous['actual_prior_commands_started']+prior_v2['actual_commands_started'],
        'actual_prior_captured_output_bytes': previous['actual_prior_captured_output_bytes']+prior_v2['actual_captured_output_bytes'],
        'actual_prior_parent_read_bytes': previous['actual_prior_parent_read_bytes']+prior_v2['actual_parent_read_bytes'],
        'actual_prior_observed_CPU_seconds': previous['actual_prior_observed_CPU_seconds']+prior_v2['actual_observed_CPU_seconds']}
    return inputs


def validate_journal(raw):
    need(len(raw) <= c.MAX_JSON_BYTES, 'DIAGNOSTIC_JOURNAL_SIZE')
    value = json_body(raw)
    need(type(value) is dict and set(value) == {'kind', 'events', 'total_events', 'dropped_events', 'counter_saturated'}
         and value['kind'] == 'BOUNDED_GUEST_REFUSAL_JOURNAL_V2'
         and type(value['events']) is list and len(value['events']) <= c.MAX_EVENTS
         and type(value['counter_saturated']) is bool, 'DIAGNOSTIC_JOURNAL_SCHEMA')
    for key in ('total_events', 'dropped_events'):
        need(type(value[key]) is int and 0 <= value[key] <= c.MAX_COUNTER, 'DIAGNOSTIC_JOURNAL_COUNTER')
    previous = 0
    for event in value['events']:
        need(type(event) is dict and set(event) == {'sequence', 'code', 'operation'}
             and type(event['sequence']) is int and previous < event['sequence'] <= value['total_events']
             and type(event['code']) is str and event['code'] in c.CODES|{'UNKNOWN_REFUSAL_CODE'}
             and type(event['operation']) is str and event['operation'] in c.OPERATIONS|{'UNKNOWN'},
             'DIAGNOSTIC_JOURNAL_EVENT')
        previous = event['sequence']
    need(value['total_events'] >= len(value['events'])
         and (value['counter_saturated'] or value['dropped_events'] == value['total_events']-len(value['events'])),
         'DIAGNOSTIC_JOURNAL_COUNTS')
    return value


def read_owned_result(scope, name, maximum):
    path = relative(scope, name); no_alias(path)
    need(path.is_file() and path.stat().st_size <= maximum, 'DIAGNOSTIC_RESULT_SIZE')
    raw = path.read_bytes()
    need(len(raw) <= maximum, 'DIAGNOSTIC_RESULT_SIZE')
    return raw


def validate_compatibility_receipt(raw, binding, root):
    need(len(raw) <= 131072, 'COMPATIBILITY_RECEIPT_SIZE')
    receipt = json_body(raw)
    expected_keys = {'kind', 'original_has_ipv6', 'temporary_has_ipv6',
        'restored_has_ipv6', 'vendor_cached_ipv6', 'target_module', 'socket_ref',
        'import_closure', 'closure_logical_read_bytes', 'network_permissions_changed',
        'parent_transitive_consumers_may_observe_false'}
    need(type(receipt) is dict and set(receipt) == expected_keys
         and receipt['kind'] == 'E01_OFFLINE_IPV6_COMPATIBILITY_RECEIPT_V1_1'
         and receipt['original_has_ipv6'] is True and receipt['temporary_has_ipv6'] is False
         and receipt['restored_has_ipv6'] is True and receipt['vendor_cached_ipv6'] is False
         and receipt['target_module'] == a.TARGET
         and receipt['socket_ref'] == {'path': str(Path(binding['base_prefix'])/'lib/python3.12/socket.py'), **a.SOCKET_REF}
         and receipt['network_permissions_changed'] is False
         and receipt['parent_transitive_consumers_may_observe_false'] is True
         and type(receipt['closure_logical_read_bytes']) is int
         and 0 < receipt['closure_logical_read_bytes'] <= a.MAX_SOURCE_BYTES,
         'COMPATIBILITY_RECEIPT_SCHEMA')
    closure = receipt['import_closure']
    need(type(closure) is list and 1 <= len(closure) <= a.MAX_MODULES,
         'COMPATIBILITY_RECEIPT_CLOSURE')
    names, source_bytes, sources = [], 0, set()
    base = Path(binding['base_prefix'])/'lib/python3.12'
    for item in closure:
        need(type(item) is dict and type(item.get('name')) is str
             and 0 < len(item['name']) <= 256 and type(item.get('origin')) is str,
             'COMPATIBILITY_RECEIPT_MODULE')
        names.append(item['name'])
        if item['origin'] in {'built-in', 'frozen', 'not-found'}:
            need(set(item) == {'name', 'origin'}, 'COMPATIBILITY_RECEIPT_MODULE')
            continue
        need(set(item) == {'name', 'origin', 'source_ref'}, 'COMPATIBILITY_RECEIPT_MODULE')
        ref = item['source_ref']
        need(type(ref) is dict and set(ref) == {'path', 'bytes', 'sha256'}
             and type(ref['path']) is str and type(ref['bytes']) is int
             and 0 <= ref['bytes'] <= a.MAX_FILE_BYTES
             and type(ref['sha256']) is str and len(ref['sha256']) == 64
             and all(c in '0123456789abcdef' for c in ref['sha256']),
             'COMPATIBILITY_RECEIPT_SOURCE')
        path = Path(item['origin'])
        need(path.is_absolute() and '..' not in path.parts, 'COMPATIBILITY_RECEIPT_ORIGIN')
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else None
        if rel in binding['pip_files']:
            need(ref == {'path': rel, **binding['pip_files'][rel]}, 'COMPATIBILITY_RECEIPT_PIP_PIN')
        else:
            need(path.is_relative_to(base) and not path.is_relative_to(base/'site-packages')
                 and ref['path'] == str(path), 'COMPATIBILITY_RECEIPT_ORIGIN')
        if ref['path'] not in sources:
            source_bytes += ref['bytes']+1
            sources.add(ref['path'])
    need(names == sorted(set(names)) and a.TARGET in names
         and source_bytes <= receipt['closure_logical_read_bytes'],
         'COMPATIBILITY_RECEIPT_CLOSURE')
    target = next(item for item in closure if item['name'] == a.TARGET)
    expected = binding['pip_root']+'/_vendor/urllib3/util/connection.py'
    need(target.get('source_ref') == {'path': expected, **binding['pip_files'][expected]}
         and target['origin'] == str(root/expected), 'COMPATIBILITY_RECEIPT_TARGET')
    return receipt


def capture_compatibility(scope, binding, root):
    """Bind full bounded evidence in its guest file; never embed its closure.

    Used after ordinary completion and again on every exception/stopped-child
    path. Invalid bounded evidence is still hashed and retained as invalid.
    """
    path = scope/'guest-compatibility.json'
    no_alias(path)
    if not path.exists(): return None
    raw = read_owned_result(scope, 'guest-compatibility.json', 131072)
    ref = {'path': 'guest-compatibility.json', 'bytes': len(raw), 'sha256': sha(raw)}
    try:
        receipt = validate_compatibility_receipt(raw, binding, root)
    except BaseException as exc:
        code = str(exc) if type(exc) is Refused else type(exc).__name__
        need(len(code) <= 128, 'COMPATIBILITY_RECEIPT_ERROR_BOUND')
        return {'ref': ref, 'validated': False, 'summary': None, 'error_code': code}
    summary = {key: receipt[key] for key in ('kind', 'original_has_ipv6',
        'temporary_has_ipv6', 'restored_has_ipv6', 'vendor_cached_ipv6',
        'target_module', 'closure_logical_read_bytes', 'network_permissions_changed',
        'parent_transitive_consumers_may_observe_false')}
    summary['closure_entries'] = len(receipt['import_closure'])
    need(len(packed(summary)) <= 1024, 'COMPATIBILITY_TERMINAL_SUMMARY_BOUND')
    record = {'ref': ref, 'validated': True, 'summary': summary, 'error_code': None}
    need(len(packed(record)) <= 1536, 'COMPATIBILITY_TERMINAL_BINDING_BOUND')
    return record


def terminal_headroom(prior, before):
    """Reject oversized preserved ancestry before consuming the new scope.

    Other terminal fields have finite control schemas: <=4096B fine refusal
    journal, <=1536B compatibility binding, two command output refs, <=7 own
    artifact refs, bounded counters/closed reasons and fixed labels. Reserve
    12288B for all those fields and the terminal-size fixpoint. The inherited
    Journal still enforces the exact32768B final encoding limit.
    """
    ancestry_bytes = len(packed({'prior': prior, 'old_metadata_snapshot': before}))
    need(ancestry_bytes+12288 <= 32768, 'COMPATIBILITY_TERMINAL_ANCESTRY_HEADROOM')
    return {'ancestry_bytes': ancestry_bytes, 'other_reserved_bytes': 12288,
            'terminal_bytes_cap': 32768, 'maximum_supported_total': ancestry_bytes+12288}


def execute(root, methods, packet, *, launcher=run_command, clock=time.monotonic):
    root = Path(root).absolute()
    reader, budget = p.Reader(root, CAPS['parent_read_bytes']), StageBudget(root, clock)
    validate_methods(root, methods, reader); validate_release(root, methods, packet, reader)
    for name in SUPERSEDED_ABSENT:
        no_alias(root/name); need(not (root/name).exists(), 'COMPATIBILITY_SUPERSEDED_SCOPE_NOT_ABSENT')
    for path in (root/OUTPUT, root/TARGET):
        no_alias(path); need(not path.exists(), 'DIAGNOSTIC_ALREADY_CONSUMED')
    inputs = verify_inputs(root, methods, reader)
    before = snapshot(root)
    terminal_headroom(inputs['prior'], before)
    need(owned_size(root)+DIAGNOSTIC_SCOPE_BYTES <= CAPS['owned_logical_bytes'], 'DIAGNOSTIC_STORAGE_PREFLIGHT')
    budget.check()
    scope = root/OUTPUT; scope.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    scope.mkdir(mode=0o700, exist_ok=False)
    parent = os.open(scope.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(parent)
    finally: os.close(parent)
    journal = Journal(root)
    compatibility = None
    outcome, reason, command_result, observed = 'FAILED_COMPATIBILITY', None, None, None
    try:
        journal.save('STARTED.json', {'kind': 'E01_OFFLINE_COMPATIBILITY_STARTED_V1_1',
            'utc': datetime.now(timezone.utc).isoformat(), 'methods_sha256': sha(packed(methods)),
            'packet_sha256': sha(packed(packet)), 'code_ref': packet['diagnostic_code_ref'],
            'prior': inputs['prior'], 'allocation': ALLOCATION, 'limits': methods['limits'],
            'old_metadata_snapshot': before, 'installation_accepted': False, 'no_retry': True})
        for name in ('tmp', 'home'): (scope/name).mkdir(mode=0o700)
        journal.save('requirements.txt', inputs['requirements'])
        argv = c.dry_run_arguments(p.pip_arguments('install', root/TARGET, scope/'requirements.txt'))
        environment = {'HOME': str(scope/'home'), 'TMPDIR': str(scope/'tmp'),
            'PATH': str(Path(inputs['binding']['base_prefix'])/'bin')+':/usr/bin:/bin',
            'PIP_CONFIG_FILE': os.devnull, 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
            'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C', 'LANG': 'C'}
        budget.check()
        payload = {'kind': 'E01_OFFLINE_COMPATIBILITY_GUEST_PAYLOAD_V1_1',
            'root_sha256': methods['root_sha256'], 'code_ref': packet['diagnostic_code_ref'],
            'binding_ref': inputs['binding_ref'], 'scope': OUTPUT, 'target': TARGET,
            'wheels': inputs['wheels'], 'pip_arguments': argv,
            'remaining_wall_seconds': 30-(budget.clock()-budget.started),
            'remaining_output_bytes': CAPS['command_output_bytes']-budget.output}
        payload_ref = journal.save('guest-payload.json', payload)
        command = [inputs['binding']['executable_ref']['path'], '-I', '-B', '-S', str(root/CODE_PATH),
                   '--guest', '--payload', str(scope/payload_ref['path']), '--payload-sha256', payload_ref['sha256']]
        need(budget.commands == 0, 'DIAGNOSTIC_ONE_CHILD')
        journal.save('1-COMMAND_RESERVED.json', {'argv': command, 'helper_descendants_permitted': 0,
            'remaining_wall_seconds': payload['remaining_wall_seconds'], 'absolute_interpreter': True})
        budget.commands = 1
        try: command_result = launcher(command, environment, root, budget, 1)
        except CommandStopped as exc:
            command_result = exc.record
            journal.save('1-COMMAND_STOPPED.json', command_result)
            raise Refused(str(exc)) from None
        journal.save('1-COMMAND_RECORDED.json', command_result)
        need(command_result.get('pip_helper_descendants_permitted') == 0, 'DIAGNOSTIC_HELPER_DENIED')
        observed = validate_journal(read_owned_result(scope, 'guest-refusals.json', c.MAX_JSON_BYTES))
        result = json_body(read_owned_result(scope, 'guest-result.json', 8192))
        compatibility = None
        if (scope/'guest-compatibility.json').exists():
            compatibility = capture_compatibility(scope, inputs['binding'], root)
        need(type(result) is dict and set(result) == {'kind', 'pip_arguments_sha256', 'guard_violations',
             'pip_completed', 'error_code', 'mime_configuration', 'installation_accepted',
             'downloaded_package_imports', 'target_exists'}
             and result['kind'] == 'E01_OFFLINE_COMPATIBILITY_GUEST_RESULT_V1_1'
             and result['pip_arguments_sha256'] == sha(packed(argv))
             and result['installation_accepted'] is False and result['downloaded_package_imports'] is False
             and result['target_exists'] is False and type(result['guard_violations']) is int
             and result['guard_violations'] >= 0 and type(result['pip_completed']) is bool,
             'DIAGNOSTIC_GUEST_RESULT')
        if result['guard_violations']:
            need(observed['total_events'] > 0 and command_result.get('exit_code') != 0
                 and result['error_code'] == 'GUEST_CAUGHT_VIOLATION', 'DIAGNOSTIC_REFUSAL_POSTCONDITION')
            outcome, reason = 'REFUSAL_OBSERVED', 'GUEST_CAUGHT_VIOLATION'
        else:
            need(observed['total_events'] == 0 and command_result.get('exit_code') == 0
                 and result['pip_completed'] is True and result['error_code'] is None
                 and result['mime_configuration'] == p.MIME_RECEIPT
                 and compatibility is not None and compatibility['validated'] is True, 'DIAGNOSTIC_NO_REFUSAL_PROOF')
            outcome = 'COMPATIBLE_OFFLINE_CONFIGURATION'
    except BaseException as exc:
        reason = str(exc) if type(exc) is Refused else type(exc).__name__
    finally:
        try:
            final_compatibility = capture_compatibility(scope, inputs['binding'], root)
            if compatibility is not None:
                need(final_compatibility == compatibility, 'COMPATIBILITY_RECEIPT_CHANGED')
            compatibility = final_compatibility
            if compatibility is not None and compatibility['validated'] is not True:
                outcome, reason = 'FAILED_COMPATIBILITY', 'COMPATIBILITY_RECEIPT_INVALID'
        except BaseException as exc:
            outcome, reason = 'FAILED_COMPATIBILITY', str(exc) if type(exc) is Refused else type(exc).__name__
        try:
            need(verify_inputs(root, methods, reader) == inputs
                 and snapshot(root) == before, 'DIAGNOSTIC_OLD_STATE_CHANGED')
            for name in SUPERSEDED_ABSENT:
                no_alias(root/name); need(not (root/name).exists(), 'COMPATIBILITY_SUPERSEDED_SCOPE_NOT_ABSENT')
            no_alias(root/TARGET); need(not (root/TARGET).exists(), 'DIAGNOSTIC_TARGET_CREATED')
            budget.check()
        except BaseException as exc:
            outcome, reason = 'FAILED_COMPATIBILITY', str(exc) if type(exc) is Refused else type(exc).__name__
        journal.save('TERMINAL.json', {'kind': 'E01_OFFLINE_COMPATIBILITY_TERMINAL_V1_1',
            'outcome': outcome, 'reason': reason, 'commands_started': budget.commands,
            'command': command_result, 'refusals': observed, 'compatibility': compatibility, 'prior': inputs['prior'], 'allocation': ALLOCATION,
            'old_metadata_snapshot': before, 'maximum_polled_owned_logical_bytes': budget.max_owned,
            'parent_bound_reference_read_bytes_charged': reader.charged, 'captured_command_output_bytes': budget.output,
            'reaped_child_CPU_seconds': budget.reaped_cpu, 'artifacts': journal.refs,
            'observed_self_and_reaped_CPU_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime+
                resource.getrusage(resource.RUSAGE_SELF).ru_stime+budget.reaped_cpu,
            'no_retry': True, 'installation_accepted': False, 'runtime_or_source_qualification': False,
            'model_calls': 0, 'cost_USD': 0})
    return {'outcome': outcome, 'reason': reason, 'commands_started': budget.commands,
            'installation_accepted': False, 'cost_USD': 0}


def logical_scope_size(root):
    tree = root/OUTPUT
    if not tree.exists(): return 0
    no_alias(tree)
    total = count = 0
    for parent, dirs, names in os.walk(tree, followlinks=False):
        for name in dirs+names:
            info = (Path(parent)/name).lstat(); count += 1
            need(count <= CAPS['tree_entries'], 'OWNED_ENTRY_CAP')
            if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode): total += info.st_size
            else: need(stat.S_ISDIR(info.st_mode), 'OWNED_SPECIAL_FILE')
            need(total <= DIAGNOSTIC_SCOPE_BYTES, 'DIAGNOSTIC_SCOPE_LOGICAL_CAP')
    return total


def compatibility_policy_class(base_policy):
    recording = c.recording_policy_class(base_policy)
    class CompatibilityPolicy(recording):
        def __init__(self, root, binding, payload):
            super().__init__(root, binding, payload)
            self.stage, self.target = self.root/OUTPUT, self.root/TARGET
            for path in (self.stage, self.target):
                no_alias(path)
            need(not self.target.exists(), 'COMPATIBILITY_TARGET_EXISTS')
    return CompatibilityPolicy


def install_guard(root, binding, payload):
    import builtins
    import io
    helper = p.load_bound_module(root, p.GUARD_REF, 'diagnostic_bound_dirfd_guard')
    policy = compatibility_policy_class(p.GuestPolicy)(root, binding, payload)
    # These exact trusted code bodies were hash-verified before hook setup.
    policy.exact_reads.update({root/CODE_PATH, root/CANDIDATE_REF['path'], root/ADAPTER_REF['path']})
    guard = helper.DirectoryFdGuard(policy.path)
    policy.fdguard = guard
    sys.meta_path.insert(0, p.DownloadedImportGuard(policy))
    sys.addaudithook(policy.audit)
    os.open, os.close = guard.open, guard.close
    def wrap(original):
        def opening(*args, **kwargs):
            stream = original(*args, **kwargs)
            return stream if isinstance(stream, p.ChargedFile) else p.ChargedFile(stream, policy)
        return opening
    builtins.open, io.open, os.fdopen = wrap(builtins.open), wrap(io.open), wrap(os.fdopen)
    raw_write = os.write
    def write(fd, body):
        policy.charge(body, fd in {1, 2})
        return raw_write(fd, body)
    os.write = write
    sys.stdout, sys.stderr = p.ChargedFile(sys.stdout, policy, True), p.ChargedFile(sys.stderr, policy, True)
    return policy


def run_dry_pip(binding, root, arguments):
    target, site = root/TARGET, root/SITE
    p.target_scheme(target)
    expected = c.dry_run_arguments(p.pip_arguments('install', target, root/OUTPUT/'requirements.txt'))
    need(arguments == expected, 'DIAGNOSTIC_EXACT_ARGUMENTS')
    original = p.narrowed_paths(list(sys.path), binding['base_prefix'])
    need(not any('site-packages' in item for item in original), 'BASE_OR_OLD_SITE_ON_PATH')
    need(not any(name == 'pip' or name.startswith('pip.') for name in sys.modules), 'DIAGNOSTIC_PIP_PRELOADED')
    pip_root = root/binding['pip_root']
    spec = importlib.util.spec_from_file_location('pip', pip_root/'__init__.py',
                                                submodule_search_locations=[str(pip_root)])
    module = importlib.util.module_from_spec(spec)
    sys.modules['pip'] = module
    spec.loader.exec_module(module)
    need(module.__version__ == '25.0.1', 'PIP_LOADED_VERSION')
    receipt = a.initialize_offline(root, binding, p.Reader(root, a.MAX_SOURCE_BYTES))
    write_guest_file('guest-compatibility.json', packed(receipt))
    sys.path[:] = [str(site)]+original
    old_args = sys.argv
    sys.argv = expected
    try:
        try: runpy.run_module('pip', run_name='__main__', alter_sys=True)
        except SystemExit as exc: need(exc.code in (None, 0), 'PIP_NONZERO_EXIT')
    finally: sys.argv = old_args
    need(sys.modules['socket'].has_ipv6 is True and sys.modules[a.TARGET].HAS_IPV6 is False,
         'COMPATIBILITY_PERSISTENT_RESULT_DRIFT')
    need(sys.path[0] == str(site) and str(pip_root.parent) not in sys.path
         and all(str(root/name/'lib/python3.12/site-packages') not in sys.path
                 for name in PRESERVED_ROOTS if name.startswith('.venv')), 'DIAGNOSTIC_OLD_SITE_EXPOSED')


def write_guest_file(name, raw):
    path = relative(ROOT/OUTPUT, name); no_alias(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        need(stream.write(raw) == len(raw), 'DIAGNOSTIC_GUEST_SHORT_WRITE')
        stream.flush(); os.fsync(stream.fileno())


def guest_main(args):
    need(Path.cwd().absolute() == ROOT, 'DIAGNOSTIC_GUEST_ROOT')
    path = relative(ROOT, OUTPUT+'/guest-payload.json')
    need(Path(args.payload).absolute() == path, 'DIAGNOSTIC_GUEST_PAYLOAD_PATH')
    no_alias(path); need(path.stat().st_size <= 1048576, 'DIAGNOSTIC_GUEST_PAYLOAD_SIZE')
    raw = path.read_bytes(); need(sha(raw) == args.payload_sha256, 'DIAGNOSTIC_GUEST_PAYLOAD_HASH')
    payload = json_body(raw)
    need(type(payload) is dict and set(payload) == {'kind', 'root_sha256', 'code_ref', 'binding_ref', 'scope',
         'target', 'wheels', 'pip_arguments', 'remaining_wall_seconds', 'remaining_output_bytes'}
         and payload['kind'] == 'E01_OFFLINE_COMPATIBILITY_GUEST_PAYLOAD_V1_1'
         and payload['root_sha256'] == sha(str(ROOT).encode()) and payload['scope'] == OUTPUT
         and payload['target'] == TARGET and payload['code_ref']['path'] == CODE_PATH
         and payload['code_ref']['sha256'] == sha(Path(__file__).read_bytes()), 'DIAGNOSTIC_GUEST_IDENTITY')
    remaining = payload['remaining_wall_seconds']
    need(type(remaining) in {int, float} and 0 < remaining <= 30
         and type(payload['remaining_output_bytes']) is int
         and 0 < payload['remaining_output_bytes'] <= CAPS['command_output_bytes'], 'DIAGNOSTIC_GUEST_LIMITS')
    def deadline(*_): raise Refused('DIAGNOSTIC_GUEST_DEADLINE')
    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline)
    signal.setitimer(signal.ITIMER_REAL, remaining)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); resource.setrlimit(resource.RLIMIT_CPU, (7, 8))
    resource.setrlimit(resource.RLIMIT_FSIZE, (CAPS['single_file_bytes'], CAPS['single_file_bytes']))
    reader = p.Reader(ROOT, 4194304)
    binding = json_body(reader.read(payload['binding_ref']))
    reader.read(FROZEN_REF); reader.read(CANDIDATE_REF); reader.read(ADAPTER_REF); reader.read(payload['code_ref'])
    expected = c.dry_run_arguments(p.pip_arguments('install', ROOT/TARGET, ROOT/OUTPUT/'requirements.txt'))
    need(payload['pip_arguments'] == expected, 'DIAGNOSTIC_EXACT_ARGUMENTS')
    policy = install_guard(ROOT, binding, payload)
    completed, error, mime = False, None, None
    try:
        mime = p.prepare_builtin_mime(binding)
        run_dry_pip(binding, ROOT, expected)
        completed = True
    except BaseException as exc:
        error = 'PIP_NONZERO_EXIT' if type(exc) is Refused and str(exc) == 'PIP_NONZERO_EXIT' else 'DIAGNOSTIC_GUEST_ERROR'
    finally:
        # No raw write exemption: the original file/read/write/output guards and
        # charges remain active. A flush failure is a failure, never permission.
        write_guest_file('guest-refusals.json', policy.refusal_journal.packed())
    if policy.violations: error = 'GUEST_CAUGHT_VIOLATION'
    result = {'kind': 'E01_OFFLINE_COMPATIBILITY_GUEST_RESULT_V1_1', 'pip_arguments_sha256': sha(packed(expected)),
              'guard_violations': policy.violations, 'pip_completed': completed, 'error_code': error,
              'mime_configuration': mime, 'installation_accepted': False, 'downloaded_package_imports': False,
              'target_exists': (ROOT/TARGET).exists()}
    write_guest_file('guest-result.json', packed(result))
    need(policy.violations == 0, 'GUEST_CAUGHT_VIOLATION')
    return 0 if completed and error is None and not (ROOT/TARGET).exists() else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--methods-sha256'); parser.add_argument('--packet-sha256')
    parser.add_argument('--guest', action='store_true')
    parser.add_argument('--payload'); parser.add_argument('--payload-sha256')
    args = parser.parse_args()
    need(Path.cwd().absolute() == ROOT and sys.version.split()[0] == '3.12.14'
         and sys.implementation.name == 'cpython' and sys.platform == 'darwin'
         and platform.machine() == 'arm64' and platform.mac_ver()[0] == '26.6', 'DIAGNOSTIC_HOST_RUNTIME')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); resource.setrlimit(resource.RLIMIT_CPU, (7, 8))
    def deadline(*_): raise Refused('DIAGNOSTIC_DEADLINE_SIGNAL')
    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline)
    signal.setitimer(signal.ITIMER_REAL, 30)
    if args.guest: return guest_main(args)
    def no_network(event, _):
        if event.startswith('socket.'): raise Refused('DIAGNOSTIC_PARENT_NETWORK_DENIED')
    sys.addaudithook(no_network)
    need(args.methods_sha256 and args.packet_sha256, 'DIAGNOSTIC_CLI_BINDING_REQUIRED')
    path = ROOT/METHODS; no_alias(path); need(path.stat().st_size <= 65536, 'DIAGNOSTIC_METHODS_SIZE')
    raw = path.read_bytes(); need(sha(raw) == args.methods_sha256, 'DIAGNOSTIC_METHODS_HASH')
    methods = json_body(raw); need(packed(methods) == raw, 'DIAGNOSTIC_METHODS_CANONICAL')
    path = relative(ROOT, methods['packet']); no_alias(path)
    need(path.stat().st_size <= 65536, 'DIAGNOSTIC_PACKET_SIZE')
    raw = path.read_bytes(); need(sha(raw) == args.packet_sha256, 'DIAGNOSTIC_PACKET_HASH')
    packet = json_body(raw); need(packed(packet) == raw, 'DIAGNOSTIC_PACKET_CANONICAL')
    result = execute(ROOT, methods, packet)
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(packed(result).decode())
    return 0 if result['outcome'] == 'COMPATIBLE_OFFLINE_CONFIGURATION' else 1


if __name__ == '__main__':
    raise SystemExit(main())

