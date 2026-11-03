# Production E02 phase bridge v5.1 — closed methods successor

Methods only. All actual policy/review/operator instances are null, all authority is disabled, and no implementation or owner/key/network/source access is granted. The original v5 proposal and independent specification findings remain preserved at `8ffbb01`. This successor addresses those findings; independent acceptance is still required before S5A implementation.

The JSON companion `configs/production_survey_v5_1_methods_proposal.json` defines closed schemas, exact cross-field constraints, the acyclic hash graph, V4 field mappings, atomic append protocol, restart states, limits and tests. Its schemas describe future artifacts; they are not operator assertions or independent review receipts.

## Closed authority and derivation artifacts

Every object has the exact required fieldset, `additionalProperties:false`, built-in finite JSON types, no duplicate keys or coercion, bounded byte/node counts and canonical SHA256 serialization. Integer schema checks must also require Python built-in integers, rejecting booleans and floats. UTC strings require valid UTC calendar values and an increasing interval, not regex checks alone. Existing frozen validators still govern owner approvals, terms, contexts, rows and events.

The objects are PolicyBody (PB), ParentReview (R), externally supplied OperatorAssertion (O), Release (L), DerivationSeed (S), PhaseProof (FP), AdmittedPlan (P), and GrantReserveIntent (GI). Their full fieldsets and scalar ranges are in `$defs`. PB binds one fixed owner/header/initial head/active epoch, one run ID, a frozen compiled study/unit order, code/terms/source-gate hashes, scope label, positive absolute lifetime and per-module limits, a separate new-study money/count limit, UTC window and explicit bounded delegation. R binds that exact PB and its code/study/terms/gates. O binds PB and R and explicitly authorizes execution and the specified derivation; it supplies no new caps or template overrides.

Expected PB/R/O hashes must come from the trusted owner workflow. The adapter consumes these assertions; it does not mint them at runtime. Hashes and role strings are workflow bindings, not cryptographic human authentication or hostile-host isolation. The earlier key-credit screenshot and general autonomous-research instruction are not execution assertions. The current run03 unfinished phase still blocks actual admission.

Pre requests come from the frozen unit. A post requires the same unit's own PHASE_COMMITTED pre row, exact checkpoint bytes/output hash, original request/epoch, and parsed instrument result. There is no caller-supplied answer/payload interface. A financially verified but invalid pre produces an explicit skipped-post journal record with no grant/reservation/call. An uncertain pre halts the study.

## Acyclic hash order and ordinary-owner encoding

Let H mean the existing canonical finite-JSON SHA256. The graph in the JSON is authoritative:

1. Frozen compiled study CS, derivation/code contract D, terms T, scope-gate set G and the initial owner snapshot feed PB. R binds H(PB); O binds H(PB) and H(R). L contains only H(PB), H(R), H(O).
2. S binds H(L), the compiled unit-plan hash, unit ID, phase, and own-pre checkpoint hash (null for pre). Derive the exact payload/envelope from that plan and verified checkpoint. Observe at most one bounded fresh catalog response for this phase and bind the resulting price proof.
3. FP binds S, PB/R/O/L, plan/unit/phase, payload/envelope/price-proof hashes, the expected current owner head and active approval, own-pre witnesses, the journal prefix before GI, and durable phase start clocks. FP expressly excludes P, request binding, approval hash, final context and GI; it cannot contain a descendant hash.
4. P contains only H(FP) and H(S). Its hash is the final `context.plan_hash`. Build a draft V4 context with H(P), H(L), the exact payload/envelope/terms/price proof/run/unit/phase/sampling and a placeholder approval hash. Compute RB using unchanged `production_owner_v4.request_binding`, which excludes approval hash and price proof. H(P) nevertheless transitively binds FP's price proof and expected head.
5. Encode A as an ordinary closed V4 approval. Its ID is the first32hex of H({kind:DERIVED_APPROVAL_ID_V5_1, phase_proof_sha256:H(FP)}). Previous approval is FP's expected active hash; owner, validity and all lifetime/module caps come unchanged from PB; review is H(R), release is H(L), and credential assertion comes from O. Its allowed map contains exactly H(P), module E02, H(T), the prepared output/input ceilings and RB. No extra owner fields or event kinds are introduced.
6. AH=H(A). Replace the context's approval hash with AH and assert unchanged request_binding(context)==RB. Derive the expected reservation ID from H({kind:RESERVATION_ID_V5_1, phase_proof_sha256:H(FP), approval_sha256:AH}) truncated to32hex. Refuse collisions; do not generate a substitute identity. GI binds all these finished hashes, expected receipt/head/active epoch, release and journal prefix. Its `intent_id` is H(FP), not a self-hash.

The ordinary owner encoding is a derived binding under the earlier explicit delegation. It does not claim a fresh human or auditor action for each post. The original public `grant_operator_authorization` still admits only its fixed v4 release; it must not be monkeypatched or fed fabricated compatibility/review objects. A separately versioned v5.1 admission/batch-write bridge is required.

## Atomic authority, price proof and reservation

The new privileged helper is proposed as `production_study_owner_v5_1.append_admitted_phase`. Its batch persistence is new owner-control code requiring independent review even though the namespace, registration, header, event/row schemas and original validators remain unchanged. It has no bootstrap/reset/path override or generic raw-SQL/grant hook. It accepts only an exact privately admitted proof/capability from the reviewed v5.1 validator.

All private run files and the run lock live at the original fixed `production_owner_directory()/v5-runs/<PB.fixed_run_id>`, shared across worktrees. An immutable run marker binds PB/R/O/CS; no workspace/output-root override can hide an earlier intent. All v5.1 code acquires that fixed run lock before the original owner's nonblocking lock. Legacy v4 takes only its owner lock. Under the run lock, validate PB/R/O, own lineage and a read-only original owner snapshot; global unfinished state refuses before catalog/key/grant. Persist phase intent and its clock, observe the bounded price metadata, and persist FP/A/context/GI create-once. An already existing incomplete intent is not permission to retry.

Then acquire the original owner lock and `BEGIN IMMEDIATE`. Replay the unchanged original `_verify`; compare the full current anchor hash and active approval exactly with FP. Recheck the own checkpoint/journal prefix, policy/lease/price/caps and original unfinished state. No resnapshot-and-substitute or retry follows CAS failure. Validate the opaque credential/transport shape only after those final checks and before any write; constructing the transport makes no request.

Construct and apply in memory, using unchanged `_event`/`_apply`, exactly three standard bodies: APPROVAL(A), PRICE_PROOF(final context), RESERVE(the original STARTED row with the deterministic receipt). All three must validate before any SQL INSERT. Insert their chained events and one charge row in **one SQLite transaction**, commit once, and publish the original head anchor for the last event once. Calling the existing `_append` three times is forbidden: it commits per event and would expose approval without its reservation.

Reread the original verifier and prove the exact triplet, original prior rows, charge/context/price/approval/receipt and final anchor. Record the private acknowledgement. Only normal verified acknowledgement returns a dispatch capability. A successful triplet must remain readable by the original v4 verifier; no claim is made that the original v4 fixed-request factory understands the new policy.

After that acknowledgement, recheck source/clock/deadline and persist POST_INTENT before the single POST. Existing response/statistics/reconciliation/checkpoint/commit semantics follow. A global reservation barrier exists before any model request.

## Crash, lost acknowledgement and concurrent writers

If the SQLite transaction rolls back before commit, it creates no approval, price proof or reservation. Read-only diagnosis can report NO_COMMIT only with an intact verified owner store and absence of the exact expected triplet/receipt. Missing acknowledgement alone remains UNKNOWN. No automatic repeat follows even proven NO_COMMIT; the study halts and needs a reviewed continuation.

If database commit succeeds but anchor publication fails, original owner verification refuses the torn store. No POST, reset or automatic anchor repair follows. If commit and anchor succeed but acknowledgement is lost, STARTED and its full charge/unfinished barrier remain. The runner never redispatches from a reconstructed acknowledgement. There is no committed APPROVAL-only prefix and no false claim that approval alone creates the financial barrier.

If a model or statistics operation is uncertain, retain the reservation or higher safe known cost and the original global barrier. A durable statistics claim may consume its one-attempt authority even if the GET was never reached. It is never polled or retried. Known costs survive invalid/secret response content.

A fully PHASE_COMMITTED own row plus exact checkpoint/journal can support preapproved local paired-state completion without a model call. A next phase still needs its own new intent/CAS within the original policy. Foreign, missing, torn or uncommitted evidence blocks. Any runtime exception halts the study; valid billed quality failures are separately registered dispositions. Two processes using different roots/policies must compete on the same original owner head and reservation barrier; only one atomic triplet can win.

## Counts, budgets, sizes and time

One PB has1–180 distinct units and exactly two potential phases per unit, so its new-study dispatch ceiling is exactly2×unit_count≤360. Invalid pre answers can reduce observed calls; unused capacity cannot add units or retries. There is at most one POST, one statistics GET and one fresh catalog GET per admitted phase. All new calls are E02; no E01 phase is admitted. Lifetime module maps still preserve any prior E01 consumption.

PB has separate positive new-study money and absolute lifetime/module money/count caps. Exact nonnegative built-in integers must fit63bits; module caps cannot exceed their global counterpart, and every lifetime cap must cover retained consumption. The full frozen worst-case pre/post estimate must fit the new-study cap and initially available global/E02 allowances. Before each atomic reserve, conservative charges identified by H(L), plus the next reservation, must fit the study cap and count; unchanged owner checks additionally enforce all historical totals. Derived epochs never increase caps, extend time or erase prior consumption. Verified settlement can release only that request's unused reservation under existing rules; unknown charges cannot be refunded.

The full offline primary/replay test uses **two explicit MOCK policies**, each with180 units/360 fake calls and distinct fixed run IDs, under the same owner. Their absolute cumulative limits cover720 calls plus all prior fixture consumption; they never reset between policies. Exact mock request/scoring replay is not a deterministic-provider claim.

Both size constraints apply: encoded message bytes≤100000 (with at most16 messages), and complete serialized request≤262144. Input bound remains message bytes+1024×message_count, at most1000000; output≤4096tokens and raw HTTP reply≤2000000bytes. The frozen compiler's smaller ceilings still govern actual phases. The JSON specifies additional policy/proof/history/artifact limits. Full old owner history and temporary/atomic files count; a limit breach blocks rather than deleting history or expanding a cap.

The phase's **120-second cooperative wall budget** starts with durable phase intent and includes catalog, locks, hashing, local I/O, POST, statistics and bookkeeping. Each HTTP operation separately has a30-second cooperative total and15-second socket limit. Policy UTC lease is at most43200seconds and lies inside the fixed terms window. Before phase intent, the complete120seconds must fit before policy expiry. Monotonic/boot continuity and original UTC rollback checks apply. These are not hard OS deadlines.

No new catalog, POST or statistics request starts after its phase deadline or without valid authority. An already in-flight reply may still record safe known cost and complete local reconciliation under its original authority. If fully verified billing arrives late, commit a charged TIMING_FAILURE with no analytic answer; if billing cannot be verified, remain UNCERTAIN. Local accounting/checkpointing may finish after expiry; it grants no further network call or renewed policy.

## Gates and limitations

Independent S5M successor review must close the three original specification findings before implementation. Then S5A pure admission/batch-control fixtures, S5B single-phase/client crash tests, and S5C full two-policy720-fake-call journaled pilot require separate independent acceptance. The required oracles include real process deaths before/after triplet inserts/commit/anchor/ack, legacy-reader compatibility, zero-or-three events, CAS races, own-pre substitution, closed schema/hash-cycle rejection, lifetime-versus-study limits, both size ceilings and late accounting.

S5L remains separately blocked on authentic compatibility/billing, resolution of the existing owner uncertainty, accepted scientific or explicitly limited engineering sources, current prices, complete cost estimate and explicit owner positive execution approval. No reconciliation protocol, positive budget, actual study or live request is supplied here. All original research/population/earned-complexity/privacy/publication requirements remain unchanged.
