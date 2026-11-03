# E01 v1.9 actual primary failure and code-only diagnosis handoff

TASK_ID: E01_TYPED_V1_9_CACHED_PRIMARY_REPLAY_20261103

FILES_CHANGED: New bounded explicit-release harness, aggregate failure evidence, authored diagnostic test and code-only diagnostic record below, plus this receipt. All frozen candidate/reference/source files and accepted Alabama module/runtime remain unchanged. No status, auditor finding, publisher WIP or commit edited.

OUTPUT_ARTIFACTS: Actual primary FAILED parent `data/processed/runs/e01-aadc141b93f74f69ad70f0279c67489e`; five-checksum-entry ledger SHA33f06b879fce052fbfa6dca7675e9e8a26538d095da6ea6fdd4e35de6af14ae1;6retained artifacts plus lock; immutable local control receipts `data/processed/e01_typed_v1_9_actual_control/release-20261103-e61f5e2b`. No typed payloads, typed commit or final seal. Exact handoff SHA-256:

- `scripts/e01_typed_readiness_v1_9_actual_release.py`: `381594340533b7e87c20f7b37f1db409edb36f1fad0d6a770e4229710e971126`
- `reports/E01_TYPED_READINESS_V1_9_ACTUAL_PRIMARY_FAILURE.json`: `5a664a3a01128426885d087d06fe7ad6434502521f464e1c9753d131bbf7f671`
- `tests/test_e01_typed_readiness_v1_9_tuple_diagnosis.py`: `75e91a2f96afd2f1235877e78b37eec33adf842c87bfcd34ea5e6a9fffd554e9`
- `reports/E01_TYPED_READINESS_V1_9_CODE_ONLY_TUPLE_DIAGNOSIS.json`: `e486248d6156b6c94a041b1e01666f6e0c2fe0bef8ff3e8ee183677c7ebc003c`

REPRODUCTION_COMMANDS: Executed preflight and primary only using `PYTHONPATH=src .venv/bin/python scripts/e01_typed_readiness_v1_9_actual_release.py <phase> --control /Users/joshua/Documents/ChatGPT/synthetic-society-lab/data/processed/e01_typed_v1_9_actual_control/release-20261103-e61f5e2b --execute-lead-release E01_TYPED_V1_9_CACHED_PRIMARY_REPLAY_20261103`. Do NOT rerun actual phases: immutable starts reject retries; primary/replay need independent diagnosis/new release. The separate authored diagnostic commands in its JSON may be repeated without actual source access.

TESTS_RUN_AND_RESULTS: Actual preflight verified declared40source/fourreference hashes/sizes, exact21oldcode/config/audit pins plus candidate/wrapper/acceptance pins, Python3.12.14 and20accepted runtime versions includingpdfplumber0.11.9. First actual primary raised CaptureRejected with sealed ValueError, FAILED summary, valid checksum ledger and zero diagnostic bytes. No typed/private payload or seal was published. Replay NOT_RUN; no automatic retry. One new authored native-NE-bounds diagnostic test passed Python3.12.14(0.057s)/3.11.17(0.048s); it demonstrates strict tuple-versus-JSON-list object equality can reject byte-identical legacy payloads. This is a static/helper-shape-compatible authored reproduction, not confirmation of the actual internal failure trace. Frozen candidate code unchanged.

SOURCE_DATA_AND_LICENSE_NOTES: Actual preflight/primary used only the declared40cachedsources/fourreferences and accepted pure helper/runtime under lead release E01_TYPED_V1_9_CACHED_PRIMARY_REPLAY_20261103/code audit e61f5e2b. All raw/private bytes remain ignored/local; report contains hashes/paths/runtime/static errors only. After failure, no further actual source/reference/helper/readiness invocation occurred; diagnostic uses temporary authored files and stubbed components. Existing source roles/UNKNOWNs/rights remain unpromoted. Alabama actualPDF/render/transcription remains unopened.

COST_USD_ACTUAL_OR_ZERO: $0 experimental model/API spend; zero GET/acquisition/outcomes/publisher/model/paid calls or source expansion. Local development compute/labor unpriced.

RISKS_AND_LIMITATIONS: Preflight byte identity does not prove the integrated actual parse/assembly works. Generic ValueError does not establish the failed internal stage; no actual rerun was performed to expose a traceback. The code-only test finds a concrete native-tuple/list comparison blocker but independent diagnosis must adjudicate its relation to this actual failure. Because no final seal/payload exists, this run is a sealed failure rather than post-seal acknowledgment ambiguity. Do not rewrite/delete it or treat its completed event as success.

UNRESOLVED_BLOCKERS: Independent read-only failure/source/code diagnosis and exact finding; separate reviewed versioned remediation and new execution release if needed. Primary/replay/payload comparisons remain incomplete. Current accepted12documentstates/21unfinishedjobs/0finalballots unchanged. Source-policy/legal/final/latest/geography/selection/forecast/science gates remain.

NEXT_UNBLOCKED_TASK: Independent diagnosis reviews preserved failed parent/control/metadata/code and authored test. Worker may prepare separate Alabama actual-literal-admission METHODS without any actualPDF/render/source access; no v1.9 retry or frozen-code modification.
