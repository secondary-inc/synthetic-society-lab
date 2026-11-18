"""Pure CI harness models. Import installs no audit hooks; no child is launched.

Direct execution adds finite author-only limits. Frozen qualification modules are
read as AST inventories only. Supervisor processes/selectors are always fakes.
"""
from pathlib import Path
from contextlib import contextmanager
import importlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('offline_ci_authored_model', ROOT/'scripts/run_offline_ci_v1.py')
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


def binding(row):
    return {key: row[key] for key in ('path','bytes','sha256')}


def valid_receipt(job, specification, digest='runner'):
    r = dict(kind='OFFLINE_CI_CHILD_V1', job_id=job['id'], runner_sha256=digest,
             status='PASS', tests_run=1, started_cases=['Ordinary.test_one'], skips=[])
    if job['phase'] == 'ordinary':
        cases = [Path(job['test_module']).stem+'.'+case for case in job['declared_local_cases']] if 'test_module' in job else ['test_ordinary.Ordinary.test_one']
        r.update(tests_run=len(cases), suite_scope='ONE_ORDINARY_MODULE' if 'test_module' in job else 'LEGACY_AGGREGATE',
                 planned_case_ids=cases[:], discovered_case_ids=cases[:], started_case_ids=cases[:],
                 completed_case_ids=cases[:], outcomes=[{'case_id':case,'status':'PASS'} for case in cases],
                 failures=[], errors=[], unexpected_successes=[], not_run_cases=[], unstarted_skips=[])
        if 'test_module' in job:r.update(test_module=job['test_module'],source_ref=job['source_ref'])
        if job.get('test_module') in c.NO_SITE_PROFILES:
            r.update(no_site=True,startup_profile=c.NO_SITE_PROFILES[job['test_module']])
    if job['phase'] != 'ordinary':
        row = specification['inventory'][job['group']]
        cases = row['historical_cases'] if job['phase']=='historical' else row['portable_cases']
        r.update(frozen_source_ref=binding(row), planned_cases=cases,
                 tests_run=len(cases), started_cases=cases)
        if job['phase']=='historical':
            r.update(status='NOT_RUN', tests_run=0, started_cases=[],
                     qualification={'status':'NOT_RUN','reasons':['UNSUPPORTED_PLATFORM']})
    return r


class CollectionTests(unittest.TestCase):
    def test_exact_frozen_inventory_and_all_applicable_cases(self):
        before=set(sys.modules)
        spec=c.plan(ROOT)
        self.assertEqual((spec['portable_cases'], spec['historical_cases'],len(spec['jobs'])),(216,4,11))
        self.assertEqual(sum(len(r['all_cases']) for r in spec['inventory'].values()),220)
        self.assertEqual(set(sys.modules),before)
        self.assertEqual(len(spec['inventory']),6)

    def test_loader_excludes_six_only(self):
        loader=c.OrdinaryLoader(ROOT)
        for row in c.FROZEN.values():
            self.assertFalse(loader._match_path(row[0],str(ROOT/'tests'/row[0]),'test*.py'))
        self.assertTrue(loader._match_path('test_other.py',str(ROOT/'tests/test_other.py'),'test*.py'))

    def test_direct_and_transitive_frozen_execution_refused(self):
        for row in c.FROZEN.values():
            barrier=c.CollectionBarrier(ROOT)
            with self.assertRaisesRegex(c.IsolationError,'TRANSITIVE_FROZEN'):
                barrier('exec',(compile('pass',str(ROOT/'tests'/row[0]),'exec'),))
        captured=[]
        class TransitiveLoader:
            def discover(self, path):
                captured[0]('exec',(compile('pass',str(ROOT/'tests'/next(iter(c.FROZEN.values()))[0]),'exec'),))
        with self.assertRaises(c.IsolationError):
            c.collect_ordinary(ROOT, loader=TransitiveLoader(),install_hook=captured.append)
        self.assertFalse(captured[0].collecting)

    def test_no_real_hook_and_registration_guard_reset(self):
        callbacks=[]
        class Loader:
            def discover(self,path):
                with self_outer.assertRaisesRegex(c.IsolationError,'GLOBAL_HOOK'):
                    callbacks[0]('sys.addaudithook',())
                return unittest.TestSuite()
        self_outer=self
        original=c.unittest.main
        suite,barrier=c.collect_ordinary(ROOT,loader=Loader(),install_hook=callbacks.append)
        barrier('sys.addaudithook',())
        self.assertIs(c.unittest.main,original)
        self.assertFalse(barrier.collecting)
        self.assertEqual(suite.countTestCases(),0)

    def test_runner_import_has_no_top_level_effect_calls(self):
        import ast
        tree=ast.parse((ROOT/'scripts/run_offline_ci_v1.py').read_bytes())
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef,ast.If)):continue
            calls=[ast.unparse(x.func) for x in ast.walk(node) if isinstance(x,ast.Call)]
            self.assertFalse(any(x in {'sys.addaudithook','subprocess.Popen','child_entry','main'} for x in calls))


class OrdinaryNamespaceTests(unittest.TestCase):
    @contextmanager
    def authored_tree(self):
        # Also works when this test is itself collected inside the real ordinary
        # child: isolate only its import namespace, never execute repo tests.
        names={p.stem for p in (ROOT/'tests').glob('*.py')}
        removed={name:module for name,module in list(sys.modules.items())
                 if name=='tests' or name.startswith('tests.') or name in names}
        before_path,before_meta=sys.path[:],sys.meta_path[:]
        before_cache=sys.path_importer_cache.copy()
        for name in removed:del sys.modules[name]
        sys.path[:]=[p for p in sys.path if p not in {str(ROOT),str(ROOT/'tests')}]
        sys.meta_path[:]=[finder for finder in sys.meta_path if not getattr(finder,'offline_ci_owned_tests_namespace_v1_2',False)]
        try:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory).resolve();(root/'tests').mkdir()
                yield root
        finally:
            for name in list(sys.modules):
                if name=='tests' or name.startswith('tests.') or name in removed:
                    del sys.modules[name]
            sys.modules.update(removed)
            sys.path[:],sys.meta_path[:]=before_path,before_meta
            sys.path_importer_cache.clear();sys.path_importer_cache.update(before_cache)

    def test_bare_and_qualified_authored_fixtures_collect_and_restore_state(self):
        with self.authored_tree() as root:
            (root/'tests/test_ns_fixture.py').write_text("VALUE='MOCK_LOCAL_FIXTURE'\n")
            (root/'tests/test_ns_bridge.py').write_text('from test_ns_fixture import VALUE as BARE\nfrom tests.test_ns_fixture import VALUE as QUALIFIED\n')
            before_path,before_meta,before_cache=sys.path[:],sys.meta_path[:],sys.path_importer_cache.copy()
            callbacks=[]
            class Loader(c.OrdinaryLoader):
                def discover(self,path):
                    bridge=importlib.import_module('test_ns_bridge')
                    self_outer.assertEqual((bridge.BARE,bridge.QUALIFIED),('MOCK_LOCAL_FIXTURE',)*2)
                    for name in ('test_ns_fixture','tests.test_ns_fixture'):
                        self_outer.assertEqual(Path(sys.modules[name].__file__),root/'tests/test_ns_fixture.py')
                    return unittest.TestSuite()
            self_outer=self
            suite,barrier=c.collect_ordinary(root,loader=Loader(root),install_hook=callbacks.append)
            self.assertEqual(suite.countTestCases(),0)
            self.assertFalse(barrier.collecting);self.assertEqual(len(callbacks),1)
            self.assertEqual(sys.path,before_path);self.assertEqual(sys.meta_path,before_meta)
            self.assertEqual(sys.path_importer_cache,before_cache)
            self.assertFalse(any(name in sys.modules for name in ('tests','tests.test_ns_fixture','test_ns_fixture','test_ns_bridge')))

    def test_lazy_qualified_fixture_import_kept_for_ordinary_child_lifetime(self):
        with self.authored_tree() as root:
            (root/'tests/test_lazy_fixture.py').write_text("VALUE='MOCK_LAZY_LOCAL'\n")
            (root/'tests/test_lazy_bridge.py').write_text('def lazy():\n from tests.test_lazy_fixture import VALUE\n return VALUE\n')
            callbacks=[];observed=[];original_collect=c._collect_ordinary
            class Loader:
                def discover(self,path):
                    observed.append(importlib.import_module('test_lazy_bridge'))
                    return unittest.TestSuite()
            class ModelRunner:
                def __init__(self,*args,**kwargs):pass
                def run(self,suite):
                    observed.append(observed[0].lazy())
                    return c.RecordingResult(io.StringIO(),False,0)
            def collect(root):return original_collect(root,loader=Loader(),install_hook=callbacks.append)
            with mock.patch.object(c,'_collect_ordinary',side_effect=collect), mock.patch.object(c.unittest,'TextTestRunner',ModelRunner), mock.patch.object(c.resource,'setrlimit'), mock.patch.object(c.signal,'signal'), mock.patch.object(c.signal,'setitimer'):
                receipt=c.child_entry(root,'ordinary','ordinary')
            self.assertEqual(observed[1],'MOCK_LAZY_LOCAL')
            self.assertEqual(receipt['tests_run'],0)  # ModelRunner executed no test.
            self.assertFalse(any(name in sys.modules for name in ('tests','tests.test_lazy_fixture','test_lazy_bridge')))

    def test_foreign_cached_namespace_and_path_shadowing_refused(self):
        with self.authored_tree() as root:
            (root/'tests/test_ns_fixture.py').write_text('VALUE=1\n')
            foreign=root/'foreign';foreign.mkdir();(foreign/'tests').mkdir()
            (foreign/'tests/__init__.py').write_text('raise AssertionError("FOREIGN_MUST_NOT_EXECUTE")\n')
            before_path,before_meta=sys.path[:],sys.meta_path[:]
            with mock.patch.dict(sys.modules,{'tests':SimpleNamespace(__spec__=None)}):
                with self.assertRaisesRegex(c.IsolationError,'UNBOUND_CACHED_TEST'):
                    with c.ordinary_import_context(root):self.fail('foreign namespace admitted')
            with mock.patch.object(sys,'path',[str(foreign),*sys.path]):
                with self.assertRaisesRegex(c.IsolationError,'FOREIGN_TEST_MODULE_ORIGIN'):
                    with c.ordinary_import_context(root):self.fail('foreign path admitted')
            (foreign/'tests/__init__.py').unlink()
            with mock.patch.object(sys,'path',[str(foreign),*sys.path]):
                with self.assertRaisesRegex(c.IsolationError,'FOREIGN_TESTS_NAMESPACE'):
                    with c.ordinary_import_context(root):self.fail('foreign namespace portion admitted')
            self.assertEqual(sys.path,before_path);self.assertEqual(sys.meta_path,before_meta)
            self.assertNotIn('tests',sys.modules)

    def test_existing_owned_namespace_attributes_restored_after_import(self):
        with self.authored_tree() as root:
            (root/'tests/test_ns_fixture.py').write_text('VALUE=1\n')
            finder=c.OrdinaryNamespaceFinder(root)
            namespace=importlib.util.module_from_spec(finder.find_spec('tests'))
            with mock.patch.dict(sys.modules,{'tests':namespace}):
                before=namespace.__dict__.copy()
                with c.ordinary_import_context(root):
                    importlib.import_module('tests.test_ns_fixture')
                    self.assertIn('test_ns_fixture',namespace.__dict__)
                self.assertEqual(namespace.__dict__,before)

    def test_foreign_bare_fixture_and_aliased_root_refused(self):
        with self.authored_tree() as root:
            (root/'tests/test_ns_fixture.py').write_text('VALUE=1\n')
            foreign=root/'foreign';foreign.mkdir();(foreign/'test_ns_fixture.py').write_text('VALUE=2\n')
            with mock.patch.object(sys,'path',[str(foreign),*sys.path]):
                with self.assertRaisesRegex(c.IsolationError,'FOREIGN_TEST_MODULE_ORIGIN'):
                    with c.ordinary_import_context(root):self.fail('foreign bare fixture admitted')
            alias=root/'alias';alias.symlink_to(root,target_is_directory=True)
            with self.assertRaisesRegex(c.IsolationError,'ORDINARY_IMPORT_PATH_ALIAS'):
                with c.ordinary_import_context(alias):self.fail('aliased root admitted')

    def test_transitive_frozen_bare_and_qualified_imports_never_execute(self):
        for spelling in ('bare','qualified'):
            with self.subTest(spelling=spelling),self.authored_tree() as root:
                name=Path(next(iter(c.FROZEN.values()))[0]).stem
                (root/'tests'/f'{name}.py').write_text('raise AssertionError("FROZEN_PLACEHOLDER_MUST_NOT_EXECUTE")\n')
                target=name if spelling=='bare' else 'tests.'+name
                (root/'tests/test_bridge.py').write_text(f'import {target}\n')
                before_path,before_meta,before_cache=sys.path[:],sys.meta_path[:],sys.path_importer_cache.copy()
                with self.assertRaisesRegex(c.IsolationError,'TRANSITIVE_FROZEN_MODULE_IMPORT'):
                    with c.ordinary_import_context(root):importlib.import_module('test_bridge')
                self.assertNotIn(target,sys.modules)
                self.assertEqual(sys.path,before_path);self.assertEqual(sys.meta_path,before_meta)
                self.assertEqual(sys.path_importer_cache,before_cache)

    def test_preloaded_frozen_module_refused_under_both_names(self):
        with self.authored_tree() as root:
            filename=next(iter(c.FROZEN.values()))[0]
            path=root/'tests'/filename;path.write_text('raise AssertionError("NEVER_EXECUTE")\n')
            for name in (path.stem,'tests.'+path.stem):
                module=importlib.util.module_from_spec(importlib.util.spec_from_file_location(name,path))
                with self.subTest(name=name),mock.patch.dict(sys.modules,{name:module}):
                    with self.assertRaisesRegex(c.IsolationError,'PRELOADED_FROZEN_TEST_MODULE'):
                        with c.ordinary_import_context(root):self.fail('preloaded frozen module admitted')


class ReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.spec=c.plan(ROOT)

    def test_historical_exact_profile_and_unsupported_variants(self):
        host=dict(version='3.11.17',implementation='cpython',platform='darwin',machine='arm64',macos='26.6')
        size,digest=c.SOCKET_PINS[host['version']]
        observation=dict(bytes=size,sha256=digest)
        self.assertEqual(c.historical_admission(host,observation)['status'],'SUPPORTED')
        for key,value in [('version','3.11.18'),('platform','linux'),('machine','x86_64'),('macos','26.5'),('implementation','pypy')]:
            self.assertEqual(c.historical_admission(dict(host,**{key:value}),observation)['status'],'NOT_RUN')
        self.assertEqual(c.historical_admission(host,dict(observation,sha256='unknown'))['status'],'NOT_RUN')
        self.assertEqual(c.historical_admission(host,None)['status'],'NOT_RUN')

    def test_complete_frozen_coverage_no_blanket_skip(self):
        for job in self.spec['jobs']:
            receipt=valid_receipt(job,self.spec)
            c.validate_coverage(receipt,job,self.spec)
            if job['phase']=='portable':
                for change in ({'tests_run':0},{'started_cases':[]},{'skips':[{'case':'one'}]}, {'status':'NOT_RUN'}, {'frozen_source_ref':{}}):
                    with self.assertRaises(c.IsolationError):
                        c.validate_coverage(dict(receipt,**change),job,self.spec)
        ordinary=self.spec['jobs'][0]
        with self.assertRaises(c.IsolationError):c.validate_coverage(dict(valid_receipt(ordinary,self.spec),tests_run=0),ordinary,self.spec)

    def test_historical_pass_cannot_claim_unknown_host(self):
        job=next(j for j in self.spec['jobs'] if j['phase']=='historical')
        r=valid_receipt(job,self.spec)
        r.update(status='PASS',tests_run=1,started_cases=r['planned_cases'],skips=[])
        with self.assertRaises(c.IsolationError):c.validate_coverage(r,job,self.spec)
        r.update(host=dict(version='3.12.14',implementation='cpython',platform='darwin',machine='arm64',macos='26.6'),
                 socket_observation=dict(zip(('bytes','sha256'),c.SOCKET_PINS['3.12.14'])))
        c.validate_coverage(r,job,self.spec)

    def test_receipt_binding_duplicate_keys_and_missing_marker(self):
        job=self.spec['jobs'][0];r=valid_receipt(job,self.spec)
        raw=(c.MARKER+json.dumps(r)+'\n').encode()
        self.assertEqual(c.parse_receipt(raw,job,'runner'),r)
        for bad in (b'',raw+raw,(c.MARKER+'{"kind":0,"kind":1}').encode(),raw.replace(b'runner',b'spoof')):
            with self.assertRaises((c.IsolationError,ValueError)):c.parse_receipt(bad,job,'runner')

    def test_receipt_size_distinguishes_large_ordinary_inventory(self):
        job=self.spec['jobs'][0];r=valid_receipt(job,self.spec);r['padding']='x'*140000
        raw=(c.MARKER+json.dumps(r)).encode()
        c.parse_receipt(raw,job,'runner')
        with self.assertRaises(c.IsolationError):c.parse_receipt(raw,self.spec['jobs'][1],'runner')

    def test_final_status_preserves_failure_and_not_run(self):
        self.assertEqual(c.final_status([{'status':'PASS'},{'status':'NOT_RUN'}]),'PASS_PORTABLE_HISTORICAL_NOT_RUN')
        self.assertEqual(c.final_status([{'status':'NOT_RUN'}],True),'FAIL_HISTORICAL_NOT_RUN')
        self.assertEqual(c.final_status([{'status':'FAIL'},{'status':'NOT_RUN'}]),'FAIL')


class ModuleIsolationRepairTests(unittest.TestCase):
    def authored_tree(self, directory):
        root=Path(directory).resolve();(root/'tests').mkdir()
        for name in ('test_a.py','test_b.py','test_c.py','test_d.py','test_zero.py'):
            (root/'tests'/name).write_text('import unittest\nclass Local(unittest.TestCase):\n def test_one(self): pass\n' if name!='test_zero.py' else '# import-only helper\n')
        return root

    def specification(self, root, **kwargs):
        with mock.patch.object(c,'plan',return_value={'jobs':[{'id':'ordinary'},{'id':'frozen-model'}],'inventory':{}}):
            return c.module_plan(root,**kwargs)

    def test_shards_partition_dynamic_modules_and_preserve_total_time_allowance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.authored_tree(directory)
            specs=[self.specification(root,shard_index=i,shard_count=4) for i in range(4)]
            all_jobs=[job['id'] for spec in specs for job in spec['jobs']]
            self.assertEqual(len(all_jobs),len(set(all_jobs)))
            self.assertEqual(len(all_jobs),6)
            self.assertEqual(sum(s['shard']['budget_seconds'] for s in specs),c.COORDINATOR_WALL)
            self.assertTrue(all(s['ordinary_manifest_sha256']==specs[0]['ordinary_manifest_sha256'] for s in specs))
            (root/'tests/test_new.py').write_text('# newly added module\n')
            updated=self.specification(root)
            self.assertIn('ordinary-test_new',[j['id'] for j in updated['jobs']])
            self.assertNotEqual(updated['ordinary_manifest_sha256'],specs[0]['ordinary_manifest_sha256'])

    def test_focused_plan_never_claims_whole_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            spec=self.specification(self.authored_tree(directory),only_modules=['test_a.py'])
            self.assertEqual(spec['suite_scope'],'FOCUSED_MODULES_ONLY')
            self.assertEqual([j['id'] for j in spec['jobs']],['ordinary-test_a'])
            def dispatch(command,env,job,output):
                receipt=valid_receipt(job,spec,command[-1]);path=output/'mock.stdout'
                c.save_new(path,(c.MARKER+json.dumps(receipt)).encode())
                return dict(stdout=str(path),returncode=0,reason=None,reaped=True)
            with mock.patch.object(c,'module_plan',return_value=spec):
                summary=c.run_parent(Path(directory)/'output',run_process=dispatch,shard_count=1,only_modules=['test_a.py'])
            self.assertEqual(summary['status'],'PASS_FOCUSED_ONLY')

    def test_nested_packages_refuse_before_partial_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.authored_tree(directory)
            package=root/'tests/pkg';package.mkdir()
            (package/'__init__.py').write_text('raise AssertionError("MUST_NOT_IMPORT")\n')
            (package/'test_nested.py').write_text('import unittest\nclass Local(unittest.TestCase):\n def test_one(self): pass\n')
            with self.assertRaisesRegex(c.IsolationError,'NESTED_PACKAGES_UNSUPPORTED'):
                c.ordinary_modules(root)

    def test_source_hash_change_and_alias_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.authored_tree(directory);reference=c.module_source(root,'test_a.py')
            (root/'tests/test_a.py').write_text('# changed\n')
            with self.assertRaisesRegex(c.IsolationError,'SOURCE_CHANGED'):c.module_source(root,'test_a.py',reference['sha256'])
            (root/'tests/test_link.py').symlink_to(root/'tests/test_a.py')
            with self.assertRaisesRegex(c.IsolationError,'ALIAS'):c.ordinary_modules(root)
            with self.assertRaises(c.IsolationError):c.module_source(root,'../test_a.py')

    def test_module_receipt_requires_exact_case_accounting_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            spec=self.specification(self.authored_tree(directory));job=spec['jobs'][0]
            receipt=valid_receipt(job,spec);c.validate_coverage(receipt,job,spec)
            changes=[{'planned_case_ids':[]},{'discovered_case_ids':[]},{'started_case_ids':[]},
                     {'completed_case_ids':[]},{'outcomes':[]},{'source_ref':{}},{'test_module':'test_other.py'},
                     {'tests_run':7},{'failures':['foreign']},{'unexpected_successes':['foreign']},
                     {'not_run_cases':[{'case_id':receipt['planned_case_ids'][0],'qualification':{'status':'NOT_RUN','reasons':['invented']}}]}]
            for change in changes:
                with self.subTest(change=change),self.assertRaises(c.IsolationError):c.validate_coverage(dict(receipt,**change),job,spec)
            forged=dict(receipt,planned_case_ids=[],discovered_case_ids=[],started_case_ids=[],completed_case_ids=[],outcomes=[],tests_run=0)
            with self.assertRaisesRegex(c.IsolationError,'DECLARED_CASE_MISSING'):c.validate_coverage(forged,job,spec)

    def test_positive_count_without_inventory_is_refused(self):
        with self.assertRaises(c.IsolationError):c.validate_coverage({'status':'PASS','tests_run':1},{'phase':'ordinary'}, {})

    def test_skip_and_expected_failure_require_matching_disposition(self):
        job={'id':'ordinary','phase':'ordinary'}
        receipt=valid_receipt(job,{})
        case=receipt['outcomes'][0]['case_id']
        receipt['outcomes'][0]['status']='SKIP'
        with self.assertRaisesRegex(c.IsolationError,'SKIP_OUTCOME_MISMATCH'):
            c.validate_coverage(receipt,job,{})
        receipt['skips']=[{'case':case,'reason':'authored reason'}]
        c.validate_coverage(receipt,job,{})
        receipt['outcomes'][0]['status']='PASS'
        with self.assertRaisesRegex(c.IsolationError,'SKIP_OUTCOME_MISMATCH'):
            c.validate_coverage(receipt,job,{})
        receipt['skips']=[]
        receipt['outcomes'][0]['status']='EXPECTED_FAILURE'
        with self.assertRaisesRegex(c.IsolationError,'EXPECTED_FAILURE_DISPOSITION'):
            c.validate_coverage(receipt,job,{})
        receipt['expected_failures']=[case]
        c.validate_coverage(receipt,job,{})

    def test_subtest_skip_is_visible_and_validates_on_parent(self):
        class Cases(unittest.TestCase):
            def test_one(self):
                for value in (1,2):
                    with self.subTest(value=value):self.skipTest('authored subtest skip')
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
        planned=[test.id() for test in c.flatten(suite)]
        result=unittest.TextTestRunner(stream=io.StringIO(),resultclass=c.OrdinaryRecordingResult).run(suite)
        receipt=valid_receipt({'id':'ordinary','phase':'ordinary'},{})
        receipt.update(planned_case_ids=planned,discovered_case_ids=planned,
                       started_case_ids=result.started_case_ids,completed_case_ids=result.completed_case_ids,
                       outcomes=result.outcomes,tests_run=1,
                       skips=[{'case':test.id(),'reason':reason} for test,reason in result.skipped])
        self.assertEqual(result.outcomes[0]['status'],'SKIP')
        c.validate_coverage(receipt,{'id':'ordinary','phase':'ordinary'},{})
        receipt['skips'][0]['case']='unrelated.test_case (value=1)'
        with self.assertRaisesRegex(c.IsolationError,'SKIP_PARENT_MISSING'):
            c.validate_coverage(receipt,{'id':'ordinary','phase':'ordinary'},{})

    def test_duplicate_discovered_ids_require_duplicate_completion(self):
        job={'id':'ordinary','phase':'ordinary'};receipt=valid_receipt(job,{})
        for key in ('planned_case_ids','discovered_case_ids','started_case_ids','completed_case_ids','outcomes'):
            receipt[key]=receipt[key]*2
        receipt['tests_run']=2;c.validate_coverage(receipt,job,{})
        receipt['completed_case_ids']=receipt['completed_case_ids'][:1]
        with self.assertRaises(c.IsolationError):c.validate_coverage(receipt,job,{})

    def test_failure_traceback_is_flushed_before_next_case(self):
        stream=io.StringIO();observed=[]
        class Cases(unittest.TestCase):
            def test_a(self):raise ValueError('AUTHORED_EARLY_ERROR')
            def test_b(self):observed.append(stream.getvalue())
        result=unittest.TextTestRunner(stream=stream,resultclass=c.OrdinaryRecordingResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
        self.assertFalse(result.wasSuccessful());self.assertEqual(result.testsRun,2)
        self.assertIn('AUTHORED_EARLY_ERROR',observed[0]);self.assertIn('CI_FAILURE_DETAIL_END',observed[0])
        self.assertEqual([r['status'] for r in result.outcomes],['ERROR','PASS'])
        self.assertEqual(result.started_case_ids,result.completed_case_ids)

    def test_subtest_failure_is_recorded_on_parent(self):
        class Cases(unittest.TestCase):
            def test_one(self):
                with self.subTest(value=1):self.fail('AUTHORED_SUBTEST')
        stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,resultclass=c.OrdinaryRecordingResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
        self.assertEqual(result.outcomes[0]['status'],'FAIL')
        self.assertIn('AUTHORED_SUBTEST',stream.getvalue())

    def test_class_setup_skip_covers_only_original_members(self):
        class Skipped(unittest.TestCase):
            @classmethod
            def setUpClass(cls):raise unittest.SkipTest('authored class skip')
            def test_one(self):pass
            def test_two(self):pass
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Skipped)
        planned=[t.id() for t in c.flatten(suite)]
        result=unittest.TextTestRunner(stream=io.StringIO(),resultclass=c.OrdinaryRecordingResult).run(suite)
        covered=c.unstarted_skip_cases(planned,[],result.skipped)
        self.assertEqual(covered[0]['case_ids'],planned)
        receipt=valid_receipt({'id':'ordinary','phase':'ordinary'}, {})
        receipt.update(planned_case_ids=planned,discovered_case_ids=planned,started_case_ids=[],completed_case_ids=[],
                       tests_run=0,outcomes=[],unstarted_skips=covered,
                       skips=[{'case':t.id(),'reason':reason} for t,reason in result.skipped])
        job={'id':'ordinary','phase':'ordinary','test_module':'test_authored.py','source_ref':{},'declared_local_cases':[]}
        receipt.update(test_module='test_authored.py',source_ref={},suite_scope='ONE_ORDINARY_MODULE')
        c.validate_coverage(receipt,job,{})
        receipt['skips']=[]
        with self.assertRaises(c.IsolationError):c.validate_coverage(receipt,job,{})

    def test_host_classification_models_never_run_historical_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.authored_tree(directory);(root/'scripts').mkdir();(root/'scripts/contract.py').write_text('# inert authored contract\n')
            test_ref=c.module_source(root,'test_a.py')
            raw=(root/'scripts/contract.py').read_bytes();contract=dict(path='scripts/contract.py',bytes=len(raw),sha256=c.sha(raw))
            rule=dict(test_ref=test_ref,contract_ref=contract,gate='DARWIN_MIME_ONLY',local_cases=['Local.test_one'])
            with mock.patch.object(c,'HOST_CASE_RULES',{'test_a.py':rule}):
                self.assertEqual(c.host_case_decision(root,'test_a.py',platform_name='darwin')['status'],'SUPPORTED')
                decision=c.host_case_decision(root,'test_a.py',platform_name='linux')
                self.assertEqual(decision['status'],'NOT_RUN')
                spec=self.specification(root);job=spec['jobs'][0];receipt=valid_receipt(job,spec)
                receipt.update(tests_run=0,started_case_ids=[],completed_case_ids=[],outcomes=[],
                               not_run_cases=[{'case_id':receipt['planned_case_ids'][0],'qualification':decision}])
                with mock.patch.object(c.sys,'platform','linux'):c.validate_coverage(receipt,job,spec)
                with mock.patch.object(c.sys,'platform','darwin'),self.assertRaises(c.IsolationError):c.validate_coverage(receipt,job,spec)
            rule=dict(rule,gate='EXACT_GENERATED_RUNTIME')
            with mock.patch.object(c,'HOST_CASE_RULES',{'test_a.py':rule}):
                self.assertEqual(c.host_case_decision(root,'test_a.py',version='unknown')['status'],'NOT_RUN')
                self.assertEqual(c.host_case_decision(root,'test_a.py',version='3.11.17',observe=lambda:c.COMPILE_PROFILE_PINS['3.11.17'])['status'],'SUPPORTED')
                self.assertEqual(c.host_case_decision(root,'test_a.py',version='3.11.17',observe=lambda:{})['status'],'NOT_RUN')
                (root/'scripts/contract.py').write_text('# drift\n')
                with self.assertRaises(c.IsolationError):c.host_case_decision(root,'test_a.py')

    def test_literal_host_partition_keeps_all_four_portable_mime_cases(self):
        self.assertEqual(sorted(len(r['local_cases']) for r in c.HOST_CASE_RULES.values()),[4,5,5,8])
        self.assertEqual(sum(r['gate']=='DARWIN_MIME_ONLY' for r in c.HOST_CASE_RULES.values()),3)
        self.assertEqual(len(c.COMPILE_PROFILE_PINS),2)

    def test_canonical_interpreter_resolves_existing_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'python';target.write_text('# inert executable model\n')
            alias=Path(directory)/'python-alias';alias.symlink_to(target)
            with mock.patch.object(c.sys,'executable',str(alias)):self.assertEqual(c.canonical_interpreter(),str(target.resolve()))


class HostedFailureRepairTests(unittest.TestCase):
    def test_four_exact_installer_mock_modules_get_no_site_without_global_path_rewrite(self):
        self.assertEqual(set(c.NO_SITE_PROFILES),{'test_e01_pypdf701_install_'+v+'.py' for v in ('v1','v1_1','v1_2','v1_3')})
        for name,profile in c.NO_SITE_PROFILES.items():
            job={'phase':'ordinary','test_module':name,'source_ref':profile['test_ref']}
            self.assertEqual(c.child_isolation_flags(job),['-I','-B','-S'])
            with self.assertRaises(c.IsolationError):c.child_isolation_flags(dict(job,source_ref={}))
        self.assertEqual(c.child_isolation_flags({'phase':'ordinary','test_module':'test_other.py'}),['-I','-B'])
        self.assertEqual(c.child_isolation_flags({'phase':'portable'}),['-I','-B','-S'])

    def test_no_site_child_admission_is_source_bound_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();(root/'tests').mkdir();(root/'scripts').mkdir()
            (root/'tests/test_mock.py').write_text('# authored inert test\n');(root/'scripts/contract.py').write_text('# authored no-site contract\n')
            def reference(path):
                body=(root/path).read_bytes();return {'path':path,'bytes':len(body),'sha256':c.sha(body)}
            rule={'test_ref':reference('tests/test_mock.py'),'contract_ref':reference('scripts/contract.py'),'reason':'AUTHORED_MODEL_ONLY'}
            with mock.patch.object(c,'NO_SITE_PROFILES',{'test_mock.py':rule}):
                with mock.patch.object(c.sys,'flags',SimpleNamespace(no_site=0)),self.assertRaisesRegex(c.IsolationError,'NO_SITE_CHILD_REQUIRED'):
                    c.no_site_admission(root,'test_mock.py')
                with mock.patch.object(c.sys,'flags',SimpleNamespace(no_site=1)):
                    self.assertEqual(c.no_site_admission(root,'test_mock.py'),rule)
                    (root/'scripts/contract.py').write_text('# changed\n')
                    with self.assertRaisesRegex(c.IsolationError,'NO_SITE_PROFILE_SOURCE_CHANGED'):c.no_site_admission(root,'test_mock.py')

    def test_no_site_receipt_cannot_claim_default_startup(self):
        name=next(iter(c.NO_SITE_PROFILES));profile=c.NO_SITE_PROFILES[name]
        job={'id':'ordinary-model','phase':'ordinary','test_module':name,'source_ref':profile['test_ref'],'declared_local_cases':['Local.test_one']}
        receipt=valid_receipt(job,{})
        c.validate_coverage(receipt,job,{})
        for change in ({'no_site':False},{'startup_profile':None},{'startup_profile':{}}):
            with self.assertRaisesRegex(c.IsolationError,'NO_SITE_STARTUP_BINDING'):c.validate_coverage(dict(receipt,**change),job,{})

    def test_production_mime_class_preserves_three_portable_origin_cases(self):
        row=c.HOST_CASE_RULES['test_e01_pypdf701_install_v1_5.py']
        self.assertEqual(row['gate'],'DARWIN_MIME_ONLY')
        self.assertEqual(set(row['local_cases']),{'ProductionMimeTests.'+name for name in (
            'test_bound_stdlib_origin_fresh_initialization_has_no_mime_file_reads',
            'test_bound_stdlib_origin_prepopulated_initialization_resets_mappings',
            'test_init_error_propagates_once_without_fallback','test_invalid_public_state_refuses')})
        for name in ('test_unknown_origin_refuses_before_initialization','test_unknown_spec_origin_refuses_before_initialization','test_alias_origin_refuses_before_initialization'):
            self.assertNotIn('ProductionMimeTests.'+name,row['local_cases'])

    def test_result_relative_timestamps_expose_class_setup_time_without_sleep(self):
        now=[0.0];stream=io.StringIO()
        class Cases(unittest.TestCase):
            @classmethod
            def setUpClass(cls):now[0]=2.5
            def test_one(self):pass
        with mock.patch.object(c.time,'perf_counter',side_effect=lambda:now[0]):
            result=unittest.TextTestRunner(stream=stream,resultclass=c.OrdinaryRecordingResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
        self.assertTrue(result.wasSuccessful())
        events=[json.loads(line[len(c.EVENT_MARKER):]) for line in stream.getvalue().splitlines() if line.startswith(c.EVENT_MARKER)]
        self.assertEqual(events[0]['event'],'START');self.assertEqual(events[0]['since_result_seconds'],2.5)
        self.assertEqual(events[-1]['since_result_seconds'],2.5)


class FakePipe:
    def __init__(self,number):self.number=number;self.closed=False
    def fileno(self):return self.number
    def close(self):self.closed=True


class GuardedEntrypointModelTests(unittest.TestCase):
    def test_supported_historical_stub_receipt_survives_coverage_validation(self):
        raw=b'''import unittest
class Model(unittest.TestCase):
    def test_portable(self): raise AssertionError("MUST_NOT_RUN_IN_HISTORICAL")
    def test_historical(self): self.assertTrue(True)
def guarded_main(): unittest.main(failfast=True,verbosity=2)
'''
        row=('AUTHORED_STUB_ONLY.py',len(raw),c.sha(raw),2,'Model.test_historical',None)
        size,digest=c.SOCKET_PINS['3.11.17']
        observation={'scope':'MOCK_HISTORICAL_SOURCE_ONLY','bytes':size,'sha256':digest}
        original=c.unittest.main
        with mock.patch.dict(c.FROZEN,{'stub':row}), mock.patch.object(c,'verified_source',return_value=raw) as source, mock.patch.object(c,'socket_observation',return_value=observation), mock.patch.object(c.platform,'machine',return_value='arm64'), mock.patch.object(c.platform,'mac_ver',return_value=('26.6',(),'')), mock.patch.object(c.sys,'version','3.11.17 MOCK'), mock.patch.object(c.sys,'platform','darwin'), mock.patch.object(sys,'stderr',io.StringIO()):
            receipt=c.run_frozen(ROOT,'stub','historical')
        self.assertIs(c.unittest.main,original)
        self.assertEqual(receipt['status'],'PASS')
        self.assertEqual(receipt['qualification']['status'],'SUPPORTED')
        self.assertEqual(receipt['host']['version'],'3.11.17')
        self.assertEqual(receipt['started_cases'],['Model.test_historical'])
        self.assertEqual(source.call_count,2)
        # Mirror main's source-bound child envelope, then exercise real parsing
        # and coverage checks. No real frozen source/guard or process is run.
        source_ref={'path':'tests/'+row[0],'bytes':len(raw),'sha256':c.sha(raw)}
        job={'id':'stub-historical','group':'stub','phase':'historical'}
        specification={'inventory':{'stub':dict(source_ref, historical_cases=['Model.test_historical'],portable_cases=['Model.test_portable'])}}
        receipt.update(kind='OFFLINE_CI_CHILD_V1',job_id=job['id'],runner_sha256='MOCK_RUNNER_SHA',frozen_source_ref=source_ref)
        parsed=c.parse_receipt((c.MARKER+c.packed(receipt).decode()).encode(),job,'MOCK_RUNNER_SHA')
        c.validate_coverage(parsed,job,specification)
        for change in ({'host':{}},{'frozen_source_ref':dict(source_ref,sha256='MOCK_WRONG_SOURCE')}):
            with self.assertRaises(c.IsolationError):c.validate_coverage(dict(parsed,**change),job,specification)

    def test_unsupported_historical_model_never_executes_stub(self):
        raw=b'import unittest\nraise AssertionError("MUST_NOT_EXECUTE")\nclass Model(unittest.TestCase):\n def test_historical(self): pass\n'
        row=('AUTHORED_STUB_ONLY.py',len(raw),c.sha(raw),1,'Model.test_historical',None)
        with mock.patch.dict(c.FROZEN,{'stub':row}), mock.patch.object(c,'verified_source',return_value=raw), mock.patch.object(c,'socket_observation',return_value=None), mock.patch.object(c.platform,'machine',return_value='MOCK'), mock.patch.object(c.platform,'mac_ver',return_value=('MOCK',(),'')):
            receipt=c.run_frozen(ROOT,'stub','historical',admission=lambda *a:{'status':'NOT_RUN','reasons':['MOCK_UNSUPPORTED']})
        self.assertEqual(receipt['status'],'NOT_RUN')
        self.assertEqual(receipt['tests_run'],0)

    def test_authored_stub_guard_selection_and_main_restoration(self):
        raw=b'''import unittest
class Model(unittest.TestCase):
    def test_portable(self): self.assertTrue(True)
    def test_historical(self): raise AssertionError("MUST_NOT_RUN_IN_PORTABLE")
def guarded_main(): unittest.main(failfast=True,verbosity=2)
'''
        row=('AUTHORED_STUB_ONLY.py',len(raw),c.sha(raw),2,'Model.test_historical',None)
        original=c.unittest.main
        with mock.patch.dict(c.FROZEN,{'stub':row}), mock.patch.object(c,'verified_source',return_value=raw) as source, mock.patch.object(c,'socket_observation',return_value={'scope':'MOCK'}), mock.patch.object(sys,'stderr',io.StringIO()):
            receipt=c.run_frozen(ROOT,'stub','portable')
            self.assertEqual(receipt['status'],'PASS')
            self.assertEqual(receipt['started_cases'],['Model.test_portable'])
            self.assertEqual(source.call_count,2)
        self.assertIs(c.unittest.main,original)

    def test_authored_stub_guard_error_restores_parent_main(self):
        raw=b'import unittest\nclass Model(unittest.TestCase):\n def test_one(self): pass\ndef guarded_main(): raise ValueError("MOCK_GUARD_FAILURE")\n'
        row=('AUTHORED_STUB_ONLY.py',len(raw),c.sha(raw),1,None,None)
        original=c.unittest.main
        with mock.patch.dict(c.FROZEN,{'stub':row}), mock.patch.object(c,'verified_source',return_value=raw):
            with self.assertRaisesRegex(ValueError,'MOCK_GUARD_FAILURE'):c.run_frozen(ROOT,'stub','portable')
        self.assertIs(c.unittest.main,original)


class FakeProcess:
    def __init__(self,hang=False):
        self.stdout=FakePipe(101);self.stderr=FakePipe(102);self.pid=54321
        self.returncode=None;self.waits=0;self.hang=hang
    def poll(self):return 0
    def wait(self,timeout):
        self.waits+=1
        if self.hang:raise c.subprocess.TimeoutExpired('MOCK',timeout)
        self.returncode=0;return 0


class FakeSelector:
    def __init__(self):self.entries={};self.closed=False
    def register(self,pipe,event,sink):self.entries[pipe.number]=SimpleNamespace(fileobj=pipe,data=sink)
    def unregister(self,pipe):self.entries.pop(pipe.number)
    def get_map(self):return self.entries
    def select(self,timeout):return [(key,1) for key in list(self.entries.values())]
    def close(self):self.closed=True


class SupervisorTests(unittest.TestCase):
    def model(self, directory, *, chunks=None, cap=100, times=None, hang=False, launch_error=False):
        proc=FakeProcess(hang);selector=FakeSelector();killed=[];calls=[]
        chunks={101:[b'hello',b''],102:[b'world',b'']} if chunks is None else chunks
        def launch(*args,**kwargs):
            calls.append((args,kwargs))
            if launch_error:raise OSError('MOCK_LAUNCH_FAILURE')
            return proc
        clock=(lambda:0) if times is None else mock.Mock(side_effect=times)
        result=c.supervise(['MOCK'],{},dict(id='model',wall_seconds=120,output_bytes=cap),directory,
                          popen=launch,selector_factory=lambda:selector,clock=clock,
                          read_fd=lambda fd,n:chunks[fd].pop(0),kill_group=lambda *a:killed.append(a))
        return result,proc,selector,killed,calls

    def test_success_bounded_capture_and_fresh_session(self):
        with tempfile.TemporaryDirectory() as directory:
            result,proc,selector,killed,calls=self.model(directory)
            self.assertTrue(result['reaped']);self.assertIsNone(result['reason'])
            self.assertEqual(Path(result['stdout']).read_bytes(),b'hello')
            self.assertEqual(result['captured_bytes'],10);self.assertFalse(killed)
            self.assertTrue(selector.closed and proc.stdout.closed and proc.stderr.closed)
            self.assertTrue(calls[0][1]['start_new_session'])

    def test_output_limit_kills_and_reaps(self):
        with tempfile.TemporaryDirectory() as directory:
            r,p,s,k,_=self.model(directory,cap=3)
            self.assertEqual(r['reason'],'OUTPUT_LIMIT');self.assertTrue(r['reaped'])
            self.assertEqual(len(k),1);self.assertEqual(p.waits,1)
            self.assertEqual(Path(r['stdout']).stat().st_size,3)

    def test_wall_limit_kills_and_unknown_shutdown_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            r,p,s,k,_=self.model(directory,times=[0,121,122],hang=True)
            self.assertEqual(r['reason'],'WALL_LIMIT');self.assertFalse(r['reaped']);self.assertEqual(len(k),1)

    def test_launch_failure_preserved_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            r,p,s,k,calls=self.model(directory,launch_error=True)
            self.assertEqual(r['reason'],'SUPERVISOR_ERROR');self.assertFalse(r['reaped'])
            self.assertEqual(len(calls),1);self.assertEqual(k,[]);self.assertTrue(s.closed)

    def test_combined_capture_boundary(self):
        capture=c.Capture(3)
        self.assertEqual(capture.take(b'abc'),(b'abc',False))
        self.assertEqual(capture.take(b'd'),(b'',True))


class CoordinatorTests(unittest.TestCase):
    def test_mock_dispatch_isolated_environment_and_unsupported_host(self):
        specification=c.plan(ROOT)
        specification['jobs']=[specification['jobs'][0],specification['jobs'][1],specification['jobs'][7]]
        calls=[]
        def dispatch(command,env,job,directory):
            calls.append((command,env,job))
            r=valid_receipt(job,specification,command[-1]);path=directory/(job['id']+'.stdout')
            c.save_new(path,(c.MARKER+json.dumps(r)+'\n').encode())
            return dict(stdout=str(path),returncode=0,reason=None,reaped=True)
        with tempfile.TemporaryDirectory() as parent, mock.patch.object(c,'plan',return_value=specification), mock.patch.dict(os.environ,{'OPENROUTER_API_KEY':'MOCK_PRIVATE_VALUE'}):
            result=c.run_parent(Path(parent)/'one',run_process=dispatch)
            self.assertEqual(result['status'],'PASS_PORTABLE_HISTORICAL_NOT_RUN')
            self.assertEqual(len(calls),3)
            for command,env,job in calls:
                self.assertIn('-I',command);self.assertIn('-B',command)
                self.assertEqual('-S' in command,job['phase']!='ordinary')
                self.assertNotIn('OPENROUTER_API_KEY',env)
                self.assertEqual(env['MAX_SPEND_USD'],'0')
            self.assertEqual(len(list((Path(parent)/'one').glob('*-RESERVED.json'))),3)
            with self.assertRaises(FileExistsError):c.run_parent(Path(parent)/'one',run_process=dispatch)

    def test_dispatch_failure_not_hidden_or_stale(self):
        specification=c.plan(ROOT);specification['jobs']=specification['jobs'][:2]
        def dispatch(command,env,job,directory):
            if job['phase']!='ordinary':raise OSError('MOCK_DISPATCH_FAILURE')
            path=directory/'mock.stdout';r=valid_receipt(job,specification,command[-1])
            c.save_new(path,(c.MARKER+json.dumps(r)).encode())
            return dict(stdout=str(path),returncode=0,reason=None,reaped=True)
        with tempfile.TemporaryDirectory() as parent, mock.patch.object(c,'plan',return_value=specification):
            result=c.run_parent(Path(parent)/'one',run_process=dispatch)
            self.assertEqual(result['status'],'FAIL')
            self.assertEqual(result['results'][1]['status'],'ERROR')
            self.assertNotIn('execution',result['results'][1])


def bounded_main():
    """Finite trusted authored tests, no real subprocess/network or raw data reads."""
    import builtins
    import resource
    import signal
    import sysconfig
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    def deadline(*_):raise AssertionError('CI_AUTHOR_120_SECOND_LIMIT')
    signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline)
    signal.setitimer(signal.ITIMER_REAL,120)
    reads=[0];writes=[0];console=[0]
    # All authored scratch writes live under this one fresh directory.
    scratch=tempfile.TemporaryDirectory(prefix='civiclab-ci-author-')
    scratch_root=Path(scratch.name).resolve();tempfile.tempdir=str(scratch_root)
    stdlib=Path(sysconfig.get_path('stdlib')).resolve()
    helper_path=ROOT/'scripts/e01_authored_dirfd_guard_v2_20261112.py'
    helper_spec=importlib.util.spec_from_file_location('ci_author_dirfd_helper',helper_path)
    helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
    descriptor_guard=helper.DirectoryFdGuard(lambda path,flags:None)
    allowed={Path(__file__).resolve(),(ROOT/'scripts/run_offline_ci_v1.py').resolve(),
             helper_path.resolve(),
             *((ROOT/'tests'/row[0]).resolve() for row in c.FROZEN.values())}
    def audit(event,args):
        if event.startswith(('socket.','ctypes.')) or event in {'subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.system','pty.spawn'}:
            raise AssertionError('CI_AUTHOR_NO_REAL_NETWORK_PROCESS_NATIVE')
        if event=='open':
            value,mode,flags=args
            if isinstance(value,int):
                size=os.fstat(value).st_size
            else:
                path=Path(os.path.realpath(descriptor_guard.event_path(value)))
                writing=flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
                if writing:
                    if not path.is_relative_to(scratch_root):raise AssertionError('CI_AUTHOR_WRITE_OUTSIDE_SCRATCH')
                    return
                if not (path in allowed or path.is_relative_to(stdlib) or path.is_relative_to(scratch_root)):
                    raise AssertionError('CI_AUTHOR_READ_OUTSIDE_SCOPE')
                try:size=path.stat().st_size
                except FileNotFoundError:size=0
            reads[0]+=size+1
            if reads[0]>67108864:raise AssertionError('CI_AUTHOR_READ_CAP')
    sys.addaudithook(audit)
    os.open=descriptor_guard.open;os.close=descriptor_guard.close
    class Writer:
        def __init__(self,stream,counter,limit):self.stream=stream;self.counter=counter;self.limit=limit
        def __getattr__(self,name):return getattr(self.stream,name)
        def __enter__(self):return self
        def __exit__(self,*args):return self.stream.__exit__(*args)
        def write(self,value):
            self.counter[0]+=len(value.encode() if isinstance(value,str) else value)
            if self.counter[0]>self.limit:raise AssertionError('CI_AUTHOR_WRITE_OR_OUTPUT_CAP')
            return self.stream.write(value)
    for owner,name in ((builtins,'open'),(io,'open'),(os,'fdopen')):
        original=getattr(owner,name)
        def wrapped(*args,_original=original,**kwargs):
            stream=_original(*args,**kwargs)
            mode=kwargs.get('mode',args[1] if len(args)>1 else 'r')
            return Writer(stream,writes,33554432) if any(x in mode for x in 'wax+') else stream
        setattr(owner,name,wrapped)
    original_write=os.write
    def write(fd,value):
        writes[0]+=len(value)
        if writes[0]>33554432:raise AssertionError('CI_AUTHOR_TEMP_WRITE_CAP')
        return original_write(fd,value)
    os.write=write
    sys.stdout=Writer(sys.stdout,console,262144);sys.stderr=Writer(sys.stderr,console,262144)
    try:
        program=unittest.main(verbosity=2,exit=False)
        print(json.dumps({'kind':'CI_ISOLATION_AUTHOR_MOCK_V1','python':sys.version.split()[0],
                          'tests_run':program.result.testsRun,'successful':program.result.wasSuccessful(),
                          'read_reservation_bytes':reads[0],'temp_write_bytes':writes[0],
                          'console_bytes_before_receipt':console[0],
                          'actual_children':0,'actual_frozen_groups':0,'network_calls':0}))
        return 0 if program.result.wasSuccessful() else 1
    finally:
        scratch.cleanup()


if __name__=='__main__':raise SystemExit(bounded_main())
