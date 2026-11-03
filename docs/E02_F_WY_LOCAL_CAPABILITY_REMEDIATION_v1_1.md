# F/WY v1.1 capability field and output binding remediation

Status: independent implementation remediation review pending. The original `IA-E02-F-WY-V1-CAPABILITY-001` finding is preserved and remains open until the reviewer issues a new exact-version decision. Original v1 code/config/tests/docs/evidence/runs are unchanged and pinned in `reports/E02_F_WY_LOCAL_IMPLEMENTATION_V1_FREEZE.json`, alongside lead preservation commit407c5f1. This is a separate five-module `_v1_1.py`, scoped config and test candidate. Actual execution references remain null and actual authority0. No real cache stat/hash/open/parse/GET, model call, key use, disclosure or fit occurs.

## Problem and final behavior

A frozen dataclass prevents field assignment but is copyable. v1 relied on its readable token plus only part of its body. With unchanged valid synthetic external receipts, a copied ActualAdmission could replace its archive hash or output root. The relocated root could start a second ledger and ENROLL reservation under the same unchanged execution receipt. Correct arithmetic and immutable config/receipt files did not close this field-binding gap.

On every v1.1 actual capability use, the guard now detaches/parses its config and manifest, validates the fresh external code/source/execution records, reconstructs the complete `_actual_manifest()` solely from that protected configuration/source contract/source-identity admission, and compares canonical typed hashes of the complete body. Archive size/hash, literal members/CRC/compressed/uncompressed sizes/member hashes, header hash/bytes, columns/rows, period/state/origin, metadata pins, parent provenance and stat identity must all match. Extra fields or numeric type substitutions do not become authority through equality aliases.

The guard also rederives the canonical approved private output root from the unchanged execution receipt and compares the object's root exactly, before reading a marker or creating ledger state. Its source path must be the exact lexical path from the frozen source contract. The original-root marker and complete recorded admission configuration/manifest/scope must match the same rebuilt authority. Copying a token, marker or admission file to a different root is insufficient. Invalid copied types/body/config/reference paths are structured refusals, not a route to source inspection.

The ledger revalidates admission before each replay/transition/reservation and checks that its internal root/path/config/manifest still equal the admitted context. Storage revalidates admission before quota checks/writes. Thus revocation/corruption/field changes cannot leave an already-created controller with unchecked authority. Metadata reference names also reject traversal/out-of-domain and symlink references before following a target. Existing detached-first metadata validation, bound byte snapshots, raw-read reservation requirement, lost-ledger/marker refusal, source-versus-analysis continuation and all native quotas remain unchanged. There is no new key, signer or hostile-host trust requirement.

## Regression fixture and reproduction

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest test_e02_f_wy_local_v1_1.CapabilityBindingTests -v
PYTHONPATH=src:tests .venv/bin/python -m unittest test_e02_f_wy_local_v1_1 -v
PYTHONPATH=src:tests .venv/bin/python -c "from test_e02_f_wy_local_v1_1 import record_fixture_run; record_fixture_run('data/processed/e02_F_local_fixture/NEW-ID')"
```

The regression uses the existing explicitly tagged TEST_ONLY three-receipt pattern in an isolated temporary ROOT with no raw source file. The real project approval records are neither created nor edited. A valid exact-output object and an exact dataclass copy remain usable in the original ledger. One initial ENROLL reservation is the positive control. Twenty-four copied variants then change manifest source/hash/size/member/header/stat/rows/columns/period/state/origin/provenance, config, approval-path domain, source path or relocated root. The relocated root contains copies of the original marker and admission file while its external source contract/config/three receipt bytes remain unchanged.

For every variant, direct admission use, ledger construction/reservation, pilot enrollment, source inspection and source parsing refuse. Replacing the admission attached to the existing ledger also refuses before another transition. Instrumented raw-source stat/open/hash/identity and worker hooks must remain uncalled. The original state and event bytes remain unchanged; no ledger appears in the relocated directory. An exact object copy reopens the original ledger, but a second ENROLL is still refused. External authority bytes are verified unchanged after all probes.

The complete20-method suite also retains all19 prior source/CSV/domain/private-output/partial-mask/uncertainty/resource/continuation/crash/metadata-alias/lost-ledger checks. Retained new v1.1 full-shape MOCK primary/replay and output indexes are pinned in the versioned evidence. Old v1 remains defective history; rerunning its passing old tests is not acceptance of that implementation.

## Acceptance and limits

A separate auditor must reproduce the original two copied-object attacks and independent field/root/config/authority-loss variants against exact new pins; verify zero additional source I/O/reservations/workers and exact-positive output behavior; rerun the new suite; inspect the retained typed partial data, charges/replay and protected metadata bindings; and issue a new bounded decision. The implementer does not edit or close old findings.

Actual data/execution remains gated behind separately reviewed real code/source/execution receipts. No current cache presence/identity or29,297-row parser/arithmetic/resource compatibility has been verified. Authored/mock values and fabricated metadata test receipts are engineering fixtures only. National transport, post-run actual arithmetic review, F disclosure/fit, representative political priors/human effects and the full research contract remain separate. The existing trusted code/preserved-authority boundary, sampled/cooperative limits and unpriced local/development-assistant costs remain explicit; experimental API/model spend0.
