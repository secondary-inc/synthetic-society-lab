# E01 ballot readiness v1.1 corrective amendment

This amendment addresses independent findings `IA-E01-BALLOT-LABEL-001` and `IA-E01-BALLOT-LIFECYCLE-001`. Implementer evidence is pending fresh independent review; this document does not certify closure.

## Correction to prior source description

The original implementation documentation, worker receipt, evidence and local v1 runs are preserved as historical evidence. Their descriptions of New Jersey's petition Party columns as blank were incorrect. The source prints **END THE CORRUPTION!** and **SOCIALIST WORKERS PARTY** in that column. The current parser preserves the full printed label in `source_party_label`, including text wider than the nominal column. It separately keeps `party_class=UNSPECIFIED` for these labels; that normalization neither infers nor denies recognized legal party status. No slogan-to-party inference is required to retain a printed source label.

The NJ list/certification cross-check now includes the full literal labels, so a change from one unrecognized label to another cannot disappear behind equal normalized classifications. Candidate contacts remain omitted. Original source bytes and their nine pins are unchanged; `configs/e01_ballot_readiness_v1_1.json` is an explicit new execution input copy with identical source content and config hash. Protocol schema remains1 because its input structure is unchanged. New code/test pins and new run IDs are in `reports/E01_BALLOT_READINESS_REMEDIATION_V1_1.json`.

## Failed-run preservation

`run_readiness` now creates its RunStore and config/code/environment provenance before local source verification and parsing. A parser, validation or cancellation exception seals `failure.json`, events, a terminal `summary.json` with status FAILED, and artifact checksums. Only the exception type is recorded, never its message or traceback. The original exception propagates after sealing. Failed parsing emits neither `ballot_readiness.json` nor `candidate_rosters.local.json`. The shared RunStore's completed event denotes ledger finalization; the explicit failed event, failure artifact and FAILED summary determine research-job status.

This covers ordinary exceptions and Python cancellation exceptions (`KeyboardInterrupt`, `SystemExit`); process kill, power loss and filesystem failure cannot be guaranteed to seal artifacts. RunStore construction failure is outside the admitted parser lifecycle.

## Preservation and reproduction

The six original readiness files were snapshotted, with hashes, at ignored local `data/processed/reproducibility/e01-ballot-readiness-v1-pre-remediation/`. Original v1 config, docs, reports and runs were not overwritten. The code/test entrypoints were updated for this correction. Batch02 acquisition receipts/cache remain frozen and are not merged into this input.

Run `PYTHONPATH=src .venv/bin/python -m unittest tests.test_e01_ballots tests.test_e01 tests.test_isolation` (38 passed). This includes a full-label mismatch under identical names/normalized classes; parser RuntimeError and cancellation failure ledgers; type-only error logging; checksum verification; absence of final artifacts after failure; and successful literal-label replay. Source execution: `PYTHONPATH=src .venv/bin/python -m civiclab.e01.ballots configs/e01_ballot_readiness_v1_1.json --root "$PWD"`.

Fresh source runs `e01-d2a62fec0a25420bbd0fad40e5ae1f96` and `e01-82750c6ed2a94e61a56da7479e628353` reproduce identical readiness/roster bytes. Both six-artifact ledgers verify. Injected parser failure `e01-413373ee05784e4aad046e611e93dd83` verifies its five-artifact ledger, terminal FAILED status and absent final readiness/roster artifacts. It records RuntimeError without injected detail. These are implementation checks, not independent acceptance.

Nine source hashes verify; the roster coverage remains NJ/NC only. All33regular slots remain present;31candidate documents are unacquired unblocked source jobs. Zero final ballots accepted; latest amendment review, source adoption, actual selection and original E01 gates remain unresolved. OH/FL ClassIII and FL20contexts remain separated. No outcomes or model calls were used; cost$0.
