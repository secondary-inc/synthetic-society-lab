"""Shared-ledger survey integration: authored fixtures, no network/keys."""
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from civiclab.common import atomic_json, canonical_hash, sha256_file
from civiclab.dashboard import verified_run
from civiclab.live_billing_v2 import GlobalFixtureLedger, fixture_policy
from civiclab.model import ExecutionBlocked
from civiclab.reconciled_client_v2 import FixtureHTTP, fixture_terms
from civiclab.reproduction import build_package
from civiclab.survey_execution import PhaseJournal
from civiclab.survey_global_execution_v2 import run_mock_global_bridge, run_live_global_bridge

ROOT=Path(__file__).resolve().parents[1]
INSTRUMENT=json.loads((ROOT/'configs/e02_instrument.json').read_text())
STIMULI=json.loads((ROOT/'configs/e02_demo_stimuli.json').read_text())
PROFILES=[{'profile_id':'GLOBAL-DEMO-'+str(i),'party':p} for i,p in enumerate(('D','R','I'))]


def crash(root, owner, policy, stage):
    ledger=GlobalFixtureLedger.open(owner,policy)
    def die(*args,**kwargs):os._exit(87)
    if stage=='JOURNAL':
        original=PhaseJournal.finish
        def finish(self,unit,phase,status,result):
            if status.startswith('DONE_'):die()
            return original(self,unit,phase,status,result)
        target=patch.object(PhaseJournal,'finish',finish)
    elif stage=='OWNER_COMMIT':target=patch.object(GlobalFixtureLedger,'commit_phase',die)
    elif stage=='PAIR':
        import civiclab.survey_global_execution_v2 as execution
        original=execution.atomic_json
        def write(path,value):
            if Path(path).name=='global-phase-pair.local.json' and Path(path).exists():die()
            return original(path,value)
        target=patch.object(execution,'atomic_json',write)
    else:target=patch.object(FixtureHTTP,'post',die)
    with target:
        run_mock_global_bridge(root,PROFILES[:1],STIMULI[:1],INSTRUMENT,ledger=ledger)


class GlobalSurveyTests(unittest.TestCase):
    def make(self, root, terms=None, **kwargs):
        terms=terms or fixture_terms(); ledger=GlobalFixtureLedger.create(Path(root)/'owner',kwargs.pop('policy',None))
        return ledger,FixtureHTTP(terms,**kwargs),terms
    def run_it(self,root,ledger,transport=None,terms=None,**kwargs):
        return run_mock_global_bridge(root,PROFILES,STIMULI[:1],INSTRUMENT,ledger=ledger,transport=transport,terms=terms,**kwargs)

    def test_shared_complete_runs_deterministic_analysis_and_no_network(self):
        with tempfile.TemporaryDirectory() as t,patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            ledger,http,terms=self.make(t)
            a=self.run_it(t,ledger,http,terms);b=self.run_it(t,ledger,terms=terms)
            for p in (a,b):
                run=verified_run(p);self.assertEqual(run['summary']['completed_global_calls'],30)
                self.assertEqual(run['summary']['actual_spend_usd'],0)
            self.assertEqual(json.loads((a/'analysis.json').read_text()),json.loads((b/'analysis.json').read_text()))
            self.assertEqual(json.loads((a/'analysis.json').read_text())['estimate_thermometer_points'],0)
            self.assertEqual(len(ledger.snapshot()),60)
            self.assertTrue(all(c['status']=='PHASE_COMMITTED' for c in ledger.snapshot()))
            self.assertEqual(len(http.calls),60) #30POST+30same-IDstats
            self.assertEqual((a.stat().st_mode&0o777),0o700)
            self.assertEqual(((a/'global-phase-journal.local.sqlite').stat().st_mode&0o777),0o600)

    def test_clean_resume_can_cross_another_completed_run_without_budget_reset(self):
        with tempfile.TemporaryDirectory() as t:
            ledger,http,terms=self.make(t)
            first=self.run_it(t,ledger,http,terms,stop_after_phases=3)
            self.assertEqual(len(ledger.snapshot()),3)
            other=self.run_it(t,ledger,terms=terms)
            self.assertTrue((other/'checksums.json').exists())
            before=len(ledger.snapshot())
            first=self.run_it(t,ledger,terms=terms,resume=first)
            self.assertEqual(len(ledger.snapshot()),60)
            self.assertEqual(len(ledger.snapshot())-before,27)
            self.assertEqual(verified_run(first)['summary']['completed_global_calls'],30)

    def test_invalid_answers_retain_private_raw_and_skip_post(self):
        for text in ('{"democratic_party":null,"republican_party":1}', '[1,2]', 'bad',
                     '{"democratic_party":'+('9'*1000)+',"republican_party":1}'):
            with self.subTest(kind=text[:15]),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t,content=text)
                path=self.run_it(t,ledger,http,terms)
                run=verified_run(path);self.assertEqual(run['summary']['completed_global_calls'],15)
                self.assertEqual(run['summary']['skipped_post_phases'],15)
                rows=json.loads((path/'responses.local.json').read_text())
                self.assertTrue(all(r['pre'] is None and r['post'] is None for r in rows))
                self.assertTrue(all(r['phase_accounting']['pre']['completion']['answer']['raw_text']==text for r in rows))
                self.assertTrue(all(r['phase_status']['post']=='SKIPPED_INVALID_PRE' for r in rows))

    def test_owner_budget_shared_even_when_new_run_or_directory(self):
        with tempfile.TemporaryDirectory() as t:
            terms=fixture_terms();terms.update(input_usd_per_token='0',output_usd_per_token='0',request_fee_usd='0.000001')
            ledger,http,_=self.make(t,terms,policy=fixture_policy(total=1,e01=0,e02=1))
            with self.assertRaises(ExecutionBlocked):self.run_it(t,ledger,http,terms)
            self.assertEqual(len(http.calls),2);self.assertEqual(sum(c['charged'] for c in ledger.snapshot()),1)
            for directory in (t,str(Path(t)/'new-output')):
                new=FixtureHTTP(terms)
                with self.assertRaises(ExecutionBlocked):self.run_it(directory,ledger,new,terms)
                self.assertEqual(new.calls,[])
            self.assertEqual(sum(c['charged'] for c in ledger.snapshot()),1)

    def test_missing_replaced_owner_or_changed_script_refuses_zero_calls(self):
        for mode in ('owner','policy','script','checkpoint','journal'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t)
                path=self.run_it(t,ledger,http,terms,stop_after_phases=1)
                new=FixtureHTTP(terms)
                if mode=='owner': ledger=GlobalFixtureLedger.create(Path(t)/'other-owner')
                elif mode=='policy':ledger.policy['total_microusd']+=1
                elif mode=='script':new.content='{}'
                elif mode=='checkpoint':(path/'global-phase-pair.local.json').unlink()
                else:(path/'global-phase-journal.local.sqlite').unlink()
                with self.assertRaises((ExecutionBlocked,ValueError)):
                    self.run_it(t,ledger,new,terms,resume=path)
                self.assertEqual(new.calls,[])

    def test_semantically_resealed_journal_output_route_and_seed_refuse(self):
        for mode in ('output','seed','route','prehash'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t)
                path=self.run_it(t,ledger,http,terms,stop_after_phases=1)
                dbpath=path/'global-phase-journal.local.sqlite'
                with sqlite3.connect(dbpath) as db:
                    result=json.loads(db.execute('SELECT result FROM phases').fetchone()[0])
                    if mode=='output':result['output']['democratic_party']+=1
                    elif mode=='seed':result['completion']['context']['sampling']['seed']+=1
                    elif mode=='route':result['completion']['context']['terms']['requested_route']='other'
                    else:result['completion']['context']['envelope']['request_hash']='0'*64
                    db.execute('UPDATE phases SET result=?',(json.dumps(result),))
                pair=path/'global-phase-pair.local.json';state=json.loads(pair.read_text())
                state['journal_sha256']=sha256_file(dbpath);atomic_json(pair,state)
                new=FixtureHTTP(terms)
                with self.assertRaises((ExecutionBlocked,ValueError)):
                    self.run_it(t,ledger,new,terms,resume=path)
                self.assertEqual(new.calls,[])

    def test_missing_changed_phase_checkpoint_and_orphan_charge_refuse(self):
        for mode in ('missing','changed','extra','orphan'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t)
                path=self.run_it(t,ledger,http,terms,stop_after_phases=1)
                cp=next(path.glob('phase-*.local.json'))
                if mode=='missing':cp.unlink()
                elif mode=='changed':cp.write_text('{}')
                elif mode=='extra':atomic_json(path/'phase-extra.local.json',{})
                else:
                    with sqlite3.connect(path/'global-phase-journal.local.sqlite') as db:db.execute('DELETE FROM phases')
                pair=path/'global-phase-pair.local.json';state=json.loads(pair.read_text())
                state['phase_files']={p.name:sha256_file(p) for p in path.glob('phase-*.local.json')}
                state['journal_sha256']=sha256_file(path/'global-phase-journal.local.sqlite');atomic_json(pair,state)
                new=FixtureHTTP(terms)
                with self.assertRaises((ExecutionBlocked,ValueError)):
                    self.run_it(t,ledger,new,terms,resume=path)
                self.assertEqual(new.calls,[])

    def test_actual_process_death_at_dispatch_settlement_and_owner_commit(self):
        for stage in ('POST','JOURNAL','OWNER_COMMIT','PAIR'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t);ctx=multiprocessing.get_context('spawn')
                child=ctx.Process(target=crash,args=(t,str(ledger.directory),ledger.policy,stage));child.start();child.join(30)
                self.assertFalse(child.is_alive());self.assertEqual(child.exitcode,87)
                path=next((Path(t)/'data/processed/runs').glob('e02-*'))
                self.assertEqual(len(ledger.snapshot()),1)
                self.assertEqual(ledger.snapshot()[0]['status'],'STARTED' if stage=='POST' else 'PHASE_COMMITTED' if stage=='PAIR' else 'SETTLED')
                new=FixtureHTTP(terms)
                with self.assertRaises(ExecutionBlocked):
                    run_mock_global_bridge(t,PROFILES[:1],STIMULI[:1],INSTRUMENT,ledger=ledger,transport=new,resume=path)
                self.assertEqual(new.calls,[])
                if stage!='PAIR':
                    with self.assertRaises(ExecutionBlocked):self.run_it(t,ledger,new,terms)
                    self.assertEqual(new.calls,[])
                else:
                    # The prior phase is fully durably committed; only its run
                    # pair marker is stale. Other completed phases may proceed.
                    another=self.run_it(t,ledger,new,terms)
                    self.assertTrue((another/'checksums.json').exists())
                    self.assertEqual(len(ledger.snapshot()),31)

    def test_same_run_concurrency_refuses_and_private_run_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            ledger,http,terms=self.make(t)
            path=self.run_it(t,ledger,http,terms,stop_after_phases=1)
            import fcntl
            with (path/'.lock').open('a') as lock:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                new=FixtureHTTP(terms)
                with self.assertRaisesRegex(RuntimeError,'already owned'):
                    self.run_it(t,ledger,new,terms,resume=path)
                self.assertEqual(new.calls,[])
            path=self.run_it(t,ledger,terms=terms,resume=path)
            with self.assertRaises(ValueError):build_package(t,Path(t)/'not-allowed.zip',[path.name])
            self.assertFalse((Path(t)/'not-allowed.zip').exists())

    def test_input_privacy_and_live_factory_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            ledger,http,terms=self.make(t)
            profiles=deepcopy(PROFILES);profiles[0]['person_name']='PRIVATE_MARKER'
            with self.assertRaises(ValueError):run_mock_global_bridge(t,profiles,STIMULI[:1],INSTRUMENT,ledger=ledger,transport=http)
            self.assertEqual(http.calls,[])
            self.assertFalse((Path(t)/'data/processed/runs').exists())
            with self.assertRaises(ExecutionBlocked):run_live_global_bridge()

    def test_answer_type_and_missing_content_remain_settled_quality_events(self):
        for content in (None,42):
            with self.subTest(content=content),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t,overrides={'response':{'choices':[{'message':{'content':content}}]}})
                path=self.run_it(t,ledger,http,terms)
                self.assertEqual(verified_run(path)['summary']['skipped_post_phases'],15)
                self.assertEqual(len(ledger.snapshot()),15)
                self.assertTrue(all(c['status']=='PHASE_COMMITTED' for c in ledger.snapshot()))

    def test_cancel_and_route_overrun_hold_global_ledger_without_retry(self):
        for mode in ('cancel','route','overrun'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                overrides={'stats':{'provider_name':'UNVERIFIED'}} if mode=='route' else {'response':{'usage':{'cost':1000}}} if mode=='overrun' else {}
                ledger,http,terms=self.make(t,overrides=overrides)
                if mode=='cancel':
                    with patch.object(FixtureHTTP,'post',side_effect=KeyboardInterrupt):
                        with self.assertRaises(KeyboardInterrupt):self.run_it(t,ledger,http,terms)
                else:
                    with self.assertRaises(ExecutionBlocked):self.run_it(t,ledger,http,terms)
                states=ledger.snapshot();self.assertEqual(len(states),1)
                self.assertIn(states[0]['status'],('UNCERTAIN','OVERRUN'))
                self.assertGreaterEqual(states[0]['charged'],states[0]['reserved'])
                if mode=='overrun':self.assertGreaterEqual(states[0]['charged'],1_000_000_000)
                new=FixtureHTTP(terms)
                with self.assertRaises(ExecutionBlocked):self.run_it(t,ledger,new,terms)
                self.assertEqual(new.calls,[])
