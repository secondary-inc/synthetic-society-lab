"""Authored recording/privacy/commit fixtures; no actual source execution."""
from contextlib import ExitStack
import errno
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab.common import sha256_file
from civiclab.reproduction import build_package
from civiclab.dashboard import verified_run
from tests.test_e01_alabama_office_context_v1_1 import fixture, runtime, identities, encoded, a, w


def parents(root):
    folder=root/'data/processed/runs'
    return set(p for p in folder.iterdir() if p.is_dir()) if folder.exists() else set()


def controls(root,expected):return root/'data/processed/e01_al_release_controls'/expected


class ALContextRecordedPreflightFixtures(unittest.TestCase):
    def test_invalid_metadata_or_phase_before_any_control_RunStore_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);before=identities(root)
            with runtime(root,f),patch.object(w.RunStore,'__init__') as store,patch.object(a,'_materialize') as source:
                for raw,expected,phase in [(b'{}',f['outer_sha'],'source_only'),(f['outer_raw'],f['outer_sha'],'source_only')]:
                    with self.assertRaises(a.pure.DocumentsRejected):w.record(root,raw,expected_sha=expected,phase=phase)
                store.assert_not_called();source.assert_not_called()
            self.assertEqual(before,identities(root))

    def test_no_new_source_only_phase_and_old_grant_no_new_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);before=parents(root)
            with runtime(root,f),patch.object(w.RunStore,'__init__') as store:
                for raw,expected,phase in [(f['legacy']['source_raw'],f['legacy']['source_sha'],'source_only'),
                    (f['outer_raw'],f['outer_sha'],'source_only')]:
                    with self.assertRaises(a.pure.DocumentsRejected):w.record(root,raw,expected_sha=expected,phase=phase)
                store.assert_not_called()
            self.assertEqual(before,parents(root))

    def test_audited_primary_replay_two_parents_exact_data_and_readonly_consumer_no_PDF_image_IO(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);before=parents(root)
            with runtime(root,f):
                one=w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                two=w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='replay')
                for phase in ['primary','replay']:
                    with self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase=phase)
                original=a.pure.bound_file
                def bound(root,path,*args,**kw):
                    if path.startswith('data/raw/'):raise AssertionError('NO_SAVED_CONSUMER_SOURCE_IO')
                    return original(root,path,*args,**kw)
                with patch.object(a.pure,'bound_file',side_effect=bound):
                    public=w.read_verified(one,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])
                    w.read_verified(two,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])
            self.assertEqual(parents(root)-before,{one,two})
            for name in [w.PRIVATE,w.PUBLIC]:self.assertEqual((one/name).read_bytes(),(two/name).read_bytes())
            payload=json.loads((one/w.PRIVATE).read_text())['payload']
            self.assertEqual(len(payload['occurrences']),6);self.assertEqual(len(payload['exclusions_by_page_role']),41)
            self.assertEqual(len(payload['typed_unknowns']),4);self.assertEqual(public['execution_kind'],'AUTHORED_FIXTURE')
            self.assertNotIn('DEMO ÉLISE',json.dumps(public,ensure_ascii=False));self.assertNotIn('DEMO ÉLISE',json.dumps(verified_run(one),ensure_ascii=False))
            for p in [one,two]:
                with self.assertRaisesRegex(ValueError,'local-only'):build_package(root,root/(p.name+'.zip'),[p.name])
                self.assertFalse((root/(p.name+'.zip')).exists())

    def assert_failed(self,root,f,before):
        created=parents(root)-before;self.assertEqual(len(created),1);p=created.pop()
        self.assertTrue((p/'failure.json').exists());self.assertFalse((p/'al_release.json').exists() and not (p/'al_terminal_failure.local.json').exists())
        with runtime(root,f),self.assertRaises(a.pure.DocumentsRejected):w.read_verified(p,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])
        if (p/'al_failure_checksums.local.json').exists():
            ledger=json.loads((p/'al_failure_checksums.local.json').read_text())
            self.assertTrue(all(sha256_file(p/n)==h for n,h in ledger.items()))
        else:
            ledger=json.loads((p/'checksums.json').read_text());self.assertTrue(all(sha256_file(p/n)==h for n,h in ledger.items()))
            self.assertEqual(json.loads((p/'summary.json').read_text())['status'],'FAILED')
        for n in ['failure.json','summary.json','events.jsonl','al_terminal_failure.local.json']:
            if (p/n).exists():self.assertNotIn('PRIVATE_ERROR', (p/n).read_text())
        self.assertFalse((controls(root,f['outer_sha'])/'primary.completed.local.json').exists())
        return p

    def test_constructor_payload_hash_commit_summary_ledger_seal_before_after_failures_retained(self):
        targets=['manifest.json','environment.json',*w.DATA,'al_payload_hashes.json','al_commit.json','summary.json','checksums.json','al_release.json']
        for target in targets:
            for after in [False,True]:
                with tempfile.TemporaryDirectory() as td:
                    root=Path(td).resolve();f=fixture(root);before=parents(root);original=w.RunStore.write;fired=[False]
                    def write(run,name,value):
                        if name==target and not fired[0]:
                            fired[0]=True
                            if after:original(run,name,value)
                            raise OSError('PRIVATE_ERROR')
                        return original(run,name,value)
                    with runtime(root,f),patch.object(w.RunStore,'write',new=write),self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                    self.assertTrue(fired[0]);self.assert_failed(root,f,before)

    def test_parse_hash_cancel_SystemExit_keep_failed_parent_and_replay_gate(self):
        for error in [ValueError,KeyboardInterrupt,SystemExit]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root);before=parents(root)
                expected=error if error in [KeyboardInterrupt,SystemExit] else a.pure.DocumentsRejected
                with runtime(root,f),patch.object(a.context,'_reconcile',side_effect=error('PRIVATE_ERROR')),self.assertRaises(expected) as cm:w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                self.assertNotIn('PRIVATE_ERROR',str(cm.exception));self.assertIsNone(cm.exception.__context__)
                self.assert_failed(root,f,before)
                with runtime(root,f),patch.object(w.RunStore,'__init__') as store,self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='replay')
                store.assert_not_called()

    def test_final_rechecks_after_payload_and_finish_drift_invalidate_no_commit(self):
        for position in [3,4]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root);before=parents(root);original=a.recheck;count=[0]
                # read_released invokesone recheck; wrapperpostpayload issecond,
                # postfinish third. Prepare injected stage at2/3 respectively.
                target=position-1
                def check(*args,**kw):
                    count[0]+=1
                    if count[0]==target:raise RuntimeError('PRIVATE_ERROR')
                    return original(*args,**kw)
                with runtime(root,f),patch.object(a,'recheck',side_effect=check),self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                self.assertEqual(count[0],target);p=self.assert_failed(root,f,before)
                self.assertTrue((p/w.PRIVATE).exists());self.assertFalse((p/'al_release.json').exists())

    def test_postseal_persist_then_error_readonly_can_retain_valid_commit_no_autoretry(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);before=parents(root);original=w.RunStore.write;originalevent=w.RunStore.event;persisted=[False]
            def write(run,name,value):
                if persisted[0]:raise OSError(errno.EROFS,'PRIVATE_ERROR')
                out=original(run,name,value)
                if name=='al_release.json':persisted[0]=True;raise OSError(errno.EIO,'PRIVATE_ERROR')
                return out
            def event(run,kind,**kw):
                if persisted[0]:raise OSError(errno.EROFS,'PRIVATE_ERROR')
                return originalevent(run,kind,**kw)
            def control_write(path,value):
                if persisted[0]:raise OSError(errno.EROFS,'PRIVATE_ERROR')
                with path.open('x') as stream:json.dump(value,stream)
            with runtime(root,f),patch.object(w.RunStore,'write',new=write),patch.object(w.RunStore,'event',new=event),patch.object(w,'_write_once',side_effect=control_write),self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
            created=parents(root)-before;self.assertEqual(len(created),1);p=created.pop()
            self.assertTrue((p/'al_release.json').exists());self.assertFalse((p/'failure.json').exists())
            with runtime(root,f):
                w.read_verified(p,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])
                with self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                with self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='replay')
            self.assertEqual(len(parents(root)-before),1)

    def test_persistent_early_storage_failure_never_seals_or_claims_durable_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);before=parents(root)
            with runtime(root,f),patch.object(w.RunStore,'write',side_effect=OSError('PRIVATE_ERROR')),self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
            created=parents(root)-before;self.assertEqual(len(created),1);p=created.pop();self.assertFalse((p/'al_release.json').exists())
            with runtime(root,f),self.assertRaises(a.pure.DocumentsRejected):w.read_verified(p,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])

    def test_resealed_saved_private_public_manifest_and_extra_files_refused(self):
        for mode in ['private','public','manifest','extra','directory','unknown_schema']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root)
                with runtime(root,f):p=w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                if mode=='extra':(p/'extra.local.json').write_text('{}')
                elif mode=='directory':
                    q=p/'extra_directory';q.mkdir();(q/'private.local.json').write_text('{}')
                else:
                    name=w.PRIVATE if mode=='private' else ('manifest.json' if mode=='manifest' else w.PUBLIC)
                    data=json.loads((p/name).read_text())
                    if mode=='private':data['payload']['occurrences'][0]['official_name_literal']='DEMO RESEALED'
                    elif mode=='manifest':data['config']['phase']='source_only'
                    elif mode=='unknown_schema':data['schema_version']=3
                    else:data['payload']['candidate_names']='DEMO RESEALED'
                    (p/name).write_bytes(encoded(data))
                    if name in w.DATA:
                        ph=json.loads((p/'al_payload_hashes.json').read_text());ph[name]=sha256_file(p/name);(p/'al_payload_hashes.json').write_bytes(encoded(ph))
                    ledger=json.loads((p/'checksums.json').read_text());ledger[name]=sha256_file(p/name)
                    if name in w.DATA:ledger['al_payload_hashes.json']=sha256_file(p/'al_payload_hashes.json')
                    (p/'checksums.json').write_bytes(encoded(ledger));seal=json.loads((p/'al_release.json').read_text());seal['checksums_sha256']=sha256_file(p/'checksums.json');(p/'al_release.json').write_bytes(encoded(seal))
                with runtime(root,f),self.assertRaises(a.pure.DocumentsRejected):w.read_verified(p,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])

    def test_control_ack_tamper_missing_seal_and_symlink_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root)
            with runtime(root,f):p=w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
            ack=controls(root,f['outer_sha'])/'primary.completed.local.json';data=json.loads(ack.read_text());data['seal_sha256']='0'*64;ack.write_bytes(encoded(data))
            with runtime(root,f),patch.object(w.RunStore,'__init__') as store,self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='replay')
            store.assert_not_called();(p/'al_release.json').unlink()
            with runtime(root,f),self.assertRaises(a.pure.DocumentsRejected):w.read_verified(p,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);outside=root/'elsewhere';outside.mkdir();q=root/'data/processed/runs';q.rename(root/'saved_history');q.symlink_to(outside)
            with runtime(root,f),patch.object(w.RunStore,'__init__') as store,self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
            store.assert_not_called();self.assertFalse(list(outside.iterdir()))

    def test_saved_consumer_rechecks_grant_and_metadata_drift_without_PDF_or_image_IO(self):
        for mode in ['grant','metadata']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root)
                with runtime(root,f):p=w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                relative=f['runtime']['release_documents'][0]['path'] if mode=='grant' else next(iter(f['runtime']['metadata_pins']))
                changed=root/relative;changed.write_bytes(changed.read_bytes()+b'ALTERED')
                original=a.pure.bound_file
                def read(root,path,*args,**kw):
                    if path.startswith('data/raw/'):raise AssertionError('NO_SAVED_SOURCE_IO')
                    return original(root,path,*args,**kw)
                with runtime(root,f),patch.object(a.pure,'bound_file',side_effect=read),self.assertRaises(a.pure.DocumentsRejected):w.read_verified(p,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])

    def test_four_source_passes_coedited_alias_first_middle_last_failure_retained(self):
        for position in [0,25,51,52,77,103,104,129,155,156,181,207]:
            with self.subTest(position=position),tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root);before=parents(root);original=a.pure.bound_file;count=[0]
                def read(r,path,*args,**kw):
                    if path.startswith('data/raw/'):
                        if count[0]==position:
                            # Caller aliases and hashes change together, while admitted
                            # external raw bytes and config remain fixed.
                            for s in f['runtime']['sources']:
                                q=root/s['path'];q.write_bytes(q.read_bytes()+b'ALTERED');s['sha256']=sha256_file(q)
                            for p in f['runtime']['pages']:
                                q=root/p['render_path'];q.write_bytes(q.read_bytes()+b'ALTERED');p['render_sha256']=sha256_file(q)
                            f['outer']['source_snapshot_sha256']='0'*64
                        count[0]+=1
                    return original(r,path,*args,**kw)
                with runtime(root,f),patch.object(a.pure,'bound_file',side_effect=read),self.assertRaises(a.pure.DocumentsRejected):
                    w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                self.assertEqual(count[0],position+1);self.assert_failed(root,f,before)

    def test_control_ack_persisted_then_error_is_not_silent_retry_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);before=parents(root);original=w._write_once
            def write(path,value):
                out=original(path,value)
                if path.name=='primary.completed.local.json':raise OSError('PRIVATE_ERROR')
                return out
            with runtime(root,f),patch.object(w,'_write_once',side_effect=write),self.assertRaises(a.pure.DocumentsRejected):
                w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
            created=parents(root)-before;self.assertEqual(len(created),1);p=created.pop()
            self.assertTrue((p/'al_release.json').exists());self.assertTrue((p/'al_terminal_failure.local.json').exists())
            with runtime(root,f):
                with self.assertRaises(a.pure.DocumentsRejected):w.read_verified(p,root=root,raw=f['outer_raw'],expected_sha=f['outer_sha'])
                with self.assertRaises(a.pure.DocumentsRejected):w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='replay')
