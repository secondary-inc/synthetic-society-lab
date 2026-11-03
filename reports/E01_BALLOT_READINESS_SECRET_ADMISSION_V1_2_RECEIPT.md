# E01 ballot readiness metadata admission v1.2

TASK_ID: E01_BALLOT_READINESS_SECRET_ADMISSION_V1_2

FILES_CHANGED: `src/civiclab/e01/ballots.py`, `tests/test_e01_ballots.py`; new `configs/e01_ballot_readiness_v1_2.json`, `reports/E01_BALLOT_READINESS_SECRET_ADMISSION_V1_2.json`, this receipt. No common.py changes. The v1.1 six-file snapshot and hashes are preserved under ignored `data/processed/reproducibility/e01-ballot-readiness-v1_1-pre-admission-remediation/`. Prior configs/docs/evidence/runs and batch02 acquisition receipts/cache remain untouched.

OUTPUT_ARTIFACTS: Successful runs `e01-f1de103d63af446ab3ed0400ece82845`, `e01-b2fbe45cfef841f49add4a9eeccf2901`; sealed injected RuntimeError failure `e01-6dfc1683af5e4f0e8363a77b18a9206b`. New code/test/config hashes recorded in evidence JSON. Source pins/config content unchanged but new input filename/version explicit.

REPRODUCTION_COMMANDS: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_e01_ballots tests.test_e01 tests.test_isolation`; `PYTHONPATH=src .venv/bin/python -m civiclab.e01.ballots configs/e01_ballot_readiness_v1_2.json --root "$PWD"`.

TESTS_RUN_AND_RESULTS:40targeted tests passed. Five synthetic metadata probes (URLuserinfo, Set-Cookie, Authorization, querytoken, CRLFinjection) all reject before RunStore/parser calls and leave no run directory or marker bytes in any fixture file. Admitted source-hash, RuntimeError, KeyboardInterrupt and SystemExit failures remain sealed with type-only errors and no final readiness/localroster result. Full NJ literal-label retention and certification mismatch checks retained. Actual success readiness/roster replay bytes identical; all17artifact hashes across three actual runs verify. No real credentials involved or tested.

SOURCE_DATA_AND_LICENSE_NOTES: No new requests/downloads. Same nine official pins; no contacts reported. NJ literal correction remains END THE CORRUPTION! / SOCIALIST WORKERS PARTY, normalized UNSPECIFIED without legal recognition inference. Source discovery batch02 remains separately frozen.

COST_USD_ACTUAL_OR_ZERO:0; no model calls.

RISKS_AND_LIMITATIONS: Pending fresh independent audit, not self-certified. `admit_metadata` runs without file reads or logging and validates top/source schema, official HTTPS URLs without userinfo/query/fragment, allowlisted response header names and no CR/LF header injection. Error messages contain no rejected values. RunStore receives only role and canonical config_sha256, avoiding full untrusted configuration text in its manifest. The complete reproducible input remains in the separately versioned config file, pinned by the manifest's canonical digest; file-byte hashes are separately in evidence. This supersedes v1.1's full-config manifest behavior, without modifying old runs. It is not a general secret scanner for arbitrary government document text or free-text output. Source bytes/hash/PDF parsing remain inside the recorded lifecycle after metadata admission; power loss, process kill or storage failures cannot guarantee final sealing.

UNRESOLVED_BLOCKERS: Fresh independent acceptance of IA-E01-BALLOT-ADMISSION-SECRET-001 and retained v1.1 fixes. Original gates remain:33regularslots/2rosterstates/31unacquired unblockedsourcejobs/0finalaccepted. No source adoption, actual selection, outcomes or prospective claims. Old failed historical implementation evidence remains immutable.

NEXT_UNBLOCKED_TASK: Auditor reruns synthetic credential-location rejection and admitted failure/replay probes under new hashes. Source expansion remains separate; do not merge batch02 or promote final ballots during this review.
