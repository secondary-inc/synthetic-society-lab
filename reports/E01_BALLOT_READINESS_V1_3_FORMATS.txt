"""Narrow government roster formats. Source observations never accept final ballots."""
from collections import Counter
from html.parser import HTMLParser
import re


def norm(value):return ' '.join(value.split())


class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None;self.struck=False;self.skip=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in {'script','style','noscript'}:self.skip+=1
        if self.skip:return
        if tag=='table':
            if self.table is not None:raise ValueError('nested roster table unsupported')
            self.table=[]
        if self.table is None:return
        if tag=='tr':self.row=[];self.struck=False
        if tag in {'td','th'}:self.cell=[]
        if self.row is not None and (tag in {'s','strike','del'} or re.search(r'text-decoration(?:-line)?\s*:[^;]*line-through',attrs.get('style',''),re.I)):
            self.struck=True
    def handle_data(self,data):
        if not self.skip and self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in {'script','style','noscript'}:self.skip=max(0,self.skip-1);return
        if self.skip:return
        if tag in {'td','th'} and self.cell is not None:
            if self.row is None:raise ValueError('roster cell outside row')
            self.row.append(norm(''.join(self.cell)));self.cell=None
        if tag=='tr' and self.row is not None:
            self.table.append((self.row,self.struck));self.row=None
        if tag=='table' and self.table is not None:
            self.tables.append(self.table);self.table=None


def table_with_header(html,header):
    parser=Tables();parser.feed(html)
    if parser.table is not None or parser.cell is not None:raise ValueError('unclosed roster table')
    matches=[t for t in parser.tables if t and [x.casefold() for x in t[0][0]]==[x.casefold() for x in header]]
    if len(matches)!=1:raise ValueError('official roster header missing/ambiguous')
    return matches[0][1:]


def classification(label):
    return {'Democratic':'D','Democratic Party':'D','Republican':'R','Republican Party':'R'}.get(label,'UNSPECIFIED')


def roster(state,candidates,**extra):
    if not candidates or len({c['official_name'].casefold() for c in candidates})!=len(candidates):
        raise ValueError('empty or duplicate official candidate rows')
    return {'state':state,'office':'SENATE','seat_class':2,'election_date':'2026-11-03',
            'printed_stage':'GENERAL','candidates':candidates,
            'completeness_claim':'OBTAINED_DOCUMENT_ONLY_NOT_LATEST_AMENDMENT_OR_FINAL_BALLOT_ACCEPTANCE',**extra}


def candidate(name,label,**extra):
    if not name or not label:raise ValueError('empty candidate name or printed label')
    return {'official_name':name,'source_name_literal':name,'source_party_label':label,
            'party_class':classification(label),**extra}


def extract_co_senate(html):
    if '2026 General Election Official Candidate List' not in html or 'certified to the counties on September 4' not in html:
        raise ValueError('Colorado general edition identity differs')
    rows=table_with_header(html,['Candidate name','Office','District','Party','Write in?']);out=[]
    for fields,struck in rows:
        if 'US Senate' not in fields:continue
        if len(fields)!=5 or fields[1]!='US Senate' or fields[2]!='State' or fields[4] not in {'Y','N'}:
            raise ValueError('Colorado Senate row identity/width/write-in differs')
        out.append(candidate(fields[0],fields[3],qualified_write_in=fields[4]=='Y',
                             printed_on_ballot=fields[4]=='N',withdrawal_markup_observed=struck))
    return roster('CO',out,printed_candidates=sum(c['printed_on_ballot'] for c in out),
                  qualified_write_ins=sum(c['qualified_write_in'] for c in out),
                  withdrawal_scope='INLINE_MARKUP_ONLY_NO_LATER_AMENDMENT_ASSURANCE',
                  printed_candidate_party_class_counts=dict(Counter(c['party_class'] for c in out if c['printed_on_ballot'])))


VA_HEADER=['Office Title','District','Candidate Party','Candidate Name','Incumbent','Campaign Email',
           'Campaign Website','Campaign Phone','Campaign Address Line 1','Campaign Address Line 2',
           'Campaign City','Campaign State','Campaign Zip']


def extract_va_senate(html):
    if 'November 3, 2026 - Federal Offices' not in html:raise ValueError('Virginia federal general identity differs')
    rows=table_with_header(html,VA_HEADER);out=[]
    for fields,struck in rows:
        if 'Member, United States Senate' not in fields:continue
        if len(fields)!=13 or fields[0]!='Member, United States Senate' or fields[1]!='Statewide' or fields[4] not in {'Yes','No'}:
            raise ValueError('Virginia Senate row identity/width differs')
        out.append(candidate(fields[3],fields[2],incumbent_printed=fields[4]=='Yes',withdrawal_markup_observed=struck))
    return roster('VA',out,withdrawal_scope='OBTAINED_FEDERAL_DOCUMENT_ONLY_ALL_OFFICES_COMPARISON_PENDING')


def extract_wy_senate(pages):
    if len(pages)!=19:raise ValueError('Wyoming roster expects obtained19-page edition')
    text=pages[0]
    if not all(x in text for x in ['2026 General Election Candidate Roster','Party Affiliation','Candidate Name',
                                  'Date Filed','Date Withdrawn','Wednesday, September 09, 2026 - 11:20AM','Page 1 of 19']):
        raise ValueError('Wyoming roster edition/columns differ')
    if text.count('UNITED STATES SENATOR')!=1 or text.count('UNITED STATES REPRESENTATIVE')!=1:
        raise ValueError('Wyoming Senate section missing/ambiguous')
    block=text.split('UNITED STATES SENATOR',1)[1].split('UNITED STATES REPRESENTATIVE',1)[0]
    out=[]
    for line in block.splitlines():
        if not line.strip():continue
        fields=re.split(r'\s{2,}',line.strip())
        if len(fields)>=4:
            if len(fields)!=5 or not re.fullmatch(r'\d{2}/\d{2}/2026',fields[3]):
                raise ValueError('Wyoming candidate row layout differs')
            out.append(candidate(fields[1],fields[0],pdf_page=1,filing_date_printed=fields[3],withdrawal_date_printed=None))
        else:
            # Observed continuation line contains city/contact and optional withdrawal date.
            if not out or not any('@' in f for f in fields):raise ValueError('Wyoming partial candidate/continuation row')
            dates=re.findall(r'\b\d{2}/\d{2}/\d{4}\b',line)
            if len(dates)>1:raise ValueError('ambiguous Wyoming withdrawal date')
            if dates:out[-1]['withdrawal_date_printed']=dates[0]
    return roster('WY',out,publication_date_printed='2026-09-09',
                  withdrawal_scope='PRINTED_DATE_CELLS_ONLY_NOT_ABSENCE_OF_LATER_WITHDRAWALS')
