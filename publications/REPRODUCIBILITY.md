# Synthetic Society Lab Reproducibility and Owner Review

This package is for local owner review. It does not authorize publication, paid inference, source redistribution or an affiliation claim.

## Environment

Use Python 3.11 or 3.12 on macOS/Linux. Core execution uses the standard library. New E01 selector fixtures additionally use the pinned optional SciPy selection extra; install it to exercise the actual solver. Older frozen archives document their own dependency/test snapshot. Static figures use the optional pinned Matplotlib extra; official election PDF parsing uses the pinned sources extra:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[selection]'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/civiclab validate-sources --fixture-only
# Optional research figures:
.venv/bin/python -m pip install -e '.[figures,sources]'
```

The actual local `.env` and raw data are excluded. Do not paste secrets into these documents. Download/import registered source bytes before running full-source validation, real population fitting or real election workflows. The source inventory and module-specific importer documentation state what can be reacquired; unresolved legacy-source acquisition paths remain a completion blocker.

For the observed Python 3.12 research environment, `configs/runtime_python312_20261103.txt` pins the installed optional tools and their transitive dependencies. In a fresh Python 3.12 environment, install that file with `python -m pip install -r configs/runtime_python312_20261103.txt`, then install this project with `python -m pip install -e . --no-deps`. The lock is not for Python 3.11: its NumPy 2.5 requires Python 3.12+. The Python 3.11 CI job instead resolves compatible dependencies from the pinned SciPy extra and must independently pass the same selector fixtures. Run artifacts record the actual Python and relevant dependency versions; older sealed runs preserve their older environment records.

## Recorded outputs

`reports/ENGINEERING_EVIDENCE_20261103.json` records the original sealed engineering runs. Newer module receipts and independent audits may supersede those for specific claims. Every run includes source/configuration identity, environment, seeds, summaries, events and a final checksum ledger. `verified_run()` rejects altered or incomplete artifacts. MOCK/DEMO outputs remain engineering fixtures after packaging.

The original population figure can be regenerated from the recorded fit:

```bash
.venv/bin/python -c "from pathlib import Path; from civiclab.figures import population_figures; population_figures(Path.cwd(), 'e02-ad2ad153c5ea480d8a9b7f39433927e7', Path('publications/figures'))"
```

Its PNG, SVG and provenance JSON identify the exact input run and output hashes. This diagnostic plot is not a model-effect estimate.

The accepted post-hoc E01 result can be inspected without raw source data in its selected sealed run; recreating the importer requires the pinned public inputs:

```bash
.venv/bin/civiclab e01-historical download
.venv/bin/civiclab e01-historical verify
.venv/bin/civiclab e01-historical run
.venv/bin/python -c "from pathlib import Path; from civiclab.figures import election_figures; election_figures(Path.cwd(), 'e01-ed5b716aa76145258ece94c3df6b4188', Path('publications/figures'))"
```

The population-support comparison runs with `.venv/bin/python -m civiclab.e02.population_alternatives` once the registered ANES/ACS inputs are restored. It reports all candidates and sensitivities; it does not automatically select a winner or resolve the population validity gate.

## Completion and dashboard

```bash
.venv/bin/civiclab completion
.venv/bin/civiclab dashboard --run e02-ad2ad153c5ea480d8a9b7f39433927e7 --run e02-0121548188194f04936b85c984ee677f
.venv/bin/civiclab serve
```

The completion status consumes independently authored audit receipts. Empty, duplicate, stale, unsupported or unreviewed requirements cannot produce an accepted complete program. The role declaration is a workflow assertion rather than a cryptographic identity. The lead must not write its own audit PASS findings. The preview server binds only to loopback and serves only the generated index/snapshot.

## Build a review package

Select every included run explicitly. The builder includes code, configurations, tests, protocols, drafts, audit/status reports and the full checked artifact set for those runs. It excludes `.env`, raw datasets and Git credentials. It refuses unsafe paths, credential-like values, source changes during assembly, unsealed runs and inconsistent hashes.

```bash
.venv/bin/civiclab repro-pack --run e02-ad2ad153c5ea480d8a9b7f39433927e7 --run e02-0121548188194f04936b85c984ee677f --out data/processed/reproducibility/new-review-snapshot.zip
```

The default output is `data/processed/reproducibility/owner-review.zip`; that historically audited snapshot already exists locally. Choose a new output name for every snapshot. The builder refuses to overwrite an existing archive. The embedded `REPRODUCIBILITY_MANIFEST.json` lists code identity, selected runs, every member hash, reproduction commands and limits. Package integrity is not scientific acceptance. An independent auditor must verify restoration and the claims attached to each result before the package is publication-ready.
