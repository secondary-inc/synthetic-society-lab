import tempfile
import unittest
from pathlib import Path
from civiclab.jobs import JobQueue
from civiclab.gdelt import ingest
import json


class CheckpointTests(unittest.TestCase):
    def test_job_execution_follows_recorded_randomized_order(self):
        with tempfile.TemporaryDirectory() as temp:
            q=JobQueue(Path(temp)/'jobs.sqlite')
            for n in (2,0,1):q.add({'execution_order':n})
            self.assertEqual([q.claim()[1]['execution_order'] for _ in range(3)],[0,1,2])

    def test_idempotent_resume_and_quarantine(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'jobs.sqlite'
            queue = JobQueue(path)
            identity = queue.add({'profile': 1, 'seed': 3})
            self.assertEqual(queue.add({'seed': 3, 'profile': 1}), identity)
            self.assertEqual(len(queue.snapshot()), 1)
            claimed = queue.claim()
            self.assertEqual(claimed[0], identity)
            self.assertIsNone(JobQueue(path).claim())
            queue.finish(identity, {'response': 4})
            self.assertEqual(JobQueue(path).snapshot()[0]['result'], {'response': 4})
            other = queue.add({'profile': 2})
            queue.claim()
            queue.recover_interrupted()
            self.assertEqual([j for j in queue.snapshot() if j['id'] == other][0]['status'], 'NEEDS_RECONCILIATION')
            self.assertIsNone(queue.claim())

    def test_actual_gdelt_fixture_and_wrong_hash(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / 'tests/fixtures/gdelt/manifest.json').read_text())
        result = ingest(root / manifest['path'], manifest['sha256'])
        self.assertEqual(len(result['records']), 868)
        self.assertTrue(all(not r['forecast_admissible'] and r['published_at_utc'] is None for r in result['records']))
        with self.assertRaises(ValueError):
            ingest(root / manifest['path'], 'wrong')
