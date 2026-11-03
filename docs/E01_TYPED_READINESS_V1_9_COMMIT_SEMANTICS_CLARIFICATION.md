# E01 v1.9 final-seal commit and uncertain caller acknowledgment

Status: separate clarification candidate pending independent review. The original code, config, tests, documentation, evidence and receipt remain frozen. No production change or actual-source release is proposed.

## Correction to the earlier claim

The original implementation evidence's limitation says: “Persistent filesystem failure can prevent durable failure sealing; no success is returned or admitted.” The final phrase is too broad. A caller exception does not prove that a final seal was never committed, and a read-only filesystem cannot be assumed to accept a later failure marker.

A precise counterexample is now covered by a separate authored fixture: the `typed_release.json` write persists the complete valid final seal, then raises OSError to the caller. All later failure-record writes fail with modeled EROFS. `run_readiness` raises, while `read_verified_public` accepts the complete intact committed artifacts. This is acknowledgment ambiguity after complete publication, not admission of an incomplete or corrupt payload. The original overbroad claim is withdrawn for this terminal boundary; its files are preserved as historical evidence.

## Commit, acknowledgment and review

The persisted final seal is the local commit record. It follows validated complete payloads, their hashes, normal parent ledger, all final source/reference/code rechecks and wrapper stability checks. Its contents bind the parent checksum ledger, wrapper and admitted configuration. Normal caller return is a separate acknowledgment; it can fail after that record is present.

Before a valid final seal exists, the strict typed consumer refuses the run even if the normal parent ledger exists. After a valid seal exists, an exception or lost acknowledgment alone does not make all complete retained bytes invalid. The consumer still requires the exact admitted file set, complete hash checks, summary/manifest/config bindings, exact legacy payload identities, Idaho identity, public schema and absence of failure markers. Missing/invalid/resealed-incompatible artifacts remain refused.

Existing behavior when later writes remain available is also preserved: an exception after seal publication can append failure evidence, invalidate the normal event-ledger hash and create explicit failure markers. Ordinary consumer admission then refuses the run, while original successful summary/seal/payload bytes remain for review. This clarification does not bypass those markers or rewrite the wrapper's failure policy. The independent reviewer must distinguish an intact sealed run with uncertain caller acknowledgment from a run with later invalidating evidence.

Do not automatically retry, create a replacement parent, resume or delete artifacts merely because the caller raised. First preserve the original run and inspect its exact files read-only. A reviewer separate from the implementation may resolve the completed sealed artifact under the existing admission rules. Missing evidence or ambiguity remains unresolved; an exception is neither an automatic success nor an automatic proof of no commit. No always-writable tombstone, remote witness, rollback prevention or hostile-host control is invented.

Here “persisted”/“commit” describes the observed saved-file boundary in the current local artifact protocol. The new tests do not prove survival of power loss, filesystem remount behavior, OS storage durability, directory-fsync guarantees or hostile concurrent mutation. The final seal and same-host hashes provide no independent timestamp, owner authentication or irreversible external commitment.

## Separate regression fixtures

`tests/test_e01_typed_readiness_v1_9_commit_semantics.py` adds three scenarios without editing the frozen18-test candidate:

1. Persist the final seal, inject EIO before acknowledgment, then model read-only storage by rejecting both RunStore persistence boundaries (`write` and `event`) with EROFS. Assert caller raises; no later failure marker can be persisted; all committed file bytes are unchanged; strict read-only validation accepts the valid complete run; no second parent or retry appears; adoption/forecast/coverage-promotion flags remain false and final ballots remain zero.
2. Persist the normal checksum ledger, inject the same uncertain acknowledgment before any final seal, then reject later writes. Assert the consumer refuses because no final commit seal exists. A normal ledger alone is insufficient.
3. Persist the final seal, inject EIO with later writes still available. Assert explicit failure records invalidate ordinary consumer admission, while original summary/seal bytes remain unchanged as review evidence.

Both persistence boundaries are guarded so every later failure-record write would be rejected in the read-only scenarios; the current wrapper stops its sealing attempt when the first such write fails. This is deterministic filesystem-error injection, not an actual read-only mount or operating-system permission test. The wrapper's source files and original test outcomes are unchanged.

The tests reuse the existing temporary authored40-source/reference fixture and stubbed component boundaries. All actual source PDFs, cached renders, private actual reference bodies and helpers remain untouched. See `reports/E01_TYPED_READINESS_V1_9_COMMIT_SEMANTICS_EVIDENCE.json` for exact pins, supported-runtime commands, final test counts and frozen-file checks.

## Gates remain unchanged

Independent review must decide whether this corrected commit/acknowledgment semantics resolves the claim finding for the exact frozen code plus separate clarification. There is no self-issued PASS, runtime release, actual readiness run/replay, coverage adoption, source-policy, legal/final-ballot or scientific completion. Current accepted coverage remains **12 document states / 21 unfinished jobs / zero final ballots**. No GET/UI/OCR/model actions or experimental spend occurred. The separate Alabama methods proposal is unchanged and grants no source access.
