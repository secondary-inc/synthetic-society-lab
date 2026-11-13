# Research findings log

**Evidence cutoff: November 12, 2026, America/New_York.** The fourth live experiment ended November 13 in UTC. This log covers the completed live studies, population diagnostics and historical election baseline available at this cutoff. It also records consequential methodological limitations and separates engineering checks from scientific results.

The central question is whether added realism in synthetic social research improves useful inference. E02 asks whether news versus social presentation changes a model's answers when content and fictional persona are fixed. E01's intended comparison is synthetic-agent estimates versus simpler election baselines. Neither program is complete.

All results below are exploratory or retrospective. Independent audit means the named evidence, arithmetic and controls were reviewed; it does not mean peer review, human validity or completion of the full research contract. Older evidence files retain their original status fields. Later linked audit receipts govern the scoped acceptance described here.

## E02: four live model studies

The studies contain **32 + 22 + 53 + 40 = 147 recorded model answers**. They measure different outcomes and are not pooled into one treatment estimate. A model answer is not a human participant. These live profiles were authored fictional contexts, not draws from the population-calibration models below.

### E02-01 — No measured partisan-warmth change in the first wrapper pilot

**Question and design.** Does an identical civic notice change the model's partisan-warmth gap differently when labeled as news versus a social post? Four fictional party-prior profiles and two authored civic notices yielded eight matched comparisons and **32 valid baseline/post answers** from GPT-4.1 nano/Azure. Each post included its own earlier answers. The November 5 batch stopped; a continuation completed only the remaining requests on November 8 local time.

**Result.** All within-arm changes and all eight social-minus-news differences were **0 thermometer points**. No matched comparison was excluded. The descriptive bootstrap returned **[0, 0]** because all observed differences were identical.

**Meaning and limits.** These prompts produced no measured partisan-warmth change. This is a narrow null observation, not proof that presentation has no effect. Warmth toward parties may be weakly related to these civic issues. Four comparisons crossed the multi-day batch gap, preventing a clean causal interpretation of the combined contrast. The zero-width bootstrap is not an equivalence test or precise population interval.

Evidence: [result report](reports/E02_LIVE_PILOT_COMPLETE_20261108.md), [aggregate](reports/E02_EXPLORATORY_CONTINUATION_ACTUAL_20261108.json), [independent actual-evidence audit](reports/INDEPENDENT_AUDIT_E02_CONTINUATION_ACTUAL_20261108.json).

### E02-02 — Relevant evidence changed issue support; earlier-answer comparisons were incomplete

**Question and design.** Can a directly relevant support measure distinguish positive from negative evidence, and does displaying earlier answers change that contrast? One fictional library proposal, four fictional contexts and a fixed news wrapper used authored notices describing increased visits, decreased visits or no measured effect. Support used a custom 0–100 scale. GPT-4.1 nano/Azure returned **22 answers**; **six posts were skipped** under the frozen rule. The reference baseline contained a neutral notice, not an unexposed control.

**Result.** Without earlier answers, positive-minus-negative support contrasts were **50, 75, 50 and 50 points**, averaging **56.25** across four contexts. In the **two** contexts eligible for both conditions, the matched mean contrast fell from **62.5 to 0** when all four earlier answers were shown: a **−62.5-point interaction**. All **22 asked factual questions** were correct.

**Missingness and interpretation.** Two baselines had a missing party-thermometer item despite valid issue support; the complete-baseline rule skipped their six follow-up posts. Only the two D-prior contexts contributed to the cue comparison. The prespecified content-sensitive pattern was met; the four-context anchoring-compatible pattern was **not met**. The model responded to relevant evidence, but the incomplete cue comparison does not establish a psychological mechanism or party difference. Changing the supplied evidence does not answer the same-content presentation question.

**Separate secondary measures.** The positive-minus-negative contrast in the in-party minus out-party warmth gap was **0** in both eligible contexts, in each cue condition; the other two contexts were unavailable. That does not mean every warmth response stayed fixed: one neutral-notice repeat without earlier answers changed the gap by **−40 points**; the other 11 valid baseline-to-post gap changes were zero. Neutral-notice support changes were zero in all **four OMITTED** and **two SHOWN** eligible repeats. These quantities are separate from the primary issue-support contrast.

Evidence: [result report](reports/E02_ALIGNMENT_ANCHORING_RESULT_20261109.md), [aggregate](reports/E02_ALIGNMENT_ANCHORING_ACTUAL_20261109.json), [independent actual-evidence audit](reports/INDEPENDENT_AUDIT_E02_ALIGNMENT_ANCHORING_ACTUAL_20261109.json).

### E02-03 — Support-only cues reduced evidence contrasts in the available samples of two configurations

**Question and design.** Does the earlier-answer pattern persist when only the earlier support rating is shown, and in a second fixed model/provider configuration? The same authored library issue and four contexts were tested using GPT-4.1 nano/Azure and Qwen3-30B-A3B-Instruct-2507/Nebius. **53 answers and three prespecified skips** accounted for 56 planned slots. Two saved baselines preceded the November 10 continuation; the timing gap remains documented.

**Result.** Mean positive-minus-negative support contrasts, without versus with the earlier support rating:

- **GPT/Azure:** **33.33 → 0 points**, on the same **three** complete contexts; mean interaction **−33.33**.
- **Qwen/Nebius:** **51.25 → 20 points**, on the same **four** complete contexts; mean interaction **−31.25**.
- **Cross-configuration comparison:** Qwen-minus-GPT interaction **−6.67 points** on the **three common complete contexts**. Subtracting unequal-denominator overall means would be incorrect.

All **53 asked factual questions** were correct. GPT returned three null support items, including the baseline responsible for three skipped posts. Its fourth complete comparison was unavailable. Qwen met its finite within-configuration pattern; the frozen pattern requiring four contexts in **both** configurations was **not met**.

**Meaning and limits.** Earlier support cues were associated with smaller evidence contrasts in the available matched answers. This strengthens a task-specific observation but does not establish a general mechanism. Model, provider, quantization and tokenization varied together; this does not isolate a model-family effect. No significance test or confidence interval was estimated.

**Separate secondary measures.** GPT's positive-minus-negative party-warmth-gap contrast averaged **+20 points in two OMITTED contexts** and **0 in one SHOWN context**; these unequal samples must not be subtracted as a matched effect. The single context common to both had **40 → 0**. Qwen's corresponding four-context contrasts were **−5, 0, −10, −65** (mean **−20**) without the cue and **+10, +5, −60, −20** (mean **−16.25**) with it. These mixed warmth results are distinct from support sensitivity and do not establish human polarization. Neutral-notice support changes were zero in each condition's **three eligible GPT** and **four Qwen** repeats.

For completeness, mean **baseline-to-post warmth-gap changes** for the neutral / positive / negative notices were **−20 / +20 / 0** for GPT OMITTED (two valid contexts each), **−20 / +40 / +40** for GPT SHOWN (two / one / one), **+1.25 / −7.5 / +12.5** for Qwen OMITTED (four each), and **+20 / 0 / +16.25** for Qwen SHOWN (four each). These use an already-exposed reference baseline, not an unexposed control. Missingness and unequal denominators prevent a general before/after or cross-model claim.

Evidence: [result report](reports/E02_ISSUE_CUE_CROSSMODEL_RESULT_20261110.md), [aggregate](reports/E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json), [independent actual-evidence audit](reports/INDEPENDENT_AUDIT_E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json).

### E02-04 — Same-text presentation differences were mostly zero; earlier-answer visibility had mixed effects

**Question and design.** Does news/social presentation affect issue support with identical content, and does showing earlier support alter the difference? Four fictional contexts crossed with two authored topics, library hours and transit access, produced **eight profile–topic units**, eight fresh reference baselines and 32 posts. All **40 answers** were valid and factually correct. NEWS/SOCIAL labels and earlier-support SHOWN/OMITTED were crossed while words and source attribution stayed fixed. One Qwen/Nebius configuration was selected based on earlier completeness.

**Result.** Social-minus-news support differences:

- Earlier answer **omitted:** **0, +5, 0, 0, 0, 0, 0, 0**; mean **+0.625 points**.
- Earlier answer **shown:** **−25, 0, 0, 0, 0, 0, 0, 0**; mean **−3.125 points**.
- Mean paired signed interaction: **−3.75 points**.
- Mean change in the **absolute size** of the difference: **+2.5 points**—one expansion, one contraction and six unchanged. The +5 and −25 occurred in different topic units. No strict nonzero sign reversal occurred.

**Meaning and limits.** Most primary contrasts were zero. Showing earlier answers did **not** generally suppress presentation effects: one difference became larger. A negative signed interaction is not evidence of uniform attenuation. This qualifies the earlier content diagnostics without erasing or pooling them. Text labels are not actual visual feeds or recommendation systems. Both topics supplied positive fictional evidence, the support scale is custom, and no interval or equivalence test was estimated. Eight crossed units are not eight independent people. Source credibility and human persuasion were not tested.

**Separate secondary warmth outcome.** Social-minus-news differences in the in-party minus out-party warmth gap were **0, +6, 0, 0, −25, 0, 0, 0** without the earlier support cue (mean **−2.375 points**) and **−15, 0, 0, +5, −35, 0, +40, 0** with it (mean **−0.625**), with **eight complete units in each condition**. These are post-response wrapper contrasts, separate from issue support and from E02-01's before/after contrast. The means conceal opposing changes and do not establish equivalence or uniform attenuation.

**Topic sensitivity.** The primary OMITTED support contrast averaged **0 for library** and **+1.25 for transit**, each over four units. These are subdivisions of the same eight observations, not independent replications or a basis for general topic differences.

Evidence: [result report](reports/E02_WRAPPER_VISIBILITY_RESULT_20261112.md), [aggregate](reports/E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json), [independent actual-evidence audit](reports/INDEPENDENT_AUDIT_E02_WRAPPER_VISIBILITY_ACTUAL_20261112.json). Run `e02-wrapper-visibility-live-v1-03`, November 12 local / November 13 UTC.

## Population diagnostics: realism must earn its place

### POP-01 — Matching demographic totals concealed sparse support

The initial ANES/ACS fit retained **1,253 training records in 139 supported cells**, reserved **446 held-out records**, and excluded **1,033 training records** in sparse cells. Together with **2,416** records outside the selected weighted fresh sample and **373** age/education/region exclusions, these account for **5,521 input records**.

Calibration matched selected margins closely, with maximum residual approximately **9.70 × 10⁻⁹**, but effective survey sample size was **352.08**, maximum calibration factor **5.40**, and held-out party-share discrepancy **5.70 percentage points**. The suppressed model retained **47.80% of eligible training survey weight** and covered **38.74% of held-out survey weight** in its supported joint cells.

**Meaning.** Matching selected demographic totals did not establish a representative electorate. ANES citizen and ACS resident universes differed; age, household and person denominators constrained valid calibration. These are real data-preparation observations, not model-response or human treatment effects.

Evidence: [population evidence](reports/E02_WORKER_EVIDENCE.json), [independent recalculation](reports/INDEPENDENT_AUDIT_E02_aggregate_recalculation.json), [record-disposition provenance](publications/figures/population-record-disposition.provenance.json).

### POP-02 — The primary hierarchical population model was worse than its simpler comparator

Both replacement candidates retained the same **2,286 training records** and used the same **446 already-inspected held-out records**, resident benchmarks and **2,880-cell** grid. The simpler model combined smoothed marginal distributions; the hierarchy modeled additional conditional relationships.

Weighted predictive log loss—**lower is better**, measured in nats—was **6.93936** for the simpler independent model and **7.16178** for the primary hierarchy H5. Their paired difference was **+0.22242**, with descriptive cluster-resampling interval **[0.05118, 0.41953]**. H1 and H20 sensitivity losses were **7.46003** and **6.96338**; H20's paired interval included zero. No best-performing prior was selected after seeing results. The original suppressed model scored **19.62295** under a declared probability floor, on which that absolute loss materially depends.

**Meaning.** The primary added complexity did not earn adoption. This does not prove that independence correctly describes people. Positive support supplied by smoothing is an assumption. The inspected holdout makes this exploratory model development, not confirmation.

Evidence: [comparison aggregate](reports/E02_POPULATION_SUPPORT_EVIDENCE.json), [independent comparison audit](reports/INDEPENDENT_AUDIT_E02_SUPPORT_COMPARISON.json).

### POP-03 — Citizen benchmarks did not reverse the primary population-model comparison

A matched sensitivity study held records, distributions and scoring rules fixed while comparing resident targets with citizen-age-25+ targets. It evaluated **40 configurations with zero failures** and **66 paired contrasts**. Two executions reproduced **45 deterministic artifacts** exactly.

Under central citizen targets, loss was **6.94195** for the independent model and **7.16397** for H5. Their paired difference was **+0.22202**, with descriptive resampling interval **[0.05165, 0.41974]**. H5 remained worse under both constructions. Citizen-minus-resident loss changes were approximately **+0.00259** and **+0.00219**, respectively; both descriptive intervals included zero.

Eight predefined rounded-input perturbations produced losses **6.941846–6.942063** for the independent model and **7.163865–7.164077** for H5. These are finite observed sensitivity ranges, not worst-case bounds or Census sampling intervals. H1/H20 sensitivity conditions remain in the aggregate.

**Meaning.** Changing the benchmark universe did not rescue the primary hierarchy. It does not estimate a causal citizenship effect or solve national/state representativeness, age coverage, household/group-quarters differences, model-response validity or full survey-design uncertainty.

Evidence: [comparison aggregate](reports/E02_CITIZEN_COMPARISON_V1_ACTUAL_EVIDENCE.json), [independent actual audit](reports/INDEPENDENT_AUDIT_E02_CITIZEN_COMPARISON_ACTUAL.json), [figure provenance](publications/figures/e02-citizen-primary-comparison.provenance.json).

## E01: a real historical baseline, not an agent forecasting result

### E01-01 — Prior same-seat margins beat a tied-margin comparator on 30 historical Senate states

**Design.** The diagnostic started with 33 regular Class-I Senate constituencies and required a Democratic and Republican nominee in both 2018 and 2024. California, Nebraska and Vermont were structurally excluded, leaving **30 states**. The outcome was the Democratic-minus-Republican margin conditional on those parties' votes—not all-candidate vote share or the actual winner's probability. Maine remained included despite its independent winner.

**Result.** Carrying the **2018 same-seat margin** forward, with zero national/incumbency adjustments, produced **10.1993 percentage-point mean absolute error** for 2024. Predicting a tied D–R margin produced **18.1883**. The paired persistence-minus-tie error difference was **−7.9890 points**. Leave-one-state-out paired means ranged from **−8.7247 to −6.5241**; this is descriptive sensitivity, not a confidence interval.

The source audit checked **120 official candidate counts** and retained **nine explicit corrections** to discovery-source counts. Disagreeing races were not removed to improve performance. Two recorded runs reproduced the same summary. No agents or fitted coefficients were used; model/API spend was **$0**.

**Meaning.** A transparent same-seat baseline was informative on this historical cohort. Researchers had access to outcomes while validating sources, so this was post-hoc, not an untouched holdout. It does not establish prospective performance, 2026 accuracy, general forecasting superiority or incremental value from AI agents.

Evidence: [historical aggregate](reports/E01_HISTORICAL_EVIDENCE.json), [independent historical audit](reports/INDEPENDENT_AUDIT_E01_HISTORICAL.json), [protocol](protocols/E01_SENATE_2018_2024_DIAGNOSTIC.md), [figure provenance](publications/figures/e01-historical-errors.provenance.json).

## Methodological and engineering findings

- **Missingness can change the question being answered.** Missing unrelated thermometer items prevented otherwise valid support comparisons in E02-02. E02-03 narrowed eligibility to support, but a missing support baseline still prevented a complete context. Neither study repaired or silently replaced missing answers.
- **A signed decrease is not necessarily a smaller effect.** E02-04 had a negative mean signed interaction while average absolute presentation differences increased. Direction and magnitude must both support an attenuation claim.
- **Factual accuracy and attitude sensitivity are distinct.** All asked factual items were correct in E02-02, E02-03 and E02-04 even when support answers were missing or changed. These simple authored questions are not a broad accuracy benchmark.
- **MOCK tests validate software, not social effects.** The initial mock pilot used 12 profiles × three stories × five arms: 180 units and 360 mocked pre/post calls. Its programmed +2-point contrast and [2, 2] interval were fixture properties. Scripted assistant conditions were not live assistant research. E01 DEMO errors used invented inputs. [Initial engineering evidence](reports/ENGINEERING_EVIDENCE_20261103.json).
- **Source acquisition and retained arithmetic are narrower than population acceptance.** The Wyoming full-adult pipeline has scoped engineering/replay acceptance; DC archive metadata and official election-document captures have separate source-level acceptance. None establishes nationwide population validity, complete 2026 ballots or accepted 2026 forecast inputs. Private cell values are not reproduced here. [Wyoming audit](reports/INDEPENDENT_AUDIT_E02_F_WY_REAL_NATIVE_ENGINEERING_v1.json), [DC metadata audit](reports/INDEPENDENT_AUDIT_E02_N2A_DC_ACTUAL_METADATA_v1.json), [election-document audit](reports/INDEPENDENT_AUDIT_E01_CLERK_DOCUMENT_CAPTURE_V1_ACTUAL.json).
- **Independent review found failures normal-path tests missed.** Initial probes found false-like enablement, uncertain-billing cancellation handling, interrupted-finalization recovery and empty-contract completion errors. Fixes and rerun probes are preserved; this is not proof of defect-free software. Later failed configurations, stopped runs and pending recovery remain in the [operational status](reports/STATUS.md) and [audit archive](reports/). [Initial independent audit](reports/INDEPENDENT_AUDIT_G0.md).

## Costs and reproducibility

Verified generation charges for the four E02 studies were **$0.0014340**, **$0.0016084**, **$0.0038870** and **$0.0028919**, totaling **$0.0098213** for 147 research generations. This is accounting, not pooled evidence or total project cost. Conservative recorded exposure was **$0.012221**, including per-generation rounding and four unchanged historical holds. It is not an account invoice; labor, energy and infrastructure are unpriced.

The cumulative E02 ceiling remains **$1**, within the shared **$5** ceiling; E01 paid inference remains **$0**. Research requests use OpenRouter. Raw responses, financial stores and credentials remain outside Git. Public aggregates identify run IDs, code/input hashes, exclusions, serving configurations, usage and audit lineage. Qwen service tier remains UNKNOWN where reported null; streaming telemetry differs from nonstreaming requests and remains unresolved. No silent provider fallback or general service behavior is inferred.

A fresh clone can run fixture tests and inspect public aggregates. Full raw-response rescoring requires retained private journals; real-data rebuilding requires the exact permitted source files. Do not rerun consumed paid launchers. See the [reproducibility guide](publications/REPRODUCIBILITY.md).

## What remains unanswered

- Whether realistic presentation, source attribution, live assistants or swarms add value over matched simpler controls.
- Whether model responses agree with comparable human experimental results.
- Whether an accepted population construction supports the original national adult/state scope.
- Whether licensed real-news or X/Meta stimuli change the conclusions. Platform-data plans are proposals, not acquired-data findings.
- Whether synthetic-agent forecasts improve on statistical baselines for a valid common race sample. No prospective 2026 forecast is established.

The full [completion contract](configs/completion_contract.json) remains open. E03/E04 stay deferred. This public log does not release an external journal article or promote draft manuscripts to validated publications.

## Updating this log

Add dated entries with the frozen question, complete planned/observed denominators, numerical findings, source report and independent audit. Keep nulls, failures and exclusions. Label exploratory follow-ups and outcome-informed choices. Correct summaries explicitly rather than overwriting historical evidence or pooling incompatible studies. Operational details remain in the audit archive to keep the scientific account readable.

**2026-11-12 — Initial consolidated public log:** four live E02 studies, three population diagnostic entries, one historical E01 baseline, and the methodological/engineering boundaries above. Later audits supersede historical pending labels only within their named scope.
