"""Authored-fixture tests only. Run directly with -I -B -S; no civiclab import.

The standalone guard denies network/process/native launches, actual repo data,
PDF packages and writes outside its own temporary tree. Its read-byte counter
covers audited file opens after guard installation, not interpreter startup.
"""
import sys
import os
import time
import resource
import signal
START=None
import ast
import copy
import hashlib
import types
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).absolute().parents[1]
SOURCE=ROOT/'src/civiclab/e01/source_job_ledger_v1.py'
ENTRY=ROOT/'scripts/compile_e01_saved_job_ledger_v1_20261117.py'
AUTHOR_TMP=None
GUARD={'logical_open_read_bytes':0,'fixture_write_bytes':0,'denied':0}

def setup_direct_runtime():
    """Process controls apply only to the explicit standalone suite entry."""
    global START
    START=time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
    signal.alarm(120)


def standalone_guard():
    global AUTHOR_TMP
    AUTHOR_TMP=Path(tempfile.mkdtemp(prefix='ssl-job-ledger-fixture-suite-')).resolve()
    stdlib=Path(os.__file__).resolve().parent
    exact={SOURCE,ENTRY,Path(__file__).absolute()}
    def deny():
        GUARD['denied']+=1
        raise PermissionError('AUTHORED_TEST_GUARD')
    def own(path):
        return type(path) in {str,bytes} and Path(os.fsdecode(path)).absolute().is_relative_to(AUTHOR_TMP)
    def audit(event,args):
        if time.monotonic()-START>=120:deny()
        if event.startswith(('socket.','subprocess.','ctypes.')) or event in {'os.system','os.fork','os.posix_spawn','os.exec','os.kill'}:deny()
        if event=='import' and (args[0].startswith(('civiclab','pypdf','pdfplumber'))):deny()
        if event=='open':
            name,mode,flags=args
            if type(name) is int: return # only already-admitted fixture descriptors
            p=Path(os.fsdecode(name)).absolute()
            write=bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if write:
                if not own(name):deny()
            else:
                if not (p in exact or p.is_relative_to(stdlib) or own(name)):deny()
                try:size=p.stat().st_size
                except FileNotFoundError:size=0
                GUARD['logical_open_read_bytes']+=size+1
                if GUARD['logical_open_read_bytes']>67108864:deny()
        if event in {'os.mkdir','os.remove','os.rmdir','os.chmod','os.utime','os.truncate'} and not own(args[0]):deny()
        if event in {'os.rename','os.link','os.symlink'} and not own(args[1]):deny()
    sys.addaudithook(audit)


def load_module():
    module=types.ModuleType('authored_source_job_ledger_v1');module.__file__=str(SOURCE)
    exec(compile(SOURCE.read_bytes(),str(SOURCE),'exec'),module.__dict__);return module

M=None
PUBLIC_SAMPLE=None

def ref(path,raw):return {'path':path,'bytes':len(raw),'sha256':M.sha(raw)}

def authored(change=None):
    """All files are invented, including shadow code/review files; none executed."""
    files={path:('# MOCK INERT '+path).encode() for path in M.ACCEPTED_CODE_PINS}
    diag={'MOCK_PRIVATE_DIAGNOSTIC':'AUTHORED_PRIVATE_NAME_DO_NOT_EXPORT'}
    contexts=[{'contest_id':'MOCK_CONTEXT_'+str(i),'name':'AUTHORED_PRIVATE_CONTEXT'} for i in range(3)]
    config={'kind':'MOCK_TYPED_READER_CONFIG_V1','source_ids':list(M.SOURCE_IDS),'id_diagnostics_sha256':M.sha(M.packed(diag)),
            'context_contests_sha256':M.sha(M.packed(contexts))}
    files[M.CONFIG_PATH]=M.packed(config)
    rows=[]
    for index,state in enumerate(M.REGULAR_STATES):
        row={'state':state,'kind':M.expected_kind(state)}
        if row['kind']==M.LEGACY:row['legacy_observation_index']=index
        elif state=='ID':row.update(record_role='OBSERVED_GENERAL_CONTEXT_CANDIDACY_STATUS_HISTORY',
            local_record_artifact_ref='id_status_records.local.json',source_status_record_count=5,
            Approved_status_record_count=4,Withdrawn_status_record_count=1,safe_diagnostics=diag)
        rows.append(row)
    metrics={'regular_frame_slots':33,'legacy_roster_state_count':12,'typed_status_history_state_count':1,
             'document_state_coverage_count':13,'remaining_document_acquisition_jobs':20,'distinct_source_representation_count':40,'final_ballots_accepted':0}
    value={'schema_version':2,'scope':M.TYPED_SCOPE,'config_sha256':M.sha(files[M.CONFIG_PATH]),'legacy_payload_ref':'legacy_readiness_v1_7.json',
           'document_observations':rows,'metrics':metrics,'context_contests':contexts,**{k:False for k in M.FLAGS},'cost_usd':0,'model_calls':0}
    if change:change(value)
    prefix='data/processed/runs/e01-'+'a'*32
    for name in M.LEDGER_FILES:files[prefix+'/'+name]=M.packed({'mock_private':'AUTHORED_PRIVATE_NAME_DO_NOT_EXPORT'})
    files[prefix+'/typed_document_readiness.json']=M.packed(value)
    files[prefix+'/summary.json']=M.packed({'status':'SEALED_AUTHORED_TYPED_OBSERVATIONS','final_ballots_accepted':0,**{k:False for k in M.FLAGS}})
    files[prefix+'/checksums.json']=M.packed({name:M.sha(files[prefix+'/'+name]) for name in M.LEDGER_FILES})
    files[prefix+'/typed_release.json']=M.packed({'kind':'MOCK_TYPED_RELEASE_V1','status':'SEALED_AUTHORED_ONLY',
        'checksums_sha256':M.sha(files[prefix+'/checksums.json']),'reader_sha256':M.sha(files[M.READER_PATH])})
    files[M.REVIEW_PATH]=M.packed({'kind':'MOCK_READER_ACCEPTANCE_V1','status':'PASS_AUTHORED_BINDINGS_ONLY',
        'reader_sha256':M.sha(files[M.READER_PATH]),'config_sha256':M.sha(files[M.CONFIG_PATH])})
    for role in M.REFERENCE_ROLES:files['authored_references/'+role+'.json']=M.packed({'MOCK_PRIVATE':'AUTHORED_PRIVATE_NAME_DO_NOT_EXPORT'})
    manifest={'kind':'SAVED_TYPED_INPUT_MANIFEST_V1','provenance':'MOCK_AUTHORED','run_id':'e01-'+'a'*32,
       'code_refs':{p:ref(p,files[p]) for p in M.ACCEPTED_CODE_PINS},'config_ref':ref(M.CONFIG_PATH,files[M.CONFIG_PATH]),
       'review_ref':ref(M.REVIEW_PATH,files[M.REVIEW_PATH]),'saved_refs':{n:ref(prefix+'/'+n,files[prefix+'/'+n]) for n in M.SAVED_FILES},
       'reference_refs':{r:ref('authored_references/'+r+'.json',files['authored_references/'+r+'.json']) for r in M.REFERENCE_ROLES}}
    files['metadata/input_manifest.json']=M.packed(manifest)
    plan={'kind':'SAVED_JOB_LEDGER_MOCK_PLAN_V1','provenance':'MOCK_AUTHORED','limits':copy.deepcopy(M.LIMITS),
          'input_manifest_ref':ref('metadata/input_manifest.json',files['metadata/input_manifest.json'])}
    return files,plan,prefix,value,config

class Reader:
    mock_only=True
    def __init__(self):self.calls=0
    def read_verified_public(self,view,prefix,config):
        self.calls+=1;return view.json(prefix+'/typed_document_readiness.json')

def run_fixture(parts=None,reader=None,output=None,**kwargs):
    files,plan,*_=parts or authored()
    return M.compile_mock_once(plan,M.MemoryFixture(files),reader or Reader(),output,
        expected_plan_sha256=M.sha(M.packed(plan)),**kwargs)

def repin_manifest(parts,mutate):
    files,plan,*_=parts;manifest=M.exact_json(files['metadata/input_manifest.json']);mutate(manifest)
    files['metadata/input_manifest.json']=M.packed(manifest);plan['input_manifest_ref']=ref('metadata/input_manifest.json',files['metadata/input_manifest.json'])

class LedgerTests(unittest.TestCase):
    def refuses(self,parts,reader=None,code=None,**kwargs):
        output=M.MemoryOutput()
        with self.assertRaises(M.LedgerRefused) as caught:run_fixture(parts,reader,output,**kwargs)
        if code:self.assertEqual(caught.exception.code,code)
        self.assertNotIn('COMPLETE.json',output.files)
        self.assertNotIn(b'AUTHORED_PRIVATE',b''.join(output.files.values()))
        return output

    def test_01_derives_dispositions_and_zero_acceptance(self):
        global PUBLIC_SAMPLE
        reader=Reader();result=run_fixture(reader=reader);ledger=result['ledger'];PUBLIC_SAMPLE=ledger
        self.assertEqual(reader.calls,1);self.assertEqual(len(ledger['state_dispositions']),33)
        self.assertEqual([r['state'] for r in ledger['state_dispositions']],list(M.REGULAR_STATES))
        counts={kind:sum(r['document_kind']==kind for r in ledger['state_dispositions']) for kind in (M.LEGACY,M.HISTORY,M.MISSING)}
        self.assertEqual(list(counts.values()),[12,1,20]);self.assertEqual(ledger['metrics']['document_state_coverage_count'],13)
        self.assertEqual(ledger['context_contests_count'],3);self.assertEqual(ledger['final_ballots_accepted'],0)
        self.assertTrue(all(ledger[k] is False for k in M.FLAGS));self.assertTrue(result['budget']['closing'])
        self.assertEqual(result['budget']['reader_calls'],1);self.assertFalse(result['budget']['failed'])
        self.assertEqual(M.exact_json(result['output'].files['COMPLETE.json'])['status'],'MOCK_LEDGER_COMPILED_ONLY')

    def test_02_privacy_and_missing_semantics(self):
        ledger=run_fixture()['ledger'];raw=M.packed(ledger)
        for forbidden in (b'AUTHORED_PRIVATE',b'.local.json',b'/Users/',b'candidate_name',b'safe_diagnostics'):self.assertNotIn(forbidden,raw)
        al=next(r for r in ledger['state_dispositions'] if r['state']=='AL')
        self.assertEqual(al['disposition'],'NO_DOCUMENT_ADMITTED')
        self.assertEqual(al['unresolved_conditions'][0]['status'],'NO_ADMITTED_DOCUMENT')
        self.assertTrue(all(c['status']=='NOT_ASSESSED_BY_THIS_LEDGER' for c in al['unresolved_conditions'][1:]))
        self.assertIn('not evidence that real candidates do not exist',ledger['interpretation'])
        self.assertEqual(ledger['metrics']['remaining_document_acquisition_jobs'],20)

    def test_03_reproducible(self):self.assertEqual(run_fixture()['output'].files,run_fixture()['output'].files)

    def test_04_no_adoption_or_inference(self):
        for key in (*M.FLAGS,'cost_usd','model_calls'):
            with self.subTest(key=key):self.refuses(authored(lambda v:v.__setitem__(key,True)),code='ADOPTION_OR_COST')

    def test_05_reject_numeric_false_flags(self):
        for key in M.FLAGS:
            with self.subTest(key=key):self.refuses(authored(lambda v:v.__setitem__(key,0)),code='ADOPTION_OR_COST')

    def test_06_state_shape_order_duplicate_missing(self):
        changes=[lambda v:v['document_observations'].pop(),lambda v:v['document_observations'].reverse(),
                 lambda v:v['document_observations'].__setitem__(1,copy.deepcopy(v['document_observations'][0]))]
        for change in changes:
            with self.subTest(change=changes.index(change)):self.refuses(authored(change))

    def test_07_no_alabama_or_kind_promotion(self):
        self.refuses(authored(lambda v:v['document_observations'][1].update(kind=M.LEGACY,legacy_observation_index=1)),code='STATE_OR_KIND')

    def test_08_legacy_index_strict(self):
        for index in (True,999):
            with self.subTest(index=index):self.refuses(authored(lambda v:v['document_observations'][0].update(legacy_observation_index=index)),code='LEGACY_ROW')

    def test_09_history_role_counts_and_extra(self):
        mutations=[{'record_role':'FINAL_BALLOT'},{'source_status_record_count':6},{'Approved_status_record_count':True},
                   {'local_record_artifact_ref':'/private/person.json'},{'person':'AUTHORED_PRIVATE_NAME'}]
        for mutation in mutations:
            with self.subTest(mutation=list(mutation)):self.refuses(authored(lambda v:next(r for r in v['document_observations'] if r['state']=='ID').update(mutation)))

    def test_10_diagnostics_context_and_metrics_binding(self):
        changes=[lambda v:next(r for r in v['document_observations'] if r['state']=='ID')['safe_diagnostics'].update(drift=True),
                 lambda v:v['context_contests'].pop(),lambda v:v['metrics'].update(remaining_document_acquisition_jobs=19),
                 lambda v:v['metrics'].update(final_ballots_accepted=False)]
        for i,change in enumerate(changes):
            with self.subTest(i=i):self.refuses(authored(change))

    def test_11_tamper_every_admitted_file_before_reader(self):
        base=authored()
        for path in list(base[0]):
            with self.subTest(path=path):
                parts=copy.deepcopy(base);parts[0][path]+=b' ';reader=Reader();self.refuses(parts,reader)
                self.assertEqual(reader.calls,0)

    def test_12_missing_every_admitted_file_before_reader(self):
        base=authored()
        for path in list(base[0]):
            with self.subTest(path=path):
                parts=copy.deepcopy(base);del parts[0][path];reader=Reader();self.refuses(parts,reader)
                self.assertEqual(reader.calls,0)

    def test_13_extra_failed_or_directory_members(self):
        for extra in ('FAILED.json','FAILURE.json','nested/file','extra.json'):
            with self.subTest(extra=extra):
                parts=authored();parts[0][parts[2]+'/'+extra]=b'{}';self.refuses(parts,code='SAVED_MEMBERSHIP')

    def test_14_lock_optional_never_read(self):
        parts=authored();parts[0][parts[2]+'/.lock']=b'UNBOUND_AUTHORED_LOCK'
        self.assertEqual(run_fixture(parts)['ledger']['metrics']['final_ballots_accepted'],0)

    def test_15_manifest_closed_bindings_paths(self):
        changes=[lambda m:m.update(extra=True),lambda m:m['code_refs'].pop(next(iter(m['code_refs']))),
                 lambda m:m['config_ref'].update(path='/private/config.json'),
                 lambda m:m['review_ref'].update(path='../review.json'),
                 lambda m:m['reference_refs']['legacy_public'].update(path=m['config_ref']['path']),
                 lambda m:m['saved_refs']['summary.json'].update(path='data/raw/source.pdf')]
        for i,change in enumerate(changes):
            with self.subTest(i=i):
                parts=authored();repin_manifest(parts,change);reader=Reader();self.refuses(parts,reader);self.assertEqual(reader.calls,0)

    def test_16_plan_hash_pre_effect(self):
        files,plan,*_=authored();output=M.MemoryOutput();reader=Reader()
        with self.assertRaisesRegex(M.LedgerRefused,'PLAN_HASH'):
            M.compile_mock_once(plan,M.MemoryFixture(files),reader,output,expected_plan_sha256='0'*64)
        self.assertEqual(output.files,{});self.assertFalse(output.claimed);self.assertEqual(reader.calls,0)

    def test_17_no_limit_increase_or_type_coercion(self):
        for key,value in [('reader_calls',True),('retries',1),('logical_read_bytes',67108865)]:
            with self.subTest(key=key):
                parts=authored();parts[1]['limits'][key]=value;self.refuses(parts,code='PLAN_SCHEMA')

    def test_18_duplicate_invalid_nonfinite_json(self):
        for raw in (b'{"x":1,"x":2}',b'{',b'"\xff"',b'NaN',b'Infinity'):
            with self.subTest(raw=repr(raw)):
                with self.assertRaises(M.LedgerRefused):M.exact_json(raw)

    def test_19_caught_outside_or_invalid_path_still_fails(self):
        for path in ('data/raw/forbidden.pdf','../escape','/private/name'):
            class CatchingReader(Reader):
                def read_verified_public(self,view,prefix,config):
                    try:view.read(path)
                    except M.LedgerRefused:pass
                    return super().read_verified_public(view,prefix,config)
            with self.subTest(path=path):self.refuses(authored(),CatchingReader())

    def test_20_caught_bad_json_still_fails(self):
        class CatchingReader(Reader):
            def read_verified_public(self,view,prefix,config):
                try:view.json(M.READER_PATH) # inert mock code is deliberately non-JSON
                except M.LedgerRefused:pass
                return super().read_verified_public(view,prefix,config)
        self.refuses(authored(),CatchingReader(),code='JSON_INVALID')

    def test_21_caught_budget_exhaustion_still_fails(self):
        for direction in ('read','write'):
            class CatchingReader(Reader):
                def read_verified_public(self,view,prefix,config):
                    try:getattr(view.budget,direction)(67108865)
                    except M.LedgerRefused:pass
                    return super().read_verified_public(view,prefix,config)
            with self.subTest(direction=direction):
                out=self.refuses(authored(),CatchingReader());record=M.exact_json(out.files['FAILURE.json'])
                self.assertTrue(record['budget']['failed']);self.assertLessEqual(record['budget']['logical_read_bytes'],67108864)

    def test_22_reader_result_substitution_refused(self):
        class Substitution(Reader):
            def read_verified_public(self,view,prefix,config):
                value=super().read_verified_public(view,prefix,config);value['scope']='OTHER';return value
        self.refuses(authored(),Substitution(),code='READER_RESULT_DRIFT')

    def test_23_no_retry_after_success_or_failure(self):
        for failing in (False,True):
            parts=authored();output=M.MemoryOutput();reader=Reader()
            if failing:parts[0][M.CONFIG_PATH]+=b' '
            try:run_fixture(parts,reader,output)
            except M.LedgerRefused:pass
            calls=reader.calls
            with self.assertRaisesRegex(M.LedgerRefused,'SPENT_OUTPUT'):run_fixture(parts,reader,output)
            self.assertEqual(reader.calls,calls)

    def test_24_cancel_deadline_clock_invalid(self):
        for clock,cancel in [(lambda:0,lambda:True),(iter([0,120]).__next__,lambda:False),(iter([1,0]).__next__,lambda:False)]:
            with self.subTest(i=repr(clock)):self.refuses(authored(),clock=clock,cancel=cancel)
        for value in (float('nan'),float('inf'),True):
            output=M.MemoryOutput()
            with self.assertRaisesRegex(M.LedgerRefused,'CLOCK'):run_fixture(output=output,clock=lambda:value)
            self.assertTrue(output.claimed);self.assertEqual(output.files,{})

    def test_25_failure_marker_redacts_and_primary_survives(self):
        class Exploding(Reader):
            def read_verified_public(self,*_):raise RuntimeError('/private/AUTHORED_PRIVATE_NAME')
        output=M.MemoryOutput()
        with self.assertRaisesRegex(RuntimeError,'AUTHORED_PRIVATE'):run_fixture(reader=Exploding(),output=output)
        record=M.exact_json(output.files['FAILURE.json']);self.assertEqual(record['error_type'],'RuntimeError')
        self.assertNotIn(b'AUTHORED_PRIVATE',M.packed(record));self.assertNotIn('COMPLETE.json',output.files)
        output=M.MemoryOutput();original=output.new
        def broken(name,*args,**kwargs):
            if name=='FAILURE.json':raise OSError('SECONDARY')
            return original(name,*args,**kwargs)
        output.new=broken
        with self.assertRaisesRegex(RuntimeError,'AUTHORED_PRIVATE'):run_fixture(reader=Exploding(),output=output)
        self.assertNotIn('COMPLETE.json',output.files)

    def test_26_direct_projection_binding_privacy(self):
        _,_,_,value,config=authored();binding={k:'0'*64 for k in ('reader_sha256','config_sha256','reader_acceptance_sha256','manifest_sha256','typed_public_sha256')}
        binding['config_sha256']=value['config_sha256']
        self.assertEqual(M.project_public(value,config,binding)['metrics']['document_state_coverage_count'],13)
        for change in ({'private':'/private/person'}, {'reader_sha256':'/private/person'}):
            with self.subTest(change=list(change)):
                bad={**binding,**change}
                with self.assertRaisesRegex(M.LedgerRefused,'BINDING_HASH'):M.project_public(value,config,bad)

    def test_27_eventual_packet_pins_and_actual_disabled(self):
        packet={'kind':'E01_SAVED_JOB_LEDGER_PREPARATION_ONLY_V1','execution_enabled':False,'reader_ref':M.ACCEPTED_CODE_PINS[M.READER_PATH],
                'config_ref':M.ACCEPTED_CONFIG_PIN,'review_ref':M.ACCEPTED_REVIEW_PIN,'code_refs':M.ACCEPTED_CODE_PINS,'input_manifest_ref':None,'limits':M.LIMITS}
        self.assertEqual(M.validate_eventual_binding(packet)['real_reader_calls'],0)
        for key,value in [('execution_enabled',True),('input_manifest_ref',{'path':'/private/manifest'}),('review_ref',{}),('code_refs',{})]:
            with self.subTest(key=key):
                bad=copy.deepcopy(packet);bad[key]=value
                with self.assertRaises(M.LedgerRefused):M.validate_eventual_binding(bad)
        class Poison:
            def __getattribute__(self,_):raise AssertionError('ARGUMENT_ACCESSED')
        with self.assertRaisesRegex(M.LedgerRefused,'ACTUAL_DISABLED'):M.actual_entry(Poison(),packet=Poison())

    def test_28_entry_and_source_do_not_import_actual_reader(self):
        tree=ast.parse(SOURCE.read_bytes())
        imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
        names=[a.name for n in imports for a in n.names]
        self.assertTrue(all(not name.startswith(('civiclab','pypdf','pdfplumber','subprocess')) for name in names))
        entry=ast.parse(ENTRY.read_bytes());self.assertEqual([a.name for n in entry.body if isinstance(n,ast.Import) for a in n.names],['json'])
        self.assertNotIn('civiclab',sys.modules);self.assertNotIn('pypdf',sys.modules)

    def test_29_disk_authored_fixture_and_symlink_refusal(self):
        self.assertIsNotNone(AUTHOR_TMP)
        root=AUTHOR_TMP/'ssl-job-ledger-fixture-case29';root.mkdir();parts=authored()
        for name,raw in parts[0].items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
            GUARD['fixture_write_bytes']+=len(raw)
            self.assertLessEqual(GUARD['fixture_write_bytes'],33554432);p.write_bytes(raw)
        result=M.compile_mock_once(parts[1],M.DiskFixture(root),Reader(),expected_plan_sha256=M.sha(M.packed(parts[1])))
        self.assertEqual(result['ledger']['metrics']['remaining_document_acquisition_jobs'],20)
        target=root/M.CONFIG_PATH;target.unlink();target.symlink_to(root/M.READER_PATH)
        with self.assertRaisesRegex(M.LedgerRefused,'FIXTURE_ALIAS'):M.DiskFixture(root).size(M.CONFIG_PATH)
        alias=AUTHOR_TMP/'ssl-job-ledger-fixture-alias';alias.symlink_to(root,target_is_directory=True)
        with self.assertRaisesRegex(M.LedgerRefused,'FIXTURE_ALIAS'):M.DiskFixture(alias)

    def test_30_disk_bad_root_and_extra_member(self):
        with self.assertRaisesRegex(M.LedgerRefused,'FIXTURE_ROOT'):M.DiskFixture(ROOT)
        root=AUTHOR_TMP/'ssl-job-ledger-fixture-case30';root.mkdir();parts=authored()
        for name,raw in parts[0].items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);GUARD['fixture_write_bytes']+=len(raw)
            self.assertLessEqual(GUARD['fixture_write_bytes'],33554432);p.write_bytes(raw)
        extra=root/parts[2]/'unexpected';extra.mkdir()
        with self.assertRaisesRegex(M.LedgerRefused,'FIXTURE_MEMBER'):
            M.compile_mock_once(parts[1],M.DiskFixture(root),Reader(),expected_plan_sha256=M.sha(M.packed(parts[1])))


    def test_31_exponent_overflow_rejected_at_any_depth(self):
        invalid=(b'1e999',b'-1e999',b'{"x":1e999}',b'{"nested":[0,{"x":-1e999}]}',
                 b'[1.0e+999]',b'{"s":"1e999","x":1E9999}',b'-Infinity')
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(M.LedgerRefused,'JSON_NONFINITE'):M.exact_json(raw)
        for raw in (b'1e308',b'-1e308',b'0.125',b'-0.0',b'1e-9999'):
            with self.subTest(finite=raw):
                value=M.exact_json(raw);self.assertIs(type(value),float);self.assertTrue(M.math.isfinite(value))
        value=M.exact_json(b'{"x":[0.125,1e-9999,-0.0],"s":"1e999"}')
        self.assertEqual(value['x'],[0.125,0.0,-0.0]);self.assertEqual(value['s'],'1e999')

    def test_32_caught_store_io_errors_latch_before_completion(self):
        for operation,error_type in (('size',PermissionError),('read',OSError),('size',OSError),('read',PermissionError)):
            observed=[]
            class FaultReader(Reader):
                def read_verified_public(self,view,prefix,config):
                    value=super().read_verified_public(view,prefix,config)
                    original=getattr(view.store,operation)
                    def fault(*args):raise error_type('/private/AUTHORED_PRIVATE_IO')
                    setattr(view.store,operation,fault)
                    try:
                        try:view.read(prefix+'/typed_document_readiness.json')
                        except M.LedgerRefused as error:observed.append(error.code)
                    finally:setattr(view.store,operation,original)
                    return value
            with self.subTest(operation=operation,error=error_type.__name__):
                output=self.refuses(authored(),FaultReader(),code='INPUT_IO')
                self.assertEqual(observed,['INPUT_IO'])
                record=M.exact_json(output.files['FAILURE.json'])
                self.assertTrue(record['budget']['failed']);self.assertTrue(record['budget']['closing'])
                self.assertEqual(record['budget']['reader_calls'],1)
                self.assertNotIn('job_ledger.json',output.files)
                self.assertNotIn(b'AUTHORED_PRIVATE_IO',b''.join(output.files.values()))

    def test_33_caught_missing_store_controls_still_latch(self):
        for operation,error_type in (('size',KeyError),('read',FileNotFoundError),('size',FileNotFoundError),('read',KeyError)):
            observed=[]
            class MissingReader(Reader):
                def read_verified_public(self,view,prefix,config):
                    value=super().read_verified_public(view,prefix,config)
                    original=getattr(view.store,operation)
                    def missing(*args):raise error_type('AUTHORED_MISSING')
                    setattr(view.store,operation,missing)
                    try:
                        try:view.read(prefix+'/typed_document_readiness.json')
                        except M.LedgerRefused as error:observed.append(error.code)
                    finally:setattr(view.store,operation,original)
                    return value
            with self.subTest(operation=operation,error=error_type.__name__):
                output=self.refuses(authored(),MissingReader(),code='MISSING_INPUT')
                self.assertEqual(observed,['MISSING_INPUT'])
                self.assertTrue(M.exact_json(output.files['FAILURE.json'])['budget']['failed'])
                self.assertNotIn('job_ledger.json',output.files)


def guarded_main():
    global M
    setup_direct_runtime()
    standalone_guard();M=load_module()
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(LedgerTests)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    console=stream.getvalue()
    if len(console.encode())>262144:raise RuntimeError('CONSOLE_CAP')
    print(console,end='')
    if result.wasSuccessful():print('MOCK_PUBLIC_SAMPLE_JSON='+json.dumps(PUBLIC_SAMPLE,sort_keys=True,separators=(',',':')))
    print(json.dumps({'kind':'MOCK_SAVED_JOB_LEDGER_SUITE','tests':result.testsRun,'failures':len(result.failures),
        'errors':len(result.errors),'guard':GUARD,'wall_seconds':time.monotonic()-START,
        'real_saved_reader_calls':0,'network_calls':0,'model_calls':0,'cost_usd':0,'interpreter_startup_read_accounting':'NOT_CLAIMED'},sort_keys=True))
    # Remove only this authored tree. No raw/private/project artifacts are read.
    for parent,dirs,files in os.walk(AUTHOR_TMP,topdown=False,followlinks=False):
        for name in files:(Path(parent)/name).unlink()
        for name in dirs:
            p=Path(parent)/name
            if p.is_symlink():p.unlink()
            else:p.rmdir()
    AUTHOR_TMP.rmdir()
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(guarded_main())
