# Limited-pilot adapter v1.1: response before statistics

November 5, 2026. Proposed methods correction only; no implementation or actual
execution authority. Preserve the v1 proposal, closed addendum and independent
ordering finding unchanged. The composite specification is those two documents
plus this addendum, which supersedes only the checkpoint output definition and
its relationship to the later statistics hash.

The checkpoint retains the original closed field set
`{schema_version,run_id,unit_id,phase,receipt,request_hash,output}`. Its output is
exactly **`{status,answer,response_raw_sha256}`**, entirely known after the model
response and bounded questionnaire parsing, before any statistics request.
At RESPONSE_SEEN set `row.output_hash=H(output)`. That non-null hash never
changes. No statistics raw hash appears inside output or its hash projection.

Only after that transition may STATISTICS_CLAIM be written and the one billing
GET occur. Verify its identity, provider, usage and cost; retain its exact raw
bytes and B(statistics_raw). Only then may SETTLED and checkpoint/commit occur.
No speculative future hash or replacement of response evidence is permitted.

The later W retains its existing exact field set, including
`statistics_raw_sha256`. Its status, answer and response_raw_sha256 repeat the
exact checkpoint.output values; its statistics_raw_sha256 binds the separately
retained verified billing response. Before committing, check raw statistics
identity and its allowlisted billing values against row.billing, plus B(raw)
against W. W.checkpoint_sha256 binds the checkpoint bytes. Neither checkpoint
nor response output contains W, H(W), or future statistics evidence. Thus the
order is response/output hash → statistics claim → statistics raw/hash and
settlement → checkpoint bytes/hash → W → commit event. Post plans later bind
H(the committed own-pre W). All original non-null output immutability,
checkpoint-output hash equality and no-commit-before-settlement rules remain.

The pure parser's `diagnostic` enum belongs in the private quality record; it is
not an extra checkpoint.output field. No parser return object may be substituted
for the closed three-field output without constructing and hashing that exact
projection before RESPONSE_SEEN.
