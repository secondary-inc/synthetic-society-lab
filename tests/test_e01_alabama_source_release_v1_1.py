"""Ported v1 negative controls against separate v1.1; authored inputs only."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_e01_alabama_office_context_v1_1 import fixture, runtime, reseal_runtime, identities, encoded, save_inputs, bind_json, a


class ContextAdmissionFixtures(unittest.TestCase):
    def test_null_runtime_or_policy_unknowns_and_extra_source_admission_not_relabelled(self):
        for mode in ['null','unknown','extra_source','extra_key','scope','role','limits']:
            with tempfile.TemporaryDirectory() as td:
                r=Path(td).resolve();f=fixture(r)
                if mode=='null':f['runtime']['actual_execution_release']['approved']=False
                elif mode=='unknown':f['runtime']['unknowns']['legal_nominee']=True
                elif mode=='extra_source':f['runtime']['sources'].append(copy.deepcopy(f['runtime']['sources'][0]))
                elif mode=='extra_key':f['runtime']['caller_permission']=True
                elif mode=='scope':f['runtime']['scope']='PROSPECTIVE_FORECAST'
                elif mode=='role':f['runtime']['occurrence_slots'][1]['historical']=False
                else:f['runtime']['limits']['max_source_pdf_bytes_each']=99999999
                reseal_runtime(r,f)
                with runtime(r,f),patch.object(a.pure,'verify_inputs') as source,self.assertRaises(a.pure.DocumentsRejected):
                    a.read_released(r,f['outer_raw'],expected_sha=f['outer_sha'])
                source.assert_not_called()

    def test_wrong_phase_output_root_code_review_and_self_declared_hash_refused(self):
        for mode in ['phase','output','root','review','code','extra','schema','prior_grant_mode']:
            with tempfile.TemporaryDirectory() as td:
                r=Path(td).resolve();f=fixture(r);outer=f['outer']
                if mode=='phase':outer['phase_limit']['primary']=True
                elif mode=='output':outer['output_scope']='data/raw'
                elif mode=='root':outer['root_sha256']='0'*64
                elif mode=='review':
                    ref=outer['code_review'];data=json.loads((r/ref['path']).read_text());data['reviewed_code_pins'][a.ADAPTER]='0'*64
                    outer['code_review']=bind_json(r,ref['path'],data)
                elif mode=='code':outer['code_pins'][a.ADAPTER]='0'*64
                elif mode=='extra':outer['self_approved_sha256']='0'*64
                elif mode=='schema':outer['schema_version']=True
                else:
                    source=copy.deepcopy(f['legacy']['source']);source['mode']='AUDITED_RUNTIME';outer['source_release']=bind_json(r,outer['source_release']['path'],source)
                raw=encoded(outer)
                with runtime(r,f),self.assertRaises(a.pure.DocumentsRejected):a.read_released(r,raw,expected_sha=a.pure.digest(raw))

    def test_metadata_and_release_ref_symlinks_paths_and_bounds_refused(self):
        for mode in ['runtime_symlink','review_traversal','runtime_oversize','source_grant_path','origin']:
            with tempfile.TemporaryDirectory() as td:
                r=Path(td).resolve();f=fixture(r)
                if mode=='runtime_symlink':
                    p=r/f['outer']['runtime']['path'];p.rename(p.with_suffix('.other'));p.symlink_to(p.with_suffix('.other').name)
                elif mode=='review_traversal':f['outer']['code_review']['path']='../private'
                elif mode=='runtime_oversize':f['outer']['runtime']['bytes']=262145
                elif mode=='source_grant_path':f['outer']['source_release']['path']='data/raw/forbidden.json'
                raw=encoded(f['outer'])
                with runtime(r,f),ExitStack() as stack:
                    if mode=='origin':stack.enter_context(patch.object(a,'__file__','/foreign/release.py'))
                    with self.assertRaises(a.pure.DocumentsRejected):a.read_released(r,raw,expected_sha=a.pure.digest(raw))

    def test_first_middle_last_bothpass_cache_coedit_refuses_original_authority(self):
        for mode in ['outer']:
            for position in [0,5,25,51,52,103]:
                with tempfile.TemporaryDirectory() as td:
                    r=Path(td).resolve();f=fixture(r);raw=f[mode+'_raw'];expected=f[mode+'_sha'];count=[0];original=a.pure.bound_file
                    def read(root,path,*args,**kw):
                        if path.startswith('data/raw/'):
                            if count[0]==position:
                                for s in f['base']['sources']:
                                    q=r/s['path'];q.write_bytes(q.read_bytes()+b'ALTERED');s['sha256']=a.pure.digest(q.read_bytes())
                                for p in f['base']['pages']:
                                    q=r/p['render_path'];q.write_bytes(q.read_bytes()+b'ALTERED');p['render_sha256']=a.pure.digest(q.read_bytes())
                                f[mode]['source_snapshot_sha256']='0'*64
                            count[0]+=1
                        return original(root,path,*args,**kw)
                    with runtime(r,f),patch.object(a.pure,'bound_file',side_effect=read),self.assertRaises(a.pure.DocumentsRejected):a.read_released(r,raw,expected_sha=expected)
                    self.assertEqual(count[0],position+1)

    def test_between_pass_runtime_priorgrant_code_transcript_audit_drift_rejected(self):
        for kind in ['runtime','prior','code','transcript','audit']:
            with tempfile.TemporaryDirectory() as td:
                r=Path(td).resolve();f=fixture(r);original=a.context._reconcile
                def altered(*args):
                    result=original(*args)
                    if kind=='runtime':p=r/f['outer']['runtime']['path']
                    elif kind=='prior':p=r/f['outer']['source_release']['path']
                    elif kind=='code':p=r/a.ADAPTER
                    else:p=r/f['runtime']['transcription' if kind=='transcript' else 'independent_transcription_audit']['path']
                    p.write_bytes(p.read_bytes()+b'ALTERED');return result
                with runtime(r,f),patch.object(a.context,'_reconcile',side_effect=altered),self.assertRaises(a.pure.DocumentsRejected):a.read_released(r,f['outer_raw'],expected_sha=f['outer_sha'])

    def test_resealed_literal_history_office_disagreement_and_privacy_still_checked(self):
        for mode in ['name','history','office','contact']:
            with tempfile.TemporaryDirectory() as td:
                r=Path(td).resolve();f=fixture(r);record=f['transcript']['occurrences'][1]
                if mode=='name':record['official_name_literal']='DEMO DIFFERENT';record['name_utf8_sha256']=a.pure.digest(record['official_name_literal'].encode())
                elif mode=='history':record['historical']=False
                elif mode=='office':record['office_label_literal']='Governor';record['office_utf8_sha256']=a.pure.digest(b'Governor')
                else:record['contact']='DEMO PRIVATE'
                save_inputs(r,f['runtime'],f['transcript']);reseal_runtime(r,f)
                with runtime(r,f),self.assertRaises(a.pure.DocumentsRejected):a.read_released(r,f['outer_raw'],expected_sha=f['outer_sha'])

    def test_parser_cancel_systemexit_no_write_message_or_partial_result(self):
        for error in [RuntimeError,KeyboardInterrupt,SystemExit]:
            with tempfile.TemporaryDirectory() as td:
                r=Path(td).resolve();f=fixture(r);before=identities(r)
                expected=error if error in [KeyboardInterrupt,SystemExit] else a.pure.DocumentsRejected
                with runtime(r,f),patch.object(a.context,'_reconcile',side_effect=error('DEMO PRIVATE')),self.assertRaises(expected) as cm:a.read_released(r,f['outer_raw'],expected_sha=f['outer_sha'])
                self.assertEqual(before,identities(r));self.assertNotIn('DEMO',str(cm.exception));self.assertIsNone(cm.exception.__context__)
