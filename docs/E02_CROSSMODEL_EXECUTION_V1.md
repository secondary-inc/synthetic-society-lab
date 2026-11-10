# E02 support-only cue: bounded two-model execution

Prepared November 10, 2026. This document describes the new execution candidate,
not completed results. The scientific specification is
`E02_ISSUE_CUE_CROSSMODEL_V1.md`; the previous whole-answer cue study remains
immutable and is not pooled with this intervention.

The owner has authorized autonomous, justified recovery and experiments within
$5 shared cumulative exposure and $1 cumulative E02 exposure. E01 model inference
remains $0. This batch adds no allowance and creates no replacement budget owner.
The predecessor has 342 events, 56 financial rows, and conservative exposure
4473 microUSD, including the three unresolved historical holds.

## Fixed execution contract

- 56 model POSTs maximum: four new baselines plus 24 post-treatment slots per
  model. The two model roles are interleaved in adjacent, counterbalanced pairs.
- Model A: `openai/gpt-4.1-nano`, Azure provider family `azure`.
- Model B: `qwen/qwen3-30b-a3b-instruct-2507`, Nebius route prefix `nebius/fp8`.
- Both use temperature 0, matched pair seeds, JSON-object responses, at most 8192
  conservatively bounded input tokens and 256 output tokens. The same seed is
  not a guarantee of equivalent randomness or deterministic provider behavior.
- Maximum new batch exposure 100000 microUSD ($0.10), maximum individual
  reservation 1785 microUSD, and 112 lifetime dispatches including all 56 old
  rows. With the November 10 candidate prices, full-envelope bounds are 1285
  microUSD for A and 1716 for B: 84028 microUSD for 56 calls. Actual reservations
  use each compiled message's conservative byte-plus-framing token bound.
- Zero model retries, silent provider fallbacks, credit purchases, or sample
  extensions. `provider.only`, `require_parameters=true`, and
  `allow_fallbacks=false` remain on the wire.
- One logical billing claim per model generation; at most three GETs, with
  fixed preceding waits of 10, 10, and 20 seconds. Only an exact closed HTTP404
  permits another lookup. At most 168 billing GETs across the entire batch.
- Four unauthenticated public catalog GETs maximum: A/B at start, A/B before
  the first admitted slot at or beyond execution order 28. Skipped slots do
  not trigger additional catalog observations. Each observation must match
  the frozen numerical prices, route membership, and semantic capability hash.
- Price observation age remains 900 seconds. Each phase remains 120 seconds;
  the hash-bound run window is at most 7200 seconds. These limits are never renewed
  after an interruption. A phase must fit its existing deadlines before entry.
- Concurrency one; journal at most 768 artifacts, each at most the existing
  artifact byte cap, with the existing total bytes and free-disk reserve.

## Compatibility and fee interpretation

The raw November 10 catalogs are preserved with their receipts in the ignored
`data/processed/e02_crossmodel_price_20261110_01` directory. The new
`crossmodel_price_v1` adapter accepts exactly the Qwen/Nebius route's advertised
legacy `max_tokens` capability as the documented `max_completion_tokens`
successor. Its semantic hash includes both observed parameter names and the
explicit normalization. The original catalog is never rewritten or described
as advertising the successor. The wire limit is `max_completion_tokens=256`
for both models. The gateway may still reject this combination; that stops
execution with retained evidence and no automatic POST retry.

Source: [OpenRouter chat API](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion).
This documentation is compatibility evidence, not a successful live-route test.
The [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507-FP8)
identifies this checkpoint as non-thinking. An observed nonzero or unknown
native reasoning-token count still fails the billing validator.

Missing cache-write, one-hour-write, internal-reasoning, and per-request prices
are explicit conditional zero-fee interpretations of the published standard
text-token schedules, not observed zero-valued catalog fields. The request
uses no cache-control override, tools, plugins, BYOK, or service-tier override.
Input reservations sum all input price components, including cache reads.
Nebius's public model schedule lists input and cached input at $0.10/million,
output at $0.30/million, matching the OpenRouter route. OpenRouter's
[support page](https://openrouter.ai/support) describes passthrough inference
pricing; credit-purchase fees are irrelevant because no purchase is made.
The saved decision enumerates every omitted component and source hash.

## Accounting, evidence and acceptance

The separately versioned owner inherits the existing accounting implementation.
It adds only the `issue_cue_crossmodel` namespace and distinct start, reservation,
commit and one scheduled price-refresh event. It requires the exact preceding
head/history/rows/study/continuation/alignment hashes and preserves every old
row and uncertainty hold. The append-only ledger is not reset or refunded.

A create-once caller intent prevents launcher replay. The caller binds its own
bytes, exact packet, predecessor export and credential-reader hash before
loading the existing private credential. Credential values are never printed;
the process restores the prior environment afterward. No raw respondent or
publisher data is sent: this finite study uses authored fictional contexts and
notices.

Each model response, billing record, request, quality record and checkpoint is
retained in the private journal. Only exact released model identities and
provider names are accepted. Optional missing activity counters remain unknown;
mandatory native usage and all-in billing must be present and within reservation.
An uncertain dispatch retains its full hold and stops the batch. Ctrl-C, process
failure or a consumed deadline cannot silently resume this caller.

Acceptance requires: frozen scientific scoring and assignments; independent
methods, price, code and exact packet review; isolated full-history integration
with both model roles and scheduled price refresh; preservation of all old
financial state; successful stop/hold tests; and independent recomputation of
any actual result. MOCK tests are engineering checks only. Completion of these
limited diagnostics does not satisfy the original nationwide calibration,
human-validation or broader research completion requirements.
