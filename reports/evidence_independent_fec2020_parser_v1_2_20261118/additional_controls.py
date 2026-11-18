"""Independent authored controls, no actual workbook/owner/key/network."""
import io
import unittest
import zipfile
from civiclab.e01 import fec2020_parser_v1 as p


def tiny_zip(name,body):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(name,body)
    raw=stream.getvalue()
    if len(raw)>8388608:raise AssertionError('review ZIP bound')
    return raw


class IndependentArchiveControls(unittest.TestCase):
    def test_ascii_DTD_refused_positive_control(self):
        raw=tiny_zip('xl/worksheets/sheet1.xml',b'<!DOCTYPE x [<!ENTITY e "AUTHORED">]><x>&e;</x>')
        with self.assertRaises(p.ParserRefused):p.archive_preflight(raw)

    def test_utf16_DTD_refused(self):
        xml='<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE Relationships [<!ENTITY e "AUTHORED">]><Relationships><Relationship Id="&e;"/></Relationships>'
        raw=tiny_zip('xl/_rels/workbook.xml.rels',xml.encode('utf-16'))
        with self.assertRaises(p.ParserRefused):p.archive_preflight(raw)

    def test_uppercase_XML_DTD_refused(self):
        raw=tiny_zip('xl/worksheets/sheet1.XML',b'<!DOCTYPE x [<!ENTITY e "AUTHORED">]><x>&e;</x>')
        with self.assertRaises(p.ParserRefused):p.archive_preflight(raw)

    def test_absolute_and_traversal_members_refused(self):
        for name in ('/xl/workbook.xml','xl/../workbook.xml','xl\\workbook.xml'):
            with self.subTest(name=name),self.assertRaises(p.ParserRefused):
                p.archive_preflight(tiny_zip(name,b'<x/>'))

    def test_external_relationship_refused_positive_control(self):
        raw=tiny_zip('xl/_rels/workbook.xml.rels',b'<Relationships><Relationship TargetMode="External" Target="https://example.invalid/AUTHORED"/></Relationships>')
        with self.assertRaises(p.ParserRefused):p.archive_preflight(raw)


if __name__=='__main__':unittest.main(verbosity=2)
