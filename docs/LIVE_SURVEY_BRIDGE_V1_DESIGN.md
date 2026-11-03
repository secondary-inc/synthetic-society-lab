# Survey / OpenRouter bridge v1: proposed engineering contract

Status: implementation design, pending independent methods/code acceptance. No live-run authorization. This extends the shared runner; it does not rewrite the frozen mocked pilot or approve its cohort for real inference.

## Scope and invariants

Use the existing fully crossed assignments, exact two-item instrument and independently implemented scoring. Each pre request contains only its fictional profile, item order, seed and instrument. Each post request contains only that same unit's baseline and its assigned exposure. Serialize the complete request into a fresh two-message OpenRouter call; no cross-unit conversation, tools, hidden reasoning requests, routing fallback or retries. The existing OpenRouter adapter handles fixed-model/provider pricing validation, pre-dispatch reservations and usage settlement. This bridge adds the experimental phase lifecycle around it.

Persist the run manifest, frozen protocol/input hashes and assignment/instrument artifacts before any call. A SQLite phase journal records the exact request/hash and a durable STARTED state before invoking the adapter. A complete valid/invalid answer and returned billing metadata are committed together after the adapter has reconciled its ledger. Reopening a journal with STARTED or FAILED_UNCERTAIN refuses further dispatch; never infer that an interrupted request was free or replayable. Crash after provider success but before the phase checkpoint is intentionally unresolved rather than retried. Reconciliation is a separately reviewed, explicit future operation, not an automatic retry switch.

A clean interruption between committed phases may resume the identical code/config/input run. The run lock prevents concurrent owners. Resume verifies exact phase requests, stored outcomes and billing receipt bindings before reuse. A sealed completed or failed run is immutable. Errors/cancellation caught in-process preserve type-only failure artifacts and seal the current run; an abrupt process death leaves the manifest/journal available for fail-closed inspection.

## Proposed invalid-phase amendment

Record all raw structured survey answers after credential-pattern redaction, including missing/null/unexpected fields; rescore independently. For an invalid or missing pre answer, skip that unit's post dispatch and record its exact would-be post request, null item answers and explicit SKIPPED_INVALID_PRE status. This avoids presenting an invalid baseline as usable context, does not impute a response, and does not drop the assignment. Retain the unit in arm/quality counts and exclude its invalid numeric pair under the frozen complete-pair rule. A valid pre with an invalid post remains a recorded invalid pair. No repair prompt, replacement profile, compensating sample or selective rerun is allowed. This is a new operational amendment requiring independent acceptance before live use.

Responses in all five arms remain available for the original exact-assignment rescorer. Mock bridge analysis stays MOCK and does not estimate scientific effects. Any later real-model analysis must have separately reviewed finite-cohort interpretation, uncertainty, invalidity/missingness sensitivities and non-confirmatory labeling; changing a kind string does not validate an experiment.

## Live admission

The initial bridge exposes only an authored mocked transport run. A real OpenRouter transport path must remain unavailable until an independently accepted bridge/release, independently accepted protocol/population/stimuli, actual owner budget/credential authorization, pinned fresh provider prices, a concrete per-call cost envelope and matched simpler conditions exist. Supplied credentials are not authorization. This implementation must not read local credentials, fetch prices, issue source requests or model calls. Fixture ledger amounts are simulated accounting, never actual spend.

A separate future release can connect this tested phase engine to a live admission factory. Until that reviewed release exists, live dispatch is explicitly refused. This milestone completes integrated offline OpenRouter-adapter accounting, not live-study readiness or the full model-controls/scientific contract.

## Acceptance criteria

1. Complete a 12-profile, three authored-stimulus, five-arm mocked bridge run through the actual OpenRouter adapter class with fake transport: 180 units, 360 complete phase calls, exact request/instrument/treatment isolation and independent raw rescoring.
2. Verify invalid pre skips post without changing assignment counts; invalid post is recorded; neither triggers retries or imputation.
3. Verify clean between-phase resume reuses completed phases, while unknown STARTED and charged-but-uncommitted gaps block without another transport call. Test abrupt process termination and concurrent resume ownership meaningfully.
4. Verify wrong input/code/instrument, changed request/checkpoint, duplicate/missing assignments and cross-unit response substitution are rejected.
5. Exercise provider mismatch, unknown cost, overruns, timeouts and cancellation through the adapter, retaining conservative charges and type-only failure evidence.
6. Log exact request hashes, serving provider/model, usage, completion IDs, per-phase billing receipts and a frozen price/policy snapshot. Label fake amounts separately; actual paid calls/spend remain zero.
7. Preserve all failed runs and local journals. Names containing `.local.` exclude entire runs from review bundles until a separate approved disclosure derivative exists.
8. An independent auditor reviews protocol/lifecycle behavior, recomputes the actual mock run and checks the absence of real network access. No owner spend question is needed for fixture execution.

## Pre-review hardening after the first prototype fixture

The first unaccepted prototype run remains immutable and its exact implementation is preserved at local commit `4e7fc7e`. The current candidate additionally stores the explicit simulated price/policy in its manifest and `bridge-lock.json`, pins the exact existing instrument and three authored stimulus identities, and permits fixture profiles containing only fictional IDs and explicit party priors. It is not a population generator.

A private checkpoint pairs the journal and simulated-budget SQLite byte hashes with the frozen config hash after each fully committed phase. Resume requires both databases, every frozen artifact and this matching checkpoint; missing/replaced databases and a charged-but-uncommitted phase are refused before any new call. Semantically verify every stored phase against the frozen assignment and its own pre response; reconcile exact output/request hashes, unique billing receipts, serving model/provider, token/cost metadata and frozen price/policy against the separate adapter ledger. Recomputing one checksum does not bypass those cross-record checks. This is trusted local execution and independent drift detection, not hostile-host authentication or a guarantee against power loss/storage failure. A crash during checkpoint persistence can deliberately require reconciliation despite a completed response. Copy unresolved SQLite bytes before any future forensic recovery that could mutate them.

The initial real transport entry point always refuses. Future live release must use the same durable **owner-wide** approved ledger across runs, not treat each per-run simulated fixture ledger as a renewed budget. It must verify owner authorization, independent exact-code/analysis/source/population release, fresh authenticated price evidence and a conservative upper envelope for the adaptive valid-baseline post request. A live invalidity/attrition sensitivity amendment remains mandatory; complete-case mock scoring cannot by itself establish the full-cohort causal estimand.
