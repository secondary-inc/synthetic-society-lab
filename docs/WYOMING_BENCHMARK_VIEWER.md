# Recorded Wyoming benchmark viewer extension

This local owner-review extension consumes only the two exact finalized runs admitted by `reports/INDEPENDENT_AUDIT_WYOMING_FINALIZATION_ADMISSION.json`. The receipt's bytes are pinned in `src/civiclab/benchmark_viewer.py`. Updating a receipt is an explicit reviewed code change, never an automatic latest-PASS lookup. Workflow role labels are not cryptographic auditor identity.

`civiclab dashboard` uses the extension while the original `dashboard.py`, common runtime and base HTML remain unchanged. A static script fragment composes at one checked anchor in the existing template; zero or multiple anchors fail before output. Existing comparative research views remain available. A root without the admission receipt retains its generic base viewer, without typed benchmark cells. An altered receipt/schema or an otherwise valid resealed run with a different admitted ledger fails closed. Invalid/incomplete runs remain rejected under the original viewer's checks.

For an admitted run, the extension verifies the receipt role/scope, run ledger, finalized payload bytes, canonical payload, closed schema, exact finalization trace and approval/config/schema bindings. It verifies the ledger/payload/trace and receipt/schema again after reading. Only the accepted finalized `demographic-benchmark.json` is read for typed cells; source aggregates and `.local` projections never supply them. Original failed/local runs remain unchanged. This is local filesystem integrity checking under trusted application execution, not a hostile-host or atomic multi-file publication guarantee.

The table shows all twelve fixed age/education cells, unweighted contributors, person-weighted count estimates, shares and design-based 90% sampling margins. Shares and share margins use fractions, not percentage points. Display rounding is four decimals; the exact stored values remain in `snapshot.json`. Source year/universe, source digests, resource-measurement limitations and the separate independent admission are visible. The recorded run's original pending status is retained and explained alongside its later exact-payload admission.

The universe is Wyoming household citizens aged 18+ in 2020–2024 ACS PUMS. It excludes other populations and is neither a nationwide population fit nor evidence of political-response validity. Sampling error does not include transport, selection or model validity. The broader adult/state science requirement remains blocked. Owner review does not authorize external publication.

## Acceptance and reproduction

Run `.venv/bin/python -m unittest tests.test_benchmark_viewer tests.test_dashboard -v` for authored-only fixture checks: missing admission/private-only inputs; exact admitted rendering; changed receipt/schema; resealed payload/trace; source drift during validation; script injection and traversal. Fixtures never contain actual respondent rows or Census aggregate cells.

Build with `.venv/bin/civiclab dashboard --out data/processed/wyoming-owner-viewer --run e02-775f7460965047e0999ddb81083fee6b --run e02-b99863e7664f4af19386526bd5f438ef --run e02-1be3718699e54d7380755be1f9d87e6d`. Serve with `.venv/bin/civiclab serve --directory data/processed/wyoming-owner-viewer --port 8767`. The existing server binds only to loopback and serves only index/snapshot; no API or inference occurs.

Milestone acceptance requires independent code/admission/privacy review, actual table and replay/comparison browser inspection, HTTP path guards and a fresh isolated restore of a new source archive. The earlier stage3 archive remains immutable and does not contain this extension. No broader milestone is self-certified by this runbook.
