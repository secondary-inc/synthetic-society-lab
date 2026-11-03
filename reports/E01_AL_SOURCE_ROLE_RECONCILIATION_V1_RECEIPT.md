# Alabama cached source-role reconciliation v1

Worker evidence only; independent review pending. This report does not change accepted document coverage, final ballots, candidate manifests or source policy.

The five cached documents contain 47 physical pages. Thirteen selected pages were rendered locally and manually inspected; 34 pages remain unread. All five original PDF hashes/byte sizes match the original batch04 HTTP receipt. The companion JSON records every original source hash, exact physical-page locator, derived PNG hash and unread range. PNG hashes identify local derived images, not original PDF page bytes.

The Democratic and Republican state covers are dated August 26 and explicitly concern the November 3 general election. Democratic state-package page 2 and separate party-amendment page 1 are dated/received August 24, amend the July 1 filing, describe Special Primary/withdrawal changes and reserve later corrective action. The single United States Senator entry on state-package page 3 visually agrees with party-amendment page 2; names remain local and are not reproduced here.

Republican state-package page 2 contains a June 24 party letter, received June 30, with an explicit November 3 ballot statement. Separate party-amendment page 1 is dated August 28 and describes correction of an omitted State House District 51 entry; page 2 contains the updated general-ballot statement. The single U.S. Senate entry agrees visually across the reviewed June/August pages. This does not establish an exhaustive unchanged-office inventory. A state-hosted party amendment remains distinct from the signed state certificate; August 28 postdates the August 26 state cover.

The complete one-page independent state certificate, dated August 26, lists six state-legislative entries: State Senate districts 10 and 21; State House district 7 twice, 35 and 65. It contains no U.S. Senate office. This bounded observation does not establish the absence of other or later independent nominations. No external Dropbox reference was followed; no election returns were acquired or used.

## Worker task contract

- TASK_ID: E01_AL_SOURCE_ROLE_RECONCILIATION_V1.
- FILES_CHANGED: Only this receipt and `reports/E01_AL_SOURCE_ROLE_RECONCILIATION_V1.json`. Local renders/source receipt and preparation diagnostics remain ignored under `data/raw/e01_alabama_role_reconciliation_v1/`.
- OUTPUT_ARTIFACTS: Companion evidence JSON; its SHA256 is recorded in the stable handoff. No raw images/PDFs or named roster exported.
- REPRODUCTION_COMMANDS: Verify PDF SHA256/bytes against `data/raw/e01_ballots_batch04_v1/http_receipt.json`; use pypdf page counts and stripped extracted-text lengths; locally render physical pages 1-3 of each multipage file and sole independent page using `pdftoppm -f 1 -l 3 -scale-to 1500 -png INPUT PREFIX`; inspect exact page roles in JSON. Renderer-dependent PNG bytes need not match across tool versions. The local preparation script is not a shipped reproducibility pipeline.
- TESTS_RUN_AND_RESULTS: Five source hashes/byte sizes and 47 page-count/stripped-text-length observations rechecked; 13 render hashes recorded and corresponding pages manually read. Initial verification used unstripped text lengths and failed for the text-bearing Republican amendment; diagnostic script retained locally, then corrected to the original receipt's stripped-text definition. No application tests needed because no application code changed; no scientific or milestone PASS self-issued.
- SOURCE_DATA_AND_LICENSE_NOTES: Previously captured official Alabama SOS links only. Acquisition timestamps/URLs/body hashes remain in original receipt and companion evidence. Official hosting does not establish permission to redistribute raw documents; raw PDFs/renders remain ignored. Candidate/contact/address literals omitted from report.
- COST_USD_ACTUAL_OR_ZERO: $0; zero new network requests, model calls or external OCR calls.
- RISKS_AND_LIMITATIONS: Manual role/date/office review of selected pages only, not independently validated candidate extraction. Original document dates and retrieval dates do not establish immutable pre-cutoff provenance or latest-ballot validity. No representation, final-ballot or geography claim.
- UNRESOLVED_BLOCKERS: Independent review of these observations; remaining 34 pages; versioned extraction/transcription and independent literal-office/name checks; later amendments, withdrawals/write-ins and legal completeness.
- NEXT_UNBLOCKED_TASK: Separately versioned DE/NE v1.7 readiness integration following the independent geometry-runtime acceptance. Alabama remains outside readiness integration.
