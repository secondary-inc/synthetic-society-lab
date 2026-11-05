"""Pure, bounded analysis of the accepted finite E02 v1.1 pilot.

No file access, dispatch, authority, price estimation or scientific promotion.
Inputs are closed JSON byte envelopes, including all 32 phase dispositions.
"""
from collections import Counter
import hashlib
import json
import math
import random

from .instrument import change, score
from ..common import canonical_hash

PROTOCOL_SHA256 = 'a76e3f8924c568e58960a99822f6e5665df4c95e38bb6e00e8d3075f71a5847b'
PROJECTION_SHA256 = '1ad387de7ec320720849b1cacbcbbd4291b091cf0541cc43a8b39dc065172a5b'
ASSIGNMENT_SHA256 = '15fbe5b3b87ed800600e5044a31fe970f405165297f63807ea2b8ed04087bafd'
STATUSES = {'ANSWER', 'PARSE_ERROR', 'SKIPPED_INVALID_PRE', 'NOT_ATTEMPTED',
            'FAILED_UNCERTAIN', 'CANCELLED'}


def _object(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('duplicate JSON key')
        result[k] = v
    return result


def _load(raw, limit):
    if type(raw) is not bytes or len(raw) > limit:
        raise ValueError('bounded JSON bytes required')
    def reject(value):
        raise ValueError('nonfinite JSON constant')
    try:
        value = json.loads(raw, object_pairs_hook=_object, parse_constant=reject)
        def walk(x, depth=0):
            if depth > 20:
                raise ValueError('JSON depth exceeds bound')
            if type(x) is float and not math.isfinite(x):
                raise ValueError('nonfinite JSON number')
            if isinstance(x, dict):
                for k, v in x.items():
                    if len(k) > 256:
                        raise ValueError('key length exceeds bound')
                    walk(v, depth+1)
            elif isinstance(x, list):
                for v in x:
                    walk(v, depth+1)
            elif isinstance(x, str) and len(x) > 8192:
                raise ValueError('string length exceeds bound')
        walk(value)
        return value
    except (UnicodeError, RecursionError, OverflowError) as exc:
        raise ValueError('invalid bounded JSON') from exc


def _valid(answer, party):
    return (type(answer) is dict and
            set(answer) == {'democratic_party', 'republican_party'} and
            all(type(v) in (int, float) and 0 <= v <= 100 for v in answer.values()) and
            score(answer, party)['status'] == 'VALID')


def _mean(values):
    return sum(values)/len(values) if values else None


def analyze(protocol_bytes, response_bytes):
    """Return deterministic descriptive results; never certify live provenance.

    Response envelope fields: response_provenance (MOCK or
    EXPLORATORY_REAL_MODEL), protocol_sha256, projection_sha256,
    assignment_sha256, records. Each of the 32 records has execution_order,
    phase (pre/post), status and answer. ANSWER contains the unmodified parsed
    JSON response, even if invalid; other dispositions require answer=null.
    Caller must separately verify authentic bridge/financial records for live
    data. This pure evaluator checks structural and experimental binding only.
    """
    if type(protocol_bytes) is not bytes or hashlib.sha256(protocol_bytes).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('protocol byte hash differs from accepted v1.1')
    config = _load(protocol_bytes, 65536)
    if (canonical_hash(config['instrument']) != PROJECTION_SHA256 or
        canonical_hash(config['assignments']) != ASSIGNMENT_SHA256):
        raise ValueError('projection/assignment binding differs')
    envelope = _load(response_bytes, 131072)
    fields = {'response_provenance', 'protocol_sha256', 'projection_sha256',
              'assignment_sha256', 'records'}
    if type(envelope) is not dict or set(envelope) != fields:
        raise ValueError('closed response envelope required')
    if envelope['response_provenance'] not in ('MOCK', 'EXPLORATORY_REAL_MODEL'):
        raise ValueError('explicit response provenance required')
    for field, expected in [('protocol_sha256', PROTOCOL_SHA256),
                            ('projection_sha256', PROJECTION_SHA256),
                            ('assignment_sha256', ASSIGNMENT_SHA256)]:
        if envelope[field] != expected:
            raise ValueError('response binding differs: '+field)
    records = envelope['records']
    if type(records) is not list or len(records) != 32:
        raise ValueError('all 32 phase dispositions required')
    indexed = {}
    for row in records:
        if (type(row) is not dict or set(row) != {'execution_order','phase','status','answer'} or
            type(row['execution_order']) is not int or not 0 <= row['execution_order'] < 16 or
            row['phase'] not in ('pre','post') or type(row['status']) is not str or row['status'] not in STATUSES):
            raise ValueError('invalid closed phase record')
        key = row['execution_order'], row['phase']
        if key in indexed:
            raise ValueError('duplicate phase record')
        if row['status'] != 'ANSWER' and row['answer'] is not None:
            raise ValueError('non-answer disposition contains answer')
        if row['phase'] == 'pre' and row['status'] == 'SKIPPED_INVALID_PRE':
            raise ValueError('baseline cannot skip itself')
        indexed[key] = row
    counts = Counter(); strata = Counter(); units = {}; stopped = False
    for job in config['assignments']:
        i = job['execution_order']; party = job['profile']['party']
        pre, post = indexed[i,'pre'], indexed[i,'post']
        before_valid = pre['status'] == 'ANSWER' and _valid(pre['answer'], party)
        invalid_pre = pre['status'] == 'PARSE_ERROR' or (pre['status'] == 'ANSWER' and not before_valid)
        if invalid_pre and post['status'] != 'SKIPPED_INVALID_PRE':
            raise ValueError('invalid baseline requires explicit skipped post')
        if not invalid_pre and post['status'] == 'SKIPPED_INVALID_PRE':
            raise ValueError('skipped post without invalid baseline')
        if pre['status'] in ('NOT_ATTEMPTED','FAILED_UNCERTAIN','CANCELLED') and post['status'] != 'NOT_ATTEMPTED':
            raise ValueError('post without successful baseline phase')
        qualities = {}
        for phase, row in [('pre',pre),('post',post)]:
            status = row['status']
            attempted = status in ('ANSWER','PARSE_ERROR','FAILED_UNCERTAIN','CANCELLED')
            if stopped and attempted:
                raise ValueError('attempted phase after run stop')
            if status in ('NOT_ATTEMPTED','FAILED_UNCERTAIN','CANCELLED'):
                stopped = True
            valid = status == 'ANSWER' and _valid(row['answer'], party)
            if phase == 'pre' and valid and any(len(json.dumps(v,allow_nan=False)) > 32 for v in row['answer'].values()):
                raise ValueError('baseline encoding exceeds frozen envelope')
            quality = 'VALID' if valid else 'INVALID_ANSWER' if status == 'ANSWER' else status
            qualities[phase] = quality
            counts[quality] += 1
            strata[(job['arm'], phase, party, quality)] += 1
        numeric = before_valid and post['status'] == 'ANSWER' and _valid(post['answer'], party)
        delta = change(pre['answer'],post['answer'],party) if numeric else None
        key = job['profile']['profile_id'], job['stimulus_id']
        units.setdefault(key, {})[job['arm']] = {'change':delta, 'pre_status':pre['status'],
                                                'post_status':post['status'], 'pre_quality':qualities['pre'],
                                                'post_quality':qualities['post'], 'numeric':numeric}
    blocks = []
    parties = {p['profile_id']:p['party'] for p in config['profiles']}
    for (p,s), arms in sorted(units.items()):
        complete = all(arms[a]['numeric'] for a in ('C1','C2'))
        blocks.append({'profile_id':p,'stimulus_id':s,'party':parties[p],
                       'status':'COMPLETE' if complete else 'EXCLUDED_INCOMPLETE_FOUR_ANSWERS',
                       'difference_points':arms['C2']['change']['primary']-arms['C1']['change']['primary'] if complete else None,
                       'absolute_gap_difference_points':arms['C2']['change']['absolute_gap']-arms['C1']['change']['absolute_gap'] if complete else None,
                       'arms':arms})
    complete = [b for b in blocks if b['status']=='COMPLETE']
    profiles = sorted({b['profile_id'] for b in complete}); stimuli = sorted({b['stimulus_id'] for b in complete})
    draws = []; zero = 0; interval = None
    if complete:
        rng = random.Random(20261103)
        for _ in range(2000):
            pc = Counter(rng.choices(profiles,k=len(profiles)))
            sc = Counter(rng.choices(stimuli,k=len(stimuli)))
            weighted = [(b['difference_points'],pc[b['profile_id']]*sc[b['stimulus_id']]) for b in complete]
            total = sum(w for _,w in weighted)
            if total:
                draws.append(sum(v*w for v,w in weighted)/total)
            else:
                zero += 1
        draws.sort()
        if len(profiles)>=2 and len(stimuli)>=2:
            interval = [draws[math.floor((len(draws)-1)*q)] for q in (.025,.975)] if draws else None
    return {'component':'E02_EXPLORATORY_PILOT_ANALYSIS_V1','response_provenance':envelope['response_provenance'],
            'input_stimulus_provenance':'DEMO / PROJECT_AUTHORED_FIXTURE',
            'binding':{k:envelope[k] for k in ('protocol_sha256','projection_sha256','assignment_sha256')},
            'response_envelope_sha256':hashlib.sha256(response_bytes).hexdigest(),
            'provenance_verification':'DECLARED_ONLY; authentic live bridge/accounting verification required separately',
            'status':'DESCRIPTIVE_COMPLETE_CASES' if complete else 'NOT_ESTIMABLE',
            'planned_blocks':8,'complete_blocks':len(complete),'excluded_blocks':8-len(complete),
            'estimate_thermometer_points':_mean([b['difference_points'] for b in complete]),
            'interval_95_descriptive_crossed_bootstrap':interval,
            'bootstrap':{'seed':20261103,'requested_draws':2000,'nonempty_draws':len(draws),'zero_weight_draws':zero,'executed':bool(complete)},
            'phase_counts':dict(sorted(counts.items())),
            'phase_arm_party_counts':[{'arm':a,'phase':ph,'party':p,'quality':q,'count':n} for (a,ph,p,q),n in sorted(strata.items())],
            'run_stopped':stopped,'blocks':blocks,
            'sensitivity':{'party_means':{p:_mean([b['difference_points'] for b in complete if b['party']==p]) for p in ('D','R')},
                           'leave_one_profile_out':{p:_mean([b['difference_points'] for b in complete if b['profile_id']!=p]) for p in sorted(parties)},
                           'leave_one_stimulus_out':{s:_mean([b['difference_points'] for b in complete if b['stimulus_id']!=s]) for s in sorted({b['stimulus_id'] for b in blocks})},
                           'absolute_gap_mean_difference_points':_mean([b['absolute_gap_difference_points'] for b in complete])},
            'limitations':'Tiny purposive technical replicates; unstable descriptive resampling; complete-case attrition bias; no human, nationwide, representative, confirmatory or model-universe inference.',
            'authority_created':False}
