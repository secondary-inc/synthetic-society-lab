# RUN FIRST — for Codex and the human operator

**This package is a local overlay to your existing `secondary-inc/synthetic-society-lab` repository, not a replacement for uncommitted GitHub work.** GitHub access was not confirmed in this chat. Inspect existing files and reconcile changes before copying, branching or pushing.

## In Codex, give this exact task

> Read `AGENTS.md`, then the complete `CODEX_MASTER_EXECUTION.md`, and execute its dependency-ordered tickets. Audit the current repo/status first; don't destroy user changes. Today is 2026-11-03 (Election Day): immediately determine the E01 forecasting validity status using `docs/20_ELECTION_DAY_DECISION_TREE.md`. If a genuine pre-results forecast cannot be independently proven, mark the study RETROSPECTIVE; never backdate it. Keep statistical baseline independent of X/Meta/OpenRouter. In parallel build E02 as a controlled matched-content synthetic-agent experiment, nationwide by design, starting with an offline pilot. Use the included GDELT ZIP as an ingestion fixture, not pre-Nov2 news evidence. OpenRouter is the only inference gateway; paid requests disabled by default. Report DONE/BLOCKED/NOT RUN with artifacts and tests after each task.

## What runs now without data purchases

```bash
python -m unittest discover -s tests -v
python scripts/gdelt_ingest.py \
  --zip data/raw/gdelt/20261103090000.gkg.csv.zip \
  --out-dir data/processed/gdelt \
  --expected-sha256 6ed52033813c98b8b341c56e0a58bff8449907c0a823d3a780f4228d617af9bf
python scripts/preflight.py configs/e01_forecast_manifest.json
python scripts/preflight.py configs/e02_feed_manifest.json
```

GDELT metadata output is saved locally under `data/processed/gdelt/` and excluded from Git. Expect the two preflight configs to report NOT READY until datasets/protocols/approvals are populated. Offline tests: 17 passing at packaging.

## Human downloads/actions needed

1. ANES 2024 **CSV + user guide/codebook + questionnaire**: https://electionstudies.org/data-center/2024-time-series-study/
2. Census ACS data and verified **2026/120th congressional map**: https://data.census.gov/ and https://www.census.gov/programs-surveys/decennial-census/about/rdo/congressional-districts.html
3. 2022/2024 historical election returns: https://electionlab.mit.edu/data and/or official state archives; actual candidate rosters and dated ratings for 2026.
4. Optional authorized X public posts: https://docs.x.com/x-api/posts/search/introduction ; Meta political ads: https://www.facebook.com/ads/library/api/ . Neither gives real individual recommender feeds.
5. OpenRouter API key only if actual inference is authorized: https://openrouter.ai/keys . Place **locally** in `.env` and do not share it; approve explicit spend limits in config first.
6. GDELT historical news windows: https://data.gdeltproject.org/gdeltv2/masterfilelist.txt ; https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ . The included GKG is just one snapshot.

For file paths, credentials, costs, fallbacks and every edge case, read `docs/21_DATA_ACQUISITION_MAP.md`, `configs/MASTER_DATA_ACQUISITION.csv` and `docs/22_PREANALYSIS_AND_STATISTICS.md`.

## Outcomes and exit rules

- **E01:** status is `PROSPECTIVE_VERIFIED`, `PRE_RESULTS_UNVERIFIED`, `RETROSPECTIVE`, or `NOT_STARTED`, established with evidence. No data means `BLOCKED`, not an invented forecast.
- **E02:** the main confirmatory experiment is not allowed until questionnaire, stimulus identities, hypotheses, model, seeds, analysis, exclusions and budget are frozen. A pilot may run as `EXPLORATORY`.
- **Publication:** output only results with raw-file provenance, reproducible run IDs, uncertainty, negative outcomes and transparent human-vs-synthetic distinction.
