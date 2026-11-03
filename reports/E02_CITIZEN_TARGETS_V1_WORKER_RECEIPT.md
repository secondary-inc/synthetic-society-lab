# E02 citizen25+ target worker receipt

TASK_ID: E02-CITIZEN25PLUS-TARGETS-v1.

FILES_CHANGED: New files only: `configs/e02_citizen_targets_v1.json`; `src/civiclab/e02/citizen_targets.py`; `tests/test_e02_citizen_targets.py`; `docs/E02_CITIZEN_TARGETS_V1_RUNBOOK.md`; `reports/E02_CITIZEN_TARGETS_V1_EVIDENCE.json`; this receipt. No existing audited acquisition/methods/v3/population/support code or inputs edited. No shared CLI, packaging, dashboard, audit findings or status changes.

OUTPUT_ARTIFACTS: Immutable ignored real target diagnostic `e02-edf2b36e269442748f4721ef7f479876` and replay `e02-457e2e2a4e3a47eebc80e1f4a8adcd15`; each contains full Decimal-string target artifact, exact config/input lineage, code identity, environment, events and checksums. Aggregate handoff evidence is in `reports/E02_CITIZEN_TARGETS_V1_EVIDENCE.json`.

REPRODUCTION_COMMANDS: `PYTHONPATH=src .venv/bin/python -m civiclab.e02.citizen_targets`; `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v`; `PYTHONPATH=src .venv/bin/python -m civiclab.e02.methods`.

TESTS_RUN_AND_RESULTS: All31 E02 tests PASS, including6 new hand/adversarial/integration tests. Exact real target content hashes match across two fresh run IDs. v3 definition integrity remains PASS. Tests cover separate age/education denominators, native+naturalized addition, geography/DC/PR, proposed coarsening, published25+ normalization, bounds, malformed/suppressed/nonfinite values, mixed products, swapped definitions, overlapping citizenship columns, original MOE annotation preservation, proposal tamper, source-byte tamper, failed-run retention and immutable replay. Worker results are not independent certification.

SOURCE_DATA_AND_LICENSE_NOTES: Exact previously acquired official public ACSST5Y2024.S0501 ZIP, metadata and table notes. Source/proposal/methods/acquisition audit byte hashes are pinned before conversion. No source fetch or API key use. Public aggregate point estimates only; no respondent rows or cluster identifiers. Native+naturalized citizen25+ rationale is independently reviewed, while target arithmetic still needs its separate review.

COST_USD_ACTUAL_OR_ZERO: $0 model/API spend,0 paid/model calls. Local compute and labor not priced.

RISKS_AND_LIMITATIONS: Derived approximate normalized subgroup counts, not published exact counts. Componentwise rounding intervals are not simultaneously feasible target vectors or statistical confidence intervals. Original90% MOEs retained without unsupported covariance-adjusted error propagation. ACS2020–2024 period, group-quarters coverage, ANES eligibility/nonresponse/transport, full-adult/state scope and model-response validity remain limitations. No new fit or model promotion. Concurrent lead changes to shared infrastructure are captured by each run's code identity; the converter and target content hash are pinned, and no clean-source or remote-CI claim is made.

UNRESOLVED_BLOCKERS: Independent target-arithmetic audit required before fitting. Any later fit requires separately frozen matched2×2 evaluation and feasible rounding-sensitivity design. Original scientific/population gates remain BLOCKED, live trials/publication unauthorized.

NEXT_UNBLOCKED_TASK: Separate auditor recomputes exact published25+ anchoring, rounding consistency/bounds, geography, native+naturalized aggregation and per-region/national mass from the pinned local ZIP, then reviews failures/tests before any fitting amendment. Lead owns integration/commits and status.
