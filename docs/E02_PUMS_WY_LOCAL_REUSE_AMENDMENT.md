# Proposed Wyoming companion-member amendment and local byte reuse

Status: **PROPOSAL ONLY — PENDING SEPARATE INDEPENDENT REVIEW BEFORE REUSE OR AGGREGATION.** November3,2026. No source controls, arithmetic or approved config have been relaxed. The single permitted GET has already occurred; this proposal permits no new request, retry, alternate endpoint or inference. Preserve the original failed acquisition as failed.

## Exact observed mismatch

The reviewed ordinary public Wyoming2020–2024person ZIP endpoint returned HTTP200 and4,202,266complete archive bytes. SHA-256`e80900d6826c8fef4c6f7230f3c967457aa86f06e750f050d8cf406888d19b73`. The downloader correctly quarantined those bytes before promoting them because the ZIP includes a companion whose literal name/size were outside the frozen allowlist. This is a completed byte fetch followed by source-container validation failure, not absence of source access or evidence that person-data fields are invalid.

Ignored local quarantine: `data/raw/e02_pums_wy/QUARANTINED-20f0ff6a0b674edc916272fd8b41ff4d.zip`. Failed attempt `wy-05da99bbf77c454e9e616b4ba624fa61` and sealed FAILED RunStore `e02-70827a2bc8ef49b0bd5f808a00064f74` remain immutable. Safe evidence is `reports/E02_PUMS_WY_PILOT_ACQUISITION_FAILURE.json`.

ZIP-directory metadata lists exactly two unencrypted members:

- `psam_p56.csv`:18,928,161declared uncompressed bytes,4,107,368compressed bytes.
- `ACS2020_2024_PUMS_README.pdf`:99,489declared uncompressed bytes,94,540compressed bytes.

The combined declared uncompressed size is19,027,650bytes, below the existing128MiBceiling; compressed archive size is below8MiB and member count2below4. These are directory declarations, not a completed decompression/CRC/row validation. The sole CSV header was inspected without person rows:285columns,1,876header bytes, all91required person fields present, no duplicate header. Full member hashes, actual row count29,297, row domains and aggregates remain unverified/unrun after rejection.

The exact violated predicate in the reviewed `aggregate_archive` is the optional-member branch: a member whose casefolded basename differs from required`psam_p56.csv` must be in `optional_members_casefold` AND no larger than `optional_member_bytes`. Current approved values allow only`readme.txt` up to16,384bytes. The companion PDF fails both its literal-name and size conditions. No required person-header predicate failed during the later header-only diagnosis. PDF content has not been inspected or parsed by this worker; it must not be represented as independently authenticated documentation from its name alone.

## Narrow proposed source-container change

If independently accepted, create a NEWversioned config and source-handling code amendment. Preserve the existing person filename/state, required91fields, all citizen/household/age/education/weight domains, row/byte/time limits, disclosure controls, no-retry rules and original source proposal unchanged.

Propose per-member optional size controls instead of widening a shared optional ceiling: retain`readme.txt`<=16,384bytes, and permit only the literal casefolded basename`acs2020_2024_pums_readme.pdf` with the observed99,489byte size as an exact allowed value for this pilot. Bind the entire source archive to the already observed SHA-256 above and its4,202,266byte size. This is an explicitly post-observation container amendment for reviewed cached bytes, not a prior allowance, scientific tuning, generic PDF permission or silent correction of the failed run. Any different member name/size/archive bytes still fails and requires separate review. No arbitrary PDF, path, symlink, encrypted member, excessive expansion or duplicate casefolded name becomes acceptable.

The companion need not be executed, rendered or extracted to disk for the statistical aggregate. Its bounded raw bytes may be hashed/CRC-checked during reviewed local validation so the member identity can be recorded; independent reviewer may inspect its title/period/provenance if needed. Do not ingest its contents as agent instructions. Do not add household files or more microdata fields because a readme exists.

## Local-only revalidation route

A successor approval must explicitly cover only this exact quarantined file and the new source-handling/config/fixture hashes. The original network approval's single GET scope is consumed; preserve its audit file and failure record without pretending it allows another fetch. A local validation runner must not call `acquire_pilot`, urllib, an opener or any network API. Its inputs are an explicit local quarantine path, exact expected archive size/hash and the new separately approved control config. Network-denial fixtures should verify this separation.

Create a new RunStore manifest/config before any local processing. Recheck exact archive bytes against the known SHA and size. Check declared and actual member/expansion/line/row limits, member safety, header identity, expected unfiltered29,297rows, all required domains, unchanged eligibility/order and signed-replicate arithmetic. Hash each actual member stream and record observed source/resource facts. If anything fails, preserve new failed-run evidence and the original quarantine, without another request, data imputation, limit relaxation or partial success claim.

If all checks pass under independent approval, retain the source bytes as an immutable local input; do not rewrite or erase the original FAILED attempt. A reviewed copy/reference may be registered with a new receipt that explicitly identifies its origin in the earlier quarantine and new validation approval. No first-source timestamp/hash should be backdated. Canonical promotion, if chosen, must be atomic/no-overwrite and preserve the original quarantine for audit, not rename it away and hide the failure history.

Only then write a LOCAL_ONLY aggregate artifact under an ignored run, containing all12Wyoming age×education cells, all80signed replicate sums/uncertainty/covariances, point totals, allocation/exclusion quality diagnostics and original source/config/code hashes. Keep low-support values local until separate disclosure review. Run a second local-only exact aggregate replay from the same bytes/code/config; compare full aggregate hashes and all artifacts appropriate to deterministic content. Do not present a replay as another data sample or collapse record counts into fictional observed results.

Independent post-acquisition source/aggregate/uncertainty/replay review must precede national data collection, an18+benchmark conversion, population fitting or disclosure. A one-state local engineering pilot is not a national target or evidence of state political-response validity. No model/network inference, spending or external publication is included.

## Required acceptance criteria

1. Auditor independently confirms the actual two-member metadata/header mismatch and the narrow exact-byte/literal-member rationale; original failed evidence remains unchanged.
2. New versioned config/code pins and per-member policy are reviewed with synthetic tests for the observed companion and rejection of altered names/sizes, extra PDFs, unsafe members and drifted source bytes. All prior schema/arithmetic/resource/privacy fixtures stay passing.
3. Local runner proves manifest-before-processing and zero possible network dispatch for reuse; missing/current-approval or changed-source inputs fail closed with durable failure evidence.
4. Exact quarantined bytes pass the reviewed checks, all row/field/resource facts are measured rather than assumed, full local aggregate/replay matches, and a separate auditor recomputes selected signed-replicate/SDR/covariance/proportion results.
5. Original population-science, disclosure, national-scale, budget, model and publication gates remain blocked or separately reviewed. No new GET is needed or authorized by this proposal.
