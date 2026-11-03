"""Authored integration/lifecycle fixtures only; no real source/helper execution."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civiclab.e01 import ballots_v1_9 as m
from civiclab.common import canonical_hash,sha256_file
from civiclab.dashboard import verified_run
from civiclab.reproduction import build_package
from tests.test_e01_idaho_v1_8_1 import primitive
REPO=Path(__file__).resolve().parents[1]


def base_fixture():
    roster={s:{'state':s,'candidates':[{'official_name':'DEMO PRIOR '+s,'source_party_label':'DEMO PARTY','party_class':'UNSPECIFIED','printed_on_ballot':False,'declared_write_in':True}], 'observations':{'final_ballot_accepted':False},'source_hashes':['0'*64]} for s in m.STATES}
    public={'status':'READINESS_PARTIAL_NOT_SOURCE_OR_SAMPLE_ACCEPTANCE','scope':'OFFICIAL_BALLOT_READINESS_ONLY','regular_frame_slots':33,'official_rosters_extracted':12,'source_hash_checks':35,'final_ballots_accepted':0,'source_adoption':False,'actual_selection':False,'cost_usd':0,'model_calls':0,
    'candidate_observations':[{'state':s,'status':'DEMO_OBSERVED' if s in m.STATES else 'NOT_YET_ACQUIRED_OFFICIAL_CANDIDATE_DOCUMENT'} for s in m.legacy.base.CLASS_II_STATES],
    'context_contests':[{'contest_id':k,'scope':'CONTEXT_OUTSIDE_REGULAR_QUOTAS','official_source_ids':[],'status':'DEMO_PENDING','reason':'DEMO context'} for k in sorted(m.legacy.base.CONTEXT_IDS)]}
    return {**public,'local_only_rosters':roster}


def fixture(root):
    c=json.loads((REPO/'configs/e01_typed_readiness_v1_9_candidate.json').read_text());bundle=primitive();base=base_fixture()
    for source in c['sources']:
        p=root/source['path'];p.parent.mkdir(parents=True,exist_ok=True);raw=('DEMO SOURCE '+source['source_id']).encode();p.write_bytes(raw);source.update(bytes=len(raw),sha256=m.idaho.digest(raw))
    for relative in c['code_config_audit_pins']:
        p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((REPO/relative).read_bytes());c['code_config_audit_pins'][relative]=sha256_file(p)
    module=root/'src/civiclab/e01/ballots_v1_9.py';module.parent.mkdir(parents=True,exist_ok=True);module.write_bytes((REPO/'src/civiclab/e01/ballots_v1_9.py').read_bytes())
    values={'legacy_public':{k:v for k,v in base.items() if k!='local_only_rosters'},'legacy_rosters':base['local_only_rosters'],'id_records':list(bundle.local_records),'id_diagnostics':bundle.public_diagnostics()}
    for name,value in values.items():
        ref=c['references'][name];p=root/ref['path'];p.parent.mkdir(parents=True,exist_ok=True);raw=m.encoded(value);p.write_bytes(raw);ref['sha256']=m.idaho.digest(raw)
    c['id_diagnostics_canonical_sha256']=canonical_hash(values['id_diagnostics']);c['context_contests_canonical_sha256']=canonical_hash(values['legacy_public']['context_contests'])
    (root/'configs/e01_typed_readiness_v1_9_candidate.json').write_bytes(m.encoded(c))
    return c,base,bundle


def runtime(root,c,base,bundle):
    s=ExitStack();s.enter_context(patch.object(m,'CONTRACT_SHA',canonical_hash(c)));s.enter_context(patch.object(m,'ID_DIAG_SHA',canonical_hash(bundle.public_diagnostics())));s.enter_context(patch.object(m,'CONTEXT_SHA',canonical_hash(base['context_contests'])))
    for module,name in [(m,'ballots_v1_9'),(m.legacy,'ballots_v1_7'),(m.idaho,'idaho_v1_8_1')]:s.enter_context(patch.object(module,'__file__',str(root/f'src/civiclab/e01/{name}.py')))
    s.enter_context(patch.object(m.legacy,'validate_readiness',side_effect=lambda *a:copy.deepcopy(base)))
    s.enter_context(patch.object(m.idaho,'read_sources',return_value=bundle))
    s.enter_context(patch.object(m.legacy,'run_readiness',side_effect=AssertionError('NO CHILD RUN')))
    return s


def new_runs(root,before):return [p for p in (root/'data/processed/runs').iterdir() if p.is_dir() and p not in before]


class TypedReadinessTests(unittest.TestCase):
    def test_single_parent_success_replay_unchanged_twelve_rosters_separate_typed_ID(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();c,base,bundle=fixture(root)
            before=set((root/'data/processed/runs').iterdir())
            with runtime(root,c,base,bundle):
                runs=[m.run_readiness(root,c),m.run_readiness(root,c)]
                public=m.read_verified_public(runs[0])
            self.assertEqual(len(new_runs(root,before)),2)
            for f in m.DATA_FILES:self.assertEqual((runs[0]/f).read_bytes(),(runs[1]/f).read_bytes())
            self.assertEqual((runs[0]/'candidate_rosters.local.json').read_bytes(),(root/c['references']['legacy_rosters']['path']).read_bytes())
            self.assertEqual((runs[0]/'legacy_readiness_v1_7.json').read_bytes(),(root/c['references']['legacy_public']['path']).read_bytes())
            local=json.loads((runs[0]/'candidate_rosters.local.json').read_text());self.assertEqual(local,base['local_only_rosters']);self.assertNotIn('ID',local)
            self.assertEqual(json.loads((runs[0]/'id_status_records.local.json').read_text()),list(bundle.local_records))
            self.assertEqual(public['metrics']['document_state_coverage_count'],13);self.assertEqual(public['metrics']['legacy_roster_state_count'],12)
            self.assertFalse(public['accepted_coverage_promoted']);self.assertFalse(public['forecast_consumption'])
            self.assertNotIn('DEMO NAME',json.dumps(public));self.assertNotIn('DEMO PRIOR',json.dumps(public))
            for r in runs:
                verified_run(r)
                with self.assertRaisesRegex(ValueError,'local-only'):build_package(root,root/'unsafe.zip',[r.name])
            self.assertFalse((root/'unsafe.zip').exists())

    def test_metadata_rejection_before_root_store_or_source_reads(self):
        c=json.loads((REPO/'configs/e01_typed_readiness_v1_9_candidate.json').read_text())
        for change in [lambda q:q.update(secret='SYNTHETIC_PRIVATE'),lambda q:q['sources'][0].update(sha256='0'*64),lambda q:q.update(source_adoption=True)]:
            altered=copy.deepcopy(c);change(altered)
            with patch.object(m,'root_guard') as rg,patch.object(m.RunStore,'__init__') as store,patch.object(m,'read_bound') as read,self.assertRaises(m.idaho.CaptureRejected) as cm:m.run_readiness('/unused',altered)
            rg.assert_not_called();store.assert_not_called();read.assert_not_called();self.assertNotIn('SYNTHETIC_PRIVATE',str(cm.exception))

    def assert_failed(self,root,before,kind):
        runs=new_runs(root,before);self.assertEqual(len(runs),1);p=runs[0]
        self.assertEqual(json.loads((p/'failure.json').read_text())['error_type'],kind)
        with self.assertRaises((ValueError,FileNotFoundError)):m.read_verified_public(p)
        if (p/'failure_checksums.local.json').exists():
            hashes=json.loads((p/'failure_checksums.local.json').read_text())
            self.assertTrue(all(sha256_file(p/f)==h for f,h in hashes.items()))
            with self.assertRaises((ValueError,FileNotFoundError)):verified_run(p)
        else:
            self.assertEqual(json.loads((p/'summary.json').read_text())['status'],'FAILED')
            hashes=json.loads((p/'checksums.json').read_text());self.assertTrue(all(sha256_file(p/f)==h for f,h in hashes.items()))
        for f in p.iterdir():
            if f.is_file():self.assertNotIn(b'SYNTHETIC_PRIVATE',f.read_bytes())

    def test_component_errors_cancellation_single_failed_parent_type_only(self):
        for component in ['legacy','id']:
            for error in [RuntimeError,KeyboardInterrupt,SystemExit]:
                with tempfile.TemporaryDirectory() as td:
                    root=Path(td).resolve();c,base,bundle=fixture(root);before=set((root/'data/processed/runs').iterdir())
                    target=m.legacy if component=='legacy' else m.idaho;name='validate_readiness' if component=='legacy' else 'read_sources'
                    expected=error if error in [KeyboardInterrupt,SystemExit] else m.idaho.CaptureRejected
                    with runtime(root,c,base,bundle),patch.object(target,name,side_effect=error('SYNTHETIC_PRIVATE')),self.assertRaises(expected):m.run_readiness(root,c)
                    self.assert_failed(root,before,error.__name__)

    def test_each_old_object_mutation_IDinlegacy_and_private_UNKNOWN_coercion_refused(self):
        mutations=[(lambda b,state=state:b['local_only_rosters'][state].update(extra='ALTERED')) for state in m.STATES]+[lambda b:b['local_only_rosters'].update(ID={}),lambda b:b['candidate_observations'][0].update(status='ALTERED')]
        for mutation in mutations:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,base,bundle=fixture(root);before=set((root/'data/processed/runs').iterdir());mutation(base)
                with runtime(root,c,base,bundle),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
                self.assert_failed(root,before,'ValueError')
        for field in m.idaho.UNKNOWN_REASONS:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,base,bundle=fixture(root);before=set((root/'data/processed/runs').iterdir());bundle.local_records[0][field]=False
                with runtime(root,c,base,bundle),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
                self.assert_failed(root,before,'ValueError')

    def test_strict_public_schema_kinds_states_counts_private_diag_and_filters(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();c,b,u=fixture(root)
            with runtime(root,c,b,u):public=m.compute(root,c)['typed_document_readiness.json'];m.validate_public(public)
            mutations=[lambda q:q.update(schema_version=1),lambda q:q.update(extra='DEMO PRIVATE'),lambda q:q['document_observations'][0].update(kind='UNKNOWN'),lambda q:q['document_observations'].__setitem__(1,q['document_observations'][0]),lambda q:q['metrics'].update(typed_status_history_state_count=True),lambda q:q['context_contests'][0].update(extra='DEMO NAME'),lambda q:next(x for x in q['document_observations'] if x['state']=='ID')['safe_diagnostics'].update(names='DEMO PRIVATE'),lambda q:next(x for x in q['document_observations'] if x['state']=='ID')['safe_diagnostics']['candidate_name_input_evidence'].__setitem__(0,{'kind':'KNOWN','value':''})]
            for change in mutations:
                altered=copy.deepcopy(public);change(altered)
                with runtime(root,c,b,u),self.assertRaises(ValueError):m.validate_public(altered)

    def test_final_source_recheck_after_partial_publication_failure_sealed_not_success(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir());original=m.verify_bound_inputs;calls=[0]
            def check(*a):
                calls[0]+=1
                if calls[0]==3:raise RuntimeError('SYNTHETIC_PRIVATE')
                return original(*a)
            with runtime(root,c,b,u),patch.object(m,'verify_bound_inputs',side_effect=check),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
            self.assertEqual(calls[0],3);self.assert_failed(root,before,'RuntimeError')
            p=new_runs(root,before)[0];self.assertTrue((p/'typed_document_readiness.json').exists());self.assertFalse((p/'typed_commit.json').exists())

    def test_constructor_payload_commit_summary_ledger_write_errors_before_and_after(self):
        targets=['manifest.json','environment.json',*m.DATA_FILES,'typed_payload_hashes.json','typed_commit.json','summary.json','checksums.json','typed_release.json']
        for name in targets:
            for after in [False,True]:
                with tempfile.TemporaryDirectory() as td:
                    root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir());original=m.RunStore.write;fired=[False]
                    def write(run,n,value):
                        if n==name and not fired[0]:
                            fired[0]=True
                            if after:original(run,n,value)
                            raise OSError('SYNTHETIC_PRIVATE')
                        return original(run,n,value)
                    with runtime(root,c,b,u),patch.object(m.RunStore,'write',new=write),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
                    self.assertTrue(fired[0]);self.assert_failed(root,before,'OSError')

    def test_events_and_post_finish_cancel_retain_failure_and_invalidate_success_ledger(self):
        for mode in ['started','completed','after_finish']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir());fired=[False];original_event=m.RunStore.event;original_finish=m.RunStore.finish
                def event(run,kind,**kw):
                    if kind==mode and not fired[0]:fired[0]=True;raise KeyboardInterrupt('SYNTHETIC_PRIVATE')
                    return original_event(run,kind,**kw)
                def finish(run,summary):
                    original_finish(run,summary)
                    if not fired[0]:fired[0]=True;raise KeyboardInterrupt('SYNTHETIC_PRIVATE')
                with runtime(root,c,b,u),ExitStack() as stack:
                    if mode=='after_finish':stack.enter_context(patch.object(m.RunStore,'finish',new=finish))
                    else:stack.enter_context(patch.object(m.RunStore,'event',new=event))
                    with self.assertRaises(KeyboardInterrupt):m.run_readiness(root,c)
                self.assert_failed(root,before,'KeyboardInterrupt')

    def test_first_middle_last_metadata_source_coedit_fixed_authority_refuses(self):
        for position in [0,20,39,60,159]:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir());original=m.read_bound;count=[0]
                def read(root,path,digest,area=None,size=None):
                    if area=='data/raw':
                        if count[0]==position:
                            for source in c['sources']:
                                p=root/source['path'];raw=p.read_bytes()+b'ALTERED';p.write_bytes(raw);source.update(bytes=len(raw),sha256=m.idaho.digest(raw))
                        count[0]+=1
                    return original(root,path,digest,area,size)
                with runtime(root,c,b,u),patch.object(m,'read_bound',side_effect=read),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
                self.assertEqual(count[0],position+1);self.assert_failed(root,before,'ValueError')

    def test_verified_consumer_refuses_resealed_schema_extra_diag_and_extra_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();c,b,u=fixture(root)
            with runtime(root,c,b,u):p=m.run_readiness(root,c);m.read_verified_public(p)
            (p/'unexpected.local.json').write_text('{}')
            with runtime(root,c,b,u),self.assertRaises(ValueError):m.read_verified_public(p)
            (p/'unexpected.local.json').unlink()
            f=p/'typed_document_readiness.json';data=json.loads(f.read_text());next(x for x in data['document_observations'] if x['state']=='ID')['safe_diagnostics']['private']='DEMO NAME';f.write_bytes(m.encoded(data))
            hashes=json.loads((p/'typed_payload_hashes.json').read_text());hashes[f.name]=sha256_file(f);(p/'typed_payload_hashes.json').write_bytes(m.encoded(hashes))
            ledger=json.loads((p/'checksums.json').read_text());ledger[f.name]=sha256_file(f);ledger['typed_payload_hashes.json']=sha256_file(p/'typed_payload_hashes.json');(p/'checksums.json').write_bytes(m.encoded(ledger))
            with runtime(root,c,b,u),self.assertRaises(ValueError):m.read_verified_public(p)


    def test_after_finish_source_or_wrapper_drift_invalidates_published_run(self):
        for which in ['source','wrapper']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir());original=m.RunStore.finish
                def finish(run,summary):
                    original(run,summary)
                    p=root/c['sources'][-1]['path'] if which=='source' else root/'src/civiclab/e01/ballots_v1_9.py'
                    p.write_bytes(p.read_bytes()+b'ALTERED')
                with runtime(root,c,b,u),patch.object(m.RunStore,'finish',new=finish),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
                self.assert_failed(root,before,'ValueError')

    def test_bound_reference_code_runtime_and_symlink_failures_not_silent(self):
        for mode in ['reference','code','runtime','source_symlink']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir())
                if mode=='reference':p=root/c['references']['id_records']['path'];p.write_bytes(p.read_bytes()+b'ALTERED')
                elif mode=='code':p=root/next(iter(c['code_config_audit_pins']));p.write_bytes(p.read_bytes()+b'ALTERED')
                elif mode=='runtime':c['geometry_runtime']['version']='0.0'
                else:
                    p=root/c['sources'][0]['path'];q=p.with_name('other');p.rename(q);p.symlink_to(q.name)
                with runtime(root,c,b,u),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
                self.assert_failed(root,before,'ValueError')


    def test_ID_record_boolean_ordinal_alias_refused_by_strict_JSON_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir());u.local_records[0]['source_locations'][0]['data_row_1_based']=True
            with runtime(root,c,b,u),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
            self.assert_failed(root,before,'ValueError')

    def test_completion_not_visible_during_final_recheck_and_missing_seal_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir());original=m.verify_bound_inputs;calls=[0]
            def check(*args):
                calls[0]+=1
                if calls[0]==4:
                    p=new_runs(root,before)[0]
                    self.assertTrue((p/'checksums.json').exists())
                    with self.assertRaises((ValueError,FileNotFoundError)):m.read_verified_public(p)
                return original(*args)
            with runtime(root,c,b,u),patch.object(m,'verify_bound_inputs',side_effect=check):
                p=m.run_readiness(root,c);m.read_verified_public(p)
                (p/'typed_release.json').unlink()
                with self.assertRaises((ValueError,FileNotFoundError)):m.read_verified_public(p)
            self.assertEqual(calls[0],4)

    def test_resealed_private_legacy_and_id_record_mutations_refused(self):
        for name in ['candidate_rosters.local.json','legacy_readiness_v1_7.json','id_status_records.local.json']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,b,u=fixture(root)
                with runtime(root,c,b,u):p=m.run_readiness(root,c)
                f=p/name;data=json.loads(f.read_text())
                if name=='candidate_rosters.local.json':data['AK']['candidates'][0]['official_name']='DEMO ALTERED'
                elif name=='legacy_readiness_v1_7.json':data['candidate_observations'][0]['status']='ALTERED'
                else:data[0]['source_status_literal']='Approved'
                f.write_bytes(m.encoded(data))
                hashes=json.loads((p/'typed_payload_hashes.json').read_text());hashes[name]=sha256_file(f);(p/'typed_payload_hashes.json').write_bytes(m.encoded(hashes))
                ledger=json.loads((p/'checksums.json').read_text());ledger[name]=sha256_file(f);ledger['typed_payload_hashes.json']=sha256_file(p/'typed_payload_hashes.json');(p/'checksums.json').write_bytes(m.encoded(ledger))
                release=json.loads((p/'typed_release.json').read_text());release['checksums_sha256']=sha256_file(p/'checksums.json');(p/'typed_release.json').write_bytes(m.encoded(release))
                with runtime(root,c,b,u),self.assertRaises(ValueError):m.read_verified_public(p)

    def test_status_dates_blank_cells_roles_and_record_order_cannot_collapse(self):
        mutations=[lambda r:r[0].update(source_status_literal='Approved'),lambda r:r[0].update(source_party_label='Republican'),lambda r:r[0].update(date_filed_literal='02/01/2026'),lambda r:r[0].update(date_filed_iso='2026-02-01'),lambda r:r[0].update(source_district_literal='0'),lambda r:r[0].update(source_write_in_cell_literal='False'),lambda r:r[0].update(legal_nominee=False),lambda r:r[0].update(copy.deepcopy(r[1]))]
        for mutation in mutations:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir());mutation(u.local_records)
                with runtime(root,c,b,u),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
                self.assert_failed(root,before,'ValueError')

    def test_persistent_filesystem_failure_never_returns_or_admits_success(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();c,b,u=fixture(root);before=set((root/'data/processed/runs').iterdir())
            with runtime(root,c,b,u),patch.object(m.RunStore,'write',side_effect=OSError('SYNTHETIC_PRIVATE')),self.assertRaises(m.idaho.CaptureRejected):m.run_readiness(root,c)
            p=new_runs(root,before)[0]
            self.assertFalse((p/'typed_release.json').exists())
            self.assertFalse((p/'checksums.json').exists())
            with runtime(root,c,b,u),self.assertRaises((ValueError,FileNotFoundError)):m.read_verified_public(p)


    def test_consumer_symlink_and_resealed_manifest_or_summary_refused(self):
        for mode in ['symlink','manifest','summary']:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td).resolve();c,b,u=fixture(root)
                with runtime(root,c,b,u):p=m.run_readiness(root,c)
                if mode=='symlink':
                    q=p.with_name('linked');q.symlink_to(p.name,target_is_directory=True)
                    with runtime(root,c,b,u),self.assertRaises(ValueError):m.read_verified_public(q)
                    continue
                f=p/(mode+'.json');data=json.loads(f.read_text())
                if mode=='manifest':data['config']['wrapper_sha256']='0'*64
                else:data['source_adoption']=True
                f.write_bytes(m.encoded(data))
                ledger=json.loads((p/'checksums.json').read_text());ledger[f.name]=sha256_file(f);(p/'checksums.json').write_bytes(m.encoded(ledger))
                release=json.loads((p/'typed_release.json').read_text());release['checksums_sha256']=sha256_file(p/'checksums.json');(p/'typed_release.json').write_bytes(m.encoded(release))
                with runtime(root,c,b,u),self.assertRaises(ValueError):m.read_verified_public(p)


if __name__=='__main__':unittest.main()
