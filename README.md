# Synthetic Society Lab

Research project exploring whether demographic grounding, information exposure, and agent interaction improve useful predictive or experimental results.

- **E01 — Feed to Ballot:** Evaluate electoral-margin forecasts against transparent statistical baselines, subject to source-cutoff and forecast-validity checks.
- **E02 — The Information Effect:** Measure changes in synthetic model responses under controlled, matched-content information treatments. Synthetic responses do not establish effects on human voters.

## Project handoff

- [Complete progress report — November 3, 2026](reports/PROGRESS_2026-11-03.md)
- [Current orchestration status](reports/STATUS.md)
- [Full completion contract](configs/completion_contract.json)
- [Master execution blueprint](CODEX_MASTER_EXECUTION.md)
- [Original start-here handoff](START_HERE.md)
- [Data acquisition inventory](configs/MASTER_DATA_ACQUISITION.csv)
- [Received data and validation status](docs/DATA_SOURCES.md)
- [Source hashes and CSV structure inventory](configs/SOURCE_INVENTORY.json)
- [GDELT ingestion fixture](tests/fixtures/gdelt/20261103090000.gkg.csv.zip)
- [Fixture provenance](tests/fixtures/gdelt/manifest.json)

## Implemented offline laboratory

One installable Python project with a standard-library core contains four module namespaces. E02 and E01 have tested engineering pipelines; E03 (Synthetic City) and E04 (Government AI Reliability) have separate deferred protocols and blocking preflights. Python 3.11+ on macOS/Linux is supported; run locking uses POSIX file locks.

- Shared infrastructure: automated source-byte verification, GDELT fixture ingestion, immutable checksummed run artifacts, JSONL events, environment/code provenance, SQLite job checkpoints and concurrency-safe spending reservations.
- E02: versioned party-thermometer instrument, ANES weighted joint-cell/ACS calibration, diagnostics, fictional profiles, content-matched randomized treatments, before/after scoring, crossed bootstrap and reproducible mocked pilot.
- E01: retrospective-only manifests and ballot/geography validators, historical-margin S0, feature-only predictor subprocess, frozen predictions, separate held-out scoring, matched comparisons and actual returns-readiness audit.
- Local run viewer: integrity-checked snapshots, exclusions, uncertainty, source hashes, paired exposure replay and saved DEMO counterfactuals. It never runs inference or invents results.

Read [current status](reports/STATUS.md), [initial implementation evidence](reports/STATUS_20261103.md), [E02 protocol](protocols/E02_INFORMATION_EFFECTS.md), [E01 protocol](protocols/E01_RETROSPECTIVE.md) and [milestone criteria](configs/milestones.json). The original November 3 progress audit is retained as the pre-implementation historical record. Verify older descriptions of missing components against the current checkout.

## Install and verify

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[selection]'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/civiclab modules
.venv/bin/civiclab validate-sources --fixture-only
.venv/bin/civiclab gdelt-ingest
.venv/bin/civiclab completion
```

For the optional physical-PDF reader, install `.venv/bin/python -m pip install -e '.[geometry]'`. Its scoped Python 3.11/3.12 installation and cached-source checks have [independent acceptance](reports/INDEPENDENT_AUDIT_GEOMETRY_RUNTIME_V1_7.json); readiness integration remains separately gated. The observed full Python 3.12 environment is pinned in [the geometry runtime lock](configs/runtime_python312_geometry_20261103.txt). Historical archives retain their original dependency locks; the new lock is not a Python 3.11 full-environment lock. See the [runtime notes](docs/GEOMETRY_RUNTIME_V1_7.md).

On a machine with the registered local raw inputs:

```bash
.venv/bin/civiclab validate-sources --out data/processed/validation/source-integrity.json
.venv/bin/civiclab e02-fit
# Use population.json from the run directory printed above:
.venv/bin/civiclab e02-pilot --population data/processed/runs/PRINTED_RUN_ID/population.json
.venv/bin/civiclab e01-demo
.venv/bin/civiclab e01-audit
.venv/bin/civiclab dashboard
.venv/bin/civiclab serve
```

The viewer serves only its generated index/snapshot at loopback `127.0.0.1:8765`, not the repository or raw-data tree. The generated HTML also works as a standalone local file. Use repeated `dashboard --run RUN_ID` options to select an evidence set. Interrupt the preview with Ctrl-C. The pilot's `--resume RUN_DIRECTORY` requires unchanged code/config and refuses interrupted jobs needing reconciliation.

## Scientific and financial gates

All E02 responses so far are explicitly MOCK, using project-authored fictional notices and a deliberate known mock effect. Scripted Q&A tests C3/C4 plumbing; it is not live assistant research. The ACS/ANES universe mismatch and sparse population support prohibit representative-electorate claims. Real-news text/rights, population review and preregistration remain unresolved.

E01 includes a real 2018→2024 regular Senate diagnostic with 30 matched states, official-count adjudications and S_ZERO/S0 baselines. Its recorded arithmetic and replay have [scoped independent acceptance](reports/INDEPENDENT_AUDIT_E01_HISTORICAL.json); this post-hoc diagnostic does not complete the original 2026 House/Senate and agent study. The separate DEMO uses invented fixtures. Local outcome separation is a tested feature-flow boundary, not an OS sandbox or independent timestamp. No prospective forecast claim is permitted. See the [historical runbook](docs/E01_HISTORICAL_RUNBOOK.md).

Paid model inference remains disabled, with $0 approved spend and no paid calls. OpenRouter is the only network inference adapter. It requires a fixed model/provider, fresh pricing evidence, an explicit approval ID and positive total/module caps. Atomic reservations count pending requests; unknown billing halts the ledger, known charges are retained even for malformed outputs, and there are no automatic retries/fallbacks. The adapter is mocked in tests; live behavior and billing are not verified. Credentials remain local and untracked; no Meta/X access was exercised.

Advanced demographics, news/social content, live assistants and swarms need matched simpler comparisons; swarms require equal-compute independent controls. See `configs/milestones.json`. A passing engineering test does not demonstrate scientific superiority.

## Reproducibility and data boundaries

The GDELT fixture has 868 records and 27 fields and is versioned under `tests/fixtures`. Full acquired datasets and generated runs remain under Git-ignored `data/`. A fresh clone can run offline tests and the E01 DEMO; full population fitting requires the exact local source files recorded in the inventory. The historical handoff's original commands/tests were not present; use the commands above for the implemented software.

Each run records source-code identity (including uncommitted implementation fingerprint), Python/platform, config, seeds, artifact hashes and events. Responses/assignments replay deterministically for the mock provider; real hosted models may not honor deterministic seeds. The dashboard is local-only; nothing has been publicly deployed or published.

## Review workflows

The [paper draft](publications/TECHNICAL_PAPER_DRAFT.md), [blog draft](publications/BLOG_DRAFT.md), [limitations](publications/LIMITATIONS.md) and [reproducibility instructions](publications/REPRODUCIBILITY.md) are for owner review. Independent acceptance is scoped to the exact evidence in each audit receipt; a packaged mock run remains a mock run.

```bash
# Plan restoration from previously downloaded registered files; add --apply to copy:
.venv/bin/civiclab restore-inputs --from /path/to/downloads
# Optional official election-document parser:
.venv/bin/python -m pip install -e '.[sources]'
.venv/bin/civiclab e01-historical verify
.venv/bin/civiclab e01-historical prepare
.venv/bin/civiclab e01-historical run
# Exact statutory excerpts, separate from real-news acquisition:
.venv/bin/civiclab e02-stimuli verify
# Explicitly select sealed artifacts for an owner-review archive:
.venv/bin/civiclab repro-pack --run RECORDED_RUN_ID --out data/processed/reproducibility/review-snapshot.zip
```

E01's `download` action and E02's `acquire` action fetch only their documented public sources. The local restore command verifies registered hashes and refuses changed existing files; it does not prove upstream authenticity or legal reuse. The full source-reacquisition and remote-CI gates remain separate requirements.


The optional `selection` extra pins SciPy for the exact E01 fixture selector; CI installs it so solver checks do not silently skip. Actual 2026 selection remains blocked until a complete permitted as-of ratings/ballot frame passes independent review. Source acquisition permission is separate from public page visibility.

The new citizen-target stage is separate from population fitting:

```bash
.venv/bin/civiclab e02-targets
```

It records approximate normalized ACS citizen25+ targets, original MOEs, rounding bounds and source/review lineage. Independent arithmetic acceptance is required before any new fit. Prior v3 runs and resident-calibrated models remain unchanged. See [the target runbook](docs/E02_CITIZEN_TARGETS_V1_RUNBOOK.md).

[Cost planning](docs/COST_PLANNING.md) uses the same conservative request envelope and per-call reservation rounding as the adapter. `civiclab cost-plan --spec PATH` produces a review-only estimate for exact frozen calls; it never loads credentials, dispatches requests or authorizes spend. No real priced run proposal is accepted yet.
