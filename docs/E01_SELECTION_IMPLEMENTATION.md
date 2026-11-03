# E01 fixture-only selector implementation

Status: worker implementation and local execution; independent code audit pending. Methods approval `reports/INDEPENDENT_AUDIT_E01_SELECTION_METHODS.json` authorizes fixture implementation only and pins the unchanged proposal hash. No real 2026 frame is selected. Cook collection/reuse/as-of blockers and all original E01 scientific gates remain in force.

## Admission and versioned contracts

`configs/e01_selection_v1.json` mirrors the approved algorithm ID, seed, UTC cutoff, quotas, frozen four-region state mapping and solver controls. `configs/e01_selection_schema_v1.json` describes the complete authored-fixture frame; `configs/e01_selection_source_schema_v1.json` describes its synthetic source receipts. Both forbid unknown fields. `validate_fixture` additionally checks cross-field identity, unique and complete expected IDs, source references, cutoff date order, UTC timestamps, structural-exclusion codes and resolved fixture amendment/as-of metadata. Missing evidence is pending/blocked, never a convenient exclusion. Outcome fields and input-availability exclusions are not accepted.

Only `DEMO_SELECTION_FIXTURE`, canonical `DEMO-2026-*` IDs, `fixture://DEMO/` sources and authored fixture reuse metadata are admitted. A REAL frame is refused regardless of supplied approval flags. These receipts simulate review states for engineering; they do not authenticate source bytes, final-ballot status, candidate-party mappings or actual rights. There is deliberately no real-source acceptance switch. Private optimization helpers are trusted implementation functions, not a security boundary against an operator altering Python or relabeling data. No external content ingestion/network/inference exists in this module.

## Exact ordered objectives

The model has one binary selection variable per eligible contest, integer absolute-deviation auxiliaries, and binary region/state coverage indicators with both implications enforced. It fixes cardinality and nonempty band coverage, then minimizes quota-cell L1 deviation, minimizes D/R imbalance, maximizes regions, maximizes states, in that order. Every achieved objective is constrained to equality before the next. Twelve quota cells include OTHER with nominal zero; OTHER is never split between D/R. House shortages remain explicitly incomplete; absent bands are preserved in receipts. Senate cardinality is capped at eight independently of House.

Rows are ordered by the exact reviewed SHA-256 input and canonical-ID collision tie-break. At fixed cardinality the lexicographically smallest sorted selected-rank list is equivalent to lexicographically maximizing the binary inclusion vector. The implementation optimizes ten bits at a time, with integer coefficients at most 512, then fixes each bit before the next chunk. Thus an earlier bit outweighs every later bit in its chunk and earlier chunks cannot change. It avoids huge powers across the entire frame and an approximate weighted sum across scientific objectives.

Deep House requires one per band, then minimizes `abs(n_D-2)+abs(n_R-2)`, maximizes regions/states, then fixes hash ties. Deep Senate requires competitive and less-competitive groups when available, then the reviewed target-party/region/rank objectives. The absent-group fallback is explicit; fewer than two Senate cases or a missing House band blocks six-case completion. No missing-input or post-error replacement rule exists.

## Solver evidence and refusal

The optional extra is `selection = ["scipy==1.16.3"]`; core imports remain standard library until optimization. PyPI's [exact release metadata](https://pypi.org/pypi/scipy/1.16.3/json) identifies supported Python versions and license. The [official v1.16.3 MILP implementation/documentation](https://raw.githubusercontent.com/scipy/scipy/v1.16.3/scipy/optimize/_milp.py) defines HiGHS integration, integer constraints, status, limit and gap fields. Actual local serving solver is SciPy 1.16.3 / bundled HiGHS 1.8.0, recorded in each fixture result. No model serving provider or paid call is involved.

Each solve requests relative MIP gap zero, has at most ten seconds, and shares a 60-second default total admission deadline (caller may set a positive finite bound up to 120). A late result is refused. Acceptance requires success/status 0, zero reported gap, finite objective and dual bound agreeing with an exactly recomputed integer objective within 1e-6, integer variables within 1e-6, then exact integer bounds and every constraint. Nonoptimal, infeasible, unknown, fractional, nonfinite, timed-out and contradictory results are rejected; no heuristic result is substituted. Bounds/objectives here have small integer coefficients. These are numerical MILP optimality receipts plus independent integer feasibility checks, not formal rational proof certificates or a guarantee for arbitrary future data sizes. Aggregate objective vectors are recomputed directly from chosen rows and checked against stage optima.

All stage objective values, bounds, zero gaps and node counts are preserved. The selection hash covers normalized frame identity and selected broad/deep IDs. Node counts and runtime may vary by platform; they are diagnostic receipts, not part of the deterministic identity claim. An exact pinned SciPy version is required; changes need validation rather than silent fallback.

## APIs and recorded execution

```sh
python -m pip install -e '.[selection]'
PYTHONPATH=src python -m unittest tests.test_e01_selection tests.test_e01 tests.test_isolation -v
PYTHONPATH=src python -m civiclab.e01.selection data/processed/e01/selection_435H_33S.fixture.json --root "$PWD" --max-seconds 60
```

The ignored full-size fixture is generated reproducibly by `tests.test_e01_selection.fixture(435,33)`; it is not committed source data. `select_fixture(frame, max_seconds=60)` returns the in-memory result. `run_fixture(root, frame, max_seconds=60)` records accepted fixture input, all solver receipts and a final summary through shared immutable RunStore with kind MOCK and visibly DEMO dataset labels. Admitted fixture configurations that fail solving preserve their input/config, streamed prior stage receipts, failure artifact and explicit FAILED summary sealed with checksums; they do not acquire a success summary. The exception is re-raised after failure finalization. Invalid/external frames are rejected before storing their contents. CLI prints the run directory only after successful finalization. Parent owns any shared CLI hook.

`comparison_gate` checks fixture full-set method coverage, status and cutoff; it refuses failed/missing/replacement cases and a missing comparator. It does not calculate scores, establish outcome version equality, enforce provider compute allocation or replace the existing E01 evaluator/comparison conditions. Those broader scientific gates remain separate and blocked for actual 2026 execution.

## Verification and limits

Fifteen selector tests plus existing E01/isolation checks passed: 40 total. An independent algorithm in the test file enumerates all subsets on 27-House/12-Senate fixtures, six randomized Senate/shortage cases and a repeated-state House fixture; it computes quotas/objectives/ranks directly rather than calling production model/objective helpers. This is an independently verifiable oracle written by the implementing worker, not an independent auditor's certification. Tests include OTHER, absent bands, deep fallback, row order, hash collision ordering, malformed dates/identities, unknown outcomes, missing evidence, refused REAL inputs, nonoptimal/NaN/fractional solver receipts, deadlines and failed-run logging. Region constants are shared with the oracle; policy/config and source-region mapping still require independent review.

A synthetic 435-House/33-Senate computational fixture completes with 24/8 broad and 4/2 deep IDs, 65 optimal stages and zero reported gaps. Its district distribution and source receipts are invented engineering inputs, not an official or representative election frame. Two recorded runs reproduce selection identity; aggregate receipt is `reports/E01_SELECTION_EVIDENCE.json`. First recorded execution including logging was approximately 0.32 seconds locally; this is not a performance guarantee. A smaller 27-case exhaustive fixture alone is not presented as full-size scalability evidence.

No official ballots, copyrighted ratings, 2026 returns, forecasting scores, inference spend or real race selections were generated by this task. Independent auditor review of the code, numerical assumptions, exhaustive oracle and full-size receipt is required before certifying this implementation milestone. Actual cost: $0.
