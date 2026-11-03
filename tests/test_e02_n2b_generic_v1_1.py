"""All fixtures newly authored in isolated roots; no actual source/private access."""
from copy import deepcopy
import csv
import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from civiclab.common import canonical_hash
from civiclab.e02 import n2b_admission_v1_1 as a
from civiclab.e02 import n2b_source_v1_1 as source
from civiclab.e02 import n2b_parts_v1_1 as parts
from civiclab.e02 import n2b_assembly_v1_1 as assembly
from civiclab.e02 import n2b_runner_v1_1 as runner
from civiclab.e02.n2b_control_v1_1 import Control
from civiclab.e02 import n2b_metrics_v1_1 as metrics
from civiclab.e02 import n2b_storage_v1_1 as prior_storage
from civiclab.e02.full_adult_types_v1_2 import AdultMatrix,parse_person
from civiclab.e02.full_adult_analysis_v1_2 import moments,Ops,uncertainty
from civiclab.e02.f_wy_bootstrap_v1_1 import _open_no_follow,_identity
from civiclab.e02.national_budget import Blocked

REAL=Path(__file__).resolve().parents[1]
METHODS='configs/e02_n2b_generic_state_import_methods_v1.json'
AUDIT='reports/INDEPENDENT_AUDIT_E02_N2B_GENERIC_STATE_IMPORT_METHODS_v1.json'
SPEC='configs/e02_full_adult_benchmark_u1_v1_1.json'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 p=Path(p);p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def code_files():
 names=['src/civiclab/e02/n2b_'+n+'_v1_1.py' for n in ('admission','control','parts','source','assembly','runner')]+['tests/test_e02_n2b_generic_v1_1.py',AUDIT,'src/civiclab/common.py','src/civiclab/__init__.py','src/civiclab/e02/__init__.py','src/civiclab/e02/national_budget.py','src/civiclab/e02/full_adult_types_v1_2.py','src/civiclab/e02/full_adult_analysis_v1_2.py','src/civiclab/e02/f_actual_admission_v1_1.py','src/civiclab/e02/f_wy_bootstrap_v1.py','src/civiclab/e02/f_wy_bootstrap_v1_1.py','src/civiclab/e02/n2a_collector_v1.py']
 names+=['src/civiclab/e02/n2b_storage_v1_1.py','src/civiclab/e02/n2b_metrics_v1_1.py','configs/e02_n2a_dc_collector_v1.json','reports/INDEPENDENT_AUDIT_E02_N2B_GENERIC_V1_RESOURCE_COMPARATOR_FINDINGS.json']
 return {p:sha(REAL/p) for p in names}
def static_config(realm='PRODUCTION',state='11'):
 m=json.loads((REAL/METHODS).read_text())
 prior={'data/processed/e02_F_wy_private/conditional-actual-v1-20261103-01':'WY_mixed','data/processed/e02_F_wy_private_bootstrap/conditional-actual-v1-20261103-01':'core','data/processed/e02_n2a_registry_v1':'core','data/processed/e02_n2a_core_v1':'core','data/raw/e02_n2a_sources_v1':'raw','data/raw/e02_pums_wy':'raw','data/raw/e02_pums_metadata':'raw'} if realm=='PRODUCTION' else {'prior/data':'data','prior/core':'core','prior/raw':'raw'}
 return {'schema':'E02_N2B_DISABLED_IMPLEMENTATION_V1_1','realm':realm,'active_state':state,'execution_authority':0,'approvals':{'code_review':None,'source_review':None,'execution':None},'source_manifest':None,'saved_parts':None,'files':code_files(),'methods':{'path':METHODS,'sha256':sha(REAL/METHODS)},'specification':{'path':SPEC,'sha256':sha(REAL/SPEC)},'stages':m['proposed_stage_plan_NOT_AUTHORIZATION'],'caps':m['new_artifact_subcaps_NOT_AUTHORIZATION'],'history':m['cumulative_history_no_refund'],'native_limits':m['native_limits_UNCHANGED'],'native_storage':m['native_storage_UNCHANGED'],'required_fields':m['required_fields_exact'],'prior_directories':prior,'output_directory':'data/processed/e02_n2b_private_v1','registry_directory':'data/processed/e02_n2b_registry_v1','model_calls':0,'fit':False,'disclosure':False,'prior_storage_policy':prior_storage.policy(m['native_storage_UNCHANGED'],json.loads((REAL/'configs/e02_n2a_dc_collector_v1.json').read_text())['unit_limits']),'n2a_reference':{'path':'configs/e02_n2a_dc_collector_v1.json','sha256':sha(REAL/'configs/e02_n2a_dc_collector_v1.json')},'evaluation_schedule':{'PRIMARY':['direct','registry'],'REPLAY':['registry','direct']}}


def rows(state='11'):
 fields=json.loads((REAL/METHODS).read_text())['required_fields_exact'];out=[]
 for d in range(6):
  cit,res=divmod(d,3);r={f:'0' for f in fields};r.update(RT='P',STATE=state,AGEP='18',CIT='1' if cit==0 else '5',RELSHIPP=str(20 if res==0 else 36+res),SCHL='1',PWGTP=str(d+1))
  for i in range(1,81):r['PWGTP'+str(i)]=str((-1 if i%2 else 3) if d==0 else d+1)
  out.append(r)
 for d in range(6):
  r=deepcopy(out[d]);r.update(AGEP='2',SCHL='',PWGTP='1')
  for i in range(1,81):r['PWGTP'+str(i)]='1'
  out.append(r)
 return out

def body(state='11',records=None,extra=False):
 fields=json.loads((REAL/METHODS).read_text())['required_fields_exact']+['UNUSED_'+str(i) for i in range(194)]
 s=io.StringIO();w=csv.DictWriter(s,fields,lineterminator='\n');w.writeheader()
 for r in rows(state) if records is None else records:w.writerow({f:r.get(f,'') for f in fields})
 person=s.getvalue().encode();comp=b'%PDF-TEST_ONLY_INERT_NOT_REAL_PUBLISHER';memory=io.BytesIO()
 with zipfile.ZipFile(memory,'w',compression=zipfile.ZIP_STORED) as z:
  z.writestr('psam_p'+state+'.csv',person);z.writestr('ACS2020_2024_PUMS_README.pdf',comp)
  if extra:z.writestr('extra',b'X')
 return memory.getvalue(),person


def legacy_wy(spec):
 matrix=AdultMatrix();s=50;accounting={k:parts.empty() for k in ('all','adult','under18')};domains={str(d):{k:parts.empty() for k in ('all','adult','under18')} for d in range(6)}
 for d in range(6):
  w=d+1;reps=[(-1 if i%2 else 3) if d==0 else w for i in range(1,81)];matrix.add(s*72+d,w,reps,[0]*4)
  for t in (accounting['all'],accounting['adult'],domains[str(d)]['all'],domains[str(d)]['adult']):parts.count_add(t,w,reps)
  for t in (accounting['all'],accounting['under18'],domains[str(d)]['all'],domains[str(d)]['under18']):parts.count_add(t,1,[1]*80)
 matrix.mark_state(s);person=body('56')[1]
 return {'schema':'E02_F_WY_AUTHORED_STATE_PART_V1','origin':'AUTHORED','actual_person_rows_processed':0,'state':'56','source_manifest_sha256':'1'*64,'source_identity':{'TEST_ONLY':True},'rows':12,'csv_bytes':len(person),'expanded_bytes':len(person)+4000,'accounting':accounting,'domains':domains,'primitive_bundle':{k:v.hex() for k,v in matrix.blobs().items()}}

class Env:
 def __init__(self,root,state='11',records=None,source_blob=None):
  self.realm=a.test_realm(root);self.root=self.realm.root;self.base=static_config('TEST_ONLY',state)
  for p in set(self.base['files'])|{METHODS,SPEC}:
   q=self.root/p;q.parent.mkdir(exist_ok=True,parents=True);q.write_bytes((REAL/p).read_bytes())
  save(self.root/a.CONFIG,self.base);self.live=deepcopy(self.base);self.live['execution_authority']=1
  blob,person=body(state,records);blob=blob if source_blob is None else source_blob
  p=self.root/'inputs/source.zip';p.parent.mkdir();p.write_bytes(blob)
  f,dfd,chain=_open_no_follow(p)
  try:
   with f:identity=_identity(os.fstat(f.fileno()))
  finally:os.close(dfd)
  with zipfile.ZipFile(p) as z:
   members=[{'name':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'crc32':i.CRC,'compression':i.compress_type,**({'sha256':hashlib.sha256(z.read(i.filename)).hexdigest()} if i.filename.endswith('.pdf') else {})} for i in z.infolist()]
  m={'state':state,'period':'2020-2024 five-year','relative_path':'inputs/source.zip','archive_bytes':len(blob),'archive_sha256':hashlib.sha256(blob).hexdigest(),'identity':identity,'chain':chain,'person':'psam_p'+state+'.csv','companion':'ACS2020_2024_PUMS_README.pdf','members':members,'header_bytes':len(person.splitlines(keepends=True)[0]),'header_sha256':hashlib.sha256(person.splitlines(keepends=True)[0]).hexdigest(),'expected_rows':len(rows(state) if records is None else records),'first_person_sha256':None,'source_receipt_sha256':'2'*64,'source_audit_sha256':'3'*64,'provenance':'TEST_ONLY_AUTHORED_NO_REAL_PERMISSION'}
  self.live['source_manifest']=m;spec=json.loads((REAL/SPEC).read_text());old=legacy_wy(spec);saved={}
  for phase in ('PRIMARY','REPLAY'):
   name='inputs/WY_'+phase+'.json';save(self.root/name,old);saved[phase]={'relative_path':name,'sha256':sha(self.root/name),'part_canonical_sha256':canonical_hash(old),'manifest_sha256':old['source_manifest_sha256'],'accepted_audit_sha256':'4'*64}
  self.live['saved_parts']=saved;self.reseal()
 def record(self,name,v):
  name='reports/TEST_ONLY_N2B_'+name+'.json';save(self.root/name,v);return {'path':name,'sha256':sha(self.root/name)}
 def reseal(self):
  c=self.live;policy={k:v for k,v in c.items() if k not in ('execution_authority','approvals','source_manifest','saved_parts')};P=canonical_hash(policy);S=canonical_hash(c['source_manifest']);D=canonical_hash({'policy_sha256':P,'source_sha256':S,'saved_parts':c['saved_parts'],'root':str(self.root),'realm':'TEST_ONLY'})
  code=self.record('code',{'status':'PASS_N2B_GENERIC_CODE_AUTHORED','auditor_role':'independent_auditor','files':c['files'],'policy_sha256':P,'realm':'TEST_ONLY'})
  src=self.record('source',{'status':'PASS_N2B_PARTICULAR_SOURCE_SAVED_PART_METADATA','auditor_role':'independent_auditor','source_sha256':S,'saved_parts':c['saved_parts'],'realm':'TEST_ONLY'})
  release=self.record('release',{'status':'RELEASE_N2B_TWO_SWEEPS_MATCHED_ASSEMBLY','issuer_role':'lead','realm':'TEST_ONLY','design_sha256':D,'scope':{'root':str(self.root),'output':c['output_directory'],'state':c['active_state'],'GETs':0,'person_sweeps':2,'WY_raw_sweeps':0,'model_calls':0,'fit':False,'disclosure':False},'code_review_sha256':code['sha256'],'source_review_sha256':src['sha256'],'stages':c['stages'],'not_before':1793736000.,'expires':1793740000.})
  c['approvals']={'code_review':code,'source_review':src,'execution':release}
 def admit(self):return a.admit_fixture(self.realm,self.live)

class N2bTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.clock={'wall':1793737000.,'mono':1000.};self.patch=patch.object(a,'tick',side_effect=lambda:dict(self.clock));self.patch.start();self.env=Env(Path(self.tmp.name)/'realm');self.c=self.env.admit()
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def control(self):return Control(self.c,create=True)
 def reserve(self,key='DC_PRIMARY'):
  ctl=self.control()
  # Tests use genuine preceding metadata-only stage, not counter patching.
  ctl.run_stage('BIND',lambda:{'metadata':source.inspect_source(self.c,ctl,'BIND')})
  with ctl.lock():ctl.advance('RESERVE',key)
  return ctl
 def parse(self):
  ctl=self.reserve();return source.parse_state(self.c,ctl,'DC_PRIMARY')

 def test_N2B01_same_generic_code_DC_WY(self):
  dc=self.parse();self.assertEqual(dc['state'],'11');self.assertEqual(dc['accounting']['adult']['point'],21)
  with tempfile.TemporaryDirectory() as t:
   e=Env(Path(t)/'wy','56');c=e.admit();ctl=Control(c,create=True);ctl.run_stage('BIND',lambda:source.inspect_source(c,ctl,'BIND'))
   with ctl.lock():ctl.advance('RESERVE','DC_PRIMARY')
   wy=source.parse_state(c,ctl,'DC_PRIMARY');self.assertEqual(wy['state'],'56');self.assertEqual(wy['accounting'],dc['accounting'])

 def test_N2B02_copied_binding_state_policy_path_tamper(self):
  for key,value in (('active_state','56'),('output_directory','data/processed/escape'),('model_calls',1)):
   live=deepcopy(self.env.live);live[key]=value
   with patch.object(source,'_open_no_follow',side_effect=AssertionError('raw')) as raw:
    with self.assertRaises(Blocked):a.admit_fixture(self.env.realm,live)
    raw.assert_not_called()
  b=self.c.binding;b['config']['caps']['total']*=2
  copied=a.Context(self.c.realm,self.c.config_json,json.dumps(b),self.c.token)
  with self.assertRaises(Blocked):a.require(copied)

 def test_N2B03_actual_default_refuses_before_FS_and_fixture_no_actual(self):
  with patch('pathlib.Path.stat',side_effect=AssertionError('stat')),patch('pathlib.Path.open',side_effect=AssertionError('open')):
   for c in (None,self.env.base,self.env.live):
    with self.assertRaises(Blocked):runner.run_actual(c)

 def test_N2B04_bad_child_noncitizen_GQ_required_fields(self):
  for field,value in (('STATE','56'),('RT','H'),('PWGTP80','BAD'),('FAGEP','2')):
   rs=rows();rs[-1][field]=value
   with tempfile.TemporaryDirectory() as t:
    e=Env(Path(t)/'e',records=rs);c=e.admit();ctl=Control(c,create=True);ctl.run_stage('BIND',lambda:source.inspect_source(c,ctl,'BIND'))
    with ctl.lock():ctl.advance('RESERVE','DC_PRIMARY')
    with self.assertRaises(Blocked):source.parse_state(c,ctl,'DC_PRIMARY')

 def test_N2B05_width_header_schema(self):
  ctl=self.reserve();original=csv.DictReader
  class BadReader:
   def __init__(self,*args,**kw):self.inner=original(*args,**kw)
   def __iter__(self):
    for row in self.inner:row[None]=['extra'];yield row
  with patch.object(source.csv,'DictReader',BadReader),self.assertRaises(Blocked):source.parse_state(self.c,ctl,'DC_PRIMARY')

 def test_N2B06_boundaries_and_blank_universe(self):
  required=self.c.config['required_fields'];r=rows()[0]
  for age in (0,2,3,17,18,24,25,44,45,64,65,99):
   q=dict(r,AGEP=str(age),SCHL='' if age<3 else '24');local,w,reps,flags=parse_person(q,'11',required);self.assertEqual(local is None,age<18)
  with self.assertRaises(Blocked):parse_person(dict(r,AGEP='3',SCHL=''),'11',required)

 def test_N2B07_signed_replicates_flags_and_bigint(self):
  p=self.parse();m=parts.validate(p,self.c.binding['spec']);s=8*72;self.assertEqual(m.data['replicates.i64le'][s*80],-1);self.assertEqual(m.data['replicates.i64le'][s*80+1],3)
  num,*_=moments(9000000000000000000,[-9000000000000000000]*80,Ops(1000));self.assertGreater(num,2**63)
  with self.assertRaises(Blocked):m.add(s,2**63,[1]*80,[0]*4)

 def test_N2B08_all_age_six_domain_nested_C(self):
  p=self.parse();self.assertEqual(p['accounting']['all']['count'],12);self.assertEqual(p['accounting']['under18']['count'],6);self.assertEqual(p['accounting']['adult']['point'],21);self.assertEqual([d['adult']['count'] for d in p['domains'].values()],[1]*6)
  q=deepcopy(p);q['domains']['5']['adult']['count']=0
  with self.assertRaises(Blocked):parts.validate(q,self.c.binding['spec'])

 def test_N2B09_exact_two_streams_firsthash_replay_and_count(self):
  calls=[];original=zipfile.ZipFile.open
  def watch(z,name,*args,**kw):
   if name=='psam_p11.csv':calls.append(name)
   return original(z,name,*args,**kw)
  with patch.object(zipfile.ZipFile,'open',watch):result=runner.run(self.c)
  self.assertEqual(len(calls),2);self.assertEqual(result['reservation']['rows'],65010)
  for cohort,order in [('PRIMARY',['direct','registry']),('REPLAY',['registry','direct'])]:
   proof=json.loads((self.c.output/'core'/('ASSEMBLE_'+cohort+'.receipt.json')).read_text());ev=proof['result']['comparison']['resource_evidence'];self.assertEqual(ev['evaluation_order_observed'],order)
   self.assertGreater(ev['stage_common']['bookkeeping']['content_read_bytes'],0);self.assertGreater(ev['stage_common']['bookkeeping']['content_write_bytes'],0)
   self.assertTrue(all(v['input_sha256']==ev['input_sha256'] for v in ev['variants']))
  with self.assertRaises(Blocked):runner.run(self.c)

 def test_N2B10_parent_file_identity_replacement_refuses(self):
  ctl=self.reserve();p=self.c.root/self.c.source['relative_path'];data=p.read_bytes();old=p.with_suffix('.old');p.rename(old);p.write_bytes(data)
  with self.assertRaises(Blocked):source.parse_state(self.c,ctl,'DC_PRIMARY')

 def test_N2B11_historical_part_refs_and_schema_tamper(self):
  old=json.loads((self.env.root/'inputs/WY_PRIMARY.json').read_text());ref=self.env.live['saved_parts']['PRIMARY'];spec=self.c.binding['spec']
  p=parts.from_saved_wy(old,spec,ref,realm='TEST_ONLY',spec_sha256=self.c.config['specification']['sha256']);self.assertEqual(p['state'],'56')
  old['state']='11'
  with self.assertRaises(Blocked):parts.from_saved_wy(old,spec,ref,realm='TEST_ONLY',spec_sha256=self.c.config['specification']['sha256'])

 def test_N2B12_WY_singleton_bridge_arrays(self):
  wy=runner._saved(self.c,'PRIMARY');spec=self.c.binding['spec'];a1=assembly.direct_merge([wy],spec);a2=assembly.registry_merge([wy],spec);self.assertEqual(a1.blobs(),a2.blobs());self.assertEqual(sum(a1.present),72)

 def test_N2B13_independent_correlated_antivar_oracle(self):
  self.assertEqual(moments(2,[2]*80,Ops(1000))[0],0)
  self.assertEqual(moments(1,[-1 if i%2 else 3 for i in range(80)],Ops(1000))[0]/20,16)
  dc=self.parse();wy=runner._saved(self.c,'PRIMARY');m=assembly.direct_merge([wy,dc],self.c.binding['spec']);self.assertEqual(sum(m.data['point.i64le']),42)

 def test_N2B14_partial_unknown_vs_known_zero(self):
  dc=self.parse();wy=runner._saved(self.c,'PRIMARY');spec=self.c.binding['spec'];m=assembly.registry_merge([dc,wy],spec);self.assertEqual(sum(m.present),144);self.assertIsNone(m.record(0,spec)['point_weight_sum']);self.assertEqual(m.record(8*72+6,spec)['point_weight_sum'],0)
  with self.assertRaises(Blocked):assembly.require_full_national(m)

 def test_N2B15_replay_sourceorder_data_and_separate_lineage(self):
  dc=self.parse();wy=runner._saved(self.c,'PRIMARY');spec=self.c.binding['spec'];self.assertEqual(assembly.registry_merge([wy,dc],spec).blobs(),assembly.direct_merge([dc,wy],spec).blobs())
  with self.assertRaises(Blocked):assembly.registry_merge([wy,wy],spec)

 def test_N2B16_ratio_nonpositive_and_signed_covariance(self):
  rec=uncertainty('ratio',1,[3]*80,Ops(1000),denominator=('F',2,[-1]*80));self.assertEqual(rec['status'],'BLOCKED_NONPOSITIVE_REPLICATE_DENOMINATOR')
  rec=uncertainty('missing',None,[None]*80,Ops(1000));self.assertIsNone(rec['variance_sdr'])

 def test_N2B17_before_work_query_plan_bounds(self):
  for kw in ({'optional_queries':1},{'logical_limit':11999999}):
   with self.assertRaises(Blocked):assembly.plan(**kw)
  self.assertEqual(assembly.plan()['total_reserved'],12000000)

 def test_N2B18_full_history_and_reservation_no_refund(self):
  ctl=self.control();s=ctl.snapshot();self.assertEqual(s['history']['WY_full_outer_reservation']['seconds'],1800);self.assertEqual(s['history']['N2a_DC_full_reservation']['processing_seconds'],300);self.assertEqual(s['reservation']['ops'],24000000)
  with self.assertRaises(Blocked):ctl.run_stage('BIND',lambda:(_ for _ in ()).throw(OSError('PRIVATE_PAYLOAD_NOT_LOGGED')))
  after=ctl.snapshot();self.assertTrue(after['halted']);self.assertEqual(after['reservation'],s['reservation']);self.assertNotIn('PRIVATE_PAYLOAD', (ctl.path/'core/events.jsonl').read_text())

 def test_N2B19_deadlines_original_fit_and_rollback(self):
  self.clock['wall']=1793739516.
  with self.assertRaises(Blocked):self.control()
  self.assertFalse(self.c.output.exists());self.clock['wall']=1793737000.;ctl=self.control();self.clock['wall']-=1
  with self.assertRaises(Blocked):ctl.snapshot()

 def test_N2B20_real_authored_crash_pending_unknown(self):
  ctl=self.control();ctx=multiprocessing.get_context('fork')
  def crash():
   with ctl.lock():ctl.advance('RESERVE','BIND');os._exit(29)
  p=ctx.Process(target=crash);p.start();p.join(8);self.assertEqual(p.exitcode,29);self.assertEqual(ctl.snapshot()['stages']['BIND']['status'],'RESERVED');ctl.unknown();s=ctl.snapshot();self.assertEqual(s['stages']['BIND']['status'],'UNKNOWN');self.assertEqual(s['reservation']['seconds'],1500)
  with self.assertRaises(Blocked):runner.run(self.c)

 def test_N2B21_torn_counter_lost_control_concurrency(self):
  ctl=self.control()
  with ctl.lock():
   with self.assertRaises(Blocked):Control(self.c)
  p=ctl.path/'core/state.json';s=json.loads(p.read_text());s['reservation']['seconds']=0;save(p,s)
  with self.assertRaises(Blocked):ctl.snapshot()
  with self.assertRaises(Blocked):Control(self.c,create=True)

 def test_N2B22_whole_storage_hardlinks_exactcap_and_disk(self):
  ctl=self.control();p=ctl.path/'core/unexpected';p.write_bytes(b'x'*97);os.link(p,ctl.path/'core/hardlink');used=ctl.storage()['new']['core'];cap=self.c.config['caps']['core'];self.assertEqual(ctl.storage(extra={'core':cap-used})['new']['core'],cap)
  with self.assertRaises(Blocked):ctl.storage(extra={'core':cap-used+1})
  with patch('shutil.disk_usage',return_value=shutil.disk_usage(self.env.root)._replace(free=0)):
   with self.assertRaises(Blocked):ctl.storage()

 def test_N2B23_partition_sum_and_whole_old_new_data(self):
  ctl=self.control();caps=self.c.config['caps'];self.assertEqual(sum(caps[k] for k in ('core','DC_PRIMARY_part','DC_REPLAY_part','ASSEMBLE_PRIMARY_canonical_data','ASSEMBLE_REPLAY_canonical_data','scratch')),44040192)
  prior=self.env.root/'prior/data';prior.mkdir(parents=True);(prior/'unexpected').write_bytes(b'X'*10)
  self.assertEqual(ctl.storage()['old_data'],10)
  with self.assertRaises(Blocked):ctl.storage(extra={'DC_PRIMARY_part':caps['DC_PRIMARY_part']+1})

 def test_N2B24_disclosure_and_payload_safe_failures(self):
  with self.assertRaises(Blocked):runner.project_outputs(self.c)
  ctl=self.control();ctl.cancel()
  with self.assertRaises(Blocked):ctl.run_stage('BIND',lambda:None)
  self.assertEqual(ctl.snapshot()['stages']['BIND']['status'],'FAILED')

 def test_N2B25_no_campaign_cap_reset_or_new_window(self):
  for field in ('caps','history','native_limits'):
   c=deepcopy(self.env.live);key=next(k for k,v in c[field].items() if type(v) is int);c[field][key]+=1
   with self.assertRaises(Blocked):a.admit_fixture(self.env.realm,c)
  p=self.env.root/'src/civiclab/common.py';p.write_bytes(p.read_bytes()+b'\n# ALTERED_AUTHORED_PIN\n')
  with self.assertRaises(Blocked):a.require(self.c)


 def test_person_read_quota_prevents_hidden_third_sweep(self):
  ctl=self.reserve();source.parse_state(self.c,ctl,'DC_PRIMARY')
  with patch.object(source,'_open_no_follow',side_effect=AssertionError('third scan')) as raw:
   with self.assertRaises(Blocked):source.parse_state(self.c,ctl,'DC_PRIMARY')
   raw.assert_not_called()
  self.assertEqual(ctl.snapshot()['stages']['DC_PRIMARY']['source_reads'],{'metadata':2,'person':1})

 def test_lost_output_cannot_reset_external_owner(self):
  ctl=self.control();shutil.rmtree(ctl.path)
  with self.assertRaises(Blocked):Control(self.c,create=True)
  self.assertTrue((self.c.registry/'ORIGINAL_OWNER.json').exists())

 def test_low_initial_disk_no_control_or_source_access(self):
  with patch('shutil.disk_usage',return_value=shutil.disk_usage(self.env.root)._replace(free=0)),patch.object(source,'_open_no_follow',side_effect=AssertionError('raw')) as raw:
   with self.assertRaises(Blocked):self.control()
   raw.assert_not_called()
  self.assertFalse(self.c.output.exists());self.assertFalse(self.c.registry.exists())

 def test_person_CRC_failure_and_partial_stop_retained(self):
  raw,person=body();raw=bytearray(raw);position=raw.index(b'P,11');raw[position]=ord('Q')
  with tempfile.TemporaryDirectory() as t:
   e=Env(Path(t)/'e',source_blob=bytes(raw));c=e.admit()
   with self.assertRaises(Blocked):runner.run(c)
   state=Control(c).snapshot();self.assertEqual(state['stages']['DC_PRIMARY']['status'],'FAILED');self.assertEqual(state['reservation']['rows'],65010)

 def test_firsthash_replay_mismatch_requires_original_digest(self):
  ctl=self.control();ctl.run_stage('BIND',lambda:source.inspect_source(self.c,ctl,'BIND'))
  ctl.run_stage('DC_PRIMARY',lambda:{'part_sha256':canonical_hash(source.parse_state(self.c,ctl,'DC_PRIMARY'))})
  with self.assertRaises(Blocked):ctl.run_stage('DC_REPLAY',lambda:source.parse_state(self.c,ctl,'DC_REPLAY',primary_person_sha256='f'*64))
  self.assertEqual(ctl.snapshot()['stages']['DC_REPLAY']['status'],'FAILED')

 def test_changed_expected_rows_not_repaired(self):
  self.env.live['source_manifest']['expected_rows']=13;self.env.reseal();c=self.env.admit()
  with self.assertRaises(Blocked):runner.run(c)
  self.assertEqual(Control(c).snapshot()['stages']['DC_PRIMARY']['status'],'FAILED')

 def test_allocation_flags_exact_source_arithmetic(self):
  rs=rows()
  for d in range(6):rs[d]['FAGEP']=str(d%2)
  with tempfile.TemporaryDirectory() as t:
   e=Env(Path(t)/'e',records=rs);c=e.admit();ctl=Control(c,create=True);ctl.run_stage('BIND',lambda:source.inspect_source(c,ctl,'BIND'))
   with ctl.lock():ctl.advance('RESERVE','DC_PRIMARY')
   p=source.parse_state(c,ctl,'DC_PRIMARY');m=parts.validate(p,c.binding['spec']);self.assertEqual(sum(m.data['allocation_counts.i64le']),3);self.assertEqual(sum(m.data['allocation_weights.i64le']),12)

 def test_cancel_writer_independent_of_owner_lock(self):
  ctl=self.control()
  with ctl.lock():ctl.cancel()
  self.assertTrue((ctl.path/'core/CANCEL').exists())

 def test_late_postcommit_guard_withdraws_acceptance(self):
  ctl=self.control();original=ctl.advance
  def late(event,*args,**kw):
   result=original(event,*args,**kw)
   if event=='COMPLETE':self.clock['wall']+=301;self.clock['mono']+=301
   return result
  with patch.object(ctl,'advance',side_effect=late),self.assertRaises(Blocked):ctl.run_stage('BIND',lambda:{'safe':True})
  self.assertEqual(ctl.snapshot()['stages']['BIND']['status'],'FAILED');self.assertTrue((ctl.path/'core/BIND.receipt.json').exists())

 def test_control_path_override_and_safe_schema_refusal(self):
  ctl=self.control();ctl.path=self.env.root/'inputs'
  with self.assertRaises(Blocked):ctl.snapshot()

 def test_symlink_source_refuses_before_follow(self):
  ctl=self.reserve();p=self.c.root/self.c.source['relative_path'];p.rename(p.with_suffix('.old'));p.symlink_to(p.with_suffix('.old'))
  with self.assertRaises(Blocked):source.parse_state(self.c,ctl,'DC_PRIMARY')

 def test_semantic_event_reseal_without_reserved_stage(self):
  ctl=self.control();g=ctl.snapshot();p={'at':a.tick(),'stage':'BIND','result':{'kind':'person'}};row={'seq':1,'previous':None,'before':canonical_hash(g),'event':'ACCESS','payload':p,'after':canonical_hash(g)};row['hash']=canonical_hash(row);(ctl.path/'core/events.jsonl').write_text(json.dumps(row)+'\n')
  with self.assertRaises(Blocked):ctl.snapshot()

 def test_exact_correlated_variance_not_sum_state_variances(self):
  first=[-1 if i%2 else 3 for i in range(80)];second=[3 if i%2 else -1 for i in range(80)]
  aggregated=[x+y for x,y in zip(first,second)];self.assertEqual(moments(2,aggregated,Ops(1000))[0]//20,0);self.assertEqual(sum(moments(1,r,Ops(1000))[0]//20 for r in (first,second)),32)

 def test_source_compressed_or_header_pin_change_refuses(self):
  self.env.live['source_manifest']['archive_sha256']='0'*64;self.env.reseal();c=self.env.admit()
  with self.assertRaises(Blocked):runner.run(c)
  self.assertEqual(Control(c).snapshot()['stages']['BIND']['status'],'FAILED')

 def test_actual_scope_and_approvals_cannot_promote_test(self):
  release=self.env.live['approvals']['execution'];p=self.env.root/release['path'];r=json.loads(p.read_text());r['scope']['GETs']=1;self.env.live['approvals']['execution']=self.env.record('badrelease',r)
  with self.assertRaises(Blocked):self.env.admit()



 def test_original_WY_byte_SHA_is_distinct_from_canonical_SHA(self):
  methods=json.loads((REAL/METHODS).read_text());ref={'accepted_audit_sha256':methods['public_input_pins']['reports/INDEPENDENT_AUDIT_E02_F_WY_REAL_NATIVE_ENGINEERING_v1.json'],'sha256':methods['initial_states']['WY']['saved_part_SHA256']['PRIMARY'],'part_canonical_sha256':'9'*64}
  self.assertTrue(a.verify_accepted_wy_reference(ref,'PRIMARY',methods));ref['sha256']='0'*64
  with self.assertRaises(Blocked):a.verify_accepted_wy_reference(ref,'PRIMARY',methods)

 def test_prior_storage_ancestor_symlink_refuses(self):
  ctl=self.control();p=self.env.root/'prior';target=self.env.root/'AUTHORED_OUTSIDE_OWNED';target.mkdir();p.symlink_to(target)
  with self.assertRaises(Blocked):ctl.storage()

 def test_control_output_ancestor_symlink_refuses(self):
  ctl=self.control();p=self.env.root/'data/processed';p.rename(p.with_name('AUTHORED_MOVED'));p.symlink_to(p.with_name('AUTHORED_MOVED'))
  with self.assertRaises(Blocked):ctl.snapshot()



 def prior_file(self,relative,size,name='unexpected.tmp'):
  p=self.env.root/relative/name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('wb') as f:f.truncate(size)
  return p

 def test_F1_N2A_raw_exactcap_plusone_blocks_before_source(self):
  p=self.prior_file('data/raw/e02_n2a_sources_v1',8388608);ctl=self.control();self.assertEqual(ctl.storage()['prior_subpartitions']['N2A:raw'],8388608)
  with p.open('ab') as f:f.write(b'X')
  with patch.object(source,'_open_no_follow',side_effect=AssertionError('source')) as raw:
   with self.assertRaises(Blocked):ctl.run_stage('BIND',lambda:source.inspect_source(self.c,ctl,'BIND'))
   raw.assert_not_called()
  self.assertEqual(ctl.snapshot()['reservation']['seconds'],1500)

 def test_F1_N2A_combined_registry_core_boundary(self):
  p=self.prior_file('data/processed/e02_n2a_core_v1',2097152);q=self.prior_file('data/processed/e02_n2a_registry_v1',2097152);ctl=self.control();self.assertEqual(ctl.storage()['prior_subpartitions']['N2A:core'],4194304)
  with q.open('ab') as f:f.write(b'X')
  with self.assertRaises(Blocked):ctl.storage()

 def test_F1_N2A_shared_scratch_all_roots_and_hardlinks(self):
  p=self.prior_file('data/raw/e02_n2a_sources_v1/scratch',524288);q=self.env.root/'data/processed/e02_n2a_core_v1/scratch/alias';q.parent.mkdir(parents=True);os.link(p,q);ctl=self.control();self.assertEqual(ctl.storage()['prior_subpartitions']['N2A:scratch'],1048576)
  with p.open('ab') as f:f.write(b'X')
  with self.assertRaises(Blocked):ctl.storage()

 def test_F1_WY_base_both_phases_cap_plusone(self):
  for phase in ('PRIMARY','REPLAY'):
   root='data/processed/e02_F_wy_private/conditional-actual-v1-20261103-01/'+phase;p=self.prior_file(root,8388608)
  ctl=self.control();self.assertEqual(ctl.storage()['prior_subpartitions']['WY:data_both'],16777216)
  with p.open('ab') as f:f.write(b'X')
  with self.assertRaises(Blocked):ctl.storage()

 def test_F1_WY_catalog_atomic_and_unexpected_accounting(self):
  root='data/processed/e02_F_wy_private/conditional-actual-v1-20261103-01/PRIMARY';p=self.prior_file(root,3145728,'selectors.json.atomic');ctl=self.control();self.assertEqual(ctl.storage()['prior_subpartitions']['WY:PRIMARY:catalog'],3145728)
  q=self.prior_file(root+'/catalog',1,'unexpected.bin')
  with self.assertRaises(Blocked):ctl.storage()

 def test_F1_WY_receipts_and_bootstrap_core_exactcap_plusone(self):
  root='data/processed/e02_F_wy_private_bootstrap/conditional-actual-v1-20261103-01';p=self.prior_file(root,20971520,'query_receipts_v1_1.jsonl');ctl=self.control();self.assertEqual(ctl.storage()['prior_subpartitions']['WY:receipts'],20971520)
  with p.open('ab') as f:f.write(b'X')
  with self.assertRaises(Blocked):ctl.storage()

 def test_F1_all_local_subcaps_atcap_then_plusone(self):
  # Some original local limits are larger than other whole limits: test local
  # equality directly, without pretending the full inventory can fit them all.
  p=self.c.config['prior_storage_policy'];cases={'N2A:raw':8388608,'N2A:core':4194304,'N2A:scratch':1048576,'N2A:total':13631488,'WY:PRIMARY:base':8388608,'WY:REPLAY:base':8388608,'WY:PRIMARY:catalog':3145728,'WY:REPLAY:catalog':3145728,'WY:PRIMARY:query':9437184,'WY:REPLAY:query':9437184,'WY:core':71303168,'WY:receipts':20971520,'WY:scratch':268435456,'WY:raw':4294967296,'WY:logs':92274688,'WY:data_both':41943040,'WY:all_artifacts':134217728}
  for key,cap in cases.items():
   self.assertTrue(prior_storage.validate_subcaps({key:cap},p))
   with self.assertRaises(Blocked):prior_storage.validate_subcaps({key:cap+1},p)

 def test_F1_storage_caps_not_mutable_and_no_namespace_reset(self):
  c=deepcopy(self.env.live);c['prior_storage_policy']['n2a_limits']['core_metadata_bytes']*=2
  with self.assertRaises(Blocked):a.admit_fixture(self.env.realm,c)
  self.assertEqual(self.c.config['output_directory'],'data/processed/e02_n2b_private_v1');self.assertEqual(self.c.config['registry_directory'],'data/processed/e02_n2b_registry_v1')

 def test_F2_actual_variant_order_and_scoped_measurements(self):
  dc=self.parse();wy=runner._saved(self.c,'PRIMARY');items=[wy,dc];spec=self.c.binding['spec'];called=[];d=assembly.direct_merge;r=assembly.registry_merge
  def direct(*args):called.append('direct');return d(*args)
  def registry(*args):called.append('registry');return r(*args)
  with patch.object(assembly,'direct_merge',direct),patch.object(assembly,'registry_merge',registry):result=assembly.matched(items,spec,evaluation_order=('registry','direct'))
  evidence=result[3]['resource_evidence'];self.assertEqual(called[:2],['registry','direct']);self.assertEqual(evidence['evaluation_order_observed'],['registry','direct'])
  for v in evidence['variants']:
   self.assertGreaterEqual(v['evaluation_seconds'],0);self.assertGreater(v['sampled_current_rss_peak_bytes'],0);self.assertGreaterEqual(v['rss_samples'],2);self.assertGreater(v['input_logical_bytes'],0);self.assertGreater(v['output_logical_bytes'],0);self.assertIn('bookkeeping_seconds_sum',v['bookkeeping']);self.assertEqual(v['physical_payload_file_read_bytes'],0)

 def test_F2_RSS_or_measurement_failure_is_retained_no_refund(self):
  ctl=self.control();events=[]
  def work():
   with patch.object(metrics,'current_rss',return_value=536870913):
    return metrics.evaluate('direct',lambda:None,input_bytes=1,input_sha256='0'*64)
  with self.assertRaises(Blocked):ctl.run_stage('BIND',work)
  self.assertEqual(ctl.snapshot()['stages']['BIND']['status'],'FAILED');self.assertEqual(ctl.snapshot()['reservation']['ops'],24000000)

 def test_F2_failed_comparator_measurement_callback(self):
  dc=self.parse();wy=runner._saved(self.c,'PRIMARY');failed=[]
  with patch.object(metrics,'current_rss',side_effect=Blocked('AUTHORED_MEASUREMENT_UNAVAILABLE')):
   with self.assertRaises(assembly.ComparisonFailure):assembly.matched([wy,dc],self.c.binding['spec'],record_failure=failed.append)
  self.assertEqual(failed[0]['status'],'FAILED_ENGINEERING_COMPARISON');self.assertEqual(failed[0]['variants'][0]['status'],'FAILED');self.assertTrue(failed[0]['full_reservations_retained']);self.assertEqual(failed[0]['evaluation_order_observed'],[]);self.assertEqual(failed[0]['measurement_attempt_order'],['direct']);self.assertFalse(failed[0]['variants'][0]['evaluation_started'])



 def test_F2_partial_evaluation_failure_records_elapsed_without_payload(self):
  def failure():raise ValueError('PRIVATE_AUTHORED_ERROR_PAYLOAD')
  with patch.object(metrics,'current_rss',return_value=1024):
   with self.assertRaises(metrics.VariantFailure) as caught:metrics.evaluate('direct',failure,input_bytes=1,input_sha256='0'*64)
  e=caught.exception.evidence;self.assertTrue(e['evaluation_started']);self.assertGreaterEqual(e['evaluation_seconds'],0);self.assertNotIn('PRIVATE_AUTHORED_ERROR_PAYLOAD',json.dumps(e));self.assertTrue(e['sampler_shutdown_confirmed'])


def retain_authored_evidence(root):
 root=Path(root).resolve();root.mkdir(exist_ok=False)
 summary={'label':'TEST_ONLY_AUTHORED_NOT_ACTUAL_POPULATION','code_files':code_files(),'cases':{},'real_network_calls':0,'actual_person_rows':0,'experimental_spend_usd':0,'fixture_generation_overhead':'All inputs, copied repo metadata and scripted approval records are authored generation overhead outside42MiB new-owned output partitions; actual source/private data never copied.'}
 clock={'wall':1793737000.,'mono':1000.}
 with patch.object(a,'tick',side_effect=lambda:dict(clock)):
  for name in ('success','invalid_child_failure','crash_unknown','prior_raw_overcap','variant_measurement_failure'):
   case=root/name;case.mkdir();rs=rows()
   if name=='invalid_child_failure':rs[-1]['PWGTP80']='INVALID_AUTHORED'
   e=Env(case/'realm',records=rs);c=e.admit()
   if name=='prior_raw_overcap':
    prior=c.root/'data/raw/e02_n2a_sources_v1/UNEXPECTED.partial';prior.parent.mkdir(parents=True)
    with prior.open('wb') as f:f.truncate(8388609)
    try:runner.run(c)
    except Blocked:pass
    else:raise AssertionError('prior overcap accepted')
    if c.output.exists() or c.registry.exists():raise AssertionError('overcap created job/owner')
    out={'status':'EXPECTED_PRE_JOB_PRIOR_RAW_CAP_REFUSAL','prior_raw_bytes_retained':prior.stat().st_size,'new_job_reserved':False,'person_rows':0,'original_history':c.config['history']}
    save(case/'CONTROL_ORACLE.json',out);summary['cases'][name]=out;continue
   if name=='crash_unknown':
    ctl=Control(c,create=True)
    def crash():
     with ctl.lock():ctl.advance('RESERVE','BIND');os._exit(29)
    child=multiprocessing.get_context('fork').Process(target=crash);child.start();child.join(8)
    if child.is_alive():child.terminate();child.join();raise RuntimeError('AUTHORED_CHILD_TIMEOUT')
    if child.exitcode!=29:raise RuntimeError('AUTHORED_CRASH_NOT_REACHED')
    save(case/'PENDING_BEFORE_UNKNOWN.json',ctl.snapshot());ctl.unknown();out={'child_exitcode':29,'raw_person_passes':0}
   else:
    try:
     if name=='variant_measurement_failure':
      with patch.object(metrics,'current_rss',return_value=536870913):out=runner.run(c)
     else:out=runner.run(c)
     if name!='success':raise AssertionError('expected invalid child refusal')
    except Blocked:
     if name=='success':raise
     out={'status':'EXPECTED_AUTHORED_FAILURE_'+name}
    ctl=Control(c)
   state=ctl.snapshot();out.update(final_state=state,storage=ctl.storage(),old_saved_parts_unchanged=all(sha(c.root/v['relative_path'])==v['sha256'] for v in c.config['saved_parts'].values()))
   before=canonical_hash(state)
   try:runner.run(c)
   except Blocked:pass
   else:raise AssertionError('retry accepted')
   if canonical_hash(ctl.snapshot())!=before:raise AssertionError('retry mutated retained history')
   out['retry_unchanged']=True;save(case/'CONTROL_ORACLE.json',out);summary['cases'][name]={'status':out.get('status'),'stages':{k:v['status'] for k,v in state['stages'].items()},'reservation':state['reservation'],'retry_unchanged':True,'storage':out['storage']}
 summary['files']={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(root.rglob('*')) if p.is_file()}
 save(root/'AUTHORED_EVIDENCE_INDEX.json',summary);return root/'AUTHORED_EVIDENCE_INDEX.json'
