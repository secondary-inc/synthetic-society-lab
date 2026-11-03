"""Authored exact main-table/nested-print/inline-XLSX Delaware fixtures."""
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
import xml.etree.ElementTree as E
from civiclab.e01 import delaware_v1_7 as d


def html(*,writein=False,duplicate=False,bad_status=False):
    header=['Office','County']+([] if writein else ['Party'])+['Candidate','Status','Filed'];rows=[]
    names=['DEMO WRITEIN A','DEMO WRITEIN B','DEMO WRITEIN C'] if writein else ['DEMO A','DEMO B']
    for i,name in enumerate(names):
        cell='<span class="main-span">'+name+'</span><span class="sub-span">DEMO PRIVATE CONTACT<table><tr><td>U.S. Senator</td><td>Nested Duplicate</td></tr></table></span>'
        row=['U.S. Senator','Statewide']+([] if writein else [['Republican','Democratic'][i]])+[cell,'Pending' if bad_status else 'Qualified','6/12/2026']
        rows.append('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>')
    body='<tr>'+''.join('<th>'+x+'</th>' for x in header)+'</tr>'+''.join(rows)
    main='<table class="lighthouse-table m-1">'+body+'</table>'
    # Three separately printed/mobile tables with the same header must not add candidates.
    extras=''.join('<table class="table no-screen">'+body+'</table>' for _ in range(3)) if writein else ''
    return 'General Election 11/3/2026 Last Updated: 2026-10-30 07:56 PM'+main+extras+(main if duplicate else '')


def book(path,*,bad_name=False,formula=False,external=False,withdrawal=False):
    ns=d.NS['m'];root=E.Element('{'+ns+'}worksheet');data=E.SubElement(root,'{'+ns+'}sheetData')
    rows=[d.DE_HEADER]
    for i,name in enumerate(['DEMO ALTERED' if bad_name else 'DEMO A','DEMO B']):
        row=['']*20;row[0]='Statewide';row[1]='U.S. Senator';row[2]='7/1/2026' if withdrawal else '';row[3]=name;row[4]=['Republican','Democratic'][i];row[9]='6/12/2026';row[10]='DEMO RESIDENCE';row[19]='Qualified';rows.append(row)
    for number,row in enumerate(rows,1):
        r=E.SubElement(data,'{'+ns+'}row',r=str(number))
        for i,value in enumerate(row):
            c=E.SubElement(r,'{'+ns+'}c',r=chr(65+i)+str(number),t='inlineStr');E.SubElement(E.SubElement(c,'{'+ns+'}is'),'{'+ns+'}t').text=value
            if formula and number==2 and i==0:E.SubElement(c,'{'+ns+'}f').text='DEMO()'
    wb=f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rel='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="/xl/worksheets/sheet1.xml"'+(' TargetMode="External"' if external else '')+'/></Relationships>'
    with ZipFile(path,'w') as z:
        z.writestr('xl/workbook.xml',wb);z.writestr('xl/_rels/workbook.xml.rels',rel);z.writestr('xl/worksheets/sheet1.xml',E.tostring(root))

INDEX='<a href="/candidates/candidatelist/genl_fcddt_2026.html">2026 General</a><a href="genl_wcddt_2026.html">Declared Write-In</a>'


class DelawareTests(unittest.TestCase):
    def test_exact_main_tables_not_nested_or_print_duplicates_no_contacts(self):
        printed=d.html_rows(html());declared=d.html_rows(html(writein=True),writein=True)
        self.assertEqual((len(printed),len(declared)),(2,3))
        self.assertTrue(all(x['source_party_label'] is None and x['party_class']=='UNSPECIFIED' for x in declared))
        self.assertNotIn('DEMO PRIVATE CONTACT',str(printed)+str(declared))
        self.assertNotIn('Nested Duplicate',str(printed)+str(declared))

    def test_duplicate_main_unknown_status_edition_header_name_scope_refused(self):
        for value in [html(duplicate=True),html(bad_status=True),html().replace('2026-10-30','2026-10-29'),
                      html().replace('<th>Party</th>','<th>Unknown</th>'),html().replace('DEMO B','DEMO A'),
                      html().replace('Statewide','District'),html().replace('main-span','wrong-span')]:
            with self.assertRaises(ValueError):d.html_rows(value)

    def test_inline_workbook_literal_fields_and_no_residence(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.xlsx';book(p);r=d.workbook_rows(p)
            self.assertEqual(len(r),2);self.assertEqual(r[0]['official_name'],'DEMO A');self.assertNotIn('DEMO RESIDENCE',str(r))
            for args in [{'formula':True},{'external':True},{'withdrawal':True}]:
                book(p,**args)
                with self.assertRaises(ValueError):d.workbook_rows(p)

    def test_exact_html_workbook_reconciliation_and_no_writein_party_inference(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.xlsx';book(p);r=d.reconcile(html(),html(writein=True),p,INDEX)
            self.assertEqual((r['printed_candidate_count'],r['declared_write_in_count'],r['HTML_workbook_full_literal_matches']),(2,3,2))
            self.assertFalse(r['writein_party_inference']);self.assertEqual(r['final_ballots_accepted'],0)
            book(p,bad_name=True)
            with self.assertRaises(ValueError):d.reconcile(html(),html(writein=True),p,INDEX)
            book(p)
            with self.assertRaises(ValueError):d.reconcile(html(),html(writein=True).replace('DEMO WRITEIN A','DEMO A'),p,INDEX)
            with self.assertRaises(ValueError):d.reconcile(html(),html(writein=True),p,INDEX.replace('2026','2024'))


if __name__=='__main__':unittest.main()
