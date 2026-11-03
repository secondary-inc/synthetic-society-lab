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

## Verified committed engineering snapshot

Exact commit `722e63aad090714eba58b51c83e68e21beeb0bc9` has an independently reviewed clean-source restoration. A new Python3.12 environment installed `configs/runtime_python312_geometry_20261103.txt` and the editable project;767 fixture tests passed in377.484seconds, fixture-only source validation passed, and all974 archived files remained byte-identical. See the [execution receipt](../reports/CLEAN_RESTORE_722E63A_767_FIXTURES_LEAD.json) and [independent review](../reports/INDEPENDENT_AUDIT_CLEAN_RESTORE_722E63A_767_FIXTURES_V1.json).

Export that exact commit with `git archive --format=zip --output=committed-source.zip 722e63aad090714eba58b51c83e68e21beeb0bc9`, extract into a new directory, and use a credential-free subprocess environment. In the extracted directory:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip --isolated install --no-input -r configs/runtime_python312_geometry_20261103.txt
.venv/bin/python -m pip --isolated install --no-input --no-deps -e .
PYTHONPATH=src:tests .venv/bin/python -m unittest discover -s tests -q
.venv/bin/civiclab validate-sources --fixture-only
```

The source ZIP hash is `baeb3d209901cceaa96cbb3206fbb7659f0b42438141773b2d4855e935e1bee8` (7,027,666bytes). It excludes actual raw sources, private run/owner histories and credentials; selected research outputs require the separate review-package procedure below. This receipt does not cover later worker code, remote CI, full research-data reconstruction or scientific validity. Historical defective versions remain present for regression evidence, without their findings being closed by healthy tests. The earlier `a856b96` restoration failed one nonportable historical-proposal test; its archive/log and original test remain preserved. The correction has its own independent receipt. Dependency versions were pinned, but transient isolated build tools were not hash-locked.

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

The accepted exploratory citizen/resident comparison is recorded in runs `e02-1be3718699e54d7380755be1f9d87e6d` and `e02-ab4188e6c75d46a18179cb81dfde156c`. Its [runbook](../docs/E02_CITIZEN_COMPARISON_V1_RUNBOOK.md) describes exact source/code/approval pins. A rerun intentionally fails closed if pinned inputs change; do not rewrite old approvals to make it run. With exact registered source bytes and the reviewed implementation present:

```bash
.venv/bin/python -m civiclab.e02.citizen_comparison_v1 compare
.venv/bin/civiclab dashboard --run e02-1be3718699e54d7380755be1f9d87e6d --run e02-ab4188e6c75d46a18179cb81dfde156c --out data/processed/comparison-dashboard
.venv/bin/python -c "from pathlib import Path; from civiclab.figures import citizen_comparison_figure; citizen_comparison_figure(Path.cwd(), 'e02-1be3718699e54d7380755be1f9d87e6d', Path('publications/figures'))"
```

The viewer renders every saved configuration and failure, all paired contrasts and finite directional ranges. Changing its benchmark selector reads existing recorded scores; it performs no new fit, model call or counterfactual computation. The figure shows the frozen H5 primary under both central targets; full sensitivities remain in the run. Both original population-science acceptance and paid inference remain gated.

```bash
.venv/bin/civiclab completion
.venv/bin/civiclab dashboard --run e02-ad2ad153c5ea480d8a9b7f39433927e7 --run e02-0121548188194f04936b85c984ee677f
.venv/bin/civiclab serve
```

The completion status consumes independently authored audit receipts. Empty, duplicate, stale, unsupported or unreviewed requirements cannot produce an accepted complete program. The role declaration is a workflow assertion rather than a cryptographic identity. The lead must not write its own audit PASS findings. The preview server binds only to loopback and serves only the generated index/snapshot.

## Build a review package

The current `repro-pack` command routes to the versioned builder. It requires six exact public evidence receipts, including both preserved pre-POST compatibility stops, and binds captured run artifacts and checksum bytes to the original verified seal. The historical builder remains unchanged for prior evidence; its demonstrated capture race is preserved in the independent finding and original-source fixture. The six-receipt extension passed independent review (`reports/INDEPENDENT_AUDIT_REVIEW_PACKAGE_SIXTH_RECEIPT_EXTENSION_V1.json`); no new archive is claimed by these instructions.

Select every included run explicitly. The builder includes code, configurations, tests, protocols, drafts, audit/status reports and the full checked artifact set for those runs. It excludes `.env`, raw datasets and Git credentials. It refuses unsafe paths, credential-like values, source changes during assembly, unsealed runs and inconsistent hashes.

```bash
.venv/bin/civiclab repro-pack --run e02-ad2ad153c5ea480d8a9b7f39433927e7 --run e02-0121548188194f04936b85c984ee677f --out data/processed/reproducibility/new-review-snapshot.zip
```

The default output is `data/processed/reproducibility/owner-review.zip`; that historically audited snapshot already exists locally. Choose a new output name for every snapshot. The builder refuses to overwrite an existing archive. The embedded `REPRODUCIBILITY_MANIFEST.json` lists code identity, selected runs, every member hash, reproduction commands and limits. Package integrity is not scientific acceptance. An independent auditor must verify restoration and the claims attached to each result before the package is publication-ready.
