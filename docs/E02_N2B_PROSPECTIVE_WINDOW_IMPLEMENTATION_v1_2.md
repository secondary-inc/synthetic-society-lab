# E02 N2b v1.2 prospective elapsed-window candidate

**New candidate only; no actual preflight/release/import authority.** This implements the exact elapsed-window methods reviewed in `INDEPENDENT_AUDIT_E02_N2B_PROSPECTIVE_WINDOW_METHODS_V1.json` (SHA `c20910bf8fc93d78ff10312ca9a7580951f33c503ea25f681edcf83702ecaaca`), proposal config SHA `512afa5fcb5b6bb27a81e4dcce8b010d2dd24248e5364e6d4d9afa49c1128594` and document SHA `c1eb537dc81f921c25e06670e6cab0ea6bc50e68d69ecdddeb41ec9379bb38f4`.

The exact v1.1.1 component has independent offline acceptance `cb55fd4382f25cc58f0de1488dd53ad113c0d96a4d578357096787423f156785`. Its parts, assembly/arithmetic, prior storage and scoped metrics are reused unchanged with exact dependency pins. New versioned admission/Context, control, source wrapper and runner identities bind the prospective contract; separate window validation and a TEST_ONLY reader complete the new module set. No predecessor module/config/test/handoff/log/evidence is edited or resealed. Earlier blocked versions stay historical. Prospective here means a dated resource window, not an E01 prospective forecast.

## Default and exact authority

`configs/e02_n2b_prospective_window_v1_2.json` has authority0, live code/source/execution refs null, prospective grant null, all effective/expiry UTC/Unix fields null, source manifest null and saved parts null. `run_actual()` defaults to refusal before source/owner work. No actual identities or window dates were filled. A new Context type/session cannot reuse an old component release. The contract is `E02_N2B_PROSPECTIVE_EXECUTOR_V1_2`; the code-review and execution status identities are distinct from the predecessor.

Conditional admission requires matching policy/code/spec/accepted-component/window-methods pins, a particular read-only source/history/absence/storage preflight record and a distinct finite execution release. The preflight binds exact source/saved parts, old full history hash, fixed paths, observed clock and finite validity, asserted marker absence and its storage-review hash. This candidate defines required bindings; it has not implemented or performed that actual preflight. Actual manifest/descriptors/current identities/old anchors/whole capacity remain unknown until a separately finite authorized reader and independent review establish them.

The prospective grant is a closed built-in JSON record with exact kind/realm/lead role/nonce, issued wall+monotonic+boot stamp, effective/expiry UTC and Unix, methods-review/policy/source/history/capacity/preflight hashes and fixed root. Effective equals the issued wall observation; expiry is exactly effective+10,800seconds. Canonical UTC strings must match those Unix values at the documented microsecond ISO rendering. Finite types reject booleans, NaN/Inf, invalid dates, wrong boot/clock, wrong fields/kind/hash/caps/root and stale/future-effective dates. Preflight observation cannot be after grant issuance. All of this remains under the declared trusted local reviewer/writer/history boundary, not cryptographic lead authentication or hostile-host containment.

## Time, history and no native allowance increase

Only new-job elapsed admission replaces both inherited deadline minima. Original WY deadline1793741015.473082 and N2a deadline1793746220.467812 remain immutable historical contracts, with original genesis/terminal provenance and all charges unchanged. Frozen predecessors still refuse the expired original window.

A first sequence needs effective<=start<=expiry−1500. The last admissible grant-relative start offset is9300;9301 refuses. Its immutable job deadline is min(start+1500, new expiry), and each stage retains300seconds. Pauses count. Issued and job clocks validate wall/monotonic continuity and the current bootstrap identity; backward, unavailable, discontinuous or changed-boot clocks refuse. No timing is restarted at a reopened reader or process.

Genesis, the owner marker and stage proofs retain the grant hash/session, original histories and a separately recorded prospective chronology: old WY/DC genesis/deadlines, new issued/effective/expiry UTC/Unix, added10,800elapsed seconds, max(0,effective−oldWYdeadline) historical gap, expiry−oldWYdeadline extension, max(0,expiry−oldDCdeadline) positive DC extension, cumulative wall elapsed from original WY genesis and observed new sequence elapsed. Old boot/monotonic data are provenance; wall elapsed from old history is not misrepresented as a cross-boot monotonic measurement.

Native processing remains1,800old WY+300old DC metadata+1,500new=3,600seconds. New rows65,010, expanded bytes134,724,553 and logical ops24M are unchanged. Full original metadata expansion6,356,992 remains charged, not replaced by observed101,365. All source/request, storage/root/subpartition/free/RSS, query, scope, private-output and scientific rules remain unchanged. Added elapsed capacity cannot finance additional processing, GETs, source sweeps or49remaining jurisdictions.

## Strict first use and live-session continuity

The original production output and owner paths stay `data/processed/e02_n2b_private_v1` and `data/processed/e02_n2b_registry_v1`. Any existing marker/output—including empty, orphan, failed or unknown history—blocks new first use; no alternate path or automatic continuation is introduced. Owner-directory claim is exclusive, then an immutable owner record holds the grant/design/session/original t0/full job reservations before any source work. Partial bootstrap remains occupied rather than reset.

A newly admitted Context receives an ephemeral original-session capability. Only the session that created that exact owner can open its live control. A fresh context or lost process/session cannot reconstruct an old writer from saved grant/config bytes; it needs a separately reviewed state-bound continuation. Within the original live session, semantic replay/snapshots/unknown bookkeeping remain possible only while authority and clocks remain valid. After expiry, failure bookkeeping may itself refuse; retained RESERVED history means unknown shutdown with full allowances, not successful cleanup. No new grant refreshes an existing job.

The source wrapper uses the new admission/control type and per-use binding checks. Two DC person sweeps, first PRIMARY digest pinned for REPLAY, zero new WY person sweeps and zero GETs remain. Pure accepted storage/parts/assembly/metrics are not monkeypatched to bypass predecessor admission.

## Read-only boundary

`readonly_preflight_actual()` is intentionally a default-denied placeholder: it raises before any filesystem, source or controller operation, even if passed arguments. It is not an actual preflight implementation or grant. No old `Control`, `snapshot` or writer is constructed to read actual history.

`n2b_fixture_reader_v1_2.read_state()` accepts only a registered isolated TEST_ONLY realm with its own authored marker and new TEST_ONLY schema. It reads retained state bytes without constructing any old/new Control or writing a lock. It is a fixture inspection helper, not an actual reader or independent semantic certification. Production realms refuse before filesystem access. Normal postrun independent audits can inspect separately authorized saved bytes; actual-reader implementation/release remains a later gate.

## Tests and retained authored proof

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_e02_n2b_prospective_v1_2 -v
PYTHONPATH=src:tests data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11 -m unittest tests.test_e02_n2b_prospective_v1_2 -v
```

Python3.11's path is machine-local. The suite retains the64 prior arithmetic/control/root/resource methods under the new contract; the predecessor-window-fit case now checks the prospective limit, and separate isolated predecessor tests verify old code still rejects expired original deadlines. Additional cases cover closed grants/types/hashes/caps/UTC,−1/0/9300/9301/expiry offsets, new job after both old deadlines, boot/clock failures, old-release reuse, fresh-context restart, lost session, expiry/pauses, marker drift, default-denied actual reader and lost acknowledgement. Job/issued clocks and approvals are authored; they do not establish current actual feasibility. Comparator perf/RSS remain scoped real observations of development execution, with the accepted nonexclusive/cache/cooperative limitations.

Initial handoff validation caught a TEST_ONLY helper routing error: three planned window cases were incorrectly routed to a missing-directory refusal. The first bundle, original validation error and passing79-test logs remain preserved as nonfinal evidence. A focused scenario-helper regression was added; the corrected final bundle is pinned in the handoff. Ten cases include the seven accepted-component regression scenarios plus null-grant early refusal, existing-marker/fresh-session refusal and lease expiry with retained RESERVED/unknown/full charges. The successful MOCK case uses a simulated effective1793750000, after both inherited deadlines, and records its explicit added-window/gap/extension provenance. This is not an issued actual date.

To reproduce, use a new nonexistent isolated root:

```sh
PYTHONPATH=src:tests .venv/bin/python -c 'from pathlib import Path; from test_e02_n2b_prospective_v1_2 import retain_authored_evidence; print(retain_authored_evidence(Path("data/processed/e02_F_local_fixture/n2b-prospective-review-reproduction")))'
```

Fixture generation creates equivalent-production-relative historical directories and fake ZIP/parts/clock/review/grant records; all such input/copy overhead is outside new-owned stage partitions and explicitly labeled TEST_ONLY. No actual raw/private/control/part stat/read/hash, key/.env/environment inspection, network, model, actual import or fit occurred. Own-process OS/runtime resource observation is separate from credential/environment-variable inspection.

## Remaining gates

Independent exact v1.2 code/clock/boot/history/cap/session/arithmetic/privacy/retained-fixture review comes next. Then the actual finite read-only reader/preflight must be separately implemented/reviewed/released; current marker absence, entire storage, source identity, old anchors and WY part bindings must be established. Only afterward may the lead issue a genuine dated grant and one exact execution release. None is present now. No actual fit/disclosure/dashboard/publication/national/human-validity gate advances, and the original national campaign remains49jurisdictions short with no added capacity authorization.
