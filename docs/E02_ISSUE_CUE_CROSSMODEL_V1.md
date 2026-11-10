# E02 issue-support cue across two fixed configurations, v1

Prospective exploratory methods and pure-engine candidate, November 10, 2026.
This document and its exact config must pass independent review before new
outcomes. Neither grants execution authority. Results are currently absent.

## Question and scope

Does showing an exact own issue-support rating attenuate responsiveness to
opposing fictional notice evidence? Does that interaction differ between two
fixed model/provider configurations? This follows 54 independently audited
research responses: the original32 and the separate22-response full-answer cue
study. In the latter, two baselines had valid support but a null unrelated
thermometer, which under its frozen rules excluded six SHOWN posts. Preserve
those exclusions and results. The new itemwise rule is prospective and the new
support-only cue is a different intervention; never pool them as one study.

This is one fictional policy issue and four technical contexts (2D/2R authored
party priors), not four independent humans, a demographic population or a human
polarization estimate. No numeric opinion priors or demographics are supplied.
The custom support item is not a validated human scale. Party thermometers remain
separate secondary outcomes; a local library proposal need not move them.

The human anchoring literature motivates a design question only. Epley and
Gilovich's2001 human quantity-estimation study distinguishes self-generated and
experimenter-provided anchors ([primary publication](https://journals.sagepub.com/doi/10.1111/1467-9280.00372)).
Showing a model a previously elicited fictional policy rating is a different
task. This is neither a replication of that human experiment nor evidence that
a measured output interaction identifies human adjustment, persuasion or any
particular cognitive mechanism. We import no copyrighted experimental stimuli.

## Frozen design and matched controls

Literal role A: `openai/gpt-4.1-nano`, Azure, route `azure`, PROVIDER_FAMILY.
Literal role B: `qwen/qwen3-30b-a3b-instruct-2507`, Nebius, route `nebius/fp8`,
ENDPOINT_PREFIX. Both wire requests use temperature0, bounded JSON output,
`max_completion_tokens=256`, no tools/plugins/reasoning and no fallback.
These differ in model, provider, tokenization and quantization; the contrast is
between these exact configurations, not a causal effect of architecture or
model families generally. Same numeric seed is a technical match, not common
random numbers or a determinism guarantee. Record actual serving identities.

Eight fresh reference-notice baselines (4contexts ×2roles), then48 posts
(4contexts ×3notices ×2cue modes ×2roles): at most56 model calls. N01 reports no
measured visit effect; N02/N03 report40% more/fewer visits. Their remaining
proposal, unchanged budget, source and wrapper words are identical. These are
project-authored DEMO scenarios with fictional quantities, not real news.
Question/notice text is retained from the prior study; the exact new instrument
identity and assignments are pinned in the config.

Every baseline sees N01 and is a neutral/reference-notice baseline, not an
unexposed baseline. Every SHOWN post adds exactly
`pre_response: {library_support: <exact own rating>}`. OMITTED has no such key.
All other model-visible data match within profile/notice across modes: system,
questionnaire, fixed party prior, item order and seed. OMITTED is the simpler
comparator and remains party-conditioned. Neither mode contains answer keys,
mode labels or model role labels. Calls use isolated contexts. No other baseline
item, other-model response or historical baseline enters the cue.

Seed20261110 fixes shuffled profile order, per-profile seed and item order, and
post-cell order. Each pre profile or post cell is an adjacent A/B pair; model
order alternates within each phase. This limits sequential drift while retaining
same-context comparisons; it cannot remove all serving/time confounding. Each
post references its own role/profile baseline execution order. The literal
56-job manifest is authoritative and reconstructible from the documented seed.

## Eligibility, missingness and denominators

Request all four known keys. Accept a bounded JSON object containing any subset
of them for itemwise scoring; any unknown extra key invalidates the whole
object. Nonobjects are parse failures. Do not coerce, repair or impute.
Numeric validity means a finite builtin int/float in[0,100], excluding bool.
Preserve MISSING_KEY, MISSING_NULL, INVALID and INVALID_SHAPE separately.

Only valid own `library_support` gates SHOWN. Missing, null or invalid unrelated
thermometers or comprehension never invalidate support/cue. If own baseline
support is invalid, skip exactly its three SHOWN posts; run its three OMITTED
posts. Never replace a refusal or regenerate a baseline. Wrong factual answers
never exclude numeric support. Each thermometer outcome requires its own valid
items. Parsed ANSWER is not a claim of valid survey scores or authenticated bill.

Report comprehension correct/planned and correct/valid, observed factual errors,
missing key/null/invalid/no usable answer and unasked counts for each role/mode,
with directional-notice denominators8 and total post denominators12. Coverage
failure is distinct from observed factual error. Report baseline comprehension
separately. Every slot has a disposition, including skipped and stopped slots.

## Frozen analysis and interpretation

Within each role and context, primary interaction in support points:

`Delta = (N02_SHOWN - N03_SHOWN) - (N02_OMITTED - N03_OMITTED)`.

A context needs all four support ratings; each role reports four planned,
complete count, raw values and descriptive mean/min/max, theoretical[-200,200].
The key secondary is mean`(Delta_B - Delta_A)` on the common complete context
intersection, range[-400,400]. Never subtract unequal-denominator means.
Empty estimands are null, not zero. Also report directional content contrasts
per role/mode, N01 post-minus-reference support and fixed-party thermometer
changes/content contrasts separately. Factual correctness never changes primary
inclusion. No inferential CI, p-value, equivalence, population N or human effect
claim is justified by these four purposive contexts and one issue.

A descriptive attenuation pattern across these two fixed configurations requires
both to have four complete interactions, negative mean and at least3 negative
values. Each must also have four complete OMITTED content contrasts, positive
mean and at least3 positive values, and at least6/8 planned directional factual
answers correct in each mode. Otherwise report the failed criterion and raw
outcomes. This threshold is not a significance test or a model-family claim.
The batch ends regardless of result: no adaptive models, notices, profiles,
seeds, prompt revision or replacements. Any later study is separately frozen.

## Finite operations and costs

Per call: at most8192 input-bound tokens and256 output tokens, reservation1785
microUSD,120s phase deadline,30s HTTP/15s socket; no POST retry. At most3 statistics
GETs per generation with waits10/10/20s; retry only404. Thus at most168 billing
GETs,458752 input-bound +14336 output =473088 total tokens,99960microUSD at the
per-call maximum, within this batch's100000microUSD ($0.10) ceiling. This remains
inside existing cumulative E02$1/shared$5 limits with all old charges/holds.
Prior conservative exposure4473microUSD is context, never a ledger reset.

Exactly two public endpoint catalog GETs at start and two before global slot28,
including when intervening slots are skipped; at most four. Expired900s evidence,
changed prices/capabilities, unknown billing, identity/route mismatch, timeout,
unsupported activity, failed persistence or exhausted cap stops the whole batch.
Retain holds and all diagnostics; remaining jobs NOT_ATTEMPTED. No automatic extra
refresh, fallback or probe. Fresh release quotes and same-owner accounting belong
to the lead's separately reviewed financial adapter/caller, not this pure engine.

B advertises legacy`max_tokens` in the raw catalog. The lead's separate reviewed
adapter explicitly interprets its documented successor`max_completion_tokens`
without rewriting raw evidence. This is conditional metadata interpretation,
not proof of gateway compatibility. First actual request must fail closed if
unsupported; no separate paid compatibility request is added. Conditional prior
price arithmetic is not a current price release or actual spend.

## Acceptance and reproducibility

1. Independent methods review: exact config hash, one issue, cue-only intervention,
   model bindings, itemwise exclusions and all denominators frozen before outcomes.
2. Pure tests: reconstruct56 slots/interleaving; prove request-only ablation and
   same-model baseline isolation; null/missing unrelated pre fields remain
   eligible; invalid support skips only its own3; unknown keys refuse scoring.
3. Scorer tests: authored A interaction-30/B-60/cross-30, unmatched-denominator
   counterexample, empty/null and factual-error-vs-coverage checks; all56 terminal
   dispositions, hash tampering and stopped/extra-record refusals. MOCK numerical
   changes are arithmetic oracles, not empirical treatment positive controls.
4. Financial owner/client/caller independently reviewed and mocked with previous
   history/holds intact, fresh two-role terms, all quotas/reservations/reconciliation
   and cancellation. No live call from the pure module. No new authority inferred.
5. Actual execution and independent outcome review remain separate milestones;
   record run IDs, code/config/input/payload hashes, seed, provider/model, native
   usage/cost, errors, exclusions and all failed configurations. Update lead-owned
   status only on direct evidence. Public publication requires owner approval.

Pure API: `load_protocol`, `cost_envelope(raw, terms_by_model)`,
`next_action(raw, terms_by_model, transcript_bytes)`, `parse_response`,
`response_envelope(raw, transcript_bytes, response_provenance=..., stopped=...,
terms_by_model=...)`, `analyze(raw, envelope_bytes)`. Transcript rows retain exactly
execution_order/phase/payload_sha256/status/answer. The fixed protocol hash binds
roles and assignments. With terms, export replays every payload hash; without
terms it is a structural projection of an owner-authenticated transcript, not
financial evidence. Response envelopes contain all56 dispositions and explicit
MOCK or EXPLORATORY_REAL_MODEL provenance. Reproduce using
`PYTHONPATH=src:tests .venv/bin/python -m unittest test_e02_issue_cue_crossmodel_v1 -q`.
