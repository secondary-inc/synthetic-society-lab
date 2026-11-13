# Research direction after the 2026 midterms

Recorded November 12, 2026 (America/New_York). This is an owner-approved direction
and work sequence, not a new experimental protocol, execution release or result.
The owner asked whether the completed election should change the research and
answered “sure” to keeping E02 primary, completing E01 retrospectively, and
reserving genuine advance-prediction testing for a future election.

## Priorities and completion requirements

E02 remains the primary experimental track. E01's independent statistical
baseline continues alongside it as a retrospective benchmark. E03 and E04 stay
gated. The [original completion contract](../AUTONOMOUS_RESEARCH_ORCHESTRATION.md)
and [machine-readable requirements](../configs/completion_contract.json) remain
in force; this decision does not mark any scientific gate complete.

For E01, preserve the proposed 24 House/up-to-8 Senate scope and the 4 House/2
Senate deep comparison, subject to the existing source and selection gates.
Missing evidence remains BLOCKED. An available subset or a future election
cannot silently replace an unmet original requirement.

## E01: retrospective evaluation

The research question is whether additional model complexity improves
electoral-margin estimates over simpler methods on the same races, using
documented historical inputs and cutoffs. The [current retrospective
protocol](../protocols/E01_RETROSPECTIVE.md) continues to govern scoring and
comparability.

1. Complete and independently review the source-format pipeline already in
   development. Generated PDF tests and format inventories do not validate
   candidate identities, vote totals, ballot status or geography.
2. Validate historical inputs, official contest/ballot evidence, map versions
   and the permitted selection frame. Same-seat Senate persistence uses 2020
   for regular 2026 contests; House persistence requires comparable 2024
   geography. Record unavailable inputs rather than inventing or imputing them.
3. Freeze the race-selection rules, historical feature cutoff, methods,
   exclusions and scoring before new evaluation. Keep prediction inputs and
   outcome files separate. Record every prior exposure to outcomes that is
   known, including outcome exposure in this November 12 planning chat.
4. Use official certified returns for final scoring, with source/version dates,
   hashes and certification status. Any interim scoring must be explicitly
   provisional; preserve each revision and rerun scores without retuning the
   predictions. Election-night returns and media calls are not certification.
   See the [EAC explanation of canvass and certification](https://www.eac.gov/election-officials/election-results-canvass-and-certification)
   (consulted November 12, 2026).
5. Compare methods on identical eligible races, cutoffs and outcome versions.
   Report House and Senate separately, including race-level errors, missing
   predictions and paired differences from the simpler baseline. Swarm
   comparisons additionally require equal-compute independent controls.

Freezing work now improves reproducibility; it does not restore pre-election
ignorance. Researchers and models may already know outcomes. A historical date
in a prompt, a local hash, or withholding an outcome file cannot establish
absence of model-memory or researcher contamination. No independently accepted
pre-results 2026 prediction archive exists in the current project evidence.
Any authentic archive discovered later must be reviewed on its own unchanged
bytes and independent timing evidence. New work remains retrospective.

## E02: controlled experiments in AI responses

Keep the three completed studies distinct and retain their original protocols,
exclusions, failed attempts, costs and missing responses. Their post-election
execution dates belong in the methods. Neither election timing nor a new plan
changes the third study's unmet across-configuration criterion.

Next scientific design work should address additional permitted stimuli,
broader model/configuration robustness and an appropriate independent human-study
comparison. Freeze each follow-up question, sample, scoring, exclusions, matched
controls and finite cost envelope before execution and obtain independent
review. A study can be prospectively specified before its own model responses
even though it occurs after the election. It cannot explain actual 2026 voting
behavior from synthetic responses alone.

## Future advance-prediction test

A future election is a planning direction only; no contest or execution date is
selected here. Before such a test, specify the sample and methods, archive the
eligible inputs and exact predictions with independently verifiable pre-results
timestamps, and lock the evaluation rules. Retain failures and all registered
contests. Any external registration or publication must follow the existing
owner-approval rule.

## Current operating boundary

The combined cumulative ceiling remains $5, the current E02 pilot ceiling $1,
and E01 paid inference $0, counting charges and outstanding holds together.
Existing one-shot launchers and consumed limits are unchanged. This note
initiates no inference, acquisition, ledger change, publication or scheduled job.

Current execution evidence remains in [STATUS.md](../reports/STATUS.md), the
[latest E02 result](../reports/E02_ISSUE_CUE_CROSSMODEL_RESULT_20261110.md), and
their separate independent audits. This planning update requires its own narrow
document review; it does not renew historical code or scientific acceptance.
