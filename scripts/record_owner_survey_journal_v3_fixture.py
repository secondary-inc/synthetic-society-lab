#!/usr/bin/env python3
"""Record an authored miniature survey with renewal and same-owner replay.

Requires checkout helpers: PYTHONPATH=src:tests. No credentials or real transport.
"""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import time

from civiclab.common import atomic_json, canonical_hash, sha256_file
from civiclab.model import ExecutionBlocked
from civiclab.owner_budget_v3 import OwnerBudgetFixtureV3, SCOPE, production_owner_directory
from civiclab.survey_owner_execution_v3 import compile_owner_study
from test_survey_owner_execution_v3 import PROFILES, STIMULI, INSTRUMENT, T0, grant_study, execute


def record(directory):
    root=Path(directory).resolve()
    base=(Path(__file__).resolve().parents[1]/'data/processed/fixture_scopes').resolve()
    production=production_owner_directory().resolve()
    if base not in root.parents or root==production or production in root.parents:
        raise ExecutionBlocked('new directory within checkout fixture_scopes required')
    root.mkdir(parents=True,mode=0o700,exist_ok=False)
    now=[T0]; owner=OwnerBudgetFixtureV3.create_fixture(root/'authored-owner',clock=lambda:now[0])
    study=compile_owner_study(PROFILES,STIMULI[:1],INSTRUMENT)
    epoch1=grant_study(owner,study);start=time.monotonic()
    primary=execute(root,owner,study,epoch1,stop_after_phases=1)
    before=owner.snapshot();now[0]+=timedelta(minutes=2)
    epoch2=grant_study(owner,study,now=now[0])
    primary=execute(root,owner,study,epoch2,resume=primary)
    replay=execute(root,owner,study,epoch2)
    analysis=json.loads((primary/'analysis.json').read_text())
    if analysis!=json.loads((replay/'analysis.json').read_text()):
        raise AssertionError('authored analysis replay differs')
    snapshot=owner.snapshot();charges=snapshot['charges']
    if len(charges)!=20 or snapshot['consumed_microusd']['total']!=40:
        raise AssertionError('same-owner miniature fixture accounting differs')
    first=next(c for c in charges if c['id']==before['charges'][0]['id'])
    if first!=before['charges'][0] or first['context']['approval_hash']!=epoch1:
        raise AssertionError('renewal changed historical phase authority')
    atomic_json(root/'study.local.json',study)
    atomic_json(root/'owner-snapshot.local.json',snapshot)
    summary={'kind':SCOPE,'primary':str(primary.relative_to(root)), 'replay':str(replay.relative_to(root)),
             'expected_study_hash':canonical_hash(study),'approval_epochs':2,'units_per_run':5,
             'committed_phases':20,'simulated_microusd':40,'same_owner_no_reset':True,
             'original_phase_unchanged':True,'analysis_equal':True,'elapsed_seconds':time.monotonic()-start,
             'actual_owner_bootstraps':0,'human_approvals':0,'model_calls':0,'network_requests':0,'spend_usd':0,
             'scope':'MOCK miniature engineering control, no source population or human effects'}
    atomic_json(root/'summary.local.json',summary)
    hashes={str(p.relative_to(root)):sha256_file(p) for p in sorted(root.rglob('*')) if p.is_file()}
    atomic_json(root/'index.local.json',{'kind':SCOPE,'artifacts':hashes})
    return {**summary,'path':str(root),'index_sha256':sha256_file(root/'index.local.json'),'indexed_files':len(hashes)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',required=True)
    print(json.dumps(record(parser.parse_args().directory),sort_keys=True))
