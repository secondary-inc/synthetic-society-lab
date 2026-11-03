"""One-parent Alabama v1.1 office-context recording under a fresh exact release.

No automatic retry or source acquisition. A final seal is commit, distinct from
caller acknowledgment. Persistent storage failure cannot promise a tombstone.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import os
from civiclab.common import RunStore, sha256_file, utc_now
from civiclab.e01 import alabama_source_release_v1_1 as adapter

PRIVATE = 'al_document_observations.local.json'
PUBLIC = 'al_document_diagnostics.json'
PROVENANCE = 'al_release_provenance.json'
DATA = (PRIVATE, PUBLIC, PROVENANCE)
EXTRA = {'al_payload_hashes.json', 'al_commit.json', 'manifest.json', 'environment.json', 'events.jsonl', 'summary.json'}


def _write_once(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def _directory(root, relative):
    p = root / relative
    adapter.pure.require(not any(x.is_symlink() for x in (p, *p.parents)))
    p.mkdir(parents=True, exist_ok=True)
    adapter.pure.require(p.resolve().is_relative_to(root))
    return p


def _kind(exc):
    return exc.error_type if isinstance(exc, adapter.pure.DocumentsRejected) else type(exc).__name__


def _raise(kind):
    if kind == 'KeyboardInterrupt': raise KeyboardInterrupt()
    if kind == 'SystemExit': raise SystemExit()
    raise adapter.pure.DocumentsRejected(kind)


def _failure(run, kind, config):
    run.finished = False
    try:
        if not (run.path/'manifest.json').exists():
            run.write('manifest.json', {'run_id':run.run_id, 'module':'E01', 'kind':'EXPLORATORY',
                       'config':config, 'status':'FAILED_DURING_CONSTRUCTOR'})
        run.event('al_failed', error_type=kind if kind in adapter.pure.SAFE_ERRORS|{'KeyboardInterrupt','SystemExit'} else 'Exception')
        run.write('failure.json', {'status':'FAILED', 'error_type':kind if kind in adapter.pure.SAFE_ERRORS|{'KeyboardInterrupt','SystemExit'} else 'Exception',
                                  'accepted_coverage_promoted':False, 'final_ballots_accepted':0})
        if not (run.path/'summary.json').exists() and not (run.path/'checksums.json').exists():
            run.finish({'status':'FAILED', 'cost_usd':0, 'final_ballots_accepted':0})
        else:
            run.write('al_terminal_failure.local.json', {'status':'FAILED', 'reason':'PRESERVED_PUBLICATION_NOT_ELIGIBLE_SUCCESS'})
            run.write('al_failure_checksums.local.json', {p.name:sha256_file(p) for p in sorted(run.path.iterdir()) if p.is_file() and p.name!='.lock'})
    finally:
        run.finished = True


def _config(release, expected_sha, phase):
    return {'role':'AL_RELEASED_OFFICE_CONTEXT_RECORDING_V1_1', 'execution_kind':release['execution_kind'],
            'mode':release['mode'], 'phase':phase, 'external_release_sha256':expected_sha,
            'admission_config_sha256':adapter.CONFIG_SHA, 'code_pins':release['code_pins']}


def _payloads(root, raw, expected_sha, phase, authority, result):
    _, release, _, _, _ = authority
    envelope = {'schema_version':2, 'execution_kind':release['execution_kind'], 'mode':release['mode']}
    return {PRIVATE:{**envelope, 'payload':result.private_payload()},
            PUBLIC:{**envelope, 'payload':result.public_diagnostics()},
            PROVENANCE:{**envelope, 'phase':phase, 'external_release_sha256':expected_sha,
                        'admission_config_sha256':adapter.CONFIG_SHA, 'source_policy_sha256':release['source_policy_sha256'],
                        'source_snapshot_sha256':release['source_snapshot_sha256'], 'code_pins':release['code_pins'],
                        'runtime_sha256':release['runtime']['sha256'] if release['runtime'] else None,
                        'source_release_sha256':release['source_release']['sha256'] if release['source_release'] else None,
                        'office_rule_sha256':release['office_rule']['sha256'],
                        'office_rule_canonical_sha256':adapter.context.RULE_SHA}}


def _record(root, raw, *, expected_sha, phase):
    # No control/RunStore/source read until exact release metadata admission.
    authority = adapter.pure.safe(lambda:adapter._prepare(root, raw, expected_sha))
    root, release, _, _, _ = authority
    adapter.pure.require(Path(__file__).resolve() == root/adapter.WRAPPER)
    adapter.pure.require(type(phase) is str and phase in release['phase_limit'])
    controls = _directory(root, 'data/processed/e01_al_release_controls/'+expected_sha)
    _directory(root, release['output_scope'])
    if phase == 'replay':
        previous = adapter.pure.strict_json((controls/'primary.completed.local.json').read_bytes())
        adapter.pure.require(set(previous)=={'status','run_id','external_release_sha256','seal_sha256'} and previous['status']=='WRITER_SEAL_VERIFIED' and previous['external_release_sha256']==expected_sha and re.fullmatch('e01-[0-9a-f]{32}', previous['run_id']) is not None)
        adapter.pure.require(previous['seal_sha256']==sha256_file(root/'data/processed/runs'/previous['run_id']/'al_release.json'))
        read_verified(root/'data/processed/runs'/previous['run_id'], root=root, raw=raw, expected_sha=expected_sha)
    _write_once(controls/(phase+'.started.local.json'), {'at_utc':utc_now(), 'phase':phase, 'external_release_sha256':expected_sha, 'retry_authorized':False})
    config = _config(release, expected_sha, phase)
    run = RunStore.__new__(RunStore)
    failure = None
    try:
        RunStore.__init__(run, root, 'E01', config, kind='EXPLORATORY')
        adapter.pure.require(run.path.parent == root/release['output_scope'])
        result = adapter.read_released(root, raw, expected_sha=expected_sha)
        payloads = _payloads(root, raw, expected_sha, phase, authority, result)
        for name, data in payloads.items(): run.write(name, data)
        adapter.recheck(root, raw, expected_sha=expected_sha)
        run.write('al_payload_hashes.json', {name:sha256_file(run.path/name) for name in DATA})
        run.write('al_commit.json', {'status':'PAYLOADS_COMPLETE_AWAITING_FINAL_SEAL', 'external_release_sha256':expected_sha,
                                   'mode':release['mode'], 'phase':phase, 'required_payloads':list(DATA)})
        run.finish({'status':'AL_RECORDING_COMPLETE_PENDING_INDEPENDENT_REVIEW', 'execution_kind':release['execution_kind'],
                    'mode':release['mode'], 'phase':phase, 'accepted_coverage_promoted':False, 'final_ballots_accepted':0, 'cost_usd':0})
        adapter.recheck(root, raw, expected_sha=expected_sha)
        run.finished = False
        run.write('al_release.json', {'status':'LOCAL_AL_FINAL_SEAL_PENDING_INDEPENDENT_REVIEW', 'external_release_sha256':expected_sha,
                                     'mode':release['mode'], 'phase':phase, 'checksums_sha256':sha256_file(run.path/'checksums.json'),
                                     'code_pins':release['code_pins']})
        run.finished = True
        read_verified(run.path, root=root, raw=raw, expected_sha=expected_sha)
        _write_once(controls/(phase+'.completed.local.json'), {'status':'WRITER_SEAL_VERIFIED', 'run_id':run.run_id,
                     'external_release_sha256':expected_sha, 'seal_sha256':sha256_file(run.path/'al_release.json')})
    except BaseException as exc:
        failure = _kind(exc)
        if getattr(run, 'path', None) and run.path.is_dir():
            try: _failure(run, failure, config)
            except BaseException: run.finished = True
        try:
            _write_once(controls/(phase+'.uncertain_or_failed.local.json'), {'status':'STOP_INDEPENDENT_READ_ONLY_RESOLUTION_NO_RETRY',
                         'error_type':failure if failure in adapter.pure.SAFE_ERRORS|{'KeyboardInterrupt','SystemExit'} else 'Exception',
                         'run_id':getattr(run,'run_id',None), 'external_release_sha256':expected_sha})
        except BaseException: pass
    finally:
        run._release_lock()
    if failure: _raise(failure)
    return run.path


def _read_verified(path, *, root, raw, expected_sha):
    """Admit complete saved evidence without new PDF/image I/O or source parse."""
    authority = adapter.pure.safe(lambda:adapter._prepare(root, raw, expected_sha))
    root, release, _, _, _ = authority
    p = Path(path).absolute()
    adapter.pure.require(p.parent==root/'data/processed/runs' and p.is_dir() and '..' not in p.parts)
    adapter.pure.require(not any(x.is_symlink() for x in (p,*p.parents)))
    adapter.pure.require(not any((p/n).exists() for n in ['failure.json','al_terminal_failure.local.json','al_failure_checksums.local.json']))
    adapter.pure.require(all(f.is_file() and not f.is_symlink() for f in p.iterdir()))
    ledger = adapter.pure.strict_json((p/'checksums.json').read_bytes())
    adapter.pure.require(type(ledger) is dict and set(ledger)==set(DATA)|EXTRA)
    adapter.pure.require({f.name for f in p.iterdir() if f.is_file() and f.name!='.lock'}==set(ledger)|{'checksums.json','al_release.json'})
    for name, h in ledger.items(): adapter.pure.bound_file(p,name,h,4194304,'.')
    manifest = adapter.pure.strict_json((p/'manifest.json').read_bytes())
    phase = manifest['config']['phase']
    adapter.pure.require(phase in release['phase_limit'] and manifest['module']=='E01' and manifest['kind']=='EXPLORATORY' and manifest['run_id']==p.name)
    adapter.pure.require(adapter.pure.canonical(manifest['config'])==adapter.pure.canonical(_config(release,expected_sha,phase)))
    summary = adapter.pure.strict_json((p/'summary.json').read_bytes())
    adapter.pure.require(adapter.pure.canonical(summary)==adapter.pure.canonical({'status':'AL_RECORDING_COMPLETE_PENDING_INDEPENDENT_REVIEW',
        'execution_kind':release['execution_kind'],'mode':release['mode'],'phase':phase,'accepted_coverage_promoted':False,'final_ballots_accepted':0,'cost_usd':0}))
    seal = adapter.pure.strict_json((p/'al_release.json').read_bytes())
    adapter.pure.require(adapter.pure.canonical(seal)==adapter.pure.canonical({'status':'LOCAL_AL_FINAL_SEAL_PENDING_INDEPENDENT_REVIEW',
        'external_release_sha256':expected_sha,'mode':release['mode'],'phase':phase,'checksums_sha256':sha256_file(p/'checksums.json'),'code_pins':release['code_pins']}))
    commit = adapter.pure.strict_json((p/'al_commit.json').read_bytes())
    adapter.pure.require(commit=={'status':'PAYLOADS_COMPLETE_AWAITING_FINAL_SEAL','external_release_sha256':expected_sha,
                                'mode':release['mode'],'phase':phase,'required_payloads':list(DATA)})
    payload_hashes = adapter.pure.strict_json((p/'al_payload_hashes.json').read_bytes())
    adapter.pure.require(set(payload_hashes)==set(DATA) and all(sha256_file(p/name)==h for name,h in payload_hashes.items()))
    private, public = adapter.expected_saved_payloads(root, raw, expected_sha=expected_sha)
    expected = _payloads(root,raw,expected_sha,phase,authority,adapter.ReleasedResult(adapter.pure.canonical(private),adapter.pure.canonical(public)))
    for name, data in expected.items():
        adapter.pure.require(adapter.pure.canonical(adapter.pure.strict_json((p/name).read_bytes()))==adapter.pure.canonical(data))
    return expected[PUBLIC]


def _safe_call(operation):
    failure=None
    try:result=operation()
    except BaseException as exc:failure=_kind(exc)
    if failure:_raise(failure)
    return result


def record(root, raw, *, expected_sha, phase):
    return _safe_call(lambda:_record(root,raw,expected_sha=expected_sha,phase=phase))


def read_verified(path, *, root, raw, expected_sha):
    return _safe_call(lambda:_read_verified(path,root=root,raw=raw,expected_sha=expected_sha))
