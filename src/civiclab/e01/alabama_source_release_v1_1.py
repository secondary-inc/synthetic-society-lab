"""Versioned exact-six office-context release; historical grant is provenance only; external expected SHA is trusted input.

No owner authentication, network, OCR, rendering or recording. Actual use needs
an independently reviewed particular lead release, not a caller-minted digest.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sys
from civiclab.e01 import alabama_documents_v1 as pure
from civiclab.e01 import alabama_office_context_v1_1 as context
from civiclab.e01 import alabama_source_release_v1 as legacy
from civiclab.e01 import alabama_recorded_preflight_v1 as legacy_writer

ADAPTER = 'src/civiclab/e01/alabama_source_release_v1_1.py'
HELPER = 'src/civiclab/e01/alabama_office_context_v1_1.py'
PURE = 'src/civiclab/e01/alabama_documents_v1.py'
WRAPPER = 'src/civiclab/e01/alabama_recorded_preflight_v1_1.py'
COMMON = 'src/civiclab/common.py'
CONFIG = 'configs/e01_al_source_release_v1_1_candidate.json'
CONFIG_SHA = '35f947d6ff32d3229e04ee8f46cd985237fb27e7b1f90f908602b145cf336a01'
CODE_PATHS = {ADAPTER, PURE, WRAPPER, COMMON, HELPER}
MODES = {'AUDITED_RUNTIME_OFFICE_CONTEXT_V1_1'}
RELEASE_KEYS = {'schema_version', 'mode', 'execution_kind', 'root_sha256', 'source_policy_sha256',
                'source_snapshot_sha256', 'admission_config_sha256', 'code_pins', 'code_review',
                'output_scope', 'visual_pages', 'source_release', 'runtime', 'phase_limit', 'office_rule'}
DYNAMIC = {'scope', 'actual_execution_release', 'release_documents', 'transcription', 'independent_transcription_audit'}


def _raw(raw, expected_sha):
    pure.require(type(raw) is bytes and len(raw) <= 131072 and pure.is_hash(expected_sha))
    pure.require(pure.digest(raw) == expected_sha)
    value = pure.closed_snapshot(pure.strict_json(raw))
    pure.require(type(value) is dict and set(value) == RELEASE_KEYS)
    pure.require(type(value['schema_version']) is int and value['schema_version'] == 1)
    pure.require(value['mode'] in MODES and value['execution_kind'] in {'AUTHORED_FIXTURE', 'LOCAL_ACTUAL'})
    pure.require(value['output_scope'] == 'data/processed/runs')
    wanted = {'primary': 1, 'replay': 1}
    pure.require(pure.canonical(value['phase_limit']) == pure.canonical(wanted))
    pure.require(type(value['code_pins']) is dict and set(value['code_pins']) == CODE_PATHS)
    pure.require(all(pure.is_hash(x) for x in value['code_pins'].values()))
    pure.require(type(value['source_release']) is dict and type(value['runtime']) is dict)
    pure.require(type(value['office_rule']) is dict)
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
    pure.require(Path(context.__file__).resolve() == p / HELPER)
    pure.require(Path(legacy.__file__).resolve() == p / legacy.ADAPTER)
    pure.require(Path(legacy_writer.__file__).resolve() == p / legacy.WRAPPER)
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
    pure.require(review['status'] == 'PASS_BOUNDED_AL_OFFICE_CONTEXT_V1_1_CODE_PRIVACY')
    pure.require(review['scope'] == 'AUTHORED_CODE_PRIVACY_ONLY_NOT_ACTUAL_SOURCE_RELEASE')
    pure.require(pure.canonical(review['reviewed_code_pins']) == pure.canonical(release['code_pins']))
    pure.require(review['source_policy_sha256'] == policy and review['source_snapshot_sha256'] == pure.source_snapshot_sha(base))
    pure.require(pure.canonical(release['office_rule']) == pure.canonical(cfg['rule_ref']))
    rule = context.admit_rule(pure.strict_json(_ref(root, release['office_rule'], area='configs')))
    pure.require(context.RULE_SHA == cfg['rule_canonical_sha256'])
    pure.require(rule['fixed_source_policy_sha256'] == policy)
    pure.require(rule['source_snapshot_sha256'] == pure.source_snapshot_sha(base))
    _history(root, release, cfg)
    runtime = _runtime(base, pure.closed_snapshot(pure.strict_json(_ref(root, release['runtime'], area='data/processed', limit=262144))))
    pure.require(pure.canonical(runtime['transcription']) == pure.canonical(cfg['transcript_ref']))
    pure.require(runtime['transcription']['sha256'] == rule['source_transcript_sha256'])
    audit_ref = runtime['independent_transcription_audit']
    pure.require(audit_ref['sha256'] == cfg['accepted_literal_audit_ref']['sha256'])
    pure.require(audit_ref['bytes'] == cfg['accepted_literal_audit_ref']['bytes'])
    # Exact private copy, not permission to change the independently reviewed audit.
    _ref(root, audit_ref, area=cfg['runtime_audit_copy_area'], limit=65536)
    _ref(root, cfg['accepted_literal_audit_ref'], limit=65536)
    return root, release, cfg, base, runtime


def _history(root, release, cfg):
    """One pinned historical source grant, never new-code authorization."""
    h = cfg['historical_source_only']
    pure.require(pure.canonical(release['source_release']) == pure.canonical(h['manifest_ref']))
    raw = _ref(root, h['manifest_ref'], area='data/processed')
    prior = legacy._prepare(root, raw, h['manifest_ref']['sha256'])[1]
    pure.require(prior['mode'] == 'SOURCE_TRANSCRIPTION_ONLY')
    pure.require(prior['execution_kind'] == release['execution_kind'])
    pure.require(prior['root_sha256'] == release['root_sha256'])
    pure.require(prior['source_policy_sha256'] == release['source_policy_sha256'])
    pure.require(prior['source_snapshot_sha256'] == release['source_snapshot_sha256'])
    pure.require(pure.canonical(prior['code_pins']) == pure.canonical(h['code_pins']))
    import re
    pure.require(type(h['run_id']) is str and re.fullmatch('e01-[0-9a-f]{32}', h['run_id']) is not None)
    run_relative = 'data/processed/runs/' + h['run_id']
    pure.bound_file(root, run_relative+'/checksums.json', h['ledger_sha256'], 65536, 'data/processed')
    pure.bound_file(root, run_relative+'/al_release.json', h['seal_sha256'], 65536, 'data/processed')
    controls = 'data/processed/e01_al_release_controls/'+h['manifest_ref']['sha256']
    pure.require(set(h['control_hashes']) == {'source_only.started.local.json','source_only.completed.local.json'})
    for name, sha in h['control_hashes'].items():
        data = pure.strict_json(pure.bound_file(root, controls+'/'+name, sha, 65536, 'data/processed', retain=True))
        if name == 'source_only.completed.local.json':
            pure.require(pure.canonical(data) == pure.canonical({'status':'WRITER_SEAL_VERIFIED',
                'run_id':h['run_id'], 'external_release_sha256':h['manifest_ref']['sha256'], 'seal_sha256':h['seal_sha256']}))
        else:
            pure.require(set(data) == {'at_utc','phase','external_release_sha256','retry_authorized'})
            pure.require(type(data['at_utc']) is str and data['phase']=='source_only' and data['retry_authorized'] is False)
            pure.require(data['external_release_sha256']==h['manifest_ref']['sha256'])
    legacy_writer.read_verified(root/run_relative, root=root, raw=raw, expected_sha=h['manifest_ref']['sha256'])


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
    rule = pure.strict_json(_ref(root, cfg['rule_ref'], area='configs'))
    result = context._reconcile(runtime, transcript, audit, rule)
    return result.private_payload(), result.public_diagnostics()


def read_released(root, raw, *, expected_sha):
    """Exact-six v1.1 reconciliation under a fresh external runtime release."""
    def operation():
        authority = _prepare(root, raw, expected_sha)
        private, public = _materialize(authority, verify_cache=True)
        recheck(root, raw, expected_sha=expected_sha)
        return ReleasedResult(pure.canonical(private), pure.canonical(public))
    return pure.safe(operation)


def recheck(root, raw, *, expected_sha):
    authority = _prepare(root, raw, expected_sha)
    checked_root, release, _, base, runtime = authority
    pure.verify_inputs(checked_root, runtime, release['code_pins'][PURE])


def expected_saved_payloads(root, raw, *, expected_sha):
    """Read-only saved-run semantic check; no source PDF/image I/O or parsing."""
    authority = _prepare(root, raw, expected_sha)
    private, public = _materialize(authority, verify_cache=False)
    return private, public
