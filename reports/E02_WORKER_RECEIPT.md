# E02 worker receipt — corpus, methods and scoring integrity

TASK_ID: E02_METHODS_CORPUS_V2

FILES_CHANGED:

- `src/civiclab/e02/stimuli.py`: bounded exact-source importer and corpus verification.
- `src/civiclab/e02/methods.py`: analysis definition-lock verification.
- `src/civiclab/e02/instrument.py`: invalid raw response handling and pre/post status preservation.
- `src/civiclab/e02/experiment.py`: raw-score recomputation, frozen assignment validation, secondary and leave-one-cluster-out sensitivity diagnostics.
- `src/civiclab/e02/population.py`: survey-weight mass exclusion and held-out joint support diagnostics.
- `configs/e02_official_stimuli.json`, `configs/e02_analysis_plan.json`, `configs/e02_analysis_lock.json`.
- `protocols/E02_INFORMATION_EFFECTS.md`, `docs/E02_CORPUS_AND_METHODS.md`.
- Existing E02 tests plus `tests/test_e02_stimuli.py` and `tests/test_e02_methods.py`.
- This receipt and `reports/E02_WORKER_EVIDENCE.json`.

OUTPUT_ARTIFACTS:

- Seven active official-source/metadata/policy files in local ignored `data/raw/e02_official_sources`.
- Provenance receipt `data/processed/e02/official-stimulus-integrity.json`.
- Population diagnostic receipt `data/processed/e02/population-diagnostics-worker.json`.
- Updated population and two mocked pilot runs, with exact IDs and response hash in `reports/E02_WORKER_EVIDENCE.json`. Old runs are preserved; none was relabeled scientific.

REPRODUCTION_COMMANDS:

```bash
PYTHONPATH=src .venv/bin/python -m civiclab.e02.stimuli acquire
PYTHONPATH=src .venv/bin/python -m civiclab.e02.stimuli verify
PYTHONPATH=src .venv/bin/python -m civiclab.e02.methods
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v
```

The library APIs are `civiclab.e02.stimuli.acquire(root, transport=...)`, `verify_corpus(root)` and `civiclab.e02.methods.verify_analysis_lock(root)`. The lead owns shared CLI integration. PYTHONPATH explicitly selects checkout code if another worker's packaging verification changes the shared environment install.

TESTS_RUN_AND_RESULTS:

- Existing 10 E02 tests passed before edits.
- Current checkout: 19 E02 tests pass. Coverage includes raw-score tamper rejection, unknown/raw invalid types, known mock effect recovery, assignment integrity, deterministic replay, exact extraction, duplicate/ambiguous sources, drift quarantine, URL/path restrictions, metadata dates and definition-lock drift.
- Candidate corpus: PASS_PROVENANCE_CHECKS for three excerpts; independent rights/content review remains PENDING.
- Definition lock: PASS_DEFINITION_INTEGRITY across 11 inputs; external registration remains NOT_RUN.
- Mocked response hashes match across replay; this is engineering evidence only. The known injected two-point effect and its narrow interval are not scientific findings.

SOURCE_DATA_AND_LICENSE_NOTES:

- GovInfo original statutory paragraphs from 5 USC 552(a)(3)(A), 29 USC 157 and 42 USC 7401(b)(1)-(2), 2024 Edition. Exact source URLs, bytes, SHA-256 values, dates and paragraph selectors are in the corpus manifest.
- Reuse rationale: GovInfo public-domain/copyright policy, with original federal statute text selected and third-party contributions excluded. Independent audit remains pending; no worldwide legal permission claim is made.
- No raw ANES respondent records, credentials or full publisher articles were committed or transmitted externally. No Git commit/push was made by this worker.

COST_USD_ACTUAL_OR_ZERO: $0 model/API spend; zero model calls and no use of exposed credentials. Public source downloads only. Local compute/labor is unpriced.

RISKS_AND_LIMITATIONS:

- This small purposive official-document corpus is not representative news, actual platform exposure or a validated treatment for human political outcomes.
- The plan is locally versioned and hash-locked, not externally preregistered or independently approved.
- The original population fit drops about 52.20% of training survey weight through sparse-cell suppression and covers about 38.74% of held-out joint survey weight. Citizen/resident universes differ. These remain blocking limitations.
- Hosted model/provider choice, prompt robustness, genuine model variance/power, live assistant contrasts, equal-compute advanced comparisons and human external validity remain unestablished.

UNRESOLVED_BLOCKERS:

- Independent review of protocol, content, rights and population.
- Owner rotation/secure validation of exposed credentials and explicit nonzero budget before model dispatch.
- Fresh exact-provider cost evidence and operational approval before a paid pilot.
- Population specification revision and citizenship-aligned benchmark investigation; existing convergence does not establish defensibility.
- Main-run size/analysis registration cannot be based on deterministic mock variance.

NEXT_UNBLOCKED_TASK:

Per the lead's follow-up, compare defensible alternatives that preserve more survey mass and inspect official citizen-adult ACS benchmarks. Preserve the current specification and report a matched diagnostic comparison; do not redefine success around a narrower model or open a representative gate without evidence. Independent auditor should review the completed corpus/methods milestone separately from that follow-up.
