"""Offline oracles for bounded metadata recovery; no key or network access."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import recover_e02_billing_v1 as m
from civiclab.common import canonical_hash
from civiclab.production_admission_v4 import _Credential
from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure


def bill():
    return {'data':{'id':m.GENERATION,'model':'openai/gpt-4.1-nano-2025-04-14',
        'provider_name':'Azure','is_byok':False,'total_cost':0.0000531,
        'native_tokens_prompt':459,'native_tokens_completion':18,'native_tokens_reasoning':0,
        'service_tier':'default','streamed':True,'cancelled':False}}


@contextmanager
def case(results):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp).resolve(); (root/m.OUTPUT).parent.mkdir(parents=True)
        row={'reserved':788,'context':{'terms':{'model':'openai/gpt-4.1-nano','reported_provider':'Azure'},
            'envelope':{'input_token_bound':3935,'max_tokens':512}}}
        transport=Mock();transport.statistics.side_effect=results
        now=[0.0]
        with patch.object(m,'evidence',return_value=(row,{'usage':{'cost':0.0000531}})), \
             patch.object(m,'_credential',return_value=_Credential('AUTHORED_TEST_CREDENTIAL_123456')) as credential, \
             patch.object(m,'_transport',return_value=transport), \
             patch.object(m.time,'monotonic',side_effect=lambda:now[0]), \
             patch.object(m.time,'sleep',side_effect=lambda n:now.__setitem__(0,now[0]+n)):
            yield root,transport,credential,now


class BillingRecoveryTests(unittest.TestCase):
    def test_success_one_get_no_post_no_owner_write(self):
        with case([bill()]) as (root,t,_,_):
            result=m.collect(canonical_hash(m.contract()),root=root)
            self.assertEqual(result['status'],'VERIFIED_BILLING_EVIDENCE_ONLY')
            self.assertEqual(result['GET_attempts'],1);self.assertEqual(result['POSTs'],0)
            self.assertFalse(result['financial_state_changed']);t.post_bytes.assert_not_called()
            self.assertEqual(json.loads((root/m.OUTPUT/'statistics.json').read_text()),bill())

    def test_only_404_retries_up_to_three_with_original_generation(self):
        error=_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
        with case([error,error,bill()]) as (root,t,_,clock):
            result=m.collect(canonical_hash(m.contract()),root=root)
            self.assertEqual(result['GET_attempts'],3);self.assertEqual(clock[0],30)
            self.assertEqual([x.args for x in t.statistics.call_args_list],[(m.GENERATION,)]*3)
            self.assertEqual(len(list((root/m.OUTPUT).glob('get-*-intent.json'))),3)

    def test_exhaustion_stops_at_three(self):
        with case([_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)]*4) as (root,t,*_):
            r=m.collect(canonical_hash(m.contract()),root=root)
            self.assertEqual(r['status'],'STOPPED');self.assertEqual(t.statistics.call_count,3)

    def test_other_errors_do_not_retry(self):
        for error in (_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',401),
                      _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',429),
                      _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404,True),TimeoutError()):
            with self.subTest(error=type(error).__name__),case([error]) as (root,t,*_):
                r=m.collect(canonical_hash(m.contract()),root=root)
                self.assertEqual(r['status'],'STOPPED');self.assertEqual(t.statistics.call_count,1)

    def test_wrong_cost_identity_tier_usage_or_activity_refuses(self):
        for field,value in [('id','gen-wrong'),('total_cost',0.000054),('service_tier','priority'),
                            ('model','another/model'),('native_tokens_prompt',True),('num_search_results',1)]:
            bad=bill();bad['data'][field]=value
            with self.subTest(field=field),case([bad]) as (root,t,*_):
                r=m.collect(canonical_hash(m.contract()),root=root)
                self.assertEqual(r['status'],'STOPPED');self.assertTrue(r['body_retained'])
                self.assertEqual(t.statistics.call_count,1)

    def test_consumed_directory_cannot_repeat_even_after_failure(self):
        with case([TimeoutError()]) as (root,t,credential,_):
            h=canonical_hash(m.contract());m.collect(h,root=root)
            with self.assertRaises(FileExistsError):m.collect(h,root=root)
            self.assertEqual(t.statistics.call_count,1);self.assertEqual(credential.call_count,1)

    def test_changed_contract_blocks_before_secret(self):
        with case([]) as (root,t,credential,_):
            with self.assertRaises(m.ExecutionBlocked):m.collect('0'*64,root=root)
            credential.assert_not_called();t.statistics.assert_not_called()

    def test_cancellation_retained_without_retry(self):
        with case([KeyboardInterrupt()]) as (root,t,*_):
            r=m.collect(canonical_hash(m.contract()),root=root)
            self.assertEqual(r['status'],'CANCELLED');self.assertEqual(t.statistics.call_count,1)

    def test_secret_body_never_persisted(self):
        bad=bill();bad['secret']='AUTHORED_TEST_CREDENTIAL_123456'
        with case([bad]) as (root,t,*_):
            r=m.collect(canonical_hash(m.contract()),root=root)
            self.assertEqual(r['status'],'STOPPED');self.assertFalse((root/m.OUTPUT/'statistics.json').exists())
            self.assertEqual(r['observed_total_cost_microusd'],54)

    def test_safe_cost_survives_storage_or_privacy_failure(self):
        bad=bill();bad['data']['total_cost']=0.001;bad['secret']='AUTHORED_TEST_CREDENTIAL_123456'
        with case([bad]) as (root,t,*_):
            r=m.collect(canonical_hash(m.contract()),root=root)
            self.assertEqual(r['observed_total_cost_microusd'],1000)
            self.assertTrue(r['observed_cost_exceeds_hold'])
        with case([bill()]) as (root,t,*_):
            write=m._write
            def fail_body(path,value):
                if path.name=='statistics.json':raise OSError('authored disk error')
                write(path,value)
            with patch.object(m,'_write',side_effect=fail_body):
                r=m.collect(canonical_hash(m.contract()),root=root)
            self.assertEqual(r['observed_total_cost_microusd'],54)

    def test_foreign_generation_does_not_supply_observed_cost(self):
        bad=bill();bad['data']['id']='gen-foreign';bad['data']['total_cost']=0.1
        with case([bad]) as (root,t,*_):
            r=m.collect(canonical_hash(m.contract()),root=root)
            self.assertIsNone(r['observed_total_cost_microusd'])

    def test_deadline_stops_before_next_get(self):
        with case([_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)]) as (root,t,_,clock):
            def jump(_):clock[0]=151
            with patch.object(m.time,'sleep',side_effect=jump):
                r=m.collect(canonical_hash(m.contract()),root=root)
            self.assertEqual(r['status'],'STOPPED');self.assertEqual(t.statistics.call_count,1)


if __name__=='__main__':unittest.main()
