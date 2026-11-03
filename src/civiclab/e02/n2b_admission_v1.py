"""N2b separate admission; actual defaults null, tests require isolated namespace."""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import time
from ..common import canonical_hash
from .f_actual_admission_v1_1 import detached
from .full_adult_types_v1_2 import strict_json
from .national_budget import Blocked

ROOT=Path(__file__).resolve().parents[3]
CONFIG='configs/e02_n2b_generic_state_import_v1.json'
TOKEN=object();TEST=object();TEST_ROOTS=set()

def sha(b):return hashlib.sha256(b).hexdigest()
def tick():return {'wall':time.time(),'mono':time.monotonic()}
def elapsed(a,b):
 if set(a)!={'wall','mono'} or set(b)!=set(a) or any(type(v) not in (int,float) or not math.isfinite(v) for d in (a,b) for v in d.values()):raise Blocked('clock domain')
 ds=[b[k]-a[k] for k in a]
 if min(ds)<0 or abs(ds[0]-ds[1])>2:raise Blocked('clock rollback/discontinuity')
 return max(ds)

def metadata(root,name,h=None):
 if type(name) is not str or Path(name).is_absolute() or '..' in Path(name).parts or Path(name).parts[0] not in ('src','tests','configs','reports','docs'):raise Blocked('public metadata path')
 p=root
 for part in Path(name).parts:
  p=p/part
  if p.is_symlink():raise Blocked('metadata symlink')
 with p.open('rb') as f:b=f.read(8*1024**2+1)
 if len(b)>8*1024**2 or h is not None and sha(b)!=h:raise Blocked('public metadata bound/hash')
 return b

def record(root,ref):
 if type(ref) is not dict or set(ref)!={'path','sha256'}:raise Blocked('closed reference')
 return strict_json(metadata(root,ref['path'],ref['sha256']))

@dataclass(frozen=True)
class Realm:
 root:Path
 kind:str
 token:object=None

def test_realm(root):
 root=Path(root).resolve()
 if root==ROOT or root.is_relative_to(ROOT) and not root.is_relative_to(ROOT/'data/processed/e02_F_local_fixture'):raise Blocked('isolated authored root only')
 root.mkdir(exist_ok=False);(root/'TEST_ONLY_N2B').write_text(str(root)+'\n');TEST_ROOTS.add(root)
 return Realm(root,'TEST_ONLY',TEST)

@dataclass(frozen=True)
class Context:
 realm:Realm
 config_json:str
 binding_json:str
 token:object
 @property
 def binding(self):return strict_json(self.binding_json)
 @property
 def config(self):return self.binding['config']
 @property
 def source(self):return self.config['source_manifest']
 @property
 def root(self):return self.realm.root
 @property
 def output(self):return self.root/self.config['output_directory']
 @property
 def registry(self):return self.root/self.config['registry_directory']


def verify_accepted_wy_reference(ref,phase,methods):
 # Original handoff source_part_sha256 was sha256_file, not canonical_hash.
 if ref['accepted_audit_sha256']!=methods['public_input_pins']['reports/INDEPENDENT_AUDIT_E02_F_WY_REAL_NATIVE_ENGINEERING_v1.json'] or ref['sha256']!=methods['initial_states']['WY']['saved_part_SHA256'][phase]:raise Blocked('accepted original WY byte evidence')
 return True


def _load(realm,config):
 c=detached(config)
 # No metadata/raw stat, import helper, credentials or network before authority.
 if type(c) is not dict or type(c.get('execution_authority')) is not int or c['execution_authority']!=1 or c.get('realm')!=realm.kind:raise Blocked('N2b actual/source authority absent')
 if type(realm) is not Realm or (realm.kind=='PRODUCTION' and (realm.root!=ROOT or realm.token is not None)) or (realm.kind=='TEST_ONLY' and (realm.token is not TEST or realm.root not in TEST_ROOTS or (realm.root/'TEST_ONLY_N2B').read_text()!=str(realm.root)+'\n')) or realm.kind not in ('PRODUCTION','TEST_ONLY'):raise Blocked('realm binding')
 base=strict_json(metadata(realm.root,CONFIG));excluded={'execution_authority','approvals','source_manifest','saved_parts'}
 if base['execution_authority']!=0 or any(v is not None for v in base['approvals'].values()) or {k:v for k,v in c.items() if k not in excluded}!={k:v for k,v in base.items() if k not in excluded}:raise Blocked('frozen N2b policy')
 for name,h in c['files'].items():metadata(realm.root,name,h)
 methods=record(realm.root,c['methods']);spec=record(realm.root,c['specification'])
 if c['stages']!=methods['proposed_stage_plan_NOT_AUTHORIZATION'] or c['caps']!=methods['new_artifact_subcaps_NOT_AUTHORIZATION'] or c['history']!=methods['cumulative_history_no_refund'] or c['native_limits']!=methods['native_limits_UNCHANGED'] or c['native_storage']!=methods['native_storage_UNCHANGED'] or c['required_fields']!=methods['required_fields_exact']:raise Blocked('methods/resource/schema drift')
 if c['active_state'] not in spec['universe']['state_fips'] or realm.kind=='PRODUCTION' and c['active_state']!='11':raise Blocked('registry state scope')
 if c['registry_directory']!='data/processed/e02_n2b_registry_v1' or c['output_directory']!='data/processed/e02_n2b_private_v1' or c['model_calls']!=0 or c['fit'] is not False or c['disclosure'] is not False:raise Blocked('fixed private output/scope')
 m=c['source_manifest']
 fields={'state','period','relative_path','archive_bytes','archive_sha256','identity','chain','person','companion','members','header_bytes','header_sha256','expected_rows','first_person_sha256','source_receipt_sha256','source_audit_sha256','provenance'}
 if type(m) is not dict or set(m)!=fields or m['state']!=c['active_state'] or m['period']!=spec['universe']['period'] or m['first_person_sha256'] is not None:raise Blocked('closed provisional source state/period')
 p=Path(m['relative_path'])
 if p.is_absolute() or '..' in p.parts or (realm.kind=='TEST_ONLY' and p.parts[:1]!=('inputs',)) or (realm.kind=='PRODUCTION' and str(p)!='data/raw/e02_n2a_sources_v1/11/csv_pdc.zip'):raise Blocked('exact source path')
 expected={x['name']:x for x in m['members']}
 if len(expected)!=2 or set(expected)!={m['person'],m['companion']} or m['person']!='psam_p'+m['state']+'.csv' or m['companion']!='ACS2020_2024_PUMS_README.pdf' or m['header_bytes']>65536 or len(c['required_fields'])!=91:raise Blocked('literal member/header contract')
 if expected[m['person']]['bytes']>67108864 or expected[m['companion']]['bytes']>2097152 or sum(x['bytes'] for x in expected.values())>69206016:raise Blocked('source expansion')
 published=next(s for s in spec['source_registry'] if s['state_fips']==c['active_state'])
 if realm.kind=='PRODUCTION' and (m['archive_bytes']!=4739881 or m['archive_sha256']!='bc9ea5024f1fe1755274171bd3374488f63ef454baf1e46c2c77a74b67e79ee9' or m['expected_rows']!=published['published_person_rows'] or m['header_sha256']!='4232ff33d8ef453a59ed659d662a98bbb510421d7c001aabffcd5ec292f20604'):raise Blocked('actual DC source pins')
 refs=c['approvals']
 if type(refs) is not dict or set(refs)!={'code_review','source_review','execution'}:raise Blocked('closed approvals')
 code=record(realm.root,refs['code_review']);source=record(realm.root,refs['source_review']);release=record(realm.root,refs['execution'])
 P=canonical_hash({k:v for k,v in c.items() if k not in excluded});S=canonical_hash(m);saved=c['saved_parts']
 D=canonical_hash({'policy_sha256':P,'source_sha256':S,'saved_parts':saved,'root':str(realm.root),'realm':realm.kind})
 if code.get('status')!='PASS_N2B_GENERIC_CODE_AUTHORED' or code.get('auditor_role')!='independent_auditor' or code.get('files')!=c['files'] or code.get('policy_sha256')!=P or code.get('realm')!=realm.kind:raise Blocked('independent exact code review')
 if source.get('status')!='PASS_N2B_PARTICULAR_SOURCE_SAVED_PART_METADATA' or source.get('auditor_role')!='independent_auditor' or source.get('source_sha256')!=S or source.get('saved_parts')!=saved or source.get('realm')!=realm.kind:raise Blocked('particular source/part review')
 scope={'root':str(realm.root),'output':c['output_directory'],'state':c['active_state'],'GETs':0,'person_sweeps':2,'WY_raw_sweeps':0,'model_calls':0,'fit':False,'disclosure':False}
 if release.get('status')!='RELEASE_N2B_TWO_SWEEPS_MATCHED_ASSEMBLY' or release.get('issuer_role')!='lead' or release.get('realm')!=realm.kind or release.get('design_sha256')!=D or release.get('scope')!=scope or release.get('code_review_sha256')!=refs['code_review']['sha256'] or release.get('source_review_sha256')!=refs['source_review']['sha256'] or release.get('stages')!=c['stages']:raise Blocked('exact finite execution release')
 now=tick()['wall']
 if any(type(release.get(k)) not in (int,float) or not math.isfinite(release[k]) for k in ('not_before','expires')) or not release['not_before']<=now<release['expires']:raise Blocked('finite release inactive')
 if realm.kind=='PRODUCTION' and (type(saved) is not dict or set(saved)!={'PRIMARY','REPLAY'}):raise Blocked('accepted WY saved parts absent')
 if type(saved) is not dict or set(saved)-{'PRIMARY','REPLAY'}:raise Blocked('savedpart phases')
 if realm.kind=='PRODUCTION' and m['source_audit_sha256']!=methods['public_input_pins']['reports/INDEPENDENT_AUDIT_E02_N2A_DC_ACTUAL_METADATA_v1.json']:raise Blocked('accepted DC metadata audit')
 for phase,ref in saved.items():
  if type(ref) is not dict or set(ref)!={'relative_path','sha256','part_canonical_sha256','manifest_sha256','accepted_audit_sha256'}:raise Blocked('closed savedpart reference')
  if realm.kind=='PRODUCTION':verify_accepted_wy_reference(ref,phase,methods)
  rp=Path(ref['relative_path'])
  if rp.is_absolute() or '..' in rp.parts or (realm.kind=='TEST_ONLY' and rp.parts[:1]!=('inputs',)) or (realm.kind=='PRODUCTION' and not str(rp).startswith('data/processed/e02_F_wy_private/')):raise Blocked('fixed savedpart domain')
 return {'config':c,'spec':spec,'policy_sha256':P,'design_sha256':D,'source_sha256':S,'release':release}


def _admit(r,c):
 try:b=_load(r,c)
 except (OSError,KeyError,TypeError,ValueError) as e:
  if isinstance(e,Blocked):raise
  raise Blocked('N2b metadata unavailable') from None
 return Context(r,json.dumps(detached(c),sort_keys=True),json.dumps(b,sort_keys=True),TOKEN)
def admit(config=None):return _admit(Realm(ROOT,'PRODUCTION'),config)
def admit_fixture(realm,config):
 if type(realm) is not Realm or realm.kind!='TEST_ONLY' or realm.token is not TEST:raise Blocked('isolated test realm')
 return _admit(realm,config)
def require(c):
 if type(c) is not Context or c.token is not TOKEN:raise Blocked('minted context required')
 try:b=_load(c.realm,strict_json(c.config_json))
 except (OSError,KeyError,TypeError,ValueError):raise Blocked('context no longer valid') from None
 if b!=c.binding:raise Blocked('context/policy changed')
 return c
