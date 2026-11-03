"""Conditional local Alabama source release; external expected SHA is trusted input.

No owner authentication, network, OCR, rendering or recording. Actual use needs
an independently reviewed particular lead release, not a caller-minted digest.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sys
from civiclab.e01 import alabama_documents_v1 as pure

ADAPTER = 'src/civiclab/e01/alabama_source_release_v1.py'
PURE = 'src/civiclab/e01/alabama_documents_v1.py'
WRAPPER = 'src/civiclab/e01/alabama_recorded_preflight_v1.py'
COMMON = 'src/civiclab/common.py'
CONFIG = 'configs/e01_al_source_release_v1_candidate.json'
CONFIG_SHA = 'fc1084826c2e014ae533d076915dd4b126b596f6010ce0f6c78384e35c0f4099'
CODE_PATHS = {ADAPTER, PURE, WRAPPER, COMMON}
MODES = {'SOURCE_TRANSCRIPTION_ONLY', 'AUDITED_RUNTIME'}
RELEASE_KEYS = {'schema_version', 'mode', 'execution_kind', 'root_sha256', 'source_policy_sha256',
                'source_snapshot_sha256', 'admission_config_sha256', 'code_pins', 'code_review',
                'output_scope', 'visual_pages', 'source_release', 'runtime', 'phase_limit'}
DYNAMIC = {'scope', 'actual_execution_release', 'release_documents', 'transcription', 'independent_transcription_audit'}


def _raw(raw, expected_sha):
    pure.require(type(raw) is bytes and len(raw) <= 131072 and pure.is_hash(expected_sha))
    pure.require(pure.digest(raw) == expected_sha)
    value = pure.closed_snapshot(pure.strict_json(raw))
    pure.require(type(value) is dict and set(value) == RELEASE_KEYS)
    pure.require(type(value['schema_version']) is int and value['schema_version'] == 1)
    pure.require(value['mode'] in MODES and value['execution_kind'] in {'AUTHORED_FIXTURE', 'LOCAL_ACTUAL'})
    pure.require(value['output_scope'] == 'data/processed/runs')
    wanted = {'source_only': 1} if value['mode'] == 'SOURCE_TRANSCRIPTION_ONLY' else {'primary': 1, 'replay': 1}
    pure.require(pure.canonical(value['phase_limit']) == pure.canonical(wanted))
    pure.require(type(value['code_pins']) is dict and set(value['code_pins']) == CODE_PATHS)
    pure.require(all(pure.is_hash(x) for x in value['code_pins'].values()))
    if value['mode'] == 'SOURCE_TRANSCRIPTION_ONLY':
        pure.require(value['source_release'] is None and value['runtime'] is None)
    else:
        pure.require(type(value['source_release']) is dict and type(value['runtime']) is dict)
    return value


def _ref(root, ref, *, area='.', limit=131072):
    pure.require(type(ref) is dict and set(ref) == {'path', 'sha256', 'bytes'})
    pure.require(type(ref['path']) is str and pure.is_hash(ref['sha256']))
    pure.require(type(ref['bytes']) is int and 0 < ref['bytes'] <= limit)
    return pure.bound_file(root, ref['path'], ref['sha256'], limit, area, ref['bytes'], True)


def _root(root, release):
    p = Path(root).absolute()
    pure.require('..' not in p.parts and p.is_dir())
    pure.require(not any(x.is_symlink() for x in (p, *p.parents)))
    pure.require(pure.digest(str(p).encode()) == release['root_sha256'])
    pure.require(Path(__file__).resolve() == p / ADAPTER)
    pure.require(Path(pure.__file__).resolve() == p / PURE)
    common = sys.modules.get('civiclab.common')
    pure.require(common is not None and Path(common.__file__).resolve() == p / COMMON)
    return p


def _runtime(base, runtime):
    pure.require(type(runtime) is dict and set(runtime) == set(base))
    pure.require(runtime['scope'] == 'RELEASED_LOCAL_AL_DOCUMENT_RECONCILIATION_ONLY')
    pure.require(pure.canonical({k: v for k, v in runtime.items() if k not in DYNAMIC}) ==
                 pure.canonical({k: v for k, v in base.items() if k not in DYNAMIC}))
    grant = runtime['actual_execution_release']
    pure.require(type(grant) is dict and set(grant) == set(base['actual_execution_release']))
    pure.require(grant['approved'] is True and all(pure.is_hash(v) for k, v in grant.items() if k != 'approved'))
    pure.require(runtime['transcription']['sha256'] == grant['trusted_private_transcript_sha256'])
    pure.require(runtime['independent_transcription_audit']['sha256'] == grant['independent_literal_transcription_audit_sha256'])
    pure.require([r['role'] for r in runtime['release_documents']] ==
                 ['source_read_authorization', 'runtime_code_acceptance_sha256', 'recorded_preflight_release_sha256'])
    for ref in [runtime['transcription'], runtime['independent_transcription_audit'], *runtime['release_documents']]:
        pure.require(type(ref['path']) is str and pure.is_hash(ref['sha256']))
        pure.require(type(ref['bytes']) is int and 0 < ref['bytes'] <= 65536)
    pure.require(all(r['sha256'] == grant[r['role']] for r in runtime['release_documents']))
    return runtime


def _prepare(root, raw, expected_sha):
    # Caller metadata cannot replace authority once the exact external bytes
    # have been admitted. The expected SHA must originate in the lead release.
    release = _raw(raw, expected_sha)
    root = _root(root, release)
    cfg = pure.closed_snapshot(pure.strict_json(pure.bound_file(root, CONFIG, CONFIG_SHA, 1048576, '.', retain=True)))
    pure.require(release['admission_config_sha256'] == CONFIG_SHA)
    for p, h in cfg['metadata_pins'].items():
        pure.bound_file(root, p, h, 1048576, '.')
    base = pure.closed_snapshot(pure.strict_json(pure.bound_file(root, cfg['base_runtime']['path'], cfg['base_runtime']['sha256'], 1048576, '.', retain=True)))
    for p, h in base['metadata_pins'].items():
        pure.bound_file(root, p, h, 1048576, '.')
    policy = pure.digest(pure.canonical({k: base[k] for k in cfg['fixed_policy_keys']}))
    pure.require(policy == cfg['fixed_policy_sha256'] == release['source_policy_sha256'])
    pure.require(pure.source_snapshot_sha(base) == cfg['source_snapshot_sha256'] == release['source_snapshot_sha256'])
    pure.require(pure.canonical(release['visual_pages']) == pure.canonical(cfg['visual_pages']))
    for p, h in release['code_pins'].items():
        pure.bound_file(root, p, h, 1048576, '.')
    pure.require(release['code_pins'][PURE] == cfg['metadata_pins'][PURE])
    review = pure.strict_json(_ref(root, release['code_review']))
    pure.require(review['status'] == 'PASS_BOUNDED_AL_SOURCE_RELEASE_ADAPTER_WRAPPER_CODE_PRIVACY')
    pure.require(review['scope'] == 'AUTHORED_CODE_PRIVACY_ONLY_NOT_ACTUAL_SOURCE_RELEASE')
    pure.require(pure.canonical(review['reviewed_code_pins']) == pure.canonical(release['code_pins']))
    pure.require(review['source_policy_sha256'] == policy and review['source_snapshot_sha256'] == pure.source_snapshot_sha(base))
    runtime = None
    if release['mode'] == 'AUDITED_RUNTIME':
        source_raw = _ref(root, release['source_release'], area='data/processed')
        prior = _raw(source_raw, release['source_release']['sha256'])
        pure.require(prior['mode'] == 'SOURCE_TRANSCRIPTION_ONLY')
        pure.require(prior['execution_kind'] == release['execution_kind'])
        # Re-admit the earlier particular source-only grant, without reading
        # any source PDF/image. This cannot recurse to a further grant chain.
        _prepare(root, source_raw, release['source_release']['sha256'])
        pure.require(prior['root_sha256'] == release['root_sha256'])
        pure.require(prior['code_pins'] == release['code_pins'])
        runtime = _runtime(base, pure.closed_snapshot(pure.strict_json(_ref(root, release['runtime'], area='data/processed', limit=262144))))
    return root, release, cfg, base, runtime


def _cache(root, base):
    for source in base['sources']:
        pure.bound_file(root, source['path'], source['sha256'], 1048576, 'data/raw', source['bytes'])
    total = 0
    for page in base['pages']:
        total += pure.bound_file(root, page['render_path'], page['render_sha256'], 8388608, 'data/raw')
        pure.require(total <= 394264576)
    pure.require(len(base['sources']) == 5 and len(base['pages']) == 47)


def _inspection(release, base, cfg):
    pages = {(p['source_id'], p['physical_pdf_page_1_based']): p for p in base['pages']}
    allowed = [pages[(x['source_id'], x['physical_pdf_page_1_based'])] for x in cfg['visual_pages']]
    private = {'schema_version': 1, 'scope': 'SOURCE_ONLY_LOCAL_VISUAL_GUIDANCE_NOT_TRANSCRIPTION',
               'source_snapshot_sha256': pure.source_snapshot_sha(base), 'allowed_images': allowed,
               'literal_transcription': None, 'independent_literal_audit': None}
    public = {'schema_version': 1, 'scope': 'CACHED_SOURCE_INTEGRITY_FOR_LOCAL_LITERAL_TRANSCRIPTION_ONLY',
              'source_count': 5, 'physical_page_count': 47, 'permitted_visual_page_count': 11,
              'transcription_created': False, 'literal_audit_completed': False, 'source_adoption': False,
              'accepted_coverage_promoted': False, 'final_ballots_accepted': 0, 'model_calls': 0, 'cost_usd': 0}
    return private, public


@dataclass(frozen=True, repr=False)
class ReleasedResult:
    _private: bytes
    _public: bytes

    def __repr__(self):
        return '<ReleasedALResult local-only; values withheld>'

    def private_payload(self):
        return pure.strict_json(self._private)

    def public_diagnostics(self):
        return pure.strict_json(self._public)


def _materialize(authority, *, verify_cache):
    root, release, cfg, base, runtime = authority
    if release['mode'] == 'SOURCE_TRANSCRIPTION_ONLY':
        if verify_cache:
            _cache(root, base)
        return _inspection(release, base, cfg)
    if verify_cache:
        transcript, audit = pure.verify_inputs(root, runtime, release['code_pins'][PURE])
    else:
        for ref in runtime['release_documents']:
            data = pure.strict_json(_ref(root, {k: v for k, v in ref.items() if k != 'role'}, area='data/processed', limit=65536))
            expected = {'schema_version': 1, 'role': ref['role'], 'status': 'AUTHORED_OR_SEPARATELY_RELEASED_EXACT_SNAPSHOT',
                        'source_snapshot_sha256': pure.source_snapshot_sha(runtime)}
            if ref['role'] == 'runtime_code_acceptance_sha256':
                expected['module_sha256'] = release['code_pins'][PURE]
            pure.require(pure.canonical(data) == pure.canonical(expected))
        transcript = pure.strict_json(_ref(root, runtime['transcription'], area='data/processed', limit=65536))
        audit = pure.strict_json(_ref(root, runtime['independent_transcription_audit'], area='data/processed', limit=65536))
    result = pure._reconcile(runtime, transcript, audit)
    return result.private_payload(), result.public_diagnostics()


def read_released(root, raw, *, expected_sha):
    """Working source-only or audited-runtime path under external exact release."""
    def operation():
        authority = _prepare(root, raw, expected_sha)
        private, public = _materialize(authority, verify_cache=True)
        recheck(root, raw, expected_sha=expected_sha)
        return ReleasedResult(pure.canonical(private), pure.canonical(public))
    return pure.safe(operation)


def recheck(root, raw, *, expected_sha):
    authority = _prepare(root, raw, expected_sha)
    checked_root, release, _, base, runtime = authority
    if release['mode'] == 'SOURCE_TRANSCRIPTION_ONLY':
        _cache(checked_root, base)
    else:
        pure.verify_inputs(checked_root, runtime, release['code_pins'][PURE])


def expected_saved_payloads(root, raw, *, expected_sha):
    """Read-only saved-run semantic check; no source PDF/image I/O or parsing."""
    authority = _prepare(root, raw, expected_sha)
    private, public = _materialize(authority, verify_cache=False)
    return private, public
