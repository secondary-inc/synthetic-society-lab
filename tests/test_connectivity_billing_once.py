"""Offline one-GET evidence collection; no account, model or financial owner."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('billing_collector',ROOT/'scripts/collect_connectivity_billing_once.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def response():
    return {'data':{'id':c.MANIFEST['generation_id'],'model':c.MANIFEST['model'],
        'provider_name':'Azure','is_byok':False,'total_cost':'0.000007',
        'native_tokens_prompt':100,'native_tokens_completion':4,'native_tokens_reasoning':0}}


class Stub:
    def __init__(self):self.calls=[];self.reply=response();self.error=None
    def statistics(self,identity):
        self.calls.append(identity)
        if self.error:raise self.error
        return deepcopy(self.reply)
    def post_bytes(self,*args):raise AssertionError('POST forbidden')


class CollectorTests(unittest.TestCase):
    def case(self,root,stub):
        digest=c.canonical_hash(c.contract(c.MANIFEST,root))
        with patch.object(c,'_credential',return_value=c._Credential('AUTHORED_BILLING_CREDENTIAL')), \
             patch.object(c,'_transport',return_value=stub):
            return c.collect_once(c.MANIFEST,root=root,expected_contract_hash=digest,owner_approved=True)
    def test_approval_refuses_before_file_key_or_transport(self):
        with patch.object(c,'_credential',side_effect=AssertionError()),patch.object(c,'_transport',side_effect=AssertionError()):
            with self.assertRaises(c.ExecutionBlocked):c.collect_once(None,expected_contract_hash='0'*64)
    def test_one_exact_get_canonical_retention_and_no_financial_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();stub=Stub();out=self.case(root,stub)
            self.assertEqual(stub.calls,[c.MANIFEST['generation_id']]);self.assertEqual(out['POSTs'],0)
            self.assertEqual(out['reported_provider_cost_microusd'],7)
            self.assertFalse(out['financial_state_changed']);self.assertFalse(out['invoice_or_quality_adoption'])
            path=root/'data/processed/connectivity_billing_once'/c.MANIFEST['run_id']
            self.assertEqual((path/'statistics.local.json').read_bytes(),c.canonical_bytes(stub.reply))
            self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in path.iterdir()))
            with self.assertRaises(FileExistsError):self.case(root,stub)
            self.assertEqual(len(stub.calls),1)
    def test_http404_no_retry_or_exception_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();stub=Stub();stub.error=c._SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
            out=self.case(root,stub)
            self.assertEqual(out['transport']['http_status'],404);self.assertEqual(len(stub.calls),1)
            self.assertEqual(out['provider_body'],'MISSING');self.assertEqual(out['original_hold_microusd'],340)
    def test_identity_native_provider_aux_and_monetary_domains(self):
        changes=[{'id':'gen-foreign'},{'provider_name':'foreign'},{'model':'foreign'},
                 {'is_byok':True},{'native_tokens_prompt':2277},{'native_tokens_prompt':True},
                 {'native_tokens_completion':33},{'native_tokens_reasoning':1},{'num_search_results':1},
                 {'total_cost':None},{'total_cost':'NaN'},{'total_cost':True}]
        for update in changes:
            with self.subTest(update=update),tempfile.TemporaryDirectory() as tmp:
                stub=Stub();stub.reply['data'].update(update);out=self.case(Path(tmp).resolve(),stub)
                self.assertEqual(out['status'],'STOPPED_NO_RETRY');self.assertEqual(len(stub.calls),1)
                self.assertEqual(out['provider_body'],'RETAINED_CANONICAL_COMPLETE')
                self.assertFalse(out['financial_state_changed'])
    def test_different_or_overrun_cost_is_retained_not_assumed_seven(self):
        for cost,overrun in [('0.000009',False),('0.01',True)]:
            with self.subTest(cost=cost),tempfile.TemporaryDirectory() as tmp:
                stub=Stub();stub.reply['data']['total_cost']=cost;out=self.case(Path(tmp).resolve(),stub)
                self.assertEqual(out['status'],'VERIFIED_BILLING_EVIDENCE_ONLY')
                self.assertFalse(out['reported_cost_matches_response_observation'])
                self.assertEqual(out['reported_cost_exceeds_original_hold'],overrun)
                self.assertFalse(out['holds_released'])
    def test_observed_overrun_survives_unverified_provider_as_evidence_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub=Stub();stub.reply['data'].update(total_cost='0.01',provider_name='foreign')
            out=self.case(Path(tmp).resolve(),stub)
            self.assertEqual(out['status'],'STOPPED_NO_RETRY')
            self.assertEqual(out['observed_total_cost_microusd'],10000)
            self.assertTrue(out['observed_cost_exceeds_original_hold'])
            self.assertFalse(out['financial_state_changed'])
    def test_secret_and_unknown_exception_not_retained_or_printed(self):
        for secret in (True,False):
            with tempfile.TemporaryDirectory() as tmp:
                stub=Stub()
                if secret:stub.reply['secret']='AUTHORED_BILLING_CREDENTIAL'
                else:stub.error=ValueError('AUTHORED_BILLING_CREDENTIAL')
                root=Path(tmp).resolve();out=self.case(root,stub)
                directory=root/'data/processed/connectivity_billing_once'/c.MANIFEST['run_id']
                self.assertEqual(out['provider_body'],'MISSING')
                self.assertFalse(any(b'AUTHORED_BILLING_CREDENTIAL' in p.read_bytes() for p in directory.iterdir()))
    def test_contract_or_manifest_tamper_prevents_key_or_network(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(c,'_credential',side_effect=AssertionError('credential touched')):
            with self.assertRaises(c.ExecutionBlocked):c.collect_once(c.MANIFEST,root=Path(tmp),expected_contract_hash='0'*64,owner_approved=True)
            for field,value in [('generation_id','gen-other'),('input_token_bound',8192),('extra',1)]:
                m=deepcopy(c.MANIFEST);m[field]=value
                with self.assertRaises(c.ExecutionBlocked):c.contract(m,Path(tmp))
    def test_intent_exists_before_credential_and_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();stub=Stub();digest=c.canonical_hash(c.contract(c.MANIFEST,root))
            def credential(path):
                self.assertTrue((root/'data/processed/connectivity_billing_once'/c.MANIFEST['run_id']/'intent.local.json').exists())
                return c._Credential('AUTHORED_BILLING_CREDENTIAL')
            with patch.object(c,'_credential',side_effect=credential),patch.object(c,'_transport',return_value=stub):
                c.collect_once(c.MANIFEST,root=root,expected_contract_hash=digest,owner_approved=True)
    def test_strict_private_ignored_env_loader_no_shell_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();p=root/'.env'
            p.write_text('OPENROUTER_API_KEY=sk-or-v1-AUTHORED_NOT_A_REAL_KEY\n');p.chmod(0o600)
            with patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
                credential=c._credential(root);self.assertEqual(credential._value,'sk-or-v1-AUTHORED_NOT_A_REAL_KEY')
                for text in ['OPENROUTER_API_KEY=$(touch forbidden)\n','OPENROUTER_API_KEY=sk-or-v1-TESTVALUE\nOPENROUTER_API_KEY=sk-or-v1-TESTVALUE\n']:
                    p.write_text(text)
                    with self.assertRaises(c.ExecutionBlocked):c._credential(root)
                self.assertFalse((root/'forbidden').exists())
                p.write_text('OPENROUTER_API_KEY=sk-or-v1-AUTHORED_NOT_A_REAL_KEY\n');p.chmod(0o644)
                with self.assertRaises(c.ExecutionBlocked):c._credential(root)
            p.chmod(0o600)
            with patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],1)):
                with self.assertRaises(c.ExecutionBlocked):c._credential(root)
    def test_symlink_output_and_credential_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();(root/'data').symlink_to(root,target_is_directory=True)
            with self.assertRaises(c.ExecutionBlocked):self.case(root,Stub())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();(root/'other').write_text('AUTHORED');(root/'.env').symlink_to(root/'other')
            with patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
                with self.assertRaises(OSError):c._credential(root)


if __name__=='__main__':unittest.main()
