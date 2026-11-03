"""Authored same-owner amendment tests. No actual owner, credentials or HTTP."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import json
import multiprocessing
import os
import sqlite3
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from civiclab.common import canonical_bytes, canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_price_v4 import contract_from_catalog
from civiclab.production_admission_v4 import compile_compatibility_release, code_pins, make_context
from civiclab.production_owner_v4 import ProductionOwnerV4, request_binding
from civiclab.additional_compatibility_owner_v1 import (
    _AdditionalOwnerV1, OLD_RECEIPT, EVENT, code_contract, validate_bundle, receipt_for, open_actual)
from test_production_admission_v4 import account, initialize, approval, grant, reserve, seen, settle, checkpoint
from test_production_price_v4 import catalog, decision_for, T0, COMPONENTS


def materials(run):
    data=catalog(); data['data']['id']='openai/gpt-4.1-nano'
    for i,e in enumerate(data['data']['endpoints']):
        e['model_id']='openai/gpt-4.1-nano'; e['provider_name']='Azure'
        e['tag']='azure' if i==0 else 'azure/authored'
        e['pricing']={k:'0' for k in COMPONENTS}; e['pricing']['request']='0.000340'
    d=decision_for(data); d.update(model='openai/gpt-4.1-nano',requested_route='azure',reported_provider='Azure')
    terms=contract_from_catalog(canonical_bytes(data),d,expected_decision_hash=canonical_hash(d))
    release=compile_compatibility_release(terms,d,run_id=run)
    review={'kind':'INDEPENDENT_PRODUCTION_RELEASE_REVIEW_V4','scope':'CODE_PRICE_REQUEST_READY_FOR_OWNER',
        'review_id':uuid.uuid4().hex,'release_hash':canonical_hash(release),'source_pins':code_pins(),
        'reviewer_role':'independent_auditor','limitations_sha256':canonical_hash('AUTHORED_ONLY')}
    return release,review


@contextmanager
def case():
    with tempfile.TemporaryDirectory() as t, account(Path(t).resolve()/'AUTHORED_OS_HOME') as clock:
        oldrelease,oldreview=materials('AUTHORED_OLD')
        original=initialize(oldrelease,oldreview); a=approval(original,oldrelease,oldreview,total=1000)
        epoch=grant(original,a,oldrelease,oldreview)
        proof={'url':'https://openrouter.ai/api/v1/models/openai/gpt-4.1-nano/endpoints',
            'body_sha256':oldrelease['terms']['initial_catalog_sha256'],'observed_at_utc':T0.isoformat(),
            'metadata_semantic_hash':oldrelease['terms']['metadata_semantic_hash']}
        c=make_context(oldrelease,epoch,proof)
        with patch('civiclab.production_owner_v4.uuid.uuid4',return_value=SimpleNamespace(hex=OLD_RECEIPT)):
            oldid=reserve(original,c)
        original.transition(oldid,'UNCERTAIN',error_type='AuthoredTransportFailure')
        owner=_AdditionalOwnerV1.open()
        with owner._lock(),owner._connect() as db: state,head=owner._verify(db)
        old=deepcopy(state['rows'][oldid]); release,_=materials('AUTHORED_ADDITIONAL')
        c=make_context(release,'0'*64,proof); e=c['envelope']
        m={'kind':'ADDITIONAL_COMPATIBILITY_POLICY_V1','owner_id':owner.header['owner_id'],
            'header_hash':canonical_hash(owner.header),'prior_head':head,'prior_active_approval':state['active'],
            'prior_history_hash':canonical_hash(state['_prefix_events']),'predecessor_receipt':oldid,
            'predecessor_row_hash':canonical_hash(old),'predecessor_context_hash':canonical_hash(old['context']),
            'prior_statistics_claims_hash':canonical_hash([]),'release_hash':canonical_hash(release),
            'request_binding_hash':request_binding(c),'new_run_id':c['run_id'],'new_unit_id':c['unit_id'],
            'new_phase':'compatibility','new_module':'E02','new_plan_hash':c['plan_hash'],
            'terms_hash':canonical_hash(c['terms']),'total_microusd':1000,'module_microusd':{'E01':0,'E02':1000},
            'total_dispatches':2,'module_dispatches':{'E01':0,'E02':2},'added_reservation_max':340,
            'valid_from_utc':(T0-timedelta(seconds=1)).isoformat(),
            'valid_until_utc':(T0+timedelta(seconds=300)).isoformat(),
            'assertion':'RETAIN_UNKNOWN_OLD_CHARGE_ONE_ADDITIONAL_DISPATCH'}
        r={'kind':'ADDITIONAL_COMPATIBILITY_REVIEW_V1','reviewer_role':'independent_auditor',
            'policy_hash':canonical_hash(m),'release_hash':canonical_hash(release),
            'code_contract_hash':canonical_hash(code_contract()),'review_id':uuid.uuid4().hex}
        a=approval(original,release,oldreview,total=1000,count=2)
        a.update(review_hash=canonical_hash(r),valid_from_utc=m['valid_from_utc'],valid_until_utc=m['valid_until_utc'])
        o={'kind':'EXTERNAL_ADDITIONAL_COMPATIBILITY_OWNER_ASSERTION_V1','policy_hash':canonical_hash(m),
            'review_hash':canonical_hash(r),'approval_hash':canonical_hash(a),
            'code_contract_hash':r['code_contract_hash'],
            'assertion':'EXPLICITLY_ALLOW_ONE_NEW_REQUEST_WHILE_PRIOR_BILLING_UNKNOWN',
            'credential_state':'OWNER_ASSERTED_ROTATED_DEDICATED_KEY_AND_PREFUNDED'}
        c=make_context(release,canonical_hash(a),proof)
        b={'policy':m,'review':r,'approval':a,'owner_assertion':o,'context':c,'receipt':receipt_for(m,r,o,c)}
        expected={k:canonical_hash(b[k]) for k in ('policy','review','approval','owner_assertion')}
        yield owner,original,b,expected,release,clock,old


def append(owner,b,expected,release,**kwargs):
    return owner.append_authored_batch(b,expected=expected,release=release,
                                      credential_shape_check=kwargs.get('check',lambda:True))


def crash_batch(home, b, x, release, boundary):
    native_connect=sqlite3.connect
    class CrashConnection(sqlite3.Connection):
        insert_count=0
        def execute(self,sql,*args,**kwargs):
            result=super().execute(sql,*args,**kwargs)
            if sql.startswith('INSERT INTO events'):
                self.insert_count+=1
                if boundary=='INSERT_'+str(self.insert_count):os._exit(91)
            if sql.startswith('INSERT INTO charges') and boundary=='CHARGE_INSERT':os._exit(92)
            return result
        def commit(self):
            super().commit()
            if boundary=='COMMIT':os._exit(93)
    from civiclab.additional_compatibility_owner_v1 import atomic_json as native_anchor
    def anchor(path,value):
        native_anchor(path,value)
        if boundary=='ANCHOR':os._exit(94)
    def connect(*args,**kwargs):return native_connect(*args,**kwargs,factory=CrashConnection)
    with account(Path(home)),patch('civiclab.production_owner_v4.sqlite3.connect',side_effect=connect), \
        patch('civiclab.additional_compatibility_owner_v1.atomic_json',side_effect=anchor):
        owner=_AdditionalOwnerV1.open()
        append(owner,b,x,release)
        if boundary=='RETURN_LOST':os._exit(95)


def race_batch(home,b,x,release,gate,queue):
    with account(Path(home)):
        gate.wait(10)
        try:
            owner=_AdditionalOwnerV1.open(); append(owner,b,x,release)
            queue.put('RESERVED')
        except (ExecutionBlocked,ValueError):queue.put('REFUSED')


class AdditionalOwnerTests(unittest.TestCase):
    def test_live_entry_denies_before_touching_any_argument_or_os_home(self):
        class Bomb:
            def __getattribute__(self,name):raise AssertionError('argument touched')
        with patch('civiclab.production_owner_v4.pwd.getpwuid',side_effect=AssertionError('home read')):
            with self.assertRaises(ExecutionBlocked):open_actual(Bomb())

    def test_atomic_four_events_true_two_rows_no_dispatch_capability(self):
        with case() as (owner,original,b,x,release,clock,old):
            before=owner.snapshot(); result=append(owner,b,x,release)
            self.assertIs(result['dispatch_capability'],False)
            after=owner.snapshot()
            self.assertEqual(after['consumed_microusd'],{'total':680,'modules':{'E01':0,'E02':680},
                'dispatches':2,'module_dispatches':{'E01':0,'E02':2}})
            self.assertEqual(next(r for r in after['charges'] if r['id']==OLD_RECEIPT),old)
            with owner._lock(),owner._connect() as db:
                state,head=owner._verify(db)
                self.assertEqual(state['unfinished'],2)
                self.assertEqual(state['additional']['spent'],True)
                self.assertEqual([e['body']['kind'] for e in state['_prefix_events'][-4:]],
                                 [EVENT,'APPROVAL','PRICE_PROOF','RESERVE'])
                self.assertEqual(head['sequence'],b['policy']['prior_head']['sequence']+4)
            with self.assertRaises((ValueError,ExecutionBlocked)):original.snapshot()
            self.assertEqual(len(before['charges']),1)

    def test_third_request_and_original_predecessor_mutation_always_denied_after_success(self):
        with case() as (owner,original,b,x,release,clock,old):
            append(owner,b,x,release); receipt=b['receipt']
            answer,identity=seen(owner,receipt,cost=1);owner.claim_statistics_lookup(receipt)
            settle(owner,receipt,identity,cost=1); owner.commit_phase(receipt,checkpoint(owner,receipt,answer))
            snap=owner.snapshot(); self.assertEqual(snap['consumed_microusd']['total'],341)
            self.assertEqual(snap['consumed_microusd']['dispatches'],2)
            self.assertEqual(next(r for r in snap['charges'] if r['id']==OLD_RECEIPT),old)
            for operation in (lambda:append(owner,b,x,release),lambda:owner.reserve(b['context']),
                              lambda:owner._register_price_proof(b['context']),
                              lambda:owner.transition(OLD_RECEIPT,'RESPONSE_SEEN'),
                              lambda:owner.grant_operator_authorization({},expected_approval_hash='0'*64,
                                      release=release,review={},expected_review_hash='0'*64)):
                with self.assertRaises((ExecutionBlocked,ValueError)):operation()
            self.assertEqual(owner.snapshot(),snap)

    def test_unknown_new_billing_retains_both_holds_and_cannot_retry(self):
        with case() as (owner,original,b,x,release,clock,old):
            append(owner,b,x,release); owner.transition(b['receipt'],'UNCERTAIN',error_type='AuthoredMissingBill')
            self.assertEqual(owner.snapshot()['consumed_microusd']['total'],680)
            with self.assertRaises((ExecutionBlocked,ValueError)):append(owner,b,x,release)
            with self.assertRaises(ExecutionBlocked):owner.claim_statistics_lookup(b['receipt'])

    def test_known_new_overrun_preserved_in_full_old_hold_unchanged(self):
        with case() as (owner,original,b,x,release,clock,old):
            append(owner,b,x,release)
            owner.transition(b['receipt'],'UNCERTAIN',observed_cost=2000,error_type='AuthoredOverrun')
            snap=owner.snapshot(); self.assertEqual(snap['consumed_microusd']['total'],2340)
            self.assertEqual(next(r for r in snap['charges'] if r['id']==OLD_RECEIPT),old)
            with self.assertRaises((ExecutionBlocked,ValueError)):append(owner,b,x,release)

    def test_untrusted_external_hash_and_artifact_drift_refuse_before_credential_or_events(self):
        for key in ('policy','review','approval','owner_assertion'):
            with self.subTest(key=key),case() as (owner,_,b,x,release,clock,old):
                x[key]='0'*64; before=owner.snapshot()
                with self.assertRaises(ExecutionBlocked):append(owner,b,x,release,check=lambda:self.fail('credential'))
                self.assertEqual(owner.snapshot(),before)

    def test_drifted_original_materialized_row_refuses_before_credential(self):
        with case() as (owner,_,b,x,release,clock,old):
            with owner._connect() as db:
                corrupt=deepcopy(old); corrupt['charged']=339
                db.execute('UPDATE charges SET data=? WHERE id=?',(json.dumps(corrupt),OLD_RECEIPT));db.commit()
            with self.assertRaises((ValueError,ExecutionBlocked)):
                append(owner,b,x,release,check=lambda:self.fail('credential'))

    def test_invalid_transport_shape_precommit_keeps_exact_old_snapshot(self):
        with case() as (owner,_,b,x,release,clock,old):
            before=owner.snapshot()
            with self.assertRaises(ExecutionBlocked):append(owner,b,x,release,check=lambda:False)
            self.assertEqual(owner.snapshot(),before)

    def test_expired_lease_rollback_or_clock_unavailable_never_appends(self):
        for seconds in (181,-2,None):
            with self.subTest(seconds=seconds),case() as (owner,_,b,x,release,clock,old):
                before=owner.snapshot()
                clock[0]=RuntimeError('AUTHORED_CLOCK_LOSS') if seconds is None else T0+timedelta(seconds=seconds)
                with self.assertRaises((ExecutionBlocked,ValueError)):append(owner,b,x,release)
                clock[0]=T0; self.assertEqual(owner.snapshot(),before)

    def test_failed_anchor_after_commit_holds_store_and_never_claims_zero(self):
        with case() as (owner,original,b,x,release,clock,old):
            with patch('civiclab.additional_compatibility_owner_v1.atomic_json',side_effect=OSError('AUTHORED_ANCHOR_FAILURE')):
                with self.assertRaises(OSError):append(owner,b,x,release)
            for obj in (owner,original):
                with self.assertRaises((ExecutionBlocked,ValueError)):obj.snapshot()
            with owner._connect() as db:
                rows=[json.loads(data) for data, in db.execute('SELECT data FROM charges')]
                self.assertEqual(len(rows),2); self.assertEqual(sum(r['charged'] for r in rows),680)
                self.assertEqual(next(r for r in rows if r['id']==OLD_RECEIPT),old)

    def test_failure_during_insert_rolls_back_whole_four_event_batch(self):
        with case() as (owner,_,b,x,release,clock,old):
            before=owner.snapshot()
            with owner._connect() as db:
                # Native SQLite trigger fails the final INSERT, after earlier
                # event INSERTs in this transaction have already executed.
                db.execute("CREATE TRIGGER authored_fail_charge BEFORE INSERT ON charges BEGIN SELECT RAISE(ABORT,'AUTHORED'); END")
                db.commit()
            with self.assertRaises(Exception):append(owner,b,x,release)
            self.assertEqual(owner.snapshot(),before)

    def test_new_amendment_replay_explicitly_rejects_rollback_missing_and_outside_lease(self):
        for mode in ('rollback','missing','expired'):
            with self.subTest(mode=mode),case() as (owner,_,b,x,release,clock,old):
                with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
                body=owner._event(EVENT,b,state,new=True)
                if mode=='missing':
                    body.update(recorded_at_utc=None,clock_status='CLOCK_UNAVAILABLE',clock_error='UNAVAILABLE_UTC')
                elif mode=='rollback':
                    body.update(recorded_at_utc=(T0-timedelta(seconds=1)).isoformat(),clock_status='CLOCK_ROLLBACK')
                else:body['recorded_at_utc']=(T0+timedelta(seconds=301)).isoformat()
                with self.assertRaises((ValueError,ExecutionBlocked)):owner._apply(body,state)

    def test_native_process_exit_at_all_insert_commit_anchor_and_return_boundaries(self):
        boundaries=['INSERT_1','INSERT_2','INSERT_3','INSERT_4','CHARGE_INSERT','COMMIT','ANCHOR','RETURN_LOST']
        ctx=multiprocessing.get_context('spawn')
        for boundary in boundaries:
            with self.subTest(boundary=boundary),case() as (owner,original,b,x,release,clock,old):
                before=owner.snapshot()
                # Pass the mocked OS home directly rather than reconstructing a
                # platform-dependent directory-parent depth.
                from civiclab.production_owner_v4 import pwd
                child=ctx.Process(target=crash_batch,args=(pwd.getpwuid(os.getuid()).pw_dir,b,x,release,boundary))
                child.start();child.join(15)
                if child.is_alive():child.kill();child.join();self.fail('authored child exceeded bound')
                self.assertIn(child.exitcode,(91,92,93,94,95))
                if boundary.startswith('INSERT') or boundary=='CHARGE_INSERT':
                    self.assertEqual(owner.snapshot(),before)
                elif boundary=='COMMIT':
                    with self.assertRaises(ExecutionBlocked):owner.snapshot()
                    with owner._connect() as db:
                        rows=[json.loads(data) for data, in db.execute('SELECT data FROM charges')]
                        self.assertEqual(len(rows),2);self.assertEqual(sum(r['charged'] for r in rows),680)
                else:
                    snap=owner.snapshot();self.assertEqual(snap['consumed_microusd']['dispatches'],2)
                    self.assertEqual(snap['consumed_microusd']['total'],680)
                    self.assertEqual(next(r for r in snap['charges'] if r['id']==OLD_RECEIPT),old)
                    with self.assertRaises(ExecutionBlocked):append(owner,b,x,release)

    def test_two_native_processes_same_owner_different_callers_one_batch_only(self):
        with case() as (owner,original,b,x,release,clock,old):
            from civiclab.production_owner_v4 import pwd
            home=pwd.getpwuid(os.getuid()).pw_dir
            ctx=multiprocessing.get_context('spawn');gate=ctx.Event();queue=ctx.Queue()
            children=[ctx.Process(target=race_batch,args=(home,b,x,release,gate,queue)) for _ in range(2)]
            for child in children:child.start()
            gate.set()
            for child in children:
                child.join(15)
                if child.is_alive():child.kill();child.join();self.fail('race child exceeded bound')
                self.assertEqual(child.exitcode,0)
            self.assertEqual(sorted([queue.get(timeout=2),queue.get(timeout=2)]),['REFUSED','RESERVED'])
            snap=owner.snapshot();self.assertEqual(snap['consumed_microusd']['dispatches'],2)
            self.assertEqual(len(snap['charges']),2)
            self.assertEqual(next(r for r in snap['charges'] if r['id']==OLD_RECEIPT),old)


if __name__=='__main__':unittest.main()
