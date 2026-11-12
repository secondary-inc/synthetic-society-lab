# E02 wrapper by prior-answer visibility: proposal v1

November 12, 2026. **Exploratory proposal pending independent methods review.**
Not frozen, registered, implemented, confirmatory, released or executed. The
exact candidate texts, instrument, 40-slot schedule and limits are in
`configs/e02_wrapper_visibility_proposal_v1_20261112.json`. Results are null.
The three earlier studies retain their own protocols and separate outcomes.

## Finite scope and reason for this design

Return to the original identical-content presentation question: does changing
only a news-article versus social-media-post label change issue support when
prior answers are omitted? Does providing own earlier support modify that
wrapper contrast? Cross these two factors rather than infer that cue visibility
explained an earlier study with different outcomes and prompts.

Choose two topics, library hours and bus-route access, with four existing
fictional party-prior contexts (2D/2R), one fixed Qwen3-30B-A3B-Instruct-2507 /
Nebius nebius/fp8 configuration and one generation per cell. Eight common
reference baselines plus32 posts (8units x2wrappers x2visibility levels) permit
40 calls maximum. This is the smallest recommended next diagnostic: one topic
would repeat the earlier topic-specific limitation, and adding a second model
would double this factorial from40 to80 calls before learning whether the
unmasked wrapper contrast is informative. Model choice is informed by prior
Qwen item completeness, not a new outcome; disclose this selection and do not
generalize to model families. GPT replication remains separately proposed and
reviewed, not an automatic adaptive extension.

Both topics use project-authored DEMO text and a fictional positive40% visit/trip
finding; neither is real evidence or sampled from a population of topics. This
avoids bundling a content-direction factor into the next small factorial. It
also limits inference to positive evidence in these two selected civic scenarios;
negative-valence generalization is untested. Library words reuse earlier authored
reference/positive notices; transit words and both exact questions are supplied
in full in the config. No new publisher rights or acquisition is assumed.

## Treatment identity and instrument

Use one canonical treatment body and fixed source label per topic across all
four cells. The only model-visible differences are presentation_label equal to
`news article` or `social-media post`, and presence or absence of exactly
`pre_response:{policy_support:<own valid reference rating>}`. A simpler matched
news-label condition exists at each visibility level, and OMITTED is the simpler
visibility control at each wrapper. No other baseline answers are forwarded.
Do not add source brands, answer keys, mode labels, social metrics, comments,
ranking or another instruction in one arm only. This tests a textual format
label, not visual scrolling, an authentic platform, source credibility or
personalized recommendation. Hold source attribution constant; a separate
source-factor study would be needed to answer that part of the blueprint.

Every call is isolated. Each unit's baseline sees the same neutral/reference
notice, the common reference-survey label, and no previous answer. It is not an
unexposed baseline and does not favor either post wrapper. Post content supplies
the fictional positive finding. The common system explicitly allows any supplied
prior response; this administration differs from earlier prompts and is not a
replication or pooled continuation of them. The cue may create a consistency
demand; the design does not identify an anchoring mechanism.

Four requested keys: democratic_party, republican_party, policy_support,
factual_answer. Thermometer wording/instructions retain the prior ANES-adapted
party items, separately scored. Each topic has its exact support question and
factual-change question. Support is a custom unvalidated0–100 item; factual
answers are INCREASE_40 or NOT_REPORTED (or null). Null indicates refusal or
unknown. There is no institutional-trust/certainty measurement claim.

## Primary estimand and missingness

For each profile-topic unit i, primary W_i is support(SOCIAL,OMITTED) minus
support(NEWS,OMITTED), range[-100,100]. Both OMITTED post supports must be valid;
a missing pre never excludes a valid W_i. Report eight planned units, raw values,
complete counts per topic and overall mean/min/max on complete pairs. An8/8
result supports a full planned-sample descriptive headline; otherwise label
DESCRIPTIVE_PARTIAL and disclose which topics/party contexts are missing. A null
mean is required when no pair is estimable; never substitute zero.

Key secondary I_i is [SOCIAL_SHOWN-NEWS_SHOWN] minus W_i, range[-200,200]. It needs
own valid pre and all four post supports. Compare SHOWN and OMITTED wrapper
contrasts on that same common intersection, never unmatched marginal means.
Also report absolute-magnitude change |W_SHOWN|-|W_OMITTED| and sign reversals:
a signed interaction alone does not demonstrate masking. Magnitude shrinkage
without reversal is merely descriptively compatible with masking. No statistical
significance, equivalence, cognitive-mechanism or human-effect criterion follows.

Accept bounded JSON objects with a subset of the four known keys itemwise.
An extra unknown key invalidates all item scores; nonobjects and duplicate or
nonfinite JSON are parse errors. A valid numeric item is a finite builtin int or
float0–100, excluding bool and numeric strings. Distinguish missing key, null,
invalid value and invalid shape. No imputation, repair, baseline replacement or
post regeneration. Invalid own pre support skips exactly its two SHOWN wrapper
posts, while both OMITTED posts still run. Unrelated thermometer/comprehension
missingness does not gate support. Wrong factual answers never exclude support.

Report topic-specific results, descriptive party strata, leave-one-topic-out
values, separate party-gap contrasts, reference-to-post support drift, and
comprehension/coverage by topic, wrapper and visibility. Correct/planned and
correct/valid differ; unasked is not an observed factual error. There are four
purposive profiles and two topics, not eight independent humans. Do not bootstrap
a population CI, test p-values or select the responsive topic/model. No result
threshold automatically unlocks scaling or added realism.

## Assignment and operational proposal

Seed20261112 fixes eight shuffled profile-topic baselines, one pair seed and
item order per unit, and shuffled post-quartet order. Each quartet contains all
four crossed cells consecutively in a cyclic rotation of the canonical cell
list. Eight quartets make each cell occupy each ordinal twice. Wrapper and cue
are orthogonal in the planned manifest; missing pre produces disclosed attrition
rather than rerandomization. Preserve isolated contexts, matched unit seeds,
identical topic body/source hashes and request-only ablations in future compiler
tests. A seed is technical matching, not guaranteed deterministic serving.

Proposed maximum40 POSTs, no POST retry,8192 input-bound and256 output tokens
per call:327680input+10240output=337920tokens. At most120 billing GETs, three per
generation, waits10/10/20s,404-only retries. One logical billing claim per call.
Single-model catalog GETs at start and before the first admitted global slot at
or beyond10,20,30: at most four, ordered one-use stages. Crossing a barrier via
scientific skips consumes required stages in order. No adaptive extra refresh;
900s proof age and120s full-phase headroom remain mandatory. Phase120s,
HTTP30s/socket15s, finite authority lease at most7200s. Stop at any exhausted
bound, uncertain bill, mismatch, unknown cost/usage, stale proof or persistence
failure; preserve reservations and all remaining NOT_ATTEMPTED dispositions.

Proposed subcap75000microUSD ($0.075);40x1785=71400microUSD is the maximum call
reservation sum. Latest public accepted exposure9319 leaves990681microUSD below
the existing E02$1 ceiling and4990681 below shared$5. These are public-snapshot
planning figures, not a current ledger read, fresh price observation or spend
release. New head-bound same-owner accounting must include every old charge and
hold and all outstanding new reservations. E01 paid inference remains$0. No
old hold, consumed request allowance or launcher is reset. Actual model/provider
prices, request compatibility and finite window require separate review; default
unapproved execution remains zero and only OpenRouter may serve inference.

## Acceptance and next steps

1. Independent review of this candidate's texts, scale, orthogonality, missingness,
   ordering, scientific scope and cost arithmetic before any freeze or new outcome.
2. Separately versioned pure compiler/parser/scorer implementation and meaningful
   authored arithmetic/missingness/ablation tests, including shape corruption,
   unknown extra keys, no-topic/other-profile cue leakage, partial denominators,
   sign reversal and zero/empty estimands. Existing engines do not implement
   generic policy_support or this factorial merely because earlier tests passed.
3. Independently reviewed mocked same-owner financial/client lifecycle, all limits,
   scheduled refresh stages, UNKNOWN telemetry handling, cancellation/holds and
   exhausted billing. No actual provider or private source use in preparation.
4. Lead-only exact code/protocol/current-price/head-bound release under existing
   authority; then independent actual-evidence review. No consumed launcher reuse.
5. Preserve negative/failed configurations and report uncertainty/provenance before
   considering a separately specified model/valence replication, licensed news,
   assistants or other realism. Full original population/human-validity and
   publication requirements stay open. No external publication is authorized.
