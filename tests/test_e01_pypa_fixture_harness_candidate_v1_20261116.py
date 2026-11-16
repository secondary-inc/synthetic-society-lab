"""Pure API/IO doubles only. No actual installer/tool import or fixture install."""
import sys


def early_guard():
    def deny(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn',
                'os.system','os.exec','os.spawn','ctypes.dlopen'}:
            raise AssertionError('HARNESS_MOCK_NO_NETWORK_PROCESS_NATIVE')
        if event=='import' and args and args[0].split('.')[0] in {'installer','pip','ssl_fixture_payload',
                'pypdf','PIL','cryptography','cffi','_cffi_backend','pycparser'}:
            raise AssertionError('HARNESS_MOCK_NO_TOOL_OR_PAYLOAD_IMPORT')
    sys.addaudithook(deny)


if __name__=='__main__':early_guard()

import ast
import base64
import builtins
import contextlib
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import stat
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/'scripts/e01_pypa_fixture_harness_candidate_v1_20261116.py'


def load_own(name,path,expected=None):
    path=Path(path).resolve();raw=path.read_bytes()
    if path not in {CODE,Path(__file__).resolve()} or len(raw)>131072:
        raise AssertionError('HARNESS_MOCK_OWN_SOURCE_ONLY')
    if expected is not None and hashlib.sha256(raw).hexdigest()!=expected:
        raise AssertionError('HARNESS_MOCK_OWN_SOURCE_HASH')
    spec=importlib.util.spec_from_loader(name,loader=None,origin=str(path))
    module=importlib.util.module_from_spec(spec);module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


m=load_own('mocked_fixture_harness',CODE)


class MockAPI:
    """Authored data writer, not PyPA or a claimed implementation substitute."""
    mock_only=True
    def __init__(self,corrupt=None):self.calls=0;self.corrupt=corrupt;self.bindings=[]
    @contextlib.contextmanager
    def source_context(self,token):
        self.bindings.append((token.filename,token.sha256));yield token
    def destination(self,fs,prefix,marker):
        if marker!=m.MARKER:raise AssertionError('MOCK_MARKER_DRIFT')
        return fs,Path(prefix)
    def install(self,source,destination,additional_metadata):
        self.calls+=1;fs,prefix=destination
        # Read inert source bytes; never import/compile the payload.
        with source.open() as stream:
            with zipfile.ZipFile(stream) as archive:
                payload={name:archive.read(name) for name in archive.namelist() if name!=m.DIST+'RECORD'}
        files={'bin/fixture-cli':m.SCRIPT_BYTES}
        files.update({'site/'+name:body for name,body in payload.items()})
        files['site/'+m.DIST+'INSTALLER']=additional_metadata['INSTALLER']
        if self.corrupt=='SCRIPT':files['bin/fixture-cli']+=b'MOCK_CORRUPTION'
        if self.corrupt=='EXTRA':files['site/UNEXPECTED']=b'MOCK'
        for name,body in files.items():fs.write_new(prefix/name,body)
        rows=[]
        for name,body in sorted(files.items()):
            record_name='../bin/fixture-cli' if name=='bin/fixture-cli' else name[len('site/'):]
            hash_text='sha256='+base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b'=').decode()
            if self.corrupt=='RECORD_HASH':hash_text='sha256='+'A'*43
            rows.append([record_name,hash_text,str(len(body))])
        rows.append([m.DIST+'RECORD','',''])
        if self.corrupt=='RECORD_DUPLICATE':rows.append(rows[0][:])
        text=io.StringIO(newline='');csv.writer(text,lineterminator='\n').writerows(rows)
        fs.write_new(prefix/'site'/m.DIST/'RECORD',text.getvalue().encode())


class HarnessMockFlowTests(unittest.TestCase):
    def test_eight_cases_four_families_three_mock_installs_and_replay(self):
        api=MockAPI();result=m.drive_mock(api);terminal=result['terminal']
        self.assertEqual(terminal['outcome'],'FIXTURE_ASSERTIONS_PASS_ONLY');self.assertIsNone(terminal['reason'])
        self.assertEqual([r['id'] for r in terminal['cases']],list(m.CASE_IDS));self.assertEqual(api.calls,3)
        self.assertEqual(terminal['usage']['install_attempts'],3);self.assertEqual(terminal['actual_installer_imports'],0)
        self.assertFalse(terminal['installation_accepted']);self.assertFalse(terminal['runtime_or_P3_accepted'])
        self.assertEqual(terminal['original_guard_counter'],8)
        for row in terminal['cases']:
            raw=result['fs'].files[str(result['fs'].root/'controls'/row['ref']['path'])]
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row['ref']['sha256'])
        print(json.dumps({'kind':'MOCK_ONLY_EIGHT_CASE_HARNESS_RESULT','cases':len(terminal['cases']),
            'mock_install_calls':api.calls,'actual_installer_imports':0,'actual_installer_fixture_calls':0,
            'guard_refusals':terminal['original_guard_counter'],'terminal_bytes':result['terminal_ref']['bytes'],
            'usage':terminal['usage']},sort_keys=True))
    def test_spent_scope_refuses_without_more_mock_dispatch(self):
        api=MockAPI();fs=m.MemoryFS();m.drive_mock(api,fs);before=dict(fs.files)
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_SPENT_SCOPE'):m.drive_mock(api,fs)
        self.assertEqual(api.calls,3);self.assertEqual(fs.files,before)
    def test_wrong_script_or_extra_output_is_not_accepted(self):
        for corruption,code in (('SCRIPT','FIXTURE_OUTPUT_BYTES'),('EXTRA','FIXTURE_OUTPUT_MEMBERSHIP')):
            api=MockAPI(corruption);fs=m.MemoryFS()
            with self.assertRaisesRegex(m.HarnessRefused,code):m.drive_mock(api,fs)
            terminal=json.loads(fs.files[str(fs.root/'controls/TERMINAL.json')])
            self.assertEqual(terminal['outcome'],'FAILED_FIXTURE_HARNESS');self.assertEqual(api.calls,1)
            self.assertFalse(terminal['installation_accepted'])
    def test_corrupt_installed_RECORD_and_duplicates_refuse(self):
        for corruption,code in (('RECORD_HASH','FIXTURE_INSTALLED_RECORD_HASH'),('RECORD_DUPLICATE','FIXTURE_INSTALLED_RECORD_SCHEMA')):
            fs=m.MemoryFS()
            with self.assertRaisesRegex(m.HarnessRefused,code):m.drive_mock(MockAPI(corruption),fs)
            self.assertIn(str(fs.root/'controls/TERMINAL.json'),fs.files)
    def test_quota_failure_evidence_and_counter_not_reset(self):
        result=m.drive_mock(MockAPI());fs=result['fs']
        quota=json.loads(fs.files[str(fs.root/'controls/WRITE_QUOTA-RESULT.json')])
        later=json.loads(fs.files[str(fs.root/'controls/GUARD_EFFECT_SPIES-RESULT.json')])
        self.assertEqual(quota['verdict'],'EXPECTED_INSTALL_REFUSAL');self.assertEqual(quota['destination_bytes'],0)
        self.assertEqual(quota['guard_counter_after'],1);self.assertEqual(later['guard_counter_before'],1)
        self.assertTrue(quota['partial_manifest']);self.assertTrue(all(r['bytes']==0 for r in quota['partial_manifest'].values()))
    def test_interruption_retains_primary_identity_partial_files_and_receipt(self):
        result=m.drive_mock(MockAPI());fs=result['fs']
        item=json.loads(fs.files[str(fs.root/'controls/INTERRUPTED_WRITE-RESULT.json')])
        self.assertTrue(item['primary_identity_preserved']);self.assertEqual(item['error_code'],'INJECTED_WRITE_FAILURE')
        self.assertGreater(item['destination_bytes'],0);self.assertTrue(item['partial_manifest'])
    def test_unexpected_primary_not_replaced_by_terminal_write_failure(self):
        error=RuntimeError('MOCK_PRIMARY_NOT_FOR_OUTPUT')
        class FailAPI(MockAPI):
            def install(self,*args,**kwargs):raise error
        class BrokenFS(m.MemoryFS):
            def write_new(self,path,raw):
                if str(path).endswith('/TERMINAL.json'):raise OSError('MOCK_SECONDARY_NOT_FOR_OUTPUT')
                return super().write_new(path,raw)
        # Private core deliberately receives an authored FS double; public mock
        # entry only accepts exact MemoryFS, production entry only exact DiskFS.
        pure=m.own_module(m.PURE_REF,'primary_pure');base=m.own_module(m.POLICY_REF,'primary_base')
        fd=m.own_module(m.FD_REF,'primary_fd')
        with self.assertRaises(RuntimeError) as caught:m._drive(BrokenFS(),FailAPI(),pure,base,fd)
        self.assertIs(caught.exception,error)
    def test_api_must_be_explicit_mock_and_fs_must_be_memory(self):
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_MOCK_API_REQUIRED'):m.drive_mock(object())
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_MEMORY_FS_REQUIRED'):m.drive_mock(MockAPI(),object())


class FixtureOracleAndBudgetTests(unittest.TestCase):
    def controls(self):
        pure=m.own_module(m.PURE_REF,'budget_pure');base=m.own_module(m.POLICY_REF,'budget_base')
        return pure,base
    def test_fixed_normative_bytes_and_valid_fixture_hash(self):
        self.assertEqual((len(m.ENTRYPOINT),m.ENTRYPOINT.count(b'\n'),m.sha(m.ENTRYPOINT)),
            (57,2,'7c681c48ff47ebff69a7725580e9f612320498b6a27ecdcb7540237eed6978bb'))
        self.assertEqual((len(m.INSTALLER),m.INSTALLER.count(b'\n'),m.sha(m.INSTALLER)),
            (52,1,'a25d1b0c7e51bf5e0dd2aa45bf85e03faf1101a0bbd8a92347ce5dc3d913e2dd'))
        self.assertEqual(m.sha(m.make_fixture('VALID')),'cc20ab865ad6ed2549f97033486e59a4f37be462347f1cd34d38adec12e43c6f')
    def test_case_plan_deterministic_and_only_three_install_cases(self):
        self.assertEqual(m.case_plan(),m.case_plan());self.assertEqual(sum(r['install'] for r in m.case_plan()),3)
        self.assertEqual(len(m.output_oracle()),6);self.assertEqual(m.SCRIPT_BYTES.splitlines()[0],b'#!'+m.MARKER.encode())
    def test_headroom_is_bounded_with_reserved_failure_space(self):
        self.assertLessEqual(m.headroom(),28672);self.assertLessEqual(m.headroom()+4096,32768)
    def test_partitioned_reads_and_control_write_reserve(self):
        pure,base=self.controls();budget=m.SharedBudget(pure)
        budget.write(33554432-32768)
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_WRITE_CAP'):budget.write(1)
        budget.write(100,control=True);self.assertTrue(budget.failed)
        self.assertLessEqual(budget.summary()['write_bytes'],33554432)
        reader=m.SharedBudget(pure);reader.read(33554432-32768)
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_READ_CAP'):reader.read(1)
        reader.read(100,control=True);self.assertLessEqual(reader.summary()['combined_read_bytes'],67108864)
    def test_clock_regression_and_deadline_refuse(self):
        pure,base=self.controls();clock=[1.0];budget=m.SharedBudget(pure,lambda:clock[0]);clock[0]=0.0
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_CLOCK_REGRESSION'):budget.check()
        clock=[0.0];budget=m.SharedBudget(pure,lambda:clock[0]);clock[0]=120.0
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_WALL_CAP'):budget.check()
    def test_null_write_and_outside_write_remain_denied(self):
        pure,base=self.controls();policy=m.policy_class(base.GuestPolicy)(Path('/SSL_MOCK_GUARDS'),m.SharedBudget(pure))
        for path in ('/dev/null','/SSL_OUTSIDE'):
            with self.assertRaises(base.Refused):policy.path(path,os.O_WRONLY)
        self.assertEqual(policy.violations,2)
    def test_sealed_snapshot_compile_and_symlink_controls_refuse(self):
        pure,base=self.controls();policy=m.policy_class(base.GuestPolicy)(Path('/SSL_MOCK_GUARDS'),m.SharedBudget(pure))
        snapshot=policy.stage/'installer-1.1.0-py3-none-any.whl';policy.sealed.add(snapshot)
        with self.assertRaises(base.Refused):policy.path(snapshot,os.O_WRONLY)
        with self.assertRaises(base.Refused):policy.audit('compile',(b'MOCK',str(policy.target/'payload.py')))
        with self.assertRaises(base.Refused):policy.audit('os.symlink',('MOCK','MOCK',-1))
        self.assertEqual(policy.violations,3)
    def test_case_reentry_not_a_counter_or_budget_reset(self):
        pure,base=self.controls();policy=m.policy_class(base.GuestPolicy)(Path('/SSL_MOCK_GUARDS'),m.SharedBudget(pure))
        policy.begin('VALID')
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_SPENT_CASE'):policy.begin('VALID')


class ToolAndReleasePreparationTests(unittest.TestCase):
    def mock_tool(self):
        out=io.BytesIO();sources={'installer/__init__.py':b'NOT EXECUTABLE MOCK SOURCE\n'}
        with zipfile.ZipFile(out,'w') as archive:
            for name,raw in sources.items():archive.writestr(name,raw)
        raw=out.getvalue();return raw,{'bytes':len(raw),'sha256':m.sha(raw)},
    def test_tool_inspection_hashes_only_and_never_compiles(self):
        raw,ref=self.mock_tool();source=b'NOT EXECUTABLE MOCK SOURCE\n';refs={'installer/__init__.py':(len(source),m.sha(source))}
        original=builtins.compile;calls=[]
        def fail(*args,**kwargs):calls.append(True);raise AssertionError('MOCK_TOOL_WAS_COMPILED')
        try:
            builtins.compile=fail
            result=m.inspect_tool_bytes(raw,expected_archive=ref,expected_sources=refs)
            self.assertEqual(result,('installer/__init__.py',));self.assertEqual(calls,[])
        finally:builtins.compile=original
    def test_tool_archive_source_mismatch_refuses(self):
        raw,ref=self.mock_tool()
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_TOOL_ARCHIVE_HASH'):
            m.inspect_tool_bytes(raw,expected_archive={**ref,'sha256':'0'*64},expected_sources={})
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_TOOL_SOURCE_SET'):
            m.inspect_tool_bytes(raw,expected_archive=ref,expected_sources={})
        with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_TOOL_MEMBER_HASH'):
            m.inspect_tool_bytes(raw,expected_archive=ref,expected_sources={'installer/__init__.py':(len(b'NOT EXECUTABLE MOCK SOURCE\n'),'0'*64)})
    def test_tool_activation_refuses_before_standard_zip_loader(self):
        original=m.zipimport.zipimporter;calls=[]
        def fail(*args):calls.append(True);raise AssertionError('ACTUAL_TOOL_LOADER_CALLED')
        try:
            m.zipimport.zipimporter=fail
            with self.assertRaisesRegex(m.HarnessRefused,'FIXTURE_TOOL_RELEASE_REQUIRED'):
                m.activate_tool(None,None,b'',None,None)
            self.assertEqual(calls,[])
        finally:m.zipimport.zipimporter=original
    def packet(self):
        raw=b'MOCK_CANDIDATE_CODE_NOT_EXECUTED';root=Path('/SSL_MOCK_REVIEW_ROOT')
        packet={'kind':'E01_PYPA_FIXTURE_RELEASE_V1','execution_enabled':True,'root_sha256':m.sha(str(root).encode()),
            'runtime':'3.12.14','candidate_ref':{'path':m.CODE,'bytes':len(raw),'sha256':m.sha(raw)},
            'plan_sha256':m.sha(m.packed(m.case_plan())),'limits':m.LIMITS,
            'source_audit_ref':m.SOURCE_AUDIT,'pure_audit_ref':m.PURE_AUDIT,'bytes_audit_ref':m.BYTES_AUDIT,
            'review_ref':{'path':'reports/INDEPENDENT_AUDIT_MOCK_ONLY.json','bytes':0,'sha256':'0'*64},
            'temp_parent':'/SSL_MOCK_TEMP'}
        core={k:v for k,v in packet.items() if k!='review_ref'}
        review={'decision':'PASS_MOCK_REVIEW_DATA_ONLY_NOT_ACTUAL_AUTHORITY',
            'reviewed_release_core_sha256':m.sha(m.packed(core)),'evidence_refs':{m.CODE:packet['candidate_ref']}}
        return packet,root,raw,review
    def test_release_binding_is_exact_but_mock_data_grants_no_dispatch(self):
        packet,root,raw,review=self.packet();self.assertEqual(m.validate_release(packet,root,raw,review),packet)
        for field,value in (('execution_enabled',False),('plan_sha256','0'*64),('limits',{})):
            changed=copy.deepcopy(packet);changed[field]=value
            with self.assertRaises(m.HarnessRefused):m.validate_release(changed,root,raw,review)
    def test_release_review_code_root_and_runtime_cannot_drift(self):
        packet,root,raw,review=self.packet()
        for changed_raw,changed_root,changed_review in ((b'OTHER',root,review),(raw,Path('/OTHER'),review),
            (raw,root,{**review,'reviewed_release_core_sha256':'0'*64})):
            with self.assertRaises(m.HarnessRefused):m.validate_release(packet,changed_root,changed_raw,changed_review)
        packet['runtime']='3.10.0'
        with self.assertRaises(m.HarnessRefused):m.validate_release(packet,root,raw,review)


class CollectionAndSourceSafetyTests(unittest.TestCase):
    def test_ordinary_collection_installs_no_global_hooks_or_tool_loader(self):
        hooks=[];original=(sys.addaudithook,signal.signal,resource.setrlimit)
        try:
            sys.addaudithook=lambda *a:hooks.append('AUDIT');signal.signal=lambda *a:hooks.append('SIGNAL')
            resource.setrlimit=lambda *a:hooks.append('RESOURCE')
            raw=Path(__file__).read_bytes()
            load_own('ordinary_harness_test_collection',Path(__file__),hashlib.sha256(raw).hexdigest())
            self.assertEqual(hooks,[])
        finally:sys.addaudithook,signal.signal,resource.setrlimit=original
    def test_top_level_candidate_has_no_hooks_or_thirdparty_import(self):
        tree=ast.parse(CODE.read_bytes())
        for node in tree.body:
            if isinstance(node,ast.Import):self.assertFalse(any(a.name.split('.')[0] in {'installer','pip'} for a in node.names))
            elif isinstance(node,ast.ImportFrom):self.assertFalse((node.module or '').startswith(('installer','pip')))
            elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call):
                self.assertNotIn('addaudithook',ast.unparse(node));self.assertNotIn('activate_tool',ast.unparse(node))
    def test_no_fixture_function_calls_library_validation_or_executes_scripts(self):
        tree=ast.parse(CODE.read_bytes())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                self.assertNotEqual(node.func.attr,'validate_record')
                self.assertNotIn(node.func.attr,{'system','Popen','fork','execv','execve'})


def guarded_main():
    reads=[0];output=[0];stdlib=Path(sys.base_prefix)/'lib'
    allowed={Path(__file__).resolve(),CODE,ROOT/m.PURE_REF['path'],ROOT/m.POLICY_REF['path'],ROOT/m.FD_REF['path']}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=Path(os.path.realpath(args[0]));flags=args[2]
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise AssertionError('HARNESS_MOCK_NO_OS_WRITES')
            if not (path in allowed or (path.is_relative_to(stdlib) and 'site-packages' not in path.parts)):
                raise AssertionError('HARNESS_MOCK_UNAPPROVED_READ')
            try:size=path.stat().st_size
            except FileNotFoundError:size=0
            reads[0]+=size+1
            if reads[0]>67108864:raise AssertionError('HARNESS_MOCK_READ_CAP')
        if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.truncate','os.chmod'}:
            raise AssertionError('HARNESS_MOCK_NO_OS_MUTATION')
    sys.addaudithook(audit)
    class Output:
        def __init__(self,stream):self.stream=stream
        def __getattr__(self,name):return getattr(self.stream,name)
        def write(self,value):
            output[0]+=len(value.encode())
            if output[0]>262144:raise AssertionError('HARNESS_MOCK_OUTPUT_CAP')
            return self.stream.write(value)
    sys.stdout=Output(sys.stdout);sys.stderr=Output(sys.stderr)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    def timeout(*_):raise AssertionError('HARNESS_MOCK_WALL_CAP')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
    unittest.main(failfast=True,verbosity=2)


if __name__=='__main__':guarded_main()
