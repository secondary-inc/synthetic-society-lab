"""Offline engineering pilot. Its deterministic fixture outputs are not findings."""
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import json
import random
import statistics
from ..common import RunStore, canonical_hash
from ..jobs import JobQueue
from .instrument import change
from .population import sample_profiles

ARMS = ('C0', 'C1', 'C2', 'C3', 'C4')


def treatment(stimulus, arm):
    if arm not in ARMS:
        raise ValueError('unknown arm')
    return {'arm': arm, 'content_id': stimulus['id'],
            'body': '' if arm == 'C0' else stimulus['text'],
            'body_sha256': canonical_hash('' if arm == 'C0' else stimulus['text']),
            'source_label': stimulus['source_label'],
            'wrapper': 'none' if arm == 'C0' else 'synthetic social post' if arm in ('C2','C4') else 'news card',
            'qa': deepcopy(stimulus['qa']) if arm in ('C3','C4') else None,
            'qa_status': 'SCRIPTED_FIXTURE_NOT_LIVE_ASSISTANT' if arm in ('C3','C4') else 'NOT_RUN'}


def assignments(profiles, stimuli, seed, repeats=1):
    if not profiles or not stimuli or repeats < 1:
        raise ValueError('profiles, stimuli and repetitions required')
    if len({p['profile_id'] for p in profiles}) != len(profiles) or len({s['id'] for s in stimuli}) != len(stimuli):
        raise ValueError('duplicate profile or stimulus ID')
    rng = random.Random(seed); jobs = []
    for profile in profiles:
        for stimulus in stimuli:
            for repeat in range(repeats):
                # Same seed, item order and pre priors across arms for each matched unit.
                pair_seed = int(canonical_hash([seed,profile['profile_id'],stimulus['id'],repeat])[:8],16)
                item_order = ['democratic_party','republican_party']
                random.Random(pair_seed).shuffle(item_order)
                for arm in ARMS:
                    exposure = treatment(stimulus,arm)
                    jobs.append({'profile': deepcopy(profile), 'stimulus_id': stimulus['id'],
                                 'repeat': repeat, 'arm': arm, 'exposure': exposure,
                                 'pair_seed': pair_seed, 'item_order': item_order})
    rng.shuffle(jobs)
    return [{**job,'execution_order':i} for i,job in enumerate(jobs)]


class MockSurvey:
    name = 'deterministic-engineering-fixture-v1'

    def respond(self, request):
        """Known 2-point social shift deliberately injected to test score recovery."""
        rng = random.Random(request['seed'])
        party = request['profile']['party']
        center = 60 if party == 'D' else 40 if party == 'R' else 50
        baseline = center + rng.randrange(-5,6)
        shift = 1 if request['phase'] == 'post' and request['exposure']['wrapper'] == 'synthetic social post' else 0
        sign = 1 if party == 'D' else -1 if party == 'R' else 0
        return {'democratic_party':baseline+sign*shift,'republican_party':100-baseline-sign*shift}


def evaluate(responses, seed=20261103, bootstrap_repeats=500):
    grouped = defaultdict(dict); invalid = Counter(); arms = Counter()
    for row in responses:
        key = (row['profile_id'], row['stimulus_id'], row['repeat'])
        if row['arm'] in grouped[key]:
            raise ValueError('duplicate profile-stimulus-repeat-arm response')
        grouped[key][row['arm']] = row
        arms[row['arm']] += 1
        if row['change']['status'] != 'VALID':
            invalid[row['change']['status']] += 1
    differences = []; excluded = Counter()
    for key, group in grouped.items():
        if set(group) != set(ARMS):
            raise ValueError('incomplete crossed assignment; do not change evaluation denominator')
        one, two = group['C1'],group['C2']
        a,b = one['change']['primary'],two['change']['primary']
        if a is None or b is None:
            excluded['missing_invalid_or_nonpartisan_primary'] += 1; continue
        differences.append({'profile_id':key[0], 'stimulus_id':key[1], 'repeat':key[2], 'difference':b-a})
    interval = None; estimate = None
    if differences:
        estimate = statistics.mean(d['difference'] for d in differences)
        profile_ids = sorted({d['profile_id'] for d in differences}); stimulus_ids = sorted({d['stimulus_id'] for d in differences})
        rng = random.Random(seed); draws = []
        for _ in range(bootstrap_repeats):
            p_counts=Counter(rng.choices(profile_ids,k=len(profile_ids)))
            s_counts=Counter(rng.choices(stimulus_ids,k=len(stimulus_ids)))
            weighted=[(d['difference'],p_counts[d['profile_id']]*s_counts[d['stimulus_id']]) for d in differences]
            total=sum(w for _,w in weighted)
            if total:
                draws.append(sum(v*w for v,w in weighted)/total)
        draws.sort()
        if len(profile_ids)>=2 and len(stimulus_ids)>=2 and draws:
            interval=[draws[int((len(draws)-1)*.025)],draws[int((len(draws)-1)*.975)]]
    return {'kind':'MOCK_ENGINEERING_ONLY','primary_contrast':'(post-pre) C2 minus C1',
            'estimate_thermometer_points':estimate,'interval_95_crossed_bootstrap':interval,
            'uncertainty_label':'Resampling interval of deterministic mock outputs; no human or model-effect inference.',
            'paired_units':len(differences),'excluded_units':dict(excluded),'invalid_counts':dict(invalid),
            'arm_counts':dict(arms),'responses':len(responses),'paired_differences':differences,
            'scale_standardization':'divide thermometer points by 100',
            'primary_weighting':'equal matched profile-stimulus-repeat units; describes this engineering pool, not a national estimate'}


def run_population(root, seed=20261103):
    from .population import fit_population
    fit = fit_population(root,seed)
    config={'stage':'population-fit','seed':seed,'source_hashes':fit['source_hashes']}
    with RunStore(root,'E02',config,kind='EXPLORATORY') as run:
        run.write('population.json',fit)
        run.finish({'status':'PASS_EXPLORATORY_FIT','diagnostics':fit['diagnostics'],
                    'confirmatory_status':fit['confirmatory_status'],'paid_calls':0,'spent_usd':0})
    return run.path


def run_pilot(root, fit, *, seed=20261103, n=12, repeats=1, resume=None):
    root=Path(root)
    instrument=json.loads((root/'configs/e02_instrument.json').read_text())
    stimuli=json.loads((root/'configs/e02_demo_stimuli.json').read_text())
    if any(s['kind']!='DEMO' or s['rights']!='PROJECT_AUTHORED_FIXTURE' for s in stimuli):
        raise ValueError('offline mock pilot accepts project-authored DEMO fixtures only')
    profiles=sample_profiles(fit,n,seed)
    jobs=assignments(profiles,stimuli,seed,repeats)
    config={'stage':'mock-pilot','seed':seed,'profiles':n,'repeats':repeats,
            'population_hash':canonical_hash(fit),'instrument_hash':canonical_hash(instrument),
            'stimuli_hash':canonical_hash(stimuli),'assignment_hash':canonical_hash(jobs),
            'provider':MockSurvey.name,'paid_api_enabled':False,'budget_usd':0,
            'confirmatory_status':'BLOCKED: mock only; real stimuli, transport validity and preregistration absent'}
    run=RunStore.resume(root,resume,config) if resume else RunStore(root,'E02',config,kind='MOCK')
    queue=JobQueue(run.path/'jobs.sqlite')
    def write_once(name,value):
        if (run.path/name).exists():
            if json.loads((run.path/name).read_text()) != value:
                raise ValueError('checkpoint artifact mismatch')
        else:run.write(name,value)
    with run:
        write_once('instrument.json',instrument);write_once('profiles.json',profiles)
        write_once('stimuli.json',stimuli);write_once('assignments.json',jobs)
        for job in jobs:queue.add(job)
        if any(j['status'] in ('RUNNING','NEEDS_RECONCILIATION') for j in queue.snapshot()):
            raise ValueError('interrupted job needs explicit reconciliation; never silently replay')
        provider=MockSurvey()
        while claimed := queue.claim():
            identity, job=claimed
            # New independent request objects per unit. Only this unit's baseline is carried to post.
            pre_request={'phase':'pre','seed':job['pair_seed'],'profile':deepcopy(job['profile']),
                         'survey':deepcopy(instrument),'item_order':job['item_order'],'exposure':None}
            pre=provider.respond(deepcopy(pre_request))
            post_request={**deepcopy(pre_request),'phase':'post','pre_response':deepcopy(pre),'exposure':deepcopy(job['exposure'])}
            post=provider.respond(deepcopy(post_request))
            result={'profile_id':job['profile']['profile_id'],'stimulus_id':job['stimulus_id'],
                    'repeat':job['repeat'],'arm':job['arm'],'execution_order':job['execution_order'],
                    'pre':pre,'post':post,'change':change(pre,post,job['profile']['party']),
                    'pre_request':pre_request,'post_request':post_request,
                    'request_hashes':[canonical_hash(pre_request),canonical_hash(post_request)],
                    'provider':provider.name,'model':'MOCK','tokens':None,'cost_usd':0}
            queue.finish(identity,result)
            run.event('unit_completed',job_id=identity,arm=job['arm'],cost_usd=0)
        responses=sorted((j['result'] for j in queue.snapshot()),key=lambda x:x['execution_order'])
        summary=evaluate(responses,seed)
        write_once('responses.json',responses);write_once('analysis.json',summary)
        run.finish({'status':'PASS_MOCK_PILOT','kind':'MOCK','units':len(jobs),'mock_calls':2*len(jobs),
                    'paid_calls':0,'spent_usd':0,'analysis':{k:v for k,v in summary.items() if k!='paired_differences'},
                    'advanced_gates':{'real_news':'BLOCKED: no permitted corpus','demographics':'BLOCKED: no persona-free comparison',
                                      'assistant':'MOCK_SCRIPT_ONLY; live matched-compute comparison NOT_RUN',
                                      'swarms':'BLOCKED: independent equal-compute baseline NOT_RUN'},
                    'reproducibility_hash':canonical_hash(responses)})
    return run.path
