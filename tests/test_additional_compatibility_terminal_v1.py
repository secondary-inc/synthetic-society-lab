"""Authored terminal packets only. Model, OS owner and credential access denied."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.additional_compatibility_terminal_v1 import (
    code_contract,validate_packet,run_once,_read_exact_packet,LIMITS,ACTION,prepare_original_metadata)
from test_additional_compatibility_client_v1_1 import client_case


@contextmanager
def packet_case():
    with client_case() as (args,kw,*rest):
        p={'kind':'ADDITIONAL_COMPATIBILITY_TERMINAL_PACKET_V1','release':args[4],
            'policy':args[0],'review':args[1],'approval':args[2],'owner_assertion_candidate':args[3],
            'executor_review':kw['executor_review'],'expected':kw['expected'],
            'expected_executor_review_hash':kw['expected_executor_review_hash'],
            'launcher_contract_sha256':canonical_hash(code_contract()),
            'historical_audit_sha256':'5e998c37e4be53b265527c4df0558ba70ea80e52b7fd0d75a0c8599388e015b0',
            'limits':deepcopy(LIMITS),'owner_action':ACTION}
        p['readiness_review']={'kind':'INDEPENDENT_ADDITIONAL_TERMINAL_PACKET_REVIEW_V1',
            'reviewer_role':'independent_auditor','review_id':uuid.uuid4().hex,
            'packet_inputs_hash':canonical_hash(p),'code_contract_hash':canonical_hash(code_contract())}
        yield p


class TerminalTests(unittest.TestCase):
    def test_exact_authored_packet_validates_but_validation_dispatches_nothing(self):
        with packet_case() as p:
            with patch('civiclab.additional_compatibility_terminal_v1.execute_authored',side_effect=AssertionError('dispatch')):
                self.assertEqual(validate_packet(p),p)

    def test_missing_human_assertion_or_integer_substitute_denies_before_paths(self):
        for flags in ((False,True,True),(True,False,True),(True,True,False),(1,True,True)):
            with self.subTest(flags=flags),patch('civiclab.production_owner_v4.pwd.getpwuid',side_effect=AssertionError('OS')):
                with self.assertRaises(ExecutionBlocked):run_once('not-a-packet','0'*64,
                    accept_prior_unknown=flags[0],confirm_rotated_dedicated_key=flags[1],confirm_prefunded_no_purchase=flags[2])

    def test_altered_caps_review_closure_payload_or_unapproved_file_refused(self):
        for mode in ('cap','bool','review','code','prompt','oldhold'):
            with self.subTest(mode=mode),packet_case() as p:
                if mode=='cap':p['limits']['absolute_lifetime_microusd']=5000000
                elif mode=='bool':p['limits']['new_POSTs']=True
                elif mode=='review':p['readiness_review']['packet_inputs_hash']='0'*64
                elif mode=='code':p['launcher_contract_sha256']='0'*64
                elif mode=='prompt':p['release']['request']['payload']['messages'][1]['content']='AUTHORED_CHANGED_PROMPT'
                else:p['limits']['old_uncertain_hold_microusd']=0
                with self.assertRaises(ExecutionBlocked):validate_packet(p)

    def test_loader_exact_bytes_duplicate_keys_and_size_limits(self):
        with packet_case() as p,tempfile.TemporaryDirectory() as t:
            path=Path(t)/'packet.json';raw=canonical_bytes(p);path.write_bytes(raw)
            self.assertEqual(_read_exact_packet(path,hashlib.sha256(raw).hexdigest()),p)
            with self.assertRaises(ExecutionBlocked):_read_exact_packet(path,'0'*64)
            path.write_bytes(b'{"kind":"one","kind":"two"}')
            with self.assertRaises(ValueError):_read_exact_packet(path,hashlib.sha256(path.read_bytes()).hexdigest())
            path.write_bytes(b'x'*524289)
            with self.assertRaises(ExecutionBlocked):_read_exact_packet(path,'0'*64)

    def test_run_uses_fixed_packet_and_passes_only_verified_detached_inputs(self):
        with packet_case() as p:
            path=Path(__file__).resolve().parents[1]/'configs/json_compatibility_additional_v1_terminal_packet.json'
            with patch('civiclab.additional_compatibility_terminal_v1._read_exact_packet',return_value=validate_packet(p)) as loader, \
                 patch('civiclab.additional_compatibility_terminal_v1.execute_authored',return_value={'summary':{'status':'COMPATIBLE'}}) as execute:
                result=run_once(path,'0'*64,accept_prior_unknown=True,confirm_rotated_dedicated_key=True,confirm_prefunded_no_purchase=True)
                self.assertEqual(result['summary']['status'],'COMPATIBLE');loader.assert_called_once()
                self.assertEqual(execute.call_args.args,(p['policy'],p['review'],p['approval'],p['owner_assertion_candidate'],p['release']))
                with self.assertRaises(ExecutionBlocked):run_once(Path('/tmp/unapproved-packet'),'0'*64,
                    accept_prior_unknown=True,confirm_rotated_dedicated_key=True,confirm_prefunded_no_purchase=True)
                self.assertEqual(execute.call_count,1)

    def test_launcher_prints_only_closed_error_summary_and_never_exception_text(self):
        path=Path(__file__).resolve().parents[1]/'scripts/run_additional_json_compatibility_once_v1.py'
        spec=importlib.util.spec_from_file_location('AUTHORED_TERMINAL_SCRIPT',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        out=io.StringIO()
        with patch.object(module,'run_once',side_effect=RuntimeError('AUTHORED_SECRET_EXCEPTION_TEXT')),patch('sys.stdout',out):
            result=module.main(['--packet-sha256','0'*64])
        self.assertEqual(result,2);self.assertNotIn('AUTHORED_SECRET_EXCEPTION_TEXT',out.getvalue())
        self.assertEqual(json.loads(out.getvalue())['status'],'STOPPED_NO_RETRY')

    def test_invalid_readonly_release_refuses_before_owner_or_output(self):
        with patch('civiclab.production_owner_v4.pwd.getpwuid',side_effect=AssertionError('owner read')), \
             patch('civiclab.additional_compatibility_terminal_v1._preparation_base',side_effect=AssertionError('output access')):
            with self.assertRaises(ExecutionBlocked):prepare_original_metadata({},'0'*64)

    def test_readonly_release_writes_only_private_metadata_and_cannot_repeat(self):
        with packet_case(),tempfile.TemporaryDirectory() as t:
            release={'kind':'INDEPENDENT_ORIGINAL_OWNER_READONLY_RELEASE_V1_1',
                'reviewer_role':'independent_auditor','review_id':uuid.uuid4().hex,
                'code_contract_hash':canonical_hash(code_contract()),
                'scope':'ONE_FINITE_ORIGINAL_OWNER_METADATA_SNAPSHOT_NO_DISPATCH',
                'predecessor_receipt':'4fc8f40cbc434a308f11e1094fae5d7a','max_invocations':1,
                'owner_writes':False,'credential_reads':False,'HTTP_requests':0}
            with patch('civiclab.additional_compatibility_terminal_v1._preparation_base',return_value=Path(t).resolve()/'AUTHORED_PREPARATION'):
                result=prepare_original_metadata(release,canonical_hash(release))
                self.assertFalse(result['owner_writes']);self.assertFalse(result['credential_reads'])
                raw=Path(result['snapshot_path']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),result['snapshot_sha256'])
                with self.assertRaises(FileExistsError):prepare_original_metadata(release,canonical_hash(release))


if __name__=='__main__':unittest.main()
