"""Read-only physical text-box extraction for obtained Nebraska rotated PDF."""
from hashlib import sha256
import math
from civiclab.e01.ballot_formats_v1_3 import norm

HEADERS={'Office':19.32,'Term':202.08,'Vote':227.99,'Party':255.12,'Candidate':317.66,
         'City':431.19,'Incumbency':485.56,'Mailing':540.60,'Phone/Email':637.69}
BOUNDS={'district':(151,200),'term':(200,225),'vote':(225,253),'party':(253,317),
        'name':(317,430),'city':(430,484),'incumbency':(484,540)}


def lines(words):
    groups=[]
    for word in sorted(words,key=lambda w:(w['top'],w['x0'])):
        group=next((g for g in groups if abs(g[0]['top']-word['top'])<0.4),None)
        if group is None:groups.append([word])
        else:group.append(word)
    return [' '.join(w['text'] for w in sorted(g,key=lambda w:w['x0'])) for g in groups]


def extract_geometry(words,*,page_count=24,rotation=90,width=792,height=612,metadata=None):
    if (page_count,rotation,width,height)!=(24,90,792,612):raise ValueError('Nebraska obtained document geometry differs')
    if len(words)>10000:raise ValueError('Nebraska word resource limit')
    for w in words:
        if not isinstance(w.get('text'),str) or not w['text'] or len(w['text'])>256:raise ValueError('Nebraska word schema differs')
        if any(not isinstance(w.get(k),(int,float)) or not math.isfinite(w[k]) for k in ['x0','x1','top','bottom']):raise ValueError('Nebraska finite coordinates required')
        if not 0<=w['x0']<w['x1']<=792 or not 0<=w['top']<w['bottom']<=612:raise ValueError('Nebraska text box outside page')
    title=' '.join(lines([w for w in words if w['top']<50]))
    if not all(t in title for t in ['Final Statewide General Candidate List','November 3, 2026 General Election','9/11/2026']):raise ValueError('Nebraska printed title/edition differs')
    for key,x in HEADERS.items():
        found=[w for w in words if w['text']==key and abs(w['top']-55.8)<0.3 and abs(w['x0']-x)<0.3]
        if len(found)!=1:raise ValueError('Nebraska physical header location differs')
    office_words=[w for w in words if 18<=w['x0'] and w['x1']<=151 and w['top']>72]
    groups=[]
    for w in sorted(office_words,key=lambda w:(w['top'],w['x0'])):
        g=next((g for g in groups if abs(g[0]['top']-w['top'])<0.4),None)
        if g is None:groups.append([w])
        else:g.append(w)
    anchors=[(g[0]['top'],' '.join(w['text'] for w in sorted(g,key=lambda w:w['x0']))) for g in groups]
    first=next((i for i,(t,label) in enumerate(anchors) if label=='For United States Senator'),None)
    if first is None:raise ValueError('Nebraska Senate office anchor missing')
    selected=anchors[first:first+6]
    if len(selected)!=6 or [label for _,label in selected]!=['For United States Senator']*5+['For Representative in Congress']:
        raise ValueError('Nebraska five-row Senate/next-office boundary differs')
    out=[]
    for (top,office),(next_top,_) in zip(selected,selected[1:]):
        if not 21.1<=next_top-top<=21.9:raise ValueError('Nebraska obtained row-band spacing differs')
        band=[w for w in words if top-0.4<=w['top']<next_top-0.4]
        cells={key:[] for key in BOUNDS}
        for w in band:
            if w['x1']<=151 or w['x0']>=540:continue  # Outside exported table fields.
            match=[key for key,(left,right) in BOUNDS.items() if left<=w['x0'] and w['x1']<=right]
            if len(match)!=1:raise ValueError('Nebraska word overlaps table columns')
            cells[match[0]].append(w)
        values={key:lines(value) for key,value in cells.items()}
        if values['district'] or values['term']!=['6'] or values['vote']!=['1'] or len(values['name'])!=1 or not 1<=len(values['party'])<=2 or len(values['incumbency'])!=1:
            raise ValueError('Nebraska literal district/term/vote/name/party shape differs')
        status=values['incumbency'][0]
        if status not in {'Incumbent','Nonincumbent'}:raise ValueError('Nebraska incumbency literal differs')
        name=values['name'][0];parts=values['party'];label=' '.join(parts)
        out.append({'official_name':name,'source_party_label':label,'source_party_label_lines':parts,
                    'party_class':'R' if label=='Republican' else 'UNSPECIFIED','source_term_literal':'6',
                    'source_vote_for_literal':'1','source_district_literal':'','source_incumbency_literal':status,'pdf_page':1})
    if len({x['official_name'] for x in out})!=5:raise ValueError('Nebraska duplicate candidate name')
    return {'state':'NE','scope':'OBTAINED_FIRST_PAGE_SENATE_ONLY_NOT_FINAL_BALLOT','candidates':out,'candidate_count':5,
            'source_printed_edition':'2026-09-11','pdf_creation_metadata':(metadata or {}).get('CreationDate',(metadata or {}).get('/CreationDate')),
            'pdf_modification_metadata':(metadata or {}).get('ModDate',(metadata or {}).get('/ModDate')),'metadata_role':'FILE_METADATA_NOT_INDEPENDENT_PUBLICATION_OR_ASOF_ARCHIVE',
            'physical_column_bounds':BOUNDS,'final_title_role':'SOURCE_PRINTED_TITLE_NOT_OUR_FINAL_BALLOT_ACCEPTANCE',
            'final_ballots_accepted':0,'source_adoption':False,'actual_selection':False,'model_calls':0,'cost_usd':0}


def read_pdf(path,index_html):
    from pathlib import Path
    try:import pdfplumber
    except ImportError:raise RuntimeError('optional pdfplumber0.11.9 geometry runtime required') from None
    if '/Final_Statewide_General_Candidate_Filing_List_9.11.26.pdf' not in index_html:raise ValueError('Nebraska offered official edition link missing')
    source=Path(path);before=sha256(source.read_bytes()).hexdigest()
    with pdfplumber.open(source) as pdf:
        page=pdf.pages[0]
        result=extract_geometry(page.extract_words(),page_count=len(pdf.pages),rotation=page.rotation,
                                width=page.width,height=page.height,metadata=pdf.metadata)
    if sha256(source.read_bytes()).hexdigest()!=before:raise RuntimeError('Nebraska source bytes changed during read')
    result['source_bytes_unchanged']=True;result['geometry_engine']='pdfplumber';result['geometry_engine_version']=pdfplumber.__version__
    return result
