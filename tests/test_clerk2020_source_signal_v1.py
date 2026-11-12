"""Bounded OS-signal controls on tiny authored programs, no research inputs."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest


class SourceSignalControls(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','POSIX source controller target')
    def test_wall_alarm_stops_an_authored_idle_child(self):
        result=subprocess.run([sys.executable,'-I','-B','-S','-c',
            'import signal,time;signal.setitimer(signal.ITIMER_REAL,.1);time.sleep(10)'],
            capture_output=True,timeout=3)
        self.assertEqual(result.returncode,-signal.SIGALRM)
        self.assertEqual(result.stdout,b'')

    @unittest.skipUnless(os.name=='posix','POSIX source controller target')
    def test_cpu_soft_limit_stops_authored_busy_child(self):
        result=subprocess.run([sys.executable,'-I','-B','-S','-c',
            'import resource;resource.setrlimit(resource.RLIMIT_CPU,(1,2))\nwhile True: pass'],
            capture_output=True,timeout=4)
        self.assertIn(result.returncode,{-signal.SIGXCPU,-signal.SIGKILL})
        self.assertEqual(result.stdout,b'')


if __name__=='__main__':unittest.main()
