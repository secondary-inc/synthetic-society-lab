# Official E01 ballot readiness foundation v1

Worker implementation and source execution; independent review pending. Scope is official outcome-free source/contest/candidate readiness, not source-policy adoption, race selection or a forecast. This work proceeds despite the separate unverified historical-ratings gate. Existing Cook proposal, audited selector/historical code and original study acceptance criteria remain unchanged.

## What exists

`src/civiclab/e01/ballots.py` provides strict local byte/hash checks, narrowly scoped New Jersey/North Carolina document readers, a complete 33-slot class-II ledger and separate Ohio/Florida Senate plus FL-20 House context records. `configs/e01_ballot_readiness_v1.json` pins nine obtained official sources or clearly labeled government-page text representations. Every regular slot remains pending independent ballot/amendment review. Thirty-one slots have no acquired candidate roster yet; these are **unblocked source jobs**, not owner/as-of blockers or justified exclusions.

The nine sources comprise official class-II text; NJ Senate list and signed nominee certification; NC general federal/state list; Florida vacancy law; official class-III and appointment registers; and Florida Broward/Palm Beach notices. Config records exact URL, local path, bytes, SHA-256, retrieval clock, representation, publication date when known and limited HTTP headers when available. Unknown publication days remain null. HTTP response byte hashes and browser-visible-text hashes are explicitly distinct. Official source authority/interpretation and latest amendment completeness still require separate audit; passing a byte hash does not authenticate arbitrary metadata supplied by an operator.

No network collection, model calls or selector activation occurs in the module. Ad hoc public acquisitions and failed Ohio accesses are separately preserved under ignored raw-source receipt files; source/candidate data never goes into Git. Raw PDFs may contain public candidate contacts; parsers return names/party evidence only and omit addresses/contact fields. No raw respondent or publisher rating collection is redistributed.

## Source observations and remaining identity gaps

The current official class-II text has all 33 expected states and terms January3,2021–January3,2027. The reader validates its actual captured bytes and state set against the fixed roster, rather than generating regular seats from the forecaster's year field. No sample is drawn from those slots.

New Jersey's five-page official Senate list is dated July27,2026 and specifies the November3 general election. Four names are extracted with page locators. Its Democratic and Republican columns provide one observed candidate each; two petition/designation candidates retain UNSPECIFIED normalized party class instead of turning slogans into recognized party affiliations. Names and explicit party labels independently match the Senate block in the signed 20-page nominee certification. This establishes matching obtained documents, not proof no later withdrawals/amendments exist. The provisional NC list supplies four Senate names, DEM/REP/GRE/LIB codes and exact election criteria; the parser stops before the House block. The publisher's warning that lists can change is not bypassed by calling it a final ballot.

Florida statutory section100.161 is now locally obtained and hashed; it says a Senate vacancy is filled by election at the next general election with temporary appointment permitted. Current official class-III text places FL/OH in the 2023–2029 class; the official register records Florida's January21,2025 appointment. Combined with the obtained 2026 Senate notice, this **supports a vacancy/unexpired-term inference** for Florida, with exact state writ/term-specific final ballot still pending. It is not promoted to directly verified Florida special-election certification. Ohio's indexed official directive/writ supports an explicit special election, but local writ body/hash access still failed; that gap remains visible.

The downloaded Broward notice directly lists Congressional District20 at the November3 GENERAL election, in conflict with treating the forecaster's special=true as a complete regular-contest exclusion rule. Latest writ/term/candidate/amendment validation remains pending; no race is automatically dropped or relabeled. All three context IDs are outside the regular Senate quota ledger, never substitutes for its missing source rows. Relevant primary URLs and earlier scope limits are in `reports/E01_ELECTION_TYPE_EVIDENCE.md`; the newer pinned law/class/appointment sources strengthen context only, without overwriting earlier findings.

## Readers and refusal rules

Source validation requires raw-local paths, exact sizes/hashes, explicit retrieval timezone, known representation/official-document role and ordinary public official HTTPS URLs without embedded credentials/query strings (the explicitly offered NCSBE S3 directory is allowed). Finance-registration roles, unknown fields, altered bytes, outside paths and sensitive/unapproved header fields fail. Source files are read as data; HTML script/style content is excluded from visible-text fact checks.

The NJ reader requires all five pages in order, exact Senate/general/date headings, a consistent printed edition, unique names, unambiguous name/address column boundaries and matching printed candidate total. It retains literal source names and page numbers; it does not perform fuzzy name matching or infer affiliations from county repetitions/slogans. The certification block comparison ignores document order while requiring exact candidate/explicit-party agreement. Unexpected formats fail rather than silently use another state's layout.

The NC reader requires exact November3 election criteria and named columns, enters only US SENATE, and requires a terminating US HOUSE boundary. It refuses unknown party codes, duplicate or partial/wrapped rows, and incomplete blocks. It never mistakes state Senate or later House nominees for the federal Senate roster. These are source-specific narrow readers, not a claim of automatic parsing for all33 states.

The ledger requires all33 unique class-II states, fixed canonical identities/dates, and separately scoped context IDs. Missing documents remain NOT_YET_ACQUIRED. All independent ballot/amendment statuses must remain PENDING in this readiness phase; a caller cannot self-enable source adoption or certify a final ballot. Observed D/R cardinality is reported separately from legal/analysis eligibility. No outcome fields or missing-input-based exclusions can be inserted into the ledger. The current result always has zero final ballots accepted, source_adoption=false and actual_selection=false.

## Reproduce and review

```sh
python -m pip install -e '.[sources]'
PYTHONPATH=src python -m unittest tests.test_e01_ballots tests.test_e01 tests.test_isolation -v
PYTHONPATH=src python -m civiclab.e01.ballots configs/e01_ballot_readiness_v1.json --root "$PWD"
```

Core unit fixtures are authored synthetic text and mocked PDF extraction; they do not require raw sources or pypdf in CI. Actual source execution needs the pinned local files and pypdf6.10.0 source extra. Public URLs/hashes and the raw acquisition receipts allow permitted reacquisition/review; a reusable network downloader for this manifest is **not implemented**. RunStore records the admitted actual readiness run, full config/source hashes, local-only candidate roster artifact, aggregate readiness, environment, events and checksums. Admission failures raise before starting a run; no source bytes are overwritten or fake success emitted.

Nine new tests plus25 existing E01/isolation tests pass locally, including altered source hashes, registration-role refusal, incomplete/duplicate/context frame rows, date/office confusion, NJ page/printed-total/ambiguous-name safeguards, NC block/partial/party safeguards, matching-vs-disagreeing certification and contact-field omission. Actual runs `e01-fb151193502c41a59b798500987d433f` / `e01-9a614a6525234e119aa93ac92fb83898` have byte-identical readiness and local roster artifacts. These are source/readiness outputs, not voting results. `reports/E01_BALLOT_READINESS_EVIDENCE.json` contains aggregate evidence only.

Independent auditor review must confirm all9 source bytes, document labels, party/name extraction, context interpretation and stage limitations before certifying this implementation. Next unblocked work is ordinary official candidate-list/ballot acquisition for the remaining31 states, plus latest amendment/term verification for the first2 and contexts. Missing authenticated ratings cannot excuse stopping those jobs. No source policy, real selector, forecast, model budget or external publication is enabled. Actual cost: $0.
