"""Pure MOCK-only Clerk contracts. No source reads, parser, authority or REAL adapter."""
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
import re

SPAN_FIELDS = frozenset(['source_id', 'source_sha256', 'physical_pdf_page_1_based', 'printed_page_label', 'extraction_backend', 'backend_version', 'text_coordinate_system', 'text_start', 'text_end', 'text_span_utf8_sha256', 'render_bbox_points', 'field_roles'])
RAW_FIELDS = frozenset(['schema_version', 'kind', 'occurrence_id', 'source_id', 'source_sha256', 'source_spans', 'office_literal', 'state_literal', 'contest_label_literal', 'event_date_literal', 'stage_literal', 'special_term_literal', 'candidate_name_literal', 'party_line_literal', 'votes_literal', 'unit_literal', 'mode_literal', 'footnote_literals', 'source_context_span_refs'])
ANNOTATION_FIELDS = frozenset(['schema_version', 'raw_occurrence_id', 'raw_occurrence_canonical_sha256', 'evidence_refs', 'state', 'office', 'seat_class', 'term_context', 'cycle_year', 'event_year', 'event_date', 'stage', 'special', 'unit_kind', 'unit_id', 'mode', 'record_role', 'candidate_id', 'party_line_id', 'party_family', 'votes', 'normalization_rule_ref', 'adjudication_status'])
NOMINEE_FIELDS = frozenset(['schema_version', 'kind', 'occurrence_id', 'source_id', 'source_sha256', 'source_spans', 'publication_date_evidence', 'office_literal', 'state_literal', 'district_or_seat_literal', 'candidate_name_literal', 'party_literal', 'footnote_literals', 'source_role', 'typed_unknowns'])
FEATURE_FIELDS = frozenset(['race_id', 'office', 'prior_margin_pp', 'national_shift_pp', 'incumbency_adjustment_pp', 'feature_as_of', 'cutoff', 'source_hashes'])

SENATE_STATES = frozenset('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())


class ContractRejected(ValueError):
    def __init__(self):super().__init__('CLERK_M1_CONTRACT_REFUSED')


def require(ok):
    if not ok:raise ContractRejected()


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf8')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def is_hash(x):return type(x) is str and re.fullmatch('[0-9a-f]{64}',x) is not None

def snapshot(value):
    budget=[0]
    def clone(x,depth):
        budget[0]+=1;require(depth<=16 and budget[0]<=20000)
        if x is None or type(x) is bool:return x
        if type(x) is int:require(abs(x)<=10**30);return x
        if type(x) is float:require(math.isfinite(x));return x
        if type(x) is str:require(len(x)<=40000);return x
        if type(x) is list:return [clone(v,depth+1) for v in x]
        if type(x) is dict:
            require(all(type(k) is str for k in x));return {k:clone(v,depth+1) for k,v in x.items()}
        raise ContractRejected()
    return clone(value,0)


def exact(x,keys):require(type(x) is dict and set(x)==set(keys))
def unknown():return {'kind':'UNKNOWN','reason':'REQUIRES_SEPARATE_SOURCE_INSPECTION'}
def is_unknown(x):return type(x) is dict and set(x)=={'kind','reason'} and x['kind']=='UNKNOWN' and type(x['reason']) is str and 0<len(x['reason'])<=256

def literal(x):
    require(type(x) is str and 0<len(x)<=256 and not any(ord(c)<32 for c in x));return x


def authored_context(source_id,pages,role='AUTHORED_HISTORICAL_COUNTS'):
    source_id,pages,role=snapshot([source_id,pages,role])
    require(type(source_id) is str and re.fullmatch('DEMO_[A-Z0-9_]+',source_id) is not None)
    require(role in {'AUTHORED_HISTORICAL_COUNTS','AUTHORED_NOMINEE_COMPILATION'})
    require(type(pages) is list and 1<=len(pages)<=100 and all(type(p) is str and len(p)<=40000 for p in pages))
    obj={'label':'MOCK','source_id':source_id,'pages':pages,'role':role}
    require(len(canonical(obj))<=1048576)
    return {**obj,'source_sha256':digest(canonical(obj))}


def _context(x):
    exact(x,{'label','source_id','pages','role','source_sha256'})
    expected=authored_context(x['source_id'],x['pages'],x['role'])
    require(canonical(x)==canonical(expected));return expected


def validate_span(span,context):
    span,context=snapshot([span,context]);context=_context(context);exact(span,SPAN_FIELDS)
    require(span['source_id']==context['source_id'] and span['source_sha256']==context['source_sha256'])
    p=span['physical_pdf_page_1_based'];require(type(p) is int and 1<=p<=len(context['pages']))
    require(span['extraction_backend']=='AUTHORED_UTF8_PAGE_ARRAY_V1' and span['backend_version']=='1.0.0')
    require(span['text_coordinate_system']=='UTF8_BYTE_OFFSETS_V1')
    raw=context['pages'][p-1].encode('utf8');a=span['text_start'];b=span['text_end']
    require(type(a) is int and type(b) is int and 0<=a<b<=len(raw))
    try:raw[:a].decode('utf8');part=raw[a:b].decode('utf8')
    except UnicodeError:raise ContractRejected() from None
    require(is_hash(span['text_span_utf8_sha256']) and digest(raw[a:b])==span['text_span_utf8_sha256'])
    require(is_unknown(span['render_bbox_points']))
    require(is_unknown(span['printed_page_label']) or (type(span['printed_page_label']) is str and 0<len(span['printed_page_label'])<=24))
    require(type(span['field_roles']) is list and len(span['field_roles'])==1 and span['field_roles'][0] in RAW_FIELDS|NOMINEE_FIELDS)
    return part


def _raw(row,context,fields,kind):
    row,context=snapshot([row,context]);context=_context(context);exact(row,fields)
    require(type(row['schema_version']) is int and row['schema_version']==1 and row['kind']==kind)
    require(row['source_id']==context['source_id'] and row['source_sha256']==context['source_sha256'])
    require(type(row['occurrence_id']) is str and re.fullmatch('DEMO_[A-Z0-9_]+',row['occurrence_id']) is not None)
    require(type(row['source_spans']) is list and 1<=len(row['source_spans'])<=128)
    witnesses={}
    for span in row['source_spans']:
        text=validate_span(span,context);field=span['field_roles'][0];require(field in fields)
        witnesses.setdefault(field,[]).append(text)
    for field,value in row.items():
        if field.endswith('_literal'):
            if is_unknown(value):continue
            literal(value);require(witnesses.get(field)==[value])
        elif field=='footnote_literals':
            require(type(value) is list and all(type(v) is str and 0<len(v)<=256 for v in value))
            require(witnesses.get(field,[])==value)
    return row,context


_PARTY={'DEMO_D_A':'DEMOCRAT','DEMO_D_B':'DEMOCRAT','DEMO_R':'REPUBLICAN','DEMO_OTHER':'OTHER',
        'DEMO_TOTAL_D':'DEMOCRAT','DEMO_TOTAL_R':'REPUBLICAN'}

def _votes(value):
    if is_unknown(value):return value
    literal(value)
    # This grammar is explicitly fictional, never a rule for uninspected PDFs.
    if value in {'-','UNOPPOSED','REDACTED'}:return unknown()
    require(re.fullmatch(r'(0|[1-9][0-9]*|[1-9][0-9]{0,2}(,[0-9]{3})+)',value) is not None)
    return int(value.replace(',',''))


@dataclass(frozen=True,repr=False)
class AuthoredRecord:
    _raw:bytes
    _annotation:bytes
    _context:bytes
    def __repr__(self):return '<MOCK Clerk record; literals withheld>'
    def raw(self):return json.loads(self._raw)
    def annotation(self):return json.loads(self._annotation)


def normalize_authored(row,context):
    row,context=_raw(row,context,RAW_FIELDS,'HISTORICAL_2020_VOTE_LINE')
    require(context['role']=='AUTHORED_HISTORICAL_COUNTS')
    require(type(row['source_context_span_refs']) is list and all(type(i) is int and 0<=i<len(row['source_spans']) for i in row['source_context_span_refs']))
    require(len(set(row['source_context_span_refs']))==len(row['source_context_span_refs']))
    required_context={'office_literal','state_literal','contest_label_literal','event_date_literal','stage_literal','special_term_literal','unit_literal','mode_literal'}
    require(required_context<={row['source_spans'][i]['field_roles'][0] for i in row['source_context_span_refs']})
    require(type(row['candidate_name_literal']) is str and row['candidate_name_literal'].startswith('DEMO_'))
    require(row['office_literal']=='SENATE' and row['state_literal'] in SENATE_STATES)
    label=row['contest_label_literal'];require(type(label) is str)
    match=re.fullmatch(r'([0-9]{4})\|C([123])\|([0-9]{4})-([0-9]{4})',label);require(match is not None)
    cycle,seat,start,end=map(int,match.groups());require(end-start==6)
    require(row['stage_literal'] in {'GEN','RUNOFF','PRI'} and row['special_term_literal'] in {'REGULAR','SPECIAL'})
    try:event=date.fromisoformat(row['event_date_literal'])
    except (ValueError,TypeError):raise ContractRejected() from None
    require(row['unit_literal']=='STATEWIDE' and row['mode_literal']=='TOTAL')
    markers=set(row['footnote_literals']);require(len(markers & {'COMPONENT','COMBINED_TOTAL','SUMMARY'})==1)
    role=next(iter(markers & {'COMPONENT','COMBINED_TOTAL','SUMMARY'}))
    party=_PARTY.get(row['party_line_literal'],unknown())
    annotation={'schema_version':1,'raw_occurrence_id':row['occurrence_id'],'raw_occurrence_canonical_sha256':digest(canonical(row)),
      'evidence_refs':[digest(canonical(s)) for s in row['source_spans']], 'state':row['state_literal'],'office':row['office_literal'],
      'seat_class':seat,'term_context':f'{start}-{end}','cycle_year':cycle,'event_year':event.year,'event_date':event.isoformat(),
      'stage':row['stage_literal'],'special':row['special_term_literal']=='SPECIAL','unit_kind':'STATEWIDE','unit_id':row['state_literal'],
      'mode':'TOTAL','record_role':role,'candidate_id':digest(row['candidate_name_literal'].encode('utf8')),
      'party_line_id':digest(row['party_line_literal'].encode('utf8')),'party_family':party,'votes':_votes(row['votes_literal']),
      'normalization_rule_ref':'AUTHORED_ASCII_COUNTS_V1_NOT_REAL_SOURCE_GRAMMAR',
      'adjudication_status':'AUTHORED_COMPLETE_REPRESENTATION' if 'COMPLETE' in markers else 'AUTHORED_INCOMPLETE_REPRESENTATION'}
    exact(annotation,ANNOTATION_FIELDS)
    return AuthoredRecord(canonical(row),canonical(annotation),canonical(context))


def _validated(record):
    require(type(record) is AuthoredRecord)
    raw=json.loads(record._raw);context=json.loads(record._context)
    derived=normalize_authored(raw,context)
    require(derived._raw==record._raw and derived._annotation==record._annotation and derived._context==record._context)
    return derived.annotation()


def validate_nominee_authored(row,context):
    row,context=_raw(row,context,NOMINEE_FIELDS,'DATED_2026_NOMINEE_LINE')
    require(context['role']=='AUTHORED_NOMINEE_COMPILATION' and row['source_role']=='DATED_NOMINEE_OBSERVATION_ONLY')
    require(row['candidate_name_literal'].startswith('DEMO_'))
    require(is_unknown(row['publication_date_evidence']))
    keys={'printed_on_final_ballot','legal_nominee_adjudication','latest_amendment_complete','independent_cutoff_binding'}
    exact(row['typed_unknowns'],keys);require(all(is_unknown(x) for x in row['typed_unknowns'].values()))
    return snapshot(row)


@dataclass(frozen=True,repr=False)
class AuthoredFeature:
    _feature:bytes
    _lineage:bytes
    def __repr__(self):return '<MOCK feature; not REAL source acceptance>'
    def feature(self):return json.loads(self._feature)
    def lineage(self):return json.loads(self._lineage)


def derive_authored_feature(records,target,representation='COMPONENTS'):
    require(type(records) is list and 1<=len(records)<=128 and representation in {'COMPONENTS','COMBINED_TOTAL'})
    rows=[_validated(r) for r in records];target=snapshot(target)
    source_versions={}
    for record in records:
        context=json.loads(record._context);source_versions.setdefault(context['source_id'],set()).add(context['source_sha256'])
    require(all(len(v)==1 for v in source_versions.values()))
    exact(target,{'label','year','state','office','seat_class','term_context','prior_constituency_sha256','target_constituency_sha256','feature_as_of','cutoff'})
    require(target['label']=='MOCK' and target['state'] in SENATE_STATES and type(target['year']) is int and target['year']==2026 and target['office']=='SENATE')
    require(type(target['seat_class']) is int and target['seat_class']==2)
    require(is_hash(target['prior_constituency_sha256']) and target['prior_constituency_sha256']==target['target_constituency_sha256'])
    try:require(date.fromisoformat(target['feature_as_of'])<=date.fromisoformat(target['cutoff']))
    except (ValueError,TypeError):raise ContractRejected() from None
    event_keys=['state','office','seat_class','term_context','cycle_year','event_year','event_date','stage','special']
    require(len({canonical({k:r[k] for k in event_keys}) for r in rows})==1)
    first=rows[0]
    require(first['office']=='SENATE' and first['stage']=='GEN' and first['special'] is False)
    require(first['event_year']==first['cycle_year']==2020 and target['year']-first['event_year']==6)
    require(first['state']==target['state'] and first['seat_class']==target['seat_class'])
    require(date.fromisoformat(first['event_date'])<date.fromisoformat(target['cutoff']))
    require(target['term_context']==f"{int(first['term_context'][:4])+6}-{int(first['term_context'][5:])+6}")
    require(all(r['record_role']!='SUMMARY' and r['adjudication_status']=='AUTHORED_COMPLETE_REPRESENTATION' for r in rows))
    require(all(type(r['votes']) is int and r['votes']>=0 and r['party_family'] in {'DEMOCRAT','REPUBLICAN','OTHER'} for r in rows))
    unique=[(r['candidate_id'],r['party_line_id'],r['unit_id'],r['mode'],r['record_role']) for r in rows]
    require(len(unique)==len(set(unique)))
    candidates={}
    for r in rows:
        group=candidates.setdefault(r['candidate_id'],{'family':r['party_family'],'COMPONENT':[],'COMBINED_TOTAL':[]})
        require(group['family']==r['party_family']);group[r['record_role']].append(r['votes'])
    totals={};other=0
    for cid,g in candidates.items():
        require(len(g['COMBINED_TOTAL'])<=1)
        if g['COMPONENT'] and g['COMBINED_TOTAL']:require(sum(g['COMPONENT'])==g['COMBINED_TOTAL'][0])
        chosen=g['COMPONENT'] if representation=='COMPONENTS' else g['COMBINED_TOTAL']
        require(bool(chosen));votes=sum(chosen)
        if g['family']=='OTHER':other+=votes
        else:
            require(g['family'] not in totals);totals[g['family']]=votes
    require(set(totals)=={'DEMOCRAT','REPUBLICAN'} and all(v>0 for v in totals.values()))
    d=totals['DEMOCRAT'];r=totals['REPUBLICAN'];margin=100*(d-r)/(d+r)
    feature={'race_id':f"2026-{target['state']}-SENATE-STATEWIDE-C2",'office':'SENATE','prior_margin_pp':margin,
             'national_shift_pp':0,'incumbency_adjustment_pp':0,'feature_as_of':target['feature_as_of'],'cutoff':target['cutoff'],
             'source_hashes':sorted({json.loads(record._context)['source_sha256'] for record in records})}
    exact(feature,FEATURE_FIELDS)
    lineage={'label':'MOCK','prior_event':{k:first[k] for k in event_keys},'annotations':rows,'raw_record_hashes':[digest(rec._raw) for rec in records],
             'representation':representation,'D':d,'R':r,'excluded_other_votes':other,'denominator':d+r,'constituency_evidence':'AUTHORED_ONLY_NOT_OFFICIAL_GEOGRAPHY','real_adoption':False}
    return AuthoredFeature(canonical(feature),canonical(lineage))


def matched_authored_status(selected_ids,features):
    selected_ids,features=snapshot([selected_ids,features])
    require(type(selected_ids) is list and len(selected_ids)==len(set(selected_ids)) and selected_ids)
    require(type(features) is list and all(type(f) is dict and set(f)==FEATURE_FIELDS for f in features))
    for f in features:
        require(type(f['race_id']) is str and re.fullmatch('2026-[A-Z]{2}-SENATE-STATEWIDE-C2',f['race_id']) is not None and f['office']=='SENATE')
        require(type(f['prior_margin_pp']) in {int,float} and math.isfinite(f['prior_margin_pp']) and abs(f['prior_margin_pp'])<=100)
        require(type(f['national_shift_pp']) is int and f['national_shift_pp']==0 and type(f['incumbency_adjustment_pp']) is int and f['incumbency_adjustment_pp']==0)
        require(type(f['source_hashes']) is list and f['source_hashes'] and all(is_hash(h) for h in f['source_hashes']))
        require(date.fromisoformat(f['feature_as_of'])<=date.fromisoformat(f['cutoff']))
    ids=[f['race_id'] for f in features];require(len(ids)==len(set(ids)) and set(ids)<=set(selected_ids))
    return {'label':'MOCK','selected_ids':selected_ids,'available_ids':sorted(ids),'blocked_ids':sorted(set(selected_ids)-set(ids)),
            'status':'COMPLETE_AUTHORED_SET' if set(ids)==set(selected_ids) else 'BLOCKED_NO_PRIOR_FEATURE','replacement_permitted':False}


def _safe_public(fn):
    def call(*args,**kwargs):
        failed=None
        try:result=fn(*args,**kwargs)
        except BaseException as exc:failed=type(exc).__name__
        if failed=='KeyboardInterrupt':raise KeyboardInterrupt()
        if failed=='SystemExit':raise SystemExit()
        if failed:raise ContractRejected()
        return result
    call.__name__=fn.__name__
    return call

for _name in ['authored_context','validate_span','normalize_authored','validate_nominee_authored','derive_authored_feature','matched_authored_status']:
    globals()[_name]=_safe_public(globals()[_name])
