# Local-only run artifacts and review packages

Some intermediate runs deliberately retain material only in the ignored local run store. Current examples are the PUMS `aggregate-local-only.json`, pending source/arithmetic/disclosure review, and E01 `candidate_rosters.local.json`. A completed checksum ledger establishes byte integrity; it does not approve redistribution.

The reproducibility builder refuses a selected run if any checked artifact name contains `-local-only.` or `.local.`, case-insensitively. This applies to owner-review bundles as well as any later release. It does not copy a partial run or silently remove the marked artifact: either action would misrepresent the complete sealed record. A refusal leaves the original run intact and creates no output archive. Ordinary metadata names such as `local-reuse-config.json` are not local-only markers.

The same markers also block enumerated source/report inputs, rather than protecting only run-store paths. Permitted evidence reports may include preserved `.txt` code/test snapshots under the named report prefixes; raw data directories remain excluded. The Wyoming projection's initial `.local.json` output is intentionally unbundled until separately reviewed finalization.

To prepare shareable evidence, preserve the original run, obtain independent disclosure review for the proposed transformation, and create a separately recorded derivative with explicit source hashes, exclusions and approved scope. Renaming the original file is not disclosure review. A derivative must retain scientifically relevant failures and uncertainty without including restricted source records or unreviewed low-support outputs. The lead must not write its own independent approval.

This guard enforces the existing marker convention, rather than discovering arbitrary sensitive contents. Raw data and credentials remain excluded by the separate package path and credential checks. No new publication permission, source permission or spending authority follows from creating a package.
