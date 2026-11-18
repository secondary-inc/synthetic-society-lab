"""Independent inert CI controls; no child or research module executes."""
class IndependentAllocationControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.policy,_=c.load_allocation(ROOT);cls.rows=c.ordinary_modules(ROOT);cls.base=c.plan(ROOT)
 def specs(self):return c.allocation_plans(ROOT,allocation=self.policy,rows=self.rows,base=self.base)
 def test_missing_nonheavy_original_refuses(self):
  heavy={r['module_ref']['path'] for r in self.policy['lanes'] if r['type']=='HEAVY'}
  filename=next(r['path'] for r in self.rows if r['path'] not in heavy and Path(r['path']).name in self.policy['baseline_module_names'])
  with self.assertRaisesRegex(c.IsolationError,'MODULE_MISSING_OR_DUPLICATE'):c.allocation_plans(ROOT,allocation=self.policy,rows=[r for r in self.rows if r['path']!=filename],base=self.base)
 def test_bad_job_clocks_refuse_before_any_dispatch(self):
  from copy import deepcopy
  for clock in (float('nan'),float('inf'),-1,1001):
   spec=deepcopy(self.specs()['fast-0']);spec['jobs']=spec['jobs'][:1];calls=[]
   with self.subTest(clock=clock),tempfile.TemporaryDirectory() as parent,mock.patch.object(c,'allocation_plan',return_value=spec),mock.patch.object(c.time,'monotonic',return_value=1000):
    with self.assertRaisesRegex(c.IsolationError,'ALLOCATION_JOB_CLOCK'):c.run_parent(Path(parent)/'one',allocation_v2_lane='fast-0',job_start_monotonic=clock,run_process=lambda *a:calls.append(a))
    self.assertEqual(calls,[])
 def test_exhausted_setup_has_results_but_no_reservations_or_dispatch(self):
  from copy import deepcopy
  spec=deepcopy(self.specs()['fast-0']);spec['jobs']=spec['jobs'][:2];calls=[]
  with tempfile.TemporaryDirectory() as parent,mock.patch.object(c,'allocation_plan',return_value=spec),mock.patch.object(c.time,'monotonic',return_value=2000):
   out=Path(parent)/'one';result=c.run_parent(out,allocation_v2_lane='fast-0',job_start_monotonic=23,run_process=lambda *a:calls.append(a))
   self.assertEqual(result['status'],'FAIL');self.assertEqual(calls,[]);self.assertEqual(list(out.glob('*-RESERVED.json')),[])
   self.assertEqual([x['reason'] for x in result['results']],['COORDINATOR_WALL_LIMIT']*2)
 def test_remaining_deadline_is_rechecked_before_second_job(self):
  from copy import deepcopy
  spec=deepcopy(self.specs()['fast-0']);spec['jobs']=[j for j in spec['jobs'] if j['phase']=='ordinary'][:2];now=[1000];walls=[]
  def fake(command,env,job,directory):
   walls.append(job['wall_seconds']);receipt=valid_receipt(job,spec,command[-1]);path=directory/'inert.stdout';c.save_new(path,(c.MARKER+json.dumps(receipt)).encode());now[0]=2100
   return {'stdout':str(path),'returncode':0,'reason':None,'reaped':True}
  with tempfile.TemporaryDirectory() as parent,mock.patch.object(c,'allocation_plan',return_value=spec),mock.patch.object(c.time,'monotonic',side_effect=lambda:now[0]):
   result=c.run_parent(Path(parent)/'one',allocation_v2_lane='fast-0',job_start_monotonic=100,run_process=fake)
  self.assertEqual(walls,[1077]);self.assertEqual([x['status'] for x in result['results']],['PASS','ERROR']);self.assertEqual(result['status'],'FAIL')
 def test_only_four_original_profile_modules_get_no_site(self):
  jobs=[j for s in self.specs().values() for j in s['jobs']];ordinary=[j for j in jobs if j['phase']=='ordinary']
  self.assertEqual({j['test_module'] for j in ordinary if '-S' in c.child_isolation_flags(j)},set(c.NO_SITE_PROFILES));self.assertEqual(len(c.NO_SITE_PROFILES),4)
  self.assertTrue(all('-S' in c.child_isolation_flags(j) for j in jobs if j['phase']!='ordinary'))
 def test_portable_mime_origin_cases_cannot_be_relabelled_not_run(self):
  filename='test_e01_pypdf701_install_v1_5.py';rule=c.HOST_CASE_RULES[filename]
  for name in ('test_unknown_origin_refuses_before_initialization','test_unknown_spec_origin_refuses_before_initialization','test_alias_origin_refuses_before_initialization'):
   job={'id':'ordinary-inert','phase':'ordinary','test_module':filename,'source_ref':rule['test_ref'],'declared_local_cases':['ProductionMimeTests.'+name]};receipt=valid_receipt(job,{})
   qual={'status':'NOT_RUN','reasons':['FROZEN_CANDIDATE_REQUIRES_DARWIN'],'test_ref':rule['test_ref'],'contract_ref':rule['contract_ref'],'gate':rule['gate']}
   receipt.update(tests_run=0,started_case_ids=[],completed_case_ids=[],outcomes=[],not_run_cases=[{'case_id':receipt['planned_case_ids'][0],'qualification':qual}])
   with self.subTest(name=name),self.assertRaisesRegex(c.IsolationError,'HOST_DISPOSITION_BINDING'):c.validate_coverage(receipt,job,{})
 def test_duplicate_json_keys_refuse_even_with_inert_expected_digest(self):
  raw=(ROOT/c.ALLOCATION_PATH).read_bytes();changed=raw.replace(b'{',b'{"version":2,',1)
  with tempfile.TemporaryDirectory() as parent:
   root=Path(parent);(root/'configs').mkdir();(root/c.ALLOCATION_PATH).write_bytes(changed)
   with mock.patch.object(c,'ALLOCATION_SHA256',c.sha(changed)),self.assertRaisesRegex(c.IsolationError,'DUPLICATE_JSON_KEY'):c.load_allocation(root)
 def test_empty_helper_is_still_covered_and_quarantine_not_active(self):
  new={'path':'tests/test_authored_empty_helper.py','bytes':10,'sha256':'f'*64,'declared_local_cases':[]}
  plans=c.allocation_plans(ROOT,allocation=self.policy,rows=self.rows+[new],base=self.base);jobs=[j for s in plans.values() for j in s['jobs']]
  self.assertEqual(sum(j.get('source_ref')=={k:new[k] for k in ('path','bytes','sha256')} for j in jobs),1)
  self.assertNotIn('test_wrapper_slot46_v3.py',{Path(r['path']).name for r in self.rows});self.assertFalse((ROOT/'tests/test_wrapper_slot46_v3.py').exists())
