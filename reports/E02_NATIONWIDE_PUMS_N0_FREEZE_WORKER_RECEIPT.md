# N0 nationwide candidate methods and metadata freeze

TASK_ID: E02-NATIONWIDE-PUMS-N0-METHODS-METADATA-FREEZE-v1.2.

FILES_CHANGED: Current nationwide proposal doc/JSON/check evidence only, plus this receipt. Added exact `_V1_1` snapshots of previous doc/JSON/checks, preserving `_V1_0` and metadata/actual-run evidence. No parser, source, controls, fixture, active run config, shared file or auditor edits.

OUTPUT_ARTIFACTS: `docs/E02_NATIONWIDE_PUMS_RESOURCE_METHODS_PROPOSAL.md`, `reports/E02_NATIONWIDE_PUMS_RESOURCE_METHODS_PROPOSAL.json`, `reports/E02_NATIONWIDE_PUMS_PROPOSAL_CHECKS.json`. Current JSON freezes51 exact published counts/URLFIPS identities,5 retained primary metadata hashes/URLs/dates, single51-state route, source unknowns, byte-accounting/reservation semantics and candidate universe limitations. Full prior proposal versions preserved.

REPRODUCTION_COMMANDS: Load current JSON; assert51states/FIPS equal `civiclab.e02.population.FIPS_REGION`, countsum16,095,728,5metadata source files match frozen hashes/sizes, and all source_evidence pins match. Source guide/accuracy PDFs retained at metadata paths in registry; primary same-index passages are guidePDFpages6,10–12 and accuracyPDFpages12–13. Read-only `pypdf.PdfReader` extraction used; no new network/source processing. PDF skill read for this inspection.

TESTS_RUN_AND_RESULTS: Proposal/source/count/identity consistency assertions PASS. Code/tests unchanged; last executed E02 suite56PASS from metadata stage. Byte/body reservation and future national cancellation controls are specifications only and require N1 failure/restart fixtures; no test or implementation acceptance claimed here.

SOURCE_DATA_AND_LICENSE_NOTES: Previously cached official Census metadata only. Full files rehashed against frozen identities; no person rows or unreviewed actual aggregate values accessed/exported. Primary guidance specifies matching numbered replicate estimates and general full-estimate recipe; cross-state same-release union is explicitly an application, not a claimed verbatim ZIP-compatibility guarantee. No newly fetched technical reference. Existing reviewed ANES feasibility/FAQ evidence used to preserve frame/state-validity limits.

COST_USD_ACTUAL_OR_ZERO: $0 API/model spend;0 new metadata/person requests, person rows, models or fits in this amendment. Prior authorized metadata stage remains5GETs/1,279,577bodybytes, recorded separately.

RISKS_AND_LIMITATIONS: Proposed3GiB counts application-delivered HTTP BODY, not unmeasured wire/TLS/socket/client buffering. Full-attempt writeahead reservation must survive crashes; successful unused allowance release requires durable EOF/closure/count/hash/ledger proof; failures/cancellation/unprovable attempts consume full reservation, unknown bounds block dispatch. No claim these future controls are implemented. Same-release source/partition checks remain needed. Householdcitizen18+ excludesnoncitizens/GQ and is not alladults, verifiedelectoraleligibility or validatedstatepoliticalresponse. Original adult/state goal remains unwaived.

UNRESOLVED_BLOCKERS: Independent N0 methods/metadata/resource freeze review. National controls implementation and synthetic cumulative-quota/crash/partial/transport-buffer fixtures remain unimplemented. No national/person acquisition execution approval;50newhashes/manifests remainunknown. Broader target definition, conversion/fitting, disclosure and scientific acceptance separate.

NEXT_UNBLOCKED_TASK: Lead routes exact stable proposal/checks/primary hashes to independent auditor before any national control implementation or person fetches. Preserve all completed evidence and original research contract.
