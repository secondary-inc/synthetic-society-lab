# N2b v1.1.1: required directory shape/presence remedy candidate

**Separate candidate; not independent acceptance or actual authority.** The predecessor finding is `reports/INDEPENDENT_AUDIT_E02_N2B_V1_1_OWNED_ROOT_FILE_FINDING.json`, SHA `de21ad4e051d20dadb5a8b9a2a2be4458354899cbd14ab9de6655abe915968fc`. It demonstrated that a regular file at a fixed expected historical directory could disappear from an `exists()+rglob()` inventory. All frozen v1/v1.1 modules, configs, tests, docs, reports, logs and authored bundles remain unchanged. The predecessor remains blocked; only independent review can close the finding for new exact pins.

## Minimal change

The new storage policy declares required historical directory paths and has no TEST_ONLY presence waiver. All seven original fixed historical roots must exist as directories. The already-completed WY runtime's PRIMARY, REPLAY and ledger directories, plus the acquired N2a source state11 directory, are required structural history paths too. Extra declared TEST_ONLY inventory directories are required when listed; they cannot silently vanish. Missing paths refuse before a new owner/job is created.

One no-follow directory checker uses lstat on every path component below the bound workspace. A regular file (including zero-byte), symlink/dangling link, FIFO or other non-directory at a required root or ancestor refuses before descendant enumeration. This deliberately refuses malformed roots rather than treating their bytes as a valid empty directory. The same guard applies to original storage roles and new output/registry/partition roots. Unexpected special entries inside an owned tree refuse rather than disappear from the file inventory.

The exact original output and owner namespaces remain `data/processed/e02_n2b_private_v1` and `data/processed/e02_n2b_registry_v1`. Both may be absent before first ownership; an existing output without its owner registry is refused. After registry creation, the output/core directories must remain present and valid. New DC-part, assembly-data and scratch directories may be absent before their stage uses them; if present they must be real directories. No alternate root, marker reset, history migration, retry or refund is introduced. Existing owner/output still blocks rebootstrap.

The directory checker establishes shape and presence, not semantic acceptance of historical ledger contents or current capacity. Genuine terminal-anchor/receipt/source/saved-part hashes and current inventories still need their separately scoped actual preflight/review. An empty authored directory is a topology fixture, not a genuine old-history or capacity certificate. No actual old roots, marker absence, raw source, saved parts or controls were inspected here.

## Invariants retained

Original per-root N2a raw/core+registry/shared-scratch/13MiB, WY outer base and detailed catalog/query/receipt/core/scratch/log, and all native whole/free/RSS/atomic projections remain unchanged. All old irrevocable charges and new1500seconds/65010rows/134724553expanded bytes/24Mops remain held. The full sequence must still fit before the original inherited deadlines; those are not renewed. This version contains **no prospective-window implementation or grant**.

The generic all-age parser,285/91/currentSTATE and domain validation before filtering, signed80 five-year weights, all-adult F/noncitizens/both GQ, nested C, flags/unknown masks, first PRIMARY digest and two-sweep replay, accepted WY saved-part bridge, private output gate, independent scalar/registry arithmetic, actual alternate comparator order and scoped F2 measurements remain unchanged except for version-specific import bindings. No model, API spend, network, key/.env/environment inspection, fit, national coverage or disclosure is enabled.

## Authored tests and reproduction

```sh
PYTHONPATH=src:tests .venv/bin/python -m unittest tests.test_e02_n2b_generic_v1_1_1 -v
PYTHONPATH=src:tests data/processed/toolchains/cpython-3.11.17-macos-aarch64-none/bin/python3.11 -m unittest tests.test_e02_n2b_generic_v1_1_1 -v
```

The Python3.11 path is machine-local. The suite retains all55 predecessor regression methods, with fixture-arrangement changes only where required mock directories now exist. The generator creates the same required production-relative directory layout inside an isolated TEST_ONLY root and declares it as authored topology outside production. There is no relaxation of real required paths or caps.

Additional probes cover every historical root role as a zero/one-byte and cap/cap+1 regular file, each required directory missing, nested required and listed fallback paths missing/replaced, new output/registry file shapes, all optional new partition/scratch shapes, live core/output/registry loss, full-ancestry file/symlink replacements and attempted TEST_ONLY policy waiver. Large root-file boundary probes use sparse truncate and lstat refusal; no such file is opened as a dataset. Negative preowner probes assert no new owner/output and zero source-helper calls. Existing-job shape probes restore only their deliberately corrupted authored layout and assert its original control history remains unchanged.

The initial root smoke caught one additional case in the candidate: a lost owner registry beside an existing output could still appear optional. The original failing log remains; the candidate now refuses that orphan pair. The separate owner/full-run smoke passed afterward. Final logs and exact counts are pinned in the handoff; passing implementer tests are not independent certification.

Recreate retained authored evidence using a new nonexistent root:

```sh
PYTHONPATH=src:tests .venv/bin/python -c 'from pathlib import Path; from test_e02_n2b_generic_v1_1_1 import retain_authored_evidence; print(retain_authored_evidence(Path("data/processed/e02_F_local_fixture/n2b-v1_1_1-review-reproduction")))'
```

The final indexed bundle retains seven cases: complete MOCK job, invalid child-weight failure, real authored process exit29/UNKNOWN, prior raw cap+1, variant RSS-measurement refusal, the finding's4,194,305-byte file at the N2a core root, and a missing required N2a registry root. The last two refuse before ownership/reservation/source work; their malformed authored layouts and safe metadata remain retained. No actual history files are removed or recreated. Authored input ZIPs, copied public metadata and saved-part-shaped fixtures are generation overhead outside measured new-owned partitions, not actual source work.

All resource measurements keep their v1.1 scopes: own-process sampled current RSS and real perf time, shared/unflushed runtime/cache, canonical logical payload sizes and scoped content-I/O/bookkeeping, not exclusive allocations/full syscall tracing or performance/scientific improvement. Fixture job clocks are simulated historical clocks and do not establish current production feasibility.

## Next gate

Independent code/root-shape/presence/lifecycle/arithmetic/resource/privacy review must inspect the exact new candidate and retained evidence. Actual source/private metadata/current identity/whole storage and saved-part review, finite execution authority and any separately accepted elapsed-window implementation remain absent. The inherited expired deadline still blocks actual work. No national49-state campaign/capacity, ANES fit, behavioral/human validity, dashboard adoption or publication gate is advanced.
