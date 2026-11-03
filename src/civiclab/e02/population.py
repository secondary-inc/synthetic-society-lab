"""Weighted joint-cell calibration, with explicit universe and support limitations."""
from collections import Counter, defaultdict
from pathlib import Path
import csv
import json
import math
import random
from ..common import canonical_hash, sha256_file, atomic_json

REGION_FIPS = {
    "1": "09 23 25 33 44 50 34 36 42".split(),
    "2": "18 17 26 39 55 19 20 27 29 31 38 46".split(),
    "3": "10 11 12 13 24 37 45 51 54 01 21 28 47 05 22 40 48".split(),
    "4": "04 08 16 30 32 35 49 56 02 06 15 41 53".split(),
}
FIPS_REGION = {state: region for region, states in REGION_FIPS.items() for state in states}


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def acs_table(path):
    if 'ACSDT5Y2024.' not in Path(path).name:
        raise ValueError('matching 2024 five-year ACS product required')
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        labels = next(reader)
        if labels['GEO_ID'] != 'Geography':
            raise ValueError('expected descriptive-label row')
        rows = list(reader)
    relevant = [r for r in rows if r['GEO_ID'][-2:] in FIPS_REGION]
    if len(relevant) != 51 or len({r['GEO_ID'] for r in relevant}) != 51:
        raise ValueError('all 50 states and DC required')
    return relevant


def acs_targets(age_path, education_path):
    targets = {"region_age": defaultdict(float), "region_education": defaultdict(float)}
    def value(row, table, index):
        result = number(row[f'{table}_{index:03d}E'])
        if result is None or result < 0:
            raise ValueError('missing/negative ACS estimate')
        return result
    for row in acs_table(age_path):
        region = FIPS_REGION[row['GEO_ID'][-2:]]
        groups = {'25-44': list(range(11, 15)), '45-64': list(range(15, 20)), '65+': list(range(20, 26))}
        for category, indices in groups.items():
            targets['region_age'][region + ':' + category] += sum(value(row, 'B01001', i) + value(row, 'B01001', i + 24) for i in indices)
    for row in acs_table(education_path):
        region = FIPS_REGION[row['GEO_ID'][-2:]]
        groups = {'HS_OR_LESS': range(2, 19), 'SOME_COLLEGE': range(19, 22), 'BA_PLUS': range(22, 26)}
        for category, indices in groups.items():
            targets['region_education'][region + ':' + category] += sum(value(row, 'B15003', i) for i in indices)
    # Both 25+ resident universes should agree up to published integer estimates.
    a, b = sum(targets['region_age'].values()), sum(targets['region_education'].values())
    if abs(a - b) > max(100, a * 0.001):
        raise ValueError('ACS age/education universe totals disagree')
    return {dimension: {k: v / sum(margins.values()) for k, v in margins.items()} for dimension, margins in targets.items()}


def rake(cells, targets, tolerance=1e-8, max_iterations=500):
    cells = [dict(cell) for cell in cells]
    total = sum(c['weight'] for c in cells)
    if not cells or total <= 0 or any(not math.isfinite(c['weight']) or c['weight'] <= 0 for c in cells):
        raise ValueError('empty population support')
    for c in cells:
        c['weight'] /= total
    for dimension, wanted in targets.items():
        supported = {c[dimension] for c in cells}
        if supported != set(wanted) or any(not math.isfinite(t) or t <= 0 for t in wanted.values()) or abs(sum(wanted.values()) - 1) > 1e-8:
            raise ValueError('structural zero, extra category, or invalid target: ' + dimension + ' missing=' + str(sorted(set(wanted) - supported)))
    for iteration in range(max_iterations):
        for dimension, wanted in targets.items():
            observed = defaultdict(float)
            for c in cells:
                observed[c[dimension]] += c['weight']
            for c in cells:
                c['weight'] *= wanted[c[dimension]] / observed[c[dimension]]
        errors = []
        for dimension, wanted in targets.items():
            observed = defaultdict(float)
            for c in cells:
                observed[c[dimension]] += c['weight']
            errors.extend(abs(observed[k] - wanted[k]) for k in wanted)
        residual = max(errors)
        if residual < tolerance:
            return cells, {"iterations": iteration + 1, "max_absolute_margin_residual": residual, "converged": True}
    raise ValueError('calibration did not converge; cannot silently continue')


def fit_population(root, seed=20261103):
    root = Path(root)
    mapping_path = root / 'configs/e02_population_mapping.json'
    mapping = json.loads(mapping_path.read_text())
    anes = root / 'data/raw/anes_2024/extracted/anes_timeseries_2024_csv_20260519.csv'
    acs = root / 'data/raw/census/acs2024/extracted'
    age, education = acs / 'ACSDT5Y2024.B01001-Data.csv', acs / 'ACSDT5Y2024.B15003-Data.csv'
    source_paths = [anes, age, education, mapping_path,
                    acs / 'ACSDT5Y2024.B03002-Data.csv', acs / 'ACSDT5Y2024.B19001-Data.csv',
                    root / 'data/raw/anes_2024/extracted/anes_timeseries_2024_userguidecodebook_20260519.pdf']
    # Validate actual source bytes against registered inventory before fitting.
    inventory = json.loads((root / 'configs/SOURCE_INVENTORY.json').read_text())
    expected = {}
    for item in inventory['archives']:
        local = item.get('local_archive')
        if not local:
            continue
        for member in item.get('members', []):
            path = Path(local).parent / 'extracted' / member['name'] if local.endswith('.zip') else Path(local)
            expected[str(path)] = member['sha256']
    for path in source_paths:
        if path == mapping_path:
            continue
        if sha256_file(path) != expected.get(str(path.relative_to(root))):
            raise ValueError('population input not registered or changed')
    targets = acs_targets(age, education)
    grouped = defaultdict(lambda: {'weight': 0., 'squared_weight': 0., 'count': 0})
    exclusions = Counter(); heldout = []; cluster_count = set()
    weighted_exclusions = Counter()
    with anes.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if any(mapping[k] not in reader.fieldnames for k in ('weight', 'age', 'education', 'race', 'income', 'party', 'region', 'psu', 'stratum')):
            raise ValueError('ANES variable mapping not found')
        for row in reader:
            sample = number(row[mapping['sample']]); weight = number(row[mapping['weight']])
            if sample not in mapping['sample_values'] or weight is None or weight <= 0:
                exclusions['outside_fresh_weighted_sample'] += 1; continue
            age_value, edu = number(row[mapping['age']]), number(row[mapping['education']])
            region_value = number(row[mapping['region']])
            if age_value is None or not 25 <= age_value <= 80 or edu not in range(1, 6) or region_value not in range(1, 5):
                exclusions['age_education_or_region_missing_outside_universe'] += 1
                weighted_exclusions['age_education_or_region_missing_outside_universe'] += weight
                continue
            region = str(int(region_value)); age_bin = '25-44' if age_value < 45 else '45-64' if age_value < 65 else '65+'
            party_value = number(row[mapping['party']])
            party = 'D' if party_value == 1 else 'R' if party_value == 2 else 'I' if party_value in (0, 3, 5) else 'UNKNOWN'
            race_value = number(row[mapping['race']]); income_value = number(row[mapping['income']])
            race = 'WHITE_NH' if race_value == 1 else 'BLACK_NH' if race_value == 2 else 'HISPANIC' if race_value == 3 else 'OTHER_NH' if race_value in (4, 5, 6) else 'UNKNOWN'
            income = 'LOW' if income_value in (1, 2) else 'MID' if income_value in (3, 4) else 'HIGH' if income_value in (5, 6) else 'UNKNOWN'
            education_bin = mapping['education_recode'][str(int(edu))]
            key = (region, age_bin, education_bin, party, race, income)
            cluster = (row[mapping['stratum']], row[mapping['psu']])
            if any(number(x) is None or number(x) < 0 for x in cluster):
                exclusions['invalid_design_cluster'] += 1
                weighted_exclusions['invalid_design_cluster'] += weight
                continue
            cluster_count.add(cluster)
            holdout = int(canonical_hash([seed, cluster])[:8], 16) % 5 == 0
            if holdout:
                heldout.append((key, weight)); continue
            grouped[key]['weight'] += weight
            grouped[key]['squared_weight'] += weight * weight
            grouped[key]['count'] += 1
    cells = []
    for key, value in sorted(grouped.items()):
        if value['count'] < 5:
            exclusions['sparse_joint_cell_below_5_records'] += value['count']
            weighted_exclusions['sparse_joint_cell_below_5_records'] += value['weight']
            continue
        region, age_bin, edu, party, race, income = key
        cells.append({**value, 'region': region, 'age_bin': age_bin, 'education': edu,
                      'party': party, 'race': race, 'income': income,
                      'region_age': region + ':' + age_bin, 'region_education': region + ':' + edu})
    initial = [c['weight'] for c in cells]
    initial_total = sum(initial)
    fitted, diagnostics = rake(cells, targets)
    sum_sq = sum(c['squared_weight'] * (c['weight'] / initial[i]) ** 2 for i, c in enumerate(fitted))
    diagnostics.update(effective_survey_sample_size=1 / sum_sq, supported_joint_cells=len(cells),
                       contributing_survey_records=sum(c['count'] for c in cells),
                       exclusions=dict(exclusions), design_clusters=len(cluster_count), heldout_records=len(heldout),
                       max_calibration_factor=max(c['weight'] / (initial[i] / initial_total) for i, c in enumerate(fitted)))
    training_weight=sum(v['weight'] for v in grouped.values())
    diagnostics['weighted_training_mass_excluded_sparse_fraction'] = weighted_exclusions['sparse_joint_cell_below_5_records']/training_weight
    diagnostics['weighted_exclusions_before_normalization'] = dict(weighted_exclusions)
    train_party = defaultdict(float)
    for cell in fitted:
        train_party[cell['party']] += cell['weight']
    test_party = defaultdict(float)
    for key, weight in heldout:
        test_party[key[3]] += weight
    test_total = sum(test_party.values())
    if not test_total:
        raise ValueError('held-out survey partition empty')
    diagnostics['heldout_party_max_absolute_share_error'] = max(abs(train_party[k] - test_party[k] / test_total) for k in set(train_party) | set(test_party))
    supported_keys={(c['region'],c['age_bin'],c['education'],c['party'],c['race'],c['income']) for c in fitted}
    diagnostics['heldout_joint_support_coverage_fraction'] = sum(w for key,w in heldout if key in supported_keys)/test_total
    diagnostics['support_interpretation'] = 'Marginal calibration can converge despite unsupported held-out joint cells and substantial removed survey mass. These diagnostics do not open a representative-population gate.'
    # Never export donor identifiers or individual thermometers; cells are coarsened aggregates.
    for c in fitted:
        c.pop('squared_weight')
    return {'kind': 'EXPLORATORY_POPULATION_FIT', 'seed': seed, 'cells': fitted, 'targets': targets,
            'diagnostics': diagnostics, 'mapping': mapping,
            'source_hashes': {str(p.relative_to(root)): sha256_file(p) for p in source_paths},
            'confirmatory_status': 'BLOCKED: citizen/resident universe mismatch, sparse support exclusions, unvalidated transport and state inference'}


def sample_profiles(fit, n=12, seed=20261103):
    if n < 4:
        raise ValueError('at least four profiles for region stratification')
    rng = random.Random(seed); profiles = []
    for region in ('1', '2', '3', '4'):
        cells = [c for c in fit['cells'] if c['region'] == region]
        count = n // 4 + (int(region) <= n % 4)
        if not cells:
            raise ValueError('region has no joint support')
        share = sum(c['weight'] for c in cells)
        for cell in rng.choices(cells, weights=[c['weight'] for c in cells], k=count):
            profiles.append({'profile_id': f'fictional-{len(profiles)+1:04d}', 'region': region,
                             **{k: cell[k] for k in ('age_bin', 'education', 'party', 'race', 'income')},
                             'design_weight': share / count, 'fictional': True,
                             'experimental_prior': 'party and demographic categories only; no supplied thermometer answers'})
    return profiles
