# E02 wrapper visibility v1: pure implementation candidate

November 12,2026. Exact protocol/freeze and pure-code candidate, pending independent
code review. No paid release, serving proof, financial admission or scientific
result follows. The reviewed proposal and its design-only receipt remain intact.
The full original E02 contract, existing caps and historical holds stay unchanged.

## Ancestry and scope

`configs/e02_wrapper_visibility_v1.json` copies every scientific field from the
exact reviewed `e02_wrapper_visibility_proposal_v1_20261112.json`. It changes
only protocol identity/status/frozen flag, records proposal/review hashes, and
adds canonical instrument/topic hashes. `proposal_ancestry.design_changes` is
empty. The unit test compares every original field except those three explicit
administrative identity fields. The candidate's `frozen:true` means exact-byte
pinning in this implementation, not confirmatory registration, acceptance or
execution authority. No old result, proposal or protocol bytes were edited.

Eight fresh reference baselines and32 posts cross two text-format labels with
own-support visibility in four purposive fictional profiles and two authored
positive-evidence topics. Qwen/Nebius is fixed. Topics, questions, labels, seed,
quartet schedule, sample, missingness and all proposed operation/cost limits
are unchanged. Source labels remain constant; real sourcing/feeds and human
validity are untested. Earlier studies remain separate.

## Public API and data boundaries

All functions in `src/civiclab/e02/wrapper_visibility_v1.py` are pure: no file,
key, owner, network or inference operations. The caller supplies bytes and terms.

- `load_protocol(raw: bytes) -> dict`: requires the exact byte SHA,40 slots and
  canonical assignment/instrument/topics hashes. No implicit schema migration.
- `parse_response(provider_response) -> {status,answer,diagnostic}`: reuses the
  accepted strict duplicate/nonfinite JSON parser and bounded-object controls.
  ANSWER is bounded questionnaire syntax, not valid item scores, serving identity,
  absence of tools or authenticated billing. Financial/raw-response guards remain
  the separate client's responsibility. Item validity is assessed without repair.
- `valid_baseline(answer) -> bool`: bounded-object shape is checked by callers;
  known-key subset and finite numeric policy_support0–100 determine eligibility.
  Other missing/null/malformed known items do not gate it. Unknown extra keys do.
- `cost_envelope(raw, terms) -> dict`: validates a supplied complete fixed
  model/route/provider/output price contract and conditional all-in8192/256 bound.
  At most1785microUSD/call and40calls within75000microUSD. It does not establish
  price freshness, current ledger headroom or authority.
- `next_action(raw, terms, transcript_bytes) -> dict`: replays every supplied
  payload hash in exact order; returns REQUEST_READY_NOT_ADMITTED or COMPLETE /
  STOPPED with all40 dispositions. A ready request grants no capability to POST.
- `response_envelope(raw, terms, transcript_bytes, *, stopped=False,
  response_provenance='MOCK') -> dict`: replay-checks hashes, fills the40
  dispositions on completion/explicit stop and binds protocol, assignment,
  instrument,topics and provenance. Incomplete nonstopped exports are refused.
- `analyze(raw, envelope_bytes) -> dict`: validates every ordered phase/status,
  scientific skip and stop disposition and deterministically scores the envelope.
  It does not authenticate owner journals, invoices or the true origin of data.

A compiled request contains execution_order,phase,pair_seed,
baseline_execution_order,topic_id,wrapper,visibility,unit_sha256,request,messages,
payload,payload_sha256,envelope and actual_authority:false. Topic/wrapper/visibility
metadata do not enter the model prompt except the intended presentation label.
Model-visible request fields are phase,seed,profile,survey,item_order,notice,
and in SHOWN only pre_response:{policy_support:exact own number}. The survey
contains the exact topic support/factual questions and shared party items.
Notice contains only text,source_label,presentation_label. No answer keys, rights,
hashes, topic IDs or selection rationale leak into it. News/social requests vary
only the label; SHOWN/OMITTED vary only the own support field. Unit seeds and item
order are matched; this is not a common-RNG or deterministic-serving guarantee.

Transcript rows have exactly execution_order,phase,payload_sha256,status,answer.
Dispatched statuses are ANSWER,PARSE_ERROR,FAILED_UNCERTAIN,CANCELLED. Only ANSWER
may carry an object. A parse failure is retained with no replacement. An invalid
own pre derives two SKIPPED_INVALID_PRE SHOWN posts and retains both OMITTED
posts. A failure/cancel stops all remaining slots as NOT_ATTEMPTED. Extra,
duplicate,reordered,retried or wrong-payload rows are refused. A caller halt
before dispatch may export an explicit stopped prefix. Envelope records contain
exactly execution_order,phase,status,answer and do not fabricate dispatch hashes
for skips. All40 records must remain ordered and internally consistent.

## Scoring and quality

Known-key subset responses are scored itemwise. Missing key,missing null,invalid
value,invalid shape,parse failure,failed/cancelled disposition and unasked are
kept distinguishable. A malformed unrelated item does not exclude valid support.
No numeric strings/bools,imputation,repair,repeat baseline or cell retry.

`primary_wrapper_omitted` reports SOCIAL minus NEWS support per profile/topic,
planned8 and complete counts, raw values and descriptive mean/min/max. No valid
pre is required. Eight complete units yield a full-planned-sample descriptive
status; partial coverage is labeled partial; empty means remain null.
`visibility_interaction` and `matched_wrapper_contrasts` require own valid pre
plus all four supports and use that same unit intersection. They never subtract
unmatched marginal means. `absolute_wrapper_magnitude_change` and
`direction_diagnostics` report magnitude and reversals separately. No empirical
pass pattern or threshold triggers scaling or establishes an anchoring mechanism.

Topic/party strata and leave-one-topic-out results retain planned denominators.
Party-gap wrapper contrasts remain separate from custom support. Reference-to-post
support changes require their own valid baseline, while OMITTED wrapper effects
do not. Factual coverage reports correct/planned,correct/valid and observed wrong
answers separately from missing,invalid and unasked counts, per topic/wrapper/
visibility and baseline topic. Wrong factual answers never exclude support.
There is no p-value,inferential CI,equivalence or human-population claim.

## Verification and preserved evidence

Twenty focused worker tests passed on Python3.12.14 and3.11.17. Tests include
exact reviewed-proposal ancestry, seeded40-job reconstruction, both request
ablations, own-profile/topic baselines, reference exposure, independent numeric
quality, invalid-pre primary retention, same-intersection counterexample,
negative/positive signed interactions versus shrinkage, reversal, comprehension
coverage, partial topic/party counts, stop/cancel/parse/empty handling, malformed
JSON, tampered bindings, no retry, exact replay, zero/range extremes and pure
functions under forbidden filesystem/network boundaries.

Authored arithmetic oracles are not model positive controls: default OMITTED20,
SHOWN5,interaction-15; signed reversal20→-5 has interaction-25 and magnitude-15
but is flagged reversal; negative wrapper-20→-5 has positive interaction15 while
magnitude shrinks15. Zero/extreme/empty oracles retain the proper descriptive
limits. Full fixture transcripts,compiled requests,envelopes and scores are
retained under the ignored
`data/processed/e02_wrapper_visibility_v1_authored_20261112/final/` with an exact
index and visible MOCK_AUTHORED_NOT_EMPIRICAL provenance. Prices are authored test
contracts,not current releases. They contain no actual research responses.

The initial candidate and failed3.12 log remain under `initial/`: incomplete
nonstopped export exposed a KeyError,corrected to explicit ExecutionBlocked;
one test incorrectly expected missing unrelated thermometers to erase valid
support drift,corrected to require valid drift. Neither fix changes the design.
Later exact source/config/test pins and worker logs accompany the handoff. These
worker checks do not certify their own milestone; independent review is next.

Reproduce the focused suite with
`PYTHONPATH=src:tests .venv/bin/python -m unittest test_e02_wrapper_visibility_v1 -q`
and the local Python3.11 toolchain. No actual-source/key/owner/provider access
is needed. The lead separately owns financial integration,fresh prices,scheduled
catalog proof barriers10/20/30,all global caps andholds,full mocked admission and
the future head-bound one-shot release. None is supplied by this pure unit.
