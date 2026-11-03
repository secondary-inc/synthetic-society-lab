# Proposed E02 citizen-25+ calibration amendment

Status: **METHODS PROPOSAL — NOT IMPLEMENTED, NOT EXTERNALLY PREREGISTERED, NO NEW FIT AUTHORIZED BY THIS DOCUMENT.** Prepared November 3, 2026. This document proposes rules for a future offline exploratory amendment. It does not alter locked v3, the original population target, acquired source manifests, frozen comparison inputs or prior runs. Independent methods review must precede implementation; a later implementation needs its own versioned configuration, hashes and independent audit. No paid execution is requested or enabled.

## Evidence and scope

The public acquisition is documented in `configs/e02_citizen_benchmark_acquisition.json` and `reports/E02_CITIZEN_BENCHMARK_ACQUISITION.json`. The exact ACSST5Y2024.S0501 ZIP SHA-256 is `7b3684807e87cc38c79fff3ae53154926448eea3575ea9a7f852fd6fc7876204`. `reports/INDEPENDENT_AUDIT_E02_CITIZEN_ACQUISITION.json` records PASS for acquisition and unit rationale only, including independent examination of the official S0501 shell (SHA-256 `13ed8f7313c156b9acf9bc608814e72925e5cb7413c8be7317eb7147360a34b7`). That finding does not approve a new fit. This proposal relies on that separately authored evidence rather than claiming a second independent review.

The [official Census nativity definition](https://www.census.gov/topics/population/foreign-born/about/faq.html) supports treating Native (C02, citizens at birth) plus Foreign-born; Naturalized citizen (C04) as a candidate resident-citizen benchmark. The [official 2024 S0501 shell](https://www2.census.gov/programs-surveys/acs/tech_docs/table_shells/2024/Shells/S0501.xlsx) distinguishes person-count totals from subgroup percentages and their denominators. The [acquired public table](https://data.census.gov/table/ACSST5Y2024.S0501?g=010XX00US$0400000) supplies estimates and 90% MOEs.

The proposed benchmark is **resident citizens aged 25+ in the 50 states and DC during the 2020–2024 ACS five-year period**, including persons represented in the ACS group-quarters universe. It is not registered voters, likely voters, all eligible adults aged18+, a November2026 census or evidence about political responses. Native includes citizenship at birth rather than merely birthplace in a state. C02 and C04 are disjoint; C03 (all foreign-born) must not also be added, because it includes C04. Noncitizen C05 is excluded from the proposed citizen totals.

ANES inclusion remains fresh combined pre-election sample types2/3, positive V240103a survey weight, valid region, age25+ and existing education recodes, with the existing PSU/stratum treatment. Its citizenship/eligibility, institutional/group-quarters coverage, interview/nonresponse mechanisms and survey period still need explicit alignment review against ACS. Matching citizenship improves one benchmark dimension; it does not resolve all transport or target-validity differences. The original nationwide, state-stratified ambition remains outstanding: region aggregation and a small regional pilot do not establish state coverage or effects. The age25+ restriction remains a limitation rather than silently becoming full adult-population completion.

## Geography and exact variable mapping

Preserve all52 acquired state-level rows in source evidence. A future fit must select exactly the50 states and DC using the existing documented Census-region FIPS partition. Exclude Puerto Rico FIPS72 explicitly from this calibration target, with its source record and exclusion reason retained. Do not drop DC, silently substitute a national row or use territories in a four-region partition that does not define them. Require exactly51 unique selected geographies, one per expected state/DC code, and no duplicates or missing rows. These state inputs are aggregated to four regions; no state-level fit or inference follows.

For each selected state s and column c in {C02,C04}, define:

- T_sc = S0501_c_001E, published all-age person total.
- N_sc = S0501_c_038E, published person total aged25+.
- p_sc,j = percentage estimate for age row j in007..012. These percentages use T_sc, not N_sc, as denominator.
- e_sc,j = percentage estimate for education row j in039..043. These percentages use N_sc, not T_sc, as denominator.

Retain each matching M variable and all original source annotations. Missing, suppressed, nonfinite, negative, out-of-domain or unexpectedly annotated required values must block conversion, with the failing state/column/variable recorded. Do not turn symbols into zero. Counts must be integer-valued, with 0<=N_sc<=T_sc; require positive denominators for the proposed normalization. A zero-count column or section requires an explicit reviewed rule rather than division by zero or silent exclusion.

Age bins are25–44=row007;45–64=008+009;65+=010+011+012. Education bins are HS_OR_LESS=039+040; SOME_COLLEGE=041 (some college or associate degree); BA_PLUS=042+043. This matches the existing ANES education recode1/2,3,4/5 respectively. It does not introduce race or household-income constraints. All six fictional profile fields remain in the joint-distribution target, including party, race and income; those fields are not made independent or dropped merely to solve calibration.

## Proposed point-target construction

Published subgroup percentages are rounded to one decimal place. Their products with totals are **approximate derived counts**, never published integer subgroup counts. Use Decimal arithmetic while parsing and constructing targets; retain full precision in saved artifacts. Do not round intermediate products to persons or overwrite source percentages.

For age group g, first compute raw approximate A_sc,g = T_sc × sum(p_sc,j for j in g)/100. Let A_sc,+ be the sum over all three age groups. Report A_sc,+−N_sc, relative discrepancy, the six percentage sum and the proposed scale factor k_age=N_sc/A_sc,+ for every state/column before normalization. The primary proposal anchors the25+ total to published N_sc and uses normalized age composition:

    age_target_sc,g = N_sc × A_sc,g / A_sc,+
                   = N_sc × sum(p_sc,j in g) / sum(p_sc,j for j=007..012).

This explicitly reconciles the rounded age composition to the independently published25+ total; it does not assert that the unnormalized derived total equals N_sc. The use of T_sc is retained for denominator validation and discrepancy diagnostics even though it cancels algebraically in the normalized composition. Never multiply age percentages directly by N_sc without renormalizing their25+ composition: those percentages are shares of all ages.

For education group h, compute E_sc,h=N_sc × sum(e_sc,j in h)/100. Report the five-category percentage sum and k_edu=100/sum(e_sc,j for j=039..043). Use:

    education_target_sc,h = N_sc × sum(e_sc,j in h) / sum(e_sc,j for j=039..043).

Normalize within each state/column before adding C02+C04; this preserves each published subgroup's25+ mass and avoids allowing percentage rounding to reweight native versus naturalized citizens. Then sum state/column targets to region×age and region×education. Both sets must total exactly the same sum of N_sc before division by the common national25+ citizen total. Save the common national total, regional totals, unnormalized/normalized cells and all scale factors. The proposed normalized targets must sum to1 in each margin set and have identical region shares. Reconciliation is a named deterministic method, not a hidden repair to obtain convergence.

## Rounding checks and sensitivity bounds

The following bounds address published numerical precision only. They are not confidence intervals and do not bound sampling or nonsampling error. Adopt ±0.05 percentage point for each displayed one-decimal percentage, clipped to[0,100]. Treat integer count estimates as fixed point anchors for primary fitting; separately allow ±0.5 person in precision-consistency checks. These are rounding assumptions for reviewer approval, not claims that the estimates are exact population truths.

Six age percentages have a worst-case summed rounding allowance of0.30 percentage point of T_sc. Thus require the unnormalized age-derived25+ total to agree with N_sc within0.003×T_sc+1 person, where1 is a conservative allowance for the two rounded count totals. Also require individual percent values within[0,100] and the rounded25+ percentage sum not to imply an impossible fraction beyond its precision bound. Five education percentages must sum to100 within0.25 percentage point. Add only a named negligible arithmetic tolerance, proposed1e−10 in proportions; do not choose wider tolerances after observing a failure. A violation blocks the affected target set for review. Observed independent checks (education sums99.8..100.1 and maximum age-total discrepancy about0.0019883 of T) motivate documenting these already-known facts, but the proposed tolerances derive from numerical precision, not optimization to pass those observations.

For every normalized age or education composition, save conservative componentwise bounds. If a group's percentage sum has interval[L_g,U_g] from its constituent displayed percentages, and other groups have intervals[L_o,U_o], bound its normalized share by:

    lower = L_g / (L_g + sum(U_o))
    upper = U_g / (U_g + sum(L_o)).

Require positive denominators and clamp only the original input percentage intervals to their mathematical domain; do not clip an inconsistent final target into apparent validity. Multiplying these shares by the fixed N_sc yields rounding-only componentwise count bounds. A separate sensitivity may propagate the integer precision interval[N_sc−0.5,N_sc+0.5] as well. The componentwise endpoints are not jointly attainable simultaneous margin vectors; do not fit all lower or all upper bounds as though each vector sums to the published total. Preserve mass-conserving feasible combinations for any future fitting sensitivity.

A future implementation should first report these bounds and scaling diagnostics without fitting. Any model sensitivity to rounding needs a separately frozen finite set of feasible percentage perturbations satisfying interval, sum, geography and common-total constraints. It must use the same perturbations across compared models. No random search for a favorable target or selection on held-out scores is allowed. If bounds are wide enough to change conclusions, report the instability and leave promotion blocked.

## MOEs, covariance and other uncertainty

Original S0501 M fields are90% MOEs: persons for count totals and percentage points for percentage rows. Preserve them alongside each source estimate and identify controlled/unavailable/suppressed MOE annotations distinctly. Do not multiply, add or normalize MOEs using the point-estimate formulas and label the result a valid90% interval. Totals and subgroup proportions are correlated; native/naturalized components and geographic aggregates may also require covariance treatment. Their product, ratio and sum uncertainties cannot be established from these marginal MOEs alone.

No covariance-adjusted ACS benchmark interval is proposed for release in this amendment. A future uncertainty extension requires documented Census-approved approximation assumptions or suitable variance/covariance information, independent review, and separation of sampling uncertainty from rounding precision. ANES cluster resampling below conditions on the chosen ACS point targets; it does not include ACS target uncertainty. Even fully accounted sampling uncertainty would not include all nonresponse, measurement, coverage, temporal transport or synthetic-response validity errors.

## Matched exploratory validation and historical preservation

Preserve the original suppressed-cell model, all prior runs, sparse-weight loss, held-out support diagnostics and the failed hierarchical comparison. Do not overwrite them or silently relabel resident-calibrated runs citizen-calibrated. The prior primary hierarchy tau5 performed worse than the independent comparator; this proposal does not select a new tau to reverse that result. Keep primary tau5 and sensitivity tau1/20 only if a later independently reviewed configuration explicitly freezes them. Any revised model is a new exploratory candidate, not a retroactive correction of prior predictions.

Use exactly the same ANES recodes, eligible records, positive survey weights and PSU/stratum hash partition with seed20261103. Internally verify exact record membership and weights against the original loader, not only counts. Do not export respondent IDs, raw answers or cluster identities. The446 held-out records and352 held-out clusters have already been inspected; this remains retrospective exploratory validation. No reused holdout may be called untouched, sealed for a new confirmatory test or prospective evidence. A future independent dataset/split and an analysis freeze would be needed for stronger confirmation.

Predeclare a matched2×2 comparison: independent versus hierarchical population model, crossed with resident versus proposed citizen25+ calibration. Hold fixed source sample, six-field grid, recodes, smoothing, seeds, calibration algorithm/tolerance and evaluation records. Compare the two models under each target, and compare the calibration change within each model. This distinguishes changing benchmark universes from changing model complexity. Treat the original suppressed baseline as the preserved historical reference; any attempt to calibrate its limited support to new targets must fail closed on structural zeros and must not redefine the target or exclusion rule to force success.

Use the existing full2,880-cell grid, common scoring probability q=(1−1e−9)p+1e−9/2880, weighted held-out joint negative log probability, raw support coverage, retained training weight and calibration/concentration diagnostics. Lower log loss is better. Keep the fixed primary hierarchy-minus-independent paired loss difference and descriptive500-repetition cluster resampling with seed20261103. Report all2×2 cells and all frozen sensitivities, including failures, exclusions and negative comparisons. These are exploratory diagnostics conditional on the point targets, not survey-design confidence intervals or evidence of representative humans. Marginal convergence, full support imposed by smoothing or citizenship alignment alone cannot earn demographic complexity.

## Acceptance and nonpromotion criteria

A future implementation may be marked as passing only its explicitly bounded engineering or exploratory milestone after separate audit. Required criteria are:

1. Independent methods reviewer approves or amends this proposal in writing before conversion code or candidate fitting. Record deviations prospectively in a new version; preserve this draft and frozen v3 lineage.
2. Exact acquired source bytes, metadata, official units/denominators, geography set and citizen25+ interpretation verify. Required missing/suppressed values, impossible domains or rounding-inconsistent totals fail closed with preserved diagnostics.
3. Hand-calculated fixtures verify age versus education denominators, native/naturalized addition, education coarsening, PR exclusion, rounding bounds, non-overlapping citizenship categories and common published25+ mass. Adversarial fixtures reject swapped denominators, mixed years/products, duplicate geographies, bad annotations and silent target rescaling outside declared bounds.
4. A target-only artifact records source/code/config hashes, all raw and normalized derived margins, precision intervals, scale factors, MOEs, exclusions and independent review status. Age/education national totals and regional shares agree by construction and by tested arithmetic. This artifact is clearly labeled DERIVED_APPROXIMATE_CITIZEN25PLUS_TARGETS, never published exact subgroup counts.
5. Only after target audit, run and replay the separately frozen matched exploratory comparison. Log immutable run IDs, inputs, code hashes, seed, failures and zero spend. Exact aggregate replay hashes must match; all model/target conditions remain visible and receive the same evaluation rules.
6. The independent auditor recomputes target arithmetic and held-out paired scores from permitted local inputs. The worker cannot certify its own scientific milestone. No automatic promotion follows an improved score on this inspected holdout; worse or unstable scores retain the simpler model and the original failure record.
7. The full population-science gate remains BLOCKED until the original coverage/state scope, transport, independent validation, privacy/disclosure limitations and matched-complexity conditions are met. No human persuasion, prospective forecasting, representative electorate or external validity claim is enabled. No live model calls, spending or publication is authorized by this amendment.

Next action: independent review of these choices, especially published25+ anchoring and rounding-only reconciliation, then a separately versioned target-conversion implementation. This document itself executes nothing.
