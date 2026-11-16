"""Authored concurrency and existing23checks; no sockets/pip/native/process calls."""
import runpy,sys,threading,unittest,json
from collections import Counter

def guard(event,args):
 if event in ('os.kill','os.killpg'):raise AssertionError('AUDIT_NO_ACTUAL_PROCESS_SIGNAL')
sys.addaudithook(guard)
ns=runpy.run_path('tests/test_e01_p2_refusal_observability_candidate_v3_20261116.py',run_name='audit_frozen_observer_v3')
RefusalObservabilityTests=ns['RefusalObservabilityTests']
c=ns['c']
class IndependentThreadChecks(unittest.TestCase):
 def test_thread_local_event_context_isolated_and_restored(self):
  cases=[('socket.__new__','SOCKET_CONSTRUCT'),('socket.bind','SOCKET_BIND'),('socket.connect','SOCKET_CONNECT'),('socket.getaddrinfo','SOCKET_RESOLVE'),('socket.gethostname','SOCKET_METADATA'),('socket.future_unknown','SOCKET_UNKNOWN')]
  barrier=threading.Barrier(len(cases));errors=[];restored=[]
  class Denied(RuntimeError):pass
  class AuthoredBase:
   def __init__(self):self.violations=0;self.lock=threading.Lock()
   def audit(self,event,args):barrier.wait(timeout=3);self.refuse('GUEST_NETWORK_HELPER_OR_CTYPES_DENIED')
   def refuse(self,reason):
    with self.lock:self.violations+=1
    raise Denied(reason)
  policy=c.recording_policy_class(AuthoredBase)()
  def call(event):
   try:policy.audit(event,('MOCK_PRIVATE_ARGUMENT',))
   except Denied:restored.append(policy._refusal_context.operation)
   except BaseException as error:errors.append(type(error).__name__)
  threads=[threading.Thread(target=call,args=(event,)) for event,_ in cases]
  for thread in threads:thread.start()
  for thread in threads:thread.join(timeout=5)
  self.assertFalse(any(thread.is_alive() for thread in threads));self.assertEqual(errors,[])
  value=json.loads(policy.refusal_journal.packed());self.assertEqual(policy.violations,6)
  self.assertEqual(Counter(e['operation'] for e in value['events']),Counter(label for _,label in cases))
  self.assertEqual(restored,['UNKNOWN']*6);self.assertNotIn('MOCK_PRIVATE_ARGUMENT',json.dumps(value))
 def test_journal_counts_are_locked_and_bounded_with_concurrent_writers(self):
  journal=c.RefusalJournal();errors=[]
  def write():
   try:
    for _ in range(500):journal.record('GUEST_NETWORK_HELPER_OR_CTYPES_DENIED','SOCKET_CONSTRUCT')
   except BaseException as error:errors.append(type(error).__name__)
  threads=[threading.Thread(target=write) for _ in range(8)]
  for thread in threads:thread.start()
  for thread in threads:thread.join(timeout=5)
  self.assertFalse(any(thread.is_alive() for thread in threads));self.assertEqual(errors,[])
  raw=journal.packed();value=json.loads(raw)
  self.assertEqual(value['total_events'],4000);self.assertEqual(value['dropped_events'],3984)
  self.assertEqual(len(value['events']),16);self.assertLessEqual(len(raw),4096)
ns['t'].g.old.guarded_test_main()
