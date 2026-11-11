# E02 live issue-support cue: two model configurations

The third distinct live E02 study completed on November 10, 2026. Its continuation ran from 19:52:57 to 20:13:57 UTC (2:52–3:13 p.m. EST), using two saved baselines from an earlier stopped attempt. The closed evidence was collected on November 11. [Independent actual-evidence review passed](INDEPENDENT_AUDIT_E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json) on November 11 for the retained responses, accounting, exclusions and registered descriptive scores. The immutable aggregate retains its build-time pending flag; the later separate audit supplies acceptance. The original E02 research contract remains incomplete.

Run: `e02-issue-cue-crossmodel-recovery-live-20261110-01`. Frozen source commit: `80ee535b1aab3b1ba292ee929d8dac51d4c20cc1`; release commit: `dc82cbe6b6b6cb19f1ce302e4c777714642b2162`. The [aggregate evidence](E02_ISSUE_CUE_CROSSMODEL_RECOVERY_ACTUAL_20261110.json), [frozen scientific protocol](../docs/E02_ISSUE_CUE_CROSSMODEL_V1.md), [release](E02_ISSUE_CUE_CROSSMODEL_RECOVERY_RELEASE_20261110.json), and [pre-execution review](INDEPENDENT_AUDIT_E02_ISSUE_CUE_CROSSMODEL_RECOVERY_CODE_PARTICULAR_V1_20261110.json) record the exact scope.

## What was tested

Four fictional party-prior contexts received three authored library notices: no reported measured visit effect, 40% more visits, or 40% fewer visits. The proposal, budget and news-card wrapper were otherwise matched. These are fictional scenarios, not real news or library measurements. Each isolated post prompt either omitted the model's earlier support rating or showed its exact own rating for that same context. Other earlier questionnaire answers were not shown. The reference baseline already contained the neutral notice; it was not an unexposed baseline.

Two fixed configurations were interleaved: GPT-4.1 nano served by Azure, and Qwen3-30B-A3B-Instruct-2507 served by Nebius. The reported GPT revision was `openai/gpt-4.1-nano-2025-04-14`; the Qwen route was `nebius/fp8`. Model, serving provider, quantization and tokenization differ together, so this is not an isolated causal comparison of model families.

## Descriptive results and denominators

Content contrast means support for the positive notice minus support for the negative notice, on the custom 0–100 support scale. The primary interaction is the SHOWN content contrast minus the OMITTED contrast within the same context.

- **GPT/Azure:** OMITTED contrasts were 25, 25 and 50 points in the three complete contexts (mean 33.33). SHOWN contrasts were 0, 0 and 0 in those same contexts. Interactions were −25, −25 and −50, mean **−33.33 points**, with **3 of 4** planned contexts complete.
- **Qwen/Nebius:** OMITTED contrasts were 55, 55, 40 and 55 (mean 51.25). SHOWN contrasts were 0, 20, 35 and 25 (mean 20). Interactions were −55, −35, −5 and −30, mean **−31.25 points**, with **4 of 4** contexts complete.
- **Matched cross-model comparison:** Qwen-minus-GPT interactions were −30, −10 and +20 in the **three common complete contexts**, mean **−6.67 points**. This is not subtraction of the two unequal-denominator overall means.

The finite descriptive attenuation criterion was met by Qwen but not GPT, because GPT lacked the required fourth complete context. Consequently the frozen pattern **across both configurations was not met**. The available contrasts became smaller in both configurations, but that observation does not repair missing data or establish a general anchoring mechanism. No confidence interval, significance test, equivalence test or population inference was planned or estimated.

## Missingness and factual answers

All 56 planned slots have dispositions: **53 answers and three prespecified skips**, with zero parse-error, failed, cancelled or unattempted slots. ANSWER means a parsed response, not that every survey item was valid.

One GPT R-prior baseline returned null issue support. Its three SHOWN posts were therefore skipped under the frozen rule; its OMITTED posts still ran. Two of those OMITTED answers also returned null support, preventing that context's content contrast. In total GPT returned three null support items among its 25 answers. Qwen returned all four valid items in all 28 answers. Missing unrelated thermometers did not exclude valid support scores.

All **53 asked factual questions were answered correctly**: GPT 25/25, Qwen 28/28. For post questions, GPT OMITTED was 12/12 and SHOWN 9/9 answered (9/12 planned); Qwen was 12/12 in each mode. The three unasked GPT posts are not factual errors. No missing answer was repaired, imputed, replaced or resent.

## Execution, costs and preservation

The continuation made **51 new model POSTs, 53 billing GETs and eight catalog GETs**. The two additional billing attempts were permitted retries of closed 404 responses; no model prompt was retried. Together with the two saved baselines, the study contains 53 actual generations. The original stopped attempt made two POSTs, four billing GETs and two catalog GETs. Its evidence and the temporal gap remain explicit.

Verified continuation charges total **$0.0037429**: $0.0017402 for 24 new GPT generations and $0.0020027 for 27 new Qwen generations. Including the saved baselines, this study costs **$0.0038870**. Across all three distinct research studies there are **107 generations costing $0.0069294**; their scientific estimands are not pooled.

The financial owner conservatively counts **$0.009319**, including rounding and all four unchanged historical holds of 340, 340, 788 and 1008 microdollars. This is not an invoice total. The original Qwen hold remains even though its saved response and matching bill were admitted analytically. Reported-null service tier remains UNKNOWN, not default. Generation metadata reports `streamed:true` although the client requested `stream:false`; the reviewed policy preserves this unresolved provider-telemetry discrepancy without inferring streaming or fallback. The original $0.10 study ceiling, cumulative E02 $1 ceiling and shared $5 ceiling were preserved; E01 paid inference remains $0. No credit purchase, silent fallback or sample extension occurred.

The closed owner export contains 664 events and 109 lifetime financial rows. All 354 earlier events, 58 earlier rows, prior study namespaces and journals are unchanged. The continuation retains 374 private journal files. The read-only collector changed no owner files and made no provider requests. Credentials, owner storage and raw journals remain outside Git; public receipts bind their hashes. Saved provider objects are canonical parsed objects, not claimed original HTTP wire bytes.

## Offline score reproduction

This command requires the retained local private journal. It reads saved files and runs the pure scorer; it sends no requests and does not access credentials or the financial owner.

```bash
cd /Users/joshua/Documents/ChatGPT/synthetic-society-lab
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
from civiclab.common import canonical_bytes, canonical_hash
from civiclab.e02.issue_cue_crossmodel_v1 import analyze
base = Path('data/processed/e02_issue_cue_crossmodel_recovery_actual_20261110_01')
saved = json.loads((base / 'retained-journal/summary.json').read_bytes())
result = analyze(Path('configs/e02_issue_cue_crossmodel_v1.json').read_bytes(),
                 canonical_bytes(saved['response_envelope']))
assert result == saved['analysis']
print(canonical_hash(result))
print(result['crossmodel_common_context_interaction_difference'])
PY
```

Do not rerun the consumed paid launcher. A fresh clone contains the implementation, authored tests and public aggregates, but not the private raw journal.

## Research limits

This is one authored issue, four purposive fictional contexts, a custom human-unvalidated support item and two fixed serving configurations. It supports a descriptive comparison of these recorded model outputs. It does not estimate human persuasion, representative political opinion, a general cognitive mechanism or prospective election performance. The earlier whole-answer cue and wrapper studies remain separate. The published human anchoring literature motivates the question but supplies no matched human anchor for this task.

Broader stimuli, a suitable human-study comparison, representative population validity and preregistered replication remain necessary. Real feeds, assistant interaction, swarms and E03/E04 remain gated. This report and publication drafts are for owner review; no external paper or blog publication is authorized.
