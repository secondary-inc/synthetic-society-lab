# Production admission v4 candidate

This is an implementation handoff for independent review. It grants no real
owner bootstrap, human approval, credential access, model selection or spending.
All positive execution evidence uses authored catalogs, simulated external
assertions, mocked OS-account homes and stub credentials. The actual account
namespace and environment credentials were not inspected.

Three new modules implement the separately reviewed methods proposal:

- `production_price_v4.py` validates complete text-price interpretations and
  conservative per-route component bounds, checks fresh metadata for a new
  dispatch, and preserves historical quote mathematics after expiry. Missing
  prices require explicit external interpretations. Four input components are
  summed, output and reasoning are summed, then the maximum across permitted
  route-family members is used. Each request rounds upward independently to
  microdollars in a pinned Decimal context. Ignored discounts are conservative;
  disabled nontext services, cache and reasoning applicability still require
  reviewed evidence. Free/all-zero reservations are currently unsupported.
- `production_owner_v4.py` uses a fixed OS-account namespace, an outside-store
  create-once registration and initially zero allowance. Explicit externally
  supplied approvals bind the exact released request, predecessor and absolute
  lifetime money and dispatch ceilings. Reservations, uncertain charges,
  generation identities, unfinished phases and counters survive renewal.
  Missing or torn protected state refuses rather than recreates. A protected
  metadata-proof event prevents editing a prepared object's timestamp into
  freshness. Exact phase checkpoints and one retained statistics intent are
  required. Late accounting retains original authority and honest clock-error
  metadata; new operations refuse on invalid time.
- `production_admission_v4.py` derives a single nonpolitical JSON compatibility
  request using `max_completion_tokens`, no tools/plugins/BYOK, no fallback and
  no inference retry. It checks exact released source/request hashes and
  external operator assertions before resolving owner state or reading a key.
  Its fixed unauthenticated catalog GET validates framing, response size and
  cooperative elapsed time, closes resources and never retries. All tests of
  this collector use HTTPS stubs. No native call through this new collector has
  been made. Preparation persists price proof but does not reserve money until
  the explicit reservation. A missing key may therefore leave a price-proof
  event, with zero dispatches or charge.

The conditional positive preparation path works under isolated authored tests.
`run_live_compatibility` still refuses because authenticated model transport,
actual response reconciliation and the recorded compatibility executor are a
separate future integration milestone. Prepared credentials are opaque/redacted,
kept in memory and never written to the raw example. No paid runner is claimed.

External review and operator assertion hashes are trusted workflow inputs. They
do not authenticate a human merely through a kind string, hash or role field.
The agent must never generate real affirmative owner authority. Protected local
registration/history/head and reviewed Python execution are trusted; arbitrary
same-process code execution, coordinated replacement of all authority, hostile
host control and external immutable timestamps are outside the boundary.
No daemon, HMAC service or impossible always-writable failure marker is required.
Process crashes can leave uncertain/torn state that refuses and retains charges;
this is not automatic recovery or a power-loss/directory-fsync guarantee.

The request's provider policy denotes a family or endpoint prefix, not physical
region, hardware or revision identity. Seed determinism is unproven. Credit
purchases, taxes, account fees and development costs are separate and unpriced.
No actual price interpretation, real source contract, model/provider release,
dedicated rotated key, owner bootstrap or affirmative paid approval exists.
These controls are not acceptance of E02 population fitting or E01 forecasting.

## Reproduction and evidence

Run from the checkout with `PYTHONPATH=src:tests`:

```
.venv/bin/python -m unittest test_production_admission_v4 test_production_price_v4 -q
data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11 -m unittest test_production_admission_v4 test_production_price_v4 -q
.venv/bin/python scripts/record_production_admission_v4_fixture.py --directory data/processed/fixture_scopes/production-admission-v4-NEW
```

The recorder requires a fresh child directory of the checkout fixture scopes.
It patches the private OS-home/clock/catalog/key boundaries, and imports only
authored test helpers. It offers no production path or authority option. The
retained example has two exact requests across two simulated external epochs,
two microdollars of simulated settled charge and six zero-key-read/unchanged-
history refusals. Its fake key is not persisted. The example is private and is
not added to the viewer, source inventory or reproducibility export.

`reports/SURVEY_PRODUCTION_ADMISSION_V4_CANDIDATE.json` records exact file pins,
24 new targeted tests on each supported Python version, the combined139-test
regression execution, retained raw hashes and three corrected harness failures.
Tests include six real child-process exit boundaries and a two-process one-
reservation race. They do not demonstrate actual provider/TLS behavior, large-
history scalability, actual OS-account state or an authorized live experiment.
Independent code, raw-history and credential-gating review remains pending.
