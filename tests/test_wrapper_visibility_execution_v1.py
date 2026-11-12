"""Wholly authored same-owner wrapper lifecycle; no real keys, owner or HTTP.

The prefix is generated once using the real earlier state machines in a fake OS
home. Each test gets a byte copy of that closed MOCK prefix. No production
allowance, old packet, charge, source or journal is read or modified.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import uuid
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash,sha256_file
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from civiclab.production_compatibility_v4_2_1 import _SafeExecutionFailure
from civiclab.e02 import wrapper_visibility_client_v1 as client
from civiclab.e02.wrapper_visibility_owner_v1 import (
    WrapperVisibilityOwnerV1,LIMITS,PROTOCOL,code_contract,refresh_stage_for_slot,validate_refresh)
import test_issue_cue_crossmodel_recovery_execution_v1 as prior


class ClosedPrefixTransport(prior.RecoveryTransport):
    def post_bytes(self,raw):
        response=super().post_bytes(raw)
        # Sixth recovery POST is global baseline7: three SHOWN posts will skip.
        if self.posts==6:
            answer=json.loads(response['choices'][0]['message']['content'])
            answer['library_support']=None
            response['choices'][0]['message']['content']=json.dumps(answer)
        return response


class Transport(prior.RecoveryTransport):
    def post_bytes(self,raw):
        response=super().post_bytes(raw)
        old=response['id'];new=f'gen-wrapper-authored-{self.posts}'
        self.models[new]=self.models.pop(old);response['id']=new
        response['choices'][0]['message']['content']=json.dumps({
            'democratic_party':50,'republican_party':50,
            'policy_support':None if self.mode=='skip' and self.posts==1 else 50,
            'factual_answer':'NOT_REPORTED'})
        return response


def bind(q):
    p=q['policy'];p['code_contract_hash']=canonical_hash(code_contract())
    q['authority']={'kind':'WRAPPER_VISIBILITY_AUTHORITY_V1','approval_id':uuid.uuid4().hex,
        'policy_hash':canonical_hash(p),'code_contract_hash':p['code_contract_hash']}
    q['review']={'kind':'INDEPENDENT_WRAPPER_VISIBILITY_REVIEW_V1','reviewer_role':'independent_auditor',
        'review_id':uuid.uuid4().hex,'inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='review'})}
    return q


@contextmanager
def boundaries(owner,proofs,transport):
    with prior.boundaries(owner,proofs,transport) as calls, \
         patch.object(client,'_owner',return_value=owner), \
         patch.object(client,'_fetch_public_catalog',side_effect=prior.old_client._fetch_public_catalog), \
         patch.object(client,'_read_environment_key',return_value=_Credential('AUTHORED_ONLY_KEY_NOT_REAL_12345')), \
         patch.object(client,'_transport',return_value=transport):
        yield calls


class RefreshTests(unittest.TestCase):
    def test_each_slot_and_skipped_barrier_crossing(self):
        self.assertEqual([refresh_stage_for_slot(i) for i in range(40)],
                         [0]*10+[1]*10+[2]*10+[3]*10)
        for bad in (-1,40,True,1.0,'10'):
            with self.subTest(bad=bad),self.assertRaises(ExecutionBlocked):refresh_stage_for_slot(bad)
        # A jump caused by skipped posts still consumes each missing stage once.
        for stage in range(3):validate_refresh(stage,31,stage+1)
        for args in [(0,9,1),(0,10,2),(1,10,1),(3,39,4),(True,20,2)]:
            with self.subTest(args=args),self.assertRaises(ExecutionBlocked):validate_refresh(*args)


class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack=ExitStack();cls.addClassCleanup(cls.stack.close)
        old,oldq,proofs,before,saved=cls.stack.enter_context(prior.case())
        transport=ClosedPrefixTransport()
        with prior.boundaries(old,proofs,transport):
            result=prior.client.execute_recovery(oldq,expected_packet_hash=canonical_hash(oldq))
        assert result['status']=='COMPLETE' and transport.posts==51
        owner=WrapperVisibilityOwnerV1()
        with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
        assert len(state['rows'])==109 and state['unfinished']==4
        assert len(state['issue_cue_crossmodel_recovery']['witnesses'])==53
        cls.before=deepcopy(state);cls.proofs=deepcopy(proofs);cls.location=owner.directory
        assert 'AUTHORED_OS_HOME' in cls.location.parts and not cls.location.is_symlink()
        cache=Path(cls.stack.enter_context(tempfile.TemporaryDirectory())).resolve()/'MOCK_PREFIX'
        shutil.copytree(cls.location,cache);cls.cache=cache
        oldpolicy=oldq['policy'];releases={'B':deepcopy(oldq['price_release']['B'])}
        p={'kind':'WRAPPER_VISIBILITY_POLICY_V1','owner_id':owner.header['owner_id'],
           'run_id':'AUTHORED_WRAPPER_VISIBILITY','valid_from_utc':oldpolicy['valid_from_utc'],
           'valid_until_utc':oldpolicy['valid_until_utc'],'limits':deepcopy(LIMITS),
           'protocol_sha256':sha256_file(PROTOCOL),'price_release_hash':canonical_hash(releases),
           'consent_evidence_hash':canonical_hash('AUTHORED_STANDING_AUTHORITY'),
           'predecessor':{'head':head,'history_hash':canonical_hash(state['_prefix_events']),
             'rows_hash':canonical_hash(state['rows']),'study_hash':canonical_hash(state['study']),
             'continuation_hash':canonical_hash(state['continuation']),
             'alignment_hash':canonical_hash(state['alignment_followup']),
             'crossmodel_hash':canonical_hash(state['issue_cue_crossmodel']),
             'recovery_hash':canonical_hash(state['issue_cue_crossmodel_recovery']),
             'claims_hash':canonical_hash(sorted(state['statistics_claims'])),'consumed':deepcopy(state['consumed'])}}
        cls.packet=bind({'kind':'WRAPPER_VISIBILITY_PACKET_V1','policy':p,'price_release':releases})

    def setUp(self):
        # Only restore this class's temporary, wholly authored financial tree.
        assert 'AUTHORED_OS_HOME' in self.location.parts and not self.location.is_symlink()
        shutil.rmtree(self.location);shutil.copytree(self.cache,self.location)
        self.owner=WrapperVisibilityOwnerV1();self.q=deepcopy(self.packet)

    def verify_preserved(self):
        with self.owner._lock(),self.owner._connect() as db:state,_=self.owner._verify(db)
        before=self.before
        self.assertEqual(state['_prefix_events'][:len(before['_prefix_events'])],before['_prefix_events'])
        self.assertEqual({k:state['rows'][k] for k in before['rows']},before['rows'])
        for name in ('study','continuation','alignment_followup','issue_cue_crossmodel','issue_cue_crossmodel_recovery'):
            self.assertEqual(state[name],before[name])
        self.assertEqual(sum(r['charged'] for r in state['rows'].values()),state['consumed']['total'])
        return state

    def test_complete40_delayed_billing_preserves_all_prefix_and_four_holds(self):
        t=Transport('delayed')
        with boundaries(self.owner,self.proofs,t) as calls:
            result=client.execute_wrapper_visibility(self.q,expected_packet_hash=canonical_hash(self.q))
        self.assertEqual(result['status'],'COMPLETE');self.assertEqual((t.posts,t.gets),(40,42))
        self.assertEqual(calls,['B']*4);self.assertEqual(result['catalog_GET_attempts'],4)
        self.assertEqual(len(result['response_envelope']['records']),40)
        self.assertEqual(result['analysis']['response_provenance'],'MOCK')
        self.assertFalse(result['snapshot']['saved_answers_reused'])
        state=self.verify_preserved();self.assertEqual(state['consumed']['dispatches'],149)
        self.assertEqual(state['unfinished'],4);self.assertEqual(state['wrapper_visibility']['refresh_stage'],3)
        oldgens={r['generation_id'] for r in self.before['rows'].values() if r['generation_id']}
        newgens={state['rows'][r]['generation_id'] for r in state['wrapper_visibility']['receipts']}
        self.assertEqual(len(newgens),40);self.assertTrue(oldgens.isdisjoint(newgens))
        self.assertLessEqual(result['snapshot']['batch_charged_microusd'],75000)
        with self.assertRaises(ExecutionBlocked):
            self.owner.start_wrapper_visibility(self.q,{'B':self.proofs['B']},expected_packet_hash=canonical_hash(self.q))
        with self.assertRaises(ExecutionBlocked):
            self.owner.transition(next(iter(self.before['rows'])),'UNCERTAIN',error_type='AuthoredForbiddenOldRow')
        self.assertEqual(self.owner.reserve_next(self.q,{'B':self.proofs['B']},expected_packet_hash=canonical_hash(self.q),transport_ready=lambda c:True)['status'],'COMPLETE')

    def test_unknown_bill_stops_after_one_post_three_gets_keeps_full_new_hold(self):
        t=Transport('404')
        with boundaries(self.owner,self.proofs,t) as calls,self.assertRaises(_SafeExecutionFailure):
            client.execute_wrapper_visibility(self.q,expected_packet_hash=canonical_hash(self.q))
        self.assertEqual((t.posts,t.gets),(1,3));self.assertEqual(calls,['B'])
        state=self.verify_preserved();self.assertEqual(state['unfinished'],5)
        row=state['rows'][state['wrapper_visibility']['receipts'][0]]
        self.assertEqual(row['charged'],row['reserved']);self.assertEqual(self.owner.study_snapshot()['status'],'STOPPED')
        self.assertEqual(self.owner.reserve_next(self.q,{'B':self.proofs['B']},expected_packet_hash=canonical_hash(self.q),transport_ready=lambda c:True)['status'],'STOPPED')

    def test_invalid_own_baseline_skips_only_two_shown_posts_without_charge(self):
        t=Transport('skip')
        with boundaries(self.owner,self.proofs,t) as calls:
            result=client.execute_wrapper_visibility(self.q,expected_packet_hash=canonical_hash(self.q))
        self.assertEqual(result['status'],'COMPLETE');self.assertEqual((t.posts,t.gets),(38,38))
        self.assertEqual(calls,['B']*4)
        rows=result['response_envelope']['records'];skipped=[r for r in rows if r['status']=='SKIPPED_INVALID_PRE']
        self.assertEqual(len(skipped),2)
        state=self.verify_preserved();self.assertEqual(state['consumed']['dispatches'],147)
        self.assertEqual(state['unfinished'],4)

    def test_changed_ancestry_caps_model_and_clock_refuse_before_new_rows(self):
        before=self.owner.snapshot()
        for change in ('ancestry','count','money','model','clock'):
            q=deepcopy(self.q)
            if change=='ancestry':q['policy']['predecessor']['recovery_hash']='0'*64
            elif change=='count':q['policy']['limits']['new_model_POSTs']=41
            elif change=='money':q['policy']['limits']['new_batch_microusd']=75001
            elif change=='model':q['price_release']['B']['terms']['reported_provider']='Azure'
            else:q['policy']['valid_until_utc']=q['policy']['valid_from_utc']
            bind(q)
            with self.subTest(change=change),self.assertRaises((ExecutionBlocked,ValueError)):
                self.owner.start_wrapper_visibility(q,{'B':self.proofs['B']},expected_packet_hash=canonical_hash(q))
            self.assertEqual(self.owner.snapshot(),before)


if __name__=='__main__':unittest.main()
