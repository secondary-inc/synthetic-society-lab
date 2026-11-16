"""Create-once P2 offline installer. Actual execution is lead-scheduled only.

No downloaded package is imported. A completed P1 is input evidence, never
installation authority. Main requires separately hash-bound methods and packet.
"""
import argparse
import ast
from email.parser import BytesParser
import hashlib
import importlib.abc
import importlib.metadata
import importlib.util
import io
import json
import os
import platform
from pathlib import Path
import re
import resource
import runpy
import selectors
import signal
import stat
import subprocess
import sys
import sysconfig
import threading
import time
import venv

ROOT = Path(__file__).absolute().parents[1]
METHODS = 'configs/e01_pypdf701_install_v1_1_20261115.json'
OUTPUT = 'data/processed/e01_pypdf701_build_v1/install-v1_1-20261115'
TARGET = '.venv-e01-pypdf-7.0.1-v1'
SITE = TARGET + '/lib/python3.12/site-packages'
P1_SCOPE = 'data/processed/e01_pypdf701_build_v1/acquisition-v1_3-20261115'
VERSIONS = {'pypdf': '7.0.1', 'cffi': '2.1.1', 'cryptography': '50.0.2', 'pillow': '13.0.0', 'pycparser': '3.12'}
CAPS = {'wall_seconds': 120, 'parent_child_CPU_soft_seconds': 7, 'parent_child_CPU_hard_seconds': 8,
        'observed_aggregate_CPU_seconds': 40, 'command_output_bytes': 262144,
        'owned_logical_bytes': 805306368, 'main_commands': 3, 'network': 0,
        'parent_read_bytes': 536870912, 'guest_read_bytes_each': 268435456,
        'guest_cumulative_write_bytes_each': 805306368, 'single_file_bytes': 67108864,
        'tree_entries': 16384, 'control_write_bytes': 8388608}
BASE_REF = {'path': 'scripts/acquire_e01_pypdf701_artifacts_v1.py', 'bytes': 31924,
            'sha256': '6a8c9ec9826b3f16c8a9cd11b6f9d7991d0dbe65b136d2fed05b74330223a9cc'}
GUARD_REF = {'path': 'scripts/e01_authored_dirfd_guard_v2_20261112.py', 'bytes': 5143,
             'sha256': '431fe340a87bd090f0898c5efef87a5b69f766964eaeb4a53776c3479f3dd000'}
MARKERS = {'python_version': '3.12', 'python_full_version': '3.12.14', 'implementation_version': '3.12.14',
           'implementation_name': 'cpython', 'platform_python_implementation': 'CPython',
           'platform_machine': 'arm64', 'platform_system': 'Darwin', 'sys_platform': 'darwin',
           'os_name': 'posix', 'extra': ''}
BLOCKED_IMPORTS = {'pypdf', 'PIL', 'cryptography', 'cffi', '_cffi_backend', 'pycparser'}


class Refused(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise Refused(reason)


def sha(raw): return hashlib.sha256(raw).hexdigest()
def packed(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def normalize(name): return re.sub('[-_.]+', '-', name).lower()


def json_body(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, 'JSON_DUPLICATE_KEY')
            out[key] = value
        return out
    try:
        result = json.loads(raw, object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(Refused('JSON_NONFINITE')))
    except (ValueError, UnicodeError, RecursionError):
        raise Refused('JSON_SCHEMA') from None
    left = [50000]
    def walk(item, depth):
        left[0] -= 1
        need(left[0] >= 0 and depth <= 24, 'JSON_COMPLEXITY')
        if isinstance(item, dict):
            for value in item.values(): walk(value, depth+1)
        elif isinstance(item, list):
            for value in item: walk(value, depth+1)
        elif isinstance(item, float):
            import math
            need(math.isfinite(item), 'JSON_NONFINITE')
    walk(result, 0)
    return result


def no_alias(path):
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'PATH_ALIAS')


def relative(root, name):
    need(type(name) is str and name and not Path(name).is_absolute()
         and '..' not in Path(name).parts and str(Path(name)) == name, 'RELATIVE_PATH')
    return root / name


class Reader:
    def __init__(self, root, limit=CAPS['parent_read_bytes']):
        self.root, self.limit, self.charged = Path(root), limit, 0

    def read(self, ref, absolute=False):
        need(type(ref) is dict and set(ref) == {'path', 'bytes', 'sha256'} and type(ref['bytes']) is int
             and 0 <= ref['bytes'] <= CAPS['single_file_bytes'] and type(ref['sha256']) is str
             and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'INPUT_REF')
        path = Path(ref['path']) if absolute else relative(self.root, ref['path'])
        need(not absolute or path.is_absolute(), 'ABSOLUTE_REF')
        no_alias(path)
        before = path.stat(follow_symlinks=False)
        need(stat.S_ISREG(before.st_mode) and before.st_size == ref['bytes'], 'INPUT_TYPE_SIZE')
        self.charged += ref['bytes']+1
        need(self.charged <= self.limit, 'READ_CAP')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                 (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns), 'INPUT_CHANGED')
            raw = stream.read(ref['bytes']+1)
            after = os.fstat(stream.fileno())
            need((opened.st_size, opened.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'INPUT_CHANGED')
        need(len(raw) == ref['bytes'] and sha(raw) == ref['sha256'], 'INPUT_HASH')
        return raw


def load_bound_module(root, ref, name, reader=None):
    raw = (reader or Reader(root)).read(ref)
    spec = importlib.util.spec_from_file_location(name, relative(root, ref['path']))
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(root/ref['path']), 'exec'), module.__dict__)
    return module


def numeric(text):
    need(type(text) is str and re.fullmatch(r'[0-9]+(?:\.[0-9]+){0,2}', text), 'UNSUPPORTED_VERSION')
    parts = tuple(map(int, text.split('.')))
    return parts + (0,)*(3-len(parts))


def version_matches(spec, candidate):
    if not spec.strip(): return True
    parts = spec.split(',')
    need(len(parts) <= 8, 'ACTIVE_VERSION_SPEC')
    result = []
    for clause in parts:
        match = re.fullmatch(r'\s*(<=|>=|==|!=|<|>)\s*([0-9]+(?:\.[0-9]+){0,2})\s*', clause)
        need(match is not None, 'ACTIVE_VERSION_SPEC')
        op, text = match.groups(); a, b = numeric(candidate), numeric(text)
        result.append({'<': a < b, '>': a > b, '<=': a <= b, '>=': a >= b, '==': a == b, '!=': a != b}[op])
    return all(result)


def marker_active(text):
    if text is None: return True
    need(type(text) is str and 0 < len(text) <= 512, 'MARKER_SCHEMA')
    try:
        tree = ast.parse(text.strip(), mode='eval')
    except (SyntaxError, RecursionError): raise Refused('UNKNOWN_MARKER') from None
    allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Compare, ast.Name, ast.Load, ast.Constant,
               ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn)
    nodes = list(ast.walk(tree))
    need(len(nodes) <= 100 and all(isinstance(node, allowed) for node in nodes), 'UNKNOWN_MARKER')
    for node in nodes:
        if isinstance(node, ast.Name): need(node.id in MARKERS, 'UNKNOWN_MARKER_VARIABLE')
        if isinstance(node, ast.Constant): need(type(node.value) is str and len(node.value) <= 128, 'MARKER_LITERAL')
    def value(node):
        if isinstance(node, ast.Name): return MARKERS[node.id]
        need(isinstance(node, ast.Constant), 'MARKER_OPERAND')
        return node.value
    def evaluate(node):
        if isinstance(node, ast.BoolOp):
            values = [evaluate(v) for v in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        need(isinstance(node, ast.Compare), 'MARKER_BOOLEAN')
        checks = []
        for left, op, right in zip([node.left]+node.comparators, node.ops, node.comparators):
            a, b = value(left), value(right)
            version_names = {'python_version', 'python_full_version', 'implementation_version'}
            is_version = any(isinstance(n, ast.Name) and n.id in version_names for n in (left, right))
            if isinstance(op, ast.In): checks.append(a in b); continue
            if isinstance(op, ast.NotIn): checks.append(a not in b); continue
            if is_version: a, b = numeric(a), numeric(b)
            checks.append({ast.Eq: a == b, ast.NotEq: a != b, ast.Lt: a < b,
                           ast.LtE: a <= b, ast.Gt: a > b, ast.GtE: a >= b}[type(op)])
        return all(checks)
    return evaluate(tree.body)


def dependency_closure(requirements):
    need(set(requirements) == set(VERSIONS), 'DEPENDENCY_PACKAGE_SET')
    result = []
    for owner, rows in requirements.items():
        need(type(rows) is list and len(rows) <= 256, 'DEPENDENCY_ROWS')
        for raw in rows:
            need(type(raw) is str and 0 < len(raw) <= 1024 and raw.count(';') <= 1, 'DEPENDENCY_SCHEMA')
            requirement, _, marker = raw.partition(';')
            match = re.fullmatch(r'\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[A-Za-z0-9_,.-]+\])?\s*(.*?)\s*', requirement)
            need(match is not None and '@' not in requirement and '\n' not in requirement, 'DEPENDENCY_SCHEMA')
            name, extras, spec = match.groups(); name = normalize(name)
            active = marker_active(marker if _ else None)
            spec = spec.strip()
            if spec.startswith('(') and spec.endswith(')'): spec = spec[1:-1]
            if active:
                need(extras is None, 'ACTIVE_DEPENDENCY_EXTRAS')
                need(name in VERSIONS and version_matches(spec, VERSIONS[name]), 'DEPENDENCY_NOT_SATISFIED')
            result.append({'owner': owner, 'raw': raw, 'active': active, 'dependency': name,
                           'disposition': 'SATISFIED_FIXED_FIVE' if active else 'INACTIVE_MARKER_NO_EXTRA_ACTIVATION'})
    return result


def target_scheme(target, get_paths=sysconfig.get_paths):
    # Explicit --prefix is decisive on CPython3.12 -S, where sys.prefix is base.
    target = Path(target).absolute()
    paths = get_paths(vars={'base': str(target), 'platbase': str(target)})
    expected = target/'lib/python3.12/site-packages'
    need(Path(paths['purelib']) == expected and Path(paths['platlib']) == expected
         and Path(paths['scripts']) == target/'bin' and Path(paths['data']) == target, 'TARGET_INSTALL_SCHEME')
    return {k: paths[k] for k in ('purelib', 'platlib', 'scripts', 'data')}


def pip_arguments(stage, target, requirements):
    base = ['pip', '--isolated', '--disable-pip-version-check', '--no-input']
    if stage == 'install':
        wheel_dir = Path(requirements).parent.parent/Path(P1_SCOPE).name/'wheels'
        return base + ['install', '--prefix', str(target), '--ignore-installed', '--no-index',
            '--find-links', str(wheel_dir), '--no-deps',
            '--no-compile', '--no-cache-dir', '--only-binary=:all:', '--require-hashes', '-r', str(requirements)]
    need(stage == 'check', 'PIP_STAGE')
    return base + ['--no-cache-dir', 'check']


def installed_metadata(site):
    site = Path(site)
    found, requirements = {}, {}
    for dist in importlib.metadata.distributions(path=[str(site)]):
        name = normalize(dist.metadata.get('Name', ''))
        need(name not in found and name in VERSIONS and dist.version == VERSIONS[name], 'INSTALLED_IDENTITIES')
        found[name] = dist.version
        requirements[name] = list(dist.requires or [])
    need(found == VERSIONS, 'INSTALLED_IDENTITIES')
    return {'versions': found, 'closure': dependency_closure(requirements)}


def verify_bootstrap(root, methods, reader):
    binding = json_body(reader.read(methods['installer_binding_ref']))
    need(binding.get('kind') == 'E01_INSTALLER_BINDING_V1' and binding.get('pip_version') == '25.0.1'
         and binding.get('target') == {'python': '3.12.14', 'OS': 'macOS', 'architecture': 'arm64'}, 'BOOTSTRAP_IDENTITY')
    base = Path(binding['base_prefix'])
    need(base.is_absolute() and binding['executable_ref']['path'] == str(base/'bin/python3.12'), 'BASE_INTERPRETER_PATH')
    reader.read(binding['executable_ref'], absolute=True)
    pip_root = relative(root, binding['pip_root'])
    need(binding['pip_root'] == '.venv/lib/python3.12/site-packages/pip', 'PIP_ROOT')
    files = binding['pip_files']
    need(type(files) is dict and 3 <= len(files) <= 4094, 'PIP_MANIFEST')
    observed, directories = set(), 0
    for parent, dirs, names in os.walk(pip_root, followlinks=False):
        directories += 1
        need(directories <= 4096, 'PIP_DIRECTORY_CAP')
        for name in dirs: no_alias(Path(parent)/name)
        for name in names:
            path = Path(parent)/name; no_alias(path)
            need(path.is_file(), 'PIP_FILE_TYPE')
            observed.add(str(path.relative_to(root)))
            need(len(observed) <= 4094, 'PIP_FILE_CAP')
    need(observed == set(files), 'PIP_MANIFEST_MEMBERSHIP')
    counts = binding.get('counts')
    need(type(counts) is dict and counts.get('files') == len(files)+2
         and counts.get('directories') == directories
         and counts.get('total_bytes') == sum(ref['bytes'] for ref in files.values())+
             binding['pip_metadata_ref']['bytes']+binding['executable_ref']['bytes'], 'BOOTSTRAP_COUNTS')
    for name, ref in files.items():
        need(relative(root, name).is_relative_to(pip_root), 'PIP_MANIFEST_PATH')
        reader.read({'path': name, **ref})
    metadata = BytesParser().parsebytes(reader.read(binding['pip_metadata_ref']))
    need(metadata.get_all('Name') == ['pip'] and metadata.get_all('Version') == ['25.0.1'], 'PIP_METADATA')
    need(all(binding['pip_root']+'/'+name in files
             for name in ('__init__.py', '__main__.py', '__pip-runner__.py')), 'PIP_ENTRYPOINTS')
    return binding


def verify_acquisition(root, methods, packet, reader):
    need(set(packet) == {'kind', 'root_sha256', 'methods_sha256', 'acquisition_terminal_ref', 'hashlock_ref', 'wheels'}
         and packet['kind'] == 'E01_PYPDF701_INSTALL_PACKET_V1'
         and packet['root_sha256'] == methods['root_sha256']
         and packet['methods_sha256'] == sha(packed(methods)), 'PACKET_IDENTITY')
    scope = methods['acquisition_scope']
    need(scope == P1_SCOPE and packet['acquisition_terminal_ref']['path'] == scope+'/TERMINAL.json'
         and packet['hashlock_ref']['path'] == scope+'/hashlock.json', 'ACQUISITION_PATHS')
    terminal = json_body(reader.read(packet['acquisition_terminal_ref']))
    lock = json_body(reader.read(packet['hashlock_ref']))
    p1_methods_raw = reader.read(methods['acquisition_methods_ref'])
    p1_methods = json_body(p1_methods_raw)
    need(sha(p1_methods_raw) == sha(packed(p1_methods)), 'P1_METHODS_CANONICAL')
    need(terminal.get('kind') == 'P1_TERMINAL_V1_3'
         and terminal.get('status') == 'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION'
         and terminal.get('reason') is None and terminal.get('current_request') is None
         and terminal.get('no_retry') is True and terminal.get('installation') is False
         and terminal.get('package_imports') is False and terminal.get('model_calls') == 0, 'P1_COMPLETE_REQUIRED')
    need(terminal.get('previous_scope') == p1_methods['previous_scope']
         and terminal.get('previous_terminal_ref') == p1_methods['previous_refs']['TERMINAL.json']
         and terminal.get('prior_cumulative') == p1_methods['prior_cumulative'], 'P1_ANCESTRY')
    previous_methods = json_body(reader.read(p1_methods['previous_methods_ref']))
    previous_bodies = {name: reader.read({'path': p1_methods['previous_scope']+'/'+name, **ref})
                       for name, ref in p1_methods['previous_refs'].items()}
    previous_terminal = json_body(previous_bodies['TERMINAL.json'])
    second_methods = json_body(reader.read(previous_methods['previous_methods_ref']))
    second_bodies = {name: reader.read({'path': previous_methods['previous_scope']+'/'+name, **ref})
                     for name, ref in previous_methods['previous_refs'].items()}
    second_terminal = json_body(second_bodies['TERMINAL.json'])
    ancestor = second_methods['predecessor']
    old_bodies = {name: reader.read({'path': ancestor['scope']+'/'+name, **ref}) for name, ref in ancestor['refs'].items()}
    old_terminal = json_body(old_bodies['TERMINAL.json'])
    need(old_terminal.get('status') == 'FAILED_OR_UNKNOWN_NO_RETRY'
         and old_terminal.get('reason') == 'ADVISORY_PACKAGE_MISSING' and old_terminal.get('budget') == ancestor['budget'], 'ANCESTOR_FAILURE_EVIDENCE')
    need(sum(map(len, old_bodies.values())) == ancestor['owned_bytes'], 'ANCESTOR_WRITE_ACCOUNTING')
    need(second_terminal.get('kind') == 'P1_TERMINAL_V1_1'
         and second_terminal.get('status') == 'FAILED_OR_UNKNOWN_NO_RETRY'
         and second_terminal.get('reason') == 'CONTENT_TYPE'
         and second_terminal.get('predecessor') == ancestor
         and second_terminal.get('budget') == previous_methods['prior_cumulative']['budget']
         and second_terminal['budget']['body_bytes_charged']['wheel'] == 16777216, 'SECOND_ANCESTOR_FAILURE_EVIDENCE')
    second_physical = sum(map(len, second_bodies.values()))
    second_metadata = sum(len(raw) for name, raw in second_bodies.items() if name.startswith('metadata/'))
    need(previous_methods['prior_cumulative']['owned_bytes'] == ancestor['owned_bytes']+second_physical
         and previous_methods['prior_cumulative']['control_bytes'] == ancestor['control_bytes']+second_physical-second_metadata,
         'SECOND_ANCESTOR_WRITE_ACCOUNTING')
    need(previous_terminal.get('kind') == 'P1_TERMINAL_V1_2'
         and previous_terminal.get('status') == 'FAILED_OR_UNKNOWN_NO_RETRY'
         and previous_terminal.get('reason') == 'HTTP_FRESHNESS'
         and previous_terminal.get('prior_cumulative') == previous_methods['prior_cumulative']
         and previous_terminal.get('budget') == p1_methods['prior_cumulative']['budget']
         and previous_terminal['budget']['body_bytes_charged']['wheel'] == 33554432, 'THIRD_ANCESTOR_FAILURE_EVIDENCE')
    prior_physical = sum(map(len, previous_bodies.values()))
    prior_raw = sum(len(raw) for name, raw in previous_bodies.items() if name.startswith(('metadata/', 'wheels/')))
    need(p1_methods['prior_cumulative']['owned_bytes'] == previous_methods['prior_cumulative']['owned_bytes']+prior_physical
         and p1_methods['prior_cumulative']['control_bytes'] == previous_methods['prior_cumulative']['control_bytes']+prior_physical-prior_raw,
         'THIRD_ANCESTOR_WRITE_ACCOUNTING')
    refs, bodies = {}, {}
    need(type(terminal['artifacts']) is list and len(terminal['artifacts']) <= 64, 'P1_ARTIFACT_COUNT')
    for ref in terminal['artifacts']:
        need(type(ref) is dict and set(ref) == {'path', 'bytes', 'sha256'} and ref['path'] not in refs, 'P1_ARTIFACT_REFSET')
        refs[ref['path']] = ref
        bodies[ref['path']] = reader.read({**ref, 'path': scope+'/'+ref['path']})
    need(refs.get('hashlock.json') == {**packet['hashlock_ref'], 'path': 'hashlock.json'}, 'HASHLOCK_INDEX')
    started = json_body(bodies['STARTED.json'])
    need(started.get('kind') == 'P1_THIRD_SUCCESSOR_STARTED_NO_RETRY'
         and started.get('methods_sha256') == methods['acquisition_methods_ref']['sha256']
         and started.get('code_sha256') == methods['acquisition_code_sha256']
         and started.get('previous_terminal_ref') == p1_methods['previous_refs']['TERMINAL.json']
         and started.get('prior_cumulative') == p1_methods['prior_cumulative']
         and started.get('historical_original_caps') == p1_methods['historical_original_caps']
         and started.get('cumulative_caps') == p1_methods['caps']
         and started.get('additional_root_authorized_technical_GET') == 1, 'P1_START_BINDING')
    need(lock.get('kind') == 'P1_FIVE_WHEEL_HASHLOCK_V1' and lock.get('schema_version') == 1
         and lock.get('methods_sha256') == started['methods_sha256']
         and lock.get('target') == {'implementation': 'CPython', 'python': '3.12.14', 'architecture': 'arm64',
             'OS': 'macOS', 'macOS_version': '26.6'} and lock.get('ready_for_install') is False
         and lock.get('qualification_or_source_authority') is False
         and lock.get('previous_terminal_sha256') == p1_methods['previous_refs']['TERMINAL.json']['sha256']
         and lock.get('cached_pypdf_ref') == p1_methods['cached_pypdf_ref']
         and lock.get('failed_wheel_GET_charges_retained') == 33554432
         and lock.get('historical_original_GET_cap') == 13 and lock.get('cumulative_root_authorized_GET_cap') == 14, 'P1_HASHLOCK')
    need(terminal['budget']['attempts'] == {'GET': 14, 'metadata_GET': 8, 'wheel_GET': 6}
         and terminal.get('historical_original_GET_cap') == 13 and terminal.get('cumulative_root_authorized_GET_cap') == 14
         and terminal['budget']['outstanding_body_hold'] == 0, 'P1_FINAL_ACCOUNTING')
    assessment = json_body(bodies['advisory-assessment.json'])
    need(sha(bodies['advisory-assessment.json']) == lock['advisory_assessment_sha256']
         and assessment.get('fresh_current_response') is True
         and assessment.get('status') == 'NO_APPLICABLE_ISSUE_IN_CAPTURED_MAINTAINER_PAGES', 'P1_ADVISORY_GATE')
    helper = load_bound_module(root, BASE_REF, 'p2_frozen_p1', reader)
    wheels = lock['wheels']
    need(type(wheels) is list and [w.get('name') for w in wheels] == list(VERSIONS), 'WHEEL_SET')
    requires, identities, entries, inflated = {}, [], 0, 0
    for wheel in wheels:
        name = wheel['name']
        need(wheel['version'] == VERSIONS[name] and wheel.get('yanked') is False, 'WHEEL_VERSION')
        artifact, metadata = wheel['artifact_ref'], wheel['metadata_ref']
        need(refs.get(artifact['path']) == artifact and artifact['path'] == 'wheels/'+wheel['filename']
             and refs.get(metadata['path']) == metadata and metadata['path'] == 'metadata/'+name+'.json', 'WHEEL_REFS')
        raw = bodies[artifact['path']]
        need(len(raw) == wheel['size'] and sha(raw) == wheel['sha256'], 'WHEEL_HASH_SIZE')
        selected = helper.select_wheel(name, helper.json_body(bodies[metadata['path']]))
        need(all(wheel.get(k) == v for k, v in selected.items()), 'WHEEL_METADATA_SELECTION')
        inspection = helper.inspect_wheel(raw, name, wheel['filename'], entries_left=4096-entries,
                                          bytes_left=268435456-inflated)
        need(inspection == wheel['inspection'], 'WHEEL_INSPECTION')
        entries += inspection['entries']; inflated += inspection['uncompressed_bytes']
        requires[name] = inspection['requires_dist']
        identities.append({k: wheel[k] for k in ('name', 'version', 'filename', 'size', 'sha256')})
    need(packet['wheels'] == identities, 'EXTERNAL_FIVE_WHEEL_BINDING')
    need(terminal['budget']['body_bytes_charged']['wheel'] == 33554432+sum(w['size'] for w in wheels[1:])
         and terminal['budget']['body_bytes_charged']['metadata'] == p1_methods['prior_cumulative']['budget']['body_bytes_charged']['metadata'],
         'P1_FINAL_BODY_ACCOUNTING')
    return {'lock': lock, 'identities': identities, 'closure': dependency_closure(requires),
            'inflated_bytes': inflated, 'terminal_sha256': packet['acquisition_terminal_ref']['sha256']}


class GuestPolicy:
    """Trusted installer guard, not an OS sandbox or physical IO meter."""
    def __init__(self, root, binding, payload):
        self.root, self.binding = Path(root), binding
        self.target, self.stage = self.root/TARGET, self.root/OUTPUT
        self.base_lib = Path(binding['base_prefix'])/'lib/python3.12'
        self.pip_root = self.root/binding['pip_root']
        self.exact_reads = {self.root/name for name in binding['pip_files']}
        self.exact_reads.update({self.root/binding['pip_metadata_ref']['path'],
            self.root/'scripts/install_e01_pypdf701_runtime_v1_1.py', self.root/GUARD_REF['path'],
            Path('/System/Library/CoreServices/SystemVersion.plist'), Path('/dev/null')})
        self.exact_reads.update(self.root/P1_SCOPE/('wheels/'+w['filename']) for w in payload['wheels'])
        self.reads = self.writes = self.output = 0
        self.output_limit = payload['remaining_output_bytes']
        self.violations = 0
        self.lock = threading.RLock()
        self.fdguard = None

    def refuse(self, reason):
        self.violations += 1
        raise Refused(reason)

    def owned(self, path):
        return path.is_relative_to(self.target) or path.is_relative_to(self.stage)

    def path(self, value, flags):
        path = Path(value)
        if '..' in path.parts or not path.is_absolute(): self.refuse('GUEST_RAW_PATH')
        writing = flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        if writing:
            if not self.owned(path): self.refuse('GUEST_WRITE_OUTSIDE_OWNED')
        else:
            stdlib = path.is_relative_to(self.base_lib) and not path.is_relative_to(self.base_lib/'site-packages')
            directory = path.is_relative_to(self.pip_root) and path.is_dir()
            if not (self.owned(path) or path in self.exact_reads or stdlib or directory):
                self.refuse('GUEST_READ_OUTSIDE_ALLOWLIST')

    def mutation(self, value, dir_fd=None):
        if type(value) is int: self.refuse('GUEST_UNKNOWN_MUTATION_DESCRIPTOR')
        path = Path(os.fsdecode(value))
        if dir_fd not in (None, -1) and not path.is_absolute():
            path = self.fdguard.directory(dir_fd)[0]/path
        path = self.fdguard.absolute(path)
        self.path(path, os.O_WRONLY)
        self.fdguard.no_alias(path)

    def audit(self, event, args):
        if event.startswith('socket.') or event in {'subprocess.Popen', 'os.fork', 'os.forkpty',
                'os.posix_spawn', 'os.system', 'os.exec', 'os.spawn', 'ctypes.dlopen'}:
            self.refuse('GUEST_NETWORK_HELPER_OR_CTYPES_DENIED')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = self.fdguard.event_path(args[0])
            self.path(path, args[2])
            if not args[2] & os.O_WRONLY:
                try: size = path.stat().st_size
                except FileNotFoundError: size = 0
                with self.lock:
                    self.reads += size+1
                    if self.reads > CAPS['guest_read_bytes_each']: self.refuse('GUEST_READ_CAP')
        if event in {'os.mkdir', 'os.chmod'}:
            self.mutation(args[0], args[2] if len(args)>2 else None)
        if event in {'os.remove', 'os.rmdir'}: self.mutation(args[0], args[1])
        if event == 'os.rename':
            self.mutation(args[0], args[2]); self.mutation(args[1], args[3])
        if event == 'os.symlink':
            self.mutation(args[1], args[2])
            source = Path(os.fsdecode(args[0]))
            if source.is_absolute() and source != Path(self.binding['executable_ref']['path']) and not self.owned(source):
                self.refuse('GUEST_SYMLINK_SOURCE')
            if '..' in source.parts: self.refuse('GUEST_SYMLINK_TRAVERSAL')
        if event == 'shutil.rmtree': self.mutation(args[0], args[1])
        if event in {'os.link', 'os.truncate', 'shutil.copytree'}:
            # No hardlinks or unrestricted tree copying. Pip's own temporary
            # cleanup is allowed only inside the owned tree, via dirfd guard.
            self.refuse('GUEST_UNBOUNDED_MUTATION')

    def charge(self, data, output=False):
        count = len(data.encode('utf8')) if isinstance(data, str) else memoryview(data).nbytes
        with self.lock:
            if output:
                self.output += count
                if self.output > self.output_limit: self.refuse('GUEST_OUTPUT_CAP')
            else:
                self.writes += count
                if self.writes > CAPS['guest_cumulative_write_bytes_each']: self.refuse('GUEST_WRITE_CAP')


class ChargedFile:
    def __init__(self, stream, policy, output=False): self.stream, self.policy, self.output = stream, policy, output
    def __getattr__(self, name): return getattr(self.stream, name)
    def __enter__(self): self.stream.__enter__(); return self
    def __exit__(self, *args): return self.stream.__exit__(*args)
    def __iter__(self): return self
    def __next__(self): return next(self.stream)
    def write(self, data): self.policy.charge(data, self.output); return self.stream.write(data)
    def writelines(self, items):
        for item in items: self.write(item)
    def truncate(self, *_): self.policy.refuse('GUEST_TRUNCATE_DENIED')


class DownloadedImportGuard(importlib.abc.MetaPathFinder):
    def __init__(self, policy): self.policy = policy
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED_IMPORTS:
            self.policy.refuse('DOWNLOADED_PACKAGE_IMPORT_DENIED')


def install_guest_guard(root, binding, payload):
    import builtins
    helper = load_bound_module(root, GUARD_REF, 'p2_reviewed_dirfd_guard')
    policy = GuestPolicy(root, binding, payload)
    guard = helper.DirectoryFdGuard(policy.path)
    policy.fdguard = guard
    sys.meta_path.insert(0, DownloadedImportGuard(policy))
    sys.addaudithook(policy.audit)
    os.open, os.close = guard.open, guard.close
    def wrap(original):
        def opening(*args, **kwargs):
            stream = original(*args, **kwargs)
            return stream if isinstance(stream, ChargedFile) else ChargedFile(stream, policy)
        return opening
    builtins.open, io.open, os.fdopen = wrap(builtins.open), wrap(io.open), wrap(os.fdopen)
    raw_write = os.write
    def write(fd, body):
        policy.charge(body, fd in {1, 2})
        return raw_write(fd, body)
    os.write = write
    sys.stdout, sys.stderr = ChargedFile(sys.stdout, policy, True), ChargedFile(sys.stderr, policy, True)
    return policy


def run_pip(binding, stage, root):
    target, site = root/TARGET, root/SITE
    target_scheme(target)
    original = list(sys.path)
    need(not any('site-packages' in p for p in original), 'BASE_OR_OLD_SITE_ON_PATH')
    # Public package loading isolates pip without placing its parent oldsite on
    # sys.path. Vendored imports resolve beneath pip.__path__, not oldpackages.
    pip_root = root/binding['pip_root']
    spec = importlib.util.spec_from_file_location('pip', pip_root/'__init__.py',
                                                submodule_search_locations=[str(pip_root)])
    module = importlib.util.module_from_spec(spec)
    sys.modules['pip'] = module
    spec.loader.exec_module(module)
    need(module.__version__ == '25.0.1', 'PIP_LOADED_VERSION')
    sys.path[:] = [str(site)] + original
    before = installed_metadata(site) if stage == 'check' else None
    old_args = sys.argv
    sys.argv = pip_arguments(stage, target, root/OUTPUT/'requirements.txt')
    try:
        try: runpy.run_module('pip', run_name='__main__', alter_sys=True)
        except SystemExit as exc: need(exc.code in (None, 0), 'PIP_NONZERO_EXIT')
    finally:
        sys.argv = old_args
    need(sys.path[0] == str(site) and str(pip_root.parent) not in sys.path, 'PIP_OLD_SITE_EXPOSED')
    return before if stage == 'check' else None


def guest_main(args):
    need(Path.cwd().absolute() == ROOT and sys.version.split()[0] == '3.12.14', 'GUEST_HOST')
    path = relative(ROOT, OUTPUT+'/'+args.guest+'-payload.json')
    need(Path(args.payload).absolute() == path, 'GUEST_PAYLOAD_PATH')
    no_alias(path)
    raw = path.read_bytes()
    need(len(raw) <= 1048576 and sha(raw) == args.payload_sha256, 'GUEST_PAYLOAD_HASH')
    payload = json_body(raw)
    need(payload['root_sha256'] == sha(str(ROOT).encode()) and payload['target'] == TARGET
         and payload['stage'] == args.guest and payload['code_sha256'] == sha(Path(__file__).read_bytes()), 'GUEST_PAYLOAD_IDENTITY')
    remaining = payload.get('remaining_wall_seconds')
    need(type(remaining) in {int, float} and 0 < remaining <= 120, 'GUEST_REMAINING_WALL')
    def deadline(*_): raise Refused('GUEST_REMAINING_WALL_LIMIT')
    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, remaining)
    binding = json_body(Reader(ROOT).read(payload['binding_ref']))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (7, 8))
    resource.setrlimit(resource.RLIMIT_FSIZE, (67108864, 67108864))
    policy = install_guest_guard(ROOT, binding, payload)
    scheme = target_scheme(ROOT/TARGET)
    metadata = None
    if args.guest == 'venv':
        need(not (ROOT/TARGET).exists(), 'GUEST_TARGET_EXISTS')
        venv.EnvBuilder(with_pip=False, symlinks=True, system_site_packages=False).create(ROOT/TARGET)
    else:
        metadata = run_pip(binding, args.guest, ROOT)
    need(policy.violations == 0, 'GUEST_CAUGHT_VIOLATION')
    result = {'kind': 'P2_GUEST_COMPLETE', 'stage': args.guest, 'target_scheme': scheme,
              'observed_sys_prefix': sys.prefix, 'explicit_prefix': str(ROOT/TARGET),
              'pip_helper_descendants_permitted': 0, 'guard_violations': 0,
              'read_open_bytes_charged': policy.reads, 'write_bytes_precharged': policy.writes,
              'metadata_only': metadata, 'downloaded_package_imports': False}
    output = ROOT/OUTPUT/(args.guest+'-guest-result.json')
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(packed(result)); stream.flush(); os.fsync(stream.fileno())
    return 0


def owned_size(root):
    total = count = 0
    for tree in (root/OUTPUT, root/TARGET):
        if not tree.exists(): continue
        no_alias(tree)
        for parent, dirs, names in os.walk(tree, followlinks=False):
            for name in dirs+names:
                path = Path(parent)/name
                info = path.lstat()
                count += 1
                need(count <= CAPS['tree_entries'], 'OWNED_ENTRY_CAP')
                if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode): total += info.st_size
                else: need(stat.S_ISDIR(info.st_mode), 'OWNED_SPECIAL_FILE')
                need(total <= CAPS['owned_logical_bytes'], 'OWNED_LOGICAL_BYTES_CAP')
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
        need(now-self.started < 120, 'P2_WALL_LIMIT')
        usage = resource.getrusage(resource.RUSAGE_SELF)
        observed = usage.ru_utime+usage.ru_stime+self.reaped_cpu
        need(observed < 40, 'P2_OBSERVED_AGGREGATE_CPU_LIMIT')
        self.max_owned = max(self.max_owned, owned_size(self.root))
        return observed


class Journal:
    def __init__(self, root): self.root, self.bytes, self.refs = root, 0, []
    def save(self, name, obj):
        raw = obj if type(obj) is bytes else packed(obj)
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
                need(now >= budget.prior and now-budget.started < 120, 'P2_COMMAND_DEADLINE')
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


def verify_new_interpreter(root, binding, reader):
    target = root/TARGET
    interpreter = target/'bin/python'
    need(interpreter.resolve(strict=True) == Path(binding['executable_ref']['path']), 'NEW_INTERPRETER_IDENTITY')
    reader.read(binding['executable_ref'], absolute=True)
    cfg = target/'pyvenv.cfg'
    no_alias(cfg)
    need(cfg.stat().st_size <= 4096, 'NEW_VENV_CFG_SIZE')
    text = cfg.read_text()
    need('include-system-site-packages = false' in text
         and 'home = '+str(Path(binding['base_prefix'])/'bin') in text, 'NEW_VENV_CONFIG')


def validate_methods(root, methods):
    need(methods.get('kind') == 'E01_PYPDF701_OFFLINE_INSTALL_METHODS_V1_1'
         and methods.get('schema_version') == 1 and methods.get('caps') == CAPS
         and methods.get('target') == TARGET and methods.get('new_site') == SITE
         and methods.get('output') == OUTPUT and methods.get('versions') == VERSIONS
         and methods.get('root_sha256') == sha(str(root).encode())
         and methods.get('base_acquisition_code_ref') == BASE_REF
         and methods.get('dirfd_guard_ref') == GUARD_REF, 'P2_METHODS_IDENTITY')


def execute(root, methods, packet, *, launcher=run_command, clock=time.monotonic):
    root = Path(root).absolute()
    validate_methods(root, methods)
    for path in (root/OUTPUT, root/TARGET):
        no_alias(path)
        need(not path.exists(), 'P2_ALREADY_CONSUMED')
    reader, budget = Reader(root), StageBudget(root, clock)
    binding = verify_bootstrap(root, methods, reader)
    evidence = verify_acquisition(root, methods, packet, reader)
    need(2*evidence['inflated_bytes'] + binding['executable_ref']['bytes'] + 33554432
         <= CAPS['owned_logical_bytes'], 'OWNED_PREFLIGHT_UPPER_BOUND')
    budget.check()
    scope = root/OUTPUT
    scope.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    scope.mkdir(mode=0o700, exist_ok=False)
    fd = os.open(scope.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    journal = Journal(root)
    journal.save('STARTED.json', {'kind': 'P2_STARTED_NO_RETRY', 'methods_sha256': sha(packed(methods)),
        'packet_sha256': sha(packed(packet)), 'code_sha256': sha(Path(__file__).read_bytes()),
        'caps': CAPS, 'binding_ref': methods['installer_binding_ref'], 'actual_installation_started': False})
    status, reason, stage = 'FAILED_PARTIAL_ENV_NO_RETRY', None, 'PREPARE'
    results = []
    try:
        for name in ('tmp', 'home'): (scope/name).mkdir(mode=0o700)
        requirements = ''.join(f"{w['name']}=={w['version']} --hash=sha256:{w['sha256']}\n" for w in evidence['identities'])
        journal.save('requirements.txt', requirements.encode())
        journal.save('dependency-preflight.json', evidence['closure'])
        environment = {'HOME': str(scope/'home'), 'TMPDIR': str(scope/'tmp'),
            'PATH': str(Path(binding['base_prefix'])/'bin')+':/usr/bin:/bin', 'PIP_CONFIG_FILE': os.devnull,
            'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C', 'LANG': 'C'}
        for number, stage in enumerate(('venv', 'install', 'check'), 1):
            budget.check()
            need(budget.commands < 3, 'P2_COMMAND_COUNT')
            payload = {'root_sha256': methods['root_sha256'], 'target': TARGET, 'stage': stage,
                'code_sha256': sha(Path(__file__).read_bytes()), 'binding_ref': methods['installer_binding_ref'],
                'wheels': evidence['identities'], 'remaining_output_bytes': CAPS['command_output_bytes']-budget.output,
                'remaining_wall_seconds': 120-(budget.clock()-budget.started)}
            payload_ref = journal.save(stage+'-payload.json', payload)
            executable = binding['executable_ref']['path'] if stage == 'venv' else str(root/TARGET/'bin/python')
            command = [executable, '-I', '-B', '-S', str(root/'scripts/install_e01_pypdf701_runtime_v1_1.py'),
                '--guest', stage, '--payload', str(scope/payload_ref['path']), '--payload-sha256', payload_ref['sha256']]
            journal.save(f'{number}-COMMAND_RESERVED.json', {'kind': 'MAIN_COMMAND_RESERVED', 'number': number,
                'stage': stage, 'argv': command, 'helper_descendants_permitted': 0,
                'CPU_hard_unsettled_upper_bound_seconds': 8, 'remaining_output_bytes': payload['remaining_output_bytes']})
            budget.commands += 1
            try:
                result = launcher(command, environment, root, budget, number)
            except CommandStopped as exc:
                results.append(exc.record)
                journal.save(f'{number}-COMMAND_STOPPED.json', exc.record)
                raise Refused(str(exc)) from None
            results.append(result)
            journal.save(f'{number}-COMMAND_RECORDED.json', result)
            need(result['exit_code'] == 0 and result['pip_helper_descendants_permitted'] == 0, 'P2_COMMAND_FAILED')
            guest_path = scope/(stage+'-guest-result.json')
            no_alias(guest_path)
            need(guest_path.stat().st_size <= 262144, 'GUEST_RESULT_SIZE')
            receipt = json_body(guest_path.read_bytes())
            need(receipt.get('kind') == 'P2_GUEST_COMPLETE' and receipt.get('stage') == stage
                 and receipt.get('guard_violations') == 0 and receipt.get('downloaded_package_imports') is False
                 and receipt.get('explicit_prefix') == str(root/TARGET), 'GUEST_RECEIPT')
            need(receipt.get('target_scheme') == {'purelib': str(root/SITE), 'platlib': str(root/SITE),
                 'scripts': str(root/TARGET/'bin'), 'data': str(root/TARGET)}, 'GUEST_TARGET_SCHEME')
            if stage == 'venv': verify_new_interpreter(root, binding, reader)
        metadata = installed_metadata(root/SITE)
        journal.save('installed-metadata-only.json', metadata)
        # Rehash the complete original pip/base binding; no mutation is allowed.
        verify_bootstrap(root, methods, reader)
        budget.check()
        status = 'OFFLINE_INSTALL_COMPLETE_NOT_RUNTIME_QUALIFICATION'
    except BaseException as exc:
        reason = str(exc) if type(exc) is Refused else type(exc).__name__
    finally:
        journal.save('TERMINAL.json', {'kind': 'P2_TERMINAL_V1', 'status': status, 'reason': reason,
            'stage': stage, 'commands_started': budget.commands, 'results': results,
            'parent_bound_reference_read_bytes_charged': reader.charged, 'captured_command_output_bytes': budget.output,
            'reaped_child_CPU_seconds': budget.reaped_cpu,
            'observed_self_and_reaped_CPU_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime+
                resource.getrusage(resource.RUSAGE_SELF).ru_stime+budget.reaped_cpu,
            'maximum_polled_owned_logical_bytes': budget.max_owned, 'artifacts': journal.refs,
            'pip_helper_descendants_permitted': 0, 'network_model_calls': 0, 'cost_USD': 0,
            'downloaded_package_imports': False, 'runtime_or_source_qualification': False,
            'no_retry': True, 'partial_environment_preserved': status.startswith('FAILED')})
    return {'status': status, 'reason': reason, 'commands_started': budget.commands,
            'network_model_calls': 0, 'cost_USD': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--methods-sha256')
    parser.add_argument('--packet-sha256')
    parser.add_argument('--guest', choices=('venv', 'install', 'check'))
    parser.add_argument('--payload'); parser.add_argument('--payload-sha256')
    args = parser.parse_args()
    if args.guest: return guest_main(args)
    need(args.methods_sha256 and args.packet_sha256 and Path.cwd().absolute() == ROOT, 'P2_CLI_BINDING_REQUIRED')
    need(sys.version.split()[0] == '3.12.14' and sys.implementation.name == 'cpython'
         and sys.platform == 'darwin' and platform.machine() == 'arm64'
         and platform.mac_ver()[0] == '26.6', 'P2_HOST_RUNTIME')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); resource.setrlimit(resource.RLIMIT_CPU, (7, 8))
    def deadline(*_): raise Refused('P2_DEADLINE_SIGNAL')
    signal.signal(signal.SIGALRM, deadline); signal.signal(signal.SIGXCPU, deadline)
    signal.setitimer(signal.ITIMER_REAL, 120)
    def deny_network(event, _):
        if event.startswith('socket.'): raise Refused('P2_PARENT_NETWORK_DENIED')
    sys.addaudithook(deny_network)
    path = ROOT/METHODS
    no_alias(path)
    need(path.stat().st_size <= 65536, 'METHODS_SIZE')
    raw = path.read_bytes()
    need(sha(raw) == args.methods_sha256, 'METHODS_HASH')
    methods = json_body(raw); need(packed(methods) == raw, 'METHODS_CANONICAL')
    path = relative(ROOT, methods['packet'])
    no_alias(path)
    need(path.stat().st_size <= 65536, 'PACKET_SIZE')
    raw = path.read_bytes()
    need(sha(raw) == args.packet_sha256, 'PACKET_HASH')
    packet = json_body(raw); need(packed(packet) == raw, 'PACKET_CANONICAL')
    result = execute(ROOT, methods, packet)
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(packed(result).decode())
    return 0 if result['status'].startswith('OFFLINE_INSTALL_COMPLETE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
