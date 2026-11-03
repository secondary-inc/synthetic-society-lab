# E02 N2a: exact one-DC-unit actual launch recipe

**Recipe only; no release, admission, registry, source access or execution created by this document.** The frozen collector/default configuration and its independent methods gate remain unchanged. The genuine independent code review is `reports/INDEPENDENT_AUDIT_E02_N2A_COLLECTOR_V1_CODE_RAW.json`, SHA-256 `fd3aef35f9d5664b721ac9b8c50ab15a371425e5aadc558dbd402fb33c8d8d03` (9,523 bytes). It accepts exact code/authored controls only; actual-source finite release and particular metadata review remain separate requirements stated in that audit. This document is neither a new methods/code gate nor authority. The lead owns the particular finite release and actual execution after genuine code PASS.

## Exact bindings from the frozen code

Working root: `/Users/joshua/Documents/ChatGPT/synthetic-society-lab`. Active state is the string `11`; realm is `PRODUCTION`. The sole URL is `https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year/csv_pdc.zip`. The complete DC descriptor is selected from `complete_public_metadata.states` in the pinned reconstruction, not reconstructed from assumed fields or edited to claim acquisition. Its first hash, exact archive size and literal member manifest are null. Published 32,505 person rows, rounded 4.5M and index dates are historical metadata, not observed current DC bytes/adults or an availability guarantee.

Canonical hashing is SHA-256 of UTF-8 `json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)`. Policy is the entire disabled config excluding only `execution_authority`, `live_refs`, `active_state`. Its exact hash is `b4cf8cd839dff28be1dc11641aa803f8aa8bd6be52b93fa09b1d7531dd5d53c5`. Design is the canonical object with `policy_sha256`, `active_state`, full unmodified `source`, `realm`, `root`; this root/DC design hashes to `b1e80a80123226821da99a2070f16763bde28ff7c00f3a58dbc3d45e54c2fa8c`. Relocation changes design and needs its own exact release; changing policy/code invalidates these pins.

`_load` directly validates these genuine review fields, allowing additional audit narrative without relying on a field count:

- `status`: `PASS_N2A_COLLECTOR_CODE_AUTHORED_FIXTURES`.
- `auditor_role`: `independent_auditor`; `realm`: `PRODUCTION`.
- `policy_sha256`: exact policy hash above.
- `files`: exact mapping from the frozen config, including collector, adapter, test, imported primitives/package initializers and methods audit.
- `reviewed_states`: contains string `11`.

The review is authored and issued by the independent auditor. Neither a worker test report nor the methods-only audit substitutes for it. The lead must check all material independent findings, not just fabricate the admission-shaped fields. Each reference is exactly `{'path': repository_relative_path, 'sha256': exact_file_bytes_hash}`. `_record` admits only the repository metadata/code path domains, rejects symlinks and applies its bounded file read/hash. Review and release content may have narrative fields; the reference objects are closed.

The finite release fields validated by `_load` are `status`, `issuer_role`, `realm`, `design_sha256`, `code_review_sha256`, `scope`, `limits`, `owner_research_authorization_reference`, `not_before`, `expires`. Their values and exact scope are in the executable example below. The nonempty authorization reference cites the existing owner ordinary-public-Census research scope; it does not require a new owner/key gate or imply inference/publication permission. The lead issues finite actual timestamps; no backdating. Release validity is rechecked per use, so choose a finite window that covers preparation and the whole 900-second unit with safe closure margin. Window length does not extend the unit or native clocks. If authority expires during work, retain the original record/bytes and stop; never edit or refresh it silently to resume.

## Executable lead sequence after genuine code PASS

The following is an executable example **to be run once by the lead after review**. It has not been executed by the recipe worker. The genuine independent-review path/hash are fixed below; the sole argument is a nonempty existing owner-research-scope reference. The lead completes the existing particular-source metadata/release review before invoking it. No credential is requested. The public release record is exclusive-create, never overwrite. `live` stays in memory; the checked-in disabled config remains untouched. Calling `collect(live)` is the one actual operation; it performs its own admission, original registry bootstrap and dispatch. Do not call a fixture helper, manually bootstrap a registry, separately call internal `_collect`, substitute transport or wrap this in a retry loop.

```sh
PYTHONPATH=src .venv/bin/python - EXISTING_OWNER_RESEARCH_SCOPE_REFERENCE <<'PY'
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from civiclab.common import canonical_hash
from civiclab.e02.n2a_collector_v1 import collect
from civiclab.e02.national_budget import Blocked

root = Path('/Users/joshua/Documents/ChatGPT/synthetic-society-lab')
assert Path.cwd() == root
owner_ref, = sys.argv[1:]
review_name = 'reports/INDEPENDENT_AUDIT_E02_N2A_COLLECTOR_V1_CODE_RAW.json'
review_hash = 'fd3aef35f9d5664b721ac9b8c50ab15a371425e5aadc558dbd402fb33c8d8d03'
assert owner_ref.strip()
base = json.loads((root / 'configs/e02_n2a_dc_collector_v1.json').read_text())
assert base['execution_authority'] == 0
assert base['live_refs'] == {'code_review': None, 'release': None}
assert base['realm'] == 'PRODUCTION' and base['active_state'] == '11'
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha((root / 'configs/e02_n2a_dc_collector_v1.json').read_bytes()) == '4ce01dbb19732b52516e4623632b473df46389a05226a7d0475bda49147cdaf8'
review_path = Path(review_name)
assert not review_path.is_absolute() and '..' not in review_path.parts
assert review_path.parts[0] == 'reports'
review_bytes = (root / review_path).read_bytes()
assert sha(review_bytes) == review_hash
review = json.loads(review_bytes)
policy = {k: v for k, v in base.items() if k not in ('execution_authority', 'live_refs', 'active_state')}
P = canonical_hash(policy)
assert P == 'b4cf8cd839dff28be1dc11641aa803f8aa8bd6be52b93fa09b1d7531dd5d53c5'
assert review['status'] == 'PASS_N2A_COLLECTOR_CODE_AUTHORED_FIXTURES'
assert review['auditor_role'] == 'independent_auditor'
assert review['realm'] == 'PRODUCTION'
assert review['policy_sha256'] == P and review['files'] == base['files']
assert '11' in review['reviewed_states']
# These are public repository files only. No source/cache path is touched here.
for name, expected in base['files'].items():
    assert sha((root / name).read_bytes()) == expected, name
registry_ref = base['registry_reference']
registry_bytes = (root / registry_ref['path']).read_bytes()
assert sha(registry_bytes) == registry_ref['sha256']
source = next(s for s in json.loads(registry_bytes)['complete_public_metadata']['states'] if s['state_fips'] == '11')
assert source['url'] == 'https://www2.census.gov/programs-surveys/acs/data/pums/2024/5-Year/csv_pdc.zip'
D = canonical_hash({'policy_sha256': P, 'active_state': '11', 'source': source, 'realm': 'PRODUCTION', 'root': str(root)})
assert D == 'b1e80a80123226821da99a2070f16763bde28ff7c00f3a58dbc3d45e54c2fa8c'
now = time.time()
release = {
    'status': 'RELEASE_N2A_ONE_ORDINARY_PUBLIC_SOURCE_GET',
    'issuer_role': 'lead', 'realm': 'PRODUCTION',
    'design_sha256': D, 'code_review_sha256': review_hash,
    'scope': {'root': str(root), 'state': '11', 'url': source['url'],
              'GETs': 1, 'HEADs': 0, 'redirects': 0, 'retries': 0,
              'person_rows': 0, 'model_calls': 0, 'fit': False, 'disclosure': False},
    'limits': base['unit_limits'],
    'owner_research_authorization_reference': owner_ref,
    'not_before': now, 'expires': now + 1800,
}
assert math.isfinite(release['not_before']) and math.isfinite(release['expires'])
release_name = 'reports/E02_N2A_DC_FINITE_RELEASE_v1.json'
release_blob = (json.dumps(release, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
with (root / release_name).open('xb') as stream:
    stream.write(release_blob)
    stream.flush()
    os.fsync(stream.fileno())
live = deepcopy(base)
live['execution_authority'] = 1
live['live_refs'] = {
    'code_review': {'path': str(review_path), 'sha256': review_hash},
    'release': {'path': release_name, 'sha256': sha(release_blob)},
}
# Single call. Any refusal/failure is terminal for this launch recipe.
try:
    receipt = collect(live)
except Blocked:
    print('STOPPED: retain original registry, charges and bytes; no retry or reset.')
    raise SystemExit(1)
else:
    print(receipt['status'])  # Metadata closure only; no import/fit/science claim.
PY
```

The example's 1,800-second finite issuance window is preparation/closure margin, not a new source cap. The only actual unit still has 900 seconds from registry creation. The example does not authenticate the lead or independent auditor cryptographically: it runs under the declared trusted local history/writer boundary. Full trusted-store replacement is outside the collector's claim.

## Original registry, time and history

`collect` admits the supplied live config, then initializes `Registry(context, create=not registry_root.exists())`. Its fixed roots are `data/processed/e02_n2a_registry_v1`, `data/processed/e02_n2a_core_v1`, `data/raw/e02_n2a_sources_v1`; the recipe worker has not inspected their existence. First bootstrap refuses any preexisting registry/raw/core root when creation was requested. Partial bootstrap remnants cannot be deleted/recreated to reset history. Existing registry reuse semantically replays its original markers, policy binding and events; duplicate/pending source attempts refuse. Do not manually create empty directories before launch.

Genesis `created` has both wall and monotonic readings and anchors the first unit's `started`. It is the 900-second t0, not the release timestamp, GET timestamp or later process start. The first reservation refuses elapsed >=900 seconds; `_guard` and completion use the same start. Delayed preflight, failure, restart, expired release, an extra process or a new root cannot restart that unit. Clock rollback/discontinuity refuses. Existing native batch horizon is 10,800 seconds from original N2a registry creation for additional reservation admission; this one-unit recipe uses the stricter first900-second deadline throughout. It does not reset/revive the earlier completed Wyoming job's original clock or authorize a later campaign.

Before DISPATCH, RESERVE persists one GET, 8,388,608 body bytes, 180 network seconds, 300 processing seconds. The original history retains prior WY GET1, metadata requests5, metadata received1,279,577 bytes, WY retained4,202,266 bytes, prior person-body allowance8,388,608 bytes and `prior_charges_refunded: false`. That allowance is conservative historical reservation, not observed old delivery. New first-unit body accounting is 8,388,608 + 8,388,608 + 1,279,577 = 18,056,793 bytes against native body cap; unique-source conservative sum is 8,388,608 + 4,202,266 = 12,590,874. These values are not read from/revalidated against old raw files. Prior GET/metadata counts remain explicit provenance; native `requests:50` limits the newly registered non-WY attempts. The implementation does not subtract old requests twice or refund failures.

New reservations accumulate against unchanged native body3GiB, unique3GiB, new requests50, network7,200seconds, processing3,600seconds. Full new allowances remain reserved for completed/failed/unknown attempts, so12x300-second processing reservations would exhaust that future sequence. Fixed shared raw/core caps can stop it sooner. No national throughput, migration/reconciliation or campaign authority is claimed.

## Caps, completion and terminal stop

The complete unit-limit object is copied verbatim into the requirements record and eventual release. Principal limits: one worker/GET, no HEAD/redirect/retry/Range, application/raw8MiB, core4MiB, scratch1MiB, total13MiB, network180seconds, individual socket30seconds, metadata300seconds, total900seconds, sampled RSS512MiB, targetpoll0.1seconds, header64KiB, declared person64MiB/companion2MiB/combined66MiB, expanded metadata reservation6,356,992bytes, person rows0 and analysis operations0. Native initial free5,771,362,304bytes and continuous free1GiB plus atomic headroom apply. Every owned file, unexpected path, hardlink and temporary projection counts. No duplicate raw promotion copy: exclusive no-follow creation, fresh compressed hash/full lexical identity, same-directory rename and final identity.

GET uses verified TLS and identity encoding; final URL must equal exact requested URL. HTTP errors/redirect/encoding/type refusals do not read an error body. Allowed metadata headers are date, last-modified, content-length, content-type, content-encoding, etag, each bounded. Reads are <=64KiB and remaining allowance; delivered bytes are persisted before writing and before refusing a late read. Received may exceed written after interruption; keep both lower bounds and full charges. Missing Content-Length can succeed at observed EOF below cap. Unknown EOF-atcap refuses without an extra probe; exactly known length atcap can close. Truncation/overlong, unsupported layout/schema, identity changes, limits, cancellation and unknown shutdown stop. No alternate endpoint, changed headers, retry, resume, deletion or new-root workaround follows.

Checks sample cooperatively between blocking operations. They do not prove absolute stop latency, instantaneous RSS containment, wire-byte caps or cleanup after parent death. A completed receipt may exist before a late guard causes registry FAILED; authoritative event/state history takes precedence over an earlier receipt. A process death may leave PENDING with no failure record. Missing evidence stays unknown, not successful cleanup. `Registry.unknown()` is a **mutating** explicit recovery operation requiring valid admission, not part of this recipe or read-only audit; lead must coordinate any such bookkeeping without creating a second attempt or refreshing authority silently.

Only compressed archive bytes, exact central membership, header285 unique/91 required fields and bounded companion bytes/CRC are inspected. Planned DC names (`psam_p11.csv`, `ACS2020_2024_PUMS_README.pdf`) are not observed facts. Header-reference equality is recorded; unrecognized contents do not permit changing frozen code. No person ZipExtFile/full CRC/person rows/STATE-value validation/PDF execution occurs. Success is exactly `ACQUIRED_METADATA_VALIDATED_NOT_PERSON_IMPORTED`; `import_admitted` remains false.

## Read-only post-run evidence and independent audit

After the one operation, preserve the fixed roots and public release/review/config/code pins. Future independent access must be scoped separately to this DC metadata-only unit; this recipe issues no raw inspection authority. Audit surfaces are source paths described by code, not claims those paths now exist:

- Registry `genesis.json`, `ORIGINAL`, `policy-binding.local.json`, `events.jsonl`, `state.json` and any `CANCEL_11` marker: immutable original t0/history, sequence/hash chain, semantic event replay, one source/attempt, full allowances, received/written counters, dispatch intent, completion or failure/unknown. `.lock` is control state. Do not call `Registry(...)`, `snapshot()`, `unknown()` or any other live API as a purported read-only audit; lock acquisition opens the lock file in append mode and unknown mutates events.
- Core `11/attempt-binding.local.json`, optional `11/receipt.local.json`, optional `11/failure.local.json`: exact code/policy/source/review/release binding, clocks/HTTP metadata, receipt hash referenced by COMPLETE, metadata-only flags, safe failure type and lower bounds. Failures can prevent any core record; absence alone does not prove no GET.
- Raw `11/csv_pdc.zip.part` and/or `11/csv_pdc.zip`: preserve either/both as observed, never delete/quarantine by moving outside counted roots. Under later explicit metadata-only inspection scope, bounded no-follow hash/size/identity and header/companion checks may be rederived without person scan. Do not run generic ZIP CRC/testzip, extractall or row readers.

A reviewer can read saved bytes and independently reconstruct the chain without live collector entry points. Record exact code/config/review/release hashes, original t0, measured clocks/resources, application delivery and retained files, exclusion/error status and limitations. Exclude credentials/raw payloads/person contents from Git/public reports/external tools. A private receipt is not dashboard/disclosure permission. Retain failure/unknown configurations with full allowances. Later N2b import, fitting, matched comparisons, national coverage, human effects and publication remain separately gated.
