import sys,os,signal,resource,unittest,json,ast
from pathlib import Path
from unittest.mock import patch,Mock
root=Path.cwd();sys.path[:0]=[str(root/'src'),str(root/'tests')]
def guard(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn'):raise RuntimeError('NO_NETWORK_OR_CHILD_PROCESS')
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=os.path.abspath(os.fsdecode(args[0]))
  if p.startswith(str(root/'data')) and not p.startswith(str(root/'data/processed/toolchains')+'/'):raise RuntimeError('NO_ACTUAL_DATA_OWNER_SOURCE')
  if '/.codex/' in p or p.endswith('/.env'):raise RuntimeError('NO_SECRET')
sys.addaudithook(guard);resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(30,30));signal.alarm(60)
import test_e02_f_wy_actual_bootstrap_v1 as m
class Adverse(unittest.TestCase):
 def test_success_return_and_snapshot_not_called(self):
  result=object();control=Mock()
  with patch.object(m.api,'run_authorized',return_value=result):self.assertIs(m._run_positive_with_diagnostics(None,control),result)
  control.snapshot.assert_not_called()
 def test_all_original_exception_types_and_snapshot_failure(self):
  for typ in (m.Blocked,RuntimeError,AssertionError,OSError,KeyboardInterrupt,SystemExit):
   with self.subTest(typ=typ):
    original=typ('PRIVATE PATH respondent token-secret');control=Mock();control.snapshot.side_effect=OSError('OTHER PRIVATE')
    with patch.object(m.api,'run_authorized',side_effect=original):
     try:m._run_positive_with_diagnostics(None,control)
     except BaseException as caught:self.assertIs(caught,original)
     else:self.fail('did not preserve original')
    self.assertEqual(len(original.__notes__),1);note=original.__notes__[0];self.assertLessEqual(len(note),2048);v=json.loads(note)
    self.assertEqual(v['error']['reason'],'REDACTED');self.assertEqual(v['state_error']['reason'],'REDACTED')
    for secret in ('PRIVATE','respondent','token-secret'):self.assertNotIn(secret,note)
 def test_note_failure_preserves_original(self):
  class BadNote(RuntimeError):
   def add_note(self,*args):raise ValueError('PRIVATE')
  original=BadNote('PRIVATE');control=Mock();control.snapshot.side_effect=RuntimeError('PRIVATE')
  with patch.object(m.api,'run_authorized',side_effect=original):
   with self.assertRaises(BadNote) as caught:m._run_positive_with_diagnostics(None,control)
  self.assertIs(caught.exception,original)
 def test_allowlisted_state_only_and_context_preserved(self):
  context=RuntimeError('PRIVATE');original=m.Blocked('rollback or discontinuous clocks');original.__context__=context
  control=Mock();control.snapshot.return_value={'shutdown':'CLOSED','failed':True,'stages':{k:{'status':'UNKNOWN' if i%2 else 'PENDING'} for i,k in enumerate(m.ORDER)},'raw':'PRIVATE'}
  with patch.object(m.api,'run_authorized',side_effect=original):
   with self.assertRaises(m.Blocked) as caught:m._run_positive_with_diagnostics(None,control)
  self.assertIs(caught.exception,original);self.assertIs(original.__context__,context)
  note=original.__notes__[0];value=json.loads(note);self.assertLessEqual(len(note),2048);self.assertNotIn('PRIVATE',note)
  self.assertEqual(value['error']['reason'],'rollback or discontinuous clocks');self.assertEqual(value['context']['reason'],'REDACTED')
suite=unittest.defaultTestLoader.loadTestsFromTestCase(Adverse)
r=unittest.TextTestRunner(verbosity=2).run(suite);signal.alarm(0);sys.exit(0 if r.wasSuccessful() and r.testsRun==4 else 1)
