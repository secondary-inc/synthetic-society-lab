"""F v1 standard-library closed-vocabulary data/semantic validation; MOCK only."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from ..common import canonical_hash,sha256_file
from .national_budget import Blocked

I64_MIN=-(2**63);I64_MAX=2**63-1
FLAGS=('FAGEP','FCITP','FSCHLP','FRELSHIPP')
FILES={'count.i64le':3672,'point.i64le':3672,'sum_squared.i64le':3672,'replicates.i64le':293760,'allocation_counts.i64le':14688,'allocation_weights.i64le':14688}


def actual_source(*args,**kwargs):raise Blocked('F actual GET/enrollment/parse/WY reuse/fit unavailable: fresh F review required')


def i64(v):
    if type(v) is not int or not I64_MIN<=v<=I64_MAX:raise Blocked('checked int64 overflow/type')
    return v


def finite(v):
    if type(v) not in (int,float) or not math.isfinite(v):raise Blocked('nonfinite/boolean numeric value')
    return v


def decimal(v,*,signed=True):
    pattern=r'(0|-[1-9][0-9]*|[1-9][0-9]*)' if signed else r'(0|[1-9][0-9]*)'
    if not isinstance(v,str) or re.fullmatch(pattern,v) is None:raise Blocked('noncanonical decimal')
    return int(v)


def hash_value(v):
    if type(v) is not str or re.fullmatch('[0-9a-f]{64}',v) is None:raise Blocked('hash domain')
    return v


def strict_json(text):
    def pairs(xs):
        result={}
        for key,value in xs:
            if key in result:raise Blocked('duplicate JSON key')
            result[key]=value
        return result
    try:return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(Blocked('nonfinite JSON')))
    except (ValueError,TypeError):raise Blocked('invalid JSON') from None


def keys(obj,required):
    if type(obj) is not dict or set(obj)!=set(required):raise Blocked('closed vocabulary/missing/extra field')


def schema_check(value,schema):
    """Only pinned keywords used by reviewed spec; NOT a full JSONSchema engine."""
    supported={'$schema','type','additionalProperties','required','properties','enum','const','minimum','maximum','pattern','minItems','maxItems','items','allOf','anyOf','if','then','else','not'}
    if set(schema)-supported:raise Blocked('unsupported schema keyword')
    if type(value) is float:finite(value)
    types={'null':lambda v:v is None,'integer':lambda v:type(v) is int,'number':lambda v:type(v) in (int,float) and math.isfinite(v),'string':lambda v:type(v) is str,'object':lambda v:type(v) is dict,'array':lambda v:type(v) is list,'boolean':lambda v:type(v) is bool}
    if 'type' in schema:
        wanted=schema['type'] if type(schema['type']) is list else [schema['type']]
        if any(t not in types for t in wanted) or not any(types[t](value) for t in wanted):raise Blocked('schema type')
    eq=lambda a,b:(type(a) is type(b) or type(a) in (int,float) and type(b) in (int,float)) and a==b
    if 'enum' in schema and not any(eq(value,v) for v in schema['enum']):raise Blocked('schema enum')
    if 'const' in schema and not eq(value,schema['const']):raise Blocked('schema const')
    if type(value) in (int,float):
        if 'minimum' in schema and value<schema['minimum'] or 'maximum' in schema and value>schema['maximum']:raise Blocked('schema numeric bound')
    if type(value) is str and 'pattern' in schema and re.search(schema['pattern'],value) is None:raise Blocked('schema pattern')
    if type(value) is dict:
        if not set(schema.get('required',[])).issubset(value):raise Blocked('schema required')
        if schema.get('additionalProperties') is False and set(value)-set(schema.get('properties',{})):raise Blocked('schema extra field')
        for k,s in schema.get('properties',{}).items():
            if k in value:schema_check(value[k],s)
    if type(value) is list:
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',float('inf')):raise Blocked('schema array size')
        if 'items' in schema:
            for v in value:schema_check(v,schema['items'])
    for s in schema.get('allOf',[]):schema_check(value,s)
    def matches(s):
        try:schema_check(value,s);return True
        except Blocked:return False
    if 'anyOf' in schema and not any(matches(s) for s in schema['anyOf']):raise Blocked('schema anyOf')
    if 'not' in schema and matches(schema['not']):raise Blocked('schema not')
    if 'if' in schema:
        branch='then' if matches(schema['if']) else 'else'
        if branch in schema:schema_check(value,schema[branch])


def load_engine(root):
    root=Path(root).resolve();c=strict_json((root/'configs/e02_full_adult_engine_v1_1.json').read_text())
    if c['actual_approvals']!={'source':None,'parse':None,'fit':None} or c['actual_authority']!=0:raise Blocked('F implementation has no actual authority')
    for name,h in c['required_files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or sha256_file(path)!=h:raise Blocked('F frozen input/code changed')
    return c,strict_json((root/c['specification']).read_text())


def axes(spec):
    u=spec['universe'];return [u['state_fips'],u['ages'],u['education'],u['citizenship'],u['residence']]


def row_axes(index,spec):
    shape=[51,4,3,2,3];coords=[]
    for size in reversed(shape):coords.append(index%size);index//=size
    return [values[i] for values,i in zip(axes(spec),reversed(coords))]


def parse_person(row,state,required):
    if None in row or any(type(value) is not str for value in row.values()) or any(k not in row for k in required):raise Blocked('row width/required field type')
    def integer(k,low,high,blank=False):
        text=row[k].strip()
        if blank and not text:return None
        if re.fullmatch('-?[0-9]+',text) is None:raise Blocked('required integer domain')
        v=int(text)
        if not low<=v<=high:raise Blocked('required field range')
        return v
    if row['RT']!='P' or row['STATE']!=state:raise Blocked('record/state mismatch')
    age=integer('AGEP',0,99);cit=integer('CIT',1,5);res=integer('RELSHIPP',20,38)
    edu=integer('SCHL',1,24,blank=age<3);weight=integer('PWGTP',1,9999)
    reps=[integer('PWGTP'+str(i),-9999,9999) for i in range(1,81)];flags=[integer(f,0,1) for f in FLAGS]
    if age<18:return None,weight,reps,flags
    a=0 if age<25 else 1 if age<45 else 2 if age<65 else 3;e=0 if edu<=17 else 1 if edu<=20 else 2
    citizenship=0 if cit<=4 else 1;residence=0 if res<=36 else 1 if res==37 else 2
    return ((a*3+e)*2+citizenship)*3+residence,weight,reps,flags


class AdultMatrix:
    def __init__(self):
        self.data={name:array('q',[0])*length for name,length in FILES.items()};self.present=bytearray(3672);self.support=bytearray(3672)
        if array('q').itemsize!=8:raise Blocked('platform int64 layout unavailable')
    def add(self,index,w,reps,flags):
        if type(index) is not int or not 0<=index<3672 or type(w) is not int or not 1<=w<=9999 or len(reps)!=80 or any(type(v) is not int or not -9999<=v<=9999 for v in reps) or len(flags)!=4 or any(type(v) is not int or v not in (0,1) for v in flags):raise Blocked('source contribution domain')
        self.data['count.i64le'][index]=i64(self.data['count.i64le'][index]+1)
        self.data['point.i64le'][index]=i64(self.data['point.i64le'][index]+w)
        self.data['sum_squared.i64le'][index]=i64(self.data['sum_squared.i64le'][index]+w*w)
        for r,value in enumerate(reps):
            k=index*80+r;self.data['replicates.i64le'][k]=i64(self.data['replicates.i64le'][k]+value)
        for j,flag in enumerate(flags):
            k=index*4+j;self.data['allocation_counts.i64le'][k]=i64(self.data['allocation_counts.i64le'][k]+flag);self.data['allocation_weights.i64le'][k]=i64(self.data['allocation_weights.i64le'][k]+flag*w)
    def mark_state(self,state_index):
        for i in range(state_index*72,(state_index+1)*72):
            self.present[i]=1;n=self.data['count.i64le'][i];self.support[i]=1 if n==0 else 2 if n<30 else 3
    def record(self,i,spec):
        labels=row_axes(i,spec);known=bool(self.present[i]);get=lambda name:self.data[name][i] if known else None
        return dict(zip(['state_fips','age_bin','education_bin','citizenship_bin','residence_bin'],labels))|{'source_status':'VALIDATED_SOURCE' if known else 'SOURCE_NOT_PROCESSED','unweighted_count':get('count.i64le'),'point_weight_sum':get('point.i64le'),'point_weight_squared_sum':get('sum_squared.i64le'),'replicate_sums':list(self.data['replicates.i64le'][i*80:(i+1)*80]) if known else [None]*80,'allocation_counts':{f:self.data['allocation_counts.i64le'][i*4+j] if known else None for j,f in enumerate(FLAGS)},'allocation_point_weight_sums':{f:self.data['allocation_weights.i64le'][i*4+j] if known else None for j,f in enumerate(FLAGS)},'support_status':['UNKNOWN_SOURCE','NO_RELEASED_CONTRIBUTORS_NOT_POPULATION_ZERO','LOW_SOURCE_SUPPORT_NOT_SHARING_PERMISSION','SOURCE_SUPPORT_RECORDED_NOT_POLITICAL_VALIDITY'][self.support[i]],'political_prior_status':'NOT_IDENTIFIED_BY_PUMS'}
    def validate(self,spec):
        if len(self.present)!=3672 or len(self.support)!=3672:raise Blocked('mask shape')
        for name,length in FILES.items():
            if len(self.data[name])!=length:raise Blocked('primitive shape')
        for s in range(51):
            if sum(self.data['count.i64le'][s*72:(s+1)*72])>spec['source_registry'][s]['published_person_rows']:raise Blocked('adult count exceeds published all-age source')
            if len(set(self.present[s*72:(s+1)*72]))!=1:raise Blocked('partially committed state mask')
        for i in range(3672):
            if self.present[i] not in (0,1) or self.support[i] not in (0,1,2,3):raise Blocked('mask vocabulary')
            record=self.record(i,spec);schema_check(record,spec['primitive_cell_json_schema'])
            n=self.data['count.i64le'][i];p=self.data['point.i64le'][i];sq=self.data['sum_squared.i64le'][i]
            quantities=[n,p,sq,*self.data['replicates.i64le'][i*80:(i+1)*80],*self.data['allocation_counts.i64le'][i*4:(i+1)*4],*self.data['allocation_weights.i64le'][i*4:(i+1)*4]]
            if not self.present[i] and (any(quantities) or self.support[i]!=0):raise Blocked('unknown padding is not measured zero')
            if self.present[i]:
                if n<0 or p<n or p>9999*n or sq<p or sq>9999*p or n*sq<p*p or any(v<0 or v>n for v in self.data['allocation_counts.i64le'][i*4:(i+1)*4]) or any(v<0 or v>p for v in self.data['allocation_weights.i64le'][i*4:(i+1)*4]):raise Blocked('cell algebra/allocations')
    def blobs(self):
        out={}
        for name,values in self.data.items():
            copied=array('q',values)
            if sys.byteorder!='little':copied.byteswap()
            out[name]=copied.tobytes()
        out['source_status.u8']=bytes(self.present);out['support_status.u8']=bytes(self.support);return out
    @classmethod
    def decode(cls,blobs,spec):
        if set(blobs)!=set(FILES)|{'source_status.u8','support_status.u8'}:raise Blocked('primitive vocabulary')
        result=cls()
        for name,length in FILES.items():
            if type(blobs[name]) is not bytes or len(blobs[name])!=length*8:raise Blocked('binary length')
            values=array('q');values.frombytes(blobs[name])
            if sys.byteorder!='little':values.byteswap()
            result.data[name]=values
        result.present=bytearray(blobs['source_status.u8']);result.support=bytearray(blobs['support_status.u8']);result.validate(spec);return result
    def dot(self,vector):
        if len(vector)!=3672 or any(type(v) is not int or v not in (-1,0,1) for v in vector):raise Blocked('compiled coefficient domain')
        point=0;reps=[0]*80
        for i,k in enumerate(vector):
            if not k:continue
            if not self.present[i]:raise Blocked('unknown source in selector')
            point=i64(point+k*self.data['point.i64le'][i])
            for j in range(80):reps[j]=i64(reps[j]+k*self.data['replicates.i64le'][i*80+j])
        return point,reps


def vector_hash(values):
    values=array('q',[i64(v) for v in values])
    if sys.byteorder!='little':values.byteswap()
    return hashlib.sha256(values.tobytes()).hexdigest()
