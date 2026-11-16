"""Authored finite controller and fabricated-module checks. Never run real pip.

The original frozen test guard enforces120s/64MiB reads/32MiB writes/256KiB
output. An earlier hook also covers the transitive loader and forbids actual
socket/process/native operations and pip imports. All mutable states are mocks.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def no_actual(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty',
        'os.posix_spawn','os.system','os.exec','os.spawn','ctypes.dlopen'}:
        raise AssertionError('AUTHORED_NO_ACTUAL_SOCKET_PROCESS_NATIVE')
    if event == 'import' and args and (args[0]=='pip' or args[0].startswith('pip.')):
        raise AssertionError('AUTHORED_NO_ACTUAL_PIP_IMPORT')
sys.addaudithook(no_actual)
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

d=load('authored_compatibility_v1',ROOT/'scripts/validate_e01_offline_ipv6_compatibility_v1_1_20261116.py')
g=load('authored_accepted_diagnostic_v2',ROOT/'tests/test_e01_pypdf701_guard_diagnostic_v2.py')
g.d=d.r;g.g.d=d.q;g.f.p=d.p;g.f.old.p=d.p;g.f.old.t.p=d.p
g.ORIGINAL_READER=d.p.Reader
A=d.a


def receipt(root,binding):
    name=binding['pip_root']+'/_vendor/urllib3/util/connection.py'
    return {'kind':'E01_OFFLINE_IPV6_COMPATIBILITY_RECEIPT_V1_1','original_has_ipv6':True,
        'temporary_has_ipv6':False,'restored_has_ipv6':True,'vendor_cached_ipv6':False,
        'target_module':A.TARGET,'socket_ref':{'path':str(Path(binding['base_prefix'])/'lib/python3.12/socket.py'),**A.SOCKET_REF},
        'import_closure':[{'name':A.TARGET,'origin':str(root/name),'source_ref':{'path':name,**binding['pip_files'][name]}}],
        'closure_logical_read_bytes':binding['pip_files'][name]['bytes']+1,
        'network_permissions_changed':False,'parent_transitive_consumers_may_observe_false':True}


def maximal_receipt(root, binding):
    """256 valid entries, exact131072B without whitespace padding."""
    value=receipt(root,binding)
    target=value['import_closure'][0]
    items=[dict(copy.deepcopy(target),name='MOCK_%03d_'%i) for i in range(255)]+[target]
    value['import_closure']=sorted(items,key=lambda row:row['name'])
    for row in value['import_closure']:
        if row['name']==A.TARGET:continue
        remaining=131072-len(d.packed(value))
        if remaining<=0:break
        row['name']+='x'*min(remaining,256-len(row['name']))
    raw=d.packed(value)
    if len(raw)!=131072:raise AssertionError(('MAXIMAL_VALID_RECEIPT_SHAPE',len(raw)))
    return raw


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache=patch.object(d.p,'Reader',g.temporary_fixture_reader());cls.cache.start()
        cls.addClassCleanup(cls.cache.stop)
        # Add a visibly authored connection source before any mock binding is
        # frozen; all old full ancestry validators still run unchanged.
        oldclass=g.f.old.t.InstallerFixtureTests
        original=oldclass.save
        def save_with_source(self,name,raw):
            if name=='data/processed/MOCK_INSTALLER_BINDING/binding.json':
                connection=self.binding['pip_root']+'/_vendor/urllib3/util/connection.py'
                ref=original(self,connection,b'# MOCK SOURCE NEVER IMPORTED\n')
                self.binding['pip_files'][connection]={k:ref[k] for k in ('bytes','sha256')}
                self.binding['counts']['files']+=1
                self.binding['counts']['directories']+=3
                self.binding['counts']['total_bytes']+=ref['bytes']
                raw=d.packed(self.binding)
            return original(self,name,raw)
        with patch.object(oldclass,'save',save_with_source):
            cls.prior=g.DiagnosticFixtureTests('test_no_refusal_is_only_diagnostic_and_preserves_all_old_roots')
            cls.prior.setUp()
        cls.addClassCleanup(cls.prior.doCleanups)
        cls.root=cls.prior.root;cls.binding=cls.prior.old.binding
        def refused(command,env,root,budget,number):
            result=cls.prior.launcher(command,env,root,budget,number)
            observer=d.c.RefusalJournal();observer.record('GUEST_NETWORK_HELPER_OR_CTYPES_DENIED','SOCKET_CONSTRUCT')
            (root/d.r.OUTPUT/'guest-refusals.json').write_bytes(observer.packed())
            path=root/d.r.OUTPUT/'guest-result.json';value=d.json_body(path.read_bytes())
            value.update(guard_violations=1,error_code='GUEST_CAUGHT_VIOLATION');path.write_bytes(d.packed(value))
            result.update(exit_code=1,output=[])
            for suffix,body in [('stdout',b'MOCK WOULD INSTALL\n'),('stderr',b'GUEST_CAUGHT_VIOLATION\n')]:
                name='1-'+suffix+'.bin';(root/d.r.OUTPUT/name).write_bytes(body)
                result['output'].append({'path':name,'bytes':len(body),'sha256':d.sha(body)})
                budget.output+=len(body)
            return result
        result=cls.prior.execute(refused)
        if result['outcome']!='REFUSAL_OBSERVED':raise AssertionError(result)
        cls.base=d.json_body((ROOT/d.METHODS).read_bytes())
        cls.base['root_sha256']=d.sha(str(cls.root).encode())
        for ref in (d.PRIOR_V2_REF,d.ADAPTER_REF,d.DECISION_REF,d.PURE_REVIEW_REF,d.V2_ACTUAL_REF,d.V1_REVIEW_REF):
            cls.prior.save(ref['path'],(ROOT/ref['path']).read_bytes())
        for ref in d.V1_PRESERVED_REFS:
            cls.prior.save(ref['path'],(ROOT/ref['path']).read_bytes())
        cls.base['prior_v2_methods_ref']=cls.prior.ref(d.r.METHODS)
        cls.constant=patch.object(d,'PRIOR_V2_METHODS_REF',cls.base['prior_v2_methods_ref']);cls.constant.start()
        cls.addClassCleanup(cls.constant.stop)
        cls.base['prior_v2_refs']={'packet':cls.prior.save('data/processed/e01_pypdf701_build_v1/diagnostic-v2-packet-20261116.json',d.packed(cls.prior.packet))}
        for name in ('TERMINAL.json','STARTED.json','requirements.txt','guest-payload.json','1-COMMAND_RESERVED.json',
                     '1-COMMAND_RECORDED.json','1-stdout.bin','1-stderr.bin','guest-refusals.json','guest-result.json'):
            cls.base['prior_v2_refs'][name]=cls.prior.ref(d.r.OUTPUT+'/'+name)
        cls.code_ref=cls.prior.save(d.CODE_PATH,(ROOT/d.CODE_PATH).read_bytes())

    def setUp(self):
        self.methods=copy.deepcopy(self.base);self.calls=[];self.time=[0.0]
        self.rebind()
    def tearDown(self):
        for name in (d.OUTPUT,d.TARGET):
            path=self.root/name
            if path.exists():shutil.rmtree(path)
    def rebind(self):
        self.prior.save(d.METHODS,d.packed(self.methods))
        core={'kind':'E01_OFFLINE_COMPATIBILITY_EXECUTION_PACKET_V1_1','root_sha256':self.methods['root_sha256'],
              'methods_sha256':d.sha(d.packed(self.methods)),'diagnostic_code_ref':self.code_ref,'execution_enabled':True}
        review={'status':'PASS_MOCK_ONLY_NOT_REAL_RELEASE','reviewed_packet_core_sha256':d.sha(d.packed(core)),
                'evidence_refs':{d.CODE_PATH:self.code_ref,d.METHODS:self.prior.ref(d.METHODS)}}
        self.packet={**core,'review_ref':self.prior.save('reports/INDEPENDENT_AUDIT_MOCK_COMPATIBILITY.json',d.packed(review))}
    def launcher(self,command,env,root,budget,number):
        self.calls.append((command,env,number));scope=root/d.OUTPUT
        payload=d.json_body((scope/'guest-payload.json').read_bytes())
        (scope/'guest-refusals.json').write_bytes(d.c.RefusalJournal().packed())
        (scope/'guest-compatibility.json').write_bytes(d.packed(receipt(root,self.binding)))
        value={'kind':'E01_OFFLINE_COMPATIBILITY_GUEST_RESULT_V1_1','pip_arguments_sha256':d.sha(d.packed(payload['pip_arguments'])),
               'guard_violations':0,'pip_completed':True,'error_code':None,'mime_configuration':d.p.MIME_RECEIPT,
               'installation_accepted':False,'downloaded_package_imports':False,'target_exists':False}
        (scope/'guest-result.json').write_bytes(d.packed(value))
        return {'exit_code':0,'pip_helper_descendants_permitted':0,'output':[],'observed_reaped_CPU_seconds':0}
    def execute(self,launch=None):
        return d.execute(self.root,self.methods,self.packet,launcher=launch or self.launcher,clock=lambda:self.time[0])
    def test_compatible_fixture_preserves_eight_roots_and_no_target(self):
        before=d.snapshot(self.root);result=self.execute()
        self.assertEqual(result['outcome'],'COMPATIBLE_OFFLINE_CONFIGURATION');self.assertFalse(result['installation_accepted'])
        self.assertEqual(d.snapshot(self.root),before);self.assertFalse((self.root/d.TARGET).exists())
        command,env,number=self.calls[0]
        self.assertEqual(command[0],self.binding['executable_ref']['path']);self.assertEqual(command[1:4],['-I','-B','-S'])
        self.assertEqual(env['PATH'],str(Path(self.binding['base_prefix'])/'bin')+':/usr/bin:/bin')
        self.assertEqual(number,1)
        terminal=d.json_body((self.root/d.OUTPUT/'TERMINAL.json').read_bytes())
        self.assertEqual(terminal['allocation'],d.ALLOCATION);self.assertEqual(terminal['prior']['actual_prior_commands_started'],8)
        self.assertEqual(terminal['combined_logical_bytes_including_terminal'],d.owned_size(self.root))
    def test_scope_is_once_only(self):
        self.execute();self.calls.clear()
        with self.assertRaisesRegex(d.Refused,'DIAGNOSTIC_ALREADY_CONSUMED'):self.execute()
        self.assertFalse(self.calls)
    def test_preexisting_target_refuses(self):
        (self.root/d.TARGET).mkdir()
        with self.assertRaisesRegex(d.Refused,'DIAGNOSTIC_ALREADY_CONSUMED'):self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())
    def test_no_execution_from_disabled_methods_or_missing_packet(self):
        self.packet['execution_enabled']=False
        with self.assertRaisesRegex(d.Refused,'DIAGNOSTIC_EXPLICIT_RELEASE_REQUIRED'):self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists())
    def test_prior_allocations_cannot_reset(self):
        self.methods['allocation']['prior_main_commands']=0;self.rebind()
        with self.assertRaisesRegex(d.Refused,'COMPATIBILITY_METHODS_IDENTITY'):self.execute()
    def test_particular_review_must_match(self):
        ref=self.packet['review_ref'];value=d.json_body((self.root/ref['path']).read_bytes());value['reviewed_packet_core_sha256']='0'*64
        self.packet['review_ref']=self.prior.save(ref['path'],d.packed(value))
        with self.assertRaisesRegex(d.Refused,'DIAGNOSTIC_EXACT_PARTICULAR_REVIEW'):self.execute()
    def test_changed_v2_control_refuses_before_scope(self):
        path=self.root/d.r.OUTPUT/'guest-refusals.json';raw=path.read_bytes()
        try:
            path.write_bytes(b'X'+raw[1:])
            with self.assertRaisesRegex(d.Refused,'INPUT_HASH'):self.execute()
        finally:path.write_bytes(raw)
    def test_residual_refusal_stays_failed_without_counter_reset(self):
        def denied(*args):
            result=self.launcher(*args);scope=self.root/d.OUTPUT
            journal=d.c.RefusalJournal();journal.record('GUEST_NETWORK_HELPER_OR_CTYPES_DENIED','SOCKET_CONNECT')
            (scope/'guest-refusals.json').write_bytes(journal.packed())
            path=scope/'guest-result.json';value=d.json_body(path.read_bytes());value.update(guard_violations=1,error_code='GUEST_CAUGHT_VIOLATION')
            path.write_bytes(d.packed(value));result['exit_code']=1;return result
        self.assertEqual(self.execute(denied)['outcome'],'REFUSAL_OBSERVED')
    def test_missing_compatibility_receipt_cannot_pass(self):
        def missing(*args):
            result=self.launcher(*args);(self.root/d.OUTPUT/'guest-compatibility.json').unlink();return result
        self.assertEqual(self.execute(missing)['outcome'],'FAILED_COMPATIBILITY')
    def test_false_restore_receipt_fails(self):
        def bad(*args):
            result=self.launcher(*args);path=self.root/d.OUTPUT/'guest-compatibility.json'
            value=d.json_body(path.read_bytes());value['restored_has_ipv6']=False;path.write_bytes(d.packed(value));return result
        self.assertEqual(self.execute(bad)['outcome'],'FAILED_COMPATIBILITY')
    def test_child_failure_does_not_retry(self):
        def stopped(*args):
            self.calls.append('MOCK');raise d.CommandStopped('MOCK_STOP',{'exit_code':-9})
        self.assertEqual(self.execute(stopped)['outcome'],'FAILED_COMPATIBILITY');self.assertEqual(len(self.calls),1)
    def test_new_target_after_child_cannot_pass(self):
        def bad(*args):
            result=self.launcher(*args);(self.root/d.TARGET).mkdir();return result
        self.assertEqual(self.execute(bad)['outcome'],'FAILED_COMPATIBILITY')
    def test_deadline_prevents_child(self):
        def clock():self.time[0]+=31;return self.time[0]
        with self.assertRaisesRegex(d.Refused,'P2_WALL_LIMIT'):
            d.execute(self.root,self.methods,self.packet,launcher=self.launcher,clock=clock)
        self.assertFalse(self.calls)
    def test_receipt_pinned_vendor_hash_cannot_drift(self):
        value=receipt(self.root,self.binding);value['import_closure'][0]['source_ref']['sha256']='0'*64
        with self.assertRaisesRegex(d.Refused,'COMPATIBILITY_RECEIPT_PIP_PIN'):
            d.validate_compatibility_receipt(d.packed(value),self.binding,self.root)
    def test_receipt_unknown_origin_cannot_pass(self):
        value=receipt(self.root,self.binding);value['import_closure'][0]['origin']='/outside/evil.py'
        with self.assertRaisesRegex(d.Refused,'COMPATIBILITY_RECEIPT_ORIGIN'):
            d.validate_compatibility_receipt(d.packed(value),self.binding,self.root)
    def test_large_valid_closure_is_bound_without_terminal_embedding(self):
        raw=maximal_receipt(self.root,self.binding)
        self.assertEqual(len(d.validate_compatibility_receipt(raw,self.binding,self.root)['import_closure']),256)
        def large(*args):
            result=self.launcher(*args);(self.root/d.OUTPUT/'guest-compatibility.json').write_bytes(raw);return result
        self.assertEqual(self.execute(large)['outcome'],'COMPATIBLE_OFFLINE_CONFIGURATION')
        terminal_raw=(self.root/d.OUTPUT/'TERMINAL.json').read_bytes();terminal=d.json_body(terminal_raw)
        bound=terminal['compatibility']
        self.assertLessEqual(len(terminal_raw),32768);self.assertTrue(bound['validated'])
        self.assertEqual(bound['ref'],{'path':'guest-compatibility.json','bytes':131072,'sha256':d.sha(raw)})
        self.assertEqual(bound['summary']['closure_entries'],256)
        self.assertNotIn('import_closure',bound['summary']);self.assertLessEqual(len(d.packed(bound)),1536)
        self.assertEqual((self.root/d.OUTPUT/'guest-compatibility.json').read_bytes(),raw)
    def test_stopped_child_still_binds_and_validates_full_large_receipt(self):
        raw=maximal_receipt(self.root,self.binding)
        def stopped(*args):
            self.launcher(*args);(self.root/d.OUTPUT/'guest-compatibility.json').write_bytes(raw)
            raise d.CommandStopped('MOCK_STOP_WITH_RECEIPT',{'exit_code':-9,'stopped':True})
        self.assertEqual(self.execute(stopped)['outcome'],'FAILED_COMPATIBILITY')
        terminal_raw=(self.root/d.OUTPUT/'TERMINAL.json').read_bytes();terminal=d.json_body(terminal_raw)
        self.assertLessEqual(len(terminal_raw),32768);self.assertTrue(terminal['compatibility']['validated'])
        self.assertEqual(terminal['compatibility']['ref']['sha256'],d.sha(raw))
    def test_invalid_bounded_evidence_retains_exact_binding_on_error(self):
        raw=b'{"MOCK_INVALID":true}'
        def stopped(*args):
            self.launcher(*args);(self.root/d.OUTPUT/'guest-compatibility.json').write_bytes(raw)
            raise d.CommandStopped('MOCK_STOP_INVALID_RECEIPT',{'exit_code':-9})
        self.assertEqual(self.execute(stopped)['outcome'],'FAILED_COMPATIBILITY')
        terminal=d.json_body((self.root/d.OUTPUT/'TERMINAL.json').read_bytes())
        self.assertFalse(terminal['compatibility']['validated'])
        self.assertEqual(terminal['compatibility']['ref']['sha256'],d.sha(raw))
        self.assertEqual(terminal['compatibility']['error_code'],'COMPATIBILITY_RECEIPT_SCHEMA')
        self.assertEqual((self.root/d.OUTPUT/'guest-compatibility.json').read_bytes(),raw)
    def test_saved_actual_ancestry_and_maximum_closure_fit_terminal(self):
        fixture=d.json_body((ROOT/'reports/e01_offline_ipv6_compatibility_v1_1_ancestry_headroom_fixture_20261116.json').read_bytes())
        proof=d.terminal_headroom(fixture['prior'],fixture['before_shape'])
        self.assertLessEqual(proof['maximum_supported_total'],32768)
        original=d.verify_inputs
        def with_saved_ancestry(*args):
            inputs=original(*args);inputs['prior']=copy.deepcopy(fixture['prior']);return inputs
        raw=maximal_receipt(self.root,self.binding)
        def large(*args):
            result=self.launcher(*args);(self.root/d.OUTPUT/'guest-compatibility.json').write_bytes(raw);return result
        with patch.object(d,'verify_inputs',side_effect=with_saved_ancestry):
            self.assertEqual(self.execute(large)['outcome'],'COMPATIBLE_OFFLINE_CONFIGURATION')
        terminal_raw=(self.root/d.OUTPUT/'TERMINAL.json').read_bytes();value=d.json_body(terminal_raw)
        self.assertEqual(value['prior'],fixture['prior']);self.assertLessEqual(len(terminal_raw),32768)
        self.assertTrue(value['compatibility']['validated']);self.assertEqual(value['compatibility']['ref']['bytes'],131072)
        print(json.dumps({'kind':'AUTHORED_SAVED_ANCESTRY_MAX_CLOSURE_HEADROOM',
            'actual_current_state_validated':False,'preserved_prior_bytes':len(d.packed(fixture['prior'])),
            'maximum_receipt_bytes':len(raw),'terminal_bytes':len(terminal_raw),'terminal_cap':32768,
            'headroom_proof':proof},sort_keys=True))
    def test_ancestry_headroom_refuses_before_scope(self):
        original=d.verify_inputs
        def excessive(*args):
            inputs=original(*args);inputs['prior']={'MOCK_TOO_LARGE':'x'*22000};return inputs
        with patch.object(d,'verify_inputs',side_effect=excessive):
            with self.assertRaisesRegex(d.Refused,'COMPATIBILITY_TERMINAL_ANCESTRY_HEADROOM'):self.execute()
        self.assertFalse((self.root/d.OUTPUT).exists());self.assertFalse(self.calls)
    def test_superseded_v1_scope_must_stay_absent(self):
        path=self.root/d.SUPERSEDED_ABSENT[0];path.mkdir(parents=True)
        try:
            with self.assertRaisesRegex(d.Refused,'COMPATIBILITY_SUPERSEDED_SCOPE_NOT_ABSENT'):self.execute()
            self.assertFalse((self.root/d.OUTPUT).exists())
        finally:shutil.rmtree(path)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.active=patch.object(A,'_ACTIVE',None);self.failed=patch.object(A,'_FAILED',False)
        self.active.start();self.failed.start();self.addCleanup(self.active.stop);self.addCleanup(self.failed.stop)
        self.socket=ModuleType('MOCK_SOCKET');self.socket.has_ipv6=True
    def run_scope(self,initialize,check=lambda value:None):return A.scoped(self.socket,initialize,check)
    def test_success_restores_exact_mock_flag(self):
        def initialize():self.assertIs(self.socket.has_ipv6,False);return 'MOCK'
        self.assertEqual(self.run_scope(initialize),'MOCK');self.assertIs(self.socket.has_ipv6,True)
    def test_caught_reentry_poison_is_sticky(self):
        def initialize():
            try:self.run_scope(lambda:None)
            except A.CompatibilityRefused:pass
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_STICKY_FAILURE'):self.run_scope(initialize)
        self.assertTrue(A._FAILED);self.assertIs(self.socket.has_ipv6,True)
    def test_public_failure_reset_does_not_clear_owner(self):
        def initialize():
            try:self.run_scope(lambda:None)
            except A.CompatibilityRefused:pass
            A._FAILED=False
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_STICKY_FAILURE'):self.run_scope(initialize)
    def test_reentry_propagates_and_restores(self):
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_REENTRY'):
            self.run_scope(lambda:self.run_scope(lambda:None))
        self.assertIs(self.socket.has_ipv6,True);self.assertIsNone(A._ACTIVE)
    def test_primary_exception_identity_preserved(self):
        error=RuntimeError('MOCK_PRIMARY')
        def initialize():
            try:self.run_scope(lambda:None)
            except A.CompatibilityRefused:pass
            raise error
        with self.assertRaises(RuntimeError) as caught:self.run_scope(initialize)
        self.assertIs(caught.exception,error);self.assertIs(self.socket.has_ipv6,True)
    def test_baseexception_restores_and_no_retry(self):
        def interrupt():raise KeyboardInterrupt('MOCK')
        with self.assertRaises(KeyboardInterrupt):self.run_scope(interrupt)
        self.assertIs(self.socket.has_ipv6,True)
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_PRIOR_FAILURE_NO_RETRY'):self.run_scope(lambda:None)
    def test_exact_module_before_reentry_poison(self):
        owner=A.Owner();A._ACTIVE=owner
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_EXACT_SOCKET_MODULE'):
            A.scoped(SimpleNamespace(has_ipv6=True),lambda:None,lambda value:None)
        self.assertFalse(owner.poisoned)
    def test_false_original_refuses_without_callback(self):
        self.socket.has_ipv6=False
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_ORIGINAL_NOT_TRUE'):self.run_scope(lambda:self.fail('called'))
    def test_owner_change_refuses_and_restores(self):
        with patch.object(A.threading,'active_count',return_value=2):
            with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_PROCESS_THREAD_OWNER'):self.run_scope(lambda:None)
        self.assertIs(self.socket.has_ipv6,True)
    def test_final_owner_change_refuses_and_restores(self):
        with patch.object(A.threading,'active_count',side_effect=[1,2]):
            with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_PROCESS_THREAD_OWNER'):self.run_scope(lambda:None)
        self.assertIs(self.socket.has_ipv6,True)
    def test_exit_drift_refused_but_transient_restoration_not_observed(self):
        def drift():self.socket.has_ipv6=True
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_SCOPE_DRIFT'):self.run_scope(drift)
        A._FAILED=False
        def transient():self.socket.has_ipv6=True;self.socket.has_ipv6=False
        self.run_scope(transient);self.assertIs(self.socket.has_ipv6,True)
    def test_result_check_error_preserves_primary(self):
        error=ValueError('MOCK_RESULT')
        def check(value):raise error
        with self.assertRaises(ValueError) as caught:self.run_scope(lambda:None,check)
        self.assertIs(caught.exception,error);self.assertIs(self.socket.has_ipv6,True)
    def test_real_api_rejects_fabricated_socket_origin(self):
        with patch.dict(A.sys.modules,{'socket':self.socket}):
            with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_EXACT_SOCKET_MODULE'):
                A.initialize_offline(ROOT,{},None)
    def test_residual_guard_denial_is_never_waived(self):
        with tempfile.TemporaryDirectory(prefix='compatibility-MOCK-') as temp:
            root=Path(temp).resolve();binding={'base_prefix':str(root/'base'),'pip_root':'MOCK_PIP','pip_files':{},'pip_metadata_ref':{'path':'MOCK_METADATA'}}
            policy=d.compatibility_policy_class(d.p.GuestPolicy)(root,binding,{'wheels':[],'remaining_output_bytes':1024})
            for event in ('socket.__new__','socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','ctypes.dlopen'):
                with self.assertRaises(d.Refused):self.run_scope(lambda:policy.audit(event,()))
                self.assertIs(self.socket.has_ipv6,True);A._FAILED=False
            self.assertEqual(policy.violations,6)
            with self.assertRaisesRegex(d.Refused,'GUEST_CAUGHT_VIOLATION'):d.need(policy.violations==0,'GUEST_CAUGHT_VIOLATION')
            self.assertEqual(d.validate_journal(policy.refusal_journal.packed())['total_events'],6)


class PublicFacadeMockTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='facade-MOCK-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.socket=ModuleType('socket');self.socket.has_ipv6=True
        self.path=self.root/'mockpip/_vendor/urllib3/util/connection.py';self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'import socket\nHAS_IPV6=False\ndef _has_ipv6(): return False\n')
        self.binding={'base_prefix':str(self.root/'base'),'pip_root':'mockpip',
            'pip_files':{str(self.path.relative_to(self.root)):{'bytes':self.path.stat().st_size,
                'sha256':hashlib.sha256(self.path.read_bytes()).hexdigest()}}}
        self.patchers=[patch.object(A,'_ACTIVE',None),patch.object(A,'_FAILED',False),
            patch.object(A,'checked_socket',return_value=self.socket),patch.dict(A.sys.modules,{'socket':self.socket})]
        for p in self.patchers:p.start();self.addCleanup(p.stop)
    def initialize(self):
        module=ModuleType(A.TARGET);module.__file__=str(self.path)
        module.__spec__=importlib.util.spec_from_file_location(A.TARGET,self.path)
        exec(compile(self.path.read_bytes(),str(self.path),'exec'),module.__dict__)
        sys.modules[A.TARGET]=module
        self.addCleanup(sys.modules.pop,A.TARGET,None)
        return module
    def run_facade(self):
        with patch.object(A.importlib,'import_module',side_effect=lambda name:self.initialize()):
            return A.initialize_offline(self.root,self.binding,d.p.Reader(self.root))
    def test_fabricated_facade_records_closure_and_surviving_cache(self):
        finders=tuple(sys.meta_path)
        value=self.run_facade()
        self.assertIs(self.socket.has_ipv6,True);self.assertIs(sys.modules[A.TARGET].HAS_IPV6,False)
        self.assertEqual(tuple(sys.meta_path),finders);self.assertFalse(A._imp.lock_held())
        self.assertTrue(value['parent_transitive_consumers_may_observe_false'])
        self.assertEqual(value['import_closure'][0]['name'],A.TARGET)
    def test_preloaded_vendor_rejected_before_override(self):
        with patch.dict(sys.modules,{A.PREFIX:ModuleType(A.PREFIX)}):
            with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_VENDOR_PRELOADED'):self.run_facade()
        self.assertIs(self.socket.has_ipv6,True)
    def test_initializing_module_rejected_before_override(self):
        module=ModuleType('MOCK_INITIALIZING');module.__spec__=SimpleNamespace(_initializing=True)
        with patch.dict(sys.modules,{'MOCK_INITIALIZING':module}):
            with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_IMPORT_IN_PROGRESS'):self.run_facade()
        self.assertIs(self.socket.has_ipv6,True)
    def test_import_lock_owned_elsewhere_refused_before_override(self):
        with patch.object(A._imp,'lock_held',return_value=True):
            with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_IMPORT_IN_PROGRESS'):self.run_facade()
        self.assertIs(self.socket.has_ipv6,True)
    def test_vendor_result_drift_refused_and_restored(self):
        old=self.initialize
        def wrong():
            module=old();module.HAS_IPV6=True;return module
        with patch.object(self,'initialize',side_effect=wrong):
            with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_VENDOR_RESULT'):self.run_facade()
        self.assertIs(self.socket.has_ipv6,True);self.assertTrue(A._FAILED)
        self.assertFalse(A._imp.lock_held())


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='closure-MOCK-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.base=self.root/'base';self.pip=self.root/'mockpip'
        self.source=self.pip/'module.py';self.source.parent.mkdir();self.source.write_bytes(b'# MOCK NEVER EXECUTED\n')
        self.binding={'base_prefix':str(self.base),'pip_files':{'mockpip/module.py':{'bytes':self.source.stat().st_size,'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest()}}}
        self.closure=A.Closure(self.root,self.binding,d.p.Reader(self.root))
    def test_pinned_vendor_spec_records_without_execution(self):
        spec=importlib.util.spec_from_file_location('MOCK_MODULE',self.source)
        self.closure.spec('MOCK_MODULE',spec)
        self.assertIn('MOCK_MODULE',self.closure.names);self.assertNotIn('MOCK_MODULE',sys.modules)
    def test_changed_pinned_vendor_source_refuses(self):
        self.source.write_bytes(b'X'*self.source.stat().st_size)
        with self.assertRaisesRegex(d.Refused,'INPUT_HASH'):self.closure.source(self.source)
    def test_unknown_origin_refuses_before_execution(self):
        path=self.root/'outside.py';path.write_bytes(b'raise AssertionError()\n')
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_UNBOUND_IMPORT_ORIGIN'):
            self.closure.spec('MOCK_UNKNOWN',importlib.util.spec_from_file_location('MOCK_UNKNOWN',path))
    def test_custom_loader_refused(self):
        spec=importlib.machinery.ModuleSpec('MOCK_CUSTOM',object(),origin=str(self.source))
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_IMPORT_LOADER'):self.closure.spec('MOCK_CUSTOM',spec)
    def test_module_cap_refuses(self):
        self.closure.names={str(i):{} for i in range(A.MAX_MODULES)}
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_CLOSURE_MODULE_CAP'):
            self.closure.spec('MOCK_EXTRA',importlib.util.spec_from_file_location('MOCK_EXTRA',self.source))
    def test_read_cap_refuses(self):
        self.closure.bytes=A.MAX_SOURCE_BYTES
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_CLOSURE_READ_CAP'):self.closure.source(self.source)
    def test_optional_absence_is_recorded_without_import(self):
        self.closure.previous_finders=()
        with self.assertRaises(ModuleNotFoundError) as caught:self.closure.find_spec('MOCK_ABSENT')
        self.assertEqual(caught.exception.name,'MOCK_ABSENT')
        self.assertEqual(str(caught.exception),"No module named 'MOCK_ABSENT'")
        self.assertEqual(self.closure.names['MOCK_ABSENT']['origin'],'not-found')
    def test_origin_alias_refuses(self):
        alias=self.root/'alias.py';alias.symlink_to(self.source)
        with self.assertRaisesRegex(A.CompatibilityRefused,'COMPATIBILITY_ORIGIN_ALIAS'):self.closure.source(alias)
    def test_stdlib_observation_is_bounded_and_explicitly_not_prepinned(self):
        path=self.base/'lib/python3.12/mock_stdlib.py';path.parent.mkdir(parents=True);path.write_bytes(b'# MOCK STDLIB\n')
        ref=self.closure.source(path)
        self.assertEqual(ref['path'],str(path));self.assertEqual(ref['bytes'],path.stat().st_size)
        self.assertEqual(self.closure.bytes,2*(ref['bytes']+1))
        self.assertNotIn(str(path),self.binding['pip_files'])


class FrozenStructureTests(unittest.TestCase):
    def test_original_guard_wrappers_retained_with_explicit_routing_and_source_allowance(self):
        old=ast.parse((ROOT/d.PRIOR_V2_REF['path']).read_bytes());new=ast.parse((ROOT/d.CODE_PATH).read_bytes())
        before=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='install_guard')
        after=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='install_guard')
        for body in (before.body,after.body):
            for node in body:
                if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='policy' for t in node.targets):
                    node.value=ast.parse('MOCK_EXPLICIT_ROUTE',mode='eval').body
            body[:]=[n for n in body if not (isinstance(n,ast.Expr) and 'policy.exact_reads.update' in ast.unparse(n))]
        self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False))
    def test_capture_guard_and_budget_semantics_retained(self):
        old=ast.parse((ROOT/d.PRIOR_V2_REF['path']).read_bytes());new=ast.parse((ROOT/d.CODE_PATH).read_bytes())
        for name in ('run_command','StageBudget','Journal','validate_journal','logical_scope_size'):
            before=next(n for n in old.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name)
            after=next(n for n in new.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name)
            self.assertEqual(ast.dump(before,include_attributes=False),ast.dump(after,include_attributes=False),name)
    def test_old_frozen_runner_observer_adapter_hashes_retained(self):
        for ref in (d.PRIOR_V2_REF,d.FROZEN_REF,d.CANDIDATE_REF,d.ADAPTER_REF):
            raw=(ROOT/ref['path']).read_bytes();self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256'])
    def test_stdlib_socket_origin_record_only_no_mutation(self):
        module=sys.modules['socket'];path=Path(module.__file__)
        expected={'3.12.14':(37815,'7d4d4c66e6f4bcc961ab462c4f08002ca97def8713a4be1c7373bdbd970a5274'),
                  '3.11.17':(37557,'64360e73e3db69396d45d5ee256e8306b3653212ab96ae4a130070488cddbb30')}
        raw=path.read_bytes();self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),expected[sys.version.split()[0]])
        print(json.dumps({'kind':'AUTHORED_TRANSITIVE_STDLIB_SOCKET_ORIGIN','origin':str(path),'bytes':len(raw),
                          'sha256':hashlib.sha256(raw).hexdigest(),'python':sys.version.split()[0],
                          'actual_socket_operations':0,'socket_global_mutations':0,'pip_import':False},sort_keys=True))


if __name__=='__main__':g.f.old.g.old.guarded_test_main()
