"""Exploratory support-preserving models; no representative-population certificate."""
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
import argparse
import csv
import json
import math
import random
from ..common import RunStore, canonical_hash, sha256_file
from .population import fit_population, number, rake

FIELDS=('region','age_bin','education','party','race','income')
LEVELS=(('1','2','3','4'),('25-44','45-64','65+'),
        ('HS_OR_LESS','SOME_COLLEGE','BA_PLUS'),('D','R','I','UNKNOWN'),
        ('WHITE_NH','BLACK_NH','HISPANIC','OTHER_NH','UNKNOWN'),('LOW','MID','HIGH','UNKNOWN'))
GRID=tuple(product(*LEVELS))


def load_cohort(root,mapping,seed):
    """Exactly reproduce original recodes/split, retaining sparse training records internally."""
    train=[];test=[]
    source=Path(root)/'data/raw/anes_2024/extracted/anes_timeseries_2024_csv_20260519.csv'
    with source.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            sample=number(row[mapping['sample']]);w=number(row[mapping['weight']])
            if sample not in mapping['sample_values'] or w is None or w<=0:continue
            a,e,r=(number(row[mapping[k]]) for k in ('age','education','region'))
            if a is None or not 25<=a<=80 or e not in range(1,6) or r not in range(1,5):continue
            p=number(row[mapping['party']]);race=number(row[mapping['race']]);income=number(row[mapping['income']])
            key=(str(int(r)),'25-44' if a<45 else '45-64' if a<65 else '65+',
                 mapping['education_recode'][str(int(e))],
                 'D' if p==1 else 'R' if p==2 else 'I' if p in (0,3,5) else 'UNKNOWN',
                 'WHITE_NH' if race==1 else 'BLACK_NH' if race==2 else 'HISPANIC' if race==3 else 'OTHER_NH' if race in (4,5,6) else 'UNKNOWN',
                 'LOW' if income in (1,2) else 'MID' if income in (3,4) else 'HIGH' if income in (5,6) else 'UNKNOWN')
            cluster=(row[mapping['stratum']],row[mapping['psu']])
            if any(number(x) is None or number(x)<0 for x in cluster):continue
            record=(key,w,canonical_hash(cluster))
            (test if int(canonical_hash([seed,cluster])[:8],16)%5==0 else train).append(record)
    if not train or not test:raise ValueError('nonempty matched training and held-out partitions required')
    return train,test


def distributions(train,tau=5,half_count=.5):
    """Full-grid independent and hierarchical models, with survey weight scale normalized."""
    if not train or not math.isfinite(tau) or tau<=0 or not math.isfinite(half_count) or half_count<=0:
        raise ValueError('positive smoothing and nonempty training data required')
    if any(k not in GRID or not math.isfinite(w) or w<=0 for k,w,_ in train):
        raise ValueError('invalid training cell or survey weight')
    scale=len(train)/sum(w for _,w,_ in train)
    margins=[Counter() for _ in FIELDS]
    base=Counter();party_counts=[defaultdict(Counter) for _ in range(3)]
    ri_global=Counter();ri_counts=[defaultdict(Counter) for _ in range(4)]
    for key,w,_ in train:
        w*=scale
        for i,v in enumerate(key):margins[i][v]+=w
        base[key[:3]]+=w;ri_global[key[4:]]+=w
        for table,indices in zip(party_counts,((0,),(0,2),(0,1,2))):
            table[tuple(key[i] for i in indices)][key[3]]+=w
        for table,indices in zip(ri_counts,((3,),(0,3),(0,2,3),(0,1,2,3))):
            table[tuple(key[i] for i in indices)][key[4:]]+=w
    marg=[{v:(counts[v]+half_count)/(len(train)+half_count*len(levels)) for v in levels}
          for counts,levels in zip(margins,LEVELS)]
    def smooth(counts,category,prior):return (counts[category]+tau*prior)/(sum(counts.values())+tau)
    independent={};hierarchical={}
    for key in GRID:
        independent[key]=math.prod(marg[i][v] for i,v in enumerate(key))
        b=(base[key[:3]]+tau*math.prod(marg[i][key[i]] for i in range(3)))/(len(train)+tau)
        p=marg[3][key[3]]
        for table,indices in zip(party_counts,((0,),(0,2),(0,1,2))):
            p=smooth(table[tuple(key[i] for i in indices)],key[3],p)
        ri=smooth(ri_global,key[4:],marg[4][key[4]]*marg[5][key[5]])
        for table,indices in zip(ri_counts,((3,),(0,3),(0,2,3),(0,1,2,3))):
            ri=smooth(table[tuple(key[i] for i in indices)],key[4:],ri)
        hierarchical[key]=b*p*ri
    for model in (independent,hierarchical):
        if abs(sum(model.values())-1)>1e-10 or any(p<=0 for p in model.values()):
            raise ValueError('invalid fitted joint probability')
    return independent,hierarchical


def calibrate(model,targets):
    cells=[{**dict(zip(FIELDS,key)),'region_age':key[0]+':'+key[1],
            'region_education':key[0]+':'+key[2],'weight':p} for key,p in model.items() if p>0]
    fitted,diagnostics=rake(cells,targets)
    result={tuple(c[f] for f in FIELDS):c['weight'] for c in fitted}
    diagnostics['effective_grid_cells']=1/sum(p*p for p in result.values())
    diagnostics['maximum_cell_probability']=max(result.values())
    return result,diagnostics


def score(model,test,epsilon=1e-9):
    if not 0<epsilon<1 or not test:raise ValueError('valid common scoring floor and heldout data required')
    if any(k not in GRID or not math.isfinite(p) or p<0 for k,p in model.items()) or abs(sum(model.values())-1)>1e-8:
        raise ValueError('invalid probability model')
    if any(k not in GRID or not math.isfinite(w) or w<=0 for k,w,_ in test):raise ValueError('invalid evaluation record')
    weight=sum(w for _,w,_ in test)
    losses=[(-math.log((1-epsilon)*model.get(k,0)+epsilon/len(GRID)),w,c) for k,w,c in test]
    return {'weighted_joint_log_loss_nats':sum(loss*w for loss,w,_ in losses)/weight,
            'raw_weighted_joint_support_coverage':sum(w for k,w,_ in test if model.get(k,0)>0)/weight},losses


def paired_interval(left,right,seed,repeats):
    if len(left)!=len(right) or not left or repeats<1:raise ValueError('paired nonempty losses required')
    clusters=defaultdict(lambda:[0.,0.])
    for (a,w,c),(b,v,d) in zip(left,right):
        if (w,c)!=(v,d):raise ValueError('evaluation conditions differ')
        clusters[c][0]+=(a-b)*w;clusters[c][1]+=w
    values=list(clusters.values());rng=random.Random(seed);draws=[]
    for _ in range(repeats):
        draw=rng.choices(values,k=len(values));draws.append(sum(x for x,_ in draw)/sum(w for _,w in draw))
    draws.sort()
    return {'mean_hierarchical_minus_independent_nats':sum(x for x,_ in values)/sum(w for _,w in values),
            'percentile_95_cluster_bootstrap':[draws[int((repeats-1)*.025)],draws[int((repeats-1)*.975)]],
            'clusters':len(values),'repetitions':repeats,
            'interpretation':'Exploratory resampling on an already-inspected holdout; not design-based or confirmatory inference.'}


def run_comparison(root):
    root=Path(root).resolve();plan_path=root/'configs/e02_population_support_plan.json'
    plan=json.loads(plan_path.read_text());params=plan['parameters'];seed=params['seed']
    baseline=fit_population(root,seed)  # Includes registered source-byte validation.
    train,test=load_cohort(root,baseline['mapping'],seed)
    d=baseline['diagnostics']
    if len(train)!=d['contributing_survey_records']+d['exclusions'].get('sparse_joint_cell_below_5_records',0) or len(test)!=d['heldout_records']:
        raise ValueError('alternative cohort differs from original reference')
    suppressed={tuple(c[f] for f in FIELDS):c['weight'] for c in baseline['cells']}
    summary={'kind':'EXPLORATORY_POPULATION_SUPPORT_COMPARISON','grid_cells':len(GRID),
             'training_records':len(train),'heldout_records':len(test),'seed':seed,
             'models':{},'sensitivities':{},'source_hashes':baseline['source_hashes'],
             'plan_sha256':sha256_file(plan_path),'paid_calls':0,'api_spend_usd':0,
             'representative_population_gate':'BLOCKED: citizen/resident universe mismatch, unvalidated transport, already-inspected holdout; full support is imposed by smoothing, not proof of validity.'}
    suppressed_score,_=score(suppressed,test,params['common_log_score_floor_mass'])
    summary['models']['Q_suppressed']={**suppressed_score,'training_weight_retained_fraction':1-d['weighted_training_mass_excluded_sparse_fraction'],
                                      'calibration':{k:d[k] for k in ('iterations','max_absolute_margin_residual')}}
    taus=[params['primary_smoothing_prior_records']]+params['sensitivity_smoothing_prior_records']
    for tau in taus:
        independent,hierarchical=distributions(train,tau,params['global_marginal_half_count'])
        outputs={};losses={}
        for name,model in (('Q_independent',independent),('Q_hierarchical',hierarchical)):
            before,_=score(model,test,params['common_log_score_floor_mass'])
            calibrated,cal=calibrate(model,baseline['targets'])
            metrics,losses[name]=score(calibrated,test,params['common_log_score_floor_mass'])
            outputs[name]={**metrics,'before_calibration':before,'training_weight_retained_fraction':1.,'calibration':cal}
        paired=paired_interval(losses['Q_hierarchical'],losses['Q_independent'],seed,params['cluster_bootstrap_repetitions'])
        if tau==params['primary_smoothing_prior_records']:
            summary['models'].update(outputs);summary['primary_paired_comparison']=paired
        else:summary['sensitivities'][str(tau)]={'models':outputs,'paired_comparison':paired,'selection':'No automatic promotion or best-tau choice'}
    config={'stage':'population-support-comparison','seed':seed,'plan_sha256':sha256_file(plan_path),
            'implementation_sha256':sha256_file(Path(__file__)),'source_hashes':baseline['source_hashes'],
            'paid_api_enabled':False,'budget_usd':0}
    with RunStore(root,'E02',config,kind='EXPLORATORY') as run:
        run.write('population-support-comparison.json',summary)
        run.write('plan.json',plan)
        run.finish({'status':'EXPLORATORY_COMPARISON_RECORDED','paid_calls':0,'spent_usd':0,
                    'representative_population_gate':summary['representative_population_gate'],
                    'reproducibility_hash':canonical_hash(summary)})
    return run.path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args();print(run_comparison(args.root))


if __name__=='__main__':main()
