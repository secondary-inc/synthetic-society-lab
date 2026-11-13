"""Real local fsync/flock on authored temporary control records; no source/backend."""
import copy
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from civiclab.e01 import clerk2020_native_campaign_v2 as n


class NativeCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        lock=self.root/n.PREDECESSOR_REGISTRY/'registrar.lock';lock.parent.mkdir(parents=True);lock.write_bytes(b'')
        self.store=n.FixedStore(self.root);self.reg=n.FixedRegistrar(self.store,n.sha(b'AUTHORED_SOURCE_SET'))
        # These persistence-only tests isolate registry IO; full predecessor
        # validation uses real authored records in source_job_v2 tests.
        self.proof_patch=patch.object(n.FixedRegistrar,'_verify_predecessor_locked',return_value=n.sha(b'MOCK_PREDECESSOR_PROOF'))
        self.proof_patch.start()
    def tearDown(self):self.proof_patch.stop();self.temp.cleanup()
    def adopt(self,reg,store,h):
        store.read_meter=n.ClosingReadMeter()
        reg.adopt_successor(h)
        store.read_meter=None
    def issued(self,phase='BOOT',anchor=None):
        obj={'kind':'CLERK_SOURCE_ISSUED_V2_1','phase':phase,'ordinal':1,'binding':self.reg.binding(),
             'decision_sha256':n.sha(b'AUTHORED_DECISION'),'expected_anchor_sha256':anchor,
             'one_shot':True,'prefix_budget':n.PREFIX_BUDGETS[phase]}
        raw=n.canonical(obj);return raw,n.sha(raw)
    def bootstrap(self):
        raw,h=self.issued();self.reg.consume('BOOT',raw,h)
        self.adopt(self.reg,self.store,h)
        a0=self.reg.cas(None,'anchor_initial',{'genesis_sha256':n.sha(b'AUTHORED_GENESIS')})
        a1=self.reg.cas(a0['sha256'],'anchor_boot',{'receipt_sha256':n.sha(b'AUTHORED_RECEIPT')})
        return a1['sha256']

    def test_layout_ceilings_are_intersections_not_extra_global_allowance(self):
        totals={k:sum(v[1] for v in n.LAYOUT.values() if v[2]==k) for k in ['data','control','staging']}
        self.assertEqual(totals,{'data':262144,'control':125952,'staging':131072})
        self.assertLessEqual(sum(totals.values()),524288)
        self.assertEqual(sum(v[1] for v in n.LAYOUT.values() if v[3]=='BOOT'),24576)
        self.assertEqual(sum(v[1] for v in n.LAYOUT.values() if v[3]=='EXEC'),24576)

    def test_wrong_envelope_has_zero_control_effects(self):
        raw,h=self.issued()
        with self.assertRaises(n.Refused):self.reg.consume('BOOT',raw,'f'*64)
        self.assertFalse(self.store.exists('boot_reservation'))
        self.assertFalse(self.store.exists('source_index'))

    def test_boot_reservation_and_registration_are_create_once(self):
        raw,h=self.issued();self.reg.consume('BOOT',raw,h)
        with self.assertRaises(FileExistsError):self.reg.consume('BOOT',raw,h)
        reservation,_=self.store.read('boot_reservation',2049)
        self.assertFalse(n.decode(reservation)['source_access_before_admission'])
        self.assertEqual(n.decode(reservation)['precharged_prefix'],n.PREFIX_BUDGETS['BOOT'])
        self.assertFalse(self.store.exists('source_index'));self.assertFalse(self.store.exists('registration'))
        self.adopt(self.reg,self.store,h)
        self.assertEqual(self.store.path('registration').stat().st_mode&0o777,0o600)
        with self.assertRaises(n.Refused):self.adopt(self.reg,self.store,h)

    def test_crossed_root_or_source_set_refused_before_new_state(self):
        raw,_=self.issued();obj=n.decode(raw)
        for key,value in [('repository_root_sha256','f'*64),('source_set_sha256','f'*64),('campaign_id','OTHER')]:
            bad=copy.deepcopy(obj);bad['binding'][key]=value;b=n.canonical(bad)
            with self.assertRaises(n.Refused):self.reg.consume('BOOT',b,n.sha(b))
        self.assertFalse(self.store.exists('boot_reservation'))

    def test_prefix_budget_tamper_or_ordinal_boolean_refused(self):
        raw,_=self.issued();obj=n.decode(raw)
        for key,value in [('ordinal',True),('prefix_budget',dict(n.PREFIX_BUDGETS['BOOT'],source_jobs=1))]:
            bad=copy.deepcopy(obj);bad[key]=value;b=n.canonical(bad)
            with self.assertRaises(n.Refused):self.reg.consume('BOOT',b,n.sha(b))

    def test_anchor_cas_and_exec_ordinal(self):
        a1=self.bootstrap();raw,h=self.issued('EXEC',a1)
        self.reg.consume('EXEC',raw,h)
        a2=self.reg.cas(a1,'anchor_active',{'context_sha256':n.sha(b'AUTHORED_CONTEXT')})
        self.assertEqual(self.reg.current()[0],a2['sha256'])
        with self.assertRaises(n.Refused):self.reg.cas(a1,'prefix_anchor',{})
        with self.assertRaises(FileExistsError):self.reg.consume('EXEC',raw,h)

    def test_noncontiguous_anchor_chain_is_not_current(self):
        raw,h=self.issued();self.reg.consume('BOOT',raw,h)
        a0=self.reg.cas(None,'anchor_initial',{})
        obj={'kind':'CLERK_SOURCE_ANCHOR_V2_1','binding':self.reg.binding(),'state':'anchor_active',
             'previous_anchor_sha256':a0['sha256'],'payload':{}}
        self.store.create('anchor_active',n.canonical(obj))
        with self.assertRaises(n.Refused):self.reg.current()

    def test_concurrent_boot_one_owner(self):
        raw,h=self.issued();outcomes=[]
        def run():
            try:self.reg.consume('BOOT',raw,h);outcomes.append('WON')
            except FileExistsError:outcomes.append('CONSUMED')
        threads=[threading.Thread(target=run) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertCountEqual(outcomes,['WON','CONSUMED'])

    def test_prewrite_crash_no_source_or_new_ordinal(self):
        def crash(event):
            if event=='registration.before':raise RuntimeError('AUTHORED_CRASH')
        store=n.FixedStore(self.root,crash);reg=n.FixedRegistrar(store,n.sha(b'AUTHORED_SOURCE_SET'))
        raw,h=self.issued()
        reg.consume('BOOT',raw,h)
        with self.assertRaises(RuntimeError):self.adopt(reg,store,h)
        self.assertTrue(store.exists('boot_reservation'))
        with self.assertRaises(FileExistsError):reg.consume('BOOT',raw,h)

    def test_postwrite_lost_ack_preserves_bytes_and_consumed_slot(self):
        def crash(event):
            if event=='boot_reservation.after':raise RuntimeError('AUTHORED_LOST_ACK')
        store=n.FixedStore(self.root,crash);reg=n.FixedRegistrar(store,n.sha(b'AUTHORED_SOURCE_SET'))
        raw,h=self.issued()
        with self.assertRaises(RuntimeError):reg.consume('BOOT',raw,h)
        b,_=store.read('boot_reservation',2049)
        with self.assertRaises(FileExistsError):self.reg.consume('BOOT',raw,h)
        self.assertEqual(store.read('boot_reservation',2049)[0],b)

    def test_store_slots_alias_oversize_and_unknown_refused(self):
        with self.assertRaises(n.Refused):self.store.create('UNLISTED',b'X')
        with self.assertRaises(n.Refused):self.store.create('registration',b'X'*2049)
        target=self.root/'AUTHORED_TARGET';target.write_bytes(b'MOCK')
        p=self.store.path('registration');p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(target)
        with self.assertRaises(n.Refused):self.store.read('registration',2049)

    def test_normal_journal_freezes_and_caps(self):
        self.store.create('normal_journal',b'')
        self.store.bind_run('e01-'+'a'*32)
        self.store.append_event(b'{"label":"MOCK"}\n')
        self.store.create('sealed_prefix',b'AUTHORED_SEALED_PREFIX')
        with self.assertRaises(n.Refused):self.store.append_event(b'{"label":"MOCK"}\n')

    def test_counter_restore_carries_legacy_and_warmup_state(self):
        c=n.PersistentCounters();c.precharge_writes();c.activate_source()
        c.reserve({'code_integrity_read_bytes':100,'warmup_backend_attempts':4,
                   'total_backend_attempts':5},'EXEC')
        c.settle('code_integrity_read_bytes',100,80,'EXEC')
        c.settle('warmup_backend_attempts',4,4,'EXEC')
        before=n.canonical(c.snapshot());other=n.PersistentCounters.restore(n.decode(before))
        self.assertEqual(n.canonical(other.snapshot()),before)
        self.assertEqual(other.snapshot()['engineering_axes']['warmup_backend_attempts']['charged'],4)
        self.assertEqual(other.snapshot()['legacy_axes']['owned_write_bytes']['charged'],524288)

    def test_counter_transaction_refusal_is_atomic(self):
        c=n.PersistentCounters();before=n.canonical(c.snapshot())
        with self.assertRaises(n.Refused):c.reserve({'source_read_attempts':1,'warmup_backend_attempts':9},'EXEC')
        self.assertEqual(n.canonical(c.snapshot()),before)

    def test_partition_exhaustion_and_source_no_refund(self):
        c=n.PersistentCounters();c.activate_source();c.reserve({'code_integrity_read_bytes':268435456},'BOOT')
        with self.assertRaises(n.Refused):c.reserve({'code_integrity_read_bytes':1},'BOOT')
        c.reserve({'source_jobs':1,'source_read_attempts':1,'source_read_bytes':602173,
                   'backend_attempts':1,'page_extractions':81,'warmup_backend_attempts':4,
                   'warmup_page_extractions':119,'total_backend_attempts':5,'total_page_extractions':200},'EXEC')
        c.stop_unknown();s=c.snapshot()
        for axis,cap in [('source_read_attempts',2),('source_read_bytes',859913),('page_extractions',119)]:
            self.assertEqual(s['legacy_axes'][axis]['charged'],cap)
            self.assertIsNone(s['legacy_axes'][axis]['observed'])
        self.assertEqual(s['engineering_axes']['total_page_extractions']['charged'],357)
        with self.assertRaises(n.Refused):c.reserve({'source_read_attempts':1},'EXEC')
        n.PersistentCounters.restore(s)

    def test_snapshot_cannot_alias_current_counter_state(self):
        c=n.PersistentCounters();snapshot=c.snapshot();snapshot['phase_reserved']['BOOT']['cpu_ms']=7
        self.assertEqual(c.snapshot()['phase_reserved']['BOOT']['cpu_ms'],0)

    def test_tampered_counter_phase_totals_and_axes_refuse(self):
        c=n.PersistentCounters();c.reserve({'code_integrity_read_bytes':10},'BOOT')
        c.settle('code_integrity_read_bytes',10,10,'BOOT');snapshot=c.snapshot()
        for edit in ['phase','ceiling','warmup']:
            bad=copy.deepcopy(snapshot)
            if edit=='phase':bad['phase_observed']['BOOT']['code_integrity_read_bytes']=0
            elif edit=='ceiling':bad['legacy_axes']['source_read_attempts']['ceiling']=3
            else:bad['engineering_axes']['warmup_backend_attempts']['ceiling']=9
            with self.assertRaises(n.Refused):n.PersistentCounters.restore(bad)

    def terminal_fixture(self, crash=None):
        if crash is not None:self.store.crash=crash
        a1=self.bootstrap();raw,h=self.issued('EXEC',a1);self.reg.consume('EXEC',raw,h)
        self.store.bind_run('e01-'+'a'*32)
        self.reg.cas(a1,'anchor_active',{'context_sha256':n.sha(b'AUTHORED_CONTEXT')})
        c=n.PersistentCounters();c.precharge_writes()
        self.store.create('normal_journal',b'')
        genesis=n.sha(b'AUTHORED_GENESIS')
        journal=n.NativeJournal(self.store,genesis,c)
        journal.append('BOOT','BOOT_RESERVE',{'reservation_token_sha256':n.sha(b'AUTHORED_BOOT_TOKEN')},
                       reserve={'bootstrap_attempts':1},settle=[['bootstrap_attempts',1,1]])
        journal.append('EXEC','EXEC_ADMISSION',{'context_sha256':n.sha(b'AUTHORED_CONTEXT'),
            'reservation_token_sha256':n.sha(b'AUTHORED_EXEC_TOKEN')},activate_source=True,
            reserve={'execution_admission_attempts':1,'source_jobs':1},
            settle=[['execution_admission_attempts',1,1],['source_jobs',1,1]])
        terminal=n.NativeTerminal(self.store,self.reg,journal,n.sha(b'AUTHORED_CONTEXT'))
        payloads={name:n.canonical({'label':'MOCK','fixture':'AUTHORED_TERMINAL_ONLY'})
                  for name in n.LEDGER_MAP if name not in {'events.jsonl','counters.prefix.local.json'}}
        bindings={key:n.sha(('AUTHORED_'+key).encode()) for key in ['registration_sha256','static_spec_sha256',
            'genesis_sha256','execution_decision_sha256','issued_envelope_sha256']}
        return terminal,payloads,bindings,genesis,c

    def test_journal_replay_and_counter_digest(self):
        terminal,payloads,bindings,genesis,initial=self.terminal_fixture()
        replay=n.NativeJournal(self.store,genesis,n.PersistentCounters.restore(initial.snapshot()),terminal.journal.prefix)
        self.assertEqual(replay.head,terminal.journal.head)
        self.assertEqual(replay.counters.snapshot(),terminal.journal.counters.snapshot())
        tampered=terminal.journal.prefix.replace(b'BOOT_RESERVE',b'EXEC_ADMIT__')
        with self.assertRaises(n.Refused):n.NativeJournal(self.store,genesis,initial,tampered)

    def test_authored_terminal_serializes_verifies_and_freezes_exact_prefix(self):
        terminal,payloads,bindings,genesis,initial=self.terminal_fixture()
        result=terminal.finalize(payloads,bindings)
        self.assertEqual(result['status'],'WRITER_COMMITTED_AWAITING_CALLER_OBSERVATION')
        seal_raw,_=self.store.read('seal',4097);seal=n.decode(seal_raw,4096)
        self.assertLessEqual(len(seal_raw),4096)
        events,_=self.store.read('normal_journal',49153)
        commit,_=self.store.read('commit_event',1025)
        full,_=self.store.read('sealed_prefix',49153)
        self.assertEqual(events+commit,full)
        self.assertEqual(n.sha(events),seal['prefix_ledger']['events.jsonl'])
        self.assertEqual(n.sha(full),seal['sealed_prefix_ref']['sha256'])
        self.assertEqual(self.reg.current()[0],result['completed_anchor_ref']['sha256'])
        with self.assertRaises(n.Refused):self.store.append_event(b'{}\n')
        with self.assertRaises(n.Refused):terminal.finalize(payloads,bindings)

    def test_terminal_crashes_preserve_slots_without_rerun(self):
        events=['private_projection.before','sealed_prefix.after','seal.after','verification.before',
                'tail_verify.after','writer_ack.after','tail_ack.after','anchor_complete.after']
        for target in events:
            with self.subTest(target=target),tempfile.TemporaryDirectory() as folder:
                old_store,old_reg=self.store,self.reg
                lock=Path(folder).resolve()/n.PREDECESSOR_REGISTRY/'registrar.lock';lock.parent.mkdir(parents=True);lock.write_bytes(b'')
                self.store=n.FixedStore(Path(folder).resolve())
                self.reg=n.FixedRegistrar(self.store,n.sha(b'AUTHORED_SOURCE_SET'))
                terminal,payloads,bindings,_,_=self.terminal_fixture()
                def crash(event):
                    if event==target:raise RuntimeError('AUTHORED_CRASH')
                self.store.crash=crash
                with self.assertRaises(RuntimeError):terminal.finalize(payloads,bindings)
                before={k:self.store.read(k,n.LAYOUT[k][1]+1)[0] for k in n.LAYOUT if self.store.exists(k)}
                with self.assertRaises(n.Refused):terminal.finalize(payloads,bindings)
                after={k:self.store.read(k,n.LAYOUT[k][1]+1)[0] for k in before}
                self.assertEqual(before,after)
                self.store,self.reg=old_store,old_reg

    def test_full_private_slot_serialization_fits_and_is_verified(self):
        terminal,payloads,bindings,_,_=self.terminal_fixture()
        def padded(size):
            obj={'label':'MOCK','fixture':'AUTHORED_MAX_SLOT','a':'A'*min(120000,max(0,size-100)), 'b':''}
            raw=n.canonical(obj)
            self.assertLessEqual(len(raw),size)
            obj['b']='B'*(size-len(raw));result=n.canonical(obj)
            self.assertEqual(len(result),size);return result
        payloads['inspection_projection.local.json']=padded(251904)
        payloads['inspection_diagnostics.json']=padded(8192)
        payloads['inspection_provenance.local.json']=padded(2048)
        result=terminal.finalize(payloads,bindings)
        self.assertEqual(result['status'],'WRITER_COMMITTED_AWAITING_CALLER_OBSERVATION')
        self.assertLessEqual(self.store.path('seal').stat().st_size,4096)
        self.assertLessEqual(terminal.verified_bytes,2097152)

    def test_boot_failure_does_not_invent_a_source_attempt_or_warmup(self):
        counters=n.PersistentCounters();counters.precharge_writes();counters.stop_unknown()
        snapshot=counters.snapshot()
        for axis in ['source_jobs','source_read_attempts','source_read_bytes','backend_attempts','page_extractions']:
            self.assertEqual(snapshot['legacy_axes'][axis]['charged'],0)
        self.assertEqual(snapshot['engineering_axes']['warmup_backend_attempts']['charged'],0)
        n.PersistentCounters.restore(snapshot)



if __name__=='__main__':unittest.main()
