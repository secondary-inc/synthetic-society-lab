# Reproduce the bounded real historical diagnostic

Use Python 3.12 and the optional source-verification dependency:

```sh
python -m pip install -e '.[sources]'
civiclab e01-historical download
civiclab e01-historical verify
civiclab e01-historical prepare
civiclab e01-historical run
python -m unittest tests.test_e01 tests.test_isolation -v
```

The equivalent direct API is `python -m civiclab.e01.historical {download,verify,prepare,run} --root /absolute/repository/path`. Set `PYTHONPATH=src` when using an environment without an editable installation. CLI wiring is owned by the lead. `pypdf==6.10.0` is required for real PDF extraction, not core fixture tests. Download uses public, pinned URLs, a 20 MB ceiling, timeout and no retries/authentication. A changed live page halts; it does not silently replace its hash. Acquisition/verification receipts are local. Some public endpoints returned 403; no bypass was attempted.

All six sources, raw hashes, reuse notes and failed endpoints are in `configs/e01_official_sources.json`. Raw files stay under ignored `data/raw/e01_official/`. Published government numeric facts are used for verification; this does not assert a license for MEDSL code or authorize redistributing entire third-party collections. No respondent, publisher article text or credential data enters this diagnostic.

`prepare` writes ignored `data/processed/e01/prepared_historical.json`. It validates candidate identity/party and official counts before producing any forecast error. Explicit count corrections and the Maryland spelling alias are versioned protocol records. `run` calls preparation again and writes an immutable `data/processed/runs/e01-*` directory with source receipt, eligibility, official crosschecks, manifest, features, both frozen prediction files, outcomes, separate evaluations, paired differences, events, manifest/checksum ledger and summary. Source dates, code/tree hashes and runtime identity use shared RunStore provenance. Outcomes are not sent to predictor children; the operator is not historically blinded.

The PDF extractor warns about rotated text on unrelated pages. Senate tables used here are nonrotated and have 120 explicit source crosschecks. Visual spot checks rendered FEC PDF page 34 (printed 28: ND/OH/PA) and Clerk PDF page 31 (printed 29: Maine), confirming general-column positions, official counts and exclusion of presidential/House sections. Those local review PNGs live in `data/processed/e01/pdf_review/`; spot checks do not replace independent review of all source mappings.

Two completed runs on November 3, 2026:

- `e01-ed5b716aa76145258ece94c3df6b4188`
- `e01-9a3e3305877f40b3a84e63bd5ca5ed1c`

Their summary JSON and reproducibility hash match exactly: `ec3ded3027c50c3468abea845b63caa64bdf6b14306644248ef63da0acd17cda`. These are real historical diagnostics, not DEMO fixtures. They remain post-hoc and unaudited until an independent reviewer records a finding. Aggregate evidence and limitations are in `reports/E01_HISTORICAL_EVIDENCE.json`; the original study completion contract remains blocked.
