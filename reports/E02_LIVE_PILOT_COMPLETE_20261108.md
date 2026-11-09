# E02: completed exploratory live pilot

The original 32-response sample is now complete. The continuation sent the
sixteen remaining requests through OpenRouter, received sixteen valid responses,
and verified every new generation bill on its first lookup. Together with the
separately recovered earlier response, all eight planned matched comparisons
can be scored. Independent outcome review passed for the evidence, accounting
and descriptive scoring. See [the independent audit](INDEPENDENT_AUDIT_E02_CONTINUATION_ACTUAL_20261108.json).

Run `e02-exploratory-continuation-20261108-01` executed November 8, 2026,
11:53:38–11:57:24 p.m. EST (November 9, 04:53:38–04:57:24 UTC). Its date suffix
records preparation, not an earlier execution time. It follows the preserved
November 5 run `e02-exploratory-live-20261105-01`, which remains **PARTIAL / STOPPED**.
No earlier prompt was resent and no original failure record was overwritten.

The experiment used four fictional party-prior profiles, two project-authored
fictional civic notices, and identical notice words in C1 news and C2 social
wrappers. Each arm had a separate baseline and post-exposure response. The
frozen outcome is the change in the in-party minus out-party feeling-thermometer
gap; the primary comparison subtracts the C1 change from the C2 change.
The serving provider was Azure, with generation metadata identifying
`openai/gpt-4.1-nano-2025-04-14`. Temperature, assignments, seeds, scoring,
exclusions and sample size stayed fixed.

All 32 answers are valid, with zero excluded matched blocks. Every within-arm
primary change and all eight C2-minus-C1 contrasts are **zero thermometer
points**. The registered descriptive bootstrap returns `[0, 0]`; with all
observed contrasts identical, this is a degenerate resampling result. It is
**not evidence of equivalence or a precise population estimate**. The registered
party, leave-one-profile-out, leave-one-stimulus-out and absolute-gap summaries
also equal zero.

This is evidence that the real inference, structured responses, billing,
checkpointing and scoring pipeline completed this small sample. These notices
produced no measured partisan-gap changes under these prompts. They do not
establish that wrappers never matter, that the model represents people, or that
human political attitudes would behave similarly. Own-baseline values appear
in each post prompt, so anchoring or consistency behavior is another limitation.

The two batches were separated in time. Four matched blocks compare an original
arm with a continuation arm, two lie entirely in the original batch, and two
entirely in the continuation. The same model name and request settings do not
guarantee identical service internals across dates. All registered blocks are
retained; the temporal gap precludes a clean causal interpretation of the
combined wrapper contrast.

Verified research charges total **$0.0014340**: $0.0007178 for the original
sixteen responses and $0.0007162 for the continuation. Native usage totals
12,036 input and 576 output tokens, with zero reasoning tokens. The new batch
made 16 model POSTs, 16 billing GETs and one public catalog GET, with no retries
or credit purchases. Earlier billing recovery made one separate GET and no
model request.

The ledger conservatively counts **$0.002857**, including all three unchanged
historical holds, against the shared $5 ceiling. This is also below the $1
pilot ceiling. Financial records contain 31 committed study phases and three
unchanged uncertain rows across 34 lifetime dispatches. The recovered sixteenth
study answer is analytically verified but its original financial row retains
its full hold. Thus 32 usable study answers must not be described as 32 newly
committed financial rows. E01 paid inference remains $0.

The source and exact execution packet passed independent review before dispatch
(commits `4748482` and `991170f`). All 26 new continuation tests passed on Python
3.11 and 3.12 in the independent code review. Post-run verification reproduced
the saved analysis and confirmed that the original eighteen financial rows,
112-event history prefix, stopped-study state and 98 original journal files
remain unchanged. The continuation adds sixteen committed phases; the owner
now has 209 events. Its 118-file private journal, raw responses, bills and
read-only owner export are preserved locally and excluded from Git.

The aggregate evidence, exact costs, source/input/output hashes, registered
analysis and temporal block grouping are in
`reports/E02_EXPLORATORY_CONTINUATION_ACTUAL_20261108.json`. Local read-only
rescoring requires the private retained journal and sends no requests:

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
from civiclab.common import canonical_bytes
from civiclab.e02.exploratory_pilot_analysis_v1 import analyze

root = Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
saved = json.loads((root / 'data/processed/e02_continuation_20261108_01/retained-journal/summary.json').read_bytes())
result = analyze(
    (root / 'configs/e02_exploratory_live_pilot_v1_1.json').read_bytes(),
    canonical_bytes(saved['response_envelope']),
)
assert result == saved['analysis']
print({k: result[k] for k in ('complete_blocks', 'excluded_blocks', 'estimate_thermometer_points')})
PY
```

This completes the limited exploratory sample, not the full E02 research
contract. A human-study anchor, accepted ACS/ANES population fitting, permitted
real-news stimuli, second-model robustness and confirmatory design remain
separate gates. The next scientific step is to examine instrument sensitivity
and baseline anchoring under a separately frozen matched design. The zero
result does not justify changing this sample or expanding paid execution
without a new bounded plan. E01 remains retrospective; E03/E04 remain gated.
Nothing has been published externally.
