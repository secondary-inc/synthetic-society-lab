"""MOCK memory declarations/readers only; no source/PDF library/native/file reads."""
import copy
import json
import unittest
from unittest.mock import patch

from civiclab.e01 import clerk2020_source_format_adapter_v1 as a
from civiclab.e01 import clerk2020_native_inventory_v1 as original
from civiclab.e01.clerk2020_m2_v1_1_contracts import sha
from test_clerk2020_native_inventory_v1 import generated_pdf, Reader, Page


class SourceFormatAdapterTests(unittest.TestCase):
    def setUp(self):
        self.real_declarations = copy.deepcopy(a.SOURCES)
        self.raw = {name: generated_pdf(ref['pages']) for name, ref in a.SOURCES.items()}
        declarations = copy.deepcopy(a.SOURCES)
        for name, ref in declarations.items():
            ref.update(bytes=len(self.raw[name]), sha256=sha(self.raw[name]),
                       role='AUTHORED_MOCK_SOURCE_DECLARATION_NOT_REAL_CLERK')
        self.patches = [patch.object(a, 'SOURCES', declarations),
                        patch.object(original, 'SOURCES', declarations)]
        for item in self.patches: item.start()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()

    def inspect(self, source='clerk2020_statistics', factory=None, telemetry=None):
        pages = a.SOURCES[source]['pages']
        reader = Reader([Page('AUTHORED MOCK SOURCE FORMAT FIXTURE') for _ in range(pages)])
        state = a.SourceTelemetry() if telemetry is None else telemetry
        return a.inspect_source(self.raw[source], source, reader.factory if factory is None else factory,
                                telemetry=state), state

    def test_two_mocked_source_declarations_match_frozen_actual_mode_outputs(self):
        for source in a.SOURCES:
            output, state = self.inspect(source)
            count = a.SOURCES[source]['pages']
            expected = original.inspect_snapshot(self.raw[source], source,
                Reader([Page('AUTHORED MOCK SOURCE FORMAT FIXTURE') for _ in range(count)]).factory)
            self.assertEqual(output, expected)
            self.assertEqual(state.stage, 'COMPLETE')
            self.assertIsNone(state.first_exception)
            private = json.loads(output['private_projection'])
            self.assertEqual(private['candidate_or_vote_records_parsed'], 0)
            self.assertFalse(private['printed_dates_or_roles_adopted'])
            self.assertEqual(private['source_role'], 'AUTHORED_MOCK_SOURCE_DECLARATION_NOT_REAL_CLERK')

    def test_real_declarations_unpatched_are_exact_and_distinct_roles(self):
        self.assertEqual(self.real_declarations['clerk2020_statistics'], {
            'bytes': 602172, 'sha256': '666b2a1f673f263087c141c4d44b0dce47cbddc8f4df27fbc8b415cf05842b76',
            'pages': 81, 'role': 'HISTORICAL_2020_COUNTS_NOT_2026_OUTCOMES', 'worker_output_bytes': 167936})
        self.assertEqual(self.real_declarations['clerk2026_nominees'], {
            'bytes': 257739, 'sha256': 'cb2e4194c88042cf22f8589fb6b8c352d29b501f96abc62a962b6cc52e2c28a8',
            'pages': 38, 'role': 'DATED_2026_NOMINEES_NOT_OUTCOMES_OR_FINAL_BALLOTS', 'worker_output_bytes': 79872})

    def test_unknown_hash_or_source_refused_before_reader(self):
        calls = []
        def never(*args, **kwargs): calls.append(1); raise AssertionError()
        for raw, source in [(b'%PDF-WRONG', 'clerk2020_statistics'),
                            (self.raw['clerk2020_statistics'], 'DEMO_FAKE')]:
            with self.assertRaises(a.InventoryRefused):
                a.inspect_source(raw, source, never, telemetry=a.SourceTelemetry())
        self.assertEqual(calls, [])

    def test_no_authored_true_or_fixture_page_workaround(self):
        with self.assertRaises(TypeError):
            a.inspect_source(self.raw['clerk2020_statistics'], 'clerk2020_statistics', lambda: None,
                             telemetry=a.SourceTelemetry(), authored_fixture=True)
        with self.assertRaises(a.InventoryRefused): original.actual_source_factory()

    def test_wrong_page_count_refused(self):
        state = a.SourceTelemetry()
        with self.assertRaises(a.InventoryRefused):
            self.inspect(factory=Reader([Page('MOCK')]).factory, telemetry=state)
        self.assertEqual(state.first_exception['stage'], 'READER_CONTRACT')

    def test_active_structure_refused_and_code_identity_retained(self):
        state = a.SourceTelemetry()
        with self.assertRaises(a.InventoryRefused):
            self.inspect(factory=Reader([Page('MOCK')]*81, root={'/OpenAction':'MOCK'}).factory,
                         telemetry=state)
        self.assertEqual(state.first_exception['stage'], 'STRUCTURE')
        self.assertTrue({'inspect_source','_check_structure','require'} <=
                        {r['function'] for r in state.first_exception['frames']})

    def test_import_guard_failure_survives_source_sanitizer(self):
        state = a.SourceTelemetry()
        class GuardedPage:
            def extract_text(self, **kwargs): state.guard('import', ('UNRETAINED_SECRET',))
        with self.assertRaises(a.InventoryRefused) as caught:
            self.inspect(factory=Reader([GuardedPage()]*81).factory, telemetry=state)
        self.assertIsNone(caught.exception.__context__)
        self.assertEqual(state.first_guard, {'event':'import'})
        self.assertEqual(state.first_exception['stage'], 'PAGE_EXTRACTION')
        self.assertEqual(state.first_exception['page'], 1)
        self.assertNotIn('SECRET',json.dumps(state.first_exception))

    def test_private_windows_remain_bounded_and_not_a_complete_record_parse(self):
        output, _ = self.inspect(factory=Reader([Page('MOCK ' * 3000)]*81).factory)
        private = json.loads(output['private_projection'])
        self.assertFalse(private['retained_full_document'])
        self.assertLessEqual(len(output['private_projection']), 167936)
        self.assertTrue(all(p['omitted_text_utf8_bytes'] > 0 for p in private['pages']))
        self.assertTrue(all(p['layout_quality_UNKNOWN_UNVERIFIED']=='UNKNOWN' for p in private['pages']))

    def test_unknown_hostile_exception_attributes_never_read(self):
        touched=[]
        class Evil(ValueError):
            def __getattribute__(self, name): touched.append(name);raise RuntimeError()
        state=a.SourceTelemetry();state.observe(Evil())
        self.assertEqual(state.first_exception['type'],'UNKNOWN_EXACT_TYPE')
        self.assertEqual(touched,[])

    def test_telemetry_subclass_refused(self):
        class Sub(a.SourceTelemetry): pass
        with self.assertRaises(a.Refused): self.inspect(telemetry=Sub())


if __name__ == '__main__': unittest.main()
