"""Offline adaptive pre/post request bounds; no transport is constructed."""
from copy import deepcopy
import json
from pathlib import Path
import random
import struct
import unittest

from civiclab.common import canonical_hash
from civiclab.e02.experiment import assignments
from civiclab.model import ExecutionBlocked
from civiclab.reconciled_client_v2 import fixture_terms
from civiclab.survey_envelope_v2 import compile_envelope, prepare_phase, validate_plan
from civiclab.survey_execution import messages, post_request

ROOT=Path(__file__).resolve().parents[1]
INSTRUMENT=json.loads((ROOT/'configs/e02_instrument.json').read_text())
STIMULI=json.loads((ROOT/'configs/e02_demo_stimuli.json').read_text())


class SurveyEnvelopeTests(unittest.TestCase):
    def job(self):return assignments([{'profile_id':'AUTHORED','party':'D'}],STIMULI[:1],20261103)[0]
    def plan(self):return compile_envelope(self.job(),INSTRUMENT,fixture_terms())
    def prepare(self,plan,phase,**kwargs):
        return prepare_phase(plan,phase,expected_plan_hash=canonical_hash(plan),**kwargs)

    def test_pre_and_adaptive_post_preserve_exact_own_response(self):
        plan=self.plan();before={'democratic_party':60.5,'republican_party':39.5}
        pre=self.prepare(plan,'pre');post=self.prepare(plan,'post',before=before)
        self.assertEqual(pre['quote'],plan['pre_quote'])
        self.assertEqual(post['messages'],messages(post_request(plan['job'],INSTRUMENT,before)))
        self.assertEqual(post['request']['pre_response'],before)
        self.assertLessEqual(post['quote']['reserved_microusd'],plan['post_bound']['reserved_microusd'])
        before['democratic_party']=1;self.assertEqual(post['request']['pre_response']['democratic_party'],60.5)

    def test_extreme_finite_numbers_and_authored_ieee_samples_fit(self):
        plan=self.plan();rng=random.Random(9164)
        numbers=[0,100,-0.0,5e-324,2.2250738585072014e-308,99.99999999999999]
        for _ in range(3000):
            value=struct.unpack('>d',rng.getrandbits(64).to_bytes(8,'big'))[0]
            if 0<=value<=100:numbers.append(value)
        self.assertGreater(len(numbers),600)
        for value in numbers:
            response={'democratic_party':value,'republican_party':value}
            phase=self.prepare(plan,'post',before=response)
            self.assertLessEqual(phase['quote']['encoded_message_bytes'],plan['post_bound']['encoded_message_bytes'])
            self.assertEqual(phase['request']['pre_response'],response)

    def test_invalid_missing_refused_pre_skips_without_messages_or_quote(self):
        for value in (None,{},[],{'democratic_party':None,'republican_party':1},
                      {'democratic_party':True,'republican_party':1},
                      {'democratic_party':101,'republican_party':1},
                      {'democratic_party':10**1000,'republican_party':1},
                      {'democratic_party':-(10**1000),'republican_party':1},
                      {'democratic_party':float('inf'),'republican_party':1},
                      {'democratic_party':2,'republican_party':1,'extra':'rejected'}):
            self.assertEqual(self.prepare(self.plan(),'post',before=value),
                             {'status':'SKIPPED_INVALID_PRE','request':None,'messages':None,'quote':None})

    def test_coedited_quotes_costs_pins_and_request_fields_refuse(self):
        for mutate in (lambda p:p['pre_quote'].__setitem__('reserved_microusd',1),
                       lambda p:p['post_bound'].__setitem__('input_token_bound',1),
                       lambda p:p.__setitem__('pair_reserved_microusd_bound',0),
                       lambda p:p.__setitem__('number_text_bound',100),
                       lambda p:p['source_pins'].__setitem__('model.py','0'*64)):
            plan=self.plan();mutate(plan)
            with self.assertRaises(ExecutionBlocked):self.prepare(plan,'pre')

    def test_frozen_serialization_replay_and_price_rounding(self):
        job=self.job();terms=fixture_terms();terms['input_usd_per_token']='0.0000000001';terms['output_usd_per_token']='0';terms['request_fee_usd']='0.0000001'
        plan=compile_envelope(job,INSTRUMENT,terms)
        self.assertEqual(plan['pair_reserved_microusd_bound'],2)
        copied=json.loads(json.dumps(plan));self.assertEqual(validate_plan(copied,expected_hash=canonical_hash(plan)),plan)
        self.assertEqual(canonical_hash(compile_envelope(job,INSTRUMENT,terms)),canonical_hash(plan))
        job['profile']['party']='R';self.assertEqual(plan['job']['profile']['party'],'D')

    def test_unknown_phase_instrument_and_baseline_context_refuse(self):
        with self.assertRaises(ValueError):self.prepare(self.plan(),'unknown')
        with self.assertRaises(ValueError):self.prepare(self.plan(),'pre',before={})
        instrument=deepcopy(INSTRUMENT);instrument['status']='altered'
        with self.assertRaises(ValueError):compile_envelope(self.job(),instrument,fixture_terms())

    def test_recompiled_different_job_cannot_replace_external_plan_binding(self):
        original=self.plan(); frozen=canonical_hash(original)
        job=deepcopy(original['job']);job['profile']['party']='R'
        replacement=compile_envelope(job,INSTRUMENT,fixture_terms())
        with self.assertRaises(ExecutionBlocked):
            prepare_phase(replacement,'pre',expected_plan_hash=frozen)
        with self.assertRaises(TypeError):prepare_phase(original,'pre')
