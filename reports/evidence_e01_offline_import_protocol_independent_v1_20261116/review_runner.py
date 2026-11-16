from pathlib import Path
import hashlib,json,os,resource,runpy,signal,sys,time,unittest
ROOT=Path(__file__).resolve().parents[2];START=time.monotonic();READS=0;META_BEFORE=tuple(sys.meta_path)
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
def deadline(*a):raise RuntimeError('INDEPENDENT_METHODS_DEADLINE')
signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline);signal.setitimer(signal.ITIMER_REAL,120)
def early(event,args):
 global READS
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.exec','os.spawn','os.fork','os.forkpty','ctypes.dlopen','os.kill','os.killpg'}:raise RuntimeError('INDEPENDENT_METHODS_NO_ACTUAL_OPERATION')
 if event=='import' and args and args[0].split('.')[0] in {'socket','_socket','pip','pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:raise RuntimeError('INDEPENDENT_METHODS_NO_SOCKET_VENDOR_PACKAGE_IMPORT')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  p=Path(os.fsdecode(args[0])).resolve();flags=args[2]
  if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise RuntimeError('INDEPENDENT_METHODS_NO_FILE_WRITES')
  if p.is_relative_to(ROOT/'data') and not p.is_relative_to(Path(sys.base_prefix).resolve()):raise RuntimeError('INDEPENDENT_METHODS_NO_ACTUAL_INPUTS')
  try:size=p.stat().st_size
  except FileNotFoundError:size=0
  READS+=size+1
  if READS>67108864:raise RuntimeError('INDEPENDENT_METHODS_READ_CAP')
sys.addaudithook(early)
ns=runpy.run_path(str(ROOT/'tests/test_e01_offline_import_protocol_methods_v1_20261116.py'),run_name='independent_original_import_methods')
for name in ['DelegationMechanismTests','BoundPredicateTests','ReproducibilityAndScopeTests']:globals()[name]=ns[name]
Env=ns['Environment'];Bound=ns['BoundRegistrationModel'];Ordinary=ns['OrdinaryControl'];Frozen=ns['FrozenSnapshot'];Vendor=ns['VendorFinder'];Standard=ns['StandardFinder'];Spec=ns['Spec'];Refused=ns['ModelRefused'];Missing=ns['ModelMissing']
class IndependentMethods(unittest.TestCase):
 def test_extended_baseline_identity_is_checked_at_every_position(self):
  env=Env();env.finders.append(Standard());resolver=Bound(env);env.register();self.assertEqual(resolver.resolve('MODEL_MOVES_QUEUE').target,'MODEL_STDLIB_QUEUE')
  env.finders[1]=Standard()
  with self.assertRaisesRegex(Refused,'MODEL_BASELINE_CHANGED'):resolver.postcheck()
 def test_wrong_loader_spec_refused_for_exact_registered_finder(self):
  env=Env();resolver=Bound(env);vendor=env.register();vendor.find=lambda name:Spec(name,ns['ALIASES'][name],'MODEL_WRONG_LOADER')
  with self.assertRaisesRegex(Refused,'MODEL_SPEC_UNBOUND'):resolver.resolve('MODEL_MOVES_QUEUE')
 def test_alias_map_drift_after_success_is_refused(self):
  env=Env();resolver=Bound(env);vendor=env.register();resolver.resolve('MODEL_MOVES_QUEUE');queries=env.queries();vendor.aliases['MODEL_MOVES_QUEUE']='MODEL_DRIFT'
  with self.assertRaisesRegex(Refused,'MODEL_ALIAS_MAP_UNBOUND'):resolver.postcheck()
  self.assertEqual(env.queries(),queries)
 def test_unsupported_request_is_refused_before_any_finder_query(self):
  env=Env();resolver=Bound(env);env.register()
  with self.assertRaisesRegex(Refused,'MODEL_REQUEST_UNSUPPORTED'):resolver.resolve('MODEL_UNKNOWN')
  self.assertEqual(env.queries(),0)
 def test_frozen_resolved_lookup_does_not_qualify_post_state(self):
  env=Env(known=('MODEL_MOVES_HTTP',));resolver=Frozen(env);vendor=env.register();self.assertEqual(resolver.resolve('MODEL_MOVES_HTTP').loader,'MODEL_STANDARD');self.assertEqual(vendor.calls,0)
  with self.assertRaisesRegex(Refused,'MODEL_FINDER_STACK_CHANGED'):resolver.postcheck()
 def test_unregistered_bound_route_is_not_equivalent_to_ordinary_missing(self):
  for cls,code in [(Bound,'MODEL_APPEND_COUNT'),(Ordinary,'MODEL_MISSING')]:
   env=Env();resolver=cls(env)
   with self.assertRaisesRegex(Refused if cls is Bound else Missing,code):resolver.resolve('MODEL_MOVES_HTTP')
   self.assertEqual(env.queries(),0 if cls is Bound else 1)
 def test_unbound_source_resolution_is_not_security_acceptance(self):
  env=Env();ordinary=Ordinary(env);env.register(Vendor(source='MODEL_UNBOUND'));self.assertEqual(ordinary.resolve('MODEL_MOVES_HTTP').target,'MODEL_STDLIB_HTTP')
  env=Env();bound=Bound(env);env.register(Vendor(source='MODEL_UNBOUND'))
  with self.assertRaisesRegex(Refused,'MODEL_SOURCE_UNBOUND'):bound.resolve('MODEL_MOVES_HTTP')
 def test_postcheck_does_not_revalidate_previously_returned_mutable_spec_limit(self):
  env=Env();bound=Bound(env);env.register();spec=bound.resolve('MODEL_MOVES_HTTP');spec.target='MODEL_MUTATED_AFTER_RETURN';bound.postcheck()
  self.assertEqual(spec.target,'MODEL_MUTATED_AFTER_RETURN')
  print(json.dumps({'kind':'INDEPENDENT_MODEL_LIMITATION','postcheck_checks_registration_not_returned_spec_state':True,'real_importer_or_runtime_qualified':False},sort_keys=True))
try:ns['guarded_main']()
except SystemExit as stopped:EXIT=stopped.code or 0
assert tuple(sys.meta_path)==META_BEFORE
assert not any(n=='pip' or n.startswith('pip.') for n in sys.modules)
assert 'socket' not in sys.modules
print(json.dumps({'kind':'INDEPENDENT_IMPORT_METHODS_REVIEW','python':sys.version.split()[0],'original_checks':20,'independent_checks':8,'expected_checks':28,'exit_code':EXIT,'wall_seconds':time.monotonic()-START,'logical_open_read_bytes_including_startup':READS,'sys_meta_path_unchanged':True,'socket_imported':False,'vendor_or_project_runtime_imported':False,'filesystem_writes':0,'actual_child_network_or_importer':0,'bounds':'120sCPUwall_64MiBread_32MiBwrite_256KiBconsole','no_rerun':True}))
raise SystemExit(EXIT)
