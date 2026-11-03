# E02 F Wyoming path and owned-root storage remedy v1.1

IMPLEMENTATION CANDIDATE, pending independent re-review. Exact v1 files,70 indexed raw fixture files, original findings and actual-wiring proposal are preserved. `reports/E02_F_WY_BOOTSTRAP_V1_FREEZE.json` and the supplemental storage-finding freeze pin the historical state. No actual source authority or access follows.

## Narrow changes

`f_wy_bootstrap_v1_1.py` retains authored bundle construction and source semantics. The first no-follow descriptor walk records device/inode identities for every absolute lexical ancestor, including the filesystem root. After bounded archive/header/companion reads and original file fstat, the inspector independently reopens the entire current absolute lexical path with no-follow checks. It compares current ancestor device/inode identities and the reopened regular file's five-field identity against the original observations. It no longer treats stat relative to an old retained parent FD as proof of the current lexical path. Directory mtime/ctime are deliberately excluded from directory identity: unrelated new entries can legitimately change those timestamps. File pre/post identity retains device/inode/size/mtime_ns/ctime_ns. This is observed pre/post path closure, not an atomic snapshot or hostile-host guarantee.

`f_wy_bootstrap_control_v1_1.py` derives from the frozen control transition implementation and overrides storage accounting to scan the entire owned bundle root once. It includes mandatory `BUNDLE.local.json`, the new explicit v1.1 lineage marker and unexpected owned-root files under existing core accounting. Source/runtime inputs and native runtime output categories retain their existing category roles; unknown owned-root files are charged conservatively to core. Hardlinked/duplicate bytes are counted per retained path, symlinks refused, and all existing per-category/cumulative/free-space limits and write projections remain. No excluded metadata pool, quota increase, reset or refund is introduced. New v1.1 controls require freshly marked v1.1 fixture lineage; frozen v1 evidence is never adopted or mutated.

`f_wy_bootstrap_launcher_v1_1.py` is the frozen launcher with only its inspector/control imports switched to the new components, ensuring the real staged authored path uses both remedies. It retains normal whole-stage/global timing, conservative accounting, native cooperative topology, UNKNOWN cleanup/barrier handling and disabled actual entries. All native runtime code/config/test/approval pins remain unchanged.

## Regression and retained evidence

The separately versioned tests carry the29 prior bootstrap checks forward and add13 targeted cases: exact positive reopen, identical-byte file/parent/higher-ancestor replacement, introduced file/parent symlinks, legitimate directory timestamp change, launcher refusal/full UNKNOWN charges/no accepted proof, binding+unexpected-root accounting, exact core-cap acceptance, one-byte-over refusal, original omitted-binding allowance refusal, binding tamper/hardlink counting and refusal to adopt old lineage. The eight immutable prior release-proposal checks run alongside them. Test outcomes and exact code/test/raw pins are recorded in the new candidate config/report, not an independent PASS claim.

Private retained evidence `data/processed/e02_F_local_fixture/bootstrap-native-v1_1-20261103-01` includes the normal78-row six-stage exact PRIMARY/REPLAY fixture, a no-dispatch UNKNOWN case, a same-byte parent-replacement refusal with full charges/no accepted inspection proof, and exact/over-cap storage projections. The projections allocate no oversized file; they demonstrate arithmetic quota refusal, not an observed healthy-disk overrun. Both independently generated authored archive copies in native mock admission remain explicitly charged; no real archive copy or transfer is performed.

The original path finding is `INDEPENDENT_AUDIT_E02_F_WY_BOOTSTRAP_V1_PATH_IDENTITY_FINDING.json` SHA f2aabef0b24468392bd3574e26d6c3561e22ba2b333ac16a54f5ac75445fb681. The storage finding is `INDEPENDENT_AUDIT_E02_F_WY_BOOTSTRAP_V1_STORAGE_BINDING_FINDING.json` SHA bcb3f10dd5d74e7d6dc3f92e416c86310ed437d826f9b861d2c62374a18c9b83. Only the independent auditor can close these for the exact remedy; their original records are not edited.

## Reproduction and remaining gates

`PYTHONPATH=src:tests .venv/bin/python -m unittest tests/test_e02_f_wy_bootstrap_v1_1.py tests/test_e02_f_wy_release_proposal_v1.py -v`

Fresh evidence requires a NEW directory: `PYTHONPATH=src:tests .venv/bin/python -c "from pathlib import Path; from test_e02_f_wy_bootstrap_v1_1 import retain_remedy_evidence; retain_remedy_evidence(Path('data/processed/e02_F_local_fixture/NEW_V1_1_REMEDY'))"`.

Candidate preparation used only generated authored files and repository metadata. Actual cache stat/hash/open/read/resolve/person parsing/helper/runtime, GET/model calls, fit/disclosure and experimental spend remain zero. All source identities/actual approvals remain null in checked-in defaults. The separate conditional actual-wiring proposal remains unchanged and unimplemented; no source permission or code readiness is inferred from these worker results. Independent exact re-review is next, before any actual wiring implementation or source access.
