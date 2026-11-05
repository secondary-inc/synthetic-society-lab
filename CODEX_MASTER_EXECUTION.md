> **Historical November 3, 2026 handoff — not a current runbook.** Preserve the blueprint below as research context. Election-Day wording, example paths/commands and test counts describe that handoff and must not be treated as current execution evidence. E01 is retrospective. Use [README.md](README.md), [reports/STATUS.md](reports/STATUS.md), and the checked-in CLI for current setup and readiness. The versioned GDELT fixture is `tests/fixtures/gdelt/20261103090000.gkg.csv.zip`.

# SYNTHETIC SOCIETY LAB — CODEX MASTER EXECUTION BLUEPRINT

**Version:** 2.0 · **Prepared:** November 3, 2026 · **Repository:** `secondary-inc/synthetic-society-lab` · **Mode:** One monorepo, OpenRouter-only model inference, default **offline / $0 authorized model spend**.

> **Read first:** `AGENTS.md`, this file, `docs/20_ELECTION_DAY_DECISION_TREE.md`, `docs/21_DATA_ACQUISITION_MAP.md`, `docs/22_PREANALYSIS_AND_STATISTICS.md`, `docs/23_IMPLEMENTATION_BACKLOG.md`, `docs/24_GDELT_SNAPSHOT_RUNBOOK.md`, and the existing `protocols/E01_FEED_TO_BALLOT.md` and `protocols/E02_INFORMATION_EFFECTS.md`.
>
> Existing documents are research drafts, not evidence that an experiment has been implemented. Inspect the real repo before editing. Do not claim any actual election prediction, experimental result, API connection, or validation unless demonstrated with source artifacts.

## 0. The mission in two sentences

**E01 — Feed to Ballot:** Test whether adding demographic grounding, synthetic agents, date-bounded news, controlled social-feed approximations, AI assistants, and agent interaction improves 2026 House/Senate *electoral margin forecasts* over honest statistical and polling baselines, at what computational/data cost.

**E02 — The Information Effect:** Test how randomized differences in *presentation and sourcing of the same underlying political information*, followed optionally by AI-assistant interaction, change **synthetic models'** expressed issue positions, institutional trust, certainty, and factual answers; validate outputs against external human studies before suggesting relevance to real voters.

The shared **research meta-question** is *Does simulated realism produce real predictive/inferential value, or only convincing-looking behavior?* A negative result is acceptable and publishable when properly designed and analyzed.

### Scope and priorities

| Priority | Experiment | Geography | Nature of inference | Deadline |
|---|---|---|---|---|
| P0 | E01 Forecast | Proposed 24 House + up to 8 Senate races (confirmed via pre-specified, verifiable 2026 race manifest); six preselected deep-run races if feasible | Predictions evaluated against election results; no human persuasion claim | Protect any **genuine** pre-results prediction window on Nov 3, 2026 |
| P1 | E02 Information Effects | A **nationwide, state-stratified** synthetic population, pilot 12 and then 50–100 profiles; scale only after power/validity audit | Randomized interventions cause changes in **AI outputs only**, not proof about humans | Pilot after time-critical E01 step |
| P2 | E03 Synthetic City | Optional Los Angeles neighborhood visualization, not a substitute for nationwide E02 | Exploratory | After E01/E02 |
| P3 | E04 Government AI Reliability | Public-source synthetic workflow cases | Benchmark | After E01/E02 |

Do **not** change this scope because UI polish is easier than evaluation. The city visualization must not silently become the entire polarization population.

## 1. Codex working contract

1. Inspect `pwd`, Git branch/status, repository tree, existing tests, mounted inputs and source manifests. Verify if the connected remote is actually accessible; GitHub connection previously returned 404. **Never overwrite or push to remote without approval.** Treat this package as an overlay for an already checked-out repo; reconcile existing changes rather than replacing them.
2. Write `reports/STATUS_YYYYMMDD.md` with `DONE / BLOCKED / NOT RUN` for each requirement and proof links. Update after every work unit. Distinguish toy fixtures from real data.
3. Default network model inference to **disabled** and hard spend limits to zero. `OPENROUTER_API_KEY` must come from a local untracked `.env`; never log it. Do not request separate OpenAI/DeepSeek/Anthropic keys.
4. Data collections may proceed only from documented, permitted endpoints. Observe rates, licensing, rights, privacy, and cost. No scraping around logins or captchas, no access to real private personalized feeds or named-voter profiling, no automated political outreach, ad targeting, or persuasion.
5. Record all inputs, source/publication/collection dates, SHA-256 bytes, code Git SHA, model ID and *actual serving provider*, parameters, random seeds, tokens, approximate and reported spend, errors/refusals/retries, and any human amendments.
6. Keep `data/raw/`, `frozen_forecasts/`, model responses, and `outcomes/` in separate directories. Election outcome data **must not** be visible to prediction-building processes. Apply access controls and test the split, not just comments.
7. Freeze predefined primary hypotheses, contrasts, evaluation metrics, race and profile selection, exclusion rules, and statistical models **before** confirmatory runs. Any later changes must be logged as deviations. Use exploratory tags for subsequent analyses.
8. Make the baseline work **without** X, Meta, OpenRouter, agent swarms, or a dashboard. Run the smallest reproducible tests first. No fabricated source data and no silent imputation of missing real inputs.
9. Every feature must have unit tests, offline integration tests or fixture-based regression tests, and evidence of actual execution. Simulated/demo UI results must be labeled *DEMO*.
10. Autonomous execution is limited to approved experimental configurations, controlled quotas, and approved sources. Agents must not change the research question, ground truth, study exclusion rules, or publish without human sign-off.

## 2. Election Day reality check — mandatory first action

Today is **Nov 3, 2026**. The original Nov 2 freeze target has passed. The user's GDELT file `20261103090000.gkg.csv.zip` is a batch timestamped **09:00 UTC / 04:00 EST on Election Day** and is **not automatically admissible for a Nov 2 pre-election cutoff**. Its source manifest is included; it is valid for ingest testing and E02 content catalog work, not by itself valid as an earlier election information archive.

In `docs/20_ELECTION_DAY_DECISION_TREE.md` implement this decision tree, race by race:

- **A: Already externally timestamped before results:** Verify immutable receipts; use the authentic archive without mutation.
- **B: No earlier archive but a genuinely uncontaminated pre-results interval remains:** Complete a *timestamped Nov 3 pre-results submission* with exact time, source cutoff and race-specific polls/results availability status. Do not backdate to Nov 2; check exit-poll/news contamination and record when each contest's polling opens and closes, with sources.
- **C: Results/exit polls or live returns have entered any relevant data/model context, or valid timing cannot be established:** Mark the affected races **RETROSPECTIVE or CONTAMINATED**. Do not claim prospective validity. Build retrospective pipeline, publish limitation, and prioritize E02. Never use observed election outcomes for choice of configuration or pre-results baseline tuning.

**Time gate supersedes feature scope.** If the model/agent system is incomplete, freeze only a defensible statistical baseline (or return BLOCKED for missing valid input), not made-up synthetic predictions. An internal timestamp/hash alone is not independent evidence of pre-results publication; obtain a user-approved publicly timestamped immutable commit/release, or trusted independent timestamp receipt.

## 3. Technical architecture

```text
synthetic-society-lab/
  AGENTS.md                       # standing rules
  CODEX_MASTER_EXECUTION.md      # this authoritative execution plan
  configs/                       # versioned preregistration, tasks, schemas, budgets, model IDs
  protocols/                     # original E01–E04 plus amendments
  docs/20_... to 28_...          # runbooks and controls
  schemas/                       # JSON schemas for authoritative records
  data/raw/                      # immutable obtained inputs, excluded from Git by default
  data/staging/                  # parsed source records before review
  data/processed/                # curated source caches, checksums
  src/civiclab/
    data/                         # loaders, schema validation, licensing filters
    geo/                          # geographic concordance and district validation
    baselines/                    # no-LLM election and polling baselines
    synthetic/                    # profiles, prompts, memories, turnout, sampling
    feeds/                        # offline feed construction; no fake platform fidelity
    model/                        # OpenRouter adapter, response validation, budgets
    experiment/                   # frozen protocol runner and assignment
    evaluate/                     # MAE, paired differences, uncertainties, errors
    provenance/                   # byte hashes, source/method lineage
  scripts/                        # CLI for preflight, ingestion, dry run, freeze, evaluations
  tests/                          # deterministic offline tests, mocked inference
  frozen_forecasts/               # append-only, timestamped; not overwritten
  outcomes/                       # isolated later analysis inputs, no access to predictor
  reports/                        # status reports and gate certificates
  dashboard/                      # only observational results, not invented animations
  publications/                   # blog, paper draft, figures, caveats and replication
```

Use Python 3.11+, typed dataclasses/Pydantic or JSON Schema, `pandas` or DuckDB for analytical tables, pytest, a local SQLite/Parquet data ledger for the MVP, and a small Streamlit or Next.js dashboard *after* the core run works. Build a task queue using SQLite/checkpointed CLI jobs rather than prematurely adding distributed microservices.

**Non-functional requirements:** idempotency, deterministic fixture testing, bounded concurrency, timeouts, retry caps, request backoff, file locking, atomic writes, checksums, redacted errors, crash recovery, logical clocks, provider pinning, and cost ceilings checked **before** calls with in-flight cost reservations.

## 4. E01: step-by-step scientific design

### 4.1 Sample registration and election unit

- Proposed **24 House races** spanning toss-up/lean/likely/solid and **up to 8 Senate contests**, geographically varied. Confirm *actual* counts and availability from an **as-of** ratings source before selection. If there are fewer eligible races per stratum, publish the pre-specified fallback rather than inventing races.
- Deep simulation: **4 House + 2 Senate** predetermined before any outcomes are inspected; apply each baseline to **those same exact six races**. The 32-race broad baseline and six-race deep study must never be compared using different race denominators.
- Separate House/Senate results, two-party vs multi-party counts, geography versions (120th Congress maps for 2026), incumbency and uncontested races. Statewide Senate voting units and House congressional units use different spatial information.
- Handle redistricting with 2026 official boundary/block equivalency data and areal/geographic crosswalks; keep source year, method, uncertainty and all mappings. As of November 2026, ACS 120th Congress district estimates may not be released; older district-level estimates are not interchangeable. Verify Missouri authoritative 2026 maps as Census updates may reflect court decisions.

### 4.2 Source cutoff and forecast target

- Primary target: signed **two-party vote margin in percentage points**, a documented sign convention and denominator, among valid ballots for the two major-party candidates. For races with more candidates, report the denominator and exclusion treatment transparently. Separate turnout and vote-share modeling; abstention/undecided agents are not silently split 50/50.
- Input source fields: `published_at_utc`, `first_observed_at_utc`, `retrieved_at_utc`, `licensed_reuse_status`, `content_sha256`, `source_url`, `source_type`, `snapshot_id`, `relevance_review_status`, `as_of_cutoff_utc`.
- Distinguish article publication time from the GDELT **processing** time; older URLs may now contain edited content. For strict forecast input validity, require authenticated dated snapshot or established archival provenance, and document every time uncertainty. An October publication date retrieved November 3 is not automatically a frozen October snapshot.

### 4.3 Complexity ladder: factorial arms with direct incremental comparisons

| Config | Increment over prior method | Control and main test |
|---|---|---|
| S0 | Transparent historical/partisan baseline | Baseline prediction using prior races or appropriately crosswalked past geography and incumbency/national shift, chosen without outcomes |
| S1 | Polling benchmark (separate comparator, not necessarily nested) | Date-snapshotted published polling average, with sample/mode/field dates; missing polling explicitly NA |
| S2 | Demographic statistical model (non-LLM) | Does real demographic information improve prior baseline? |
| A0 | Direct fixed LLM forecast on approved evidence | Does AI add info above same inputs? |
| A1 | Matched independent synthetic agents (no interaction) | Weighted and turnout-adjusted agent mean, not equal vote per prompt |
| A2 | A1 + controlled, time-valid news/social inputs | Does information incrementally improve forecast on **same** races? |
| A3 | A2 + bounded AI assistant Q&A | Does mediated information add useful signal? |
| A4 | A3 + interacting agents vs equal-compute independent ensemble | Does group interaction, not more tokens, help? |

Implement **S0/S1/S2 before A0–A4**. No call to an LLM is necessary for S0–S2. If an arm fails, report failure/not run; do not elevate a later arm by comparing to a weaker denominator or changing source availability.

### 4.4 Statistical scoring

- Primary: race-level absolute signed two-party-margin error (pp). Aggregate by **predeclared weights**, macro MAE with race-level paired differences and descriptive uncertainty. House/Senate separate, toss-ups separate; selection intentionally oversamples competitive elections.
- Secondary: signed margin bias, winner correctness (descriptive), calibration/Brier or log loss **only if valid, separately produced win probabilities** and a prespecified probability model, total cost (inference + content API + collection + infrastructure + review), runtime, incremental MAE per incremental dollar.
- Audit general election context, simultaneous state/national shocks, correlated errors, missing data, crosswalk uncertainty, third-party races, early voters and differing election schedules. **Six deep races are underpowered for universal superiority claims.** Avoid confident causal/external-validity claims from six cases.
- Historical 2022/2024 tests are *pipeline diagnostics and contaminated benchmarks* unless demonstrated otherwise. Model training may already include historical election results. No historical backtest should be advertised as prospective.

### 4.5 E01 stop/go rules

E01 may publish a prospective forecast ONLY if (a) entire race manifest and input cutoffs timestamped, (b) no observed returns/exits leaked, (c) each predicted race and method has a real forecast file, (d) source/data byte hashes and code version saved, (e) archive independently timestamped before outcomes, and (f) all missing/blocked methods labeled. Otherwise E01 publishes a retrospective/methodological pilot instead.

## 5. E02: experimental design and national stratification

### 5.1 Scope and target

**Primary question:** holding identical story content and synthetic persona fixed, does rendering it as a simulated social-media post instead of an original-news article cause a systematic change in that **model's** expressed institutional-trust or issue-attitude response?

**Primary estimand:** paired difference in a **single, preregistered standardized survey scale** between C2 and C1 (social wrapper minus original-news presentation) at the profile × stimulus unit. The exact scale and question wordings must be fixed *from a published human research instrument or explicitly labeled custom instrument* **before** main trials. Report raw units, score directions, missing responses and item-level reliability. Changes do not prove actual humans polarize or vote differently.

### 5.2 Population design

- Nationwide synthetic profiles across **all 50 states plus DC as feasible**, anchored to joint Census/ACS distributions and **ANES survey associations with survey-weight design**; no shortcut that independently samples age, income, race, education and political attitudes as if they were unrelated. Start a tiny 12-profile smoke test; then a 50–100 profile pilot; *never claim state-representative effects from 1–2 profiles/state*. If only broad census/ANES distribution fitting is available, use region strata and describe state labels as visualization, not estimation.
- Keep profiles **fictional and synthetic**, with no named, traceable real social accounts. Sensitive demographic features may be included only to evaluate aggregate fairness and robustness, not to infer a real person's voting preference or personalize persuasion.
- Validate generated population marginals/cross-tab associations, effective sample sizes, missingness, weight extremes, codebook-specific refusal/universe codes, and out-of-sample survey predictions.
- Agent baseline views may be supplied as explicit *experimental priors* or elicited with a questionnaire. Keep those modes separate; otherwise the study may be measuring whether the model repeats a scripted persona.

### 5.3 Stimulus curation and experimental arms

Curate a sample of real US-policy/issue **news items** with source IDs, UTC time, exact excerpt/safe paraphrase rights, editorial/publisher tags, geographic relevance, GDELT topics (no assumption that GDELT tone = ideology), factual verification and copyright handling. Control for article duplication, bots, syndicated story repetition, and platform-content self-selection.

| Arm | Treatment | Scientific purpose |
|---|---|---|
| C0 | No political content | Time/repeat-instrument control |
| C1 | Original story or fact-equivalent neutral news card | Baseline exposure |
| C2 | **Identical underlying words** shown in a synthetic social-feed wrapper | Primary presentation/source effect |
| C3 | C1 followed by fixed, source-bounded AI Q&A | AI mediation of original news |
| C4 | C2 followed by same fixed, source-bounded AI Q&A | AI mediation after social presentation |

Optional **exploratory** arms after C0–C4: actual X public posts, Meta political-ad creatives, verified misinformation warnings, source labels, chronological versus interest-match versus engagement-proxy feed ranking, bounded multi-agent interactions, repeat doses and counterfactual post removals. These require separate hypotheses and should not contaminate the primary content-matched contrast.

The user's original ambition—realistic scrolling experiences across demographic segments—becomes a **transparent approximation**. Neither public X APIs nor Meta Ad Library provide exact user-personalized feeds or private platform profiling data. Interface must say *synthetic feed, not actual X/Instagram recommendation*. Actual video/Reels stimulus access and usage rights need separate approval; otherwise use text/card stimuli, not claim Reels exposure.

### 5.4 Experimental execution and measurement

- Freeze questionnaire, polarity of each scale item, persona pool, stimuli, assignment randomization and seeds, instruction wording, outcome calculation, stopping rule, primary comparison, and planned model family.
- A within-profile crossed assignment is efficient: each synthetic profile receives every arm in **separate reset contexts**, with randomized arm/stimulus order, item sets and no cross-arm memory. No chat histories bleed across treatments.
- Preserve the same actual content across C1/C2 and C3/C4; platform shell and source attribution are separate manipulations. Control survey priming/order, verbosity, artificial obedience, baseline extremist scores, political valence, intensity of exposure, post count and response mode.
- Outputs: unchanged/changed issue responses, institutional trust, certainty, and verified factual accuracy. The 2D political compass is an **illustration only**; construct coordinates from explicitly defined consistent scales, not the original Political Compass questionnaire, and do not imply it has validated psychometric interpretation.
- Repeat across random seeds/prompt paraphrases; a second independent model family via OpenRouter as a robustness condition after budgeting. Fixed model slug/provider where possible, log actual completion metadata. Refusals/invalids are primary quality measures, not quietly dropped.
- Estimate differences with participant-profile and stimulus clustering, uncertainty intervals and repeated-run random effects, as warranted. Predeclare familywise/multiple testing adjustments for secondary contrasts. If pilot too small, report feasibility and effect estimates without overinterpreting statistical significance.
- Validate against external **human experimental** data only for comparable questions/interventions. ANES is a **human baseline distribution**, not a post-exposure human control group.

### 5.5 E02 preregistration gate

No confirmatory run until: measured variable names/codebook, valid scale items, matched content IDs, assignment/checksum manifests, exclusion rules, budget, model IDs, versioned prompts, fixed sample/estimand, and preanalysis code are committed. Post-hoc findings must be labeled exploratory.

## 6. Data acquisition: required versus optional

Read `docs/21_DATA_ACQUISITION_MAP.md`. **The only actual news data included in this package is the user-provided GDELT 2.0 GKG ZIP** and its manifest. Its 868 records / 27 fields are a parser fixture and source-candidate pool. The 95 broad US politics candidates in the earlier review are **not verified midterm stories**. No ANES, ACS, official ballots, poll snapshots, X posts, or Meta ads have been downloaded/approved here.

Minimum E01: dated 2026 district/candidate manifest, official historical election returns and geographic crosswalks, optional dated public polling snapshots, optional pre-cutoff news; strict source register. Minimum E02: approved questionnaire/codebook, real news records/text with permitted use, pilot synthetic profiles, experimental configs, OpenRouter credential only if operator approves paid runs. A full list with exact URLs, access/account status, fallback and filenames is in `docs/21_DATA_ACQUISITION_MAP.md` and `configs/MASTER_DATA_ACQUISITION.csv`.

## 7. OpenRouter-only model execution and money controls

- Only required **model-inference** credential: `OPENROUTER_API_KEY` (local `.env` ignored by Git). Endpoint: `https://openrouter.ai/api/v1`. Intended fixed model: `deepseek/deepseek-v4.1-flash-1017`; verify it exists and price at execution time. Any alternate/model family must have approved exact slug/provider (no changing `latest`/`openrouter/free` for confirmatory runs).
- Spend defaults: `PAID_API_ENABLED=false`, `TOTAL_BUDGET_USD=0`, `E01_BUDGET_USD=0`, `E02_BUDGET_USD=0`. Do not make a charge until the user explicitly approves a budget. A nominal $10–20 ceiling is **proposed**, not authorized.
- Build pre-dispatch worst-case request cost reservations based on actual provider price metadata, max input/output tokens and in-flight retries; revise with actual reported usage; hard stop on unknown price, model-switch, exhausted balance or budget breach. Separate model invoice cost from content licensing and human labor.
- Prompt/response recording should preserve structured outputs, not model private reasoning traces or sensitive secrets. Use `max_tokens`, input truncation rules, JSON validation, retry caps, rate limiting, JSONL run receipts, costs/errors. Do not silently alter provider or model to recover failures.

## 8. Research validation and risk gates

All gates below require a machine-readable `PASS`, `BLOCKED`, or `NOT_RUN` with evidence files; **no aggregate green status based only on smoke tests.**

| Gate | Acceptance evidence | Block if |
|---|---|---|
| G0 Repo & secrets | tests, source tree, hashes, .gitignore, no secret leakage | Git state unknown, secrets tracked |
| G1 Source & provenance | actual bytes hashes, URLs, dates, legal reuse | timestamp uncertain, unauthorized or corrupted data |
| G2 Geography/ballot | 2026 maps, actual candidates, crosswalk | stale boundaries, invented races |
| G3 E01 baseline | independent deterministic fixture tests, documented formula | no real inputs or output validity |
| G4 Forecast freeze | no results leakage, independently sealed artifact | late, retrospective, unsealed or contaminated |
| G5 E02 human-data mapping | survey weights, valid coded scales, population audit | implausible profiles, invalid instrument |
| G6 Treatment integrity | identical content, randomized arms, no context carryover | leakage, different content, broken randomization |
| G7 Financial & operational | paid execution off by default, capped retries/cost | unbounded calls, unknown provider pricing |
| G8 Claim integrity | transparent uncertainties, sample scope, provenance | claims imply human causation or polling equivalence |
| G9 Reproduction | second clean runner recreates fixtures/metrics | undocumented manual changes, missing code |

The master prioritized risk register `configs/MASTER_CRITICAL_RISKS.csv` covers timing, sample selection, model memory, selected information, early voting, source rights, privacy, sampling, confounding, measurement validity, API economics, and publication claims. The older 100-case risk register remains available; do **not** interpret 100 written risks as 100 resolved problems.

## 9. Required issue-by-issue execution order

**P0 — TODAY, strictly sequential where dependent**

1. `T00` Inspect repo and produce gap report, audit real/GitHub access. Test old freeze scripts and data inventory. Never lose uncommitted user work.
2. `T01` Run offline GDELT ingest (`scripts/gdelt_ingest.py`) on included zip; verify SHA-256 and 27 columns, create CSV summary, review unknown publication timestamps. The Election Day snapshot must be quarantined from any Nov 2 cutoff.
3. `T02` Decide if an uncontaminated E01 pre-results archive exists or is possible right now. Record UTC time and proof. If NO, set E01=retrospective and proceed to the first reproducible baseline **without prospective claims**.
4. `T03` Build/check source manifest and 2026 race list; code validation and geography safeguards.
5. `T04` Build S0 baseline and evaluation fixtures; verify data coverage. If real source missing, emit BLOCKED not fabricated.
6. `T05` If genuine forecast possible, freeze and independently timestamp. If not, explicitly mark that gate blocked and move on. No fancy UI first.

**P1 — E02 viable research this week**

7. `T06` Register E02 primary outcome, content-matched wrapper experiment, instrument and sources. Produce preregistration manifest.
8. `T07` Build real controlled stimulus sampler and synthetic-profile validator (nationwide/region strata); no personal user profiles.
9. `T08` Build OpenRouter adapter and *mocked* tests, zero paid execution by default. Print projected upper-bound cost for 12 × 5 smoke before asking permission.
10. `T09` Randomize C0–C4; run 12-profile dry run against mock provider; verify matched content and no carryover.
11. `T10` After user approves money and true source rights, run paid smoke and validity audit; scale conditionally to 50–100 profiles with repeats.
12. `T11` Compute paired synthetic effects, uncertainty, negative controls, prompt/provider robustness and independent review.

**P2 — publication and visualization**

13. `T12` Build **data-backed** dashboard: race status, errors (when real outcomes permitted), exposure replay, agent pre/post movement, uncertainty, cost ledger; demo fixtures must be prominently watermarked DEMO.
14. `T13` Produce results report, replication package, preregistration deviations, limitation section and separate short blog graphics.
15. `T14` Add city microgeography exploratory pilot only when nationwide E02 and E01 deliverables are credible.
16. `T15` Begin government oversight pilot in a later sprint.

See `configs/MASTER_CODEX_TICKETS.csv` for machine-readable dependency chain, acceptance tests, and stop conditions.

## 10. Publication standards and final handoff artifacts

A publishable pilot isn't automatically a peer-reviewed contribution. The package should contain:

- Research question, novelty/closest literature, dated preregistration and amendments.
- Full sample and item selection rule; actual access/rights, source cutoffs, input manifests with checksums.
- Statistical/statistical-model baseline and same-race/condition ablations, execution logs, costs and compute-matched controls.
- Main outcome with uncertainty and failure/negative controls; nulls and incompletes disclosed.
- Exact code release, reproducible CLI commands, data access/licensing instructions, model/provider metadata; no redistribution of restricted content.
- Dashboard screenshots/figures built from recorded data; no generated people or votes masquerading as observations.
- Separate findings for **human election outcomes**, **observed human research**, and **synthetic LLM response behavior**. Do not merge these into a single causal statement.

### What Codex must report after each batch

```text
RUN STATUS — [UTC time] [Git commit]
TICKET: [IDs]
DONE: [real files, hashes and passing tests]
BLOCKED: [precise missing download/API/permission]
NOT RUN: [and why]
E01 STATUS: [PROSPECTIVE_VERIFIED | PRE_RESULTS_UNVERIFIED | RETROSPECTIVE | NOT_STARTED]
E02 STATUS: [PROTOCOL_DRAFT | PREREGISTERED | PILOT_PASSED | MAIN_RUN | ANALYZED]
PAID API CALLS: [count], APPROVED CAP: [$], SPENT: [$]
SOURCE DATA: [real vs fixture, timestamps]
NEXT SAFE ACTION: [one concrete step]
```

## 11. Verification sources (accessed/reviewed Nov 3, 2026)

- ANES 2024 data and full May 19, 2026 questionnaire/codebook: https://electionstudies.org/data-center/2024-time-series-study/ — use survey weights, strata/PSUs and negative missing-response codes.
- Census 2026/120th Congressional District data and boundary corrections: https://www.census.gov/programs-surveys/decennial-census/about/rdo/congressional-districts.html — verify authoritative update, including Missouri.
- Historical U.S. election data: https://electionlab.mit.edu/data — check actual geographic vintages and dataset licensing.
- GDELT DOC 2.0 API constraints: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ — 250 max article-list records per query, timestamps and recent historical range; rate-limit conservatively (user received one request per five seconds warning).
- GDELT GKG daily/raw: https://data.gdeltproject.org/gkg/index.html and https://data.gdeltproject.org/gdeltv2/lastupdate.txt — do not download the world archive indiscriminately.
- OpenRouter fixed DeepSeek model page: https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017 and unified API: https://openrouter.ai/docs — read live pricing/provider before spending.
- Meta Ad Library API: https://www.facebook.com/ads/library/api/ — identity/developer access; aggregates do not establish individual exposure.
- X API: https://docs.x.com/x-api/posts/search/introduction — developer access/pricing and ToS are separate from OpenRouter.
- GDELT/source collection must never imply legal rights to reproduce entire copyrighted news articles.

**FINAL DIRECTIVE:** Optimize for one externally verifiable and one experimentally controlled result. *No fake predictions, no hidden model substitutions, no human-behavior causal claims from LLM-only data, no uncontrolled costs, no model selection on future outcomes.*
