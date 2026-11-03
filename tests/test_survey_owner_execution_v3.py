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
from civiclab.owner_budget_v3 import OwnerBudgetFixtureV3, SCOPE
from datetime import datetime, timedelta, timezone
import uuid
from civiclab.model import ExecutionBlocked
from civiclab.reconciled_client_v2 import FixtureHTTP, fixture_terms
from civiclab.reproduction import build_package
from civiclab.survey_execution import PhaseJournal
from civiclab.survey_owner_execution_v3 import run_mock_owner_bridge, run_live_owner_bridge, compile_owner_study

ROOT=Path(__file__).resolve().parents[1]
INSTRUMENT=json.loads((ROOT/'configs/e02_instrument.json').read_text())
STIMULI=json.loads((ROOT/'configs/e02_demo_stimuli.json').read_text())
PROFILES=[{'profile_id':'OWNER-JOURNAL-DEMO','party':'D'}]
T0=datetime(2026,11,3,12,tzinfo=timezone.utc)


def grant_study(owner,study,*,total=1000000,e02=None,now=T0):
    snap=owner.snapshot()
    return owner.grant_fixture({'kind':SCOPE,'approval_id':uuid.uuid4().hex,'owner_id':snap['owner_id'],
       'previous_approval_hash':snap['approval_hash'],'valid_from_utc':(now-timedelta(seconds=1)).isoformat(),
       'valid_until_utc':(now+timedelta(minutes=1)).isoformat(),'total_microusd':total,
       'module_microusd':{'E01':0,'E02':total if e02 is None else e02},
       'allowed_plans':{canonical_hash(p):{'module':'E02','terms_sha256':canonical_hash(study['terms']),
          'max_tokens':p['max_tokens'],'max_input_token_bound':max(p['pre_quote']['input_token_bound'],p['post_bound']['input_token_bound'])}
          for p in study['plans'].values()}})


def execute(root,owner,study,epoch,**kwargs):
    return run_mock_owner_bridge(root,study,expected_study_hash=canonical_hash(study),
           expected_approval_hash=epoch,ledger=owner,**kwargs)


def crash(root,owner_path,study,epoch,stage):
    owner=OwnerBudgetFixtureV3.open_fixture(owner_path,clock=lambda:T0)
    def die(*args,**kwargs):os._exit(87)
    if stage=='STARTED':
        original=PhaseJournal.start
        def start(self,*args):original(self,*args);die()
        target=patch.object(PhaseJournal,'start',start)
    elif stage=='RESERVE':
        original=owner.reserve
        def reserve(*args):original(*args);die()
        target=patch.object(owner,'reserve',reserve)
    elif stage in ('RESPONSE','SETTLED'):
        original=owner.transition
        def transition(receipt,status,**kwargs):
            out=original(receipt,status,**kwargs)
            if status==('RESPONSE_SEEN' if stage=='RESPONSE' else 'SETTLED'):die()
            return out
        target=patch.object(owner,'transition',transition)
    elif stage=='JOURNAL':
        original=PhaseJournal.finish
        def finish(self,unit,phase,status,result):
            out=original(self,unit,phase,status,result)
            if status.startswith('DONE_'):die()
            return out
        target=patch.object(PhaseJournal,'finish',finish)
    elif stage=='OWNER_COMMIT':target=patch.object(owner,'commit_phase',die)
    elif stage=='PAIR':
        original=owner.commit_phase
        def commit(*args):original(*args);die()
        target=patch.object(owner,'commit_phase',commit)
    else:target=patch.object(FixtureHTTP,'post',die)
    with target:execute(root,owner,study,epoch)


class OwnerJournalTests(unittest.TestCase):
    def make(self,root,terms=None,**kwargs):
        terms=terms or fixture_terms()
        policy=kwargs.pop('policy',None)
        owner=OwnerBudgetFixtureV3.create_fixture(Path(root)/'owner',clock=lambda:T0)
        http=FixtureHTTP(terms,**kwargs)
        study=compile_owner_study(PROFILES,STIMULI[:1],INSTRUMENT,terms=terms,content=http.content,overrides=http.overrides)
        grant_study(owner,study,**(policy or {}))
        return owner,http,terms

    def run_it(self,root,ledger,transport=None,terms=None,**kwargs):
        terms=terms or fixture_terms()
        transport=transport or FixtureHTTP(terms)
        study=compile_owner_study(PROFILES,STIMULI[:1],INSTRUMENT,terms=terms,content=transport.content,overrides=transport.overrides)
        epoch=kwargs.pop('epoch',ledger.snapshot()['approval_hash'])
        return execute(root,ledger,study,epoch,transport=transport,**kwargs)

    def test_shared_complete_runs_deterministic_analysis_and_no_network(self):
        with tempfile.TemporaryDirectory() as t,patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            ledger,http,terms=self.make(t)
            a=self.run_it(t,ledger,http,terms);b=self.run_it(t,ledger,terms=terms)
            for p in (a,b):
                run=verified_run(p);self.assertEqual(run['summary']['completed_global_calls'],10)
                self.assertEqual(run['summary']['actual_spend_usd'],0)
            self.assertEqual(json.loads((a/'analysis.json').read_text()),json.loads((b/'analysis.json').read_text()))
            self.assertEqual(json.loads((a/'analysis.json').read_text())['estimate_thermometer_points'],0)
            self.assertEqual(len(ledger.snapshot()['charges']),20)
            self.assertTrue(all(c['status']=='PHASE_COMMITTED' for c in ledger.snapshot()['charges']))
            self.assertEqual(len(http.calls),20) #10POST+10same-IDstats
            self.assertEqual((a.stat().st_mode&0o777),0o700)
            self.assertEqual(((a/'global-phase-journal.local.sqlite').stat().st_mode&0o777),0o600)

    def test_clean_resume_can_cross_another_completed_run_without_budget_reset(self):
        with tempfile.TemporaryDirectory() as t:
            ledger,http,terms=self.make(t)
            first=self.run_it(t,ledger,http,terms,stop_after_phases=3)
            self.assertEqual(len(ledger.snapshot()['charges']),3)
            other=self.run_it(t,ledger,terms=terms)
            self.assertTrue((other/'checksums.json').exists())
            before=len(ledger.snapshot()['charges'])
            first=self.run_it(t,ledger,terms=terms,resume=first)
            self.assertEqual(len(ledger.snapshot()['charges']),20)
            self.assertEqual(len(ledger.snapshot()['charges'])-before,7)
            self.assertEqual(verified_run(first)['summary']['completed_global_calls'],10)

    def test_invalid_answers_retain_private_raw_and_skip_post(self):
        for text in ('{"democratic_party":null,"republican_party":1}', '[1,2]', 'bad',
                     '{"democratic_party":'+('9'*1000)+',"republican_party":1}'):
            with self.subTest(kind=text[:15]),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t,content=text)
                path=self.run_it(t,ledger,http,terms)
                run=verified_run(path);self.assertEqual(run['summary']['completed_global_calls'],5)
                self.assertEqual(run['summary']['skipped_post_phases'],5)
                rows=json.loads((path/'responses.local.json').read_text())
                self.assertTrue(all(r['pre'] is None and r['post'] is None for r in rows))
                self.assertTrue(all(r['phase_accounting']['pre']['completion']['answer']['raw_text']==text for r in rows))
                self.assertTrue(all(r['phase_status']['post']=='SKIPPED_INVALID_PRE' for r in rows))

    def test_owner_budget_shared_even_when_new_run_or_directory(self):
        with tempfile.TemporaryDirectory() as t:
            terms=fixture_terms();terms.update(input_usd_per_token='0',output_usd_per_token='0',request_fee_usd='0.000001')
            ledger,http,_=self.make(t,terms,policy={'total':1,'e02':1})
            with self.assertRaises(ExecutionBlocked):self.run_it(t,ledger,http,terms)
            self.assertEqual(len(http.calls),2);self.assertEqual(sum(c['charged'] for c in ledger.snapshot()['charges']),1)
            for directory in (t,str(Path(t)/'new-output')):
                new=FixtureHTTP(terms)
                with self.assertRaises(ExecutionBlocked):self.run_it(directory,ledger,new,terms)
                self.assertEqual(new.calls,[])
            self.assertEqual(sum(c['charged'] for c in ledger.snapshot()['charges']),1)

    def test_missing_replaced_owner_or_changed_script_refuses_zero_calls(self):
        for mode in ('owner','policy','script','checkpoint','journal'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t)
                path=self.run_it(t,ledger,http,terms,stop_after_phases=1)
                new=FixtureHTTP(terms)
                if mode=='owner': ledger=OwnerBudgetFixtureV3.create_fixture(Path(t)/'other-owner',clock=lambda:T0)
                elif mode=='policy':ledger.header['owner_id']='0'*32
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
        for stage in ('STARTED','RESERVE','POST','RESPONSE','SETTLED','JOURNAL','OWNER_COMMIT','PAIR'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t);study=compile_owner_study(PROFILES,STIMULI[:1],INSTRUMENT,terms=terms);epoch=ledger.snapshot()['approval_hash'];ctx=multiprocessing.get_context('spawn')
                child=ctx.Process(target=crash,args=(t,str(ledger.directory),study,epoch,stage));child.start();child.join(30)
                self.assertFalse(child.is_alive());self.assertEqual(child.exitcode,87)
                path=next((Path(t)/'data/processed/runs').glob('e02-*'))
                self.assertEqual(len(ledger.snapshot()['charges']),0 if stage=='STARTED' else 1)
                if stage!='STARTED':self.assertEqual(ledger.snapshot()['charges'][0]['status'],
                   'STARTED' if stage in ('RESERVE','POST') else 'RESPONSE_SEEN' if stage=='RESPONSE' else 'PHASE_COMMITTED' if stage=='PAIR' else 'SETTLED')
                new=FixtureHTTP(terms)
                with self.assertRaises(ExecutionBlocked):
                    execute(t,ledger,study,epoch,transport=new,resume=path)
                self.assertEqual(new.calls,[])
                if stage not in ('PAIR','STARTED'):
                    with self.assertRaises(ExecutionBlocked):self.run_it(t,ledger,new,terms)
                    self.assertEqual(new.calls,[])
                elif stage=='PAIR':
                    # The prior phase is fully durably committed; only its run
                    # pair marker is stale. Other completed phases may proceed.
                    another=self.run_it(t,ledger,new,terms)
                    self.assertTrue((another/'checksums.json').exists())
                    self.assertEqual(len(ledger.snapshot()['charges']),11)

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
            with self.assertRaises(ValueError):compile_owner_study(profiles,STIMULI[:1],INSTRUMENT)
            self.assertEqual(http.calls,[])
            self.assertFalse((Path(t)/'data/processed/runs').exists())
            with self.assertRaises(ExecutionBlocked):run_live_owner_bridge()

    def test_answer_type_and_missing_content_remain_settled_quality_events(self):
        for content in (None,42):
            with self.subTest(content=content),tempfile.TemporaryDirectory() as t:
                ledger,http,terms=self.make(t,overrides={'response':{'choices':[{'message':{'content':content}}]}})
                path=self.run_it(t,ledger,http,terms)
                self.assertEqual(verified_run(path)['summary']['skipped_post_phases'],5)
                self.assertEqual(len(ledger.snapshot()['charges']),5)
                self.assertTrue(all(c['status']=='PHASE_COMMITTED' for c in ledger.snapshot()['charges']))

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
                states=ledger.snapshot()['charges'];self.assertEqual(len(states),1)
                self.assertIn(states[0]['status'],('UNCERTAIN','OVERRUN'))
                self.assertGreaterEqual(states[0]['charged'],states[0]['reserved'])
                if mode=='overrun':self.assertGreaterEqual(states[0]['charged'],1_000_000_000)
                new=FixtureHTTP(terms)
                with self.assertRaises(ExecutionBlocked):self.run_it(t,ledger,new,terms)
                self.assertEqual(new.calls,[])

    def test_explicit_epoch_renewal_resume_preserves_own_pre_authority(self):
        with tempfile.TemporaryDirectory() as t:
            owner,http,terms=self.make(t);now=[T0];owner.clock=lambda:now[0]
            study=compile_owner_study(PROFILES,STIMULI[:1],INSTRUMENT,terms=terms)
            old_epoch=owner.snapshot()['approval_hash']
            path=execute(t,owner,study,old_epoch,stop_after_phases=1)
            original=deepcopy(owner.snapshot()['charges'][0])
            now[0]=T0+timedelta(minutes=2);new_epoch=grant_study(owner,study,now=now[0])
            other=execute(t,owner,study,new_epoch)
            self.assertTrue((other/'checksums.json').exists())
            resumed=execute(t,owner,study,new_epoch,resume=path)
            own=[r for r in owner.snapshot()['charges'] if r['context']['run_id']==path.name]
            self.assertEqual(own[0],original)
            self.assertEqual(own[0]['context']['approval_hash'],old_epoch)
            self.assertTrue(all(r['context']['approval_hash']==new_epoch for r in own[1:]))
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],40)
            rows=json.loads((resumed/'responses.local.json').read_text())
            self.assertTrue(all(r['post_request']['pre_response']==r['pre'] for r in rows))

    def test_stale_expired_attempt_has_no_owner_reservation_and_unknown_is_not_zero(self):
        with tempfile.TemporaryDirectory() as t:
            owner,http,terms=self.make(t);owner.clock=lambda:T0+timedelta(minutes=2)
            with self.assertRaises(ExecutionBlocked):self.run_it(t,owner,http,terms)
            self.assertEqual(http.calls,[]);self.assertEqual(owner.snapshot()['charges'],[])
            path=next((Path(t)/'data/processed/runs').glob('e02-*'))
            self.assertEqual(PhaseJournal(path/'global-phase-journal.local.sqlite').rows()[0]['status'],'FAILED_BEFORE_OWNER_RESERVATION')
        with tempfile.TemporaryDirectory() as t:
            owner,http,terms=self.make(t)
            with patch('civiclab.owner_budget_v3.atomic_json',side_effect=OSError('AUTHORED_STORE_FAILURE')):
                with self.assertRaises(OSError):self.run_it(t,owner,http,terms)
            self.assertEqual(http.calls,[])
            path=next((Path(t)/'data/processed/runs').glob('e02-*'))
            self.assertEqual(PhaseJournal(path/'global-phase-journal.local.sqlite').rows()[0]['status'],'FAILED_OWNER_STATE_UNKNOWN')
            with self.assertRaises(ExecutionBlocked):owner.snapshot()

    def test_changed_external_study_and_invalid_assignments_zero_writes(self):
        with tempfile.TemporaryDirectory() as t:
            owner,http,terms=self.make(t);study=compile_owner_study(PROFILES,STIMULI[:1],INSTRUMENT,terms=terms)
            original=canonical_hash(study);study['seed']+=1
            with self.assertRaises(ExecutionBlocked):run_mock_owner_bridge(t,study,expected_study_hash=original,expected_approval_hash=owner.snapshot()['approval_hash'],ledger=owner,transport=http)
            self.assertEqual(http.calls,[]);self.assertFalse((Path(t)/'data/processed/runs').exists())
            for profiles in ([],PROFILES*2,[{'profile_id':' ','party':'D'}], [{'profile_id':str(i),'party':'D'} for i in range(37)]):
                with self.assertRaises(ValueError):compile_owner_study(profiles,STIMULI[:1],INSTRUMENT)

    def test_resealed_own_prior_epoch_foreign_receipt_and_duplicate_rows_refuse(self):
        for mode in ('prior','epoch','foreign','duplicate'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                owner,http,terms=self.make(t)
                path=self.run_it(t,owner,http,terms,stop_after_phases=2)
                dbpath=path/'global-phase-journal.local.sqlite'
                with sqlite3.connect(dbpath) as db:
                    if mode in ('prior','epoch'):
                        raw=json.loads(db.execute("SELECT request FROM phases WHERE phase='post'").fetchone()[0])
                        if mode=='prior':raw['survey_request']['pre_response']['democratic_party']+=1
                        else:raw['approval_hash']='0'*64
                        db.execute("UPDATE phases SET request=?,request_hash=? WHERE phase='post'",(json.dumps(raw),canonical_hash(raw)))
                    elif mode=='duplicate':
                        db.execute('CREATE TABLE duplicate AS SELECT * FROM phases')
                        db.execute('DROP TABLE phases');db.execute('ALTER TABLE duplicate RENAME TO phases')
                        db.execute('INSERT INTO phases SELECT * FROM phases LIMIT 1')
                if mode=='foreign':
                    other=self.run_it(t,owner,terms=terms)
                    with sqlite3.connect(other/'global-phase-journal.local.sqlite') as db:
                        result=db.execute("SELECT result FROM phases WHERE phase='pre' LIMIT 1").fetchone()[0]
                    with sqlite3.connect(dbpath) as db:db.execute("UPDATE phases SET result=? WHERE phase='pre'",(result,))
                pair=path/'global-phase-pair.local.json';value=json.loads(pair.read_text());value['journal_sha256']=sha256_file(dbpath);atomic_json(pair,value)
                new=FixtureHTTP(terms)
                with self.assertRaises((ValueError,ExecutionBlocked)):self.run_it(t,owner,new,terms,resume=path)
                self.assertEqual(new.calls,[])

    def test_private_answer_body_absent_from_generic_local_overview(self):
        marker='AUTHORED_PRIVATE_RESPONSE_SENTINEL_V3'
        content=json.dumps({'democratic_party':60,'republican_party':40,'private_marker':marker})
        with tempfile.TemporaryDirectory() as t:
            owner,http,terms=self.make(t,content=content)
            path=self.run_it(t,owner,http,terms)
            self.assertIn(marker,(path/'responses.local.json').read_text())
            self.assertNotIn(marker,json.dumps(verified_run(path)))
            with self.assertRaises(ValueError):build_package(t,Path(t)/'blocked-private.zip',[path.name])
            self.assertFalse((Path(t)/'blocked-private.zip').exists())
