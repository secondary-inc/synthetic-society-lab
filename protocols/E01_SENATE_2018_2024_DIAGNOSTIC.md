# E01 bounded historical diagnostic

This amendment supports the independent E01 statistical baseline. It does not replace `E01_RETROSPECTIVE.md`, the original 2026 race sample, agent comparisons, sealed holdout, or prospective evidence requirements. Status: implemented and locally executed; independent audit pending. No confirmatory preregistration claim.

## Frozen design and acceptance criteria

`configs/e01_senate2018_2024.json` fixes the 33 Class-I Senate constituencies, dates, eligibility, two arithmetic methods and zero adjustments. The six-year seat cycle is documented in the official FEC 2018 publication, printed page 34. The Senate Class-I page confirms terms beginning in 2025. Statewide seat identity is used; this is not a House boundary or precinct interpolation validation.

Eligibility requires one named Democratic and Republican candidate in both regular general elections. California has no Republican in the 2018 D-D contest; Nebraska has no Democrat in 2024; Vermont has no Democrat. These structural exclusions leave 30 states. Maine stays included even though an independent wins: the target is explicitly conditional D-R two-party margin, not winner identity. Party affiliates DFL/NPL count as Democratic, fusion lines for the same candidate are summed, and nonmajor votes are never reallocated.

Acceptance requires all six pinned source hashes, exact candidate/party checks against government Senate sections, 120 major-candidate count reconciliations, recorded exclusions, no unresolved count mismatch, isolated predictor inputs, two frozen prediction artifacts before evaluation, identical comparison conditions, exact replay hashes, and regression tests. Independent review must assess source interpretation and limitations before milestone certification.

## Source adjudication before scoring

MEDSL CSV files provide machine-readable discovery, not final authority. Validation found nine count discrepancies before any performance calculation: 2018 OH (both parties), PA (Democrat), WV (both), and 2024 ME/NY (both). The configuration records both CSV and official values and explicitly replaces those counts with the pinned FEC/House Clerk values. No state was excluded because of a discrepancy. An unlisted mismatch blocks the entire evaluation. This is a documented protocol amendment after inspection of target data, before scoring; it is not an untouched historical holdout.

The 2018 FEC table misspells Tony Campbell as Cambell. A single explicit alias is corroborated by the pinned public Maryland State Archives page, which lists Tony Campbell under Republican and 697,017 votes. No fuzzy name correction runs automatically. Surname matches must be unique within a state's Senate section, with matching official party and exact authoritative count; full-name/nickname variations remain visible in the crosscheck receipt.

## Methods, isolation and evaluation

S0 predicts the 2018 D-R margin with zero national/incumbency adjustments. S_ZERO predicts zero for every eligible state. Both have the same available historical inputs and state sample; S_ZERO ignores the prior by definition. No fitted coefficients, target-based tuning, external models or paid inference run. Prior-feature availability uses November 1, 2019 conservatively after FEC's October 2019 cover month; this is not a verified exact publication day.

Each child process receives only allowlisted feature JSON, a stripped environment and an empty working directory. Its post-import audit hook denies file, network and subprocess access. This controls accidental I/O by trusted code, not malicious Python under an OS security sandbox. The parent already reconstructed outcomes to establish eligibility and validate sources. Prediction hashing is computational separation, not proof that researchers never saw outcomes or that predictions existed in 2024. Generic REAL freezing remains blocked; only the scoped historical command exists.

The primary descriptive metric is macro MAE in percentage points, with paired S0-minus-S_ZERO absolute errors on the same 30 states. Leave-one-state-out paired-mean range is descriptive sensitivity, not a sampling confidence interval or forecast uncertainty. No causal or general superiority claim follows from this finite, retrospectively chosen eligible cohort.

## Remaining original E01 gates

The 2026 candidate/race manifest, geographic checks for House seats, valid historical predictors for that sample, untouched holdout, agent variants and matched/equal-compute comparisons remain incomplete. There is no independent pre-results 2026 submission. No prospective performance, human persuasion or demographic realism claim is supported.
