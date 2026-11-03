"""Pure local Idaho rendered-capture reader candidate; not readiness admission.

No network, browser, details activation, persistence or inference. The code and
candidate contract require independent release review before real-source use.
Only observed candidacy-status history is returned; ballot/legal states unknown.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from datetime import datetime,timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urljoin

CONTRACT_CANONICAL_SHA='5db0092879caa96e1b0c4bf4b496427446ef31329168acb93e82d5ecc854f3ff'
SOURCE_IDS=('id_general_index','id_candidate_search','id_browser_visible','id_browser_federal','id_browser_senate')
URL='https://run.voteidaho.gov/search'
KIND='BROWSER_VISIBLE_TEXT_AND_RENDERED_TABLE_DOM_NOT_HTTP_WIRE'
COLUMNS=('ballotName','districtType','office','district','party','filedDate','isWriteIn','status','actions')
HEADERS=('BALLOT NAMEHeader','DISTRICT TYPEHeader','OFFICEHeader','DISTRICTHeader','PARTYHeader','DATE FILEDHeader','WRITE-INHeader','STATUSHeader','ACTIONS')
SEMANTIC_HEADERS=('BALLOT NAME','DISTRICT TYPE','OFFICE','DISTRICT','PARTY','DATE FILED','WRITE-IN','STATUS','ACTIONS')
ELECTION='November 03, 2026 - 2026 GENERAL'
INVENTORY=(('Democratic','Withdrawn','02/23/2026'),('Independent','Approved','02/25/2026'),
 ('Independent','Approved','02/26/2026'),('Libertarian','Approved','02/27/2026'),('Republican','Approved','02/23/2026'))
UNKNOWN_REASONS={'write_in_status':'BLANK_SOURCE_CELL_DOES_NOT_ESTABLISH_BOOLEAN_FALSE',
 'printed_ballot_status':'PORTAL_APPROVAL_AND_FINAL_TITLE_ARE_NOT_PRINTED_BALLOT_CERTIFICATION',
 'legal_nomination_status':'NO_INDEPENDENT_LEGAL_NOMINATION_ADJUDICATION',
 'latest_amendment_completeness':'CAPTURED_PORTAL_CONTEXT_NOT_LATEST_UPSTREAM_COMPLETENESS_CERTIFICATE'}
SAFE_ERROR_TYPES={'ValueError','TypeError','KeyError','UnicodeDecodeError','JSONDecodeError','FileNotFoundError',
 'PermissionError','OSError','RuntimeError','AttributeError','RecursionError','OverflowError'}


def norm(s):return ' '.join(s.split())


def require(ok):
    if not ok:raise ValueError('ID_CAPTURE_CONTRACT_MISMATCH')


def digest(data):return sha256(data).hexdigest()


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


class CaptureRejected(Exception):
    """Only exception type survives a failure. No raw values/cause/context."""
    def __init__(self,error_type):
        self.error_type=error_type if error_type in SAFE_ERROR_TYPES else 'Exception'
        super().__init__('ID_CAPTURE_REJECTED:'+self.error_type)


def _safe(operation):
    failure=None
    try:result=operation()
    except BaseException as exc:failure=type(exc).__name__
    # Raise after leaving except, so an injected exception carrying private
    # values is not retained in __cause__ or __context__ of the exported error.
    if failure=='KeyboardInterrupt':raise KeyboardInterrupt()
    if failure=='SystemExit':raise SystemExit()
    if failure is not None:raise CaptureRejected(failure)
    return result


def _admit_metadata(contract):
    require(type(contract) is dict and digest(canonical(contract))==CONTRACT_CANONICAL_SHA)
    require(tuple(s['source_id'] for s in contract['inputs'])==SOURCE_IDS)
    return {'role':'ID_STANDALONE_READER_CANDIDATE_ONLY_NOT_READINESS','contract_canonical_sha256':CONTRACT_CANONICAL_SHA}


def admit_metadata(contract):return _safe(lambda:_admit_metadata(contract))


def strict_json(data):
    def pairs(items):
        obj={}
        for key,value in items:
            require(key not in obj);obj[key]=value
        return obj
    def invalid(_):raise ValueError('ID_NONFINITE_JSON')
    return json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid)


@dataclass
class Node:
    tag:str
    attrs:dict=field(default_factory=dict)
    children:list=field(default_factory=list)
    def text(self):return ''.join(x if isinstance(x,str) else x.text() for x in self.children)
    def text_leaves(self):
        for child in self.children:
            if isinstance(child,str):
                if child.strip():yield child
            else:yield from child.text_leaves()


class DOM(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self,html):
        require(isinstance(html,str) and len(html)<=750000)
        super().__init__(convert_charrefs=True);self.root=Node('root');self.stack=[self.root];self.nodes=0
        self.feed(html);self.close();require(len(self.stack)==1)
    def handle_starttag(self,tag,attrs):
        self.nodes+=1;require(self.nodes<=100000 and len(self.stack)<=64)
        require(len(attrs)==len({k for k,v in attrs}))
        node=Node(tag,dict(attrs));self.stack[-1].children.append(node)
        if tag not in self.VOID:self.stack.append(node)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:self.handle_endtag(tag)
    def handle_endtag(self,tag):
        require(len(self.stack)>1 and self.stack[-1].tag==tag);self.stack.pop()
    def handle_data(self,data):self.stack[-1].children.append(data)


def descendants(node,tag):
    for child in node.children:
        if isinstance(child,Node):
            if child.tag==tag:yield child
            yield from descendants(child,tag)


def table_rows(html):
    root=DOM(html).root;tables=list(descendants(root,'table'));require(len(tables)==1);table=tables[0]
    require(table.attrs.get('role')=='table' and table.attrs.get('aria-describedby')=='SmartTableGrid')
    require(not any(list(descendants(table,t)) for t in ('script','style','noscript','iframe','object','svg','template')))
    captions=list(descendants(table,'caption'));require(len(captions)==1 and norm(captions[0].text())=='Smart Table')
    rows=list(descendants(table,'tr'));require(1<len(rows)<=51)
    header=[x for x in rows[0].children if isinstance(x,Node)]
    require(all(c.tag=='th' for c in header))
    require(len(header)==9 and tuple(norm(c.text()) for c in header)==HEADERS)
    for cell,column in zip(header,COLUMNS):
        require(cell.attrs.get('role')=='columnheader' and [token for token in cell.attrs.get('class','').split() if token.startswith('cdk-column-')]==['cdk-column-'+column])
    result=[]
    for row in rows[1:]:
        cells=[x for x in row.children if isinstance(x,Node)];require(len(cells)==9 and all(c.tag=='td' for c in cells))
        require(not any(x.tag in {'th','table'} for x in row.children if isinstance(x,Node)))
        values=[]
        for cell,column in zip(cells,COLUMNS):
            require(cell.attrs.get('role')=='cell' and [token for token in cell.attrs.get('class','').split() if token.startswith('cdk-column-')]==['cdk-column-'+column])
            # Each observed body cell has at most one non-whitespace text leaf.
            # Nested duplicate/contact text must not silently enter names.
            require(len(list(cell.text_leaves()))<=1)
            values.append(norm(cell.text()))
        result.append(tuple(values))
    require(len(list(descendants(table,'th')))==9 and len(list(descendants(table,'td')))==9*len(result))
    return result


def _parse_capture(payload,variant):
    require(type(payload) is dict and set(payload)=={'url','capture_kind','captured_at_utc','data'})
    require(payload['url']==URL and payload['capture_kind']==KIND)
    stamp=datetime.strptime(payload['captured_at_utc'],'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
    require(stamp.date().isoformat()=='2026-11-03')
    d=payload['data'];require(type(d) is dict and type(variant) is int and variant in (0,1,2))
    expected={'body','selects','tables'} if variant==0 else {'body','checkboxes','selected','table'}
    require(set(d)==expected and isinstance(d['body'],str) and len(d['body'])<=750000)
    body=d['body'];require('FINAL CANDIDATES LIST' in body and ELECTION in body)
    require('Search Filed Candidates' in body and 'Filing Status' in body)
    count=(592,15,5)[variant];page=(592,15,5)[variant];visible=(50,15,5)[variant]
    require(f'{count} Candidate(s) Found of 592 total' in norm(body))
    require(f'1 – {visible} of {page}' in norm(body))
    # Exactly one count and range statement; no competing partial pagination.
    import re
    require(re.findall(r'\d+ Candidate\(s\) Found\s+of \d+ total',body)==[f'{count} Candidate(s) Found of 592 total'])
    require(re.findall(r'\d+ – \d+ of \d+',body)==[f'1 – {visible} of {page}'])
    controls=d['selects'] if variant==0 else d['selected']
    expected_controls=[('mat-select-0',ELECTION),('mat-select-1','Select District Type' if variant==0 else 'Federal')]
    if variant>0:expected_controls.append(('mat-select-4','Select Office' if variant==1 else 'United States Senator'))
    expected_controls.extend([('partyAffiliation','Select Party'),('mat-select-3','50')])
    require(type(controls) is list and len(controls)==len(expected_controls))
    for control,(key,value) in zip(controls,expected_controls):
        require(type(control) is dict and set(control)==({'id','text','disabled'} if variant==0 else {'id','text'}))
        require(control['id']==key and control['text']==value)
        if variant==0:require(control['disabled']=='false')
    if variant==0:
        require(type(d['tables']) is list and len(d['tables'])==1);html=d['tables'][0]
        checkbox_evidence={'kind':'UNKNOWN','reason':'INITIAL_ARTIFACT_HAS_NO_CHECKBOX_STATE_ARRAY'}
    else:
        require(d['checkboxes']==[{'id':f'mat-mdc-checkbox-{i}-input','checked':True} for i in range(3)])
        require(all(type(c['checked']) is bool for c in d['checkboxes']))
        # The recorded body labels bind status-ID order without pretending the
        # initial capture contains a checkbox snapshot.
        section=norm(body).split('Filing Status',1)[1].split('Reset All Filters',1)[0]
        require(norm(section)=='Select All Approved Withdrawn')
        html=d['table'];checkbox_evidence={'kind':'OBSERVED_BOTH_SELECTED','labels':['Approved','Withdrawn']}
    rows=table_rows(html);require(len(rows)==visible)
    body_projection=norm(body);cursor=0
    for row in rows[:5]:
        projected=norm(' '.join(row));position=body_projection.find(projected,cursor)
        require(position>=cursor);cursor=position+len(projected)
    selected=[(i,row) for i,row in enumerate(rows,1) if row[2]=='United States Senator']
    require([i for i,_ in selected]==[1,2,3,4,5])
    if variant<2:require(rows[5][2]=='United States Representative')
    if variant==1:require(all(row[1]=='Federal' and row[2]=='United States Representative' for row in rows[5:]))
    senator=[row for _,row in selected];require(len({row[0] for row in senator})==5)
    for row,(party,status,date) in zip(senator,INVENTORY):
        require(row[0] and len(row[0])<=256 and row[1:4]==('Federal','United States Senator',''))
        require((row[4],row[7],row[5])==(party,status,date) and row[6]=='' and row[8]=='View Details')
        parsed=datetime.strptime(row[5],'%m/%d/%Y').date();require(parsed<=stamp.date())
    return {'rows':senator,'stamp':stamp,'data_row_locations':[i for i,_ in selected],
        'checkbox_evidence':checkbox_evidence,'candidate_name_filter':{'kind':'UNKNOWN','reason':'INPUT_VALUE_NOT_CAPTURED'},
        'data_rows':visible,'pagination':f'1 – {visible} of {page}'}


class LinkIndex(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.link=None;self.links=[];self.title=False;self.titles=[]
    def handle_starttag(self,t,a):
        if t=='a':self.link=[dict(a).get('href',''),'']
        if t=='title':self.title=True
    def handle_data(self,d):
        if self.link is not None:self.link[1]+=d
        if self.title:self.titles.append(d)
    def handle_endtag(self,t):
        if t=='a' and self.link is not None:self.links.append(tuple(self.link));self.link=None
        if t=='title':self.title=False


@dataclass(repr=False,frozen=True)
class ObservationBundle:
    local_records:tuple=field(repr=False)
    _public:dict=field(repr=False)
    def __repr__(self):return 'IdahoObservationBundle(local_only=True)'
    def public_diagnostics(self):
        # Detached copy of a fixed allowlist projection, never arbitrary record
        # dictionaries or parsed names/details/body text.
        return json.loads(json.dumps(self._public))


def _reconcile_payloads(payloads,index_html,shell_html,source_hashes):
    """Pure authored-fixture/parser primitive; real-source binding is read_sources."""
    index=LinkIndex();index.feed(index_html)
    require(any(urljoin('https://voteidaho.gov/idaho-general-election/',href)==URL and norm(label)=='See The Full Candidate List' for href,label in index.links))
    require('2026 Idaho General Election' in index_html)
    shell=LinkIndex();shell.feed(shell_html);require(norm(''.join(shell.titles))=='Idaho Candidate Filing Portal - ReFrame')
    require(type(payloads) is list and len(payloads)==3)
    parsed=[_parse_capture(p,i) for i,p in enumerate(payloads)]
    require(parsed[0]['stamp']<parsed[1]['stamp']<parsed[2]['stamp'])
    require(parsed[0]['rows']==parsed[1]['rows']==parsed[2]['rows'])
    records=[]
    for number,row in enumerate(parsed[2]['rows'],1):
        record={'record_role':'OBSERVED_GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY','official_name':row[0],
            'source_district_type_literal':row[1],'source_office_literal':row[2],'source_district_literal':row[3],
            'source_party_label':row[4],'date_filed_literal':row[5],
            'date_filed_iso':datetime.strptime(row[5],'%m/%d/%Y').date().isoformat(),
            'source_write_in_cell_literal':row[6],'source_status_literal':row[7],
            'source_locations':[{'source_id':SOURCE_IDS[i+2],'data_row_1_based':number} for i in range(3)]}
        record.update({key:{'kind':'UNKNOWN','reason':reason} for key,reason in UNKNOWN_REASONS.items()});records.append(record)
    # Values below are constants or strictly validated finite/hash/date fields.
    require(type(source_hashes) is dict and tuple(source_hashes)==SOURCE_IDS)
    import re
    require(all(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h) for h in source_hashes.values()))
    public={'scope':'OBSERVED_SOURCE_LOCAL_STATUS_HISTORY_ONLY','source_hashes':source_hashes,
        'header_semantic_columns':list(SEMANTIC_HEADERS),'source_title_role':'SOURCE_LABEL_NOT_FINAL_ACCEPTANCE',
        'source_election_context':ELECTION,'source_local_row_count':5,'Approved_count':4,'Withdrawn_count':1,
        'safe_literal_party_status_date_inventory':[{'party':p,'status':s,'date_filed':d} for p,s,d in INVENTORY],
        'blank_source_district_and_writein_cells_preserved':True,'all_three_full_nine_cell_tuples_agree':True,
        'capture_observed_clocks_utc':[p['stamp'].isoformat() for p in parsed],
        'capture_pagination':[p['pagination'] for p in parsed],
        'status_checkbox_evidence':[p['checkbox_evidence'] for p in parsed],
        'candidate_name_input_evidence':[p['candidate_name_filter'] for p in parsed],
        'typed_unknown_reasons':UNKNOWN_REASONS.copy(),'unfiltered_global_completeness':'UNKNOWN_NOT_CAPTURED',
        'source_adoption':False,'readiness_integration':False,'final_ballots_accepted':0,'model_calls':0,'cost_usd':0}
    return ObservationBundle(tuple(records),public)


def _root(root):
    p=Path(root).absolute();require('..' not in p.parts)
    require(not any(x.is_symlink() for x in (p,*p.parents)))
    require(p.is_dir());p=p.resolve()
    require(Path(__file__).resolve()==p/'src/civiclab/e01/idaho_v1_8.py')
    return p


def _read_one(root,source):
    relative=Path(source['path']);require(not relative.is_absolute() and '..' not in relative.parts)
    p=root/relative;require(not any(x.is_symlink() for x in (p,*p.parents) if x.is_relative_to(root)))
    require(p.resolve().is_relative_to(root/'data/raw') and p.is_file())
    size=p.stat().st_size;require(type(source['bytes']) is int and 0<=size==source['bytes']<=1048576)
    with p.open('rb') as stream:data=stream.read(1048576)
    require(p.stat().st_size==size and len(data)==size and digest(data)==source['sha256'])
    return data


def _read_sources(root,contract):
    _admit_metadata(contract)  # Exact frozen contract before any root/input reads.
    root=_root(root);sources=contract['inputs'];require(sum(s['bytes'] for s in sources)<=5242880)
    raw=[_read_one(root,s) for s in sources]
    payloads=[strict_json(data) for data in raw[2:]]
    result=_reconcile_payloads(payloads,raw[0].decode('utf-8'),raw[1].decode('utf-8'),{s['source_id']:s['sha256'] for s in sources})
    # Every source is checked again after extraction, before returning a result.
    for source,before in zip(sources,raw):require(_read_one(root,source)==before)
    return result


def read_sources(root,contract):
    """Read only independently reviewed local source identities; no persistence.

    This candidate must not be invoked on cached real sources until its separate
    code/input/runtime/privacy review and lead authorization. Fixture tests patch
    the trusted contract digest/origin explicitly for authored temporary inputs.
    """
    return _safe(lambda:_read_sources(root,contract))
