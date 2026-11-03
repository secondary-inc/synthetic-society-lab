# Citizen comparison implementation worker receipt

TASK_ID: E02-CITIZEN-COMPARISON-v1-IMPLEMENTATION-FIXTURES-IDENTITY.

FILES_CHANGED: New `configs/e02_citizen_comparison_v1.json`, `src/civiclab/e02/cohort_reference_v1.py`, `src/civiclab/e02/citizen_scenarios_v1.py`, `src/civiclab/e02/citizen_comparison_v1.py`, `tests/test_e02_citizen_comparison_v1.py`, `docs/E02_CITIZEN_COMPARISON_V1_RUNBOOK.md`, `reports/E02_CITIZEN_COMPARISON_V1_FIXTURE_EVIDENCE.json` and this receipt. No old target/source/population/support/v3 module/config or prior run edited; no shared infrastructure edits.

OUTPUT_ARTIFACTS: Actual identity-only run `e02-80dc42b6dd104c319096ae77bdce7aef`; aggregate identity fixture evidence receipt. No real fitted distributions, calibration runs or real scenario targets produced by this task.

REPRODUCTION_COMMANDS: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v`; `PYTHONPATH=src .venv/bin/python -m civiclab.e02.citizen_comparison_v1 identity`. The real compare CLI is NOT RUN and remains blocked by null execution_approval.

TESTS_RUN_AND_RESULTS: All36 E02 tests PASS. Five new tests cover full recode categories/age boundaries/exclusion branches and exact transient member/weight/recode/design/split identity tampering, eight rounded-input transfer directions and source nonmutation, preserved99.8 rounded education sums/25+ anchors, clipping and invalid mass, forty-configuration coverage, four model objects reused ten times each, failed configurations retained, shared500draw bootstrap and gate-before-real-load/fit. New numerical fitting tests use authored synthetic rows only. An initial fixture compared Decimal-rendered sum strings and was corrected to compare numeric Decimal values; no scientific arithmetic rule or actual result was changed to pass it.

SOURCE_DATA_AND_LICENSE_NOTES: Registered original ANES25+source/mapping and original split for identity only; all source/target/proposal/review/extractor/model/helper hashes frozen in new config. Existing citizen source/target acquisition rights and limitations unchanged. No downloads. Reference extractor is derived from pinned original loader semantics but awaits separate independent equivalence review. No raw respondent records/row positions/identifiers/cluster details/per-record hashes exported.

COST_USD_ACTUAL_OR_ZERO: $0API/model spend;0model calls. Local compute/labor not priced.

RISKS_AND_LIMITATIONS: Real execution approval is separate from methods approval. Exact candidate/reference agreement is an engineering diagnostic, not independent evidence that the reference extraction correctly implements the original loop. The inspected holdout remains exploratory. Rounding scenarios normalize perturbed rounded input weights and cannot certify latent ACS vectors, worst-case coverage or sampling intervals. Forty-config code and gate still require independent audit. The prior unfavorable hierarchy result, suppressed fit and original adult/state/transport population-science blockers remain intact. Trusted-code gate is not an adversarial OS sandbox.

UNRESOLVED_BLOCKERS: Independent reference equivalence/scenario/coverage/leakage/identity code/fixture audit; separate correctly pinned implementation approval before real fitting/calibration. No live inference, positive budget or publication authorization.

NEXT_UNBLOCKED_TASK: Auditor reviews the stable new config/modules/tests/identity aggregate and freezes a distinct execution approval only if appropriate. Meanwhile separately approved PUMS pilot preparation may proceed on new files with synthetic fixtures and explicit predownload gates; no person GET permitted yet.


## Version1.1 prefit output and provenance amendment

Separate auditor requested canonical full2,880-cell probability-grid hashes for4PREcalibration distributions and each successful fitted configuration(null for failed), plus explicit per-model finite eight-directional-scenario raw-loss/delta ranges with all tied minimum/maximum scenario IDs, successful IDs and failed IDs. Hashing uses lexical full-grid ordering, implicit zeros and exact float.hex probabilities; pre-distribution hashes are checked again after all calibrations. New tests verify canonical order/probability-change detection, endpoint IDs/ties/failures and missing central cases. Numeric models, target/scenario rules, cohort and bootstrap are unchanged. Finite ranges are not95%intervals or worst-case/latent-ACS feasibility certificates.

The lead expanded shared RunStore code identity to cover executable scripts/. Both new configs explicitly pin common.py SHA-256566c5f3947e3048a1521d1edfa2ee6e7ade7b66502e3b4ee6ee440573eb885fa. Previous uncommitted config/evidence bytes are preserved as V1_0 snapshots; original comparison source bytes are in reports/E02_CITIZEN_COMPARISON_V1_0_IMPLEMENTATION.txt. No old run or independent audit report is rewritten or renewed. Current identity-only run e02-10f83244230e4189b223e5d32febd10e matches2,732exact records(2,286training/446heldout); reference/scenario modules unchanged. All45E02testsPASS. execution_approval remains null; real comparisonCLI/fit/calibration NOT_RUN pending separate audit of these current hashes.


## Version1.2 lifecycle amendment — durable run before model computation

Root integration review found that v1.1 computed real model outputs before creating its RunStore. Version1.2 creates the run manifest/environment/config first, records preparation events, saves safe aggregate cohort identity, target sets and scenario artifacts, and only then enters training/calibration. Training started/completed and every configuration started/completed/failed event are streamed. Each known completed or failed configuration receives an immutable aggregate checkpoint before processing continues. No respondent record, row position, cluster ID or raw per-record loss is written.

Unexpected exceptions and cancellation save aggregate progress/error type only, a failure artifact and a sealed summary explicitly marked FAILED; completed checkpoints are preserved and incomplete configuration IDs remain visible. The original exception is re-raised after the sealed RunStore context exits. Known calibration ValueErrors remain preserved failed configurations under the existing40-condition result contract. No model, score, scenario, bootstrap, reference or cohort arithmetic changed.

The new injected-later-failure fixture checks manifests/config/identity/scenarios before the first training call, then raises RuntimeError and KeyboardInterrupt separately on the second configuration. It verifies the first result/checkpoint and two start events persist, final status/failure artifacts are FAILED with checksums, no final comparison.json is fabricated, and the original exception is propagated. Known failed configuration events are also tested. All46E02testsPASS, including8comparisonfixture cases.

Previous v1.1 config/evidence/source bytes are preserved in configs/e02_citizen_comparison_v1_1.json, reports/E02_CITIZEN_COMPARISON_V1_1_FIXTURE_EVIDENCE.json and reports/E02_CITIZEN_COMPARISON_V1_1_IMPLEMENTATION.txt. All prior run/audit artifacts remain unchanged. The older prefit approval arrived before this lifecycle fix and is explicitly not applied; execution_approval stays null pending a fresh independent review of current config/code. Refreshed identity-only run e02-36557c451c134bee8e946efdf44cae11 again checks2,732exact records(2,286training/446heldout). No real compareCLI, candidate fit, calibration, personGET, paid inference or publication occurred.
