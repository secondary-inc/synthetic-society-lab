# E01 typed document readiness v1.9: authored integration candidate

Status: implementation candidate for independent code/privacy/fixture review. The accepted methods audit is `reports/INDEPENDENT_AUDIT_E01_TYPED_READINESS_V1_9_METHODS.json` (SHA-256 `465241cf3a3a57445074f7e91c4c62609ed2ba8430d7d3fc040bd93b900a06e9`). This document grants no actual-source execution or coverage release.

## Acceptance contract

The separate wrapper must leave the v1.7 module, configuration, 12 roster objects and complete serialized public/private payloads unchanged. It must preserve five Idaho status-history records in a separate local artifact, with all four typed UNKNOWNs, blank district/write-in cells, literal parties, filing dates, Withdrawn Democratic history and four Approved rows. Approved does not mean nominee, printed ballot entry or amendment completeness.

A new schema2 document view has exactly 33 regular ClassII state slots and three separately bound context contests. Legacy roster references, Idaho status history and no-admitted-document observations have distinct, closed discriminators. It has no legacy fallback. Unknown schemas, kinds, extra diagnostics, changed filters, boolean/integer coercions and altered frozen contexts must refuse. The candidate's 13 document states/20 remaining jobs are conditional output fields only. Current accepted coverage remains **12 document states / 21 unfinished acquisition jobs / zero final ballots**. Legacy roster-state count remains12.

## Admission, execution and publication

1. Deep-copy a bounded closed built-in metadata tree before exact canonical admission. No root inspection, RunStore construction or source reading precedes successful admission. Every downstream authority comes from that snapshot, not the caller's aliases.
2. Require the expected checkout/import origins, no symlink ancestors, bounded relative files, pinned code/config/audits, 40 disjoint source IDs/paths and four pinned reference artifacts. Source declarations total3,760,839bytes; this number was calculated from metadata, not a new source read. Enforce per-file4MiB and total declared32MiB bounds. Preserve original geometry `pdfplumber==0.11.9` through the unchanged legacy validator.
3. Create one parent RunStore. Call only the existing pure v1.7 validator and pure v1.8.1 reader. Compute/validate both components in memory; create no child recorded success. Compare complete legacy encoded-byte hashes and canonical Idaho identities against references.
4. Write four payloads: `legacy_readiness_v1_7.json`, `candidate_rosters.local.json`, `id_status_records.local.json`, `typed_document_readiness.json`. Recheck exact serialized bytes and frozen inputs after publication; write payload hashes and typed commit. Check wrapper stability and finalize the normal parent ledger.
5. Recheck all bound inputs and wrapper after normal finalization. Only then atomically write `typed_release.json`, a terminal seal binding the complete parent checksum ledger, wrapper and admitted config. The typed consumer refuses the parent ledger while this seal is absent. A success path performs four complete input-binding passes (160 authored source verification attempts in the fixture); this is not160 distinct source representations.
6. Before returning, re-read the strict local consumer. It requires the exact run location/file set, main ledger, terminal seal, manifest role/config, exact success summary, payload hashes, frozen legacy byte identities, Idaho reference identity and public schema. The terminal seal is necessarily outside the ledger it binds; it is a final commit record, not independent timestamping or owner authentication.

No shared CLI, dashboard or forecasting consumer is extended. No actual helper/source/hash/readiness execution is included in this handoff. The legacy public payload is explicitly a component-only view; it does not supersede the new typed Idaho observation.

## Failure, cancellation and partial publication

The wrapper catches parser/hash/persistence errors, KeyboardInterrupt and SystemExit after admission. Error payloads contain only a safe type/static message, never exception text or names. It manually controls one RunStore lifecycle to prevent automatic DONE on failed execution.

A failure before normal summary/ledger publication retains partial files and attempts a FAILED summary/ledger. If normal summary or ledger already exists, preserve it without overwrite, append a failure event (invalidating its earlier event hash), and retain separate `failure.json`, `terminal_failure.local.json` and `failure_checksums.local.json`. Typed consumers refuse all failure-marked parents; stale success ledgers also fail generic hash verification. Locks are released. Cancellations re-raise empty KeyboardInterrupt/SystemExit after attempted sealing.

Persistent filesystem unavailability can prevent even a failure artifact from being written. The wrapper still raises and never returns success, but cannot certify a durable failure seal. An authored persistent-write-error fixture checks this limit explicitly. No hostile-host, rollback, concurrent-file-replacement or independent immutable-store guarantee is claimed by same-host hashes. The wrapper's post-check seal governs cooperating consumers; original reference provenance remains separately reviewed evidence.

## Privacy and scope

Names appear only in two private `.local.json` payloads. Public assembly uses the frozen allowlisted Idaho diagnostics and legacy observation references. Fixtures assert no DEMO name leakage, default package refusal, unknown-schema denial, private-payload tamper refusal and symlink refusal. Existing package/privacy guards remain unchanged. The new consumer returns only the public envelope after local verification; it is not a new public HTTP endpoint or distribution permission. Actual named records and raw respondent/publisher/source bodies remain ignored and unbundled.

## Executed fixture evidence and reproduction

See `reports/E01_TYPED_READINESS_V1_9_IMPLEMENTATION_EVIDENCE.json` for exact final code/config/test pins, Python versions, before/after identity, command outputs and counts. Commands:

```
PYTHONPATH=src .venv/bin/python -m unittest tests.test_e01_typed_readiness_v1_9 -q
PYTHONPATH=src data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11 -m unittest tests.test_e01_typed_readiness_v1_9 -q
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e01*.py' -q
```

The v1.9 tests use temporary authored40-source files, authored reference payloads, patched fixture-only trust/import identities and stubbed pure component boundaries. Idaho primitive reconciliation uses authored DEMO HTML only. Thus these tests establish integration/lifecycle engineering, not actual40-source parsing. Existing separate E01 fixtures exercise prior parser components. Real integration stays NOT_RUN pending independent code review and explicit lead release.

Fixtures cover replay and complete legacy byte preservation; each of12 old-object mutations; Idaho legacy insertion; all four UNKNOWN boolean substitutions; ordinal boolean aliases; status/party/date/blank/role/collapsed-record mutations; schema/kind/state/count/context/filter mutations; all40-source caller coedits at attempts0/20/39/60/159 with unchanged trusted authority; source/code/reference/runtime/import/path drift; parse/cancel/SystemExit; before/after constructor, four-payload, payload-hash, commit, summary, checksum and terminal-seal write failures; event failures; post-finish source/wrapper drift; missing terminal seal during final recheck; resealed private/public/manifest/summary tampering; extra files; and persistent disk failure.

Two added test-harness errors (wrong authored run selected; tuple reverse attempted before execution) are preserved in `reports/E01_TYPED_READINESS_V1_9_DEVELOPMENT_FAILURE.json`. They were corrected; no actual-source failed run or scientific outcome is inferred.

## Remaining gates

Independent reviewer must validate exact implementation and fixture pins, privacy and lifecycle behavior. Only after that may the lead authorize an exact actual-source recorded run/replay; those require separate post-run source/content/result/privacy review before any status update or13/20 coverage promotion. Final ballots, latest amendments, nominee/legal interpretation, candidate IDs, geography, real selection and forecasting remain blocked independently. No GET/UI/OCR/model actions, credentials, paid execution or publication were used. Actual experimental cost is$0; local development compute/labor is unpriced.
