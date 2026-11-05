# Limited E02 pilot accounting adapter: proposed release boundary

November 5, 2026. **PROPOSAL / NOT RELEASED / NO SPENDING AUTHORITY.**

Purpose: connect the accepted 16-unit exploratory protocol to the existing
OpenRouter transport and original financial history. This is the remaining live
integration, not another population-fitting or dashboard milestone. The owner has
authorized $5 combined for connectivity and the first pilot. The pilot proposes
a $1 subset of that amount, never an additional allowance.

## Entry and retained history

Use the original registered owner, header, database, anchor and history. No
bootstrap, second ledger, history replacement, charge forgiveness or simulated
clean state. Replay the original V4 prefix and accepted additional-connectivity
amendment using their unchanged semantics.

Entry requires the exact historical UNKNOWN receipt
`4fc8f40cbc434a308f11e1094fae5d7a` unchanged at 340 microdollars and the single
additional connectivity row successfully `PHASE_COMMITTED`, with validated
provider identity, native usage, one billing lookup and checkpoint. If that
additional check is missing, uncertain, overrun or uncommitted, refuse the pilot.
This proposal does not renew an expired connectivity lease or grant a further
connectivity request.

Pin the entire predecessor head/history, active approval, rows and statistics
claims in the independently reviewed study policy. Check that prefix under the
original guard and `BEGIN IMMEDIATE`. Keep the true unfinished count: exactly
one quarantined historical row at entry. Only that exact immutable row is
exempt from the study's unfinished-phase barrier. Any other unfinished row
prevents the next request. Historical readers are expected to refuse unknown
successor events; do not pretend this is unchanged V4 admission.

## Closed release graph and limits

The policy binds the accepted protocol bytes, instrument projection, assignment,
compiler, sequencer, evaluator, owner adapter, client and terminal code pins;
one run ID; exact predecessor snapshot; reviewed model/route/price contract;
finite validity window; and these integer caps:

- Shared lifetime amount: 5,000,000 microdollars; E02 same, E01 zero.
- This study's cumulative charged amounts and outstanding reservations: at most
  1,000,000 microdollars, inside the shared total.
- This study: at most 32 POST reservations and 32 generation-statistics claims,
  concurrency one, no retries, replacements, fallback or purchases.
- Total lifetime dispatch ceiling: 34 (old attempt + additional connectivity +
  at most 32 pilot phases). Existing charges and counts never reset.
- Per phase: at most 31,250 microdollars, 8,192 input-bound tokens and 512 output
  tokens. Actual exact-request quote must fit the common envelope.
- At most one unauthenticated endpoint-catalog GET for a particular run release.
  Its fresh proof must cover every admitted phase; when it expires, stop. This
  version does not refresh prices or renew authority during a run.
- Whole phase: 120 seconds cooperative deadline including checkpoint; each HTTP
  operation 30 seconds with 15-second socket timeout. These are cooperative
  limits, not hard real-time guarantees.
- Study authority window at most two hours, within reviewed price validity;
  every phase must fit its full 120 seconds before either deadline. Fresh-price
  age remains at most 900 seconds, so the usable run may be shorter.
- Keep existing 10,000-event/1,024-row/64-KiB-event financial-store bounds.
  Before the first study request reserve capacity for all 32 phases and terminal
  accounting events. The private run journal has a separate 16-MiB cumulative
  cap, 256-artifact cap and 2-MiB per-artifact cap; no raw key or Authorization
  header is retained.

Graph: policy P pins parents and code; independent review R binds P and those
pins; operator assertion O binds P and R, existing shared-$5 consent, retained
unknown billing and rotated dedicated prefunded-key readiness; study authority A
binds P/R/O. None of these binds a descendant. The terminal review binds the
complete P/R/O/A packet and code. Runtime fresh catalog proof C is checked
against the released terms and is included in each exact phase context. Actual
dates, release IDs, code hashes and predecessor head remain absent until an
independent particular release. Local hashes express trusted-workflow content
bindings, not cryptographic proof of human identity or a hostile-host boundary.

## Adaptive phase admission and checkpoint witness

The pure sequencer reconstructs the next request from all preceding authenticated
study records. Supplied transcript records alone are never authority. Before
each reservation, the owner adapter reconstructs those records from its own
validated financial events and durable checkpoints and verifies all request,
response, billing and checkpoint hashes. The client's caller cannot supply a
baseline, unit override, payload override or arbitrary output path.

For post-surveys, admission requires the same run/unit's own committed pre phase.
The persisted pre-answer witness contains only the exact parsed questionnaire
object or explicit parse-error disposition, with its response/checkpoint hash.
It is recorded with the commit event and cannot be replaced. Recompute the post
payload from that witness and the accepted projection; reject a foreign unit,
changed baseline, noncommitted pre or a changed request hash. Invalid pre answers
derive `SKIPPED_INVALID_PRE` with no reservation/POST. Invalid post answers remain
observed exclusions; no imputation or replacement.

The owner appends study authority once. For each phase it validates the next
sequence position, price proof, total and study caps, exact context and own-pre
witness, then atomically appends a phase grant and reservation plus materialized
row under one transaction and one anchor update. No approval renewal is needed
between phases. This is an explicit new successor grammar, not temporary changes
to `unfinished`, `_binding` or predecessor approval fields. Replay must validate
the new grammar from the true prior state. The original terminal UNKNOWN row
cannot be transitioned or reconciled by study events.

Only a postcommit/readback acknowledgement can yield an opaque in-memory
single-use dispatch capability. Persist the acknowledgement and POST intent
before consuming it. Never reconstruct a capability from a returned receipt or
restart after intent. A crash may forfeit the request; it must not duplicate it.

## Response, billing, failure and analysis

Reuse strict OpenRouter/provider/native-usage/auxiliary-fee validation. Claim one
statistics lookup durably before its GET; a missing generation ID permits none.
Only verified billing and a validated durable checkpoint allow a phase commit.
The next phase is forbidden until that commit. Unknown billing, integrity error,
timeout, lost acknowledgement or accounting failure stops the entire study and
retains the full reservation. Known overrun retains the higher cost even above
the cap and stops further dispatch. Late verified billing is retained separately
as observed evidence while the phase remains UNCERTAIN/full hold, consistent
with the accepted connectivity timing rule.

On termination emit all 32 phase dispositions, remaining phases NOT_ATTEMPTED,
exact request/response/financial provenance, costs and failure reason. Feed only
authenticated records into the accepted evaluator. Real response provenance is
EXPLORATORY_REAL_MODEL; stimuli remain authored DEMO inputs. Pure fixtures and
sequencing tests remain MOCK. Tiny fictional technical replicates are not a
representative population, confirmatory experiment or evidence about humans.

## Acceptance criteria and current blockers

1. Independent methods review of this successor grammar and closed authority
   graph before adopting it. This document does not certify an implementation.
2. Authored adapter/client tests: exact 32-phase sequence, changed/foreign pre
   rejection, old-row immutability, caps including old holds, duplicate claims,
   crashes at transaction/anchor/ACK/POST/billing/checkpoint boundaries,
   concurrency races and terminal-tail refusal. Both supported runtimes.
3. Independent exact-code and retained-mock-run review. No milestone self-review.
4. Successful one additional connectivity check under a fresh separately reviewed
   release; the November 4 packet remains expired and must not be edited/reused.
5. Particular study release with current prices, exact head, code and verified
   credential readiness; execute only within existing consent and fixed caps.
6. Independent raw-response/accounting/analysis review before reporting results.

As checked November 5, the execution process has no exported
`OPENROUTER_API_KEY`. No credential value was displayed or read into a report.
This proposal performs no provider calls or financial writes. The actual adapter
and particular release are still incomplete; no live result is claimed.
