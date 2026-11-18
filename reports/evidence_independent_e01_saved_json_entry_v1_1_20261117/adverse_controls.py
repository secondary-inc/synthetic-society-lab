"""Independently authored successor controls, under frozen authored guard."""
import runpy,unittest
from pathlib import Path
root=Path.cwd()
ns=runpy.run_path(str(root/'tests/test_e01_saved_json_entry_v1.py'),run_name='independent_entry_definitions')
original=ns['_authored_cases']
def extra(E,C,runtime,tmp,counters):
    suite=original(E,C,runtime,tmp,counters)
    first=next(iter(suite))
    closure=lambda f:dict(zip(f.__code__.co_freevars,(v.cell_contents for v in f.__closure__)))
    scope=closure(first.test_01_physical16_admission_one_reader_safe_ledger)
    fresh,execute,outcome=scope['fresh'],scope['execute'],scope['outcome']
    class Extra(unittest.TestCase):
        def test_independent_01_foreign_code_and_descriptor_are_ignored(self):
            class Foreign(RuntimeError):code='AUTHORED_PRIVATE_SENTINEL'
            self.assertEqual(E.safe_error(Foreign()),'UNCLASSIFIED_FAILURE')
            class Descriptor(RuntimeError):
                @property
                def code(self):raise AssertionError('FOREIGN_DESCRIPTOR_EVALUATED')
            self.assertEqual(E.safe_error(Descriptor()),'UNCLASSIFIED_FAILURE')
        def test_independent_02_subclass_and_tampering_are_rejected(self):
            class Subclass(E.Refused):
                @property
                def code(self):raise AssertionError('SUBCLASS_DESCRIPTOR_EVALUATED')
            self.assertEqual(E.safe_error(Subclass.__new__(Subclass)),'UNCLASSIFIED_FAILURE')
            e=E.Refused('SAVED_CAP');e.code='AUTHORED_PRIVATE_SENTINEL'
            self.assertEqual(E.safe_error(e),'UNCLASSIFIED_FAILURE')
            self.assertEqual(E.safe_error(E.Refused('AUTHORED_PRIVATE_SENTINEL')),'UNCLASSIFIED_FAILURE')
        def test_independent_03_known_code_and_unclassified_message(self):
            self.assertEqual(E.safe_error(E.Refused('SAVED_CAP')),'SAVED_CAP')
            self.assertEqual(E.safe_error(ValueError('AUTHORED_PRIVATE_SENTINEL')),'UNCLASSIFIED_FAILURE')
        def test_independent_04_authorized_foreign_error_failure_record(self):
            parts=fresh()
            class Foreign(RuntimeError):code='AUTHORED_PRIVATE_SENTINEL'
            error=Foreign()
            class Reader:
                mock_only=True
                def __call__(self,*args,**kwargs):raise error
            with self.assertRaises(Foreign) as caught:execute(parts,Reader())
            self.assertIs(caught.exception,error)
            raw=outcome(parts,'FAILURE.json').read_bytes()
            self.assertNotIn(b'AUTHORED_PRIVATE_SENTINEL',raw)
            self.assertEqual(E.strict(raw)['error_code'],'UNCLASSIFIED_FAILURE')
            self.assertFalse(outcome(parts,'COMPLETE.json').exists())
        def test_independent_05_foreign_descriptor_failure_still_records(self):
            parts=fresh()
            class Foreign(RuntimeError):
                @property
                def code(self):raise AssertionError('FOREIGN_DESCRIPTOR_EVALUATED')
            error=Foreign()
            class Reader:
                mock_only=True
                def __call__(self,*args,**kwargs):raise error
            with self.assertRaises(Foreign) as caught:execute(parts,Reader())
            self.assertIs(caught.exception,error)
            self.assertEqual(E.strict(outcome(parts,'FAILURE.json').read_bytes())['error_code'],'UNCLASSIFIED_FAILURE')
        def test_independent_06_shared_budget_counter_fails_closed(self):
            for key in ('saved_JSON_bytes','project_source_bytes','write_bytes'):
                with self.assertRaises(E.Refused):E.Budget(initial={key:-1})
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Extra));return suite
ns['_child_main'].__globals__['_authored_cases']=extra
raise SystemExit(ns['_child_main']())
