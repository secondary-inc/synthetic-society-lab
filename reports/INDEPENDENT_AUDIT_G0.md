# Independent audit — initial G0 foundation and completion scope

Auditor role: independent auditor, separate from implementing lead and E01/E02 workers. Date: November 3, 2026. This report certifies only the inspected snapshots and named evidence. It does not certify later concurrent edits or the full research program.

## Verdict

**G0 is BLOCKED as a full completion-contract milestone.** Clean isolated installation, the existing fixture test suite, local byte integrity and current secret exclusions were independently verified. Reacquisition/import paths for the complete registered source collection are not yet demonstrated, and remote CI is not observed. No clause of the six-part scientific completion contract is fully proven by the current engineering evidence.

The initial inspection reproduced three software defects using temporary ledgers and injected transports only. The lead fixed them; the independent auditor reran the original probes and verified their remediation. The original findings remain in the audit record. A fourth issue in the new completion controller (an empty contract classified COMPLETE) was also independently reproduced, then fixed by the lead and independently verified after the clean snapshot run.

No implementation files were changed by the auditor. No real model request, credential-authenticated API request, external publication or paid execution was performed. The only fresh environment setup was installation from a local source snapshot with normal Python build tooling.

## Evidence and reproducibility

- `INDEPENDENT_AUDIT_G0_execution.json`: original frozen source snapshot, every file hash, exact installation/test commands and stdout/stderr, source check results, and secret-file metadata. The original checkout and independently installed snapshot each passed 46 tests. Fixture validation passed one check and full local registered-source validation passed 90 checks.
- `INDEPENDENT_AUDIT_G0_current_execution.json`: a subsequent frozen snapshot after the three lead remediations, installed into a new virtual environment. All 53 tests in that snapshot passed, as did fixture integrity validation. No copied file changed between snapshot creation and completion of these commands. Later new files/edits are outside this result and need re-audit.
- `INDEPENDENT_AUDIT_G0_probes.json`: original independent counterexamples, kept unchanged.
- `INDEPENDENT_AUDIT_G0_remediation.json`: independent post-fix probes and the additional empty-contract finding, including exact code-file SHA-256 values.
- `INDEPENDENT_AUDIT_G0_artifacts.json`: independent rehash of six recorded run directories, their checksum ledgers against the committed evidence receipt, the tracked-file credential-pattern scan, nonsecret zero-budget settings and an independent arithmetic recalculation of the mock primary contrast.
- `INDEPENDENT_AUDIT_G0_controller_remediation.json`: empty and duplicate contracts now rejected; five controller tests independently rerun after the lead fix.

The snapshot paths and commands in the execution JSON are concrete local reproductions. They copy source/tests/configs/protocols, not `.env` or acquired raw data, then install into a fresh virtual environment and run unittest discovery plus fixture validation. Full source integrity was checked against the actual local raw collection separately. Python was 3.12.14 on the local macOS host; configured Linux/Python 3.11 CI is not a substitute for observed execution.

## Findings

### IA-G0-001 — P2, false-like policy flag — REMEDIATION VERIFIED

Original location: `src/civiclab/model.py`, `BudgetLedger.reserve`, line 53. The original truthiness check allowed `Policy(enabled='false', ...)` with nonzero test caps to reserve money. This was an enforcement-boundary type error; the real default zero caps remained safe, and no real request was made.

The lead changed the enforcement check to require the exact boolean `True` and a nonempty string approval ID. Independent rerun now rejects the same false-like string. This is not independent proof that an approval ID corresponds to a genuine owner authorization; it remains an operator/workflow attestation.

### IA-G0-002 — P1 before paid execution, cancellation did not halt uncertain billing — REMEDIATION VERIFIED

Original location: `src/civiclab/model.py`, `OpenRouter.complete`, original line 196. An injected `KeyboardInterrupt` from the transport escaped the `Exception` handler. The receipt remained RESERVED and another reservation was accepted, despite unknown request outcome. Conservative reserved amounts still counted toward caps, but the promised uncertain-billing halt was absent for cancellation.

The lead changed the handler to include cancellation/base exceptions, preserve/reconcile the reservation conservatively and re-raise cancellation after recording uncertainty. Independent rerun observes UNCERTAIN, rejection of subsequent reservations, and propagated `KeyboardInterrupt`. No real billing/provider behavior was exercised.

### IA-G0-003 — P2, finalization crash could not recover — REMEDIATION VERIFIED

Original location: `src/civiclab/common.py`, original `finish` lines 133–135 and `resume` line 158. Injecting failure while writing `checksums.json` left `summary.json` present but no seal. The dashboard correctly rejected that incomplete run, while resume also rejected it as finalized, preventing recovery.

The lead now distinguishes a sealed run from a pending finalization and allows the identical saved summary to be sealed on resume. Independent rerun confirms the checksum ledger is created after recovery. Tests are for accidental interruption in trusted local code, not adversarial tampering or an independently timestamped archive.

### IA-G0-004 — P2, empty completion contract yields false COMPLETE — REMEDIATION VERIFIED

Location: `src/civiclab/orchestration.py`, `completion_status`, final `all(...)` status expression. A temporary contract containing `{"requirements":[]}` returns COMPLETE because `all([])` is true. Duplicate IDs also silently collapse in the requirements dictionary unless validated. The real contract currently has 23 requirements, so this counterexample does not mean the current program has been displayed complete.

Required remediation: reject empty/malformed contracts and duplicate requirement IDs before computing status, with negative regression tests. Broader contract scope remains anchored to the owner's six completion clauses; a configuration edit cannot legitimately redefine completion.

The lead added nonempty-list/identified-ID and duplicate-ID checks. Independent rerun rejected both empty and duplicate contracts, and all five controller tests passed. The original counterexample remains recorded in `INDEPENDENT_AUDIT_G0_remediation.json`; the correction is separately recorded in `INDEPENDENT_AUDIT_G0_controller_remediation.json`.

## Test validity and limits

The tests exercise useful failure cases, including tamper detection, missing/escaped paths, exact outcome coverage, party sign and range, IPF support/convergence, known mock-effect recovery, repeated assignment consistency, concurrency/cap persistence, malformed billed responses and basic trusted-worker file/network denial. The passing original tests did not cover the three original independent probes, demonstrating why test count alone is insufficient. New tests passing after fixes are necessary, not a blanket certificate of scientific validity.

The six stored evidence runs had 53 sealed artifacts in total. Every checked artifact matched its run checksum ledger; all six ledgers matched the tracked evidence receipt. The two mock pilots have identical response hashes, 180 response records each, 24 primary pairs and 12 nonpartisan primary exclusions. Independently recomputing the in-party-before/after contrast gives the deliberately injected two-point fixture value. This is MOCK engineering behavior, not observed model or human treatment effects.

The predictor environment and Python audit hooks are useful trusted-code controls. They are not an adversarial operating-system sandbox, cannot prove an operator never saw historical outcomes, and do not establish prospective timing. Local hashes prove consistency with the recorded bytes, not authenticity, licensing or external timestamping.

## Completion contract, clause by clause

1. **Source inventory and clean reproduction — BLOCKED overall.** Independent install and fixture tests pass; local source hashes pass. Exact documented reacquisition/import paths for the entire nonredistributable raw collection are not demonstrated. In particular, manually supplied Dataverse release identity/reuse notes and timestamped Census-export acquisition remain incomplete. A byte-hash pass alone does not close this clause.
2. **E01 complete forecasting workflow — BLOCKED / NOT RUN.** The audited snapshot has strict validators and a deterministic DEMO S0/evaluator, but its genuine historical baseline remains blocked; a real frozen race registry, valid ballots/geography, comparable real agent variants and real sealed evaluation tables are not proven. Later E01 worker discoveries must be audited separately. No prospective 2026 submission is established.
3. **E02 scientific workflow — BLOCKED / NOT RUN.** A mock-frozen primary instrument and weighted exploratory joint-cell fit exist. Sparse support exclusions, citizen/resident universe mismatch, the 25+ restricted target, lack of state estimates, absence of independently reviewed real stimuli, registration and scientific sensitivity analysis prevent full acceptance. Five-arm mock sessions do not establish real-model exposure or assistant effects.
4. **Inference, money and checkpoints — PARTIAL, not full scientific completion.** Defaults are disabled and zero; reservations/conservative reconciliation are implemented and tested using injected transports. Three control/recovery defects were independently found and remediated. Positive authorized funding, rotated/verified keys, real provider pricing/billing evidence, a reviewed real runner and cancellation behavior in actual service use remain unproven. Automatic retries are disabled; no retry-success claim is made.
5. **Independent milestone review, CI and traceability — INCOMPLETE.** This is an independent first milestone audit. Every future scientific milestone has not yet been reviewed. GitHub CI configuration exists, but passing remote CI was not observed. Six audited run ledgers are internally traceable; future research tables/figures still need their own validated real-run lineage.
6. **Owner-review publication/reproducibility package — INCOMPLETE.** The initial snapshot lacks a complete audited paper/blog, full limitations report and reproducibility pack. Work on those drafts can proceed without spending; their claims must be audited when ready. External publication, affiliations and hosting have no approval.

## Gate-by-gate acceptance evidence still required

- **G0:** current independently installed source snapshot, documented passing fixture tests, secret exclusion/default checks, and complete source reacquisition/import evidence. Remote CI is a separate explicit requirement of the contract.
- **G1:** exact frozen E01/E02 hypotheses, target population, primary/secondary outcomes, scoring, missingness, exclusions, assignment, sample size, uncertainty and sensitivity plan, with independent signoff before confirmatory execution.
- **G2:** genuine permitted frozen stimuli and source rights/times/hashes; official candidate/race/geography evidence; compatible historical returns; population-support and universe acceptance. Newly acquired files need new source manifests and independent checks.
- **G3:** tested deterministic engines and reviewed default-deny inference controls, including reservation, cancellation, reconciliation, route/price bounds, failure records and resumable checkpoint behavior. Current mock engineering provides partial evidence only.
- **G4:** a 12-profile mocked pilot with complete crossed assignments, identical content/source attribution, context reset, invalid-response accounting and independently recomputed scores. This gate is verified only for the sealed MOCK runs identified in the artifact receipt; it never proves scientific effects.
- **G5:** affirmative owner-approved positive budget, rotated/verified credentials, fresh exact provider price and full-run cost estimate. This is genuinely externally blocked and cannot be self-authorized.
- **G6:** actual preregistered model/retrospective evaluations, same-unit/same-race simpler comparisons, seed/prompt/model sensitivity, uncertainty, negative outcomes and independently computed metrics. These have not been established by the mock pilot.
- **G7:** figures/tables generated from identified validated runs, consistent paper/blog/limitations drafts, a reproducibility pack, independent publication-claim review and review PR. Human approval precedes publication. GitHub access/CI remains a delivery dependency.

## Auditor job receipt

TASK_ID: INDEPENDENT_G0_INITIAL

FILES_CHANGED: only `reports/INDEPENDENT_AUDIT_G0*.md/json` and `reports/AUDIT_COMPLETION_G0.json`.

OUTPUT_ARTIFACTS: this report; original/current execution snapshots and logs; original/remediation probes; stored-artifact arithmetic/hash audit; machine completion receipt.

REPRODUCTION_COMMANDS: exact commands and snapshot paths are in the execution JSON. Relevant probe logic and actual outcomes are in the probe/remediation JSON; no fake transport contacted a service.

TESTS_RUN_AND_RESULTS: original snapshot 46 PASS; post-remediation snapshot 53 PASS; later controller tests five PASS; full local registered-source checks 90 PASS; fixture check one PASS; six sealed run ledgers validated; all four independently reported defects have verified remediations. The counts refer to overlapping suites/snapshots and must not be added as unique tests.

SOURCE_DATA_AND_LICENSE_NOTES: acquired source bytes verified locally; licenses and complete reacquisition are not inferred from hashes. No raw respondent/publisher data were copied into reports or uploaded.

COST_USD_ACTUAL_OR_ZERO: $0 model/content API cost, zero real model/API calls; local compute/build tooling not priced.

RISKS_AND_LIMITATIONS: scoped snapshots can become stale during concurrent development; passing fixtures are not research completion; real billing, rights, external validity, CI and publication not certified.

UNRESOLVED_BLOCKERS: complete source reacquisition; real scientific protocols/data/evaluations; positive owner authorization and rotated/verified credentials; observed CI; final publication package review. Concurrent later edits require fresh scoped audit receipts.

NEXT_UNBLOCKED_TASK: implementers complete bounded work; auditor separately reviews each finished milestone and publication artifacts against fresh scoped fingerprints. The new reproduction module and publication drafts are not certified by this G0 report.
