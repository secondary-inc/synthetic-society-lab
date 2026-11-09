# E02 alignment and own-baseline follow-up v1

**Frozen exploratory methods candidate, prepared November 9, 2026. No new outcomes collected or execution authority created here.** The exact machine-readable protocol is `configs/e02_alignment_anchoring_followup_v1.json`; the pure planner/parser/scorer is `src/civiclab/e02/alignment_anchoring_v1.py`. This is the next small real-batch preparation, subject to independent methods/code and exact financial/caller review. Preserve the completed original 32-response study, including its stopped predecessor, continuation and all-zero thermometer result.

## Question and fixed sample

The prior result does not distinguish insensitive measures, weak content alignment, own-answer cueing, stable model preferences, or a lack of wrapper response. This new study asks whether support for the actual fictional library proposal responds to directional visit evidence, and whether inserting the model's exact own baseline attenuates that response. It fixes the simpler news-card wrapper. It does not retest social-versus-news framing, human persuasion, nationwide populations or a validated psychological scale.

Use the four original project-authored ID/party contexts, two D and two R, with no demographics or numerical prior ratings. These are technical seed/item-order contexts, not four independent people. Party identification stays supplied in both conditions; it is not elicited from the questionnaire. The four new measured baselines are elicited model answers. No old answers become new baselines.

There are exactly **28 planned model calls: four neutral/reference-notice baselines and 24 posts**. Each context crosses three notices with SHOWN versus OMITTED own-answer contexts. The four baselines run first; the 24-post execution order is seeded and frozen in the config. All calls are fresh stateless two-message sessions. Same-profile item order and pair seed stay identical across all six posts. Provider seeds do not guarantee deterministic responses.

## Instrument and manipulation

The Democratic and Republican party questions and 0–100 thermometer administration remain the existing ANES-adapted wording. They are separate secondary measurements. The new primary question is **“How strongly do you support or oppose the proposed Exampleville library schedule?”**, on 0 strongly oppose, 50 neither, 100 strongly support. It is explicitly custom, exploratory and unvalidated in humans.

The objective comprehension item asks which measured change in total library visits is reported. Its allowed strings are `INCREASE_40`, `DECREASE_40` and `NOT_REPORTED`. The response object has exactly four keys: `democratic_party`, `republican_party`, `library_support`, `visits_change`. Nulls remain missing, never zero or neutral imputation. Correct comprehension is a task-following/manipulation check, not a known model or human opinion effect.

All three project-authored DEMO notices describe the same fictional proposal: move existing staff hours to provide two additional evening library hours on weekdays, retain the stated staffing budget, and await the council vote. Only one final evidence sentence changes: no measured visit effect is reported (N01); a completed fictional pilot reports 40% more total visits (N02); or it reports 40% fewer visits (N03). These are separate counterfactual fictional worlds, not empirical claims or real trials. The source label, wrapper and all common wording are identical. The model does not receive notice IDs, answer keys, condition labels, directional hypotheses or analysis rules.

The four baselines already see N01. They are **neutral/reference-notice baselines, not unexposed baselines**. N01 is a no-measured-data reference, not a placebo-equivalence condition. Higher visits are not assumed to force support; a model may reasonably keep its support unchanged.

For a matched post pair, the entire request is identical except that SHOWN inserts `pre_response` with **all four exact own-baseline fields**, while OMITTED has no such field. The same supplied party prior remains in both conditions. Thus “OMITTED” does not mean free of all priming or anchoring: it removes only the elicited own-answer cue. Whole-answer context, including previous factual response and thermometers, is the manipulation; it is not support-only numerical anchoring.

## Frozen estimands and diagnostics

Primary: equal-context mean of `support(N02,OMITTED) − support(N03,OMITTED)`, range −100 to 100 points. Show all four paired values, complete/planned denominators, mean and min/max.

Key secondary anchoring diagnostic: equal-context mean of `[support(N02,SHOWN) − support(N03,SHOWN)] − [support(N02,OMITTED) − support(N03,OMITTED)]`, range −200 to 200. Show each context and missing reasons. Do not replace the primary with whichever result is favorable.

Also report neutral-reference post minus own baseline support; partisan-gap changes with fixed D/R scoring direction; and comprehension correct/planned and correct/valid by notice/context. Primary support remains eligible when comprehension is wrong or an unrelated thermometer is invalid, provided the object has the exact key set and support is valid. Comprehension is never a primary exclusion gate.

There is one primary descriptive contrast. All other outcomes are exploratory diagnostics, without significance claims. No confidence interval, bootstrap, p-value or equivalence test is estimated for four purposive technical contexts and one issue. The interval field is null with an explicit NOT_ESTIMATED reason, not a zero-width interval. This batch does not estimate independent-person, stimulus-sampling or repeated-serving variance.

The config freezes limited pattern summaries before new data: a content-sensitive pattern requires all four primary contrasts, at least three positive, a positive mean, and at least six of eight planned directional-notice comprehension answers correct in OMITTED. An anchoring-compatible pattern additionally requires all four interactions, at least three attenuated, and a negative interaction mean. Complete zero support contrasts plus adequate comprehension is labeled support-stable/notice-understood, never equivalence or proof that information has no effect. Low comprehension is reported as a concern without discarding numeric outcomes. These labels summarize this finite task; none identifies a human psychological mechanism.

## Invalid answers, stopping and reproducibility

Malformed JSON, duplicate/nonfinite members, non-object JSON and bounded-representation violations yield explicit parse errors. An exact-key object is scored item by item. Missing/extra keys invalidate all items; booleans are not numbers. No repair prompt, imputation, repeated baseline or answer replacement occurs.

A SHOWN post requires its own baseline to have all three valid numeric ratings and an allowed comprehension string. A wrong but allowed comprehension answer remains eligible and is shown unchanged. If the baseline fails, skip its three SHOWN posts with no dispatch; the three OMITTED posts still run. Each named contrast uses exactly its required valid values. Zero complete primary pairs yields null estimates, not zero. All failed, skipped and unattempted jobs remain in the final 28-disposition record.

Financial, identity, clock, unsupported activity or persistence failures stop the whole batch and retain conservative holds. Each dispatched generation has at most three billing GETs, with bounded 10/10/20-second waits inside its original 120-second phase; only reviewed 404 recovery is allowed, never another model POST. Insufficient time or unavailable billing stops rather than extending limits. The existing source/response privacy and serving-provider/native-usage safeguards remain mandatory.

The pure `next_action` recompiles every request from the frozen config and validated prefix, including the exact own baseline only when SHOWN. The final `response_envelope(protocol_bytes, transcript_bytes, response_provenance=..., stopped=...)` exports all dispositions from an owner-authenticated transcript. Without optional price terms it verifies structural ordering/skip rules but does not independently authenticate payload hashes; the financial owner must already have done that. Passing `terms=` also replays exact compiled hashes. `analyze` recomputes item outcomes from raw answers and checks protocol/instrument/assignment binding. No model judges its own score.

## Calls, costs and minimal integration

Freeze the same model/provider/route: `openai/gpt-4.1-nano`, Azure family, `azure`, temperature 0, no fallback/tools/plugins, JSON object, maximum 256 output tokens. A fresh exact financial release determines actual serving identity and prices. No model change, automatic resampling or post-outcome tuning is authorized by this protocol.

Maximum 28 POSTs, 84 billing GETs, 8,192 input-bound tokens and 256 output tokens per call; total at most 236,544 tokens. The per-call reservation ceiling is **1,785 microdollars**, and the new batch subceiling is **50,000 microdollars ($0.05)**. At that ceiling 28 calls reserve at most 49,980 microdollars. This is within the existing cumulative E02 $1 and shared $5, including every old settled charge and hold; no fresh allowance is created.

For comparison only, the prior reviewed 0.143/0.44 USD-per-million input/output bounds and no added request fee give **1,285 microdollars per maximum-sized call, 35,980 microdollars for 28**. That is a conditional price calculation, not the 1,785 ceiling and not a current authenticated quote. Root must verify fresh all-in route pricing and headroom for the complete batch before dispatch. Retain all actual costs, provider identity, tokens, errors, code/input hashes and run IDs. Root uses a separately bounded 384-artifact private journal for worst-case billing intents; this pure module creates no files or authority.

The old compiler hard-pins the earlier two-item protocol and cannot execute this new questionnaire unchanged. The new pure module supplies a small data-driven request planner, strict parser and independent scorer. Root owns the specific same-owner append-only financial adapter and caller; existing checked transport, privacy checks, reservations and billing reconciliation are reused. No new platform, national dataset, news acquisition or dashboard is prerequisite.

## Acceptance and end of batch

Before live data: independent methods review; deterministic changed/unchanged/invalid-answer oracles; exact request ablation and seed/order tests; pure prefix/stop/no-retry checks; and independent root financial/caller review with fresh prices and cumulative cap evidence. A changed mock (primary 60, interaction −30) verifies arithmetic only and is never described as an empirical model positive control.

After live data: independently reconstruct all item scores, exclusions, contrasts and factual checks from the saved raw responses, and report every condition and cost. Preserve the old pilot separately. Stop at the fixed batch regardless of results; do not automatically scale, modify stimuli, add a model or pursue a favorable outcome. Full E02 scientific validity and human anchoring remain later gates.
