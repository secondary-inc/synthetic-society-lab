# Clerk historical input methods v1 — proposal only

This proposal prepares original E01's2026 retrospective S0 work, prioritizing2020 same-seat Senate inputs. It does not inspect either PDF, authorize parsing or adopt features/candidates/ballots. The companion `configs/e01_clerk_2020_senate_input_methods_v1.json` records exact sources, schemas, event rules, fixture requirements, dependencies and null authority fields. No parser, real sample, candidate/contest count or numerical result is asserted.

The original contract remains24 House plus up to8 Senate broad races and4 House/2 Senate deep races. We do not replace it with the separately accepted2018→2024 Class-I post-hoc diagnostic, a convenient2020 subset, or a Senate-only deliverable. E03/E04 and paid inference remain gated; S0 needs neither agents nor publishers.

## Source knowledge and its limits

The two Clerk PDFs have exact byte/provenance acceptance in `reports/INDEPENDENT_AUDIT_E01_CLERK_DOCUMENT_CAPTURE_V1_ACTUAL.json`, SHA2b0e3af466645773ca00b11590d871533ee7b2d80abec27abb9b2e77cd5c3a75:

- `clerk2020_statistics`,602172bytes, SHA666b2a1f673f263087c141c4d44b0dce47cbddc8f4df27fbc8b415cf05842b76, captured from `https://clerk.house.gov/member_info/electionInfo/2020/statistics2020.pdf`. Its role is historical2020 official counts, never2026 outcomes.
- `clerk2026_nominees`,257739bytes, SHAcb2e4194c88042cf22f8589fb6b8c352d29b501f96abc62a962b6cc52e2c28a8, captured from `https://clerk.house.gov/member_info/electionInfo/2026/120-nominations.pdf`. Its role is a dated official nominee compilation, not target returns or proof of final ballots/latest amendments.

The existing exploratory public cover report records81 and38 physical pages, zero candidate/vote records parsed and no layout validation. It does not contain the literal publication-date strings. The lead reports February26,2021 and October8,2026 from cover observations; the latter date is also in the public capture-discovery note. These dates are retained with that attribution, not promoted to independently source-spanned facts. Later inspection must bind each printed date to its actual cover text/span. We have not opened the private extracted covers. HTTP Last-Modified observations (March9,2021 and October13,2026) and November3,2026 collection times are distinct transport/acquisition evidence, not substitutes for publication, election date, certification, latest edition or pre-cutoff authenticity.

Neither byte acceptance nor a cover page establishes full body validity, Senate page ranges, state/event coverage, row/column grammar, candidate totals, numerical accuracy or class/regular/special/round interpretation. Actual parsed record/contest/eligible-feature counts remain null. All119 physical pages need a role inventory under a later finite inspection release; no body ranges or table boundaries are guessed here. Unknown pages/headers/columns/footnotes stay UNKNOWN. No2026 results source was requested or used.

## Existing protocol and the feature boundary

`protocols/E01_RETROSPECTIVE.md`, `protocols/E01_FEED_TO_BALLOT.md` and the original selection proposal remain authoritative. S0 is a transparent conditional two-party margin:

`prior_margin_pp = 100 * (D - R) / (D + R)`

`predicted_margin_pp = clamp(prior_margin_pp + 0 + 0, -100, 100)`

D and R are verified total votes for exactly one named Democratic-affiliated and one named Republican-affiliated candidate in the chosen regular general event. Other candidates and their votes remain recorded outside this denominator; their votes are not redistributed and their winning is not a reason to change the sample. This is not win probability or a turnout/persuasion model. National and incumbency adjustments stay zero; changing them requires separately reviewed outcome-independent methods.

A2026 Senate prior must be the same state/constitutional seat class six years earlier, hence2020. A2026 House prior must be2024 on validated2026 geography, with exact reaggregation if boundaries changed.2020 House totals cannot fill that two-year requirement. Different Senate classes,2022/2024 Senate votes, or matching candidate surnames cannot replace a missing2020 same-seat prior.

The existing predictor accepts exactly eight fields: `race_id`, `office`, `prior_margin_pp`, `national_shift_pp`, `incumbency_adjustment_pp`, `feature_as_of`, `cutoff`, `source_hashes`. Rich historical row/count/party/seat/source-span lineage belongs in a separate private sidecar, never extra worker feature fields. Current generic `freeze_predictions` rejects REAL inputs. Frozen `historical.prepare` only accepts its2018→2024 Class-I diagnostic. A future separately reviewed REAL adapter is required; neither gate is weakened by this document.

## Proposed observation and provenance schemas

All schemas are closed versioned record contracts, not populated examples. The configuration lists exact field sets. Raw text/names/rows remain local and unbundled; only safe hash/count/error/method metadata may enter public reports.

A source span binds source ID/hash, physical1-based PDF page, separately preserved printed-page label, extraction backend/version, declared text coordinate system and exact text-span hash. Offsets must refer to the saved backend's exact extracted UTF-8 stream. If a later separately authorized visual check supplies a bounding box, record its coordinate convention; never invent bbox precision from plain text. Unavailable offsets/labels/boxes use typed UNKNOWN. Text extraction bytes are not the original PDF's text encoding. Field-role/context links identify the specific header, candidate row, party line, vote cell, unit/mode, stage and footnote spans supporting each value.

The immutable historical raw occurrence retains source-spanned literal office/state/contest/date/stage/special-term/candidate/party/vote/unit/mode tokens and footnotes, plus its canonical record hash. No parser rewrites a raw record to make a match pass. A separate normalized annotation references that raw identity/hash and exact reviewed rule/adjudication evidence. It carries state, office, seat class, term, cycle year, actual event year/date, stage, special status, unit/mode, record role, candidate identity, party-line identity, party family and votes. Each is a known supported value or typed UNKNOWN; no absent fact becomes an empty string, false flag or zero. Historical regularity/class/party/votes must be independently admitted before setting a manifest `verified` flag.

Votes are exact integers parsed under a reviewed source-specific grammar; no boolean, float, nonfinite, negative, fractional or lossy rounded counts. Preserve thousands separators/whitespace/footnote markers as raw text and admit only the independently observed supported form. Blank, dash, unopposed and redaction tokens remain UNKNOWN unless the source explicitly supplies a reviewed meaning. A clear literal one vote is not automatically a sentinel; nor is a source-ambiguous one accepted by assuming another dataset's semantics. Check integer aggregation against an independent arithmetic oracle; do not round component votes or margins before aggregation.

The separate2026 nominee observation has its own discriminator and source/date/office/state/district-or-seat/candidate/party/footnote spans. It has no vote, outcome, winner, margin or historical-feature fields. Numeric-looking districts/page/footnote values cannot become votes. Its unknown final-ballot/legal-nominee/latest-amendment/independent-cutoff statuses remain separate. A dated federal list can guide a candidate-source job; it cannot automatically certify all state amendments, final ballot printing, regular/special term or target constituency.

## Event, class and state rules

A contest key includes state, office, independently verified seat class, term context, actual event date, stage and regular/special status. Raw source occurrence identity remains source/page/row-span based until these facts are resolved. Never join Senate rows by state/year alone. A cycle label does not overwrite actual event year or date.

Use current official Class-II reference metadata only as a possible2026 identity anchor. Its underlying raw text was not reopened here, and a2026 list alone does not prove2020 term or regular/special classification. Source-bound2020 and2026 event/term evidence must link to one accepted canonical statewide constituency manifest before emitting prior/target geography fields. Do not copy a geography hash/vintage between years merely to satisfy `validate_pair`. House keeps its separate exact-reaggregation gate; CD120 assignments or repeated district labels do not complete it.

Special contests are retained with their own class/term/event evidence and stay outside current S0. Unknown regularity is pending evidence, not automatic exclusion or `special=false`. A same-year special may share a state with a regular contest; no assumption about class can be made from candidate, incumbent or winner identity.

Runoffs retain their own actual dates, event years and stage. An event in a later calendar year cannot be relabeled as a2020 GEN just because it belongs to a2020 cycle. Do not pool rounds or silently substitute a final-runoff margin for the selected general stage. Current S0 refuses RUNOFF; using it requires a separate protocol amendment. A verified2020 regular GEN with exactly one named D/R can supply a conditional general-stage margin even if a later runoff exists; that margin does not claim to represent the final winner. This is a proposed explicit application of the existing GEN-only rule for methods review, not a finding about either PDF.

Georgia is an explicit ambiguity gate: resolve simultaneous seat/term contexts, regular versus special, and November versus later rounds separately using headers/footnotes/official crosschecks. We make no actual GA participant, vote, class or row count claim. Louisiana likewise requires the source-defined stage and all named participants. If a prior event contains multiple named Democrats or Republicans, current S0 cannot collapse them into a single pretend nominee or choose the winner. Preserve all records and mark the prior feature unsupported. Actual LA stage and candidate structure are uninspected.

Fusion requires reviewed identity mapping from each separately observed party line to the same named candidate. Preserve literal party text and disjoint counts. If a combined candidate total and component lines both appear, choose the source-supported complete representation once and use the other as a crosscheck; never add them together. Duplicate candidate/line/unit/mode keys or uncertain completeness block the feature. Affiliate-to-major-party rules and exact aliases need versioned source evidence. Do not borrow the old diagnostic's surname/fuzzy/diacritic-stripping match as new admission authority.

Classify detail rows, combined candidate totals, party totals, statewide totals, substate units, mode components, summaries and footnotes separately. Never add statewide TOTAL to county/precinct/component/mode totals, or mix President/House figures into Senate. Global page/header state cannot spill across a new office/event/table. Conflicting official counts require immutable observed values plus a separately reviewed correction; do not silently prefer a value because it improves a2026 forecast.

## Selection, missingness and leakage

Freeze original target selection independently of prior-input availability and2026 returns/errors.2020 missing/ambiguous/unsupported party structure affects whether S0 can run for an already selected race; it does not remove the race from the target frame, reroll selection or nominate a replacement. In particular, incomplete2020 data cannot quietly shrink the24House/up-to8Senate contract. A successful availability-subset comparison, if separately prespecified as secondary, must show every failed ID/reason and recompute simpler methods on exactly that same subset. It cannot claim the full original comparison.

Preserve prediction inputs and2026 outcomes as separate roles, artifacts and processes.2020 statistics may enter historical predictors; the2026 nominee compilation may enter independently reviewed target candidate lineage; neither source supplies2026 target returns. The predictor child receives only the existing allowlist, with current trusted-worker external-I/O guards retained. Source/manifest/feature decisions are frozen before the separate outcome custodian loads certified2026 evaluation counts. Do not use source-derived target outcomes, live returns, raw PDFs, arbitrary paths, keys or unapproved extra fields in predictor stdin.

Record printed publication, event date, source version, source availability evidence, retrieval, actual artifact creation, feature-as-of and historical cutoff separately. A source published after2020 can be a known historical prior for2026; a November3,2026 download does not prove an independently bound earlier snapshot. Unknown as-of eligibility blocks that use. Never autoassign cutoff to an unsupported feature date or backdate artifact creation. This remains retrospective even with deterministic freezes or process isolation; operator knowledge and model training contamination are not erased.

Compare advanced methods only against simpler methods on the same race IDs, outcome version, cutoffs, weights and allowable evidence. Keep office-specific macro MAE and paired differences; do not invent probabilities or IID confidence from a small correlated sample. Agents/news/social/assistants require their separate earned-complexity gates; interaction additionally needs equal-compute independent controls. None is required to finish the statistical baseline first.

## Earned implementation and source gates

1. **M0 methods:** independent reviewer accepts/revises this exact source-role, event, missingness, schema and lineage proposal. Status NOT_RUN; no source authority follows.
2. **M1 authored contracts first:** implement pure closed schemas/normalization/feature contracts and a finite inspection harness against fictional tokens only. F01–F16 in the config require independent numerical oracles, event/class/runoff/GA/LA/fusion/uncontested/total/unit/grammar/continuation/schema/privacy/leakage/bounds/cancel/failure/matched-set cases on Python3.11/3.12 and independent code review. Anticipated fictional layouts are not evidence of actual PDF grammar.
3. **M2 source inspection:** only after a fresh bounded source-inspection release, inventory all81+38 pages and full-body role/layout/date/stage/footnote/text completeness. Any needed rendering/visual inspection needs its own explicit bound; no automatic OCR or alternate-parser retry. Unknown formats stay blocked. Independent source-format review follows; no statistical projection or baseline yet.
4. **M3 source-format implementation:** implement separately versioned parsers/rules for observed formats, repeat authored adversarial/source-role fixtures and obtain independent new code/privacy/bounds acceptance. Actual parsing is not authorized by fixture success.
5. **M4 actual parser and source output:** a fresh exact cached-source/code/parser/config/limits/phase release precedes recorded parse/replay. Preserve raw literals/annotations/input/code hashes/backend/version/run IDs/error/exclusions and partial failures. Independent original-output count/span/arithmetic/completeness review is required.
6. **M5 feature admission:** independently adjudicate each proposed historical candidate/party/fusion/vote/unit/stage/class/term/as-of feature and its target candidate/geography link. Missing data stays blocked; original complete ratings/selection/geography/outcome-custody gates remain.
7. **M6 baseline:** separately reviewed REAL integration and finite release, frozen selected features/predictions before2026 outcome access, recorded retrospective run/replay, independent leakage/evaluation/provenance/limitations acceptance. Full original sample and matched comparison remain required; the old diagnostic cannot self-authorize this route.

No parser, sample, candidate/contest coverage, feature, prediction or evaluation result has been created by these methods. Capture/page-count evidence does not fill those gates. Full body grammar,2020 event/class/party/fusion/count roles,2026 target candidates/amendments/final ballots, ratings/as-of selection frame,2024 House geography, target outcome custody and REAL integration remain unresolved. Every milestone keeps explicit BLOCKED/NOT_RUN state until separate evidence exists. Failure/error logs must preserve types and configurations without names; no silent imputation, source guessing, looped retries, parser fallback, revised source boundary or post-result repair.

This task read public repository metadata/code only: no PDF/private cover/raw/history/person source stat/hash/open/view, helper/parser/source call, network/credential/model access or API spending. Raw rows/names/source text remain local; source access and publication/reuse rights are not broadened. Current13typed/20unfinished/12legacy/final0 remain unchanged.

## Worker handoff

TASK_ID: E01_CLERK_2020_SENATE_INPUT_METHODS_v1

FILES_CHANGED:
- docs/E01_CLERK_2020_SENATE_INPUT_METHODS_v1.md
- configs/e01_clerk_2020_senate_input_methods_v1.json
- No accepted protocol/code/config, source/capture/cover, publisher, Alabama integration, status or history file edited.

OUTPUT_ARTIFACTS:
- Methods proposal and machine-readable closed contracts/fixture plan/gates; config SHAab53c24e13f27327b623f7f0ef622de046c3308f3e139418b3b79b73563bade0. No parser/records/features/predictions/results created.

REPRODUCTION_COMMANDS:
- Use Python standard-library json/hashlib/ast to inspect the two proposals and referenced public metadata/code only. Do not open any `data/` path from the source declarations.
- Verify refs with SHA256; compare source metadata to accepted capture handoff and81/38page counts to public cover report. AST-extract pipeline.FEATURE_FIELDS to compare exact8feature keys. Confirm all approval fields false/null,16 authored fixture requirements and7 explicit gates.
- Actual source inspections/parser/tests/runs require later separately assigned gates; this document grants none.

TESTS_RUN_AND_RESULTS:
- Static public-only metadata checks observed matching accepted2b0e3acapture/2exactsourcehash-size-path-URL refs/81and38page counts; exact8existingfeature keys; unique closed schema fields;16proposedfixture cases/7milestones;6yearSenate/2yearHouse and24House/up8Senate/4+2deep scope.
- Referenced public protocol/config/code bytes unchanged after drafting. No parser/helper imports or calls, fixture tests, source-format inspections or baseline runs performed. Source grammar/candidate counts remain unverified/null, not passing test claims.

SOURCE_DATA_AND_LICENSE_NOTES:
- Public repo metadata/code only. No PDF/private cover/raw/history/person source stat/hash/open/view; no source/helper/parser call or source acquisition.
- Historical2020counts and dated2026nominee compilation have distinct roles. Lead-reported publication dates are attributed and require literal source spans; LastModified/collection/printed/publication/event dates stay separate.
- No raw names/text/votes reported; source reuse/publication rights unchanged.

COST_USD_ACTUAL_OR_ZERO:
- $0API spend; zeroGET/model/key/network calls. Development compute unpriced.

RISKS_AND_LIMITATIONS:
- Methods proposal only, awaiting independent review. No actual full-body layout, candidate/contest count, historical feature, verified class/term/fusion/stage record or source completeness is claimed.
- Missing prior evidence blocks selected-race execution, never changes selection or replaces a race. GA/LA rules are proposed evidence/eligibility procedures, not inspected facts. Specials/runoffs/multiple-major-party participants are preserved separately and remain unsupported by currentS0 as specified.
- Existing2018→2024diagnostic remains frozen and distinct; genericREAL2026 execution remains denied. No2026returns or scientific/prospective/coverage/finalballot claims.

UNRESOLVED_BLOCKERS:
- Independent methods review; authored contract/finite inspection fixture implementation; finite full-body inspection and source-format review; exact parser implementation/code review; actual parser runs/independent output and arithmetic review;2020class/term/party/fusion/count/asof evidence; original2026selection/targetcandidates/geography/2024Houseinputs/outcome custody/REALintegration.

NEXT_UNBLOCKED_TASK:
- Independent reviewer accepts/revises exact two-file methods proposal. Then implement/test pure authored contracts and bounded inspection harness before asking for any new raw-source inspection. Preserve all original gates and explicit missing-input states.
