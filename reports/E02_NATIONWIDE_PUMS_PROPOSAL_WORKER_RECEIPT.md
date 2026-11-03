# Nationwide adult/state PUMS proposal worker contract

TASK_ID: E02-NATIONWIDE-ADULT-STATE-PUMS-RESOURCE-METHODS-PROPOSAL-v1.

FILES_CHANGED: New owned proposal doc, JSON registry/resource specification, local consistency-check evidence and this receipt. No source code, shared files, active pilot configs, previous runs or auditor findings changed for this proposal.

OUTPUT_ARTIFACTS: `docs/E02_NATIONWIDE_PUMS_RESOURCE_METHODS_PROPOSAL.md`, `reports/E02_NATIONWIDE_PUMS_RESOURCE_METHODS_PROPOSAL.json`, `reports/E02_NATIONWIDE_PUMS_PROPOSAL_CHECKS.json` and this receipt. Alternative national-four-part versus preferred51-state/DC routes evaluated from existing recorded metadata and measured Wyoming evidence. Preferred route would reuse Wyoming once and request50otherarchives under a new approval; no route currently authorized.

REPRODUCTION_COMMANDS: Parse proposal JSON and check its51stateFIPS equals `civiclab.e02.population.FIPS_REGION`, URLs unique and PR excluded; sum four recorded national part counts to16,095,728; validate source_evidence file SHA256 pins; verify50newhashes and49unretainedstatecounts remain null. Exact numerical calculations/limits are saved in JSON. `PYTHONPATH=src .venv/bin/python` is the runtime used. No person data need be accessed for these checks.

TESTS_RUN_AND_RESULTS: Local proposal consistency checks PASS, recorded separately as worker evidence, not independent acceptance. Counts/registry/units/known-versus-unknown source fields checked. No new implementation or actual acquisition run exists, and no engineering/scientific milestone is self-certified.

SOURCE_DATA_AND_LICENSE_NOTES: Existing official public2020–2024ACS PUMS metadata receipts plus Wyoming recorded execution and independent actual-source audit used. Exact original metadata bytes were not retained; future bounded official refresh/retention/countmanifest review is explicitly required. No new metadata/person fetch. Raw respondents and actual aggregate cell/replicate values excluded from proposal and reports. Full existing aggregates stay ignored local pending separate disclosure review. Public access does not imply a redistribution or reidentification approval.

COST_USD_ACTUAL_OR_ZERO: $0 API/model spend; zero new network requests, person processing, fits or inference. Proposed network/time/storage envelopes are future limits, not incurred costs or authority.

RISKS_AND_LIMITATIONS: Linear extrapolation from29,297-row Wyoming pilot is illustrative, not guaranteed national throughput/RSS. Display labels are rounded and units interpreted explicitly. Literal newcontainers/hashes and49statecounts unknown. Cooperative/monitored quotas can overshoot; controls need implementation and failure tests. PUMS period, sampling/disclosure/coverage and ANES transport limitations persist. Demographics cannot establish state political associations or human-response validity.

UNRESOLVED_BLOCKERS: Independent proposal/methods/resource review, bounded metadata freeze, route/container enrollment controls, independently reviewed national parser/quotas/checkpoints/resume implementation before acquisition. Separate actual national arithmetic, disclosure, adult/state fitting, matched held-out evaluation and publication gates remain blocked. Wyoming pilot approval cannot authorize scaling.

NEXT_UNBLOCKED_TASK: Lead routes stable proposal/checks to separate auditor; proceed only to the bounded metadata/implementation scope it accepts. Preserve consumed v1.1 actual runs, original negative population findings and test-only v1.2 review history.
