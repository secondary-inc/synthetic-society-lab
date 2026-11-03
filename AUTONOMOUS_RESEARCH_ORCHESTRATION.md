# Synthetic Society Lab — autonomous agent organization

**Status:** orchestration design / drop-in configuration. Not evidence of executed experiments.
**Scope:** E01 retrospective 2026 election forecasting, E02 randomized synthetic information exposure; E03 city/E04 government follow after gates.
**Repository:** `secondary-inc/synthetic-society-lab` (inspect actual repo before editing). These are agents for *building and evaluating the research software*, not thousands of simulated voters. The simulated voters are data-generating experimental runs via the OpenRouter adapter.

## Mission and completion contract
Run the maximum defensible fraction of the research workflow unattended after owner setup, while never inventing data, results, authority, publication approvals or spending authorization. The project is **done** only when:

1. Source inventory verifies and a clean checkout can reproduce the dependency setup and **documented fixture tests** (except source files not legally distributable; documented download scripts must recreate their manifests).
2. E01 has a frozen reproducible race manifest, candidate and geography checks, historical baselines, comparable agent variants, sealed holdout evaluation, result tables and an explicit statement that no prospective 2026 submission exists unless independently proven. Retrospective contamination limitations are documented.
3. E02 has a frozen hypothesis and questionnaire mapping, ACS/ANES-calibrated fictional profiles, independently licensed/approved stimuli, controlled randomization, context isolation, deterministic scoring, variance estimation, registered analysis and sensitivity analysis.
4. Model calls run only via OpenRouter, require an explicit enabled budget with real dispatch reservation and provider usage reconciliation, and have cancellation/retry and checkpoint semantics.
5. A reviewer separate from the implementing agent tests every milestone; CI passes. Every table and figure traces to stored run IDs and versioned provenance.
6. A reproducibility pack, draft paper/blog, uncertainty and failure analysis, source/reuse notes and a truthful status report are ready for **owner review**. No automatic public release or external political activity.

If a gate cannot be met, issue a truthful `BLOCKED` finding with exact unresolved dependencies, preserve the valid partial work, and continue independent approved work. Do not silently lower success criteria.

## Roles and ownership
The **Lead/Orchestrator** is the primary Codex thread, not a separate custom file. It sequences tasks, delegates read-only exploration and independent work, protects scientific protocol, coordinates branches/PRs, runs CI and updates `reports/STATUS.md`. Never self-certify. Only spawn 2–3 workers concurrently (subagents cost additional tokens), preferably from distinct files/worktrees.

| Subagent | Owns | Evidence of completion |
|---|---|---|
| `data_steward` | Download manifests, consent/licenses, ANES/ACS/GDELT/MEDSL/FEC/Census validation, timestamps, hashes | source integrity summary and reproducible importer tests |
| `methods_researcher` | Primary scales, questionnaire mappings, preregistered estimands, statistical plan, research ethics | frozen analysis-plan draft with deterministic scoring specifications |
| `population_engineer` | Synthetic fictional profiles, weights, correlations, geographic strata, calibration, missingness | calibration report and held-out ANES comparison |
| `stimulus_engineer` | Permitted real news/official statements, X/Meta when authorized, dedupe, treatment cells, matched text, feed approximation | stimulus manifest with exact text, rights, timestamps and randomization checks |
| `election_engineer` | E01 race registry, candidate/ballot checks, district boundaries, crosswalks, baseline and agent forecasts | same-race baseline evaluations and leakage report |
| `exposure_engineer` | E02 isolated sessions, OpenRouter adapters, pre/post survey runner, paid-run gating and retry handling | mock run and bounded-pilot traces with reconciled cost |
| `platform_engineer` | installable Python package, CI, artifacts, job queue, GitHub actions, auth/secrets safety, cloud runner, dashboard API | clean install, budget/cancel tests, trace storage |
| `independent_auditor` | Review test validity, bias, source leaks, statistical implementation, reproducibility and publication claims | independent audit with findings severity and pass/fail gates |
| `publication_engineer` | Dashboard, visualization, figures, blog and technical manuscript drafts | plots built only from real run files; publication package with caveats |

Scientific independence rule: `independent_auditor` must not be asked to write the code it certifies. Final metrics must be computed from validated raw outcomes, not produced or judged by the same responding LLM.

## Dependency graph and activation order

- **Gate G0 — Repo reality:** Inspect actual checkout / source inventory. Verify paths, package, tests, existing branches and `.env` ignore. Ignore any previous claim about passing tests unless rerun. Lead activates `platform_engineer` + `data_steward`; `independent_auditor` reviews.
- **G1 — Freeze scientific protocols:** `methods_researcher` chooses ONE E02 primary estimand and scale (e.g. ANES partisan feeling-thermometer gap) and secondary ideological position and institutional trust separately; confirms scoring/missing-code handling, population and clustering. E01 protocol defines margin error, race sample, control baselines and any post-election contamination. Auditor signs protocol before confirmatory runs.
- **G2 — Data:** `data_steward` verifies raw inventory / licensing and source timestamps. `election_engineer` verifies final ballots and valid district geographies. `stimulus_engineer` assembles small permitted matched-content stimuli, can use GDELT metadata as discovery, never assumes full-text rights or actual personalized feeds.
- **G3 — Deterministic engine:** `platform_engineer`, `population_engineer` and `exposure_engineer` implement in separate modules; deterministic mock calls and unit tests before inference.
- **G4 — Offline pilot:** 12 fictional profiles x predefined treatments with mock provider; ensure assignment reproducibility, matched content, session independence, invalid-response logging, scoring reliability and strong test coverage. This is an engineering smoke test, NOT a scientific result.
- **G5 — Paid pilot (owner authorization required):** Only after full run estimate, hard spend cap, key rotation where exposed, valid external billing and affirmative permission. Use an inexpensive pinned OpenRouter model; do not self-authorize spend. Record model revision/provider, model call ID, usage and costs. If spend remains zero, proceed with all offline work.
- **G6 — Scale and independent evaluate:** Run preregistered sample sized from pilot variance and budget, cross-model checks, seed/prompt robustness and statistical intervals. Freeze holdout and analyze all failed conditions. E01 retrospectively on sealed historical data if no verified timely forecast.
- **G7 — Publishable package:** `independent_auditor` reviews; `publication_engineer` writes honest findings, plots and blog draft; lead creates a review PR. Human signoff required for publication/affiliation claims.

Run E02 and E01 engineering in parallel only after G0. Run E01's *statistical baseline* independently of E02; do not wait for X/Meta. Separate data lineage, protocol, result folders, metrics and interpretation.

## Security, policy and cost boundaries

- `.env` and credentials stay local or in trusted secret stores; never commit/print them. Rotate any previously exposed credentials. No browser logins, Meta verification or ToS circumvention by an agent unless a permitted connected interaction is expressly authorized; do not scrape restricted private feeds.
- `PAID_API_ENABLED=false`, `MAX_SPEND_USD=0` by default. Model calls must fail closed; a string flag alone is not budget enforcement. Budget reservation must occur before requests; reconcile after provider usage. Disable unbounded retries. Separate OpenRouter inference costs from X/Meta content costs.
- No posting to X, personalized political targeting, campaign contact, real-voter persuasion, autonomous public publication, or unsupported claims about human voter behavior. Fictional synthetic profiles only; avoid collecting unnecessary sensitive personal data.
- Do not label 2026 election work prospective unless a pre-results independently timestamped forecast file is verified; never backdate or selectively choose pre-election predictions.
- When anything fails, preserve raw artifacts, record error and source, retry boundedly and mark it BLOCKED rather than inventing outputs.
- Independent workers must not edit the same files at once. Use task-level branches/worktrees, PR review and explicit ownership before merging.

## Agent job contract
Each worker returns:

```
TASK_ID:
FILES_CHANGED:
OUTPUT_ARTIFACTS:
REPRODUCTION_COMMANDS:
TESTS_RUN_AND_RESULTS:
SOURCE_DATA_AND_LICENSE_NOTES:
COST_USD_ACTUAL_OR_ZERO:
RISKS_AND_LIMITATIONS:
UNRESOLVED_BLOCKERS:
NEXT_UNBLOCKED_TASK:
```

Lead updates `reports/STATUS.md` on each milestone and stops only at the full completion contract, a real external blocker, a budget ceiling, or a required approval. Each task has one responsible worker and one independent reviewer. No fake green status.

## Minimal one-time owner input (cannot legitimately bypass)
- Confirm intended repo/workspace access and install or choose a Codex Cloud environment or hosted runner.
- Put valid secrets into a secure environment; rotate exposed tokens. Approve third-party data permissions where requested.
- Set any **nonzero** API / content-spending ceiling explicitly and enable approved usage. Default remains $0.
- Approve use of organization name and final external publication; review scientific claims and any copyrighted excerpts.

After setup, cloud tasks can continue while the laptop is asleep, but this is **not** a guarantee of indefinite autonomous execution. For repeated scheduled runs, install persistent job orchestration (e.g. GitHub Actions with careful secret handling and job queues). Codex cloud task workspaces are not themselves a permanent production job scheduler.
