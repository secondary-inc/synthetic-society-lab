"""Conditional exact-source bootstrap. TEST_ONLY realms cannot enter production."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import threading
import time

from ..common import canonical_hash
from .national_budget import Blocked
from .full_adult_types_v1_2 import strict_json
from .f_actual_admission_v1_1 import detached

ROOT = Path(__file__).resolve().parents[3]
CONFIG = 'configs/e02_F_WY_ACTUAL_BOOTSTRAP_IMPLEMENTATION_v1.json'
_PROD = object()
_TEST = object()
_CONTEXT = object()
_TEST_ROOTS = set()
_NATIVE_LOCK = threading.RLock()


@dataclass(frozen=True)
class Realm:
    root: Path
    tag: str
    token: object


def make_test_realm(root):
    root = Path(root).resolve()
    if root == ROOT or root.is_relative_to(ROOT/'data/raw'):
        raise Blocked('not an isolated new test realm')
    root.mkdir(exist_ok=False)
    (root/'.TEST_ONLY_ACTUAL_WIRING').write_text('TEST_ONLY_GENERATED_INPUTS_NO_REAL_AUTHORITY\n')
    _TEST_ROOTS.add(root)
    return Realm(root, 'TEST_ONLY', _TEST)


def _realm(r):
    if type(r) is not Realm or type(r.root) is not type(ROOT):
        raise Blocked('fixed realm required')
    if r.tag == 'PRODUCTION' and r.token is _PROD and r.root == ROOT:
        return r
    if r.tag == 'TEST_ONLY' and r.token is _TEST and r.root != ROOT and r.root in _TEST_ROOTS:
        p = r.root/'.TEST_ONLY_ACTUAL_WIRING'
        if not p.is_symlink() and p.read_text() == 'TEST_ONLY_GENERATED_INPUTS_NO_REAL_AUTHORITY\n':
            return r
    raise Blocked('realm identity mismatch')


def _metadata(r, relative, expected=None):
    r = _realm(r)
    if type(relative) is not str:
        raise Blocked('metadata path type')
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0] not in ('configs','reports','src','tests','docs'):
        raise Blocked('metadata outside admitted domain')
    cursor = r.root
    for part in p.parts:
        cursor = cursor/part
        if cursor.is_symlink(): raise Blocked('metadata symlink')
    with cursor.open('rb') as f: data = f.read(8*1024**2+1)
    if len(data)>8*1024**2 or expected is not None and hashlib.sha256(data).hexdigest()!=expected:
        raise Blocked('metadata bytes changed/oversized')
    return data


def _ref(r, ref):
    if type(ref) is not dict or set(ref) != {'path','sha256'}:
        raise Blocked('closed metadata reference required')
    return detached(strict_json(_metadata(r, ref['path'], ref['sha256'])))


def _output(r, name, prefix):
    if type(name) is not str or not name.startswith(prefix) or Path(name).is_absolute() or '..' in Path(name).parts:
        raise Blocked('exact output domain')
    return r.root/name  # lexical only; never resolve the source path here.


def _manifest(native, source):
    m = {'origin':'ACTUAL_WY_EXACT_LOCAL_V1','period':native['period'],'state':'56',
         'archive_bytes':source['archive']['bytes'],'archive_sha256':source['archive']['sha256'],
         'person':source['person_member']['name'],'companion':source['companion']['name'],
         'header_bytes':source['header']['bytes'],'header_sha256':source['header']['sha256'],
         'columns':285,'expected_rows':source['person_member']['expected_all_age_rows'],
         'metadata_hashes':native['metadata_hashes'],'parent_provenance':native['parent_provenance'],
         'expected_identity':None,'members':[]}
    for x in source['literal_members']:
        m['members'].append({'name':x['name'],'bytes':x['declared_uncompressed_bytes'],
                             'compressed_bytes':x['compressed_bytes'],'crc32':x['crc32'],
                             'sha256':source['person_member']['sha256'] if x['name']==m['person'] else source['companion']['sha256']})
    return m


def _load(r, config):
    # Deny null/test production authority BEFORE metadata or source filesystem work.
    config = detached(config)
    if type(config) is not dict or type(config.get('actual_authority')) is not int or config['actual_authority'] != 1 or config.get('realm') != r.tag:
        raise Blocked('exact live inspection authority absent/wrong realm')
    refs = config.get('live_refs')
    if type(refs) is not dict or set(refs) != {'implementation_manifest','implementation_review','inspection'} or any(type(v) is not dict for v in refs.values()):
        raise Blocked('implementation/inspection references absent')
    r = _realm(r)
    base = detached(strict_json(_metadata(r, CONFIG)))
    excluded = {'actual_authority','live_refs'}
    design = {k:v for k,v in config.items() if k not in excluded}
    if base.get('actual_authority') != 0 or any(v is not None for v in base['live_refs'].values()) or design != {k:v for k,v in base.items() if k not in excluded}:
        raise Blocked('fixed adapter design changed')
    M = canonical_hash(design)
    for name, expected in config['implementation_files'].items(): _metadata(r, name, expected)
    native = detached(strict_json(_metadata(r, 'configs/e02_F_WY_LOCAL_IMPLEMENTATION_v1_1.json', config['native_config_sha256'])))
    for name, expected in native['required_files'].items(): _metadata(r, name, expected)
    source_bytes = _metadata(r, native['proposal'], native['required_files'][native['proposal']])
    source = detached(strict_json(source_bytes)['source'])
    if native['limits'] != config['native_limits'] or native['storage'] != config['native_storage']:
        raise Blocked('native caps mismatch')
    D = canonical_hash({k:v for k,v in native.items() if k not in ('actual_authority','actual_approvals','scope')})
    A = _ref(r, refs['implementation_manifest']); review = _ref(r, refs['implementation_review']); I = _ref(r, refs['inspection'])
    common = {'realm':r.tag,'adapter_design_sha256':M,'native_design_sha256':D,
              'source_contract_sha256':hashlib.sha256(source_bytes).hexdigest()}
    for record in (A,review,I):
        if any(record.get(k)!=v for k,v in common.items()): raise Blocked('authority realm/design/source mismatch')
    if A.get('status') != 'IMPLEMENTATION_BINDING_NOT_PERMISSION' or A.get('files') != config['implementation_files']:
        raise Blocked('implementation manifest mismatch')
    if review.get('status') != 'PASS_F_WY_ACTUAL_BOOTSTRAP_IMPLEMENTATION_AND_AUTHORED_FIXTURES' or review.get('auditor_role') != 'independent_auditor' or review.get('implementation_manifest_sha256') != refs['implementation_manifest']['sha256']:
        raise Blocked('independent actual adapter review absent')
    if I.get('status') != 'APPROVE_F_WY_BOUNDED_EXACT_LOCAL_INSPECTION' or I.get('auditor_role') != 'independent_auditor' or I.get('implementation_manifest_sha256') != refs['implementation_manifest']['sha256'] or I.get('implementation_review_sha256') != refs['implementation_review']['sha256']:
        raise Blocked('distinct fresh inspection scope absent')
    expected_scope = {'repository_root':str(r.root),'source_path':source['archive']['path'],'control_directory':config['control_directory'],
                      'output_directory':config['output_directory'],'GETs':0,'model_calls':0,'person_rows':0,
                      'fit':False,'disclosure':False,'single_use':True}
    if canonical_hash(I.get('scope')) != canonical_hash(expected_scope) or type(I.get('source_authorization_reference')) is not str or not I['source_authorization_reference'].strip():
        raise Blocked('genuine exact source scope reference required')
    if config['resource_envelope'] != envelope(source,native['limits']) or I.get('resource_envelope') != config['resource_envelope']:
        raise Blocked('exact six-stage scope required')
    for name in ('not_before','expires'):
        if type(I.get(name)) not in (int,float): raise Blocked('finite scope time required')
    if not I['not_before'] <= time.time() < I['expires']:
        raise Blocked('inspection scope expired/not active')
    relative = Path(source['archive']['path'])
    if relative.is_absolute() or '..' in relative.parts or relative.parts[:3] != ('data','raw','e02_pums_wy'):
        raise Blocked('fixed source path domain')
    return {'config':config,'native':native,'source':source,'manifest':_manifest(native,source),
            'M':M,'D':D,'I':I,'A':A,'refs':refs,'realm':r.tag}


@dataclass(frozen=True)
class InspectionContext:
    realm: Realm
    spec_json: str
    binding_json: str
    token: object
    @property
    def binding(self): return strict_json(self.binding_json)
    @property
    def config(self): return self.binding['native']
    @property
    def manifest(self): return self.binding['manifest']
    @property
    def control_root(self): return self.realm.root/self.binding['config']['control_directory']
    @property
    def runtime_root(self): return self.realm.root/self.binding['config']['output_directory']
    @property
    def path(self): return self.realm.root/self.binding['source']['archive']['path']


def _admit(r, config):
    try: binding = _load(r, config)
    except (OSError,ValueError,TypeError,KeyError): raise Blocked('inspection admission metadata incomplete') from None
    _output(r,binding['config']['control_directory'],'data/processed/e02_F_wy_private_bootstrap/')
    _output(r,binding['config']['output_directory'],'data/processed/e02_F_wy_private/')
    return InspectionContext(r,json.dumps(detached(config),sort_keys=True),json.dumps(binding,sort_keys=True),_CONTEXT)


def admit_inspection(config=None): return _admit(Realm(ROOT,'PRODUCTION',_PROD),config)
def admit_test_inspection(realm,config=None):
    if type(realm) is not Realm or realm.tag != 'TEST_ONLY' or realm.token is not _TEST: raise Blocked('test realm required')
    return _admit(realm,config)


def require_context(c):
    if type(c) is not InspectionContext or c.token is not _CONTEXT or type(c.spec_json) is not str or type(c.binding_json) is not str:
        raise Blocked('minted actual inspection context required')
    try:
        current=_load(c.realm,strict_json(c.spec_json))
    except (OSError,ValueError,TypeError,KeyError):
        raise Blocked('context authority metadata unavailable') from None
    if current != c.binding:
        raise Blocked('context differs from current bound authority')
    return c


@contextmanager
def native_session(c):
    c = require_context(c)
    from . import f_actual_admission_v1_1 as native
    with _NATIVE_LOCK:
        old = native.ROOT
        if c.realm.tag == 'PRODUCTION' and old != ROOT:
            raise Blocked('production native root mismatch')
        if c.realm.tag == 'TEST_ONLY': native.ROOT=c.realm.root
        try: yield
        finally: native.ROOT=old


def inspect_authorized(context):
    from .f_wy_actual_bootstrap_launcher_v1 import run_inspection
    return run_inspection(require_context(context))

import csv
import io
import os
import stat
import zipfile
import zlib
from .f_wy_bootstrap_v1_1 import _open_no_follow, _identity, _header_only

def _inspect_reserved(context, control):
    b = require_context(context)
    if control.b.binding != b.binding:
        raise Blocked('inspection control mismatch')
    state = control.snapshot()
    if state['stages'].get('INSPECT', {}).get('status') != 'PENDING' or state['failed'] or state['shutdown'] != 'ACTIVE':
        raise Blocked('durable original INSPECT reservation required')
    control.storage()
    m = b.manifest; c = b.config
    stream, directory, initial_chain = _open_no_follow(b.path)
    try:
        with stream:
            before = _identity(os.fstat(stream.fileno()))
            if before['bytes'] != m['archive_bytes'] or before['bytes'] > c['limits']['archive_body_bytes']:
                raise Blocked('archive size mismatch')
            h = hashlib.sha256(); n = 0
            while True:
                chunk = stream.read(min(65536, m['archive_bytes'] - n + 1))
                if not chunk: break
                n += len(chunk)
                if n > m['archive_bytes']: raise Blocked('archive delivered bound')
                h.update(chunk)
            if n != m['archive_bytes'] or h.hexdigest() != m['archive_sha256']:
                raise Blocked('archive bytes/hash mismatch')
            stream.seek(0)
            expected = {x['name']: x for x in m['members']}
            with zipfile.ZipFile(stream) as archive:
                members = archive.infolist()
                if len(members) != 2 or set(x.filename for x in members) != {m['person'], m['companion']} or len({x.filename.casefold() for x in members}) != 2:
                    raise Blocked('exact two literal members required')
                if sum(x.file_size for x in members) > c['limits']['state_uncompressed_bytes']:
                    raise Blocked('declared expansion bound')
                for x in members:
                    e = expected[x.filename]
                    if '/' in x.filename or '\\' in x.filename or x.flag_bits & 1 or stat.S_ISLNK(x.external_attr >> 16) or x.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) or (x.file_size, x.compress_size, x.CRC) != (e['bytes'], e['compressed_bytes'], e['crc32']):
                        raise Blocked('member metadata/compression mismatch')
                companion = expected[m['companion']]
                if companion['bytes'] > c['limits']['companion_bytes']:
                    raise Blocked('companion native bound')
                with archive.open(m['companion']) as f:
                    digest = hashlib.sha256(); expanded = 0
                    while True:
                        data = f.read(min(65536, companion['bytes'] - expanded + 1))
                        if not data: break
                        expanded += len(data)
                        if expanded > companion['bytes']: raise Blocked('companion expansion')
                        digest.update(data)
                if expanded != companion['bytes'] or digest.hexdigest() != companion['sha256']:
                    raise Blocked('companion hash mismatch')
                if m['header_bytes'] > c['limits']['line_bytes']:
                    raise Blocked('header native bound')
                # No extra byte read from CSV, no person-row iteration or full-member CRC scan.
                header = _header_only(stream, archive.getinfo(m['person']), m['header_bytes'], m['archive_bytes'])
                if len(header) != m['header_bytes'] or hashlib.sha256(header).hexdigest() != m['header_sha256'] or not header.endswith(b'\n'):
                    raise Blocked('header hash/length mismatch')
                fields = next(csv.reader(io.StringIO(header.decode('utf-8-sig')), strict=True))
                if len(fields) != 285 or len(set(fields)) != 285 or not set(c['required_fields']).issubset(fields):
                    raise Blocked('header columns mismatch')
            after = _identity(os.fstat(stream.fileno()))
            # Reopen EVERY current lexical ancestor. A stat relative to the old
            # retained parent FD cannot detect that parent being renamed/replaced.
            current_stream, current_directory, current_chain = _open_no_follow(b.path)
            try:
                with current_stream:
                    current_file = _identity(os.fstat(current_stream.fileno()))
                    if current_chain != initial_chain or before != after or current_file != before:
                        raise Blocked('current lexical ancestor/file identity changed')
            finally:
                os.close(current_directory)
    except (OSError, ValueError, zipfile.BadZipFile, UnicodeError, csv.Error, zlib.error):
        raise Blocked('bounded inspection refused') from None
    finally:
        os.close(directory)
    control.storage()
    return {'kind': 'ACTUAL_AUTHORIZED_INSPECTION' if b.realm.tag == 'PRODUCTION' else 'TEST_ONLY_ACTUAL_SHAPED_INSPECTION', 'identity': before, 'archive_sha256': h.hexdigest(),
            'source_manifest_hash': canonical_hash(m), 'archive_bytes_hashed': n,
            'expanded_bytes': len(header) + expanded, 'header_bytes_read': len(header),
            'person_rows_read': 0, 'full_person_crc_scan_performed': False, 'GETs': 0,
            'fixed_lexical_path_reopened': True, 'directory_chain_identity': initial_chain}


def envelope(source, limits):
    expanded=source['header']['bytes']+source['companion']['exact_bytes']
    reserve=limits['line_bytes']+3*limits['companion_bytes']
    parse=source['person_member']['exact_bytes']+2*expanded
    return {'expanded_bytes':2*reserve+2*parse,'rows':2*source['person_member']['expected_all_age_rows'],
            'logical_operations':12000000,'seconds':1800,'stages':6,'stage_seconds':300,'deadline_seconds':10800}


def owned_json(context, path):
    context=require_context(context)
    if path.parent != context.control_root or path.is_symlink(): raise Blocked('fixed owned metadata only')
    with path.open('rb') as f: data=f.read(8*1024**2+1)
    if len(data)>8*1024**2: raise Blocked('owned metadata oversized')
    return strict_json(data)


def observation(context):
    from .f_wy_actual_bootstrap_control_v1 import Control
    c=require_context(context);control=Control(c)
    o=owned_json(c,c.control_root/'observation.local.json')
    expected={'realm':c.realm.tag,'adapter_design_sha256':c.binding['M'],
              'inspection_sha256':c.binding['refs']['inspection']['sha256'],'control_root':str(c.control_root)}
    if any(o.get(k)!=v for k,v in expected.items()): raise Blocked('observation binding mismatch')
    expected_files={'genesis.json','ORIGINAL','inspection-admission.local.json','INSPECT.proof.local.json','post-inspection-state.local.json','events.jsonl'}
    if set(o.get('files',{})) != expected_files or type(o.get('event_prefix_bytes')) is not int or o['event_prefix_bytes']<0:
        raise Blocked('closed observation prefix/files required')
    for name,ref in o['files'].items():
        if Path(name).name!=name: raise Blocked('observation closed file names')
        p=c.control_root/name
        if p.is_symlink(): raise Blocked('observation original symlink')
        blob=p.read_bytes()
        if name=='events.jsonl':blob=blob[:o['event_prefix_bytes']]
        if hashlib.sha256(blob).hexdigest()!=ref:raise Blocked('observation original prefix changed')
    frozen=owned_json(c,c.control_root/'post-inspection-state.local.json')
    if canonical_hash(frozen) != o['post_inspection_state_sha256'] or set(frozen['stages'])!={'INSPECT'} or frozen['failed'] or frozen['shutdown']!='CLOSED' or frozen['t0']!=o['t0']:
        raise Blocked('sealed post-inspection state mismatch')
    prefix=(c.control_root/'events.jsonl').read_bytes()[:o['event_prefix_bytes']]
    reconstructed=owned_json(c,c.control_root/'genesis.json')
    for line in prefix.splitlines():
        row=strict_json(line);reconstructed=control._transition(reconstructed,row['event'],row['payload'])
    if reconstructed != frozen:raise Blocked('observation prefix/state mismatch')
    proof=owned_json(c,c.control_root/'INSPECT.proof.local.json')
    inspected=proof['result']['inspection']
    if inspected['identity'] != o['source_identity'] or inspected['source_manifest_hash'] != canonical_hash(c.manifest) or inspected['person_rows_read']!=0:
        raise Blocked('observed identity does not derive from inspection')
    if control.snapshot()['t0']!=o['t0']: raise Blocked('observation original deadline changed')
    return o


def validate_execution(context, runtime_config):
    c=require_context(context);config=detached(runtime_config)
    with native_session(c):
        from .f_actual_admission_v1_1 import _release
        records,expected=_release(config)
    o=observation(c)
    oh=hashlib.sha256((c.control_root/'observation.local.json').read_bytes()).hexdigest()
    common={'realm':c.realm.tag,'bootstrap_adapter_design_sha256':c.binding['M'],
            'bootstrap_implementation_manifest_sha256':c.binding['refs']['implementation_manifest']['sha256']}
    for record in records.values():
        if any(record.get(k)!=v for k,v in common.items()):raise Blocked('actual execution bootstrap code/realm binding')
    if records['exact_source']['source_identity']!=o['source_identity'] or records['exact_source'].get('observation_sha256')!=oh:
        raise Blocked('S lacks exact new observation')
    e=records['execution']
    more={'inspection_authorization_sha256':c.binding['refs']['inspection']['sha256'],'observation_sha256':oh,
          'post_inspection_state_sha256':o['post_inspection_state_sha256'],
          'control_directory':c.binding['config']['control_directory'],'output_directory':c.binding['config']['output_directory'],
          'bootstrap_adapter_required':True,'resource_envelope':c.binding['config']['resource_envelope'],
          'network_requests_authorized':0,'model_calls_authorized':0,'fit_authorized':False,'disclosure_authorized':False}
    if any(canonical_hash(e.get(k))!=canonical_hash(v) for k,v in more.items()):raise Blocked('E supplemental exact scope mismatch')
    excluded={'actual_authority','actual_approvals','scope'}
    if {k:v for k,v in config.items() if k not in excluded}!={k:v for k,v in c.config.items() if k not in excluded}:
        raise Blocked('runtime config differs from initial native design')
    return config,{'runtime_config_sha256':canonical_hash(config),'execution_sha256':config['actual_approvals']['execution']['sha256'],'observation_sha256':oh}


def admit_execution(context,runtime_config=None):
    from .f_wy_actual_bootstrap_control_v1 import Control
    from ..common import atomic_json
    c=require_context(context);config,release=validate_execution(c,runtime_config);ctl=Control(c)
    # Check deadline and exact original history BEFORE output admission/source work.
    ctl.bind_release(release)
    path=c.control_root/'runtime-config.local.json'
    ctl.storage(extra=2*len(json.dumps(config).encode())+4096)
    if path.exists():raise Blocked('immutable runtime release config')
    atomic_json(path,config)
    return c


def admit_independent_cleanup(context,receipt=None):
    from .f_wy_actual_bootstrap_control_v1 import Control
    c=require_context(context);ctl=Control(c);state=ctl.snapshot();record=_ref(c.realm,detached(receipt))
    required={'status':'PASS_EXACT_BOOTSTRAP_SHUTDOWN_OBSERVATION_ONLY','realm':c.realm.tag,
              'auditor_role':'independent_auditor','inspection_authorization_sha256':c.binding['refs']['inspection']['sha256'],
              'state_sha256':canonical_hash(state),'original_root':str(c.control_root),
              'shutdown_observed':True,'authority_granted':False}
    if any(canonical_hash(record.get(k))!=canonical_hash(v) for k,v in required.items()) or type(record.get('liveness_evidence')) is not str or not record['liveness_evidence']:
        raise Blocked('independent exact cleanup observation required')
    return ctl._record_cleanup({'receipt':detached(receipt)})


def run_authorized(context):
    from .f_wy_actual_bootstrap_launcher_v1 import Launcher
    return Launcher(require_context(context)).run()
