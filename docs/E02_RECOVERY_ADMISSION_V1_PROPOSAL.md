# E02 admission using retained connectivity evidence

Status: offline proposal; no new execution or spending authority.

The November 5 model call returned an answer whose recorded hash matches the
expected valid JSON output. Its immediate statistics lookup returned 404. The
owner separately approved one billing-only lookup, which returned retained
metadata for the same generation: Azure, 46 input tokens, 6 output tokens,
0 reasoning tokens and $0.000007. The original response body was not retained.
Both original rows remain UNCERTAIN with $0.000340 held each, two lifetime
dispatches and two unfinished rows. This proposal does not change those facts.

## Metadata interpretation

1. Accept only the exact model identity mapping from
   `openai/gpt-4.1-nano` to `openai/gpt-4.1-nano-2025-04-14`, supported by the
   [official model record](https://openrouter.ai/api/v1/model/openai/gpt-4.1-nano).
   The November 5 public response has SHA-256
   `e234cd7362756b3bfe4411471f6966bec6a2be7ef81bff131f6a4c30ea9164be`.
   Preserve the reported model name; never strip arbitrary date suffixes.
2. Preserve optional null counters as `REPORTED_NULL_UNKNOWN`, absent counters
   as `NOT_REPORTED_UNKNOWN`, and integer zero as `OBSERVED_ZERO`. Reject
   positive unsupported activity, negative counts and ill-typed values (including
   booleans used as counts). Unknown optional counters
   are admissible only for the fixed text-only request with no tools or plugins,
   mandatory native usage and an all-in bill within its reservation. This does
   not establish that hidden upstream activity was absent.
3. Admit only a reported `default` service tier. Null/absent tier remains
   explicitly unknown and is refused; it is never projected to `default`.
   OpenRouter's [service-tier documentation](https://openrouter.ai/docs/guides/features/service-tiers)
   identifies `default` as regular capacity and pricing. Do not turn it into a
   null observation or admit flex/priority/unknown tier names.
4. Preserve `streamed: true` literally and flag the discrepancy with the
   request's `stream: false`. The checked HTTP transport accepted a complete
   bounded JSON response, not SSE. The meaning of the provider's contrary
   telemetry remains unresolved. For this small exploratory pilot, control the
   client request and response format while recording the telemetry separately;
   do not claim control over undocumented upstream transport or rewrite true
   to false. Apply the same rule to both treatment arms.
   Require a literal boolean streaming observation; null, absent and malformed
   streaming observations are refused under this narrow version. Require
   `cancelled: false` as a literal boolean, refusing unknown or malformed values.
5. Exact generation identity, Azure provider, non-BYOK mode, finite nonnegative
   total cost, strict integer native input/output bounds and zero reasoning
   remain mandatory. Reject cancellation, observed unsupported tools/search or
   media/reasoning activity, non-default paid tiers, unknown model aliases and
   overruns. Retain original metadata unchanged. Any internal billing projection
   must be explicitly marked as normalized and independently rederived from the
   saved metadata at settlement/commit; it must never be described as raw data.

The November 3 saved official OpenAPI document, SHA-256
`33c53c85504e0f3a314d834a179c731597493d24ad68d4f0ba0193824184012e`,
allows nullable optional activity counters, service tier and streaming telemetry.
Schema validity alone does not explain the streaming discrepancy.

## Alternative admission without rewriting history

A separate independently reviewed recovery receipt must bind the current saved
16-event history and head, both exact original rows, the sole statistics claim,
the exact retained billing object and its hash, the exact documented model map,
and the independently computed expected decoded-output hash witness. It must
state the missing original response body and unresolved telemetry explicitly.
Its bill must fit the original reservation and round up to the previously
recorded 7 microdollars; no exact original completion-cost decimal is claimed.

The study successor may admit this technical evidence as an alternative to a
completed standalone connectivity checkpoint. It must not create such a
checkpoint, claim the failed run completed, reopen either old row, release holds,
reset lookup claims, reset dispatch counts or replace the original owner.
Every later reservation must retain both original rows unchanged and count
their two unfinished states. Any additional unfinished study row prevents a
next request. Historical total consumption remains 680 microdollars.

The original 32-phase pilot, $1 subset of the shared $5 ceiling, original run
logging, native usage reconciliation, raw provider retention, uncertainty and
exclusions remain in force. No third connectivity model request is proposed.
The first and every later pilot phase must retain its own full canonical model
response and billing metadata and pass the normal quality/accounting checks.

## Avoid the immediate lookup race

Before each phase's sole statistics GET, wait a fixed 10 seconds after the
response is retained. This is an exploratory visibility allowance, not a
provider availability guarantee. Recheck monotonic/UTC time and leave enough
time for the one bounded GET and checkpoint inside the existing 120-second
phase. An unavailable record still stops the run with its full hold; no retry,
refresh or replacement prompt is permitted.

## Acceptance criteria

- Independent review accepts the explicit telemetry limitation and exact alias.
- Pure metadata tests cover the saved real shape, unknown versus zero, wrong
  identity/date/tier/provider, type confusion, positive activity and overruns.
- Owner tests reject changed historical rows/head/claims, forged recovery
  receipts and output hashes; two preserved unfinished rows permit a grant,
  while a third unfinished study row blocks it. Both original holds survive.
- Commit rederives normalized billing from unchanged retained metadata and
  rejects any tampering; the original row validator remains unchanged.
- Mock primary/replay and failure cases pass; bounded initial wait tests prove
  no extra GET or POST and no request after cancellation or expired time.
- Independent code review and the exact final packet/caller review pass before
  the already-budgeted pilot is executed. No new budget is inferred here.
