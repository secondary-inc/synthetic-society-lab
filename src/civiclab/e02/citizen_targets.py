"""Decimal S0501 citizen25+ point-target diagnostics; no population fitting."""
import argparse
import csv
from decimal import Decimal, InvalidOperation, localcontext
import io
import json
from pathlib import Path
import zipfile
from ..common import RunStore, canonical_hash, sha256_file
from .citizen_benchmark import inspect_archive
from .population import FIPS_REGION

D=Decimal
AGE_GROUPS={'25-44':['007'],'45-64':['008','009'],'65+':['010','011','012']}
EDUCATION_GROUPS={'HS_OR_LESS':['039','040'],'SOME_COLLEGE':['041'],'BA_PLUS':['042','043']}


def value(raw,*,count=False,percentage=False):
    try:result=D(raw)
    except (InvalidOperation,TypeError,ValueError):raise ValueError('missing, suppressed or invalid required estimate')
    if not result.is_finite() or result<0:raise ValueError('nonfinite or negative estimate')
    if count and result!=result.to_integral_value():raise ValueError('noninteger person estimate')
    if percentage and (result>100 or result.as_tuple().exponent < -1):
        raise ValueError('percentage outside one-decimal display domain')
    return result


def source_cell(row,column,index,unit):
    key=f'S0501_{column}_{index}'
    estimate=value(row.get(key+'E'),count=unit=='persons',percentage=unit=='percent')
    raw_moe=row.get(key+'M')
    # Preserve the original symbol, never coerce an unavailable MOE to zero.
    if raw_moe=='*****' and unit=='persons':
        moe={'raw':raw_moe,'status':'CONTROLLED_TOTAL_NO_APPROPRIATE_MOE','unit':'persons'}
    else:
        m=value(raw_moe,count=unit=='persons',percentage=unit=='percent')
        moe={'raw':raw_moe,'value':m,'status':'PUBLISHED_90_PERCENT_MOE',
             'unit':'persons' if unit=='persons' else 'percentage points'}
    return estimate,{'variable':key+'E','raw_estimate':row[key+'E'],'estimate':estimate,
                     'unit':unit,'moe':moe}


def composition(percentages,groups,anchor,raw_denominator,rounding):
    """Bounds are componentwise, holding the published25+ count fixed."""
    half=D(rounding['percentage_half_width_pp']);count_half=D(rounding['count_half_width_persons'])
    total=sum(percentages.values(),D(0))
    if total<=0:raise ValueError('zero percentage composition cannot be normalized')
    raw={g:raw_denominator*sum((percentages[i] for i in indices),D(0))/100 for g,indices in groups.items()}
    normalized={g:anchor*sum((percentages[i] for i in indices),D(0))/total for g,indices in groups.items()}
    bounds={}
    intervals={g:(sum((max(D(0),percentages[i]-half) for i in indices),D(0)),
                  sum((min(D(100),percentages[i]+half) for i in indices),D(0))) for g,indices in groups.items()}
    for g,(low,high) in intervals.items():
        lower_den=low+sum((u for other,(_,u) in intervals.items() if other!=g),D(0))
        upper_den=high+sum((l for other,(l,_) in intervals.items() if other!=g),D(0))
        if lower_den<=0 or upper_den<=0:raise ValueError('rounding interval has zero normalization denominator')
        lower,upper=low/lower_den,high/upper_den
        bounds[g]={'share_lower':lower,'share_upper':upper,
                   'count_lower_fixed_anchor':anchor*lower,'count_upper_fixed_anchor':anchor*upper,
                   'count_lower_with_integer_precision':max(D(0),anchor-count_half)*lower,
                   'count_upper_with_integer_precision':(anchor+count_half)*upper}
        if not lower<=normalized[g]/anchor<=upper:raise ValueError('point composition outside rounding bounds')
    return {'percentages':percentages,'percentage_sum':total,'raw_denominator':raw_denominator,
            'published25plus_anchor':anchor,'raw_approximate_counts':raw,
            'raw_approximate_total':sum(raw.values(),D(0)),
            'scale_to_published25plus':anchor/sum(raw.values(),D(0)),
            'normalized_approximate_counts':normalized,'rounding_componentwise_bounds':bounds}


def convert_column(row,column,config):
    if column not in ('C02','C04'):raise ValueError('only disjoint native and naturalized citizen columns permitted')
    sources={}
    def fetch(index,unit):
        estimate,record=source_cell(row,column,index,unit);sources[index]=record;return estimate
    total=fetch('001','persons');adult=fetch('038','persons')
    if not 0<adult<=total:raise ValueError('positive consistent all-age and25+ denominators required')
    ages={i:fetch(i,'percent') for i in ('007','008','009','010','011','012')}
    education={i:fetch(i,'percent') for i in ('039','040','041','042','043')}
    rounding=config['rounding'];tol=D(rounding['arithmetic_tolerance_proportion'])
    age=composition(ages,AGE_GROUPS,adult,total,rounding)
    edu=composition(education,EDUCATION_GROUPS,adult,adult,rounding)
    difference=age['raw_approximate_total']-adult
    bound=D(rounding['age_sum_tolerance_fraction_of_total'])*total+D(rounding['age_count_tolerance_persons'])
    if abs(difference)>bound+tol or age['percentage_sum']/100>D(1)+D(rounding['age_sum_tolerance_fraction_of_total'])+tol:
        raise ValueError('age-derived25+ total inconsistent with declared rounding bounds')
    if abs(edu['percentage_sum']-100)>D(rounding['education_sum_tolerance_pp'])+tol*100:
        raise ValueError('education percentages inconsistent with declared rounding bounds')
    for section in (age,edu):
        if abs(sum(section['normalized_approximate_counts'].values(),D(0))-adult)>tol:
            raise ValueError('normalized composition does not preserve published25+ mass')
    return {'column':column,'published_total':total,'published25plus':adult,'source_cells':sources,
            'age':age,'education':edu,
            'diagnostics':{'age_derived_minus_published25plus':difference,
                           'age_difference_fraction_of_all_age_total':difference/total,
                           'age_allowed_count_discrepancy':bound,
                           'education_sum_minus100_pp':edu['percentage_sum']-100}}


def convert_rows(rows,config):
    """Pure target arithmetic for fixed schema; never accepts a model or heldout outcomes."""
    if config.get('dataset')!='ACSST5Y2024.S0501':raise ValueError('matching2024five-year S0501 dataset required')
    if config.get('columns')!=['C02','C04'] or config.get('age_groups')!=AGE_GROUPS or config.get('education_groups')!=EDUCATION_GROUPS:
        raise ValueError('target mapping differs from reviewed citizenship/age/education definitions')
    if config.get('count_rows')!={'all_ages':'001','age25plus':'038'}:
        raise ValueError('swapped or altered count denominators')
    expected={'0400000US'+s for s in FIPS_REGION}|{'0400000US72'}
    if len(rows)!=52 or {r.get('GEO_ID') for r in rows}!=expected:
        raise ValueError('exactly50states,DC,PR required before declared PR exclusion')
    per_state=[];regional={r:{'published25plus':D(0),'age':{g:D(0) for g in AGE_GROUPS},
                              'education':{g:D(0) for g in EDUCATION_GROUPS}} for r in ('1','2','3','4')}
    with localcontext() as ctx:
        ctx.prec=config['decimal_precision']
        for row in sorted(rows,key=lambda x:x['GEO_ID']):
            fips=row['GEO_ID'][-2:]
            if fips=='72':continue
            columns={}
            for c in config['columns']:
                try:columns[c]=convert_column(row,c,config)
                except ValueError as error:raise ValueError(row['GEO_ID']+' '+c+': '+str(error)) from error
            region=FIPS_REGION[fips]
            state={'geoid':row['GEO_ID'],'name':row['NAME'],'region':region,'columns':columns}
            state['native_plus_naturalized25plus']=sum((c['published25plus'] for c in columns.values()),D(0))
            per_state.append(state);regional[region]['published25plus']+=state['native_plus_naturalized25plus']
            for section in ('age','education'):
                for g in regional[region][section]:
                    regional[region][section][g]+=sum((c[section]['normalized_approximate_counts'][g] for c in columns.values()),D(0))
        national=sum((r['published25plus'] for r in regional.values()),D(0));targets={'region_age':{},'region_education':{}}
        tol=D(config['rounding']['arithmetic_tolerance_proportion'])
        for region,data in regional.items():
            for section,dimension in (('age','region_age'),('education','region_education')):
                mass=sum(data[section].values(),D(0))
                if abs(mass-data['published25plus'])>tol:raise ValueError('regional25+ masses disagree')
                for g,n in data[section].items():targets[dimension][region+':'+g]=n/national
        for dimension,margins in targets.items():
            if abs(sum(margins.values(),D(0))-1)>tol:raise ValueError('normalized national target does not sum to1')
        return {'kind':'DERIVED_APPROXIMATE_CITIZEN25PLUS_TARGETS','dataset':config['dataset'],
                'arithmetic_representation':'Decimal values serialized as decimal strings, precision40; not float published counts',
                'included_state_dc_rows':len(per_state),
                'excluded_geographies':[{'geoid':'0400000US72','name':'Puerto Rico','reason':'Outside declared50states+DC four-region target; retained in source ZIP'}],
                'per_state':per_state,'regional':regional,'national_published25plus_sum':national,'targets':targets,
                'uncertainty':'Componentwise rounding bounds are not simultaneous feasible margin vectors or statistical confidence intervals. Original90percentMOEs retained; covariance-adjusted target uncertainty NOT_ESTIMATED.',
                'population_fit':'NOT_RUN_PENDING_INDEPENDENT_TARGET_ARITHMETIC_AUDIT',
                'scientific_population_gate':'BLOCKED: citizenship alignment does not validate transport, full adult/state scope, associations or synthetic behavior',
                'paid_calls':0,'api_spend_usd':0}


def decimal_strings(obj):
    if isinstance(obj,D):return str(obj)
    if isinstance(obj,dict):return {k:decimal_strings(v) for k,v in obj.items()}
    if isinstance(obj,list):return [decimal_strings(v) for v in obj]
    return obj


def run_targets(root):
    root=Path(root).resolve();config_path=root/'configs/e02_citizen_targets_v1.json'
    config=json.loads(config_path.read_text());inputs=dict(config['required_files'])
    if config['stage']!='TARGET_CONVERSION_ONLY_NO_FITTING':raise ValueError('target-only stage required')
    run_config={'stage':'citizen25plus-target-diagnostic','config_sha256':sha256_file(config_path),
                'implementation_sha256':sha256_file(Path(__file__)),'required_files':inputs,'paid_calls':0,'budget_usd':0}
    with RunStore(root,'E02',run_config,kind='EXPLORATORY') as run:
        run.write('target-config.json',config)
        for name,expected in inputs.items():
            source=(root/name).resolve()
            if not source.is_relative_to(root) or sha256_file(source)!=expected:
                raise ValueError('reviewed source/proposal/audit input changed: '+name)
        audit=json.loads((root/'reports/INDEPENDENT_AUDIT_E02_CITIZEN_FIT_METHODS.json').read_text())
        if audit['status']!='PASS_METHODS_FOR_TARGET_ONLY_IMPLEMENTATION' or audit['proposal_sha256']!=inputs['docs/E02_CITIZEN_FIT_PROPOSAL.md']:
            raise ValueError('matching target-only methods approval required')
        manifest=json.loads((root/'configs/e02_citizen_benchmark_acquisition.json').read_text())
        archive=(root/manifest['local_archive']).resolve()
        if not archive.is_relative_to(root):raise ValueError('source archive escapes repository')
        raw=archive.read_bytes();inspect_archive(raw,manifest)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            reader=csv.DictReader(io.StringIO(z.read(config['dataset']+'-Data.csv').decode('utf-8-sig')))
            next(reader);rows=list(reader)
        try:result=decimal_strings(convert_rows(rows,config))
        except ValueError as error:
            run.write('target-conversion-error.json',{'status':'BLOCKED','error':str(error),'config_sha256':sha256_file(config_path)})
            raise
        result['provenance']={**run_config,'archive_sha256':sha256_file(archive)}
        run.write('citizen-targets.json',result)
        run.finish({'status':'TARGET_DIAGNOSTIC_RECORDED_PENDING_INDEPENDENT_ARITHMETIC_AUDIT',
                    'reproducibility_hash':canonical_hash(result),'paid_calls':0,'spent_usd':0,
                    'population_fit':'NOT_RUN','national_published25plus_sum':result['national_published25plus_sum']})
    return run.path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args();print(run_targets(args.root))


if __name__=='__main__':main()
