from pathlib import Path
import json
import tempfile
import unittest
from civiclab.common import atomic_json,sha256_file
from civiclab.orchestration import completion_status


class CompletionTests(unittest.TestCase):
    def test_empty_or_duplicate_contract_cannot_be_complete(self):
        for requirements in ([],[{'id':'DUP'},{'id':'DUP'}]):
            atomic_json(self.root/'configs/completion_contract.json',{'requirements':requirements})
            with self.assertRaises(ValueError):completion_status(self.root)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        atomic_json(self.root/'configs/completion_contract.json',{'requirements':[
            {'id':'TEST','description':'A required scientific result','clause':2,'gate':'G6'}]})
        self.code=self.root/'src/component.py';self.code.parent.mkdir();self.code.write_text('version1')
        self.evidence=self.root/'reports/AUDIT_TEST.json';atomic_json(self.evidence,{'verified':True})

    def receipt(self,**kw):
        audit={'schema_version':1,'auditor_role':'independent_auditor','audited_at_utc':'2026-11-03T00:00:00+00:00',
               'code_files':{'src/component.py':sha256_file(self.code)},'requirements':[
                   {'id':'TEST','status':'PASS','reason':'Independent observed evidence',
                    'evidence':[{'path':'reports/AUDIT_TEST.json','sha256':sha256_file(self.evidence)}]}]}
        audit.update(kw);atomic_json(self.root/'reports/AUDIT_COMPLETION_TEST.json',audit)

    def test_missing_or_unreviewed_work_never_completes(self):
        self.assertEqual(completion_status(self.root)['status'],'INCOMPLETE')
        self.receipt(auditor_role='implementer')
        self.assertEqual(completion_status(self.root)['status'],'INCOMPLETE')

    def test_current_independent_evidence_required(self):
        self.receipt();self.assertEqual(completion_status(self.root)['status'],'COMPLETE')
        self.code.write_text('version2')
        result=completion_status(self.root)
        self.assertEqual(result['status'],'INCOMPLETE')
        self.assertIn('stale',result['rejected_audits'][0]['reason'])

    def test_altered_or_escaped_evidence_rejected(self):
        self.receipt();self.evidence.write_text('{}')
        self.assertEqual(completion_status(self.root)['status'],'INCOMPLETE')
        self.receipt(code_files={'../../outside':'a'*64})
        self.assertEqual(completion_status(self.root)['status'],'INCOMPLETE')

    def test_latest_audit_wins_regardless_of_filename(self):
        self.receipt(audited_at_utc='2026-11-01T00:00:00+00:00')
        old=self.root/'reports/AUDIT_COMPLETION_TEST.json'
        old.rename(old.with_name('AUDIT_COMPLETION_Z_OLD.json'))
        self.receipt(audited_at_utc='2026-11-02T00:00:00+00:00',requirements=[
            {'id':'TEST','status':'BLOCKED','reason':'New finding invalidates earlier pass','evidence':[]}])
        self.assertEqual(completion_status(self.root)['requirements'][0]['status'],'BLOCKED')
