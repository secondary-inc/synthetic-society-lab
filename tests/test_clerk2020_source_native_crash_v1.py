"""SIGKILL/restart controls on authored campaign trees; no actual PDF stack."""
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

from civiclab.e01 import clerk2020_native_campaign_v1 as n

REPO=Path(__file__).resolve().parents[1]
SCRIPT=r'''
import json,os,signal,sys
from pathlib import Path
sys.path[:0]=[str(Path(sys.argv[2])/'src'),str(Path(sys.argv[2])/'tests')]
import test_clerk2020_source_job_v1 as fixtures
root=Path(sys.argv[1]).resolve();phase=sys.argv[3];target=sys.argv[4]
class FixedTemp:
    name=str(root)
    def cleanup(self):pass
fixtures.tempfile.TemporaryDirectory=lambda *a,**k:FixedTemp()
f=fixtures.SourceJobTests();f.setUp()
j=fixtures.j;n=fixtures.n
if phase=='BOOT':raw,h=f.packet()
else:
    b=f.boot()
    assert b['status']=='BOOT_PREPARED_NO_SOURCE'
    raw,h=f.packet('EXEC',b['prepared_ref'],b['completed_anchor_sha256'])
print(json.dumps({'label':'MOCK_AUTHORED_NO_REAL_SOURCE','issued':j.decode(raw)['issued']}),flush=True)
original=n.FixedStore.__init__
def initialize(store,*args,**kwargs):
    original(store,*args,**kwargs)
    def crash(event):
        if event==target:
            assert 'pypdf' not in sys.modules and 'cryptography' not in sys.modules
            os.kill(os.getpid(),signal.SIGKILL)
    store.crash=crash
n.FixedStore.__init__=initialize
with fixtures.patch.object(j,'dispatch',side_effect=f.fake_dispatch):
    result=(j.run_boot if phase=='BOOT' else j.run_exec)(root,raw,h)
raise RuntimeError('AUTHORED_CRASH_TARGET_NOT_REACHED')
'''


class NativeProcessCrashTests(unittest.TestCase):
    def test_native_death_preserves_ordinal_and_forbids_restart(self):
        cases=[('BOOT','boot_reservation.before'),('BOOT','genesis.after'),
               ('BOOT','prepared_metadata.after'),('EXEC','source_receipt_0.after'),
               ('EXEC','writer_ack.after'),('EXEC','caller.before')]
        for phase,target in cases:
            with self.subTest(phase=phase,target=target),tempfile.TemporaryDirectory() as folder:
                root=Path(folder).resolve()
                result=subprocess.run([sys.executable,'-I','-B','-S','-c',SCRIPT,str(root),str(REPO),phase,target],
                                      capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,-signal.SIGKILL,result.stderr)
                issued=json.loads(result.stdout)['issued']
                store=n.FixedStore(root);self.assertTrue(store.exists('boot_issued' if phase=='BOOT' else 'exec_issued'))
                reg=n.FixedRegistrar(store,issued['binding']['source_set_sha256'])
                raw=n.canonical(issued)
                with self.assertRaises(FileExistsError):reg.consume(phase,raw,n.sha(raw))
                if target=='boot_reservation.before':
                    self.assertFalse(store.exists('boot_reservation'))
                    self.assertFalse(store.exists('source_index'))


if __name__=='__main__':unittest.main()
