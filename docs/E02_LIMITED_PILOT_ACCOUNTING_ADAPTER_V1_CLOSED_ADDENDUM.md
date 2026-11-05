# Limited-pilot adapter: closed successor specification

November 5, 2026. Proposed companion to the v1 proposal; neither is execution
authority. Original proposal and independent findings remain unchanged. This
addendum supersedes the proposal's conceptual grammar and 16-MiB journal bound.

## Canonical objects and acyclic authority

`H(x)` is the existing canonical JSON SHA-256, `B(raw)` the raw-byte SHA-256.
All listed object field sets are closed, with duplicate/nonfinite JSON rejected;
all hashes are 64 lowercase hex, receipts and approval/review IDs 32 lowercase
hex, counters builtin nonnegative integers (never booleans). Unknown fields or
types fail. Every control object is detached before any callback or I/O.

The immutable price release L has exactly `{kind, terms, interpretation}`;
kind `LIMITED_PILOT_PRICE_RELEASE_V1`. Terms/interpretation retain the existing
production V4 validators, matching identity/semantic/interpretation hashes and
date windows. L contains no policy, authority or descendant reference.

Code contract K is the complete transitive implementation pin map plus exact
accepted protocol/compiler/sequence/evaluator/methods receipts and these limits.
Its field set is `{kind, pins, methods, protocol_sha256, projection_sha256,
assignment_sha256, limits}`, kind `LIMITED_PILOT_CODE_V1`. Pin paths are exact
repository-relative files, values their byte hashes; no caller-added modules.
Particular review must enumerate the final transitive map before any access.

Policy P has exactly `{kind, owner_id, predecessor, compatibility_receipt,
run_id, protocol_sha256, projection_sha256, assignment_sha256, code_contract_hash,
price_release_hash, limits, valid_from_utc, valid_until_utc}`; kind
`LIMITED_PILOT_POLICY_V1`. Predecessor has exactly `{header_hash, head,
history_hash, active_approval_hash, rows_hash, statistics_claims_hash}`; `head`
retains the original five-field owner head. Rows hash covers the entire receipt
to row map; statistics claims hash covers the sorted entire claim set. These
fields bind the two-row original history, not a filtered or synthetic snapshot.
P binds H(K), H(L), all exact accepted protocol hashes and one safe run ID.

Limits is exactly `{shared_microusd, study_microusd, module_microusd,
lifetime_dispatches, study_dispatches, study_statistics_GETs, catalog_GETs,
per_call_microusd, input_bound, output_tokens, retries, concurrency,
phase_seconds, HTTP_seconds, socket_seconds, authority_seconds,
price_age_seconds, event_limit, row_limit, event_bytes, journal_bytes,
journal_artifacts, artifact_bytes, minimum_free_bytes}`. Fixed values in order:
`5000000,1000000,{E01:0,E02:5000000},34,32,32,1,31250,8192,512,0,1,
120,30,15,7200,900,10000,1024,65536,268435456,256,2000000,536870912`.
No grant follows from a limit value. Study cost is separately tracked from the
immutable prefix and includes all study charges and outstanding holds.

R has exactly `{kind, reviewer_role, review_id, policy_hash,
code_contract_hash}`, kind `INDEPENDENT_LIMITED_PILOT_REVIEW_V1`, role
`independent_auditor`. R binds H(P)/H(K). O has exactly `{kind, policy_hash,
review_hash, consent_evidence_hash, assertion, credential_state}`, kind
`EXTERNAL_LIMITED_PILOT_OWNER_ASSERTION_V1`, binding H(P)/H(R) and the retained
verified human shared-$5 consent evidence. Assertion must equal
`RETAIN_OLD_UNKNOWN_CHARGE_ALLOW_ONE_32_PHASE_PILOT_WITHIN_SHARED_5_USD`;
credential_state equals `OWNER_ASSERTED_ROTATED_DEDICATED_KEY_AND_PREFUNDED`.
No code synthesizes this assertion on behalf of the human.

A has exactly `{kind, approval_id, policy_hash, review_hash,
owner_assertion_hash, code_contract_hash}`, kind `LIMITED_PILOT_AUTHORITY_V1`,
binding H(P)/H(R)/H(O)/H(K). It is a new authority type, not a fabricated
original V4 approval. T has exactly `{kind, reviewer_role, review_id,
packet_inputs_hash, code_contract_hash}`, kind
`INDEPENDENT_LIMITED_PILOT_TERMINAL_REVIEW_V1`, role `independent_auditor`.
The terminal packet Q has exactly `{kind, policy, review, owner_assertion,
authority, price_release, terminal_review}`, kind `LIMITED_PILOT_PACKET_V1`.
T.packet_inputs_hash is H(Q without terminal_review); H(T) is never a parent
of P/R/O/A/L/K. The operator supplies B(Qbytes) as an external expected hash.

## Runtime context and event grammar

Fresh proof C retains the original V4 closed proof schema. Validate the fetched
body with `fresh_proof` against L, exact URL, semantic hash and current clocks.
Store the observed raw metadata/proof once; never infer freshness from a dummy
proof made for static validation. Every initial study grant rechecks age<=900s,
term/P validity and full120-second fit. No catalog refresh or second attempt.

Let N be the next request recomputed by the accepted sequencer from authenticated
committed study witnesses. The phase plan J is exactly `{kind, authority_hash,
protocol_sha256, execution_order, phase, unit_sha256, payload_sha256,
pre_witness_hash}`, kind `LIMITED_PILOT_PHASE_PLAN_V1`. Its authority is H(A),
unit/request/hash fields are from N. For pre, pre_witness_hash=null. For post it
is H(W) of the exact same unit's committed pre witness below. All copied values
are checked against recomputation, not accepted merely because hashes match.

Context c retains exactly the original V4 closed `base_context` schema:
approval_hash=H(A); plan_hash=H(J); release_hash=H(L); price_proof=C;
run_id=P.run_id; unit_id=`exploratory-` plus execution_order as two decimal digits;
phase=N.phase; module=E02; terms=L.terms; envelope=N.envelope;
sampling={seed:N.pair_seed,temperature:0,retries:0};
payload_hash=N.payload_sha256. `base_context(c)` must pass unchanged.
Receipt d is first32 H({authority_hash:H(A),plan_hash:H(J),context_hash:H(c)}).

New initial grant transaction is exactly:
`LIMITED_STUDY_START, LIMITED_STUDY_GRANT, RESERVE`.
Later grant transactions are exactly `LIMITED_STUDY_GRANT, RESERVE`.
START payload is exactly `{packet:Q, code_contract:K, fresh_proof:C}`.
GRANT payload is exactly `{plan:J, context:c, receipt:d}`.
RESERVE payload retains `{before_hash:null,after:newrow}` with the original row
schema, id=d/statusSTARTED/reserved=charged=exact quote and all evidence null.
No intermediate transaction grammar may be acknowledged or opened for dispatch.

START requires no prior study; exact P predecessor head/full history/header/
active approval/rows/claims; exactly old UNKNOWN340 plus the additional
compatibility row PHASE_COMMITTED; all claimed compatibility billing/checkpoint
bindings valid; true unfinished1; old receipt and row unchanged. It installs A
in a separate study authority map, not the predecessor's original approvals.
Prefix replay remains byte-for-byte original semantics. STUDY state separately
tracks immutable predecessor hashes, study counters/charges, phase order,
witnesses and terminal failure. No old row can be an event target.

GRANT recomputes N/J/c/d from study state, immutable protocol/L/K and retained C.
Reject duplicate run/unit/phase/receipt, any unfinished study phase, stopped run,
exhausted money/count/capacity or changed same-unit pre. Stage a single pending
grant. The next event must be its exact RESERVE; install the original row and
update the true consumed/unfinished counts without masking the historical row.
Transitions may only target the current study receipt. Original row validation,
immutability/generation uniqueness, charge arithmetic and statistics-claim
predicates are reused, with explicit study authority lookup and exact original
context. Do not call the one-shot predecessor's post-amendment admission branch
for a study request or temporarily substitute its allowed_plans/unfinished.

All new START/GRANT/RESERVE kinds explicitly call original `_clock` and require
clock_status=OK, finite UTC, no rollback vs prior max; then enforce P/terms
validity, proof freshness and remaining full120 seconds. The original `_clock`
rollback-kind list alone is insufficient for these new kinds. Accounting
TRANSITION/STATISTICS_CLAIM/COMMIT bookkeeping preserves existing unavailable/
rollback clock evidence; bad clocks prevent further grants.

Each batch runs under the original guard and BEGIN IMMEDIATE, validates the
complete prefix/state under lock, constructs/replays the whole finite batch,
then writes its events/materialized row in one SQL commit and updates one
anchor. Commit then anchor failure leaves the store refusing. A readback checks
head/row before ACK is persisted. ACK loss gives no reconstructible capability.
The client consumes the opaque one-use capability and persists POST intent
before HTTP. No restart/resume can grant a phase with a reservation or intent.

## Response bounds, commit witnesses and failures

Preserve original raw response/statistics evidence privately, each body <=
2,000,000 bytes, and retain raw-byte hashes. No truncation, key/header storage or
silent sanitization. Transport overflow/read failure retains its diagnostic and
known monetary observations, marks the phase UNCERTAIN and stops; a missing
complete body is explicitly missing. Unsupported auxiliary activity or credential
content also stops with the full hold, never becomes a normal questionnaire miss.

Questionnaire parsing is a separate bounded quality operation after response
identity and monetary observations have been harvested. The exact selected
message.content must be a string of <=2048 UTF-8 bytes; exactly one JSON value,
no duplicate/nonfinite values, nesting<=8, object key length<=64 and string
length<=256. Numeric JSON values must be finite with canonical representation
<=32 characters. Any violation yields PARSE_ERROR/answer=null; preserve original
raw evidence and a fixed diagnostic enum, never a repaired/truncated answer.
Any successfully parsed bounded JSON value remains exact ANSWER, even if it is
an invalid survey object. This explicit quality parsing rule is additional to
the original protocol and requires methods acceptance before use; scoring and
whole-block exclusion rules remain unchanged.

After RESPONSE_SEEN and the one durable STATISTICS_CLAIM, strictly verify model,
serving provider, is_byok=false, native prompt/completion/reasoning bounds,
auxiliary activity and total cost consistency. Original cost helpers and
conservative higher-known-cost handling remain unchanged. Only timely verified
billing permits SETTLED. No ANSWER/PARSE_ERROR disposition is committed merely
because content could be parsed.

Commit witness W has exactly `{kind, execution_order, phase, receipt,
context_hash, payload_sha256, generation_id, response_raw_sha256,
statistics_raw_sha256, checkpoint_sha256, status, answer}`; kind
`LIMITED_PILOT_COMMITTED_WITNESS_V1`; status is ANSWER or PARSE_ERROR only.
Checkpoint has exactly original `{schema_version,run_id,unit_id,phase,receipt,
request_hash,output}`; output is exactly `{status,answer,response_raw_sha256,
statistics_raw_sha256}`. W repeats that exact output disposition and hashes.
W has no self hash; checkpoint never contains W or its hash, so no cycle.

New `LIMITED_STUDY_COMMIT` payload is exactly `{before_hash,after,witness}`:
before_hash=H(currentSETTLEDrow), after is exact PHASE_COMMITTED row with
checkpoint_hash=B(checkpoint), W agrees with context/receipt/output/billing and
parsed response. Under lock verify the actual bounded checkpoint and raw files
against W/row; replay checks retained witness hashes/output binding and strict
bounded parse predicates. Append event+materialized row+anchor with the same
fail-closed discipline. W's answer is in the financial event; future own-pre
reconstruction does not trust an arbitrary caller transcript or mutable path.
Keep checkpoint/output hash convention identical to original `commit_phase`.

The writer must stage the exact immutable commit witness before granting
PHASE_COMMITTED; ordinary original TRANSITION-to-PHASE_COMMITTED is denied for
study rows. All other original transitions retain their legal edges; terminal
UNKNOWN/OVERRUN cannot recover or authorize another request. Late verified
billing stays UNCERTAIN/fullhold with observed evidence, no witness/commit.
On any failure, terminate the run and fill remaining phases NOT_ATTEMPTED.

At commit/terminal export enforce each final phase record<=3072 canonical bytes
and the entire32-record envelope<=131072 bytes; depth/key/string/number bounds
already fit the accepted evaluator. Derived skips contain null answers. A
financially failed phase exports FAILED_UNCERTAIN or CANCELLED/null instead of
an uncommitted answer. If exporter bounds unexpectedly fail, preserve financial
history/raw files and report analysis NOT_RUN, never truncate data or dispatch.

## Finite storage and required tests

Private journal cap is256MiB/256artifacts/2,000,000bytesperartifact, with at least
512MiB measured free at entry. Before any request reserve worst-case complete
run capacity for64response/statistics bodies (128,000,000bytes),32requests
(8,388,608bytes),32checkpoints and32witnesses (2,097,152byteseachcategory),
metadata/packet/summary32MiB plus bounded event journal8MiB. Their sum stays
below256MiB/256artifacts. Check free/cumulative/artifact limits at every write;
capacity failure stops and retains an uncertain hold if already reserved.
Owner event/row admission similarly reserves space for the worst-case full
study: 193 events (one START plus 32 times GRANT, RESERVE, RESPONSE_SEEN,
STATISTICS_CLAIM, SETTLED and COMMIT) and 32 rows. Failure transitions replace
the unexecuted success tail; they do not add a second tail or recovery path.
Entry requires prefixevents+193<=10000 and prefixrows+32<=1024. Generation IDs
must match `gen-[0-9A-Za-z-]+` and be at most128 characters to fit the existing
statistics transport. Then enforce bounds before every batch/transition. No cleanup/reclaim
or permission to widen limits occurs during execution.

Independent tests must cover exact object graph and native type rejection;
initial/later atomic grammars; every new clock kind; original-prefix replay;
old-row immutability; aggregate and study caps including overruns; exact own-pre
witness binding; invalid-pre derived skip; response parse/serialization limits;
extra/duplicate/reordered events; generation/statistics uniqueness; all
transaction/anchor/ACK/intent/response/billing/commit crash points; and two-process
same-phase races. A 32-phase retained MOCK primary/replay must feed the evaluator
with truthful costs/provenance before an actual particular release is considered.
