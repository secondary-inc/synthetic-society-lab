# E02: controlled synthetic-response engineering pilot

Version 1; frozen for an offline mocked engineering pilot, not externally preregistered. This implements the v2 blueprint and November 3 audit. Confirmatory work remains blocked. No human persuasion inference is supported.

## Outcome and instrument

`configs/e02_instrument.json` fixes the two ANES pre-election party feeling thermometers, V241166 and V241167, each 0–100. The May 19, 2026 supplied codebook printed pp. 82–83 verifies the items; p. 102 maps V241221 party identification. Model-administration instructions are explicitly adapted, rather than claimed to reproduce a human interview exactly. The questionnaire cover-date/filename mismatch is recorded in the source notes; the actual CSV and release-specific codebook govern this mapping.

Primary response is in-party minus out-party warmth, in thermometer points, for profiles with fixed Democrat or Republican priors. Independents and unknown party remain in quality counts and the exploratory absolute-gap measure, but are excluded from the primary contrast by definition. A negative primary value is permitted. The time-point gap ranges from -100 to 100, before/after change from -200 to 200, and difference-in-changes from -400 to 400. Divide by 100 for normalized units; this is a range normalization, not an empirical standard-deviation effect size.

The primary contrast is C2 minus C1 in before/after change for exactly matched profile × stimulus × repetition units. Both items must be valid at both time points. Missing, refusals, negative ANES codes, out-of-range numbers, booleans and nonnumeric responses are not imputed. Invalid pairs and nonpartisan primary exclusions are reported. There are no confirmatory secondary hypotheses in this pilot.

## Population and calibration

`configs/e02_population_mapping.json` freezes source variables and exploratory recodes. Use fresh combined pre-election ANES sample types 2/3, V240103a weights and its matching PSU/stratum fields. Restrict to 25+ so that B01001 age cells and B15003 education margins refer to a compatible age universe. Retain top-coded 80+ as 65+. Unknown income, race or party is explicit; invalid age, education, region or design clusters are excluded and counted.

Fit coarsened joint region × age × education × party × race × income cells with at least five training observations. Split held-out records at the survey cluster level with a fixed seed. Iterative proportional fitting matches region-age and region-education resident shares from ACS 2024 five-year files. Preserve supported joint associations rather than drawing independent marginal features. Five-category education had structural zeros after suppression; three categories were selected before model execution and recorded as an exploratory protocol revision.

Race B03002 is all ages and income B19001 counts households, so those tables are registered as audit-only references, not forced onto 25+ person weights. No race/income calibration claim is made. The ANES citizen universe differs from ACS resident benchmarks; transport is exploratory. Diagnostics include convergence, residuals, supported cells, sparse-cell exclusions, calibration factors, effective sample size, and held-out party-share discrepancy. These diagnostics do not replace design-based human-survey inference or validate synthetic responses.

Generate fictional IDs and coarsened joint cells only; no respondent identifiers, exact ages, addresses or individual survey answers enter generated profiles. The 12-profile pilot draws three profiles per Census region. Design weights are saved for inspection, but primary scores describe the equally weighted engineering pool. No state-level estimates or voter representativeness claims are allowed. Demographic complexity is not promoted until compared against a persona-free simpler configuration under matched evaluation conditions.

## Treatments and assignment

The versioned stimulus collection contains three project-authored fictional DEMO policy notices. They test software, not real news effects. C0 receives no notice; C1 and C2 receive byte-identical underlying text and identical source labels in different text wrappers. This is text framing, not visual feed exposure. C3/C4 additionally receive the same fixed source-bounded Q&A. That Q&A is a scripted fixture and not a live assistant.

Use a fully crossed design with randomized execution order. For each profile–stimulus–repeat unit, all five arms share the baseline seed and survey item order. Fresh independent request objects prevent cross-arm state; the post request sees only its own pre response and assigned exposure. Model/provider seeds cannot guarantee deterministic real API responses; no such claim is made.

The deterministic mock deliberately injects a known two-point primary social-wrapper change to verify scoring recovery. This is an authored test expectation, not an empirical finding. C0 provides a repeat-instrument engineering check. Responses, request hashes, assignments, source hashes, prompts/requests, exclusions and scoring are saved. Private reasoning traces are never requested or retained.

## Analysis, checkpoints and execution gates

The engineering analysis uses a seeded crossed profile/stimulus bootstrap; repetitions remain within those clusters. Small cluster counts and deterministic mock output prohibit meaningful scientific significance claims. The reported interval only summarizes resampling of recorded mock responses. Full arm coverage and duplicate-unit checks prevent denominator switching.

SQLite jobs use deterministic IDs and durable completion records. Resume requires identical code and configuration. Jobs left RUNNING by an interruption need explicit reconciliation; no unknown model request is silently retried. Outputs are immutable, checksummed and labeled MOCK. Paid execution is unavailable through the pilot CLI; the shared OpenRouter adapter defaults to disabled and requires approval, fresh provider pricing and ledger reservations before dispatch.

Main/paid experimental execution additionally requires permitted real stimuli, population-validity review, complete instrument/protocol approval, exact model/provider selection, explicit budget and prespecified analysis. News, actual social feeds, live assistants and swarms each need matched simpler comparisons. A swarm requires an equal-compute independent ensemble. A failed advanced configuration remains recorded; passing a smoke test never establishes incremental value.

## Acceptance criteria

1. Instrument tests verify party direction, valid range, missingness and exact change calculation.
2. Population tests verify known margin recovery, joint odds-ratio preservation, structural-zero rejection, convergence failure and reproducible region-stratified sampling.
3. Treatment tests verify byte-identical stories, same attribution, same scripted Q&A and no stimulus for C0.
4. Assignment tests verify full crossed coverage, deterministic seeded ordering and reset requests.
5. Analysis tests recover the known fixture contrast and reject duplicate/incomplete assignments.
6. An actual 12-profile mocked run saves all artifacts, reports exclusions, uses no paid requests and reproduces response hashes on replay.

Passing these criteria establishes an offline engineering pilot only. Human external validity, real-model effects, source-rights clearance and confirmatory preregistration remain separate blocked gates.
