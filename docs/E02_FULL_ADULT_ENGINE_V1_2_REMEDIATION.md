# F engine v1.2 — retained analysis failure barrier

Status: implementer remediation candidate, independent review pending. The finding `IA-E02-F-V1_1-HALT-003` remains open until a separate auditor issues a new scoped decision. This version does not claim overall F acceptance, actual-source authority, population fitting, disclosure or model/spending release.

Original v1 and v1.1 files/runs/findings remain unchanged. The new `reports/E02_FULL_ADULT_ENGINE_V1_1_FREEZE.json` pins v1.1, alongside the lead's preservation commit `fb72ff4`. v1.2 uses separate seven `full_adult_*_v1_2.py` modules, `configs/e02_full_adult_engine_v1_2.json`, `tests/test_e02_full_adult_v1_2.py` and the `F_AUTHORED_V1_2` fixture namespace. Normative U1 v1.1 output names, schemas, arithmetic and quotas remain unchanged. Earlier cost and CSV-width fixes are carried forward.

## Defect and fix

The reviewed v1.1 ledger retained an UNKNOWN query's full 645-unit/2,048-byte charge but treated the mutable `halted` boolean as sufficient permission for later work. Clearing that flag and resealing the mutable final state/receipt/event closure let a different query run. Retaining cost alone did not enforce the frozen-batch stop condition.

In v1.2, FAILED/UNKNOWN phase records and FAILED/UNKNOWN/REFUSED query records imply a permanent analysis barrier. Semantic write/reopen validation rejects a false halt flag with any such retained record. Query result status, payload-proof presence and terminal receipt phase must agree; for example, an UNKNOWN record cannot be relabeled COMMITTED while keeping its failure status/proof. Phase failures emit an explicit `phase_failed` event. Reopen validation also derives the barrier from retained phase-failed/phase-unknown events and failure/unknown/refusal receipt statuses, so changing a current phase to COMMITTED with a plausible zero duration does not erase retained failure history. Writes cannot clear a prior halt. There is no reset or continuation-approval entry point for this analysis version.

New work checks the reconciled barrier before phase/query reservation, admission/binding, and execution before context work, reservation or real child dispatch. Read-only inspection, recording UNKNOWN recovery, typed NULL/refusal projection and sealing recorded outputs remain possible under an intact halted ledger; they do not evaluate new queries or refund usage. Torn/corrupt ledgers remain refused. Successfully committed batches continue normally.

## Semantic review scope

The review covers query FAILED/UNKNOWN, pre-work REFUSED, catalog/mandatory phase FAILED/UNKNOWN, pending reservations, recovery, terminal receipt/current-status correspondence and direct write attempts. Full known operations and bytes remain unchanged by the halt attacks and subsequent refusals. Recovery consumes the existing full reservation and cannot dispatch again. A pending reservation remains pending or is explicitly recovered UNKNOWN; other reservations still refuse. Failure assembly accepts only committed proof or typed failed projections.

This analysis barrier must not be generalized into a different source-acquisition policy. `docs/E02_NATIONAL_PUMS_N1_CONTROLS.md` lines15–17 separately specify conservatively charged source failures and exact-state authored continuation. That source policy is unchanged. The v1.2 source-control/coordinator copies change only their F namespace/imports. No accepted N1 source file, source-continuation mechanism, method or quota was edited, and no new source shutdown or release is inferred. Arbitrary coordinated rewriting of all trusted histories/anchors remains outside internal SHA-chain authentication claims.

## Verification and reproduction

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest test_e02_full_adult_v1_2.PermanentBarrierTests test_e02_full_adult_v1_2.RemediationTests -v
PYTHONPATH=src:tests .venv/bin/python -m unittest test_e02_full_adult_v1_2 -v
PYTHONPATH=src:tests .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v
PYTHONPATH=src:tests .venv/bin/python -c "from test_e02_full_adult_v1_2 import record_authored_run; record_authored_run('data/processed/e02_F_authored/F-mock-v1_2-NEW-ID')"
```

The new suite retains 20 preceding fixture methods and adds two expanded barrier methods. Ten retained attacks cover five terminal cases (query FAILED/UNKNOWN/REFUSED and phase FAILED/UNKNOWN), each with flag-only resealing and terminal relabeling. All preserve immutable plan/runtime/genesis bytes and known charge counters. Each must reject fresh opening, direct query reservation, execute, phase reservation and work guard; an instrumented real-worker dispatch hook must remain uncalled and no evaluator marker may be written. The positive test dispatches two actual fixture child processes successfully, records two evaluator markers, then recovers another reservation UNKNOWN and rejects a direct write/reset attempt without changing charges.

A separate ignored probe directory preserves the ten bad histories and all indexed files. A new full-shape retained MOCK run checks successful pipeline continuation and primary/replay equality. The versioned evidence report pins code/config/tests, full test log, probe index and run artifacts. Historical v1/v1.1 tests remain present for reproducibility; aggregate passing tests do not certify those known-defective historical engines.

## Acceptance and unchanged limits

A separate auditor must rerun the original halt attack and independent phase/query variants, verify zero future evaluation/reservation/dispatch, validate no charge loss, inspect retained histories and successful continuation, and issue an exact-version scoped decision. The implementer does not close or edit old findings.

All previous scientific/resource/source limitations remain: closed-vocabulary standard-library schema checks rather than general JSON Schema conformance, sampled/cooperative limits rather than absolute OS/wire/physical caps, authored full output shape rather than national source-volume capacity, unknown political priors, no human treatment-effect claim, no actual population fit or actual F source/reuse/disclosure authority. Actual source/parse/fit approvals remain null and actual authority/API/model spend remain zero. No shared CLI/dashboard/status or auditor file is edited by this worker.
