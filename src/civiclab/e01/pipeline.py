"""Conservative, stdlib-only E01 baseline and evidence gates.

Outcome files enter only evaluation. This is a tested data-flow boundary, not an
OS sandbox or independent timestamp. DEMO input contains invented toy numbers.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Iterable

from civiclab.common import canonical_hash, sha256_file, RunStore

STATES = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())
RACE_FIELDS = {'race_id', 'year', 'state', 'office', 'district', 'seat_class', 'stage',
               'special', 'election_date', 'cutoff', 'geography', 'candidates', 'status'}
FEATURE_FIELDS = {'race_id', 'office', 'prior_margin_pp', 'national_shift_pp',
                  'incumbency_adjustment_pp', 'feature_as_of', 'cutoff', 'source_hashes'}


def _exact(obj, fields, name):
    if not isinstance(obj, dict) or set(obj) != fields:
        raise ValueError(f'{name}: exact fields required; missing={fields-set(obj) if isinstance(obj, dict) else fields}, extra={set(obj)-fields if isinstance(obj, dict) else set()}')


def _hash(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9a-f]{64}', value))


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_race(race: dict) -> dict:
    """Validate verified manifest evidence, never infer ballot status from FEC."""
    _exact(race, RACE_FIELDS, 'race')
    if race['status'] != 'RETROSPECTIVE':
        raise ValueError('E01 accepts RETROSPECTIVE status only')
    if type(race['year']) is not int or race['state'] not in STATES or race['office'] not in {'HOUSE', 'SENATE'}:
        raise ValueError('invalid year/state/office')
    if race['stage'] != 'GEN' or type(race['special']) is not bool or race['special']:
        raise ValueError('S0 initially supports regular general elections only; no runoffs/specials')
    election_date, cutoff = date.fromisoformat(race['election_date']), date.fromisoformat(race['cutoff'])
    if election_date.year != race['year'] or cutoff >= election_date:
        raise ValueError('cutoff must precede target election date')
    if race['office'] == 'SENATE':
        if race['district'] != 'STATEWIDE' or type(race['seat_class']) is not int or race['seat_class'] not in (1, 2, 3):
            raise ValueError('Senate requires explicit seat class and statewide geography')
    elif not isinstance(race['district'], str) or not re.fullmatch(r'\d{2}', race['district']) or race['seat_class'] is not None:
        raise ValueError('House requires two-digit district (00 at large), no Senate class')
    expected_id = f"{race['year']}-{race['state']}-{race['office']}-{race['district']}" + (f"-C{race['seat_class']}" if race['office'] == 'SENATE' else '')
    if race['race_id'] != expected_id:
        raise ValueError('noncanonical race ID')
    geo = race['geography']
    _exact(geo, {'vintage', 'official_source', 'sha256', 'verified'}, 'geography')
    if geo['verified'] is not True or not geo['vintage'] or not geo['official_source'] or not _hash(geo['sha256']):
        raise ValueError('geography requires verified source bytes and vintage')
    candidates = race['candidates']
    if not isinstance(candidates, list) or not candidates:
        raise ValueError('candidate list missing')
    seen = set()
    for c in candidates:
        _exact(c, {'candidate_id', 'name', 'party', 'official_ballot_source', 'sha256', 'verified'}, 'candidate')
        if c['verified'] is not True or not c['candidate_id'] or not c['name'] or not c['official_ballot_source'] or not _hash(c['sha256']):
            raise ValueError('official ballot verification required; FEC registration insufficient')
        if c['candidate_id'] in seen or c['party'] not in {'DEMOCRAT', 'REPUBLICAN', 'OTHER'}:
            raise ValueError('duplicate candidate ID or unsupported party mapping')
        seen.add(c['candidate_id'])
    for party in ('DEMOCRAT', 'REPUBLICAN'):
        if sum(c['party'] == party for c in candidates) != 1:
            raise ValueError('S0 requires exactly one verified candidate from each major party')
    return race


def validate_pair(prior: dict, target: dict, crosswalk: dict | None = None) -> None:
    """A Senate two-year gap is not a same-seat baseline; House maps must match."""
    validate_race(prior)
    validate_race(target)
    if any(prior[k] != target[k] for k in ('state', 'office', 'district', 'seat_class')):
        raise ValueError('prior/target constituency or Senate seat mismatch')
    expected_gap = 6 if target['office'] == 'SENATE' else 2
    if target['year'] - prior['year'] != expected_gap:
        raise ValueError(f'same-seat baseline requires {expected_gap}-year lag')
    if date.fromisoformat(prior['election_date']) >= date.fromisoformat(target['cutoff']):
        raise ValueError('prior outcome unavailable at target cutoff')
    if prior['geography']['vintage'] != target['geography']['vintage'] or prior['geography']['sha256'] != target['geography']['sha256']:
        if crosswalk is None:
            raise ValueError('changed maps require verified prior returns reaggregation')
        _exact(crosswalk, {'verified', 'source_vintage', 'target_vintage', 'sha256', 'method', 'reaggregated_returns_sha256'}, 'crosswalk')
        if (crosswalk['verified'] is not True or crosswalk['source_vintage'] != prior['geography']['vintage']
                or crosswalk['target_vintage'] != target['geography']['vintage']
                or not _hash(crosswalk['sha256']) or not _hash(crosswalk['reaggregated_returns_sha256'])
                or crosswalk['method'] != 'exact_reaggregation'):
            raise ValueError('crosswalk must evidence exact reaggregation; assignment table alone insufficient')


def predict(features: dict) -> dict:
    """S0 = prior Democratic-minus-Republican margin + frozen shifts, clamped ±100.

    This callable receives only allowlisted features. Hyperparameters are never
    fit using held-out outcomes. Nonzero shifts are explicitly configured inputs.
    """
    _exact(features, FEATURE_FIELDS, 'features')
    if not isinstance(features['race_id'], str) or features['office'] not in {'HOUSE', 'SENATE'}:
        raise ValueError('invalid race ID/office')
    for key in ('prior_margin_pp', 'national_shift_pp', 'incumbency_adjustment_pp'):
        if not _number(features[key]) or abs(features[key]) > 100:
            raise ValueError(f'invalid {key}')
    if date.fromisoformat(features['feature_as_of']) > date.fromisoformat(features['cutoff']):
        raise ValueError('post-cutoff feature')
    if not isinstance(features['source_hashes'], list) or not features['source_hashes'] or not all(_hash(h) for h in features['source_hashes']):
        raise ValueError('feature source hashes missing')
    margin = max(-100.0, min(100.0, sum(features[k] for k in ('prior_margin_pp', 'national_shift_pp', 'incumbency_adjustment_pp'))))
    return {'race_id': features['race_id'], 'office': features['office'], 'predicted_margin_pp': margin}


def freeze_predictions(features: list[dict], *, dataset_kind: str, config: dict) -> dict:
    if dataset_kind != 'DEMO':
        raise ValueError('REAL forecast execution blocked until verified manifest/history/aggregation gates are wired; DEMO only')
    if len({f['race_id'] for f in features}) != len(features) or not features:
        raise ValueError('empty or duplicate feature races')
    # Validate before spawning; only allowlisted feature objects cross stdin.
    for item in features:
        predict(item)
    from .isolation import worker_environment
    with tempfile.TemporaryDirectory(prefix='civiclab-predictor-') as isolated:
        worker = subprocess.run([sys.executable, '-m', 'civiclab.e01.worker'],
                                input=json.dumps(features, allow_nan=False), text=True,
                                capture_output=True, check=True, timeout=30,
                                cwd=isolated, env=worker_environment())
    predictions = sorted(json.loads(worker.stdout), key=lambda p: p['race_id'])
    payload = {'status': 'RETROSPECTIVE', 'dataset_kind': dataset_kind, 'method': 'S0',
               'config': config, 'features_sha256': canonical_hash(features), 'predictions': predictions}
    return {**payload, 'freeze_sha256': canonical_hash(payload)}


def evaluate(frozen: dict, outcomes: list[dict], *, outcome_source_sha256: str) -> dict:
    """Outcomes accepted only after validating a frozen prediction artifact.

    Hashes establish byte consistency, not independent temporal sealing. Race
    coverage must match exactly. Uncertainty is descriptive, no IID race claim.
    """
    payload = {k: v for k, v in frozen.items() if k != 'freeze_sha256'}
    if frozen.get('freeze_sha256') != canonical_hash(payload):
        raise ValueError('prediction freeze hash mismatch')
    if not _hash(outcome_source_sha256):
        raise ValueError('outcome source hash required')
    if not outcomes or len({o['race_id'] for o in outcomes}) != len(outcomes):
        raise ValueError('empty or duplicate outcomes')
    actual = {}
    for o in outcomes:
        _exact(o, {'race_id', 'office', 'observed_margin_pp'}, 'outcome')
        if not _number(o['observed_margin_pp']) or abs(o['observed_margin_pp']) > 100:
            raise ValueError('invalid observed margin')
        actual[o['race_id']] = o
    if set(actual) != {p['race_id'] for p in frozen['predictions']}:
        raise ValueError('held-out evaluation requires same exact race set')
    rows = []
    for p in frozen['predictions']:
        o = actual[p['race_id']]
        if o['office'] != p['office']:
            raise ValueError('outcome office mismatch')
        error = p['predicted_margin_pp'] - o['observed_margin_pp']
        rows.append({**p, **o, 'signed_error_pp': error, 'absolute_error_pp': abs(error)})
    by_office = {}
    for office in sorted({r['office'] for r in rows}):
        errors = [r['absolute_error_pp'] for r in rows if r['office'] == office]
        by_office[office] = {'n': len(errors), 'macro_mae_pp': sum(errors) / len(errors),
                             'min_absolute_error_pp': min(errors), 'max_absolute_error_pp': max(errors)}
    return {'dataset_kind': frozen['dataset_kind'], 'status': 'RETROSPECTIVE',
            'freeze_sha256': frozen['freeze_sha256'], 'outcome_source_sha256': outcome_source_sha256,
            'outcomes_sha256': canonical_hash(outcomes), 'rows': rows, 'by_office': by_office,
            'uncertainty': 'Descriptive range only; small, correlated races do not support an IID confidence interval.',
            'provenance_limit': 'Local hashes are not independent timestamps or model-contamination guarantees.'}


def compare(simple: dict, advanced: dict, *, simple_conditions: dict, advanced_conditions: dict) -> dict:
    condition_fields = {'race_ids', 'historical_cutoff', 'selection_rule', 'feature_access', 'compute_policy'}
    _exact(simple_conditions, condition_fields, 'comparison conditions')
    _exact(advanced_conditions, condition_fields, 'comparison conditions')
    if any(not simple_conditions[k] for k in condition_fields) or any(not advanced_conditions[k] for k in condition_fields):
        raise ValueError('empty comparison conditions')
    if simple_conditions != advanced_conditions:
        raise ValueError('matched cutoff, race set, features, compute policy and selection required')
    if simple['dataset_kind'] != advanced['dataset_kind'] or simple['outcomes_sha256'] != advanced['outcomes_sha256']:
        raise ValueError('matched outcome source and dataset kind required')
    a = {r['race_id']: r for r in simple['rows']}
    b = {r['race_id']: r for r in advanced['rows']}
    if set(a) != set(b) or sorted(simple_conditions['race_ids']) != sorted(a):
        raise ValueError('same exact race set required in rows and comparison conditions')
    return {'paired_differences': [{'race_id': k, 'advanced_minus_simple_absolute_error_pp':
             b[k]['absolute_error_pp'] - a[k]['absolute_error_pp']} for k in sorted(a)],
            'interpretation': 'Negative favors advanced on these races only; complexity is not earned by appearance.'}


def aggregate_race(rows: Iterable[dict], race: dict, *, accepted_modes: set[str],
                   party_line_map: dict[str, str], unit_fields: tuple[str, ...],
                   one_vote_policy: str = 'review_required') -> dict:
    """Strict selected-race aggregation. Caller explicitly resolves mode/party policy.

    Mixed TOTAL and component modes per unit/candidate/party line are rejected.
    One race/date/stage only; no sentinel/redacted/imputed counts. A declared
    party-line map links fusion lines to the verified ballot candidate ID.
    """
    validate_race(race)
    if not accepted_modes or not unit_fields:
        raise ValueError('explicit modes and geographic unit fields required')
    if one_vote_policy not in {'review_required', 'documented_real_count', 'sentinel'}:
        raise ValueError('invalid one-vote policy')
    candidates = {c['candidate_id']: c for c in race['candidates']}
    groups = defaultdict(set)
    seen = set()
    totals = Counter()
    excluded = 0
    selected = 0
    for row in rows:
        if (int(row['year']) != race['year'] or row['state_po'] != race['state']
                or row['office'].replace('US ', '') != race['office']):
            raise ValueError('row outside selected race')
        district = row.get('district', 'STATEWIDE')
        if district != race['district']:
            raise ValueError('district mismatch: normalize only using verified mapping')
        if row['stage'].upper() != 'GEN' or row['date'] != race['election_date'] or row['special'].upper() != 'FALSE':
            raise ValueError('runoff/special/date mismatch; filter explicitly upstream')
        line = f"{row['candidate']}|{row['party_detailed']}"
        if line not in party_line_map or party_line_map[line] not in candidates:
            raise ValueError('unresolved candidate/fusion party line')
        candidate_id = party_line_map[line]
        unit = tuple(row[k] for k in unit_fields)
        if any(not v for v in unit):
            raise ValueError('missing geographic unit')
        mode = row['mode'].upper()
        key = (*unit, candidate_id, row['party_detailed'])
        groups[key].add(mode)
        if 'TOTAL' in groups[key] and len(groups[key]) > 1:
            raise ValueError('TOTAL/component overlap could double count')
        identity = (*key, mode)
        if identity in seen:
            raise ValueError('duplicate unit/candidate/party/mode row')
        seen.add(identity)
        raw = row.get('votes', row.get('candidatevotes', ''))
        try:
            votes = float(raw)
        except (ValueError, TypeError):
            raise ValueError('redacted or missing votes') from None
        if not math.isfinite(votes) or votes < 0 or not votes.is_integer():
            raise ValueError('invalid vote count')
        if votes == 1 and one_vote_policy != 'documented_real_count':
            raise ValueError('one-vote row requires documented real count vs sentinel review')
        if mode not in accepted_modes:
            raise ValueError('unapproved mode; refusing partial-mode aggregate')
        selected += 1
        party = candidates[candidate_id]['party']
        if party == 'OTHER':
            excluded += int(votes)
        else:
            totals[party] += int(votes)
    if not selected or any(totals[p] <= 0 for p in ('DEMOCRAT', 'REPUBLICAN')):
        raise ValueError('empty or uncontested two-party race')
    denominator = totals['DEMOCRAT'] + totals['REPUBLICAN']
    return {'race_id': race['race_id'], 'office': race['office'],
            'democratic_votes': totals['DEMOCRAT'], 'republican_votes': totals['REPUBLICAN'],
            'excluded_other_votes': excluded, 'two_party_denominator': denominator,
            'observed_margin_pp': 100 * (totals['DEMOCRAT'] - totals['REPUBLICAN']) / denominator,
            'accepted_modes': sorted(accepted_modes), 'row_count': selected}


def audit_returns(path: Path) -> dict:
    """Structural readiness audit only; never silently aggregate election outcomes."""
    path = Path(path)
    counts = Counter()
    states, modes, years, stages = Counter(), Counter(), Counter(), Counter()
    state_modes = defaultdict(set)
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        required = {'year', 'state_po', 'office', 'candidate', 'party_detailed', 'mode', 'stage', 'special', 'date'}
        if not required <= set(reader.fieldnames or ()):
            raise ValueError('returns schema missing required columns')
        for row in reader:
            counts['rows'] += 1
            states[row['state_po']] += 1
            modes[row['mode']] += 1
            years[row['year']] += 1
            stages[row['stage']] += 1
            state_modes[row['state_po']].add(row['mode'].upper())
            if row['special'].upper() != 'FALSE':
                counts['special_rows'] += 1
            raw = row.get('votes', row.get('candidatevotes', ''))
            try:
                n = float(raw)
                if not math.isfinite(n) or n < 0 or not n.is_integer():
                    counts['invalid_numeric_votes'] += 1
                if n == 1:
                    counts['one_vote_rows_require_sentinel_review'] += 1
            except (ValueError, TypeError):
                counts['redacted_or_missing_votes'] += 1
    return {'path': str(path), 'sha256': sha256_file(path), 'counts': dict(counts),
            'states': dict(sorted(states.items())), 'years': dict(years), 'stages': dict(stages),
            'modes': dict(modes), 'states_with_TOTAL_and_components': sorted(s for s, m in state_modes.items() if 'TOTAL' in m and len(m) > 1),
            'warning': 'Mixed modes at state level flag review, not proof of unit-level duplication. No vote totals or predictions produced.'}


def run_audit(root: Path, output: Path) -> Path:
    paths = [Path(root) / 'data/raw/medsl_2022_senate_county/extracted/senate_2022.csv',
             Path(root) / 'data/raw/medsl_2024_senate_precinct/extracted/SENATE_precinct_general.csv',
             Path(root) / 'data/raw/medsl_2024_house_precinct/extracted/HOUSE_precinct_general.csv']
    config = {'protocol': 'E01_RETROSPECTIVE_v1', 'action': 'real_input_readiness_audit'}
    with RunStore(output, 'E01', config, kind='RETROSPECTIVE') as run:
        audits, missing = [], []
        for path in paths:
            if path.exists():
                audits.append(audit_returns(path))
            else:
                missing.append(str(path))
        run.write('returns_audit.json', {'audits': audits, 'missing': missing})
        summary = {'status': 'BLOCKED_REAL_BASELINE', 'cost_usd': 0, 'files_audited': len(audits),
                   'blockers': ['2024 House target lacks 2022 House returns on validated matching geography.',
                                '2022 and 2024 regular Senate returns are different seat classes; need 2018 for a 2024 same-seat lag.',
                                'Official candidate manifests, exact map vintage verification and state-specific aggregation policies remain missing.'],
                   'claims': 'Structural real-data audit only; no forecast or election performance result.'}
        run.write('readiness.json', summary)
        run.finish(summary)
        return run.path


def run_demo(output: Path, seed: int = 20261103) -> Path:
    """Clearly fictional fixture exercises freeze/evaluate/replay, not research."""
    config = {'protocol': 'E01_RETROSPECTIVE_v1', 'seed': seed, 'dataset_kind': 'DEMO',
              'baseline': 'S0 prior margin, zero shifts', 'selection': 'two explicitly fictional races'}
    features = [{'race_id': f'DEMO-{office}', 'office': office, 'prior_margin_pp': prior,
                 'national_shift_pp': 0, 'incumbency_adjustment_pp': 0,
                 'feature_as_of': '2022-12-31', 'cutoff': '2024-11-04',
                 'source_hashes': [canonical_hash({'fixture': 'invented engineering data'})]}
                for office, prior in [('HOUSE', 4.0), ('SENATE', -3.0)]]
    outcomes = [{'race_id': 'DEMO-HOUSE', 'office': 'HOUSE', 'observed_margin_pp': 2.0},
                {'race_id': 'DEMO-SENATE', 'office': 'SENATE', 'observed_margin_pp': -4.0}]
    with RunStore(output, 'E01', config, kind='MOCK') as run:
        run.write('features.json', features)
        frozen = freeze_predictions(features, dataset_kind='DEMO', config=config)
        run.write('predictions.frozen.json', frozen)
        run.event('prediction_freeze', freeze_sha256=frozen['freeze_sha256'])
        result = evaluate(frozen, outcomes, outcome_source_sha256=canonical_hash(outcomes))
        run.write('evaluation.json', result)
        # A predeclared +1pp national-shift counterfactual, on the same two fixtures.
        shifted = [{**f, 'national_shift_pp': 1} for f in features]
        counterfactual = freeze_predictions(shifted, dataset_kind='DEMO', config={**config, 'shift_pp': 1})
        run.write('counterfactual.predictions.json', counterfactual)
        counter_eval = evaluate(counterfactual, outcomes, outcome_source_sha256=canonical_hash(outcomes))
        run.write('counterfactual.evaluation.json', counter_eval)
        conditions = {'race_ids': [f['race_id'] for f in features], 'historical_cutoff': '2024-11-04',
                      'selection_rule': 'two fixed invented fixtures', 'feature_access': 'same allowlisted historical margin; predeclared shift is the intervention',
                      'compute_policy': 'same deterministic S0 evaluation; no paid inference'}
        run.write('paired_comparison.json', compare(result, counter_eval, simple_conditions=conditions, advanced_conditions=conditions))
        summary = {'status': 'DEMO_COMPLETE', 'dataset_kind': 'DEMO', 'cost_usd': 0,
                   'claims': 'Invented toy values test engineering only; not electoral forecasting evidence.',
                   'prediction_sha256': frozen['freeze_sha256'], 'by_office': result['by_office']}
        run.finish(summary)
        return run.path
