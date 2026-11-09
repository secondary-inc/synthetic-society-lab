"""Frozen finite alignment/own-baseline diagnostic: pure planning and scoring.

No credential, file, owner, HTTP or spending operations. Mock numerical changes
are arithmetic oracles, not empirical model treatment-positive-control results.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import re
from decimal import Decimal

from ..common import canonical_bytes,canonical_hash
from ..model import ExecutionBlocked,micros
from ..production_price_v4 import validate_terms,quote,decimal_price,financial_context
from ..production_admission_v4 import _payload
from .exploratory_pilot_analysis_v1 import _load
from .exploratory_response_v1 import parse_survey_response
from .instrument import score as thermometer_score

PROTOCOL_SHA256='ccdb1f374924173e37a1d385715e7fa7d2aea1d5eb5daa17a403b0e9e09efb6d'
KEYS={'democratic_party','republican_party','library_support','visits_change'}
NUMERIC=('democratic_party','republican_party','library_support')
VISITS=('INCREASE_40','DECREASE_40','NOT_REPORTED')
DISPATCHED={'ANSWER','PARSE_ERROR','FAILED_UNCERTAIN','CANCELLED'}


def load_protocol(raw):
    if type(raw) is not bytes or len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA256:
        raise ExecutionBlocked('exact frozen alignment protocol bytes required')
    p=_load(raw,65536)
    if (len(p['jobs'])!=28 or canonical_hash(p['jobs'])!=p['assignment_canonical_sha256'] or
        canonical_hash(p['instrument'])!=p['instrument_canonical_sha256']):
        raise ExecutionBlocked('frozen instrument/assignment hashes differ')
    return p


def _bound(value,depth=0):
    if depth>8:raise ValueError('answer depth')
    if type(value) is dict:
        for k,v in value.items():
            if len(k)>64:raise ValueError('answer key length')
            _bound(v,depth+1)
    elif type(value) is list:
        for v in value:_bound(v,depth+1)
    elif type(value) is str:
        if len(value)>32:raise ValueError('answer string length')
    elif type(value) in (int,float):
        if (type(value) is float and not math.isfinite(value)) or len(canonical_bytes(value))>32:
            raise ValueError('answer number representation')


def _bounded_answer(answer):
    _bound(answer)
    if type(answer) is not dict:raise ValueError('answer must be an object')
    surrogate={'execution_order':27,'phase':'post','payload_sha256':'0'*64,'status':'ANSWER','answer':answer}
    if len(canonical_bytes(surrogate))>3072:raise ValueError('canonical phase bound')


def parse_response(provider_response):
    result=parse_survey_response(provider_response)
    if result['status']!='ANSWER':return result
    try:_bounded_answer(result['answer'])
    except (ValueError,TypeError,RecursionError,UnicodeError,OverflowError):
        return {'status':'PARSE_ERROR','answer':None,'diagnostic':'ALIGNMENT_OBJECT_OR_BOUND'}
    return result


def _number(v):
    return type(v) in (int,float) and 0<=v<=100 and (type(v) is int or math.isfinite(v))


def valid_baseline(answer):
    return (type(answer) is dict and set(answer)==KEYS and
            all(_number(answer[k]) for k in NUMERIC) and answer['visits_change'] in VISITS and
            type(answer['visits_change']) is str)


@financial_context
def cost_envelope(protocol_bytes,terms):
    p=load_protocol(protocol_bytes);validate_terms(terms)
    if (terms['model']!=p['params']['model'] or terms['requested_route']!=p['params']['requested_route'] or
        terms['reported_provider']!=p['params']['reported_provider']):
        raise ExecutionBlocked('exact existing model/provider/route required')
    ceiling=micros(Decimal(8192)*decimal_price(terms['input_usd_per_token'])+
                   Decimal(256)*decimal_price(terms['output_usd_per_token'])+decimal_price(terms['request_fee_usd']))
    if not 0<ceiling<=1785 or 28*ceiling>50000:
        raise ExecutionBlocked('full frozen batch all-in quote exceeds reserved envelope')
    return {'maximum_POSTs':28,'maximum_GETs':84,'per_call_microusd':ceiling,
            'maximum_batch_microusd':28*ceiling,'batch_subceiling_microusd':50000,'actual_authority':False}


def _compile(p,terms,job,baseline):
    notice=next(x for x in p['notices'] if x['id']==job['notice_id'])
    request={'phase':job['phase'],'seed':job['pair_seed'],'profile':deepcopy(job['profile']),
             'survey':deepcopy(p['instrument']),'item_order':deepcopy(job['item_order']),
             'notice':{k:notice[k] for k in ('text','source_label','wrapper')}}
    if job['baseline_mode']=='SHOWN':request['pre_response']=deepcopy(baseline)
    messages=[{'role':'system','content':p['system_prompt']},
              {'role':'user','content':json.dumps(request,sort_keys=True,allow_nan=False)}]
    envelope=quote(messages,256,terms)
    if envelope['input_token_bound']>8192 or envelope['reserved_microusd']>1785:
        raise ExecutionBlocked('exact adaptive request exceeds frozen envelope')
    payload=_payload(messages,job['pair_seed'],256,terms)
    if len(canonical_bytes(payload))>262144:raise ExecutionBlocked('bounded payload required')
    return {'execution_order':job['execution_order'],'phase':job['phase'],'pair_seed':job['pair_seed'],
            'baseline_execution_order':job['baseline_execution_order'],'baseline_mode':job['baseline_mode'],
            'unit_sha256':canonical_hash(job),'request':request,'messages':messages,
            'payload':payload,'payload_sha256':canonical_hash(payload),'envelope':envelope,
            'actual_authority':False}


def _envelope(p,records,provenance):
    if provenance not in ('MOCK','EXPLORATORY_REAL_MODEL'):raise ExecutionBlocked('explicit response provenance required')
    result={'protocol_sha256':PROTOCOL_SHA256,'instrument_sha256':p['instrument_canonical_sha256'],
            'assignment_sha256':p['assignment_canonical_sha256'],'response_provenance':provenance,'records':records}
    if len(canonical_bytes(result))>131072:raise ExecutionBlocked('response envelope bound exceeded')
    return result


def next_action(protocol_bytes,terms,transcript_bytes):
    p=load_protocol(protocol_bytes);cost_envelope(protocol_bytes,terms)
    transcript=_load(transcript_bytes,131072)
    if type(transcript) is not list or len(transcript)>28:raise ExecutionBlocked('finite ordered transcript required')
    rows=[];position=0;pre={};stopped=False
    for job in p['jobs']:
        i=job['execution_order'];phase=job['phase'];before=pre.get(job['baseline_execution_order'])
        if stopped:
            rows.append(dict(execution_order=i,phase=phase,status='NOT_ATTEMPTED',answer=None));continue
        if job['baseline_mode']=='SHOWN' and not valid_baseline(before):
            rows.append(dict(execution_order=i,phase=phase,status='SKIPPED_INVALID_PRE',answer=None));continue
        compiled=_compile(p,terms,job,before)
        if position==len(transcript):
            return {'status':'REQUEST_READY_NOT_ADMITTED','request':compiled,'derived_records':rows,
                    'transcript_sha256':canonical_hash(transcript),'actual_authority':False}
        row=transcript[position]
        if (type(row) is not dict or set(row)!={'execution_order','phase','payload_sha256','status','answer'} or
            type(row['execution_order']) is not int or row['execution_order']!=i or row['phase']!=phase or
            type(row['status']) is not str or row['status'] not in DISPATCHED or
            row['payload_sha256']!=compiled['payload_sha256'] or
            (row['status']!='ANSWER' and row['answer'] is not None)):
            raise ExecutionBlocked('phase, payload, sequence or disposition differs')
        if row['status']=='ANSWER':
            try:_bounded_answer(row['answer'])
            except (ValueError,TypeError,RecursionError):raise ExecutionBlocked('answer contradicts bounded parser') from None
        rows.append({k:row[k] for k in ('execution_order','phase','status','answer')});position+=1
        if phase=='pre':pre[i]=row['answer'] if row['status']=='ANSWER' else None
        if row['status'] in ('FAILED_UNCERTAIN','CANCELLED'):stopped=True
    if position!=len(transcript):raise ExecutionBlocked('extra response after completion or stop')
    return {'status':'STOPPED' if stopped else 'COMPLETE','records':rows,
            'response_envelope':_envelope(p,rows,'MOCK'),'actual_authority':False}


def response_envelope(protocol_bytes,transcript_bytes,*,response_provenance='MOCK',stopped=False,terms=None):
    """Export all dispositions from an OWNER-AUTHENTICATED transcript.

    With terms, the request compiler also replays payload hashes. Without terms,
    this structural export checks fixed job identity, skips and safe hash syntax;
    it does not claim to authenticate payloads or financial checkpoints. The root
    owner supplies that verification before this convenience projection.
    """
    p=load_protocol(protocol_bytes)
    if type(stopped) is not bool:raise ExecutionBlocked('literal stop flag required')
    if terms is not None:
        state=next_action(protocol_bytes,terms,transcript_bytes)
        if state['status']=='REQUEST_READY_NOT_ADMITTED':
            if not stopped:raise ExecutionBlocked('incomplete nonstopped transcript')
            rows=state['derived_records'];seen={r['execution_order'] for r in rows}
            rows=rows+[dict(execution_order=j['execution_order'],phase=j['phase'],status='NOT_ATTEMPTED',answer=None)
                       for j in p['jobs'] if j['execution_order'] not in seen]
        else:rows=state['records']
        return _envelope(p,rows,response_provenance)
    transcript=_load(transcript_bytes,131072)
    if type(transcript) is not list or len(transcript)>28:raise ExecutionBlocked('finite transcript required')
    rows=[];pre={};position=0;halt=False
    for job in p['jobs']:
        i=job['execution_order'];phase=job['phase']
        if halt:
            rows.append(dict(execution_order=i,phase=phase,status='NOT_ATTEMPTED',answer=None));continue
        if job['baseline_mode']=='SHOWN' and not valid_baseline(pre.get(job['baseline_execution_order'])):
            rows.append(dict(execution_order=i,phase=phase,status='SKIPPED_INVALID_PRE',answer=None));continue
        if position==len(transcript):
            if not stopped:raise ExecutionBlocked('incomplete nonstopped transcript')
            halt=True;rows.append(dict(execution_order=i,phase=phase,status='NOT_ATTEMPTED',answer=None));continue
        row=transcript[position]
        if (type(row) is not dict or set(row)!={'execution_order','phase','payload_sha256','status','answer'} or
            type(row['execution_order']) is not int or row['execution_order']!=i or row['phase']!=phase or
            type(row['status']) is not str or row['status'] not in DISPATCHED or
            type(row['payload_sha256']) is not str or re.fullmatch(r'[a-f0-9]{64}',row['payload_sha256']) is None or
            (row['status']!='ANSWER' and row['answer'] is not None)):
            raise ExecutionBlocked('structural transcript binding differs')
        if row['status']=='ANSWER':_bounded_answer(row['answer'])
        rows.append({k:row[k] for k in ('execution_order','phase','status','answer')});position+=1
        if phase=='pre':pre[i]=row['answer'] if row['status']=='ANSWER' else None
        if row['status'] in ('FAILED_UNCERTAIN','CANCELLED'):halt=True
    if position!=len(transcript):raise ExecutionBlocked('records after terminal stop')
    return _envelope(p,rows,response_provenance)


def _item_scores(answer,party,notice_key):
    shape=type(answer) is dict and set(answer)==KEYS
    numeric={k:(answer[k] if shape and _number(answer[k]) else None) for k in NUMERIC}
    qualities={k:('INVALID_SHAPE' if not shape else 'VALID' if _number(answer[k]) else 'MISSING' if answer[k] is None else 'INVALID') for k in NUMERIC}
    visits=answer.get('visits_change') if shape else None
    comprehension='INVALID_SHAPE' if not shape else 'MISSING' if visits is None else 'CORRECT' if type(visits) is str and visits==notice_key else 'INCORRECT' if type(visits) is str and visits in VISITS else 'INVALID'
    gap=thermometer_score({k:numeric[k] for k in ('democratic_party','republican_party')},party)['primary']
    return {'support':numeric['library_support'],'party_gap':gap,'numeric_quality':qualities,
            'comprehension':comprehension,'baseline_valid':valid_baseline(answer)}


def _summary(values):
    complete=[r['value'] for r in values if r['value'] is not None]
    return {'planned_contexts':4,'complete_contexts':len(complete),
            'mean_points':sum(complete)/len(complete) if complete else None,
            'min_points':min(complete) if complete else None,'max_points':max(complete) if complete else None,
            'context_values':values,'interval_95':None,'uncertainty_status':'NOT_ESTIMATED_PURPOSIVE_TECHNICAL_CONTEXTS_ONE_ISSUE'}


def analyze(protocol_bytes,canonical_envelope_bytes):
    p=load_protocol(protocol_bytes);e=_load(canonical_envelope_bytes,131072)
    if (type(e) is not dict or set(e)!={'protocol_sha256','instrument_sha256','assignment_sha256','response_provenance','records'} or
        e['protocol_sha256']!=PROTOCOL_SHA256 or e['instrument_sha256']!=p['instrument_canonical_sha256'] or
        e['assignment_sha256']!=p['assignment_canonical_sha256'] or e['response_provenance'] not in ('MOCK','EXPLORATORY_REAL_MODEL') or
        type(e['records']) is not list or len(e['records'])!=28):
        raise ExecutionBlocked('exact frozen 28-record response envelope required')
    indexed={};scored={};counts=Counter();stopped=False;peritem=Counter()
    notice_keys={x['id']:x['visits_change_key'] for x in p['notices']}
    for row in e['records']:
        if (type(row) is not dict or set(row)!={'execution_order','phase','status','answer'} or
            type(row['execution_order']) is not int or not 0<=row['execution_order']<28 or row['execution_order'] in indexed):
            raise ExecutionBlocked('duplicate or malformed phase record')
        indexed[row['execution_order']]=row
    for job in p['jobs']:
        i=job['execution_order'];row=indexed[i];status=row['status'];before=indexed.get(job['baseline_execution_order'],{}).get('answer')
        if row['phase']!=job['phase'] or status not in DISPATCHED|{'SKIPPED_INVALID_PRE','NOT_ATTEMPTED'}:
            raise ExecutionBlocked('unexpected phase disposition')
        if status!='ANSWER' and row['answer'] is not None:raise ExecutionBlocked('non-answer contains answer')
        if status=='ANSWER':_bounded_answer(row['answer'])
        if stopped and status!='NOT_ATTEMPTED':raise ExecutionBlocked('phase after terminal stop')
        if status=='SKIPPED_INVALID_PRE' and (job['baseline_mode']!='SHOWN' or valid_baseline(before)):
            raise ExecutionBlocked('unsupported skip')
        if not stopped and job['baseline_mode']=='SHOWN' and not valid_baseline(before) and status not in ('SKIPPED_INVALID_PRE','NOT_ATTEMPTED'):
            raise ExecutionBlocked('shown baseline invalid but post attempted')
        if status in ('FAILED_UNCERTAIN','CANCELLED','NOT_ATTEMPTED'):stopped=True
        scores=_item_scores(row['answer'] if status=='ANSWER' else None,job['profile']['party'],notice_keys[job['notice_id']])
        scored[i]=scores;counts[status]+=1
        for item,q in scores['numeric_quality'].items():peritem[(item,q)]+=1
    bycell={(j['profile']['profile_id'],j['notice_id'],j['baseline_mode']):scored[j['execution_order']] for j in p['jobs'] if j['phase']=='post'}
    pre={j['profile']['profile_id']:scored[j['execution_order']] for j in p['jobs'] if j['phase']=='pre'}
    contexts={j['profile']['profile_id']:j for j in p['jobs'] if j['phase']=='pre'}
    contrasts={mode:[] for mode in ('OMITTED','SHOWN')};interactions=[];neutral=[];gaps=[]
    for profile in p['profiles']:
        pid=profile['profile_id'];baseinfo={'profile_id':pid,'party':profile['party'],'pair_seed':contexts[pid]['pair_seed']}
        ds={}
        for mode in ('OMITTED','SHOWN'):
            plus=bycell[pid,'N02',mode]['support'];minus=bycell[pid,'N03',mode]['support']
            value=plus-minus if plus is not None and minus is not None else None;ds[mode]=value
            contrasts[mode].append({**baseinfo,'value':value,'exclusion':None if value is not None else 'MISSING_OR_INVALID_TARGET_SUPPORT'})
            n=bycell[pid,'N01',mode]['support'];b=pre[pid]['support']
            neutral.append({**baseinfo,'mode':mode,'value':n-b if n is not None and b is not None else None})
            for notice in ('N01','N02','N03'):
                postgap=bycell[pid,notice,mode]['party_gap'];pregap=pre[pid]['party_gap']
                gaps.append({**baseinfo,'notice_id':notice,'mode':mode,'value':postgap-pregap if postgap is not None and pregap is not None else None})
        interactions.append({**baseinfo,'value':ds['SHOWN']-ds['OMITTED'] if all(v is not None for v in ds.values()) else None,
                             'exclusion':None if all(v is not None for v in ds.values()) else 'MISSING_OR_INVALID_TARGET_SUPPORT'})
    party_content={}
    for mode in ('OMITTED','SHOWN'):
        values=[]
        for profile in p['profiles']:
            pid=profile['profile_id'];plus=bycell[pid,'N02',mode]['party_gap'];minus=bycell[pid,'N03',mode]['party_gap']
            values.append({'profile_id':pid,'party':profile['party'],'value':plus-minus if plus is not None and minus is not None else None})
        party_content[mode]=_summary(values)
    comp={}
    for mode in ('OMITTED','SHOWN'):
        subset=[bycell[x['profile_id'],n,mode] for x in p['profiles'] for n in ('N01','N02','N03')]
        factual=[bycell[x['profile_id'],n,mode] for x in p['profiles'] for n in ('N02','N03')]
        valid=sum(x['comprehension'] in ('CORRECT','INCORRECT') for x in subset);correct=sum(x['comprehension']=='CORRECT' for x in subset)
        comp[mode]={'planned':12,'valid':valid,'correct':correct,'correct_per_planned':correct/12,
                    'correct_per_valid':correct/valid if valid else None,'factual_planned':8,
                    'factual_correct':sum(x['comprehension']=='CORRECT' for x in factual),
                    'quality_counts':dict(Counter(x['comprehension'] for x in subset)),
                    'by_notice':{notice:{'planned':4,
                        'valid':sum(bycell[x['profile_id'],notice,mode]['comprehension'] in ('CORRECT','INCORRECT') for x in p['profiles']),
                        'correct':sum(bycell[x['profile_id'],notice,mode]['comprehension']=='CORRECT' for x in p['profiles'])} for notice in ('N01','N02','N03')}}
    primary=_summary(contrasts['OMITTED']);shown=_summary(contrasts['SHOWN']);interaction=_summary(interactions)
    full=primary['complete_contexts']==4
    sensitive=full and sum(r['value']>0 for r in contrasts['OMITTED'])>=3 and primary['mean_points']>0 and comp['OMITTED']['factual_correct']>=6
    attenuated=interaction['complete_contexts']==4 and sensitive and sum(r['value']<0 for r in interactions)>=3 and interaction['mean_points']<0
    stable=full and all(r['value']==0 for r in contrasts['OMITTED']) and comp['OMITTED']['factual_correct']>=6
    return {'kind':'EXPLORATORY_ALIGNMENT_ANCHORING_DIAGNOSTIC','response_provenance':e['response_provenance'],
            'protocol_sha256':PROTOCOL_SHA256,'response_envelope_sha256':hashlib.sha256(canonical_envelope_bytes).hexdigest(),
            'status':'NOT_ESTIMABLE' if primary['complete_contexts']==0 else 'DESCRIPTIVE_PARTIAL' if stopped else 'DESCRIPTIVE_COMPLETE_BATCH',
            'primary_absent_content_contrast':primary,'shown_content_contrast':shown,'anchoring_interaction':interaction,
            'phase_counts':dict(counts),'item_quality_counts':[{'item':k,'quality':q,'count':n} for (k,q),n in sorted(peritem.items())],
            'scored_phases':[{'execution_order':i,**scored[i]} for i in range(28)],
            'neutral_reference_support_changes':neutral,'separate_partisan_gap_changes':gaps,
            'separate_partisan_content_contrasts':party_content,'comprehension':comp,
            'baseline_quality':{'planned':4,'valid_for_shown':sum(x['baseline_valid'] for x in pre.values()),
                'comprehension_counts':dict(Counter(x['comprehension'] for x in pre.values()))},
            'prespecified_patterns':{'content_sensitive':bool(sensitive),'anchoring_compatible':bool(attenuated),
                'support_stable_notice_understood':bool(stable),'task_following_concern':any(comp[m]['factual_correct']<6 for m in comp)},
            'limitations':p['scientific_scope']+' Correct comprehension never gates primary inclusion; no inferential interval or equivalence claim.',
            'actual_authority':False}
