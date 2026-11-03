"""Read-only obtained Delaware HTML/inline-XLSX reconciliation, not final ballots."""
from dataclasses import dataclass,field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import PurePosixPath
import re
from zipfile import ZipFile
from civiclab.e01.maine_v1_5 import xml,NS


def norm(s):return ' '.join(s.split())


@dataclass
class Node:
    tag:str=''
    attrs:dict=field(default_factory=dict)
    children:list=field(default_factory=list)
    def text(self):
        if self.tag in {'script','style','noscript'}:return ''
        return ''.join(x if isinstance(x,str) else x.text() for x in self.children)


class Tree(HTMLParser):
    def __init__(self):super().__init__();self.root=Node();self.stack=[self.root]
    def handle_starttag(self,t,a):
        n=Node(t,dict(a));self.stack[-1].children.append(n)
        if t not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(n)
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==t:self.stack=self.stack[:i];break
    def handle_data(self,d):self.stack[-1].children.append(d)


def descendants(n,tag,*,stop_tables=False):
    for x in n.children:
        if isinstance(x,Node):
            if x.tag==tag:yield x
            if not(stop_tables and x.tag=='table'):yield from descendants(x,tag,stop_tables=stop_tables)


def main_table(root,header):
    matches=[]
    for t in descendants(root,'table'):
        if 'lighthouse-table' not in t.attrs.get('class','').split():continue
        rows=list(descendants(t,'tr',stop_tables=True));cells=[[c for c in r.children if isinstance(c,Node) and c.tag in {'td','th'}] for r in rows]
        if cells and [norm(c.text()) for c in cells[0]]==header:matches.append(cells[1:])
    if len(matches)!=1:raise ValueError('Delaware exact main table missing/duplicate')
    return matches[0]


def date_iso(s):return datetime.strptime(s,'%m/%d/%Y').date().isoformat()


def html_rows(html,*,writein=False):
    p=Tree();p.feed(html);text=norm(p.root.text())
    if 'General Election 11/3/2026' not in text or 'Last Updated: 2026-10-30 07:56 PM' not in text:
        raise ValueError('Delaware obtained general edition differs')
    header=['Office','County']+([] if writein else ['Party'])+['Candidate','Status','Filed']
    out=[]
    for cells in main_table(p.root,header):
        if not cells or norm(cells[0].text())!='U.S. Senator':continue
        if len(cells)!=len(header) or norm(cells[1].text())!='Statewide':raise ValueError('Delaware Senate width/scope differs')
        slot=2 if writein else 3;candidate=cells[slot]
        spans=[x for x in candidate.children if isinstance(x,Node) and x.tag=='span' and 'main-span' in x.attrs.get('class','').split()]
        if len(spans)!=1:raise ValueError('Delaware unambiguous literal candidate span missing')
        name=norm(spans[0].text());status=norm(cells[slot+1].text());filed=date_iso(norm(cells[slot+2].text()))
        label=None if writein else norm(cells[2].text())
        if not name or status!='Qualified' or (not writein and not label):raise ValueError('Delaware obtained literal status/name/party differs')
        if not '2026-01-01'<=filed<='2026-10-30':raise ValueError('Delaware filing date after edition')
        out.append({'official_name':name,'source_party_label':label,'source_status_literal':status,
                    'filing_date_printed':filed,'declared_write_in':writein,'printed_on_ballot':not writein,
                    'party_class':'UNSPECIFIED' if writein else {'Democratic':'D','Republican':'R'}.get(label,'UNSPECIFIED')})
    if len(out)!=(3 if writein else 2) or len({c['official_name'] for c in out})!=len(out):raise ValueError('Delaware obtained Senate row count/uniqueness differs')
    return out


DE_HEADER=['County','Office','Withdrawal Date','BallotName','Party','First Name','Middle Name or Initial','Last Name',
           'Suffix','Filing Date','Residential Address Line 1','Residential Address City, State, Zip','Mailing Address Line1',
           'Mailing Address City, State, Zip','Website','Email #1','Email #2','Phone Number #1','Phone Number #2','DisplayedStatus']


def workbook_rows(path):
    with ZipFile(path) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        if len(names)!=len(set(names)) or len(infos)>50 or sum(x.file_size for x in infos)>1_000_000:raise ValueError('Delaware workbook resource/schema differs')
        for i in infos:
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or i.flag_bits&1 or i.file_size>500_000 or any(w in i.filename.lower() for w in ['vbaproject','externallink','connections']):raise ValueError('active/unsafe workbook component')
            if i.filename.endswith('.rels') and any(r.attrib.get('TargetMode')=='External' for r in xml(z.read(i.filename))):raise ValueError('external workbook relationship')
        wb=xml(z.read('xl/workbook.xml'));sheets=wb.findall('m:sheets/m:sheet',NS)
        if len(sheets)!=1 or sheets[0].attrib.get('name')!='Sheet':raise ValueError('Delaware workbook sheet differs')
        rid=sheets[0].attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        if [r.attrib.get('Target') for r in xml(z.read('xl/_rels/workbook.xml.rels')) if r.attrib.get('Id')==rid]!=['/xl/worksheets/sheet1.xml']:raise ValueError('Delaware named sheet target differs')
        rows=[]
        for row in xml(z.read('xl/worksheets/sheet1.xml')).findall('m:sheetData/m:row',NS):
            fields={}
            for cell in row.findall('m:c',NS):
                if cell.find('m:f',NS) is not None:raise ValueError('Delaware workbook formulas unsupported')
                match=re.fullmatch(r'([A-T])([1-9][0-9]*)',cell.attrib.get('r',''))
                if not match or match.group(1) in fields or int(match.group(2))!=int(row.attrib['r']):raise ValueError('Delaware cell layout differs')
                kind=cell.attrib.get('t','n')
                if kind=='inlineStr':value=''.join(x.text or '' for x in cell.findall('m:is/m:t',NS))
                elif kind=='n' and cell.find('m:v',NS) is None:value=''
                else:raise ValueError('Delaware obtained inline string cell type differs')
                fields[match.group(1)]=value
            rows.append(fields)
        if not rows or [rows[0].get(c,'') for c in 'ABCDEFGHIJKLMNOPQRST']!=DE_HEADER:raise ValueError('Delaware20column header differs')
        out=[]
        for r in rows[1:]:
            if r.get('B')!='U.S. Senator':continue
            if r.get('A')!='Statewide' or norm(r.get('C','')) or r.get('T')!='Qualified':raise ValueError('Delaware workbook scope/status/withdrawal requires review')
            out.append({'official_name':norm(r.get('D','')),'source_party_label':r.get('E',''),'source_status_literal':r.get('T',''),
                        'filing_date_printed':date_iso(r.get('J',''))})
        if len(out)!=2 or len({c['official_name'] for c in out})!=2:raise ValueError('Delaware workbook two candidates differ')
        return out


def reconcile(general_html,writein_html,workbook_path,index_html):
    index=Tree();index.feed(index_html);hrefs=[x.attrs.get('href','') for x in descendants(index.root,'a')]
    if not any(x.endswith('/genl_fcddt_2026.html') for x in hrefs) or not any(x.endswith('genl_wcddt_2026.html') for x in hrefs):raise ValueError('Delaware observed general/writein index links missing')
    printed=html_rows(general_html);declared=html_rows(writein_html,writein=True);book=workbook_rows(workbook_path)
    key=lambda r:sorted((x['official_name'],x['source_party_label'],x['source_status_literal'],x['filing_date_printed']) for x in r)
    if key(printed)!=key(book):raise ValueError('Delaware HTML/workbook literal candidate agreement differs')
    if {x['official_name'] for x in printed}&{x['official_name'] for x in declared}:raise ValueError('Delaware printed/writein overlap requires review')
    return {'state':'DE','scope':'OBTAINED_SOURCE_RECONCILIATION_NOT_FINAL_BALLOT','printed_candidates':printed,'declared_write_ins':declared,
            'printed_candidate_count':2,'declared_write_in_count':3,'HTML_workbook_full_literal_matches':2,
            'writein_party_inference':False,'source_last_updated_printed':'2026-10-30 07:56 PM','source_timezone':'NOT_STATED',
            'final_ballots_accepted':0,'source_adoption':False,'actual_selection':False,'model_calls':0,'cost_usd':0}
