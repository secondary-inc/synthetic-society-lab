from array import array
from copy import deepcopy
import csv
from fractions import Fraction
import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile
from civiclab.common import canonical_hash,sha256_file
from civiclab.e02.national_budget import Blocked,FixtureResponse,acquire_fixture
from civiclab.e02.full_adult_types_v1_1 import AdultMatrix,actual_source,decimal,finite,i64,strict_json,schema_check,row_axes,parse_person
from civiclab.e02.full_adult_control_v1_1 import fixture_root,FResourceLedger,Policy
from civiclab.e02.full_adult_engine_v1_1 import enroll_F,process_F,parse_F,merge_F
from civiclab.e02.full_adult_analysis_v1_1 import compile_plan,uncertainty,Ops,evaluate_query,validate_result,mandatory_analysis,moments
from civiclab.e02.full_adult_queries_v1_1 import QueryLedger,prepare_plan,execute_query,assemble_results
from civiclab.e02.full_adult_runtime_v1_1 import FullAdultFixtureEngine
from civiclab.e02.full_adult_codec_v1_1 import primitive_bundle,read_benchmark

ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'configs/e02_full_adult_benchmark_u1_v1_1.json').read_text())


def config(root,*,rows=12):
    c=json.loads((ROOT/'configs/e02_full_adult_engine_v1_1.json').read_text());c['authored_fixture']=True;c['fixture_root']=str(Path(root).resolve())
    for r in c['registry']:r.update(published_person_rows=rows,url='fixture://F/'+r['state_fips'],first_archive_sha256=None,exact_archive_bytes=None,literal_member_manifest=None)
    c['limits'].update(free_disk_bytes=0,minimum_initial_free_disk_bytes=0,state_processing_seconds=60,request_seconds=60,network_seconds=7200)
    c['F_storage'].update(free=0,initial_free=0);fixture_root(root,c,create=True);return c


def source(c,state='01',*,full=False,anticorrelated=False,mutate=None,children=True,width_change=None):
    fields=c['person_controls']['required_fields']+['SERIALNO']+['UNUSED'+str(i) for i in range(193)]
    assert len(fields)==285
    rows=[]
    for a in (range(4) if full else [0]):
        for e in (range(3) if full else [0]):
            for citizen in (1,5):
                for residence in (20,37,38):
                    row={k:'' for k in fields};row.update(RT='P',STATE=state,AGEP=str([18,25,45,65][a]),CIT=str(citizen),RELSHIPP=str(residence),SCHL=str([17,20,24][e]),PWGTP='1',SERIALNO='PRIVATE_F_AUTHOR_MARKER')
                    for j in range(80):row['PWGTP'+str(j+1)]=str(([-1,3][j%2] if state!='02' or anticorrelated=='same' else [3,-1][j%2]) if anticorrelated and citizen==1 and residence==20 else 1)
                    for f in ('FAGEP','FCITP','FSCHLP','FRELSHIPP'):row[f]='0'
                    rows.append(row)
    if children:
        for citizen in (1,5):
            for residence in (20,37,38):
                row=dict(rows[0]);row.update(AGEP='2',SCHL='',CIT=str(citizen),RELSHIPP=str(residence))
                for j in range(80):row['PWGTP'+str(j+1)]='1'
                rows.append(row)
    if mutate:mutate(rows)
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader();writer.writerows(rows);payload=out.getvalue().encode()
    if width_change is not None:
        target,kind=width_change;raw=list(csv.reader(io.StringIO(payload.decode())))
        if kind=='missing':raw[target+1]=raw[target+1][:-1]
        elif kind=='extra':raw[target+1].append('PRIVATE_EXTRA_F,quoted "value"')
        elif kind=='empty':raw[target+1][-1]=''
        else:raise AssertionError('bad authored width mode')
        out=io.StringIO();csv.writer(out).writerows(raw);payload=out.getvalue().encode()
    name='psam_p'+state+'.csv';pdf=b'%PDF-AUTHORED-F-NOT-EXECUTED';root=Path(c['fixture_root'])/'sources';path=root/(state+'.zip')
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo(name,(2026,1,1,0,0,0)),payload);z.writestr(zipfile.ZipInfo('fixture.pdf',(2026,1,1,0,0,0)),pdf)
    m={'input_kind':'AUTHORED_F_V1_1','state':state,'url':'fixture://F/'+state,'period':c['period'],'metadata_hashes':c['metadata_hashes'],'archive_bytes':path.stat().st_size,'archive_sha256':sha256_file(path),'person_member':name,'header_sha256':hashlib.sha256(payload.splitlines(keepends=True)[0]).hexdigest(),'members':{name:{'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()},'fixture.pdf':{'bytes':len(pdf),'sha256':hashlib.sha256(pdf).hexdigest()}}}
    return path,m,{'kind':'AUTHORED_REVIEW_F_ONLY','manifest_sha256':canonical_hash(m)}


def catalogs():
    names=['state_fips','age_bin','education_bin','citizenship_bin','residence_bin'];selectors=[]
    for ident,state in [('x','01'),('y','02')]:
        filters=dict(zip(names,[[state],['18-24'],['HS_OR_LESS'],['CITIZEN'],['HOUSEHOLD']]))
        mask=bytes(int(all(value in filters[name] for name,value in zip(names,row_axes(i,SPEC)))) for i in range(3672))
        selectors.append({'selector_id':ident,'axis_filters':filters,'selector_definition_sha256':canonical_hash({'selector_id':ident,'axis_filters':filters}),'compiled_mask_sha256':hashlib.sha256(mask).hexdigest()})
    coeff=[];vectors={}
    for ident,terms in [('x',[('x',1)]),('y',[('y',1)]),('difference',[('x',1),('y',-1)]),('negative',[('x',-1)])]:
        definitions=[{'selector_id':name,'coefficient':k} for name,k in terms];v=[0]*3672
        for name,k in terms:
            selector=next(s for s in selectors if s['selector_id']==name)
            for i in range(3672):v[i]+=k*int(all(value in selector['axis_filters'][n] for n,value in zip(names,row_axes(i,SPEC))))
        h=hashlib.sha256(array('b',v).tobytes()).hexdigest();vectors[ident]=h
        coeff.append({'coefficient_id':ident,'terms':definitions,'coefficient_definition_sha256':canonical_hash({'coefficient_id':ident,'terms':definitions}),'compiled_vector_sha256':h})
    requests=[]
    for ident,kind,x,y in [('cov','COUNT_COVARIANCE','x','y'),('diff','COUNT_LINEAR_SIGNED','difference',None),('neg','COUNT_LINEAR_SIGNED','negative',None)]:
        if y and vectors[x]>vectors[y]:x,y=y,x
        definition={'query_kind':kind,'x_vector_sha256':vectors[x],'y_vector_sha256':vectors[y] if y else None,'units':'PUMS_WEIGHTED_PERSONS_SQUARED' if y else 'PUMS_WEIGHTED_PERSONS','target_schema_version':SPEC['specification_id']}
        requests.append({'query_id':ident,'query_kind':kind,'x_coefficient_id':x,'y_coefficient_id':y,'query_definition_sha256':canonical_hash(definition)})
    return selectors,coeff,requests


def parts(c,*,full=False,anti=False):
    ledger=FResourceLedger(c);out=[];replay=[];manifests={}
    for state in SPEC['universe']['state_fips']:
        path,m,a=source(c,state,full=full,anticorrelated=anti);e=enroll_F(ledger,path,m,a)
        p,_=process_F(ledger,path,m,e);r,_=process_F(ledger,path,m,e,sweep='REPLAY');out.append(p);replay.append(r);manifests[state]=m
    return ledger,out,replay,manifests


class FullAdultTests(unittest.TestCase):
    def test_F01_six_domains_and_all_age_before_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);ledger=FResourceLedger(c)
            def weights(rows):
                for i,row in enumerate(rows[:6]):
                    row['PWGTP']=str(i+1)
                    for j in range(80):row['PWGTP'+str(j+1)]=str([-1,3][j%2] if i==0 else i+1)
            path,m,a=source(c,mutate=weights);e=enroll_F(ledger,path,m,a);p,_=process_F(ledger,path,m,e)
            self.assertEqual(p['accounting']['all']['count'],12);self.assertEqual(p['accounting']['adult']['point'],21);self.assertEqual(p['accounting']['all']['point'],27)
            self.assertEqual(p['accounting']['adult']['replicates'],[19,23]*40);self.assertEqual([p['cells'][str(i)]['point'] for i in range(6)],[1,2,3,4,5,6])
            self.assertNotIn('PRIVATE_F_AUTHOR_MARKER',json.dumps(p))

    def test_F02_F03_full_partition_signed_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);ledger,p,r,m=parts(c,anti='same');matrix=merge_F(p,c,SPEC);replay=merge_F(list(reversed(r)),c,SPEC)
            self.assertEqual(matrix.blobs(),replay.blobs());self.assertEqual(sum(matrix.data['count.i64le']),306)
            self.assertEqual(sum(n>0 for n in matrix.data['count.i64le']),306);self.assertEqual(sum(matrix.present),3672)
            self.assertEqual(sum(matrix.data['point.i64le'][i] for i in range(0,3672,6)),51)
            self.assertEqual(len(matrix.data['replicates.i64le']),293760)
            point,reps=matrix.dot([1]*3672);self.assertEqual(point,306);self.assertEqual(reps,[204,408]*40)
            self.assertEqual(moments(point,reps,Ops(1000))[1],41616)
            self.assertNotEqual(41616,51*16)
            for which in ('count','point'):
                self.assertEqual(sum(v['accounting']['all'][which] for v in p),sum(v['accounting']['adult'][which]+v['accounting']['under18'][which] for v in p))
            with self.assertRaises(Blocked):merge_F(p[:-1]+[p[0]],c,SPEC)

    def test_F04_required_domains_precede_age_citizenship_gq(self):
        for name,value in [('PWGTP','0'),('PWGTP80','-10000'),('CIT','0'),('RELSHIPP','39'),('SCHL',''),('FAGEP','2')]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                c=config(tmp);ledger=FResourceLedger(c)
                def corrupt(rows):rows[0].update(CIT='5',RELSHIPP='37');rows[0][name]=value
                path,m,a=source(c,mutate=corrupt);e=enroll_F(ledger,path,m,a)
                with self.assertRaises(Blocked):process_F(ledger,path,m,e)
                self.assertTrue(ledger.snapshot()['halted'])

    def test_F05_F06_codec_unknown_zero_shape_and_overflow(self):
        matrix=AdultMatrix();self.assertIsNone(matrix.record(0,SPEC)['point_weight_sum']);matrix.mark_state(0);matrix.validate(SPEC)
        self.assertEqual(matrix.record(0,SPEC)['point_weight_sum'],0);self.assertEqual(matrix.support[0],1)
        blobs=matrix.blobs();self.assertEqual(sum(map(len,blobs.values())),2680560);self.assertEqual(len(blobs['replicates.i64le']),2350080)
        self.assertEqual(AdultMatrix.decode(blobs,SPEC).blobs(),blobs)
        for change in ('length','mask','padding','extra'):
            bad=dict(blobs)
            if change=='length':bad['point.i64le']=bad['point.i64le'][:-1]
            if change=='mask':bad['source_status.u8']=bytes([255])*3672
            if change=='padding':bad['point.i64le']=b'\x01'+bad['point.i64le'][1:];bad['source_status.u8']=bytes(3672);bad['support_status.u8']=bytes(3672)
            if change=='extra':bad['extra.bin']=b''
            with self.subTest(change=change),self.assertRaises(Blocked):AdultMatrix.decode(bad,SPEC)
        with self.assertRaises(Blocked):i64(2**63)
        self.assertGreater((2*16095728*9999)**2,2**63)

    def test_F07_F19_negative_covariance_and_canonical_semantics(self):
        plan=compile_plan(SPEC,*catalogs());matrix=AdultMatrix()
        for state,reps in [(0,[-1,3]*40),(1,[3,-1]*40)]:matrix.add(state*72,1,reps,[0]*4)
        for state in range(51):matrix.mark_state(state)
        matrix.validate(SPEC);result={q['query_id']:evaluate_query(matrix,q,'a'*64,SPEC) for q in plan['queries']}
        self.assertEqual(result['cov']['covariance_numerator_signed_decimal'],'-320');self.assertEqual(result['cov']['covariance_sdr'],-16)
        self.assertEqual(result['diff']['variance_sdr'],64);self.assertEqual(result['diff']['standard_error'],8);self.assertEqual(result['neg']['point_signed_decimal'],'-1')
        query=next(q for q in plan['queries'] if q['query_id']=='cov')
        for field,value in [('covariance_sdr',16),('covariance_numerator_signed_decimal','-0'),('x_replicates_sha256','0'*64),('units','persons'),('x_point_signed_decimal',' 1')]:
            bad={**result['cov'],field:value}
            with self.subTest(field=field),self.assertRaises(Blocked):validate_result(bad,matrix,query,'a'*64,SPEC)
        rec=uncertainty('ratio',1,[3]*80,Ops(1000),denominator=('F',2,[-1]*80));self.assertIsNone(rec['variance_sdr']);self.assertEqual(rec['point_value'],.5)
        rec=uncertainty('ratio',3,[3]*80,Ops(1000),denominator=('F',2,[2]*80));self.assertEqual(rec['point_value'],1.5)
        for value in ['-0',' 1','01','+1','1.0']:
            with self.assertRaises(Blocked):decimal(value)
        for value in [float('nan'),float('inf'),True]:
            with self.assertRaises(Blocked):finite(value)

    def test_F06_F09_F15_F20_full_shape_runtime_and_signed_query_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp,rows=78);engine=FullAdultFixtureEngine(c,SPEC,*catalogs())
            for state in SPEC['universe']['state_fips']:
                path,m,a=source(c,state,full=True,anticorrelated=True);engine.source(path,m,a)
            matrices=engine.benchmark();results=engine.analyze()
            self.assertEqual(sum(matrices['PRIMARY'].data['count.i64le']),3672)
            self.assertEqual(sum(matrices['PRIMARY'].data['count.i64le'][i] for i in range(0,3672,6)),612)
            self.assertEqual(matrices['PRIMARY'].blobs(),matrices['REPLAY'].blobs());self.assertEqual(results['PRIMARY'],results['REPLAY'])
            for name in ('covariance_results_v1_1.jsonl','contrast_results_v1_1.jsonl'):
                self.assertEqual((Path(tmp)/'PRIMARY'/name).read_bytes(),(Path(tmp)/'REPLAY'/name).read_bytes())
            snap=engine.queries.snapshot();self.assertEqual(snap['ops'],engine.plan['total_ops'])
            self.assertEqual(len(snap['queries']),6);self.assertEqual(len(engine.sources.snapshot()['sources']),51)
            self.assertEqual(read_benchmark(c,SPEC,'PRIMARY')[0].blobs(),matrices['PRIMARY'].blobs())

    def test_F08_intentional_64m_plan_refusal_preserves_configuration(self):
        names=['state_fips','age_bin','education_bin','citizenship_bin','residence_bin'];axis_values=[SPEC['universe'][k] for k in ('state_fips','ages','education','citizenship','residence')]
        defs=[('all',dict(zip(names,axis_values)))]+[('s'+str(i),dict(zip(names,[[v] for v in row_axes(i,SPEC)]))) for i in range(32)]
        selectors=[];masks={}
        for ident,filters in defs:
            mask=[int(all(v in filters[k] for k,v in zip(names,row_axes(i,SPEC)))) for i in range(3672)];masks[ident]=mask
            selectors.append({'selector_id':ident,'axis_filters':filters,'selector_definition_sha256':canonical_hash({'selector_id':ident,'axis_filters':filters}),'compiled_mask_sha256':hashlib.sha256(bytes(mask)).hexdigest()})
        coefficients=[];hs={}
        for i in range(33):
            ident='c'+str(i);terms=[{'selector_id':'all','coefficient':1}]+([{'selector_id':'s'+str(i-1),'coefficient':-1}] if i else [])
            v=[1-(masks['s'+str(i-1)][r] if i else 0) for r in range(3672)];h=hashlib.sha256(array('b',v).tobytes()).hexdigest();hs[ident]=h
            coefficients.append({'coefficient_id':ident,'terms':terms,'coefficient_definition_sha256':canonical_hash({'coefficient_id':ident,'terms':terms}),'compiled_vector_sha256':h})
        requests=[]
        for i in range(1,31):
            x,y=sorted(['c0','c'+str(i)],key=lambda k:hs[k]);definition={'query_kind':'COUNT_COVARIANCE','x_vector_sha256':hs[x],'y_vector_sha256':hs[y],'units':'PUMS_WEIGHTED_PERSONS_SQUARED','target_schema_version':SPEC['specification_id']}
            requests.append({'query_id':'q'+str(i),'query_kind':'COUNT_COVARIANCE','x_coefficient_id':x,'y_coefficient_id':y,'query_definition_sha256':canonical_hash(definition)})
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp)
            with self.assertRaisesRegex(Blocked,'64million'):prepare_plan(c,SPEC,selectors,coefficients,requests)
            state=json.loads((Path(tmp)/'analysis/state.json').read_text());self.assertTrue(state['halted']);self.assertGreater(state['ops'],0);self.assertEqual(state['queries'],{})
            self.assertTrue((Path(tmp)/'analysis/plan_input.json').is_file());self.assertTrue((Path(tmp)/'PRIMARY/plan_refusal.json').is_file())

    def test_F10_valid_json_source_and_query_counter_resets_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);ledger=FResourceLedger(c);acquire_fixture(ledger,'01',FixtureResponse(b'body',url='fixture://F/01'))
            s=json.loads((ledger.path/'ledger.json').read_text());s['body_charged']=0;(ledger.path/'ledger.json').write_text(json.dumps(s))
            with self.assertRaises(Blocked):FResourceLedger(c)
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);plan,q=prepare_plan(c,SPEC,*catalogs());q.bind('a'*64);q.reserve_query(plan['queries'][0],'PRIMARY')
            state=json.loads((q.path/'state.json').read_text());state['ops']=0;(q.path/'state.json').write_text(json.dumps(state))
            with self.assertRaises(Blocked):QueryLedger(c,q.template)

    def test_F11_F20_real_query_crash_and_concurrent_reservation(self):
        context=multiprocessing.get_context('fork')
        for boundary in ('after_receipt_before_index','after_index_before_state','after_reservation'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as tmp:
                c=config(tmp);plan,q=prepare_plan(c,SPEC,*catalogs());q.bind('a'*64);query=plan['queries'][0]
                def crash():
                    child=QueryLedger(c,q.template)
                    def hook(event):
                        if event==boundary:os._exit(31)
                    if boundary=='after_reservation':
                        child.reserve_query(query,'PRIMARY');os._exit(31)
                    child.reserve_query(query,'PRIMARY',hook=hook)
                child=context.Process(target=crash);child.start();child.join(5);self.assertEqual(child.exitcode,31)
                if boundary=='after_reservation':
                    before=q.snapshot();q.recover_unknown(plan);after=q.snapshot();self.assertEqual(before['ops'],after['ops']);self.assertEqual(after['queries']['PRIMARY:'+query['query_id']]['status'],'UNKNOWN')
                    self.assertEqual(after['queries']['PRIMARY:'+query['query_id']]['charged_bytes'],2048)
                else:
                    with self.assertRaises(Blocked):q.snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);plan,q=prepare_plan(c,SPEC,*catalogs());q.bind('a'*64);event=context.Event();queue=context.Queue()
            def reserve(query):
                event.wait(3)
                try:QueryLedger(c,q.template).reserve_query(query,'PRIMARY');queue.put('RESERVED')
                except Blocked:queue.put('BLOCKED')
            children=[context.Process(target=reserve,args=(query,)) for query in plan['queries'][:2]]
            for child in children:child.start()
            event.set();results=[queue.get(timeout=5) for _ in children]
            for child in children:child.join(5);self.assertEqual(child.exitcode,0)
            self.assertEqual(sorted(results),['BLOCKED','RESERVED'])

    def test_F12_space_lost_before_F_checkpoint_retains_full_usage(self):
        from types import SimpleNamespace
        from civiclab.e02.full_adult_engine_v1_1 import supervise_fixture as supervisor
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);c['F_storage']['free']=100;c['limits']['free_disk_bytes']=100;ledger=FResourceLedger(c);path,m,a=source(c);e=enroll_F(ledger,path,m,a)
            patcher=patch('civiclab.e02.full_adult_control_v1_1.shutil.disk_usage',return_value=SimpleNamespace(free=0))
            def fill(*args,**kwargs):result=supervisor(*args,**kwargs);patcher.start();return result
            try:
                with patch('civiclab.e02.full_adult_engine_v1_1.supervise_fixture',side_effect=fill):
                    with self.assertRaises(Blocked):process_F(ledger,path,m,e)
                s=ledger.snapshot();key=s['processing_active'];self.assertEqual(s['processing'][key]['status'],'RESERVED')
                with self.assertRaises(Blocked):ledger.recover_unknown()
            finally:patcher.stop()
            ledger.recover_unknown();self.assertTrue(ledger.snapshot()['halted'])
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);c['F_storage']['free']=100;plan,q=prepare_plan(c,SPEC,*catalogs());q.bind('a'*64)
            with patch('civiclab.e02.full_adult_control_v1_1.shutil.disk_usage',return_value=SimpleNamespace(free=0)):
                with self.assertRaises(Blocked):q.reserve_query(plan['queries'][0],'PRIMARY')
            self.assertEqual(q.snapshot()['queries'],{})

    def test_F13_authored_BODY_failures_full_charge_no_network(self):
        from http.client import IncompleteRead
        for mode in ('partial','encoding','declared'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                c=config(tmp);ledger=FResourceLedger(c);r=FixtureResponse(b'x',url='fixture://F/01')
                if mode=='partial':r.error=IncompleteRead(b'PRIVATE_F_PARTIAL',3)
                if mode=='encoding':r.encoding='gzip'
                if mode=='declared':r.content_length=2
                with patch('socket.socket.connect',side_effect=AssertionError('network forbidden')):
                    with self.assertRaises(BaseException):acquire_fixture(ledger,'01',r)
                s=ledger.snapshot();self.assertEqual(s['body_charged'],c['limits']['archive_body_bytes']);self.assertTrue(s['halted'])
                self.assertNotIn('PRIVATE_F_PARTIAL',(ledger.path/'events.jsonl').read_text())

    def test_F14_source_drift_keys_header_and_released_count_fail(self):
        for kind in ('state','header','extra','count','drift'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                c=config(tmp);ledger=FResourceLedger(c);path,m,a=source(c)
                if kind=='state':m['state']='02'
                if kind=='header':m['header_sha256']='0'*64
                if kind=='extra':m['extra']='not allowed'
                a['manifest_sha256']=canonical_hash(m)
                if kind in ('state','header','extra'):
                    with self.assertRaises(Blocked):enroll_F(ledger,path,m,a)
                    continue
                e=enroll_F(ledger,path,m,a)
                if kind=='count':
                    m2=deepcopy(m);m2['members'][m2['person_member']]['bytes']+=1
                    with self.assertRaises(Blocked):parse_F(path,c,m2,e)
                else:
                    from civiclab.e02.full_adult_engine_v1_1 import inspect_F as original
                    count=[0]
                    def swap(*args,**kwargs):
                        result=original(*args,**kwargs);count[0]+=1
                        if count[0]==1:path.write_bytes(path.read_bytes()+b'drift')
                        return result
                    with patch('civiclab.e02.full_adult_engine_v1_1.inspect_F',side_effect=swap):
                        with self.assertRaises(Blocked):parse_F(path,c,m,e)

    def test_F15_parent_limits_and_F_artifact_caps(self):
        from civiclab.e02.national_population import supervise_fixture
        for case in ('rss','time','cancel'):
            with self.subTest(case=case):
                with self.assertRaises(Blocked):supervise_fixture(lambda:time.sleep(3),seconds=.1 if case=='time' else 2,rss_bytes=1 if case=='rss' else 512*1024**2,poll_seconds=.01,cancelled=lambda:case=='cancel')
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);c['F_storage']['caps']['scratch']=8;policy=Policy(c)
            with self.assertRaises(Blocked):policy.write(Path(tmp)/'scratch/overflow',b'x'*9)
            self.assertFalse((Path(tmp)/'scratch/overflow').exists())

    def test_F16_F17_F18_closed_vocabulary_privacy_and_actual_gate(self):
        actual=ROOT/'data/raw/e02_pums_wy/QUARANTINED-20f0ff6a0b674edc916272fd8b41ff4d.zip'
        with patch('pathlib.Path.open',side_effect=AssertionError('must refuse before actual read')):
            with self.assertRaises(Blocked):actual_source(actual)
        bad=json.loads((ROOT/'configs/e02_full_adult_engine_v1_1.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Blocked):fixture_root(tmp,bad,create=True)
        for text in ('{"x":NaN}','{"x":1,"x":2}'):
            with self.assertRaises(Blocked):strict_json(text)
        with self.assertRaises(Blocked):schema_check({}, {'$ref':'unimplemented'})
        selectors,coefs,queries=catalogs()
        for mutate in ('hash','kind','float_coefficient','extra'):
            a,b,d=deepcopy((selectors,coefs,queries))
            if mutate=='hash':a[0]['compiled_mask_sha256']='0'*64
            if mutate=='kind':d[0]['query_kind']='PROPORTION_COVARIANCE'
            if mutate=='float_coefficient':b[0]['terms'][0]['coefficient']=1.0
            if mutate=='extra':d[0]['unapproved']='PRIVATE'
            with self.subTest(mutate=mutate),self.assertRaises(Blocked):compile_plan(SPEC,a,b,d)

    def test_F20_failed_unknown_NULL_projection_and_zero_op_refusal(self):
        from civiclab.e02.full_adult_queries_v1_1 import null_result
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);plan,q=prepare_plan(c,SPEC,*catalogs());q.bind('a'*64);query=plan['queries'][0]
            q.reserve_query(query,'PRIMARY');before=q.snapshot();q.recover_unknown(plan);after=q.snapshot()
            self.assertEqual(before['ops'],after['ops']);self.assertEqual(before['bytes'],after['bytes'])
            record=null_result(query,'a'*64,SPEC,'UNKNOWN_AFTER_CRASH');self.assertIsNone(record['covariance_sdr'])
            validate_result(record,AdultMatrix(),query,'a'*64,SPEC)
            other=plan['queries'][1];q.refuse_query(other,'PRIMARY','a'*64,SPEC)
            s=q.snapshot();self.assertEqual(s['queries']['PRIMARY:'+other['query_id']]['cost'],0)
            self.assertEqual(s['ops'],after['ops']);self.assertLessEqual(s['queries']['PRIMARY:'+other['query_id']]['charged_bytes'],2048)


    def test_F04_exhaustive_recode_boundaries_and_bad_child(self):
        required=['RT','STATE','AGEP','CIT','RELSHIPP','SCHL','PWGTP']+['PWGTP'+str(i) for i in range(1,81)]+['FAGEP','FCITP','FSCHLP','FRELSHIPP']
        row=dict.fromkeys(required,'0');row.update(RT='P',STATE='01',PWGTP='9999')
        for i in range(1,81):row['PWGTP'+str(i)]=str(-9999 if i%2 else 9999)
        for age in (18,24,25,44,45,64,65,99):
            for cit in range(1,6):
                for res in range(20,39):
                    for edu in (1,17,18,20,21,24):
                        row.update(AGEP=str(age),CIT=str(cit),RELSHIPP=str(res),SCHL=str(edu))
                        index,w,reps,flags=parse_person(row,'01',required)
                        a=0 if age<=24 else 1 if age<=44 else 2 if age<=64 else 3
                        e=0 if edu<=17 else 1 if edu<=20 else 2
                        self.assertEqual(index,((a*3+e)*2+int(cit==5))*3+(0 if res<=36 else res-36))
        row.update(AGEP='2',SCHL='',CIT='5',RELSHIPP='38');self.assertIsNone(parse_person(row,'01',required)[0])
        for field,value in [('RT','H'),('STATE','02'),('PWGTP','0'),('PWGTP80','10000'),('FAGEP','2')]:
            bad={**row,field:value}
            with self.subTest(field=field),self.assertRaises(Blocked):parse_person(bad,'01',required)

    def test_F06_big_integer_quadratic_oracle(self):
        point=16095728*9999;reps=[-point,point]*40
        expected=sum((Fraction(v)-point)**2 for v in reps)
        numerator,variance,se,moe=moments(point,reps,Ops(1000))
        self.assertGreater(numerator,2**63);self.assertEqual(numerator,expected);self.assertEqual(variance,float(expected/20))

    def test_F11_clock_and_F20_partition_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=config(tmp);plan,q=prepare_plan(c,SPEC,*catalogs());created=q.snapshot()['created']
            for now in (created-1,created+c['limits']['batch_elapsed_seconds']+1):
                with self.assertRaises(Blocked):QueryLedger(c,q.template,clock=lambda:now)
        categories={'PRIMARY:base':'PRIMARY/base','REPLAY:base':'REPLAY/base','PRIMARY:catalog':'PRIMARY/selectors.json','REPLAY:catalog':'REPLAY/selectors.json','PRIMARY:query':'PRIMARY/covariance_results_v1_1.jsonl','REPLAY:query':'REPLAY/contrast_results_v1_1.jsonl','core':'core.bin','receipts':'analysis/query_receipts_v1_1.jsonl','scratch':'scratch/file','raw':'sources/a.zip'}
        for category,name in categories.items():
            with self.subTest(category=category),tempfile.TemporaryDirectory() as tmp:
                c=config(tmp);c['F_storage']['caps'][category]=0
                with self.assertRaises(Blocked):Policy(c).write(Path(tmp)/name,b'x')


def record_authored_run(root):
    """Explicit manual evidence driver; fictional sources only, no network/inference."""
    from datetime import datetime,timezone
    import platform
    from civiclab.e02.national_population import supervise_fixture as original_supervisor
    from civiclab.e02.full_adult_types_v1_1 import load_engine
    load_engine(ROOT)
    root=Path(root).resolve();started=datetime.now(timezone.utc).isoformat();begin=time.monotonic();observations=[]
    def observe(*args,**kwargs):
        value,resources=original_supervisor(*args,**kwargs);observations.append(resources);return value,resources
    c=config(root,rows=78)
    with patch('socket.socket.connect',side_effect=AssertionError('no network in F authored run')),patch('civiclab.e02.national_population.supervise_fixture',side_effect=observe),patch('civiclab.e02.full_adult_engine_v1_1.supervise_fixture',side_effect=observe):
        engine=FullAdultFixtureEngine(c,SPEC,*catalogs())
        for state in SPEC['universe']['state_fips']:
            path,m,a=source(c,state,full=True,anticorrelated=True);engine.source(path,m,a)
        matrices=engine.benchmark();results=engine.analyze()
    if matrices['PRIMARY'].blobs()!=matrices['REPLAY'].blobs() or results['PRIMARY']!=results['REPLAY']:raise AssertionError('MOCK replay mismatch')
    queries=engine.queries.snapshot();sources=engine.sources.snapshot();policy=Policy(c)
    receipt={'run_id':root.name,'kind':'MOCK_AUTHORED_F_ENGINE_V1_1','independent_acceptance':'PENDING','started_at_utc':started,'completed_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_wall_seconds':time.monotonic()-begin,'python':platform.python_version(),'seed':0,'generation':'deterministic authored values; no RNG/model sampling','runtime_config_sha256':canonical_hash(c),'specification_file_sha256':c['specification_sha256'],'code_and_test_pins':c['required_files'],'actual_person_rows_processed':0,'actual_source_requests':0,'model_calls':0,'actual_serving_provider':None,'api_model_cost_usd':0,'cost_scope':'local compute/storage and development assistant usage not priced','authored_all_age_rows_per_sweep':51*78,'authored_adult_rows_per_sweep':3672,'authored_C_rows_per_sweep':612,'primitive_components':293760,'primitive_payload_bytes':sum(map(len,matrices['PRIMARY'].blobs().values())),'source_coverage_states':len(sources['sources']),'source_processing_rows_charged':sources['processing_rows_charged'],'source_processing_seconds_charged':sources['processing_seconds_charged'],'query_ops_charged':queries['ops'],'query_ops_planned':engine.plan['total_ops'],'query_result_bytes_charged':queries['bytes'],'query_attempts':len(queries['queries']),'results':results,'primary_replay_exact':True,'resource_observations':observations,'max_sampled_child_rss_bytes':max(r['sampled_peak_rss_bytes'] for r in observations),'limits_semantics':'sampled child RSS and cooperative parent stopping; not absolute OS/wire/physical block caps','storage_before_receipt':policy.check(),'scientific_status':'BLOCKED_NO_REAL_POPULATION_OR_POLITICAL_PRIORS_OR_HUMAN_EFFECTS','actual_approvals':c['actual_approvals'],'errors':[],'exclusions':'6 authored under18 rows per state after required-domain validation; no adult domain removed'}
    policy.json(root/'fixture_receipt.json',receipt)
    files={str(p.relative_to(root)):sha256_file(p) for p in sorted(root.rglob('*')) if p.is_file()}
    policy.json(root/'artifact_hashes.json',{'kind':'MOCK_F_LOCAL_ONLY','files':files})
    print(json.dumps({'run_id':root.name,'receipt_sha256':sha256_file(root/'fixture_receipt.json'),'artifact_index_sha256':sha256_file(root/'artifact_hashes.json'),'elapsed_seconds':receipt['elapsed_wall_seconds'],'max_sampled_child_rss_bytes':receipt['max_sampled_child_rss_bytes'],'resource_observations':len(observations),'ops':queries['ops'],'storage_final':policy.check()},sort_keys=True))
    return receipt



def reseal_mutable_query_history(q,mutate):
    """Adversary reseals mutable state/receipt/index; frozen anchors unchanged."""
    anchors={n:(q.path/n).read_bytes() for n in ('plan_input.json','runtime_config.json','genesis.json')}
    state=json.loads((q.path/'state.json').read_text());receipts=[json.loads(x) for x in (q.path/'query_receipts_v1_1.jsonl').read_text().splitlines()];events=[json.loads(x) for x in (q.path/'events.jsonl').read_text().splitlines()]
    mutate(state,receipts)
    receipt_map={r['h']:r for r in receipts};previous=None;receipt_previous=None
    for i,event in enumerate(events):
        event['prev']=previous
        if i:event['before']=events[i-1]['after']
        if i==len(events)-1:event['after']=canonical_hash(state)
        if event['receipt'] is not None:
            r=receipt_map[event['receipt']];r['prev']=receipt_previous;r['state']=event['after'];r['h']=canonical_hash({k:v for k,v in r.items() if k!='h'});event['receipt']=r['h'];receipt_previous=r['h']
        event['h']=canonical_hash({k:v for k,v in event.items() if k!='h'});previous=event['h']
    (q.path/'state.json').write_text(json.dumps(state,sort_keys=True,indent=2)+'\n')
    from civiclab.e02.full_adult_queries_v1_1 import line
    (q.path/'query_receipts_v1_1.jsonl').write_bytes(b''.join(line(r) for r in receipts));(q.path/'events.jsonl').write_bytes(b''.join(line(e) for e in events))
    assert all((q.path/n).read_bytes()==v for n,v in anchors.items())
    return state,anchors


def probe_cost_attack(root,mode):
    c=config(root);plan,q=prepare_plan(c,SPEC,*catalogs());q.bind('a'*64);matrix=AdultMatrix()
    for s in range(51):matrix.mark_state(s)
    query=next(d for d in plan['queries'] if d['query_id']=='cov');execute_query(q,matrix,query,'a'*64,SPEC,'PRIMARY');before=q.snapshot();assert query['cost']==645
    def mutate(state,receipts):
        d=next(d for d in state['admitted']['queries'] if d['query_id']=='cov')
        if mode in ('zero','one_less'):
            delta=d['cost'] if mode=='zero' else 1;d['cost']-=delta;state['queries']['PRIMARY:cov']['cost']-=delta;state['ops']-=delta;state['admitted']['total_ops']-=2*delta
            for r in receipts:r['o']-=delta
        elif mode=='kind':d['query_kind']='COUNT_LINEAR_SIGNED'
        elif mode=='definition':
            d['definition_sha256']='f'*64
            for r in receipts:r['d']='f'*64
        elif mode=='total':state['admitted']['total_ops']-=1
        elif mode=='receipt_only':
            for r in receipts:r['o']=0
        else:raise AssertionError('bad authored cost attack')
    corrupted,anchors=reseal_mutable_query_history(q,mutate);paths=[q.path/n for n in ('state.json','query_receipts_v1_1.jsonl','events.jsonl')];snapshots=[p.read_bytes() for p in paths]
    attempts=0
    with patch('civiclab.e02.full_adult_queries_v1_1.evaluate_query',side_effect=AssertionError('must not evaluate after corrupted ledger')) as evaluated:
        for operation in (lambda:QueryLedger(c,q.template),lambda:q.reserve_query(plan['queries'][1],'PRIMARY'),lambda:execute_query(q,matrix,plan['queries'][1],'a'*64,SPEC,'PRIMARY')):
            try:operation()
            except Blocked:attempts+=1
            else:raise AssertionError('mutable coedit accepted')
        assert evaluated.call_count==0
    assert [p.read_bytes() for p in paths]==snapshots
    return {'kind':'MOCK_MUTABLE_COEDIT_REFUSED','mode':mode,'original_ops':before['ops'],'corrupt_claimed_ops':corrupted['ops'],'original_query_cost':645,'rejected_open_reserve_execute':attempts,'future_query_evaluations':0,'new_reservations':0,'anchors_unchanged':True}


def probe_width_case(root,target,kind):
    c=config(root);ledger=FResourceLedger(c);path,m,a=source(c,width_change=(target,kind));e=enroll_F(ledger,path,m,a)
    if kind=='empty':
        result,_=process_F(ledger,path,m,e);assert result['accounting']['all']['count']==12 and result['accounting']['adult']['count']==6
        return {'kind':'MOCK_VALID_EMPTY_UNUSED_ACCEPTED','target':target,'rows':12,'adults':6}
    try:process_F(ledger,path,m,e)
    except Blocked:pass
    else:raise AssertionError('malformed width accepted')
    s=ledger.snapshot();assert s['halted'];assert not any(v['status']=='MOCK_AGGREGATE_LOCAL_ONLY_PENDING_AUDIT' for k,v in s['processing'].items() if k.startswith('PRIMARY'))
    events=(ledger.path/'events.jsonl').read_text();assert 'PRIVATE_EXTRA_F' not in events and 'PRIVATE_F_AUTHOR_MARKER' not in events
    return {'kind':'MOCK_MALFORMED_WIDTH_REFUSED','target':target,'mode':kind,'halted':s['halted'],'rows_charged':s['processing_rows_charged'],'seconds_charged':s['processing_seconds_charged'],'actual_person_rows':0,'accepted_aggregate':False,'manifest_sha256':canonical_hash(m)}


class RemediationTests(unittest.TestCase):
    def test_IA_QUERY_COST_001_resealed_coedits_and_dispatch_arguments(self):
        for mode in ('zero','one_less','kind','definition','total','receipt_only'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:probe_cost_attack(tmp,mode)
        for mode in ('zero','one_less','kind','definition','vector','nonzero_count'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                c=config(tmp);plan,q=prepare_plan(c,SPEC,*catalogs());q.bind('a'*64);query=deepcopy(plan['queries'][0]);before=q.snapshot()
                if mode=='zero':query['cost']=0
                if mode=='one_less':query['cost']-=1
                if mode=='kind':query['query_kind']='COUNT_LINEAR_SIGNED'
                if mode=='definition':query['query_definition_sha256']='f'*64
                if mode=='vector':query['x']['vector']=[0]*3672
                if mode=='nonzero_count':query['x']['m']=0
                with patch('civiclab.e02.full_adult_queries_v1_1.evaluate_query') as evaluated:
                    with self.assertRaises(Blocked):execute_query(q,AdultMatrix(),query,'a'*64,SPEC,'PRIMARY')
                    self.assertEqual(evaluated.call_count,0)
                self.assertEqual(q.snapshot(),before)
                badplan=deepcopy(plan);badplan['queries'][0]=query
                with self.assertRaises(Blocked):q.admit(badplan)

    def test_IA_CSV_WIDTH_002_all_age_and_six_domains(self):
        for target in range(12):
            for kind in ('missing','extra','empty'):
                with self.subTest(target=target,kind=kind),tempfile.TemporaryDirectory() as tmp:probe_width_case(tmp,target,kind)
