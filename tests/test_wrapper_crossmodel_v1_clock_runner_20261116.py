"""Fast clock/output/stop effects only; no child, financial scope or model run."""
import importlib.util
import io
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import unittest
import tempfile
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('authored_dual_clock_runner',ROOT/'scripts/run_wrapper_crossmodel_v1_authored_utc_20261116.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Pipe:
    def __init__(self):self.closed=False
    def fileno(self):return 99
    def close(self):self.closed=True
class Process:
    def __init__(self):self.pid=424242;self.stdout=Pipe();self.returncode=None;self.waits=[]
    def poll(self):return self.returncode
    def wait(self,timeout):
        self.waits.append(timeout)
        if self.returncode is None:self.returncode=0
        return self.returncode
class Selector:
    def __init__(self,callback=None):self.open=True;self.pipe=None;self.callback=callback
    def register(self,pipe,_):self.pipe=pipe
    def get_map(self):return {99:1} if self.open else {}
    def select(self,_):
        if self.callback:self.callback()
        return [(SimpleNamespace(fileobj=self.pipe),1)]
    def unregister(self,_):self.open=False
    def close(self):self.open=False

class ClockRunnerTests(unittest.TestCase):
    def clocks(self):
        values=[0.,1000.];budget=m.ClockBudget(mono=lambda:values[0],utc=lambda:values[1]);return values,budget
    def test_coherent_clock_advances_without_freezing_elapsed(self):
        values,b=self.clocks();values[:]=[4.,1004.]
        self.assertEqual(b.check(),{'monotonic_seconds':4.,'UTC_seconds':4.})
    def test_forward_utc_jump_and_utc_deadline_stop(self):
        for advance,reason in ((3,'CLOCK_DISCONTINUITY'),(3600,'DUAL_CLOCK_DEADLINE')):
            with self.subTest(advance=advance):
                values,b=self.clocks();values[1]+=advance
                with self.assertRaisesRegex(m.Stop,reason):b.check()
    def test_utc_monotonic_rollback_and_nonfinite_refuse(self):
        for change in ((-1.,1000.),(0.,999.),(float('nan'),1000.),(0.,float('inf'))):
            values,b=self.clocks();values[:]=change
            with self.subTest(change=change),self.assertRaises(m.Stop):b.check()
        with self.assertRaisesRegex(m.Stop,'CLOCK_NONFINITE'):m.ClockBudget(mono=lambda:float('nan'),utc=lambda:1000.)
    def test_monotonic_deadline_remains_active(self):
        values,b=self.clocks();values[:]=[3600.,4600.]
        with self.assertRaisesRegex(m.Stop,'DUAL_CLOCK_DEADLINE'):b.check()
    def test_output_cap_kills_and_reaps_before_log_effect(self):
        values,b=self.clocks();b.output_cap=1;p=Process();log=io.BytesIO();calls=[]
        def kill(pid,sig):calls.append((pid,sig));p.returncode=-9
        result=m.capture(p,log,b,selector_factory=Selector,read=lambda *_:b'xx',killpg=kill)
        self.assertEqual(result['stop_reason'],'OUTPUT_CAP');self.assertEqual(log.getvalue(),b'')
        self.assertEqual(calls,[(p.pid,m.signal.SIGKILL)]);self.assertIn(5,p.waits);self.assertTrue(p.stdout.closed)
    def test_clock_jump_during_select_stops_before_read(self):
        values,b=self.clocks();p=Process();log=io.BytesIO();read=Mock(side_effect=AssertionError('read after clock stop'))
        def jump():values[1]=1003.
        def kill(*_):p.returncode=-9
        result=m.capture(p,log,b,selector_factory=lambda:Selector(jump),read=read,killpg=kill)
        self.assertEqual(result['stop_reason'],'CLOCK_DISCONTINUITY');read.assert_not_called();self.assertEqual(log.getvalue(),b'')
    def test_normal_capture_retains_bytes_and_exit_zero(self):
        values,b=self.clocks();p=Process();log=io.BytesIO();chunks=iter((b'ab',b''));kill=Mock(side_effect=AssertionError('unexpected signal'))
        result=m.capture(p,log,b,selector_factory=Selector,read=lambda *_:next(chunks),killpg=kill)
        self.assertEqual(result,{'exit_code':0,'stop_reason':None,'captured_bytes':2})
        self.assertEqual(log.getvalue(),b'ab');kill.assert_not_called()
    def test_unknown_reap_is_not_claimed_closed(self):
        p=Process();p.wait=Mock(side_effect=subprocess.TimeoutExpired('MOCK',5));kill=Mock()
        with self.assertRaisesRegex(m.Stop,'CHILD_REAP_UNKNOWN'):m.stop_child(p,kill)
        kill.assert_called_once_with(p.pid,m.signal.SIGKILL)

    def main_receipt(self,final):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fixture=root/'fixture';fixture.mkdir()
            raw=b'{}';(fixture/'index.json').write_bytes(raw)
            values=[0.,1000.];budget=m.ClockBudget(mono=lambda:values[0],utc=lambda:values[1])
            def capture(process,log,_):
                log.write(b'Ran 21 tests in 0.1s\n\nOK\n');process.returncode=0
                values[:]=[.1,1000.1];budget.check();values[:]=final
                return {'exit_code':0,'stop_reason':None,'captured_bytes':28}
            digest=hashlib.sha256(b'{}').hexdigest()
            with patch.multiple(m,ROOT=root,BASE='run',FIXTURE='fixture',FIXTURE_SHA=digest), \
                 patch.object(m,'contract',return_value={}),patch.object(m,'ClockBudget',return_value=budget), \
                 patch.object(m,'capture',side_effect=capture),patch.object(m.subprocess,'Popen',return_value=Process()), \
                 patch.object(m,'preserve_partial',return_value={'status':'MOCK_PARTIAL_RETAINED'}) as retained, \
                 patch('sys.argv',['runner','--reviewed-contract-sha256',digest]),patch('builtins.print'):
                code=m.main()
            return code,json.loads((root/'run/RECEIPT.json').read_text()),retained.call_count

    def test_main_final_receipt_rejects_post_capture_jump(self):
        code,result,retained=self.main_receipt([.1,1100.1])
        self.assertEqual(code,1);self.assertEqual(result['status'],'FAILED')
        self.assertEqual(result['final_clock_error'],'CLOCK_DISCONTINUITY');self.assertEqual(retained,1)
    def test_main_final_receipt_rejects_post_capture_rollback(self):
        for final in ((.05,1000.1),(.1,1000.05)):
            with self.subTest(final=final):
                code,result,_=self.main_receipt(final)
                self.assertEqual(code,1);self.assertEqual(result['final_clock_error'],'CLOCK_ROLLBACK')
    def test_main_final_receipt_rejects_post_capture_nonfinite(self):
        for final in ((float('nan'),1000.1),(.1,float('inf'))):
            with self.subTest(final=final):
                code,result,_=self.main_receipt(final)
                self.assertEqual(code,1);self.assertEqual(result['final_clock_error'],'CLOCK_NONFINITE')
                self.assertIsNone(result['UTC_elapsed']);self.assertIsNone(result['monotonic_elapsed'])
    def test_main_final_receipt_rejects_post_capture_deadline(self):
        for final in ((3600.,4600.),(.1,4600.),(3600.,1000.1)):
            with self.subTest(final=final):
                code,result,_=self.main_receipt(final)
                self.assertEqual(code,1);self.assertEqual(result['final_clock_error'],'DUAL_CLOCK_DEADLINE')
    def test_main_final_receipt_accepts_coherent_validated_sample(self):
        code,result,retained=self.main_receipt([.2,1000.2])
        self.assertEqual(code,0);self.assertEqual(result['status'],'PASS')
        self.assertTrue(result['final_clock_validated']);self.assertEqual(retained,0)

if __name__=='__main__':unittest.main()
