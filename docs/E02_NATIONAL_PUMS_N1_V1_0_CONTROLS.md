# N1 national PUMS controls: authored fixtures only

Status: READY FOR INDEPENDENT CODE/CONTROL/FIXTURE REVIEW, not independent acceptance. N0 is separately accepted in `reports/INDEPENDENT_AUDIT_E02_NATIONAL_PUMS_N0_FREEZE.json`. N1 adds only new E02 files; original Wyoming modules, consumed controls, shared common.py and all actual runs remain unchanged. No national source was fetched, enrolled, parsed or fitted.

## Executable boundary and ownership

`configs/e02_national_controls_v1.json` pins the accepted source/methods proposal, public metadata, original helpers and new implementation/tests. Default `authored_fixture=false`, actual approval null, person GET authority0 and budget$0. `load_controls` rehashes exact required files and retained metadata and checks the public51-source registry against the frozen proposal. `actual_dispatch` always refuses before transport; no network adapter exists. A nonfixture Ledger refuses before creating files. No actual acquisition/enrollment path can be enabled by supplying a key or mock certificate; a new reviewed N2 implementation/config would be required.

Owned modules: `national_budget.py` (locked ledger, reservations, storage, authored response) and `national_population.py` (metered fixture enrollment/parse/union and parent supervision). `tests/test_e02_national_controls.py` uses temporary paths and authored CSV/ZIP bytes only. Mock source-review/continuation dictionaries deliberately exercise guards; they are not independent milestone certificates or actual-source permissions. This is trusted-code engineering, not an adversarial authentication or OS sandbox boundary.

## Durable body and processing accounting

The immutable-design batch uses a nonblocking POSIX file lock, fsynced events and atomic ledger snapshots. Each event generation must match state. An event/state torn transition blocks rather than rolling usage back. Corrupt event tails, clock rollback, expired batch, modified design, concurrent ownership and source retries refuse. Successive instances reopen the same counters and creation time; no reset API exists.

Reserve the full per-attempt application-BODY/time allowance before any fake response read. Before each bounded read persist inflight size, then receipt the returned/partial bytes. Release unused allowance only with durable EOF, closed response and matching retained-body size/hash. Empty, truncated, encoded, overlong, cancelled, crash/unknown or failed attempts retain their full reservation and halt. An exhausted allowance refuses an extra EOF probe, so a body exactly equal to its cap conservatively fails. An observable nonconforming delivery is recorded as overrun and stops; the implementation does not claim an absolute wire cap.

An explicit authored continuation requires separate exact-ledger/design review fields; it can unhalt only reconciled state and never changes historical counters, start time, attempted sources or retry prohibition. Unknown/torn state cannot be silently reconciled. An actual continuation approval is not implemented.

Enrollment reserves bounded header/companion delivered bytes and elapsed time before a supervised child inspects its synthetic source. Exact URL/FIPS/release/metadata, independent-fixture manifest binding, literal members, size/hash/header, no path/symlink/encryption/casefold duplicates, companion bounds and file identity are checked. Unknown actual first hashes/manifests remain unknown. New source files must stay in the metered batch directory; only an exact already-known Wyoming cache identity can be referenced externally. No actual Wyoming cache is touched by fixtures.

Register each source once for unique compressed-byte accounting. Primary and replay process a source once each under distinct keys. Reserve known enrolled CSV plus pre/post header/companion expansion, exact expected rows and full processing time before supervised parsing; failures consume reserved resources. Per-sweep and two-sweep cumulative bounds persist. CSV bytes/physical lines/rows and all required domains are validated before mutually exclusive exclusions. Full member hash/count and postparse archive/member/file identity must match the frozen enrollment before committing a state result hash.

A union requires51 distinct states and committed result hashes from its own sweep, rejects changed/repeated/missing/mixed-release inputs and reserves union time. Atomic local artifacts plus the committed hash remain MOCK/local/pending audit. A crash during persistence blocks rather than authorizing a completed benchmark from an orphan file.

## Population math and resource channels

The parser reuses the unchanged reviewed `_row` and `_uncertainty` arithmetic helpers; its controls copy binds each row to its expected state. It preserves allocations, squared point weights, signed80replicates and identical exclusions, without a second divide by five. The joint612-cell union adds corresponding replicate indices before national/region totals and ratio uncertainty. Zero/nonpositive denominators block ratio intervals; zero estimates/SEs retain review flags. Covariance is computed on matched replicate deviations, with no state-independence assumption. No identifier or unused source column is emitted.

The parent supervises enrollment, state parsing and final union through POSIX fork/process groups, elapsed checks and sampled `ps` RSS. Cancellation/time/RSS/unknown-child failures terminate the group and retain full ledger charges. This requires POSIX `fcntl`, fork, setsid and ps; Windows support is not claimed. Sampling and subprocess/I/O latency allow overshoot, so memory/time are not absolute hard OS limits.

Storage checks count logical file bytes in the owned batch directory, separately bound JSON/log growth, check actual free disk and initial headroom, and refuse projected body/union writes. They do not meter physical allocated-block/directory overhead exactly; actual free-space reserve is the backstop. Application-delivered HTTP BODY excludes headers, framing, TLS and hidden transport buffers. ZIP expansion meters delivered CSV/header/companion bytes and declared member sizes, not unobservable library read-ahead/decompression work; parent RSS/time limits address a separate channel. No stronger channel guarantee is asserted. There is no full CSV extraction or raw row/identifier log. Actual transport/socket controls and real-source envelope verification remain separate N2 review work.

## Executed fixtures and evidence

`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -q` passes70tests, including14 new N1 cases. They cover:

- Pre-transport actual refusal; durable success/closure/reconciliation and immutable restart/design/source ownership.
- Partial-body errors, cancellation, encoding, storage failure, overdelivery, empty/truncated/declared/exact-cap bodies; failures retain full charge.
- Real forked crashes after reservation, after delivery before receipt, before commit, and during event-to-ledger atomic commit; unknown/torn state does not reset.
- A real two-process reservation race with exactly one winner; quota, lock, corruption, clock, expiry, initial disk/log and per-sweep failures.
- Strict source/member/release/header/count/domain/source-drift guards, including required-domain failure before a noncitizen exclusion.
-51 authored source partitions, signed weights and an independent two-state covariance example: joint variance64 versus summed individual variance32, cross covariance16. Exact union replay and checkpoint-tamper refusal.
- Parent cancellation, real elapsed/RSS stops and abrupt child exit; metered enrollment/primary/replay/union quotas and continuation without refund/retry.

Recorded current MOCK run `e02-ae0e2ceb885d4fd4864e2ef6386beff5` covers51 authored states,50 fake HTTP responses and51 authored person rows per sweep. Socket connection APIs were denied. Primary/replay bytes match SHA `e20577e2833e1542ce1386cb57b580edb20719045fc94df92b09c0d040790c07`. It records102 charged mock processing rows,58,550 mock body bytes,281,520 delivered expanded fixture bytes and sampled child RSS in ignored artifacts. These are toy engineering facts, not nationwide demographic data or scientific effects. Earlier development MOCK run `e02-38f0a99cc1264bd393a09558bf2b50b3` is preserved as a superseded prototype; current evidence uses final pins only.

The demonstration script is ignored at `data/processed/e02_national_n1_authored_pilot_v1.py`; its hash is in the run manifest. It uses the authored fixture helpers and a copied fixture config, never the real registry counts as synthetic observations. Reproduction should run fixture tests; no actual source action follows. Evidence and full worker contract are `reports/E02_NATIONAL_PUMS_N1_EVIDENCE.json` and `reports/E02_NATIONAL_PUMS_N1_WORKER_RECEIPT.md`.

## Acceptance criteria and remaining gates

Independent N1 reviewer must rerun source/budget/resource/lifecycle/math fixtures, inspect exact config/code/test hashes and audit the MOCK ledger and artifacts. No worker self-certification. N1 acceptance does not create a real adapter, approve first source enrollment, certify all physical quotas or authorize person GETs. Any future actual transport and first-response enrollment require fresh reviewed controls/config and exact-source approval before parsing. All real612-cell/replicate outputs remain local pending separate disclosure review. Broader original adult/state scope, ANES model amendment, held-out matched comparators, scientific validity, paid inference and publication stay blocked.
