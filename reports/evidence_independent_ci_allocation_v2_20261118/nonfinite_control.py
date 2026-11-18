from pathlib import Path
source=Path.cwd()/'tests/test_ci_collection_isolation_v1.py';raw=source.read_text();needle="if __name__=='__main__':raise SystemExit(bounded_main())"
extra='''
class CorrectedNonfiniteClockControl(unittest.TestCase):
 def test_exact_canonical_serializer_refusal_precedes_dispatch(self):
  traces=[]
  for label,value in (('NaN',float('nan')),('Inf',float('inf'))):
   spec={'jobs':[{'id':'inert-only','phase':'ordinary','wall_seconds':120,'group':'ordinary'}],'shard':{'budget_seconds':1980},'allocation':{}}
   calls=[]
   with self.subTest(label=label),tempfile.TemporaryDirectory() as parent,mock.patch.object(c,'allocation_plan',return_value=spec),mock.patch.object(c.time,'monotonic',return_value=1000):
    out=Path(parent)/'one'
    try:c.run_parent(out,allocation_v2_lane='fast-0',job_start_monotonic=value,run_process=lambda *a:calls.append(a))
    except ValueError as error:
     self.assertIs(type(error),ValueError);tb=error.__traceback__;names=[]
     while tb is not None:names.append(tb.tb_frame.f_code.co_name);tb=tb.tb_next
     self.assertEqual(names[-6:],['run_parent','save_new','packed','dumps','encode','iterencode']);traces.append({'input':label,'exact_exception_type':'ValueError','safe_frame_names':names[-6:]})
    else:self.fail('nonfinite clock admitted')
    self.assertEqual(calls,[]);self.assertFalse((out/'PLAN.json').exists());self.assertEqual(list(out.glob('*-RESERVED.json')),[])
  print(json.dumps({'kind':'INDEPENDENT_NONFINITE_REFUSAL_ONLY','status':'PASS','traces':traces,'actual_dispatches':0,'source_change':False},sort_keys=True))
'''
assert raw.count(needle)==1;raw=raw.replace(needle,extra+'\n'+needle)
old='program=unittest.main(verbosity=2,exit=False)';assert raw.count(old)==1
raw=raw.replace(old,"program=unittest.main(defaultTest='CorrectedNonfiniteClockControl',verbosity=2,exit=False)\n        assert program.result.testsRun==1, 'EXACT_ONE_CORRECTED_CONTROL_REQUIRED'")
raw=raw.replace('resource.setrlimit(resource.RLIMIT_CPU,(119,120))','resource.setrlimit(resource.RLIMIT_CPU,(29,30))').replace('signal.setitimer(signal.ITIMER_REAL,120)','signal.setitimer(signal.ITIMER_REAL,30)')
__file__=str(source);exec(compile(raw,str(source),'exec'),globals())
