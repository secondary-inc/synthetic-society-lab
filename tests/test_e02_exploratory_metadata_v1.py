"""Authored cases mirroring the retained metadata shape, not new observations."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from civiclab.model import ExecutionBlocked
from civiclab.e02.exploratory_metadata_v1 import (
    normalize_statistics,response_model_allowed,BASE_MODEL,DATED_MODEL,COUNTERS)


def saved_shape():
    # Same allowlisted domains as retained billing metadata; authored generation ID.
    return {'id':'gen-authored-metadata','model':DATED_MODEL,'provider_name':'Azure','is_byok':False,
            'total_cost':0.000007,'native_tokens_prompt':46,'native_tokens_completion':6,
            'native_tokens_reasoning':0,'native_tokens_completion_images':0,'num_media_prompt':None,
            'num_media_completion':0,'num_input_audio_prompt':None,'num_search_results':None,
            'num_fetches':None,'web_search_engine':None,'service_tier':'default','streamed':True,'cancelled':False}


def norm(stats,**overrides):
    kwargs={'generation_id':'gen-authored-metadata','requested_model':BASE_MODEL,'reported_provider':'Azure',
            'input_bound':2276,'output_bound':32,'reserved_microusd':340}
    kwargs.update(overrides);return normalize_statistics(stats,**kwargs)


class MetadataTests(unittest.TestCase):
    def test_saved_shape_exact_projection_and_truthful_telemetry(self):
        stats=saved_shape();before=deepcopy(stats);out=norm(stats)
        self.assertEqual(stats,before);self.assertEqual(out['observed_cost_microusd'],7)
        self.assertEqual(len(out['billing']),8);self.assertEqual(out['billing']['model'],BASE_MODEL)
        self.assertEqual(out['telemetry']['reported_model'],DATED_MODEL)
        self.assertEqual(out['telemetry']['reported_service_tier'],'default')
        self.assertIs(out['telemetry']['reported_streamed'],True);self.assertTrue(out['telemetry']['streamed_discrepancy'])
        self.assertEqual(out['telemetry']['optional_counters']['num_fetches']['status'],'REPORTED_NULL_UNKNOWN')
        self.assertEqual(out['telemetry']['optional_counters']['num_media_completion']['status'],'OBSERVED_ZERO')
        self.assertIn('NOT_RAW',out['telemetry']['billing_representation']);self.assertFalse(out['telemetry']['actual_authority'])
    def test_missing_is_not_null_is_not_zero(self):
        stats=saved_shape();stats.pop('num_fetches');out=norm(stats)
        self.assertEqual(out['telemetry']['optional_counters']['num_fetches'],{'status':'NOT_REPORTED_UNKNOWN','present':False})
        for value,status in [(None,'REPORTED_NULL_UNKNOWN'),(0,'OBSERVED_ZERO')]:
            stats['num_fetches']=value;self.assertEqual(norm(stats)['telemetry']['optional_counters']['num_fetches']['status'],status)
    def test_every_optional_counter_positive_negative_bool_fraction_rejected(self):
        for field in COUNTERS:
            for value in (1,-1,False,0.0,'0',{},[]):
                with self.subTest(field=field,value=value):
                    stats=saved_shape();stats[field]=value
                    with self.assertRaises(ExecutionBlocked):norm(stats)
    def test_exact_model_pair_and_provider_identity(self):
        self.assertTrue(response_model_allowed(BASE_MODEL,BASE_MODEL));self.assertTrue(response_model_allowed(DATED_MODEL,BASE_MODEL))
        for reported in ['openai/gpt-4.1-nano-2025-04-15','openai/gpt-4.1-nano-other',None,True]:
            self.assertFalse(response_model_allowed(reported,BASE_MODEL))
            stats=saved_shape();stats['model']=reported
            with self.assertRaises(ExecutionBlocked):norm(stats)
        for kwargs in [{'generation_id':'gen-other'},{'requested_model':DATED_MODEL},{'reported_provider':'azure'}]:
            with self.assertRaises(ExecutionBlocked):norm(saved_shape(),**kwargs)
        for field,value in [('provider_name','OpenAI'),('is_byok',0),('is_byok',True)]:
            stats=saved_shape();stats[field]=value
            with self.assertRaises(ExecutionBlocked):norm(stats)
    def test_tier_unknown_or_nondefault_refused(self):
        for value in (None,'priority','flex','DEFAULT','',0,False):
            stats=saved_shape();stats['service_tier']=value
            with self.assertRaises(ExecutionBlocked):norm(stats)
        stats=saved_shape();stats.pop('service_tier')
        with self.assertRaises(ExecutionBlocked):norm(stats)
    def test_literal_stream_and_cancel_domains(self):
        for value in (True,False):
            stats=saved_shape();stats['streamed']=value
            self.assertIs(norm(stats)['telemetry']['reported_streamed'],value)
        for field in ('streamed','cancelled'):
            for value in (None,0,1,'false',[]):
                stats=saved_shape();stats[field]=value
                with self.assertRaises(ExecutionBlocked):norm(stats)
            stats=saved_shape();stats.pop(field)
            with self.assertRaises(ExecutionBlocked):norm(stats)
        stats=saved_shape();stats['cancelled']=True
        with self.assertRaises(ExecutionBlocked):norm(stats)
    def test_native_usage_and_released_envelope_bounds(self):
        for field,value in [('native_tokens_prompt',2277),('native_tokens_completion',33),('native_tokens_reasoning',1),
                            ('native_tokens_prompt',True),('native_tokens_completion',6.0),('native_tokens_reasoning',None)]:
            stats=saved_shape();stats[field]=value
            with self.assertRaises(ExecutionBlocked):norm(stats)
        for kwargs in [{'input_bound':True},{'output_bound':513},{'reserved_microusd':0},{'input_bound':8193}]:
            with self.assertRaises(ExecutionBlocked):norm(saved_shape(),**kwargs)
    def test_cost_known_nondecreasing_finite_and_not_invented(self):
        for value in (None,True,'NaN','-0.000001','0.001',float('inf')):
            stats=saved_shape();stats['total_cost']=value
            with self.assertRaises(ExecutionBlocked):norm(stats)
        for value,amount in [('0',0),('0.0000071',8),('0.000340',340)]:
            stats=saved_shape();stats['total_cost']=value
            self.assertEqual(norm(stats)['observed_cost_microusd'],amount)
    def test_search_nonnull_refused_and_pure_no_io(self):
        stats=saved_shape();stats['web_search_engine']='unknown'
        with self.assertRaises(ExecutionBlocked):norm(stats)
        with patch('builtins.open',side_effect=AssertionError('I/O forbidden')):
            self.assertEqual(norm(saved_shape())['observed_cost_microusd'],7)


if __name__=='__main__':unittest.main()
