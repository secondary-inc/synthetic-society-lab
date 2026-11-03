# Single Wyoming acquisition worker contract

TASK_ID: E02-PUMS-WY-v1.2-ONE-APPROVED-ACQUISITION.

FILES_CHANGED: ONLY excluded predownload_approval field pinned in `configs/e02_pums_wy_pilot_v1.json`; new failure evidence/receipt and separate docs-only local-reuse proposal. No downloader, source/math controls or review records changed. No reviewed limits relaxed.

OUTPUT_ARTIFACTS: Sealed FAILED acquisition run `e02-70827a2bc8ef49b0bd5f808a00064f74`(6checksum entries verified), ignored attempt `wy-05da99bbf77c454e9e616b4ba624fa61` with pre-network manifest/control config/states/FAILEDfailure+summary, and exact4,202,266byte quarantined ZIP SHAe80900d6826c8fef4c6f7230f3c967457aa86f06e750f050d8cf406888d19b73. Safe tracked evidence is `reports/E02_PUMS_WY_PILOT_ACQUISITION_FAILURE.json`. No canonical archive/receipt, full aggregate, replay, target or fitted population was promoted/created.

REPRODUCTION_COMMANDS: The one approved GET is consumed; DO NOTrepeat acquisition. Local read-only verification of quarantine SHA/member directory/CSVheader is permitted for diagnosis. Any local full validation/aggregate reuse requires a separate independently accepted amendment, proposed in `docs/E02_PUMS_WY_LOCAL_REUSE_AMENDMENT.md`.

TESTS_RUN_AND_RESULTS:47E02tests passed before acquisition and current independent v1.2predownload approval was verified byte-for-byte and against the frozen design/required files. The one actual request returned HTTP200 and completed its byte transfer, then validation correctly rejected the companion PDF outside the exact optional-member allowlist. Attempt metadata proves1network_request_started, no retry/fallback, validation_started then quarantine+FAILED. All6run checksum entries verify; quarantine hash matches the attempted download. Header-only diagnosis confirms all91required fields among285columns with0duplicates; no actual person-row/count/aggregate validation was completed.

SOURCE_DATA_AND_LICENSE_NOTES: Exact approved official Wyoming2020–2024ACSfive-year personZIP URL. Fresh approval SHAe8fe5ad5e14885294692c3e4de8745a9b8700a21dd8c89800d5e8f09f63f985a pinned only after source/design guards passed. Raw ZIP and attempt remain local ignored. Safe diagnosis only reported member names/declared sizes and CSVheader metadata; no individual row, identifier, low-support aggregate or error body exported.

COST_USD_ACTUAL_OR_ZERO: $0API/model spend;0modelcalls; exactly1approved public person-file request and4,202,266downloaded bytes;0retries/alternate requests. Local compute/storage/network/labor not priced.

RISKS_AND_LIMITATIONS: Source access succeeded. Blocker is the reviewed container policy: actualZIPcontains psam_p56.csv plus ACS2020_2024_PUMS_README.pdf99,489bytes, while optional policy allows only readme.txt<=16,384bytes. Thus this is completed byte fetch followed by validation failure, not absent source access or proven bad person data. Declared expansion sizes and header checks do not establish row integrity, count29,297, aggregate validity or confidentiality clearance. No national/state-population or human-response result is claimed.

UNRESOLVED_BLOCKERS: Independent narrow literal-companion/exact-byte policy amendment before local validation/reuse; independent raw source/member/header/count/aggregate/uncertainty/replay audit before scaling or fitting; original scientific/disclosure/transport gates remain BLOCKED. The consumed network approval cannot be reused for anotherGET.

NEXT_UNBLOCKED_TASK: Auditor reviews safe failure metadata and the docs-only local-byte-reuse proposal. If separately approved, implement/freeze narrowly bounded companion handling and local-only validation fixtures, then revalidate the exact existing quarantined bytes without network. Preserve original FAILED history permanently.
