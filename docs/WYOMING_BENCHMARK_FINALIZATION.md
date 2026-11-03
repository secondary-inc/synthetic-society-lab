# Separately recorded owner-review benchmark

The exact local projection has independent value/schema/disclosure acceptance in `INDEPENDENT_AUDIT_WYOMING_PROJECTION_OUTPUT_DISCLOSURE.json`. That receipt accepts the fixed payload for owner review and grants no public release. Original local projection runs, full PUMS aggregate and their ledgers remain unchanged.

`civiclab.reviewed_benchmark` creates a **new** RunStore rather than renaming a local file or dropping a private artifact from its ledger. Metadata admission verifies exact accepted source run/ledger/payload/canonical identities and the independent output audit/schema. A separate code/fixture execution approval is also mandatory. `configs/wyoming_benchmark_review_v1.json` pins dependencies and defaults that approval to null.

After admission, the manifest/config precede bounded input reads. The controller verifies the original complete run, reads at most2,000,001bytes with a2,000,000byte ceiling, checks exact payload bytes/canonical identity and the closed schema, and rechecks source file identity, content, ledger, config and dependencies. It copies precisely the accepted bytes into `demographic-benchmark.json`, with a separate `review-finalization.json` recording source/disclosure/code/config/execution proof. It performs no fitting, arithmetic transformation, network call, package build or dashboard update.

Failures/cancellations seal type-only evidence. Partial or failed payload promotion remains under a local-only filename, preventing accidental review-pack inclusion. No raw source record or private full aggregate is copied. The successful result still requires an independent actual finalization check before admission to the owner-review bundle/dashboard. There is no automatic export or publication.

Synthetic fixtures test missing authorization, a forged/mismatched output audit, rejected secret metadata, source drift/cancellation, manifest ordering, exact payload/replay preservation, and failure immediately after file promotion. They use temporary MOCK sources and stubbed code approval, not actual source records or self-issued real audit receipts.

After fresh independent finalization code approval is pinned:

```bash
.venv/bin/python -m civiclab.reviewed_benchmark --root "$PWD"
```

Tests:

```bash
.venv/bin/python -m unittest tests.test_reviewed_benchmark -v
```

The dataset remains a Wyoming demographic benchmark, not a national synthetic population, political-effect estimate or validation of ANES state political behavior. Paid inference, national acquisition, fitting, external deployment and public publication remain outside this approval.
