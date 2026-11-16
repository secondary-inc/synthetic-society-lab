"""Pure state models and direct frozen guard callbacks; no actual socket/pip."""
import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

m=load('mock_ipv6_configuration',ROOT/'scripts/e01_offline_ipv6_probe_mock_candidate_v1_20261116.py')
p=load('frozen_guard_for_mock_ipv6',ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py')
o=load('frozen_observer_for_mock_ipv6',ROOT/'scripts/e01_p2_refusal_observability_candidate_v3_20261116.py')
t=load('frozen_authored_bounds_for_mock_ipv6',ROOT/'tests/test_e01_pypdf701_install_v1_3.py')


class MockIpv6ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='e01-ipv6-PURE-MOCK-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        binding={'base_prefix':str(self.root/'MOCK_BASE'),'pip_root':'MOCK_PIP/pip',
                 'pip_files':[],'pip_metadata_ref':{'path':'MOCK_PIP/pip.dist-info/METADATA'}}
        self.guard=o.recording_policy_class(p.GuestPolicy)(self.root,binding,{'wheels':[],'remaining_output_bytes':1024})
        self.socket=m.MockSocketState();self.vendor=m.MockVendorState()

    def initialize(self,socket,vendor):
        return m.initialize_probe_model(socket,vendor,self.guard.audit)

    def test_original_mock_probe_catches_denial_but_postcondition_still_fails(self):
        self.assertFalse(self.initialize(self.socket,self.vendor))
        self.assertEqual(self.guard.violations,1)
        self.assertTrue(self.socket.has_ipv6)
        with self.assertRaisesRegex(p.Refused,'GUEST_CAUGHT_VIOLATION'):
            p.need(self.guard.violations == 0,'GUEST_CAUGHT_VIOLATION')

    def test_scoped_mock_avoids_only_optional_probe_and_restores_flag(self):
        receipt=m.scoped_mock_initialization(self.socket,self.vendor,self.initialize)
        self.assertEqual(self.guard.violations,0)
        self.assertIs(self.socket.has_ipv6,True)
        self.assertIs(self.vendor.cached_ipv6,False)
        self.assertTrue(self.vendor.initialized)
        self.assertFalse(self.vendor.scope_active)
        self.assertEqual(receipt,{'mode':'PURE_MOCK_SCOPED_IPV6_INITIALIZATION',
            'original_has_ipv6':True,'temporary_has_ipv6':False,'restored_has_ipv6':True,
            'vendor_cached_ipv6':False,'network_permissions_changed':False})

    def test_actual_modules_and_arbitrary_namespaces_are_not_accepted(self):
        from types import SimpleNamespace
        fake=SimpleNamespace(has_ipv6=True)
        with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_STATE_TYPE'):
            m.scoped_mock_initialization(fake,self.vendor,self.initialize)
        self.assertTrue(fake.has_ipv6)

    def test_false_or_nonboolean_original_state_refuses_before_callback(self):
        called=[]
        for value in (False,0,1,None,'MOCK'):
            self.socket.has_ipv6=value
            with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_ORIGINAL_NOT_TRUE'):
                m.scoped_mock_initialization(self.socket,self.vendor,lambda *args:called.append(True))
            self.assertIs(self.socket.has_ipv6,value)
        self.assertEqual(called,[])

    def test_already_initialized_or_failed_vendor_refuses_without_reset(self):
        for name,value in [('initialized',True),('cached_ipv6',False),('scope_active',True),('failed',True)]:
            vendor=m.MockVendorState();setattr(vendor,name,value)
            with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_VENDOR_NOT_FRESH'):
                m.scoped_mock_initialization(self.socket,vendor,self.initialize)
            self.assertIs(self.socket.has_ipv6,True)
            self.assertIs(getattr(vendor,name),value)

    def test_initializer_error_restores_flag_and_preserves_primary_exception(self):
        error=RuntimeError('MOCK_INITIALIZATION_FAILURE')
        def fails(*args):raise error
        with self.assertRaises(RuntimeError) as caught:m.scoped_mock_initialization(self.socket,self.vendor,fails)
        self.assertIs(caught.exception,error)
        self.assertIs(self.socket.has_ipv6,True)
        self.assertTrue(self.vendor.failed)
        self.assertFalse(self.vendor.scope_active)

    def test_failed_initialization_cannot_retry_same_vendor(self):
        def fails(*args):raise RuntimeError('MOCK_FAILURE')
        with self.assertRaises(RuntimeError):m.scoped_mock_initialization(self.socket,self.vendor,fails)
        with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_VENDOR_NOT_FRESH'):
            m.scoped_mock_initialization(self.socket,self.vendor,self.initialize)

    def test_state_drift_is_refused_after_original_flag_is_restored(self):
        def drift(socket,vendor):
            self.initialize(socket,vendor);socket.has_ipv6=True
        with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_SCOPE_DRIFT'):
            m.scoped_mock_initialization(self.socket,self.vendor,drift)
        self.assertIs(self.socket.has_ipv6,True);self.assertTrue(self.vendor.failed)

    def test_primary_guard_error_is_not_replaced_by_callback_drift(self):
        def drift_and_connect(socket,vendor):
            socket.has_ipv6=True
            self.guard.audit('socket.connect',('MOCK_PRIVATE_ARGUMENT',))
        with self.assertRaisesRegex(p.Refused,'GUEST_NETWORK_HELPER_OR_CTYPES_DENIED'):
            m.scoped_mock_initialization(self.socket,self.vendor,drift_and_connect)
        self.assertIs(self.socket.has_ipv6,True);self.assertEqual(self.guard.violations,1)

    def test_socket_connect_during_scope_is_still_denied_and_counted(self):
        def connects(socket,vendor):
            self.assertIs(socket.has_ipv6,False)
            self.guard.audit('socket.connect',())
        with self.assertRaises(p.Refused):m.scoped_mock_initialization(self.socket,self.vendor,connects)
        self.assertEqual(self.guard.violations,1);self.assertIs(self.socket.has_ipv6,True)

    def test_another_caught_constructor_during_scope_is_not_waived(self):
        def other_constructor(socket,vendor):
            self.initialize(socket,vendor)
            try:self.guard.audit('socket.__new__',())
            except Exception:pass
        m.scoped_mock_initialization(self.socket,self.vendor,other_constructor)
        self.assertEqual(self.guard.violations,1)
        with self.assertRaisesRegex(p.Refused,'GUEST_CAUGHT_VIOLATION'):
            p.need(self.guard.violations == 0,'GUEST_CAUGHT_VIOLATION')

    def test_existing_violations_are_never_reset(self):
        try:self.guard.audit('socket.getaddrinfo',())
        except p.Refused:pass
        m.scoped_mock_initialization(self.socket,self.vendor,self.initialize)
        self.assertEqual(self.guard.violations,1)

    def test_constructor_after_restoration_is_still_denied(self):
        m.scoped_mock_initialization(self.socket,self.vendor,self.initialize)
        with self.assertRaises(p.Refused):self.guard.audit('socket.__new__',())
        self.assertEqual(self.guard.violations,1)

    def test_reentrant_initialization_is_rejected_and_restored(self):
        def nested(socket,vendor):m.scoped_mock_initialization(socket,vendor,self.initialize)
        with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_ORIGINAL_NOT_TRUE'):
            m.scoped_mock_initialization(self.socket,self.vendor,nested)
        self.assertIs(self.socket.has_ipv6,True);self.assertTrue(self.vendor.failed)

    def test_unexpected_vendor_result_fails_closed_after_restoration(self):
        def wrong(socket,vendor):vendor.initialized=True;vendor.cached_ipv6=True
        with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_INITIALIZATION_RESULT'):
            m.scoped_mock_initialization(self.socket,self.vendor,wrong)
        self.assertIs(self.socket.has_ipv6,True)

    def test_baseexception_also_restores_mock_state(self):
        def interrupted(*args):raise KeyboardInterrupt('MOCK_INTERRUPTION')
        with self.assertRaises(KeyboardInterrupt):m.scoped_mock_initialization(self.socket,self.vendor,interrupted)
        self.assertIs(self.socket.has_ipv6,True);self.assertFalse(self.vendor.scope_active)
        self.assertTrue(self.vendor.failed)

    def test_unexpected_failed_flag_after_callback_is_not_success(self):
        def wrong(socket,vendor):self.initialize(socket,vendor);vendor.failed=True
        with self.assertRaisesRegex(m.MockConfigurationRefused,'MOCK_INITIALIZATION_RESULT'):
            m.scoped_mock_initialization(self.socket,self.vendor,wrong)
        self.assertIs(self.socket.has_ipv6,True)

    def test_scope_does_not_permit_other_guarded_operations(self):
        for event in ('socket.bind','socket.getaddrinfo','subprocess.Popen','ctypes.dlopen'):
            socket=m.MockSocketState();vendor=m.MockVendorState()
            def forbidden(s,v):self.guard.audit(event,())
            with self.assertRaises(p.Refused):m.scoped_mock_initialization(socket,vendor,forbidden)
            self.assertIs(socket.has_ipv6,True)
        self.assertEqual(self.guard.violations,4)

    def test_no_socket_import_network_library_or_real_global_mutation_in_candidate(self):
        tree=ast.parse((ROOT/'scripts/e01_offline_ipv6_probe_mock_candidate_v1_20261116.py').read_bytes())
        imports=[node for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom))]
        self.assertEqual(len(imports),1);self.assertIsInstance(imports[0],ast.ImportFrom)
        self.assertEqual(imports[0].module,'dataclasses')
        self.assertFalse(any(isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name)
                             and node.value.id in {'socket','sys','os'} for node in ast.walk(tree)))


if __name__=='__main__':t.g.old.guarded_test_main()
