# Local live-pilot preview update

The owner requested an updated frontend after the previous preview showed only
the November 3 snapshot. The new section displays the accepted completed pilot
before the historical viewer: 32 valid real-model answers, eight complete
comparisons, zero observed partisan-gap contrast, $0.001434 verified research
charges and $0.002857 conservative ledger exposure. The real response / authored
DEMO content distinction, cross-date comparisons, baseline anchoring, degenerate
interval and incomplete full research contract remain visible.

The 28-call follow-up is explicitly a design in review, not a run or a result.
This is a saved local summary, not a live experiment controller.

`src/civiclab/live_summary_viewer.py` reads only the exact public independent
outcome audit pinned by SHA-256. Its exported fields are an aggregate allowlist;
it does not read private runs, owner stores, credentials or respondent sources.
No inference or financial operations occur. The original preview bytes are
preserved as `historical-preview.html`; the original `snapshot.json` is unchanged.
Historical results and completion receipts remain collapsed and dated.

Rebuild the generated preview with:

```sh
PYTHONPATH=src .venv/bin/python scripts/update_live_preview.py
```

Targeted verification:

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest test_live_summary_viewer -q
```

Six tests passed, covering the exact receipt, public-file-only reads, no writes
on altered evidence, HTML escaping, preserved historical bytes/snapshot and
idempotence. Actual browser inspection confirmed the current result cards and
clearly separated planned follow-up. The existing loopback server returned 200
for `/` and `/snapshot.json`, and 404 for the historical HTML, summary JSON,
credential path and parent/report path. Its allowed serving paths are unchanged.

Separate independent code, privacy and claims review passed in
`reports/INDEPENDENT_AUDIT_LIVE_SUMMARY_VIEWER_20261109.json` (SHA-256
`36e376ad1dba2194eeca8d99f58aa480656c86563872e748ed456ddde57ec55a`).
The reviewer reran the six tests and checked the exact source bindings. Visual
browser inspection remains implementer evidence, not independent layout
certification. The lead owns integration and repository commits. Private
journals and generated preview files are not added to Git.
