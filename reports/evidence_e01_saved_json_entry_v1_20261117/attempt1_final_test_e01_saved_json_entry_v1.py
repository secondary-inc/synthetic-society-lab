"""Ordinary CI wrapper for physical authored admission and inert children only."""
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time
import types
import unittest

ROOT=Path(__file__).absolute().parents[1]
ENTRY=ROOT/'src/civiclab/e01/saved_json_entry_v1.py'
CORE=ROOT/'src/civiclab/e01/saved_json_job_ledger_v1.py'
CORE_TEST=ROOT/'tests/test_e01_saved_json_job_ledger_v1.py'
LAUNCHER=ROOT/'scripts/run_e01_saved_json_entry_v1_20261117.py'


def _load(path,name):
    raw=path.read_bytes();module=types.ModuleType(name);module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__);return module


def _authored_cases(E,C,runtime,tmp,counters):
    # Borrow only frozen authored fixture/double closures; no old test runs.
    old=_load(CORE_TEST,'fixture_definitions_only');suite=old._authored_suite(C,runtime)
    first=next(iter(suite));second=list(suite)[1]
    def closure(fn):return dict(zip(fn.__code__.co_freevars,(c.cell_contents for c in fn.__closure__)))
    fixture=closure(second.test_02_tamper_and_missing_every_declared_byte)['fixture']
    Reader=closure(first.test_01_full_reader_api_projection_and_real_hash_meanings)['Reader']
    root_number=[0]
    def fresh():
        root_number[0]+=1;root=tmp/('ssl-saved-json-entry-fixture-'+str(root_number[0]));root.mkdir()
        m,files,value,prefix=fixture()
        files=files.copy()
        for path,source in ((E.CORE,CORE),(E.HELPER,ENTRY),(E.LAUNCHER,LAUNCHER)):files[path]=source.read_bytes()
        files['reports/AUTHORED_COMPONENT_REVIEW.json']=C.packed({'status':'AUTHORED_ONLY'})
        files['reports/AUTHORED_ENTRY_REVIEW.json']=C.packed({'status':'AUTHORED_ONLY'})
        def ref(path):return {'path':path,'bytes':len(files[path]),'sha256':C.digest(files[path])}
        p={'kind':'E01_SAVED_JSON_ROOT_ONE_CALL_V1','armed':True,'issued_by':'AUTHORED_TEST_ONLY','scope_id':'e01-saved-json-'+format(root_number[0],'032x'),
          'issued_at':100,'expires_at':1000,'limits':E.LIMITS.copy(),'manifest':m,
          'code_refs':{path:ref(path) for path in (E.CORE,E.HELPER,E.LAUNCHER)},
          'review_refs':{'component':ref('reports/AUTHORED_COMPONENT_REVIEW.json'),'entry':ref('reports/AUTHORED_ENTRY_REVIEW.json')},'runtime_sha256':runtime.sha256}
        for path,raw in files.items():
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
            counters['fixture_write_bytes']+=len(raw);assert counters['fixture_write_bytes']<=33554432;target.write_bytes(raw)
        return root,p,value,prefix
    def execute(parts,reader=None,**kwargs):
        root,p,*_=parts;raw=E.packed(p)
        return E.execute_authored(root,raw,E.sha(raw),C,runtime,reader or Reader(),now=lambda:101,**kwargs)
    def outcome(parts,name):return parts[0]/E.CONTROL/parts[1]['scope_id']/name

    class Cases(unittest.TestCase):
        def test_01_physical16_admission_one_reader_safe_ledger(self):
            parts=fresh();reader=Reader();ledger=execute(parts,reader);self.assertEqual(reader.calls,1)
            self.assertEqual(ledger['provenance'],C.AUTHORED);self.assertEqual(ledger['metrics']['document_state_coverage_count'],13)
            self.assertEqual(ledger['metrics']['remaining_document_acquisition_jobs'],20);self.assertEqual(ledger['final_ballots_accepted'],0)
            self.assertTrue(outcome(parts,'COMPLETE.json').is_file());self.assertIn('config_contract_sha256',ledger['bindings'])
            self.assertNotIn(b'AUTHORED_PRIVATE',E.packed(ledger));runtime.verify()

        def test_02_unarmed_window_limits_and_bad_metadata_no_control(self):
            for change in ({'armed':False},{'issued_by':'ROOT_REVIEWED_ONE_CALL'},{'expires_at':100},{'runtime_sha256':'0'*64}):
                parts=fresh();parts[1].update(change)
                with self.assertRaises(E.Refused):execute(parts)
                self.assertFalse(outcome(parts,'STARTED.json').exists())
            parts=fresh();parts[1]['limits']['reader_calls']=True
            with self.assertRaises(E.Refused):execute(parts)
            self.assertFalse(outcome(parts,'STARTED.json').exists())

        def test_03_tamper_or_missing_saved16_stops_before_reader(self):
            for i,(group,name) in enumerate([('saved_refs','typed_document_readiness.json'),('reference_refs','id_records')]):
                for missing in (False,True):
                    parts=fresh();path=parts[0]/parts[1]['manifest'][group][name]['path']
                    if missing:path.unlink()
                    else:
                        changed=path.read_bytes()+b' ';counters['fixture_write_bytes']+=len(changed);path.write_bytes(changed)
                    reader=Reader()
                    with self.assertRaises(E.Refused):execute(parts,reader)
                    self.assertEqual(reader.calls,0);self.assertTrue(outcome(parts,'FAILURE.json').exists());self.assertFalse(outcome(parts,'COMPLETE.json').exists())

        def test_04_exact_run_members_and_no_alias_or_parent_escape(self):
            for kind in ('extra_file','extra_directory','symlink'):
                parts=fresh();parent=parts[0]/parts[3]
                if kind=='extra_file':
                    counters['fixture_write_bytes']+=2;(parent/'extra.json').write_bytes(b'{}')
                elif kind=='extra_directory':(parent/'nested').mkdir()
                else:
                    path=parent/'typed_document_readiness.json';path.unlink();path.symlink_to(parts[0]/E.CORE)
                reader=Reader()
                with self.assertRaises(E.Refused):execute(parts,reader)
                self.assertEqual(reader.calls,0)
            parts=fresh();parts[1]['manifest']['reference_refs']['id_records']['path']='data/processed/../../escape'
            with self.assertRaises((E.Refused,C.Refused)):execute(parts)

        def test_05_create_once_replay_does_not_mutate_success(self):
            parts=fresh();reader=Reader();execute(parts,reader)
            folder=outcome(parts,'STARTED.json').parent;before={p.name:p.read_bytes() for p in folder.iterdir()}
            with self.assertRaises(FileExistsError):execute(parts,reader)
            self.assertEqual(reader.calls,1);self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})

        def test_06_sticky_denied_stream_failure_and_output_validation(self):
            parts=fresh()
            def after(path,root,contract,value):
                f=(path/'typed_document_readiness.json').open('rb');f.close()
                try:f.read1()
                except E.Refused:pass
            with self.assertRaisesRegex(E.Refused,'INPUT_IO'):execute(parts,Reader(after))
            self.assertFalse(outcome(parts,'COMPLETE.json').exists())
            parts=fresh();ledger=execute(parts)
            for key,value in [('source_adoption',0),('model_calls',1),('interpretation','AUTHORED_PRIVATE')]:
                bad=dict(ledger);bad[key]=value
                with self.assertRaises(E.Refused):E.validate_ledger(bad,parts[1],True)

        def test_07_physical_read_hash_io_budget_and_canonical(self):
            parts=fresh();p=parts[1]['manifest']['saved_refs']['typed_document_readiness.json'];b=E.Budget()
            self.assertEqual(E.sha(E.read_bound(parts[0],p,b)),p['sha256'])
            bad=dict(p);bad['path']='data/processed/../escape'
            with self.assertRaises(E.Refused):E.read_bound(parts[0],bad,E.Budget())
            b=E.Budget();b.saved=8388608
            with self.assertRaisesRegex(E.Refused,'SAVED_CAP'):E.read_bound(parts[0],p,b)
            self.assertIsNotNone(b.primary)
            self.assertEqual(E.packed({'café':'é'}),C.packed({'café':'é'}))

        def test_08_work_cleanup_finalization_and_primary_errors(self):
            b=E.Budget(start=0,clock=lambda:57)
            with self.assertRaisesRegex(E.Refused,'WORK_DEADLINE'):b.check()
            self.assertIsNotNone(b.primary)
            class Child:
                def __init__(self):self.done=False;self.events=[]
                def poll(self):return 0 if self.done else None
                def terminate(self):self.events.append('terminate')
                def kill(self):self.events.append('kill');self.done=True
                def wait(self,timeout):
                    self.events.append(('wait',timeout))
                    if not self.done:raise subprocess.TimeoutExpired('AUTHORED',timeout)
            c=Child();E.cleanup(c,E.Budget(start=0,clock=lambda:57.5));self.assertTrue(c.done);self.assertIn('kill',c.events)
            self.assertTrue(all(x[1]>=0 for x in c.events if isinstance(x,tuple)))
            with self.assertRaisesRegex(E.Refused,'CLEANUP_DEADLINE'):E.cleanup(c,E.Budget(start=0,clock=lambda:60))

        def test_09_inert_native_transport_success(self):
            child=subprocess.Popen([sys.executable,'-I','-B','-S','-c',"import sys;sys.stdout.write('{}');sys.stderr.write('AUTHORED_CONSOLE')"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
               stdin=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
            artifact,console=E.collect(child,E.Budget());self.assertEqual(artifact,b'{}');self.assertEqual(console,b'AUTHORED_CONSOLE');self.assertIsNotNone(child.poll())

        def test_10_inert_native_overflow_and_deadline_reaped(self):
            child=subprocess.Popen([sys.executable,'-I','-B','-S','-c',"import sys;sys.stdout.buffer.write(b'x'*131073)"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
               stdin=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
            with self.assertRaisesRegex(E.Refused,'ARTIFACT_CAP'):E.collect(child,E.Budget())
            self.assertIsNotNone(child.poll())
            child=subprocess.Popen([sys.executable,'-I','-B','-S','-c',"import time;time.sleep(2)"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
               stdin=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
            with self.assertRaisesRegex(E.Refused,'WORK_DEADLINE'):E.collect(child,E.Budget(start=time.monotonic()-57))
            self.assertIsNotNone(child.poll())

        def test_11_default_cli_unarmed_no_worker(self):
            result=subprocess.run([sys.executable,'-I','-B','-S',str(LAUNCHER)],capture_output=True,timeout=5,
              env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
            self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['status'],'UNARMED_NO_ROOT_PACKET');self.assertEqual(result.stderr,b'')

        def test_12_no_actual_reader_import_and_stream_family_supported(self):
            self.assertFalse(any(n=='civiclab' or n.startswith('civiclab.') for n in sys.modules))
            for name in ('read','read1','readline','readlines','readinto','readinto1'):
                s=C.ReadOnlyStream(b'abc',E.Budget());s.close()
                with self.assertRaisesRegex(E.Refused,'INPUT_IO'):
                    getattr(s,name)(bytearray(1)) if 'into' in name else getattr(s,name)()
            runtime.verify()


        def test_13_worker_claim_once_and_parent_usage_join(self):
            parts=fresh();root,p,*_=parts;budget=E.Budget();control=E.Control(root,p,budget)
            try:
                control.consume();raw=outcome(parts,'STARTED.json').read_bytes();record=E.strict(raw)
                initial={'saved_JSON_bytes':budget.saved,'project_source_bytes':budget.project,'write_bytes':budget.written}
                E.claim_worker(control.fd,record,p,budget.start,initial,len(raw),budget,E.sha(E.packed(p)))
                marker=outcome(parts,'WORKER_STARTED.json');before=marker.read_bytes()
                with self.assertRaises(FileExistsError):E.claim_worker(control.fd,record,p,budget.start,initial,len(raw),budget,E.sha(E.packed(p)))
                self.assertEqual(marker.read_bytes(),before)
                bad=dict(initial);bad['saved_JSON_bytes']+=1
                with self.assertRaisesRegex(E.Refused,'SHARED_USAGE_JOIN'):E.claim_worker(control.fd,record,p,budget.start,bad,len(raw),budget,E.sha(E.packed(p)))
            finally:control.close()


        def test_14_source_only_loader_authored_origins_no_reader_call(self):
            parts=fresh();raws={path:b'# AUTHORED STUB ONLY' for path in C.REAL_PROJECT_PINS}
            raws['src/civiclab/__init__.py']=b'from . import common\n'
            modules=[Path(path).stem for path in raws if path.startswith('src/civiclab/e01/') and not path.endswith('__init__.py')]
            raws['src/civiclab/e01/__init__.py']=('from . import '+','.join(modules)+'\n').encode()
            raws[C.READER]=b'def read_verified_public(path,*,root,contract):\n    raise RuntimeError("AUTHORED_STUB_MUST_NOT_BE_CALLED")\n'
            loader=E.SourceLoader(raws,parts[0])
            try:
                fn=loader.reader();self.assertEqual(fn.__module__,'civiclab.e01.ballots_v1_9_1')
                self.assertEqual(fn.__code__.co_filename,str(parts[0]/C.READER))
                self.assertEqual(len(loader.loaded),14)
                self.assertTrue(all(sys.modules[name].__loader__ is loader for name in loader.loaded))
            finally:
                for name in list(sys.modules):
                    if name=='civiclab' or name.startswith('civiclab.'):del sys.modules[name]
            self.assertFalse(any(name=='civiclab' or name.startswith('civiclab.') for name in sys.modules));runtime.verify()

    return unittest.defaultTestLoader.loadTestsFromTestCase(Cases)


def _child_main():
    import resource,signal,shutil
    resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));signal.alarm(120)
    tmp=Path(tempfile.mkdtemp(prefix='ssl-saved-json-entry-qualification-')).resolve()
    counters={'fixture_write_bytes':0,'observed_write_bytes':0,'observed_file_read_bytes':0,'denied':0,'native_children':0}
    real_open=os.open;real_close=os.close;real_write=os.write;fds={};opening=[None];stdlib=Path(os.__file__).resolve().parent
    exact={ENTRY,CORE,CORE_TEST,LAUNCHER,Path(__file__).absolute(),Path(sys.executable).absolute()}
    def own(path):return path.is_relative_to(tmp) and '..' not in path.parts
    def allowed_read(path):return own(path) or path in exact or path.is_relative_to(stdlib)
    def watched_open(path,flags,mode=0o777,*,dir_fd=None):
        p=Path(os.fsdecode(path))
        if not p.is_absolute():
            if dir_fd is None:base=Path.cwd()
            else:
                if dir_fd not in fds:raise PermissionError('UNTRACKED_DIR_FD')
                base=fds[dir_fd]
            p=base/p
        if '..' in p.parts:raise PermissionError('DIRFD_PARENT_ESCAPE')
        p=p.absolute()
        if flags & os.O_DIRECTORY:
            if not (own(p) or p in tmp.parents):raise PermissionError('DIRECTORY_SCOPE')
        elif flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            if not own(p):raise PermissionError('WRITE_SCOPE')
        elif not allowed_read(p):raise PermissionError('READ_SCOPE')
        opening[0]=p
        try:fd=real_open(path,flags,mode,dir_fd=dir_fd)
        finally:opening[0]=None
        fds[fd]=p
        if not flags & os.O_DIRECTORY and not flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            counters['observed_file_read_bytes']+=os.fstat(fd).st_size+1
            if counters['observed_file_read_bytes']>134217728:real_close(fd);raise RuntimeError('QUALIFICATION_READ_CAP')
        return fd
    def watched_close(fd):fds.pop(fd,None);return real_close(fd)
    def watched_write(fd,raw):
        if fd not in fds or not own(fds[fd]):raise PermissionError('UNTRACKED_WRITE_FD')
        counters['observed_write_bytes']+=len(raw)
        if counters['fixture_write_bytes']+counters['observed_write_bytes']>33554432:raise RuntimeError('QUALIFICATION_WRITE_CAP')
        return real_write(fd,raw)
    os.open=watched_open;os.close=watched_close;os.write=watched_write
    def audit(event,args):
        if event.startswith(('socket.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec'}:raise PermissionError('EXTERNAL_DENIED')
        if event=='subprocess.Popen':
            exe,argv,cwd,env=args
            if exe!=sys.executable or argv[:4]!=[sys.executable,'-I','-B','-S'] or env!={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}:raise PermissionError('CHILD_SCOPE')
            counters['native_children']+=1
            if counters['native_children']>4:raise PermissionError('CHILD_COUNT')
        if event=='open':
            name,mode,flags=args
            if type(name) is int:return
            if opening[0] is not None:return
            p=Path(os.fsdecode(name)).absolute()
            if p==Path('/dev/null'):return
            if '..' in p.parts:raise PermissionError('OPEN_PARENT_ESCAPE')
            writing=flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
            if writing:
                if not own(p):raise PermissionError('WRITE_SCOPE')
            else:
                if not allowed_read(p):counters['denied']+=1;raise PermissionError('READ_SCOPE')
                counters['observed_file_read_bytes']+=p.stat().st_size+1
                if counters['observed_file_read_bytes']>134217728:raise RuntimeError('QUALIFICATION_READ_CAP')
        if event in {'os.mkdir','os.remove','os.rmdir','os.chmod','os.utime'}:
            path=args[0];p=Path(os.fsdecode(path))
            if not p.is_absolute():
                parent=args[-1]
                if type(parent) is not int or parent not in fds:raise PermissionError('MUTATION_FD_SCOPE')
                p=fds[parent]/p
            if not own(p):raise PermissionError('MUTATION_SCOPE')
        if event=='os.symlink':
            p=Path(args[1]).absolute()
            if not own(p):raise PermissionError('SYMLINK_SCOPE')
    sys.addaudithook(audit)
    E=_load(ENTRY,'authored_entry');C=E.load_core(CORE.read_bytes(),CORE);runtime=C.RuntimePin()
    stream=io.StringIO();suite=_authored_cases(E,C,runtime,tmp,counters)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);runtime.verify()
    if result.wasSuccessful():print(stream.getvalue(),end='')
    else:
        first=(result.errors or result.failures)[0];print('FIRST_AUTHORED_FAILURE='+str(first[0]));print(first[1][:8192])
    print('SAVED_JSON_ENTRY_AUTHORED='+json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'counters':counters,
       'runtime_selected_origins_sha256':runtime.sha256,'startup_prewarm_complete':False,'actual_16_body_reads':0,'actual_reader_calls':0,'network_calls':0,'model_calls':0,'cost_usd':0},sort_keys=True))
    shutil.rmtree(tmp)
    return 0 if result.wasSuccessful() else 1


class SavedJSONEntryCI(unittest.TestCase):
    def test_authored_entry_and_inert_children(self):
        child=subprocess.Popen([sys.executable,'-I','-B','-S',str(Path(__file__).absolute()),'--authored-child'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
          stdin=subprocess.DEVNULL,cwd=ROOT,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
        data=bytearray();deadline=time.monotonic()+170
        try:
            with selectors.DefaultSelector() as s:
                s.register(child.stdout,selectors.EVENT_READ)
                while s.get_map():
                    self.assertLess(time.monotonic(),deadline)
                    for key,_ in s.select(0.1):
                        chunk=os.read(key.fd,min(4096,16385-len(data)))
                        if not chunk:s.unregister(key.fileobj);continue
                        data.extend(chunk);self.assertLessEqual(len(data),16384)
                child.wait(timeout=max(0.001,deadline-time.monotonic()))
            self.assertEqual(child.returncode,0,data.decode(errors='replace'))
            lines=data.decode().splitlines();record=json.loads(next(x.split('=',1)[1] for x in lines if x.startswith('SAVED_JSON_ENTRY_AUTHORED=')))
            self.assertEqual(record['tests'],14);self.assertEqual(record['failures'],0);self.assertEqual(record['errors'],0)
            self.assertEqual(sum(x.startswith('test_') and x.endswith(' ... ok') for x in lines),14)
            print('E01_ENTRY_CI_RECEIPT='+json.dumps(record,sort_keys=True))
        finally:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=1)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=1)
            child.stdout.close()


if __name__=='__main__':
    if sys.argv[1:]==['--authored-child']:raise SystemExit(_child_main())
    unittest.main(verbosity=2)
