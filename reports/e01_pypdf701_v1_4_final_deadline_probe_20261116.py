"""Independent wholly authored final-completion deadline counterexample."""
import runpy,sys,unittest,json
from datetime import timedelta

def guard(event,args):
 if event in ('os.kill','os.killpg'): raise AssertionError('AUDIT_NO_ACTUAL_PROCESS_SIGNAL')
sys.addaudithook(guard)
ns=runpy.run_path('tests/test_e01_pypdf701_acquisition_v1_4.py',run_name='audit_v14_fixtures')
class FinalDeadlineProbe(unittest.TestCase):
 def test_expiry_after_hashlock_write(self):
  fixture=ns['FreshMetadataTests']();fixture.setUp();self.addCleanup(fixture.doCleanups)
  collector=fixture.collector();original=collector.write
  def write(name,body,control=True):
   result=original(name,body,control)
   if name=='hashlock.json':fixture.now+=timedelta(seconds=121)
   return result
  collector.write=write
  result=collector.run()
  print('AUDIT_PROBE '+json.dumps({'status':result['status'],'terminal_status':fixture.terminal()['status'],'observed_utc':fixture.now.isoformat(),'deadline':collector.budget.deadline.isoformat(),'last_checked_utc':collector.budget.prior_utc.isoformat(),'GETs':len(fixture.transport.calls)}))
  self.assertEqual(result['status'],'ACQUISITION_COMPLETE_NOT_INSTALL_OR_QUALIFICATION')
ns['old'].guarded_test_main()
