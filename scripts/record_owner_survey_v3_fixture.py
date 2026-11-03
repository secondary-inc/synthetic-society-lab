#!/usr/bin/env python3
"""Retain an AUTHORED owner-client control, never a real model run.

Checkout fixture helper dependency: run with PYTHONPATH=src:tests. No key,
network transport, production directory, real approval or budget options.
"""
import argparse
from datetime import timedelta
import json
from pathlib import Path

from civiclab.common import atomic_json, canonical_hash, sha256_file
from civiclab.model import ExecutionBlocked
from civiclab.owner_budget_v3 import OwnerBudgetFixtureV3, SCOPE, production_owner_directory
from civiclab.owner_survey_client_v3 import OwnerSurveyFixtureClientV3
from civiclab.reconciled_client_v2 import FixtureHTTP, fixture_terms
from test_owner_survey_client_v3 import T0, make_plan, grant, checkpoint


def record(directory):
    root=Path(directory).resolve()
    base=(Path(__file__).resolve().parents[1]/'data/processed/fixture_scopes').resolve()
    production=production_owner_directory().resolve()
    if base not in root.parents or root==production or production in root.parents:
        raise ExecutionBlocked('new directory within checkout fixture_scopes required')
    root.mkdir(parents=True,mode=0o700,exist_ok=False)
    terms=fixture_terms();terms.update(input_usd_per_token='0.0000000001',output_usd_per_token='0',request_fee_usd='0.0000001')
    plan=make_plan(terms); now=[T0]
    owner=OwnerBudgetFixtureV3.create_fixture(root/'authored-owner',clock=lambda:now[0])
    epoch=grant(owner,plan,total=1); http=FixtureHTTP(terms);client=OwnerSurveyFixtureClientV3(owner,terms,http)
    payloads=[];original=http.post
    def post(payload):
        payloads.append(json.loads(json.dumps(payload)));return original(payload)
    # Scoped recording of the exact fake provider. This is not an injectable
    # production transport or an owner-approval mechanism.
    http.post=post
    args={'expected_plan_hash':canonical_hash(plan),'expected_approval_hash':epoch,'run_id':'AUTHORED-OWNER-CLIENT-V3'}
    first=client.complete(plan,phase='pre',**args)
    blocked=[]
    def refuse(label,call):
        before=(owner.db_path.read_bytes(),owner.anchor.read_bytes());count=len(http.calls)
        try:call()
        except ExecutionBlocked:pass
        else:raise AssertionError('fixture expected refusal: '+label)
        if before!=(owner.db_path.read_bytes(),owner.anchor.read_bytes()) or len(http.calls)!=count:
            raise AssertionError('refusal changed owner or dispatched: '+label)
        blocked.append({'case':label,'additional_fake_calls':0,'owner_bytes_unchanged':True})
    after={'phase':'post','before':first['answer']['parsed']}
    refuse('unfinished-phase',lambda:client.complete(plan,**after,**args))
    checkpoint(owner,first)
    refuse('lifetime-exhausted',lambda:client.complete(plan,**after,**args))
    now[0]+=timedelta(minutes=1);new_epoch=grant(owner,plan,total=2,now=now[0])
    refuse('stale-expired-approval-after-renewal',lambda:client.complete(plan,**after,**args))
    args['expected_approval_hash']=new_epoch
    second=client.complete(plan,**after,**args);checkpoint(owner,second)
    snapshot=owner.snapshot()
    if snapshot['consumed_microusd']['total']!=2 or len(snapshot['charges'])!=2:
        raise AssertionError('per-request lifetime control failed')
    for name,value in (('plan',plan),('payloads',payloads),('completions',[first,second]),('snapshot',snapshot),('negative-side-effects',blocked),('fake-calls',http.calls)):
        atomic_json(root/(name+'.local.json'),value)
    index={str(p.relative_to(root)):sha256_file(p) for p in sorted(root.rglob('*')) if p.is_file()}
    atomic_json(root/'index.local.json',{'kind':SCOPE,'artifacts':index})
    return {'kind':SCOPE,'path':str(root),'index_sha256':sha256_file(root/'index.local.json'),
            'indexed_files':len(index),'fake_POSTs':2,'fake_statistics_calls':2,'committed_phases':2,
            'approval_epochs':2,'retained_simulated_microusd':2,'zero_side_effect_refusals':len(blocked),
            'actual_owner_bootstraps':0,'human_approvals':0,'model_calls':0,'network_requests':0,'spend_usd':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',required=True)
    print(json.dumps(record(parser.parse_args().directory),sort_keys=True))
