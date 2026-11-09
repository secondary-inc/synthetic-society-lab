"""Reader-double checks and generated PDF bytes; no PDF library import here."""
from io import BytesIO
import json
import logging
import unittest
from unittest.mock import patch
import warnings

from civiclab.e01.clerk2020_native_inventory_v1 import (
    InventoryRefused, SOURCES, actual_source_factory, inspect_snapshot,
)


def generated_pdf(pages=2, catalog_extra=b'', content=b'AUTHORED DEMO FORMAT FIXTURE'):
    """Minimal genuine PDF syntax authored here, never obtained from a source.

    Its acceptance by the real pinned library remains untested until an explicit
    finite runtime-fixture review. Reader-double tests do not prove PDF validity.
    """
    assert type(pages) is int and 1 <= pages <= 100
    assert type(content) is bytes and all(32 <= c < 127 for c in content)
    content = content.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')
    kids = b' '.join(str(4 + 2 * i).encode() + b' 0 R' for i in range(pages))
    objects = [b'<< /Type /Catalog /Pages 2 0 R ' + catalog_extra + b' >>',
               b'<< /Type /Pages /Kids [ ' + kids + b' ] /Count ' + str(pages).encode() + b' >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for i in range(pages):
        stream = b'BT /F1 10 Tf 72 720 Td (' + content + b') Tj ET\n'
        objects.extend([
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            b'/Resources << /Font << /F1 3 0 R >> >> /Contents '
            + str(5 + 2 * i).encode() + b' 0 R >>',
            b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'endstream',
        ])
    result = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(str(i).encode() + b' 0 obj\n' + obj + b'\nendobj\n')
    startxref = len(result)
    result.extend(b'xref\n0 ' + str(len(offsets)).encode() + b'\n0000000000 65535 f \n')
    for offset in offsets[1:]:
        result.extend(('%010d 00000 n \n' % offset).encode())
    result.extend(b'trailer\n<< /Size ' + str(len(offsets)).encode()
                  + b' /Root 1 0 R >>\nstartxref\n' + str(startxref).encode() + b'\n%%EOF\n')
    return bytes(result)


class Page:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def extract_text(self, **kwargs):
        self.calls.append(kwargs)
        return self.text


class Reader:
    def __init__(self, pages=None, root=None):
        self.pages = [Page('AUTHORED PRIVATE TEXT')] * 2 if pages is None else pages
        self.is_encrypted = False
        self.root_object = {'/Type': '/Catalog'} if root is None else root
        self.calls = []

    def factory(self, stream, **kwargs):
        assert isinstance(stream, BytesIO)
        assert kwargs == {'strict': True}
        self.calls.append((len(stream.getvalue()), kwargs))
        return self


def inspect(reader, **kwargs):
    return inspect_snapshot(generated_pdf(), 'DEMO_NATIVE', reader.factory,
                            authored_fixture=True, fixture_pages=2, **kwargs)


def exercise_native_generated_pdf(reader_factory):
    """Only for a separately released finite generated-fixture runtime pass.

    No actual Clerk paths or bytes are accessed. The caller independently reviews
    and supplies the native reader; this function does not import a PDF library.
    It makes exactly four reader attempts: 81p,38p, active1p and malformed1p.
    """
    counts = []
    for pages in [81, 38]:
        out = inspect_snapshot(generated_pdf(pages), 'DEMO_NATIVE', reader_factory,
                               authored_fixture=True, fixture_pages=pages)
        counts.append(json.loads(out['public_diagnostics'])['page_count'])
    for raw in [generated_pdf(1, b'/OpenAction << /S /JavaScript /JS (DEMO) >>'),
                b'%PDF-1.4\nnot a PDF object graph\n%%EOF\n']:
        try:
            inspect_snapshot(raw, 'DEMO_NATIVE', reader_factory,
                             authored_fixture=True, fixture_pages=1)
        except InventoryRefused:
            continue
        raise AssertionError('NATIVE_NEGATIVE_FIXTURE_ACCEPTED')
    return {'label': 'MOCK_GENERATED_PDF_ONLY', 'reader_attempts': 4,
            'expected_page_extractions': 119, 'positive_page_counts': counts,
            'negative_cases_refused': 2, 'actual_source_reads': 0, 'model_calls': 0}


class NativeAdapterTests(unittest.TestCase):
    def test_strict_one_parse_and_plain_extraction(self):
        pages = [Page('DEMO one'), Page('DEMO two')]
        r = Reader(pages)
        out = inspect(r)
        private = json.loads(out['private_projection'])
        public = json.loads(out['public_diagnostics'])
        self.assertEqual(len(r.calls), 1)
        self.assertEqual(pages[0].calls, [{'extraction_mode': 'plain'}])
        self.assertEqual(private['label'], 'MOCK')
        self.assertEqual(public['page_count'], 2)
        self.assertFalse(public['source_or_feature_adoption'])

    def test_private_text_not_public(self):
        out = inspect(Reader())
        self.assertIn(b'AUTHORED PRIVATE TEXT', out['private_projection'])
        self.assertNotIn(b'AUTHORED PRIVATE TEXT', out['public_diagnostics'])
        self.assertEqual(json.loads(out['public_diagnostics'])['candidate_or_vote_records_parsed'], 0)

    def test_unknown_roles_and_page_counts_preserved(self):
        out = inspect(Reader())
        private = json.loads(out['private_projection'])
        for i, row in enumerate(private['pages'], 1):
            self.assertEqual(row['physical_pdf_page_1_based'], i)
            self.assertEqual(row['source_role_UNKNOWN_UNREVIEWED'], 'UNKNOWN')
            self.assertEqual(row['layout_quality_UNKNOWN_UNVERIFIED'], 'UNKNOWN')
        self.assertFalse(private['printed_dates_or_roles_adopted'])

    def test_encrypted_refuses_before_text(self):
        r = Reader()
        r.is_encrypted = True
        with self.assertRaises(InventoryRefused):
            inspect(r)
        self.assertEqual(r.pages[0].calls, [])

    def test_bool_encryption_property_not_coerced(self):
        for value in [0, None, 'false']:
            r = Reader()
            r.is_encrypted = value
            with self.assertRaises(InventoryRefused):
                inspect(r)

    def test_wrong_page_count_before_text(self):
        r = Reader([Page('x')])
        with self.assertRaises(InventoryRefused):
            inspect(r)
        self.assertEqual(r.pages[0].calls, [])

    def test_active_and_external_graph_keys(self):
        for key in ['/OpenAction', '/AA', '/JS', '/JavaScript', '/URI', '/EF', '/EmbeddedFiles', '/A']:
            with self.subTest(key=key), self.assertRaises(InventoryRefused):
                inspect(Reader(root={'/Type': '/Catalog', key: 'DEMO'}))

    def test_nested_external_filespec_and_form_refused(self):
        for value in [{'/Type': '/Filespec', '/F': 'DEMO'}, {'/AcroForm': {}}, {'/Type': '/EmbeddedFile'}]:
            with self.assertRaises(InventoryRefused):
                inspect(Reader(root={'/Names': {'/Nested': value}}))

    def test_shared_parent_links_are_finite(self):
        root = {'/Type': '/Catalog'}
        root['/Parent'] = root
        self.assertEqual(json.loads(inspect(Reader(root=root))['public_diagnostics'])['page_count'], 2)

    def test_structure_unknown_or_deep_refuses(self):
        for root in [object(), {'/Unknown': object()}, {'/Numeric': float('nan')}, {'/Numeric': float('inf')}]:
            with self.assertRaises(InventoryRefused):
                inspect(Reader(root=root))
        root = {}
        for _ in range(34):
            root = {'/Next': root}
        with self.assertRaises(InventoryRefused):
            inspect(Reader(root=root))

    def test_broad_object_bound(self):
        with self.assertRaises(InventoryRefused):
            inspect(Reader(root={'/Large': list(range(4097))}))

    def test_plain_text_type_and_character_caps(self):
        for text in [None, b'DEMO', 'x' * 40001, '\ud800']:
            with self.subTest(kind=type(text).__name__), self.assertRaises(InventoryRefused):
                inspect(Reader([Page(text), Page('x')]))

    def test_escaping_unicode_serialized_page_bound(self):
        out = inspect(Reader([Page('\x00\\"😀' * 2000), Page('é' * 40000)]))
        private = json.loads(out['private_projection'])
        for row in private['pages']:
            self.assertLessEqual(len(json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()), 2048)
        self.assertLessEqual(len(out['private_projection']), 2 * 2048 + 2048)

    def test_library_warning_is_refused_and_not_retained(self):
        def factory(stream, **kwargs):
            warnings.warn('DEMO_PRIVATE_WARNING')
            return Reader()
        with self.assertRaises(InventoryRefused) as caught:
            inspect_snapshot(generated_pdf(), 'DEMO_NATIVE', factory,
                             authored_fixture=True, fixture_pages=2)
        self.assertNotIn('DEMO_PRIVATE_WARNING', str(caught.exception))
        self.assertIsNone(caught.exception.__context__)

    def test_library_logging_refused_and_restored(self):
        logger = logging.getLogger('pypdf')
        original = logger.handlers[:], logger.propagate, logger.level, logger.disabled
        def factory(stream, **kwargs):
            logging.getLogger('pypdf.reader').warning('DEMO_PRIVATE_LOG')
            return Reader()
        with self.assertRaises(InventoryRefused) as caught:
            inspect_snapshot(generated_pdf(), 'DEMO_NATIVE', factory,
                             authored_fixture=True, fixture_pages=2)
        self.assertNotIn('DEMO_PRIVATE_LOG', str(caught.exception))
        self.assertEqual((logger.handlers, logger.propagate, logger.level, logger.disabled), original)

    def test_raw_parser_exception_chain_absent(self):
        def factory(stream, **kwargs):
            raise ValueError('DEMO_PRIVATE_PARSER_DETAIL')
        with self.assertRaises(InventoryRefused) as caught:
            inspect_snapshot(generated_pdf(), 'DEMO_NATIVE', factory,
                             authored_fixture=True, fixture_pages=2)
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn('DEMO_PRIVATE_PARSER_DETAIL', str(caught.exception))

    def test_stream_mutation_refuses(self):
        def factory(stream, **kwargs):
            stream.seek(0)
            stream.write(b'CHANGED')
            return Reader()
        with self.assertRaises(InventoryRefused):
            inspect_snapshot(generated_pdf(), 'DEMO_NATIVE', factory,
                             authored_fixture=True, fixture_pages=2)

    def test_actual_hash_gate_before_reader(self):
        r = Reader()
        for source_id in ['clerk2020_statistics', 'clerk2026_nominees', 'UNKNOWN']:
            with self.assertRaises(InventoryRefused):
                inspect_snapshot(generated_pdf(), source_id, r.factory)
        self.assertEqual(r.calls, [])

    def test_actual_source_factory_disabled(self):
        with self.assertRaises(InventoryRefused):
            actual_source_factory(enabled=True, approved=True, source='anything')

    def test_no_source_or_network_io_in_adapter(self):
        def refuse(*args, **kwargs):
            raise AssertionError('FORBIDDEN_ACTUAL_IO')
        with patch('builtins.open', refuse), patch('os.open', refuse), patch('socket.socket', refuse):
            out = inspect(Reader())
            self.assertEqual(json.loads(out['public_diagnostics'])['label'], 'MOCK')

    def test_generated_fixture_has_exact_xref_offsets(self):
        raw = generated_pdf(81)
        section = raw.split(b'xref\n', 1)[1].split(b'trailer', 1)[0].splitlines()
        rows = section[2:]
        self.assertEqual(len(rows), 165)
        for object_id, row in enumerate(rows, 1):
            offset = int(row[:10])
            self.assertTrue(raw[offset:].startswith(str(object_id).encode() + b' 0 obj'))

    def test_authored_fixture_limits_and_actual_roles_distinct(self):
        for count in [True, 0, 101]:
            with self.assertRaises(InventoryRefused):
                inspect_snapshot(generated_pdf(), 'DEMO_NATIVE', Reader().factory,
                                 authored_fixture=True, fixture_pages=count)
        self.assertNotEqual(SOURCES['clerk2020_statistics']['role'], SOURCES['clerk2026_nominees']['role'])


if __name__ == '__main__':
    unittest.main()
