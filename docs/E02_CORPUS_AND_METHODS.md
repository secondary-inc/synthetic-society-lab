# E02 candidate corpus and frozen methods

The source is the current checkout, not the original handoff's assertions. Existing E02 smoke tests were rerun, then expanded with exact-source import, scoring integrity and analysis-lock regressions.

## Permitted official text candidate set

`configs/e02_official_stimuli.json` contains three exact original US statutory excerpts, totaling 204 whitespace-separated words. The subjects are agency record requests, employee organizing/refraining and air-quality/research purposes. These are real official policy texts, not invented DEMO notices and not current journalism. They were purposively selected to test feasibility rather than sampled to represent public discourse or political viewpoints.

The relevant source HTML, three small granule MODS XML files and GovInfo reuse-policy snapshot are cached in `data/raw/e02_official_sources`. Only the original statute paragraphs are selected; third-party editorial contributions, logos and other material are excluded. GovInfo's public-domain notice and 17 USC 105 provide the US reuse rationale; independent content/rights audit is still required. No worker certification substitutes for that audit, source permissions or the owner's publication approval.

GovInfo MODS fields are copied verbatim, distinguishing edition dateIssued, source ingestion/record dates and laws-in-effect date. Local file receipts are not independent timestamps. Exact publication clock times remain unknown. The texts are not asserted to be current law on the collection date, legal advice, or admissible pre-results forecasting evidence.

Reproduction commands from the project root:

```bash
PYTHONPATH=src .venv/bin/python -m civiclab.e02.stimuli acquire
PYTHONPATH=src .venv/bin/python -m civiclab.e02.stimuli verify
PYTHONPATH=src .venv/bin/python -m civiclab.e02.methods
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v
```

The importer uses an exact official URL allowlist, rejects redirects, bounds response sizes, verifies pinned raw SHA-256 values and unambiguous paragraph selectors, and preserves drift bytes for review rather than silently replacing the frozen source. Cached bytes are not re-fetched. Source drift on a future fresh checkout is an explicit acquisition blocker, not permission to manufacture matching bytes. The package-level MODS initially fetched while identifying the metadata route are larger unused local acquisition artifacts; the reproducible active corpus uses only the seven small manifest-listed files.

## Scientific definitions and integrity

The v2 plan freezes a paired C2-minus-C1 difference in before/after in-party warmth gaps. V241166/V241167 thermometers and fixed V241221 priors remain the primary instrument. Independent/unknown party profiles are retained for quality and absolute-gap secondary reporting, not reclassified after treatment. Primary weighting describes the equal finite engineering pool; it is not a national effect estimate.

`configs/e02_analysis_lock.json` locks 11 plan/protocol/code inputs. Verification only demonstrates those definitions have not changed. It does not demonstrate external preregistration, independent approval, a defensible target population or paid-run authorization. Operational live model/provider, pricing and power decisions remain blocked, rather than being invented from zero-variance mock output.

The evaluator recomputes raw pre/post scores and rejects disagreement with cached derived scores. With frozen assignments, it also validates profile/stimulus/arm coverage, fixed prior, paired seeds/item order, exact exposure and own-baseline carryover, plus request hashes. Invalid raw types and unexpected response fields become quality failures rather than parser crashes or silent imputation. Descriptive secondary and leave-one-stimulus/profile-out outputs are labeled nonconfirmatory. The original DEMO collection remains the only default mocked pilot corpus.

## Population limitation uncovered

The original fit's convergence and small marginal residuals are insufficient for representative validity. Sparse full joint-cell suppression removes approximately 52.20% of training survey weight; retained cells cover only approximately 38.74% of held-out survey weight. New diagnostics retain these values and distinguish them from the existing marginal party discrepancy. The citizen/resident universe mismatch also remains. No poor fit was dropped to make a gate green.

A follow-up will compare defensible support-preserving specifications and investigate an official citizen-adult ACS benchmark before changing population claims. Any such specification is a versioned amendment, not a silent replacement of the frozen original. No real model calls have been made by this worker.
