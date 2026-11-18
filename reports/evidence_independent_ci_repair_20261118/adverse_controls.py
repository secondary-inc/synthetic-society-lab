"""Independent pure CI receipt/discovery counterexamples; no full-suite run."""
from pathlib import Path
import sys,os,resource,signal,unittest,tempfile,importlib.util,json,time
resource.setrlimit(resource.RLIMIT_CPU,(899,900));signal.alarm(900);root=Path.cwd();t=time.monotonic()
spec=importlib.util.spec_from_file_location('independent_ci_models',root/'tests/test_ci_collection_isolation_v1.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);c=old.c
class Independent(unittest.TestCase):
 def test_nested_discoverable_module_is_not_silently_omitted(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp).resolve();(base/'tests/pkg').mkdir(parents=True);(base/'tests/pkg/__init__.py').write_text('')
   body='import unittest\nclass Local(unittest.TestCase):\n def test_one(self):pass\n'
   (base/'tests/test_flat.py').write_text(body);(base/'tests/pkg/test_nested.py').write_text(body)
   rows=c.ordinary_modules(base)
   self.assertIn('tests/pkg/test_nested.py',[r['path'] for r in rows],'Original unittest discovery supports nested test packages; new module manifest silently loses them')
 def test_skip_outcome_without_skip_record_is_rejected(self):
  job={'id':'ordinary','phase':'ordinary'};receipt=old.valid_receipt(job,{})
  receipt['outcomes'][0]['status']='SKIP'
  self.assertEqual(receipt['skips'],[])
  with self.assertRaises(c.IsolationError):c.validate_coverage(receipt,job,{})
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(old),unittest.defaultTestLoader.loadTestsFromTestCase(Independent)])
r=unittest.TextTestRunner(verbosity=1).run(suite);print('INDEPENDENT_CI_REPAIR='+json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'wall_seconds':time.monotonic()-t,'full_suite_runs':0,'real_model_calls':0}));raise SystemExit(0 if r.wasSuccessful() else 1)
