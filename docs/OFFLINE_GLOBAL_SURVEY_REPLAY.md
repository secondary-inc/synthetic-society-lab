# Reproduce the offline global survey pilot

Install the local Python project first, as described in the README. The command below uses authored fixtures only. It has no live-model option, reads no credentials and grants no production allowance.

Preview the exact engineering design without creating a scope or run:

```bash
.venv/bin/python scripts/offline_global_survey_pilot_v2.py --scope-id owner-review-001 --dry-run
```

Execute the full local primary/replay when ready for several minutes of local CPU and disk work:

```bash
.venv/bin/python scripts/offline_global_survey_pilot_v2.py --scope-id owner-review-001
```

The scope ID must be fresh. Existing scopes are refused before any work, so the command cannot overwrite or reset an earlier fixture ledger. The explicit new scope is a simulation, not an owner spending authorization. Both runs share its single ledger. Outputs stay in ignored `data/processed/runs/`; the private same-ledger replay receipt is under `data/processed/survey_global_fixture_scopes/owner-review-001/`.

The fixed design uses12 fictional ID/party profiles, three exact DEMO notices, five crossed arms,180 units and360 fake calls per run. The owned fake transport supplies60/40 answers. The zero change is an engineering oracle, not a model or human effect. Invalid-response/crash/concurrency cases are exercised separately by the integration tests. Raw phase files, response journals and fixture owner accounting remain private/unbundled.

Reference evidence: `SURVEY_GLOBAL_INTEGRATION_V2_MOCK_EVIDENCE.json` and `INDEPENDENT_AUDIT_GLOBAL_SURVEY_V2_MOCK_RAW.json`. The original direct-API primary/replay used the same reviewed engine and Python3.12.14, with deterministic projection SHA `4975d804a435bee57766d82987d81684cbafbecb2da00e6e6e34fbf4f0cb5378`. Random run/generation/receipt identifiers and times intentionally differ. The wrapper separately checks exact analysis and projection equality between its two fresh runs. Changes in inputs/code/runtime need their own review rather than rewriting historical evidence.

The wrapper's help, no-write dry-run, invalid scope and existing-scope refusal checks are recorded in `SURVEY_GLOBAL_REPLAY_COMMAND_CHECK.json`. Its full non-dry invocation has not been separately run; the underlying direct-API full pilot/replay and69 integration/component tests have independent acceptance. This wrapper is pending its own narrow review. Local development compute/storage/labor are not priced; actual model/network calls and experimental API spend remain zero.
