"""Authored same-owner prefix/lifecycle only; never reads a real owner/key/source."""
from contextlib import contextmanager
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
from civiclab.e02 import wrapper_crossmodel_v1_client as client
from civiclab.e02.wrapper_crossmodel_v1_owner import WrapperCrossmodelOwnerV1,LIMITS,PROTOCOL,code_contract
import test_wrapper_visibility_execution_v1 as prior
from wrapper_crossmodel_v1_fixture_20261115 import try_reuse_prefix,retain_prefix,retain_case

class Transport(prior.Transport):
    def __init__(self,mode='success',owner=None):super().__init__(mode);self.owner=owner;self.reserved_before_post=False
    def post_bytes(self,raw):
        if self.posts==0 and self.owner is not None:
            state=self.owner.study_snapshot()
            self.reserved_before_post=state['batch_dispatches']==1
            assert self.reserved_before_post
        response=super().post_bytes(raw);old=response['id'];new=f'gen-wrapper-crossmodel-v1-authored-{self.posts}'
        self.models[new]=self.models.pop(old);response['id']=new
        if self.mode=='overrun':response['usage']['cost']=0.01
        return response
    def statistics(self,generation):
        result=super().statistics(generation)
        if self.mode=='wrong_route':result['data']['provider_name']='UNAPPROVED_PROVIDER'
        return result

def bind(q):
    p=q['policy'];p['code_contract_hash']=canonical_hash(code_contract())
    q['authority']={'kind':'WRAPPER_CROSSMODEL_AUTHORITY_V1','approval_id':uuid.uuid4().hex,
        'policy_hash':canonical_hash(p),'code_contract_hash':p['code_contract_hash']}
    q['review']={'kind':'INDEPENDENT_WRAPPER_CROSSMODEL_REVIEW_V1','reviewer_role':'independent_auditor',
        'review_id':uuid.uuid4().hex,'inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='review'})}
    return q

@contextmanager
def boundaries(owner,proofs,transport):
    with prior.boundaries(owner,proofs,transport) as calls, \
         patch.object(client,'_owner',return_value=owner), \
         patch.object(client,'_fetch_public_catalog',side_effect=prior.client._fetch_public_catalog), \
         patch.object(client,'_read_environment_key',return_value=_Credential('AUTHORED_ONLY_KEY_NOT_REAL_12345')), \
         patch.object(client,'_transport',return_value=transport):
        yield calls

class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if try_reuse_prefix(cls,bind):return
        # Reuse existing construction of an entirely authored, isolated109-row prefix.
        prior.LifecycleTests.setUpClass.__func__(cls)
        oldowner=prior.WrapperVisibilityOwnerV1();oldq=deepcopy(cls.packet)
        with prior.boundaries(oldowner,cls.proofs,prior.Transport()):
            result=prior.client.execute_wrapper_visibility(oldq,expected_packet_hash=canonical_hash(oldq))
        assert result['status']=='COMPLETE' and result['model_POST_attempts']==40
        owner=WrapperCrossmodelOwnerV1()
        with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
        assert len(state['rows'])==149 and state['unfinished']==4
        cls.before=deepcopy(state);cls.location=owner.directory
        assert 'AUTHORED_OS_HOME' in cls.location.parts and not cls.location.is_symlink()
        cache=Path(cls.stack.enter_context(tempfile.TemporaryDirectory())).resolve()/'WRAPPER_CROSSMODEL_V1_MOCK_PREFIX'
        shutil.copytree(cls.location,cache);cls.cache=cache
        releases=deepcopy(state['issue_cue_crossmodel_recovery']['packet']['price_release']);old=oldq['policy']
        p={'kind':'WRAPPER_CROSSMODEL_POLICY_V1','owner_id':owner.header['owner_id'],
            'run_id':'AUTHORED_WRAPPER_CROSSMODEL_V1_20261115','valid_from_utc':old['valid_from_utc'],
            'valid_until_utc':old['valid_until_utc'],'limits':deepcopy(LIMITS),
            'protocol_sha256':sha256_file(PROTOCOL),'price_release_hash':canonical_hash(releases),
            'consent_evidence_hash':canonical_hash('AUTHORED_STANDING_AUTHORITY'),
            'predecessor':{'head':head,'history_hash':canonical_hash(state['_prefix_events']),
                'rows_hash':canonical_hash(state['rows']),'study_hash':canonical_hash(state['study']),
                'continuation_hash':canonical_hash(state['continuation']),
                'alignment_hash':canonical_hash(state['alignment_followup']),
                'crossmodel_hash':canonical_hash(state['issue_cue_crossmodel']),
                'recovery_hash':canonical_hash(state['issue_cue_crossmodel_recovery']),
                'wrapper_hash':canonical_hash(state['wrapper_visibility']),
                'claims_hash':canonical_hash(sorted(state['statistics_claims'])),'consumed':deepcopy(state['consumed'])}}
        cls.packet=bind({'kind':'WRAPPER_CROSSMODEL_PACKET_V1','policy':p,'price_release':releases})
        retain_prefix(cls,owner)
    def setUp(self):
        assert 'AUTHORED_OS_HOME' in self.location.parts and not self.location.is_symlink()
        shutil.rmtree(self.location);shutil.copytree(self.cache,self.location)
        self.owner=WrapperCrossmodelOwnerV1();self.q=deepcopy(self.packet)
    def preserved(self):
        with self.owner._lock(),self.owner._connect() as db:state,head=self.owner._verify(db)
        b=self.before
        self.assertEqual(state['_prefix_events'][:len(b['_prefix_events'])],b['_prefix_events'])
        self.assertEqual({k:state['rows'][k] for k in b['rows']},b['rows'])
        for k in ('study','continuation','alignment_followup','issue_cue_crossmodel','issue_cue_crossmodel_recovery','wrapper_visibility'):
            self.assertEqual(state[k],b[k])
        self.assertEqual(sum(r['charged'] for r in state['rows'].values()),state['consumed']['total'])
        retain_case(self,self.owner,state,head)
        return state
    def test_full80_delayed_billing_preserves_prefix_holds_and_no_replay(self):
        t=Transport('delayed',self.owner)
        with boundaries(self.owner,self.proofs,t) as calls:
            result=client.execute_wrapper_crossmodel_v1(self.q,expected_packet_hash=canonical_hash(self.q))
        self.assertEqual(result['status'],'COMPLETE');self.assertEqual((t.posts,t.gets),(80,82))
        self.assertTrue(t.reserved_before_post);self.assertEqual(calls,['A','B']*8)
        self.assertEqual(result['catalog_GET_attempts'],16);self.assertEqual(len(result['response_envelope']['records']),80)
        self.assertEqual(result['analysis']['response_provenance'],'MOCK');self.assertFalse(result['snapshot']['saved_answers_reused'])
        state=self.preserved();self.assertEqual((state['consumed']['dispatches'],state['unfinished']),(229,4))
        self.assertEqual(state['wrapper_crossmodel']['refresh_stage'],7)
        newgens={state['rows'][r]['generation_id'] for r in state['wrapper_crossmodel']['receipts']}
        oldgens={r['generation_id'] for r in self.before['rows'].values() if r['generation_id']}
        self.assertEqual(len(newgens),80);self.assertTrue(oldgens.isdisjoint(newgens))
        for a,b in zip(t.payloads[::2],t.payloads[1::2]):
            self.assertNotEqual(a['model'],b['model']);self.assertEqual((a['seed'],a['messages']),(b['seed'],b['messages']))
        with self.assertRaises(ExecutionBlocked):self.owner.start_wrapper_crossmodel(self.q,self.proofs,expected_packet_hash=canonical_hash(self.q))
        with self.assertRaises(ExecutionBlocked):self.owner.transition(next(iter(self.before['rows'])),'UNCERTAIN',error_type='AuthoredForbiddenOldRow')
    def test_unknown_bill_stops_whole_batch_keeps_full_hold(self):
        t=Transport('404',self.owner)
        with boundaries(self.owner,self.proofs,t),self.assertRaises(_SafeExecutionFailure):
            client.execute_wrapper_crossmodel_v1(self.q,expected_packet_hash=canonical_hash(self.q))
        self.assertEqual((t.posts,t.gets),(1,3));state=self.preserved();self.assertEqual(state['unfinished'],5)
        row=state['rows'][state['wrapper_crossmodel']['receipts'][0]];self.assertEqual(row['charged'],row['reserved'])
        self.assertEqual(self.owner.study_snapshot()['status'],'STOPPED')
        self.assertEqual(self.owner.reserve_next(self.q,self.proofs,expected_packet_hash=canonical_hash(self.q),transport_ready=lambda c:True)['status'],'STOPPED')
    def test_unapproved_provider_and_known_overrun_stop_without_second_post(self):
        # Each subcase restores only this class's authored prefix, preserving failure logs in memory assertions.
        for mode,gets in [('wrong_route',1),('overrun',0)]:
            with self.subTest(mode=mode):
                if mode=='overrun':self.setUp()
                t=Transport(mode,self.owner)
                with boundaries(self.owner,self.proofs,t),self.assertRaises(_SafeExecutionFailure):
                    client.execute_wrapper_crossmodel_v1(self.q,expected_packet_hash=canonical_hash(self.q))
                self.assertEqual((t.posts,t.gets),(1,gets));state=self.preserved()
                row=state['rows'][state['wrapper_crossmodel']['receipts'][0]];self.assertGreaterEqual(row['charged'],row['reserved'])
                self.assertEqual(self.owner.study_snapshot()['status'],'STOPPED')
    def test_ancestry_cap_route_clock_refuse_before_new_reservation(self):
        before=self.owner.snapshot()
        for change in ('ancestry','count','money','model','clock'):
            q=deepcopy(self.q)
            if change=='ancestry':q['policy']['predecessor']['wrapper_hash']='0'*64
            elif change=='count':q['policy']['limits']['new_model_POSTs']=81
            elif change=='money':q['policy']['limits']['new_batch_microusd']=200001
            elif change=='model':q['price_release']['B']['terms']['reported_provider']='Azure'
            else:q['policy']['valid_until_utc']=q['policy']['valid_from_utc']
            bind(q)
            with self.subTest(change=change),self.assertRaises((ExecutionBlocked,ValueError)):
                self.owner.start_wrapper_crossmodel(q,self.proofs,expected_packet_hash=canonical_hash(q))
            self.assertEqual(self.owner.snapshot(),before)

if __name__=='__main__':unittest.main()
