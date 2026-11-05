# One billing-only recovery lookup

Status: prepared for separate owner approval; not executed.

The November 5 connectivity request reached the model. Its response-reported charge was recorded rounded up to
$0.000007, but the immediate generation-statistics lookup returned HTTP 404.
OpenRouter's [official tutorial](https://openrouter.ai/blog/tutorials/choose-best-ai-model/)
documents that generation records can become queryable a few seconds after the
model response. That is a likely explanation, not proof of this failure's cause.

The proposed action is exactly one authenticated GET to
`https://openrouter.ai/api/v1/generation?id=gen-1793870664-fiuZqWWWJpQTEUx4ZrXe`.
It fetches billing metadata for the existing request. It sends no new model
prompt, buys no credits, performs no account changes and has no automatic retry.
The collector uses the existing private, Git-ignored `.env` credential without
displaying or recording the key. It has a 30-second HTTP bound and a 15-second
socket timeout, with bounded response parsing and create-once local records.

The original run is `compatibility-additional-20261105-01`; its receipt is
`ddf80d6eb0222d75ad3ff5e42253534d`. Expected serving identity is
`openai/gpt-4.1-nano` through Azure, with at most 2,276 native input tokens,
32 native output tokens and zero reasoning tokens. The collector checks
generation identity, serving identity, billing mode, token bounds, auxiliary
activity and reported cost. The rounded $0.000007 response observation is retained
separately from any later metadata observation; its exact original decimal cost
was not retained.

Canonical parsed metadata and safe diagnostics are saved privately under
`data/processed/connectivity_billing_once/compatibility-additional-20261105-01/`.
They are not original HTTP wire bytes. No financial ledger is read or changed;
both $0.000340 holds remain in place. This lookup cannot recreate the missing
original response body, mark the failed run successful or launch the E02 pilot.

Implementation: `scripts/collect_connectivity_billing_once.py`, with offline
tests in `tests/test_connectivity_billing_once.py`. The candidate has passed 11 offline tests on both Python versions. Its source
SHA-256 is `6c9b093094a36a66ae9d99c5aeb5daf85227d624fb9819705f59c72712e49b2d`;
the exact execution contract hash is
`b5175bc8471dc93d68daa5f259c31a9d6630fca6dce8c3e2b0e838daa36fe955`.
Independent exact-code review remains required before execution.

Separate approval is necessary because the earlier one-request check explicitly
allowed one billing lookup with no retries, and that lookup has already been
used. The new approval would cover this one additional read only, with zero new
model requests and no increase to the research spending budget.
