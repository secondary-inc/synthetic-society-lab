# Synthetic Society Lab

**Does making an AI simulation of society more realistic make its answers more useful and reliable?**

We test that question with controlled experiments and transparent statistical baselines. The project studies model behavior; simulated people are not observations of real people.

## What we are studying

- **E02 — The Information Effect:** Does presenting the same political information as news versus a social-media post change an AI model's expressed issue opinions or institutional trust? We hold the model, fictional persona and underlying text fixed. Later comparisons examine source attribution and assistant interaction.
- **E01 — Feed to Ballot:** Do synthetic-agent election estimates improve on simple statistical baselines? This work is retrospective. No independently verified prospective 2026 forecast has been established.

E02 is the primary experimental track. E01's statistical baseline proceeds separately. City and government simulations, E03 and E04, remain deferred.

## What we have found so far

**Evidence snapshot: November 12, 2026, America/New_York. Four exploratory live E02 studies, 147 model answers, no human participants. The full research program is incomplete.**

1. **The primary presentation measures were mostly unchanged in the small tasks tested.** The first study found zero changes in its partisan-warmth measure. In the latest same-text comparison, seven of eight issue-support contrasts were zero when earlier answers were omitted; the remaining contrast was +5 points. Secondary party-warmth results included nonzero differences. This does not establish that presentation never matters.
2. **Models responded to directly relevant issue evidence.** On a fictional library proposal, positive versus negative evidence produced different support ratings. Showing a model its earlier answer reduced that evidence contrast in the available matched comparisons. Missing answers prevented the full prespecified cross-configuration pattern from being met.
3. **Earlier-answer cues do not have one general effect.** In the latest presentation study, showing the earlier answer increased one wrapper difference, reduced another and left six unchanged. The result does not support a general claim that earlier answers suppress presentation effects.
4. **A more elaborate population model did not outperform its simpler comparator.** On the inspected survey holdout, the primary hierarchical model had worse predictive log loss under both resident and citizen benchmark constructions. Matching demographic totals alone did not establish representativeness.
5. **A simple historical election baseline was useful.** Across 30 eligible Senate states, carrying the 2018 margin forward to 2024 had mean absolute error of **10.20 percentage points**, compared with **18.19** for predicting a tied Democratic–Republican margin. This was a post-hoc diagnostic, not evidence that AI agents improve election forecasting.

**[Read the complete findings log →](FINDINGS.md)** Each entry includes the question, sample, numerical result, interpretation, limitations and links to the detailed evidence and independent review. Null results, missing answers and findings unfavorable to added complexity are retained.

These results do **not** establish human persuasion, a representative electorate, realistic personalized feeds or general model behavior. The live studies used project-authored fictional civic notices and small purposive sets of fictional contexts. Actual X/Meta content, licensed real-news trials, human-study validation, live assistant comparisons and swarms have not supplied these findings.

## Explore the research

- [Findings log](FINDINGS.md) — public-facing results and evidence trail.
- [Current operational status](reports/STATUS.md) — completed work, failures and unresolved gates; dated older checkpoints remain historical.
- [Research blueprint](CODEX_MASTER_EXECUTION.md) and [post-election direction](docs/RESEARCH_DIRECTION_20261112.md).
- [E02 protocol](protocols/E02_INFORMATION_EFFECTS.md) and [E01 retrospective protocol](protocols/E01_RETROSPECTIVE.md).
- [Data sources and access boundaries](docs/DATA_SOURCES.md).
- [Reproducibility guide](publications/REPRODUCIBILITY.md) and [limitations](publications/LIMITATIONS.md).

The [technical manuscript](publications/TECHNICAL_PAPER_DRAFT.md) and [blog manuscript](publications/BLOG_DRAFT.md) remain drafts, not peer-reviewed publications. Independent review accepts only the specific evidence and scope named in each receipt. Historical aggregates may retain their original pending label; the later linked audit records any subsequent acceptance.

## Run the offline checks

Python 3.11+ on macOS/Linux is supported. From a checkout:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[selection]'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/civiclab validate-sources --fixture-only
.venv/bin/civiclab modules
```

These checks use authored fixtures; they do not reproduce private raw responses or prove scientific effects. The optional PDF reader uses the `geometry` extra; see [runtime notes](docs/GEOMETRY_RUNTIME_V1_7.md). Real-data reproduction requires the exact permitted inputs described in the [reproducibility guide](publications/REPRODUCIBILITY.md). Never rerun a consumed paid-study launcher to reproduce an analysis.

The repository includes code, protocols, public aggregates, provenance and independent audit receipts. Credentials, raw survey/publisher data and private model journals stay outside Git. MOCK/DEMO outputs remain labeled. The viewer is local; no public interactive dashboard is deployed.

The four live E02 studies recorded **$0.0098213 in verified generation charges**. That is not the project's total cost: conservative recorded financial exposure was **$0.012221**, including outstanding historical holds and rounding, and labor/infrastructure are unpriced. The cumulative E02 ceiling remains $1 within the shared $5 ceiling; E01 paid inference remains $0. See [accounting scope](FINDINGS.md#costs-and-reproducibility).
