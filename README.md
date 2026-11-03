# Synthetic Society Lab

Research project exploring whether demographic grounding, information exposure, and agent interaction improve useful predictive or experimental results.

- **E01 — Feed to Ballot:** Evaluate electoral-margin forecasts against transparent statistical baselines, subject to source-cutoff and forecast-validity checks.
- **E02 — The Information Effect:** Measure changes in synthetic model responses under controlled, matched-content information treatments. Synthetic responses do not establish effects on human voters.

## Project handoff

- [Complete progress report — November 3, 2026](reports/PROGRESS_2026-11-03.md)
- [Master execution blueprint](CODEX_MASTER_EXECUTION.md)
- [Original start-here handoff](START_HERE.md)
- [Data acquisition inventory](configs/MASTER_DATA_ACQUISITION.csv)
- [Received data and validation status](docs/DATA_SOURCES.md)
- [Source hashes and CSV structure inventory](configs/SOURCE_INVENTORY.json)
- [GDELT ingestion fixture](tests/fixtures/gdelt/20261103090000.gkg.csv.zip)
- [Fixture provenance](tests/fixtures/gdelt/manifest.json)

## Implemented offline laboratory

One installable, standard-library-only Python project contains four module namespaces. E02 and E01 have tested engineering pipelines; E03 (Synthetic City) and E04 (Government AI Reliability) have separate deferred protocols and blocking preflights. Python 3.11+ on macOS/Linux is supported; run locking uses POSIX file locks.

- Shared infrastructure: automated source-byte verification, GDELT fixture ingestion, immutable checksummed run artifacts, JSONL events, environment/code provenance, SQLite job checkpoints and concurrency-safe spending reservations.
- E02: versioned party-thermometer instrument, ANES weighted joint-cell/ACS calibration, diagnostics, fictional profiles, content-matched randomized treatments, before/after scoring, crossed bootstrap and reproducible mocked pilot.
- E01: retrospective-only manifests and ballot/geography validators, historical-margin S0, feature-only predictor subprocess, frozen predictions, separate held-out scoring, matched comparisons and actual returns-readiness audit.
- Local run viewer: integrity-checked snapshots, exclusions, uncertainty, source hashes, paired exposure replay and saved DEMO counterfactuals. It never runs inference or invents results.

Read [implementation status and acceptance evidence](reports/STATUS_20261103.md), [E02 protocol](protocols/E02_INFORMATION_EFFECTS.md), [E01 protocol](protocols/E01_RETROSPECTIVE.md) and [milestone criteria](configs/milestones.json). The original November 3 progress audit is retained as the pre-implementation historical record.

## Install and verify

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/civiclab modules
.venv/bin/civiclab validate-sources --fixture-only
.venv/bin/civiclab gdelt-ingest
```

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

E01's genuine historical forecasts remain blocked by missing comparable prior returns, verified manifests and aggregation policies. The working S0 demonstration uses labeled invented fixtures. Local outcome separation is a tested feature-flow boundary, not an OS sandbox or independent timestamp. No prospective forecast claim is permitted.

Paid model inference remains disabled, with $0 approved spend and no paid calls. OpenRouter is the only network inference adapter. It requires a fixed model/provider, fresh pricing evidence, an explicit approval ID and positive total/module caps. Atomic reservations count pending requests; unknown billing halts the ledger, known charges are retained even for malformed outputs, and there are no automatic retries/fallbacks. The adapter is mocked in tests; live behavior and billing are not verified. Credentials remain local and untracked; no Meta/X access was exercised.

Advanced demographics, news/social content, live assistants and swarms need matched simpler comparisons; swarms require equal-compute independent controls. See `configs/milestones.json`. A passing engineering test does not demonstrate scientific superiority.

## Reproducibility and data boundaries

The GDELT fixture has 868 records and 27 fields and is versioned under `tests/fixtures`. Full acquired datasets and generated runs remain under Git-ignored `data/`. A fresh clone can run offline tests and the E01 DEMO; full population fitting requires the exact local source files recorded in the inventory. The historical handoff's original commands/tests were not present; use the commands above for the implemented software.

Each run records source-code identity (including uncommitted implementation fingerprint), Python/platform, config, seeds, artifact hashes and events. Responses/assignments replay deterministically for the mock provider; real hosted models may not honor deterministic seeds. The dashboard is local-only; nothing has been publicly deployed or published.
