# Proposed Inside Elections source/method amendment

DRAFT, NOT ADOPTED. New retrospective proposal, November 3, 2026. Identifier proposed for review: `E01_2026_INSIDE_ELECTIONS_SELECTION_PROPOSAL_v1`. Preserve the original Cook proposal and its reviewed hash. This document changes no selector, config, protocol, accepted frame or actual sample. Independent source and methods review must approve a separately versioned adoption before implementation; the fixture selector's strict REAL denial remains unchanged.

## Source and access scope

Propose the exact public House/Senate exports captured in `configs/e01_inside_elections_acquisition.json`, with their original text, metadata and labels retained locally. The ordinary pages offered these API links; operational audit authorizes bounded internal reading/caching without requiring a blanket redistribution license. It does not authorize publishing the full publisher collection, subscriber archives, unrestricted API crawling or outreach. No additional owner permission is needed for routine internal review already within that scope. External publication/reuse scope is reviewed separately.

The observed captures have 435 unique House district IDs and 100 unique Senate state/class keys. House IDs match the already registered official CD120 district universe; all 33 class-II Senate states match the current official Senate class-II list. These checks do not establish eligible final ballots, accepted stage classifications or independent historical provenance. Retain the full acquired collection and all context rows; a row is not discarded merely because it complicates quotas.

## Explicit category and sampling-party mapping proposed

Preserve `source_rating_text` and `source_rating_numeric` as supplied. Normalize only by this exhaustive text rule, never by invented numeric thresholds:

- Solid Democrat/Republican → SOLID, rating-side D/R respectively.
- Likely Democrat/Republican → LIKELY, rating-side D/R.
- Lean Democrat/Republican → LEAN, rating-side D/R.
- Tilt Democrat/Republican → LEAN, rating-side D/R, with `coarsening=TILT_TO_LEAN` logged for every affected row.
- Toss-up → TOSS_UP; sampling-party from independently corroborated cutoff held-seat party, not a directional rating.
- Not Up This Cycle → contextual noncycle candidate only; official seat/class/election evidence must confirm its frame status. It does not mean SOLID and never supplies a fabricated D/R rating.
- Any other/missing/unrecognized rating or unresolved party → PENDING, blocks a complete accepted frame rather than becoming a structural exclusion.

Tilt-to-Lean is a proposed new coarsening, not an asserted equivalence of forecasters' meanings or win probabilities. Preserve separate original-category counts in every receipt. Do not tune this coarsening on observed election errors or quietly drop Tilt races. No probability model is derived from these categories.

For non-toss-ups use the party explicitly named in the rating, not the export's generic party object, incumbent party, election winner or candidate finance affiliation. The observed directional rating opposes the generic party field in 26 House/three Senate records; this is a semantic distinction, not automatic data corruption. For toss-ups, retain the export held-party as an unaccepted hint until official dated seat-party evidence resolves D/R/OTHER, including vacancies and last-holder rule. Unknown is never guessed; OTHER retains nominal zero quota and explicit shortfall treatment. Final candidates and fusion affiliations require independent ballot mapping, not rating-side labels.

## Regular-election universe and stage rules

Retain all 435 House IDs as coverage candidates. Require an official November 3 regular general contest, final nominees/amendments and target geography for each. A publisher special flag is not authoritative. FL-20 has special=true in the export, yet Florida's amended Broward general-election notice explicitly includes District 20. Keep this conflict pending until final state/county ballot/term documentation resolves the particular contest; do not automatically delete FL-20 or relabel all its elections regular. Simultaneous regular and vacancy elections need separate IDs and terms; only the regular contest belongs to this proposal.

For Senate, use the independently verified regular class-II roster (33 states, current term ending January 3, 2027) as the expected regular-cycle coverage frame, subject to final election/ballot certification. Do not filter on election_year alone: 75 export rows say 2026, while 65 are Not Up This Cycle. Preserve these fields and their inconsistencies without converting them into extra regular races. All 33 class-II records must reconcile to official identities; their candidate eligibility is not established by class membership alone.

OH and FL appear as rated class-III context beyond those 33. Ohio's published official directive/writ text identifies a special November 3 vacancy election for the unexpired term ending in 2029; direct PDF body/hash verification remains pending after channel failures. Florida's general notices and official appointment context support further investigation but did not, in this bounded check, explicitly resolve the particular Senate vacancy-election term/type. Record Florida as pending for that classification. Do not infer either is regular from special=false. Proposed rule: non-class-II contests never supplement the regular 33 to fill Senate quotas; after official classification they remain logged out-of-scope special/context rows. Pending classification is preserved, not mislabeled complete. See `reports/E01_ELECTION_TYPE_EVIDENCE.md/.json` for exact evidence limits.

## Selection and evaluation policy retained, with a new version lock

If adopted, retain 24 House with nominal 8 toss-up/8 lean/4 likely/4 solid, D/R cell targets 4/4,4/4,2/2,2/2; Senate up to eight with one D/R per band; seed 20261103; ordered quota, imbalance, region/state and deterministic rank objectives; and reviewed shortfall/deep/OTHER/failure rules. Use the new amendment identifier in the hash-rank prefix so a new source lock cannot masquerade as the old Cook selection. This requires a separately reviewed implementation/config version; it is not a flag accepted by the current code. No seed rerolls or source/date changes to obtain preferred contests.

Final D-R ballot structural exclusions must be independently resolved over the complete expected frame before sampling. Polling, historical vote availability, crosswalk difficulty, model behavior or eventual errors cannot select races or trigger replacements. Unknown ballots/stage/amendments remain pending. Preserve six deep IDs before predictions, evaluate simple and advanced methods on the same exact races/outcome versions and weights, and keep office-specific macro MAE separate. Missing full-set predictions block the intended comparison; swarm equal-compute and all original earned-complexity gates remain required.

## As-of tier and acceptance

Retain proposed analytical cutoff `2026-11-03T04:59:59Z`. The export declares an October 29 update; captured row dates precede that cutoff. These are publisher-declared facts, not an independently authenticated pre-cutoff archive. URL cache versions and November 3 browser copies do not prove historical immutability. The acquired hashes describe browser-visible UTF-8 text, not HTTP wire bytes; headers/redirect history were unavailable in that channel. Original urllib403 and later ordinary-browser success remain separate observations.

Strict as-of acceptance needs evidence independently binding the exact version to the cutoff, plus audit of revisions. Until then the original authenticated as-of gate remains BLOCKED. A later proposal could explicitly permit a publisher-declared-as-of exploratory reconstruction with contamination limitations, but that would be a further reviewed scope amendment, would not satisfy the strict original gate and is not authorized by this draft. Neither path can claim a past prospective submission or undo operator/model knowledge of outcomes.

Before adoption: independent reviewers must approve source identity/version and limited rights scope, Tilt mapping, party semantics, complete regular/special/noncycle adjudication, final ballot/amendment universe, geography and as-of tier. New fixtures must cover all nine directional/toss-up labels, Not Up, unknowns, held/favored mismatch, source special-flag conflict, election-year overinclusion, class coverage and hash/version mismatch. Actual selection additionally needs accepted sources/ballots and a new implementation audit; there is no REAL enablement in this task. No results, sample, paid execution or publication follow from the proposal. Cost: $0.
