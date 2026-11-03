import tempfile
import unittest
from pathlib import Path
from civiclab.common import utc_now
from civiclab.model import BudgetLedger,Policy,Price,OpenRouter,ExecutionBlocked
from civiclab.planning import cost_plan


class PlanningTests(unittest.TestCase):
    def spec(self):
        return {'schema_version':1,'price':{'model':'FIXTURE-model','provider':'FIXTURE-provider',
                'input_usd_per_token':'0.0000000001','output_usd_per_token':'0.0000000001',
                'verified_at_utc':utc_now(),'source':'https://openrouter.ai/FIXTURE-NOT-REAL-PRICING'},
                'calls':[{'module':'E02','messages':[{'role':'user','content':'FIXTUREé'}],'max_tokens':1}]*3}

    def test_matches_real_ledger_per_call_rounding_without_dispatch(self):
        spec=self.spec();plan=cost_plan(spec)
        self.assertEqual(plan['total_reservation_microusd'],3)
        self.assertFalse(plan['dispatch_authorized'])
        self.assertFalse(plan['approved_policy']['enabled'])
        with tempfile.TemporaryDirectory() as tmp:
            ledger=BudgetLedger(Path(tmp)/'ledger.sqlite',Policy(True,'1','1','1','TEST-ONLY'))
            def cancelled(payload,key):raise TimeoutError('fixture')
            with self.assertRaises(ExecutionBlocked):
                OpenRouter(ledger,Price(**spec['price']),'TEST-NOT-A-KEY',cancelled).complete(
                    spec['calls'][0]['messages'],module='E02',max_tokens=1)
            charge=ledger.snapshot()[0]
            self.assertEqual(charge['reserved_microusd'],plan['calls'][0]['reservation_microusd'])
            self.assertEqual(charge['metadata']['input_token_bound'],plan['calls'][0]['input_token_bound'])

    def test_bad_or_unfrozen_inputs_do_not_produce_an_executable_plan(self):
        for mutate in (lambda s:s.update(calls=[]),
                       lambda s:s['calls'][0].update(module='E03'),
                       lambda s:s['calls'][0].update(max_tokens=True),
                       lambda s:s['calls'][0].update(messages=[{'role':'user','content':'x'*100001}]),
                       lambda s:s['price'].update(verified_at_utc='2000-01-01T00:00:00+00:00')):
            spec=self.spec();mutate(spec)
            with self.assertRaises((ValueError,ExecutionBlocked)):cost_plan(spec)
