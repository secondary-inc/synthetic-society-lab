"""Authored PDFs only, enabled solely by an isolated pypdf7 fixture target.

Normal legacy environments skip this class; they are never upgraded or silently
qualified. The bounded target runner asserts the real imported distribution.
"""
from io import BytesIO
import hashlib
import importlib.metadata
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab.e01.historical import extract_pdf,official_sections,official_candidate_votes


def authored_pdf(*,graphics=False):
    """Three genuine PDF pages authored here: two-column text, blank, vector-only."""
    lines=[(72,760,'AUTHORED PDF COMPATIBILITY FIXTURE'),(72,740,'MAINE'),
           (72,720,'FOR UNITED STATES SENATOR'),(72,700,'Amy Example, Democrat ........'),(430,700,'100'),
           (72,680,'Bob Other, Republican ........'),(430,680,'90'),
           (72,660,'FOR UNITED STATES REPRESENTATIVE'),(72,640,'Amy Example, Democrat ........'),(430,640,'500')]
    def escaped(value):return value.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
    stream=('\n'.join(f'BT /F1 12 Tf 1 0 0 1 {x} {y} Tm ({escaped(text)}) Tj ET' for x,y,text in lines)+'\n').encode()
    vector=b'q 0 0 10 10 re S Q\n'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
             b'<< /Type /Pages /Kids [4 0 R 6 0 R 7 0 R] /Count 3 >>',
             b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
             b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>',
             b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'endstream',
             b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>',
             b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> /Contents 8 0 R >>',
             b'<< /Length '+str(len(vector)).encode()+b' >>\nstream\n'+vector+b'endstream']
    raw=bytearray(b'%PDF-1.4\n');offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(raw));raw.extend(str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
    xref=len(raw);raw.extend(b'xref\n0 '+str(len(offsets)).encode()+b'\n0000000000 65535 f \n')
    for off in offsets[1:]:raw.extend(('%010d 00000 n \n'%off).encode())
    raw.extend(b'trailer\n<< /Size '+str(len(offsets)).encode()+b' /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n')
    return bytes(raw)


class FreshInstallPypdf7CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        target=os.environ.get('CIVICLAB_PYPDF7_FIXTURE_TARGET')
        if not target:raise unittest.SkipTest('Requires separately installed hash-verified fixture-only pypdf7 target')
        import pypdf
        cls.pypdf=pypdf;cls.target=Path(target).resolve()
        if pypdf.__version__!='7.0.1' or not Path(pypdf.__file__).resolve().is_relative_to(cls.target):
            raise AssertionError('Real pypdf7 must import from the explicit isolated target; no fallback')

    def test_real_wheel_distribution_and_import_are_isolated(self):
        self.assertEqual(importlib.metadata.version('pypdf'),'7.0.1')
        dist=importlib.metadata.distribution('pypdf')
        self.assertTrue(Path(dist.locate_file('pypdf/__init__.py')).resolve().is_relative_to(self.target))

    def test_real_pdf_layout_columns_blank_and_graphics_pages(self):
        raw=authored_pdf();before=hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory(prefix='AUTHORED_PYPDF7_') as tmp:
            path=Path(tmp)/'AUTHORED_ONLY.pdf';path.write_bytes(raw)
            pages=extract_pdf(path)
            self.assertEqual([p['pdf_page'] for p in pages],[1,2,3])
            self.assertIn('AUTHORED PDF COMPATIBILITY FIXTURE',pages[0]['text'])
            self.assertRegex(pages[0]['text'],r'Amy Example, Democrat \.{2,}\s{2,}100')
            self.assertRegex(pages[0]['text'],r'Bob Other, Republican \.{2,}\s{2,}90')
            self.assertEqual(pages[1]['text'],'');self.assertEqual(pages[2]['text'],'')
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)

    def test_real_extracted_layout_feeds_authored_senate_parser_not_house(self):
        with tempfile.TemporaryDirectory(prefix='AUTHORED_PYPDF7_') as tmp:
            path=Path(tmp)/'AUTHORED_ONLY.pdf';path.write_bytes(authored_pdf())
            section=official_sections(extract_pdf(path),2024)['ME']
        amy=official_candidate_votes(section,'Amy Example',2024,expected_party='DEMOCRAT')
        bob=official_candidate_votes(section,'Bob Other',2024,expected_party='REPUBLICAN')
        self.assertEqual((amy['votes'],bob['votes'],amy['pdf_page']),(100,90,1))
        self.assertNotEqual(amy['votes'],500)
        with self.assertRaisesRegex(ValueError,'party mismatch'):
            official_candidate_votes(section,'Amy Example',2024,expected_party='REPUBLICAN')

    def test_historical_adapter_forwards_layout_to_real_reader(self):
        actual=self.pypdf.PdfReader(BytesIO(authored_pdf()));calls=[]
        for page in actual.pages:
            if '/Contents' in page:
                original=page.extract_text
                def tracked(*args,_original=original,**kwargs):
                    calls.append(kwargs.copy());return _original(*args,**kwargs)
                page.extract_text=tracked
        with patch.object(self.pypdf,'PdfReader',return_value=actual):pages=extract_pdf(BytesIO(authored_pdf()))
        self.assertEqual(calls,[{'extraction_mode':'layout'},{'extraction_mode':'layout'}])
        self.assertIn('100',pages[0]['text']);self.assertEqual(pages[2]['text'],'')

    def test_malformed_authored_pdf_is_refused(self):
        from pypdf.errors import PdfReadError
        with self.assertRaises(PdfReadError):extract_pdf(BytesIO(b'%PDF-1.4\nAUTHORED BROKEN OBJECT GRAPH\n%%EOF\n'))

    def test_missing_optional_dependency_message_names_current_fresh_pin(self):
        import builtins
        original=builtins.__import__
        def controlled(name,*args,**kwargs):
            if name=='pypdf':raise ImportError('AUTHORED_MISSING_EXTRA')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=controlled):
            with self.assertRaisesRegex(RuntimeError,r'pypdf==7\.0\.1'):extract_pdf(BytesIO(b'AUTHORED_NOT_PARSED'))

if __name__=='__main__':unittest.main()
