"""Offline reconstruction of public PUMS index/count metadata; no person access."""
import csv
from html.parser import HTMLParser
import io
import re
from .population import FIPS_REGION


class IndexRows(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.cells=None;self.cell=None;self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.cells=[];self.hrefs=[]
        elif tag=='td' and self.cells is not None:self.cell=[]
        elif tag=='a' and self.cells is not None:
            href=dict(attrs).get('href')
            if href:self.hrefs.append(href)
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag=='td' and self.cell is not None:
            self.cells.append(''.join(self.cell).strip());self.cell=None
        elif tag=='tr' and self.cells is not None:
            self.rows.append((self.hrefs,self.cells));self.cells=None;self.cell=None


def reconstruct(index_text,count_text,registry):
    """Join exact intended public filenames with all51 published person counts."""
    if len(registry)!=51 or {s['state_fips'] for s in registry}!=set(FIPS_REGION):
        raise ValueError('exact51state/DC registry required')
    filenames=[s['filename'] for s in registry]
    if len(set(filenames))!=51 or any(not re.fullmatch(r'csv_p[a-z]{2}\.zip',s) for s in filenames):
        raise ValueError('unique literal state archive names required')
    parser=IndexRows();parser.feed(index_text);index={}
    wanted=set(filenames)|{'csv_pus.zip','csv_ppr.zip'}
    for hrefs,cells in parser.rows:
        for href in hrefs:
            if href not in wanted:continue
            if href in index or len(cells)!=5 or cells[1]!=href or not re.fullmatch(r'\d+(?:\.\d+)?[MGK]',cells[3]):
                raise ValueError('duplicate or malformed literal index entry')
            index[href]={'filename':href,'index_display_size':cells[3],'index_display_modified':cells[2]}
    if set(index)!=wanted:raise ValueError('index coverage incomplete')
    reader=csv.DictReader(io.StringIO(count_text));required=['FILE_TYPE','FILE_NAME','STATE','FILE_DESCRIPTION','NUMBER_OF_RECORDS']
    if reader.fieldnames!=required:raise ValueError('recordcount schema changed')
    people={}
    for row in reader:
        if None in row or any(row.get(k) is None for k in required):raise ValueError('malformed recordcount row')
        if row['FILE_TYPE'] not in ('Person','Housing'):raise ValueError('unknown record type')
        if row['FILE_TYPE']!='Person':continue
        state=row['STATE'];n=row['NUMBER_OF_RECORDS']
        if state in people or not n.isdigit() or int(n)<=0:raise ValueError('duplicate or invalid person recordcount')
        people[state]={**row,'published_person_rows':int(n)}
    if set(people)!=set(FIPS_REGION)|{'72','US','PP','PA','PB','PC','PD'}:
        raise ValueError('person count geography coverage changed')
    for state in FIPS_REGION:
        if people[state]['FILE_NAME']!='PSAM_P'+state:raise ValueError('state recordcount member identity changed')
    parts=[]
    for code,(low,high) in zip(('PA','PB','PC','PD'),((1,15),(16,28),(29,41),(42,56))):
        part=people[code]
        if part['FILE_NAME']!='PSAM_PUS'+code[-1] or sum(people[s]['published_person_rows'] for s in FIPS_REGION if low<=int(s)<=high)!=part['published_person_rows']:
            raise ValueError('national part/state range count mismatch')
        parts.append(part)
    total=sum(people[s]['published_person_rows'] for s in FIPS_REGION)
    if total!=people['US']['published_person_rows'] or sum(p['published_person_rows'] for p in parts)!=total:
        raise ValueError('state/national total mismatch')
    if people['PP']['published_person_rows']!=total+people['72']['published_person_rows']:
        raise ValueError('US plus PR reconciliation failed')
    states=[{**s,**index[s['filename']],'published_person_rows':people[s['state_fips']]['published_person_rows'],
             'published_recordcount_name':people[s['state_fips']]['FILE_NAME'],
             'published_state_name':people[s['state_fips']]['FILE_DESCRIPTION']} for s in registry]
    return {'states':states,'national':{**index['csv_pus.zip'],'published_person_rows':total,'parts':parts},
            'excluded_PR':{**index['csv_ppr.zip'],'published_person_rows':people['72']['published_person_rows']},
            'all_persons_including_PR':people['PP']['published_person_rows'],
            'scope':'PUBLIC_METADATA_ONLY_NOT_ACTUAL_ARCHIVE_CONTENT_VALIDATION'}
