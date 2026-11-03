# E01 implementation and reproducibility

`src/civiclab/e01/pipeline.py` implements strict evidence validators, prior-seat/geography guards, S0, frozen prediction payloads, held-out evaluation, paired comparisons and conservative returns auditing. No OpenRouter or network dependency is used; costs are zero. DEMO has invented toy numbers and real-data audit has no forecast performance results.

Python API after installing the project:

```python
from pathlib import Path
from civiclab.e01 import run_demo, run_audit
run_demo(Path('.'))
run_audit(Path('.'), Path('.'))
```

Run integration only after foundation acceptance. Replay stable artifacts using the same seed; run directories/events contain run-specific timestamps while DEMO features, frozen prediction hash and scores remain deterministic. `features.json`, `predictions.frozen.json`, `evaluation.json`, `counterfactual.predictions.json`, `counterfactual.evaluation.json` and `paired_comparison.json` preserve toy baseline/counterfactual provenance. The counterfactual is a fixed +1pp shift on the same fictional outcomes and is not evidence of forecasting improvement. Seed is logged for compatibility; S0 itself is deterministic and does not consume randomness.

`returns_audit.json` hashes each real returns file and records rows, state coverage, stage/mode counts, redactions, invalid numeric votes, possible sentinel rows and state-level mixed modes. State-level mixed modes flag review, not confirmed unit-level overlap. `readiness.json` records explicit missing historical/candidate/geography blockers. Raw returns and respondent data stay local and Git ignored. Reacquire the registered source bytes for a clean-machine real audit. A fixture-only DEMO needs no downloaded data.

`freeze_predictions` launches `python -m civiclab.e01.worker` in a child process with only validated feature objects on stdin; run config and outcomes remain in the parent. The worker has an empty temporary working directory and a minimal environment excluding credentials. After trusted module imports, a Python audit hook denies file opens, directory enumeration, network sockets, subprocesses and dynamic-library loading. Separate tests verify file-read and socket denial. This guards against accidental I/O in trusted predictor code; OS access is not sandboxed against adversarial code.

The predictor's allowlist and evaluator's freeze checks are a logical separation, not OS-level isolation. JSON/feature hashes can detect changes but cannot certify that an operator never observed outcomes or that feature values have authentic historical availability. The generic `freeze_predictions` function rejects `REAL` execution. A real runner may be enabled only after verified manifest, prior-return and aggregation evidence gates are wired end to end; the existing real-data command is a readiness audit. No real forecast runner is enabled while those inputs are unresolved.

Tests in `tests/test_e01.py` are stdlib unittest fixtures, including explicit ballot/map/class failures, formula/sign, tamper detection, holdout coverage, unknown outcome fields, matched comparison, fusion-party aggregation, TOTAL/component overlap, duplicated lines, redactions, sentinel handling and runoff/date rejection. All candidate names and vote values in tests are marked DEMO.

## November 3 implementation evidence

After foundation acceptance, `.venv/bin/python -m unittest discover -s tests -p test_e01.py -v` passed 17 tests. Two final DEMO runs (`e01-a34c424232354cad9af8df554e92ffb5`, `e01-0d10b9ff3b644327bb6ea40a8e79d986`) reproduced frozen prediction SHA-256 `d39234b7a8fbd940d88fbf2482047b3252a8da690d5f25ffca755ca5c1592399`. These are local generated runs, excluded from Git, and can be regenerated using the commands above.

Real audit run `e01-d6479ed10d4645b49e9abe8c2e520909` inspected 21,938 2022 Senate county rows, 994,635 2024 Senate precinct rows and 1,177,213 2024 House precinct rows. The 2024 Senate file had 19,323 redacted/missing vote values and 3 invalid numeric rows; House had 9,863 and 4 respectively. Numerous one-vote rows require source-specific adjudication. Some states contain both TOTAL and component modes; the audit flags these for review without assuming same-unit overlap. These are structural observations, not validated state totals. Real forecasting and scoring remain `BLOCKED_REAL_BASELINE` for the missing evidence documented in the protocol. All executed work used local computation and incurred $0 model/API spend.
