"""Finite exploratory-pilot sequencing; pure data, never dispatch authority.

The production bridge must authenticate retained phase records against its
durable owner/checkpoint before supplying them here. Hashes bind content only.
This component performs no credential, filesystem, transport or ledger access.
"""
from ..common import canonical_bytes, canonical_hash
from ..model import ExecutionBlocked
from .exploratory_live_requests_v1 import (
    _protocol, compile_pre, compile_post, cost_envelope,
    PROTOCOL_SHA, PROJECTION_SHA, ASSIGNMENT_SHA)
from .exploratory_pilot_analysis_v1 import _load, analyze

DISPOSITIONS = {'ANSWER', 'PARSE_ERROR', 'FAILED_UNCERTAIN', 'CANCELLED'}


def _envelope(rows):
    return {'response_provenance': 'MOCK', 'protocol_sha256': PROTOCOL_SHA,
            'projection_sha256': PROJECTION_SHA,
            'assignment_sha256': ASSIGNMENT_SHA, 'records': rows}


def next_action(protocol_bytes, terms, transcript_bytes):
    """Reconstruct one next request or a terminal result from a bounded prefix.

    Transcript is a JSON array of exact {execution_order, phase, payload_sha256,
    status, answer} records. Every submitted hash is checked against a freshly
    compiled request. Skipped posts are derived, never supplied. A financial or
    cancellation stop terminates the entire sequence. Nothing here authenticates
    a provider response, its cost, a caller, or a claimed prior checkpoint.
    """
    _protocol(protocol_bytes)
    cost_envelope(protocol_bytes, terms)
    transcript = _load(transcript_bytes, 131072)
    if type(transcript) is not list or len(transcript) > 32:
        raise ExecutionBlocked('finite ordered phase transcript required')
    rows, compiled_hashes = [], []
    position = 0
    stopped = False
    for unit in range(16):
        before = None
        for phase in ('pre', 'post'):
            if stopped:
                rows.append(dict(execution_order=unit, phase=phase,
                                 status='NOT_ATTEMPTED', answer=None))
                continue
            compiled = (compile_pre(protocol_bytes, unit, terms) if phase == 'pre'
                        else compile_post(protocol_bytes, unit, terms, before))
            if compiled['status'] == 'SKIP_INVALID_PRE':
                rows.append(dict(execution_order=unit, phase=phase,
                                 status='SKIPPED_INVALID_PRE', answer=None))
                continue
            if position == len(transcript):
                return {'status': 'REQUEST_READY_NOT_ADMITTED', 'request': compiled,
                        'transcript_sha256': canonical_hash(transcript),
                        'derived_records': rows, 'consumed_responses': position,
                        'actual_authority': False,
                        'prior_records_authentication': 'REQUIRED_EXTERNALLY'}
            row = transcript[position]
            if (type(row) is not dict or set(row) != {
                    'execution_order', 'phase', 'payload_sha256', 'status', 'answer'}
                    or type(row['execution_order']) is not int
                    or row['execution_order'] != unit or row['phase'] != phase
                    or type(row['status']) is not str or row['status'] not in DISPOSITIONS
                    or row['payload_sha256'] != compiled['payload_sha256']
                    or (row['status'] != 'ANSWER' and row['answer'] is not None)):
                raise ExecutionBlocked('phase identity, payload or disposition differs')
            position += 1
            compiled_hashes.append(compiled['payload_sha256'])
            rows.append({key: row[key] for key in ('execution_order', 'phase', 'status', 'answer')})
            if row['status'] in ('FAILED_UNCERTAIN', 'CANCELLED'):
                stopped = True
            elif phase == 'pre':
                before = row['answer'] if row['status'] == 'ANSWER' else None
    if position != len(transcript):
        raise ExecutionBlocked('extra response after terminal stop or completion')
    envelope = _envelope(rows)
    return {'status': 'STOPPED' if stopped else 'COMPLETE',
            'response_envelope': envelope,
            'analysis': analyze(protocol_bytes, canonical_bytes(envelope)),
            'transcript_sha256': canonical_hash(transcript),
            'compiled_payload_hashes': compiled_hashes,
            'consumed_responses': position, 'actual_authority': False,
            'response_provenance': 'MOCK',
            'prior_records_authentication': 'REQUIRED_EXTERNALLY'}


def create_actual_runner(*args, **kwargs):
    raise ExecutionBlocked('live accounting/checkpoint adapter not independently released')
