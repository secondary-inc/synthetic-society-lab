"""Authored-only fixtures. Never reads real cached PDFs/renders/transcripts."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab.e01 import alabama_documents_v1 as m
from civiclab.common import RunStore
from civiclab.reproduction import build_package

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'configs/e01_al_standalone_runtime_contract_v1_candidate.json'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = m.canonical(value)
    path.write_bytes(raw)
    return {'path': str(path), 'sha256': m.digest(raw), 'bytes': len(raw)}


def fixture(root):
    c = json.loads((REPO / CONTRACT).read_text())
    module = root / m.MODULE_PATH
    module.parent.mkdir(parents=True)
    module.write_bytes((REPO / m.MODULE_PATH).read_bytes())
    for p in c['metadata_pins']:
        q = root / p
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes((REPO / p).read_bytes())
    for source in c['sources']:
        q = root / source['path']
        q.parent.mkdir(parents=True, exist_ok=True)
        raw = ('DEMO SOURCE ' + source['source_id']).encode()
        q.write_bytes(raw)
        source.update(sha256=m.digest(raw), bytes=len(raw))
    c['limits']['source_pdf_exact_declared_bytes'] = sum(s['bytes'] for s in c['sources'])
    for page in c['pages']:
        q = root / page['render_path']
        q.parent.mkdir(parents=True, exist_ok=True)
        raw = ('DEMO RENDER ' + page['source_id'] + str(page['physical_pdf_page_1_based'])).encode()
        q.write_bytes(raw)
        page['render_sha256'] = m.digest(raw)
    page_index = {(p['source_id'], p['physical_pdf_page_1_based']): p for p in c['pages']}
    source_index = {s['source_id']: s for s in c['sources']}
    records = []
    for slot in c['occurrence_slots']:
        slot['render_sha256'] = page_index[(slot['source_id'], slot['physical_pdf_page_1_based'])]['render_sha256']
        name = 'DEMO ÉLISE O’NEILL' if slot['party_context'] == 'Democratic' else 'DEMO ROBIN EXAMPLE'
        office = 'United States Senator'
        record = {k: copy.deepcopy(slot[k]) for k in ['source_id', 'physical_pdf_page_1_based', 'render_sha256', 'record_role', 'party_context', 'historical', 'date_evidence']}
        record.update(source_sha256=source_index[slot['source_id']]['sha256'],
                      official_name_literal=name, office_label_literal=office,
                      name_utf8_sha256=m.digest(name.encode()), office_utf8_sha256=m.digest(office.encode()),
                      transcription_method='SOURCE_BOUND_LOCAL_LITERAL_TRANSCRIPTION')
        records.append(record)
    transcript = {'schema_version': 1, 'scope': 'LOCAL_LITERAL_TRANSCRIPTION_NOT_BALLOT_ACCEPTANCE',
                  'source_snapshot_sha256': m.source_snapshot_sha(c), 'occurrences': records}
    save_inputs(root, c, transcript)
    return c, transcript


def bind_json(root, path, value):
    ref = write_json(root / path, value)
    ref['path'] = path
    return ref


def save_inputs(root, c, transcript):
    c['transcription'] = bind_json(root, 'data/processed/e01_al_authored/transcript.local.json', transcript)
    audit = {'schema_version': 1, 'scope': 'INDEPENDENT_LOCAL_LITERAL_TRANSCRIPTION_REVIEW',
             'status': 'PASS_EXACT_TRANSCRIBED_OCCURRENCES_ONLY', 'source_snapshot_sha256': m.source_snapshot_sha(c),
             'transcription_sha256': c['transcription']['sha256'],
             'approved_occurrences': [m.occurrence_witness(r) for r in transcript['occurrences']]}
    c['independent_transcription_audit'] = bind_json(root, 'data/processed/e01_al_authored/audit.local.json', audit)
    release = c['actual_execution_release']
    release.update(approved=True, trusted_private_transcript_sha256=c['transcription']['sha256'],
                   independent_literal_transcription_audit_sha256=c['independent_transcription_audit']['sha256'])
    for ref in c['release_documents']:
        role = ref['role']
        body = {'schema_version': 1, 'role': role, 'status': 'AUTHORED_OR_SEPARATELY_RELEASED_EXACT_SNAPSHOT',
                'source_snapshot_sha256': m.source_snapshot_sha(c)}
        if role == 'runtime_code_acceptance_sha256':
            body['module_sha256'] = m.digest((root / m.MODULE_PATH).read_bytes())
        new = bind_json(root, 'data/processed/e01_al_authored/' + role + '.local.json', body)
        ref.update(new)
        release[role] = new['sha256']
    return audit


def identities(root):
    return {str(p.relative_to(root)): m.digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def runtime(root, c):
    stack = ExitStack()
    stack.enter_context(patch.object(m, 'CONTRACT_SHA', m.digest(m.canonical(c))))
    stack.enter_context(patch.object(m, '__file__', str(root / m.MODULE_PATH)))
    return stack


class AlabamaDocumentFixtures(unittest.TestCase):
    def test_actual_null_authority_contract_denies_before_any_root_or_input_access(self):
        c = json.loads((REPO / CONTRACT).read_text())
        for mutate in [lambda x: None, lambda x: x['actual_execution_release'].update(approved=True),
                       lambda x: x['actual_execution_release'].update(trusted_private_transcript_sha256='0' * 64),
                       lambda x: x.update(extra='DEMO PRIVATE')]:
            q = copy.deepcopy(c)
            mutate(q)
            with patch.object(m, 'root_guard') as root, patch.object(m, 'bound_file') as read:
                with self.assertRaises(m.DocumentsRejected):
                    m.read_sources('/unused', q)
                root.assert_not_called()
                read.assert_not_called()

    def test_success_pure_replay_preserves_six_occurrences_history_unknowns_and_utf8(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            c, transcript = fixture(root)
            before = identities(root)
            with runtime(root, c):
                one = m.read_sources(root, c)
                two = m.read_sources(root, c)
            self.assertEqual(before, identities(root))
            self.assertEqual(one.private_payload(), two.private_payload())
            self.assertEqual(one.public_diagnostics(), two.public_diagnostics())
            private = one.private_payload()
            self.assertEqual(len(private['occurrences']), 6)
            self.assertEqual(len(private['exclusions_by_page_role']), 41)
            self.assertEqual([len(g['occurrence_indexes']) for g in private['reconciled_document_entries']], [4, 2])
            self.assertEqual(sum(x['historical'] for x in private['occurrences']), 2)
            for record, original in zip(private['occurrences'], transcript['occurrences']):
                for key in original:
                    self.assertEqual(record[key], original[key])
                self.assertEqual(record['independent_transcription_audit_sha256'], c['independent_transcription_audit']['sha256'])
            self.assertEqual(private['occurrences'][0]['official_name_literal'], 'DEMO ÉLISE O’NEILL')
            self.assertEqual(private['occurrences'][1]['date_evidence']['received_stamp_on_occurrence'],
                             {'kind': 'UNKNOWN', 'reason': 'PARTIALLY_UNREADABLE_DO_NOT_GUESS'})
            self.assertEqual(private['typed_unknowns'], c['unknowns'])
            public = one.public_diagnostics()
            self.assertEqual(set(public), {'schema_version', 'scope', 'state', 'source_hashes', 'source_count',
                'physical_page_count', 'senate_occurrence_count', 'document_supported_name_group_count',
                'historical_occurrence_count', 'typed_unknowns', 'document_role_counts', 'source_adoption',
                'accepted_coverage_promoted', 'final_ballots_accepted', 'cost_usd', 'model_calls'})
            self.assertEqual(public['document_supported_name_group_count'], 2)
            self.assertNotIn('DEMO ÉLISE', repr(one) + json.dumps(public, ensure_ascii=False))
            public['typed_unknowns'].clear()
            private['occurrences'].clear()
            self.assertEqual(len(one.private_payload()['occurrences']), 6)
            self.assertEqual(len(one.public_diagnostics()['typed_unknowns']), 4)

    def rejected(self, root, c):
        before = identities(root)
        with runtime(root, c), self.assertRaises(m.DocumentsRejected) as cm:
            m.read_sources(root, c)
        self.assertEqual(before, identities(root))
        self.assertNotIn('DEMO', str(cm.exception) + repr(cm.exception))
        self.assertIsNone(cm.exception.__context__)
        self.assertIsNone(cm.exception.__cause__)

    def test_disagreement_no_fuzzy_merge_punctuation_case_accents_office_or_missing_literal(self):
        variants = [('official_name_literal', x) for x in ['', 'DEMO ÉLISE ONEILL', 'DEMO Elise O’Neill', 'DEMO ELISE O’NEILL', 'DEMO DIFFERENT']]
        variants += [('office_label_literal', 'State Senator'), ('office_label_literal', '')]
        for key, value in variants:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                c, transcript = fixture(root)
                transcript['occurrences'][1][key] = value
                hash_key = 'name_utf8_sha256' if key == 'official_name_literal' else 'office_utf8_sha256'
                transcript['occurrences'][1][hash_key] = m.digest(value.encode())
                save_inputs(root, c, transcript)  # Audit also resealed; semantic disagreement must still fail.
                self.rejected(root, c)

    def test_whitespace_only_identity_keeps_original_literals_and_display_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            c, transcript = fixture(root)
            record = transcript['occurrences'][1]
            record['official_name_literal'] = '  DEMO\nÉLISE\tO’NEILL  '
            record['name_utf8_sha256'] = m.digest(record['official_name_literal'].encode())
            save_inputs(root, c, transcript)
            with runtime(root, c):
                result = m.read_sources(root, c)
            self.assertEqual(result.private_payload()['occurrences'][1]['official_name_literal'], record['official_name_literal'])
            self.assertEqual(result.public_diagnostics()['document_supported_name_group_count'], 2)

    def test_historical_role_party_date_stamp_slot_and_extra_fields_refused_even_with_resealed_audit(self):
        changes = [lambda r: r.update(historical=False), lambda r: r.update(historical=1),
                   lambda r: r.update(record_role='CURRENT_FINAL_BALLOT'),
                   lambda r: r.update(party_context='Republican'), lambda r: r.update(party_class='D'),
                   lambda r: r.update(source_id='al_state_independent'), lambda r: r.update(physical_pdf_page_1_based=14),
                   lambda r: r.update(physical_pdf_page_1_based=True),
                   lambda r: r['date_evidence']['received_stamp_on_occurrence'].update(kind='OBSERVED_SOURCE_STAMP', date='2026-07-01'),
                   lambda r: r.update(date_filed_iso='2026-07-01'),
                   lambda r: r.update(legal_nominee=True), lambda r: r.update(contact='DEMO PRIVATE')]
        for change in changes:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                c, transcript = fixture(root)
                change(transcript['occurrences'][1])
                save_inputs(root, c, transcript)
                self.rejected(root, c)

    def test_missing_duplicate_collapsed_reordered_records_and_hashes_refused(self):
        for mode in ['missing', 'duplicate', 'collapse', 'order', 'name_hash', 'office_hash', 'method']:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                c, transcript = fixture(root)
                records = transcript['occurrences']
                if mode == 'missing': records.pop()
                elif mode == 'duplicate': records.append(copy.deepcopy(records[0]))
                elif mode == 'collapse': records[1] = copy.deepcopy(records[0])
                elif mode == 'order': records.reverse()
                elif mode == 'method': records[0]['transcription_method'] = 'MODEL_OCR'
                else: records[0][mode.replace('_hash', '_utf8_sha256')] = '0' * 64
                save_inputs(root, c, transcript)
                self.rejected(root, c)

    def test_transcript_audit_and_release_mismatch_or_extra_fields_refused(self):
        for mode in ['audit_status', 'audit_witness', 'audit_extra', 'transcript_schema', 'transcript_extra', 'release_snapshot', 'reviewed_code']:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                c, transcript = fixture(root)
                ref = c['independent_transcription_audit']
                if mode.startswith('audit'):
                    data = json.loads((root / ref['path']).read_text())
                    if mode == 'audit_status': data['status'] = 'PASS_ALL_FINAL_BALLOTS'
                    elif mode == 'audit_witness': data['approved_occurrences'][0]['name_utf8_sha256'] = '0' * 64
                    else: data['names'] = 'DEMO PRIVATE'
                elif mode.startswith('transcript'):
                    ref = c['transcription']
                    data = json.loads((root / ref['path']).read_text())
                    if mode == 'transcript_schema': data['schema_version'] = True
                    else: data['extra'] = 'DEMO PRIVATE'
                else:
                    ref = c['release_documents'][1]
                    data = json.loads((root / ref['path']).read_text())
                    data['source_snapshot_sha256' if mode == 'release_snapshot' else 'module_sha256'] = '0' * 64
                bound = bind_json(root, ref['path'], data)
                ref.update(bound)
                if mode.startswith('audit'): c['actual_execution_release']['independent_literal_transcription_audit_sha256'] = ref['sha256']
                elif mode.startswith('transcript'): c['actual_execution_release']['trusted_private_transcript_sha256'] = ref['sha256']
                else: c['actual_execution_release'][ref['role']] = ref['sha256']
                self.rejected(root, c)

    def test_first_middle_final_source_render_transcript_caller_coedit_fixed_authority(self):
        # Each pass has5 PDF and47 render reads. Attack includes second-pass final render.
        for position in [0, 5, 25, 51, 52, 103]:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                c, _ = fixture(root)
                original = m.bound_file
                count = [0]
                def read(root_arg, relative, *args, **kwargs):
                    if relative.startswith('data/raw/'):
                        if count[0] == position:
                            for s in c['sources']:
                                q = root / s['path']; raw = q.read_bytes() + b'ALTERED'; q.write_bytes(raw)
                                s.update(sha256=m.digest(raw), bytes=len(raw))
                            for p in c['pages']:
                                q = root / p['render_path']; raw = q.read_bytes() + b'ALTERED'; q.write_bytes(raw)
                                p['render_sha256'] = m.digest(raw)
                            c['actual_execution_release']['approved'] = False
                        count[0] += 1
                    return original(root_arg, relative, *args, **kwargs)
                with runtime(root, c), patch.object(m, 'bound_file', side_effect=read), self.assertRaises(m.DocumentsRejected):
                    m.read_sources(root, c)
                self.assertEqual(count[0], position + 1)

    def test_input_transcript_or_audit_changes_between_passes_refused(self):
        for key in ['transcription', 'independent_transcription_audit']:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                c, _ = fixture(root)
                original = m._reconcile
                def altered(*args):
                    result = original(*args)
                    q = root / c[key]['path']; q.write_bytes(q.read_bytes() + b'ALTERED')
                    c[key]['sha256'] = m.digest(q.read_bytes()); c[key]['bytes'] = q.stat().st_size
                    return result
                with runtime(root, c), patch.object(m, '_reconcile', side_effect=altered), self.assertRaises(m.DocumentsRejected):
                    m.read_sources(root, c)

    def test_path_symlink_import_origin_missing_file_and_size_limits(self):
        for mode in ['traversal', 'symlink', 'origin', 'missing', 'pdf_size', 'render_size', 'transcript_size']:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                c, _ = fixture(root)
                source = c['sources'][0]
                if mode == 'traversal': source['path'] = 'data/raw/../elsewhere'
                elif mode == 'symlink':
                    q = root / source['path']; q.rename(q.with_suffix('.other')); q.symlink_to(q.with_suffix('.other').name)
                elif mode == 'missing': (root / source['path']).unlink()
                elif mode == 'pdf_size': (root / source['path']).write_bytes(b'x' * 1048577)
                elif mode == 'render_size': (root / c['pages'][0]['render_path']).write_bytes(b'x' * 8388609)
                elif mode == 'transcript_size': c['transcription']['bytes'] = 65537
                with runtime(root, c), ExitStack() as stack:
                    if mode == 'origin': stack.enter_context(patch.object(m, '__file__', '/foreign/alabama_documents_v1.py'))
                    with self.assertRaises(m.DocumentsRejected): m.read_sources(root, c)

    def test_parser_cancel_systemexit_errors_type_only_no_write_or_partial_result(self):
        for stage in ['verify_inputs', '_reconcile']:
            for error in [RuntimeError, KeyboardInterrupt, SystemExit]:
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td).resolve()
                    c, _ = fixture(root)
                    before = identities(root)
                    expected = error if error in (KeyboardInterrupt, SystemExit) else m.DocumentsRejected
                    with runtime(root, c), patch.object(m, stage, side_effect=error('DEMO PRIVATE')), self.assertRaises(expected) as cm:
                        m.read_sources(root, c)
                    self.assertEqual(before, identities(root))
                    self.assertNotIn('DEMO', str(cm.exception))
                    self.assertIsNone(cm.exception.__context__)

    def test_closed_metadata_limits_custom_hooks_duplicates_nonfinite_and_boolean_unknowns(self):
        class Evil(dict):
            def items(self): raise AssertionError('PRIVATE HOOK')
        for value in [Evil(), {'v': float('nan')}, {'v': [0] * 9000}, {'v': 'x' * 8193}]:
            with self.assertRaises(ValueError): m.closed_snapshot(value)
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}']:
            with self.assertRaises(ValueError): m.strict_json(raw)
        c = json.loads((REPO / CONTRACT).read_text())
        for key in c['unknowns']:
            changed = copy.deepcopy(c); changed['unknowns'][key] = False
            with patch.object(m, 'root_guard') as guard, self.assertRaises(m.DocumentsRejected): m.read_sources('/unused', changed)
            guard.assert_not_called()

    def test_private_run_artifacts_package_refused_and_no_bundle_values_in_repr(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            c, _ = fixture(root)
            with runtime(root, c): result = m.read_sources(root, c)
            with RunStore(root, 'E01', {'kind': 'AUTHORED_AL_PRIVACY_ONLY'}, kind='MOCK') as run:
                run.write('al_occurrences.local.json', result.private_payload())
                run.finish({'status': 'AUTHORED_PRIVACY_FIXTURE_ONLY'})
            with self.assertRaisesRegex(ValueError, 'local-only'): build_package(root, root / 'unsafe.zip', [run.run_id])
            self.assertFalse((root / 'unsafe.zip').exists())
            self.assertNotIn('DEMO', repr(result))

    def test_public_consumer_unknown_schema_roles_names_coercion_and_adoption_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            c, _ = fixture(root)
            with runtime(root, c): public = m.read_sources(root, c).public_diagnostics()
            changes = [lambda x: x.update(schema_version=True), lambda x: x.update(schema_version=2),
                       lambda x: x.update(official_name_literal='DEMO PRIVATE'),
                       lambda x: x.update(source_adoption=True),
                       lambda x: x.update(document_supported_name_group_count=True),
                       lambda x: x['document_role_counts'].update(FINAL_BALLOT=1),
                       lambda x: x['source_hashes'].update(UNKNOWN='0' * 64),
                       lambda x: x['typed_unknowns'].update(legal_nominee=False)]
            for change in changes:
                altered = copy.deepcopy(public); change(altered)
                with self.assertRaises(ValueError): m.validate_public(altered)

    def test_altered_page_inventory_null_receipt_and_audited_unknowns_default_deny(self):
        for mode in ['duplicate_page', 'missing_page', 'fake_source', 'null_authority', 'unknown_boolean']:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td).resolve()
                c, _ = fixture(root)
                if mode == 'duplicate_page': c['pages'][1] = copy.deepcopy(c['pages'][0])
                elif mode == 'missing_page': c['pages'].pop()
                elif mode == 'fake_source': c['sources'][0]['source_id'] = 'OTHER'
                elif mode == 'null_authority': c['actual_execution_release']['source_read_authorization'] = None
                else: c['unknowns']['legal_nominee'] = False
                self.rejected(root, c)

    def test_existing_viewer_handler_refuses_private_traversal_and_query_paths_without_IO(self):
        # Exercise existing handler logic without opening sockets or sending GETs.
        from types import SimpleNamespace
        from unittest.mock import Mock
        from civiclab import dashboard
        captured = []
        def server(address, handler):
            captured.append(handler)
            return SimpleNamespace(server_port=0, serve_forever=lambda: None, server_close=lambda: None)
        with tempfile.TemporaryDirectory() as td:
            with patch.object(dashboard, 'ThreadingHTTPServer', side_effect=server), patch('builtins.print'):
                dashboard.serve(td, port=0)
            for path in ['/al_occurrences.local.json', '/data/processed/e01_al_authored/transcript.local.json',
                         '/../al_occurrences.local.json', '/%2e%2e/al_occurrences.local.json',
                         '/snapshot.json?private=al_occurrences.local.json', '/index.html/../al_occurrences.local.json',
                         '/data/raw/e01_ballots_batch04_v1/al_state_democratic.pdf']:
                handler = object.__new__(captured[0]); handler.path = path; handler.send_error = Mock()
                with patch.object(Path, 'open', side_effect=AssertionError('NO_PRIVATE_PATH_IO')):
                    handler.do_GET()
                handler.send_error.assert_called_once_with(404)


if __name__ == '__main__':
    unittest.main()
