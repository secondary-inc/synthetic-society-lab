# ANES release reacquisition and verification

The official [2024 Time Series study page](https://electionstudies.org/data-center/2024-time-series-study/) publicly offers the **May 19, 2026 CSV** release. Its visible link is `https://electionstudies.org/anes_timeseries_2024_csv_20260519/`. Use that normal browser download route. The mailing-list form is optional and was not used. Stop if a future route requires login, a challenge or agreement; do not guess alternate endpoints or replace the release.

An ordinary programmatic HEAD request returned403. A normal browser download of the offered link succeeded. This channel difference is recorded in `reports/ANES_UPSTREAM_ACCESS_FEASIBILITY.json` and separately reviewed in `reports/INDEPENDENT_AUDIT_ANES_PUBLIC_DOWNLOAD_SCOPE.json`. Neither a HEAD denial nor successful browser retrieval proves unrestricted automation rights.

The reacquired archive is stored locally under ignored `data/raw/anes_upstream_reacquisition/anes_timeseries_2024_csv_20260519.zip`. Its6,516,359bytes and SHA-256 `31082da127f1ebcfb1d2736ba650d52cd67a4a6ab13fbe639c2db2515779773c` match the original registered inventory. Both registered CSV and codebook members also match their exact sizes and hashes. `reports/ANES_UPSTREAM_REACQUISITION.json` records channel, time, local location and limitations; consult the separate independent review when available. No raw survey records are committed or exported.

After downloading, verify against the existing inventory without executing or extracting the archive:

```bash
.venv/bin/python - <<'PY'
import hashlib, json, zipfile
from pathlib import Path
inventory = json.loads(Path('configs/SOURCE_INVENTORY.json').read_text())
entry = next(e for e in inventory['archives']
             if e['supplied_filename'] == 'anes_timeseries_2024_csv_20260519.zip')
path = Path('data/raw/anes_upstream_reacquisition') / entry['supplied_filename']
if path.stat().st_size != entry['archive_bytes']:
    raise ValueError('Archive size differs; preserve bytes for review')
if hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() != entry['sha256']:
    raise ValueError('Archive hash differs; preserve bytes for review')
with zipfile.ZipFile(path) as archive:
    if archive.testzip():
        raise ValueError('ZIP CRC failure')
    for member in entry['members']:
        info = archive.getinfo(member['name'])
        if info.file_size != member['bytes']:
            raise ValueError('Registered member size differs')
        if hashlib.sha256(archive.read(info)).hexdigest() != member['sha256']:
            raise ValueError('Registered member hash differs')
print('PASS exact archive and registered member bytes; no scientific acceptance inferred')
PY
```

This documents one release's ordinary manual acquisition and reproducible byte verification. It is not an automated upstream downloader or proof of complete source-inventory reconstruction. Browser HTTP headers and redirect chain were not exposed and are not inferred. The size check occurs after download, rather than imposing a network byte ceiling. Existing source copies and frozen runs remain unchanged on drift.

To restore just this registered archive and its two members into their canonical locations, first plan and then apply an explicit subset:

```bash
.venv/bin/civiclab restore-inputs --from data/raw/anes_upstream_reacquisition --only anes_timeseries_2024_csv_20260519.zip
.venv/bin/civiclab restore-inputs --from data/raw/anes_upstream_reacquisition --only anes_timeseries_2024_csv_20260519.zip --apply
```

`PASS_SELECTED_LOCAL_RESTORE` covers only the named source. Unknown, ambiguous, duplicate or empty selections fail before writes; mismatched existing files remain blocked without overwrite. Omitting `--only` retains full-inventory behavior. The lead isolated-workspace execution and exact replay are recorded in `reports/ANES_SELECTED_RESTORE_LEAD.json`, pending independent review.

The [ANES FAQ](https://electionstudies.org/faq/) also cautions against treating its sample as representative at state or smaller geographies. State-stratified synthetic engineering cannot establish state-level political response validity. Adult/state goals remain explicit research requirements with these limitations, rather than achieved through calibration labels.
