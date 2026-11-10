"""Authored callbacks only: no installed PDF library, native/source or network I/O."""
import json
import unittest
from unittest.mock import patch

from civiclab.e01 import clerk2020_generated_guard_inventory_v1 as g
from civiclab.e01 import clerk2020_native_inventory_v1 as frozen
from civiclab.e01.clerk2020_m2_v1_1_contracts import canonical
from test_clerk2020_native_inventory_v1 import generated_pdf, Reader, Page


class GuardedInventoryTests(unittest.TestCase):
    def parse(self, reader=None, telemetry=None, raw=None):
        telemetry = g.GeneratedTelemetry() if telemetry is None else telemetry
        return g.inspect_snapshot(generated_pdf(1) if raw is None else raw,
                                  'DEMO_GUARDED',
                                  (Reader([Page('AUTHORED DEMO FORMAT FIXTURE')]).factory
                                   if reader is None else reader),
                                  authored_fixture=True, fixture_pages=1,
                                  telemetry=telemetry), telemetry

    def test_original_output_matches_exactly(self):
        output, state = self.parse()
        original = frozen.inspect_snapshot(generated_pdf(1), 'DEMO_GUARDED',
                    Reader([Page('AUTHORED DEMO FORMAT FIXTURE')]).factory,
                    authored_fixture=True, fixture_pages=1)
        self.assertEqual(output, original)
        self.assertEqual(state.stage, 'COMPLETE')
        self.assertIsNone(state.first_exception)
        self.assertIsNone(state.first_guard)

    def test_guard_event_policy_matches_frozen(self):
        for event in list(g.DENIED) + ['socket.connect', 'socket.__new__', 'os.execve']:
            with self.subTest(event=event):
                state = g.GeneratedTelemetry()
                with self.assertRaises(g.qualification.QualificationStopped):
                    state.guard(event, ('SECRET_PATH',))
                self.assertNotIn('SECRET_PATH', json.dumps(state.first_guard))
        state = g.GeneratedTelemetry()
        state.guard('sys.addaudithook', ())
        self.assertIsNone(state.first_guard)

    def test_first_guard_is_retained_bounded(self):
        state = g.GeneratedTelemetry()
        for event in ['import', 'open', 'socket.' + 'x' * 10000]:
            with self.assertRaises(g.qualification.QualificationStopped):
                state.guard(event, ('SECRET',))
        self.assertEqual(state.first_guard, {'event': 'import'})

    def test_reader_failure_stage_and_no_message(self):
        state = g.GeneratedTelemetry()
        def bad(*args, **kwargs):
            raise ValueError('SECRET_PATH_SOURCE')
        with self.assertRaises(g.InventoryRefused) as caught:
            self.parse(bad, state)
        self.assertIsNone(caught.exception.__context__)
        self.assertEqual(state.first_exception['stage'], 'READER_CONSTRUCTION')
        self.assertEqual(state.first_exception['type'], 'ValueError')
        self.assertNotIn('SECRET', json.dumps(state.first_exception))
        self.assertTrue(any(r['function'] == 'inspect_snapshot' for r in state.first_exception['frames']))

    def test_extraction_guard_survives_sanitizing_boundary(self):
        state = g.GeneratedTelemetry()
        class BlockedPage:
            def extract_text(self, **kwargs):
                state.guard('import', ('UNRETAINED_NAME',))
        with self.assertRaises(g.InventoryRefused) as caught:
            self.parse(Reader([BlockedPage()]).factory, state)
        self.assertIsNone(caught.exception.__context__)
        self.assertEqual(state.first_exception['stage'], 'PAGE_EXTRACTION')
        self.assertEqual(state.first_exception['page'], 1)
        guard_frames = [r for r in state.first_exception['frames'] if r['function'] == 'parse_guard']
        self.assertEqual(len(guard_frames), 1)
        self.assertGreater(guard_frames[0]['line'], g.GeneratedTelemetry.guard.__code__.co_firstlineno)
        self.assertEqual(state.first_guard, {'event': 'import'})

    def test_structure_predicate_has_original_code_identity(self):
        state = g.GeneratedTelemetry()
        bad = Reader([Page('DEMO')], root={'/OpenAction': 'SECRET'})
        with self.assertRaises(g.InventoryRefused):
            self.parse(bad.factory, state)
        self.assertEqual(state.first_exception['stage'], 'STRUCTURE')
        names = {r['function'] for r in state.first_exception['frames']}
        self.assertTrue({'_check_structure', 'require', 'inspect_snapshot'} <= names)
        self.assertIsNone(state.first_guard)

    def test_unknown_exception_does_not_read_descriptor(self):
        touched = []
        class BadMeta(type):
            def __eq__(self, other):
                touched.append('eq'); raise RuntimeError()
            def __hash__(self):
                touched.append('hash'); raise RuntimeError()
        class Evil(ValueError, metaclass=BadMeta):
            def __getattribute__(self, name):
                touched.append(name); raise RuntimeError()
        state = g.GeneratedTelemetry()
        state.observe(Evil())
        self.assertEqual(state.first_exception['type'], 'UNKNOWN_EXACT_TYPE')
        self.assertEqual(state.first_exception['frames'], [])
        self.assertEqual(touched, [])

    def test_first_exception_not_overwritten(self):
        state = g.GeneratedTelemetry()
        state.stage = 'STRUCTURE'
        state.observe(ValueError('A'))
        first = canonical(state.first_exception)
        state.stage = 'OUTPUT_CONTRACT'
        state.observe(TypeError('B'))
        self.assertEqual(canonical(state.first_exception), first)

    def test_traceback_capped_without_untrusted_frame_names(self):
        def recursive(n):
            if n: return recursive(n-1)
            raise ValueError('SECRET')
        state = g.GeneratedTelemetry()
        try: recursive(50)
        except ValueError as exc: state.observe(exc)
        self.assertTrue(state.first_exception['traceback_truncated'])
        self.assertEqual(state.first_exception['frames'], [])

    def test_source_mode_always_refused_before_reader(self):
        def never(*args, **kwargs):
            self.fail('source reader called')
        with self.assertRaises(g.Refused):
            g.inspect_snapshot(b'%PDF-SECRET', 'clerk2020_statistics', never,
                               telemetry=g.GeneratedTelemetry())

    def test_telemetry_subclass_refused_before_reader(self):
        class Sub(g.GeneratedTelemetry): pass
        with self.assertRaises(g.Refused): self.parse(telemetry=Sub())


if __name__ == '__main__':
    unittest.main()
