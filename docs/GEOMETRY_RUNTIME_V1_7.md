# Optional physical-PDF runtime candidate

This root-owned dependency change is pending independent acceptance. It does not admit Delaware or Nebraska into the readiness pipeline.

Install the project with `python -m pip install -e '.[geometry]'` for the optional `pdfplumber==0.11.9` reader. The new `configs/runtime_python312_geometry_20261103.txt` records twenty exact runtime versions for Python 3.12 on macOS: the original thirteen versions plus seven geometry dependencies. Install that lock before the editable local project when reproducing the full observed Python 3.12 environment. The original thirteen-pin lock and historical packages remain unchanged. This is not a Python 3.11 full-environment lock, a wheel/hash lock, or a lock for transient build-isolation tools.

The offline CI configuration now requests selection, source and geometry extras on its existing Python 3.11/3.12 matrix. Remote CI has not been observed. The reproduction builder selects the new runtime lock when present, retains the old lock in the snapshot, and continues rejecting the local project as a registry dependency. Seven reproduction tests and eight standalone reader tests passed locally.

`reports/ENGINEERING_EVIDENCE_GEOMETRY_RUNTIME_V1_7.json` records two separately created Python 3.11.17/3.12.14 environments, independent optional-extra installation, eight fixture tests per runtime and actual cached-source helper preflight. The copied source subset includes the package initializer's required pipeline import. Both runtimes imported from that isolated source subset, used identical eight geometry dependency versions and returned identical Delaware/Nebraska result hashes; Nebraska had five parsed rows. All six cached source hashes were checked. No new source GET, readiness run, model request or experimental spend occurred.

This was a scoped helper verification, not a full current-tree clean installation. Initial source-copy, missing-import and macOS path-canonicalization harness failures are preserved in the evidence and its two separate failure reports. The successful check resolves both sides of source-origin containment before comparison. Product source was not changed to make the harness pass. The previously fresh isolated installations were reused for the corrected harness checks.

Independent review must assess the exact dependency/configuration/builder delta before readiness integration. Standalone source-reader acceptance does not establish final ballots, current amendments, candidate identity, geographic validity or a forecasting sample.
