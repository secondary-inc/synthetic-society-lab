import json
import subprocess
import sys
import tempfile
import unittest
from civiclab.e01.isolation import worker_environment


class IsolationTests(unittest.TestCase):
    def test_predictor_environment_excludes_credentials(self):
        self.assertEqual(set(worker_environment()),{'PATH','PYTHONHASHSEED','PYTHONNOUSERSITE','PYTHONPATH'})

    def test_worker_runtime_denies_outcome_reads_and_network(self):
        program='''
import json,socket
from civiclab.e01.isolation import deny_external_io
deny_external_io()
results=[]
for operation in (lambda: open('/etc/hosts'), lambda: socket.socket()):
    try: operation();results.append('ALLOWED')
    except PermissionError: results.append('DENIED')
print(json.dumps(results))
'''
        with tempfile.TemporaryDirectory() as cwd:
            result=subprocess.run([sys.executable,'-c',program],capture_output=True,text=True,
                                  check=True,cwd=cwd,env=worker_environment(),timeout=10)
        self.assertEqual(json.loads(result.stdout),['DENIED','DENIED'])
