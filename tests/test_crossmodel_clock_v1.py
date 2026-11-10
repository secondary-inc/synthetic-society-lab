"""Advancing event clocks must be authenticated once for both price proofs."""
from copy import deepcopy
from datetime import timedelta
import unittest
from unittest.mock import patch

from civiclab.e02.issue_cue_crossmodel_owner_v1 import CrossmodelOwnerV1,START,REFRESH
from civiclab.model import ExecutionBlocked
from test_production_price_v4 import T0


class ClockTests(unittest.TestCase):
    def test_start_and_refresh_each_advance_clock_once_for_two_models(self):
        owner=object.__new__(CrossmodelOwnerV1)
        state={'max_clock':T0-timedelta(days=1)}
        policy={'valid_from_utc':(T0-timedelta(minutes=1)).isoformat(),
                'valid_until_utc':(T0+timedelta(hours=2)).isoformat()}
        for kind,now in ((START,T0),(REFRESH,T0+timedelta(minutes=5))):
            proofs={role:{'observed_at_utc':now.isoformat()} for role in ('A','B')}
            event={'kind':kind,'recorded_at_utc':now.isoformat(),
                'prior_clock_max_utc':state['max_clock'].isoformat(),
                'clock_status':'OK','clock_error':None,'payload':{}}
            with patch.object(owner,'_check_proof'),patch.object(owner,'_clock',wraps=owner._clock) as clock:
                result=owner._new_proofs_clock(event,state,policy,proofs,{'A':{'terms':{}},'B':{'terms':{}}})
            self.assertEqual(result,now);self.assertEqual(state['max_clock'],now);clock.assert_called_once()

    def test_stale_future_and_clock_rollback_still_refused(self):
        owner=object.__new__(CrossmodelOwnerV1)
        for seconds in (-901,1):
            state={'max_clock':T0-timedelta(seconds=1)}
            policy={'valid_from_utc':(T0-timedelta(minutes=1)).isoformat(),'valid_until_utc':(T0+timedelta(hours=1)).isoformat()}
            proofs={'A':{'observed_at_utc':T0.isoformat()},'B':{'observed_at_utc':(T0+timedelta(seconds=seconds)).isoformat()}}
            event={'kind':REFRESH,'recorded_at_utc':T0.isoformat(),'prior_clock_max_utc':state['max_clock'].isoformat(),'clock_status':'OK','clock_error':None,'payload':{}}
            with patch.object(owner,'_check_proof'),self.assertRaises(ExecutionBlocked):
                owner._new_proofs_clock(event,state,policy,proofs,{'A':{'terms':{}},'B':{'terms':{}}})
        state={'max_clock':T0+timedelta(seconds=1)}
        event.update(prior_clock_max_utc=state['max_clock'].isoformat(),clock_status='CLOCK_ROLLBACK')
        with patch.object(owner,'_check_proof'),self.assertRaises(ExecutionBlocked):
            owner._new_proofs_clock(event,state,policy,proofs,{'A':{'terms':{}},'B':{'terms':{}}})

if __name__=='__main__':unittest.main()
