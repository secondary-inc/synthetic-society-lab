# Clerk M2 v1.1 authored component candidate

Prepared November 4, 2026. **AUTHORED MOCK COMPONENTS; independent implementation review pending. Actual M2 disabled.** This is a separate candidate under the accepted v1.1 methods, not implementation acceptance of the entire methods protocol.

Accepted specification: `configs/e01_clerk2020_m2_inspection_design_v1_1.json`, SHA-256 `7e87d6844ca5bec346af91359d38a9c7a612503962d13b4749fd93d3811fb0e6`; independent methods-only audit `reports/INDEPENDENT_AUDIT_E01_CLERK2020_M2_DESIGN_V1_1_METHODS.json`, SHA-256 `c4d0539514dda630926661f5f0492c0807d629f7dbeeb1e77a2e3e5c04d5d075`. The original v1 design, finding and all 17 M1 pins remain unchanged. No M1 toggle is added.

## Implemented component boundary

- `src/civiclab/e01/clerk2020_m2_v1_1_contracts.py`: bounded canonical bytes, strict canonical JSON decoding, safe refusal, integer and path predicates, immutable counter axes, atomic 15-axis transitions, downstream run-ID derivation, declared graph cycle detection, and authored sampled-resource validation. Actual factory always refuses.
- `src/civiclab/e01/clerk2020_m2_v1_1_control.py`: exact methods-policy hash loading; closed field/type checks with exact external bindings required for opaque predicates; CounterAxis/CounterState semantics; a trusted in-memory MOCK registrar with fixed namespace, source-set/hash uniqueness, one-shot issuance/consumption and anchor CAS; authored memory TCB reads after reservations; one-shot MOCK bootstrap; bounded immutable byte slots; a MOCK finalizer that charges terminal reads/writes first, freezes the checksummed payloads and normal prefix, then creates seal/VERIFY/ACK/tail/completed anchor. Lost ACK/caller delivery stays unknown without a rerun or refund.
- `src/civiclab/e01/clerk2020_m2_v1_1_backend.py`: deliberately fake-PDF containers, exact authored 81/38-page checks, unsupported-feature refusals in the fake format, fixed positional UTF-8 snippets with actual serialized clipping/coverage/hash accounting, public diagnostics without snippet content, one-shot authored source/backend/page reservations and immutable memory snapshots. The actual backend always refuses.
- `tests/test_clerk2020_m2_v1_1.py`: 64 authored tests, including threaded registrar races, counter conservation/unknown accounting, exact shapes and graph checks, policy/source pin preservation, privacy/caps/UTF-8 tests, resource sample refusals, simulated bootstrap/source failures, and all 45 reached terminal crash points.

These components perform no network, credential/environment lookup, actual PDF access, runtime inspection/import/probe or model inference. The fake-PDF container is not a valid PDF and is never passed to pypdf. The TCB and persistence model operate on authored memory snapshots; no filesystem registrar, native launcher or pypdf worker is shipped.

## Reproduce the authored evidence

From the repository root, these commands execute only existing interpreters and authored components. No installation is needed. The optional output must be a new absolute `reports/clerk2020_m2_v1_1_*` path; omission writes only a test summary. Retained evidence uses create-once output files.

```bash
.venv/bin/python reports/clerk2020_m2_v1_1_guarded_fixture_recipe.py
data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11 reports/clerk2020_m2_v1_1_guarded_fixture_recipe.py
```

The guarded recipe denies repository `data/raw` and `data/processed` open/enumeration and socket audit events, except the executing known interpreter's stdlib beneath `sys.base_prefix`. It does not claim a hostile-host sandbox, OS-wide stat interception or runtime identity acceptance. Components contain no actual source path I/O. The test suite also runs the complete authored inspection/finalization path with file open and socket construction patched to refuse.

Final retained evidence:

- `reports/clerk2020_m2_v1_1_authored_fixture_final_312.json` and `reports/clerk2020_m2_v1_1_final_guarded_with_provenance_312.txt`: 64 tests pass using observed Python 3.12.14.
- `reports/clerk2020_m2_v1_1_authored_fixture_final_311.json` and `reports/clerk2020_m2_v1_1_final_guarded_with_provenance_311.txt`: 64 tests pass using observed Python 3.11.17.

Both retain the same 19 authored artifacts (112596 bytes total), a 1132-byte frozen journal prefix, and outer fixture ID `e01-f3182a1ef6c0ca37a97a10d14bdc74ce`. The outer evidence ID binds the current component/test/recipe hashes, authored input hashes and seed 0. It is not an actual admitted source run or a claim that all methods authority records exist. Independent authored fixture objects reproduce byte-identical artifacts across both runtimes; this does not authorize replay of a consumed actual source job. Serving provider, actual billing and actual runtime admission remain null; experimental spend is $0 and development compute is unpriced.

The initial run had 55 tests with four errors caused by incorrectly treating the pinned pretty-printed methods document as a canonical protocol record. The failed source and log are preserved in `reports/clerk2020_m2_v1_1_initial_source.json` and `reports/clerk2020_m2_v1_1_initial_tests.txt`. The remedy parses only that exact hash-pinned document separately; strict protocol record decoding remains unchanged. Subsequent candidate logs and earlier successful evidence are retained as intermediate observations, not substituted for the final exact source closure.

## Acceptance criteria and limits

Component acceptance requires a separate reviewer to rerun the guarded tests, rederive the retained hashes/counters/coverage/tail links and examine adversarial failures. No worker self-certification or full-M2 milestone closure is claimed.

The following remain **NOT IMPLEMENTED / NOT RUN**, and actual execution must remain blocked:

- Real filesystem create-once registration, one-shot slots, protected anchor persistence, fsync/rename/CAS, native process death and post-persist EIO behavior. The tests model these states in memory; they do not prove physical durability or recoverability.
- Full BOOT/EXEC authority graph construction, semantic verification of every linked registration/spec/decision/envelope/genesis/receipt/context, continuation/ceiling-extension admission and record-level counter reconstruction. `ClosedRecords` enforces shape and supplied exact opaque bindings; caller-supplied bindings alone cannot establish authority. The mock registrar and mock bootstrap records are visibly authored harness records, not accepted real authority schemas.
- Reviewed minimal bootstrap TCB, fixed real runtime/code/wheel/origin manifest and immutability admission, actual clock/RSS/CPU supervision, loader/lazy-import/filesystem/network confinement. Sample validation cannot observe peaks between samples or prove hard resource containment.
- The exact proposed pypdf API and structure/warning/encryption behavior on genuine generated PDFs, decompression/cyclic-object/native resource fixtures, and actual source inspection. Unsupported flags are fake-format tests only. No library/backend/source-format acceptance follows.
- A complete native M2 recorder/launcher integrating those authorities and counters, all 13 normal event kinds and the 48-event schedule, VERIFY_FAILED/optional INVALIDATE/failure-sidecar recovery, bounded separately approved read-only resolution, and all native crash boundaries. The finite mock finalizer exercises the normal success tail and preserves failure as unknown; it is not a complete recovery service.

No real candidate, vote, ballot, geography, class, stage, date, party, as-of or forecast input is parsed/adopted. Private projection windows can miss relevant source text. M3–M6, the full race sample, E01 evaluation and scientific claims are unchanged. Actual factory and backend refusal have no enabling flag. Existing-source access, runtime inspection and any finite BOOT/EXEC must await their exact code/runtime/particular reviews and explicit grants. This track does not gate E02's separately reviewed limited exploratory pilot.

Next action: lead assigns independent review of this exact authored component candidate and its retained fake evidence, then scopes the missing native/authored integration separately under the accepted methods. Lead owns shared coordination/status/Git; this worker edited none of those files.
