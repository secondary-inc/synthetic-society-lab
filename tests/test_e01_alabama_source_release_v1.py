"""Authored conditional-release fixtures. No actual PDF/render/private reads."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab import common
from civiclab.e01 import alabama_source_release_v1 as a
from civiclab.e01 import alabama_recorded_preflight_v1 as w
from tests.test_e01_alabama_documents_v1 import fixture as pure_fixture, bind_json, save_inputs, identities

REPO = Path(__file__).resolve().parents[1]


def encoded(x): return a.pure.canonical(x)


def fixed_hash(base, keys): return a.pure.digest(encoded({k:base[k] for k in keys}))


def fixture(root):
    runtime, transcript = pure_fixture(root)
    runtime['scope']='RELEASED_LOCAL_AL_DOCUMENT_RECONCILIATION_ONLY'
    base=copy.deepcopy(runtime);base['scope']='PENDING_INDEPENDENT_CODE_REVIEW_NO_ACTUAL_EXECUTION'
    base['actual_execution_release']={k:False if k=='approved' else None for k in base['actual_execution_release']}
    base['transcription']={k:None for k in base['transcription']}
    base['independent_transcription_audit']={k:None for k in base['independent_transcription_audit']}
    base['release_documents']=[{k:r['role'] if k=='role' else None for k in r} for r in base['release_documents']]
    cfg=json.loads((REPO/a.CONFIG).read_text())
    base_path=cfg['base_runtime']['path'];(root/base_path).parent.mkdir(parents=True,exist_ok=True)
    (root/base_path).write_bytes(encoded(base));cfg['base_runtime']['sha256']=a.pure.digest(encoded(base))
    for p in cfg['metadata_pins']:
        if p==base_path:cfg['metadata_pins'][p]=a.pure.digest(encoded(base));continue
        q=root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((REPO/p).read_bytes())
    cfg['fixed_policy_sha256']=fixed_hash(base,cfg['fixed_policy_keys'])
    cfg['source_snapshot_sha256']=a.pure.source_snapshot_sha(base)
    (root/a.CONFIG).write_bytes(encoded(cfg));cfg_sha=a.pure.digest(encoded(cfg))
    for p in a.CODE_PATHS:
        q=root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((REPO/p).read_bytes())
    code={p:a.pure.digest((root/p).read_bytes()) for p in a.CODE_PATHS}
    review={'status':'PASS_BOUNDED_AL_SOURCE_RELEASE_ADAPTER_WRAPPER_CODE_PRIVACY',
            'scope':'AUTHORED_CODE_PRIVACY_ONLY_NOT_ACTUAL_SOURCE_RELEASE',
            'reviewed_code_pins':code,'source_policy_sha256':cfg['fixed_policy_sha256'],
            'source_snapshot_sha256':cfg['source_snapshot_sha256']}
    review_ref=bind_json(root,'data/processed/e01_al_authored/adapter_code_review.local.json',review)
    source={'schema_version':1,'mode':'SOURCE_TRANSCRIPTION_ONLY','execution_kind':'AUTHORED_FIXTURE',
            'root_sha256':a.pure.digest(str(root).encode()),'source_policy_sha256':cfg['fixed_policy_sha256'],
            'source_snapshot_sha256':cfg['source_snapshot_sha256'],'admission_config_sha256':cfg_sha,
            'code_pins':code,'code_review':review_ref,'output_scope':'data/processed/runs',
            'visual_pages':cfg['visual_pages'],'source_release':None,'runtime':None,'phase_limit':{'source_only':1}}
    source_raw=encoded(source);source_ref=bind_json(root,'data/processed/e01_al_authored/source_release.local.json',source)
    runtime_ref=bind_json(root,'data/processed/e01_al_authored/released_runtime.local.json',runtime)
    outer={**copy.deepcopy(source),'mode':'AUDITED_RUNTIME','source_release':source_ref,'runtime':runtime_ref,
           'phase_limit':{'primary':1,'replay':1}}
    return {'cfg':cfg,'cfg_sha':cfg_sha,'base':base,'runtime':runtime,'transcript':transcript,
            'source':source,'source_raw':source_raw,'source_sha':a.pure.digest(source_raw),
            'outer':outer,'outer_raw':encoded(outer),'outer_sha':a.pure.digest(encoded(outer))}


def runtime(root, f):
    stack=ExitStack()
    stack.enter_context(patch.object(a,'CONFIG_SHA',f['cfg_sha']))
    for module,path in [(a,a.ADAPTER),(a.pure,a.PURE),(w,a.WRAPPER),(common,a.COMMON)]:
        stack.enter_context(patch.object(module,'__file__',str(root/path)))
    return stack


def reseal_runtime(root,f):
    ref=bind_json(root,f['outer']['runtime']['path'],f['runtime'])
    f['outer']['runtime']=ref;f['outer_raw']=encoded(f['outer']);f['outer_sha']=a.pure.digest(f['outer_raw'])


class ConditionalAdmissionFixtures(unittest.TestCase):
    def test_absent_wrong_or_coedited_external_bytes_deny_before_root_or_metadata_IO(self):
        for raw,expected in [(None,'0'*64),(b'{}','0'*64),(b'{}',None)]:
            with patch.object(a,'_root') as root,patch.object(a.pure,'bound_file') as read,self.assertRaises(a.pure.DocumentsRejected):
                a.read_released('/unused',raw,expected_sha=expected)
            root.assert_not_called();read.assert_not_called()
        with tempfile.TemporaryDirectory() as td:
            r=Path(td).resolve();f=fixture(r);changed=copy.deepcopy(f['source']);changed['output_scope']='data/raw'
            with runtime(r,f),patch.object(a,'_root') as root,self.assertRaises(a.pure.DocumentsRejected):
                a.read_released(r,encoded(changed),expected_sha=f['source_sha'])
            root.assert_not_called()

    def test_source_only_positive_needs_no_transcript_audit_runtime_or_grants_and_is_no_write(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td).resolve();f=fixture(r)
            for ref in [f['runtime']['transcription'],f['runtime']['independent_transcription_audit'],*f['runtime']['release_documents'],f['outer']['runtime']]:
                (r/ref['path']).unlink()
            before=identities(r)
            with runtime(r,f):result=a.read_released(r,f['source_raw'],expected_sha=f['source_sha'])
            self.assertEqual(before,identities(r));private=result.private_payload();public=result.public_diagnostics()
            self.assertEqual(len(private['allowed_images']),11);self.assertIsNone(private['literal_transcription'])
            self.assertIsNone(private['independent_literal_audit']);self.assertFalse(public['transcription_created'])
            self.assertFalse(public['literal_audit_completed']);self.assertNotIn('DEMO ÉLISE',json.dumps(public,ensure_ascii=False))

    def test_audited_nonnull_runtime_positive_exact_replay_no_old_constant_patch_or_write(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td).resolve();f=fixture(r);before=identities(r);old_sha=a.pure.CONTRACT_SHA
            with runtime(r,f):
                one=a.read_released(r,f['outer_raw'],expected_sha=f['outer_sha'])
                two=a.read_released(r,f['outer_raw'],expected_sha=f['outer_sha'])
                with self.assertRaises(a.pure.DocumentsRejected):a.pure.read_sources(r,f['runtime'])
            self.assertEqual(old_sha,a.pure.CONTRACT_SHA);self.assertEqual(before,identities(r))
            self.assertEqual(one.private_payload(),two.private_payload());self.assertEqual(one.public_diagnostics(),two.public_diagnostics())
            self.assertEqual(len(one.private_payload()['occurrences']),6)
            self.assertEqual(len(one.private_payload()['exclusions_by_page_role']),41)
            self.assertEqual(one.public_diagnostics()['document_supported_name_group_count'],2)
            self.assertNotIn('DEMO',repr(one));self.assertNotIn('DEMO ÉLISE',json.dumps(one.public_diagnostics(),ensure_ascii=False))
            changed=one.private_payload();changed['occurrences'].clear();self.assertEqual(len(one.private_payload()['occurrences']),6)

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
                    source=copy.deepcopy(f['source']);source['mode']='AUDITED_RUNTIME';outer['source_release']=bind_json(r,outer['source_release']['path'],source)
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
        for mode in ['source','outer']:
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
                r=Path(td).resolve();f=fixture(r);original=a.pure._reconcile
                def altered(*args):
                    result=original(*args)
                    if kind=='runtime':p=r/f['outer']['runtime']['path']
                    elif kind=='prior':p=r/f['outer']['source_release']['path']
                    elif kind=='code':p=r/a.ADAPTER
                    else:p=r/f['runtime']['transcription' if kind=='transcript' else 'independent_transcription_audit']['path']
                    p.write_bytes(p.read_bytes()+b'ALTERED');return result
                with runtime(r,f),patch.object(a.pure,'_reconcile',side_effect=altered),self.assertRaises(a.pure.DocumentsRejected):a.read_released(r,f['outer_raw'],expected_sha=f['outer_sha'])

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
                with runtime(r,f),patch.object(a.pure,'_reconcile',side_effect=error('DEMO PRIVATE')),self.assertRaises(expected) as cm:a.read_released(r,f['outer_raw'],expected_sha=f['outer_sha'])
                self.assertEqual(before,identities(r));self.assertNotIn('DEMO',str(cm.exception));self.assertIsNone(cm.exception.__context__)
