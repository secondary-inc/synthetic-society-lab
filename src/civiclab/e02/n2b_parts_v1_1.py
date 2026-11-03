"""New generic state parts and explicit read-only historical WY bridge."""
from array import array
from ..common import canonical_hash
from .full_adult_types_v1_2 import AdultMatrix,i64,FLAGS
from .national_budget import Blocked

SCHEMA='E02_N2B_STATE_PART_V1'
FIELDS={'schema','realm','state','spec_sha256','source_manifest_sha256','source_identity','person_sha256','rows','csv_bytes','expanded_bytes','accounting','domains','primitive_bundle','lineage'}

def empty():return {'count':0,'point':0,'replicates':[0]*80}
def count_add(t,w,reps):
 t['count']+=1;t['point']=i64(t['point']+w)
 for i,v in enumerate(reps):t['replicates'][i]=i64(t['replicates'][i]+v)

def validate(part,spec,*,expected_state=None,expected_source=None,expected_spec=None):
 if type(part) is not dict or set(part)!=FIELDS or part['schema']!=SCHEMA or part['realm'] not in ('TEST_ONLY','PRODUCTION'):raise Blocked('closed generic part')
 state=part['state']
 if state not in spec['universe']['state_fips'] or expected_state is not None and state!=expected_state or expected_source is not None and part['source_manifest_sha256']!=expected_source or expected_spec is not None and part['spec_sha256']!=expected_spec:raise Blocked('part state/spec/source mismatch')
 if type(part['person_sha256']) is not str or len(part['person_sha256'])!=64 or type(part['rows']) is not int or part['rows']<0 or type(part['csv_bytes']) is not int or part['csv_bytes']<0 or type(part['expanded_bytes']) is not int or part['expanded_bytes']<part['csv_bytes']:raise Blocked('part source observations')
 try:m=AdultMatrix.decode({k:bytes.fromhex(v) for k,v in part['primitive_bundle'].items()},spec)
 except (TypeError,ValueError):raise Blocked('part primitives') from None
 s=spec['universe']['state_fips'].index(state)
 if bytes(m.present)!=bytes([0]*(s*72)+[1]*72+[0]*((50-s)*72)):raise Blocked('singleton known/unknown masks')
 ac=part['accounting'];ds=part['domains']
 if type(ac) is not dict or set(ac)!={'all','adult','under18'} or type(ds) is not dict or set(ds)!=set(map(str,range(6))):raise Blocked('six-domain vocabulary')
 for group in [ac,*ds.values()]:
  if type(group) is not dict or set(group)!={'all','adult','under18'}:raise Blocked('accounting vocabulary')
  for value in group.values():
   if type(value) is not dict or set(value)!={'count','point','replicates'} or type(value['count']) is not int or value['count']<0 or type(value['point']) is not int or not value['count']<=value['point']<=9999*value['count'] or type(value['replicates']) is not list or len(value['replicates'])!=80:raise Blocked('accounting domain')
   i64(value['point'])
   for r in value['replicates']:i64(r)
  for field in ('count','point'):
   if group['all'][field]!=group['adult'][field]+group['under18'][field]:raise Blocked('all-age identity')
  if group['all']['replicates']!=[group['adult']['replicates'][r]+group['under18']['replicates'][r] for r in range(80)]:raise Blocked('all-age same-index replicas')
 for k in ('all','adult','under18'):
  for field in ('count','point'):
   if ac[k][field]!=sum(d[k][field] for d in ds.values()):raise Blocked('six-domain conservation')
  if ac[k]['replicates']!=[sum(d[k]['replicates'][r] for d in ds.values()) for r in range(80)]:raise Blocked('six-domain replica conservation')
 if part['rows']!=ac['all']['count'] or sum(m.data['count.i64le'])!=ac['adult']['count'] or sum(m.data['point.i64le'])!=ac['adult']['point']:raise Blocked('cell/adult conservation')
 if ac['adult']['replicates']!=[sum(m.data['replicates.i64le'][i*80+r] for i in range(s*72,(s+1)*72)) for r in range(80)]:raise Blocked('cell same-index replicas')
 for d,group in ds.items():
  cit,res=divmod(int(d),3);indices=[s*72+a*6+cit*3+res for a in range(12)]
  if group['adult']['count']!=sum(m.data['count.i64le'][i] for i in indices) or group['adult']['point']!=sum(m.data['point.i64le'][i] for i in indices) or group['adult']['replicates']!=[sum(m.data['replicates.i64le'][i*80+r] for i in indices) for r in range(80)]:raise Blocked('domain/cell projection')
 return m


def from_saved_wy(old,spec,ref,*,realm,spec_sha256):
 expected={'schema','origin','actual_person_rows_processed','state','source_manifest_sha256','source_identity','rows','csv_bytes','expanded_bytes','accounting','domains','primitive_bundle'}
 if type(old) is not dict or set(old)!=expected or old['state']!='56' or old['schema']!='E02_F_WY_'+old['origin']+'_STATE_PART_V1' or old['origin']!=('ACTUAL' if realm=='PRODUCTION' else 'AUTHORED') or old['actual_person_rows_processed']!=(old['rows'] if realm=='PRODUCTION' else 0):raise Blocked('historical WY part origin/schema')
 if canonical_hash(old)!=ref['part_canonical_sha256'] or old['source_manifest_sha256']!=ref['manifest_sha256'] or type(ref['accepted_audit_sha256']) is not str or len(ref['accepted_audit_sha256'])!=64:raise Blocked('accepted savedpart source/review')
 # Source member hash is pinned by the accepted original WY source spec, not learned.
 person=spec['WY_raw_candidate']['person_member_sha256']
 out={'schema':SCHEMA,'realm':realm,'state':'56','spec_sha256':spec_sha256,'source_manifest_sha256':old['source_manifest_sha256'],'source_identity':old['source_identity'],'person_sha256':person,'rows':old['rows'],'csv_bytes':old['csv_bytes'],'expanded_bytes':old['expanded_bytes'],'accounting':old['accounting'],'domains':old['domains'],'primitive_bundle':old['primitive_bundle'],'lineage':{'kind':'READ_ONLY_ACCEPTED_WY_BRIDGE','accepted_audit_sha256':ref['accepted_audit_sha256'],'original_part_canonical_sha256':canonical_hash(old)}}
 validate(out,spec,expected_state='56',expected_spec=spec_sha256)
 return out
