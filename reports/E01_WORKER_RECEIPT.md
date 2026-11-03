# E01 election worker receipt

TASK_ID: E01_REAL_HISTORICAL_SENATE_DIAGNOSTIC_2018_2024

FILES_CHANGED:
- `src/civiclab/e01/historical.py` (new scoped importer, verification, historical runner)
- `src/civiclab/e01/worker.py` (validated deterministic S_ZERO option, default S0 preserved)
- `tests/test_e01.py` (six source/parser/guard regressions)
- `configs/e01_official_sources.json`, `configs/e01_senate2018_2024.json`
- `protocols/E01_SENATE_2018_2024_DIAGNOSTIC.md`
- `docs/E01_HISTORICAL_RUNBOOK.md`
- `reports/E01_HISTORICAL_EVIDENCE.json`, this receipt

OUTPUT_ARTIFACTS:
- Local raw sources: `data/raw/e01_official/` (ignored; no raw source committed)
- Prepared manifest: `data/processed/e01/prepared_historical.json`
- Completed runs: `e01-ed5b716aa76145258ece94c3df6b4188`, `e01-9a3e3305877f40b3a84e63bd5ca5ed1c`
- Both under `data/processed/runs/`; checksum/provenance/immutable artifacts use RunStore.
- 30 eligible states; 120 modeled major-candidate/party/count official crosschecks; three structural exclusions, nine recorded official-count corrections and one spelling reconciliation.

REPRODUCTION_COMMANDS:
- Install `.[sources]` (pypdf 6.10.0); `PYTHONPATH=src python -m civiclab.e01.historical download|verify|prepare|run --root /absolute/repo` (choose one action per invocation).
- `PYTHONPATH=src .venv/bin/python -m unittest tests.test_e01 tests.test_isolation -v`
- Lead owns CLI wiring: `civiclab e01-historical download|verify|prepare|run`.

TESTS_RUN_AND_RESULTS:
- 25 E01/isolation tests PASS locally, including existing DEMO/REAL-denial guards, general-vs-primary column parsing, fusion handling without blank/other votes, Senate-only scope, ambiguous-name refusal, explicit alias, party mismatch and changed-input/duplicate coverage refusal.
- Real prepare completed: 30 eligible states, 120 crosschecks; no unresolved mismatch silently discarded.
- Two actual full runs completed, their entire summary JSON matched; reproducibility hash `ec3ded3027c50c3468abea845b63caa64bdf6b14306644248ef63da0acd17cda`.
- All six public download endpoints independently refetched and matched pinned hashes (`data/processed/e01/download_endpoint_check.json`). Source hashes verified as part of each prepare/run. Visual PDF spot checks confirmed FEC PDF p34 OH/PA and Clerk PDF p31 Maine source positions/counts.
- Descriptive S0 MAE 10.199287428521943 pp; S_ZERO MAE 18.18830603000105 pp; same 30 states. Paired mean difference -7.98901860147911 pp. Leave-one-state-out paired mean range [-8.72470437989103,-6.524110162136731] is sensitivity, not CI.
- These are worker execution receipts, not independent milestone certification; audit PENDING.

SOURCE_DATA_AND_LICENSE_NOTES:
- Public pinned MEDSL 1976–2018 and 2024 statewide CSVs support discovery; authoritative FEC 2018 and House Clerk 2024 publications supply modeled counts.
- Official Senate Class-I page and FEC six-year cycle establish statewide seat identity; Maryland State Archives resolves Tony Campbell spelling.
- FEC/Maryland election endpoints with 403 were not bypassed; public Clerk/State Archives alternatives used. Raw files remain local. No MEDSL code-license assertion or wholesale third-party redistribution permission inferred.
- Government source dates/hashes, CSV unofficial flags, corrections and limitations are documented in configs/run receipts. Feature availability is conservatively after the documented October 2019 publication month; no exact release date invented.

COST_USD_ACTUAL_OR_ZERO: 0; no model calls, credential use, paid services or approved budget change.

RISKS_AND_LIMITATIONS:
- Post-hoc historical diagnostic, not historically untouched or prospective; operator/selection code encountered outcomes. Predictor child separation protects accidental I/O, not adversarial code or researcher blinding.
- Structural sample differs from original 2026 study. Maine's independent winner is outside the explicitly conditional D-R target; this is not winner forecasting.
- Official result documents establish retrospective participants, not pre-election ballot archives. Surname/party/count linkage and nickname differences remain visible for audit.
- Nine CSV disagreements were corrected by explicit pre-scoring protocol amendment to authoritative PDF counts; no performance-based exclusions. PDF extraction emitted warnings on rotated unrelated pages; spot checks are not complete independent source review.
- Finite cohort sensitivity is not population inference, general superiority evidence, human persuasion or agent evidence.
- No shared CLI/status/dashboard/publication file was edited by this worker. No commits or pushes performed.

UNRESOLVED_BLOCKERS:
- Independent auditor must review source mapping/adjudications, protocol, artifact integrity and formula implementation.
- Original 2026 sample, House geography/ballot validation, 2026 historical inputs/outcomes, genuine holdout, agent variants and same-race/equal-compute controls remain incomplete.
- Remote authentication/delivery belongs to lead; no alternate remote substituted.

NEXT_UNBLOCKED_TASK:
- Independent audit of the bounded diagnostic. Lead can integrate its accepted aggregate outputs in viewer/publication drafts while preserving original E01 blocked gates; no paid execution or public publication is authorized.
