"""One ordinary CI wrapper; authored adapter cases run only in a child."""
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import types
import unittest

ROOT=Path(__file__).absolute().parents[1]
MODULE=ROOT/'src/civiclab/e01/saved_json_job_ledger_v1.py'


def _authored_suite(M,runtime):
    def ref(path,raw):return {'path':path,'bytes':len(raw),'sha256':M.digest(raw)}
    def fixture(change=None):
        files={p:('# AUTHORED INERT '+p).encode() for p in M.REAL_PROJECT_PINS}
        diag={'AUTHORED_PRIVATE':'AUTHORED_PRIVATE_DIAGNOSTIC'}
        contexts=[{'contest_id':'AUTHORED_'+str(i),'content':'AUTHORED_PRIVATE_CONTEXT café'} for i in range(3)]
        references={}
        values={'id_diagnostics':diag,'id_records':[{'name':'AUTHORED_PRIVATE_NAME','status':'Approved' if i<4 else 'Withdrawn'} for i in range(5)],
                'legacy_public':{'AUTHORED':'READINESS_ONLY'},'legacy_rosters':{'person':'AUTHORED_PRIVATE_NAME'}}
        for role,value in values.items():
            path='data/processed/authored_reference/'+role+'.json';files[path]=M.packed(value);references[role]=ref(path,files[path])
        c={'base_config_path':'configs/AUTHORED_BASE.json','code_config_audit_pins':{},'context_contests_canonical_sha256':M.digest(M.packed(contexts)),
           'geometry_runtime':{'engine':'AUTHORED_NOT_INVOKED','version':'0'},'id_contract_path':'configs/AUTHORED_ID.json',
           'id_diagnostics_canonical_sha256':M.digest(M.packed(diag)),'pipeline_release':'AUTHORED café',
           'references':{k:{'path':v['path'],'sha256':v['sha256']} for k,v in references.items()},'schema_version':1,'scope':'TYPED_READINESS_V1_9_1_CANDIDATE_ONLY','source_adoption':False,
           'sources':[{'source_id':'AUTHORED_'+str(i),'path':'data/raw/NEVER_OPEN_'+str(i),'bytes':0,'sha256':'0'*64} for i in range(40)]}
        files[M.CONFIG]=(json.dumps(c,indent=2,sort_keys=True)+'\n').encode();contract=M.digest(M.packed(c))
        rows=[]
        for i,state in enumerate(M.STATES):
            kind=M.LEGACY if state in M.LEGACY_STATES else M.HISTORY if state=='ID' else M.MISSING;row={'state':state,'kind':kind}
            if kind==M.LEGACY:row['legacy_observation_index']=i
            elif kind==M.HISTORY:row.update(record_role='OBSERVED_GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY',local_record_artifact_ref=M.DATA[2],
                  source_status_record_count=5,Approved_status_record_count=4,Withdrawn_status_record_count=1,safe_diagnostics=diag)
            rows.append(row)
        value={'schema_version':2,'scope':M.SCOPE,'config_sha256':contract,'legacy_payload_ref':M.DATA[0],'document_observations':rows,
           'metrics':{'regular_frame_slots':33,'legacy_roster_state_count':12,'typed_status_history_state_count':1,'document_state_coverage_count':13,
                      'remaining_document_acquisition_jobs':20,'distinct_source_representation_count':40,'final_ballots_accepted':0},
           'context_contests':contexts,**{k:False for k in M.FLAGS},'cost_usd':0,'model_calls':0}
        if change:change(value)
        run='e01-'+'b'*32;prefix='data/processed/runs/'+run
        for name in M.LEDGER:files[prefix+'/'+name]=M.packed({'AUTHORED':'INERT_METADATA'})
        files[prefix+'/legacy_readiness_v1_7.json']=files[references['legacy_public']['path']]
        files[prefix+'/candidate_rosters.local.json']=files[references['legacy_rosters']['path']]
        files[prefix+'/id_status_records.local.json']=files[references['id_records']['path']]
        files[prefix+'/typed_document_readiness.json']=M.packed(value)
        files[prefix+'/typed_commit.json']=M.packed({'status':'PAYLOADS_WRITTEN_SOURCE_RECHECKED_AWAITING_FINAL_LEDGER','schema_version':2,'config_sha256':contract,'required_payloads':list(M.DATA)})
        files[prefix+'/typed_payload_hashes.json']=M.packed({n:M.digest(files[prefix+'/'+n]) for n in M.DATA})
        files[prefix+'/summary.json']=M.packed({'status':'SEALED_TYPED_OBSERVATIONS_PENDING_INDEPENDENT_POST_RUN_REVIEW','schema_version':2,'final_ballots_accepted':0,'source_adoption':False,'accepted_coverage_promoted':False,'cost_usd':0})
        files[prefix+'/manifest.json']=M.packed({'module':'E01','kind':'EXPLORATORY','run_id':run,'config':{'role':'TYPED_SOURCE_DOCUMENT_READINESS_V1_9_1','schema_version':2,'config_sha256':contract,'wrapper_sha256':M.digest(files[M.READER])}})
        files[prefix+'/checksums.json']=M.packed({n:M.digest(files[prefix+'/'+n]) for n in M.LEDGER})
        files[prefix+'/typed_release.json']=M.packed({'status':'LOCAL_TYPED_LEDGER_COMPLETE_PENDING_INDEPENDENT_REVIEW','config_sha256':contract,'checksums_sha256':M.digest(files[prefix+'/checksums.json']),'wrapper_sha256':M.digest(files[M.READER])})
        files[M.REVIEW]=M.packed({'status':'AUTHORED_ACCEPTANCE_ONLY'})
        manifest={'kind':'SAVED_JSON_ADAPTER_MANIFEST_V1','provenance':M.AUTHORED,'run_id':run,'config_ref':ref(M.CONFIG,files[M.CONFIG]),'contract_sha256':contract,
           'reader_ref':ref(M.READER,files[M.READER]),'acceptance_ref':ref(M.REVIEW,files[M.REVIEW]),'project_refs':{p:ref(p,files[p]) for p in M.REAL_PROJECT_PINS},
           'saved_refs':{n:ref(prefix+'/'+n,files[prefix+'/'+n]) for n in M.SAVED},'reference_refs':references,'runtime_sha256':runtime.sha256,'limits':M.LIMITS.copy()}
        return manifest,files,value,prefix

    class Reader:
        """Authoreddouble using acceptedreader Path/io open and stat surfaces."""
        mock_only=True
        def __init__(self,after=None):self.calls=0;self.after=after
        def __call__(self,path,*,root,contract):
            self.calls+=1;path=Path(path).absolute()
            assert path.parent==root/'data/processed/runs' and path.is_dir()
            assert not any(p.is_symlink() for p in (path,*path.parents))
            assert not any((path/n).exists() for n in ('failure.json','terminal_failure.local.json','failure_checksums.local.json'))
            def js(p):return M.strict_json(p.read_bytes())
            def sha(p):
                h=hashlib.sha256()
                with p.open('rb') as f:
                    for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
                return h.hexdigest()
            refs={k:js(root/v['path']) for k,v in contract['references'].items()}
            ledger=js(path/'checksums.json');names={p.name for p in path.iterdir() if p.is_file() and p.name!='.lock'}
            assert names==set(ledger)|{'checksums.json','typed_release.json'}
            seal=js(path/'typed_release.json')
            assert seal['config_sha256']==M.digest(M.packed(contract)) and seal['checksums_sha256']==sha(path/'checksums.json') and seal['wrapper_sha256']==sha(root/M.READER)
            for n,h in ledger.items():assert sha(path/n)==h
            run=js(path/'manifest.json');assert run['run_id']==path.name
            summary=js(path/'summary.json');assert summary['final_ballots_accepted']==0
            commit=js(path/'typed_commit.json');assert commit['config_sha256']==js(path/'typed_document_readiness.json')['config_sha256']
            payloads=js(path/'typed_payload_hashes.json')
            for n,h in payloads.items():assert sha(path/n)==h
            assert sha(path/M.DATA[0])==contract['references']['legacy_public']['sha256']
            assert sha(path/M.DATA[1])==contract['references']['legacy_rosters']['sha256']
            assert M.packed(js(path/M.DATA[2]))==M.packed(refs['id_records'])
            value=js(path/M.DATA[3])
            if self.after:self.after(path,root,contract,value)
            return value

    def run(parts=None,reader=None,scope=None,**kwargs):
        manifest,files,*_=parts or fixture()
        return M.compile_authored_once(M.packed(manifest),files,reader or Reader(),runtime,scope,**kwargs)

    class Cases(unittest.TestCase):
        def failed(self,parts=None,reader=None,code=None,**kwargs):
            scope=M.Scope()
            with self.assertRaises(M.Refused) as caught:run(parts,reader,scope,**kwargs)
            if code:self.assertEqual(caught.exception.code,code)
            self.assertNotIn('COMPLETE.json',scope.files)
            self.assertNotIn(b'AUTHORED_PRIVATE',b''.join(scope.files.values()))
            runtime.verify();return scope

        def test_01_full_reader_api_projection_and_real_hash_meanings(self):
            reader=Reader();result=run(reader=reader);ledger=result['ledger'];self.assertEqual(reader.calls,1)
            self.assertEqual(len(ledger['state_dispositions']),33);self.assertEqual(ledger['metrics']['document_state_coverage_count'],13)
            self.assertEqual(ledger['metrics']['remaining_document_acquisition_jobs'],20);self.assertEqual(ledger['final_ballots_accepted'],0)
            self.assertEqual(ledger['provenance'],M.AUTHORED);self.assertTrue(all(ledger[k] is False for k in M.FLAGS))
            self.assertNotEqual(ledger['bindings']['config_file_sha256'],ledger['bindings']['config_contract_sha256'])
            for raw in (b'AUTHORED_PRIVATE',b'.local.json',b'/Users/',b'data/processed/'):
                self.assertNotIn(raw,M.packed(ledger))
            self.assertFalse(result['budget']['failed']);runtime.verify()

        def test_02_tamper_and_missing_every_declared_byte(self):
            base=fixture()
            for path in base[1]:
                for missing in (False,True):
                    with self.subTest(path=path,missing=missing):
                        m,files,value,prefix=base;files=files.copy()
                        if missing:del files[path]
                        else:files[path]+=b' '
                        reader=Reader();self.failed((m,files,value,prefix),reader);self.assertEqual(reader.calls,0)

        def test_03_closed_membership_paths_and_descriptors(self):
            for extra in ('extra.json','nested/file','failure.json','.lock'):
                parts=fixture();parts[1][parts[3]+'/'+extra]=b'{}';self.failed(parts,code='CLOSED_MEMBERSHIP')
            for path in ('../escape','data/../escape','/tmp/escape','data/processed/a\x00b'):
                parts=fixture();parts[0]['reference_refs']['id_records']['path']=path;self.failed(parts)
            def attack(path,root,contract,value):
                for action in (lambda:os.open(str(path/'typed_document_readiness.json'),os.O_RDONLY),
                               lambda:os.unlink('../escape',dir_fd=1),lambda:os.rename(root/'x/../../escape',root/'x'),
                               lambda:io.open(root/'x/../typed_document_readiness.json','rb')):
                    try:action()
                    except M.Refused:pass
            self.failed(reader=Reader(attack),code='DESCRIPTOR_OR_MUTATION_DENIED')

        def test_04_caught_scope_mode_closed_stream_failures_sticky(self):
            actions=[lambda p,r:io.open('/etc/passwd','rb'),lambda p,r:builtins.open(p/'typed_document_readiness.json','w'),
                     lambda p,r:(p/'../escape').read_bytes(),lambda p,r:(r/'unknown').stat()]
            for action in actions:
                def attack(path,root,contract,value):
                    try:action(path,root)
                    except M.Refused:pass
                self.failed(reader=Reader(attack))
            def closed_stream(path,root,contract,value):
                f=(path/'typed_document_readiness.json').open('rb');f.close()
                try:f.read()
                except M.Refused:pass
            self.failed(reader=Reader(closed_stream),code='INPUT_IO')

        def test_05_budget_deadline_cancel_and_no_retry(self):
            scope=M.Scope();run(scope=scope)
            with self.assertRaisesRegex(M.Refused,'SPENT_SCOPE'):run(scope=scope)
            self.failed(clock=iter([0,60]).__next__,code='DEADLINE');self.failed(cancel=lambda:True,code='CANCELLED')
            def exhaust(path,root,contract,value):
                try:M._ACTIVE.budget.read(8388609)
                except M.Refused:pass
            self.failed(reader=Reader(exhaust),code='SAVED_CAP')

        def test_06_finite_unicode_and_duplicate_json(self):
            for raw in (b'1e999',b'-1e999',b'{"nested":[1e999]}',b'NaN',b'{"a":1,"a":2}'):
                with self.assertRaises(M.Refused):M.strict_json(raw)
            self.assertEqual(M.strict_json(b'{"word":"caf\\u00e9","x":1e-999}'),{'word':'café','x':0.0})
            self.assertIn(b'caf\\u00e9',M.packed({'word':'café'}));self.assertNotIn('café'.encode(),M.packed({'word':'café'}))

        def test_07_no_adoption_type_coercion_or_missing_candidate_claim(self):
            for key in M.FLAGS:
                self.failed(fixture(lambda value:value.__setitem__(key,True)))
                self.failed(fixture(lambda value:value.__setitem__(key,0)))
            self.failed(fixture(lambda value:value['metrics'].update(remaining_document_acquisition_jobs=19)))
            self.failed(fixture(lambda value:value['document_observations'][1].update(kind=M.LEGACY,legacy_observation_index=1)))
            self.assertIn('not evidence that candidates do not exist',run()['ledger']['interpretation'])

        def test_08_manifest_limits_contract_and_runtime_binding(self):
            for key,value in [('runtime_sha256','0'*64),('contract_sha256','0'*64)]:
                parts=fixture();parts[0][key]=value;self.failed(parts)
            parts=fixture();parts[0]['limits']['reader_calls']=True;self.failed(parts,code='LIMITS_OR_HASH')
            parts=fixture();parts[0]['provenance']=M.RECORDED;self.failed(parts,code='ACTUAL_ADMISSION_NOT_RELEASED')
            original=runtime.sha256
            try:
                runtime.sha256='0'*64
                with self.assertRaisesRegex(M.Refused,'RUNTIME_PIN_DRIFT'):runtime.verify()
            finally:runtime.sha256=original
            runtime.verify()

        def test_09_exact_actual_metadata_and_disabled_entry(self):
            actual={'kind':'SAVED_JSON_ADAPTER_MANIFEST_V1','provenance':M.RECORDED,'run_id':M.REAL_RUN,'config_ref':M.REAL_CONFIG_PIN,
                'contract_sha256':M.CONTRACT,'reader_ref':M.REAL_PROJECT_PINS[M.READER],'acceptance_ref':M.REAL_REVIEW_PIN,'project_refs':M.REAL_PROJECT_PINS,
                'saved_refs':M.REAL_SAVED_PINS,'reference_refs':M.REAL_REFERENCE_PINS,'runtime_sha256':runtime.sha256,'limits':M.LIMITS}
            self.assertEqual(M.validate_actual_metadata(M.packed(actual))['actual_reader_calls'],0)
            actual['contract_sha256']=M.REAL_CONFIG_PIN['sha256']
            with self.assertRaisesRegex(M.Refused,'ACTUAL_CONTRACT'):M.validate_actual_metadata(M.packed(actual))
            class Poison:
                def __getattribute__(self,_):raise AssertionError('ARGUMENT_TOUCHED')
            with self.assertRaisesRegex(M.Refused,'ACTUAL_DISABLED'):M.actual_entry(Poison())

        def test_10_guard_restore_primary_failure_and_output_bounds(self):
            class Exploding(Reader):
                def __call__(self,*a,**k):raise RuntimeError('AUTHORED_PRIVATE_ERROR')
            scope=M.Scope()
            with self.assertRaisesRegex(RuntimeError,'AUTHORED_PRIVATE'):run(reader=Exploding(),scope=scope)
            self.assertNotIn(b'AUTHORED_PRIVATE',b''.join(scope.files.values()));runtime.verify()
            self.assertIsNone(M._ACTIVE)
            budget=M.Budget();scope=M.Scope()
            with self.assertRaisesRegex(M.Refused,'PUBLIC_CAP'):scope.put('source_job_ledger.json',{'x':'x'*131073},budget)
            self.assertEqual(scope.files,{})

        def test_11_late_import_and_native_actions_denied(self):
            for event,args in [('socket.__new__',()),('subprocess.Popen',()),('compile',()),('sys.addaudithook',())]:
                def attack(path,root,contract,value):
                    try:sys.audit(event,*args)
                    except M.Refused:pass
                self.failed(reader=Reader(attack))

        def test_12_source_and_new_entry_have_no_actual_activation(self):
            tree=ast.parse(MODULE.read_bytes())
            for n in tree.body:
                if isinstance(n,(ast.Import,ast.ImportFrom)):
                    self.assertTrue(all(not a.name.startswith(('civiclab','pypdf','pdfplumber')) for a in n.names))
            entry=ast.parse((ROOT/'scripts/compile_e01_saved_json_job_ledger_v1_20261117.py').read_bytes())
            self.assertEqual([a.name for n in entry.body if isinstance(n,ast.Import) for a in n.names],['json'])


        def test_13_all_ordinary_read_family_sticky_and_positive_EOF(self):
            methods=('read','readline','readinto','read1','readlines','readinto1')
            for name in methods:
                with self.subTest(method=name,control='successful_content_and_EOF'):
                    budget=M.Budget();stream=M.ReadOnlyStream(b'abc\nxyz\n',budget)
                    method=getattr(stream,name)
                    if name in ('readinto','readinto1'):
                        buf=bytearray(4)
                        self.assertEqual(method(buf),4);self.assertEqual(bytes(buf),b'abc\n')
                        self.assertEqual(method(buf),4);self.assertEqual(bytes(buf),b'xyz\n')
                        self.assertEqual(method(buf),0)
                    elif name=='readlines':
                        self.assertEqual(method(),[b'abc\n',b'xyz\n']);self.assertEqual(method(),[])
                    elif name=='readline':
                        self.assertEqual(method(),b'abc\n');self.assertEqual(method(),b'xyz\n');self.assertEqual(method(),b'')
                    else:
                        self.assertEqual(method(4),b'abc\n');self.assertEqual(method(),b'xyz\n');self.assertEqual(method(),b'')
                    self.assertIsNone(budget.primary);stream.close()
                def closed(path,root,contract,value):
                    stream=(path/'typed_document_readiness.json').open('rb');stream.close()
                    try:
                        method=getattr(stream,name)
                        method(bytearray(4)) if name in ('readinto','readinto1') else method()
                    except M.Refused:pass
                with self.subTest(method=name,control='caught_closed_failure'):
                    scope=self.failed(reader=Reader(closed),code='INPUT_IO')
                    record=M.strict_json(scope.files['FAILURE.json'])
                    self.assertTrue(record['budget']['failed']);self.assertEqual(record['budget']['reader_calls'],1)
                    self.assertNotIn('source_job_ledger.json',scope.files)

    return unittest.defaultTestLoader.loadTestsFromTestCase(Cases)


def _child_main():
    import resource
    import signal
    import builtins
    globals()['builtins']=builtins
    resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(2097152,2097152));signal.alarm(60)
    # Audit only enumerated source/stdlib/runtime reads after prewarm. Virtual
    # reader operations are mediated by the adapter's own active guard.
    outer={'file_read_bytes':0,'logical_fixture_read_bytes':0,'logical_output_bytes':0,'denied':0}
    holder=[None];stdlib=Path(os.__file__).resolve().parent
    exact={MODULE,Path(__file__).absolute(),ROOT/'scripts/compile_e01_saved_json_job_ledger_v1_20261117.py',Path(sys.executable).absolute()}
    def audit(event,args):
        current=holder[0]
        if current is not None and current._ACTIVE is not None:return
        if event.startswith(('socket.','subprocess.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec','os.kill'}:
            outer['denied']+=1;raise PermissionError('CHILD_EXTERNAL_DENIED')
        if event=='open':
            name,mode,flags=args
            if type(name) is int:raise PermissionError('CHILD_UNDECLARED_FD')
            path=Path(os.fsdecode(name)).absolute()
            if '..' in path.parts or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('CHILD_WRITE_PATH_DENIED')
            if path not in exact and not path.is_relative_to(stdlib):
                outer['denied']+=1;raise PermissionError('CHILD_UNDECLARED_READ')
            outer['file_read_bytes']+=path.stat().st_size+1
            if outer['file_read_bytes']+outer['logical_fixture_read_bytes']>67108864:raise RuntimeError('CHILD_READ_CAP')
        if event in {'os.mkdir','os.remove','os.rmdir','os.rename','os.symlink','os.link','os.chmod','os.utime'}:raise PermissionError('CHILD_MUTATION_DENIED')
    sys.addaudithook(audit)
    # No production module imports; source load exact and no bytecode lookup.
    M=types.ModuleType('authored_saved_json_adapter');M.__file__=str(MODULE)
    exec(compile(MODULE.read_bytes(),str(MODULE),'exec'),M.__dict__)
    holder[0]=M
    original_read=M.Budget.read;original_write=M.Budget.write
    def charged_read(budget,n,project=False):
        before=budget.saved+budget.project
        try:return original_read(budget,n,project)
        finally:
            outer['logical_fixture_read_bytes']+=budget.saved+budget.project-before
            if outer['file_read_bytes']+outer['logical_fixture_read_bytes']>67108864:raise RuntimeError('CHILD_AGGREGATE_READ_CAP')
    def charged_write(budget,n,control=False):
        before=budget.written
        try:return original_write(budget,n,control)
        finally:
            outer['logical_output_bytes']+=budget.written-before
            if outer['logical_output_bytes']>33554432:raise RuntimeError('CHILD_AGGREGATE_WRITE_CAP')
    M.Budget.read=charged_read;M.Budget.write=charged_write
    runtime=M.RuntimePin();stream=io.StringIO();suite=_authored_suite(M,runtime)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);runtime.verify()
    if result.wasSuccessful():print(stream.getvalue(),end='')
    else:
        details=(result.errors or result.failures)[0]
        print('AUTHORED_FIRST_FAILURE='+str(details[0]))
        print(details[1][:8192])
        print('AUTHORED_FAILURE_TOTALS='+json.dumps({'errors':len(result.errors),'failures':len(result.failures),'full_diagnostic_sha256':hashlib.sha256(stream.getvalue().encode()).hexdigest()}))
    print('SAVED_JSON_AUTHORED_RECEIPT='+json.dumps({'kind':'AUTHORED_SAVED_JSON_ADAPTER','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'runtime_selected_origins_sha256':runtime.sha256,'runtime_pin_read_bytes':runtime.logical_read_bytes,'actual_reader_calls':0,'network_calls':0,'model_calls':0,'cost_usd':0,
        'startup_prewarm_complete':False,'outer_guard':outer},sort_keys=True))
    return 0 if result.wasSuccessful() else 1


class SavedJSONAdapterCI(unittest.TestCase):
    def test_authored_adapter_cases_in_child(self):
        cap=16384;deadline=time.monotonic()+60;chunks=[];count=0
        child=subprocess.Popen([sys.executable,'-I','-B','-S',str(Path(__file__).absolute()),'--authored-child'],cwd=ROOT,
              stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout,selectors.EVENT_READ)
                while selector.get_map():
                    left=deadline-time.monotonic();self.assertGreater(left,0,'CHILD_DEADLINE')
                    for key,_ in selector.select(min(left,0.1)):
                        raw=os.read(key.fd,min(4096,cap-count+1))
                        if not raw:selector.unregister(key.fileobj);continue
                        count+=len(raw);self.assertLessEqual(count,cap,'CHILD_CONSOLE_CAP');chunks.append(raw)
                child.wait(timeout=max(0.001,deadline-time.monotonic()))
            raw=b''.join(chunks);self.assertEqual(child.returncode,0,raw.decode(errors='replace'))
            lines=raw.decode().splitlines();receipts=[json.loads(x.split('=',1)[1]) for x in lines if x.startswith('SAVED_JSON_AUTHORED_RECEIPT=')]
            self.assertEqual(len(receipts),1);receipt=receipts[0]
            self.assertEqual(receipt['tests'],13);self.assertEqual(receipt['failures'],0);self.assertEqual(receipt['errors'],0)
            self.assertEqual(sum(x.startswith('test_') and x.endswith(' ... ok') for x in lines),13)
            for key in ('actual_reader_calls','network_calls','model_calls','cost_usd'):self.assertEqual(receipt[key],0)
            print('E01_SAVED_JSON_CI_RECEIPT='+json.dumps(receipt,sort_keys=True))
        finally:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=1)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=1)
            child.stdout.close()


if __name__=='__main__':
    if sys.argv[1:]==['--authored-child']:raise SystemExit(_child_main())
    unittest.main(verbosity=2)
