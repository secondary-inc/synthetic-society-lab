"""Authored inert XLSX/XML and PDF-layout text; no real respondent/raw data."""
from datetime import date
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
import xml.etree.ElementTree as E
from civiclab.e01 import maine_v1_5 as m


def key():return ['2026 Office Listing of Candidates Guide\nOffice Abbreviation  Office Order\nUS  US SENATOR\nCG  REPRESENTATIVE TO CONGRESS\nSS  STATE SENATOR']


def withdraw():return ['Candidate Withdrawals and Replacement Candidate Nominations after the June 9, 2026 Primary\nOfc.  Dist.  Pty  Withdrawn Candidate  Date  Replacement Candidate  Residence Municipality  Date Received\nUS  D  DEMO FORMER  7/10/2026  DEMO NEW  DEMO RESIDENCE  7/27/2026\nSS  1  D  OTHER OFFICE  7/10/2026  DEMO STATE  CITY  7/27/2026\n9/22/2026']


def ins():return ['Declared Write-in Candidates  10/15/26\nfor the November 3, 2026 General Election\nOffice  District County  Party  Name  Residence  Municipalities Affected\nUS  Faith in Humanity  DEMO WRITEIN  DEMO RESIDENCE  All\nUS  Un-enrolled  DEMO SECOND  DEMO RESIDENCE  All\nSS  1  Independent  DEMO STATE  CITY  Dist1']


def workbook(path,*,sheetname='November 3, 2026',formula=False,external=False,extra_value=False,replace=None):
    ns=m.NS['m'];serial=str((date(2026,7,27)-date(1899,12,30)).days)
    rows=[m.HEADER,['US','','','R','46078','ALPHA','DEMO','','','DEMO RESIDENCE'],
          ['US','','','D',serial,'NEW','DEMO','','','DEMO RESIDENCE'],
          ['SS','1','','D',serial,'STATE','DEMO','','','DEMO RESIDENCE']]
    if replace:rows=replace(rows)
    strings=[];root=E.Element('{'+ns+'}worksheet');data=E.SubElement(root,'{'+ns+'}sheetData')
    for number,row in enumerate(rows,1):
        rr=E.SubElement(data,'{'+ns+'}row',r=str(number))
        for i,value in enumerate(row):
            cc=E.SubElement(rr,'{'+ns+'}c',r=chr(65+i)+str(number),t='s')
            strings.append(value);E.SubElement(cc,'{'+ns+'}v').text=str(len(strings)-1)
            if formula and number==2 and i==0:E.SubElement(cc,'{'+ns+'}f').text='WEBSERVICE("DEMO")'
        if number==2:
            cc=E.SubElement(rr,'{'+ns+'}c',r='K2')
            if extra_value:E.SubElement(cc,'{'+ns+'}v').text='1'
    ss=E.Element('{'+ns+'}sst')
    for value in strings:E.SubElement(E.SubElement(ss,'{'+ns+'}si'),'{'+ns+'}t').text=value
    wb=f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{sheetname}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rel='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
    if external:rel+='<Relationship Id="rId2" Target="https://example.invalid" TargetMode="External"/>'
    rel+='</Relationships>'
    with ZipFile(path,'w') as z:
        for name,value in [('xl/workbook.xml',wb),('xl/_rels/workbook.xml.rels',rel),('xl/sharedStrings.xml',E.tostring(ss)),('xl/worksheets/sheet1.xml',E.tostring(root))]:z.writestr(name,value)


class MaineTests(unittest.TestCase):
    def test_official_key_binds_us_senator_not_state_senator(self):
        self.assertEqual(m.office_key(key())['US'],'US SENATOR')
        for old,new in [('US  US SENATOR','US  STATE SENATOR'),('2026','2024')]:
            with self.assertRaises(ValueError):m.office_key([key()[0].replace(old,new)])
        with self.assertRaises(ValueError):m.office_key(key()+key())

    def test_inert_general_xlsx_ignores_styled_blanks_no_residence_or_state_office(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.xlsx';workbook(p);r=m.read_workbook(p)
            self.assertEqual(len(r),2);self.assertEqual(r[1]['official_name'],'DEMO NEW')
            self.assertEqual(r[1]['filing_date_printed'],'2026-07-27')
            self.assertNotIn('DEMO RESIDENCE',str(r));self.assertNotIn('DEMO STATE',str(r))

    def test_workbook_wrong_edition_formula_external_extra_column_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.xlsx'
            for kwargs in [{'sheetname':'November 5, 2024'},{'formula':True},{'external':True},{'extra_value':True}]:
                workbook(p,**kwargs)
                with self.assertRaises(ValueError):m.read_workbook(p)
            with self.assertRaises(ValueError):m.xml(b'<!DOCTYPE x [<!ENTITY x "DEMO">]><x/>')

    def test_workbook_header_duplicate_scope_and_date_guards(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.xlsx'
            mutations=[lambda r:[['Unknown']+r[0][1:]]+r[1:],lambda r:r+[r[1]],
                       lambda r:[r[0],['US','1']+r[1][2:]]+r[2:],
                       lambda r:[r[0],r[1][:4]+['BAD']+r[1][5:]]+r[2:]]
            for mutate in mutations:
                workbook(p,replace=mutate)
                with self.assertRaises(ValueError):m.read_workbook(p)

    def test_withdrawal_labels_and_dates_separate_no_residence(self):
        r=m.withdrawals(withdraw());self.assertEqual(len(r),1)
        self.assertEqual(r[0]['withdrawal_date_printed'],'2026-07-10')
        self.assertEqual(r[0]['replacement_received_date_printed'],'2026-07-27')
        self.assertNotIn('DEMO RESIDENCE',str(r));self.assertNotIn('DEMO STATE',str(r))
        for old,new in [('7/27/2026','7/01/2026'),('9/22/2026','9/21/2026')]:
            with self.assertRaises(ValueError):m.withdrawals([withdraw()[0].replace(old,new)])

    def test_writein_literal_designations_not_party_nomination_no_residence(self):
        r=m.writeins(ins());self.assertEqual([x['source_party_label'] for x in r],['Faith in Humanity','Un-enrolled'])
        self.assertTrue(all('NOT_PARTY_NOMINATION' in x['source_label_role'] for x in r))
        self.assertNotIn('DEMO RESIDENCE',str(r));self.assertNotIn('DEMO STATE',str(r))
        for old,new in [('10/15/26','10/16/26'),('DEMO SECOND','DEMO WRITEIN')]:
            with self.assertRaises(ValueError):m.writeins([ins()[0].replace(old,new)])

    def test_reconciliation_exact_name_party_date_and_separate_writeins(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.xlsx';workbook(p);r=m.reconcile(p,key(),withdraw(),ins())
            self.assertEqual((r['printed_candidate_count'],r['historical_replacement_count'],r['declared_write_in_count']),(2,1,2))
            self.assertEqual(r['final_ballots_accepted'],0);self.assertFalse(r['source_adoption']);self.assertFalse(r['actual_selection'])
            self.assertEqual(r['printed_writein_exact_name_overlap_count'],0)
            for changed in [withdraw()[0].replace('DEMO NEW','DEMO ALTERED'),withdraw()[0].replace('US  D','US  R'),withdraw()[0].replace('7/27/2026','7/26/2026'),withdraw()[0].replace('DEMO FORMER','DEMO ALPHA')]:
                with self.assertRaises(ValueError):m.reconcile(p,key(),[changed],ins())
            with self.assertRaises(ValueError):m.reconcile(p,key(),withdraw(),[ins()[0].replace('DEMO WRITEIN','DEMO NEW')])


if __name__=='__main__':unittest.main()
