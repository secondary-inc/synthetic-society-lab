# Owner survey client v3: authored candidate

Independent implementation review pending. The new client accepts an existing exact owner fixture, fake provider, externally expected compiled plan hash and explicitly expected approval epoch. It rederives E02 messages, unit, seed, terms and quote before reserving. It never silently substitutes the latest approval. Existing owner/planner/client/HTTP/journal modules remain byte-identical.

Thirteen new tests passed on Python3.11.17 and3.12.14. The combined targeted check passed74 tests; a separate prior bridge/budget check passed24, totaling98 across two invocations. Inspect `reports/SURVEY_OWNER_CLIENT_V3_CANDIDATE.json` and its logs for exact pins and scope. These checks include inherited process-death/race tests, not a clean restoration of the whole current project or provider compatibility test.

Tests inspect reservation before fake POST, request/provider/cost binding, externally committed checkpoints, stale approval after renewal, retained consumption, invalid-pre zero-write skips, invalid billed answer quality, aliases, duplicate generations, billing disagreement/overrun, cancellation and statistics failure. Expiry/rollback/unavailable-clock cases preserve the original epoch and known charge while blocking new dispatch. Nonfinite or custom invalid post baselines are classified without serializing them, then use the planner's skipped disposition. Success remains SETTLED until the caller makes the existing owner's exact durable checkpoint.

A retained authored two-phase control crosses two approval epochs with two separately rounded simulated microdollar charges. Three refused requests leave owner bytes and fake-call counts unchanged. Exact payloads, completions, owner history and hashes are ignored private artifacts. It is a client control, not a research dataset, survey run or scientific effect. Operational UUIDs differ on reproduction; request semantics, charges and refusal invariants are reproducible.

Reproduce from the checkout with an unused directory under the fixture scope:

```sh
PYTHONPATH=src:tests .venv/bin/python scripts/record_owner_survey_v3_fixture.py --directory data/processed/fixture_scopes/NEW-OWNER-CLIENT-CONTROL
```

The wrapper uses checkout-only test helpers and refuses existing/outside-scope/production output directories. The initial retained01 control predates this explicit wrapper guard and remains preserved; final02 used the guard. Both used the same client code. No actual production owner directory, human approval, secret or network provider was created or used. Fixture caps grant no spending authority.

The client alone cannot prove that a caller-supplied post baseline belongs to its own prior response, or authenticate an external plan hash/human approval. The later journaled bridge and production release must establish those bindings. No RunStore, journal, scoring, source/population/attrition release or live HTTP integration is included. Original trusted-local-store limits and unpriced development costs remain. Actual model calls and experimental spending are zero.
