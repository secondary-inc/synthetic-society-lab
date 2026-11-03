# E01 retrospective forecasting protocol v1

Status: implementation protocol, RETROSPECTIVE only. No prospective forecast is established. Source of truth: `CODEX_MASTER_EXECUTION.md` and the November 3 progress audit. DEMO values are invented engineering fixtures, never research results.

## Frozen estimand and S0

Target: Democratic minus Republican two-party vote margin, percentage points, `(D - R)/(D + R) * 100`. Ballots for other candidates are recorded as excluded, not redistributed. Fusion lines count toward the verified candidate. Initially require exactly one verified Democrat and Republican; exclude uncontested, special and runoff contests until separate protocols exist.

S0 prediction: prior same-seat margin + predeclared national shift + predeclared incumbency adjustment, clamped to [-100, 100]. Default adjustments are zero. This transparent persistence baseline does not fit parameters on evaluation outcomes. It is not polling, turnout or a calibrated probability model. Senate uses the same seat class six years earlier, House the same mapped district two years earlier. A Senate outcome two years earlier cannot silently substitute for a different class. House map changes require exact reaggregation evidence; a CD120 assignment table alone is insufficient.

Freeze race selection, input cutoff, shifts, aggregation policy and exclusion rules before evaluating historical outcomes. All runs remain retrospective even when historical cutoffs are used. Survey/LLM content is not used by S0. Neither local freeze hashes nor process separation establish independent timing or absence of model pretraining contamination.

## Manifest and evidence gates

Every real race requires its canonical ID, office, state, district or Senate class, election date, historical cutoff, regular-general status, official candidate ballot evidence hashes, and verified map vintage/source/hash. Candidate finance registration is not ballot verification. Prior/target constituency must match, with exact prior-data reaggregation if maps changed. Source byte hashes identify inputs; operators must verify their authenticity and provenance.

Before aggregation, explicitly select one race/date/stage and supply the candidate-plus-party-line mapping, accepted vote modes and geographic unit fields. Unresolved fusion parties, repeated unit/candidate/line/mode rows, TOTAL-plus-component overlap, missing geography, redactions, negative/noninteger/nonfinite votes and unapproved modes fail closed. One-vote rows require source-specific review because the 2022 county codebook mentions uncontested sentinels while real precinct counts can equal one. No imputation. The structural readiness audit deliberately does not produce vote totals.

## Held-out evaluation

A separate prediction child process receives only feature JSON on stdin. Run config and outcomes remain in the parent. Prediction accepts an exact allowlist of features, rejecting outcome/live-return fields and post-cutoff feature dates. `predictions.frozen.json` contains a deterministic hash over the prediction payload before outcome evaluation. Evaluator recomputes this hash, checks the exact same held-out race set and office, and records the outcome source hash and payload hash separately. This is software data-flow checking; it is not a filesystem/network security sandbox. Public function calls alone cannot prove outcomes were unknown to an operator.

Primary score: macro mean absolute margin error within each office. Preserve race-level signed and absolute errors, count, and descriptive error range. Do not pool House and Senate silently. No winner accuracy surrogate or universal superiority claim. Small correlated samples do not justify an IID confidence interval. Real runs need a predeclared race sample and source uncertainty accounting before inferential claims.

For advanced-vs-simple comparisons, use the exact same race IDs, outcome data, historical cutoff, selection, feature access and compute policy. Report paired race-level error differences. Comparison helper rejects mismatched condition records and outcome payloads; condition metadata is an attestation, not independent enforcement of compute spent.

## Acceptance gates

1. **Foundation dependency:** install/import/logging/integrity/cost tests pass before E01 integration runs.
2. **E01 unit and DEMO gate:** independently check formula and sign; freeze tamper detection; illegal feature rejection; exact holdout coverage; ballot/map/class guards; mode/fusion/redaction/runoff/sentinel safeguards; deterministic DEMO replay. No paid calls.
3. **Real readiness gate:** register three source hashes and structural counts, missing files and aggregation hazards; emit explicit BLOCKED when candidate/geography/history evidence is absent.
4. **Real S0 gate (blocked):** validated race selection, prior same-seat history, verified candidate/map manifest, state-specific aggregation adjudication, frozen historical feature snapshot, target outcome source. A real benchmark must pass all gates before any performance claim.
5. **Earned complexity (blocked):** S1 polling, S2 demographics, agents/news/social/assistants/swarms require their additional protocol/evidence gates and matched S0 comparison. Toy comparison cannot earn a real research gate.

## Current missing inputs

2024 House evaluation lacks 2022 House returns on comparable validated geography. 2024 regular Senate evaluation needs 2018 same-seat returns; 2022 and 2024 are different classes. Existing 2026 candidate/finance files are not verified final ballots; no independently timestamped prospective archive is demonstrated. Cook PDFs are clipped and too late for historical 2024 selection. Real runs therefore stop at readiness audit.
