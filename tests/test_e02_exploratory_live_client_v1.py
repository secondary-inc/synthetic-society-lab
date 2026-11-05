"""Authored fake-owner/transport integration. No actual account or responses."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from civiclab.e02 import exploratory_live_client_v1 as client
from civiclab.e02.exploratory_sequence_v1 import next_action
from test_production_price_v4 import fixture_contract,T0

PROTOCOL=(Path(__file__).resolve().parents[1]/'configs/e02_exploratory_live_pilot_v1_1.json').read_bytes()


class FakeOwner:
    """Independent simple fixture state machine, not the financial implementation."""
    def __init__(self,directory,packet):
        self.directory=Path(directory).resolve();self.packet=packet;self.rows={};self.transcript=[]
        self.calls=[];self.claims=set();self.stopped=False;self.analysis_status='READY';self.callback=None
        self.old_hold=340;self.clock=[T0];self.bad_ack=False
    def snapshot(self):return {'charges':deepcopy(list(self.rows.values()))}
    def study_snapshot(self):
        action=next_action(PROTOCOL,self.packet['price_release']['terms'],canonical_bytes(self.transcript))
        return {'status':'STOPPED' if self.stopped else 'COMPLETE' if action['status']=='COMPLETE' else 'ACTIVE' if self.rows else 'NOT_STARTED',
                'transcript':deepcopy(self.transcript),'study_charged_microusd':sum(r['charged'] for r in self.rows.values()),
                'study_dispatches':len(self.rows),'consumed_microusd':{'total':self.old_hold+sum(r['charged'] for r in self.rows.values())},
                'analysis_status':self.analysis_status,'failure_reason':None}
    def reserve_next(self,packet,proof,*,expected_packet_hash,transport_ready):
        if self.callback:self.callback()
        if any(r['status']!='PHASE_COMMITTED' for r in self.rows.values()):raise ExecutionBlocked('unfinished')
        action=next_action(PROTOCOL,packet['price_release']['terms'],canonical_bytes(self.transcript))
        if action['status'] in ('COMPLETE','STOPPED'):return self.study_snapshot()
        compiled=action['request'];receipt=f'{len(self.rows)+1:032x}'
        context={'run_id':packet['policy']['run_id'],'unit_id':'exploratory-'+str(compiled['execution_order']).zfill(2),
            'phase':compiled['phase'],'payload_hash':compiled['payload_sha256'],'envelope':compiled['envelope'],
            'terms':packet['price_release']['terms']}
        if transport_ready(context) is not True:raise ExecutionBlocked('transport unready')
        row={'id':receipt,'status':'STARTED','reserved':compiled['envelope']['reserved_microusd'],
             'charged':compiled['envelope']['reserved_microusd'],'context':deepcopy(context),
             'output_hash':None,'generation_id':None,'observed_cost':None,'billing':None}
        self.rows[receipt]=row;self.calls.append('RESERVE')
        result={'status':'RESERVED','receipt':receipt,'head':{'fixture_head':len(self.rows)},
                'request':compiled,'context':context,'plan':{'fixture_plan':True}}
        if self.bad_ack:result['context']['payload_hash']='0'*64
        return result
    def transition(self,receipt,status,**fields):
        row=self.rows[receipt];old=row['status'];self.calls.append(status)
        allowed={'STARTED':{'RESPONSE_SEEN','UNCERTAIN'},'RESPONSE_SEEN':{'SETTLED','UNCERTAIN','OVERRUN'},'SETTLED':{'UNCERTAIN'}}
        if status not in allowed.get(old,set()):raise ExecutionBlocked('bad transition')
        if row['output_hash'] is not None and fields.get('output_hash',row['output_hash'])!=row['output_hash']:
            raise ExecutionBlocked('immutable response output')
        row.update(fields,status=status)
        if status=='SETTLED':row['charged']=fields['observed_cost']
        if status in ('UNCERTAIN','OVERRUN'):
            row['charged']=max(row['charged'],row['reserved'],fields.get('observed_cost') or 0)
            self.stopped=True
            if fields.get('error_type')=='AnalysisRepresentationBound':self.analysis_status='NOT_RUN'
            compiled=next_action(PROTOCOL,self.packet['price_release']['terms'],canonical_bytes(self.transcript))['request']
            self.transcript.append({'execution_order':compiled['execution_order'],'phase':compiled['phase'],
                'payload_sha256':compiled['payload_sha256'],'status':'FAILED_UNCERTAIN','answer':None})
        return deepcopy(row)
    def claim_statistics_lookup(self,receipt):
        self.calls.append('STATISTICS_CLAIM')
        if self.rows[receipt]['status']!='RESPONSE_SEEN' or receipt in self.claims:raise ExecutionBlocked('duplicate claim')
        generation=self.rows[receipt]['generation_id']
        if any(rid!=receipt and r['generation_id']==generation for rid,r in self.rows.items()):raise ExecutionBlocked('duplicate generation')
        self.claims.add(receipt);return generation
    def commit_survey(self,receipt):
        self.calls.append('COMMIT');row=self.rows[receipt]
        if row['status']!='SETTLED':raise ExecutionBlocked('unsettled')
        path=self.directory/'limited-pilot-v1'/self.packet['policy']['run_id']
        checkpoint=json.loads((path/(receipt+'-checkpoint.json')).read_bytes())
        response_raw=(path/(receipt+'-response.json')).read_bytes()
        stats=json.loads((path/(receipt+'-statistics.json')).read_bytes())['data']
        parsed=client.parse_survey(json.loads(response_raw));output={'status':parsed['status'],'answer':parsed['answer'],
            'response_raw_sha256':hashlib.sha256(response_raw).hexdigest()}
        if checkpoint['output']!=output or canonical_hash(output)!=row['output_hash']:raise ExecutionBlocked('checkpoint output differs')
        if stats['id']!=row['generation_id'] or stats['provider_name']!=row['billing']['provider_name']:
            raise ExecutionBlocked('statistics mismatch')
        compiled=next_action(PROTOCOL,self.packet['price_release']['terms'],canonical_bytes(self.transcript))['request']
        self.transcript.append({'execution_order':compiled['execution_order'],'phase':compiled['phase'],
            'payload_sha256':compiled['payload_sha256'],'status':parsed['status'],'answer':parsed['answer']})
        row['status']='PHASE_COMMITTED'


class FakeTransport:
    def __init__(self,owner):
        self.owner=owner;self.posts=0;self.gets=0;self.post_hook=None;self.stats_hook=None
    def post_bytes(self,body):
        self.posts+=1;self.owner.calls.append('POST')
        payload=json.loads(body);request=json.loads(payload['messages'][1]['content'])
        answer={'democratic_party':50,'republican_party':50}
        response={'id':f'gen-authored-{self.posts}','model':payload['model'],'choices':[{'message':{'content':json.dumps(answer)}}],
                  'usage':{'cost':'0.000001','prompt_tokens':1,'completion_tokens':1}}
        if self.post_hook:self.post_hook(response,request)
        return response
    def statistics(self,generation):
        self.gets+=1;self.owner.calls.append('GET')
        result={'data':{'id':generation,'model':self.owner.packet['price_release']['terms']['model'],
            'provider_name':self.owner.packet['price_release']['terms']['reported_provider'],'is_byok':False,'total_cost':'0.000001',
            'native_tokens_prompt':1,'native_tokens_completion':1,'native_tokens_reasoning':0}}
        if self.stats_hook:self.stats_hook(result)
        return result


@contextmanager
def case():
    raw,decision,terms,metadata=fixture_contract()
    packet={'policy':{'run_id':'AUTHORED-PILOT','valid_from_utc':(T0-timedelta(seconds=1)).isoformat(),
                      'valid_until_utc':(T0+timedelta(hours=1)).isoformat()},
            'price_release':{'terms':terms,'interpretation':decision}}
    mono=[0.0];clock=[T0]
    with tempfile.TemporaryDirectory() as tmp:
        owner=FakeOwner(tmp,packet);transport=FakeTransport(owner)
        with patch.object(client,'_validate_packet',side_effect=lambda p,**kw:deepcopy(p)) as validate, \
             patch.object(client,'_owner',return_value=owner) as owner_factory, \
             patch.object(client,'_read_environment_key',return_value=_Credential('AUTHORED_CREDENTIAL_NO_ACTUAL_ACCESS')) as key, \
             patch.object(client,'_transport',return_value=transport), \
             patch.object(client,'_fetch_public_catalog',return_value=(raw,metadata)) as fetch, \
             patch.object(client,'new_operation_time',side_effect=lambda:clock[0]), \
             patch.object(client.time,'monotonic',side_effect=lambda:mono[0]):
            yield packet,owner,transport,fetch,key,mono,clock,owner_factory


def execute(packet):return client.execute_authored(packet,expected_packet_hash=canonical_hash(packet))


class ParserTests(unittest.TestCase):
    def parse(self,value):return client.parse_survey({'choices':[{'message':{'content':value}}]})
    def test_valid_and_invalid_survey_json_preserved_exactly(self):
        for value in [{'democratic_party':12.5,'republican_party':None},{'ok':True},True,None,[1,2],50]:
            parsed=self.parse(json.dumps(value));self.assertEqual(parsed['status'],'ANSWER');self.assertEqual(parsed['answer'],value)
    def test_duplicate_nonfinite_overflow_extra_value_and_bounds(self):
        for text in ['{"x":1,"x":2}','NaN','Infinity','1e999','{} {}','"'+'x'*257+'"',
                     '{"'+'k'*65+'":1}','['*10+'0'+']'*10,'1'*33,'"'+'z'*2049+'"']:
            with self.subTest(text=text[:20]):self.assertEqual(self.parse(text)['status'],'PARSE_ERROR')
    def test_content_utf8_not_character_bound_and_surrogates(self):
        for text in ['"'+'😀'*512+'"','\ud800']:
            self.assertEqual(self.parse(text)['status'],'PARSE_ERROR')
    def test_escaped_surrogate_preserved_as_exact_invalid_survey_json(self):
        parsed=self.parse('"\\ud800"')
        self.assertEqual(parsed['status'],'ANSWER')
        self.assertEqual(parsed['answer'],'\ud800')
        self.assertEqual(canonical_bytes(parsed['answer']),b'"\\ud800"')
    def test_exact_one_choice_and_content_type(self):
        for response in [{},{'choices':[]},{'choices':[{},{}]},{'choices':[{'message':{'content':None}}]}]:
            self.assertEqual(client.parse_survey(response)['status'],'PARSE_ERROR')
    def test_unicode_canonical_expansion_guard(self):
        parsed=self.parse(json.dumps(['é'*170]*4,ensure_ascii=False))
        self.assertEqual(parsed['status'],'ANSWER')
        with self.assertRaises(client.AnalysisRepresentationBound):
            client.phase_record({'execution_order':0,'phase':'pre','payload_sha256':'0'*64},parsed)


class ClientTests(unittest.TestCase):
    def test_complete_32_phases_authenticated_mock_zero_injected_effect(self):
        with case() as (p,o,t,fetch,key,*_):
            result=execute(p)
            self.assertEqual((t.posts,t.gets),(32,32));fetch.assert_called_once();key.assert_called_once()
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual(result['analysis']['estimate_thermometer_points'],0)
            self.assertEqual(result['analysis']['response_provenance'],'MOCK')
            self.assertEqual(len(result['response_envelope']['records']),32)
            self.assertEqual(o.old_hold,340)
            directory=Path(result['path']);self.assertLessEqual(len(list(directory.iterdir())),256)
            self.assertTrue(all(f.stat().st_mode&0o777==0o600 for f in directory.iterdir()))
            order=o.calls[:8];self.assertEqual(order,['RESERVE','POST','RESPONSE_SEEN','STATISTICS_CLAIM','GET','SETTLED','COMMIT','RESERVE'])
    def test_primary_replay_on_new_authored_homes_same_answers_scores(self):
        outputs=[]
        for _ in range(2):
            with case() as (p,*_):outputs.append(execute(p))
        self.assertEqual(outputs[0]['response_envelope'],outputs[1]['response_envelope'])
        self.assertEqual(outputs[0]['analysis'],outputs[1]['analysis'])
    def test_parse_error_pre_skips_only_own_post_and_is_charged(self):
        with case() as (p,o,t,*_):
            def hook(response,request):
                if t.posts==1:response['choices'][0]['message']['content']='bad JSON'
            t.post_hook=hook;result=execute(p)
            self.assertEqual((t.posts,t.gets),(31,31))
            self.assertEqual(result['analysis']['complete_blocks'],7)
            self.assertEqual(result['response_envelope']['records'][1]['status'],'SKIPPED_INVALID_PRE')
            self.assertTrue(all(r['charged']==1 for r in o.rows.values()))
    def test_invalid_survey_pre_preserved_and_skipped(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:r['choices'][0]['message'].update(content='{"democratic_party":true,"republican_party":50}') if t.posts==1 else None
            result=execute(p)
            self.assertEqual(t.posts,31);self.assertEqual(result['response_envelope']['records'][0]['status'],'ANSWER')
            self.assertIs(result['response_envelope']['records'][0]['answer']['democratic_party'],True)
    def test_invalid_post_excludes_block_without_replacement(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:r['choices'][0]['message'].update(content='{}') if t.posts==2 else None
            result=execute(p);self.assertEqual(t.posts,32);self.assertEqual(result['analysis']['complete_blocks'],7)
    def test_known_response_overrun_before_lookup_and_higher_hold(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:r['usage'].update(cost='0.1')
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual((t.posts,t.gets),(1,0));row=next(iter(o.rows.values()))
            self.assertEqual(row['charged'],100000);self.assertEqual(row['status'],'UNCERTAIN')
    def test_stats_overrun_preserves_higher_known_cost(self):
        with case() as (p,o,t,*_):
            t.stats_hook=lambda r:r['data'].update(total_cost='0.2')
            with self.assertRaises(ExecutionBlocked):execute(p)
            row=next(iter(o.rows.values()));self.assertEqual(row['charged'],200000);self.assertEqual(row['status'],'OVERRUN')
    def test_provider_byok_native_auxiliary_cost_mismatch_stop(self):
        for update in [{'provider_name':'foreign'},{'is_byok':True},{'native_tokens_prompt':True},
                       {'native_tokens_completion':513},{'native_tokens_reasoning':1},{'num_search_results':1},
                       {'total_cost':'0.000002'}]:
            with self.subTest(update=update),case() as (p,o,t,*_):
                t.stats_hook=lambda r:r['data'].update(update)
                with self.assertRaises(ExecutionBlocked):execute(p)
                self.assertEqual((t.posts,t.gets),(1,1));self.assertEqual(next(iter(o.rows.values()))['status'],'UNCERTAIN')
    def test_missing_generation_identity_no_lookup(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:r.update(id='foreign')
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual(t.gets,0)
    def test_response_model_and_statistics_identity(self):
        for boundary in ('model','stats'):
            with case() as (p,o,t,*_):
                if boundary=='model':t.post_hook=lambda r,q:r.update(model='foreign')
                else:t.stats_hook=lambda r:r['data'].update(id='gen-foreign')
                with self.assertRaises(ExecutionBlocked):execute(p)
                self.assertEqual(t.posts,1)
    def test_timeout_no_retry_full_hold(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:(_ for _ in ()).throw(TimeoutError('secret exception must not escape'))
            with self.assertRaises(ExecutionBlocked) as caught:execute(p)
            self.assertNotIn('secret exception',str(caught.exception));self.assertEqual((t.posts,t.gets),(1,0))
            row=next(iter(o.rows.values()));self.assertEqual(row['charged'],row['reserved'])
    def test_duplicate_generation_claim_stops_second_phase(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:r.update(id='gen-authored-1')
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual((t.posts,t.gets),(2,1))
    def test_late_verified_billing_retains_full_hold_and_evidence(self):
        with case() as (p,o,t,fetch,key,mono,*_):
            t.stats_hook=lambda r:mono.__setitem__(0,121)
            with self.assertRaises(ExecutionBlocked):execute(p)
            row=next(iter(o.rows.values()));self.assertEqual(row['status'],'UNCERTAIN')
            self.assertEqual(row['charged'],row['reserved']);self.assertEqual(row['observed_cost'],1)
            self.assertEqual(row['billing']['provider_name'],'FixtureProvider')
    def test_price_expiry_no_refresh_or_second_post(self):
        with case() as (p,o,t,fetch,key,mono,clock,*_):
            t.stats_hook=lambda r:clock.__setitem__(0,T0+timedelta(seconds=901))
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual(t.posts,1);fetch.assert_called_once()
    def test_unicode_phase_expansion_stops_after_billing_with_not_run(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:r['choices'][0]['message'].update(content=json.dumps(['é'*170]*4,ensure_ascii=False))
            with self.assertRaises(ExecutionBlocked):execute(p)
            row=next(iter(o.rows.values()));self.assertEqual((t.posts,t.gets),(1,1))
            self.assertEqual(row['error_type'],'AnalysisRepresentationBound');self.assertEqual(row['status'],'UNCERTAIN')
            self.assertEqual(o.analysis_status,'NOT_RUN')
            self.assertTrue((o.directory/'limited-pilot-v1'/p['policy']['run_id']/(row['id']+'-response.json')).exists())
    def test_static_packet_refusal_before_owner_catalog_key(self):
        with case() as (p,o,t,fetch,key,mono,clock,owner_factory):
            with self.assertRaises(ExecutionBlocked):client.execute_authored(p,expected_packet_hash='0'*64)
            fetch.assert_not_called();key.assert_not_called();owner_factory.assert_not_called()
    def test_actual_factory_denied_without_boundaries(self):
        with case() as (p,o,t,fetch,key,mono,clock,owner_factory):
            with self.assertRaises(ExecutionBlocked):client.open_actual(p)
            fetch.assert_not_called();key.assert_not_called();owner_factory.assert_not_called()
    def test_restart_existing_journal_refused_no_duplicate_dispatch(self):
        with case() as (p,o,t,fetch,key,*_):
            execute(p)
            with self.assertRaises(FileExistsError):execute(p)
            self.assertEqual(t.posts,32);self.assertEqual(fetch.call_count,1)
    def test_ack_corruption_stops_before_post(self):
        with case() as (p,o,t,*_):
            o.bad_ack=True
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual(t.posts,0)
    def test_checkpoint_corruption_is_not_committed(self):
        with case() as (p,o,t,*_):
            native=client._Journal.write
            def corrupt(j,name,value):
                if name.endswith('-checkpoint.json'):value={**value,'output':{**value['output'],'answer':{}}}
                return native(j,name,value)
            with patch.object(client._Journal,'write',corrupt):
                with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual(next(iter(o.rows.values()))['status'],'UNCERTAIN');self.assertEqual(t.posts,1)
    def test_credential_content_stops_before_persistence_or_stats(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:r.update(secret='AUTHORED_CREDENTIAL_NO_ACTUAL_ACCESS')
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual(t.gets,0)
            directory=o.directory/'limited-pilot-v1'/p['policy']['run_id']
            self.assertFalse(any(f.name.endswith('-response.json') for f in directory.iterdir()))
    def test_encoded_credential_stops_before_body_or_output_retention(self):
        with case() as (p,o,t,*_):
            authored='AUTHORED_CREDENTIAL_NO_ACTUAL_ACCESS'
            encoded='"'+''.join('\\u%04x'%ord(c) for c in authored)+'"'
            t.post_hook=lambda r,q:r['choices'][0]['message'].update(content=encoded)
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual((t.posts,t.gets),(1,0))
            row=next(iter(o.rows.values()))
            self.assertEqual(row['status'],'UNCERTAIN')
            self.assertEqual(row['observed_cost'],1)
            self.assertEqual(row['charged'],row['reserved'])
            self.assertIsNone(row['output_hash'])
            directory=o.directory/'limited-pilot-v1'/p['policy']['run_id']
            self.assertFalse(any(f.name.endswith('-response.json') for f in directory.iterdir()))
            self.assertFalse(any(authored.encode() in f.read_bytes() for f in directory.iterdir()))
    def test_provider_reasoning_stops_before_retention_preserves_known_cost(self):
        values=[('reasoning','AUTHORED_UNSUPPORTED_REASONING'),
                ('reasoning_content','AUTHORED_PROVIDER_ALIAS'),
                ('reasoning_details',[{'type':'reasoning.text','text':'AUTHORED'}]),
                ('reasoning_details',[{'type':'reasoning.summary','summary':'AUTHORED'}]),
                ('reasoning_details',[{'type':'reasoning.encrypted','data':'AUTHORED'}]),
                ('analysis','AUTHORED_ANALYSIS'),('thinking','AUTHORED_THINKING'),
                ('reasoning',False),('reasoning_details',{})]
        for field,value in values:
            with self.subTest(field=field,value_type=type(value).__name__),case() as (p,o,t,*_):
                t.post_hook=lambda r,q:r['choices'][0]['message'].update({field:value})
                with self.assertRaises(ExecutionBlocked):execute(p)
                self.assertEqual((t.posts,t.gets),(1,0))
                row=next(iter(o.rows.values()))
                self.assertEqual(row['status'],'UNCERTAIN');self.assertEqual(row['charged'],row['reserved'])
                self.assertEqual(row['observed_cost'],1);self.assertIsNone(row['output_hash'])
                directory=o.directory/'limited-pilot-v1'/p['policy']['run_id']
                failure=json.loads((directory/'failure.json').read_bytes())
                self.assertEqual(failure['provider_bodies'],{'response':'MISSING','statistics':'MISSING'})
                self.assertFalse(any(f.name.endswith('-response.json') for f in directory.iterdir()))
                self.assertFalse(any(b'AUTHORED_UNSUPPORTED_REASONING' in f.read_bytes() for f in directory.iterdir()))
    def test_reasoning_in_unselected_choice_delta_or_top_level_stops(self):
        for location in ('top','choice','delta','extra_choice'):
            with self.subTest(location=location),case() as (p,o,t,*_):
                def hook(response,request):
                    value={'reasoning':'AUTHORED_HIDDEN_TRACE'}
                    if location=='top':response.update(value)
                    elif location=='choice':response['choices'][0].update(value)
                    elif location=='delta':response['choices'][0]['delta']=value
                    else:response['choices'].append({'message':value})
                t.post_hook=hook
                with self.assertRaises(ExecutionBlocked):execute(p)
                self.assertEqual((t.posts,t.gets),(1,0))
    def test_empty_reasoning_metadata_allowed_without_changing_parser(self):
        client._no_provider_reasoning({'choices':[{'message':{'reasoning':None,'reasoning_content':'','reasoning_details':[]}}]})
        self.assertEqual(client.parse_survey({'choices':[{'message':{'content':'{}','reasoning':'','reasoning_details':[]}}]})['status'],'ANSWER')
    def test_failure_body_dispositions_are_explicit_and_not_file_inference(self):
        for mode,expected in [('timeout',{'response':'MISSING','statistics':'MISSING'}),
                              ('response_overrun',{'response':'RETAINED_CANONICAL_COMPLETE','statistics':'MISSING'}),
                              ('bad_provider',{'response':'RETAINED_CANONICAL_COMPLETE','statistics':'RETAINED_CANONICAL_COMPLETE'}),
                              ('partial_write',{'response':'MISSING','statistics':'MISSING'})]:
            with self.subTest(mode=mode),case() as (p,o,t,*_):
                if mode=='timeout':t.post_hook=lambda r,q:(_ for _ in ()).throw(TimeoutError())
                elif mode=='response_overrun':t.post_hook=lambda r,q:r['usage'].update(cost='0.1')
                elif mode=='bad_provider':t.stats_hook=lambda r:r['data'].update(provider_name='foreign')
                native=client._Journal.write
                def write(j,name,value):
                    if mode=='partial_write' and name.endswith('-response.json'):
                        (j.path/name).write_bytes(b'{')
                        raise OSError('authored partial response write')
                    return native(j,name,value)
                with patch.object(client._Journal,'write',write):
                    with self.assertRaises(ExecutionBlocked):execute(p)
                directory=o.directory/'limited-pilot-v1'/p['policy']['run_id']
                failure=json.loads((directory/'failure.json').read_bytes())
                self.assertEqual(failure['provider_bodies'],expected)
                self.assertIn('partial',failure['missing_body_semantics'])
                if mode=='partial_write':self.assertEqual(len(list(directory.glob('*-response.json'))),1)
    def test_not_run_exports_all_dispositions_without_oversized_answer(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:r['choices'][0]['message'].update(content=json.dumps(['é'*170]*4,ensure_ascii=False))
            with self.assertRaises(ExecutionBlocked):execute(p)
            row=next(iter(o.rows.values()));self.assertEqual(row['observed_cost'],1)
            self.assertEqual(row['charged'],row['reserved'])
            directory=o.directory/'limited-pilot-v1'/p['policy']['run_id']
            terminal=json.loads((directory/'failure.json').read_bytes())['authenticated_terminal']
            self.assertEqual(terminal['analysis_status'],'NOT_RUN');self.assertIsNone(terminal['analysis'])
            records=terminal['response_envelope']['records'];self.assertEqual(len(records),32)
            self.assertEqual(records[0]['status'],'FAILED_UNCERTAIN')
            self.assertTrue(all(r['status']=='NOT_ATTEMPTED' for r in records[1:]))
            self.assertTrue(all(r['answer'] is None for r in records))
            # Direct terminal export must not run either evaluator as a side effect.
            with patch.object(client,'analyze',side_effect=AssertionError('analysis forbidden')), \
                 patch('civiclab.e02.exploratory_sequence_v1.analyze',side_effect=AssertionError('analysis forbidden')), \
                 patch.object(o,'study_snapshot',return_value=terminal['snapshot']):
                direct=client._terminal(o,PROTOCOL,p['price_release']['terms'],response_provenance='MOCK')
            self.assertEqual(direct['response_envelope'],terminal['response_envelope'])
    def test_not_run_export_preserves_prior_derived_invalid_pre_skip(self):
        with case() as (p,o,t,*_):
            def hook(response,request):
                if t.posts==1:response['choices'][0]['message']['content']='{}'
                elif t.posts==2:response['choices'][0]['message']['content']=json.dumps(['é'*170]*4,ensure_ascii=False)
            t.post_hook=hook
            with self.assertRaises(ExecutionBlocked):execute(p)
            directory=o.directory/'limited-pilot-v1'/p['policy']['run_id']
            terminal=json.loads((directory/'failure.json').read_bytes())['authenticated_terminal']
            records=terminal['response_envelope']['records']
            self.assertEqual(len(records),32)
            self.assertEqual([r['status'] for r in records[:3]],['ANSWER','SKIPPED_INVALID_PRE','FAILED_UNCERTAIN'])
            self.assertEqual(records[0]['answer'],{})
            self.assertTrue(all(r['status']=='NOT_ATTEMPTED' for r in records[3:]))
            self.assertIsNone(terminal['analysis'])
    def test_cancellation_preserves_no_retry(self):
        with case() as (p,o,t,*_):
            t.post_hook=lambda r,q:(_ for _ in ()).throw(KeyboardInterrupt())
            with self.assertRaises(KeyboardInterrupt):execute(p)
            self.assertEqual((t.posts,t.gets),(1,0));self.assertEqual(next(iter(o.rows.values()))['status'],'UNCERTAIN')
    def test_lost_ack_does_not_reconstruct_or_dispatch(self):
        with case() as (p,o,t,*_):
            native=o.reserve_next
            def lost(*args,**kwargs):
                native(*args,**kwargs)
                raise OSError('authored lost acknowledgement')
            o.reserve_next=lost
            with self.assertRaises(ExecutionBlocked) as caught:execute(p)
            self.assertEqual(t.posts,0)
            self.assertEqual(next(iter(o.rows.values()))['status'],'STARTED')
            self.assertEqual(caught.exception.diagnostic['reservation_observation'],'UNKNOWN_AT_RESERVATION_BOUNDARY')
    def test_dispatch_intent_persistence_failure_never_posts(self):
        with case() as (p,o,t,*_):
            native=client._Journal.write
            def fail(j,name,value):
                if name.endswith('-dispatch.json'):raise OSError('authored fsync boundary')
                return native(j,name,value)
            with patch.object(client._Journal,'write',fail):
                with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual(t.posts,0);self.assertEqual(next(iter(o.rows.values()))['status'],'UNCERTAIN')
    def test_response_statistic_checkpoint_write_failures_preserve_holds(self):
        for suffix,posts,gets in [('-response.json',1,0),('-statistics.json',1,1),('-checkpoint.json',1,1)]:
            with self.subTest(suffix=suffix),case() as (p,o,t,*_):
                native=client._Journal.write
                def fail(j,name,value):
                    if name.endswith(suffix):raise OSError('authored write failure')
                    return native(j,name,value)
                with patch.object(client._Journal,'write',fail):
                    with self.assertRaises(ExecutionBlocked):execute(p)
                self.assertEqual((t.posts,t.gets),(posts,gets))
                row=next(iter(o.rows.values()));self.assertEqual(row['status'],'UNCERTAIN')
                self.assertGreaterEqual(row['charged'],row['reserved'])
    def test_statistics_claim_failure_permits_no_get(self):
        with case() as (p,o,t,*_):
            o.claim_statistics_lookup=lambda receipt:(_ for _ in ()).throw(OSError('authored claim failure'))
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual((t.posts,t.gets),(1,0))
    def test_commit_lost_ack_cannot_rewrite_committed_row(self):
        with case() as (p,o,t,*_):
            native=o.commit_survey
            def lost(receipt):
                native(receipt)
                raise OSError('authored commit acknowledgement loss')
            o.commit_survey=lost
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual(t.posts,1);self.assertEqual(next(iter(o.rows.values()))['status'],'PHASE_COMMITTED')
            self.assertEqual(len(o.transcript),1)
    def test_scalar_usage_unknown_stats_and_monetary_domain_stop(self):
        for mutation in ('usage_type','cost_null','native_missing','reasoning_detail','missing_total'):
            with self.subTest(mutation=mutation),case() as (p,o,t,*_):
                if mutation=='usage_type':t.post_hook=lambda r,q:r.update(usage=[])
                elif mutation=='cost_null':t.stats_hook=lambda r:r['data'].update(total_cost=None)
                elif mutation=='native_missing':t.stats_hook=lambda r:r['data'].pop('native_tokens_completion')
                elif mutation=='reasoning_detail':t.post_hook=lambda r,q:r['usage'].update(completion_tokens_details={'reasoning_tokens':1})
                else:t.stats_hook=lambda r:r['data'].pop('total_cost')
                with self.assertRaises(ExecutionBlocked):execute(p)
                self.assertEqual(t.posts,1)
    def test_native_completion_512_is_valid_not_bool_compatibility_32(self):
        with case() as (p,o,t,*_):
            t.stats_hook=lambda r:r['data'].update(native_tokens_completion=512)
            result=execute(p);self.assertEqual(result['status'],'COMPLETE')
    def test_low_disk_and_count_bound_refuse_without_request(self):
        with case() as (p,o,t,fetch,key,*_):
            from collections import namedtuple
            usage=namedtuple('usage','total used free')(1000,999,1)
            with patch.object(client.shutil,'disk_usage',return_value=usage):
                with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual(t.posts,0);fetch.assert_not_called();key.assert_not_called()
        with case() as (p,o,*_):
            j=client._Journal(o,'COUNT-BOUND',p)
            try:
                with patch.object(client,'ARTIFACTS',2):
                    with self.assertRaises(ExecutionBlocked):j.write('third.json',{})
            finally:j.close()
    def test_opaque_one_use_capability(self):
        with case() as (p,o,t,*_):
            j=client._Journal(o,'CAPABILITY-ONLY',p)
            raw,decision,terms,metadata=fixture_contract()
            proof={**metadata,'metadata_semantic_hash':terms['metadata_semantic_hash']}
            phase=client._Phase(p,proof)
            ack=o.reserve_next(p,proof,expected_packet_hash=canonical_hash(p),transport_ready=lambda c:True)
            try:
                with self.assertRaises(ExecutionBlocked):client._Capability(object(),j,phase,t,ack)
                cap=client._Capability(client._SEAL,j,phase,t,ack)
                cap.post()
                with self.assertRaises(ExecutionBlocked):cap.post()
                self.assertEqual(t.posts,1)
            finally:j.close()
    def test_journal_limits_symlink_and_exclusive_create(self):
        with case() as (p,o,*_):
            j=client._Journal(o,'JOURNAL-ONLY',p)
            try:
                j.write('same.json',{})
                with self.assertRaises(FileExistsError):j.write('same.json',{})
                with self.assertRaises(ExecutionBlocked):j.write('../escape.json',{})
                with patch.object(client,'ARTIFACT_BYTES',10):
                    with self.assertRaises(ExecutionBlocked):j.write('large.json',{'large':'x'*100})
                (j.path/'link.json').symlink_to(j.path/'same.json')
                with self.assertRaises(ExecutionBlocked):j.write('new.json',{})
            finally:j.close()


@contextmanager
def recovery_client_case():
    from test_additional_compatibility_owner_v1 import materials
    from test_additional_compatibility_client_v1_1 import raw_catalog
    from test_e02_exploratory_metadata_v1 import saved_shape
    with case() as values:
        p,o,t,fetch,key,mono,clock,owner_factory=values
        release,_=materials('AUTHORED_RECOVERY_CLIENT')
        p['policy']['kind']='LIMITED_PILOT_RECOVERY_POLICY_V1'
        p['price_release']={'terms':release['terms'],'interpretation':release['interpretation']}
        raw=raw_catalog()
        metadata={'url':'https://openrouter.ai/api/v1/models/'+release['terms']['model']+'/endpoints',
                  'body_sha256':hashlib.sha256(raw).hexdigest(),'observed_at_utc':T0.isoformat()}
        fetch.return_value=(raw,metadata)
        def stats(result):
            modern=saved_shape();modern.update(id=result['data']['id'],total_cost='0.000001',
                                             native_tokens_prompt=1,native_tokens_completion=1)
            result['data']=modern
        t.stats_hook=stats
        with patch.object(client.time,'sleep',side_effect=lambda seconds:mono.__setitem__(0,mono[0]+seconds)) as sleep:
            yield values,sleep


class RecoveryClientTests(unittest.TestCase):
    def test_full_authored_sequence_waits_once_per_get_preserves_raw_alias_and_unknowns(self):
        with recovery_client_case() as (values,sleep):
            p,o,t,fetch,key,mono,*_=values
            t.post_hook=lambda r,q:r.update(model='openai/gpt-4.1-nano-2025-04-14')
            out=execute(p)
            self.assertEqual((t.posts,t.gets),(32,32));self.assertEqual(mono[0],320)
            self.assertEqual(sum(call.args[0] for call in sleep.call_args_list),320)
            self.assertEqual(out['analysis']['estimate_thermometer_points'],0)
            self.assertTrue(all(r['billing']['model']=='openai/gpt-4.1-nano' for r in o.rows.values()))
            path=Path(out['path']);stats=json.loads(next(path.glob('*-statistics.json')).read_bytes())['data']
            self.assertEqual(stats['model'],'openai/gpt-4.1-nano-2025-04-14');self.assertIsNone(stats['num_fetches'])
            quality=json.loads(next(path.glob('*-quality.json')).read_bytes())['auxiliary']
            self.assertTrue(quality['streamed_discrepancy']);self.assertEqual(quality['reported_streamed'],True)
            self.assertEqual(quality['optional_counters']['num_fetches']['status'],'REPORTED_NULL_UNKNOWN')
    def test_wait_starts_only_after_response_retention_and_before_claim(self):
        with recovery_client_case() as (values,sleep):
            p,o,t,fetch,key,mono,*_=values
            calls=[0]
            def wait(seconds):
                calls[0]+=1
                if calls[0]==1:
                    row=next(iter(o.rows.values()))
                    self.assertEqual(row['status'],'RESPONSE_SEEN');self.assertEqual(len(o.claims),0)
                    directory=o.directory/'limited-pilot-v1'/p['policy']['run_id']
                    self.assertTrue((directory/(row['id']+'-response.json')).exists())
                mono[0]+=seconds
            sleep.side_effect=wait;execute(p)
            self.assertEqual(t.gets,32)
    def test_wait_cancel_expiry_clock_stall_or_budget_blocks_get_without_retry(self):
        for mode in ('cancel','expired','rollback','stalled','insufficient'):
            with self.subTest(mode=mode),recovery_client_case() as (values,sleep):
                p,o,t,fetch,key,mono,clock,*_=values
                if mode=='cancel':sleep.side_effect=KeyboardInterrupt()
                elif mode=='expired':sleep.side_effect=lambda sec:clock.__setitem__(0,T0+timedelta(seconds=901))
                elif mode=='rollback':sleep.side_effect=lambda sec:mono.__setitem__(0,-1)
                elif mode=='stalled':sleep.side_effect=lambda sec:None
                else:t.post_hook=lambda r,q:mono.__setitem__(0,75)
                expected=KeyboardInterrupt if mode=='cancel' else ExecutionBlocked
                with self.assertRaises(expected):execute(p)
                self.assertEqual((t.posts,t.gets),(1,0));self.assertEqual(len(o.claims),0)
                row=next(iter(o.rows.values()));self.assertEqual(row['status'],'UNCERTAIN')
                self.assertEqual(row['charged'],row['reserved'])
                self.assertLessEqual(sleep.call_count,12)
    def test_response_tools_media_search_cannot_hide_behind_null_statistics(self):
        cases=[('tool_calls',[{'function':{'name':'AUTHORED_TOOL'}}]),('function_call',{'name':'AUTHORED_TOOL'}),
               ('audio',{'data':'AUTHORED_AUDIO'}),('images',[{'image_url':'AUTHORED_IMAGE'}]),
               ('annotations',[{'type':'url_citation'}]),('search_results',[{'title':'AUTHORED_SEARCH'}]),
               ('num_fetches',1),('content',[{'type':'image_url','image_url':'AUTHORED_IMAGE'}])]
        for field,value in cases:
            with self.subTest(field=field),recovery_client_case() as (values,sleep):
                p,o,t,*_=values
                t.post_hook=lambda r,q:r['choices'][0]['message'].update({field:value})
                with self.assertRaises(ExecutionBlocked):execute(p)
                self.assertEqual((t.posts,t.gets),(1,0));sleep.assert_not_called()
                row=next(iter(o.rows.values()));self.assertEqual(row['observed_cost'],1)
                self.assertEqual(row['charged'],row['reserved'])
                self.assertIsNone(row['output_hash'])
                path=o.directory/'limited-pilot-v1'/p['policy']['run_id']
                self.assertFalse(any(path.glob('*-response.json')))
    def test_nondefault_or_malformed_recovery_stats_stop_after_only_one_lookup(self):
        for field,value in [('service_tier',None),('streamed',None),('num_search_results',1),('cancelled',0)]:
            with self.subTest(field=field),recovery_client_case() as (values,sleep):
                p,o,t,*_=values;native=t.stats_hook
                def stats(result):native(result);result['data'][field]=value
                t.stats_hook=stats
                with self.assertRaises(ExecutionBlocked):execute(p)
                self.assertEqual((t.posts,t.gets),(1,1))
    def test_legacy_packets_do_not_gain_aliases_null_tolerance_or_visibility_wait(self):
        with case() as (p,o,t,*_),patch.object(client.time,'sleep',side_effect=AssertionError('legacy wait changed')):
            t.post_hook=lambda r,q:r.update(model='openai/gpt-4.1-nano-2025-04-14')
            with self.assertRaises(ExecutionBlocked):execute(p)
            self.assertEqual((t.posts,t.gets),(1,0))


@contextmanager
def real_owner_case():
    from types import SimpleNamespace
    from test_e02_exploratory_owner_v1 import study_case
    from test_additional_compatibility_client_v1_1 import raw_catalog
    with study_case() as (owner,packet,proof,clock,old):
        transport=FakeTransport(SimpleNamespace(packet=packet,calls=[]))
        mono=[0.0]
        metadata={k:proof[k] for k in ('url','body_sha256','observed_at_utc')}
        with patch.object(client,'_owner',return_value=owner), \
             patch.object(client,'_read_environment_key',return_value=_Credential('AUTHORED_CROSS_CREDENTIAL')), \
             patch.object(client,'_transport',return_value=transport), \
             patch.object(client,'_fetch_public_catalog',return_value=(raw_catalog(),metadata)) as fetch, \
             patch.object(client.time,'monotonic',side_effect=lambda:mono[0]):
            yield owner,packet,transport,clock,mono,old,fetch


class OriginalOwnerCrossTests(unittest.TestCase):
    def test_32_phase_primary_and_replay_authenticate_same_outputs_original_history(self):
        outputs=[]
        for _ in range(2):
            with real_owner_case() as (owner,packet,t,clock,mono,old,fetch):
                result=execute(packet);outputs.append(result)
                self.assertEqual((t.posts,t.gets),(32,32));fetch.assert_called_once()
                snapshot=owner.snapshot()
                self.assertEqual(next(r for r in snapshot['charges'] if r['id']==old['id']),old)
                self.assertEqual(result['snapshot']['study_charged_microusd'],32)
                self.assertEqual(result['snapshot']['consumed_microusd']['total'],373)
                self.assertEqual(result['snapshot']['consumed_microusd']['dispatches'],34)
                self.assertEqual(result['analysis']['response_provenance'],'MOCK')
                with owner._lock(),owner._connect() as db:
                    state,head=owner._verify(db)
                    self.assertEqual(state['unfinished'],1)
                    self.assertEqual(len(state['study']['witnesses']),32)
                checkpoint=json.loads(next(Path(result['path']).glob('*-checkpoint.json')).read_bytes())
                self.assertEqual(set(checkpoint['output']),{'status','answer','response_raw_sha256'})
                self.assertNotIn('statistics_raw_sha256',checkpoint['output'])
        self.assertEqual(outputs[0]['response_envelope'],outputs[1]['response_envelope'])
        self.assertEqual(outputs[0]['analysis'],outputs[1]['analysis'])
    def test_invalid_pre_skips_with_authenticated_witness(self):
        with real_owner_case() as (owner,packet,t,*_):
            t.post_hook=lambda r,q:r['choices'][0]['message'].update(content='bad') if t.posts==1 else None
            result=execute(packet)
            self.assertEqual(t.posts,31);self.assertEqual(result['analysis']['complete_blocks'],7)
            self.assertEqual(result['response_envelope']['records'][1]['status'],'SKIPPED_INVALID_PRE')
    def test_overrun_persists_original_owner_hold_and_stops(self):
        with real_owner_case() as (owner,packet,t,clock,mono,old,fetch):
            t.stats_hook=lambda r:r['data'].update(total_cost='0.1')
            with self.assertRaises(ExecutionBlocked):execute(packet)
            snapshot=owner.study_snapshot()
            self.assertEqual((t.posts,t.gets),(1,1));self.assertEqual(snapshot['status'],'STOPPED')
            self.assertEqual(snapshot['study_charged_microusd'],100000)
            self.assertEqual(snapshot['consumed_microusd']['total'],100341)
            self.assertEqual(next(r for r in owner.snapshot()['charges'] if r['id']==old['id']),old)
    def test_unicode_representation_preserves_raw_finance_and_not_run(self):
        with real_owner_case() as (owner,packet,t,*_):
            t.post_hook=lambda r,q:r['choices'][0]['message'].update(content=json.dumps(['é'*170]*4,ensure_ascii=False))
            with self.assertRaises(ExecutionBlocked):execute(packet)
            snapshot=owner.study_snapshot();self.assertEqual(snapshot['analysis_status'],'NOT_RUN')
            self.assertEqual(snapshot['failure_reason'],'AnalysisRepresentationBound')
            directory=owner.directory/'limited-pilot-v1'/packet['policy']['run_id']
            self.assertEqual(len(list(directory.glob('*-response.json'))),1)
            self.assertEqual(len(list(directory.glob('*-statistics.json'))),1)
    def test_late_checkpoint_commit_refused_no_committed_phase(self):
        with real_owner_case() as (owner,packet,t,clock,mono,*_):
            native=client._Journal.write
            def late(j,name,value):
                result=native(j,name,value)
                if name.endswith('-checkpoint.json'):clock[0]+=timedelta(seconds=121)
                return result
            with patch.object(client._Journal,'write',late):
                with self.assertRaises(ExecutionBlocked):execute(packet)
            snapshot=owner.study_snapshot();self.assertEqual(snapshot['status'],'STOPPED')
            self.assertEqual(len(snapshot['transcript']),1)
            self.assertEqual(snapshot['transcript'][0]['status'],'FAILED_UNCERTAIN')


if __name__=='__main__':unittest.main()
