"""No actual reader: closed-code failure projection from the A02 entry."""
from pathlib import Path
import runpy
import unittest

ROOT=Path(__file__).resolve().parents[1]


class FailureProjectionTests(unittest.TestCase):
    def setUp(self):
        self.n=runpy.run_path(str(ROOT/'reports/evidence_e01_fec2020_actual_20261118/read_candidate_once_a02_v1_1.py'),run_name='inert_diagnostic_test')
        self.safe=self.n['safe_failure']

    def test_known_guard_code(self):
        self.assertEqual(self.safe(RuntimeError('FEC_A02_READ_BOUND'))['safe_code'],'FEC_A02_READ_BOUND')

    def test_arbitrary_uppercase_private_text_is_omitted(self):
        self.assertEqual(self.safe(RuntimeError('AUTHORED_PRIVATE_CELL'))['safe_code'],'OMITTED')

    def test_foreign_string_method_is_not_called(self):
        class Foreign(Exception):
            def __str__(self):raise AssertionError('foreign method invoked')
        self.assertEqual(self.safe(Foreign())['error_type'],'OTHER')

    def test_spoofed_parser_name_is_not_identity(self):
        Fake=type('ParserRefused',(Exception,),{})
        self.assertEqual(self.safe(Fake('ARCHIVE_MEMBER'))['error_type'],'OTHER')

    def test_runtime_subclass_is_not_identity(self):
        class Fake(RuntimeError):pass
        self.assertEqual(self.safe(Fake('FEC_A02_READ_BOUND'))['error_type'],'OTHER')

    def test_only_exact_parser_and_owned_code(self):
        class ExactParser(ValueError):pass
        self.safe.__globals__['_PARSER_REFUSED_TYPE']=ExactParser
        self.assertEqual(self.safe(ExactParser('ARCHIVE_MEMBER'))['safe_code'],'ARCHIVE_MEMBER')
        self.assertEqual(self.safe(ExactParser('AUTHORED_PRIVATE_CELL'))['safe_code'],'OMITTED')

    def test_nonprimitive_argument_is_not_coerced(self):
        class Foreign:
            def __str__(self):raise AssertionError('foreign method invoked')
        self.assertEqual(self.safe(RuntimeError(Foreign()))['safe_code'],'OMITTED')


if __name__=='__main__':unittest.main(verbosity=2)
