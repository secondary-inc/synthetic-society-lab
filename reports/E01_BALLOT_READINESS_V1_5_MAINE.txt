"""Inert Maine source reconciliation; not final ballot acceptance or selection.

No network, model, ZIP extraction, workbook execution, or pipeline dispatch.
"""
from datetime import date,datetime,timedelta
from pathlib import PurePosixPath
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
HEADER=['Office','Dist','County','Party','Date Filed','Last Name','First Name','Middle Name','Suffix','Residence Municipality']


def norm(s):return ' '.join(s.split())


def office_key(pages):
    if len(pages)!=1 or '2026 Office Listing of Candidates Guide' not in pages[0]:raise ValueError('Maine office key edition differs')
    rows=[norm(l) for l in pages[0].splitlines()]
    if rows.count('US US SENATOR')!=1 or rows.count('SS STATE SENATOR')!=1 or rows.count('CG REPRESENTATIVE TO CONGRESS')!=1:
        raise ValueError('official Maine office mapping missing/ambiguous')
    return {'US':'US SENATOR','CG':'REPRESENTATIVE TO CONGRESS','SS':'STATE SENATOR'}


def xml(data):
    if b'<!DOCTYPE' in data or b'<!ENTITY' in data:raise ValueError('XML entities/doctype unsupported')
    return ET.fromstring(data)


def read_workbook(path):
    """Known one-sheet XLSX, read XML only, return no residence/contact fields."""
    with ZipFile(path) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        if len(names)!=len(set(names)) or len(names)>100 or sum(x.file_size for x in infos)>5_000_000:
            raise ValueError('Maine workbook member/count/size differs')
        for info in infos:
            p=PurePosixPath(info.filename)
            if p.is_absolute() or '..' in p.parts or info.flag_bits&1 or info.file_size>2_000_000:
                raise ValueError('Maine workbook member policy rejected')
            if any(x in info.filename.lower() for x in ['vbaproject','externallink','connections']):
                raise ValueError('active/external workbook component unsupported')
        for name in names:
            if name.endswith('.rels'):
                rel=xml(z.read(name))
                if any(x.attrib.get('TargetMode')=='External' for x in rel):raise ValueError('external workbook relationship unsupported')
        wb=xml(z.read('xl/workbook.xml'));sheets=wb.findall('m:sheets/m:sheet',NS)
        if len(sheets)!=1 or sheets[0].attrib.get('name')!='November 3, 2026':raise ValueError('Maine workbook sheet edition differs')
        pr=wb.find('m:workbookPr',NS)
        if pr is not None and pr.attrib.get('date1904','false').lower() not in {'false','0'}:raise ValueError('unsupported workbook date epoch')
        # Bind named sheet to exact local worksheet1, not a renamed unrelated part.
        relationship=sheets[0].attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        rels=xml(z.read('xl/_rels/workbook.xml.rels'))
        targets=[r.attrib.get('Target') for r in rels if r.attrib.get('Id')==relationship]
        if targets!=['worksheets/sheet1.xml']:raise ValueError('Maine named sheet target differs')
        shared=xml(z.read('xl/sharedStrings.xml'))
        strings=[''.join(n.text or '' for n in si.iter('{'+NS['m']+'}t')) for si in shared.findall('m:si',NS)]
        sheet=xml(z.read('xl/worksheets/sheet1.xml'));rows=[]
        for row in sheet.findall('m:sheetData/m:row',NS):
            fields={}
            for cell in row.findall('m:c',NS):
                if cell.find('m:f',NS) is not None:raise ValueError('workbook formulas unsupported')
                address=cell.attrib.get('r','');m=re.fullmatch(r'([A-O])([1-9][0-9]*)',address)
                if not m or int(m.group(2))!=int(row.attrib['r']) or m.group(1) in fields:raise ValueError('Maine worksheet cell layout differs')
                kind=cell.attrib.get('t','n');value=cell.find('m:v',NS)
                if m.group(1) in 'KLMNO':
                    if value is not None or kind!='n':raise ValueError('unexpected value in styled blank extra column')
                    continue
                value=value.text if value is not None else ''
                if kind=='s':
                    if not re.fullmatch(r'[0-9]+',value) or int(value)>=len(strings):raise ValueError('bad shared-string index')
                    value=strings[int(value)]
                elif kind!='n':raise ValueError('unknown Maine workbook cell type')
                fields[m.group(1)]=value
            rows.append((int(row.attrib['r']),fields))
        if not rows or rows[0]!=(1,dict(zip('ABCDEFGHIJ',HEADER))):raise ValueError('Maine general roster header differs')
        out=[]
        for number,row in rows[1:]:
            if row.get('A')!='US':continue
            if row.get('B') or row.get('C') or not row.get('D') or not row.get('F') or not row.get('G'):
                raise ValueError('Maine statewide Senate row differs')
            serial=row.get('E','')
            if not re.fullmatch(r'[0-9]+',serial):raise ValueError('Maine filing date missing/noninteger')
            filed=(date(1899,12,30)+timedelta(days=int(serial))).isoformat()
            if not '2026-01-01'<=filed<='2026-11-03':raise ValueError('Maine filing date outside2026pre-election window')
            parts={k:row.get(c,'') for k,c in [('first','G'),('middle','H'),('last','F'),('suffix','I')]}
            name=norm(' '.join(parts.values()))
            out.append({'official_name':name,'source_name_parts':parts,'source_party_label':row['D'],
                        'source_office_code':'US','worksheet_row':number,'filing_date_printed':filed,
                        'ballot_status':'PRINTED_GENERAL_ROSTER_ENTRY_NOT_FINAL_ACCEPTANCE'})
        if not out or len({x['official_name'] for x in out})!=len(out):raise ValueError('empty/duplicate Maine printed candidates')
        return out


def source_date(value):
    return datetime.strptime(value,'%m/%d/%Y').date().isoformat()


def withdrawals(pages):
    if len(pages)!=1 or not all(x in pages[0] for x in ['Candidate Withdrawals and Replacement Candidate Nominations after the June 9, 2026 Primary','Withdrawn Candidate','Replacement Candidate','Date Received','9/22/2026']):
        raise ValueError('Maine withdrawal edition/header differs')
    out=[]
    for line in pages[0].splitlines():
        if not re.match(r'^\s*US\s',line):continue
        f=re.split(r'\s{2,}',line.strip())
        if len(f)!=7 or f[0]!='US' or not all(f[i] for i in [1,2,4]):raise ValueError('Maine withdrawal row layout differs')
        withdrew,received=source_date(f[3]),source_date(f[6])
        if not '2026-01-01'<=withdrew<=received<='2026-11-03':raise ValueError('Maine replacement chronology differs')
        out.append({'source_office_code':'US','source_party_label':f[1],'withdrawn_name_literal':f[2],
                    'withdrawal_date_printed':withdrew,'replacement_name_literal':f[4],'replacement_received_date_printed':received})
    if not out or len({x['withdrawn_name_literal'] for x in out})!=len(out):raise ValueError('empty/duplicate Maine withdrawal rows')
    return out


def writeins(pages):
    if len(pages)!=1 or not all(x in pages[0] for x in ['Declared Write-in Candidates','10/15/26','for the November 3, 2026 General Election','Municipalities Affected']):
        raise ValueError('Maine declared-writein edition/header differs')
    out=[]
    for line in pages[0].splitlines():
        if not re.match(r'^\s*US\s',line):continue
        f=re.split(r'\s{2,}',line.strip())
        if len(f)!=5 or f[0]!='US' or not f[1] or not f[2]:raise ValueError('Maine declared-writein row layout differs')
        out.append({'official_name':f[2],'source_party_label':f[1],'source_office_code':'US',
                    'ballot_status':'DECLARED_WRITE_IN_LIST_ENTRY_NOT_PRINTED_ROSTER_ENTRY_OR_FINAL_ACCEPTANCE',
                    'source_label_role':'DECLARED_WRITE_IN_DESIGNATION_NOT_PARTY_NOMINATION_PROOF'})
    if not out or len({x['official_name'] for x in out})!=len(out):raise ValueError('empty/duplicate Maine declared-writein candidates')
    return out


def reconcile(workbook_path,key_pages,withdrawal_pages,writein_pages):
    mapping=office_key(key_pages);printed=read_workbook(workbook_path);changes=withdrawals(withdrawal_pages);declared=writeins(writein_pages)
    names={x['official_name']:x for x in printed}
    for change in changes:
        replacement=names.get(change['replacement_name_literal'])
        if replacement is None or replacement['source_party_label']!=change['source_party_label']:
            raise ValueError('Maine replacement full literal name/party differs from printed roster')
        if change['withdrawn_name_literal'] in names:raise ValueError('Maine withdrawn candidate still in printed roster')
        if replacement['filing_date_printed']!=change['replacement_received_date_printed']:
            raise ValueError('Maine replacement filing/received date differs')
    overlap=set(names)&{x['official_name'] for x in declared}
    if overlap:raise ValueError('Maine printed/writein overlap requires separate source review')
    return {'scope':'MAINE_OBTAINED_SOURCE_RECONCILIATION_ONLY','office_mapping':mapping,
            'printed_candidates':printed,'historical_withdrawal_replacements':changes,'declared_write_ins':declared,
            'printed_candidate_count':len(printed),'historical_replacement_count':len(changes),'declared_write_in_count':len(declared),
            'exact_replacement_fullname_party_and_date_matches':len(changes),'withdrawn_candidates_absent_printed_roster':True,
            'printed_writein_exact_name_overlap_count':0,'completeness_claim':'SOURCE_LOCAL_CONSISTENCY_NOT_LATEST_AMENDMENT_OR_FINAL_BALLOT_ACCEPTANCE',
            'final_ballots_accepted':0,'source_adoption':False,'actual_selection':False,'model_calls':0,'cost_usd':0}
