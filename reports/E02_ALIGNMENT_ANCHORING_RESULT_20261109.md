# E02 live alignment and own-answer diagnostic

The fixed exploratory batch finished on November 9, 2026, from 05:29:19 to 05:35:10 UTC. It made **22 actual model requests**, with 22 successful first-attempt billing lookups. All 28 planned slots have a recorded disposition: 22 answers and six prespecified skips. [Independent actual-evidence review passed](INDEPENDENT_AUDIT_E02_ALIGNMENT_ANCHORING_ACTUAL_20261109.json) for retained evidence, accounting and descriptive scoring. The full E02 research contract remains incomplete.

Run: `e02-alignment-anchoring-live-20261109-01`. Source commit: `2396fdabb1ff7df702a1dfcf1affaab2885098b8`; release commit: `2f8b124`. See the [aggregate evidence](E02_ALIGNMENT_ANCHORING_ACTUAL_20261109.json), [frozen protocol](../docs/E02_ALIGNMENT_ANCHORING_FOLLOWUP_V1.md), [methods review](INDEPENDENT_AUDIT_E02_ALIGNMENT_ANCHORING_METHODS_PURE_V1_20261109.json), and [code/exact-release review](INDEPENDENT_AUDIT_E02_ALIGNMENT_ANCHORING_CODE_PARTICULAR_V1_20261109.json).

## What was tested

Four fictional party-prior contexts received a custom proposal-support question and a factual comprehension question, alongside the separate party thermometers. The fictional library proposal and simple news-card wrapper stayed fixed. Three counterfactual notices described no measured visit effect, 40% more visits, or 40% fewer visits. These are authored stimuli, not real library findings.

Each context had a newly elicited reference-notice baseline. Post prompts either omitted earlier answers or showed all four exact baseline answers. The reference baseline already contained the no-measured-effect notice; it was not an unexposed baseline. Requests were stateless, with frozen seeds, item order and randomized post order. The serving provider was Azure and the reported model was `openai/gpt-4.1-nano-2025-04-14` through OpenRouter.

## Observed results

- **Primary content contrast, earlier answers omitted:** support for the positive-evidence notice minus support for the negative-evidence notice was **50, 75, 50 and 50 points** across the four contexts. Mean **56.25**, range **50–75**, on a 0–100 support scale.
- **Earlier answers shown:** the same content contrasts were **0 and 0** in the two eligible contexts. Both were D-prior contexts. The other two were not tested in this condition under the frozen baseline-validity rule.
- **Matched interaction:** for those same two eligible contexts, the omitted-answer contrasts were 50 and 75. SHOWN minus OMITTED was therefore **−50 and −75**, mean **−62.5**. This uses the matched two-context denominator; it is not the difference between the four-context primary mean and the two-context shown mean.
- **Comprehension:** all 22 asked factual questions were correct, including all 18 executed post questions. OMITTED was 12/12 planned and answered; SHOWN was 6/6 answered and 6/12 planned.

The prespecified finite-task content-sensitive pattern was met. The prespecified anchoring-compatible pattern was **not** met because it required four complete paired interactions and only two were available. The two observed interactions are consistent with a reduced content response when own answers are shown, but cannot establish that mechanism or generalize across all contexts. No confidence intervals, significance tests or equivalence claims were planned or estimated.

## Why six posts were skipped

Both R-prior baseline answers returned a null Democratic-party thermometer. Their support and comprehension answers were valid, but the frozen SHOWN condition required all four baseline fields to be valid. Its three posts were therefore skipped for each of those two contexts. Their OMITTED posts still ran and contribute to the primary support contrast.

No baseline was repaired, imputed, replaced or resent. This party-asymmetric attrition limits the own-answer comparison. The scorer's frozen `task_following_concern=true` flag counts missing planned SHOWN factual answers; it must not be interpreted as an observed comprehension error. Every factual question actually answered was correct.

## Cost and retained evidence

Verified new generation charges were **$0.0016084**, with 12,988 native input tokens, 774 output tokens and zero reported reasoning tokens. There were no model retries, billing retries, silent fallbacks or credit purchases. The batch ceiling was $0.05 within the existing cumulative E02 $1 and shared $5 caps; E01 paid inference remains $0.

The two distinct live research studies now contain 54 generations with verified research charges totaling **$0.0030424**. Their estimands are not pooled. The shared ledger conservatively counts **$0.004473**, including the unchanged historical 340, 340 and 788 microdollar holds and per-generation rounding. Reservations are not invoice totals.

The owner now has 342 events and 56 lifetime dispatches: 53 committed rows and three historical uncertain rows. The original 209-event prefix, all 34 earlier rows, the first study and continuation, and both earlier journals were verified unchanged. The 160-file new private journal retains requests, canonical parsed provider responses, generation bills, checkpoints and terminal dispositions. An immutable read-only database export changed no owner files. These artifacts and credentials remain outside Git; aggregate receipts bind their hashes.

## Reproduce the recorded scores without API calls

This command requires the retained local private journal. It only reads saved files and recomputes scores; it does not load a key, access the financial owner or send a request.

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
from civiclab.common import canonical_bytes, canonical_hash
from civiclab.e02.alignment_anchoring_v1 import analyze
base = Path('data/processed/e02_alignment_anchoring_actual_20261109_01')
saved = json.loads((base / 'retained-journal/summary.json').read_bytes())
result = analyze(Path('configs/e02_alignment_anchoring_followup_v1.json').read_bytes(),
                 canonical_bytes(saved['response_envelope']))
assert result == saved['analysis']
print(canonical_hash(result))
print(result['primary_absent_content_contrast'])
PY
```

Do not rerun the consumed paid launcher to reproduce a result. A fresh clone contains code, tests and aggregates, but not the private raw journal.

## Interpretation and remaining research

This exploratory follow-up was chosen after the first pilot's all-zero thermometer changes. It shows that this model's answers responded to directly relevant evidence on this authored issue. The earlier wrapper result remains unchanged. Four technical contexts, one issue and one model family do not estimate human persuasion, population effects, or performance across models and stimuli. Whole-answer cues and asymmetric missing thermometers prevent a clean general anchoring conclusion.

The next scientific design must address baseline-item missingness, test another model family under matched conditions, and establish a suitable human-study anchor and permitted stimuli. Representative population validity, real-news trials, assistant interaction and swarms remain gated. This report and the paper/blog remain drafts for owner review; no external publication is authorized.
