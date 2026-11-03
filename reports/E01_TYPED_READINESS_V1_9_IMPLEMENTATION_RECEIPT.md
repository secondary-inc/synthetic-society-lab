# E01 v1.9 authored integration handoff

TASK_ID: E01_TYPED_READINESS_V1_9_AUTHORED_INTEGRATION

FILES_CHANGED: Six new candidate/doc/evidence files below, plus this receipt. No legacy component, shared CLI, viewer, status, auditor record, publisher WIP or Git commit changed by this task.

OUTPUT_ARTIFACTS: Authored-fixture candidate only. Exact SHA-256 pins:

- `configs/e01_typed_readiness_v1_9_candidate.json`: `f906665266fa7f816d37002e677fdc1d3e99bcefe7a1c1163d56bc91eb48a5ac`
- `src/civiclab/e01/ballots_v1_9.py`: `c4f9cdde81cd58b9b2c5f97e6ac41dab4764b48c12376be732887e254a3be04a`
- `tests/test_e01_typed_readiness_v1_9.py`: `6a00ba117f30e7d7c09be627c39f598b7611007f5f3564abf64514948e80149f`
- `docs/E01_TYPED_READINESS_V1_9_IMPLEMENTATION.md`: `0b4f888af896cfa800f34b5cd3c41925f496a6d19f24bdcb10cf78b38c365a58`
- `reports/E01_TYPED_READINESS_V1_9_IMPLEMENTATION_EVIDENCE.json`: `18800fc7ab71c6daa154b899ed8346ebf00ed7c6adad3209392300c279de76bf`
- `reports/E01_TYPED_READINESS_V1_9_DEVELOPMENT_FAILURE.json`: `710be2eedb9f87495427e044a14a6988360e43127df95ac229e2576bd5ad0a19`

REPRODUCTION_COMMANDS: The three exact commands and interpreter versions are retained in the evidence JSON and implementation document. Run `PYTHONPATH=src .venv/bin/python -m unittest tests.test_e01_typed_readiness_v1_9 -q`; substitute the documented bare Python3.11 binary for supported-runtime checks; run `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e01*.py' -q` for E01 regression.

TESTS_RUN_AND_RESULTS: Final 18 targeted tests passed on Python3.12.14 (4.707s) and Python3.11.17 (3.995s); final173 E01 tests passed on Python3.12.14 (8.213s). Exact candidate code/config/test identities unchanged before/after. All21 historical code/config/audit pins match. Worker execution evidence only: independent implementation acceptance remains NOT_RUN. Two earlier added fixture-harness errors are retained separately and corrected.

SOURCE_DATA_AND_LICENSE_NOTES: Read only code/config/docs/public evidence metadata in the actual checkout. No actual raw source or private reference body opened/hashed, no actual component helper/readiness execution. All new source I/O in tests uses temporary authored40-source fixtures and DEMO records; wrapper component boundaries are explicitly stubbed. Source declarations are40 distinct IDs/paths totaling3,760,839bytes; declaration arithmetic is not an actual-source integrity claim. Rights and original source-role limits remain unchanged. Named data stays local-only, ignored and package-refused.

COST_USD_ACTUAL_OR_ZERO: $0 actual experimental model/API spend; zero model/network calls. Development compute/labor is unpriced.

RISKS_AND_LIMITATIONS: Twelve exact legacy objects/whole payload bytes and separate five Idaho typed records are required by the wrapper. New typed13/20 fields are conditional candidate observations, not accepted coverage. A separate terminal seal gates consumers after final rechecks and binds the full parent ledger. Failure/cancel/partial writes retain type-only errors and invalidate published success; persistent disk failure cannot guarantee durable failure evidence. Same-host hashes do not provide hostile-host or external immutable-timing guarantees. No scientific/nominee/legal/geography/source-policy/latest-amendment authority follows.

UNRESOLVED_BLOCKERS: Independent exact code/privacy/lifecycle/fixture review; then separate lead authorization before any actual40-source/reference execution or recorded readiness/replay; then independent post-run review before status/coverage changes. Current accepted12 document states/21 unfinished source jobs/0 final ballots unchanged. Real selection and forecasting remain blocked independently.

NEXT_UNBLOCKED_TASK: Independent reviewer inspects exact candidate and evidence pins, exercises the fixtures and records its own findings. Lead retains status and execution-release ownership. Do not invoke the new wrapper on the actual checkout yet.
