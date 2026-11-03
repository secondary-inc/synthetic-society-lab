"""Authored-only bootstrap adversarial fixtures; no actual cache access."""
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
from civiclab.e02.f_wy_bootstrap_v1 import make_fixture, inspect_fixture, inspect_actual, require_bundle, AuthoredBundle
from civiclab.e02.f_wy_bootstrap_control_v1 import Control, stamp, elapsed, ORDER
from civiclab.e02.f_wy_bootstrap_launcher_v1 import Launcher, execute_actual, _existing_runtime, _processes
from test_e02_f_wy_local_v1_1 import rows


class Clock:
    def __init__(self): self.value = {'wall': 1000.0, 'mono': 1000.0, 'boot': 'AUTHORED_TEST_BOOT'}
    def __call__(self): return deepcopy(self.value)
    def advance(self, seconds):
        self.value['wall'] += seconds; self.value['mono'] += seconds


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.b = make_fixture(self.root/'bundle', rows())
    def tearDown(self): self.tmp.cleanup()
    def control(self): return Control(self.b, create=True)

    def test_actual_default_denied_before_any_filesystem_or_socket(self):
        with patch('pathlib.Path.stat', side_effect=AssertionError('stat')), patch('pathlib.Path.open', side_effect=AssertionError('open')), patch('os.open', side_effect=AssertionError('osopen')):
            for fn in (inspect_actual, execute_actual):
                with self.assertRaises(Blocked): fn('/actual/cache/MUST_NOT_TOUCH.zip', approval={'status':'PASS'})
            with self.assertRaises(Blocked): require_bundle({'actual_authority':1})

    def test_bundle_copied_field_override_refuses_before_source(self):
        b = AuthoredBundle(self.b.root/'elsewhere', self.b.source, self.b.binding_json, self.b.rows_json, self.b.token)
        with patch('os.open', side_effect=AssertionError('source')):
            with self.assertRaises(Blocked): require_bundle(b)

    def test_full_plan_reserved_before_inspection_and_no_runtime_precreation(self):
        c = self.control(); s = c.snapshot()
        self.assertEqual(s['reserved'], c.charge)
        self.assertEqual(c.charge['seconds'], 1800); self.assertEqual(c.charge['ops'],12000000)
        self.assertEqual(c.charge['rows'],24); self.assertFalse((self.b.root/'runtime').exists())
        with self.assertRaises(Blocked): inspect_fixture(self.b,c)
        c.start('INSPECT'); result = inspect_fixture(self.b,c)
        self.assertEqual(result['person_rows_read'],0); self.assertFalse(result['full_person_crc_scan_performed'])
        self.assertEqual(result['archive_bytes_hashed'],self.b.source.manifest['archive_bytes'])
        self.assertEqual(result['header_bytes_read'],self.b.source.manifest['header_bytes'])
        self.assertEqual(c.snapshot()['reserved'],s['reserved'])

    def test_single_descriptor_no_path_reopen_and_no_person_zipstream(self):
        import zipfile
        c = self.control(); c.start('INSPECT'); orig=zipfile.ZipFile.open; names=[]
        def watched(z,name,*args,**kwargs):
            names.append(name); return orig(z,name,*args,**kwargs)
        with patch.object(zipfile.ZipFile,'open',watched): inspect_fixture(self.b,c)
        self.assertEqual(names,[self.b.source.manifest['companion']])

    def test_deflated_header_output_is_bounded_without_row_scan(self):
        import io,zipfile
        from civiclab.e02.f_wy_bootstrap_v1 import _header_only
        header=b'COLUMN_A,COLUMN_B\n';body=header+b'PRIVATE_AUTHORED_ONLY,0\n'*10000
        memory=io.BytesIO()
        with zipfile.ZipFile(memory,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('person.csv',body)
        data=memory.getvalue()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            result=_header_only(io.BytesIO(data),z.getinfo('person.csv'),len(header),len(data))
        self.assertEqual(result,header);self.assertNotIn(b'PRIVATE',result)

    def test_source_symlink_and_archive_drift_fail_with_full_charge(self):
        c=self.control(); c.start('INSPECT'); before=c.snapshot()['reserved']
        p=self.b.source.path; original=p.read_bytes(); p.write_bytes(original+b'x')
        with self.assertRaises(Blocked): inspect_fixture(self.b,c)
        p.write_bytes(original); moved=p.with_suffix('.moved'); p.rename(moved);p.symlink_to(moved)
        with self.assertRaises((Blocked,OSError)): inspect_fixture(self.b,c)
        self.assertEqual(before,c.snapshot()['reserved'])

    def test_parent_directory_symlink_refused(self):
        c=self.control();c.start('INSPECT')
        parent=self.b.source.path.parent; moved=parent.with_name('other-inputs');parent.rename(moved);parent.symlink_to(moved,target_is_directory=True)
        with self.assertRaises((Blocked,OSError)):inspect_fixture(self.b,c)

    def test_extra_member_and_duplicate_header_generated_as_authored_only(self):
        for kind in ('member','header'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as t:
                def bad(root,data):return create_fixture(root,data,edit=(kind,0))
                with patch('civiclab.e02.f_wy_bootstrap_v1.create_fixture',side_effect=bad):b=make_fixture(Path(t)/'bad',rows())
                c=Control(b,create=True);c.start('INSPECT')
                with self.assertRaises(Blocked):inspect_fixture(b,c)

    def test_order_duplicate_and_unknown_cannot_be_success(self):
        c=self.control()
        for key in ('ENROLL','NOPE','FINALIZE_PRIMARY'):
            with self.assertRaises(Blocked):c.start(key)
        c.start('INSPECT')
        with self.assertRaises(Blocked):c.start('INSPECT')
        before=c.snapshot();c.unknown();after=c.snapshot()
        self.assertEqual(before['reserved'],after['reserved']);self.assertEqual(after['shutdown'],'SHUTDOWN_UNKNOWN')
        for key in ORDER:
            with self.assertRaises(Blocked):c.start(key)

    def test_cleanup_cannot_refund_renew_clear_failure_or_authorize(self):
        c=self.control();c.start('INSPECT');c.unknown();before=c.snapshot()
        review={'kind':'TEST_ONLY_INDEPENDENT_CLEANUP','state_sha256':canonical_hash(before),'original_root':str(c.root),'shutdown_observed':True,'authority_granted':False}
        wrong={**review,'authority_granted':True}
        with self.assertRaises(Blocked):c.cleanup_fixture(wrong)
        c.cleanup_fixture(review);after=c.snapshot()
        self.assertEqual(after['t0'],before['t0']);self.assertEqual(after['reserved'],before['reserved'])
        self.assertTrue(after['failed']);self.assertEqual(after['stages'],before['stages'])
        with self.assertRaises(Blocked):c.start('ENROLL')

    def test_global_deadline_includes_review_gap_and_equality(self):
        clock=Clock()
        with patch('civiclab.e02.f_wy_bootstrap_control_v1.stamp',clock):
            c=self.control();initial=c.snapshot();clock.advance(10800)
            with self.assertRaises(Blocked):c.start('INSPECT')
            self.assertEqual(c.snapshot()['t0'],initial['t0']);self.assertEqual(c.snapshot()['reserved'],initial['reserved'])

    def test_normal_stage_completion_checks_whole_elapsed(self):
        clock=Clock()
        with patch('civiclab.e02.f_wy_bootstrap_control_v1.stamp',clock):
            c=self.control();c.start('INSPECT');clock.advance(301)
            with self.assertRaises(Blocked):c.commit('INSPECT',{'closure':'VERIFIED_NORMAL_CLOSED'})
            self.assertEqual(c.snapshot()['stages']['INSPECT']['status'],'PENDING')
            c.unknown();self.assertEqual(c.snapshot()['reserved'],c.charge)

    def test_rollback_boot_change_and_nonfinite_refuse(self):
        a={'wall':10.,'mono':10.,'boot':'A'}
        for b in ({'wall':9.,'mono':11.,'boot':'A'},{'wall':11.,'mono':11.,'boot':'B'},{'wall':float('nan'),'mono':11.,'boot':'A'},{'wall':20.,'mono':11.,'boot':'A'}):
            with self.subTest(b=b),self.assertRaises(Blocked):elapsed(a,b)

    def test_missing_copied_or_torn_journal_never_reinitializes(self):
        c=self.control();c.start('INSPECT')
        path=c.root/'state.json';state=json.loads(path.read_text());state['reserved']['rows']=0;path.write_text(json.dumps(state))
        with self.assertRaises(Blocked):Control(self.b)
        path.unlink()
        with self.assertRaises(Blocked):Control(self.b)
        with self.assertRaises(FileExistsError):Control(self.b,create=True)

    def test_duplicate_json_keys_and_symlink_journal_refuse(self):
        c=self.control();p=c.root/'state.json';original=p.read_text()
        p.write_text(original.rstrip()[:-1]+',"generation":0}')
        with self.assertRaises(Blocked):c.snapshot()
        p.write_text(original);saved=c.root/'saved';p.rename(saved);p.symlink_to(saved)
        with self.assertRaises(Blocked):c.snapshot()

    def test_concurrent_control_and_launcher_owner_refuse(self):
        c=self.control();l=Launcher(self.b)
        with c.lock():
            with self.assertRaises(Blocked):Control(self.b)
        with l.owner():
            with self.assertRaises(Blocked):Launcher(self.b).run_stage('INSPECT')

    def test_unknown_backend_refuses_before_start(self):
        c=self.control();l=Launcher(self.b)
        with patch('civiclab.e02.f_wy_bootstrap_launcher_v1._stage',side_effect=AssertionError('work')):
            with self.assertRaises(Blocked):l.run_stage('INSPECT',backend='DAEMON_OR_ARBITRARY_DESCENDANTS')
        self.assertEqual(c.snapshot()['stages'],{})

    def test_storage_raw_duplicates_hardlinks_and_temporaries_count(self):
        c=self.control();before=c.storage()['core'];p=c.root/'duplicate';p.write_bytes(b'x'*512)
        os.link(p,c.root/'hardlink')
        self.assertGreaterEqual(c.storage()['core'],before+1024)
        with self.assertRaises(Blocked):c.storage(extra=c.c['storage']['caps']['core'])
        with self.assertRaises(Blocked):c.storage(category='newpool',extra=1)
        with self.assertRaises(Blocked):c.storage(extra=-1)

    def test_copied_control_root_cannot_redirect_storage_scan(self):
        c=self.control();c.root=self.root/'MUST_NOT_SCAN'
        with patch('pathlib.Path.rglob',side_effect=AssertionError('redirected scan')):
            with self.assertRaises(Blocked):c.storage()

    def test_low_disk_and_symlink_storage_refuse(self):
        c=self.control();usage=shutil.disk_usage(c.root)
        with patch('shutil.disk_usage',return_value=usage._replace(free=0)):
            with self.assertRaises(Blocked):c.start('INSPECT')
        (c.root/'alias').symlink_to(c.root/'state.json')
        with self.assertRaises(Blocked):c.storage()

    def test_failed_artifact_write_retains_pending_charge(self):
        c=self.control();c.start('INSPECT')
        with patch('pathlib.Path.write_text',side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):c.commit('INSPECT',{'closure':'VERIFIED_NORMAL_CLOSED'})
        self.assertEqual(c.snapshot()['stages']['INSPECT']['status'],'PENDING');self.assertEqual(c.snapshot()['reserved'],c.charge)

    def test_launcher_deadline_or_bad_closure_unknown_no_success(self):
        c=self.control();l=Launcher(self.b)
        with patch('civiclab.e02.f_wy_bootstrap_launcher_v1.elapsed',return_value=301):
            with self.assertRaises(Blocked):l.run_stage('INSPECT')
        self.assertEqual(c.snapshot()['shutdown'],'SHUTDOWN_UNKNOWN')
        with self.assertRaises(Blocked):l.run_stage('INSPECT')

    def test_process_identity_unknown_sampling_is_failure(self):
        c=self.control();l=Launcher(self.b)
        with patch('civiclab.e02.f_wy_bootstrap_launcher_v1._sample',side_effect=Blocked('unknown PID sample')):
            with self.assertRaises(Blocked):l.run_stage('INSPECT')
        self.assertEqual(c.snapshot()['shutdown'],'SHUTDOWN_UNKNOWN')

    def test_root_order_and_copied_evidence_tampering_refuses(self):
        self.control();l=Launcher(self.b);l.run_stage('INSPECT')
        self.assertFalse((self.b.root/'runtime').exists());l.run_stage('ENROLL')
        self.assertTrue((self.b.root/'runtime/inspection_copy/index.local.json').is_file())
        raw=l.control.storage()['raw'];self.assertEqual(raw,2*self.b.source.manifest['archive_bytes'])
        p=self.b.root/'runtime/inspection_copy/genesis.json';p.write_text('{}')
        with self.assertRaises(Blocked):l.run_stage('PRIMARY')
        self.assertEqual(l.control.snapshot()['shutdown'],'SHUTDOWN_UNKNOWN')

    def test_existing_runtime_root_and_copy_failure_do_not_enroll(self):
        self.control();l=Launcher(self.b);l.run_stage('INSPECT');(self.b.root/'runtime').mkdir()
        with self.assertRaises(Blocked):l.run_stage('ENROLL')
        self.assertFalse((self.b.root/'runtime/ENROLL.local.json').exists())

    def test_happy_all_six_stages_normal_close_exact_replay(self):
        c=self.control();s=Launcher(self.b).run()
        self.assertEqual(s['reserved'],c.charge);self.assertEqual(s['shutdown'],'CLOSED');self.assertFalse(s['failed'])
        self.assertEqual(set(s['stages']),set(ORDER));self.assertEqual(s['model_calls'],0)
        a=_existing_runtime(self.b)
        from civiclab.e02.f_wy_local_pilot_v1_1 import read_partial
        primary=read_partial(a,'PRIMARY');replay=read_partial(a,'REPLAY')
        self.assertEqual(primary[0].blobs(),replay[0].blobs());self.assertEqual(primary[2],replay[2])
        proof=json.loads((c.root/'INSPECT.proof.local.json').read_text())
        self.assertEqual(proof['result']['inspection']['person_rows_read'],0)
        self.assertTrue(proof['normal_join_observed']);self.assertEqual(proof['stage_exitcode'],0)
        self.assertEqual(proof['actual_source_rows'],0)

    def test_copy_failure_preserves_admitted_root_but_never_enrolls(self):
        self.control();l=Launcher(self.b);l.run_stage('INSPECT')
        from civiclab.e02.f_actual_ledger_v1_1 import Storage
        original=Storage.write
        def fail_copy(store,path,blob):
            if 'inspection_copy' in Path(path).parts:raise OSError('AUTHORED_COPY_FAILURE')
            return original(store,path,blob)
        with patch.object(Storage,'write',fail_copy):
            with self.assertRaises(Blocked):l.run_stage('ENROLL')
        self.assertTrue((self.b.root/'runtime/.F_WY_AUTHORED_ONLY').is_file())
        self.assertFalse((self.b.root/'runtime/ENROLL.local.json').exists())
        self.assertEqual(l.control.snapshot()['shutdown'],'SHUTDOWN_UNKNOWN')

    def test_live_parent_cancel_runs_native_new_session_cleanup(self):
        c=self.control();ctx=multiprocessing.get_context('fork');pidfile=self.root/'native-worker-pid'
        def slow_native(bundle,key):
            from civiclab.e02.national_population import supervise_fixture
            def work():
                pidfile.write_text(str(os.getpid()));time.sleep(20)
                return {'AUTHORED':True}
            value,res=supervise_fixture(work,seconds=300,rss_bytes=512*1024**2)
            return {'inspection':value,'native':None}
        def controller():
            with patch('civiclab.e02.f_wy_bootstrap_launcher_v1._stage',slow_native):
                try:Launcher(self.b).run_stage('INSPECT')
                except Blocked:pass
        owner=ctx.Process(target=controller);owner.start();worker=None
        try:
            for _ in range(400):
                if pidfile.exists():break
                time.sleep(.02)
            self.assertTrue(pidfile.exists());worker=int(pidfile.read_text())
            self.assertEqual(os.getpgid(worker),worker)  # pinned inner setsid topology
            Launcher(self.b).request_cancel_fixture();owner.join(8)
            self.assertFalse(owner.is_alive());self.assertEqual(owner.exitcode,0)
            state=subprocess.run(['ps','-o','stat=','-p',str(worker)],capture_output=True,text=True,timeout=1)
            self.assertTrue(state.returncode != 0 or state.stdout.strip().startswith('Z'))
            self.assertEqual(c.snapshot()['shutdown'],'SHUTDOWN_UNKNOWN')
            self.assertEqual(c.snapshot()['reserved'],c.charge)
        finally:
            if owner.is_alive():owner.kill();owner.join(3)
            if worker:
                try:os.kill(worker,signal.SIGKILL)
                except ProcessLookupError:pass

    def test_real_controller_death_retains_pending_unknown_and_separate_cleanup(self):
        c=self.control();ctx=multiprocessing.get_context('fork');pidfile=self.root/'stage-pid'
        def slow_stage(bundle,key):
            pidfile.write_text(str(os.getpid()));time.sleep(30)
            return {'inspection':{},'native':None}
        def controller():
            with patch('civiclab.e02.f_wy_bootstrap_launcher_v1._stage',slow_stage):Launcher(self.b).run_stage('INSPECT')
        owner=ctx.Process(target=controller);owner.start()
        child=None
        try:
            for _ in range(400):
                if pidfile.exists():break
                time.sleep(.02)
            self.assertTrue(pidfile.exists());child=int(pidfile.read_text());os.kill(owner.pid,signal.SIGKILL);owner.join(3)
            self.assertIsNotNone(owner.exitcode);self.assertEqual(c.snapshot()['stages']['INSPECT']['status'],'PENDING')
            # Separate harness explicitly observes the survivor; no dead-parent cleanup claim.
            os.kill(child,0);c.unknown();before=c.snapshot()
            with self.assertRaises(Blocked):Launcher(self.b).run_stage('INSPECT')
            os.kill(child,signal.SIGKILL)
            # Independent harness observes absent or non-running zombie state;
            # it does not claim to reap a reparented grandchild.
            stopped=False
            for _ in range(100):
                state=subprocess.run(['ps','-o','stat=','-p',str(child)],capture_output=True,text=True,timeout=1)
                if state.returncode != 0 or state.stdout.strip().startswith('Z'):
                    stopped=True;break
                time.sleep(.02)
            self.assertTrue(stopped,'harness cleanup not observed')
            review={'kind':'TEST_ONLY_INDEPENDENT_CLEANUP','state_sha256':canonical_hash(before),'original_root':str(c.root),'shutdown_observed':True,'authority_granted':False}
            c.cleanup_fixture(review)
            self.assertEqual(c.snapshot()['reserved'],before['reserved'])
            with self.assertRaises(Blocked):c.start('ENROLL')
        finally:
            if owner.is_alive():owner.kill();owner.join(3)
            if child:
                try:os.kill(child,signal.SIGKILL)
                except ProcessLookupError:pass


def retain_authored_evidence(destination):
    """New private fixture root only; no actual source or approval can be selected."""
    destination = Path(destination).resolve()
    destination.mkdir(exist_ok=False)
    good = make_fixture(destination/'normal', rows(full=True))
    Control(good,create=True)
    final = Launcher(good).run()
    pending = make_fixture(destination/'unknown_no_dispatch', rows())
    c = Control(pending,create=True);c.start('INSPECT');before=c.snapshot();c.unknown()
    unknown=c.snapshot()
    review={'kind':'TEST_ONLY_INDEPENDENT_CLEANUP','state_sha256':canonical_hash(unknown),
            'original_root':str(c.root),'shutdown_observed':True,'authority_granted':False}
    # No process was dispatched for this retained UNKNOWN fixture. Real kill/cleanup
    # behavior is tested separately; do not relabel this case as that crash probe.
    c.cleanup_fixture(review)
    summary={'kind':'MOCK_AUTHORED_BOOTSTRAP_EVIDENCE','normal_stages':list(ORDER),
             'normal_charge':final['reserved'],'normal_shutdown':final['shutdown'],
             'normal_source_rows_per_parse':good.source.manifest['expected_rows'],
             'actual_source_rows':0,'GETs':0,'model_calls':0,'api_spend_usd':0,
             'normal_storage':Control(good).storage(),
             'fixture_raw_archives':'Two independently generated identical authored archives; both retained byte copies charged, not an actual cache transfer.',
             'unknown_case':'RESERVATION_THEN_UNKNOWN_NO_PROCESS_DISPATCHED_NOT_CONTROLLER_DEATH',
             'unknown_full_charges_preserved':before['reserved']==c.snapshot()['reserved'],
             'unknown_after_cleanup':c.snapshot()['shutdown'],
             'real_parent_death_and_live_cancel':'SEPARATE_TEST_LOG_NOT_THIS_RETAINED_CASE'}
    (destination/'summary.local.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    files={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination/'index.local.json').write_text(json.dumps({'kind':'MOCK_PRIVATE_FIXTURE_INDEX','files':files},indent=2,sort_keys=True)+'\n')
    return summary
