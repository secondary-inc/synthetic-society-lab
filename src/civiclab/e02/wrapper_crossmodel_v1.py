"""Fixed eighty-slot wrapper/configuration follow-up; pure, no paid authority.

Reuse the frozen wrapper compiler/parser/scorer on NEW per-configuration answers.
Comparisons are descriptive matched intersections, not model-family causal effects.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
from ..common import canonical_bytes, canonical_hash
from ..model import ExecutionBlocked, micros
from ..production_price_v4 import validate_terms, decimal_price, financial_context
from .exploratory_pilot_analysis_v1 import _load
from . import wrapper_visibility_v1 as base

PROTOCOL_SHA256='19fff8964e84c536d7b3969eeab18e1a14bff69744b7752c7fbe9b22d68cccc1'
BOUND=262144
ROLES=('A','B')
DISPATCHED=base.DISPATCHED
EXTRA=base.EXTRA
parse_response=base.parse_response
valid_baseline=base.valid_baseline
_checked_answer=base._checked_answer


def _source_bytes(p):
    return ''.join(p['base_protocol_utf8_chunks']).encode('utf-8')


def load_protocol(raw):
    if type(raw) is not bytes or len(raw)>131072 or hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA256:
        raise ExecutionBlocked('exact frozen eighty-slot wrapper crossmodel protocol required')
    p=_load(raw,131072);source=base.load_protocol(_source_bytes(p))
    if (len(p['jobs'])!=80 or canonical_hash(p['jobs'])!=p['assignment_canonical_sha256']
        or p['source_protocol_sha256']!=base.PROTOCOL_SHA256 or set(p['models'])!=set(ROLES)):
        raise ExecutionBlocked('frozen eighty-slot assignment/source differs')
    for name in ('profiles','topics','instrument','system_prompt','source_label','presentation_labels',
                 'instrument_canonical_sha256','topics_canonical_sha256'):
        p[name]=deepcopy(source[name])
    return p


@financial_context
def cost_envelope(raw,terms):
    p=load_protocol(raw)
    if type(terms) is not dict or set(terms)!=set(ROLES):
        raise ExecutionBlocked('exact two configuration contracts required')
    ceilings={}
    for role in ROLES:
        t=terms[role];validate_terms(t)
        if any(t[k]!=v for k,v in p['models'][role].items()):
            raise ExecutionBlocked('fixed model/provider/route/output contract required')
        amount=micros(Decimal(8192)*decimal_price(t['input_usd_per_token'])+
                      Decimal(256)*decimal_price(t['output_usd_per_token'])+decimal_price(t['request_fee_usd']))
        if not 0<amount<=1785:raise ExecutionBlocked('fixed per-call quote bound exceeded')
        ceilings[role]=amount
    batch=40*sum(ceilings.values())
    if batch>200000:raise ExecutionBlocked('fixed batch quote bound exceeded')
    return {'maximum_POSTs':80,'maximum_billing_GETs':240,'maximum_catalog_GETs':16,
            'per_model_call_microusd':ceilings,'maximum_batch_microusd':batch,
            'proposed_subcap_microusd':200000,'actual_authority':False}


def _compile(p,terms,job,before):
    compiled=base._compile(p,terms,job,before)
    return {**compiled,'model_key':job['model_key'],'base_execution_order':job['base_execution_order']}


def _envelope(p,records,provenance):
    if provenance not in ('MOCK','EXPLORATORY_REAL_MODEL'):raise ExecutionBlocked('explicit provenance required')
    e={'protocol_sha256':PROTOCOL_SHA256,'assignment_sha256':p['assignment_canonical_sha256'],
       'instrument_sha256':p['instrument_canonical_sha256'],'topics_sha256':p['topics_canonical_sha256'],
       'response_provenance':provenance,'records':records}
    if len(canonical_bytes(e))>BOUND:raise ExecutionBlocked('envelope bound')
    return e


def _walk(p,terms,transcript,stopped=False):
    if type(transcript) is not list or len(transcript)>80:raise ExecutionBlocked('finite ordered transcript required')
    rows=[];pre={};position=0;halt=False
    for job in p['jobs']:
        i=job['execution_order'];phase=job['phase'];before=pre.get(job['baseline_execution_order'])
        empty={'execution_order':i,'phase':phase,'answer':None}
        if halt:rows.append({**empty,'status':'NOT_ATTEMPTED'});continue
        if job['visibility']=='SHOWN' and not valid_baseline(before):
            rows.append({**empty,'status':'SKIPPED_INVALID_PRE'});continue
        compiled=_compile(p,terms[job['model_key']],job,before)
        if position==len(transcript):
            if stopped:halt=True;rows.append({**empty,'status':'NOT_ATTEMPTED'});continue
            return {'status':'REQUEST_READY_NOT_ADMITTED','request':compiled,'derived_records':rows,
                    'transcript_sha256':canonical_hash(transcript),'actual_authority':False}
        row=transcript[position]
        if (type(row) is not dict or set(row)!={'execution_order','phase','payload_sha256','status','answer'}
            or type(row['execution_order']) is not int or row['execution_order']!=i or row['phase']!=phase
            or type(row['status']) is not str or row['status'] not in DISPATCHED
            or row['payload_sha256']!=compiled['payload_sha256']
            or (row['status']!='ANSWER' and row['answer'] is not None)):
            raise ExecutionBlocked('sequence/phase/payload/disposition differs')
        if row['status']=='ANSWER':_checked_answer(row['answer'])
        rows.append({k:row[k] for k in ('execution_order','phase','status','answer')});position+=1
        if phase=='pre':pre[i]=row['answer'] if row['status']=='ANSWER' else None
        if row['status'] in ('FAILED_UNCERTAIN','CANCELLED'):halt=True
    if position!=len(transcript):raise ExecutionBlocked('extra response after completion/stop')
    return {'status':'STOPPED' if halt else 'COMPLETE','records':rows,
            'response_envelope':_envelope(p,rows,'MOCK'),'actual_authority':False}


def next_action(raw,terms,transcript_bytes):
    p=load_protocol(raw);cost_envelope(raw,terms)
    return _walk(p,terms,_load(transcript_bytes,BOUND))


def response_envelope(raw,terms,transcript_bytes,*,stopped=False,response_provenance='MOCK'):
    """Replay exact payloads; no owner/billing authentication is implied."""
    if type(stopped) is not bool:raise ExecutionBlocked('literal stop flag required')
    p=load_protocol(raw);cost_envelope(raw,terms)
    state=_walk(p,terms,_load(transcript_bytes,BOUND),stopped)
    if state['status']=='REQUEST_READY_NOT_ADMITTED':
        raise ExecutionBlocked('incomplete nonstopped transcript cannot be exported')
    return _envelope(p,state['records'],response_provenance)


def _validate_records(p,e):
    if (type(e) is not dict or set(e)!={'protocol_sha256','assignment_sha256','instrument_sha256','topics_sha256','response_provenance','records'}
        or e['protocol_sha256']!=PROTOCOL_SHA256 or e['assignment_sha256']!=p['assignment_canonical_sha256']
        or e['instrument_sha256']!=p['instrument_canonical_sha256'] or e['topics_sha256']!=p['topics_canonical_sha256']
        or e['response_provenance'] not in ('MOCK','EXPLORATORY_REAL_MODEL')
        or type(e['records']) is not list or len(e['records'])!=80):
        raise ExecutionBlocked('exact80-disposition frozen envelope required')
    pre={};halt=False
    for job,row in zip(p['jobs'],e['records']):
        if (type(row) is not dict or set(row)!={'execution_order','phase','status','answer'}
            or type(row['execution_order']) is not int or row['execution_order']!=job['execution_order']
            or row['phase']!=job['phase'] or type(row['status']) is not str or row['status'] not in DISPATCHED|EXTRA
            or (row['status']!='ANSWER' and row['answer'] is not None)):
            raise ExecutionBlocked('malformed or reordered envelope record')
        status=row['status'];skip=job['visibility']=='SHOWN' and not valid_baseline(pre.get(job['baseline_execution_order']))
        if (halt and status!='NOT_ATTEMPTED') or (status=='SKIPPED_INVALID_PRE' and not skip) or (not halt and skip and status not in ('SKIPPED_INVALID_PRE','NOT_ATTEMPTED')):
            raise ExecutionBlocked('unsupported skip/attempt/terminal disposition')
        if status=='ANSWER':_checked_answer(row['answer'])
        if job['phase']=='pre':pre[job['execution_order']]=row['answer'] if status=='ANSWER' else None
        if status in ('FAILED_UNCERTAIN','CANCELLED','NOT_ATTEMPTED'):halt=True
    return halt


def analyze(raw,envelope_bytes):
    p=load_protocol(raw);e=_load(envelope_bytes,BOUND);halt=_validate_records(p,e)
    per_configuration={}
    for role in ROLES:
        by_base={j['base_execution_order']:r for j,r in zip(p['jobs'],e['records']) if j['model_key']==role}
        projected={'protocol_sha256':base.PROTOCOL_SHA256,
            'assignment_sha256':base.load_protocol(_source_bytes(p))['assignment_canonical_sha256'],
            'instrument_sha256':p['instrument_canonical_sha256'],'topics_sha256':p['topics_canonical_sha256'],
            'response_provenance':e['response_provenance'],
            'records':[{**by_base[i],'execution_order':i} for i in range(40)]}
        per_configuration[role]=base.analyze(_source_bytes(p),canonical_bytes(projected))
    matched={}
    metrics=('primary_wrapper_omitted','visibility_interaction','absolute_wrapper_magnitude_change')
    for metric in metrics:
        a=per_configuration['A'][metric]['unit_values'];b=per_configuration['B'][metric]['unit_values']
        rows=[];arms={r:[] for r in ROLES}
        for left,right in zip(a,b):
            identity={k:left[k] for k in ('profile_id','party','topic_id')}
            if identity!={k:right[k] for k in identity}:raise ExecutionBlocked('matched unit identity differs')
            complete=left['value'] is not None and right['value'] is not None
            rows.append({**identity,'value':right['value']-left['value'] if complete else None})
            for role,item in (('A',left),('B',right)):
                arms[role].append({**identity,'value':item['value'] if complete else None})
        matched[metric]={'B_minus_A':base._summary(rows,8),
            'same_intersection_configurations':{role:base._summary(values,8) for role,values in arms.items()},
            'by_topic':{t['topic_id']:base._summary([r for r in rows if r['topic_id']==t['topic_id']],4) for t in p['topics']},
            'leave_one_topic_out':{t['topic_id']:base._summary([r for r in rows if r['topic_id']!=t['topic_id']],4) for t in p['topics']}}
    return {'kind':'E02_WRAPPER_CROSSMODEL_DESCRIPTIVE_V1','protocol_sha256':PROTOCOL_SHA256,
        'response_envelope_sha256':hashlib.sha256(envelope_bytes).hexdigest(),
        'response_provenance':e['response_provenance'],
        'batch_status':'STOPPED' if halt else 'COMPLETE_RECORDED_DISPOSITIONS',
        'planned_baselines':16,'planned_posts':64,'configurations':deepcopy(p['models']),
        'configuration_analyses':per_configuration,'matched_configuration_contrasts':matched,
        'primary_metric':'primary_wrapper_omitted','difference_direction':'B_MINUS_A',
        'saved_answers_reused':False,'limitations':p['scope']+
        ' Matched-complete descriptions can select different units across estimands; show all denominators.'+
        ' No inferential interval, p-value, equivalence or serving determinism. Prior choices informed configuration selection.',
        'actual_authority':False}
