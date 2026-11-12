"""Wrapper clock and physical lookup limits, with no financial or network I/O."""
from datetime import timedelta
from unittest.mock import Mock, patch
import unittest

from civiclab.model import ExecutionBlocked
from civiclab.e02.wrapper_visibility_owner_v1 import WrapperVisibilityOwnerV1
from civiclab.e02 import wrapper_visibility_client_v1 as client
from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
from test_production_price_v4 import T0


class ControlTests(unittest.TestCase):
    def test_new_single_proof_and_old_two_proof_replay_advance_once(self):
        owner=object.__new__(WrapperVisibilityOwnerV1)
        for kind,roles in [('WRAPPER_VISIBILITY_POLICY_V1',('B',)),
                           ('CROSSMODEL_RECOVERY_POLICY_V1',('A','B'))]:
            state={'max_clock':T0-timedelta(seconds=1)}
            policy={'kind':kind,'valid_from_utc':(T0-timedelta(seconds=1)).isoformat(),
                    'valid_until_utc':(T0+timedelta(hours=1)).isoformat()}
            event={'kind':'AUTHORED_CLOCK_PROBE','recorded_at_utc':T0.isoformat(),'prior_clock_max_utc':state['max_clock'].isoformat(),
                   'clock_status':'OK','clock_error':None,'payload':{}}
            proofs={r:{'observed_at_utc':T0.isoformat()} for r in roles}
            with patch.object(owner,'_check_proof'),patch.object(owner,'_clock',wraps=owner._clock) as clock:
                self.assertEqual(owner._new_proofs_clock(event,state,policy,proofs,{r:{'terms':{}} for r in roles}),T0)
                clock.assert_called_once()
            self.assertEqual(state['max_clock'],T0)

    def test_stale_future_and_rollback_proofs_fail(self):
        owner=object.__new__(WrapperVisibilityOwnerV1)
        for age,rollback in [(-901,False),(1,False),(0,True)]:
            state={'max_clock':T0+timedelta(seconds=1 if rollback else -1)}
            policy={'kind':'WRAPPER_VISIBILITY_POLICY_V1',
                    'valid_from_utc':(T0-timedelta(seconds=1)).isoformat(),
                    'valid_until_utc':(T0+timedelta(hours=1)).isoformat()}
            event={'kind':'AUTHORED_CLOCK_PROBE','recorded_at_utc':T0.isoformat(),'prior_clock_max_utc':state['max_clock'].isoformat(),
                   'clock_status':'CLOCK_ROLLBACK' if rollback else 'OK','clock_error':None,'payload':{}}
            proof={'B':{'observed_at_utc':(T0+timedelta(seconds=age)).isoformat()}}
            with patch.object(owner,'_check_proof'),self.assertRaises(ExecutionBlocked):
                owner._new_proofs_clock(event,state,policy,proof,{'B':{'terms':{}}})

    def test_only_closed404_can_retry_and_physical_total_is_capped(self):
        for status,close_failed,expected in [(404,False,3),(429,False,1),(500,False,1),(404,True,1)]:
            transport=Mock();transport.statistics.side_effect=_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',status,close_failed=close_failed)
            counters={'total':0,'phase':0}
            with patch.object(client,'_visibility_wait'),self.assertRaises(_SafeTransportFailure):
                client._poll_statistics(transport,'gen-authored',journal=Mock(),phase=Mock(),receipt='a'*32,counters=counters)
            self.assertEqual(transport.statistics.call_count,expected)
            self.assertEqual(counters,{'total':expected,'phase':expected})
        transport=Mock()
        with patch.object(client,'_visibility_wait'),self.assertRaises(ExecutionBlocked):
            client._poll_statistics(transport,'gen-authored',journal=Mock(),phase=Mock(),receipt='a'*32,counters={'total':120,'phase':0})
        transport.statistics.assert_not_called()


if __name__=='__main__':unittest.main()
