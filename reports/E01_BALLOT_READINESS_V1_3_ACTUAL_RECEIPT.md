# E01 ballot readiness v1.3 actual run receipt

TASK_ID: E01_BALLOT_READINESS_V1_3_ACTUAL

FILES_CHANGED: New `reports/E01_BALLOT_READINESS_V1_3_ACTUAL.json` and this receipt only. Audited code/tests/config/source pins were verified before execution and remain unchanged. Original inputs/runs, batch02 receipts and auditor findings untouched.

OUTPUT_ARTIFACTS: Recorded source-only readiness `e01-5bb6231c06494cd086e49eda1d643b65`; exact replay `e01-f1bd9dc13797462bad3651d0a3515d12`. Both local runs contain six sealed artifacts, including ignored/unbundled `candidate_rosters.local.json`. Evidence JSON records each ledger's SHA256 and each artifact hash, including roster digest, but no named roster/contact content.

REPRODUCTION_COMMANDS: First verify all current code/config pins in `INDEPENDENT_AUDIT_E01_BALLOT_V1_3_CODE_FIXTURES.json` and all14source hashes. Run twice: `PYTHONPATH=src .venv/bin/python -m civiclab.e01.ballots configs/e01_ballot_readiness_v1_3.json --root "$PWD"`; verify checksum ledgers, compare `ballot_readiness.json` and `candidate_rosters.local.json` bytes. No network needed or used.

TESTS_RUN_AND_RESULTS: Prior independently reviewed47-test fixtures are unchanged; not unnecessarily rerun here. All7audited implementation/history/config pins match; exact14sourcepins match and filehashes verify. Both actual source runs succeeded; all12runartifact hashes verify. Readiness and localroster replay byte-identical. Five official-document roster states CO/NC/NJ/VA/WY; all33regularslots preserved;28candidate sourcejobs remain explicitly unacquired/unblocked. CO6printed/3qualifiedwritein; VA2/WY2documentrows. Zero finalballotsaccepted. Narrow context facts remain observed; context IDs unchanged outside regularquotas.

SOURCE_DATA_AND_LICENSE_NOTES: Existing local official government source bytes only. No new GETs, rawdocuments/contactdata/rosters in report or package. Literal printed party/designationlabels retained, unknown normalization does not imply legalrecognition. COinlinewithdrawal count0 and WYprintedwithdrawaldate count0 describe obtaineddocuments only, not absenceoflateramendments. VAlateralloffices comparison remains pending.

COST_USD_ACTUAL_OR_ZERO:0; no model calls.

RISKS_AND_LIMITATIONS: Implementer actual execution pending independent result/ledger review. Extraction is not finalballot acceptance, asofarchive proof, ratings adoption or race sample selection. No exclusions based on publisher flag/writein/withdrawal observations; noactualsample selected. Fulloriginalmanifest/scientific gates remain unresolved. Localroster artifacts intentionally unbundled; any disclosure-safe derived run requires separate review.

UNRESOLVED_BLOCKERS: Independent actualrun/result acceptance; later amendments and finalballot checks;28remainingunacquired sourcejobs unblocked/incomplete; VAofferedalloffices sourcecomparison; originalsource/geography/selection/holdoutgates.

NEXT_UNBLOCKED_TASK: Auditor independently verifies both actual ledgers, candidate-label format observations and replay, then lead may commit accepted v1.3 and update true coverage. Continue separately versioned official-source acquisition/VAcomparison after freeze without modifying these pins or claiming final acceptance.
