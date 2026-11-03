"""F v1 finite exact moments and closed selectors/query semantics; no inference."""
from array import array
import hashlib
import math
from ..common import canonical_hash
from .national_budget import Blocked
from .full_adult_types_v1_2 import keys,finite,decimal,hash_value,schema_check,vector_hash,row_axes,i64


class Ops:
    def __init__(self,limit):self.used=0;self.limit=limit
    def add(self,n):
        if type(n) is not int or n<0 or self.used+n>self.limit:raise Blocked('logical operation bound')
        self.used+=n


def moments(point,reps,meter):
    if len(reps)!=80:raise Blocked('all80 replicas required')
    numerator=0
    for r in reps:
        meter.add(3);d=i64(r)-i64(point);numerator+=d*d
    variance=finite(numerator/20);se=finite(math.sqrt(variance));moe=finite(1.645*se);meter.add(5)
    return numerator,variance,se,moe


def uncertainty(qid,point,reps,meter,denominator=None,numerator_ref=None):
    rec={'quantity_id':qid,'quantity_kind':'COUNT_TOTAL' if denominator is None else 'PROPORTION','numerator_ref':numerator_ref or qid,'denominator_ref':None if denominator is None else denominator[0],
         'point_value':None,'exact_count_variance_numerator_decimal':None,'exact_count_variance_denominator':None,'variance_sdr':None,'standard_error':None,'moe90':None,'status':'BLOCKED_MISSING_SOURCE'}
    if point is None:return rec
    if denominator is None:
        num,var,se,moe=moments(point,reps,meter);value=float(point);rec.update(exact_count_variance_numerator_decimal=str(num),exact_count_variance_denominator=20)
    else:
        _,dp,dr=denominator
        if dp is None:return rec
        if dp<=0:rec['status']='BLOCKED_NONPOSITIVE_POINT_DENOMINATOR';return rec
        value=finite(point/dp);meter.add(1);rec['point_value']=value
        if len(dr)!=80 or any(d<=0 for d in dr):rec['status']='BLOCKED_NONPOSITIVE_REPLICATE_DENOMINATOR';return rec
        ratios=[finite(r/d) for r,d in zip(reps,dr)];meter.add(80)
        numerator=0.0
        for r in ratios:numerator+=(r-value)**2;meter.add(3)
        var=finite(numerator/20);se=finite(math.sqrt(var));moe=finite(1.645*se);meter.add(5)
    rec.update(point_value=value,variance_sdr=var,standard_error=se,moe90=moe,status='REVIEW_ZERO_ESTIMATE_OR_SE' if value==0 or se==0 else 'SDR_CONDITIONAL_SAMPLING_ERROR_ONLY')
    return rec


def mandatory_analysis(matrix,spec,*,limit=6000000):
    meter=Ops(limit);records=[];states=spec['universe']['state_fips'];summaries={}
    def reduce(indices):
        p=0;rs=[0]*80
        for i in indices:
            if not matrix.present[i]:return None,[None]*80
            p+=matrix.data['point.i64le'][i]
            for j in range(80):rs[j]+=matrix.data['replicates.i64le'][i*80+j]
            meter.add(162)
        return i64(p),[i64(r) for r in rs]
    def sum_summaries(items):
        if any(p is None for p,r in items):return None,[None]*80
        p=0;rs=[0]*80
        for a,b in items:
            p+=a
            for j in range(80):rs[j]+=b[j]
            meter.add(162)
        return p,rs
    for s,state in enumerate(states):
        f=reduce(range(s*72,(s+1)*72));cc=reduce([s*72+a*6 for a in range(12)])
        summaries['F_STATE:'+state]=f;summaries['C_STATE:'+state]=cc
        for label,(point,reps) in [('F_STATE:'+state,f),('C_STATE:'+state,cc)]:records.append(uncertainty(label,point,reps,meter))
        records.append(uncertainty('C_COVERAGE:'+state,*cc,meter,denominator=('F_STATE:'+state,*f),numerator_ref='C_STATE:'+state))
        for a in range(12):
            F=reduce(range(s*72+a*6,s*72+a*6+6));C=reduce([s*72+a*6])
            for label,value,den in [('F_VIEW',F,('F_STATE:'+state,*f)),('C_VIEW',C,('C_STATE:'+state,*cc))]:
                ident=label+':'+state+':'+str(a)
                if label=='F_VIEW':records.append(uncertainty(ident,*value,meter))
                records.append(uncertainty(ident+':share',*value,meter,denominator=den,numerator_ref=ident if label=='F_VIEW' else 'CELL:'+str(s*72+a*6)))
        for i in range(s*72,(s+1)*72):
            if matrix.present[i]:p=matrix.data['point.i64le'][i];r=list(matrix.data['replicates.i64le'][i*80:(i+1)*80])
            else:p=None;r=[None]*80
            records.append(uncertainty('CELL:'+str(i),p,r,meter));records.append(uncertainty('CELL:'+str(i)+':share',p,r,meter,denominator=('F_STATE:'+state,*f),numerator_ref='CELL:'+str(i)))
    for cohort in ('F','C'):
        value=sum_summaries([summaries[cohort+'_STATE:'+s] for s in states]);summaries[cohort+'_NATIONAL']=value;records.append(uncertainty(cohort+'_NATIONAL',*value,meter))
        from .population import FIPS_REGION
        for region in ('1','2','3','4'):
            part=sum_summaries([summaries[cohort+'_STATE:'+s] for s in states if FIPS_REGION[s]==region]);summaries[cohort+'_REGION:'+region]=part;records.append(uncertainty(cohort+'_REGION:'+region,*part,meter))
    records.append(uncertainty('C_COVERAGE:NATIONAL',*summaries['C_NATIONAL'],meter,denominator=('F_NATIONAL',*summaries['F_NATIONAL']),numerator_ref='C_NATIONAL'))
    return {'schema_version':'E02_U1_COUNT_RATIO_UNCERTAINTY_V1_1','records':records,'logical_units_observed':meter.used,'political_priors':'NOT_IDENTIFIED_BY_PUMS'},summaries


def _id(v):
    import re
    if type(v) is not str or re.fullmatch('[A-Za-z0-9_-]{1,32}',v) is None:raise Blocked('catalog identifier')
    return v


def catalog_bound(selectors,coefficients):
    if type(selectors) is not list or type(coefficients) is not list or len(selectors)>256 or len(coefficients)>256:raise Blocked('catalog limit')
    if any(type(c) is not dict or type(c.get('terms')) is not list or not 1<=len(c['terms'])<=8 for c in coefficients):raise Blocked('coefficient terms')
    return 5*3672*len(selectors)+2*3672*sum(len(c['terms']) for c in coefficients)


def compile_plan(spec,selectors,coefficients,queries):
    bound=catalog_bound(selectors,coefficients);meter=Ops(bound);masks={};maskhash=set()
    names=['state_fips','age_bin','education_bin','citizenship_bin','residence_bin'];allowed=list(zip(*[row_axes(i,spec) for i in range(3672)]));allowed=[set(x) for x in allowed]
    for entry in selectors:
        keys(entry,['selector_id','axis_filters','selector_definition_sha256','compiled_mask_sha256']);ident=_id(entry['selector_id']);keys(entry['axis_filters'],names)
        if ident in masks:raise Blocked('selector duplicate')
        for name,domain in zip(names,allowed):
            value=entry['axis_filters'][name]
            if type(value) is not list or not value or len(value)>len(domain) or any(type(v) is not str for v in value) or len(value)!=len(set(value)) or not set(value).issubset(domain):raise Blocked('selector closed domain')
        if entry['selector_definition_sha256']!=canonical_hash({'selector_id':ident,'axis_filters':entry['axis_filters']}):raise Blocked('selector definition hash')
        mask=[]
        for i in range(3672):
            flags=[v in entry['axis_filters'][name] for v,name in zip(row_axes(i,spec),names)];meter.add(5);mask.append(int(all(flags)))
        h=hashlib.sha256(bytes(mask)).hexdigest()
        if h!=entry['compiled_mask_sha256'] or h in maskhash:raise Blocked('selector mask hash/alias')
        masks[ident]=mask;maskhash.add(h)
    vectors={};hashes=set()
    for entry in coefficients:
        keys(entry,['coefficient_id','terms','coefficient_definition_sha256','compiled_vector_sha256']);ident=_id(entry['coefficient_id'])
        if ident in vectors:raise Blocked('coefficient duplicate')
        terms=entry['terms'];seen=[];v=[0]*3672
        for term in terms:
            keys(term,['selector_id','coefficient']);name=_id(term['selector_id']);k=term['coefficient']
            if name not in masks or name in seen or type(k) is not int or k not in (-1,1):raise Blocked('coefficient/selector domain')
            seen.append(name)
            for i,x in enumerate(masks[name]):v[i]+=k*x;meter.add(2)
        if seen!=sorted(seen) or not any(v) or any(x not in (-1,0,1) for x in v):raise Blocked('coefficient overlap/zero/order')
        if entry['coefficient_definition_sha256']!=canonical_hash({'coefficient_id':ident,'terms':terms}):raise Blocked('coefficient definition hash')
        h=hashlib.sha256(array('b',v).tobytes()).hexdigest()
        if h!=entry['compiled_vector_sha256'] or h in hashes:raise Blocked('compiled coefficient hash/alias')
        vectors[ident]={'vector':v,'sha256':h,'m':sum(x!=0 for x in v)};hashes.add(h)
    if type(queries) is not list or len(queries)>4224:raise Blocked('query list')
    plan=[];ids=set();definitions=set();counts={'COUNT_COVARIANCE':0,'COUNT_LINEAR_SIGNED':0}
    for q in queries:
        keys(q,['query_id','query_kind','x_coefficient_id','y_coefficient_id','query_definition_sha256']);ident=_id(q['query_id']);kind=q['query_kind']
        if type(kind) is not str:raise Blocked('query kind type')
        _id(q['x_coefficient_id'])
        if kind not in counts or ident in ids or q['x_coefficient_id'] not in vectors:raise Blocked('query kind/id/operand')
        x=vectors[q['x_coefficient_id']];y=None
        if kind=='COUNT_COVARIANCE':
            if q['y_coefficient_id'] not in vectors:raise Blocked('covariance operand')
            y=vectors[q['y_coefficient_id']]
            if x['sha256']>y['sha256']:raise Blocked('canonical covariance ordering')
        elif q['y_coefficient_id'] is not None:raise Blocked('scalar extra operand')
        definition={'query_kind':kind,'x_vector_sha256':x['sha256'],'y_vector_sha256':y['sha256'] if y else None,'units':'PUMS_WEIGHTED_PERSONS_SQUARED' if y else 'PUMS_WEIGHTED_PERSONS','target_schema_version':spec['specification_id']}
        digest=canonical_hash(definition)
        if q['query_definition_sha256']!=digest or digest in definitions:raise Blocked('query definition/hash/duplicate')
        counts[kind]+=1;ids.add(ident);definitions.add(digest)
        cost=162*(x['m']+y['m'])+321 if y else 162*x['m']+245
        plan.append({**q,'cost':cost,'x':x,'y':y})
    if counts['COUNT_COVARIANCE']>4096 or counts['COUNT_LINEAR_SIGNED']>128:raise Blocked('query count budget')
    total=2*(6000000+bound+sum(q['cost'] for q in plan))
    if total>64000000:raise Blocked('64million intentional plan refusal')
    if meter.used!=bound:raise Blocked('catalog operation reconciliation')
    return {'queries':sorted(plan,key=lambda q:q['query_id']),'catalog_ops':bound,'total_ops':total,'selectors':selectors,'coefficients':coefficients,'requests':queries,'catalog_observed_ops':meter.used}


def evaluate_query(matrix,query,binding,spec):
    if len(matrix.present)!=3672 or any(v!=1 for v in matrix.present):raise Blocked('query source bundle incomplete')
    x,xr=matrix.dot(query['x']['vector']);base={'query_id':query['query_id'],'execution_manifest_sha256':hash_value(binding),'query_definition_sha256':query['query_definition_sha256']}
    if query['y']:
        y,yr=matrix.dot(query['y']['vector']);num=sum((a-x)*(b-y) for a,b in zip(xr,yr))
        out={**base,'schema_version':'E02_U1_COVARIANCE_RESULTS_V1_1','query_kind':'COUNT_COVARIANCE','x_coefficient_sha256':query['x']['sha256'],'y_coefficient_sha256':query['y']['sha256'],'x_replicates_sha256':vector_hash(xr),'y_replicates_sha256':vector_hash(yr),'x_point_signed_decimal':str(x),'y_point_signed_decimal':str(y),'covariance_numerator_signed_decimal':str(num),'covariance_denominator':20,'covariance_sdr':finite(num/20),'units':'PUMS_WEIGHTED_PERSONS_SQUARED','status':'RECORDED_SDR_CONDITIONAL_ONLY'}
    else:
        meter=Ops(245);num,var,se,moe=moments(x,xr,meter)
        out={**base,'schema_version':'E02_U1_CONTRAST_RESULTS_V1_1','query_kind':'COUNT_LINEAR_SIGNED','coefficient_sha256':query['x']['sha256'],'replicates_sha256':vector_hash(xr),'point_signed_decimal':str(x),'variance_numerator_nonnegative_decimal':str(num),'variance_denominator':20,'variance_sdr':var,'standard_error':se,'moe90':moe,'units':'PUMS_WEIGHTED_PERSONS','variance_units':'PUMS_WEIGHTED_PERSONS_SQUARED','status':'REVIEW_ZERO_ESTIMATE_OR_SE' if x==0 or se==0 else 'RECORDED_SDR_CONDITIONAL_ONLY'}
    validate_result(out,matrix,query,binding,spec,recompute=False);return out


def validate_result(record,matrix,query,binding,spec,*,recompute=True):
    kind=query['query_kind'];schema=spec['query_contract']['covariance_result_JSON_schema' if kind=='COUNT_COVARIANCE' else 'contrast_result_JSON_schema'];schema_check(record,schema)
    if record['execution_manifest_sha256']!=binding or record['query_id']!=query['query_id'] or record['query_definition_sha256']!=query['query_definition_sha256'] or record['query_kind']!=kind:raise Blocked('query result binding')
    if kind=='COUNT_COVARIANCE':
        if record['x_coefficient_sha256']!=query['x']['sha256'] or record['y_coefficient_sha256']!=query['y']['sha256']:raise Blocked('coefficient hash binding')
        if record['status']=='RECORDED_SDR_CONDITIONAL_ONLY':
            if type(record['covariance_denominator']) is not int or record['covariance_denominator']!=20:raise Blocked('exact covariance denominator')
            num=decimal(record['covariance_numerator_signed_decimal']);finite(record['covariance_sdr'])
            if record['covariance_sdr']!=num/20:raise Blocked('signed covariance equation')
            i64(decimal(record['x_point_signed_decimal']));i64(decimal(record['y_point_signed_decimal']))
    else:
        if record['coefficient_sha256']!=query['x']['sha256']:raise Blocked('coefficient hash binding')
        if record['status'] in ('RECORDED_SDR_CONDITIONAL_ONLY','REVIEW_ZERO_ESTIMATE_OR_SE'):
            if type(record['variance_denominator']) is not int or record['variance_denominator']!=20:raise Blocked('exact variance denominator')
            num=decimal(record['variance_numerator_nonnegative_decimal'],signed=False);i64(decimal(record['point_signed_decimal']))
            if record['variance_sdr']!=num/20 or record['standard_error']!=math.sqrt(num/20) or record['moe90']!=1.645*math.sqrt(num/20):raise Blocked('contrast variance/SE/MOE equation')
    if recompute and record['status'] in ('RECORDED_SDR_CONDITIONAL_ONLY','REVIEW_ZERO_ESTIMATE_OR_SE'):
        expected=evaluate_query(matrix,query,binding,spec)
        if record!=expected:raise Blocked('result/source/replicate hash or exact equation')
    return True
