# Full-adult F engine v1.1 — narrow control remediation

Status: IMPLEMENTER CANDIDATE; independent remediation review pending. This document does not close the two findings in `reports/INDEPENDENT_AUDIT_E02_F_V1_CONTROL_FINDINGS.json`, renew any controller receipt, or approve actual sources, Wyoming reuse, disclosure, population fitting, model calls or spending.

## Preserved history

Original v1 modules, config, tests, documentation, evidence, receipt, test log and runs remain unchanged. `reports/E02_FULL_ADULT_ENGINE_V1_FREEZE.json` pins their exact bytes and retained run indexes. The lead also committed the initial candidate and findings at `75b4823`. That commit is preservation, not acceptance. New `full_adult_*_v1_1.py` files, `configs/e02_full_adult_engine_v1_1.json`, and `tests/test_e02_full_adult_v1_1.py` have a distinct F_AUTHORED_V1_1 namespace and no imports from v1 F implementation files. The accepted U0/U1 methods and N1 source controls are unchanged.

## IA-E02-F-V1-QUERY-COST-001

The original ledger reconciled charges against mutable admitted copies. A coeditor could lower both an admission cost and recorded charge, adjust aggregate counters, reseal mutable receipts/events/state and retain the immutable inputs. Reopening accepted that refund despite a previously consumed query.

The new ledger reconstructs the exact compiled plan from unchanged `plan_input.json` and the SHA-pinned U1 specification on each ledger opening that has an admission. It validates the frozen input on subsequent operations and caches the reconstructed result only within that ledger instance. Reconstruction is semantic validation, not a query evaluation or a replenishment of recorded work. Mutable admission JSON must exactly equal the reconstructed IDs, kinds, definitions, catalog units, per-query costs and two-sweep bound. Current and historical receipt charges must match those independently reconstructed costs. Query dispatch arguments must match the complete reconstructed vector, nonzero count, kind, definition and cost before reservation/evaluation; admission and terminal/refusal entry points also validate their inputs. When a common engine execution manifest is present, both copies must have the bound hash and agree with the frozen runtime/spec/code and reconstructed operation bounds. Low-level authored journal tests can still bind a dummy opaque hash; they are not source-bound production admission.

The added regression method completes the correct 645-unit covariance, then separately reseals zero-cost, one-unit-less, changed-kind, changed-definition, altered-total-bound and receipt-only edits. Frozen plan input, runtime config and genesis are byte-identical across each attack. New opening, next reservation and next execution must refuse without changing the corrupted evidence; a mocked evaluation hook must have zero calls. Six further argument mutations exercise zero/one-less charges, kind, definition, vector and nonzero count before dispatch and admission. The original 64-million-unit plan cap and no-refund semantics are retained.

## IA-E02-F-V1-CSV-WIDTH-002

The original DictReader projection checked required fields but accepted a missing unused trailing field, represented as a None value. The new all-age row gate rejects a None key (extra cells) or any non-string value anywhere in the header-mapped record (missing cells), before required-field interpretation, age selection or domain routing. Valid empty unused strings remain accepted. Required numeric/domain rules are unchanged.

The added regression method creates legitimately manifested authored ZIPs and uses actual `enroll_F`/`process_F` fixture APIs for all 12 source rows: six adult domains plus six under18 counterparts. For each row, it exercises a missing unused trailing cell, an extra quoted field and a valid empty unused cell: 36 cases. Malformed rows halt processing without an accepted aggregate, with full reserved usage retained. Operational events must not contain the private authored row or extra-field marker. No actual person data are accessed.

## Reproduction and evidence

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest test_e02_full_adult_v1_1.RemediationTests -v
PYTHONPATH=src:tests .venv/bin/python -m unittest test_e02_full_adult_v1_1 -v
PYTHONPATH=src:tests .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v
PYTHONPATH=src:tests .venv/bin/python -c "from test_e02_full_adult_v1_1 import record_authored_run; record_authored_run('data/processed/e02_F_authored/F-mock-v1_1-NEW-ID')"
```

Use a new destination for each retained run. The old v1 tests are intentionally preserved historical tests and do not certify the known-defective v1 implementation. The new v1.1 module contains 18 inherited fixture methods plus two expanded remediation methods. Aggregate E02 discovery includes both historical and new versioned suites; the evidence reports this count explicitly.

The retained v1.1 full-shape MOCK run has the same 51 authored sources, 3,978 all-age/3,672 adult/612 nested C rows per sweep, 3,672 cells and 293,760 signed replicate components. A separate ignored directory retains all six resealed cost attacks and all 36 width cases, including legitimately manifested malformed inputs, source ledgers, full failed reservations and unchanged immutable anchors. Its index and full run output hashes are pinned by the versioned evidence report. No input, failed history or prior finding is rewritten to improve status.

## Acceptance and limits

Independent acceptance requires a separate auditor to reproduce the original attacks against this exact new candidate, verify zero subsequent reservations/evaluations, inspect source-width failure consumption and positive empty-field cases, rerun the new suite, validate retained arithmetic/replay/resource hashes and issue a new scoped decision. Implementer passing tests do not close either finding.

All scientific, source and resource limitations in the original implementation documentation remain: standard-library closed-vocabulary/schema-semantic checks rather than general JSON Schema conformance; internal integrity under trusted code/immutable anchors rather than external authentication; sampled child RSS/cooperative stops rather than absolute OS/wire/physical caps; small authored source volume rather than national performance proof; no political-prior identification, human effects or actual population fitting. Actual source/parse/fit approvals remain null, authority and API/model spend zero. Shared CLI/dashboard/status/infrastructure and auditor findings are outside this worker's edits.
