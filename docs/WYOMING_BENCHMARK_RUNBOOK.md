# Wyoming owner-review projection implementation

This implements the independently reviewed disclosure proposal in `WYOMING_BENCHMARK_DISCLOSURE_PROPOSAL.md`. It is a projection of one accepted local demographic aggregate, not a new source acquisition or population fit.

`configs/wyoming_benchmark_projection_v1.json` pins the exact source run, ledger, aggregate file/canonical hashes, archive/member identities, output schema, methods/source audits and projection code/tests. Execution approval defaults to null. Metadata admission and a fresh independent code/fixture receipt must pass before a RunStore or source processing begins. The code has no network transport, model adapter or credential loader.

The projection constructs all twelve age/education rows using a literal whitelist. Every cell must have at least30 unweighted contributors, positive finite consistent estimates and scalar uncertainty, and the reviewed conditional sampling-error status. Any failed cell blocks the entire projection. Scalar count/share variance, SE and90% MOE are retained without replicates, covariance matrices, allocation/exclusion tables, person identifiers or local source paths. The closed JSON schema and separate total/share/unique-cell checks apply before persistence.

Safe provenance is also projected literally from the pinned source execution evidence: official URL, archive/member byte counts, actual header hash/bytes/columns, observed source-processing wall time and process highwater RSS, with their measurement limitations. Projection implementation, execution-approval, schema, config, source-evidence and audit hashes are explicit. No source path, inode or arbitrary host fields are copied. Config and dependency identities are rechecked before persistence.

A manifest/config precede source verification and processing. Original run checksums and aggregate hash/canonical identity are checked, then the source is reverified after projection with file identity and content checks before the derivative is written. Failure/cancellation records preserve type-only diagnostics and sealed evidence; source runs are never rewritten. Tests inject source drift and cancellation using synthetic files, not real person records.

The initial output is **`demographic-benchmark.local.json`** and remains blocked from review-pack export by the existing local-only guard. It requires independent actual value/schema/disclosure/replay review, followed by a separately recorded approved review derivative. Renaming either local-only source artifact is not that approval. No code here finalizes a shareable derivative.

Only after the fresh independent implementation approval is pinned in the excluded `execution_approval` field:

```bash
.venv/bin/python -m civiclab.benchmark_export --root "$PWD"
```

Synthetic tests:

```bash
.venv/bin/python -m unittest tests.test_benchmark_export -v
```

Source/methods and schema changes require new versioned review. Never update old approvals or weaken thresholds to obtain a result. Owner-review status grants no external publication, national acquisition, synthetic-population fitting or paid-inference authority. The original nationwide adult/state research requirement remains incomplete.
