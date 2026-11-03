from pathlib import Path
import json
import tempfile
import unittest
from civiclab.common import RunStore
from civiclab.dashboard import verified_run,build,snapshot


class DashboardTests(unittest.TestCase):
    def test_integrity_tamper_rejected_and_incomplete_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with RunStore(root,'E02',{'stage':'test'},kind='MOCK') as run:
                run.finish({'status':'MOCK'})
            self.assertEqual(verified_run(run.path)['integrity'],'PASS')
            (run.path/'summary.json').write_text('{}')
            self.assertEqual(len(snapshot(root)['runs']),0)
            self.assertEqual(len(snapshot(root)['rejected_runs']),1)

    def test_script_content_escaped_and_no_source_records_or_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with RunStore(root,'E01',{'title':'</script><script>BAD</script>','api_key':'SECRET'}) as run:
                run.finish({'status':'DEMO','cost_usd':0})
            path=build(root,root/'viewer')
            text=path.read_text()
            self.assertNotIn('</script><script>BAD</script>',text)
            self.assertNotIn('SECRET',text)
            self.assertIn('MOCK / DEMO',text)
            self.assertIn('\\u003c/script',text)
            with self.assertRaises(ValueError):snapshot(root,['../../outside'])
