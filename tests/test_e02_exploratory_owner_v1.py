"""Authored original-owner integration; fake OS homes, no keys or HTTP."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
import uuid

from civiclab.common import canonical_bytes, canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.e02.exploratory_owner_v1 import (StudyOwnerV1, LIMITS, code_contract,
    validate_packet, PROTOCOL_SHA, PROJECTION_SHA, ASSIGNMENT_SHA, open_actual,
    AnalysisRepresentationBound)
from test_additional_compatibility_owner_v1 import case, append
from test_production_admission_v4 import settle
from test_production_price_v4 import T0


def native_batch(home,q,proof,boundary,queue=None,gate=None):
    from test_production_admission_v4 import account
    native_connect=sqlite3.connect
    from civiclab.e02.exploratory_owner_v1 import atomic_json as native_anchor
    class CrashConnection(sqlite3.Connection):
        inserts=0
        def execute(self,sql,*args,**kwargs):
            value=super().execute(sql,*args,**kwargs)
            if sql.startswith('INSERT INTO events'):
                self.inserts+=1
                if boundary=='INSERT_'+str(self.inserts):os._exit(91)
            if sql.startswith('INSERT OR REPLACE INTO charges') and boundary=='CHARGE':os._exit(92)
            return value
        def commit(self):
            super().commit()
            if boundary=='COMMIT':os._exit(93)
    def connect(*args,**kwargs):return native_connect(*args,**kwargs,factory=CrashConnection)
    def anchor(path,value):
        native_anchor(path,value)
        if boundary=='ANCHOR':os._exit(94)
    with account(Path(home)),patch('civiclab.production_owner_v4.sqlite3.connect',side_effect=connect), \
            patch('civiclab.e02.exploratory_owner_v1.atomic_json',side_effect=anchor):
        if gate is not None:gate.wait(10)
        try:
            owner=StudyOwnerV1.open();result=reserve(owner,q,proof)
            if boundary=='RETURN_LOST':os._exit(95)
            if queue is not None:queue.put(result['status'])
        except (ExecutionBlocked,ValueError):
            if queue is not None:queue.put('REFUSED')
            else:raise


def packet_for(owner,release,compatibility_receipt):
    with owner._lock(),owner._connect() as db:
        state,head=owner._verify(db)
    l={'kind':'LIMITED_PILOT_PRICE_RELEASE_V1','terms':release['terms'],
       'interpretation':release['interpretation']}
    p={'kind':'LIMITED_PILOT_POLICY_V1','owner_id':owner.header['owner_id'],
       'predecessor':{'header_hash':canonical_hash(owner.header),'head':head,
           'history_hash':canonical_hash(state['_prefix_events']),'active_approval_hash':state['active'],
           'rows_hash':canonical_hash(state['rows']),
           'statistics_claims_hash':canonical_hash(sorted(state['statistics_claims']))},
       'compatibility_receipt':compatibility_receipt,'run_id':'AUTHORED_LIMITED_PILOT',
       'protocol_sha256':PROTOCOL_SHA,'projection_sha256':PROJECTION_SHA,
       'assignment_sha256':ASSIGNMENT_SHA,'code_contract_hash':canonical_hash(code_contract()),
       'price_release_hash':canonical_hash(l),'limits':deepcopy(LIMITS),
       'valid_from_utc':(T0-timedelta(seconds=1)).isoformat(),
       'valid_until_utc':(T0+timedelta(seconds=600)).isoformat()}
    r={'kind':'INDEPENDENT_LIMITED_PILOT_REVIEW_V1','reviewer_role':'independent_auditor',
       'review_id':uuid.uuid4().hex,'policy_hash':canonical_hash(p),'code_contract_hash':p['code_contract_hash']}
    o={'kind':'EXTERNAL_LIMITED_PILOT_OWNER_ASSERTION_V1','policy_hash':canonical_hash(p),
       'review_hash':canonical_hash(r),'consent_evidence_hash':canonical_hash('AUTHORED_NOT_CONSENT'),
       'assertion':'RETAIN_OLD_UNKNOWN_CHARGE_ALLOW_ONE_32_PHASE_PILOT_WITHIN_SHARED_5_USD',
       'credential_state':'OWNER_ASSERTED_ROTATED_DEDICATED_KEY_AND_PREFUNDED'}
    a={'kind':'LIMITED_PILOT_AUTHORITY_V1','approval_id':uuid.uuid4().hex,'policy_hash':canonical_hash(p),
       'review_hash':canonical_hash(r),'owner_assertion_hash':canonical_hash(o),
       'code_contract_hash':p['code_contract_hash']}
    q={'kind':'LIMITED_PILOT_PACKET_V1','policy':p,'review':r,'owner_assertion':o,
       'authority':a,'price_release':l}
    q['terminal_review']={'kind':'INDEPENDENT_LIMITED_PILOT_TERMINAL_REVIEW_V1',
       'reviewer_role':'independent_auditor','review_id':uuid.uuid4().hex,
       'packet_inputs_hash':canonical_hash(q),'code_contract_hash':p['code_contract_hash']}
    return q


@contextmanager
def study_case(compatibility_answer=None):
    with case() as (oldowner,original,b,x,release,clock,old):
        append(oldowner,b,x,release)
        answer=compatibility_answer or {'status':'VALID','parsed':{'ok':True},'raw_text':'{"ok":true}'}
        generation='gen-'+uuid.uuid4().hex
        oldowner.transition(b['receipt'],'RESPONSE_SEEN',generation_id=generation,
                            output_hash=canonical_hash(answer),observed_cost=1)
        oldowner.claim_statistics_lookup(b['receipt']);settle(oldowner,b['receipt'],generation,cost=1)
        c=b['context'];base=oldowner.directory/'additional-test-v1'/c['run_id']
        base.mkdir(parents=True)
        path=base/'phase.local.json'
        path.write_bytes(canonical_bytes({'schema_version':1,
            **{k:c[k] for k in ('run_id','unit_id','phase')},'receipt':b['receipt'],
            'request_hash':c['envelope']['request_hash'],'output':answer}))
        oldowner.commit_phase(b['receipt'],path)
        owner=StudyOwnerV1.open();q=packet_for(owner,release,b['receipt'])
        yield owner,q,b['context']['price_proof'],clock,old


def reserve(owner,q,proof):
    return owner.reserve_next(q,proof,expected_packet_hash=canonical_hash(q),transport_ready=lambda c:True)


def phase_files(owner,ack,answer,cost=1,generation=None):
    c=ack['context'];receipt=ack['receipt'];generation=generation or 'gen-'+uuid.uuid4().hex
    response={'id':generation,'model':c['terms']['model'],
              'choices':[{'message':{'content':json.dumps(answer)}}],
              'usage':{'cost':cost/1000000,'prompt_tokens':1,'completion_tokens':1}}
    from civiclab.e02.exploratory_response_v1 import parse_survey_response
    parsed=parse_survey_response(response);body=canonical_bytes(response)
    output={'status':parsed['status'],'answer':parsed['answer'],
            'response_raw_sha256':hashlib.sha256(body).hexdigest()}
    billing={'id':generation,'model':c['terms']['model'],'provider_name':c['terms']['reported_provider'],
             'total_cost':cost/1000000,'native_tokens_prompt':1,'native_tokens_completion':1,
             'native_tokens_reasoning':0,'is_byok':False}
    cp={'schema_version':1,'run_id':c['run_id'],'unit_id':c['unit_id'],'phase':c['phase'],
        'receipt':receipt,'request_hash':c['envelope']['request_hash'],'output':output}
    root=owner.directory/'limited-pilot-v1'/q_run(ack);root.mkdir(parents=True,exist_ok=True)
    for name,value in [('response',response),('statistics',{'data':billing}),('checkpoint',cp)]:
        (root/(receipt+'-'+name+'.json')).write_bytes(canonical_bytes(value))
    return output,billing,generation


def q_run(ack):return ack['context']['run_id']


def complete_phase(owner,ack,answer):
    output,billing,generation=phase_files(owner,ack,answer)
    owner.transition(ack['receipt'],'RESPONSE_SEEN',generation_id=generation,
                     output_hash=canonical_hash(output),observed_cost=1)
    owner.claim_statistics_lookup(ack['receipt'])
    owner.transition(ack['receipt'],'SETTLED',observed_cost=1,billing=billing)
    owner.commit_survey(ack['receipt'])


class StudyOwnerTests(unittest.TestCase):
    def test_actual_factory_denies_without_home_discovery(self):
        with patch('civiclab.production_owner_v4.pwd.getpwuid',side_effect=AssertionError('home')):
            with self.assertRaises(ExecutionBlocked):open_actual(object())

    def test_charged_compatibility_quality_failure_is_not_study_admission(self):
        for answer in (
            {'status':'INVALID_SHAPE','parsed':{'ok':False},'raw_text':'{"ok":false}'},
            {'status':'VALID','parsed':{'ok':True},'raw_text':'{"ok":false}'},
            {'status':'VALID','parsed':{'ok':1},'raw_text':'{"ok":1}'},
            {'status':'PARSED_OBJECT','parsed':{'ok':True},'raw_text':'{"ok":true}'},
        ):
            with self.subTest(answer=answer),study_case(answer) as (owner,q,proof,*_):
                before=owner.snapshot()
                with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)
                self.assertEqual(owner.snapshot(),before)

    def test_compatibility_fixed_checkpoint_missing_tampered_or_symlink_refuses(self):
        for mode in ('missing','tampered','symlink'):
            with self.subTest(mode=mode),study_case() as (owner,q,proof,*_):
                base=owner.directory/'additional-test-v1'/'AUTHORED_ADDITIONAL'
                path=base/'phase.local.json'
                if mode=='missing':path.unlink()
                elif mode=='tampered':path.write_bytes(path.read_bytes()+b' ')
                else:
                    original=base/'other.local.json';path.rename(original);path.symlink_to(original)
                with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)
                self.assertEqual(owner.study_snapshot()['status'],'NOT_STARTED')

    def test_study_authority_separate_from_unchanged_original_approval_map(self):
        with study_case() as (owner,q,proof,*_):
            with owner._lock(),owner._connect() as db:
                state,_=owner._verify(db)
                original=deepcopy(state['approvals']);active=state['active'];ids=state['approval_ids'].copy()
            ack=reserve(owner,q,proof)
            complete_phase(owner,ack,{'democratic_party':50,'republican_party':50})
            with owner._lock(),owner._connect() as db:
                state,_=owner._verify(db)
            self.assertEqual(state['approvals'],original)
            self.assertEqual(state['active'],active);self.assertEqual(state['approval_ids'],ids)
            self.assertEqual(state['study_authorities'],{canonical_hash(q['authority']):q['authority']})
            self.assertNotIn(canonical_hash(q['authority']),state['approvals'])

    def test_retained_statistics_types_and_auxiliary_activity_rechecked_at_commit(self):
        mutations=[('native_tokens_prompt',True),('is_byok',0),('native_tokens_completion',1.0),
                   ('native_tokens_reasoning',False),('num_search_results',1),
                   ('num_fetches',True),('service_tier','priority'),('cancelled',True)]
        for field,value in mutations:
            with self.subTest(field=field),study_case() as (owner,q,proof,*_):
                ack=reserve(owner,q,proof)
                output,billing,generation=phase_files(owner,ack,{'democratic_party':50,'republican_party':50})
                owner.transition(ack['receipt'],'RESPONSE_SEEN',generation_id=generation,
                                 output_hash=canonical_hash(output),observed_cost=1)
                owner.claim_statistics_lookup(ack['receipt'])
                owner.transition(ack['receipt'],'SETTLED',observed_cost=1,billing=billing)
                path=owner._journal(q['policy']['run_id'])/(ack['receipt']+'-statistics.json')
                stats=json.loads(path.read_bytes());stats['data'][field]=value
                path.write_bytes(canonical_bytes(stats))
                with self.assertRaises((ExecutionBlocked,ValueError)):owner.commit_survey(ack['receipt'])
                with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)
                owner.transition(ack['receipt'],'UNCERTAIN',observed_cost=1,error_type='AuthoredRetainedStatsFailure')
                snapshot=owner.study_snapshot()
                self.assertEqual(snapshot['study_dispatches'],1)
                self.assertEqual(snapshot['study_charged_microusd'],ack['context']['envelope']['reserved_microusd'])

    def test_bound_response_activity_usage_and_checkpoint_types_rechecked(self):
        for mode in ('reasoning','usage_boolean','cost_disagreement','checkpoint_boolean'):
            with self.subTest(mode=mode),study_case() as (owner,q,proof,*_):
                ack=reserve(owner,q,proof)
                output,billing,generation=phase_files(owner,ack,{'democratic_party':50,'republican_party':50})
                base=owner._journal(q['policy']['run_id'])
                response_path=base/(ack['receipt']+'-response.json')
                checkpoint_path=base/(ack['receipt']+'-checkpoint.json')
                response=json.loads(response_path.read_bytes())
                cp=json.loads(checkpoint_path.read_bytes())
                if mode=='reasoning':response['choices'][0]['message']['reasoning']='AUTHORED_UNSUPPORTED_REASONING'
                elif mode=='usage_boolean':response['usage']['prompt_tokens']=True
                elif mode=='cost_disagreement':response['usage']['cost']=0.000002
                else:cp['schema_version']=True
                raw=canonical_bytes(response);response_path.write_bytes(raw)
                from civiclab.e02.exploratory_response_v1 import parse_survey_response
                parsed=parse_survey_response(response)
                output={'status':parsed['status'],'answer':parsed['answer'],
                        'response_raw_sha256':hashlib.sha256(raw).hexdigest()}
                cp['output']=output;checkpoint_path.write_bytes(canonical_bytes(cp))
                owner.transition(ack['receipt'],'RESPONSE_SEEN',generation_id=generation,
                                 output_hash=canonical_hash(output),observed_cost=1)
                owner.claim_statistics_lookup(ack['receipt'])
                owner.transition(ack['receipt'],'SETTLED',observed_cost=1,billing=billing)
                with self.assertRaises((ExecutionBlocked,ValueError)):owner.commit_survey(ack['receipt'])
                self.assertEqual(owner.study_snapshot()['transcript'],[])

    def test_32_phases_original_hold_retained_and_no_33rd_phase(self):
        with study_case() as (owner,q,proof,clock,old):
            for i in range(32):
                ack=reserve(owner,q,proof)
                self.assertEqual(ack['status'],'RESERVED')
                self.assertEqual(ack['request']['execution_order'],i//2)
                self.assertEqual(ack['request']['phase'],'pre' if i%2==0 else 'post')
                if i%2:self.assertEqual(ack['request']['request']['pre_response'],
                                       {'democratic_party':50,'republican_party':50})
                complete_phase(owner,ack,{'democratic_party':50,'republican_party':50})
            done=reserve(owner,q,proof)
            self.assertEqual(done['status'],'COMPLETE');self.assertEqual(done['study_dispatches'],32)
            self.assertEqual(done['consumed_microusd']['total'],340+1+32)
            self.assertEqual(done['consumed_microusd']['dispatches'],34)
            with owner._lock(),owner._connect() as db:
                state,head=owner._verify(db)
                self.assertEqual(state['unfinished'],1);self.assertEqual(state['rows'][old['id']],old)
                self.assertEqual(len(state['study']['witnesses']),32)

    def test_invalid_pre_has_no_post_reservation(self):
        with study_case() as (owner,q,proof,clock,old):
            pre=reserve(owner,q,proof);complete_phase(owner,pre,{'democratic_party':None,'republican_party':50})
            next_ack=reserve(owner,q,proof)
            self.assertEqual(next_ack['request']['execution_order'],1)
            self.assertEqual(next_ack['request']['phase'],'pre')
            self.assertEqual(owner.study_snapshot()['study_dispatches'],2)

    def test_pending_uncertain_and_known_overrun_forbid_another_grant(self):
        for outcome in ('pending','UNCERTAIN','OVERRUN'):
            with study_case() as (owner,q,proof,clock,old):
                ack=reserve(owner,q,proof)
                if outcome=='UNCERTAIN':owner.transition(ack['receipt'],outcome,observed_cost=2000000,error_type='AuthoredOverrun')
                elif outcome=='OVERRUN':
                    output,billing,generation=phase_files(owner,ack,{},cost=2000000)
                    owner.transition(ack['receipt'],'RESPONSE_SEEN',generation_id=generation,
                        output_hash=canonical_hash(output),observed_cost=2000000)
                    owner.transition(ack['receipt'],outcome,observed_cost=2000000,error_type='AuthoredOverrun')
                if outcome=='pending':
                    with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)
                else:
                    stopped=reserve(owner,q,proof);self.assertEqual(stopped['status'],'STOPPED')
                    self.assertEqual(stopped['study_charged_microusd'],2000000)
                self.assertEqual(owner.study_snapshot()['study_dispatches'],1)

    def test_packet_or_proof_changes_and_original_row_mutations_refuse(self):
        with study_case() as (owner,q,proof,clock,old):
            bad=deepcopy(q);bad['policy']['limits']['shared_microusd']=5000001
            with self.assertRaises(ExecutionBlocked):validate_packet(bad,expected_packet_hash=canonical_hash(bad))
            ack=reserve(owner,q,proof)
            with self.assertRaises(ExecutionBlocked):owner.transition(old['id'],'RESPONSE_SEEN')
            with self.assertRaises(ExecutionBlocked):owner.commit_phase(ack['receipt'],Path('/unused'))
            altered={**proof,'body_sha256':'0'*64}
            with self.assertRaises(ExecutionBlocked):reserve(owner,q,altered)

    def test_foreign_raw_answer_or_checkpoint_cannot_change_own_baseline(self):
        with study_case() as (owner,q,proof,clock,old):
            ack=reserve(owner,q,proof);output,billing,generation=phase_files(owner,ack,{'democratic_party':25,'republican_party':75})
            owner.transition(ack['receipt'],'RESPONSE_SEEN',generation_id=generation,output_hash=canonical_hash(output),observed_cost=1)
            owner.claim_statistics_lookup(ack['receipt']);owner.transition(ack['receipt'],'SETTLED',observed_cost=1,billing=billing)
            path=owner._journal(q['policy']['run_id'])/(ack['receipt']+'-checkpoint.json')
            changed=json.loads(path.read_bytes());changed['output']['answer']['democratic_party']=26
            path.write_bytes(canonical_bytes(changed))
            with self.assertRaises(ExecutionBlocked):owner.commit_survey(ack['receipt'])
            with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)

    def test_unicode_export_guard_preserves_settlement_then_uncertain_full_hold(self):
        with study_case() as (owner,q,proof,clock,old):
            ack=reserve(owner,q,proof)
            answer=['😀'*250]*2
            output,billing,generation=phase_files(owner,ack,answer)
            # Use minimal Unicode original content to fit parser's UTF8 limit.
            root=owner._journal(q['policy']['run_id']);path=root/(ack['receipt']+'-response.json')
            value=json.loads(path.read_bytes());value['choices'][0]['message']['content']=json.dumps(answer,ensure_ascii=False)
            raw=canonical_bytes(value);path.write_bytes(raw)
            output={'status':'ANSWER','answer':answer,'response_raw_sha256':hashlib.sha256(raw).hexdigest()}
            cp=root/(ack['receipt']+'-checkpoint.json');v=json.loads(cp.read_bytes());v['output']=output;cp.write_bytes(canonical_bytes(v))
            owner.transition(ack['receipt'],'RESPONSE_SEEN',generation_id=generation,output_hash=canonical_hash(output),observed_cost=1)
            owner.claim_statistics_lookup(ack['receipt']);owner.transition(ack['receipt'],'SETTLED',observed_cost=1,billing=billing)
            with self.assertRaises(AnalysisRepresentationBound):owner.commit_survey(ack['receipt'])
            owner.transition(ack['receipt'],'UNCERTAIN',observed_cost=1,billing=billing,error_type='AnalysisRepresentationBound')
            state=owner.study_snapshot();self.assertEqual(state['analysis_status'],'NOT_RUN')
            self.assertEqual(state['study_charged_microusd'],340)
            self.assertEqual(reserve(owner,q,proof)['status'],'STOPPED')

    def test_expiry_rollback_and_full_phase_fit_before_new_grant(self):
        for delta in (timedelta(seconds=500),timedelta(seconds=-1)):
            with study_case() as (owner,q,proof,clock,old):
                with patch('civiclab.production_owner_v4._utc_now',return_value=T0+delta):
                    with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)
                self.assertEqual(owner.study_snapshot()['status'],'NOT_STARTED')

    def test_native_atomic_batch_crash_boundaries_and_lost_ack(self):
        ctx=multiprocessing.get_context('spawn')
        for boundary in ('INSERT_1','INSERT_2','INSERT_3','CHARGE','COMMIT','ANCHOR','RETURN_LOST'):
            with self.subTest(boundary=boundary),study_case() as (owner,q,proof,clock,old):
                process=ctx.Process(target=native_batch,args=(str(owner.directory.parents[3]),q,proof,boundary))
                # Account's OS home is the ancestor preceding Library/Application Support.
                import civiclab.production_owner_v4 as runtime
                home=Path(runtime.pwd.getpwuid(os.getuid()).pw_dir)
                process=ctx.Process(target=native_batch,args=(str(home),q,proof,boundary))
                process.start();process.join(20)
                self.assertFalse(process.is_alive());self.assertIn(process.exitcode,(91,92,93,94,95))
                if boundary=='COMMIT':
                    with self.assertRaises(ExecutionBlocked):owner.study_snapshot()
                elif boundary in ('ANCHOR','RETURN_LOST'):
                    self.assertEqual(owner.study_snapshot()['study_dispatches'],1)
                    with self.assertRaises(ExecutionBlocked):reserve(owner,q,proof)
                else:
                    self.assertEqual(owner.study_snapshot()['status'],'NOT_STARTED')
                    self.assertEqual(owner.study_snapshot()['consumed_microusd']['total'],341)

    def test_two_native_processes_reserve_exactly_one_phase(self):
        ctx=multiprocessing.get_context('spawn')
        with study_case() as (owner,q,proof,clock,old):
            import civiclab.production_owner_v4 as runtime
            home=Path(runtime.pwd.getpwuid(os.getuid()).pw_dir)
            gate=ctx.Event();queue=ctx.Queue()
            processes=[ctx.Process(target=native_batch,args=(str(home),q,proof,'RACE',queue,gate)) for _ in range(2)]
            for process in processes:process.start()
            gate.set()
            for process in processes:
                process.join(20);self.assertFalse(process.is_alive());self.assertEqual(process.exitcode,0)
            self.assertEqual(sorted(queue.get(timeout=2) for _ in processes),['REFUSED','RESERVED'])
            self.assertEqual(owner.study_snapshot()['study_dispatches'],1)


if __name__=='__main__':unittest.main()
