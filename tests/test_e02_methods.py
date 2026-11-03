from pathlib import Path
import json
import tempfile
import unittest
from civiclab.common import sha256_file
from civiclab.e02.methods import verify_analysis_lock


class MethodsTests(unittest.TestCase):
    def test_freeze_detects_changes_but_does_not_claim_registration_or_spend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'configs').mkdir()
            plan=root/'configs/plan.json';plan.write_text('{"primary":"fixed"}')
            lock=root/'configs/e02_analysis_lock.json'
            lock.write_text(json.dumps({'schema_version':1,'files':{'configs/plan.json':sha256_file(plan)}}))
            result=verify_analysis_lock(root)
            self.assertEqual(result['status'],'PASS_DEFINITION_INTEGRITY')
            self.assertEqual(result['external_preregistration'],'NOT_RUN')
            self.assertIn('BLOCKED',result['paid_execution'])
            plan.write_text('{"primary":"changed after freeze"}')
            self.assertEqual(verify_analysis_lock(root)['status'],'BLOCKED')

    def test_empty_or_escaping_locks_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'configs').mkdir()
            path=root/'configs/e02_analysis_lock.json'
            for files in ({},{'../../private':'x'}):
                path.write_text(json.dumps({'schema_version':1,'files':files}))
                with self.assertRaises(ValueError):verify_analysis_lock(root)
