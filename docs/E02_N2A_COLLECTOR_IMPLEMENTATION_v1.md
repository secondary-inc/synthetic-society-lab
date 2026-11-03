# E02 N2a registry collector: authored implementation candidate

This separate candidate implements the methods accepted in `INDEPENDENT_AUDIT_E02_NEXT_DC_SOURCE_UNIT_V1_METHODS.json`. It is **not independently code accepted or released for a real GET**. Existing Wyoming source, receipts, native runtime, controls and approvals are unchanged. No real DC raw cache was accessed during development. Paid inference remains disabled, with zero model calls and zero experimental spend.

## Contract and admission

`n2a_collector_v1.py` supplies one reusable registry-driven single-source operation. The checked-in DC/FIPS11 configuration is disabled (`execution_authority: 0`; independent code review and finite lead release null). Production admission requires a matching independent authored-code review and a source-specific lead release bound to exact policy/code hashes, root, state, URL, limits and finite dates. Existing ordinary public Census research authorization is the owner-scope reference; this adds no new blanket human/key/daemon gate. Supplying a credential does not enable this collector or authorize spending.

One active source is selected from the pinned 51-jurisdiction metadata registry, excluding already acquired WY. DC is selected using the accepted minimum published person-row rule; compressed size, current availability, exact hash, archive layout and adults remain unknown. A different source uses the same collector with separate exact reviewed/released source metadata. The authored Alaska control demonstrates this reuse. There is no campaign loop, state import adapter or nationwide assembly here.

The production adapter uses verified TLS, identity encoding, one GET and bounded `read1` operations with a 30-second socket-operation timeout. HEAD, redirects, retries, Range, fallback, authentication and error-body consumption are absent. HTTP status, content type, final URL, encoding, length and bounded allowed headers are checked. Partial bytes are metered, including bytes returned by a read that overruns the deadline. Prefix hash, retained bytes and full conservative reservations survive errors. Unknown-length EOF below the cap can close; at exactly 8 MiB it refuses without an extra-byte probe. Exact known length at the cap can close without an extra probe. A receipt records application-body delivery, not TLS/wire overhead.

## Durable attempt and resource policy

Before dispatch, one full GET/8 MiB/180-second network/300-second metadata allowance is durably reserved. Permanent append-only semantic replay checks source identity, one attempt per state/URL, phase order, monotonic received/written counters and immutable completion receipt. Failed or interrupted attempts keep their full allowance. Retry refusal leaves the prior record unchanged. A real authored child death after durable dispatch intent leaves PENDING; explicit UNKNOWN preserves the charge and prevents retry. Torn state, absent original markers, residual raw/core roots and semantic resealing cannot silently initialize a fresh registry.

The first unit's 900-second clock begins at immutable registry creation; delaying preflight cannot restart it. Later sources retain the shared registry and original 10,800-second native batch horizon. Native limits are copied exactly from the accepted WY v1.1 specification. New reservations conservatively accumulate against native request/body/unique-source/network/processing caps. Full time reservations are not refunded even on success; the current processing allowance alone would stop a future sequence after twelve 300-second reservations. This candidate makes no nationwide-throughput claim and does not implement a reservation-reconciliation or policy migration scheme.

Recorded history retains the prior WY person GET, five metadata requests, 1,279,577 metadata bytes and 4,202,266 retained WY archive bytes. The prior 8 MiB body allowance is a conservative bound, not a claim of actual earlier delivery or a refund. Prior work is not reexecuted or reread to reconstruct these figures.

All collector-owned files are measured across persistent registry, core and raw roots, including unexpected files, hardlinks and temporary-write projections. Limits are raw 8 MiB, core 4 MiB, scratch 1 MiB and total 13 MiB. Native free-space/initial headroom and aggregate raw limits also apply. These fixed shared roots may stop future source additions conservatively; no new per-source root can reset them. The archive is created exclusively with full lexical no-follow ancestry, rehashed and checked against the original descriptor and ancestry after inspection, then promoted by same-directory rename. Promotion binds the original device/inode/size/mtime and fresh final identity; directory timestamps alone are not source identity.

Clocks, RSS and cancellation are sampled cooperatively between bounded operations. The 0.1-second sampling target is not a hard interruption guarantee during a socket operation, decompression or fsync. Parent death or unavailable evidence is an unknown shutdown, not proof of resource-stop success. Local hashes and journals assume preserved trusted history; coordinated replacement of the whole trusted store is outside this scope.

## Metadata boundary

Expected member names are planned names from the existing product convention, not observed DC facts: `psam_p11.csv` and `ACS2020_2024_PUMS_README.pdf`. Exact closed membership, safe paths, compression/encryption/type flags, declared expansion caps and archive identity are checked. The person member is inflated only through the first newline under the 64 KiB header limit: exactly 285 unique fields and all 91 required fields. The bounded companion is hashed and CRC checked as bytes; no PDF execution/rendering occurs. Full compressed archive bytes are rehashed.

No person row is parsed, full-person CRC scan performed, person hash calculated, observed person count asserted, STATE content validated or import admitted. A deliberately altered person payload can pass metadata inspection while remaining explicitly unadmitted. Header equality with the historical WY reference is recorded rather than silently rewriting schema. First archive hash is legitimately unknown before acquisition and bound immutably afterward. Any actual import requires its separate N2b design, adapter, row/universe validation, matched controls and independent release. No fitting, disclosure, dashboard adoption or scientific inference follows N2a.

## Reproduction and evidence

Run from repository root with supported Python 3.11 or 3.12:

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_e02_n2a_collector_v1 -v
PYTHONPATH=src:tests data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11 -m unittest tests.test_e02_n2a_collector_v1 -v
```

The second runtime is machine-local; another supported Python 3.11 executable can replace it. No production source, credentials or network is needed by the authored suite. The transport-only adapter test mocks its HTTPS opener. The tests cover positive DC/AK metadata closure, partial/error/redirect/encoding/truncation, exact cap and cap+1, time, cancellation, crash, concurrency, semantic history, pins, path/identity and whole-owned storage. Fixture passing is implementer evidence, not independent milestone certification.

To retain another authored control bundle, choose a **new nonexistent** output root; the helper refuses overwrite:

```sh
PYTHONPATH=src:tests .venv/bin/python -c 'from pathlib import Path; from test_e02_n2a_collector_v1 import retain_authored_evidence; print(retain_authored_evidence(Path("data/processed/e02_F_local_fixture/n2a-review-reproduction")))'
```

The final retained bundle `data/processed/e02_F_local_fixture/n2a-collector-v1-20261103-02/` has authored payloads, HTTP scripts, full controls, success/partial receipts, PENDING/UNKNOWN crash history, retry-zero-call oracles and a hash index. Copied repo metadata, fake payload copies and oracles are explicitly fixture-generation overhead outside collector-owned roots. An earlier `-01` bundle is preserved with its older candidate pins and is not final evidence. No bundle contains real respondent or publisher data.

Original ZIP-spy harness failure and both clock-harness failures remain in `reports/E02_N2A_COLLECTOR_*FAILURE*`. The spy originally counted ZIP fixture creation, so the fix builds bytes before observation. The clock harness originally restored real time before reopening future-clock controls; assertions now remain inside the simulated clock, preserving rollback refusal. Interim 37-test pre-pin logs remain separate from final tests. The handoff pins exact final artifacts and test logs; independent code review must precede any real GET, actual-source metadata inspection or later import.
