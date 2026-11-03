# GDELT fixture ingestion and metadata export

The supplied 20261103090000.gkg.csv.zip is the versioned fixture in tests/fixtures/gdelt. Its pinned SHA-256 is 6ed52033813c98b8b341c56e0a58bff8449907c0a823d3a780f4228d617af9bf. It contains 868 headerless, 27-field tab-separated records. The processing batch is November3 09:00UTC; this is not an article publication clock or a November2 information archive.

From the installed checkout:

```bash
.venv/bin/civiclab validate-sources --fixture-only
.venv/bin/civiclab gdelt-ingest
# Compatibility path named in the original blueprint:
.venv/bin/python scripts/gdelt_ingest.py
.venv/bin/python -c "from pathlib import Path; from civiclab.gdelt import verify_fixture_export; print(verify_fixture_export(Path.cwd()))"
```

Defaults produce data/processed/gdelt/fixture.json and fixture.csv. Both entry points use the same parser. JSON binds the CSV hash; consumers must use verify_fixture_export or equivalent hash/row/content checks. CSV bytes are immutable through this API: identical reruns reuse them; different content requires a new output path. The final JSON pointer is atomically replaced after CSV creation. A failed pointer update can leave an unreferenced CSV, while the previous referenced pair remains intact. Source/raw paths and overlapping output paths are refused. This is not a two-file filesystem transaction or an OS tamper-proof store.

The summary has record ID, batch, source, URL, publication time, reuse status and forecast-admissibility fields. All fixture publication times are unknown/empty, all reuse statuses unverified, and all forecast-admissibility flags false. Do not convert processing time into publication time, call URL candidates verified election stories, reconstruct article text without permission, or use this late batch for the proposed November2 cutoff.

No news, Meta/X feed or model request is made by these commands. The fixture supports parser/export checks and provenance, not human persuasion or forecasting performance. Independent CSV/export remediation evidence is indexed in reports/INDEPENDENT_AUDIT_GDELT_CSV_REMEDIATION.json.
