from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from civiclab.model import BudgetLedger, Policy, Price, OpenRouter, ExecutionBlocked


def price():
    return Price("fixed/model-2026", "Provider", "0.000001", "0.000002", datetime.now(timezone.utc).isoformat(), "https://openrouter.ai/model/endpoints")


class BudgetTests(unittest.TestCase):
    def test_string_flags_do_not_authorize_paid_execution(self):
        for flag in ('false','true',1,None):
            ledger=BudgetLedger(self.path,Policy(flag,'1','0','1','TEST_ONLY'))
            with self.assertRaises(ExecutionBlocked):ledger.reserve('E02','.001')

    def test_cancellation_preserves_reservation_and_halts_then_propagates(self):
        ledger=BudgetLedger(self.path,Policy(True,'1','0','1','TEST_ONLY'))
        def cancelled(*args):raise KeyboardInterrupt()
        client=OpenRouter(ledger,price(),'fixture-key',cancelled)
        with self.assertRaises(KeyboardInterrupt):
            client.complete([{'role':'user','content':'hello'}],module='E02')
        self.assertEqual(ledger.snapshot()[0]['status'],'UNCERTAIN')
        with self.assertRaises(ExecutionBlocked):ledger.reserve('E02','.001')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "budget.sqlite"

    def test_default_blocks_before_transport(self):
        client = OpenRouter(BudgetLedger(self.path), price(), "fixture-key", lambda *args: self.fail("network called"))
        with self.assertRaises(ExecutionBlocked):
            client.complete([{"role": "user", "content": "hello"}], module="E02")

    def test_concurrent_reservations_and_restart_cannot_exceed_cap(self):
        ledger = BudgetLedger(self.path, Policy(True, "0.01", "0", "0.01", "TEST_ONLY"))
        def request(_):
            try:
                return ledger.reserve("E02", "0.003")
            except ExecutionBlocked:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(request, range(12)))
        self.assertEqual(sum(x is not None for x in ids), 3)
        with self.assertRaises(ExecutionBlocked):
            BudgetLedger(self.path, ledger.policy).reserve("E02", "0.003")

    def test_uncertain_call_halts_without_refund(self):
        ledger = BudgetLedger(self.path, Policy(True, "1", "0", "1", "TEST_ONLY"))
        def failure(*args):
            raise TimeoutError("secret should not appear")
        client = OpenRouter(ledger, price(), "fixture-key", failure)
        with self.assertRaisesRegex(ExecutionBlocked, "ledger halted"):
            client.complete([{"role": "user", "content": "hello"}], module="E02")
        self.assertEqual(ledger.snapshot()[0]["status"], "UNCERTAIN")
        with self.assertRaises(ExecutionBlocked):
            ledger.reserve("E02", "0.001")

    def test_pinned_response_and_accounting(self):
        ledger = BudgetLedger(self.path, Policy(True, "1", "0", "1", "TEST_ONLY"))
        def response(payload, key):
            self.assertFalse(payload["provider"]["allow_fallbacks"])
            self.assertEqual(payload["provider"]["only"], ["Provider"])
            return {"model": "fixed/model-2026", "provider": "Provider", "id": "mock-completion",
                    "usage": {"prompt_tokens": 12, "completion_tokens": 5, "cost": 0.000022},
                    "choices": [{"message": {"content": '{"answer": 2}'}}]}
        result = OpenRouter(ledger, price(), "fixture-key", response).complete([{"role": "user", "content": "hello"}], module="E02")
        self.assertEqual(result["output"], {"answer": 2})
        self.assertEqual(ledger.snapshot()[0]["charged_microusd"], 22)

    def test_wrong_provider_halts_and_unknown_prices_block(self):
        ledger = BudgetLedger(self.path, Policy(True, "1", "0", "1", "TEST_ONLY"))
        client = OpenRouter(ledger, price(), "fixture-key", lambda *args: {"model": "fixed/model-2026", "provider": "Other"})
        with self.assertRaises(ExecutionBlocked):
            client.complete([{"role": "user", "content": "hello"}], module="E02")
        self.assertEqual(ledger.snapshot()[0]["status"], "UNCERTAIN")
        with self.assertRaises(ExecutionBlocked):
            Price("latest", "", "0", "0", "", "").validate()

    def test_actual_overrun_halts_future_calls(self):
        ledger = BudgetLedger(self.path, Policy(True, "1", "0", "1", "TEST_ONLY"))
        receipt = ledger.reserve("E02", "0.01")
        with self.assertRaises(ExecutionBlocked):
            ledger.settle(receipt, "0.02")
        self.assertEqual(ledger.snapshot()[0]["charged_microusd"], 20000)
        with self.assertRaises(ExecutionBlocked):
            ledger.reserve("E02", "0.001")

    def test_known_billing_not_lost_when_output_is_invalid(self):
        ledger=BudgetLedger(self.path,Policy(True,'1','0','1','TEST_ONLY'))
        def malformed(*args):
            return {'model':'fixed/model-2026','provider':'Provider',
                    'usage':{'prompt_tokens':12,'completion_tokens':5,'cost':.1},
                    'choices':[{'message':{'content':'not valid JSON'}}]}
        with self.assertRaises(ExecutionBlocked):
            OpenRouter(ledger,price(),'fixture-key',malformed).complete([{'role':'user','content':'hello'}],module='E02')
        self.assertEqual(ledger.snapshot()[0]['charged_microusd'],100000)
        self.assertEqual(ledger.snapshot()[0]['status'],'OVERRUN')
