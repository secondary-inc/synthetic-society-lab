"""Matched independent direct and registry mergers; fixed mandatory evaluation."""
from array import array
from ..common import canonical_hash
from . import n2b_parts_v1_1 as parts
from .full_adult_types_v1_2 import AdultMatrix,i64
from .full_adult_analysis_v1_2 import mandatory_analysis
from .national_budget import Blocked


def _inputs(items,spec):
 if type(items) is not list or not items:raise Blocked('nonempty exact part list')
 seen=set();decoded=[]
 for p in items:
  if p['state'] in seen:raise Blocked('duplicate state part')
  seen.add(p['state']);decoded.append(parts.validate(p,spec))
 if len({p['spec_sha256'] for p in items})!=1 or len({p['realm'] for p in items})!=1:raise Blocked('mixed source spec/realm')
 return decoded


def registry_merge(items,spec):
 matrices=_inputs(items,spec);out=AdultMatrix()
 for part,m in zip(items,matrices):
  s=spec['universe']['state_fips'].index(part['state'])
  for name,values in m.data.items():
   stride=len(values)//51;out.data[name][s*stride:(s+1)*stride]=values[s*stride:(s+1)*stride]
  out.present[s*72:(s+1)*72]=m.present[s*72:(s+1)*72];out.support[s*72:(s+1)*72]=m.support[s*72:(s+1)*72]
 out.validate(spec);return out


def direct_merge(items,spec):
 matrices=_inputs(items,spec);out=AdultMatrix()
 # Independent scalar accumulation instead of registry block copying.
 for name,values in out.data.items():
  summed=[]
  for i in range(len(values)):
   total=0
   for m in matrices:total=i64(total+m.data[name][i])
   summed.append(total)
  out.data[name]=array('q',summed)
 for i in range(3672):
  present=[m.present[i] for m in matrices]
  if sum(present)>1:raise Blocked('crossed known source')
  out.present[i]=sum(present);out.support[i]=sum(m.support[i] for m in matrices)
 out.validate(spec);return out


def plan(*,optional_queries=0,logical_limit=12000000):
 if type(optional_queries) is not int or optional_queries!=0 or type(logical_limit) is not int or logical_limit<12000000:raise Blocked('both mandatory variants require12M, no optional query')
 return {'direct':6000000,'registry':6000000,'total_reserved':12000000,'optional_queries':0,'merge_validation_reserved_per_variant':2000000,'mandatory_limit_per_variant':4000000}



class ComparisonFailure(Blocked):
 def __init__(self,evidence):super().__init__('matched measurement/comparison failed; retain full charges');self.evidence=evidence


def matched(items,spec,*,logical_limit=12000000,guard=lambda:None,evaluation_order=('direct','registry'),record_failure=None):
 from . import n2b_metrics_v1_1 as metrics
 import time
 if type(items) is not list or len(items)!=2 or {p['state'] for p in items}!={'11','56'}:raise Blocked('matched budget is WY/DC pair only')
 if type(evaluation_order) not in (list,tuple) or len(evaluation_order)!=2 or set(evaluation_order)!={'direct','registry'}:raise Blocked('exact alternate evaluation pair')
 started=time.perf_counter();budget=plan(logical_limit=logical_limit);input_sha=canonical_hash(items);input_bytes=len(metrics.canonical(items));records=[];observed=[];attempted=[];results={};conditions=metrics.environment()
 try:
  for name in evaluation_order:
   guard();attempted.append(name)
   def work(name=name):
    observed.append(name)
    matrix=(direct_merge if name=='direct' else registry_merge)(items,spec)
    uncertainty,summaries=mandatory_analysis(matrix,spec,limit=budget['mandatory_limit_per_variant'])
    return matrix,uncertainty,summaries
   result,measurement=metrics.evaluate(name,work,input_bytes=input_bytes,input_sha256=input_sha,guard=guard)
   results[name]=result;records.append(measurement)
   if canonical_hash(items)!=input_sha:raise Blocked('input mutation during matched variant')
   guard()
  direct,d,ds=results['direct'];registry,r,rs=results['registry']
  if direct.blobs()!=registry.blobs() or d!=r or ds!=rs:raise Blocked('independent comparator data disagreement')
  reverse=registry_merge(list(reversed(items)),spec);guard()
  if reverse.blobs()!=registry.blobs():raise Blocked('source order nondeterminism')
 except BaseException as error:
  if isinstance(error,metrics.VariantFailure):records.append(error.evidence)
  evidence={'status':'FAILED_ENGINEERING_COMPARISON','error_type':type(error).__name__,'input_sha256':input_sha,'evaluation_order_requested':list(evaluation_order),'evaluation_order_observed':observed,'measurement_attempt_order':attempted,'variants':records,'conditions':conditions,'plan':budget,'elapsed_seconds':time.perf_counter()-started,'full_reservations_retained':True}
  if record_failure is not None:record_failure(evidence)
  raise ComparisonFailure(evidence) from None
 return registry,d,rs,{'plan':budget,'input_parts':[canonical_hash(p) for p in items],'primitive_hashes':{k:__import__('hashlib').sha256(v).hexdigest() for k,v in registry.blobs().items()},'direct_uncertainty_sha256':canonical_hash(d),'registry_uncertainty_sha256':canonical_hash(r),'direct_observed_ops':d['logical_units_observed'],'registry_observed_ops':r['logical_units_observed'],'same_canonical_payload':True,'national_status':'BLOCKED_MISSING_49_SOURCES','resource_evidence':{'status':'MEASURED_ENGINEERING_NOT_SPEED_OR_SCIENCE_CLAIM','input_sha256':input_sha,'input_logical_bytes':input_bytes,'evaluation_order_requested':list(evaluation_order),'evaluation_order_observed':observed,'measurement_attempt_order':attempted,'variants':records,'conditions':conditions,'matched_scope_seconds':time.perf_counter()-started,'timing_note':'Variant evaluation plus measurement scope, common hashing/comparison and source-order probe are separate; concurrent sampling costs overlap and are not subtracted.'}}


def require_full_national(matrix):
 if not all(matrix.present):raise Blocked('full51 requires every actual accepted source')
 return matrix
