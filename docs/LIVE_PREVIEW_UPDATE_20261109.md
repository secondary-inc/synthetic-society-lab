# Local live-pilot preview update

The owner requested an updated frontend after the previous preview showed only
the November 3 snapshot. The new section displays the accepted completed pilot
before the historical viewer: 32 valid real-model answers, eight complete
comparisons, zero observed partisan-gap contrast, $0.001434 verified research
charges and $0.002857 conservative ledger exposure. The real response / authored
DEMO content distinction, cross-date comparisons, baseline anchoring, degenerate
interval and incomplete full research contract remain visible.

The initial frontend version labeled the follow-up as a design in review. The
subsequent result overlay now reads the exact accepted follow-up audit
`INDEPENDENT_AUDIT_E02_ALIGNMENT_ANCHORING_ACTUAL_20261109.json`, SHA-256
`cf2bed0882f71d33efd3cd755ace36cf3e58aaef0759b881c0361488a0ec7246`.
It displays 22 actual answers from 28 planned slots, six rule-derived skips,
four OMITTED contrasts averaging 56.25 points, and the separate two-context
matched comparison (OMITTED 62.5, SHOWN 0, interaction -62.5). The missing pairs,
all-asked comprehension denominator, unfulfilled full anchoring pattern, no
human inference and absent inferential intervals are explicit. Current exposure
is $0.004473; the earlier $0.002857 checkpoint is labeled historical. The first
study remains separate and unchanged. This is a saved local summary, not a live
experiment controller.

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

The initial six tests passed, covering the exact receipt, public-file-only reads, no writes
on altered evidence, HTML escaping, preserved historical bytes/snapshot and
idempotence. Actual browser inspection confirmed the current result cards and
clearly separated planned follow-up. The existing loopback server returned 200
for `/` and `/snapshot.json`, and 404 for the historical HTML, summary JSON,
credential path and parent/report path. Its allowed serving paths are unchanged.

The follow-up delta passes nine tests, adding a second public-audit-only read
guard, altered-follow-up refusal before any preview writes, and exact matched
denominator / missingness / comprehension claims. Actual browser DOM inspection
confirmed the latest outcome and original result as distinct sections. The
follow-up code/privacy/claims delta passed its separate narrow independent
review in `reports/INDEPENDENT_AUDIT_LIVE_SUMMARY_FOLLOWUP_DELTA_20261109.json`,
SHA-256 `c23ec4b2829430938e93883fa9fd6931649533f552bff467b3d04a85c3178ba7`.
The actual scientific outcome audit is separately accepted. Browser layout
inspection remains implementer evidence.

Separate independent code, privacy and claims review passed in
`reports/INDEPENDENT_AUDIT_LIVE_SUMMARY_VIEWER_20261109.json` (SHA-256
`36e376ad1dba2194eeca8d99f58aa480656c86563872e748ed456ddde57ec55a`).
The reviewer reran the six tests and checked the exact source bindings. Visual
browser inspection remains implementer evidence, not independent layout
certification. The lead owns integration and repository commits. Private
journals and generated preview files are not added to Git.
