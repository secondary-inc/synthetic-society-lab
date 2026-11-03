# Synthetic Society Lab

Research project exploring whether demographic grounding, information exposure, and agent interaction improve useful predictive or experimental results.

- **E01 — Feed to Ballot:** Evaluate electoral-margin forecasts against transparent statistical baselines, subject to source-cutoff and forecast-validity checks.
- **E02 — The Information Effect:** Measure changes in synthetic model responses under controlled, matched-content information treatments. Synthetic responses do not establish effects on human voters.

## Project handoff

- [Master execution blueprint](CODEX_MASTER_EXECUTION.md)
- [Original start-here handoff](START_HERE.md)
- [Data acquisition inventory](configs/MASTER_DATA_ACQUISITION.csv)
- [Received data and validation status](docs/DATA_SOURCES.md)
- [Source hashes and CSV structure inventory](configs/SOURCE_INVENTORY.json)
- [GDELT ingestion fixture](tests/fixtures/gdelt/20261103090000.gkg.csv.zip)
- [Fixture provenance](tests/fixtures/gdelt/manifest.json)

## Current implementation status

This initial commit preserves the user-supplied planning materials and verified ingestion fixture. The handoff documents describe intended implementation and reference additional files that were not supplied. Scripts, protocols, configurations, and the claimed 17-test suite are not yet implemented or verified here. Commands in those documents are not currently runnable in this repository.

The included GDELT ZIP has 868 tab-separated records with 27 fields each. It is stored under tests/fixtures rather than the data/raw path mentioned in the original handoff, so that this small reproducible input can be versioned while acquired raw datasets remain ignored.

Paid model inference defaults to disabled; no API keys are included. E01 prospective forecast validity has not been established. No experimental results are included.
