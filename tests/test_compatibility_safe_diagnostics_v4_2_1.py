"""Only authored credentials/OS homes, fake HTTP and fabricated responses."""
import io
import json
import unittest
from unittest.mock import patch
import urllib.error

from civiclab.model import ExecutionBlocked
from civiclab.production_compatibility_transport_v4_2 import (
    _CheckedHTTPS, _SafeTransportFailure, _CompatibilityTransportV4_2)
from civiclab.production_compatibility_v4_2_1 import execute_compatibility, _Journal
from civiclab.production_admission_v4 import _Credential
from civiclab.production_owner_v4 import ProductionOwnerV4
from test_openrouter_http_v2 import KEY, Response, Opener
import test_production_compatibility_v4_2_1 as executor_fixtures

CANARY = 'AUTHORED_PRIVATE_ERROR_BODY_HEADER_REASON'


class SafeDiagnosticsTests(unittest.TestCase):
    def run_transport(self, response=None, error=None):
        client = _CheckedHTTPS(KEY)
        opener = Opener(response, error)
        client._opener = opener
        with self.assertRaises(_SafeTransportFailure) as caught:
            client.post({})
        diagnostic = caught.exception.diagnostic()
        self.assertNotIn(CANARY, json.dumps(diagnostic) + str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(len(opener.calls), 1)
        return diagnostic

    def test_http_codes_retained_without_reading_error_body_or_reason(self):
        class ForbiddenBody(io.BytesIO):
            def read(self, *args):
                raise AssertionError('HTTP error body must not be read')
        for status in (401, 403, 404, 429, 500):
            with self.subTest(status=status):
                body = ForbiddenBody(CANARY.encode())
                error = urllib.error.HTTPError('https://authored.invalid/'+CANARY,
                    status, CANARY, {'Private': CANARY}, body)
                result = self.run_transport(error=error)
                self.assertEqual(result, {'stage': 'HTTP_STATUS', 'category': 'HTTP_STATUS',
                    'http_status': status, 'close_failed': False})
                self.assertTrue(body.closed)

    def test_json_headers_and_timeout_have_distinct_closed_categories(self):
        cases = ((Response(b'{"a":NaN}'), None, 'JSON', 'INVALID_RESPONSE', 200),
                 (Response(headers=[('Content-Type', CANARY)]), None, 'HEADERS', 'INVALID_RESPONSE', 200),
                 (None, TimeoutError(CANARY), 'OPEN', 'TIMEOUT', None),
                 (None, RuntimeError(CANARY), 'OPEN', 'TRANSPORT_FAILURE', None))
        for response, error, stage, category, status in cases:
            with self.subTest(stage=stage, category=category):
                result = self.run_transport(response, error)
                self.assertEqual((result['stage'], result['category'], result['http_status']),
                                 (stage, category, status))

    def test_close_failure_preserves_http_code_and_primary_category(self):
        class CloseFailure(urllib.error.HTTPError):
            def close(self):
                super().close()
                raise OSError(CANARY)
        error = CloseFailure('https://authored.invalid', 429, CANARY, {}, io.BytesIO())
        result = self.run_transport(error=error)
        self.assertEqual(result, {'stage': 'HTTP_STATUS', 'category': 'HTTP_STATUS',
                                 'http_status': 429, 'close_failed': True})

    def test_cancellation_is_not_replaced_by_response_close_failure(self):
        class CancelResponse(Response):
            def read(self, *args):
                raise KeyboardInterrupt(CANARY)
            def close(self):
                super().close()
                raise OSError(CANARY)
        response = CancelResponse()
        client = _CheckedHTTPS(KEY); client._opener = Opener(response)
        with self.assertRaises(KeyboardInterrupt): client.post({})
        self.assertTrue(response.closed)

    def test_diagnostic_rejects_nonclosed_strings_and_boolean_status(self):
        for args in ((CANARY, 'HTTP_STATUS'), ('OPEN', CANARY),
                     ('OPEN', 'TIMEOUT', True), ('OPEN', 'TIMEOUT', 999),
                     ('OPEN', 'TIMEOUT', None, CANARY)):
            with self.assertRaises(ValueError): _SafeTransportFailure(*args)

    def case(self):
        return executor_fixtures.CompatibilityTests().case()

    def saved_summary(self, args):
        folder = args[0]/'data/processed/compatibility_runs'/args[1]['request']['run_id']
        for path in folder.iterdir():
            self.assertNotIn(CANARY.encode(), path.read_bytes())
        return json.loads((folder/'summary.local.json').read_text())

    def test_fake_http_error_reaches_terminal_exception_and_journal_with_uncertain_charge(self):
        with self.case() as (args, kwargs, owner, stub, *rest):
            transport = _CompatibilityTransportV4_2(_Credential('AUTHORED_FAKE_EXECUTOR_CREDENTIAL'))
            body = io.BytesIO(CANARY.encode())
            transport._http._opener = Opener(error=urllib.error.HTTPError(
                'https://authored.invalid', 401, CANARY, {}, body))
            with patch('civiclab.production_compatibility_v4_2_1._transport', return_value=transport):
                with self.assertRaises(ExecutionBlocked) as caught:
                    execute_compatibility(*args, **kwargs)
            diagnostic = self.saved_summary(args)['diagnostic']
            self.assertEqual(caught.exception.diagnostic, diagnostic)
            self.assertEqual(diagnostic['executor_stage'], 'MODEL_POST')
            self.assertEqual(diagnostic['transport']['http_status'], 401)
            self.assertEqual(diagnostic['model_POST_attempts'], 1)
            self.assertEqual(diagnostic['statistics_GET_attempts'], 0)
            self.assertIsNone(diagnostic['reported_provider_cost_microusd'])
            row = owner.snapshot()['charges'][0]
            self.assertEqual(row['status'], 'UNCERTAIN')
            self.assertEqual(diagnostic['conservative_charged_microusd'], row['charged'])
            self.assertEqual(row['charged'], row['reserved'])
            self.assertEqual(len(transport._http._opener.calls), 1)
            self.assertTrue(body.closed)

    def test_preparation_stop_records_zero_attempts_without_assuming_zero_billing(self):
        with self.case() as (args, kwargs, owner, stub, *rest):
            with patch('civiclab.production_compatibility_v4_2_1.prepare_new_dispatch',
                       side_effect=RuntimeError(CANARY)):
                with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kwargs)
            diagnostic = self.saved_summary(args)['diagnostic']
            self.assertEqual(diagnostic['executor_stage'], 'PUBLIC_PREPARATION')
            self.assertEqual(diagnostic['dispatch_outcome'], 'PRE_POST_STOP')
            self.assertFalse(diagnostic['reservation_recorded'])
            self.assertEqual(stub.posts, [])
            self.assertEqual(owner.snapshot()['charges'], [])
            self.assertIsNone(diagnostic['reported_provider_cost_microusd'])

    def test_reserved_pre_post_stop_differs_from_post_attempt(self):
        event = _Journal.event
        def fail(journal, kind, **fields):
            if kind == 'MODEL_POST_INTENT': raise OSError(CANARY)
            return event(journal, kind, **fields)
        with self.case() as (args, kwargs, owner, stub, *rest):
            with patch.object(_Journal, 'event', fail):
                with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kwargs)
            diagnostic = self.saved_summary(args)['diagnostic']
            self.assertTrue(diagnostic['reservation_recorded'])
            self.assertEqual(diagnostic['dispatch_outcome'], 'PRE_POST_STOP')
            self.assertEqual(diagnostic['executor_stage'], 'POST_INTENT')
            self.assertGreater(diagnostic['conservative_charged_microusd'], 0)
            self.assertEqual(stub.posts, [])

    def test_untrusted_exception_class_name_is_not_persisted(self):
        error_type = type(CANARY, (Exception,), {})
        with self.case() as (args, kwargs, owner, stub, *rest):
            stub.post_error = error_type(CANARY)
            with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kwargs)
            self.assertEqual(self.saved_summary(args)['error_type'], 'UnclassifiedFailure')
            self.assertEqual(owner.snapshot()['charges'][0]['error_type'], 'UnclassifiedFailure')

    def test_response_identity_and_statistics_failure_have_different_stages(self):
        for stage in ('RESPONSE_VALIDATION', 'STATISTICS_GET'):
            with self.subTest(stage=stage), self.case() as (args, kwargs, owner, stub, *rest):
                if stage == 'RESPONSE_VALIDATION':
                    stub.response['id'] = None
                else:
                    stub.stats_error = _SafeTransportFailure('OPEN', 'TIMEOUT')
                with self.assertRaises(ExecutionBlocked): execute_compatibility(*args, **kwargs)
                diagnostic = self.saved_summary(args)['diagnostic']
                self.assertEqual(diagnostic['executor_stage'], stage)
                self.assertEqual(diagnostic['model_POST_attempts'], 1)
                self.assertEqual(diagnostic['statistics_GET_attempts'], int(stage == 'STATISTICS_GET'))
                self.assertEqual(diagnostic['reported_provider_cost_microusd'], 1)


class ReservationAcknowledgementTests(unittest.TestCase):
    def test_missing_ack_never_claims_absence_before_or_after_durable_reserve(self):
        original = ProductionOwnerV4.reserve
        for durable in (False, True):
            with self.subTest(durable=durable), executor_fixtures.CompatibilityTests().case() as (args, kw, owner, stub, *rest):
                def lost_ack(instance, context):
                    if durable:
                        original(instance, context)
                    raise OSError(CANARY)
                with patch.object(ProductionOwnerV4, 'reserve', lost_ack):
                    with self.assertRaises(ExecutionBlocked) as caught:
                        execute_compatibility(*args, **kw)
                diagnostic = caught.exception.diagnostic
                self.assertEqual(diagnostic['executor_stage'], 'RESERVATION')
                self.assertIsNone(diagnostic['reservation_recorded'])
                self.assertEqual(diagnostic['reservation_observation'], 'UNKNOWN_AT_RESERVATION_BOUNDARY')
                self.assertIsNone(diagnostic['reserved_microusd'])
                self.assertIsNone(diagnostic['conservative_charged_microusd'])
                self.assertIsNone(diagnostic['reported_provider_cost_microusd'])
                self.assertEqual(diagnostic['model_POST_attempts'], 0)
                self.assertEqual(diagnostic['statistics_GET_attempts'], 0)
                self.assertEqual(stub.posts, [])
                snapshot = owner.snapshot()
                self.assertEqual(len(snapshot['charges']), int(durable))
                self.assertEqual(snapshot['consumed_microusd']['dispatches'], int(durable))
                if durable:
                    row = snapshot['charges'][0]
                    self.assertEqual(row['status'], 'STARTED')
                    self.assertEqual(row['charged'], row['reserved'])
                    self.assertGreater(row['charged'], 0)
                    with self.assertRaises(ExecutionBlocked): owner.reserve(row['context'])
                folder = args[0]/'data/processed/compatibility_runs'/args[1]['request']['run_id']
                saved = json.loads((folder/'summary.local.json').read_text())
                self.assertEqual(saved['diagnostic'], diagnostic)
                for p in folder.iterdir(): self.assertNotIn(CANARY.encode(), p.read_bytes())

    def test_original_v42_lost_ack_finding_remains_reproducible(self):
        import test_production_compatibility_v4_2 as original_fixtures
        from civiclab.production_compatibility_v4_2 import execute_compatibility as original_execute
        reserve = ProductionOwnerV4.reserve
        with original_fixtures.CompatibilityTests().case() as (args, kw, owner, stub, *rest):
            def lost_ack(instance, context):
                reserve(instance, context)
                raise OSError(CANARY)
            with patch.object(ProductionOwnerV4, 'reserve', lost_ack):
                with self.assertRaises(ExecutionBlocked) as caught:
                    original_execute(*args, **kw)
            self.assertFalse(caught.exception.diagnostic['reservation_recorded'])
            self.assertEqual(owner.snapshot()['charges'][0]['status'], 'STARTED')
            self.assertEqual(owner.snapshot()['consumed_microusd']['dispatches'], 1)
            self.assertEqual(stub.posts, [])
