# Shared research infrastructure

## Acceptance and execution sequence

`configs/milestones.json` declares dependencies and acceptance criteria. F0 must pass before module integrations. E02A covers exploratory population/instrument engineering, E02B covers the mocked pilot, E01A covers retrospective baseline engineering, and D0 covers the recorded-run viewer. Real research readiness remains separate from these engineering milestones. E03/E04 cannot execute merely because their namespace exists.

Offline CI installs the project on Python 3.11/3.12, runs unittest discovery and verifies the versioned GDELT fixture. The local full-source check additionally requires private/local acquired data. Missing or changed files return BLOCKED and a nonzero exit code. A byte checksum is not a source-authenticity, licensing or historical-cutoff certificate.

## Run artifacts and checkpoints

`RunStore` writes manifests, source fingerprints, Python/platform records, append-only event sequences, immutable result files and a final checksum ledger. Atomic writes flush files before replacement. A POSIX nonblocking lock prevents simultaneous writers/resumers. Run UUIDs/timestamps distinguish execution instances; the experiment configuration and deterministic response hashes support reproducibility. Source fingerprinting excludes credentials and raw data; input bytes have their own hashes. These are local integrity controls, not immutable external publication receipts.

SQLite jobs have deterministic payload IDs, randomized-assignment priority, transactional claims and durable DONE results. Re-adding a task is idempotent. A crashed RUNNING task is not automatically replayed, because a remote request might already have been billed. Explicit recovery quarantines it as NEEDS_RECONCILIATION. Resume verifies code/config. Reconciliation tooling for actually billed interrupted requests is not yet provided; paid pilots are disabled.

## OpenRouter and budget accounting

`civiclab.model` exposes a text-only, fixed-model/fixed-provider nonstreaming adapter. It has no automatic dotenv loading, retry, provider fallback, tools, plugins or model substitution. Network dispatch defaults to denied by `Policy()` and needs an explicit human-approved configuration. The offline experiment CLI cannot invoke paid inference.

Verified provider pricing must be positive, official-source-referenced and no older than 24 hours. Reserve a conservative byte-based input bound plus per-message framing and the configured output ceiling before dispatch. Send provider-only routing, no fallbacks, required parameter support and max-price constraints. Actual native token counts and reported cost are checked afterward. Unknown/invalid prices, routing changes, missing usage and exhausted budgets block. Pricing evidence is supplied to the adapter by the operator; live metadata acquisition/authentication is not implemented, so no live cost quote or provider verification is claimed.

The SQLite ledger uses integer micro-USD amounts with ceiling rounding and BEGIN IMMEDIATE to enforce total/module caps across concurrent callers and restarts sharing that ledger. Pending reservations consume caps. Unknown billing retains the full reservation and halts execution. Known reported charges are preserved even if JSON parsing or routing validation later fails; an overrun is recorded and halts further dispatch. Client limits cannot reverse an unexpected provider charge. Dedicated provider/account-side caps remain advisable for an authorized real pilot; no external account settings have been changed.

Receipt metadata includes model/provider, request hash, seed, token ceilings, pricing date/rates, approval ID, actual completion ID, native usage and error type. API keys and private reasoning are not logged. The adapter returns structured content and usage for a future approved runner to persist; current E02 execution uses a deterministic mock with full request/response logs. Tests use fake keys and injected transports exclusively.

## Earned complexity and deferred research

`compare_gate` checks matched evaluation units, outcome, split, cutoff, instrument, run status and artifact reference; equal token budgets can be required. This only establishes comparison eligibility, not improvement or publication validity. No advanced configuration is automatically promoted. Scientific adoption also requires prespecified validation evidence of incremental value; that evidence does not exist yet. E02's recorded advanced gates remain BLOCKED/NOT_RUN, with scripted assistant fixtures explicitly distinguished from live assistants.

E01 sends only allowlisted historical features into a predictor child process and introduces outcomes only in a separate evaluator after prediction hashing. The worker uses an empty temporary directory and stripped environment; after trusted imports a tested Python audit hook denies file/network/process I/O. These are controls for trusted code, not an adversarial OS sandbox, and cannot prove that an operator never saw an outcome. REAL execution remains denied until manifest/history/aggregation controls are wired to verified real evidence.

## Local dashboard

Only completed checksum-verified runs can be exported. The viewer includes summaries, uncertainty, source provenance and fictional-response replay; individual ANES rows and credentials are never exported. E02 replay shows the recorded C1/C2 pair. E01 counterfactuals come from predeclared saved S0 outputs on identical DEMO races, not an interactive unexecuted model forecast. The preview server binds to loopback and permits only index.html and snapshot.json. Browser QA checked the warning labels, E02 pair display and E01 counterfactual view. No hosted deployment was requested or performed.

## External references consulted

- https://openrouter.ai/docs/api_reference/overview
- https://openrouter.ai/docs/guides/routing/provider-selection
- https://openrouter.ai/docs/cookbook/administration/usage-accounting

Runtime inference was not used to consult these public documentation pages.
