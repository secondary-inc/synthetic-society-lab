"""Fixed rounded-input perturbations into derived targets; no latent-vector claim."""
from copy import deepcopy
from decimal import Decimal as D,localcontext
from .citizen_targets import convert_rows
from .population import FIPS_REGION

TRANSFERS=(('AGE_007_TO_008','007','008'),('AGE_008_TO_007','008','007'),
           ('AGE_009_TO_010','009','010'),('AGE_010_TO_009','010','009'),
           ('EDU_040_TO_041','040','041'),('EDU_041_TO_040','041','040'),
           ('EDU_041_TO_042','041','042'),('EDU_042_TO_041','042','041'))


def scenario_targets(rows,target_config,central,scenario,amplitude='0.04'):
    """Validate original rounded source first; allow only frozen hypothetical precision."""
    if amplitude!='0.04':raise ValueError('frozen amplitude0.04required')
    original=convert_rows(rows,target_config)
    if original!=central:raise ValueError('central target differs from original source arithmetic')
    if scenario=='CENTRAL':return original,[]
    transfer={name:(donor,receiver) for name,donor,receiver in TRANSFERS}
    if scenario not in transfer:raise ValueError('unknown frozen scenario')
    donor,receiver=transfer[scenario];altered=deepcopy(rows);audit=[]
    # convert_rows has already validated one-decimal source observations. We keep
    # the original API untouched and use its normalization on a separately labeled
    # hypothetical layer, with no raw source or existing target artifacts changed.
    with localcontext() as ctx:
        ctx.prec=target_config['decimal_precision']
        for row in altered:
            if row['GEO_ID'][-2:] not in FIPS_REGION:continue
            for column in ('C02','C04'):
                dk=f'S0501_{column}_{donor}E';rk=f'S0501_{column}_{receiver}E'
                before_d,before_r=D(row[dk]),D(row[rk]);delta=min(D(amplitude),before_d,100-before_r)
                row[dk]=str(before_d-delta);row[rk]=str(before_r+delta)
                audit.append({'geoid':row['GEO_ID'],'column':column,'donor':donor,'receiver':receiver,
                              'original_donor':str(before_d),'original_receiver':str(before_r),
                              'perturbed_donor':row[dk],'perturbed_receiver':row[rk],'delta_pp':str(delta),
                              'zero_amplitude':delta==0,'clipped_amplitude':delta<D(amplitude),
                              'pair_sum_before':str(before_d+before_r),
                              'pair_sum_after':str(D(row[dk])+D(row[rk]))})
        result=_normalize_perturbed(altered,target_config)
        _check_result(original,result,audit)
    return result,audit


def _normalize_perturbed(rows,config):
    """Do not weaken source validation: use a new exact synthetic rounding layer.

    The existing converter's arithmetic is reused via a reviewed local equivalent
    of convert_column that accepts the explicitly perturbed percentage precision.
    No monkeypatching of original module functions or global Decimal validators.
    """
    from .citizen_targets import composition,source_cell
    regional={r:{'published25plus':D(0),'age':{g:D(0) for g in config['age_groups']},
                 'education':{g:D(0) for g in config['education_groups']}} for r in ('1','2','3','4')}
    states=[]
    for row in sorted(rows,key=lambda x:x['GEO_ID']):
        fips=row['GEO_ID'][-2:]
        if fips not in FIPS_REGION:continue
        columns={}
        for column in ('C02','C04'):
            total,total_cell=source_cell(row,column,'001','persons');adult,adult_cell=source_cell(row,column,'038','persons')
            source_cells={'001':total_cell,'038':adult_cell};sections={}
            for name,groups,denominator in (('age',config['age_groups'],total),('education',config['education_groups'],adult)):
                percentages={}
                for indices in groups.values():
                    for index in indices:
                        key=f'S0501_{column}_{index}E';p=D(row[key])
                        if not p.is_finite() or not 0<=p<=100:raise ValueError('perturbed percentage outside domain')
                        percentages[index]=p
                sections[name]=composition(percentages,groups,adult,denominator,config['rounding'])
            columns[column]={'published_total':total,'published25plus':adult,**sections}
        region=FIPS_REGION[fips];mass=sum(c['published25plus'] for c in columns.values())
        states.append({'geoid':row['GEO_ID'],'region':region,'columns':columns,'native_plus_naturalized25plus':mass})
        regional[region]['published25plus']+=mass
        for section in ('age','education'):
            for g in regional[region][section]:regional[region][section][g]+=sum(c[section]['normalized_approximate_counts'][g] for c in columns.values())
    national=sum(r['published25plus'] for r in regional.values());targets={'region_age':{},'region_education':{}}
    for region,r in regional.items():
        for section,dimension in (('age','region_age'),('education','region_education')):
            for g,n in r[section].items():targets[dimension][region+':'+g]=n/national
    return {'per_state':states,'regional':regional,'national_published25plus_sum':national,'targets':targets,
            'kind':'HYPOTHETICAL_ROUNDED_INPUT_PERTURBATION_DERIVED_TARGETS_NOT_LATENT_ACS_VECTOR'}


def _check_result(original,result,audit):
    tol=D('1e-10');old={s['geoid']:s for s in original['per_state']}
    for entry in audit:
        if D(entry['pair_sum_before'])!=D(entry['pair_sum_after']):raise ValueError('percentage mass changed')
        for side in ('donor','receiver'):
            p=D(entry['original_'+side]);q=D(entry['perturbed_'+side])
            if not max(D(0),p-D('.05'))<=q<=min(D(100),p+D('.05')):raise ValueError('outside declared rounding neighborhood')
    if result['national_published25plus_sum']!=original['national_published25plus_sum']:raise ValueError('national anchor changed')
    for state in result['per_state']:
        before=old[state['geoid']]
        for c,values in state['columns'].items():
            base=before['columns'][c]
            if values['published25plus']!=base['published25plus'] or values['published_total']!=base['published_total']:raise ValueError('state/column anchor changed')
            for section in ('age','education'):
                if values[section]['percentage_sum']!=base[section]['percentage_sum']:raise ValueError('section sum changed')
                if abs(sum(values[section]['normalized_approximate_counts'].values())-base['published25plus'])>tol:raise ValueError('normalized column mass changed')
                for g,n in values[section]['normalized_approximate_counts'].items():
                    bounds=base[section]['rounding_componentwise_bounds'][g]
                    if not bounds['count_lower_fixed_anchor']-tol<=n<=bounds['count_upper_fixed_anchor']+tol:raise ValueError('derived composition outside componentwise bounds')
    for region,r in result['regional'].items():
        if r['published25plus']!=original['regional'][region]['published25plus']:raise ValueError('region anchor changed')
        for section in ('age','education'):
            if abs(sum(r[section].values())-r['published25plus'])>tol:raise ValueError('region composition incoherent')
    for margins in result['targets'].values():
        if any(v<0 for v in margins.values()) or abs(sum(margins.values())-1)>tol:raise ValueError('invalid normalized target')
