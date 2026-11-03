"""Matched independent direct and registry mergers; fixed mandatory evaluation."""
from array import array
from ..common import canonical_hash
from . import n2b_parts_v1 as parts
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


def matched(items,spec,*,logical_limit=12000000,guard=lambda:None):
 if type(items) is not list or len(items)!=2 or {p['state'] for p in items}!={'11','56'}:raise Blocked('matched budget is WY/DC pair only')
 budget=plan(logical_limit=logical_limit);guard();direct=direct_merge(items,spec);guard();registry=registry_merge(items,spec);guard()
 if direct.blobs()!=registry.blobs():raise Blocked('direct/registry primitive disagreement')
 d,ds=mandatory_analysis(direct,spec,limit=budget['mandatory_limit_per_variant']);guard();r,rs=mandatory_analysis(registry,spec,limit=budget['mandatory_limit_per_variant']);guard()
 if d!=r or ds!=rs:raise Blocked('mandatory uncertainty comparator disagreement')
 # Reverse source order must preserve exact data; no extra raw source pass.
 reverse=registry_merge(list(reversed(items)),spec)
 if reverse.blobs()!=registry.blobs():raise Blocked('source order nondeterminism')
 return registry,d,rs,{'plan':budget,'input_parts':[canonical_hash(p) for p in items],'primitive_hashes':{k:__import__('hashlib').sha256(v).hexdigest() for k,v in registry.blobs().items()},'direct_uncertainty_sha256':canonical_hash(d),'registry_uncertainty_sha256':canonical_hash(r),'direct_observed_ops':d['logical_units_observed'],'registry_observed_ops':r['logical_units_observed'],'same_canonical_payload':True,'national_status':'BLOCKED_MISSING_49_SOURCES' if len(items)==2 else 'PARTIAL_NOT_NATIONAL'}


def require_full_national(matrix):
 if not all(matrix.present):raise Blocked('full51 requires every actual accepted source')
 return matrix
