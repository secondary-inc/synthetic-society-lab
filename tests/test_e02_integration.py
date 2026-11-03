from pathlib import Path
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
from civiclab.common import sha256_file
from civiclab.e02.experiment import run_pilot


ROOT=Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'configs').mkdir()
        for name in ('e02_instrument.json','e02_demo_stimuli.json'):
            shutil.copyfile(ROOT/'configs'/name,self.root/'configs'/name)
        self.fit={'kind':'DEMO_POPULATION_FOR_TEST_ONLY','cells':[
            {'region':str(i),'age_bin':'25-44','education':'BA_PLUS','party':'D' if i%2 else 'R',
             'race':'OTHER_NH','income':'MID','weight':.25} for i in range(1,5)]}

    def test_complete_pilot_replay_dispatch_order_and_artifact_integrity(self):
        a=run_pilot(self.root,self.fit)
        b=run_pilot(self.root,self.fit)
        summaries=[json.loads((p/'summary.json').read_text()) for p in (a,b)]
        self.assertEqual(summaries[0]['reproducibility_hash'],summaries[1]['reproducibility_hash'])
        self.assertEqual(summaries[0]['units'],180)
        self.assertEqual(summaries[0]['paid_calls'],0)
        for name,digest in json.loads((a/'checksums.json').read_text()).items():
            self.assertEqual(sha256_file(a/name),digest)
        jobs=json.loads((a/'assignments.json').read_text())
        from civiclab.common import canonical_hash
        job_order={canonical_hash(j):j['execution_order'] for j in jobs}
        events=[json.loads(line) for line in (a/'events.jsonl').read_text().splitlines()]
        self.assertEqual([job_order[e['job_id']] for e in events if e['event']=='unit_completed'],list(range(180)))

    def test_failed_job_is_not_silently_replayed_on_resume(self):
        with patch('civiclab.e02.experiment.MockSurvey.respond',side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):run_pilot(self.root,self.fit)
        path=next((self.root/'data/processed/runs').iterdir())
        with self.assertRaisesRegex(ValueError,'reconciliation'):
            run_pilot(self.root,self.fit,resume=path)
