#!/usr/bin/env python3
"""Reproduce the authored global survey pilot/replay; no live model interface."""
import argparse
import json
from pathlib import Path
import re

from civiclab.common import atomic_json, canonical_hash
from civiclab.e02.experiment import assignments
from civiclab.live_billing_v2 import GlobalFixtureLedger
from civiclab.reconciled_client_v2 import fixture_terms
from civiclab.survey_envelope_v2 import compile_envelope
from civiclab.survey_global_execution_v2 import run_mock_global_bridge
from civiclab.survey_execution import DEMO_STIMULUS_HASHES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--scope-id', required=True, help='Fresh local MOCK scope, never a production owner allowance')
    parser.add_argument('--dry-run', action='store_true', help='Check input plans; write nothing and make no fake calls')
    args = parser.parse_args()
    if re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.scope_id) is None:
        parser.error('scope-id must contain1–64 letters, digits, underscore or hyphen')
    root = args.root.resolve(); scope = root/'data/processed/survey_global_fixture_scopes'/args.scope_id
    if scope.exists(): parser.error('fixture scope exists; no overwrite or reset')
    profiles = [{'profile_id': 'GLOBAL-PILOT-' + str(i+1).zfill(3), 'party': ('D','R','I')[i%3]} for i in range(12)]
    instrument = json.loads((root/'configs/e02_instrument.json').read_text())
    stimuli = json.loads((root/'configs/e02_demo_stimuli.json').read_text())
    if len(stimuli) != 3 or {canonical_hash(s) for s in stimuli} != DEMO_STIMULUS_HASHES:
        parser.error('exact three registered DEMO notices required')
    jobs = assignments(profiles, stimuli, 20261103)
    for job in jobs: compile_envelope(job, instrument, fixture_terms())
    if args.dry_run:
        print(json.dumps({'mode':'MOCK_ONLY_DRY_RUN','units_per_run':len(jobs),
                          'fake_calls_per_run':2*len(jobs),'planned_runs':2,'actual_budget_usd':0,'writes':0})); return
    scope.mkdir(mode=0o700, parents=True, exist_ok=False)
    ledger = GlobalFixtureLedger.create(scope/'owner')
    paths = [run_mock_global_bridge(root, profiles, stimuli, instrument, ledger=ledger) for _ in range(2)]
    def projection(path):
        fields = ('profile_id','stimulus_id','repeat','arm','execution_order','pre','post','scoring_party',
                  'pre_request','post_request','request_hashes','change','phase_status')
        return [{k:r[k] for k in fields} for r in json.loads((path/'responses.local.json').read_text())]
    if ((paths[0]/'analysis.json').read_bytes() != (paths[1]/'analysis.json').read_bytes()
        or canonical_hash(projection(paths[0])) != canonical_hash(projection(paths[1]))):
        raise RuntimeError('mock replay mismatch; preserved runs require inspection')
    result = {'mode':'MOCK_ONLY','runs':[p.name for p in paths],'same_fixture_owner':True,
              'owner_charges':len(ledger.snapshot()),'projection_sha256':canonical_hash(projection(paths[0])),
              'analysis_exact_replay':True,'actual_network_requests':0,'actual_model_calls':0,'actual_spend_usd':0}
    atomic_json(scope/'replay-receipt.local.json',result)
    print(json.dumps(result))


if __name__ == '__main__': main()
