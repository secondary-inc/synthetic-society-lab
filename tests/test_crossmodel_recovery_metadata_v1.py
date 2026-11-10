"""Typed null-tier guards, authored inputs only; no HTTP/owner/credential reads."""
from copy import deepcopy
import unittest
from civiclab.common import canonical_bytes
from civiclab.model import ExecutionBlocked
from civiclab.e02 import crossmodel_recovery_metadata_v1 as m
from civiclab.e02.issue_cue_crossmodel_v1 import next_action
from civiclab.e02.issue_cue_crossmodel_recovery_owner_v1 import refresh_stage_for_slot,validate_refresh
from test_e02_issue_cue_crossmodel_v1 import RAW,terms


def fixture(role='B'):
    ts=terms();first=next_action(RAW,ts,b'[]')['request']
    if role=='B':
        record={'execution_order':0,'phase':'pre','payload_sha256':first['payload_sha256'],'status':'ANSWER','answer':{'library_support':50}}
        req=next_action(RAW,ts,canonical_bytes([record]))['request']
    else:req=first
    model=ts[role]['model']
    stats={'id':'gen-authored-recovery','model':model,'provider_name':ts[role]['reported_provider'],
        'total_cost':0.0000726,'native_tokens_prompt':612,'native_tokens_completion':38,'native_tokens_reasoning':0,
        'is_byok':False,'service_tier':None if role=='B' else 'default','streamed':False,'cancelled':False}
    kw=dict(generation_id=stats['id'],requested_model=model,reported_provider=ts[role]['reported_provider'],
        input_bound=req['envelope']['input_token_bound'],output_bound=256,reserved_microusd=req['envelope']['reserved_microusd'],request_payload=req['payload'])
    return stats,kw


class MetadataTests(unittest.TestCase):
    def test_qwen_explicit_null_is_unknown_raw_unchanged_billing_still_exact(self):
        stats,kw=fixture();before=deepcopy(stats);r=m.normalize_statistics(stats,**kw)
        self.assertEqual(stats,before);self.assertIsNone(r['telemetry']['reported_service_tier'])
        self.assertEqual(r['telemetry']['service_tier_status'],'REPORTED_NULL_UNKNOWN')
        self.assertEqual(r['observed_cost_microusd'],73)
        self.assertEqual(r['billing']['native_tokens_prompt'],612)
        self.assertTrue(r['telemetry']['request_no_tier_override'])
    def test_absent_nondefault_malformed_and_azure_null_tiers_refused(self):
        for role,value in [('A',None),('B','priority'),('B','flex'),('B',''),('B',False),('B',0),('B',[]),('B',{})]:
            stats,kw=fixture(role);stats['service_tier']=value
            with self.subTest(role=role,value=value),self.assertRaises(ExecutionBlocked):m.normalize_statistics(stats,**kw)
        stats,kw=fixture();stats.pop('service_tier')
        with self.assertRaises(ExecutionBlocked):m.normalize_statistics(stats,**kw)
    def test_typed_usage_identity_activity_cost_and_override_guards(self):
        for key,value in [('id','gen-wrong'),('model',m.QWEN_MODEL+'-other'),('provider_name','Azure'),('is_byok',True),
            ('native_tokens_reasoning',None),('native_tokens_reasoning',1),('native_tokens_completion',257),
            ('native_tokens_prompt',True),('num_fetches',1),('total_cost',None),('total_cost',0.01),('cancelled',True)]:
            stats,kw=fixture();stats[key]=value
            with self.subTest(key=key,value=value),self.assertRaises((ValueError,ExecutionBlocked)):m.normalize_statistics(stats,**kw)
        for key,value in [('service_tier',None),('stream',True),('tools',[{}]),('max_completion_tokens',257),('temperature',True)]:
            stats,kw=fixture();kw['request_payload'][key]=value
            with self.subTest(request_key=key),self.assertRaises(ExecutionBlocked):m.normalize_statistics(stats,**kw)
    def test_default_retained_and_unknown_auxiliary_never_zero(self):
        stats,kw=fixture();stats['service_tier']='default';stats['num_fetches']=None
        result=m.normalize_statistics(stats,**kw)
        self.assertEqual(result['telemetry']['service_tier_status'],'OBSERVED_LITERAL_DEFAULT')
        self.assertEqual(result['telemetry']['optional_counters']['num_fetches']['status'],'REPORTED_NULL_UNKNOWN')
        self.assertEqual(result['telemetry']['optional_counters']['num_search_results']['status'],'NOT_REPORTED_UNKNOWN')


class RefreshScheduleTests(unittest.TestCase):
    def test_fixed_barriers_and_missing_out_of_order_replay_guards(self):
        for order,stage in ((2,0),(15,0),(16,1),(29,1),(30,2),(43,2),(44,3),(55,3)):
            self.assertEqual(refresh_stage_for_slot(order),stage)
        for stage,order,nxt in ((0,16,1),(1,30,2),(2,44,3),(0,31,1),(1,31,2)):
            validate_refresh(stage,order,nxt)
        # Even if scientific skips leap both16 and30, stage1 then2 required.
        for stage,order,nxt in ((0,15,1),(0,30,2),(1,30,1),(2,30,3),(3,55,4),(False,16,1),(0,16,True)):
            with self.subTest(stage=stage,order=order,nxt=nxt),self.assertRaises(ExecutionBlocked):validate_refresh(stage,order,nxt)
        for bad in (True,1,56,16.0):
            with self.assertRaises(ExecutionBlocked):refresh_stage_for_slot(bad)

if __name__=='__main__':unittest.main()
