# Synthetic Society Lab Limitations and Failure Analysis

Owner-review draft. Updated November 10, 2026 UTC. This report covers the current engineering snapshot and the full research program, including work not yet executed. Independent audit and requirement status are authoritative for completion.

## Scientific scope

Synthetic respondents are model outputs, not sampled humans. Randomizing a prompt can identify a causal effect on a specified model configuration under that prompt distribution; it does not establish human persuasion, polarization, trust change or voting behavior. A plausible persona cannot validate the response mechanism. ANES is a baseline human survey distribution, not an exposure-matched human control group.

The initial primary outcome is an in-party/out-party thermometer gap. It is not a general ideology scale or validated measure of all forms of polarization. Fixed prior party identification determines orientation, and independents are excluded from the primary estimand by definition. Exclusion changes the target population and must remain explicit. Range normalization by 100 does not create a standard-deviation effect size.

## Population and sampling

The initial fit concerns fictional profiles age 25+, not all eligible voters. ANES citizenship, residence, recruitment mode and sample design differ from the ACS resident margins. Education and household income use different universes; forcing their totals onto the same person weights would create an unsupported target. Race and household-income files currently serve as audit references rather than calibration targets.

Coarsened joint-cell suppression removes sparse combinations. In the initial recorded fit, 1,033 training records were excluded and 1,253 retained. Calibration can amplify a narrow support set while matching selected margins nearly exactly. Effective sample size, weight concentration, held-out associations and population transport matter more than numerical convergence alone. The 12-profile engineering sample cannot support state estimates. State coverage labels would not create state representativeness.

The independently checked support-preserving comparison is exploratory: its holdout had already been inspected, the common uniform floor affects the suppressed model’s absolute log loss, and uniform cluster resampling is not a complete survey-design variance estimator. Full smoothed grid support is imposed. The primary hierarchical candidate performed worse than the simpler independent model and was not promoted; sensitivity settings remain reported without selecting a winner.

The subsequent40-configuration citizen/resident benchmark comparison uses the same inspected regional25+ cohort. S0501-derived citizen targets do not resolve ANES household versus Census group-quarters coverage, missing young adults or state representativeness. Eight compensating transfers in rounded input percentages describe only those finite directions, without latent-vector feasibility guarantees, worst-case bounds or ACS sampling uncertainty. Conditional cluster-resampling intervals omit target-estimation covariance and full survey-design uncertainty. Citizen-minus-resident contrasts compare benchmark constructions, not causal effects of citizenship. Independent arithmetic acceptance does not open the original population-validity gate.

A later Wyoming-only adult-source engineering run passed independent retained-artifact review (`reports/INDEPENDENT_AUDIT_E02_F_WY_REAL_NATIVE_ENGINEERING_v1.json`). The reviewed parser processed29,297 source rows per sweep, including23,066 adults, and both outputs replay exactly. Independent review reconstructed aggregate and uncertainty arithmetic from saved primitives; it did not rescan or independently reclassify raw person rows. Other states remain missing, and the original population-fit validity problems remain unresolved. No fit, disclosure or dashboard adoption follows from this engineering receipt.

Survey cluster holdout checks do not establish external validity for generated model attitudes. Missing values, mode differences, top coding and questionnaire-version discrepancies can alter mappings. New fitting specifications require documented deviations and fresh independent review rather than post-hoc selection for desirable synthetic behavior.

## Stimuli and treatments

The original three notices are fictional engineering fixtures. The newer official-text acquisition work concerns dated government documents, not a representative sample of contemporary political news. Public availability does not automatically establish rights for every item on an official website; original statutory content, metadata, editorial additions and third-party material require separate treatment.

Text wrappers manipulate textual cues, not visual layout or realistic scrolling. Identical source attribution must be retained when testing the wrapper alone. Source-label changes, factual changes, emotional intensity, story selection and dose can otherwise confound interpretation. Actual public posts or ad libraries do not reveal individual personalized feeds. No exact X, Instagram or Reels experience has been reconstructed.

The original C3/C4 Q&A is scripted. It is not evidence about live assistant mediation, source retrieval or hallucination. Removing a wrapper from an observed pair is a recorded comparison; inventing a new unexecuted response would not be a counterfactual result.

## Measurement and statistical uncertainty

The completed limited live pilot has 32 valid answers and eight complete matched blocks, with all measured partisan-gap changes zero. Its `[0,0]` descriptive bootstrap is degenerate, not an equivalence bound. Four blocks compare arms from different execution batches; two are original-only and two continuation-only. The same dated model label does not prove stable service internals across that gap. Only four authored party-prior profiles and two fictional civic notices were tested, with own-baseline answers included in post prompts. These conditions limit sensitivity and external validity; no human anchor or representative population was used. See the [independent outcome audit](../reports/INDEPENDENT_AUDIT_E02_CONTINUATION_ACTUAL_20261108.json).

The mock provider intentionally programs its effect. A narrow or degenerate interval around that known value measures fixture structure rather than certainty about humans or an LLM. Repeated calls from the same model are not independent people. Profiles share survey priors and stimuli share text, so both sources of dependence matter.

A small stimulus set provides weak support for generalizing across news. Repeated seeds do not repair missing stimulus diversity or prompt sensitivity. Real models may disregard seeds, change serving revisions, refuse selectively or generate invalid survey answers. Those outcomes must remain in quality reporting. The primary contrast and any secondary/sensitivity families require a frozen analysis plan, adequate sample design and explicit multiplicity treatment before confirmatory interpretation.

Existing saved derived scores require recomputation from raw pre/post answers when evaluating; cached values alone are insufficient evidence. The current request-binding and raw-scoring corrections have independent audit receipts; old artifacts retain the implementation limits of their recorded versions. Selected moment matching and a few held-out descriptive checks do not validate all joint associations or demographic subgroup behavior.

## Elections and historical contamination

No independent pre-results 2026 forecast archive has been verified. Retrospective work cannot be backdated. Model training may contain historical returns and political narratives; sealing local input files does not remove model knowledge or operator exposure. A non-LLM historical baseline avoids some model-memory concerns but still requires honest sample selection and parameter freezing.

House boundaries can change across years, and regular Senate seats follow different election cycles. Two-party denominators, fusion-party lines, independent candidates, redacted votes, TOTAL/component reporting modes, specials, runoffs and uncontested sentinels can change totals. Official candidate registration is not official ballot certification. Maps require a verified vintage and justified crosswalk, not matching labels alone.

The accepted 2018→2024 diagnostic excludes three structurally ineligible states and measures conditional D–R margins, including Maine where an independent won. Nine count corrections use authoritative government totals after target-data inspection. Its 30-state cohort is post-hoc, not an untouched holdout. The leave-one-state-out range is descriptive sensitivity, not a confidence interval. Official result publications verify retrospective participants, not pre-election ballot certification.

A small or deliberately competitive race sample cannot establish universal forecasting superiority. National shocks create correlated errors. Same-race paired comparisons, prespecified weights, outcome-source checks and transparent exclusions are required. Actual 2026 retrospective evaluation also depends on authoritative outcomes and certification availability.

## Operational safety and reproducibility

Local hashes establish byte consistency rather than independent timing, source authenticity or immutable public publication. Python runtime I/O guards protect trusted prediction code from accidental reads; they are not an adversarial OS sandbox. A stripped environment and separated evaluator cannot prove that an operator never observed held-out outcomes.

Independent audit found false-like flag handling, post-dispatch cancellation accounting and interrupted-finalization recovery failures. The lead fixed them and the auditor reran those probes. Their discovery shows why tests that only mirror normal execution are insufficient. Further failures remain possible, particularly around abrupt process termination, concurrent metadata updates and provider billing behavior.

OpenRouter is the only network inference gateway. The limited live E02 sample has independently verified research bills totaling $0.0014340. At first-pilot completion the shared ledger counted $0.002857 conservatively, including three unchanged holds; these are budget reservations, not an invoice total. One earlier compatibility dispatch still lacks a verified provider charge. A recovered original E02 answer has verified billing but retains its original uncertain financial row and full hold. Thus analytical completeness does not erase historical financial uncertainty. Standing caps remain $5 shared, $1 current E02 pilot and $0 paid E01. New batches require tested finite plans; consumed launchers cannot be rerun. Local labor, energy and infrastructure costs are unpriced.

Some received sources lack reproducible reacquisition URLs or importer evidence even though local hashes pass. Raw files excluded from Git will not reappear in a fresh clone. The review package can reproduce bundled artifacts and fixture tests, but full real-data reconstruction requires the exact permitted source inputs. Remote CI and GitHub delivery require separate verification for each exact source snapshot.

## Publication and organization claims

The dashboard, figures, manuscript and blog are local review materials. No owner approval exists for public release, affiliation claims or political activity. The program must not use generated people or votes as observations, silently discard failed configurations, change denominators to favor complexity, or describe unrun experiments as findings.

The complete contract still requires genuine E01/agent comparisons, accepted real-model E02 evaluation and sensitivity analyses, independent milestone review, passing CI and a verified reproducibility package. Drafts do not satisfy those scientific requirements merely by existing. Current unresolved items remain visible in the completion dashboard.

The DC archive acquisition validates compressed bytes and limited metadata, not the person records or an adult population. The dated federal nominee compilation is an additional source role, not state final-ballot certification or proof of latest amendments. The2020 historical document still needs validated event/stage/seat-class and party-line aggregation before it supplies an original2026 same-seat baseline. The earlier run02 terminal continuation stopped before any model/statistics request with independently verified zero consumption. The later run03 attempted a POST and left uncertain billing, as detailed above; neither establishes successful compatibility.

Independent review found a package capture race: an artifact could change after run verification and be archived with its stale checksum ledger. The original candidate/source/finding remain preserved. The separate v2 remedy binds captured artifact and checksum bytes to the originally verified seal, with adversarial reseal tests. Its component acceptance does not certify any newly assembled archive, full restoration, hostile-host resistance or scientific result.

## November 10 election-reader qualification

The [accepted generated-fixture runtime check](../reports/INDEPENDENT_AUDIT_E01_DIRECTORIES_QUALIFICATION_ACTUAL_20261110.json) covers four reader entries and 119 page markers in each of warmup and strict qualification, two expected strict negative cases, and recorded runtime/backend identities. The auditor validated closed metadata rather than independently rereading installed binaries or source PDFs. Generated fixtures do not establish extraction fidelity for acquired encodings, fonts or layouts. No actual election source was read or admitted; source-format inspection, count aggregation, final-ballot validation and forecast evaluation remain separate. Earlier failed scopes remain failed and consumed. No model cost was incurred by this qualification.

## November 9 live follow-up

The new issue-aligned result uses one custom question, one fictional library issue, one model/provider family and four technical contexts. It is exploratory after the first study's zero change. Both R-prior baselines had missing Democratic-party thermometers; the frozen complete-baseline rule therefore skipped six SHOWN posts. The primary omitted-answer contrast uses four contexts, whereas the own-answer interaction uses only two D-prior contexts. Do not subtract unequal-denominator means, infer a party difference, generalize a mechanism or claim human effects. All asked factual items were correct; the planned-denominator task-following flag reflects skips. No inferential interval was estimated. Across both distinct studies, verified research cost is $0.0030424; conservative owner exposure at that November 9 checkpoint was $0.004473, with all three old holds unchanged. See the [follow-up report](../reports/E02_ALIGNMENT_ANCHORING_RESULT_20261109.md).
