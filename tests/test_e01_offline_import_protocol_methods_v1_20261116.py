"""Pure fabricated finder delegation methods. No real import-system mutation.

No project/vendor modules loaded. Models return inert specs and never execute
module code. The main-only authored harness enforces finite IO/CPU/output caps.
"""
import sys


def forbid_actual(event,args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty',
            'os.posix_spawn','os.system','os.exec','os.spawn','ctypes.dlopen'}:
        raise AssertionError('METHODS_NO_ACTUAL_SOCKET_PROCESS_NATIVE')
    if event=='import' and args and args[0].split('.')[0] in {'pip','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:
        raise AssertionError('METHODS_NO_PROJECT_VENDOR_PACKAGE_IMPORT')
sys.addaudithook(forbid_actual)

import ast
import builtins
import hashlib
import io
import json
import os
import resource
import signal
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
CODE_PATH='tests/test_e01_offline_import_protocol_methods_v1_20261116.py'
BOUND_SOURCE=hashlib.sha256(b'PURE_FABRICATED_SIX_SOURCE_NOT_REAL_SOURCE_ATTESTATION').hexdigest()
ALIASES={'MODEL_MOVES_HTTP':'MODEL_STDLIB_HTTP','MODEL_MOVES_QUEUE':'MODEL_STDLIB_QUEUE'}
VARIANTS=('ORDINARY_CONTROL','FROZEN_SNAPSHOT','BOUND_REGISTRATION_MODEL')


def need(value,code):
    if not value:raise ModelRefused(code)


class ModelRefused(RuntimeError):pass
class ModelMissing(ImportError):pass


class Spec:
    def __init__(self,request,target,loader):
        self.request,self.target,self.loader=request,target,loader
    def row(self):return {'request':self.request,'target':self.target,'loader':self.loader}


class StandardFinder:
    def __init__(self,known=()):self.known=set(known);self.calls=0
    def find(self,name):
        self.calls+=1
        return Spec(name,name,'MODEL_STANDARD') if name in self.known else None


class VendorFinder:
    def __init__(self,source=BOUND_SOURCE,aliases=None):
        self.source=source;self.aliases=dict(ALIASES if aliases is None else aliases);self.calls=0
    def find(self,name):
        self.calls+=1
        if name in self.aliases:return Spec(name,self.aliases[name],'MODEL_VENDOR_MOVES')
        return None


class Environment:
    def __init__(self,known=()):
        self.standard=StandardFinder(known);self.finders=[self.standard]
    def register(self,finder=None):
        finder=VendorFinder() if finder is None else finder
        self.finders.append(finder);return finder
    def queries(self):return sum(f.calls for f in self.finders)


class OrdinaryControl:
    """Simple model of None -> next finder, first spec -> return semantics."""
    def __init__(self,env):self.env=env
    def resolve(self,name):
        for finder in tuple(self.env.finders):
            spec=finder.find(name)
            if spec is not None:return spec
        raise ModelMissing('MODEL_MISSING')
    def postcheck(self):pass


class FrozenSnapshot:
    """Model current adapter's captured chain and terminal missing exception."""
    def __init__(self,env):self.env=env;self.before=tuple(env.finders)
    def resolve(self,name):
        for finder in self.before:
            spec=finder.find(name)
            if spec is not None:return spec
        raise ModelMissing('MODEL_MISSING_FROM_SNAPSHOT')
    def postcheck(self):
        need(tuple(self.env.finders)==self.before,'MODEL_FINDER_STACK_CHANGED')


class BoundRegistrationModel:
    """Inert design predicate only, not an actual custom-loader allowance.

    One exact append, unchanged baseline identities, exact fabricated source
    token/type/alias map. Still requires original production guards separately.
    It neither verifies any real source nor imports/delegates actual code.
    """
    def __init__(self,env):self.env=env;self.before=tuple(env.finders)
    def registration(self):
        need(len(self.env.finders)==len(self.before)+1,'MODEL_APPEND_COUNT')
        need(all(a is b for a,b in zip(self.env.finders,self.before)),'MODEL_BASELINE_CHANGED')
        finder=self.env.finders[-1]
        need(type(finder) is VendorFinder,'MODEL_EXACT_FINDER_TYPE')
        need(finder.source==BOUND_SOURCE,'MODEL_SOURCE_UNBOUND')
        need(finder.aliases==ALIASES,'MODEL_ALIAS_MAP_UNBOUND')
        return finder
    def resolve(self,name):
        self.registration()
        need(name in ALIASES,'MODEL_REQUEST_UNSUPPORTED')
        for finder in tuple(self.env.finders):
            spec=finder.find(name)
            if spec is not None:
                need(spec.row()=={'request':name,'target':ALIASES[name],'loader':'MODEL_VENDOR_MOVES'},
                     'MODEL_SPEC_UNBOUND')
                return spec
        raise ModelMissing('MODEL_MISSING_BOUND')
    def postcheck(self):self.registration()


RESOLVERS={'ORDINARY_CONTROL':OrdinaryControl,'FROZEN_SNAPSHOT':FrozenSnapshot,
           'BOUND_REGISTRATION_MODEL':BoundRegistrationModel}


def matched_case(variant,name):
    env=Environment();resolver=RESOLVERS[variant](env)
    env.register()
    try:
        spec=resolver.resolve(name);resolver.postcheck();outcome='MODEL_RESOLVED';target=spec.target
    except ModelMissing:
        outcome='MODEL_MISSING';target=None
    except ModelRefused:
        outcome='MODEL_REFUSED';target=None
    return {'variant':variant,'request':name,'outcome':outcome,'target':target,
            'finder_queries':env.queries(),'module_code_executions':0,'model_or_network_requests':0}


def matched_results():
    return {'kind':'PURE_FABRICATED_IMPORT_PROTOCOL_MATCHED_RESULTS_V1',
        'fixed_inputs':{'source_token':BOUND_SOURCE,'aliases':ALIASES,'baseline_finders':1,
                       'appended_finders':1,'requests_per_case':1,'randomness':'NONE'},
        'rows':[matched_case(variant,name) for name in sorted(ALIASES) for variant in VARIANTS],
        'interpretation':'Inert protocol models only; not actual Python import execution, package compatibility or actual failure attribution.'}


class DelegationMechanismTests(unittest.TestCase):
    def test_matched_known_moves_grid(self):
        results=matched_results()
        for row in results['rows']:
            expected='MODEL_MISSING' if row['variant']=='FROZEN_SNAPSHOT' else 'MODEL_RESOLVED'
            self.assertEqual(row['outcome'],expected)
            self.assertEqual(row['finder_queries'],1 if row['variant']=='FROZEN_SNAPSHOT' else 2)
            self.assertEqual(row['module_code_executions'],0)
            self.assertEqual(row['model_or_network_requests'],0)
        print(json.dumps(results,sort_keys=True,separators=(',',':')))
    def test_same_name_and_registration_inputs_are_reused(self):
        rows=matched_results()['rows']
        for name in ALIASES:
            same=[r for r in rows if r['request']==name]
            self.assertEqual({r['variant'] for r in same},set(VARIANTS))
            self.assertEqual({r['target'] for r in same if r['outcome']=='MODEL_RESOLVED'},{ALIASES[name]})
    def test_standard_none_allows_appended_finder_in_simple_control(self):
        env=Environment();resolver=OrdinaryControl(env);vendor=env.register()
        spec=resolver.resolve('MODEL_MOVES_QUEUE')
        self.assertEqual(spec.target,'MODEL_STDLIB_QUEUE');self.assertEqual(vendor.calls,1)
    def test_frozen_snapshot_raises_before_appended_finder(self):
        env=Environment();resolver=FrozenSnapshot(env);vendor=env.register()
        with self.assertRaises(ModelMissing):resolver.resolve('MODEL_MOVES_QUEUE')
        self.assertEqual(vendor.calls,0);self.assertEqual(env.standard.calls,1)
    def test_return_none_instead_of_raise_would_allow_outer_delegation(self):
        env=Environment();snapshot=tuple(env.finders);vendor=env.register()
        # Pure simulation of an outer importer: no actual sys.meta_path touched.
        def intercept(name):
            for finder in snapshot:
                result=finder.find(name)
                if result is not None:return result
            return None
        result=intercept('MODEL_MOVES_QUEUE')
        if result is None:result=OrdinaryControl(env).resolve('MODEL_MOVES_QUEUE')
        self.assertEqual(result.target,'MODEL_STDLIB_QUEUE');self.assertEqual(vendor.calls,1)
    def test_frozen_postcheck_can_refuse_even_when_lookup_resolved(self):
        env=Environment(known=('MODEL_MOVES_QUEUE',));resolver=FrozenSnapshot(env);env.register()
        self.assertIsNotNone(resolver.resolve('MODEL_MOVES_QUEUE'))
        with self.assertRaisesRegex(ModelRefused,'MODEL_FINDER_STACK_CHANGED'):resolver.postcheck()
    def test_no_added_finder_means_both_controls_report_missing(self):
        for cls in (OrdinaryControl,FrozenSnapshot):
            env=Environment();resolver=cls(env)
            with self.assertRaises(ModelMissing):resolver.resolve('MODEL_MOVES_QUEUE')
    def test_ordinary_control_is_not_a_security_acceptance_test(self):
        env=Environment();resolver=OrdinaryControl(env)
        env.register(VendorFinder(source='MODEL_UNBOUND_SOURCE',aliases={'MODEL_MOVES_QUEUE':'MODEL_WRONG_TARGET'}))
        self.assertEqual(resolver.resolve('MODEL_MOVES_QUEUE').target,'MODEL_WRONG_TARGET')


class BoundPredicateTests(unittest.TestCase):
    def make(self):
        env=Environment();resolver=BoundRegistrationModel(env);return env,resolver
    def test_exact_append_matches_simple_control_output(self):
        for name in ALIASES:
            control=matched_case('ORDINARY_CONTROL',name);bound=matched_case('BOUND_REGISTRATION_MODEL',name)
            self.assertEqual((bound['outcome'],bound['target']),(control['outcome'],control['target']))
    def test_unknown_source_refuses_without_query(self):
        env,resolver=self.make();env.register(VendorFinder(source='MODEL_WRONG_SOURCE'))
        with self.assertRaisesRegex(ModelRefused,'MODEL_SOURCE_UNBOUND'):resolver.resolve('MODEL_MOVES_QUEUE')
        self.assertEqual(env.queries(),0)
    def test_changed_alias_map_refuses_without_query(self):
        env,resolver=self.make();env.register(VendorFinder(aliases={'MODEL_MOVES_QUEUE':'MODEL_WRONG_TARGET'}))
        with self.assertRaisesRegex(ModelRefused,'MODEL_ALIAS_MAP_UNBOUND'):resolver.resolve('MODEL_MOVES_QUEUE')
        self.assertEqual(env.queries(),0)
    def test_subclass_finder_is_not_accepted(self):
        class OtherFinder(VendorFinder):pass
        env,resolver=self.make();env.register(OtherFinder())
        with self.assertRaisesRegex(ModelRefused,'MODEL_EXACT_FINDER_TYPE'):resolver.resolve('MODEL_MOVES_QUEUE')
    def test_extra_finder_or_missing_registration_refuses(self):
        for count in (0,2):
            env,resolver=self.make()
            for _ in range(count):env.register()
            with self.assertRaisesRegex(ModelRefused,'MODEL_APPEND_COUNT'):resolver.resolve('MODEL_MOVES_QUEUE')
    def test_reordered_or_replaced_baseline_refuses(self):
        env,resolver=self.make();env.register();env.finders.reverse()
        with self.assertRaisesRegex(ModelRefused,'MODEL_BASELINE_CHANGED'):resolver.resolve('MODEL_MOVES_QUEUE')
        env,resolver=self.make();env.register();env.finders[0]=StandardFinder()
        with self.assertRaisesRegex(ModelRefused,'MODEL_BASELINE_CHANGED'):resolver.resolve('MODEL_MOVES_QUEUE')
    def test_unsupported_request_refuses_without_query(self):
        env,resolver=self.make();env.register()
        with self.assertRaisesRegex(ModelRefused,'MODEL_REQUEST_UNSUPPORTED'):resolver.resolve('MODEL_UNSUPPORTED')
        self.assertEqual(env.queries(),0)
    def test_later_mutation_fails_postcheck(self):
        env,resolver=self.make();vendor=env.register();resolver.resolve('MODEL_MOVES_QUEUE')
        vendor.source='MODEL_CHANGED_SOURCE'
        with self.assertRaisesRegex(ModelRefused,'MODEL_SOURCE_UNBOUND'):resolver.postcheck()
    def test_bound_route_rejects_conflicting_earlier_spec(self):
        env=Environment(known=('MODEL_MOVES_QUEUE',));resolver=BoundRegistrationModel(env);env.register()
        with self.assertRaisesRegex(ModelRefused,'MODEL_SPEC_UNBOUND'):resolver.resolve('MODEL_MOVES_QUEUE')
    def test_fabricated_denial_is_same_primary_for_all_conditions(self):
        class Guard:
            def __init__(self):self.count=0;self.error=ModelRefused('MODEL_ORIGINAL_DENIAL')
            def deny(self):self.count+=1;raise self.error
        for cls in (OrdinaryControl,FrozenSnapshot,BoundRegistrationModel):
            env=Environment();resolver=cls(env);env.register();guard=Guard()
            try:
                guard.deny();resolver.resolve('MODEL_MOVES_QUEUE')
            except ModelRefused as error:self.assertIs(error,guard.error)
            else:self.fail('MISSING_FABRICATED_DENIAL')
            self.assertEqual(guard.count,1);self.assertEqual(env.queries(),0)


class ReproducibilityAndScopeTests(unittest.TestCase):
    def test_grid_is_deterministic_and_explicitly_fabricated(self):
        first=json.dumps(matched_results(),sort_keys=True,separators=(',',':')).encode()
        second=json.dumps(matched_results(),sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(first,second);self.assertIn(b'PURE_FABRICATED',first)
        print(json.dumps({'kind':'PURE_FABRICATED_MATCHED_GRID_SHA256','sha256':hashlib.sha256(first).hexdigest(),'bytes':len(first)},sort_keys=True))
    def test_model_bodies_have_no_import_or_real_global_import_mutation(self):
        tree=ast.parse((ROOT/CODE_PATH).read_bytes())
        names={'Spec','StandardFinder','VendorFinder','Environment','OrdinaryControl','FrozenSnapshot','BoundRegistrationModel','matched_case','matched_results'}
        bodies=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
        self.assertEqual(len(bodies),len(names))
        for body in bodies:
            self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(body)))
            called={n.func.id for n in ast.walk(body) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
            self.assertFalse(called & {'open','exec','eval','__import__'})
            self.assertFalse(any(isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name)
                and n.value.id in {'sys','os','importlib','subprocess','socket'} for n in ast.walk(body)))


def guarded_main():
    reads=[0];output=[0]
    test_path=ROOT/CODE_PATH
    toolchain=ROOT/'data/processed/toolchains/cpython-3.11.17-macos-aarch64-none'
    stdlib=Path(sys.base_prefix)/'lib'
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=Path(os.path.realpath(args[0]));flags=args[2]
            if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                raise AssertionError('METHODS_NO_FILE_WRITES_NEEDED')
            allowed=(path==test_path or path.is_relative_to(toolchain) or path.is_relative_to(stdlib) or path==Path('/dev/null'))
            if not allowed:raise AssertionError('METHODS_READ_OUTSIDE_AUTHORED_OR_STDLIB')
            try:size=path.stat().st_size
            except FileNotFoundError:size=0
            reads[0]+=size+1
            if reads[0]>67108864:raise AssertionError('METHODS_AUTHORED_READ_CAP')
        if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.truncate','os.chmod'}:
            raise AssertionError('METHODS_NO_FILESYSTEM_MUTATION')
    sys.addaudithook(audit)
    class Output:
        def __init__(self,stream):self.stream=stream
        def __getattr__(self,name):return getattr(self.stream,name)
        def write(self,value):
            output[0]+=len(value.encode())
            if output[0]>262144:raise AssertionError('METHODS_AUTHORED_OUTPUT_CAP')
            return self.stream.write(value)
    sys.stdout=Output(sys.stdout);sys.stderr=Output(sys.stderr)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    def timeout(*_):raise AssertionError('METHODS_AUTHORED_WALL_CAP')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
    unittest.main(failfast=True,verbosity=2)


if __name__=='__main__':guarded_main()
