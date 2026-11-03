"""Authored terminal orchestration only: fake owner/executor, no real credentials."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone

from civiclab.common import canonical_hash

SOURCE = Path(__file__).resolve().parents[1]/'scripts/continue_json_compatibility_once_v2.py'
spec = importlib.util.spec_from_file_location('terminal_continuation_v2_fixture', SOURCE)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class TerminalContinuationV2Tests(unittest.TestCase):
    def setup_fixture(self, root):
        def write(name, value):
            p=root/name; p.parent.mkdir(parents=True, exist_ok=True)
            raw=(json.dumps(value, sort_keys=True)+'\n').encode(); p.write_bytes(raw)
            return {'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        expiry=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        old={'owner_id':'AUTHORED_FIXTURE_OWNER','total_microusd':1000,
             'module_microusd':{'E01':0,'E02':1000},'total_dispatches':1,
             'module_dispatches':{'E01':0,'E02':1}}
        prior='data/processed/compatibility_operator_handoff/continuation-20261103-02'
        oldref=write(prior+'/approval.local.json', old)
        journal='data/processed/compatibility_runs/compatibility-20261103-gpt41nano-02'
        journalref=write(journal+'/summary.local.json', {'status':'AUTHORED_ZERO_STOP'})
        stop={'actual_charges':0,'actual_model_POST_attempts':0,
              'actual_statistics_GET_attempts':0,'actual_statistics_claims':0,
              'private_evidence_files':{oldref['path']:{k:v for k,v in oldref.items() if k!='path'}},
              'run_files':{journalref['path']:{k:v for k,v in journalref.items() if k!='path'}},
              'run_path':journal,'private_operator_handoff':prior}
        release={'interpretation':{'valid_until_utc':expiry},
                 'terms':{'model':'AUTHORED','initial_catalog_sha256':'0'*64,
                          'metadata_semantic_hash':'1'*64},
                 'request':{'run_id':module.RUN_ID,'plan_hash':'2'*64,
                            'envelope':{'max_tokens':32,'input_token_bound':2276}}}
        foundation={'fixture':'foundation'}; executor={'fixture':'executor'}
        launcher_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        packet={'launcher_sha256':launcher_sha,
                'release':write('configs/fixture-release.json',release),
                'foundation_review':write('reports/fixture-foundation.json',foundation),
                'executor_review':write('reports/fixture-executor.json',executor),
                'launcher_review':write('reports/fixture-launcher.json',{
                    'status':'PASS_TERMINAL_CONTINUATION_LAUNCHER_V2','launcher_sha256':launcher_sha,
                    'authored_fixture_only':True}),
                'original_stop':write('reports/fixture-stop.json',stop),
                'original_stop_audit':write('reports/fixture-stop-audit.json',{'authored_only':True}),
                'contract_sha256':canonical_hash({'fixture':'contract'}),
                'foundation_canonical_sha256':canonical_hash(foundation),
                'executor_canonical_sha256':canonical_hash(executor)}
        pref=write(module.PACKET, packet)
        snapshot={'consumed_microusd':{'total':0,'modules':{'E01':0,'E02':0},
                                     'dispatches':0,'module_dispatches':{'E01':0,'E02':0}},
                  'charges':[],'statistics_claimed_receipts':[],
                  'approval_hash':canonical_hash(old),'approval':old}
        afterref=write(prior+'/after-owner.local.json',snapshot)
        stop['retained_file_pins']={**stop.pop('private_evidence_files'), **stop.pop('run_files'),
            afterref['path']:{k:v for k,v in afterref.items() if k!='path'}}
        packet['predecessor_stop']=write('reports/fixture-stop.json',stop)
        packet['predecessor_stop_audit']=packet.pop('original_stop_audit')
        packet.pop('original_stop')
        pref=write(module.PACKET,packet)
        owner=Mock(); owner.snapshot.return_value=snapshot
        return packet,pref,owner,release

    def run_fixture(self, root, pref, owner, execute, confirm=True):
        argv=['launcher','--packet-sha256',pref['sha256']]
        if confirm: argv+=['--confirm-rotated-dedicated-key']
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.object(module,'ROOT',root))
            stack.enter_context(patch.object(Path,'cwd',return_value=root))
            stack.enter_context(patch.object(sys,'argv',argv))
            stack.enter_context(patch('civiclab.production_owner_v4.ProductionOwnerV4.open',return_value=owner))
            stack.enter_context(patch('civiclab.production_owner_v4.ProductionOwnerV4.initialize',side_effect=AssertionError('NO_BOOTSTRAP')))
            stack.enter_context(patch('civiclab.production_compatibility_v4_1.execution_contract',return_value={'fixture':'contract'}))
            stack.enter_context(patch('civiclab.production_compatibility_v4_1.validate_execution_release'))
            stack.enter_context(patch('civiclab.production_compatibility_v4_1.execute_compatibility',execute))
            stack.enter_context(patch('civiclab.production_admission_v4.make_context',return_value={'fixture':'context'}))
            stack.enter_context(patch('civiclab.production_owner_v4.request_binding',return_value='3'*64))
            return module.main()

    def test_one_linked_renewal_one_execute_and_no_second_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); _,pref,owner,_=self.setup_fixture(root)
            execute=Mock(return_value={'summary':{'status':'AUTHORED_ONLY'}})
            self.assertEqual(self.run_fixture(root,pref,owner,execute),0)
            owner.grant_operator_authorization.assert_called_once()
            approval=owner.grant_operator_authorization.call_args.args[0]
            self.assertEqual(approval['previous_approval_hash'],owner.snapshot.return_value['approval_hash'])
            self.assertEqual(approval['total_microusd'],1000)
            self.assertEqual(approval['total_dispatches'],1)
            execute.assert_called_once()
            with self.assertRaises(FileExistsError): self.run_fixture(root,pref,owner,execute)
            self.assertEqual(execute.call_count,1)
            self.assertEqual(owner.grant_operator_authorization.call_count,1)

    def test_prior_charge_dispatch_or_statistics_refuse_without_grant(self):
        for attack in ('charge','dispatch','statistics','approval'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve(); _,pref,owner,_=self.setup_fixture(root)
                snap=owner.snapshot.return_value
                if attack=='charge': snap['charges']=[{'authored':'charge'}]
                elif attack=='dispatch': snap['consumed_microusd']['dispatches']=1
                elif attack=='statistics': snap['statistics_claimed_receipts']=['authored']
                else: snap['approval_hash']='9'*64
                execute=Mock()
                with self.assertRaises(ValueError):self.run_fixture(root,pref,owner,execute)
                owner.grant_operator_authorization.assert_not_called(); execute.assert_not_called()
                self.assertFalse((root/module.HANDOFF).exists())

    def test_original_journal_change_refuses_without_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); _,pref,owner,_=self.setup_fixture(root)
            (root/'data/processed/compatibility_runs/compatibility-20261103-gpt41nano-02/extra.local.json').write_text('{}')
            with self.assertRaises(ValueError):self.run_fixture(root,pref,owner,Mock())
            owner.grant_operator_authorization.assert_not_called()

    def test_executor_failure_is_retained_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); _,pref,owner,_=self.setup_fixture(root)
            execute=Mock(side_effect=ValueError('AUTHORED_FAILURE'))
            self.assertEqual(self.run_fixture(root,pref,owner,execute),1)
            failure=json.loads((root/module.HANDOFF/'failure.local.json').read_text())
            self.assertEqual(failure['status'],'STOPPED_NO_RETRY')
            with self.assertRaises(FileExistsError):self.run_fixture(root,pref,owner,execute)
            self.assertEqual(execute.call_count,1)

    def test_packet_tamper_refuses_and_key_confirmation_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); _,pref,owner,_=self.setup_fixture(root)
            with self.assertRaises(SystemExit):self.run_fixture(root,pref,owner,Mock(),confirm=False)
            p=root/module.PACKET;p.write_bytes(p.read_bytes()+b' ')
            with self.assertRaises(ValueError):self.run_fixture(root,pref,owner,Mock())
            owner.grant_operator_authorization.assert_not_called()


if __name__=='__main__':unittest.main()
