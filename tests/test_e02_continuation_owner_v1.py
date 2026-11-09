"""Same-owner continuation integration against isolated authored accounts."""
from contextlib import contextmanager
from copy import deepcopy
import json
import unittest
import uuid

from civiclab.common import canonical_bytes, canonical_hash
from civiclab.model import ExecutionBlocked
from civiclab.e02.exploratory_continuation_owner_v1 import (
    ContinuationOwnerV1, continuation_contract)
from test_e02_recovery_owner_v1 import recovery_case, settle_modern, rebind, modern_stats
from test_e02_exploratory_owner_v1 import reserve, phase_files


def bind(bundle):
    rebind(bundle['packet'])
    bundle['code_contract_hash']=canonical_hash(continuation_contract())
    bundle['review']={'kind':'INDEPENDENT_E02_CONTINUATION_REVIEW_V1',
        'reviewer_role':'independent_auditor','review_id':uuid.uuid4().hex,
        'inputs_hash':canonical_hash({k:v for k,v in bundle.items() if k!='review'})}
    return bundle


@contextmanager
def continuation_case():
    with recovery_case() as (old,q,proof,clock,historical):
        for _ in range(15):
            ack=reserve(old,q,proof);settle_modern(old,ack);old.commit_survey(ack['receipt'])
        ack=reserve(old,q,proof);receipt=ack['receipt']
        output,billing,generation=phase_files(old,ack,{'democratic_party':40,'republican_party':60})
        old.transition(receipt,'RESPONSE_SEEN',generation_id=generation,
            output_hash=canonical_hash(output),observed_cost=1)
        old.claim_statistics_lookup(receipt)
        old.transition(receipt,'UNCERTAIN',error_type='AuthoredUnavailableStatistics')
        owner=ContinuationOwnerV1()
        with owner._lock(),owner._connect() as db:state,head=owner._verify(db)
        response=json.loads((owner._journal(q['policy']['run_id'])/(receipt+'-response.json')).read_bytes())
        stats={'data':modern_stats(billing)}
        fresh=deepcopy(q);fresh['policy']['run_id']='AUTHORED_CONTINUATION'
        fresh['authority']['approval_id']=uuid.uuid4().hex
        fresh['review']['review_id']=uuid.uuid4().hex
        fresh['terminal_review']['review_id']=uuid.uuid4().hex
        b=bind({'kind':'E02_CONTINUATION_BUNDLE_V1','packet':fresh,
            'predecessor':{'head':head,'history_hash':canonical_hash(state['_prefix_events']),
                'rows_hash':canonical_hash(state['rows']),'study_hash':canonical_hash(state['study']),
                'claims_hash':canonical_hash(sorted(state['statistics_claims']))},
            'recovery':{'receipt':receipt,'response':response,'statistics':stats,
                'response_sha256':canonical_hash(response),'statistics_sha256':canonical_hash(stats)}})
        yield owner,b,proof,deepcopy(state['rows'])


class ContinuationOwnerTests(unittest.TestCase):
    def test_remaining_sixteen_complete_no_original_row_changes_or_replay(self):
        with continuation_case() as (owner,b,proof,rows):
            s=owner.start_continuation(b,proof,expected_bundle_hash=canonical_hash(b))
            self.assertEqual(len(s['transcript']),16);self.assertEqual(s['status'],'ACTIVE')
            self.assertEqual(s['study_dispatches'],16)
            with self.assertRaises(ExecutionBlocked):
                owner.start_continuation(b,proof,expected_bundle_hash=canonical_hash(b))
            seen=[]
            for _ in range(16):
                ack=reserve(owner,b['packet'],proof)
                seen.append((ack['request']['execution_order'],ack['request']['phase']))
                settle_modern(owner,ack);owner.commit_survey(ack['receipt'])
            s=reserve(owner,b['packet'],proof)
            self.assertEqual(seen,[(i,p) for i in range(8,16) for p in ('pre','post')])
            self.assertEqual(s['status'],'COMPLETE');self.assertEqual(s['study_dispatches'],32)
            self.assertEqual(s['consumed_microusd']['dispatches'],34)
            with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
            self.assertEqual(state['unfinished'],3)
            self.assertEqual({k:state['rows'][k] for k in rows},rows)
            self.assertTrue(state['continuation']['original_study']['stopped'])
            self.assertEqual(len(state['study']['witnesses']),32)

    def test_different_prefix_bill_response_and_prices_refuse_without_writes(self):
        with continuation_case() as (owner,original,proof,rows):
            before=owner.snapshot()
            for mutation in ('history','rows','bill','answer','price','request_cap'):
                b=deepcopy(original)
                if mutation in ('history','rows'):b['predecessor'][mutation+'_hash']='0'*64
                elif mutation=='bill':
                    b['recovery']['statistics']['data']['total_cost']=0.000002
                    b['recovery']['statistics_sha256']=canonical_hash(b['recovery']['statistics'])
                elif mutation=='answer':
                    b['recovery']['response']['choices'][0]['message']['content']='{"democratic_party":100,"republican_party":0}'
                    b['recovery']['response_sha256']=canonical_hash(b['recovery']['response'])
                elif mutation=='price':b['packet']['price_release']['terms']['requested_route']='openai'
                else:b['packet']['policy']['limits']['study_dispatches']=33
                bind(b)
                with self.subTest(mutation=mutation),self.assertRaises((ExecutionBlocked,ValueError)):
                    owner.start_continuation(b,proof,expected_bundle_hash=canonical_hash(b))
                self.assertEqual(owner.snapshot(),before)

    def test_missing_ancestral_file_blocks_no_new_phase(self):
        with continuation_case() as (owner,b,proof,rows):
            first=next(r for r in rows.values() if r['status']=='PHASE_COMMITTED')
            p=owner._journal(first['context']['run_id'])/(first['id']+'-response.json')
            p.write_bytes(b'{}')
            before=owner.snapshot()
            with self.assertRaises(ExecutionBlocked):
                owner.start_continuation(b,proof,expected_bundle_hash=canonical_hash(b))
            self.assertEqual(owner.snapshot(),before)

    def test_new_uncertainty_stops_without_another_reservation(self):
        with continuation_case() as (owner,b,proof,rows):
            owner.start_continuation(b,proof,expected_bundle_hash=canonical_hash(b))
            ack=reserve(owner,b['packet'],proof)
            owner.transition(ack['receipt'],'UNCERTAIN',error_type='AuthoredStop')
            s=reserve(owner,b['packet'],proof)
            self.assertEqual(s['status'],'STOPPED');self.assertEqual(s['study_dispatches'],17)
            with owner._lock(),owner._connect() as db:state,_=owner._verify(db)
            self.assertEqual(state['unfinished'],4)
            self.assertEqual({k:state['rows'][k] for k in rows},rows)


if __name__=='__main__':unittest.main()
