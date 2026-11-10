"""Full saved-pair +54 lifecycle and uncertain-bill stop, wholly authored."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import unittest
import uuid
from unittest.mock import patch

from civiclab.common import canonical_bytes,canonical_hash,sha256_file
from civiclab.model import ExecutionBlocked
from civiclab.production_admission_v4 import _Credential
from civiclab.production_compatibility_v4_2_1 import _SafeExecutionFailure
from civiclab.e02 import issue_cue_crossmodel_client_v1 as old_client
from civiclab.e02 import issue_cue_crossmodel_recovery_client_v1 as client
from civiclab.e02.issue_cue_crossmodel_recovery_owner_v1 import CrossmodelRecoveryOwnerV1,LIMITS,PROTOCOL,code_contract
from civiclab.e02.crossmodel_saved_pair_v1 import admit_saved_pair,KIND,FIELDS
from civiclab.e02.issue_cue_crossmodel_v1 import PROTOCOL_SHA256
from civiclab.e02.crossmodel_price_v1 import contract_from_catalog,fresh_proof
import test_issue_cue_crossmodel_execution_v1 as prior
from test_crossmodel_price_metadata_v1 import qwen_release as original_qwen_release
from test_production_price_v4 import T0


def qwen_release():
    data,release,receipt=original_qwen_release()
    data['data']['endpoints'][0]['pricing']['request']='0.001008'
    raw=canonical_bytes(data);d=release['interpretation'];d['catalog_sha256']=canonical_hash(data)
    release['terms']=contract_from_catalog(raw,d,expected_decision_hash=canonical_hash(d))
    receipt['body_sha256']=canonical_hash(data)
    return data,release,receipt


class SavedPairTransport(prior.Transport):
    def post_bytes(self,raw):
        result=super().post_bytes(raw)
        result['usage']['cost']=0.000072 if self.posts==1 else 0.0000726
        return result
    def statistics(self,generation):
        result=super().statistics(generation)
        result['data']['total_cost']=0.000072 if generation.endswith('-1') else 0.0000726
        if not result['data']['model'].startswith('openai/'):result['data']['service_tier']=None
        return result


class RecoveryTransport(prior.Transport):
    def post_bytes(self,raw):
        result=super().post_bytes(raw)
        old_id=result['id'];new_id=f'gen-crossmodel-recovery-authored-{self.posts}'
        self.models[new_id]=self.models.pop(old_id);result['id']=new_id
        return result
    def statistics(self,generation):
        result=super().statistics(generation)
        if not result['data']['model'].startswith('openai/'):result['data']['service_tier']=None
        return result


def bundle_for(owner,state):
    old=state['issue_cue_crossmodel'];bundle={'kind':KIND,'protocol_sha256':PROTOCOL_SHA256,
        'source_packet_sha256':canonical_hash(old['packet']),'source_run_id':old['packet']['policy']['run_id'],'pairs':[]}
    base=owner._journal(bundle['source_run_id'])
    for rid in old['receipts']:
        entry={'receipt':rid,'row_sha256':canonical_hash(state['rows'][rid])}
        for name in FIELDS:
            raw=(base/(rid+'-'+name+'.json')).read_bytes()
            entry[name+'_utf8']=raw.decode();entry[name+'_sha256']=hashlib.sha256(raw).hexdigest()
        bundle['pairs'].append(entry)
    return bundle


def bind(q):
    p=q['policy'];p['code_contract_hash']=canonical_hash(code_contract());p['saved_pair_hash']=canonical_hash(q['saved_pair'])
    q['authority']={'kind':'CROSSMODEL_RECOVERY_AUTHORITY_V1','approval_id':uuid.uuid4().hex,
        'policy_hash':canonical_hash(p),'code_contract_hash':p['code_contract_hash']}
    q['review']={'kind':'INDEPENDENT_CROSSMODEL_RECOVERY_REVIEW_V1','reviewer_role':'independent_auditor',
        'review_id':uuid.uuid4().hex,'inputs_hash':canonical_hash({k:v for k,v in q.items() if k!='review'})}
    return q


@contextmanager
def case():
    with patch.object(prior,'qwen_release',side_effect=qwen_release),prior.case() as (old_owner,old_q,proofs,_):
        stopped=SavedPairTransport()
        with prior.boundaries(old_owner,proofs,stopped), unittest.TestCase().assertRaises(_SafeExecutionFailure):
            old_client.execute_crossmodel(old_q,expected_packet_hash=canonical_hash(old_q))
        assert (stopped.posts,stopped.gets)==(2,2)
        owner=CrossmodelRecoveryOwnerV1()
        with owner._lock(),owner._connect() as db:before,head=owner._verify(db)
        assert len(before['rows'])==58 and before['unfinished']==4
        saved=bundle_for(owner,before); old=old_q['policy'];releases=deepcopy(old_q['price_release'])
        p={'kind':'CROSSMODEL_RECOVERY_POLICY_V1','owner_id':owner.header['owner_id'],
           'run_id':'AUTHORED_ISSUE_CUE_CROSSMODEL_RECOVERY','valid_from_utc':old['valid_from_utc'],
           'valid_until_utc':old['valid_until_utc'],'limits':deepcopy(LIMITS),
           'protocol_sha256':sha256_file(PROTOCOL),'price_release_hash':canonical_hash(releases),
           'consent_evidence_hash':canonical_hash('AUTHORED_STANDING_AUTHORITY'),
           'predecessor':{'head':head,'history_hash':canonical_hash(before['_prefix_events']),
             'rows_hash':canonical_hash(before['rows']),'study_hash':canonical_hash(before['study']),
             'continuation_hash':canonical_hash(before['continuation']),
             'alignment_hash':canonical_hash(before['alignment_followup']),
             'crossmodel_hash':canonical_hash(before['issue_cue_crossmodel']),
             'claims_hash':canonical_hash(sorted(before['statistics_claims'])),'consumed':deepcopy(before['consumed'])}}
        q=bind({'kind':'CROSSMODEL_RECOVERY_PACKET_V1','policy':p,'price_release':releases,'saved_pair':saved})
        yield owner,q,proofs,deepcopy(before),saved


@contextmanager
def boundaries(owner,proofs,transport):
    with prior.boundaries(owner,proofs,transport) as calls, \
         patch.object(client,'_owner',return_value=owner), \
         patch.object(client,'_fetch_public_catalog',side_effect=old_client._fetch_public_catalog), \
         patch.object(client,'_read_environment_key',return_value=_Credential('AUTHORED_ONLY_KEY_NOT_REAL_12345')), \
         patch.object(client,'_transport',return_value=transport):
        yield calls



class HarnessTests(unittest.TestCase):
    def test_saved_and_recovery_generation_ids_are_disjoint_and_lookup_matches(self):
        raw=canonical_bytes({'model':'qwen/qwen3-30b-a3b-instruct-2507'})
        a=SavedPairTransport();b=RecoveryTransport()
        saved={a.post_bytes(raw)['id'] for _ in range(2)}
        fresh={b.post_bytes(raw)['id'] for _ in range(54)}
        self.assertTrue(saved.isdisjoint(fresh));self.assertEqual(len(fresh),54)
        for generation in fresh:self.assertEqual(b.statistics(generation)['data']['id'],generation)

class RecoveryTests(unittest.TestCase):
    def test_saved_pair_plus54_preserves_every_old_row_prefix_and_hold(self):
        with case() as (owner,q,proofs,before,saved):
            raw=PROTOCOL.read_bytes();old=before['issue_cue_crossmodel']
            admitted=admit_saved_pair(raw,saved,old,before['rows'],before['statistics_claims'])
            self.assertEqual(admitted['new_POSTs'],0);self.assertEqual(admitted['new_GETs'],0)
            self.assertEqual([w['execution_order'] for w in admitted['witnesses']],[0,1])
            # Pure corruption/identity/billing/ancestry cases share one setup.
            for change in ('hash','payload','generation','cost','tier','receipt','row','claim','swapped','stopped','override'):
                bad=deepcopy(saved);badold=deepcopy(old);rows=deepcopy(before['rows']);claims=set(before['statistics_claims'])
                entry=bad['pairs'][1]
                if change=='hash':entry['response_sha256']='0'*64
                elif change in ('payload','override'):
                    v=json.loads(entry['request_utf8']);v['request']['payload']['service_tier']='default'
                    entry['request_utf8']=canonical_bytes(v).decode();entry['request_sha256']=canonical_hash(v)
                elif change in ('generation','cost','tier'):
                    v=json.loads(entry['statistics_utf8']);v['data'][{'generation':'id','cost':'total_cost','tier':'service_tier'}[change]]={'generation':'gen-other','cost':0.001,'tier':'priority'}[change]
                    entry['statistics_utf8']=canonical_bytes(v).decode();entry['statistics_sha256']=canonical_hash(v)
                elif change=='receipt':entry['receipt']='0'*32
                elif change=='row':rows[entry['receipt']]['charged']-=1
                elif change=='claim':claims.remove(entry['receipt'])
                elif change=='swapped':bad['pairs'].reverse()
                elif change=='stopped':badold['stopped']=False
                with self.subTest(change=change),self.assertRaises((ExecutionBlocked,ValueError)):
                    admit_saved_pair(raw,bad,badold,rows,claims)
            for change in ('ancestry','cap','exposure'):
                bad=deepcopy(q)
                if change=='ancestry':bad['policy']['predecessor']['crossmodel_hash']='0'*64
                if change=='cap':bad['policy']['limits']['new_model_POSTs']=55
                if change=='exposure':bad['policy']['limits']['new_batch_microusd']=100000
                bind(bad)
                with self.subTest(packet=change),self.assertRaises((ExecutionBlocked,ValueError)):
                    owner.start_recovery(bad,proofs,expected_packet_hash=canonical_hash(bad))
            t=RecoveryTransport('delayed')
            with boundaries(owner,proofs,t) as calls:
                try:result=client.execute_recovery(q,expected_packet_hash=canonical_hash(q))
                except _SafeExecutionFailure as error:
                    print('AUTHORED_SAFE_DIAGNOSTIC',error.diagnostic,flush=True)
                    raise
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual((t.posts,t.gets),(54,56))
            self.assertEqual(calls,['A','B']*4);self.assertEqual(result['catalog_GET_attempts'],8)
            self.assertEqual(len(result['response_envelope']['records']),56)
            self.assertEqual(result['analysis']['response_provenance'],'MOCK')
            self.assertEqual(result['snapshot']['batch_dispatches'],54)
            self.assertTrue(result['snapshot']['saved_pair_reused_without_dispatch'])
            self.assertIn('separately released',result['snapshot']['cross_batch_gap_limitation'])
            expected=__import__('civiclab.e02.issue_cue_crossmodel_v1',fromlist=['load_protocol']).load_protocol(raw)['jobs'][2]
            self.assertEqual(json.loads(t.payloads[0]['messages'][1]['content'])['profile'],expected['profile'])
            with owner._lock(),owner._connect() as db:after,_=owner._verify(db)
            self.assertEqual(after['consumed']['dispatches'],112);self.assertEqual(len(after['rows']),112)
            self.assertEqual(after['unfinished'],4)
            old_generations={r['generation_id'] for r in before['rows'].values() if r['generation_id'] is not None}
            new_generations={after['rows'][rid]['generation_id'] for rid in after['issue_cue_crossmodel_recovery']['receipts']}
            self.assertEqual(len(new_generations),54);self.assertTrue(old_generations.isdisjoint(new_generations))
            self.assertEqual(after['issue_cue_crossmodel_recovery']['refresh_stage'],3)
            self.assertEqual(after['_prefix_events'][:len(before['_prefix_events'])],before['_prefix_events'])
            self.assertEqual({rid:after['rows'][rid] for rid in before['rows']},before['rows'])
            for name in ('study','continuation','alignment_followup','issue_cue_crossmodel'):
                self.assertEqual(after[name],before[name])
            self.assertEqual(sum(r['charged'] for r in after['rows'].values()),after['consumed']['total'])
            self.assertEqual(sum(after['rows'][rid]['charged'] for rid in old['receipts']),1080)
            self.assertLessEqual(result['snapshot']['batch_charged_microusd']+1080,100000)
            self.assertTrue(all(r['execution_order']>=2 for r in after['issue_cue_crossmodel_recovery']['witnesses'][2:]))
            with self.assertRaises(ExecutionBlocked):owner.start_recovery(q,proofs,expected_packet_hash=canonical_hash(q))
            with self.assertRaises(ExecutionBlocked):owner.transition(old['receipts'][1],'UNCERTAIN',error_type='AuthoredForbiddenOldRow')

    def test_recovery_unknown_billing_stops_without_releasing_saved_or_old_holds(self):
        with case() as (owner,q,proofs,before,saved):
            t=RecoveryTransport('404')
            with boundaries(owner,proofs,t) as calls,self.assertRaises(_SafeExecutionFailure):
                client.execute_recovery(q,expected_packet_hash=canonical_hash(q))
            self.assertEqual((t.posts,t.gets),(1,3));self.assertEqual(calls,['A','B'])
            snapshot=owner.study_snapshot();self.assertEqual(snapshot['status'],'STOPPED')
            self.assertEqual([r['execution_order'] for r in snapshot['transcript']],[0,1,2])
            with owner._lock(),owner._connect() as db:after,_=owner._verify(db)
            self.assertEqual(after['unfinished'],5)
            self.assertEqual({rid:after['rows'][rid] for rid in before['rows']},before['rows'])
            self.assertEqual(after['issue_cue_crossmodel'],before['issue_cue_crossmodel'])
            new=after['rows'][after['issue_cue_crossmodel_recovery']['receipts'][0]]
            self.assertEqual(new['charged'],new['reserved'])
            self.assertEqual(owner.reserve_next(q,proofs,expected_packet_hash=canonical_hash(q),transport_ready=lambda c:True)['status'],'STOPPED')

if __name__=='__main__':unittest.main()
