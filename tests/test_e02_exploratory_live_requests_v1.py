"""Authored production-price terms and pure frozen exploratory prompts."""
from copy import deepcopy
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from civiclab.common import canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.e02.exploratory_live_requests_v1 import compile_pre,compile_post,cost_envelope,create_actual_client
from test_additional_compatibility_owner_v1 import materials

RAW=(Path(__file__).resolve().parents[1]/'configs/e02_exploratory_live_pilot_v1_1.json').read_bytes()


class LiveRequestCompilerTests(unittest.TestCase):
    def terms(self):return materials('AUTHORED_COMPILER_PRICE_ONLY')[0]['terms']

    def test_all_16_pre_prompts_match_independently_reviewed_projection_hashes(self):
        protocol=json.loads(RAW);terms=self.terms()
        for i in range(16):
            compiled=compile_pre(RAW,i,terms);expected=protocol['envelope']['exact_pre_and_post_surrogate_bounds'][i]['pre']
            self.assertEqual(compiled['envelope']['request_hash'],expected['request_hash'])
            self.assertEqual(compiled['envelope']['input_token_bound'],expected['input_token_bound'])
            request=json.loads(compiled['payload']['messages'][1]['content'])
            self.assertEqual(set(request['survey']),{'instrument_id','items','instructions'})
            self.assertEqual(compiled['payload']['seed'],protocol['assignments'][i]['pair_seed'])
            self.assertFalse(compiled['actual_authority']);self.assertEqual(compiled['payload']['max_completion_tokens'],512)

    def test_real_numeric_post_baselines_fit_common_bound_and_preserve_own_values(self):
        terms=self.terms()
        for i in range(16):
            before={'democratic_party':100,'republican_party':0.000000000000000000001}
            post=compile_post(RAW,i,terms,before)
            self.assertEqual(post['request']['pre_response'],before)
            self.assertLessEqual(post['envelope']['input_token_bound'],8192)
            self.assertTrue(post['own_committed_pre_witness_required'])
            self.assertFalse(post['actual_authority'])
            before['democratic_party']=1
            self.assertEqual(post['request']['pre_response']['democratic_party'],100)

    def test_invalid_pre_has_no_post_payload_and_never_repairs_or_imputes(self):
        for before in ({},{'democratic_party':None,'republican_party':50},
                       {'democratic_party':True,'republican_party':50},
                       {'democratic_party':101,'republican_party':50}):
            result=compile_post(RAW,0,self.terms(),before)
            self.assertEqual(result['status'],'SKIP_INVALID_PRE');self.assertIsNone(result['request'])
            self.assertNotIn('payload',result)

    def test_protocol_or_unit_override_refuses(self):
        for raw,unit in ((RAW+b' ',0),(RAW,True),(RAW,-1),(RAW,16)):
            with self.assertRaises(ExecutionBlocked):compile_pre(raw,unit,self.terms())

    def test_price_envelope_uses_production_terms_and_caps_every_potential_phase(self):
        plan=cost_envelope(RAW,self.terms())
        self.assertEqual(plan['per_call_reservation_microusd'],340)
        self.assertEqual(plan['study_reservation_max_microusd'],32*340)
        self.assertEqual(plan['shared_authorized_cap_microusd'],5000000)
        self.assertFalse(plan['actual_authority'])

    def test_price_or_context_validation_cannot_be_claimed_as_live_admission(self):
        with patch('civiclab.production_owner_v4.pwd.getpwuid',side_effect=AssertionError('owner')):
            with self.assertRaises(ExecutionBlocked):create_actual_client(object())


if __name__=='__main__':unittest.main()
