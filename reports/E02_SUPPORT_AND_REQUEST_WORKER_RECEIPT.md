# E02 bounded follow-up receipt

TASK_ID: E02-IA-E02-001-v3 and E02-POPULATION-SUPPORT-EXPLORATORY-v1.

FILES_CHANGED: `src/civiclab/e02/experiment.py`, `tests/test_e02_experiment.py`, `configs/e02_analysis_plan.json`, `configs/e02_analysis_lock.json`, archived `configs/e02_analysis_lock_v2.json`, appended `protocols/E02_INFORMATION_EFFECTS.md`; new `src/civiclab/e02/population_alternatives.py`, `tests/test_e02_population_alternatives.py`, `configs/e02_population_support_plan.json`, `docs/E02_POPULATION_SUPPORT_COMPARISON.md` and this follow-up's evidence receipts. No shared platform, CLI, dashboard, status, publication or auditor files edited.

OUTPUT_ARTIFACTS: `reports/E02_REQUEST_BINDING_V3_EVIDENCE.json`, `reports/E02_POPULATION_SUPPORT_EVIDENCE.json`; ignored immutable runs named in those receipts. Original run artifacts remain unchanged. No raw respondent data or identifiers are exported.

REPRODUCTION_COMMANDS:

- `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v`
- `PYTHONPATH=src .venv/bin/python -m civiclab.e02.methods`
- `PYTHONPATH=src .venv/bin/python -m civiclab.e02.population_alternatives`
- For mock replay, load registered fit `population.json` and call `civiclab.e02.experiment.run_pilot(root, fit)`; the shared CLI also exposes the owned runner.

TESTS_RUN_AND_RESULTS: 22 E02 tests PASS, including strict full request/instrument binding, both-phase rehashed survey/phase/extra-context tampering, missing instrument, positive full-grid probability, survey-weight scale invariance, known association fixture recovery, common calibration and hand-calculated floor log score, paired zero-difference resampling and invalid inputs. Frozen v3 definition integrity PASS. New mock/replay outputs match. Candidate population run/replay aggregate hashes match. These are worker execution results, not independent audit certificates.

SOURCE_DATA_AND_LICENSE_NOTES: Same registered ANES 2024 release and local ACS five-year 2024 inputs as the original model; baseline validates original source-byte inventory before comparison. The full six-field target is retained. No new respondent or publisher data committed. Official S0501 metadata acquired; state-count data not acquired because the keyless API request returned Missing Key HTML. Possible subgroup percentage units require verification before any citizen margins can be used.

COST_USD_ACTUAL_OR_ZERO: $0 model/API spend; zero model network calls. Local compute and labor are not priced by that figure.

RISKS_AND_LIMITATIONS: All population analysis is retrospective exploratory on an already-inspected holdout, not an untouched confirmatory test. Primary hierarchical tau=5 loss is worse than the simpler comparator; no demographic-complexity promotion. Equal resident calibration conditions do not resolve citizen universe mismatch. Full support is imposed by smoothing. Bootstrap is descriptive cluster resampling, not full design-based uncertainty. No human persuasion, population representativeness, state inference or prospective election claim. Earlier request-integrity flaw is documented, not erased. v3 changes no estimand; independent request re-audit and population review remain pending.

UNRESOLVED_BLOCKERS: Independent auditor reviews; permitted citizen benchmark values and units; original population validity; independently approved stimuli and external registration; approved positive live budget, owner credential rotation and provider/pricing validation. No gate is weakened or self-certified.

NEXT_UNBLOCKED_TASK: Independent auditor recomputes strict request probes and matched population log losses; lead integrates aggregate recorded results and negative findings into the completion dashboard. Citizen-aligned benchmark acquisition can proceed through a permitted official channel; it cannot be replaced by invented values or an unreviewed percentage conversion. Any further population-model revision needs a fresh predeclared validation plan, with previously inspected holdouts disclosed.
