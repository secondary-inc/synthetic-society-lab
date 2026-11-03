# E01 ballot readiness v1.3 fixture handoff

TASK_ID: E01_BALLOT_READINESS_EXPANSION_V1_3_FIXTURES

FILES_CHANGED: New `src/civiclab/e01/ballot_formats_v1_3.py`, `tests/test_e01_ballot_formats_v1_3.py`, `configs/e01_ballot_readiness_v1_3.json`, versioned fixture evidence JSON, this receipt, v1.2 implementation/tests named reportTXT. Updated `src/civiclab/e01/ballots.py` solely for dispatch, separate index role, and exact reviewed hostname exception. Original v1.2 code/tests/config/evidence snapshot and byte hashes preserved before mutation. No sharedCLI/status/common/auditor/publisherpolicy changes. No modifications to old configs/evidence/runs or batch02 receipts/cache.

OUTPUT_ARTIFACTS: Frozen implementation/config/test pins in `reports/E01_BALLOT_READINESS_EXPANSION_V1_3_FIXTURES.json`. New config has14sourcepins:9previous plus5batch02. Official candidate indexes carry distinct OFFICIAL_CANDIDATE_INDEX role and cannot substitute as candidate-list refs. Candidate refs add exactly COofficialHTML, VAfederalHTML, WYgeneralPDF. Actual readiness/replay NOT_RUN until independent fixture review as required by source-role audit. No fabricated new run IDs or coverage claims.

REPRODUCTION_COMMANDS: Targeted47-test command in JSON; optional future source command after required review: `PYTHONPATH=src .venv/bin/python -m civiclab.e01.ballots configs/e01_ballot_readiness_v1_3.json --root "$PWD"`.

TESTS_RUN_AND_RESULTS:47tests pass,7new authored format/integration/hostname fixtures +40retained. CO distinguishes printed candidate flags from qualified write-ins, preserves literalunknownlabels and source inlinewithdrawalobservations without automatic exclusion. UnrelatedStateSenate strike is not inherited. VA bounds exact statewideUSSenate and omits contacts. WY requires obtained19pageedition, extracts firstpageSenate block beforeHouse, preserves printed filing/withdrawal date observations, refuses partial/missing/ambiguous rows. Exact `www.sos.state.co.us` exception only; evil.us, broad.us, subdomain, near-match anduserinfo negative guards. Synthetic integration preserves all33slots, noacceptedballots/adoption/sample. Secret metadata rejection and parser/hash/cancellation failure ledgers remain tested.

SOURCE_DATA_AND_LICENSE_NOTES: No new source fetch. Existing independently reviewed batch02 government bodies only. Raw sources/contact fields/localrosters stay ignored. Each printed party/designation is retained independently of normalization. NonD/R labels remain UNSPECIFIED; no legal recognition inference. CO currentbodyobservations6printed/3writein, VA2/WY2 were independently reviewed, but new readers have not yet executed on them. VAalloffices revision10/9 versus federal10/6 comparison remains outstanding. WYblankDateWithdrawn cell in September9edition and COabsenceofinlineSenatestrike do not establish no later amendments. Commented WYwithdrawn-general href was never requested.

COST_USD_ACTUAL_OR_ZERO:0; no model calls.

RISKS_AND_LIMITATIONS: Narrow obtained-format parsers, not universal state source support. HTML inline markup only, no CSS-rendered withdrawal assurance. WYsource observation coversSenateblock onpage1;19pagecount is an editionguard, not validation of everyotheroffice. No finalballotacceptance, no asof archive, no source-policy adoption, no outcomes/selection. Newconfiguration predicts5rosterstates and28unacquiredjobs only after successful future actual execution; these are not reported as executed counts now.

UNRESOLVED_BLOCKERS: Independent fixture/code review then actualreadiness/replay and independent sourceparse/result acceptance. Originalballot/amendment/geography/ratingsasof/selection/holdoutgates persist; missingstate sourcejobs remain unblocked/incomplete.

NEXT_UNBLOCKED_TASK: Independent auditor reviews new readers/integration under pinned hashes. After approval, execute new recorded readiness/replay, verify ledgers and observations, handoff for separate result review. Keep old inputs/runs immutable and never promote finalballots from extraction alone.
