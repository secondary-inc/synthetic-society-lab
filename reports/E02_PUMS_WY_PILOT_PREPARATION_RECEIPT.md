# Wyoming pilot preparation worker contract

TASK_ID: E02-PUMS-WY-PILOT-v1-PREPARATION.

FILES_CHANGED: New `configs/e02_pums_wy_pilot_v1.json`, `src/civiclab/e02/pums_wy_pilot_v1.py`, `tests/test_e02_pums_wy_pilot_v1.py`, `docs/E02_PUMS_WY_PILOT_PREPARATION.md`, `reports/E02_PUMS_WY_PILOT_PREPARATION.json` and this receipt. Comparison fixture handoff and all old sources/targets/v3/population files/runs unchanged. No shared CLI/packaging/dashboard/status/auditor edits.

OUTPUT_ARTIFACTS: Frozen preparation config/module/tests/runbook and aggregate preparation evidence. No actual PUMS archive or aggregate, no real pilot run or national target.

REPRODUCTION_COMMANDS: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v`. The actual predownload guard can be inspected/read-only checked but no actual acquisition call is authorized before its separate audit.

TESTS_RUN_AND_RESULTS: All43E02testsPASS, including7new PUMS cases using authored rows/ZIPs/fake byte transports. Hand sums/SDR/MOE/covariance/replicate proportions, signed replicate preservation, eligibility/domains/recodes/allocations, no identifier output, resource deadlines/bytes/rows, archive path/header/count safety, gate-before-network, immutable cache/quarantine/no-overwrite behavior verified. Actual null-approval guard separately returns BLOCKED and the real archive path does not exist.

SOURCE_DATA_AND_LICENSE_NOTES: No source fetch during preparation. Existing independently reviewed official5year PUMS dictionary/guide/accuracy/index/record-count hashes and proposal are frozen. Exact official Wyoming URL/state/product chosen; actual person hash unknown/null until a separately approved acquisition. Public person-only household/citizen filter requires no housing join, API key or restricted data. Raw archive/aggregate retention local ignored; aggregate-only sharing remains independently gated.

COST_USD_ACTUAL_OR_ZERO: $0API/model spend;0modelcalls;0actual personGETs/bytes. Local compute/labor not priced.

RISKS_AND_LIMITATIONS: Prepared bounds are not measured real-file resources; unexpected real member/schema/size/count blocks rather than changing the config. Parser projects only approved fields and flags low-support cells, with no anonymity/DP guarantee. Replicate weights are signed, count/ratio uncertainty conditional, zeroSE/undefined ratios flagged, full benchmark/model uncertainty not established. Pilot-only Wyoming is not a national benchmark or validated state synthetic population. Guarded trusted code is not an OS sandbox against hostile modification.

UNRESOLVED_BLOCKERS: Separate independent predownload resource/schema/privacy/code/fixture audit and exact pinned approval required for one sourceGET. Later actual archive/member/header/count/aggregate/uncertainty audit and replay before national scaling or fitting. Original adult/state/ANES transport/political-response scientific gates remain BLOCKED.

NEXT_UNBLOCKED_TASK: Auditor reviews stable preparation config/module/tests, including network guard/limits, safety/error policy, signed-replicate/SDR/covariance/proportion arithmetic and local-only disclosure. Lead pins a separate approval only if accepted; do not infer it from metadata-methods approval or supplied credentials.


## Version1.1 provenance pin amendment

Lead added executable scripts/ coverage to RunStorecode_identity, requiring explicit common.py SHA-256566c5f3947e3048a1521d1edfa2ee6e7ade7b66502e3b4ee6ee440573eb885fa pin refresh. PUMS module, fixtures, source/limits/fields/eligibility/arithmetic/downloader unchanged. Previous config/evidence bytes preserved as configs/e02_pums_wy_pilot_v1_0.json and reports/E02_PUMS_WY_PILOT_V1_0_PREPARATION.json. All45E02testsPASS. The read-only predownload guard still returns BLOCKED; actualpersonGETs/bytes0, archiveabsent and predownload_approvalnull. Old runs/audit reports untouched; a separate auditor must review refreshed required hash/design before download.


## Version1.2 acquisition-attempt lifecycle remediation

IA-E02-PUMS-ATTEMPT-001 identified missing pre-network attempt provenance. The new wrapper now creates a unique ignoredlocal attempts/wy-UUIDdirectory after approval/lock checks and before opening any network connection. It saves attempt.json(statusSTARTED) and the exact control-config.json, then fsyncs append-only stage events. Terminal success/cache-hit summaries record bounded archive/aggregate identity metadata; failures preserve error type, HTTPstatus if available, cancellation flag and quarantined relative path/bytecount/SHA when bytes exist. No raw person rows, row positions, exceptionmessages or HTTPresponse bodies are written to attempt metadata. Receipt-without-archive requires explicit reconciliation before another request; no automatic retry. An abrupt uncatchable OS/process kill can leave a STARTED/incomplete attempt, which must not be relabeled completed.

New synthetic injections cover HTTP503 before responsebytes, partial readOSError, invalidZIPvalidation, RuntimeErrorcrash and KeyboardInterruptcancellation. Each asserts manifest/config/events exist before fakeopener invocation, failedsummary survives, no archive/receipt is promoted, partialbytes are quarantined+hashed and raw/errorbody markers are absent from metadata. All47E02testsPASS, with8PUMSfixture cases. No actual personGET or archive occurred.

Timeouts are cooperative elapsed checks plus per-operation socket timeouts, not absolute OS-enforced wall-clock termination guarantees. Original resource values, schema, eligibility, point/replicate arithmetic and privacy thresholds remain unchanged. Previous1.1 config/code/evidence bytes are preserved as configs/e02_pums_wy_pilot_v1_1.json, reports/E02_PUMS_WY_PILOT_V1_1_IMPLEMENTATION.txt and reports/E02_PUMS_WY_PILOT_V1_1_PREPARATION.json. Old independent finding/audit reports are untouched; remediation acceptance is pending fresh independent review. Common.py remains frozen at566c5f3947e3048a1521d1edfa2ee6e7ade7b66502e3b4ee6ee440573eb885fa. predownload_approval remainsnull; no personacquisition under the comparison's separate executionapproval.
