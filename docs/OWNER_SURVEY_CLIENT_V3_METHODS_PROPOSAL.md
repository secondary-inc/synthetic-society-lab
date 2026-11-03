# Owner-epoch survey client v3: authored integration proposal

Status: methods proposal, independent review pending. This milestone connects the independently accepted owner-budget v3 fixture component to the existing adaptive E02 request planner and fake provider. It does not enable HTTP, create a production owner namespace, admit a human approval or use credentials. All actual model calls and experimental spending remain zero.

## Ownership and immutable dependencies

The lead owns a new `src/civiclab/owner_survey_client_v3.py` and its tests. Preserve `owner_budget_v3.py`, `reconciled_client_v2.py`, `survey_envelope_v2.py`, `survey_global_execution_v2.py`, the old survey bridge, HTTP helper and common runtime exactly. Record their hashes in the handoff. The independent auditor owns its review receipt. Existing approved fixture controls are not actual study or price releases.

## Construction and phase admission

`OwnerSurveyFixtureClientV3` accepts only an existing exact `OwnerBudgetFixtureV3` and exact `FixtureHTTP`; no duck-typed arbitrary transport, subclass, key, opener, location override, automatic owner creation or budget grant. Construction detaches terms and validates their existing fixture quote contract; transport terms must match. The production factory unconditionally refuses before resolving/creating the owner directory or accessing credentials.

The phase call takes a frozen compiled E02 envelope, a separately supplied expected plan hash, an explicit expected approval hash, run ID, phase and optional prior answer. Detach caller-controlled plan/answer values into finite built-in JSON before admission, with no caller alias retained. Use the accepted `prepare_phase` to rederive the plan, source pins, exact request and actual quote. The unit ID is the canonical hash of the plan's job; seed comes from its fixed pair seed, module is E02, and the output ceiling comes from the plan. Caller arguments cannot override messages, model, route, provider, sampling, token limits, unit or module. Plan terms must exactly match the detached client and fake transport terms on every call.

The exact approval hash is carried through the reserve context with the externally expected plan hash. The owner engine checks that epoch is current and unexpired, the plan is allowed with exact module/terms/ceilings and cumulative funds remain. Reading the current approval and silently substituting it is forbidden. An invalid pre-answer yields the planner's explicit skipped-post disposition, zero new owner events and zero fake transport calls. It produces no invented answer or completion receipt.

## Dispatch, accounting and checkpoint barrier

Build the same complete nonstreaming JSON-only/no-fallback provider-pinned payload as the accepted v2 client, derive its hash and reserve before exactly one fake POST. Retain the accepted response/statistics reconciliation rules: strict generation/model binding, unique generation owner-wide before statistics lookup, visible-answer-only parsing, exact reported provider, native prompt/completion/reasoning bounds, BYOK false and response/statistics cost agreement. One statistics request follows a valid response; no polling, retry, repair prompt or fallback. Known costs are upward-rounded independently per request, and any disagreement, overrun, cancellation or unknown response retains at least the reserved or higher known charge and the owner's unfinished barrier.

Response identity and cost are persisted before statistics; stats failure cannot refund them. Expiry/clock loss during the fake request still permits accounting under the original approval, using the accepted engine's honest clock metadata. A successful call returns SETTLED awaiting a durable phase checkpoint. It cannot commit a phase, release the barrier, grant/renew authority, create a run or score effects. The caller must use the owner's existing exact checkpoint API. A later journaled survey bridge will separately rederive checkpoint/output/assignment semantics and manage cross-epoch resume; that bridge is outside this milestone.

For failure after reservation, attempt a conservative UNCERTAIN transition under the original epoch if the row remains STARTED/RESPONSE_SEEN/SETTLED. Preserve an existing OVERRUN. Failure of persistence leaves the original outstanding or torn store blocked. Return a static safe failure reason without response bodies, keys or arbitrary provider error text; propagate process cancellation after bookkeeping. Test-only hook failures may be simulated by patching exact fake methods; the public constructor still rejects arbitrary transports.

## Acceptance criteria

1. A real temporary owner fixture with an authored approval consumes a fake response through reserve, response, settled and explicit external checkpoint. Inspect exact context, payload hash, plan, approval, unit, seed, quote, billing and answer; match the independent arithmetic oracle.
2. Wrong plan/hash/terms/seed-derived data, stale/expired/unknown approval, disallowed plan, inadequate lifetime/module funds, mutable caller aliases, and a second phase before commitment make zero additional fake POSTs. Invalid pre-answer skips with no owner writes. Wrong ledger/transport types and disabled production factory refuse before side effects.
3. Expiry, honest rollback and unavailable clock after POST retain original approval and known charge, permit external checkpoint, and refuse a new phase. Valid later renewal may authorize a new request without clearing prior consumption; old approval is never silently upgraded.
4. Missing/malformed response, invalid visible answer, duplicate generation across approvals, wrong serving/native billing, statistics error, cost disagreement/overrun and BaseException cancellation are exercised. Invalid answer with verified billing remains a charged quality failure; financial uncertainty blocks continuation. Assert fake call counts and owner rows, not exception alone.
5. Existing owner16/planner7/client/global69 targeted checks remain green alongside new tests on the supported Python runtimes. Independent audit rederives raw requests, cost ceilings and negative side effects. No full-program or actual provider compatibility acceptance follows. Keep every failure and exact code/test pin in the handoff.

## Remaining releases

This is a bounded dependency-ordered engineering step. Actual source/population and attrition validity, production fixed-owner construction, protected authority boundary, human consent admission, authentic complete fees/provider compatibility, rotated credential injection, HTTP integration, scientific release, full reproducibility and concrete owner spending approval remain separate gates. Protected-store replacement is outside the existing trusted-local-authority integrity claim; no cryptographic identity or hostile-host isolation is added here. Small tests establish no large-history performance guarantee.
