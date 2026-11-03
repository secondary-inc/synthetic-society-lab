# Alabama standalone document reconciliation v1: metadata-only proposal

Status: PENDING INDEPENDENT METHODS REVIEW. No new source read/hash, PDF extraction/rendering, OCR, network request, candidate transcription, helper execution or coverage change is authorized or performed here. The frozen v1.9 typed-readiness candidate remains separate and unchanged.

## Purpose and existing evidence

Prepare a pure standalone reader/reconciler for the cached Alabama general-context certification documents. Its first result would be bounded document observations, never a legal or final ballot roster. The five declared PDFs total1,700,245bytes and47 physical pages. These numbers and exact source/render associations come from the accepted role-review metadata, not newly inspected bytes.

The governing role evidence is `reports/E01_AL_SOURCE_ROLE_RECONCILIATION_V1_1.json`, SHA `d41d96d792547d2e665ef35d20ec73985410e424b1bf396ac5bdb9bda762e585`, with independent bounded all47-page review `reports/INDEPENDENT_AUDIT_E01_AL_SOURCE_ROLES_V1_1.json`. The machine-readable proposal pins those records, prior evidence and all five declared source bodies/47 existing render associations. Prior scoped visual name agreement does not constitute independently audited literal transcription or parser acceptance.

Four PDFs have zero extracted characters on all34 pages; the13-page amended Republican PDF has extracted text. A text-only parser would silently miss the image-only documents. This proposal therefore separates independently reviewed local transcription from deterministic reconciliation. No automated OCR or model-based transcription is proposed. Names, office labels and transcript/audit release hashes remain null. They must not be populated from memory, party expectations or metadata placeholders.

## Bounded occurrence contract

Preserve six distinct source/page occurrences:

- Democratic state package page3: amended Senate table; pages8/9: historical July1 certification letter/table. They are historical corroboration, not extra candidates.
- Democratic party amendment page2: August24 amended table. Party context comes from the letter, not an invented party column.
- Republican state package page2: June24 party certification, received June30.
- Republican party amendment page2: August28 certification in the corrected package.

The reviewed metadata reports four Democratic occurrences agreeing on one literal and two Republican occurrences agreeing on another. This defines the expected future two document-supported groups; no actual candidate names or two-party ballot completeness is claimed now. Retain all six occurrences and their exact source/PDF page/render identities even after grouping. Identity comparison may trim/collapse whitespace for line wrapping, while preserving original literals and their UTF-8 hashes; punctuation, accents and case remain significant. A disagreement blocks instead of invoking fuzzy matching, name inference or party-only merging.

Keep the full47-page role inventory bound to the accepted audit. The independent state certificate is a one-page state-legislature document with no observed federal Senate entry; it is not proof that no independent Senate candidate exists elsewhere. Republican committee sections on pages8-13 are internal party positions. The state Republican page14 attachment concerns August20 House districts1/2/6/7. The August28 correction concerns State House51. These cannot enter federal Senate candidate groups. Historical Democratic USHouse6/StateSenate25/26 conditional-primary annotations remain outside the amended Senate observation.

## Dates and unknowns

Preserve source dates by role: state covers August26; Democratic amendment August24 and historical July1 packet; Republican June24 letter/June30 receipt, August20 House-only attachment and August28 correction. These are not candidate filing dates. Three partially unreadable Democratic received stamps at pages8/11/13 remain unknown; never guess a date from another page. November3 collection timestamps do not establish independently bound pre-results evidence or cutoff admissibility.

Every reconciled entry retains typed UNKNOWNs for final printed-ballot presence, declared write-in status, independent legal-nominee adjudication and latest-amendment completeness. A source's nomination/certification assertion is recorded in the document role without converting it into a legal conclusion. Later corrective-action reservations remain explicit. No party_class, forecasting D/R pair, vote totals, addresses or contact data are emitted.

## Proposed implementation and output boundaries

After methods acceptance, author a separate `src/civiclab/e01/alabama_documents_v1.py`, `tests/test_e01_alabama_documents_v1.py` and exact runtime contract. The reader takes a closed bounded built-in metadata snapshot before any root/source access; fixed canonical authority binds code/config/source/render/transcript/audit identities. Missing transcript or execution pins deny actual execution. A caller cannot create authority using a copied metadata receipt, new digest or enable flag.

The module is pure: no RunStore, no network, no child successes and no writes. It returns detached private occurrence/group records and an exact public diagnostic allowlist. Errors and repr are type/static-only. Names stay in ignored local `.local.json` artifacts, package-refused and unavailable through existing public paths. Public data contain source hashes, page/occurrence/group counts, roles and typed unknowns, with explicit non-adoption/non-promotion flags; they do not contain names or complete raw text. No shared CLI/dashboard/readiness/forecast consumer change is proposed.

Actual parsing of the text-available Republican amendment may provide an additional deterministic extraction agreement check after code review and source execution release. It cannot substitute for the other four documents' independently audited literal transcription or silently invent values if extraction fails. Exact geometry, encoding and parser dependencies require separate code/runtime review; this metadata proposal does not claim a tested extraction implementation.

Future bounds are five source PDFs with exact declared sizes, per-PDF1MiB ceiling,47 existing renders with8MiB per-render and376MiB total ceiling, and64KiB private transcription. Render ceilings are proposed limits, not measured file sizes. Oversized or changed inputs refuse; limits cannot silently relax. This stage proposes zero new rendering/OCR/GET/model calls.

## Gates and acceptance criteria

1. Independent review accepts or rejects this methods proposal.
2. Separate authored implementation/runtime candidate passes source-binding, no-write, schema, alias/coedit, path/size/import, disagreement, historical-role, privacy and cancellation fixtures under Python3.11/3.12. Independent code/privacy review follows.
3. Lead explicitly releases bounded cached-source/render access and local transcription. No actual bytes may be read under this proposal alone. Independent literal transcription review pins source/page/render/name/office/role/date identities in ignored private artifacts; no contacts are collected. No transcript exists yet.
4. A separately reviewed exact runtime amendment binds those transcript and independent-audit hashes. Missing or unreviewed pins continue to deny actual reader execution.
5. Only a subsequent authorized recorded standalone preflight and replay, with independent actual-source/result/privacy review, can accept document extraction. Its recording wrapper must separately test durable failure/cancel/partial-write retention.
6. Readiness integration remains another methods/code/execution/post-run gate. No coverage promotion, final/legal ballot, latest-amendment, geography, source-policy, selection or forecasting authority follows from a standalone result.

The machine-readable proposal lists concrete negative fixtures: source/transcript coedits with unchanged authority; each historical/committee/House role intrusion; date/receipt/cutoff confusion; distinct-group inflation; literal disagreement; missing/duplicate pages; booleans replacing unknowns; private/public leakage; unfilled authority pins; and parse/cancel/SystemExit behavior. These are requirements, not tests already executed.

## Current result and limits

Only metadata structural/pin checks were performed; see `reports/E01_AL_STANDALONE_METHODS_V1_PROPOSAL_CHECKS.json`. Raw PDF/render/private-reference I/O, helpers, parser tests, actual extraction and readiness remain NOT_RUN. Accepted coverage stays **12 document states / 21 unfinished jobs / zero final ballots**. Experimental spend and new network/model/OCR calls are zero. Source availability in official cached records does not itself grant redistribution rights; raw documents/renders/names stay local and unbundled. No publisher WIP, prior evidence, v1.9 candidate or lead status was edited.
