# Owner-wide budget and release controller v3 proposal

Methods/design candidate; independent review pending. No actual owner approval, bootstrap, credential read, HTTP call or model execution. Preserve the accepted v2 global ledger/client/phase bridge unchanged. This proposal implements a missing original live-v2 requirement: one owner allowance across runs, modules, checkout locations and subsequent approvals.

## Trust and location

The production factory will resolve one application namespace under the current OS user's home (`Library/Application Support/SyntheticSocietyLab/openrouter-v3` on macOS, `.local/share/synthetic-society-lab/openrouter-v3` on Linux). Project/run/output paths, environment overrides and CLI flags cannot choose another production ledger. Authored tests use a separate explicitly typed scope; that scope is never a production allowance. No production factory is enabled by this component.

Approval is a human workflow assertion under trusted execution, not cryptographic proof of who wrote a JSON file. The agent cannot author its own affirmative real approval. A later factory must validate the independently released study/inputs/code/endpoint/price plan, concrete owner approval and rotated credential setup before injecting a key. This component never reads a key. Current actual budget remains zero.

Protected writer, header, approval/terminal history and current-head anchor are trusted local authority. Semantic replay detects malformed chains, counter edits and inconsistent transitions. Replacing all authority/history/anchor or rolling back the complete trusted store is outside local integrity claims, as in the accepted v2 boundary. Same-UID permissions do not establish hostile-host isolation. No new cryptographic-security requirement or undisclosed signing service is proposed.

## State and approvals

Bootstrap is exclusive/create-once, with a persistent guard, SQLite store, immutable owner/namespace header and separately persisted sequence/head. Missing/torn state never initializes an empty allowance. Header contains no positive budget. Until an explicit validated approval event exists, reservation is disabled.

An approval event freezes an ID, owner identity, absolute lifetime total and E01/E02 module caps in integer microdollars, start/expiry times and an allowed set of released plan hashes. It names the previous approval hash (null for the first). These are absolute lifetime caps, not a new additive allowance. A changed approval may increase/decrease limits only through this event; every prior charge remains consumed. Caps below existing total/module consumption refuse. Renewal requires the exact current parent identity and all earlier phases durably committed. An unknown/overrun/outstanding phase cannot be cleared by a renewal, a new study or an expired approval.

The initial implementation accepts authored approval fixtures only; the production owner-approval factory remains disabled pending separate authorization/release implementation. Tests of positive amounts do not grant spending. This is the first bounded code milestone, not final live readiness.

## Request and billing events

STARTED atomically reserves upward-rounded positive cost before any future POST. Context binds owner approval hash, released plan hash, run/unit/phase/module, exact model/route/provider contract, exact message and payload hashes, seed/temperature/no-retry policy, byte/token/output ceilings and complete linear token/request fee terms. Context must reference the currently valid approval and one of its plan hashes. No arbitrary event can change the context later. One global unfinished phase blocks further reservations and approval events.

Transitions retain the accepted sequence STARTED → RESPONSE_SEEN → SETTLED → PHASE_COMMITTED, with UNCERTAIN/OVERRUN terminal barriers. Valid generation IDs are unique owner-wide across approvals/runs/modules. Safe billing evidence must match generation/model/actual provider/native token ceilings/BYOK false/non-reasoning support and total charge. SETTLED consumes actual reconciled cost; uncertain/overrun consumes at least the greater of reservation and known cost. Unknown costs are not refunded. A durable phase checkpoint validates exact output/request/receipt/unit/phase before releasing the barrier. No automatic retry, repair prompt, reconciliation reset or approval-based refund exists.

Every event validates at write and replay, including each historical reservation against the approval current at that historical point. Current counters are derived from this history, not accepted on their own. The latest approval must not retroactively legalize reservations over an earlier cap. Current UTC checks apply before new operations; historical approval validity uses that event's recorded time. Clock rollback relative to the last trusted event refuses new work.

## Atomicity, resources and scope

Interprocess lock serializes approval/reservation/transition writes. SQLite commit precedes head advancement; failure between them conservatively refuses reopening. Run IDs and module changes never create an allowance. Separate-directory creation is a test-only action; production construction has a fixed resolver and no public relocation option. No actual owner directory is created during development.

Semantic replay should use a generation-to-receipt index rather than repeatedly scanning all previous receipts. Resource/timing observations must be measured; no large-history guarantee follows from tiny tests. Storage/retention, authentic fee/reasoning/hidden-context contracts, provider compatibility, production owner approval, key injection, HTTP/client/phase integration and study/attrition release remain separate uncompleted work.

## Acceptance criteria

The standalone authored engine must demonstrate no approval/expired/future/stale-parent/changed-owner/unknown-plan/over-cap zero-dispatch refusals; cross-run/module cumulative consumption; renewal after a completed phase with no reset; reduced-cap refusal; historical caps still enforced after renewal; generation reuse refusal across approvals; unknown/overrun barriers across expiry/renewal; exact per-request upward rounding and request fees; code/context/quote/receipt/checkpoint semantic tamper rejection; missing/torn/changed header/current-head/store; process death around reserve/billing/checkpoint and DB/head persistence; real competing processes; fixed production-path resolution independent of checkout/output; typed test scope and disabled production factory; private permissions and no secret/body logging. Every refusal asserts no additional fake dispatch rather than exception alone.

Independent approval of this design authorizes preparing code and authored fixtures only. Actual owner bootstrap, real approval admission and enabled model transport require separately reviewed implementation and concrete owner/study/price authority. Existing research/source permissions and the full original completion contract are unchanged.
