"""Pure authored Alabama document reconciler. Actual runtime is default denied.

No PDF extraction, rendering, OCR, networking, recording or readiness integration.
Literal transcription and its independent audit are separate bound local inputs.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import stat

CONTRACT_SHA = '8c09beb1fec22a3194ec82d6f30c9662d0392f807b406520e69bc2cefe85dd1d'
MODULE_PATH = 'src/civiclab/e01/alabama_documents_v1.py'
SCOPE = 'AL_CACHED_GENERAL_CONTEXT_CERTIFICATION_DOCUMENT_OBSERVATIONS_ONLY'
SOURCE_IDS = {'al_state_democratic', 'al_state_republican', 'al_state_independent',
              'al_party_democratic_amended', 'al_party_republican_amended'}
UNKNOWN_REASONS = {
    'printed_on_final_ballot': 'DOCUMENT_CERTIFICATION_IS_NOT_FINAL_PRINTED_BALLOT_PROOF',
    'declared_write_in': 'NO_WRITEIN_ADJUDICATION_IN_THIS_SCOPE',
    'legal_nominee': 'SOURCE_ASSERTION_NOT_INDEPENDENT_LEGAL_ADJUDICATION',
    'latest_amendment_complete': 'LATER_CORRECTIVE_ACTION_RESERVED_AND_UPSTREAM_COMPLETENESS_UNVERIFIED',
}
ROLE_COUNTS = {key: 1 for key in [
    'AMENDED_STATE_PACKAGE_SENATE_TABLE', 'HISTORICAL_JULY1_CERTIFICATION_LETTER',
    'HISTORICAL_JULY1_TABLE', 'STATE_PACKAGE_JUNE24_PARTY_CERTIFICATION',
    'AUGUST24_PARTY_AMENDMENT_TABLE', 'AUGUST28_PARTY_AMENDMENT_CERTIFICATION']}
SAFE_ERRORS = {'ValueError', 'TypeError', 'KeyError', 'OSError', 'FileNotFoundError',
               'PermissionError', 'UnicodeDecodeError', 'JSONDecodeError', 'RuntimeError'}


def require(ok):
    if not ok:
        raise ValueError('AL_DOCUMENT_CONTRACT_MISMATCH')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def norm(value):
    return ' '.join(value.split())


class DocumentsRejected(Exception):
    def __init__(self, kind):
        self.error_type = kind if kind in SAFE_ERRORS else 'Exception'
        super().__init__('AL_DOCUMENTS_REJECTED:' + self.error_type)


def safe(operation):
    failure = None
    try:
        result = operation()
    except BaseException as exc:
        failure = type(exc).__name__
    if failure == 'KeyboardInterrupt':
        raise KeyboardInterrupt()
    if failure == 'SystemExit':
        raise SystemExit()
    if failure:
        raise DocumentsRejected(failure)
    return result


def closed_snapshot(value):
    budget = [0, 0]

    def clone(item, depth):
        budget[0] += 1
        require(budget[0] <= 8192 and depth <= 32)
        kind = type(item)
        if kind is dict:
            out = {}
            for key, child in item.items():
                require(type(key) is str)
                out[clone(key, depth + 1)] = clone(child, depth + 1)
            return out
        if kind is list:
            return [clone(child, depth + 1) for child in item]
        if kind is str:
            budget[1] += len(item)
            require(len(item) <= 8192 and budget[1] <= 262144)
            return item
        if kind is int:
            require(item.bit_length() <= 64)
            return item
        if kind is float:
            require(math.isfinite(item))
            return item
        require(kind in (bool, type(None)))
        return item

    return clone(value, 0)


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out)
            out[key] = value
        return out

    def invalid(_):
        raise ValueError('AL_NONFINITE_JSON')

    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)


def is_hash(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def admitted_snapshot(contract):
    c = closed_snapshot(contract)
    require(digest(canonical(c)) == CONTRACT_SHA)
    require(c['schema_version'] == 1 and c['role'] == 'E01_AL_STANDALONE_DOCUMENT_RECONCILIATION_CANDIDATE_ONLY')
    require(canonical(c['unknowns']) == canonical({k: {'kind': 'UNKNOWN', 'reason': v} for k, v in UNKNOWN_REASONS.items()}))
    release = c['actual_execution_release']
    # All checks precede even root/path inspection. Current actual contract has
    # null authority, transcription and audit fields and always refuses here.
    require(release['approved'] is True)
    require(all(is_hash(v) for k, v in release.items() if k != 'approved'))
    require(c['transcription']['sha256'] == release['trusted_private_transcript_sha256'])
    require(c['independent_transcription_audit']['sha256'] == release['independent_literal_transcription_audit_sha256'])
    for ref in [c['transcription'], c['independent_transcription_audit'], *c['release_documents']]:
        require(type(ref['path']) is str and is_hash(ref['sha256']))
        require(type(ref['bytes']) is int and 0 < ref['bytes'] <= 65536)
    require([x['role'] for x in c['release_documents']] == ['source_read_authorization', 'runtime_code_acceptance_sha256', 'recorded_preflight_release_sha256'])
    require(all(x['sha256'] == release[x['role']] for x in c['release_documents']))
    return c


def root_guard(root):
    p = Path(root).absolute()
    require('..' not in p.parts and p.is_dir())
    require(not any(q.is_symlink() for q in (p, *p.parents)))
    require(Path(__file__).resolve() == p / MODULE_PATH)
    return p


def bound_file(root, relative, expected_hash, ceiling, area, expected_size=None, retain=False):
    q = Path(relative)
    require(not q.is_absolute() and '..' not in q.parts and is_hash(expected_hash))
    p = root / q
    require(not any(x.is_symlink() for x in (p, *p.parents) if x.is_relative_to(root)))
    require(p.resolve().is_relative_to(root / area))
    before = p.stat()
    require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= ceiling)
    if expected_size is not None:
        require(type(expected_size) is int and before.st_size == expected_size)
    h = hashlib.sha256()
    chunks = []
    length = 0
    with p.open('rb') as stream:
        while True:
            block = stream.read(65536)
            if not block:
                break
            length += len(block)
            require(length <= ceiling)
            h.update(block)
            if retain:
                chunks.append(block)
    after = p.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns))
    require(length == before.st_size and h.hexdigest() == expected_hash)
    return b''.join(chunks) if retain else length


def source_snapshot_sha(c):
    return digest(canonical({k: c[k] for k in ['sources', 'pages', 'occurrence_slots', 'unknowns']}))


def verify_inputs(root, c, module_sha):
    root_guard(root)
    require(digest(Path(__file__).read_bytes()) == module_sha)
    for p, h in c['metadata_pins'].items():
        bound_file(root, p, h, 1048576, '.', retain=False)
    sources = c['sources']
    require(len(sources) == len({s['source_id'] for s in sources}) == len({s['path'] for s in sources}) == 5)
    require({s['source_id'] for s in sources} == SOURCE_IDS)
    require(sum(s['bytes'] for s in sources) == c['limits']['source_pdf_exact_declared_bytes'])
    for s in sources:
        bound_file(root, s['path'], s['sha256'], 1048576, 'data/raw', s['bytes'])
    pages = c['pages']
    require(len(pages) == len({(p['source_id'], p['physical_pdf_page_1_based']) for p in pages}) == len({p['render_path'] for p in pages}) == 47)
    require(all(sorted(p['physical_pdf_page_1_based'] for p in pages if p['source_id'] == s['source_id']) == list(range(1, s['pages'] + 1)) for s in sources))
    total = 0
    for p in pages:
        total += bound_file(root, p['render_path'], p['render_sha256'], 8388608, 'data/raw')
        require(total <= 394264576)
    for ref in c['release_documents']:
        data = strict_json(bound_file(root, ref['path'], ref['sha256'], 65536, 'data/processed', ref['bytes'], True))
        expected = {'schema_version': 1, 'role': ref['role'], 'status': 'AUTHORED_OR_SEPARATELY_RELEASED_EXACT_SNAPSHOT',
                    'source_snapshot_sha256': source_snapshot_sha(c)}
        if ref['role'] == 'runtime_code_acceptance_sha256':
            expected['module_sha256'] = module_sha
        require(canonical(data) == canonical(expected))
    values = []
    for ref in [c['transcription'], c['independent_transcription_audit']]:
        values.append(strict_json(bound_file(root, ref['path'], ref['sha256'], 65536, 'data/processed', ref['bytes'], True)))
    return values


def occurrence_witness(record):
    return {k: record[k] for k in ['source_id', 'source_sha256', 'physical_pdf_page_1_based',
        'render_sha256', 'record_role', 'party_context', 'historical', 'date_evidence',
        'name_utf8_sha256', 'office_utf8_sha256', 'transcription_method']}


@dataclass(frozen=True, repr=False)
class DocumentBundle:
    _private_bytes: bytes
    _public_bytes: bytes

    def __repr__(self):
        return '<AlabamaDocumentBundle local-only occurrences; values withheld>'

    def private_payload(self):
        return strict_json(self._private_bytes)

    def public_diagnostics(self):
        return strict_json(self._public_bytes)


def _reconcile(c, transcript, audit):
    snapshot_sha = source_snapshot_sha(c)
    require(set(transcript) == {'schema_version', 'scope', 'source_snapshot_sha256', 'occurrences'})
    require(type(transcript['schema_version']) is int and transcript['schema_version'] == 1)
    require(transcript['scope'] == 'LOCAL_LITERAL_TRANSCRIPTION_NOT_BALLOT_ACCEPTANCE' and transcript['source_snapshot_sha256'] == snapshot_sha)
    require(set(audit) == {'schema_version', 'scope', 'status', 'source_snapshot_sha256', 'transcription_sha256', 'approved_occurrences'})
    require(type(audit['schema_version']) is int and audit['schema_version'] == 1)
    require(audit['scope'] == 'INDEPENDENT_LOCAL_LITERAL_TRANSCRIPTION_REVIEW' and audit['status'] == 'PASS_EXACT_TRANSCRIBED_OCCURRENCES_ONLY')
    require(audit['source_snapshot_sha256'] == snapshot_sha and audit['transcription_sha256'] == c['transcription']['sha256'])
    records = transcript['occurrences']
    require(type(records) is list and len(records) == 6)
    sources = {s['source_id']: s for s in c['sources']}
    groups = {}
    required_keys = {'source_id', 'source_sha256', 'physical_pdf_page_1_based', 'render_sha256', 'record_role',
                     'official_name_literal', 'office_label_literal', 'party_context', 'date_evidence',
                     'historical', 'transcription_method', 'name_utf8_sha256', 'office_utf8_sha256'}
    for index, (record, slot) in enumerate(zip(records, c['occurrence_slots'])):
        require(type(record) is dict and set(record) == required_keys)
        for key in ['source_id', 'physical_pdf_page_1_based', 'render_sha256', 'record_role', 'party_context', 'historical', 'date_evidence']:
            require(canonical(record[key]) == canonical(slot[key]))
        require(record['source_sha256'] == sources[slot['source_id']]['sha256'])
        require(record['transcription_method'] == 'SOURCE_BOUND_LOCAL_LITERAL_TRANSCRIPTION')
        for key, hash_key in [('official_name_literal', 'name_utf8_sha256'), ('office_label_literal', 'office_utf8_sha256')]:
            value = record[key]
            require(type(value) is str and 0 < len(value) <= 256 and bool(norm(value)))
            require(not any(ord(ch) < 32 and ch not in '\r\n\t' for ch in value))
            require(digest(value.encode('utf-8')) == record[hash_key])
        party = record['party_context']
        key = (norm(record['official_name_literal']), norm(record['office_label_literal']))
        if party in groups:
            require(groups[party]['identity'] == key)
        else:
            groups[party] = {'identity': key, 'indexes': []}
        groups[party]['indexes'].append(index)
    require(set(groups) == {'Democratic', 'Republican'})
    require({p: len(g['indexes']) for p, g in groups.items()} == {'Democratic': 4, 'Republican': 2})
    require(type(audit['approved_occurrences']) is list and canonical(audit['approved_occurrences']) == canonical([occurrence_witness(r) for r in records]))
    # Never place record literals in public diagnostics or exceptions. Private
    # names/office text are transcribed UTF8 bytes, not original PDF encodings.
    entries = [{'party_context': party, 'official_name_literal': records[g['indexes'][0]]['official_name_literal'],
                'office_label_literal': records[g['indexes'][0]]['office_label_literal'], 'occurrence_indexes': g['indexes'],
                'record_role': 'DOCUMENT_SUPPORTED_CERTIFICATION_ENTRY_ONLY', 'typed_unknowns': c['unknowns']}
               for party, g in groups.items()]
    used = {(r['source_id'], r['physical_pdf_page_1_based']) for r in records}
    exclusions = [{'source_id': p['source_id'], 'physical_pdf_page_1_based': p['physical_pdf_page_1_based'],
                   'role_office_observation': p['role_office_observation']}
                  for p in c['pages'] if (p['source_id'], p['physical_pdf_page_1_based']) not in used]
    private = {'schema_version': 1, 'scope': SCOPE, 'source_snapshot_sha256': snapshot_sha,
               'occurrences': [{**r, 'independent_transcription_audit_sha256': c['independent_transcription_audit']['sha256']} for r in records], 'reconciled_document_entries': entries,
               'exclusions_by_page_role': exclusions, 'typed_unknowns': c['unknowns']}
    public = {'schema_version': 1, 'scope': SCOPE, 'state': 'AL',
              'source_hashes': {s['source_id']: s['sha256'] for s in c['sources']},
              'source_count': 5, 'physical_page_count': 47, 'senate_occurrence_count': len(records),
              'document_supported_name_group_count': len(groups), 'historical_occurrence_count': sum(r['historical'] for r in records),
              'typed_unknowns': c['unknowns'], 'document_role_counts': dict(Counter(r['record_role'] for r in records)),
              'source_adoption': False, 'accepted_coverage_promoted': False, 'final_ballots_accepted': 0,
              'cost_usd': 0, 'model_calls': 0}
    validate_public(public)
    return DocumentBundle(canonical(private), canonical(public))


def validate_public(value):
    """Closed schema; public diagnostics never accept literal/name extensions."""
    keys = {'schema_version', 'scope', 'state', 'source_hashes', 'source_count',
            'physical_page_count', 'senate_occurrence_count', 'document_supported_name_group_count',
            'historical_occurrence_count', 'typed_unknowns', 'document_role_counts',
            'source_adoption', 'accepted_coverage_promoted', 'final_ballots_accepted', 'cost_usd', 'model_calls'}
    require(type(value) is dict and set(value) == keys)
    expected_counts = {'schema_version': 1, 'source_count': 5, 'physical_page_count': 47,
                       'senate_occurrence_count': 6, 'document_supported_name_group_count': 2,
                       'historical_occurrence_count': 2, 'final_ballots_accepted': 0, 'cost_usd': 0, 'model_calls': 0}
    require(all(type(value[k]) is int and value[k] == n for k, n in expected_counts.items()))
    require(value['scope'] == SCOPE and value['state'] == 'AL')
    require(value['source_adoption'] is False and value['accepted_coverage_promoted'] is False)
    require(type(value['source_hashes']) is dict and set(value['source_hashes']) == SOURCE_IDS)
    require(all(is_hash(h) for h in value['source_hashes'].values()))
    require(canonical(value['typed_unknowns']) == canonical({k: {'kind': 'UNKNOWN', 'reason': v} for k, v in UNKNOWN_REASONS.items()}))
    require(canonical(value['document_role_counts']) == canonical(ROLE_COUNTS))
    return value


def read_sources(root, contract):
    """Pure boundary. Actual null-authority contract refuses before root access."""
    def operation():
        c = admitted_snapshot(contract)
        checked_root = root_guard(root)
        module_sha = digest(Path(__file__).read_bytes())
        transcript, audit = verify_inputs(checked_root, c, module_sha)
        result = _reconcile(c, transcript, audit)
        verify_inputs(checked_root, c, module_sha)
        return result

    return safe(operation)
