"""Authored independent controls, run under the frozen suite's existing guard."""
import runpy,sys,unittest
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
    observations={}
    class Extra(unittest.TestCase):
        def test_independent_01_foreign_code_is_not_public_diagnostic(self):
            class Foreign(RuntimeError):code='AUTHORED_PRIVATE_SENTINEL'
            result=E.safe_error(Foreign())
            observations['foreign_code_copied']=result=='AUTHORED_PRIVATE_SENTINEL'
            self.assertEqual(result,'UNCLASSIFIED_FAILURE')
        def test_independent_02_error_code_descriptor_is_not_executed(self):
            class Foreign(RuntimeError):
                @property
                def code(self):raise RuntimeError('AUTHORED_PRIVATE_DESCRIPTOR')
            result=None
            try:result=E.safe_error(Foreign())
            except RuntimeError:observations['foreign_descriptor_executed']=True
            else:observations['foreign_descriptor_executed']=False
            self.assertEqual(result,'UNCLASSIFIED_FAILURE')
        def test_independent_03_known_refusal_and_message_redaction(self):
            self.assertEqual(E.safe_error(E.Refused('SAVED_CAP')),'SAVED_CAP')
            self.assertEqual(E.safe_error(ValueError('AUTHORED_PRIVATE_SENTINEL')),'UNCLASSIFIED_FAILURE')
        def test_independent_04_negative_shared_counters(self):
            for key in ('saved_JSON_bytes','project_source_bytes','write_bytes'):
                with self.assertRaises(E.Refused):E.Budget(initial={key:-1})
        def test_independent_05_failure_ledger_redaction(self):
            parts=fresh()
            class Foreign(RuntimeError):code='AUTHORED_PRIVATE_SENTINEL'
            def reader(*args,**kwargs):raise Foreign()
            with self.assertRaises(Foreign):execute(parts,reader)
            raw=outcome(parts,'FAILURE.json').read_bytes()
            observations['foreign_code_in_failure_file']=b'AUTHORED_PRIVATE_SENTINEL' in raw
            self.assertNotIn(b'AUTHORED_PRIVATE_SENTINEL',raw)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Extra))
    return suite
ns['_child_main'].__globals__['_authored_cases']=extra
raise SystemExit(ns['_child_main']())
