"""Authored N2a HTTP/control fixtures only. No actual Census GET or raw access."""
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
import time
import unittest
from unittest.mock import patch
import zipfile

from civiclab.common import canonical_hash
from civiclab.e02 import n2a_collector_v1 as n2
from civiclab.e02.national_budget import Blocked

REAL=Path(__file__).resolve().parents[1]
PROPOSAL='configs/e02_next_dc_source_unit_proposal_v1.json'
METHODS='reports/INDEPENDENT_AUDIT_E02_NEXT_DC_SOURCE_UNIT_V1_METHODS.json'
NATIVE='configs/e02_F_WY_LOCAL_IMPLEMENTATION_v1_1.json'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')


def code_files():
 names=['src/civiclab/e02/n2a_collector_v1.py','src/civiclab/e02/n2a_http_v1.py','tests/test_e02_n2a_collector_v1.py',METHODS,
        'src/civiclab/__init__.py','src/civiclab/e02/__init__.py','src/civiclab/common.py','src/civiclab/e02/national_budget.py',
        'src/civiclab/e02/full_adult_types_v1_2.py','src/civiclab/e02/f_actual_admission_v1_1.py',
        'src/civiclab/e02/f_wy_bootstrap_v1.py','src/civiclab/e02/f_wy_bootstrap_v1_1.py']
 return {p:sha(REAL/p) for p in names}


def static_config(tag='PRODUCTION'):
 native=json.loads((REAL/NATIVE).read_text());p=json.loads((REAL/PROPOSAL).read_text())
 return {'schema_version':1,'protocol':'N2A_REGISTRY_SINGLE_SOURCE_COLLECTOR_V1','realm':tag,'execution_authority':0,'live_refs':{'code_review':None,'release':None},'active_state':'11',
         'files':code_files(),'registry_reference':{'path':'reports/E02_PUMS_METADATA_RECONSTRUCTION.json','sha256':sha(REAL/'reports/E02_PUMS_METADATA_RECONSTRUCTION.json')},
         'native_reference':{'path':NATIVE,'sha256':sha(REAL/NATIVE)},'native_limits':native['limits'],'required_fields':native['required_fields'],
         'reference_header_sha256':native['spec']['WY_raw_candidate']['header_sha256'],'unit_limits':p['N2a_acquisition_subcaps'],
         'registry_directory':'data/processed/e02_n2a_registry_v1','core_directory':'data/processed/e02_n2a_core_v1','raw_directory':'data/raw/e02_n2a_sources_v1',
         'history_references':{'reports/E02_PUMS_WY_PILOT_ACQUISITION_FAILURE.json':sha(REAL/'reports/E02_PUMS_WY_PILOT_ACQUISITION_FAILURE.json'),'reports/E02_PUMS_WY_PILOT_PREPARATION.json':sha(REAL/'reports/E02_PUMS_WY_PILOT_PREPARATION.json'),'reports/E02_F_WY_REAL_NATIVE_ENGINEERING_HANDOFF_v1.json':sha(REAL/'reports/E02_F_WY_REAL_NATIVE_ENGINEERING_HANDOFF_v1.json')},
         'history_baseline':{'prior_person_GETs':1,'prior_metadata_requests':5,'prior_body_reserved_upper_bound':8388608,'prior_metadata_received_bytes':1279577,'prior_WY_retained_bytes':4202266,'prior_charges_refunded':False},
         'source_authority_policy':'Existing owner ordinary public Census research scope; finite source release after independent code review. No new blanket human/key gate.',
         'model_calls_authorized':0,'fit_authorized':False,'disclosure_authorized':False}


class Env:
 def __init__(self,root,active='11'):
  self.realm=n2.make_test_realm(root);self.root=self.realm.root;self.base=static_config('TEST_ONLY')
  for p in set(self.base['files'])|set(self.base['history_references'])|{NATIVE,self.base['registry_reference']['path']}:
   target=self.root/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((REAL/p).read_bytes())
  save(self.root/n2.CONFIG,self.base);self.live=deepcopy(self.base);self.live['execution_authority']=1;self.live['active_state']=active
  policy={k:v for k,v in self.base.items() if k not in ('execution_authority','live_refs','active_state')};self.P=canonical_hash(policy)
  states=json.loads((self.root/self.base['registry_reference']['path']).read_text())['complete_public_metadata']['states'];source=next(x for x in states if x['state_fips']==active)
  design=canonical_hash({'policy_sha256':self.P,'active_state':active,'source':source,'realm':'TEST_ONLY','root':str(self.root)})
  review={'realm':'TEST_ONLY','status':'PASS_N2A_COLLECTOR_CODE_AUTHORED_FIXTURES','auditor_role':'independent_auditor','policy_sha256':self.P,'files':self.base['files'],'reviewed_states':['11','02']}
  rr=self.record('review',review)
  release={'realm':'TEST_ONLY','status':'RELEASE_N2A_ONE_ORDINARY_PUBLIC_SOURCE_GET','issuer_role':'lead','design_sha256':design,'code_review_sha256':rr['sha256'],'not_before':time.time()-30,'expires':time.time()+86400,
           'scope':{'root':str(self.root),'state':active,'url':source['url'],'GETs':1,'HEADs':0,'redirects':0,'retries':0,'person_rows':0,'model_calls':0,'fit':False,'disclosure':False},
           'limits':self.base['unit_limits'],'owner_research_authorization_reference':'TEST_ONLY_AUTHORED_NOT_ACTUAL_PERMISSION'}
  self.live['live_refs']={'code_review':rr,'release':self.record('release',release)}
 def record(self,name,obj):
  p='reports/TEST_ONLY_N2A_'+name+'.json';save(self.root/p,obj);return {'path':p,'sha256':sha(self.root/p)}
 def admit(self):return n2.admit_fixture(self.realm,self.live)


def archive_bytes(*,state='11',extra_person_bytes=0,header=None,extra_member=False,mode=zipfile.ZIP_DEFLATED,symlink=False):
 fields=json.loads((REAL/NATIVE).read_text())['required_fields']+['UNUSED_'+str(i) for i in range(194)]
 out=io.StringIO();writer=csv.writer(out);writer.writerow(fields)
 head=out.getvalue().encode() if header is None else header
 payload=head+b'P,TEST_ONLY_FICTIONAL_PERSON_NO_REAL_DATA\n'+b'X'*extra_person_bytes
 memory=io.BytesIO()
 with zipfile.ZipFile(memory,'w',compression=mode) as z:
  if symlink:
   info=zipfile.ZipInfo('psam_p'+state+'.csv');info.external_attr=(0o120777<<16);z.writestr(info,payload)
  else:z.writestr('psam_p'+state+'.csv',payload)
  z.writestr('ACS2020_2024_PUMS_README.pdf',b'%PDF-AUTHORED-NOT-RENDERED')
  if extra_member:z.writestr('readme.txt',b'NOT_ALLOWED')
 return memory.getvalue()


class N2aTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.env=Env(Path(self.tmp.name)/'fake');self.c=self.env.admit()
 def tearDown(self):self.tmp.cleanup()
 def body(self,**kwargs):return archive_bytes(**kwargs)
 def run_body(self,body=None,**kwargs):
  body=self.body() if body is None else body
  headers=kwargs.pop('headers',{'content-length':str(len(body)),'content-type':'application/zip'})
  return n2.collect_fixture(self.c,n2.fake_http(body,headers=headers,**kwargs))
 def state(self):return n2.Registry(self.c).snapshot()['attempts'][self.c.state]

 def test_production_null_or_test_authority_denied_before_filesystem_socket(self):
  with patch('pathlib.Path.stat',side_effect=AssertionError('stat')),patch('pathlib.Path.open',side_effect=AssertionError('open')),patch('socket.socket.connect',side_effect=AssertionError('socket')):
   for c in (None,self.env.base,self.env.live):
    with self.assertRaises(Blocked):n2.collect(c)

 def test_tagged_test_transport_cannot_enter_production(self):
  with self.assertRaises(Blocked):n2.admit(self.env.live)
  with self.assertRaises(Blocked):n2.collect_fixture({'execution_authority':1},n2.fake_http(self.body()))

 def test_positive_immutable_firsthash_unknown_before_response(self):
  body=self.body();self.assertIsNone(self.c.source['first_archive_sha256']);r=self.run_body(body)
  self.assertEqual(r['status'],'ACQUIRED_METADATA_VALIDATED_NOT_PERSON_IMPORTED');self.assertEqual(r['metadata']['archive_sha256'],hashlib.sha256(body).hexdigest())
  self.assertEqual(r['person_rows_read'],0);self.assertFalse(r['import_admitted']);self.assertFalse(r['metadata']['full_person_crc_scan']);self.assertIsNone(r['metadata']['actual_person_rows'])
  self.assertTrue(self.c.archive.is_file());self.assertFalse(self.c.part.exists());self.assertEqual(self.state()['status'],'COMPLETED')
  self.assertEqual(self.state()['reservation']['body_bytes'],8388608)

 def test_http_error_redirect_encoding_and_type_no_fallback(self):
  for mode in ('error','redirect','encoding','type','url'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
    e=Env(Path(t)/'fake');c=e.admit();body=self.body();headers={'content-length':str(len(body))}
    status=403 if mode=='error' else 302 if mode=='redirect' else 200
    if mode=='encoding':headers['content-encoding']='gzip'
    if mode=='type':headers['content-type']='text/html'
    fixture=n2.fake_http(body,status=status,headers=headers,url='https://example.invalid/' if mode=='url' else '')
    transport=n2._FixtureTransport(fixture)
    with self.assertRaises(Blocked):n2._collect(c,transport)
    self.assertEqual(transport.calls,1);self.assertEqual(transport.reads,[]);self.assertTrue(transport.closed)
    self.assertEqual(n2.Registry(c).snapshot()['attempts']['11']['status'],'FAILED')

 def test_content_length_truncation_and_oversize_declared(self):
  for length in (str(len(self.body())+100),'8388609','not-a-number'):
   with self.subTest(length=length),tempfile.TemporaryDirectory() as t:
    e=Env(Path(t)/'fake');c=e.admit()
    with self.assertRaises(Blocked):n2.collect_fixture(c,n2.fake_http(self.body(),headers={'content-length':length}))
    self.assertEqual(n2.Registry(c).snapshot()['attempts']['11']['reservation']['body_bytes'],8388608)

 def test_missing_length_metered_EOF_before_cap_success(self):
  r=self.run_body(headers={});self.assertEqual(r['received_bytes'],len(self.body()))

 def test_partial_failure_retains_bytes_and_full_charge_no_second_GET(self):
  body=self.body(mode=zipfile.ZIP_STORED,extra_person_bytes=5000)
  transport=n2._FixtureTransport(n2.fake_http(body,chunk=1024,fail_after=1024))
  with self.assertRaises(Blocked):n2._collect(self.c,transport)
  self.assertEqual(self.c.part.stat().st_size,1024);before=n2.Registry(self.c).snapshot();self.assertEqual(before['attempts']['11']['reservation']['body_bytes'],8388608)
  with patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('second GET')) as dispatch:
   with self.assertRaises(Blocked):self.run_body()
   dispatch.assert_not_called()
  self.assertEqual(before,n2.Registry(self.c).snapshot())

 def test_registry_attempt_other_state_is_same_code_not_module_copy(self):
  with tempfile.TemporaryDirectory() as t:
   e=Env(Path(t)/'ak','02');c=e.admit();r=n2.collect_fixture(c,n2.fake_http(self.body(state='02')))
   self.assertEqual(r['state'],'02');self.assertEqual(r['url'],'https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year/csv_pak.zip')

 def test_failed_request_history_counters_not_refunded(self):
  with self.assertRaises(Blocked):self.run_body(status=500)
  s=n2.Registry(self.c).snapshot();self.assertEqual(s['history'],self.env.base['history_baseline']);self.assertEqual(s['attempts']['11']['reservation']['network_seconds'],180)
  self.assertEqual(s['attempts']['11']['reservation']['processing_seconds'],300)

 def test_completed_URL_cannot_retry_or_mutate_state(self):
  self.run_body();before=n2.Registry(self.c).snapshot()
  with patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('retry')) as dispatch:
   with self.assertRaises(Blocked):self.run_body()
   dispatch.assert_not_called()
  self.assertEqual(before,n2.Registry(self.c).snapshot())

 def test_metadata_only_does_not_open_person_ZipExtFile(self):
  original=zipfile.ZipFile.open;names=[]
  def watched(z,name,*args,**kwargs):names.append(name);return original(z,name,*args,**kwargs)
  body=self.body()
  with patch.object(zipfile.ZipFile,'open',watched):self.run_body(body)
  self.assertEqual(names,['ACS2020_2024_PUMS_README.pdf'])

 def test_person_CRC_content_is_explicitly_deferred(self):
  body=bytearray(self.body(mode=zipfile.ZIP_STORED));position=body.index(b'P,TEST_ONLY');body[position]=ord('Z')
  r=self.run_body(bytes(body));self.assertFalse(r['metadata']['full_person_crc_scan']);self.assertFalse(r['import_admitted'])

 def test_bad_members_schema_and_header_limit_refuse(self):
  cases=[self.body(extra_member=True),self.body(symlink=True),self.body(state='02'),self.body(header=b'A,B\n'),self.body(header=b'X'*65536+b'\n')]
  for idx,body in enumerate(cases):
   with self.subTest(idx=idx),tempfile.TemporaryDirectory() as t:
    e=Env(Path(t)/'fake');c=e.admit()
    with self.assertRaises(Blocked):n2.collect_fixture(c,n2.fake_http(body))
    self.assertEqual(n2.Registry(c).snapshot()['attempts']['11']['status'],'FAILED')

 def test_declared_expansion_bound_before_person_inflate(self):
  body=bytearray(self.body());central=body.index(b'PK\x01\x02');struct.pack_into('<I',body,central+24,67108865)
  with self.assertRaises(Blocked):self.run_body(bytes(body))
  self.assertEqual(self.state()['status'],'FAILED')

 def test_full_parent_replacement_same_bytes_refuses(self):
  original=n2._header_line
  def replace(stream,*args):
   value=original(stream,*args);data=self.c.part.read_bytes();old=self.c.part.parent;old.rename(old.with_name('moved11'));old.mkdir();self.c.part.write_bytes(data);return value
  with patch.object(n2,'_header_line',side_effect=replace),self.assertRaises(Blocked):self.run_body()
  self.assertEqual(self.state()['status'],'FAILED');self.assertFalse(self.c.archive.exists())

 def test_file_replacement_and_symlink_during_header_refuse(self):
  for mode in ('file','symlink'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
    e=Env(Path(t)/'fake');c=e.admit();original=n2._header_line
    def replace(stream,*args):
     value=original(stream,*args);p=c.part;data=p.read_bytes();old=p.with_suffix('.old');p.rename(old)
     if mode=='file':p.write_bytes(data)
     else:p.symlink_to(old)
     return value
    with patch.object(n2,'_header_line',side_effect=replace),self.assertRaises(Blocked):n2.collect_fixture(c,n2.fake_http(self.body()))

 def test_directory_mtime_only_change_is_allowed(self):
  original=n2._header_line
  def change(stream,*args):
   value=original(stream,*args);(self.c.part.parent/'unrelated').write_bytes(b'X');return value
  with patch.object(n2,'_header_line',side_effect=change):r=self.run_body()
  self.assertEqual(r['status'],'ACQUIRED_METADATA_VALIDATED_NOT_PERSON_IMPORTED')

 def test_owned_binding_unexpected_files_hardlinks_and_exactcap(self):
  r=n2.Registry(self.c,create=True);before=r.storage()['core'];p=self.c.registry_root/'unexpected';p.write_bytes(b'x'*97);os.link(p,self.c.core_root/'hardlink')
  self.assertEqual(r.storage()['core'],before+194);used=r.storage()['core'];cap=self.c.config['unit_limits']['core_metadata_bytes']
  self.assertEqual(r.storage(extra_core=cap-used)['core'],cap)
  with self.assertRaises(Blocked):r.storage(extra_core=cap-used+1)
  with self.assertRaises(Blocked):r.storage(extra_raw=8388609)

 def test_initial_low_disk_blocks_before_dispatch(self):
  usage=shutil.disk_usage(self.env.root)
  with patch('shutil.disk_usage',return_value=usage._replace(free=0)),patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('dispatch')):
   with self.assertRaises(Blocked):self.run_body()

 def test_torn_state_lost_registry_and_raw_remnant_no_reset(self):
  r=n2.Registry(self.c,create=True)
  with r.lock():r.advance('RESERVE',url=self.c.source['url'],design=self.c.binding['design_sha256'],pid=os.getpid())
  p=r.path/'state.json';s=json.loads(p.read_text());s['attempts']['11']['reservation']['body_bytes']=0;save(p,s)
  with self.assertRaises(Blocked):n2.Registry(self.c)
  shutil.rmtree(r.path)
  with self.assertRaises(Blocked):n2.Registry(self.c,create=True)

 def test_semantic_reseal_dispatched_before_reservation_refuses(self):
  r=n2.Registry(self.c,create=True);g=json.loads((r.path/'genesis.json').read_text())
  payload={'state':'11','at':n2.tick()};row={'seq':1,'prev':None,'before':canonical_hash(g),'event':'DISPATCH','payload':payload,'after':canonical_hash(g)};row['hash']=canonical_hash(row)
  (r.path/'events.jsonl').write_text(json.dumps(row)+'\n')
  with self.assertRaises(Blocked):r.snapshot()

 def test_concurrent_owner_refuses_without_transport(self):
  r=n2.Registry(self.c,create=True)
  with r.lock(),patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('concurrent GET')) as dispatch:
   with self.assertRaises(Blocked):self.run_body()
   dispatch.assert_not_called()

 def test_cancel_does_not_wait_on_collector_owner_lock(self):
  r=n2.Registry(self.c,create=True)
  with r.lock():n2.request_cancel(self.c)
  self.assertTrue((r.path/'CANCEL_11').exists())
  with patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('cancelled dispatch')) as dispatch:
   with self.assertRaises(Blocked):self.run_body()
   dispatch.assert_not_called()
  self.assertEqual(self.state()['status'],'FAILED')

 def test_request_and_unit_clock_overrun_fail_fullcharge(self):
  r=n2.Registry(self.c,create=True)
  with r.lock():r.advance('RESERVE',url=self.c.source['url'],design=self.c.binding['design_sha256'],pid=os.getpid())
  start=r.snapshot()['attempts']['11']['started'];late=dict(start);late['wall']+=901;late['mono']+=901
  with patch.object(n2,'tick',return_value=late),self.assertRaises(Blocked):n2._guard(r,start)
  a={'wall':1.,'mono':1.};b={'wall':0.,'mono':2.}
  with self.assertRaises(Blocked):n2.delta(a,b)

 def test_real_process_death_pending_unknown_fullcharge_no_retry(self):
  ctx=multiprocessing.get_context('fork')
  def crash():
   original=n2.Registry.advance
   def boundary(reg,event,**kwargs):
    value=original(reg,event,**kwargs)
    if event=='DISPATCH':os._exit(27)
    return value
   with patch.object(n2.Registry,'advance',boundary):self.run_body()
  owner=ctx.Process(target=crash);owner.start();owner.join(8);self.assertEqual(owner.exitcode,27)
  r=n2.Registry(self.c);before=r.snapshot();self.assertEqual(before['attempts']['11']['status'],'PENDING');r.unknown();after=r.snapshot()
  self.assertEqual(before['attempts']['11']['reservation'],after['attempts']['11']['reservation'])
  with patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('retry after death')) as dispatch:
   with self.assertRaises(Blocked):self.run_body()
   dispatch.assert_not_called()

 def test_authority_scope_tamper_and_production_test_separation(self):
  live=deepcopy(self.env.live);rr=live['live_refs']['release'];r=json.loads((self.env.root/rr['path']).read_text());r['scope']['GETs']=2
  live['live_refs']['release']=self.env.record('bad',r)
  with self.assertRaises(Blocked):n2.admit_fixture(self.env.realm,live)
  with self.assertRaises(Blocked):n2.admit(self.env.live)

 def test_context_path_override_refuses(self):
  b=dict(self.c.binding);b['config']['raw_directory']='data/raw/ESCAPE'
  bad=n2.Context(self.c.realm,self.c.config_json,json.dumps(b),self.c.token)
  with patch.object(n2,'_exclusive_part',side_effect=AssertionError('raw')):
   with self.assertRaises(Blocked):n2.require(bad)

 def test_at_cap_unknown_EOF_no_extra_probe(self):
  base=self.body(mode=zipfile.ZIP_STORED);body=self.body(mode=zipfile.ZIP_STORED,extra_person_bytes=8388608-len(base));self.assertEqual(len(body),8388608)
  transport=n2._FixtureTransport(n2.fake_http(body,headers={}))
  with self.assertRaises(Blocked):n2._collect(self.c,transport)
  self.assertEqual(transport.offset,8388608);self.assertEqual(sum(transport.reads),8388608);self.assertEqual(self.state()['status'],'FAILED')

 def test_at_cap_known_completed_length_accepts_without_probe(self):
  base=self.body(mode=zipfile.ZIP_STORED);body=self.body(mode=zipfile.ZIP_STORED,extra_person_bytes=8388608-len(base));transport=n2._FixtureTransport(n2.fake_http(body,headers={'content-length':'8388608'}))
  receipt=n2._collect(self.c,transport);self.assertEqual(receipt['received_bytes'],8388608);self.assertEqual(sum(transport.reads),8388608)

 def test_network_overrun_after_open_closes_without_body_reads(self):
  original=n2._FixtureTransport.open;base=n2.tick();clock=dict(base)
  def now():return dict(clock)
  def late(transport,url,timeout):
   response=original(transport,url,timeout);clock['wall']+=181;clock['mono']+=181;return response
  with patch.object(n2,'tick',now),patch.object(n2._FixtureTransport,'open',late):
   with self.assertRaises(Blocked):self.run_body()
   self.assertEqual(self.state()['status'],'FAILED');self.assertEqual(self.state()['received'],0)

 def test_late_metadata_closure_withdraws_completed_attempt(self):
  original=n2.Registry.advance;base=n2.tick();clock=dict(base)
  def now():return dict(clock)
  def late(reg,event,**kwargs):
   result=original(reg,event,**kwargs)
   if event=='COMPLETE':clock['wall']+=301;clock['mono']+=301
   return result
  with patch.object(n2,'tick',now),patch.object(n2.Registry,'advance',late):
   with self.assertRaises(Blocked):self.run_body()
   self.assertEqual(self.state()['status'],'FAILED');self.assertEqual(self.state()['reservation']['processing_seconds'],300)

 def test_live_cancellation_records_full_allowance(self):
  original=n2._FixtureTransport.read;triggered=[]
  def cancel(response,count):
   if not triggered:n2.request_cancel(self.c);triggered.append(True)
   return original(response,count)
  with patch.object(n2._FixtureTransport,'read',cancel),self.assertRaises(Blocked):self.run_body()
  self.assertEqual(self.state()['status'],'FAILED');self.assertEqual(self.state()['reservation']['body_bytes'],8388608)

 def test_metadata_write_headroom_stops_before_dispatch(self):
  original=n2.Registry.storage
  def bound(reg,**kwargs):
   if kwargs.get('extra_core',0)==2*len(json.dumps(reg.c.binding).encode())+8192:raise Blocked('AUTHORED_METADATA_PROJECTION')
   return original(reg,**kwargs)
  with patch.object(n2.Registry,'storage',bound),patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('dispatch')) as dispatch:
   with self.assertRaises(Blocked):self.run_body()
   dispatch.assert_not_called()

 def test_public_adapter_TLS_identity_GET_read1_no_redirect(self):
  from civiclab.e02.n2a_http_v1 import PublicHTTP,NoRedirect
  class Raw:
   code=200;headers={'Content-Length':'1'}
   def geturl(self):return self_url
   def read1(self,n):read_counts.append(n);return b'X'
   def close(self):pass
  self_url=self.c.source['url'];read_counts=[];requests=[]
  class Opener:
   def open(self,request,timeout):requests.append((request,timeout));return Raw()
  with patch('urllib.request.build_opener',return_value=Opener()),patch('ssl.create_default_context',return_value='VERIFIED_TLS_CONTEXT') as tls:
   response=PublicHTTP().open(self_url,30);self.assertEqual(response.read(1),b'X');response.close();tls.assert_called_once()
  request,timeout=requests[0];self.assertEqual(request.get_method(),'GET');self.assertEqual(timeout,30);self.assertEqual(request.get_header('Accept-encoding'),'identity');self.assertEqual(read_counts,[1])
  self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://example.invalid/'))


 def test_delayed_first_reservation_cannot_restart_registry_clock(self):
  reg=n2.Registry(self.c,create=True);start=reg.snapshot()['created'];late={k:v+901 for k,v in start.items()}
  with patch.object(n2,'tick',return_value=late),patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('expired dispatch')) as dispatch:
   with self.assertRaises(Blocked):self.run_body()
   dispatch.assert_not_called();self.assertEqual(reg.snapshot()['attempts'],{})

 def test_late_read_persists_received_before_deadline_failure(self):
  original=n2._FixtureTransport.read;clock=n2.tick()
  def late(response,count):
   block=original(response,count);clock['wall']+=181;clock['mono']+=181;return block
  with patch.object(n2,'tick',side_effect=lambda:dict(clock)),patch.object(n2._FixtureTransport,'read',late):
   with self.assertRaises(Blocked):self.run_body()
   state=self.state();self.assertEqual(state['status'],'FAILED');self.assertEqual(state['received'],len(self.body()));self.assertEqual(state['written'],0)

 def test_cumulative_time_reservations_refuse_without_refund(self):
  reg=n2.Registry(self.c,create=True);old=reg.snapshot()
  # Pure transition probe with an authored lower native cap; no changed live policy.
  binding=deepcopy(self.c.binding);binding['config']['native_limits']['processing_seconds']=299
  fake=n2.Context(self.c.realm,self.c.config_json,json.dumps(binding),self.c.token);view=object.__new__(n2.Registry);view.c=fake
  with self.assertRaises(Blocked):view._transition(old,'RESERVE',{'state':'11','at':n2.tick(),'url':self.c.source['url'],'design':self.c.binding['design_sha256'],'pid':os.getpid()})
  self.assertEqual(reg.snapshot(),old)

 def test_changed_pinned_primitive_refuses_before_dispatch(self):
  p=self.env.root/'src/civiclab/common.py';p.write_bytes(p.read_bytes()+b'\n# AUTHORED_CHANGED_PIN\n')
  with patch.object(n2._FixtureTransport,'open',side_effect=AssertionError('changed pin dispatch')) as dispatch:
   with self.assertRaises(Blocked):self.run_body()
   dispatch.assert_not_called()
  self.assertFalse(self.c.raw_root.exists())


def retain_authored_evidence(root):
 """Retain fictional HTTP/control oracles; never production source authority."""
 root=Path(root).resolve();root.mkdir(exist_ok=False)
 summary={'label':'TEST_ONLY_AUTHORED_HTTP_NOT_CENSUS_OBSERVATIONS','realm':'TEST_ONLY','code_files':code_files(),'network_calls':0,'person_rows_read':0,'model_calls':0,'experimental_spend_usd':0,'cases':{}}
 for name in ('success','partial_failure','death_pending_unknown'):
  case=root/name;case.mkdir();env=Env(case/'realm');c=env.admit()
  body=archive_bytes(mode=zipfile.ZIP_STORED,extra_person_bytes=5000 if name=='partial_failure' else 0)
  (case/'AUTHORED_HTTP_BODY.zip').write_bytes(body)
  script={'label':'TEST_ONLY_AUTHORED_NO_REAL_HTTP','status':200,'headers':{'content-length':str(len(body)),'content-type':'application/zip'},'body_sha256':hashlib.sha256(body).hexdigest(),'body_bytes':len(body),'chunk':1024 if name=='partial_failure' else 65536,'fail_after':1024 if name=='partial_failure' else -1,'real_requests':0,'no_person_content_interpreted':True}
  save(case/'AUTHORED_HTTP_SCRIPT.json',script)
  fixture=n2.fake_http(body,headers=script['headers'],chunk=script['chunk'],fail_after=script['fail_after']);transport=n2._FixtureTransport(fixture)
  if name=='death_pending_unknown':
   # Kill a real local process after its durable DISPATCH intent, before fake open.
   def crash():
    original=n2.Registry.advance
    def boundary(reg,event,**kw):
     value=original(reg,event,**kw)
     if event=='DISPATCH':os._exit(27)
     return value
    with patch.object(n2.Registry,'advance',boundary):n2._collect(c,transport)
   child=multiprocessing.get_context('fork').Process(target=crash);child.start();child.join(8)
   if child.is_alive():child.terminate();child.join();raise RuntimeError('AUTHORED_CRASH_CHILD_TIMED_OUT')
   if child.exitcode!=27:raise RuntimeError('AUTHORED_CRASH_BOUNDARY_NOT_REACHED')
   reg=n2.Registry(c);pending=reg.snapshot();save(case/'PENDING_BEFORE_UNKNOWN.json',pending);reg.unknown()
   outcome={'child_exitcode':child.exitcode,'durable_dispatch_intents':1,'actual_fake_open_calls':0,'unknown_recovery':'Explicit UNKNOWN, no retry, allowance retained'}
  else:
   try:
    receipt=n2._collect(c,transport)
    if name!='success':raise AssertionError('expected partial refusal')
    outcome={'receipt_sha256':sha(c.core_root/c.state/'receipt.local.json')}
   except Blocked:
    if name=='success':raise
    outcome={'expected_stopped':True}
   outcome.update(actual_fake_open_calls=transport.calls,delivered_bytes=transport.offset,requested_read_sizes=transport.reads,response_closed=transport.closed)
  reg=n2.Registry(c);before=reg.snapshot();denied=n2._FixtureTransport(n2.fake_http(body))
  try:n2._collect(c,denied)
  except Blocked:pass
  else:raise AssertionError('same source retry was accepted')
  if denied.calls or reg.snapshot()!=before:raise AssertionError('retry changed history or called transport')
  outcome.update(status=before['attempts']['11']['status'],reservation=before['attempts']['11']['reservation'],history=before['history'],storage=reg.storage(),retry_fake_open_calls=denied.calls,raw_files={str(p.relative_to(c.raw_root)):p.stat().st_size for p in c.raw_root.rglob('*') if p.is_file()})
  save(case/'CONTROL_ORACLE.json',outcome);summary['cases'][name]=outcome
 summary['generation_overhead_note']='Authored payload/script, copied repository metadata and oracles are fixture generation overhead outside collector-owned raw/core/registry roots; stage storage below measures all owned roots including unexpected files, links and atomic headroom. No production data copied.'
 summary['files']={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(root.rglob('*')) if p.is_file()}
 save(root/'AUTHORED_EVIDENCE_INDEX.json',summary)
 return root/'AUTHORED_EVIDENCE_INDEX.json'
