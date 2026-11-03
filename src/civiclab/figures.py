"""Standard static research figures from checksum-verified recorded diagnostics."""
from pathlib import Path
import json
from .dashboard import verified_run
from .common import atomic_json,sha256_file


def population_figures(root, run_id, output):
    root=Path(root).resolve();path=(root/'data/processed/runs'/run_id).resolve()
    if not path.is_relative_to(root/'data/processed/runs'):raise ValueError('run path escapes store')
    run=verified_run(path)
    if 'population' not in run:raise ValueError('a recorded population fit is required')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none','svg.hashsalt':'civiclab'})
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    diagnostic=run['population']['diagnostics'];excluded=diagnostic['exclusions']
    counts={'Retained training records':diagnostic['contributing_survey_records'],
            'Held-out records':diagnostic['heldout_records'],
            'Sparse joint-cell exclusions':excluded.get('sparse_joint_cell_below_5_records',0),
            'Age / education / region exclusions':excluded.get('age_education_or_region_missing_outside_universe',0),
            'Outside weighted fresh sample':excluded.get('outside_fresh_weighted_sample',0)}
    if 'invalid_design_cluster' in excluded:counts['Invalid design-cluster records']=excluded['invalid_design_cluster']
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    labels=list(counts);values=list(counts.values())
    bars=ax.barh(labels,values,color=['#315e51' if i<2 else '#9eaaa5' for i in range(len(labels))])
    ax.bar_label(bars,padding=4);ax.invert_yaxis();ax.set_xlim(0,max(values)*1.2)
    ax.set_xlabel('ANES survey records (count)');ax.set_ylabel('Disposition in exploratory population fitting')
    ax.set_title('ANES record retention and exclusions',loc='left',pad=14)
    ax.spines[['top','right']].set_visible(False)
    fig.text(.01,-.02,f'Source: ANES 2024 release May 19, 2026; run {run_id}. Counts describe calibration, not treatment effects.',fontsize=8,wrap=True)
    title='ANES record retention and exclusions'
    fig.savefig(output/'population-record-disposition.png',dpi=180,bbox_inches='tight',metadata={'Title':title,'Description':run_id})
    fig.savefig(output/'population-record-disposition.svg',bbox_inches='tight',metadata={'Title':title,'Description':run_id,'Date':None})
    plt.close(fig)
    receipt={'figure':'population-record-disposition','run_id':run_id,'source_checksums_sha256':run['checksums_sha256'],
             'counts':counts,'total_records':sum(values),'claim_scope':'Descriptive input/calibration record disposition, not evidence of representativeness or model effects.',
             'outputs':{name:sha256_file(output/name) for name in ('population-record-disposition.png','population-record-disposition.svg')}}
    atomic_json(output/'population-record-disposition.provenance.json',receipt)
    return receipt


def election_figures(root, run_id, output):
    """Describe matched historical errors, recomputing from saved predictions/outcomes."""
    import math
    import statistics
    root=Path(root).resolve();path=(root/'data/processed/runs'/run_id).resolve()
    if not path.is_relative_to(root/'data/processed/runs'):raise ValueError('run path escapes store')
    run=verified_run(path)
    advanced=run.get('evaluation',{});simple=run.get('simpler_evaluation',{})
    if advanced.get('dataset_kind')!='REAL_HISTORICAL_DIAGNOSTIC' or simple.get('dataset_kind')!='REAL_HISTORICAL_DIAGNOSTIC':
        raise ValueError('matched real historical diagnostic required')
    def indexed(evaluation):
        rows=evaluation.get('rows',[])
        if not rows or len({r['race_id'] for r in rows})!=len(rows):raise ValueError('empty or duplicated races')
        return {r['race_id']:r for r in rows}
    a=indexed(advanced);s=indexed(simple)
    if set(a)!=set(s):raise ValueError('unmatched historical cohorts')
    rows=[]
    for race in sorted(a):
        ar,sr=a[race],s[race]
        if ar['office']!=sr['office'] or ar['observed_margin_pp']!=sr['observed_margin_pp']:raise ValueError('unmatched outcome definitions')
        errors=[]
        for row in (ar,sr):
            values=[row[k] for k in ('predicted_margin_pp','observed_margin_pp','absolute_error_pp')]
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ValueError('invalid historical values')
            error=abs(row['predicted_margin_pp']-row['observed_margin_pp'])
            if not math.isclose(error,row['absolute_error_pp'],rel_tol=0,abs_tol=1e-10):raise ValueError('cached error disagrees with raw margins')
            errors.append(error)
        rows.append({'race_id':race,'s0_error_pp':errors[0],'s_zero_error_pp':errors[1],'difference_pp':errors[0]-errors[1]})
    mean_s0=statistics.mean(r['s0_error_pp'] for r in rows)
    mean_zero=statistics.mean(r['s_zero_error_pp'] for r in rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none','svg.hashsalt':'civiclab'})
    fig,(left,right)=plt.subplots(1,2,figsize=(11,9),layout='constrained',gridspec_kw={'width_ratios':[1,1.6]})
    bars=left.bar(['S_ZERO\nZero margin','S0\n2018 persistence'],[mean_zero,mean_s0],color=['#9eaaa5','#315e51'])
    left.bar_label(bars,fmt='%.2f',padding=4);left.set_ylim(0,max(mean_zero,mean_s0)*1.18)
    left.set_ylabel('Mean absolute margin error (percentage points)');left.set_title(f'Same {len(rows)} regular Senate races')
    differences=[r['difference_pp'] for r in rows]
    right.barh([r['race_id'].split('-')[1] for r in rows],differences,color=['#315e51' if v<0 else '#b8794b' for v in differences])
    right.axvline(0,color='#33413e',linewidth=.8);right.invert_yaxis()
    right.set_xlabel('S0 minus S_ZERO absolute error (pp)');right.set_ylabel('State (alphabetical)')
    right.set_title('Negative favors persistence on this cohort')
    for ax in (left,right):ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Post-hoc 2018 → 2024 Senate diagnostic',fontsize=15)
    fig.text(.01,-.02,'Conditional Democratic–Republican margin; not winner probabilities, an untouched holdout, or prospective evidence.\nSource: official FEC / House Clerk totals; run '+run_id+'. No model calls.',fontsize=8)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    base='e01-historical-errors'
    for suffix in ('png','svg'):
        metadata={'Title':'Post-hoc historical Senate margin errors','Description':run_id}
        if suffix=='svg':metadata['Date']=None
        fig.savefig(output/(base+'.'+suffix),dpi=180,bbox_inches='tight',metadata=metadata)
    plt.close(fig)
    receipt={'figure':base,'run_id':run_id,'source_checksums_sha256':run['checksums_sha256'],
             'race_count':len(rows),'s0_mae_pp':mean_s0,'s_zero_mae_pp':mean_zero,'rows':rows,
             'claim_scope':f'Descriptive post-hoc {len(rows)}-state historical comparison, not prospective or agent evidence; no sampling confidence interval.',
             'outputs':{base+'.'+s:sha256_file(output/(base+'.'+s)) for s in ('png','svg')}}
    atomic_json(output/(base+'.provenance.json'),receipt)
    return receipt
