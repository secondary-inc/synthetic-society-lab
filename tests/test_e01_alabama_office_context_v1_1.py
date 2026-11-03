"""Authored fixtures only; actual source/transcript/run bodies are never opened."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civiclab.e01 import alabama_office_context_v1_1 as h
from civiclab.e01 import alabama_source_release_v1_1 as a
from civiclab.e01 import alabama_recorded_preflight_v1_1 as w
from tests.test_e01_alabama_source_release_v1 import (
    fixture as legacy_fixture, runtime as legacy_runtime, bind_json, save_inputs,
    identities, encoded, REPO, a as legacy, w as legacy_writer)


def fixture(root):
    """Rebase authority ONLY inside a temporary authored-data root."""
    old=legacy_fixture(root)
    with legacy_runtime(root,old):
        parent=legacy_writer.record(root,old['source_raw'],expected_sha=old['source_sha'],phase='source_only')
    runtime=old['runtime'];transcript=old['transcript']
    for row,label in zip(transcript['occurrences'],['United States Senator','US Senate','United States Senator','U.S. Senate','United States Senator','U.S. Senate']):
        row['office_label_literal']=label;row['office_utf8_sha256']=h.old.digest(label.encode())
    save_inputs(root,runtime,transcript)
    cfg=json.loads((REPO/a.CONFIG).read_text())
    # Public code and metadata only, never copy any real private input.
    for p in cfg['metadata_pins']:
        if p in old['cfg']['metadata_pins'] or p==legacy.CONFIG:continue
        q=root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((REPO/p).read_bytes())
    cfg['metadata_pins']={p:h.old.digest((root/p).read_bytes()) for p in cfg['metadata_pins']}
    cfg.update(base_runtime=copy.deepcopy(old['cfg']['base_runtime']),fixed_policy_sha256=old['cfg']['fixed_policy_sha256'],source_snapshot_sha256=old['cfg']['source_snapshot_sha256'])
    cfg['transcript_ref']=copy.deepcopy(runtime['transcription'])
    cfg['accepted_literal_audit_ref']=copy.deepcopy(runtime['independent_transcription_audit'])
    audit_raw=(root/runtime['independent_transcription_audit']['path']).read_bytes()
    audit_path=cfg['runtime_audit_copy_area']+'/literal_audit.local.json'
    (root/audit_path).parent.mkdir(parents=True,exist_ok=True);(root/audit_path).write_bytes(audit_raw)
    runtime['independent_transcription_audit']={**runtime['independent_transcription_audit'],'path':audit_path}
    rule=json.loads((REPO/cfg['rule_ref']['path']).read_text())
    rule.update(fixed_source_policy_sha256=cfg['fixed_policy_sha256'],source_snapshot_sha256=cfg['source_snapshot_sha256'],source_transcript_sha256=runtime['transcription']['sha256'])
    for spec,row in zip(rule['permitted_rows'],transcript['occurrences']):
        for k in ['source_id','source_sha256','physical_pdf_page_1_based','render_sha256','record_role','party_context','historical','date_evidence']:spec[k]=copy.deepcopy(row[k])
        spec.update(source_record_canonical_sha256=h.old.digest(encoded(row)),source_name_utf8_sha256=row['name_utf8_sha256'],expected_office_literal=row['office_label_literal'],expected_office_utf8_sha256=row['office_utf8_sha256'])
    cfg['rule_ref']=bind_json(root,cfg['rule_ref']['path'],rule);cfg['rule_canonical_sha256']=h.old.digest(encoded(rule))
    controls=root/'data/processed/e01_al_release_controls'/old['source_sha']
    cfg['historical_source_only']={'manifest_ref':copy.deepcopy(old['outer']['source_release']),
        'run_id':parent.name,'ledger_sha256':h.old.digest((parent/'checksums.json').read_bytes()),
        'seal_sha256':h.old.digest((parent/'al_release.json').read_bytes()),'code_pins':old['source']['code_pins'],
        'control_hashes':{n:h.old.digest((controls/n).read_bytes()) for n in ['source_only.started.local.json','source_only.completed.local.json']}}
    for p in a.CODE_PATHS:
        if p in legacy.CODE_PATHS:continue
        q=root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((REPO/p).read_bytes())
    code={p:h.old.digest((root/p).read_bytes()) for p in a.CODE_PATHS}
    review={'status':'PASS_BOUNDED_AL_OFFICE_CONTEXT_V1_1_CODE_PRIVACY','scope':'AUTHORED_CODE_PRIVACY_ONLY_NOT_ACTUAL_SOURCE_RELEASE',
        'reviewed_code_pins':code,'source_policy_sha256':cfg['fixed_policy_sha256'],'source_snapshot_sha256':cfg['source_snapshot_sha256']}
    ref=bind_json(root,'data/processed/e01_al_authored/new_code_review.local.json',review)
    outer={**copy.deepcopy(old['outer']),'mode':'AUDITED_RUNTIME_OFFICE_CONTEXT_V1_1','code_review':ref,'code_pins':code,
        'office_rule':cfg['rule_ref'],'runtime':bind_json(root,old['outer']['runtime']['path'],runtime)}
    cfg_ref=bind_json(root,a.CONFIG,cfg);outer['admission_config_sha256']=cfg_ref['sha256']
    return {'base':old['base'],'legacy':old,'cfg':cfg,'cfg_sha':cfg_ref['sha256'],'runtime':runtime,'transcript':transcript,'rule':rule,
        'outer':outer,'outer_raw':encoded(outer),'outer_sha':h.old.digest(encoded(outer)),'historical_parent':parent}


def runtime(root,f):
    stack=ExitStack();stack.enter_context(legacy_runtime(root,f['legacy']))
    stack.enter_context(patch.object(a,'CONFIG_SHA',f['cfg_sha']))
    stack.enter_context(patch.object(h,'RULE_SHA',f['cfg']['rule_canonical_sha256']))
    for module,path in [(a,a.ADAPTER),(h,a.HELPER),(w,a.WRAPPER)]:stack.enter_context(patch.object(module,'__file__',str(root/path)))
    return stack


def reseal_runtime(root,f):
    f['outer']['runtime']=bind_json(root,f['outer']['runtime']['path'],f['runtime'])
    f['outer_raw']=encoded(f['outer']);f['outer_sha']=h.old.digest(f['outer_raw'])


class ExactContextFixtures(unittest.TestCase):
    def test_matched_strict_control_raw_objects_bytes_unknowns_and_detachment(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);before=identities(root)
            audit=json.loads((root/f['runtime']['independent_transcription_audit']['path']).read_bytes())
            with runtime(root,f):
                with self.assertRaises(h.old.DocumentsRejected):h.old.safe(lambda:h.old._reconcile(f['runtime'],f['transcript'],audit))
                out=a.read_released(root,f['outer_raw'],expected_sha=f['outer_sha'])
                with self.assertRaises(h.old.DocumentsRejected):h.old.safe(lambda:h.old.validate_public(out.public_diagnostics()))
                with self.assertRaises(h.old.DocumentsRejected):h.old.read_sources(root,f['runtime'])
            self.assertEqual(before,identities(root));p=out.private_payload()
            self.assertEqual(encoded(p['occurrences']),encoded(f['transcript']['occurrences']))
            self.assertEqual(p['source_record_canonical_sha256'],[h.old.digest(encoded(x)) for x in f['transcript']['occurrences']])
            self.assertEqual(len(p['derived_office_contexts']),6);self.assertEqual(len(p['exclusions_by_page_role']),41)
            self.assertEqual(len(p['typed_unknowns']),4);self.assertEqual(len(p['reconciled_document_entries']),2)
            self.assertEqual(out.public_diagnostics()['office_literal_form_count'],3)
            p['occurrences'].clear();self.assertEqual(len(out.private_payload()['occurrences']),6)
            self.assertNotIn('DEMO',repr(out));self.assertNotIn('DEMO',json.dumps(out.public_diagnostics()))

    def test_exact_external_bytes_and_no_new_review_deny_before_source_or_store(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root)
            for mode in ['external','old_review','no_review','old_mode','extra','rule']:
                outer=copy.deepcopy(f['outer'])
                if mode=='old_review':outer['code_review']=f['legacy']['source']['code_review']
                elif mode=='no_review':outer['code_review']=None
                elif mode=='old_mode':outer['mode']='AUDITED_RUNTIME'
                elif mode=='extra':outer['extra']='DENY'
                elif mode=='rule':outer['office_rule']['sha256']='0'*64
                raw=encoded(outer);expected=f['outer_sha'] if mode=='external' else h.old.digest(raw)
                if mode=='external':raw+=b' '
                with runtime(root,f),patch.object(a,'_materialize') as source,patch.object(w.RunStore,'__init__') as store,self.assertRaises(h.old.DocumentsRejected):
                    w.record(root,raw,expected_sha=expected,phase='primary')
                source.assert_not_called();store.assert_not_called()

    def test_coedited_transcript_audit_runtime_refused_by_fixed_six_witnesses(self):
        modes=['name','office','case','punctuation','role','party','date','historical','page','source','hash','extra','missing','order','numeric','UNKNOWN','unicode']
        for mode in modes:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root);row=f['transcript']['occurrences'][1]
                if mode in ['name','unicode']:row['official_name_literal']='DEMO ALTERED' if mode=='name' else 'DEMO E\u0301LISE O’NEILL'
                elif mode in ['office','case','punctuation']:row['office_label_literal']={'office':'Governor','case':'us Senate','punctuation':'U.S. Senate'}[mode]
                elif mode=='role':row['record_role']='OTHER'
                elif mode=='party':row['party_context']='Republican'
                elif mode=='date':row['date_evidence']={}
                elif mode=='historical':row['historical']=False
                elif mode=='page':row['physical_pdf_page_1_based']=9
                elif mode=='source':row['source_id']='OTHER'
                elif mode=='hash':row['render_sha256']='0'*64
                elif mode=='extra':row['extra']='PRIVATE'
                elif mode=='missing':row.pop('official_name_literal')
                elif mode=='order':f['transcript']['occurrences'].reverse()
                elif mode=='numeric':row['physical_pdf_page_1_based']=True
                elif mode=='UNKNOWN':f['runtime']['unknowns']['latest_amendment']={'kind':'KNOWN','reason':'INVENTED'}
                if 'official_name_literal' in row:row['name_utf8_sha256']=h.old.digest(row['official_name_literal'].encode())
                row['office_utf8_sha256']=h.old.digest(row['office_label_literal'].encode())
                save_inputs(root,f['runtime'],f['transcript'])
                # coedited references do not modify the immutable admission config/rule
                reseal_runtime(root,f)
                with runtime(root,f),self.assertRaises(h.old.DocumentsRejected):a.read_released(root,f['outer_raw'],expected_sha=f['outer_sha'])

    def test_pure_rederived_witness_checks_after_coedited_dynamic_authority(self):
        for mode in ['office','name','history','role','date','order','extra','audit','schema','unknown']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root);row=f['transcript']['occurrences'][1]
                if mode=='office':row['office_label_literal']='U.S. Senate';row['office_utf8_sha256']=h.old.digest(b'U.S. Senate')
                elif mode=='name':row['official_name_literal']='DEMO ALTERED';row['name_utf8_sha256']=h.old.digest(b'DEMO ALTERED')
                elif mode=='history':row['historical']=False
                elif mode=='role':row['record_role']='OTHER'
                elif mode=='date':row['date_evidence']={}
                elif mode=='order':f['transcript']['occurrences'].reverse()
                elif mode=='extra':row['audit_sha256']='0'*64
                elif mode=='schema':f['transcript']['schema_version']=True
                elif mode=='unknown':f['runtime']['unknowns']={}
                audit=save_inputs(root,f['runtime'],f['transcript'])
                if mode=='audit':audit['approved_occurrences']=[]
                # Fresh transcript digest is allowed only in this authored pure probe;
                # exact unchanged record witnesses still reject coedited inputs.
                rule=copy.deepcopy(f['rule']);rule['source_transcript_sha256']=f['runtime']['transcription']['sha256']
                with patch.object(h,'RULE_SHA',h.old.digest(encoded(rule))),self.assertRaises(h.old.DocumentsRejected):h.reconcile(f['runtime'],f['transcript'],audit,rule)

    def test_history_ledger_seal_controls_code_manifest_cannot_be_substituted(self):
        for mode in ['ledger','seal','started','completed','code','manifest']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root);hist=f['cfg']['historical_source_only']
                if mode in ['ledger','seal']:p=f['historical_parent']/('checksums.json' if mode=='ledger' else 'al_release.json')
                elif mode in ['started','completed']:p=root/'data/processed/e01_al_release_controls'/f['legacy']['source_sha']/('source_only.'+mode+'.local.json')
                elif mode=='code':p=root/legacy.ADAPTER
                else:p=root/hist['manifest_ref']['path']
                p.write_bytes(p.read_bytes()+b'CHANGED')
                with runtime(root,f),patch.object(a,'_materialize') as source,self.assertRaises(h.old.DocumentsRejected):a.read_released(root,f['outer_raw'],expected_sha=f['outer_sha'])
                source.assert_not_called()

    def test_closed_schema2_refuses_names_extras_boolean_counts_or_old_schema(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root)
            with runtime(root,f):out=a.read_released(root,f['outer_raw'],expected_sha=f['outer_sha'])
            for key,value in [('schema_version',1),('office_literal_form_count',True),('candidate_names',['PRIVATE']),('source_adoption',1)]:
                public=out.public_diagnostics();public[key]=value
                with runtime(root,f),self.assertRaises(h.old.DocumentsRejected):h.old.safe(lambda:h.validate_public(public))

    def test_original_rule_and_frozen_code_match_public_methods_pins(self):
        proposal=json.loads((REPO/'configs/e01_al_office_label_equivalence_v1_1_methods_proposal.json').read_text())
        rule=json.loads((REPO/'configs/e01_al_office_family_rule_v1_1.json').read_text())
        self.assertEqual(h.admit_rule(rule),proposal['proposed_rule'])
        cfg=json.loads((REPO/a.CONFIG).read_text())
        for p,sha in cfg['historical_source_only']['code_pins'].items():self.assertEqual(h.old.digest((REPO/p).read_bytes()),sha)

    def test_entire_matched_frozen_adapter_and_wrapper_refuse_literal_variation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);old=f['legacy']
            matched=copy.deepcopy(old['outer']);matched['runtime']=copy.deepcopy(f['outer']['runtime'])
            raw=encoded(matched);sha=h.old.digest(raw);original=h.old._reconcile;calls=[]
            def strict(c,t,audit):
                self.assertEqual(encoded(t),encoded(f['transcript']))
                calls.append(True);return original(c,t,audit)
            before=identities(root)
            with runtime(root,f),patch.object(h.old,'_reconcile',side_effect=strict):
                with self.assertRaises(h.old.DocumentsRejected):legacy.read_released(root,raw,expected_sha=sha)
                self.assertEqual(before,identities(root))
                with self.assertRaises(h.old.DocumentsRejected):legacy_writer.record(root,raw,expected_sha=sha,phase='primary')
            self.assertEqual(calls,[True,True])
            new_parents=[p for p in (root/'data/processed/runs').iterdir() if p.name!=f['historical_parent'].name]
            self.assertEqual(len(new_parents),1);self.assertTrue((new_parents[0]/'failure.json').exists())
            self.assertFalse((new_parents[0]/'al_release.json').exists())
            with runtime(root,f):
                one=w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='primary')
                two=w.record(root,f['outer_raw'],expected_sha=f['outer_sha'],phase='replay')
            self.assertEqual((one/w.PRIVATE).read_bytes(),(two/w.PRIVATE).read_bytes())
            self.assertEqual((root/f['runtime']['transcription']['path']).read_bytes(),encoded(f['transcript']))

    def test_resealed_rule_config_or_new_review_cannot_change_external_authority(self):
        for mode in ['rule','config','review','historical_ref','audit_copy']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();f=fixture(root)
                if mode=='rule':
                    rule=copy.deepcopy(f['rule']);rule['permitted_rows'][1]['expected_office_literal']='Governor'
                    f['outer']['office_rule']=bind_json(root,f['cfg']['rule_ref']['path'],rule)
                elif mode=='config':
                    cfg=copy.deepcopy(f['cfg']);cfg['historical_source_only']['seal_sha256']='0'*64
                    bind_json(root,a.CONFIG,cfg)
                elif mode=='review':
                    ref=f['outer']['code_review'];review=json.loads((root/ref['path']).read_bytes());review['reviewed_code_pins'][a.HELPER]='0'*64
                    f['outer']['code_review']=bind_json(root,ref['path'],review)
                elif mode=='historical_ref':f['outer']['source_release']['path']='data/processed/another.local.json'
                else:
                    ref=f['runtime']['independent_transcription_audit'];f['runtime']['independent_transcription_audit']={**ref,'path':f['cfg']['accepted_literal_audit_ref']['path']}
                    reseal_runtime(root,f)
                raw=encoded(f['outer'])
                with runtime(root,f),self.assertRaises(h.old.DocumentsRejected):a.read_released(root,raw,expected_sha=h.old.digest(raw))

    def test_history_prepare_and_readonly_saved_consumer_do_not_read_raw_sources(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();f=fixture(root);original=h.old.bound_file;before=identities(root)
            def bound(root,path,*args,**kw):
                if path.startswith('data/raw/'):raise AssertionError('UNAUTHORIZED_RAW_SOURCE_READ')
                return original(root,path,*args,**kw)
            with runtime(root,f),patch.object(h.old,'bound_file',side_effect=bound):
                a._prepare(root,f['outer_raw'],f['outer_sha'])
                private,public=a.expected_saved_payloads(root,f['outer_raw'],expected_sha=f['outer_sha'])
            self.assertEqual(before,identities(root));self.assertEqual(private['occurrences'],f['transcript']['occurrences'])
            self.assertEqual(public['schema_version'],2)
