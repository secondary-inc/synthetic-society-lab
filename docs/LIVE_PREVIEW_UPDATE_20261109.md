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

## November 11 third-study integration

The third study collected November 10 is admitted through exact outcome audit
`INDEPENDENT_AUDIT_E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json`
(SHA-256 `ea7fece4bf153eef45ec067ef8ce9753b874e53b644d2a51505add4c5820bcfd`)
and its exact public aggregate
`E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json`
(`b7269ba6c0a828c907a50b2de8b67d45dc8d4714efb8de8ccb90acba99467fb0`).
The aggregate's pending label is its original capture checkpoint, superseded by
the separate audit; neither source is edited. Both public files are bounded and
hash-checked before any preview writes. Only aggregate fields are exported;
scored phase rows, private file references and generation identifiers are omitted.

The new section keeps 53 answers and three skips separate from errors,
cancellations and unattempted slots. It reports A's three-context and B's
four-context contrasts, the secondary comparison on three common contexts,
support-null missingness separately from factual comprehension, and the unmet
full registered pattern. It distinguishes signed interaction from contraction,
preserves the baseline gap and financial holds, and records unresolved provider
streaming telemetry and unknown Qwen tiers. Earlier studies and the original
snapshot remain separate, with old ledger totals labeled historical.

Thirteen focused preview checks pass on Python 3.12, including altered audit or
aggregate refusal before any output, two-file public-only reads, a nonzero
NOT_ATTEMPTED/parse-error/cancellation/uncertain-failure oracle, unknown-status
refusal, common-context arithmetic, escaping and historical-byte preservation.
Local preview build completed. The existing in-app tab was refreshed and its
accessibility tree verified all three study sections, the 53/56 dispositions,
A3/B4/common3 denominators, 25/25 and 28/28 factual counts, historical ledger
labels and telemetry limitation. Implementer screenshots of the overview and
comparison/missingness panels are saved as crossmodel-results-preview.png and
crossmodel-comparison-preview.png in the existing local visualization directory.
Final independent renderer/draft review is separate; these tests and implementer
visual checks alone do not certify scientific acceptance or independent layout. Lead retains integration and commit ownership.
