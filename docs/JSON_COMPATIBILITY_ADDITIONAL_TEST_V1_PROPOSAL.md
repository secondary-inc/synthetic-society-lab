# Additional connectivity test: explicit control amendment proposal

Status: PREPARATION ONLY. No additional dispatch is enabled. This document prepares the owner's November 3 request for one additional tightly capped test. The existing one-request approval has been consumed. The owner's latest request authorizes preparation; a concrete final packet must disclose and bind the accounting-policy amendment before execution.

The owner reports no matching OpenRouter log. Their November 3 5:37 p.m. screenshot shows the displayed key's total/today/week/month usage as $0.0000 and Last Used: Never. This is useful account-side evidence, but does not establish that this displayed key was the credential used for run03, server acceptance, or an exact historical cost. Do not retain the key identifier, infer an HTTP cause, or treat this as a zero-cost settlement.

## Exact proposed action

One further nonpolitical JSON request to `openai/gpt-4.1-nano`, pinned to the Azure provider family, temperature 0, seed 20261103, max output 32 tokens and padded input bound at most 2276. The user prompt is: “Return exactly one JSON object with the key ok and the boolean value true. Do not add text.” Reuse the exact independently reviewed system message and full request only after checking its released byte binding. No substitutions, model fallback, tools, surveys, political content or retries.

Reserve at most **$0.000340** before the new POST. Keep the original **$0.001 absolute lifetime model-usage cap**, including the original $0.000340 conservative hold. At reservation, retained old plus new holds must be at most $0.000680. Increase the absolute dispatch allowance from one to **two total**, exclusively for this one additional exact request. One fresh bounded public catalog GET and one generation-statistics GET for the new returned generation ID are permitted only under the final release. A missing generation ID means no statistics GET. No purchases, top-ups, subscriptions or account changes.

The cap is an admission/reservation limit using reviewed advertised terms, not a promise that a provider can never misbill. Record unexpected observed cost in full and stop. If pricing/applicability changes or the new quote exceeds340 microdollars, refuse without substitution or a larger reservation.

## Why an explicit amendment is necessary

Current `production_owner_v4.py` refuses APPROVAL, PRICE_PROOF and RESERVE while any unfinished phase exists. Run03 is terminal UNCERTAIN with no implemented reconciliation transition. Changing a launcher, granting a second dispatch, or passing a fresh key cannot remove this barrier. Do not edit the existing V4 code, delete its store, create another owner or claim that the old request was settled.

Propose a separately versioned, independently reviewed **one-shot uncertainty exception**, expressly accepted by the human in the final packet. Keep the fixed owner namespace, original events, rows, amounts and dispatch count. The old receipt `4fc8f40cbc434a308f11e1094fae5d7a` remains UNCERTAIN, conservatively charged340 microdollars, provider cost UNKNOWN, and unfinished. Only that exact predecessor may coexist with the additional request. This is a disclosed change to the blanket stop policy, not reconciliation or compliance under unchanged V4 semantics.

The successor must fully replay and validate the original history before accepting a new amendment event. A successor control event may extend the same journal; the old V4 reader must fail closed on that unknown event. No requirement for legacy acceptance may be falsely claimed. The amended owner must remain accessible only through its independently reviewed successor after migration. Original files and original failed run remain preserved. No fake PHASE_COMMITTED, refund, changed old row, reduced unfinished count, bootstrap or cap reset.

## Required implementation invariants

The external amendment binds the exact prior owner header, current head, active approval, old-row canonical hash, fixed old receipt and340 charge, exact new request/release/price contract, fixed new run identity, absolute1000-microdollar/two-dispatch ceilings, expiry, independent code review and explicit owner acceptance of retained unknown billing. It must not bind its own hash or any descendant. The independent review binds the proposal/code/release; the final owner assertion binds that review. Actual hashes and dates remain null until independently reviewed and released.

A fixed original owner lock serializes admission across worktrees. Under that lock, verify the head and exact predecessor again; permit no other unfinished phase, new owner, alternate predecessor, charge reduction or changed caps. Atomically persist the one-shot amendment, new approval, price proof and new STARTED reservation in one SQLite transaction, then update the existing head anchor. All standard financial validations still apply; only the exact human-approved predecessor exception and explicit lifetime dispatch increment differ. Write-ahead request intent precedes POST. A capability is returned only after durable commit/anchor verification and acknowledged reservation. No lower-level public method may obtain another exception.

Before commit failure leaves no new events; failure after commit or anchor uncertainty consumes/holds the added allowance and blocks execution until read-only diagnosis. Missing acknowledgement is UNKNOWN, never zero and never permission to rerun. The amendment is permanently spent by the first new reservation; success, failure, cancellation, expired lease, fresh output directory, new key, new process or another worktree cannot restore it. After this additional reservation, no further model request is admitted without another explicit policy proposal. All observed new billing/errors remain recorded; old unknown billing remains disclosed even after new success.

Use the accepted closed safe diagnostic transport behavior from v4.2.1, through a separately reviewed integration contract. Log only closed stage/category/HTTP status, attempt counts and reservation observation; never response error text, request headers, key material or credential hashes. Keep accepted strict response/provider/usage/auxiliary cost checks and one new-request billing lookup. A diagnostic success must satisfy exact JSON shape plus observed provider/native usage/billing; engineering success is not an E01/E02 result.

## Acceptance before execution

1. Independent methods review accepts this explicit policy change, including its limits and evidence caveats. An objection is a concrete finding to resolve, not permission to bypass it.
2. Separate successor code passes authored unchanged-history, cap, wrong-predecessor, duplicate, stale-head, expiry, cross-process race, crash/anchor/lost-ack, unknown new billing and secret-redaction tests. Fake credentials, catalogs, model replies and temporary mocked OS homes only. No actual owner/key/environment/network access during implementation/testing.
3. Independent code review and final terminal-packet review bind exact files. Verify both original frozen history semantics and successor refusal paths. No command is issued until it points to these reviewed files.
4. The human approves the concrete one-request packet, explicitly retaining old unknown billing and amending the unfinished-phase stop for this one request. The existing $50 key limit is not this approval. Secure same-terminal key/prefunding assertion and valid reviewed prices remain required.
5. Execute at most once, then independently inspect retained new result/accounting. STOP on any error; do not tell the human to repeatedly rerun a stopped launcher.

All actual approval/release/time fields in `configs/json_compatibility_additional_test_v1_proposal.json` are null. No actual owner read/write, credential access, authenticated/public request or paid execution was performed to prepare this proposal. E01/E02 full research requirements remain unchanged.
