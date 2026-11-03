# Alabama standalone methods proposal v1 handoff

TASK_ID: E01_AL_STANDALONE_TRANSCRIPTION_RECONCILIATION_V1_METHODS

FILES_CHANGED: Three new proposal/doc/check records below, plus this receipt. No implementation, prior evidence, frozen v1.9 file, publisher WIP, shared CLI/dashboard/status or Git commit edited.

OUTPUT_ARTIFACTS: Metadata-only proposed standalone source/transcription/reconciliation contract. SHA-256:

- `configs/e01_al_standalone_methods_v1_proposal.json`: `4466cf45e96c778e44cd846fac53d3996e0fc60ee7dc09d951b61a29a97dd891`
- `docs/E01_AL_STANDALONE_METHODS_V1_PROPOSAL.md`: `12cc3259ef043698ada7a9fb1fc2c7ef2a8eb6abcad9ead8e799f91036d33b28`
- `reports/E01_AL_STANDALONE_METHODS_V1_PROPOSAL_CHECKS.json`: `d725349c9a045bbaab0745d1c3706650a44caee96d6be0266c3fd943371b1274`

REPRODUCTION_COMMANDS: `python3 -m json.tool configs/e01_al_standalone_methods_v1_proposal.json > /dev/null` and the equivalent command for `reports/E01_AL_STANDALONE_METHODS_V1_PROPOSAL_CHECKS.json`. Recompute the listed SHA-256 values with the standard library or `shasum -a 256`. The checks JSON identifies all13 executed metadata-only assertions and seven unchanged frozen v1.9 pins; no parser-test command exists because implementation is not yet authorized by methods acceptance.

TESTS_RUN_AND_RESULTS: 13 metadata structural/pin assertions passed: reference pins,5 unique source IDs/paths,47 unique/complete source-page associations,6 exact reviewed Senate slots,2 historical occurrences,4 image-only PDFs/34 pages, null names/office labels/authority, declared1,700,245byte sum, zero actual-activity flags,4typed unknowns and7 frozen v1.9 pins unchanged. JSON syntax checks passed. Source/parser/code/runtime tests NOT_RUN; independent methods review NOT_RUN.

SOURCE_DATA_AND_LICENSE_NOTES: Used only accepted public role/audit metadata. Five PDFs/47 cached-render hashes and dates are declarations from that evidence, not new body integrity checks. Four documents are image-only under the recorded extractor;13-page amended Republican PDF has text. Proposed six source/page occurrences remain separate: amended D2locations, historical D8/9, stateR2 and amendedR2; future two document-supported groups do not certify a complete ballot or distinct real persons. Names and transcript/audit hashes remain null. Raw bytes/renders/private names stay local and unbundled; no new rights or publication authority inferred.

COST_USD_ACTUAL_OR_ZERO: $0 experimental model/API spend; zero raw source/render/private reference body I/O, helper, GET, render, OCR or model calls. Development compute/labor unpriced.

RISKS_AND_LIMITATIONS: Manual source-bound literal transcription is still needed for image-only documents and requires separate authorization plus independent audit. Metadata alone cannot populate names/office labels. Preserve historical-vs-amended roles, source/asserted dates, partial receipt stamps and four legal/final/writein/latest unknowns. House-only amendments, party committees, conditional historical non-Senate rows and independent state-office entries cannot become federal Senate candidates. Same-host hashes are bindings, not owner authority or external timing proof.

UNRESOLVED_BLOCKERS: Independent methods review, then separate authored code/fixtures and independent code/privacy review; explicit lead release for cached-source/render/transcription work; independent literal transcription audit and exact runtime amendment; later actual preflight/replay/post-run review. Readiness integration and legal/final/latest/geography/source-policy/selection remain separately gated. Accepted12states/21unfinishedjobs/0finalballots unchanged.

NEXT_UNBLOCKED_TASK: Independent reviewer assesses this metadata-only proposal. If methods accepted, prepare separate authored pure-reader/runtime/fixture candidate; do not read cached PDFs/renders or execute actual helpers yet. Hold v1.9 candidate unchanged for its active independent review.
