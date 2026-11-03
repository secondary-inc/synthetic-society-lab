# Full-adult F engine v1 — authored implementation candidate

This is an implementation submission for independent review, not an accepted research milestone. It implements the separately reviewed U1 v1.1 specification (`docs/E02_FULL_ADULT_BENCHMARK_U1_SPEC_V1_1.md`, SHA-256 `90759d9e9718b98703d2a9d0353dad3a25b426311fa29fc70e6e630db6d4a2d2`; config SHA-256 `3d71a83dc88d3f0622ec4db536030ab0f42ff46520659e514853eb00be813fdf`). The frozen specification's original NOT_RUN statements describe its issuance date; new execution evidence is in `reports/E02_FULL_ADULT_ENGINE_V1_EVIDENCE.json`. No historical specification, N1 implementation or independent finding is rewritten.

F includes adults represented in the 2020–2024 five-year PUMS across 50 states/DC, including noncitizens and institutional/noninstitutional group quarters. C is the nested citizen-household slice. The implementation preserves 3,672 domain cells and 293,760 signed replicate components. Unprocessed source cells decode to NULL; a processed sample zero remains a recorded sample zero. C is never added to F. Political priors remain NOT_IDENTIFIED_BY_PUMS, including inside C: the demographic benchmark does not identify state party preferences or human treatment effects.

## Components and execution boundary

Seven new modules own scoped types/schema validation, artifact controls, streaming adult extraction, uncertainty/query math, durable query accounting, binary/source binding, and fixture coordination. Read-only N1 source-inspection, ledger and sampled-supervisor primitives are reused; their older C-only acceptance confers no F approval. The new config pins these dependencies, the seven F modules, the tests and the accepted U1 inputs. Its person controls describe F rather than inheriting the older C exclusion policy.

`load_engine(repository_root)` verifies frozen file hashes and null actual approvals. The checked-in engine config has `authored_fixture=false`, no fixture root, zero actual authority, and null source/parse/fit approvals. The test driver creates a separate explicitly marked MOCK workspace with authored source URLs, fixture counts and bytes. Actual source paths, real transport, Wyoming-cache reuse, political target conversion, fits and disclosure have no enabled entry point. The standalone `actual_source()` refuses before opening its argument. These controls define the supported API boundary; arbitrary edits to trusted code/configuration are outside its integrity model.

`FullAdultFixtureEngine` serializes phases with a shared file lock, freezes query inputs before parsing, enrolls and processes PRIMARY/REPLAY sources, seals both benchmarks, binds a common execution manifest, and runs selected queries. Source and query ledgers retain their distinct histories. A pending/torn/failed attempt blocks further work; it cannot reset a quota. Full unknown/failure reservations remain charged. Query results are assembled only from committed pending payloads or typed NULL failure records. Successful result-byte refunds require a durable length/hash proof; arithmetic charges never receive a success/replay/cache discount.

## Reproduction

Use the project's existing Python 3.12 virtual environment; no additional dependency was installed for this submission.

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest discover -s tests -p test_e02_full_adult_v1.py -v
PYTHONPATH=src:tests .venv/bin/python -m unittest discover -s tests -p 'test_e02*.py' -v
```

Create a new ignored workspace for a retained full-shape authored run. The destination must be new; do not overwrite an existing run.

```sh
PYTHONPATH=src:tests .venv/bin/python -c "from test_e02_full_adult_v1 import record_authored_run; record_authored_run('data/processed/e02_F_authored/F-mock-v1-NEW-ID')"
```

The driver blocks socket connections, generates 51 authored ZIPs with 285 columns, 72 adult and six child rows each, and records a fixture receipt, hashes and sampled child resource observations. The generated records are fictional test values. There are no respondent records, external model calls or fits. The toy count/variance/covariance values are arithmetic oracles, not population estimates or information-treatment effects.

The driver preserves inputs, catalogs, arrays, operational ledgers, committed pending query payloads, result indexes and canonical result JSONL. The two sweeps' primitive bytes and query-result bytes must match; clocks, receipt histories and source operational identities need not. Its artifact hash index describes the completed file set before the index itself; the report separately pins the index. A preliminary run with the earlier inherited metadata config remains preserved and is distinguished from the final scoped-config run.

## Acceptance criteria and current scope

The implementation suite exercises F01–F20 themes. It checks six-domain/all-age arithmetic; 51-state conservation and same-index national variance; exact source/replay partitions; all specified age/education recode boundaries across all CIT/RELSHIPP values; bad child fields before selection; NULL masks and released zeros; exact binary layout; checked int64 inputs and Python big-integer quadratic oracles; signed covariance versus nonnegative contrast variance; typed blocked denominator intervals; intentional 64-million-unit plan refusal; source/query counter corruption; real child death at journal boundaries; reservation races; clock rollback/expiry; low-disk checkpoints; BODY failure charges; source drift; sampled RSS/time/cancellation; all artifact partitions; closed catalog vocabulary, strict JSON, canonical decimals, hashes and actual-source refusal.

Acceptance requires a reviewer separate from the implementer to rerun the exact pinned code/tests, independently probe source/parser/math/ledger and storage boundaries, examine the retained successful and refused runs, and record PASS/BLOCKED/NOT_RUN. Test method names group multiple fixtures; 18 passing unit methods do not by themselves certify all adversarial permutations in the specification. The reused archive inspector/transport have existing N1 adversarial tests, but their independent F review remains necessary. The production adapter, actual F acquisition/reuse, actual arithmetic/resource validation, disclosure and population fitting remain separate blocked milestones.

## Resource semantics and limitations

The plan reserves six million mandatory logical units per sweep and exact declared selector/coefficient/query costs against a combined 64-million-unit cap. These are reference-algorithm accounting units, not CPU instruction counts. A deliberately wide plan is refused after charged catalog compilation and before source parsing/query evaluation; its input, failed state and refusal are retained. Storage checks cover separate base/catalog/query partitions, both sweeps, core/receipt logs, scratch and raw archives, projected writes/atomic headroom and current free space. The 128 MiB data/log envelope excludes separately capped raw/scratch storage, as specified.

Parent polling samples child RSS and stops process groups on observed threshold/deadline/cancellation. It does not impose an absolute OS RSS, wire-byte, physical-block or wall-clock bound. Samples may miss short peaks; a zero RSS observation is not proof of zero usage. Catalog compilation and validation/serialization remain bounded by vocabulary, byte quotas and elapsed checks rather than a separate absolute OS sandbox. The retained full-shape fixture is 3,978 rows per sweep, not a 16-million-row national performance demonstration. Larger inputs may hit independent limits earlier; no limits increase or maximum-throughput guarantee follows.

The standard-library validator implements only the closed keywords used by the pinned primitive and result contracts, plus explicit finite/canonical-decimal/equation/hash/source-key/mask/counter checks. It refuses unsupported schema keywords. No general JSON Schema engine, conformance suite or external schema package is claimed. Internal SHA chains detect inconsistent/torn/resealed-counter histories under the documented trusted-code model; they are not external authentication against coordinated rewriting of every trusted anchor.

All actual demographic cells/replicates and potential sparse query outputs require new F-specific disclosure approval; a support threshold is not release permission. ANES does not cover every F domain and does not establish representative state political priors. No party values, human persuasion claims, new estimand, confirmatory hypothesis, model release, cost authorization or publication permission is created here. Actual inference/source spend is zero; local compute and development-assistant usage are unpriced.
