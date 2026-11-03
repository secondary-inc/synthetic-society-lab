# Local-reuse approval-negative fixture isolation

TASK_ID: E02-PUMS-WY-LOCAL-REUSE-v1.2-TEST-ISOLATION.

FILES_CHANGED: `tests/test_e02_pums_wy_local_reuse_v1.py` now deep-copies config, sets explicit null approval, uses a temporary root and asserts no data/run directory was created. Active local-reuse config has a versioned test-only amendment, changed test pin and null fresh-approval gate. All other required-file hashes unchanged. Runbook appended. No implementation/parser/source or auditor changes.

OUTPUT_ARTIFACTS: `configs/e02_pums_wy_local_reuse_v1_1_consumed.json` preserves approved consumed config SHA `300d93c14762930294627dbc6ba0718d7b514e2c03a0e12518685aa76c15cf71`. `reports/E02_PUMS_WY_LOCAL_REUSE_V1_1_CONSUMED_TESTS.txt` preserves reviewed test SHA `71ebd98c00c1b91deecb41442eac3018bc3d3961d106b0cf1ae4e7b62c8700c8`. New evidence: `reports/E02_PUMS_WY_LOCAL_REUSE_TEST_ISOLATION_EVIDENCE.json`. Exact prior approval/design and completed aggregate/replay run artifacts remain unchanged.

REPRODUCTION_COMMANDS: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v`. For positive repository-state sensitivity, instantiate `LocalReuseFixtures`, call `setUp`, replace `self.config` with the consumed approved config and call the negative test. It still passes without modifying that config or creating any actual run. Worker performed this additional check.

TESTS_RUN_AND_RESULTS: All 53 E02 tests PASS. Negative fixture also passes with a valid consumed approval in input config, leaves that config unchanged and creates no actual run directory. Both previously completed actual runs' eight sealed checksums reverified. Only test required-file pin changes; module `a6aa...` and original parser `7299...` remain unchanged. Worker evidence is not independent acceptance.

SOURCE_DATA_AND_LICENSE_NOTES: Authored fixtures only for this delta. No actual person processing, source mutation or new acquisition. Existing local-only actual aggregates and disclosure restrictions remain unchanged.

COST_USD_ACTUAL_OR_ZERO: $0 API/model spend; zero network/model calls.

RISKS_AND_LIMITATIONS: Isolated negative test only; no altered research selection, parsing, aggregate math or approved past execution. Fresh config intentionally has no execution approval; consumed prior approval remains preserved rather than being represented as authorizing a changed design.

UNRESOLVED_BLOCKERS: Fresh independent test-only design delta; separate actual-source/arithmetic/disclosure reviews still pending. No future actual processing authorized by this amendment.

NEXT_UNBLOCKED_TASK: Independent auditor reviews versioned config/test delta and completed actual run evidence. Lead owns status/integration.
