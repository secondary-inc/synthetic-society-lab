"""Authored continuation states and transports; no actual owner/key/network."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.e02 import exploratory_continuation_v1 as c
from civiclab.e02.exploratory_sequence_v1 import next_action
from civiclab.production_compatibility_transport_v4_2 import _SafeTransportFailure
from test_e02_exploratory_live_client_v1 import recovery_client_case,FakeOwner,FakeTransport,PROTOCOL
from test_additional_compatibility_owner_v1 import materials


def authored_prefix(terms):
    rows=[]
    for _ in range(16):
        request=next_action(PROTOCOL,terms,canonical_bytes(rows))['request']
        rows.append({'execution_order':request['execution_order'],'phase':request['phase'],
            'payload_sha256':request['payload_sha256'],'status':'ANSWER',
            'answer':{'democratic_party':50,'republican_party':50}})
    return rows


class ContinuationFixtureOwner(FakeOwner):
    """Finite accounting oracle; actual successor grammar is independently owned."""
    def __init__(self,directory,packet,prefix):
        super().__init__(directory,packet)
        self.transcript=deepcopy(prefix);self.old_hold=2136;self.started=False;self.billing_verified=True
        self.inherited_rows=[{'id':f'{1000+i:032x}','status':'UNCERTAIN' if i in (0,1,17) else 'PHASE_COMMITTED',
            'reserved':340 if i<2 else 788 if i==17 else 44,
            'charged':340 if i<2 else 788 if i==17 else 52 if i==16 else 44} for i in range(18)]
        self.original=deepcopy(self.inherited_rows)
        self.global_limit=5000000;self.study_limit=1000000;self.dispatch_limit=34
        self.corrupt_ancestor=False;self.extra_reserved=False
    def start_continuation(self,bundle,proof,*,expected_bundle_hash):
        if self.started or not self.billing_verified:raise ExecutionBlocked('recovery absent or start consumed')
        if bundle['ancestor_sha256']!=canonical_hash(self.transcript):raise ExecutionBlocked('ancestor binding differs')
        self.started=True
    def snapshot(self):return {'charges':deepcopy(self.inherited_rows+list(self.rows.values()))}
    def study_snapshot(self):
        result=super().study_snapshot();result['study_dispatches']=16+len(self.rows)
        if self.started and result['status']=='NOT_STARTED':result['status']='ACTIVE'
        result['consumed_microusd']['dispatches']=18+len(self.rows)
        result['study_charged_microusd']+=1456
        if self.corrupt_ancestor and self.rows:result['transcript'][0]['answer']['democratic_party']=99
        return result
    def reserve_next(self,*args,**kwargs):
        request=next_action(PROTOCOL,self.packet['price_release']['terms'],canonical_bytes(self.transcript))
        if request['status']=='REQUEST_READY_NOT_ADMITTED':
            reserved=request['request']['envelope']['reserved_microusd']
            charged=sum(r['charged'] for r in self.rows.values())
            if (len(self.rows)>=16 or 18+len(self.rows)+1>self.dispatch_limit or
                2136+charged+reserved>self.global_limit or 1456+charged+reserved>self.study_limit):
                raise ExecutionBlocked('cumulative request or spending cap reached')
        ack=super().reserve_next(*args,**kwargs)
        if self.extra_reserved and ack['status']=='RESERVED':ack['request']['execution_order']=0
        return ack


@contextmanager
def continuation_case():
    with recovery_client_case() as (values,sleep):
        p,oldowner,oldt,fetch,key,mono,clock,_=values
        p['policy']['run_id']='AUTHORED-CONTINUATION-V1'
        prefix=authored_prefix(p['price_release']['terms'])
        owner=ContinuationFixtureOwner(oldowner.directory,p,prefix)
        transport=FakeTransport(owner);transport.stats_hook=oldt.stats_hook
        bundle={'kind':'AUTHORED_CONTINUATION_ONLY','packet':p,'ancestor_sha256':canonical_hash(prefix)}
        with patch.object(c,'_owner',return_value=owner), \
             patch.object(c,'_validate_bundle',side_effect=lambda b,**kw:deepcopy(b)), \
             patch.object(c,'_transport',return_value=transport):
            yield bundle,owner,transport,fetch,key,mono,clock,sleep


def execute(bundle):return c.execute_continuation(bundle,expected_bundle_hash=canonical_hash(bundle))


class PureContinuationTests(unittest.TestCase):
    def test_exact_first_unattempted_slot_and_ancestor_binding(self):
        terms=materials('AUTHORED_PREFIX')[0]['terms'];prefix=authored_prefix(terms)
        out=c.continuation_next(PROTOCOL,terms,canonical_bytes(prefix),b'[]',expected_ancestor_sha256=canonical_hash(prefix))
        self.assertEqual((out['request']['execution_order'],out['request']['phase']),(8,'pre'))
        self.assertEqual(out['continuation_ancestry']['inherited_response_phases'],16)
        self.assertIn('separate',out['continuation_ancestry']['temporal_gap'])
        with self.assertRaises(ExecutionBlocked):c.continuation_next(PROTOCOL,terms,canonical_bytes(prefix),b'[]',expected_ancestor_sha256='0'*64)
    def test_unreconciled_sixteenth_or_ancestor_replay_or_foreign_unit_refused(self):
        terms=materials('AUTHORED_PREFIX')[0]['terms'];prefix=authored_prefix(terms)
        bad=deepcopy(prefix);bad[-1].update(status='FAILED_UNCERTAIN',answer=None)
        with self.assertRaises(ExecutionBlocked):c.continuation_next(PROTOCOL,terms,canonical_bytes(bad),b'[]',expected_ancestor_sha256=canonical_hash(bad))
        for tail in [[prefix[-1]],[{**prefix[0],'execution_order':True}],[{**prefix[0],'execution_order':16}]]:
            with self.assertRaises(ExecutionBlocked):c.continuation_next(PROTOCOL,terms,canonical_bytes(prefix),canonical_bytes(tail),expected_ancestor_sha256=canonical_hash(prefix))
    def test_changed_saved_answer_and_request_hash_not_accepted(self):
        terms=materials('AUTHORED_PREFIX')[0]['terms'];prefix=authored_prefix(terms)
        bad=deepcopy(prefix);bad[0]['answer']['democratic_party']=51
        with self.assertRaises(ExecutionBlocked):c.continuation_next(PROTOCOL,terms,canonical_bytes(bad),b'[]',expected_ancestor_sha256=canonical_hash(bad))


class ClientContinuationTests(unittest.TestCase):
    def test_success_sixteen_new_posts_no_ancestor_replays_and_full_analysis(self):
        with continuation_case() as (b,o,t,fetch,key,mono,clock,sleep):
            out=execute(b)
            self.assertEqual((t.posts,t.gets),(16,16));fetch.assert_called_once();key.assert_called_once()
            self.assertEqual(len(o.transcript),32);self.assertEqual(o.inherited_rows,o.original)
            self.assertEqual(len(o.rows),16);self.assertEqual(out['analysis']['complete_blocks'],8)
            self.assertEqual(out['analysis']['estimate_thermometer_points'],0)
            self.assertEqual(out['snapshot']['consumed_microusd']['dispatches'],34)
            self.assertEqual(out['snapshot']['consumed_microusd']['total'],2152)
            self.assertEqual(out['continuation_ancestry']['original_run_status'],'PARTIAL_STOPPED_BILLING_404_NO_RETRY')
            self.assertEqual(mono[0],160)
            requests=[json.loads(f.read_bytes())['request'] for f in Path(out['path']).glob('*-request.json')]
            self.assertEqual({r['execution_order'] for r in requests},set(range(8,16)))
    def test_primary_replay_authored_answers_and_analysis_match(self):
        outputs=[]
        for _ in range(2):
            with continuation_case() as (b,*_):outputs.append(execute(b))
        self.assertEqual(outputs[0]['response_envelope'],outputs[1]['response_envelope'])
        self.assertEqual(outputs[0]['analysis'],outputs[1]['analysis'])
    def test_three_gets_per_generation_are_only_404_recovery_not_repeated_posts(self):
        with continuation_case() as (b,o,t,fetch,key,mono,clock,sleep):
            native=t.statistics;counts={}
            def stats(identity):
                counts[identity]=counts.get(identity,0)+1
                if counts[identity]<3:
                    t.gets+=1
                    raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
                return native(identity)
            t.statistics=stats;out=execute(b)
            self.assertEqual((t.posts,t.gets),(16,48));self.assertEqual(len(o.claims),16)
            self.assertEqual(out['statistics_GET_attempts'],48);self.assertEqual(mono[0],640)
            self.assertTrue(all(v==3 for v in counts.values()))
            directory=Path(out['path']);self.assertEqual(len(list(directory.glob('*-statistics-*-intent.json'))),48)
            self.assertLess(len(list(directory.iterdir())),256)
    def test_third_404_stops_at_one_post_full_hold_and_keeps_ancestor(self):
        with continuation_case() as (b,o,t,*_):
            def stats(identity):t.gets+=1;raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
            t.statistics=stats
            with self.assertRaises(ExecutionBlocked):execute(b)
            self.assertEqual((t.posts,t.gets),(1,3));self.assertEqual(o.inherited_rows,o.original)
            row=next(iter(o.rows.values()));self.assertEqual(row['status'],'UNCERTAIN');self.assertEqual(row['charged'],row['reserved'])
            failure=json.loads((o.directory/'limited-pilot-v1'/b['packet']['policy']['run_id']/'failure.json').read_bytes())
            self.assertEqual(failure['statistics_GET_attempts'],3)
            self.assertEqual(len(failure['authenticated_terminal']['response_envelope']['records']),32)
    def test_non404_or_close_failure_never_retried(self):
        for error in [_SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',429),_SafeTransportFailure('OPEN','TIMEOUT'),
                      _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404,True),ValueError('authored')]:
            with self.subTest(error=type(error).__name__),continuation_case() as (b,o,t,*_):
                def stats(identity):t.gets+=1;raise error
                t.statistics=stats
                with self.assertRaises(ExecutionBlocked):execute(b)
                self.assertEqual((t.posts,t.gets),(1,1))
    def test_exhausted_phase_time_prevents_late_retry_and_keeps_hold(self):
        with continuation_case() as (b,o,t,fetch,key,mono,*_):
            def stats(identity):
                t.gets+=1;mono[0]+=65
                raise _SafeTransportFailure('HTTP_STATUS','HTTP_STATUS',404)
            t.statistics=stats
            with self.assertRaises(ExecutionBlocked):execute(b)
            self.assertEqual((t.posts,t.gets),(1,1));self.assertEqual(next(iter(o.rows.values()))['status'],'UNCERTAIN')
    def test_cancel_during_initial_wait_has_no_get_and_no_replacement(self):
        with continuation_case() as (b,o,t,fetch,key,mono,clock,sleep):
            sleep.side_effect=KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):execute(b)
            self.assertEqual((t.posts,t.gets),(1,0));self.assertEqual(len(o.claims),1)
    def test_recovery_missing_cumulative_money_counts_and_historical_mutation_stop(self):
        for mode in ('no_reconciled_bill','global','study','count','ancestor','duplicate_ack'):
            with self.subTest(mode=mode),continuation_case() as (b,o,t,*_):
                if mode=='no_reconciled_bill':o.billing_verified=False
                elif mode=='global':o.global_limit=2136
                elif mode=='study':o.study_limit=1456
                elif mode=='count':o.dispatch_limit=18
                elif mode=='ancestor':o.corrupt_ancestor=True
                else:o.extra_reserved=True
                with self.assertRaises(ExecutionBlocked):execute(b)
                self.assertEqual(t.posts,1 if mode=='ancestor' else 0)
                self.assertEqual(o.inherited_rows,o.original)
    def test_approval_or_existing_journal_cannot_be_replayed(self):
        with continuation_case() as (b,o,t,fetch,key,*_):
            with self.assertRaises(ExecutionBlocked):c.execute_continuation(b,expected_bundle_hash='0'*64)
            fetch.assert_not_called();key.assert_not_called()
            out=execute(b)
            with self.assertRaises(FileExistsError):execute(b)
            self.assertEqual(t.posts,16)
    def test_closed_transport_failure_type_cannot_supply_arbitrary_diagnostic(self):
        class ForeignFailure(_SafeTransportFailure):
            def diagnostic(self):raise AssertionError('foreign diagnostic must not be called')
        with continuation_case() as (b,o,t,*_):
            def stats(identity):t.gets+=1;raise ForeignFailure('HTTP_STATUS','HTTP_STATUS',404)
            t.statistics=stats
            with self.assertRaises(ExecutionBlocked):execute(b)
            self.assertEqual((t.posts,t.gets),(1,1))
    def test_response_identity_privacy_and_overrun_failures_do_not_poll(self):
        for mode in ('model','secret','overrun'):
            with self.subTest(mode=mode),continuation_case() as (b,o,t,*_):
                if mode=='model':t.post_hook=lambda r,q:r.update(model='foreign/model')
                elif mode=='secret':t.post_hook=lambda r,q:r.update(secret='AUTHORED_CREDENTIAL_NO_ACTUAL_ACCESS')
                else:t.post_hook=lambda r,q:r['usage'].update(cost='0.01')
                with self.assertRaises(ExecutionBlocked):execute(b)
                self.assertEqual((t.posts,t.gets),(1,0))
                self.assertEqual(o.inherited_rows,o.original)
                row=next(iter(o.rows.values()));self.assertEqual(row['status'],'UNCERTAIN')
                if mode=='overrun':self.assertEqual(row['charged'],10000)
    def test_new_invalid_pre_skips_own_post_without_replacing_old_data(self):
        with continuation_case() as (b,o,t,*_):
            t.post_hook=lambda r,q:r['choices'][0]['message'].update(content='{}') if t.posts==1 else None
            out=execute(b)
            self.assertEqual((t.posts,t.gets),(15,15))
            records=out['response_envelope']['records']
            self.assertEqual(records[17]['status'],'SKIPPED_INVALID_PRE')
            self.assertEqual(o.inherited_rows,o.original)
    def test_old_journal_contents_are_never_modified(self):
        with continuation_case() as (b,o,t,*_):
            old=o.directory/'limited-pilot-v1'/'AUTHORED-ORIGINAL-STOPPED'
            old.mkdir(parents=True);payload=b'preserved stopped run evidence'
            (old/'failure.json').write_bytes(payload);before=hashlib.sha256(payload).hexdigest()
            execute(b)
            self.assertEqual(hashlib.sha256((old/'failure.json').read_bytes()).hexdigest(),before)
    def test_actual_factory_denied_without_owner_or_transport(self):
        with patch.object(c,'_owner',side_effect=AssertionError('owner')):
            with self.assertRaises(ExecutionBlocked):c.open_actual(object())


if __name__=='__main__':unittest.main()
