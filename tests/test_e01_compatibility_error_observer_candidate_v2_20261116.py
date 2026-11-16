"""Pure observer cases and direct frozen guard callbacks, never actual pip."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def forbid_actual(event,args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn',
            'os.system','os.exec','os.spawn','ctypes.dlopen'}:
        raise AssertionError('OBSERVER_PURE_NO_ACTUAL_SOCKET_PROCESS_NATIVE')
    if event=='import' and args and (args[0]=='pip' or args[0].startswith('pip.')):
        raise AssertionError('OBSERVER_PURE_NO_ACTUAL_PIP_IMPORT')
sys.addaudithook(forbid_actual)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module

m=load('observer_pure_candidate',ROOT/'scripts/e01_compatibility_error_observer_candidate_v2_20261116.py')
p=load('observer_frozen_guard',ROOT/'scripts/install_e01_pypdf701_runtime_v1_5.py')
t=load('observer_authored_bounds',ROOT/'tests/test_e01_pypdf701_install_v1_3.py')


class PoisonedError(RuntimeError):
    def __getattribute__(self,name):raise AssertionError('EXCEPTION_ATTRIBUTE_ACCESSED')
    def __str__(self):raise AssertionError('EXCEPTION_STR_ACCESSED')
    def __repr__(self):raise AssertionError('EXCEPTION_REPR_ACCESSED')


class PoisonedText(str):
    def __len__(self):raise AssertionError('STRING_SUBCLASS_LEN_ACCESSED')
    def __hash__(self):raise AssertionError('STRING_SUBCLASS_HASH_ACCESSED')
    def __str__(self):raise AssertionError('STRING_SUBCLASS_STR_ACCESSED')
    def __repr__(self):raise AssertionError('STRING_SUBCLASS_REPR_ACCESSED')


class ErrorObserverTests(unittest.TestCase):
    def setUp(self):self.observer=m.ErrorObserver()
    def test_initial_state_is_explicit_mock_and_no_inferred_failure(self):
        value=m.decode(self.observer.encode())
        self.assertEqual(value['kind'],m.KIND);self.assertIsNone(value['first_error'])
        self.assertEqual(value['last_phase'],'NOT_STARTED');self.assertEqual(value['failure_total'],0)
    def test_success_returns_same_object_exactly_once(self):
        value=object();calls=[]
        result=self.observer.observe_call('MIME_PREPARE',lambda:(calls.append(True),value)[1])
        self.assertIs(result,value);self.assertEqual(calls,[True]);self.assertIsNone(self.observer.snapshot()['first_error'])
    def test_primary_exception_identity_preserved(self):
        error=RuntimeError('MOCK_PRIVATE_VALUE')
        def fail():raise error
        with self.assertRaises(RuntimeError) as caught:self.observer.observe_call('ADAPTER_IMPORT_START',fail)
        self.assertIs(caught.exception,error)
        value=m.decode(self.observer.encode());self.assertEqual(value['latest_error']['exception_type'],'RUNTIME_ERROR')
        self.assertEqual(value['latest_error']['phase'],'ADAPTER_IMPORT_START')
        self.assertNotIn(b'MOCK_PRIVATE_VALUE',self.observer.encode())
    def test_unknown_exception_has_no_attribute_message_or_class_name_access(self):
        error=PoisonedError('MOCK_SECRET')
        self.observer.record_exception(error)
        raw=self.observer.encode();self.assertNotIn(b'MOCK_SECRET',raw);self.assertNotIn(b'PoisonedError',raw)
        self.assertEqual(m.decode(raw)['latest_error']['exception_type'],'UNKNOWN_TYPE')
    def test_explicit_custom_type_identity_is_only_trust_source(self):
        observer=m.ErrorObserver(((PoisonedError,'COMPATIBILITY_REFUSED'),))
        observer.record_exception(PoisonedError('MOCK_SECRET'),'COMPATIBILITY_IMPORT_LOADER')
        value=observer.snapshot()['latest_error']
        self.assertEqual(value['exception_type'],'COMPATIBILITY_REFUSED');self.assertTrue(value['code_available'])
        self.assertNotIn(b'MOCK_SECRET',observer.encode())
    def test_named_subclass_does_not_inherit_trust(self):
        class Nested(PoisonedError):pass
        observer=m.ErrorObserver(((PoisonedError,'COMPATIBILITY_REFUSED'),))
        observer.record_exception(Nested('MOCK_SECRET'),'COMPATIBILITY_IMPORT_LOADER')
        self.assertEqual(observer.snapshot()['latest_error']['exception_type'],'UNKNOWN_TYPE')
    def test_builtin_types_are_exact_closed_labels(self):
        for cls,label in m.BUILTIN_TYPES:
            observer=m.ErrorObserver();observer.record_exception(cls('MOCK_SECRET'))
            self.assertEqual(observer.snapshot()['latest_error']['exception_type'],label)
            self.assertNotIn(b'MOCK_SECRET',observer.encode())
    def test_module_not_found_name_path_and_args_are_never_emitted(self):
        error=ModuleNotFoundError('MOCK_PRIVATE_MESSAGE',name='MOCK_PRIVATE_MODULE',path='/MOCK_PRIVATE_PATH')
        self.observer.record_exception(error)
        value=self.observer.snapshot()['latest_error'];self.assertEqual(value['exception_type'],'MODULE_NOT_FOUND_ERROR')
        self.assertFalse(value['code_available']);self.assertNotIn(b'MOCK_PRIVATE',self.observer.encode())
    def test_allowed_code_is_explicit_callsite_token_not_parsed_error(self):
        self.observer.record_exception(RuntimeError('COMPATIBILITY_IMPORT_LOADER'))
        self.assertEqual(self.observer.snapshot()['latest_error']['code'],m.UNAVAILABLE)
        self.observer.record_exception(RuntimeError('MOCK_PRIVATE'),'COMPATIBILITY_VENDOR_RESULT')
        self.assertEqual(self.observer.snapshot()['latest_error']['code'],'COMPATIBILITY_VENDOR_RESULT')
    def test_unallowlisted_and_oversized_values_redacted_before_emission(self):
        for code in ('MOCK_PRIVATE_CODE','S'*100000,None,object(),PoisonedText('COMPATIBILITY_IMPORT_LOADER')):
            self.observer.record_exception(RuntimeError('MOCK_PRIVATE'),code)
            self.assertEqual(self.observer.snapshot()['latest_error']['code'],m.UNAVAILABLE)
        self.assertTrue(self.observer.snapshot()['unallowlisted_code_seen']);self.assertNotIn(b'MOCK_PRIVATE',self.observer.encode())
    def test_unknown_phase_and_string_subclass_never_stringified(self):
        for phase in ('MOCK_PRIVATE_PHASE','S'*100000,object(),PoisonedText('MIME_READY')):
            self.observer.mark_phase(phase)
            self.assertEqual(self.observer.snapshot()['last_phase'],'UNKNOWN_PHASE')
        self.assertTrue(self.observer.snapshot()['unknown_phase_seen']);self.assertNotIn(b'MOCK_PRIVATE',self.observer.encode())
    def test_first_observation_and_latest_propagation_distinguished(self):
        self.observer.mark_phase('ADAPTER_IMPORT_START');self.observer.record_exception(ImportError('MOCK_FIRST'))
        first=copy.deepcopy(self.observer.snapshot()['first_error'])
        self.observer.mark_phase('ADAPTER_SCOPE_RESTORE');self.observer.record_exception(RuntimeError('MOCK_SECOND'))
        value=self.observer.snapshot();self.assertEqual(value['first_error'],first)
        self.assertEqual(value['latest_error']['exception_type'],'RUNTIME_ERROR');self.assertEqual(value['failure_total'],2)
    def test_nested_boundary_preserves_actual_outer_primary(self):
        inner=ImportError('MOCK_INNER');outer=RuntimeError('MOCK_OUTER')
        def inner_failure():raise inner
        def outer_failure():
            try:self.observer.observe_call('ADAPTER_IMPORT_START',inner_failure)
            except ImportError:pass
            raise outer
        with self.assertRaises(RuntimeError) as caught:self.observer.observe_call('GUEST_ENTRY',outer_failure)
        self.assertIs(caught.exception,outer)
        self.assertEqual(self.observer.snapshot()['first_error']['exception_type'],'IMPORT_ERROR')
        self.assertEqual(self.observer.snapshot()['latest_error']['exception_type'],'RUNTIME_ERROR')
    def test_baseexceptions_preserve_identity_and_are_safely_classified(self):
        for cls in (KeyboardInterrupt,SystemExit):
            error=cls('MOCK_PRIVATE')
            def fail():raise error
            with self.assertRaises(cls) as caught:self.observer.observe_call('PIP_DRY_RUN_START',fail)
            self.assertIs(caught.exception,error)
        self.assertNotIn(b'MOCK_PRIVATE',self.observer.encode())
    def test_recording_failure_never_replaces_primary(self):
        error=RuntimeError('MOCK_PRIMARY')
        def fail():raise error
        with patch.object(self.observer,'record_exception',side_effect=ValueError('MOCK_OBSERVER_ERROR')):
            with self.assertRaises(RuntimeError) as caught:self.observer.observe_call('ADAPTER_IMPORT_START',fail)
        self.assertIs(caught.exception,error);self.assertTrue(m.decode(self.observer.encode())['observer_failed'])
    def test_preboundary_observer_failure_prevents_callback(self):
        calls=[]
        with patch.object(self.observer,'mark_phase',side_effect=ValueError('MOCK_OBSERVER_ERROR')):
            with self.assertRaises(ValueError):self.observer.observe_call('GUEST_ENTRY',lambda:calls.append(True))
        self.assertEqual(calls,[])
    def test_snapshot_is_detached_and_retains_no_exception_instance(self):
        self.observer.mark_phase('GUEST_ENTRY');self.observer.record_exception(RuntimeError('MOCK_PRIVATE'))
        value=self.observer.snapshot();value['phases'][0]['phase']='MOCK_CHANGED';value['first_error']['code']='MOCK_CHANGED'
        current=self.observer.snapshot();self.assertEqual(current['phases'][0]['phase'],'GUEST_ENTRY')
        self.assertNotEqual(current['first_error']['code'],'MOCK_CHANGED')
        self.assertFalse(any(isinstance(v,BaseException) for v in vars(self.observer).values()))
    def test_phase_capacity_keeps_last_phase_and_explicit_dropped_count(self):
        for _ in range(m.MAX_PHASES+5):self.observer.mark_phase('ADAPTER_IMPORT_START')
        self.observer.mark_phase('GUEST_RESULT_WRITE');value=m.decode(self.observer.encode())
        self.assertEqual(len(value['phases']),m.MAX_PHASES);self.assertEqual(value['phase_dropped'],6)
        self.assertEqual(value['last_phase'],'GUEST_RESULT_WRITE')
    def test_counter_saturation_and_serialized_cap_are_explicit(self):
        for _ in range(m.MAX_COUNTER+30):self.observer.mark_phase('ADAPTER_FRESHNESS_CHECK')
        for _ in range(m.MAX_COUNTER+1):self.observer.record_exception(RuntimeError('MOCK_PRIVATE'),'COMPATIBILITY_UNBOUND_IMPORT_ORIGIN')
        raw=self.observer.encode();value=m.decode(raw)
        self.assertLessEqual(len(raw),4096);self.assertTrue(value['phase_saturated']);self.assertTrue(value['failure_saturated'])
        self.assertEqual(value['phase_total'],m.MAX_COUNTER);self.assertEqual(value['failure_total'],m.MAX_COUNTER)
        print(json.dumps({'kind':'PURE_OBSERVER_MAXIMUM_COUNTERS_RECEIPT','serialized_bytes':len(raw),
                          'cap_bytes':4096,'phase_entries':len(value['phases'])},sort_keys=True))
    def test_registration_rejects_dynamic_or_duplicate_bindings(self):
        for value in ([('COMPATIBILITY_REFUSED',PoisonedError)],((PoisonedError,'MOCK_SECRET_LABEL'),),
                ((RuntimeError,'COMPATIBILITY_REFUSED'),),((PoisonedError,'COMPATIBILITY_REFUSED'),(PoisonedError,'FROZEN_GUARD_REFUSED'))):
            with self.assertRaises(m.ObserverPayloadRefused):m.ErrorObserver(value)
    def test_unknown_nonexception_value_is_redacted(self):
        self.observer.record_exception(object())
        self.assertEqual(self.observer.snapshot()['latest_error']['exception_type'],'UNKNOWN_TYPE')


class ObserverValidationTests(unittest.TestCase):
    def setUp(self):self.value=m.ErrorObserver().snapshot()
    def reject(self,value):
        with self.assertRaises(m.ObserverPayloadRefused):m.decode(json.dumps(value).encode())
    def test_extra_keys_and_unknown_types_rejected(self):
        value=copy.deepcopy(self.value);value['MOCK_PRIVATE']='secret';self.reject(value)
        observer=m.ErrorObserver();observer.record_exception(RuntimeError())
        value=observer.snapshot();value['first_error']['exception_type']='MOCK_CLASSNAME';self.reject(value)
    def test_unknown_phase_code_and_nonboolean_flags_rejected(self):
        value=copy.deepcopy(self.value);value['last_phase']='MOCK_PRIVATE';self.reject(value)
        value=copy.deepcopy(self.value);value['observer_failed']=1;self.reject(value)
        observer=m.ErrorObserver();observer.record_exception(RuntimeError())
        value=observer.snapshot();value['first_error']['code']='MOCK_PRIVATE';self.reject(value)
    def test_tampered_count_sequence_and_error_presence_refused(self):
        value=copy.deepcopy(self.value);value['failure_total']=1;self.reject(value)
        observer=m.ErrorObserver();observer.mark_phase('GUEST_ENTRY');value=observer.snapshot()
        value['phases'][0]['sequence']=2;self.reject(value)
        value=copy.deepcopy(self.value);value['phase_total']=True;self.reject(value)
    def test_duplicate_json_keys_nonfinite_and_invalid_json_rejected(self):
        for raw in (b'{"kind":1,"kind":2}',b'{"kind":NaN}',b'{',b'\xff'):
            with self.assertRaises(m.ObserverPayloadRefused):m.decode(raw)
    def test_oversized_or_nonbytes_input_rejected(self):
        for raw in (b' '*4097,'MOCK_STRING',bytearray(b'{}')):
            with self.assertRaises(m.ObserverPayloadRefused):m.decode(raw)
    def test_first_phase_prefix_cannot_be_omitted_or_rewritten(self):
        value=copy.deepcopy(self.value);value['last_phase']='ADAPTER_IMPORT_START';self.reject(value)
        value=copy.deepcopy(self.value);value.update(phase_total=1,phase_dropped=1);self.reject(value)
        observer=m.ErrorObserver();observer.mark_phase('GUEST_ENTRY');value=observer.snapshot()
        value['last_phase']='ADAPTER_IMPORT_START';self.reject(value)
    def test_saturation_and_redaction_flags_cannot_be_forged(self):
        value=copy.deepcopy(self.value);value['phase_saturated']=True;self.reject(value)
        value=copy.deepcopy(self.value);value['failure_saturated']=True;self.reject(value)
        observer=m.ErrorObserver();observer.record_exception(RuntimeError());value=observer.snapshot()
        value['unallowlisted_code_seen']=False;self.reject(value)
        observer=m.ErrorObserver();observer.mark_phase('UNKNOWN_PHASE');value=observer.snapshot()
        value['unknown_phase_seen']=False;self.reject(value)
    def test_single_failure_cannot_claim_two_different_exceptions(self):
        observer=m.ErrorObserver();observer.record_exception(RuntimeError());value=observer.snapshot()
        value['latest_error']['exception_type']='IMPORT_ERROR';self.reject(value)


class GuardAndStaticModelTests(unittest.TestCase):
    def test_original_guard_denials_counters_and_primary_preserved(self):
        with tempfile.TemporaryDirectory(prefix='observer-PURE-MOCK-') as temp:
            root=Path(temp).resolve();binding={'base_prefix':str(root/'base'),'pip_root':'MOCK_PIP',
                'pip_files':{},'pip_metadata_ref':{'path':'MOCK_METADATA'}}
            policy=p.GuestPolicy(root,binding,{'wheels':[],'remaining_output_bytes':1024})
            observer=m.ErrorObserver(((p.Refused,'FROZEN_GUARD_REFUSED'),))
            for event in ('socket.__new__','socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','ctypes.dlopen'):
                with self.assertRaises(p.Refused):
                    observer.observe_call('ADAPTER_IMPORT_START',lambda:policy.audit(event,()),code='GUEST_NETWORK_HELPER_OR_CTYPES_DENIED')
            self.assertEqual(policy.violations,6);self.assertEqual(observer.snapshot()['failure_total'],6)
            with self.assertRaisesRegex(p.Refused,'GUEST_CAUGHT_VIOLATION'):p.need(policy.violations==0,'GUEST_CAUGHT_VIOLATION')
            self.assertEqual(observer.snapshot()['latest_error']['exception_type'],'FROZEN_GUARD_REFUSED')
    def test_static_snapshot_finder_conflict_model_is_inference_only(self):
        calls=[]
        class OriginalFinder:
            def find_spec(self,name):calls.append('ORIGINAL');return None
        class AddedFinder:
            def find_spec(self,name):calls.append('ADDED');return 'MOCK_SPEC'
        original=(OriginalFinder(),);live=list(original);live.append(AddedFinder())
        def frozen_lookup():
            for finder in original:
                result=finder.find_spec('MOCK_MOVE')
                if result is not None:return result
            raise ModuleNotFoundError("No module named 'MOCK_MOVE'",name='MOCK_MOVE')
        observer=m.ErrorObserver()
        with self.assertRaises(ModuleNotFoundError):observer.observe_call('ADAPTER_IMPORT_START',frozen_lookup)
        self.assertEqual(calls,['ORIGINAL']);self.assertEqual(live[-1].find_spec('MOCK_MOVE'),'MOCK_SPEC')
        value=observer.snapshot()['latest_error'];self.assertEqual(value['exception_type'],'MODULE_NOT_FOUND_ERROR')
        self.assertFalse(value['code_available']);self.assertNotIn(b'MOCK_MOVE',observer.encode())
    def test_candidate_has_only_json_import_and_no_runtime_or_io_names(self):
        tree=ast.parse((ROOT/'scripts/e01_compatibility_error_observer_candidate_v2_20261116.py').read_bytes())
        imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertEqual(len(imports),1);self.assertIsInstance(imports[0],ast.Import)
        self.assertEqual([a.name for a in imports[0].names],['json'])
        names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}
        self.assertFalse(names & {'open','getattr','repr','socket','pip','subprocess','os','sys','eval','exec','__import__'})
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                             and n.func.id=='str' for n in ast.walk(tree)))
        # 'str' is used solely as an exact type identity, never called.
    def test_all_codes_are_static_existing_closed_source_tokens(self):
        values=set()
        for name in ('scripts/e01_offline_ipv6_adapter_v1_1_20261116.py','scripts/validate_e01_offline_ipv6_compatibility_v1_1_20261116.py','scripts/install_e01_pypdf701_runtime_v1_5.py'):
            tree=ast.parse((ROOT/name).read_bytes())
            values.update(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and type(n.value) is str)
        self.assertTrue(m.CODES<=values)
    def test_stdlib_socket_origin_record_without_operation_or_mutation(self):
        module=sys.modules['socket'];path=Path(module.__file__);raw=path.read_bytes()
        expected={'3.12.14':(37815,'7d4d4c66e6f4bcc961ab462c4f08002ca97def8713a4be1c7373bdbd970a5274'),
            '3.11.17':(37557,'64360e73e3db69396d45d5ee256e8306b3653212ab96ae4a130070488cddbb30')}
        self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),expected[sys.version.split()[0]])
        print(json.dumps({'kind':'PURE_OBSERVER_TRANSITIVE_STDLIB_SOCKET_ORIGIN','path':str(path),
            'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'python':sys.version.split()[0],
            'actual_socket_operations':0,'socket_global_mutations':0,'pip_import':False},sort_keys=True))


class SaturationBoundaryTests(unittest.TestCase):
    def at_boundary(self):
        observer=m.ErrorObserver()
        for _ in range(m.MAX_COUNTER):observer.mark_phase('MIME_READY')
        return observer

    def test_emitted_unsaturated_to_saturated_boundary_decodes(self):
        observer=self.at_boundary();before=m.decode(observer.encode())
        self.assertFalse(before['phase_saturated'])
        self.assertEqual(before['phase_dropped'],m.MAX_COUNTER-m.MAX_PHASES)
        observer.mark_phase('ADAPTER_IMPORT_START');after=m.decode(observer.encode())
        self.assertTrue(after['phase_saturated'])
        self.assertEqual(after['phase_dropped'],m.MAX_COUNTER-m.MAX_PHASES+1)
        self.assertEqual(after['phases'],before['phases'])
        self.assertEqual(after['last_phase'],'ADAPTER_IMPORT_START')

    def test_impossible_saturated_drop_counts_are_rejected(self):
        observer=self.at_boundary();observer.mark_phase('ADAPTER_IMPORT_START')
        for impossible in (0,1,16,m.MAX_COUNTER-m.MAX_PHASES-1,m.MAX_COUNTER-m.MAX_PHASES):
            with self.subTest(impossible=impossible):
                value=observer.snapshot();value['phase_dropped']=impossible
                with self.assertRaises(m.ObserverPayloadRefused):m.decode(m.packed(value))

    def test_emitted_drop_counter_cap_and_later_marks_decode(self):
        observer=self.at_boundary()
        for _ in range(m.MAX_PHASES+3):observer.mark_phase('ADAPTER_IMPORT_RETURN')
        value=m.decode(observer.encode())
        self.assertTrue(value['phase_saturated'])
        self.assertEqual(value['phase_total'],m.MAX_COUNTER)
        self.assertEqual(value['phase_dropped'],m.MAX_COUNTER)
        self.assertEqual(len(value['phases']),m.MAX_PHASES)
        self.assertLessEqual(len(observer.encode()),m.MAX_JSON_BYTES)


if __name__=='__main__':t.g.old.guarded_test_main()
