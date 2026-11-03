"""W01-W08 actual-shaped conditional branches using new tagged fake repositories."""
from copy import deepcopy
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from civiclab.common import canonical_hash
from civiclab.e02.national_budget import Blocked
from civiclab.e02.f_actual_admission_v1_1 import create_fixture
from civiclab.e02 import f_wy_actual_bootstrap_v1 as api
from civiclab.e02.f_wy_actual_bootstrap_control_v1 import Control, stamp, elapsed, ORDER
from civiclab.e02.f_wy_actual_bootstrap_launcher_v1 import Launcher
from test_e02_f_wy_local_v1_1 import rows

REAL=Path(__file__).resolve().parents[1]

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')

def implementation_files():
    names=['src/civiclab/e02/f_wy_actual_bootstrap_v1.py','src/civiclab/e02/f_wy_actual_bootstrap_control_v1.py','src/civiclab/e02/f_wy_actual_bootstrap_launcher_v1.py','tests/test_e02_f_wy_actual_bootstrap_v1.py','src/civiclab/e02/f_wy_bootstrap_v1_1.py','src/civiclab/e02/f_wy_bootstrap_control_v1.py','reports/INDEPENDENT_AUDIT_E02_F_WY_BOOTSTRAP_V1_1_PATH_STORAGE_REMEDY.json','reports/INDEPENDENT_AUDIT_E02_F_WY_ACTUAL_BOOTSTRAP_WIRING_V1_METHODS.json','reports/INDEPENDENT_AUDIT_E02_F_WY_ACTUAL_WIRING_V1_1_DEPENDENCY_ADDENDUM.json']
    return {p:digest(REAL/p) for p in names}

def static_spec(native,source,tag):
    return {'schema_version':1,'protocol':'E02_CONDITIONAL_ACTUAL_BOOTSTRAP_V1','realm':tag,'actual_authority':0,
            'live_refs':{'implementation_manifest':None,'implementation_review':None,'inspection':None},
            'actual_approvals':native['actual_approvals'],'native_config_sha256':None,
            'implementation_files':implementation_files(),'native_limits':native['limits'],'native_storage':native['storage'],
            'resource_envelope':api.envelope(source,native['limits']),
            'control_directory':'data/processed/e02_F_wy_private_bootstrap/conditional-actual-v1-20261103-01',
            'output_directory':'data/processed/e02_F_wy_private/conditional-actual-v1-20261103-01'}


class FakeRepository:
    """Never accepts a raw input path. Every person ZIP is freshly authored."""
    def __init__(self, root, *, full=False):
        self.realm=api.make_test_realm(root);self.root=self.realm.root
        native=json.loads((REAL/'configs/e02_F_WY_LOCAL_IMPLEMENTATION_v1_1.json').read_text())
        for name,expected in native['required_files'].items():
            data=(REAL/name).read_bytes();assert hashlib.sha256(data).hexdigest()==expected
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        donor=create_fixture(self.root/'generator',rows(full));manifest=donor.manifest
        proposal=json.loads((self.root/native['proposal']).read_text());source=proposal['source']
        p=self.root/source['archive']['path'];p.parent.mkdir(parents=True,exist_ok=True);donor.path.rename(p)
        shutil.rmtree(donor.root) # newly generated donor only; one retained person ZIP
        source['archive'].update(bytes=manifest['archive_bytes'],sha256=manifest['archive_sha256'],identity_source='TEST_ONLY_GENERATED_NO_UPSTREAM')
        person=next(m for m in manifest['members'] if m['name']==manifest['person'])
        companion=next(m for m in manifest['members'] if m['name']==manifest['companion'])
        source['person_member'].update(exact_bytes=person['bytes'],sha256=person['sha256'],expected_all_age_rows=manifest['expected_rows'])
        source['companion'].update(exact_bytes=companion['bytes'],sha256=companion['sha256'],maximum_bytes_for_this_WY_source=companion['bytes'])
        source['header'].update(bytes=manifest['header_bytes'],sha256=manifest['header_sha256'])
        source['literal_members']=[{'name':m['name'],'declared_uncompressed_bytes':m['bytes'],'compressed_bytes':m['compressed_bytes'],'crc32':m['crc32']} for m in manifest['members']]
        source['url']='TEST_ONLY_NEWLY_GENERATED_NOT_A_CENSUS_ACQUISITION'
        save(self.root/native['proposal'],proposal)
        native['required_files'][native['proposal']]=digest(self.root/native['proposal'])
        native['parent_provenance']['source_contract_sha256']=digest(self.root/native['proposal'])
        save(self.root/'configs/e02_F_WY_LOCAL_IMPLEMENTATION_v1_1.json',native)
        spec=static_spec(native,source,'TEST_ONLY');spec['native_config_sha256']=digest(self.root/'configs/e02_F_WY_LOCAL_IMPLEMENTATION_v1_1.json')
        for name in spec['implementation_files']:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((REAL/name).read_bytes())
        save(self.root/api.CONFIG,spec)
        self.native=native;self.spec=spec;self.source_path=p=self.root/source['archive']['path']
        self.D=canonical_hash({k:v for k,v in native.items() if k not in ('actual_authority','actual_approvals','scope')})
        self.M=canonical_hash({k:v for k,v in spec.items() if k not in ('actual_authority','live_refs')})
        common={'realm':'TEST_ONLY','adapter_design_sha256':self.M,'native_design_sha256':self.D,'source_contract_sha256':digest(self.root/native['proposal'])}
        self.common=common
        a=self.record('implementation',common|{'status':'IMPLEMENTATION_BINDING_NOT_PERMISSION','files':spec['implementation_files']})
        review=self.record('review',common|{'status':'PASS_F_WY_ACTUAL_BOOTSTRAP_IMPLEMENTATION_AND_AUTHORED_FIXTURES','auditor_role':'independent_auditor','implementation_manifest_sha256':a['sha256']})
        i=self.record('inspection',common|{'status':'APPROVE_F_WY_BOUNDED_EXACT_LOCAL_INSPECTION','auditor_role':'independent_auditor','implementation_manifest_sha256':a['sha256'],'implementation_review_sha256':review['sha256'],
            'source_authorization_reference':'TEST_ONLY_AUTHORED_SCOPE_NOT_OWNER_PERMISSION','not_before':time.time()-60,'expires':time.time()+86400,
            'scope':{'repository_root':str(self.root),'source_path':source['archive']['path'],'control_directory':spec['control_directory'],'output_directory':spec['output_directory'],'GETs':0,'model_calls':0,'person_rows':0,'fit':False,'disclosure':False,'single_use':True},'resource_envelope':spec['resource_envelope']})
        self.live=deepcopy(spec);self.live['actual_authority']=1;self.live['live_refs']={'implementation_manifest':a,'implementation_review':review,'inspection':i}
    def record(self,name,record):
        relative='reports/TEST_ONLY_'+name+'.json';save(self.root/relative,record)
        return {'path':relative,'sha256':digest(self.root/relative)}
    def admit(self):return api.admit_test_inspection(self.realm,self.live)
    def inspect(self):
        c=self.admit();o=api.inspect_authorized(c);return c,o
    def runtime_config(self,c):
        o=api.observation(c);oh=digest(c.control_root/'observation.local.json')
        extra={'realm':'TEST_ONLY','bootstrap_adapter_design_sha256':self.M,'bootstrap_implementation_manifest_sha256':self.live['live_refs']['implementation_manifest']['sha256']}
        common={'auditor_role':'independent_auditor','reviewed_design_sha256':self.D,'reviewed_required_files':self.native['required_files']}|extra
        k=self.record('K',common|{'status':'PASS_F_WY_LOCAL_ADAPTER_CODE_AND_AUTHORED_FIXTURES','fixture_tests_passed':True})
        s=self.record('S',common|{'status':'PASS_F_WY_EXACT_CACHE_SOURCE_ADMISSION_ONLY','source_identity':o['source_identity'],'archive_sha256':c.manifest['archive_sha256'],'header_sha256':c.manifest['header_sha256'],'observation_sha256':oh})
        e=self.record('E',common|{'status':'APPROVE_F_WY_ONE_SOURCE_TWO_SWEEP_LOCAL_EXECUTION','adapter_code_approval_sha256':k['sha256'],'exact_source_approval_sha256':s['sha256'],'source_contract_sha256':c.binding['I']['source_contract_sha256'],
            'network_requests_authorized':0,'model_calls_authorized':0,'disclosure_authorized':False,'fit_authorized':False,'output_directory':self.spec['output_directory'],'control_directory':self.spec['control_directory'],
            'inspection_authorization_sha256':self.live['live_refs']['inspection']['sha256'],'observation_sha256':oh,'post_inspection_state_sha256':o['post_inspection_state_sha256'],'bootstrap_adapter_required':True,'resource_envelope':self.spec['resource_envelope']})
        runtime=deepcopy(self.native);runtime.update(actual_authority=1,scope='NEW_F_WY_LOCAL_ACTUAL_ENGINEERING')
        runtime['actual_approvals']={'adapter_code':k,'exact_source':s,'execution':e,'disclosure':None,'fit':None}
        return runtime


class ConditionalWiringTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.env=FakeRepository(Path(self.tmp.name)/'fake')
    def tearDown(self):self.tmp.cleanup()

    def test_W01_production_rejects_null_or_test_authority_before_filesystem(self):
        with patch('pathlib.Path.stat',side_effect=AssertionError('stat')),patch('pathlib.Path.open',side_effect=AssertionError('open')),patch('os.open',side_effect=AssertionError('osopen')):
            for config in (None,self.env.spec,self.env.live):
                with self.assertRaises(Blocked):api.admit_inspection(config)

    def test_W01_missing_review_or_wrong_scope_denied_without_source_open(self):
        for mode in ('missing_review','scope','permission'):
            config=deepcopy(self.env.live)
            if mode=='missing_review':config['live_refs']['implementation_review']=None
            else:
                ref=config['live_refs']['inspection'];r=json.loads((self.env.root/ref['path']).read_text())
                if mode=='scope':r['scope']['person_rows']=1
                else:r['source_authorization_reference']=''
                config['live_refs']['inspection']=self.env.record('bad_'+mode,r)
            with patch('civiclab.e02.f_wy_actual_bootstrap_v1._open_no_follow',side_effect=AssertionError('source')):
                with self.assertRaises(Blocked):api.admit_test_inspection(self.env.realm,config)

    def test_W02_conditional_inspection_positive_no_rows_or_native_root(self):
        c,o=self.env.inspect();self.assertEqual(o['realm'],'TEST_ONLY');self.assertFalse(c.runtime_root.exists())
        state=Control(c).snapshot();self.assertEqual(state['reserved']['seconds'],1800)
        proof=json.loads((c.control_root/'INSPECT.proof.local.json').read_text())
        self.assertEqual(proof['result']['inspection']['person_rows_read'],0)
        self.assertTrue(proof['result']['inspection']['fixed_lexical_path_reopened'])
        self.assertEqual(o['source_identity']['inode'],self.env.source_path.stat().st_ino)

    def test_W02_copied_context_and_wrong_active_reservation_refuse(self):
        c=self.env.admit();ctl=Control(c,create=True)
        with self.assertRaises(Blocked):api._inspect_reserved(c,ctl)
        bad=api.InspectionContext(c.realm,c.spec_json,json.dumps({**c.binding,'M':'0'*64}),c.token)
        with self.assertRaises(Blocked):api.require_context(bad)

    def test_W03_positive_KSE_reaches_true_native_actual_admission_and_replay(self):
        c,o=self.env.inspect();runtime=self.env.runtime_config(c);api.admit_execution(c,runtime)
        self.assertFalse(c.runtime_root.exists());before=Control(c).snapshot()['t0']
        state=api.run_authorized(c);self.assertEqual(state['shutdown'],'CLOSED');self.assertEqual(state['t0'],before)
        self.assertTrue((c.runtime_root/'.F_WY_ACTUAL_LOCAL_ONLY').is_file())
        self.assertFalse((c.runtime_root/'.F_WY_AUTHORED_ONLY').exists());self.assertFalse((c.runtime_root/'inputs').exists())
        self.assertTrue((c.runtime_root/'bootstrap_inspection/observation.local.json').is_file())
        from civiclab.e02.f_wy_actual_bootstrap_launcher_v1 import _existing_runtime
        from civiclab.e02.f_wy_local_pilot_v1_1 import read_partial
        with api.native_session(c):
            a=_existing_runtime(c);self.assertEqual(a.origin,'ACTUAL')
            p=read_partial(a,'PRIMARY');r=read_partial(a,'REPLAY');self.assertEqual(p[0].blobs(),r[0].blobs());self.assertEqual(p[2],r[2])
        self.assertEqual(Control(c).storage()['raw'],c.manifest['archive_bytes'])
        self.assertEqual(state['reserved']['rows'],24)

    def test_W03_without_execution_release_no_native_dispatch(self):
        c,o=self.env.inspect()
        with self.assertRaises(Blocked):api.run_authorized(c)
        self.assertFalse(c.runtime_root.exists())

    def test_W04_same_bytes_parent_replacement_after_header_refuses(self):
        c=self.env.admit();original=api._header_only;data=self.env.source_path.read_bytes()
        def change(*args):
            out=original(*args);p=self.env.source_path.parent;p.rename(p.with_name('old-input-parent'));p.mkdir();self.env.source_path.write_bytes(data);return out
        with patch.object(api,'_header_only',side_effect=change),self.assertRaises(Blocked):api.inspect_authorized(c)
        self.assertEqual(Control(c).snapshot()['shutdown'],'SHUTDOWN_UNKNOWN');self.assertFalse((c.control_root/'observation.local.json').exists())

    def test_W04_wrong_E_supplement_or_source_identity_refuses_before_admission(self):
        c,o=self.env.inspect();runtime=self.env.runtime_config(c)
        e=json.loads((self.env.root/runtime['actual_approvals']['execution']['path']).read_text());e['post_inspection_state_sha256']='0'*64
        runtime['actual_approvals']['execution']=self.env.record('wrong_E',e)
        with self.assertRaises(Blocked):api.admit_execution(c,runtime)
        self.assertNotIn('release',Control(c).snapshot());self.assertFalse(c.runtime_root.exists())

    def test_W04_expired_review_gap_blocks_release_without_reset(self):
        c,o=self.env.inspect();runtime=self.env.runtime_config(c);ctl=Control(c);original=ctl.snapshot()['t0']
        import civiclab.e02.f_wy_actual_bootstrap_control_v1 as control_module
        actual=control_module.stamp
        def later():
            value=actual();value['wall']+=10801;value['mono']+=10801;return value
        with patch.object(control_module,'stamp',later):
            with self.assertRaises(Blocked):api.admit_execution(c,runtime)
        self.assertEqual(ctl.snapshot()['t0'],original);self.assertFalse(c.runtime_root.exists())

    def test_W05_all_owned_binding_and_unexpected_files_exact_cap(self):
        c=self.env.admit();ctl=Control(c,create=True);before=ctl.storage()['core']
        (c.control_root/'unexpected').write_bytes(b'x'*123)
        self.assertEqual(ctl.storage()['core'],before+123)
        binding=c.control_root/'inspection-admission.local.json';self.assertGreater(binding.stat().st_size,0)
        direct=sum(p.stat().st_size for p in c.control_root.rglob('*') if p.is_file())
        self.assertEqual(ctl.storage()['core'],direct)
        cap=c.config['storage']['caps']['core'];used=ctl.storage()['core']
        self.assertEqual(ctl.storage(extra=cap-used)['core'],cap)
        with self.assertRaises(Blocked):ctl.storage(extra=cap-used+1)
        self.assertEqual(ctl.storage()['raw'],c.manifest['archive_bytes'])

    def test_W05_copy_failure_retains_created_actual_root_without_ENROLL(self):
        c,o=self.env.inspect();api.admit_execution(c,self.env.runtime_config(c))
        from civiclab.e02.f_actual_ledger_v1_1 import Storage
        original=Storage.write
        def fail(store,path,blob):
            if 'bootstrap_inspection' in Path(path).parts:raise OSError('TEST_ONLY_COPY_FAIL')
            return original(store,path,blob)
        with patch.object(Storage,'write',fail),self.assertRaises(Blocked):Launcher(c).run_stage('ENROLL')
        self.assertTrue(c.runtime_root.exists());self.assertFalse((c.runtime_root/'ENROLL.local.json').exists())
        self.assertEqual(Control(c).snapshot()['shutdown'],'SHUTDOWN_UNKNOWN')

    def test_W06_reserved_failed_and_native_barriers_no_refund(self):
        c=self.env.admit();ctl=Control(c,create=True);before=ctl.snapshot();ctl.start('INSPECT');ctl.unknown();after=ctl.snapshot()
        self.assertEqual(before['reserved'],after['reserved']);self.assertEqual(before['t0'],after['t0'])
        with self.assertRaises(Blocked):ctl.start('INSPECT')

    def test_W07_independent_cleanup_exact_state_no_authority_or_reset(self):
        c=self.env.admit();ctl=Control(c,create=True);ctl.start('INSPECT');ctl.unknown();state=ctl.snapshot()
        record={'realm':'TEST_ONLY','status':'PASS_EXACT_BOOTSTRAP_SHUTDOWN_OBSERVATION_ONLY','auditor_role':'independent_auditor','inspection_authorization_sha256':c.binding['refs']['inspection']['sha256'],'state_sha256':canonical_hash(state),'original_root':str(c.control_root),'shutdown_observed':True,'authority_granted':False,'liveness_evidence':'TEST_ONLY_NO_PROCESS_DISPATCHED_NOT_OWNER_AUTHORITY'}
        wrong={**record,'authority_granted':True}
        with self.assertRaises(Blocked):api.admit_independent_cleanup(c,self.env.record('wrong_cleanup',wrong))
        after=api.admit_independent_cleanup(c,self.env.record('cleanup',record))
        self.assertEqual(after['reserved'],state['reserved']);self.assertEqual(after['t0'],state['t0']);self.assertTrue(after['failed'])
        with self.assertRaises(Blocked):ctl.start('ENROLL')
        with self.assertRaises(Blocked):api.admit_inspection(self.env.live)

    def test_W08_metadata_path_traversal_and_unreviewed_bytes_refuse(self):
        live=deepcopy(self.env.live);live['live_refs']['inspection']['path']='../escape.json'
        with self.assertRaises(Blocked):api.admit_test_inspection(self.env.realm,live)
        p=self.env.root/self.env.live['live_refs']['implementation_review']['path'];p.write_text('{}')
        with self.assertRaises(Blocked):self.env.admit()

    def test_W02_directory_timestamp_change_allowed_but_symlink_denied(self):
        c=self.env.admit();original=api._header_only
        def update(*args):
            value=original(*args);(self.env.source_path.parent/'unrelated').write_text('TEST_ONLY');return value
        with patch.object(api,'_header_only',side_effect=update):o=api.inspect_authorized(c)
        self.assertEqual(o['realm'],'TEST_ONLY')

    def test_W04_observation_sealed_state_coedit_cannot_fake_checkpoint(self):
        c,o=self.env.inspect();p=c.control_root/'observation.local.json';o['post_inspection_state_sha256']='0'*64;save(p,o)
        with self.assertRaises(Blocked):api.observation(c)

    def test_W05_root_already_exists_or_copy_bypass_never_ENROLL(self):
        c,o=self.env.inspect();api.admit_execution(c,self.env.runtime_config(c));c.runtime_root.mkdir(parents=True)
        with self.assertRaises(Blocked):Launcher(c).run_stage('ENROLL')
        self.assertFalse((c.runtime_root/'ENROLL.local.json').exists())

    def test_W06_whole_stage_overrun_and_clock_discontinuity(self):
        c=self.env.admit();ctl=Control(c,create=True);ctl.start('INSPECT')
        import civiclab.e02.f_wy_actual_bootstrap_control_v1 as module
        actual=module.stamp
        def late():
            value=actual();value['wall']+=301;value['mono']+=301;return value
        with patch.object(module,'stamp',late):
            with self.assertRaises(Blocked):ctl.commit('INSPECT',{'closure':'VERIFIED_NORMAL_CLOSED'})
        state=ctl.snapshot();self.assertEqual(state['stages']['INSPECT']['status'],'PENDING');self.assertEqual(state['reserved'],ctl.charge)
        a=stamp();b=dict(a);b['boot']='OTHER'
        with self.assertRaises(Blocked):elapsed(a,b)

    def test_W06_live_cancel_fixed_native_new_session_unknown_charges(self):
        c=self.env.admit();ctl=Control(c,create=True);ctx=multiprocessing.get_context('fork');pidfile=self.env.root/'TEST_ONLY_worker_pid'
        def slow(context,key):
            from civiclab.e02.national_population import supervise_fixture
            def worker():pidfile.write_text(str(os.getpid()));time.sleep(30);return {}
            value,res=supervise_fixture(worker,seconds=300,rss_bytes=512*1024**2)
            return {'inspection':value,'native':None}
        def controller():
            with patch('civiclab.e02.f_wy_actual_bootstrap_launcher_v1._stage',slow):
                try:Launcher(c).run_stage('INSPECT')
                except Blocked:pass
        owner=ctx.Process(target=controller);owner.start();child=None
        try:
            for _ in range(600):
                if pidfile.exists():break
                time.sleep(.02)
            self.assertTrue(pidfile.exists());child=int(pidfile.read_text());self.assertEqual(os.getpgid(child),child)
            Launcher(c).request_cancel();owner.join(12);self.assertFalse(owner.is_alive())
            stopped=subprocess.run(['ps','-o','stat=','-p',str(child)],capture_output=True,text=True,timeout=1)
            self.assertTrue(stopped.returncode!=0 or stopped.stdout.strip().startswith('Z'))
            self.assertEqual(ctl.snapshot()['shutdown'],'SHUTDOWN_UNKNOWN');self.assertEqual(ctl.snapshot()['reserved'],ctl.charge)
        finally:
            if owner.is_alive():owner.kill();owner.join(3)
            if child:
                try:os.kill(child,signal.SIGKILL)
                except ProcessLookupError:pass

    def test_W06_controller_death_no_claim_of_kill_separate_harness_cleanup(self):
        c=self.env.admit();ctl=Control(c,create=True);ctx=multiprocessing.get_context('fork');pidfile=self.env.root/'TEST_ONLY_survivor_pid'
        def slow(context,key):pidfile.write_text(str(os.getpid()));time.sleep(30);return {'inspection':{},'native':None}
        def controller():
            with patch('civiclab.e02.f_wy_actual_bootstrap_launcher_v1._stage',slow):Launcher(c).run_stage('INSPECT')
        owner=ctx.Process(target=controller);owner.start();child=None
        try:
            for _ in range(600):
                if pidfile.exists():break
                time.sleep(.02)
            self.assertTrue(pidfile.exists());child=int(pidfile.read_text());os.kill(owner.pid,signal.SIGKILL);owner.join(3)
            os.kill(child,0);self.assertEqual(ctl.snapshot()['stages']['INSPECT']['status'],'PENDING');ctl.unknown()
            with self.assertRaises(Blocked):Launcher(c).run_stage('INSPECT')
            os.kill(child,signal.SIGKILL)
            stopped=False
            for _ in range(100):
                result=subprocess.run(['ps','-o','stat=','-p',str(child)],capture_output=True,text=True,timeout=1)
                if result.returncode!=0 or result.stdout.strip().startswith('Z'):stopped=True;break
                time.sleep(.02)
            self.assertTrue(stopped);self.assertEqual(ctl.snapshot()['reserved'],ctl.charge)
        finally:
            if owner.is_alive():owner.kill();owner.join(3)
            if child:
                try:os.kill(child,signal.SIGKILL)
                except ProcessLookupError:pass

    def test_W02_file_replacement_and_symlink_full_path_failures(self):
        for mode in ('file','symlink'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                env=FakeRepository(Path(t)/'fake');c=env.admit();original=api._header_only;data=env.source_path.read_bytes()
                def replace(*args):
                    value=original(*args);p=env.source_path;old=p.with_suffix('.previous');p.rename(old)
                    if mode=='file':p.write_bytes(data)
                    else:p.symlink_to(old)
                    return value
                with patch.object(api,'_header_only',side_effect=replace),self.assertRaises(Blocked):api.inspect_authorized(c)
                self.assertEqual(Control(c).snapshot()['shutdown'],'SHUTDOWN_UNKNOWN')

    def test_W05_hardlinks_copies_and_binding_tamper(self):
        c=self.env.admit();ctl=Control(c,create=True);p=c.control_root/'extra';p.write_bytes(b'x'*31);before=ctl.storage()['core'];os.link(p,c.control_root/'duplicate')
        self.assertEqual(ctl.storage()['core'],before+31)
        (c.control_root/'inspection-admission.local.json').write_text('{}')
        with self.assertRaises(Blocked):ctl.snapshot()

    def test_W07_changed_cleanup_receipt_invalidates_history(self):
        c=self.env.admit();ctl=Control(c,create=True);ctl.start('INSPECT');ctl.unknown();state=ctl.snapshot()
        record={'realm':'TEST_ONLY','status':'PASS_EXACT_BOOTSTRAP_SHUTDOWN_OBSERVATION_ONLY','auditor_role':'independent_auditor','inspection_authorization_sha256':c.binding['refs']['inspection']['sha256'],'state_sha256':canonical_hash(state),'original_root':str(c.control_root),'shutdown_observed':True,'authority_granted':False,'liveness_evidence':'TEST_ONLY_NO_DISPATCH'}
        ref=self.env.record('immutable_cleanup',record);api.admit_independent_cleanup(c,ref)
        (self.env.root/ref['path']).write_text('{}')
        with self.assertRaises(Blocked):ctl.snapshot()

    def test_W08_copied_realm_root_or_context_cannot_redirect_source(self):
        c=self.env.admit();redirect=api.Realm(self.env.root.parent/'outside','TEST_ONLY',c.realm.token)
        fake=api.InspectionContext(redirect,c.spec_json,c.binding_json,c.token)
        with patch('civiclab.e02.f_wy_actual_bootstrap_v1._open_no_follow',side_effect=AssertionError('source')):
            with self.assertRaises(Blocked):api.require_context(fake)



    def test_W01_scope_numeric_bool_substitution_is_not_authority(self):
        live=deepcopy(self.env.live);r=json.loads((self.env.root/live['live_refs']['inspection']['path']).read_text());r['scope']['single_use']=1
        live['live_refs']['inspection']=self.env.record('numeric_bool',r)
        with self.assertRaises(Blocked):api.admit_test_inspection(self.env.realm,live)

    def test_W04_substituted_S_identity_with_rebound_E_still_refuses(self):
        c,o=self.env.inspect();runtime=self.env.runtime_config(c)
        s=json.loads((self.env.root/runtime['actual_approvals']['exact_source']['path']).read_text());s['source_identity']['inode']+=1
        sr=self.env.record('substituted_S',s);runtime['actual_approvals']['exact_source']=sr
        e=json.loads((self.env.root/runtime['actual_approvals']['execution']['path']).read_text());e['exact_source_approval_sha256']=sr['sha256']
        runtime['actual_approvals']['execution']=self.env.record('rebound_E',e)
        with self.assertRaises(Blocked):api.admit_execution(c,runtime)
        self.assertFalse(c.runtime_root.exists())

    def test_W06_native_source_failure_survives_independent_cleanup(self):
        c,o=self.env.inspect();api.admit_execution(c,self.env.runtime_config(c))
        self.env.source_path.write_bytes(self.env.source_path.read_bytes()+b'TEST_ONLY_DRIFT')
        with self.assertRaises(Blocked):Launcher(c).run_stage('ENROLL')
        state=Control(c).snapshot();record={'realm':'TEST_ONLY','status':'PASS_EXACT_BOOTSTRAP_SHUTDOWN_OBSERVATION_ONLY','auditor_role':'independent_auditor','inspection_authorization_sha256':c.binding['refs']['inspection']['sha256'],'state_sha256':canonical_hash(state),'original_root':str(c.control_root),'shutdown_observed':True,'authority_granted':False,'liveness_evidence':'TEST_ONLY_CLOSED_FAILED_NATIVE_STAGE'}
        api.admit_independent_cleanup(c,self.env.record('native_failure_cleanup',record))
        from civiclab.e02.f_wy_actual_bootstrap_launcher_v1 import _existing_runtime
        from civiclab.e02.f_actual_ledger_v1_1 import PilotLedger
        with api.native_session(c):
            a=_existing_runtime(c);native=PilotLedger(a).snapshot()
            self.assertTrue(native['source_halted']);self.assertEqual(native['stages']['ENROLL']['status'],'FAILED')
        with self.assertRaises(Blocked):Launcher(c).run_stage('ENROLL')
        self.assertEqual(Control(c).snapshot()['reserved'],state['reserved'])


def retain_actual_wiring_evidence(destination):
    """New TEST_ONLY actual-shaped repository, never a real input/approval argument."""
    destination=Path(destination).resolve();destination.mkdir(exist_ok=False)
    env=FakeRepository(destination/'normal_fake_repo',full=True);c,o=env.inspect();runtime=env.runtime_config(c)
    api.admit_execution(c,runtime);state=api.run_authorized(c)
    from civiclab.e02.f_wy_actual_bootstrap_launcher_v1 import _existing_runtime
    from civiclab.e02.f_wy_local_pilot_v1_1 import read_partial
    with api.native_session(c):
        a=_existing_runtime(c);primary=read_partial(a,'PRIMARY');replay=read_partial(a,'REPLAY')
        assert primary[0].blobs()==replay[0].blobs() and primary[2]==replay[2]
    failed=FakeRepository(destination/'path_fault_fake_repo');bad=failed.admit();original=api._header_only;data=failed.source_path.read_bytes()
    def replace(*args):
        value=original(*args);p=failed.source_path.parent;p.rename(p.with_name('before-replacement'));p.mkdir();failed.source_path.write_bytes(data);return value
    refused=False
    with patch.object(api,'_header_only',side_effect=replace):
        try:api.inspect_authorized(bad)
        except Blocked:refused=True
    assert refused
    cleanup_env=FakeRepository(destination/'cleanup_fake_repo');cc=cleanup_env.admit();ctl=Control(cc,create=True);ctl.start('INSPECT');ctl.unknown();unknown=ctl.snapshot()
    cleanup={'realm':'TEST_ONLY','status':'PASS_EXACT_BOOTSTRAP_SHUTDOWN_OBSERVATION_ONLY','auditor_role':'independent_auditor','inspection_authorization_sha256':cc.binding['refs']['inspection']['sha256'],'state_sha256':canonical_hash(unknown),'original_root':str(cc.control_root),'shutdown_observed':True,'authority_granted':False,'liveness_evidence':'TEST_ONLY_NO_PROCESS_DISPATCHED_NOT_REAL_DEATH_REVIEW'}
    after=api.admit_independent_cleanup(cc,cleanup_env.record('cleanup',cleanup))
    summary={'realm':'TEST_ONLY','kind':'CONDITIONAL_ACTUAL_SHAPED_WIRING_MOCK_EVIDENCE',
             'real_source_operations':0,'real_source_rows':0,'actual_inference_calls':0,'API_spend_usd':0,
             'fake_source_rows_per_parse':78,'native_actual_shaped_rows_total':156,
             'native_admission_origin':a.origin,'source_archive_count_for_normal_flow':1,
             'normal_shutdown':state['shutdown'],'normal_reserved':state['reserved'],
             'exact_primary_replay':True,'runtime_source_inputs_copy_exists':(c.runtime_root/'inputs').exists(),
             'normal_owned_storage':Control(c).storage(),'same_byte_path_fault_refused':refused,
             'path_fault_shutdown':Control(bad).snapshot()['shutdown'],
             'cleanup_no_dispatch_case_shutdown':after['shutdown'],'cleanup_preserved_t0':after['t0']==unknown['t0'],
             'cleanup_preserved_charges':after['reserved']==unknown['reserved'],
             'production_defaults_and_test_authority':'Production fields unpopulated; fake reports are TEST_ONLY and rejected by production loader.'}
    save(destination/'summary.local.json',summary)
    files={str(p.relative_to(destination)):digest(p) for p in sorted(destination.rglob('*')) if p.is_file()}
    save(destination/'index.local.json',{'realm':'TEST_ONLY','files':files})
    return summary
