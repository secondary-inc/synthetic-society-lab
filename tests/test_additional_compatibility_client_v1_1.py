"""Private fixed-run client fixtures; network/key boundaries always replaced."""
from contextlib import contextmanager
from copy import deepcopy
import json
import multiprocessing
import os
import shutil
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from civiclab.additional_compatibility_client_v1_1 import (
    execute_authored,code_contract,open_actual,_Journal,_Capability)
from test_additional_compatibility_owner_v1 import case
from test_production_price_v4 import catalog,COMPONENTS,T0
from test_production_compatibility_v4_2_1 import Stub


def raw_catalog():
    data=catalog();data['data']['id']='openai/gpt-4.1-nano'
    for i,e in enumerate(data['data']['endpoints']):
        e['model_id']='openai/gpt-4.1-nano';e['provider_name']='Azure'
        e['tag']='azure' if i==0 else 'azure/authored'
        e['pricing']={k:'0' for k in COMPONENTS};e['pricing']['request']='0.000340'
    return canonical_bytes(data)


@contextmanager
def client_case():
    with case() as (owner,original,b,x,release,clock,old):
        stub=Stub();stub.response['model']='openai/gpt-4.1-nano'
        stub.stats['data'].update(model='openai/gpt-4.1-nano',provider_name='Azure')
        er={'kind':'INDEPENDENT_ADDITIONAL_COMPATIBILITY_CLIENT_REVIEW_V1_1',
            'reviewer_role':'independent_auditor','review_id':uuid.uuid4().hex,
            'client_contract_hash':canonical_hash(code_contract()),'policy_hash':canonical_hash(b['policy']),
            'owner_assertion_hash':canonical_hash(b['owner_assertion']),'release_hash':canonical_hash(release)}
        args=(b['policy'],b['review'],b['approval'],b['owner_assertion'],release)
        kwargs={'expected':x,'executor_review':er,'expected_executor_review_hash':canonical_hash(er)}
        receipt={'url':'https://openrouter.ai/api/v1/models/openai/gpt-4.1-nano/endpoints',
                 'body_sha256':release['terms']['initial_catalog_sha256'],'observed_at_utc':T0.isoformat()}
        mono=[0.0]
        with patch('civiclab.additional_compatibility_client_v1_1._fetch_public_catalog',return_value=(raw_catalog(),receipt)) as fetch, \
             patch('civiclab.additional_compatibility_client_v1_1._read_environment_key',return_value=_Credential('AUTHORED_FAKE_ADDITIONAL_CREDENTIAL')) as key, \
             patch('civiclab.additional_compatibility_client_v1_1._transport',return_value=stub), \
             patch('civiclab.additional_compatibility_client_v1_1.time.monotonic',side_effect=lambda:mono[0]):
            yield args,kwargs,owner,stub,fetch,key,mono,old


def crash_client(home,args,kw,boundary,counts):
    from test_production_admission_v4 import account
    from civiclab.additional_compatibility_owner_v1 import _AdditionalOwnerV1
    stub=Stub();stub.response['model']='openai/gpt-4.1-nano'
    stub.stats['data'].update(model='openai/gpt-4.1-nano',provider_name='Azure')
    nativepost=stub.post_bytes;nativestats=stub.statistics
    def post(body):
        with counts.get_lock():counts[0]+=1
        result=nativepost(body)
        if boundary=='POST_RETURN':os._exit(81)
        return result
    def stats(identity):
        with counts.get_lock():counts[1]+=1
        result=nativestats(identity)
        if boundary=='STATS_RETURN':os._exit(82)
        return result
    stub.post_bytes=post;stub.statistics=stats
    nativewrite=_Journal.write;nativeevent=_Journal.event
    def write(j,name,value):
        result=nativewrite(j,name,value)
        if name==boundary:os._exit(83)
        return result
    def event(j,kind,**fields):
        result=nativeevent(j,kind,**fields)
        if kind==boundary:os._exit(84)
        return result
    nativetransition=_AdditionalOwnerV1.transition
    def transition(owner,receipt,status,**fields):
        result=nativetransition(owner,receipt,status,**fields)
        if status==boundary:os._exit(85)
        return result
    terms=args[4]['terms']
    metadata={'url':'https://openrouter.ai/api/v1/models/openai/gpt-4.1-nano/endpoints',
        'body_sha256':terms['initial_catalog_sha256'],'observed_at_utc':T0.isoformat()}
    with account(Path(home)), \
        patch('civiclab.additional_compatibility_client_v1_1._fetch_public_catalog',return_value=(raw_catalog(),metadata)), \
        patch('civiclab.additional_compatibility_client_v1_1._read_environment_key',return_value=_Credential('AUTHORED_FAKE_ADDITIONAL_CREDENTIAL')), \
        patch('civiclab.additional_compatibility_client_v1_1._transport',return_value=stub), \
        patch.object(_Journal,'write',write),patch.object(_Journal,'event',event), \
        patch.object(_AdditionalOwnerV1,'transition',transition):
        try:execute_authored(*args,**kw)
        except (ExecutionBlocked,FileExistsError):
            if boundary!='RACE':raise


def retain_authored_evidence(destination):
    root=Path(destination).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    records={}
    for mode in ('success','ack-failure','post-error','invalid-billing','late-billing','alias-mutation'):
        with client_case() as (args,kw,owner,stub,fetch,key,mono,old):
            manager=patch.object(_Journal,'write',_Journal.write)
            if mode=='ack-failure':
                native=_Journal.write
                def write(j,name,value):
                    if name=='acknowledgement':raise OSError('AUTHORED_ACK_FAILURE')
                    return native(j,name,value)
                manager=patch.object(_Journal,'write',write)
            elif mode=='post-error':stub.post_error=TimeoutError('AUTHORED_TIMEOUT')
            elif mode=='invalid-billing':stub.stats['data']['native_tokens_prompt']=True
            elif mode=='late-billing':
                native=stub.statistics
                def stats(identity):result=native(identity);mono[0]=121;return result
                stub.statistics=stats
            submitted_args=deepcopy(args);submitted_kwargs=deepcopy(kw)
            if mode=='alias-mutation':
                from datetime import timedelta
                metadata=fetch.return_value
                def drift(model):
                    m,r,a,o,release=args
                    m['valid_until_utc']=(T0+timedelta(seconds=599)).isoformat()
                    r['policy_hash']=canonical_hash(m)
                    a['valid_until_utc']=m['valid_until_utc'];a['review_hash']=canonical_hash(r)
                    o.update(policy_hash=canonical_hash(m),review_hash=canonical_hash(r),approval_hash=canonical_hash(a))
                    kw['expected'].update({k:canonical_hash(v) for k,v in zip(
                        ('policy','review','approval','owner_assertion'),(m,r,a,o))})
                    return metadata
                fetch.side_effect=drift
            outcome=None
            with manager:
                try:outcome=execute_authored(*args,**kw)['summary']
                except ExecutionBlocked as e:outcome={'diagnostic':e.diagnostic}
            from civiclab.production_owner_v4 import pwd
            source=Path(pwd.getpwuid(os.getuid()).pw_dir)
            target=root/mode;shutil.copytree(source,target/'AUTHORED_OS_HOME')
            record={'mode':mode,'fixture_only':True,'source_scope':'AUTHORED fake OS home/reviews/catalog/credential/replies',
                'policy':submitted_args[0],'review':submitted_args[1],'approval':submitted_args[2],'owner_assertion':submitted_args[3],
                'release':submitted_args[4],'expected':submitted_kwargs,'outcome':outcome,'old_row':old,
                'caller_after':{'policy':args[0],'expected':kw['expected']},
                'caller_mutation_observed':args[0]!=submitted_args[0],
                'catalog_calls':fetch.call_count,'credential_boundary_calls':key.call_count,
                'POST_attempts':len(stub.posts),'statistics_attempts':len(stub.lookups),
                'snapshot':owner.snapshot()}
            (target/'fixture-record.json').write_bytes(canonical_bytes(record))
            records[mode]={'POST_attempts':len(stub.posts),'statistics_attempts':len(stub.lookups)}
    index={str(p.relative_to(root)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
           for p in sorted(root.rglob('*')) if p.is_file()}
    value={'kind':'AUTHORED_ADDITIONAL_COMPATIBILITY_CLIENT_V1_1_EVIDENCE','fixtures':records,'files':index,
           'actual_owner_key_network_model_access':0}
    (root/'AUTHORED_EVIDENCE_INDEX.json').write_bytes(canonical_bytes(value));return value


class AdditionalClientRemedyTests(unittest.TestCase):
    def test_live_factory_always_denies_before_arguments_and_os(self):
        class Bomb:
            def __getattribute__(self,key):raise AssertionError('argument touched')
        with patch('civiclab.production_owner_v4.pwd.getpwuid',side_effect=AssertionError('OS read')):
            with self.assertRaises(ExecutionBlocked):open_actual(Bomb())

    def test_success_one_bound_post_one_stats_old_hold_preserved_fixed_run(self):
        with client_case() as (args,kw,owner,stub,fetch,key,mono,old):
            result=execute_authored(*args,**kw)
            self.assertEqual(result['summary']['status'],'COMPATIBLE')
            self.assertEqual(stub.posts,[canonical_bytes(args[4]['request']['payload'])])
            self.assertEqual(stub.lookups,[stub.response['id']])
            self.assertEqual(fetch.call_count,1);self.assertEqual(key.call_count,1)
            snap=owner.snapshot();self.assertEqual(snap['consumed_microusd']['total'],341)
            self.assertIn(old,snap['charges']);self.assertEqual(snap['consumed_microusd']['dispatches'],2)
            path=Path(result['path']);self.assertEqual(path,owner.directory/'additional-test-v1'/args[0]['new_run_id'])
            for name in ('manifest','acknowledgement','dispatch-consumed','phase','billing','summary'):
                self.assertTrue((path/(name+'.local.json')).is_file())
            self.assertTrue(all(b'AUTHORED_FAKE_ADDITIONAL_CREDENTIAL' not in p.read_bytes() for p in path.iterdir()))
            with self.assertRaises((ExecutionBlocked,FileExistsError)):execute_authored(*args,**kw)
            self.assertEqual(len(stub.posts),1);self.assertEqual(fetch.call_count,1)

    def test_stale_external_client_review_and_missing_expected_refuse_before_home_or_http(self):
        for mode in ('client','expected'):
            with self.subTest(mode=mode),client_case() as (args,kw,owner,stub,fetch,key,mono,old):
                if mode=='client':kw['expected_executor_review_hash']='0'*64
                else:kw['expected']=None
                with patch('civiclab.production_owner_v4.pwd.getpwuid',side_effect=AssertionError('OS read')):
                    with self.assertRaises(ExecutionBlocked):execute_authored(*args,**kw)
                fetch.assert_not_called();key.assert_not_called();self.assertEqual(stub.posts,[])

    def test_preflight_history_drift_stops_before_catalog_key_and_model(self):
        with client_case() as (args,kw,owner,stub,fetch,key,mono,old):
            # Drift the immutable head anchor after policy freeze. Refusal
            # must precede any catalog/key/model operation.
            from civiclab.common import atomic_json
            head=json.loads(owner.anchor.read_text());head['sequence']+=1
            atomic_json(owner.anchor,head)
            with self.assertRaises(ExecutionBlocked):execute_authored(*args,**kw)
            fetch.assert_not_called();key.assert_not_called();self.assertEqual(stub.posts,[])

    def test_ack_failure_and_lost_reservation_return_never_post_and_hold_added_reservation(self):
        for mode in ('ack','return'):
            with self.subTest(mode=mode),client_case() as (args,kw,owner,stub,fetch,key,mono,old):
                if mode=='ack':
                    native=_Journal.write
                    def write(j,name,value):
                        if name=='acknowledgement':raise OSError('AUTHORED_ACK_FAILURE')
                        return native(j,name,value)
                    manager=patch.object(_Journal,'write',write)
                else:
                    from civiclab.additional_compatibility_owner_v1 import _AdditionalOwnerV1
                    native=_AdditionalOwnerV1.append_authored_batch
                    def lost(o,*a,**k):native(o,*a,**k);raise OSError('AUTHORED_LOST_RETURN')
                    manager=patch.object(_AdditionalOwnerV1,'append_authored_batch',lost)
                with manager:
                    with self.assertRaises(ExecutionBlocked) as error:execute_authored(*args,**kw)
                snap=owner.snapshot();self.assertEqual(snap['consumed_microusd']['total'],680)
                self.assertEqual(snap['consumed_microusd']['dispatches'],2);self.assertIn(old,snap['charges'])
                self.assertEqual(stub.posts,[]);self.assertEqual(stub.lookups,[])
                if mode=='return':self.assertIsNone(error.exception.diagnostic['reservation_recorded'])
                with self.assertRaises((FileExistsError,ExecutionBlocked)):execute_authored(*args,**kw)

    def test_capability_consume_or_post_intent_failure_blocks_http(self):
        for boundary in ('dispatch-consumed','post-intent'):
            with self.subTest(boundary=boundary),client_case() as (args,kw,owner,stub,fetch,key,mono,old):
                nativewrite=_Journal.write;nativeevent=_Journal.event
                def write(j,name,value):
                    if boundary=='dispatch-consumed' and name=='dispatch-consumed':raise OSError('AUTHORED')
                    return nativewrite(j,name,value)
                def event(j,kind,**fields):
                    if boundary=='post-intent' and kind=='MODEL_POST_INTENT':raise OSError('AUTHORED')
                    return nativeevent(j,kind,**fields)
                with patch.object(_Journal,'write',write),patch.object(_Journal,'event',event):
                    with self.assertRaises(ExecutionBlocked):execute_authored(*args,**kw)
                self.assertEqual(stub.posts,[]);self.assertEqual(owner.snapshot()['consumed_microusd']['total'],680)

    def test_bad_or_missing_generation_id_does_not_issue_statistics(self):
        for identity in (None,'wrong-id','gen-with space'):
            with self.subTest(identity=identity),client_case() as (args,kw,owner,stub,fetch,key,mono,old):
                stub.response['id']=identity
                with self.assertRaises(ExecutionBlocked):execute_authored(*args,**kw)
                self.assertEqual(len(stub.posts),1);self.assertEqual(stub.lookups,[])
                self.assertEqual(owner.snapshot()['consumed_microusd']['total'],680)

    def test_malformed_answer_is_billed_quality_failure_without_repair(self):
        with client_case() as (args,kw,owner,stub,fetch,key,mono,old):
            stub.response['choices'][0]['message']['content']='{"ok":1}'
            result=execute_authored(*args,**kw)
            self.assertEqual(result['summary']['status'],'CHARGED_QUALITY_FAILURE')
            self.assertEqual(len(stub.posts),1);self.assertEqual(len(stub.lookups),1)

    def test_invalid_billing_and_auxiliary_activity_hold_and_stop(self):
        for field,value in (('total_cost',None),('native_tokens_prompt',True),('provider_name','Other'),
                            ('num_media_prompt',1),('is_byok',True)):
            with self.subTest(field=field),client_case() as (args,kw,owner,stub,fetch,key,mono,old):
                stub.stats['data'][field]=value
                with self.assertRaises(ExecutionBlocked):execute_authored(*args,**kw)
                self.assertEqual(len(stub.posts),1);self.assertEqual(len(stub.lookups),1)
                self.assertEqual(owner.snapshot()['consumed_microusd']['total'],680)

    def test_late_post_reply_cannot_start_statistics_and_late_complete_bill_is_accounted(self):
        for late_stage in ('post','billing'):
            with self.subTest(late_stage=late_stage),client_case() as (args,kw,owner,stub,fetch,key,mono,old):
                if late_stage=='post':
                    native=stub.post_bytes
                    def post(body):result=native(body);mono[0]=121;return result
                    stub.post_bytes=post
                    with self.assertRaises(ExecutionBlocked):execute_authored(*args,**kw)
                    self.assertEqual(stub.lookups,[])
                    self.assertEqual(owner.snapshot()['consumed_microusd']['total'],680)
                else:
                    native=stub.statistics
                    def stats(identity):result=native(identity);mono[0]=121;return result
                    stub.statistics=stats
                    result=execute_authored(*args,**kw)
                    self.assertEqual(result['summary']['status'],'TIMING_FAILURE')
                    self.assertEqual(result['summary']['reported_provider_cost_microusd'],1)
                    self.assertEqual(result['summary']['charged_microusd'],340)
                    snap=owner.snapshot();self.assertEqual(snap['consumed_microusd']['total'],680)
                    row=next(r for r in snap['charges'] if r['id']!=old['id'])
                    self.assertEqual(row['status'],'UNCERTAIN');self.assertEqual(row['observed_cost'],1)
                    self.assertIsNotNone(row['billing']);self.assertIsNone(row['checkpoint_hash'])

    def test_arbitrary_exception_text_and_response_secret_not_persisted(self):
        for mode in ('exception','response'):
            with self.subTest(mode=mode),client_case() as (args,kw,owner,stub,fetch,key,mono,old):
                if mode=='exception':stub.post_error=RuntimeError('AUTHORED_FAKE_ADDITIONAL_CREDENTIAL')
                else:stub.response['secret']='AUTHORED_FAKE_ADDITIONAL_CREDENTIAL'
                with self.assertRaises(ExecutionBlocked):execute_authored(*args,**kw)
                path=owner.directory/'additional-test-v1'/args[0]['new_run_id']
                self.assertTrue(all(b'AUTHORED_FAKE_ADDITIONAL_CREDENTIAL' not in p.read_bytes() for p in path.iterdir()))

    def test_external_boolean_cannot_construct_dispatch_capability(self):
        with self.assertRaises(ExecutionBlocked):_Capability(True,None,None,None,None,None,None)

    def test_native_crashes_ack_consume_intent_replies_checkpoint_and_owner_commit_never_retry(self):
        from civiclab.production_owner_v4 import pwd
        boundaries=['acknowledgement','dispatch-consumed','MODEL_POST_INTENT','POST_RETURN',
                    'RESPONSE_SEEN','STATISTICS_GET_INTENT','STATS_RETURN','phase','PHASE_COMMITTED','summary']
        ctx=multiprocessing.get_context('spawn')
        for boundary in boundaries:
            with self.subTest(boundary=boundary),client_case() as (args,kw,owner,stub,fetch,key,mono,old):
                counts=ctx.Array('i',[0,0]);home=pwd.getpwuid(os.getuid()).pw_dir
                child=ctx.Process(target=crash_client,args=(home,args,kw,boundary,counts))
                child.start();child.join(15)
                if child.is_alive():child.kill();child.join();self.fail('crash child exceeded bound')
                self.assertIn(child.exitcode,(81,82,83,84,85))
                no_post=boundary in ('acknowledgement','dispatch-consumed','MODEL_POST_INTENT')
                no_stats=no_post or boundary in ('POST_RETURN','RESPONSE_SEEN','STATISTICS_GET_INTENT')
                self.assertEqual(list(counts),[0 if no_post else 1,0 if no_stats else 1])
                snap=owner.snapshot();self.assertEqual(snap['consumed_microusd']['dispatches'],2)
                self.assertEqual(snap['consumed_microusd']['total'],341 if boundary in ('phase','PHASE_COMMITTED','summary') else 680)
                self.assertIn(old,snap['charges'])
                with self.assertRaises((ExecutionBlocked,FileExistsError)):execute_authored(*args,**kw)
                self.assertEqual(list(counts),[0 if no_post else 1,0 if no_stats else 1])
                self.assertEqual(stub.posts,[]);fetch.assert_not_called();key.assert_not_called()

    def test_two_native_clients_compete_for_same_fixed_run_one_post_and_one_bill_only(self):
        from civiclab.production_owner_v4 import pwd
        ctx=multiprocessing.get_context('spawn')
        with client_case() as (args,kw,owner,stub,fetch,key,mono,old):
            counts=ctx.Array('i',[0,0]);home=pwd.getpwuid(os.getuid()).pw_dir
            children=[ctx.Process(target=crash_client,args=(home,args,kw,'RACE',counts)) for _ in range(2)]
            for child in children:child.start()
            for child in children:
                child.join(15)
                if child.is_alive():child.kill();child.join();self.fail('client race exceeded bound')
                self.assertEqual(child.exitcode,0)
            self.assertEqual(list(counts),[1,1]);self.assertEqual(owner.snapshot()['consumed_microusd']['dispatches'],2)

    def test_retained_fixture_helper_records_real_boundaries_and_original_unknown_row(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve()/'retained';value=retain_authored_evidence(root)
            self.assertEqual(set(value['fixtures']),{'success','ack-failure','post-error','invalid-billing','late-billing','alias-mutation'})
            self.assertEqual(value['fixtures']['ack-failure'],{'POST_attempts':0,'statistics_attempts':0})
            self.assertEqual(value['fixtures']['post-error'],{'POST_attempts':1,'statistics_attempts':0})
            for name in value['fixtures']:
                record=json.loads((root/name/'fixture-record.json').read_text())
                self.assertIn(record['old_row'],record['snapshot']['charges'])
                self.assertEqual(record['snapshot']['consumed_microusd']['dispatches'],2)
            for name,ref in value['files'].items():
                raw=(root/name).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256'])
                self.assertNotIn(b'AUTHORED_FAKE_ADDITIONAL_CREDENTIAL',raw)

    def test_catalog_callback_coedited_authority_aliases_do_not_change_approved_snapshot(self):
        from datetime import timedelta
        with client_case() as (args,kw,owner,stub,fetch,key,mono,old):
            submitted=deepcopy((args,kw));original_policy_hash=canonical_hash(args[0])
            original_assertion_hash=canonical_hash(args[3])
            def mutate(model):
                m,r,a,o,release=args
                m['valid_until_utc']=(T0+timedelta(seconds=599)).isoformat()
                r['policy_hash']=canonical_hash(m)
                a['valid_until_utc']=m['valid_until_utc'];a['review_hash']=canonical_hash(r)
                o.update(policy_hash=canonical_hash(m),review_hash=canonical_hash(r),approval_hash=canonical_hash(a))
                kw['expected'].update({k:canonical_hash(v) for k,v in zip(
                    ('policy','review','approval','owner_assertion'),(m,r,a,o))})
                return raw_catalog(),{'url':'https://openrouter.ai/api/v1/models/openai/gpt-4.1-nano/endpoints',
                    'body_sha256':release['terms']['initial_catalog_sha256'],'observed_at_utc':T0.isoformat()}
            fetch.side_effect=mutate
            result=execute_authored(*args,**kw)
            self.assertEqual(result['summary']['status'],'COMPATIBLE');self.assertEqual(len(stub.posts),1)
            manifest=json.loads((Path(result['path'])/'manifest.local.json').read_text())
            self.assertEqual(manifest['policy_hash'],original_policy_hash)
            self.assertEqual(manifest['owner_assertion_hash'],original_assertion_hash)
            with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
            self.assertEqual(state['_amendment_bundle']['policy'],submitted[0][0])
            self.assertEqual(state['_amendment_bundle']['owner_assertion'],submitted[0][3])
            self.assertNotEqual(canonical_hash(args[0]),original_policy_hash)

    def test_catalog_callback_mutates_caller_payload_and_executor_review_but_sent_bytes_stay_approved(self):
        with client_case() as (args,kw,owner,stub,fetch,key,mono,old):
            approved=canonical_bytes(args[4]['request']['payload']); metadata=fetch.return_value
            def mutate(model):
                args[4]['request']['payload']['messages'][1]['content']='AUTHORED_UNAPPROVED_CHANGED_PROMPT'
                args[4]['request']['payload']['seed']=7
                kw['executor_review']['policy_hash']='f'*64
                kw['expected_executor_review_hash']='e'*64
                return metadata
            fetch.side_effect=mutate
            result=execute_authored(*args,**kw)
            self.assertEqual(result['summary']['status'],'COMPATIBLE')
            self.assertEqual(stub.posts,[approved])


if __name__=='__main__':unittest.main()
