"""MOCK complete controller on authored trees/worker receipts, never real PDFs."""
import base64
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from civiclab.e01 import clerk2020_source_job_v1 as j
from civiclab.e01 import clerk2020_native_campaign_v1 as n


class SourceJobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.base=self.root/'AUTHORED_PYTHON';self.base.mkdir()
        exe=self.base/'python3.12';exe.write_bytes(b'AUTHORED_INTERPRETER_NOT_NATIVE_BINARY')
        source_defs=copy.deepcopy(j.adapter.SOURCES)
        for sid,ref in source_defs.items():
            data=('AUTHORED_SNAPSHOT_NOT_ACTUAL_CLERK_'+sid).encode()
            p=self.root/(j.DATA_ROOT+sid+'.pdf');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            ref.update(bytes=len(data),sha256=n.sha(data),role='AUTHORED_MOCK_NOT_ACTUAL_CLERK')
        self.patches=[patch.object(j.adapter,'SOURCES',source_defs),patch.object(sys,'base_prefix',str(self.base)),
            patch.object(j.worker.q,'validate_child',side_effect=lambda raw:j.metadata_json(raw,262144))]
        for p in self.patches:p.start()
        self.refs={}
        for name in j.CODE_PATHS:
            raw=('# AUTHORED CODE '+name).encode();p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            self.refs[name]={'bytes':len(raw),'sha256':n.sha(raw)}
        self.qualified=self.write('reports/AUTHORED-qualified.json',{'runtime_manifest':[
            ['PYTHON_BASE/python3.12',exe.stat().st_size,n.sha(exe.read_bytes())]]})
        self.runtime_review=self.write('reports/AUTHORED-runtime-review.json',{'label':'MOCK','source_authority':False})
        self.acq=[self.write('reports/AUTHORED-acq.json',{'label':'MOCK_ACQUISITION'}),
                  self.write('reports/AUTHORED-handoff.json',{'label':'MOCK_ACQUISITION'})]
        methods={'kind':'E01_FIXED_SOURCE_FORMAT_NATIVE_METHODS_V1_3_CANDIDATE',
                 'past_consumed_qualification_records':{},'past_qualified_limits':{},
                 'qualified_worker':self.qualified,'qualified_runtime_actual':self.runtime_review,
                 'accepted_acquisition':self.acq[0],'acquisition_handoff':self.acq[1]}
        self.methods=self.write(j.METHODS,methods)
        self.patches.append(patch.object(j,'METHODS_SHA',self.methods['sha256']));self.patches[-1].start()
        self.review=self.write('reports/AUTHORED-code-review.json',{'label':'MOCK_REVIEW_NOT_REAL_AUDIT',
            'status':'PASS_CLOSED_FIXED_CAMPAIGN_CODE_V1_2','reviewer_role':'independent_auditor',
            'code_refs':self.refs,'methods_sha256':j.METHODS_SHA,'source_set_sha256':j.source_set_sha()})
        self.spec={'kind':'CLERK_SOURCE_STATIC_SPEC_V1_2','root_sha256':n.sha(str(self.root).encode()),
            'source_set_sha256':j.source_set_sha(),'methods_ref':self.methods,'code_refs':self.refs,
            'qualified_ref':self.qualified,'runtime_review_ref':self.runtime_review,'acquisition_refs':self.acq,
            'ancestor_refs':{},'past_limits':{},'code_review_ref':self.review}

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def write(self,path,obj):
        raw=json.dumps(obj,indent=2).encode();p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        return {'path':path,'bytes':len(raw),'sha256':n.sha(raw)}

    def packet(self,phase='BOOT',prepared=None,anchor=None):
        reg=n.FixedRegistrar(n.FixedStore(self.root),j.source_set_sha())
        decision={'kind':'CLERK_SOURCE_DECISION_V1_2','phase':phase,'static_spec_sha256':j.digest(self.spec),
                  'source_set_sha256':j.source_set_sha(),'phase_budget':n.PREFIX_BUDGETS[phase],
                  'expected_anchor_sha256':anchor}
        if phase=='EXEC':
            review=self.write('reports/AUTHORED-prepared-review.json',{'label':'MOCK_REVIEW_NOT_REAL_AUDIT',
                'reviewer_role':'independent_auditor','status':'PASS_PREPARED_EXACT_SOURCE_FORMAT_JOB',
                'prepared_sha256':prepared['sha256'],'source_set_sha256':j.source_set_sha(),
                'source_authority':'EXACT_TWO_SOURCES_FORMAT_ONLY'})
            decision.update(prepared_ref=prepared,prepared_review_ref=review,job_id=j.JOB)
        issued={'kind':'CLERK_SOURCE_ISSUED_V1_2','phase':phase,'ordinal':1,'binding':reg.binding(),
            'decision_sha256':j.digest(decision),'expected_anchor_sha256':anchor,'one_shot':True,
            'prefix_budget':n.PREFIX_BUDGETS[phase]}
        raw=j.canonical({'kind':'CLERK_SOURCE_PHASE_PACKET_V1_2','registration':reg.binding(),
                         'static_spec':self.spec,'decision':decision,'issued':issued})
        return raw,n.sha(raw)

    def boot(self):
        raw,h=self.packet();return j.run_boot(self.root,raw,h)

    def fake_dispatch(self,root,raw,start):
        req=j.decode(raw,950272);sid=req['source_id'];ref=j.adapter.SOURCES[sid]
        rows=[r[:3] for r in req['runtime_catalog']]
        private=j.canonical({'label':'REAL_SOURCE_FORMAT_INSPECTION_ONLY','kind':'CLERK_NATIVE_FORMAT_INVENTORY_V1','source_bytes':ref['bytes'],
            'source_role':ref['role'],'retained_full_document':False,
            'source_id':sid,'source_sha256':ref['sha256'],'page_count':ref['pages'],
            'pages':[{'authored_mock_page':i} for i in range(ref['pages'])],
            'candidate_or_vote_records_parsed':0,'printed_dates_or_roles_adopted':False})
        warmup={'reader_attempts':4,'page_extractions':119,'first_refusal':None,'read_bytes_reserved':0,
            'file_open_events':0,'directory_events':0,'directory_labels_observed':[],'import_events':0,
            'read_files':0,'missing_bytecode_probes':0,'hash_open_events':2*len(rows),
            'hash_read_bytes_reserved':sum(r[1]+1 for r in rows),'hash_files_opened':len(rows),
            'hash_descriptor_events':len(rows)}
        m={'kind':'CLERK_SOURCE_WORKER_RECEIPT_V1_2','status':'SOURCE_FORMAT_ONLY_COMPLETE',
           'source_id':sid,'context_sha256':req['context_sha256'],'source_sha256':ref['sha256'],
           'source_bytes':ref['bytes'],'source_pages':ref['pages'],'source_readers':1,
           'warmup_readers':4,'warmup_pages':119,'strict_first_refusal':None,'warmup':warmup,
           'source_counts_or_features_adopted':False,'model_calls':0,'cost_usd':0,
           'registration_sha256':req['registration_sha256'],'native_backend_hash_matched':True,
           'cpu_ms_through_private_projection':1,
           'runtime_indices':list(range(len(rows))),'runtime_manifest_sha256':j.digest(rows),
           'runtime_hash_bytes_observed':sum(r[1] for r in rows),'runtime_hash_bytes_reserved':sum(r[1]+1 for r in rows),
           'private_projection_bytes':len(private),'private_projection_sha256':n.sha(private),
           'execution_decision_sha256':req['execution_decision_sha256'],'reservation_sha256':req['reservation_sha256'],
           'public_diagnostics':{'label':'REAL_SOURCE_FORMAT_INSPECTION_ONLY',
                'kind':'CLERK_NATIVE_FORMAT_DIAGNOSTICS_V1','source_id':sid,'source_sha256':ref['sha256'],
                'source_bytes':ref['bytes'],'source_role':ref['role'],'page_count':ref['pages'],
                'text_characters':0,'text_utf8_bytes':0,'omitted_text_utf8_bytes':0,
                'unknown_role_layout_pages':ref['pages'],'structure_nodes_checked':1,
                'candidate_or_vote_records_parsed':0,'source_or_feature_adoption':False,'model_calls':0,'cost_usd':0}}
        chunks=[base64.b64encode(private[i:i+49152]).decode() for i in range(0,len(private),49152)]
        return j.canonical({'metadata':m,'private_projection_chunks_b64':chunks}),b'',1000000

    def test_wrong_packet_has_zero_reserved_campaign(self):
        raw,_=self.packet()
        with self.assertRaises(n.Refused):j.run_boot(self.root,raw,'f'*64)
        self.assertFalse(n.FixedStore(self.root).exists('boot_reservation'))

    def test_boot_has_zero_source_reads_and_no_dispatch(self):
        with patch.object(j,'source_snapshot') as source,patch.object(j,'dispatch') as dispatch:
            result=self.boot()
        self.assertEqual(result['status'],'BOOT_PREPARED_NO_SOURCE')
        source.assert_not_called();dispatch.assert_not_called()
        store=n.FixedStore(self.root);self.assertTrue(store.exists('prepared_metadata'))
        self.assertLessEqual(store.path('genesis').stat().st_size,6144)

    def test_authored_complete_boot_exec_and_sealed_outputs(self):
        boot=self.boot();self.assertEqual(boot['status'],'BOOT_PREPARED_NO_SOURCE')
        raw,h=self.packet('EXEC',boot['prepared_ref'],boot['completed_anchor_sha256'])
        with patch.object(j,'dispatch',side_effect=self.fake_dispatch) as called:
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'WRITER_COMMITTED_CALLER_OBSERVED')
        self.assertEqual(called.call_count,2)
        self.assertFalse(result['source_counts_or_features_adopted'])
        again=j.run_exec(self.root,raw,h)
        self.assertEqual(again['status'],'FAILED_OR_UNKNOWN_NO_RETRY')

    def test_first_child_failure_stops_source_two_and_preserves_private_partial(self):
        boot=self.boot();raw,h=self.packet('EXEC',boot['prepared_ref'],boot['completed_anchor_sha256'])
        sources=[];original=j.source_snapshot
        def snapshot(root,sid):sources.append(sid);return original(root,sid)
        with patch.object(j,'source_snapshot',side_effect=snapshot),patch.object(j,'dispatch',side_effect=TimeoutError()):
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        self.assertEqual(sources,['clerk2020_statistics'])

    def test_second_child_failure_keeps_first_private_projection(self):
        boot=self.boot();raw,h=self.packet('EXEC',boot['prepared_ref'],boot['completed_anchor_sha256'])
        calls=[]
        def dispatch(root,request,start):
            calls.append(1)
            if len(calls)==2:raise TimeoutError()
            return self.fake_dispatch(root,request,start)
        with patch.object(j,'dispatch',side_effect=dispatch):result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        decision=j.decode(raw)['decision'];rid=j.run_id(n.CAMPAIGN,j.JOB,decision)
        store=n.FixedStore(self.root);store.bind_run(rid)
        private,_=store.read('private_projection',251905)
        self.assertEqual(len(j.decode(private)['documents']),1)
        self.assertFalse(store.exists('seal'))

    def test_code_drift_after_boot_stops_before_any_source_read(self):
        boot=self.boot();raw,h=self.packet('EXEC',boot['prepared_ref'],boot['completed_anchor_sha256'])
        (self.root/j.CODE_PATHS[0]).write_bytes(b'AUTHORED_DRIFT')
        with patch.object(j,'source_snapshot') as called:
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY');called.assert_not_called()

    def exec_packet(self):
        boot=self.boot();self.assertEqual(boot['status'],'BOOT_PREPARED_NO_SOURCE')
        return self.packet('EXEC',boot['prepared_ref'],boot['completed_anchor_sha256'])

    def result_store(self,raw):
        store=n.FixedStore(self.root);store.bind_run(j.run_id(n.CAMPAIGN,j.JOB,j.decode(raw)['decision']))
        return store

    def test_boot_late_prepared_write_or_cpu_overrun_blocks_exec(self):
        clock=[0.0];cpu=[0.0];original=n.FixedStore.create
        def creating(store,slot,raw):
            ref=original(store,slot,raw)
            if slot=='prepared_metadata':clock[0]=46.0
            return ref
        with patch.object(j.time,'monotonic',side_effect=lambda:clock[0]),             patch.object(j.resource,'getrusage',side_effect=lambda who:SimpleNamespace(ru_utime=cpu[0],ru_stime=0)),             patch.object(n.FixedStore,'create',new=creating),patch.object(j,'source_snapshot') as source:
            result=self.boot()
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY');source.assert_not_called()
        store=n.FixedStore(self.root);self.assertTrue(store.exists('private_stderr'))
        prepared_raw,_=store.read('prepared_metadata',2049)
        prepared={'slot':'prepared_metadata','bytes':len(prepared_raw),'sha256':j.sha(prepared_raw)}
        anchor=n.FixedRegistrar(store,j.source_set_sha()).current()[0]
        raw,h=self.packet('EXEC',prepared,anchor)
        with patch.object(j,'source_snapshot') as source:again=j.run_exec(self.root,raw,h)
        self.assertEqual(again['status'],'FAILED_OR_UNKNOWN_NO_RETRY');source.assert_not_called()

    def test_boot_cpu_checked_after_prepared_write(self):
        cpu=[0.0];original=n.FixedStore.create
        def creating(store,slot,raw):
            ref=original(store,slot,raw)
            if slot=='prepared_metadata':cpu[0]=6.0
            return ref
        with patch.object(j.resource,'getrusage',side_effect=lambda who:SimpleNamespace(ru_utime=cpu[0],ru_stime=0)) as usage,             patch.object(n.FixedStore,'create',new=creating):result=self.boot()
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        self.assertGreater(usage.call_count,0)

    def test_exec_late_completed_anchor_resource_overrun_invalidates(self):
        raw,h=self.exec_packet();clock=[0.0];original=n.FixedStore.create
        def creating(store,slot,body):
            ref=original(store,slot,body)
            if slot=='anchor_complete':clock[0]=76.0
            return ref
        with patch.object(j.time,'monotonic',side_effect=lambda:clock[0]),             patch.object(n.FixedStore,'create',new=creating),patch.object(j,'dispatch',side_effect=self.fake_dispatch):
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        store=self.result_store(raw);self.assertTrue(store.exists('tail_invalidate'))
        self.assertEqual(n.FixedRegistrar(store,j.source_set_sha()).current()[1]['state'],'anchor_invalid')
        self.assertFalse(store.exists('caller_observation'))

    def test_final_wall_check_after_caller_observation_invalidates(self):
        raw,h=self.exec_packet();armed=[False];calls=[0];original=n.FixedStore.create
        protected={}
        def creating(store,slot,body):
            ref=original(store,slot,body)
            if slot in {'seal','writer_ack','caller_observation'}:protected[slot]=ref['sha256']
            if slot=='caller_observation':armed[0]=True
            return ref
        def clock():
            if armed[0]:
                calls[0]+=1
                return 0.0 if calls[0]==1 else 76.0
            return 0.0
        with patch.object(j.time,'monotonic',side_effect=clock),patch.object(n.FixedStore,'create',creating),patch.object(j,'dispatch',side_effect=self.fake_dispatch):
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        store=self.result_store(raw)
        self.assertTrue(store.exists('caller_observation'));self.assertTrue(store.exists('anchor_complete'))
        self.assertTrue(store.exists('tail_invalidate'))
        self.assertEqual(n.FixedRegistrar(store,j.source_set_sha()).current()[1]['state'],'anchor_invalid')
        for slot,expected in protected.items():self.assertEqual(j.sha(store.path(slot).read_bytes()),expected)

    def test_final_rounded_cpu_boundary_after_caller_observation_invalidates(self):
        raw,h=self.exec_packet();armed=[False];calls=[0];original=n.FixedStore.create
        def creating(store,slot,body):
            ref=original(store,slot,body)
            if slot=='caller_observation':armed[0]=True
            return ref
        def usage(who):
            if armed[0]:
                calls[0]+=1
                # First resource-window sample remains zero; the final raw
                # sample totals exactly50s and conservatively rounds to50001ms.
                if calls[0]>2:return SimpleNamespace(ru_utime=25.0,ru_stime=0.0)
            return SimpleNamespace(ru_utime=0.0,ru_stime=0.0)
        with patch.object(j.time,'monotonic',return_value=0.0),patch.object(j.resource,'getrusage',side_effect=usage),patch.object(n.FixedStore,'create',creating),patch.object(j,'dispatch',side_effect=self.fake_dispatch):
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        store=self.result_store(raw);self.assertTrue(store.exists('caller_observation'))
        self.assertTrue(store.exists('tail_invalidate'))
        self.assertEqual(n.FixedRegistrar(store,j.source_set_sha()).current()[1]['state'],'anchor_invalid')

    def test_invalidation_write_failure_stays_unknown_without_caller_observation(self):
        raw,h=self.exec_packet();clock=[0.0];original=n.FixedStore.create
        def creating(store,slot,body):
            if slot=='tail_invalidate':raise OSError('AUTHORED_EROFS')
            ref=original(store,slot,body)
            if slot=='anchor_complete':clock[0]=76.0
            return ref
        with patch.object(j.time,'monotonic',side_effect=lambda:clock[0]),             patch.object(n.FixedStore,'create',new=creating),patch.object(j,'dispatch',side_effect=self.fake_dispatch):
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        store=self.result_store(raw);self.assertTrue(store.exists('private_stderr'))
        self.assertFalse(store.exists('caller_observation'))
        self.assertTrue(store.exists('writer_ack'))

    def test_lost_caller_return_does_not_manufacture_observation(self):
        raw,h=self.exec_packet();original=n.FixedStore.__init__
        def initial(store,*args,**kwargs):
            original(store,*args,**kwargs)
            def crash(event):
                if event=='caller.before':raise RuntimeError('AUTHORED_LOST_RETURN')
            store.crash=crash
        with patch.object(n.FixedStore,'__init__',new=initial),patch.object(j,'dispatch',side_effect=self.fake_dispatch):
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        store=self.result_store(raw);self.assertTrue(store.exists('anchor_complete'))
        self.assertFalse(store.exists('caller_observation'))

    def test_safe_child_stop_retained_without_raw_source_or_excerpt(self):
        raw,h=self.exec_packet()
        stopped={'kind':'CLERK_SOURCE_WORKER_STOP_V1_2','stage':'ACTUAL_SOURCE_FORMAT',
            'source_format_accepted':False,'warmup_progress':{'reader_attempts_entered':4,
                'text_marker_pages_checked':119,'negative_failure_stages':['STRUCTURE','READER_CONSTRUCTION']},
            'warmup_refusal':None,'source_first_refusal':{'event':'import'},
            'source_exception':{'type':'QualificationStopped','stage':'PAGE_EXTRACTION','page':1,
                'frames':[{'function':'inspect_source','line':110}],'traceback_truncated':False},'model_calls':0,'cost_usd':0}
        with patch.object(j,'dispatch',return_value=(j.canonical(stopped),b'',1000000)):
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        store=self.result_store(raw);body,_=store.read('child_metadata_0',8193)
        self.assertEqual(j.decode(body)['diagnostics'],stopped)
        self.assertFalse(store.exists('source_receipt_1'))
        unsafe=dict(stopped,UNAPPROVED_SOURCE_TEXT='SECRET_SOURCE_CONTENT')
        safe=j.safe_child_failure(j.canonical(unsafe),'clerk2020_statistics',j.sha(b'AUTHORED_CONTEXT'))
        self.assertIsNone(safe['diagnostics']);self.assertNotIn('SECRET_SOURCE_CONTENT',j.canonical(safe).decode())

    def test_dispatch_partial_stdout_and_stderr_hashes_preserved_only(self):
        raw,h=self.exec_packet()
        with patch.object(j,'dispatch',side_effect=j.ChildProcessStop(b'PARTIAL_PRIVATE_SOURCE',b'PRIVATE_DIAGNOSTIC')):
            result=j.run_exec(self.root,raw,h)
        self.assertEqual(result['status'],'FAILED_OR_UNKNOWN_NO_RETRY')
        body,_=self.result_store(raw).read('child_metadata_0',8193);m=j.decode(body)
        self.assertEqual(m['wire_sha256'],j.sha(b'PARTIAL_PRIVATE_SOURCE'))
        self.assertEqual(m['stderr_sha256'],j.sha(b'PRIVATE_DIAGNOSTIC'))
        self.assertNotIn('PARTIAL_PRIVATE_SOURCE',body.decode())
        self.assertNotIn('PRIVATE_DIAGNOSTIC',body.decode())


if __name__=='__main__':unittest.main()
