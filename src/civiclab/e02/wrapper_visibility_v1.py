"""Exact40-slot wrapper x own-support visibility experiment: pure functions only.

No file/key/owner/network/dispatch operations. Pricing helpers compute bounds,
not current prices, budget authority or financial transitions. Authored outputs
are MOCK arithmetic fixtures, not scientific treatment-positive controls.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import re

from ..common import canonical_bytes, canonical_hash
from ..model import ExecutionBlocked, micros
from ..production_price_v4 import validate_terms, quote, decimal_price, financial_context
from ..production_admission_v4 import _payload
from .exploratory_pilot_analysis_v1 import _load
from .exploratory_response_v1 import parse_survey_response
from .alignment_anchoring_v1 import _bounded_answer, _number
from .instrument import score as thermometer_score

PROTOCOL_SHA256='9c2ab0741b29091a590f224821098c2a64da6ddf6c996c81e89c194d71df9428'
KEYS={'democratic_party','republican_party','policy_support','factual_answer'}
NUMERIC=('democratic_party','republican_party','policy_support')
FACTUAL=('INCREASE_40','NOT_REPORTED')
DISPATCHED={'ANSWER','PARSE_ERROR','FAILED_UNCERTAIN','CANCELLED'}
EXTRA={'SKIPPED_INVALID_PRE','NOT_ATTEMPTED'}
BOUND=262144


def load_protocol(raw):
    if type(raw) is not bytes or len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA256:
        raise ExecutionBlocked('exact frozen wrapper-visibility candidate required')
    p=_load(raw,65536)
    for key,value in (('assignment',p['jobs']),('instrument',p['instrument']),('topics',p['topics'])):
        if canonical_hash(value)!=p[key+'_canonical_sha256']:
            raise ExecutionBlocked('frozen assignment/instrument/topics differ')
    if len(p['jobs'])!=40:raise ExecutionBlocked('finite40-slot manifest required')
    return p


def parse_response(response):
    parsed=parse_survey_response(response)
    if parsed['status']!='ANSWER':return parsed
    try:_bounded_answer(parsed['answer'])
    except (ValueError,TypeError,RecursionError,UnicodeError,OverflowError):
        return {'status':'PARSE_ERROR','answer':None,'diagnostic':'WRAPPER_OBJECT_OR_BOUND'}
    return parsed


def _shape(answer):return type(answer) is dict and set(answer)<=KEYS

def valid_baseline(answer):return _shape(answer) and _number(answer.get('policy_support'))


@financial_context
def cost_envelope(raw,terms):
    p=load_protocol(raw);validate_terms(terms)
    if any(terms[k]!=p['model'][k] for k in ('model','requested_route','reported_provider','route_scope','output_parameter')):
        raise ExecutionBlocked('fixed model/provider/route/output contract required')
    amount=micros(Decimal(8192)*decimal_price(terms['input_usd_per_token'])+
                  Decimal(256)*decimal_price(terms['output_usd_per_token'])+decimal_price(terms['request_fee_usd']))
    if not 0<amount<=1785 or 40*amount>75000:
        raise ExecutionBlocked('fixed call/batch quote bound exceeded')
    return {'maximum_POSTs':40,'maximum_billing_GETs':120,'maximum_catalog_GETs':4,
            'per_call_microusd':amount,'maximum_batch_microusd':40*amount,
            'proposed_subcap_microusd':75000,'actual_authority':False}


def _compile(p,terms,job,before):
    topic=next(t for t in p['topics'] if t['topic_id']==job['topic_id']);i=p['instrument']
    survey={'instructions':i['response_instructions'],'thermometer_instructions':i['thermometer_instructions'],
        'items':deepcopy(i['party_items'])+[
            {'id':'policy_support','question':topic['support_question'],'minimum':0,'maximum':100,'instructions':i['policy_support_instructions']},
            {'id':'factual_answer','question':topic['factual_question'],'allowed_values':list(FACTUAL),'instructions':i['factual_answer_instructions']}]}
    request={'phase':job['phase'],'seed':job['pair_seed'],'profile':deepcopy(job['profile']),
        'survey':survey,'item_order':deepcopy(job['item_order']),
        'notice':{'text':topic['reference_text' if job['phase']=='pre' else 'treatment_text'],
                  'source_label':p['source_label'],'presentation_label':p['presentation_labels'][job['wrapper']]}}
    if job['visibility']=='SHOWN':request['pre_response']={'policy_support':before['policy_support']}
    messages=[{'role':'system','content':p['system_prompt']},
              {'role':'user','content':json.dumps(request,sort_keys=True,allow_nan=False)}]
    envelope=quote(messages,256,terms)
    if envelope['input_token_bound']>8192 or envelope['reserved_microusd']>1785:
        raise ExecutionBlocked('exact adaptive request exceeds frozen bounds')
    payload=_payload(messages,job['pair_seed'],256,terms)
    if len(canonical_bytes(payload))>BOUND:raise ExecutionBlocked('payload bound')
    return {**{k:job[k] for k in ('execution_order','phase','pair_seed','baseline_execution_order','topic_id','wrapper','visibility')},
        'unit_sha256':canonical_hash(job),'request':request,'messages':messages,'payload':payload,
        'payload_sha256':canonical_hash(payload),'envelope':envelope,'actual_authority':False}


def _envelope(p,records,provenance):
    if provenance not in ('MOCK','EXPLORATORY_REAL_MODEL'):raise ExecutionBlocked('explicit provenance required')
    e={'protocol_sha256':PROTOCOL_SHA256,'assignment_sha256':p['assignment_canonical_sha256'],
       'instrument_sha256':p['instrument_canonical_sha256'],'topics_sha256':p['topics_canonical_sha256'],
       'response_provenance':provenance,'records':records}
    if len(canonical_bytes(e))>BOUND:raise ExecutionBlocked('envelope bound')
    return e


def _walk(p,terms,transcript,stopped=False):
    if type(transcript) is not list or len(transcript)>40:raise ExecutionBlocked('finite ordered transcript required')
    rows=[];pre={};position=0;halt=False
    for job in p['jobs']:
        i=job['execution_order'];phase=job['phase'];before=pre.get(job['baseline_execution_order'])
        empty={'execution_order':i,'phase':phase,'answer':None}
        if halt:rows.append({**empty,'status':'NOT_ATTEMPTED'});continue
        if job['visibility']=='SHOWN' and not valid_baseline(before):
            rows.append({**empty,'status':'SKIPPED_INVALID_PRE'});continue
        compiled=_compile(p,terms,job,before)
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


def _checked_answer(answer):
    try:_bounded_answer(answer)
    except (ValueError,TypeError,RecursionError,UnicodeError,OverflowError):
        raise ExecutionBlocked('answer contradicts bounded object parser') from None


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
        or type(e['records']) is not list or len(e['records'])!=40):
        raise ExecutionBlocked('exact40-disposition frozen envelope required')
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


def _scores(answer,party,key,status):
    def quality(item):
        if status in EXTRA:return 'UNASKED'
        if status!='ANSWER':return status
        if not _shape(answer):return 'INVALID_SHAPE'
        if item not in answer:return 'MISSING_KEY'
        if answer[item] is None:return 'MISSING_NULL'
        valid=_number(answer[item]) if item in NUMERIC else type(answer[item]) is str and answer[item] in FACTUAL
        return 'VALID' if valid else 'INVALID'
    q={k:quality(k) for k in sorted(KEYS)}
    numeric={k:answer[k] if q[k]=='VALID' else None for k in NUMERIC}
    comp=q['factual_answer']
    if comp=='VALID':comp='CORRECT' if answer['factual_answer']==key else 'INCORRECT'
    return {'support':numeric['policy_support'],'party_gap':thermometer_score({k:numeric[k] for k in ('democratic_party','republican_party')},party)['primary'],
            'item_quality':q,'comprehension':comp,'valid_for_shown':status=='ANSWER' and valid_baseline(answer)}


def _difference(a,b):return a-b if a is not None and b is not None else None


def _summary(rows,planned):
    values=[r['value'] for r in rows if r['value'] is not None]
    return {'planned_units':planned,'complete_units':len(values),'mean_points':sum(values)/len(values) if values else None,
        'min_points':min(values) if values else None,'max_points':max(values) if values else None,'unit_values':rows,
        'status':'NOT_ESTIMABLE' if not values else 'DESCRIPTIVE_FULL_PLANNED_SAMPLE' if len(values)==planned else 'DESCRIPTIVE_PARTIAL',
        'interval_95':None,'uncertainty_status':'NO_INFERENTIAL_INTERVAL_PURPOSIVE_CONTEXTS_TWO_TOPICS'}


def _comprehension(scores):
    c=Counter(x['comprehension'] for x in scores);valid=c['CORRECT']+c['INCORRECT'];planned=len(scores)
    return {'planned':planned,'valid':valid,'correct':c['CORRECT'],'observed_factual_errors':c['INCORRECT'],
            'correct_per_planned':c['CORRECT']/planned if planned else None,'correct_per_valid':c['CORRECT']/valid if valid else None,
            'quality_counts':dict(c)}


def analyze(raw,envelope_bytes):
    p=load_protocol(raw);e=_load(envelope_bytes,BOUND);halt=_validate_records(p,e)
    scored={};counts=Counter();topic_map={t['topic_id']:t for t in p['topics']}
    for job,row in zip(p['jobs'],e['records']):
        topic=topic_map[job['topic_id']];key=topic['reference_answer' if job['phase']=='pre' else 'treatment_answer']
        scored[job['execution_order']]=_scores(row['answer'],job['profile']['party'],key,row['status']);counts[row['status']]+=1
    pre={(j['profile']['profile_id'],j['topic_id']):scored[j['execution_order']] for j in p['jobs'] if j['phase']=='pre'}
    cells={(j['profile']['profile_id'],j['topic_id'],j['wrapper'],j['visibility']):scored[j['execution_order']] for j in p['jobs'] if j['phase']=='post'}
    wrappers={v:[] for v in ('OMITTED','SHOWN')};interactions=[];matched_omit=[];matched_shown=[];magnitudes=[];reversals=[];drifts=[];gaps={v:[] for v in wrappers}
    for profile in p['profiles']:
        pid=profile['profile_id']
        for topic in p['topics']:
            tid=topic['topic_id'];info={'profile_id':pid,'party':profile['party'],'topic_id':tid};ds={}
            for vis in wrappers:
                news=cells[pid,tid,'NEWS',vis];social=cells[pid,tid,'SOCIAL',vis]
                ds[vis]=_difference(social['support'],news['support'])
                wrappers[vis].append({**info,'value':ds[vis]})
                gaps[vis].append({**info,'value':_difference(social['party_gap'],news['party_gap'])})
                for wrapper in ('NEWS','SOCIAL'):
                    drifts.append({**info,'wrapper':wrapper,'visibility':vis,'value':_difference(cells[pid,tid,wrapper,vis]['support'],pre[pid,tid]['support'])})
            a,b=ds['OMITTED'],ds['SHOWN'];complete=pre[pid,tid]['valid_for_shown'] and a is not None and b is not None
            interactions.append({**info,'value':b-a if complete else None})
            matched_omit.append({**info,'value':a if complete else None});matched_shown.append({**info,'value':b if complete else None})
            magnitude=abs(b)-abs(a) if complete else None;reverse=(a*b<0) if complete else None
            magnitudes.append({**info,'value':magnitude})
            reversals.append({**info,'omitted':a,'shown':b,'complete':complete,'sign_reversal':reverse,
                              'compatible_with_magnitude_masking':magnitude<0 and not reverse if complete else None})
    primary=_summary(wrappers['OMITTED'],8)
    comp={}
    for tid in topic_map:
        comp[tid]={}
        for wrapper in ('NEWS','SOCIAL'):
            comp[tid][wrapper]={vis:_comprehension([cells[x['profile_id'],tid,wrapper,vis] for x in p['profiles']]) for vis in wrappers}
    quality=Counter((k,v) for s in scored.values() for k,v in s['item_quality'].items())
    return {'kind':'E02_WRAPPER_VISIBILITY_DESCRIPTIVE_V1','response_provenance':e['response_provenance'],
        'protocol_sha256':PROTOCOL_SHA256,'response_envelope_sha256':hashlib.sha256(envelope_bytes).hexdigest(),
        'batch_status':'STOPPED' if halt else 'COMPLETE_RECORDED_DISPOSITIONS','primary_wrapper_omitted':primary,
        'wrapper_contrasts':{v:_summary(rows,8) for v,rows in wrappers.items()},
        'visibility_interaction':_summary(interactions,8),'matched_wrapper_contrasts':{'OMITTED':_summary(matched_omit,8),'SHOWN':_summary(matched_shown,8)},
        'absolute_wrapper_magnitude_change':_summary(magnitudes,8),'direction_diagnostics':{'planned_units':8,'complete_units':sum(r['complete'] for r in reversals),
        'sign_reversal_count':sum(r['sign_reversal'] is True for r in reversals),'compatible_magnitude_masking_count':sum(r['compatible_with_magnitude_masking'] is True for r in reversals),'unit_values':reversals},
        'primary_by_topic':{tid:_summary([r for r in wrappers['OMITTED'] if r['topic_id']==tid],4) for tid in topic_map},
        'primary_by_party':{party:_summary([r for r in wrappers['OMITTED'] if r['party']==party],4) for party in ('D','R')},
        'leave_one_topic_out':{tid:_summary([r for r in wrappers['OMITTED'] if r['topic_id']!=tid],4) for tid in topic_map},
        'separate_party_gap_wrapper_contrasts':{v:_summary(rows,8) for v,rows in gaps.items()},'support_reference_changes':drifts,
        'comprehension':comp,'baseline_quality':{tid:{'planned':4,'valid_for_shown':sum(pre[x['profile_id'],tid]['valid_for_shown'] for x in p['profiles']),
        'comprehension':_comprehension([pre[x['profile_id'],tid] for x in p['profiles']])} for tid in topic_map},
        'phase_counts':dict(counts),'item_quality_counts':[{'item':k,'quality':q,'count':n} for (k,q),n in sorted(quality.items())],
        'scored_phases':[{'execution_order':i,**scored[i]} for i in range(40)],
        'limitations':p['scope']+' No CI,p-value,equivalence,anchoring mechanism or adaptive scaling. Matched unit seeds are not common random numbers or serving determinism.',
        'actual_authority':False}
