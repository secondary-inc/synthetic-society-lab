# N1 v1.1 ledger/disk remediation worker contract

TASK_ID: E02-NATIONAL-PUMS-N1-v1.1-LEDGER-DISK-REMEDIATION.

FILES_CHANGED: Owned national_budget.py, N1 config/test/doc/evidence/receipt. national_population.py and original WY/runtime/common/N0 files unchanged. Added exact reviewed v1.0 config/code/test/doc/evidence/receipt snapshots with explicit `_V1_0` names. Auditor findings file unchanged and pinned. No shared/status/Git edits.

OUTPUT_ARTIFACTS: Ledger format2 genesis and hash-linked committed state/event chain; independently derived semantic resource counters/schema/state invariants on reopen and every transition; current free-space/retained/log/atomic-write headroom before all durable transitions. v1.1 evidence `reports/E02_NATIONAL_PUMS_N1_EVIDENCE.json`. New MOCK run `e02-4fc7faa5dcde4300a0975e51ef70a814`, seven sealed checksums verified. MOCK primary/replay file SHA remains `e20577e2833e1542ce1386cb57b580edb20719045fc94df92b09c0d040790c07`; all prior runs/evidence preserved.

REPRODUCTION_COMMANDS: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -q`. New format must use new controls; old ledgers are not migrated/reset. Preserved v1.0 source/config can inspect old v1.0 artifacts. Current ignored authored demonstration script is `data/processed/e02_national_n1_authored_pilot_v1.py`; hash/config/run evidence recorded. No real source action is authorized.

TESTS_RUN_AND_RESULTS:75E02tests PASS including19N1cases. Exact independent4→0/8,195byte-limit probe refuses on reopen without changing generations/events or permitting a second attempt. Other own-resource counter resets, schema/domain/status/active/event corruptions refuse. Current free0/reserve100 refuses enrollment and processing before any child. Space lost after child but before source/processing checkpoint preserves pending full reservations, refuses result commit and even failure/recovery persistence while unavailable; restored-space recovery records unknown failure without refund. Retained/log exhaustion refuses transitions. Prior real crash/torn/concurrency/cancel/resume/resource/51-state replay/covariance fixtures still pass. Worker tests do not certify independent resolution.

SOURCE_DATA_AND_LICENSE_NOTES: Authored fixtures only; no actual person source GET/enrollment/parse, raw respondent export or new metadata request. Same approved public metadata pinned. All reviewed v1.0 snapshot hashes verified against the independent findings' exact code_files values. Original actual source/run history untouched.

COST_USD_ACTUAL_OR_ZERO: $0 API/model spend,0realGETs/personrows/models/fits. New MOCK demonstration retains50fake deliveries/58,550bodybytes,102authoredprocessingrows,281,520reader-deliveredexpandedbytes and1.553chargedprocessingseconds. These are fixture metrics, not national resource guarantees; local compute/storage not priced.

RISKS_AND_LIMITATIONS: Genesis/hash commitments and semantic reconciliation protect internal consistency, not coordinated adversarial replacement of all history. Storage checks are current snapshots and projected logical-byte headroom, not a guarantee against another writer exhausting disk afterward. If persistence itself fails, the prior durable reservation/torn state remains blocked; no false terminal-success/refund claim. Event/state integrity work adds overhead; no national throughput claim. POSIX sampled resource limitations and application-versus-wire counting boundaries remain. Actual adapter does not exist and always refuses.

UNRESOLVED_BLOCKERS: IA-E02-N1-LEDGER-001 and IA-E02-N1-DISK-002 remain auditor-owned findings pending fresh independent resolution. No N1 acceptance or N2 actual source authority claimed. Real acquisition/enrollment/parse, national arithmetic/resource/disclosure, broader original adult/state target/model evaluation, paid inference and publication remain separate gates.

NEXT_UNBLOCKED_TASK: Lead sends versioned delta, preserved snapshots, exact pins,19case suite and new MOCK artifacts to independent auditor. Fix further findings before advancement; do not use previous approval/evidence to enable actual source actions.
