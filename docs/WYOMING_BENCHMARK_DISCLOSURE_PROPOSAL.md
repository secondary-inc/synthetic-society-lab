# Wyoming demographic benchmark derivative: disclosure proposal

Status: methods proposal only. No derivative, redistribution or external publication is authorized by this file. Original nationwide adult/state and political-response validity requirements remain incomplete.

The independently checked local aggregate is in run `e02-08feb38db25d4f49a7b9886ee2a692b9`, replay `e02-9fa6be30b51b4fb6a90ff68ecf2edc33`. Its file hash is `868d66c2ec727e3668b10962c38d7bfd70964fcee788b93739fbf3ef69e2b72b`; canonical aggregate hash is `e186900121fa65426fc926d358d4e3de33d578c51cb5bd25d422c416f420718d`. Exact source/arithmetic acceptance is recorded separately in `reports/INDEPENDENT_AUDIT_E02_PUMS_WY_ACTUAL.json`. The full aggregate remains local-only.

Proposed owner-review derivative: a new sealed run containing only the following fixed projection of the twelve predefined age-by-education cells for Wyoming household citizens18+, ACS2020–2024 five-year PUMS:

- Cell label, raw contributing sample count, point person-weight count, point share, and scalar count/share uncertainty objects restricted to variance, standard error,90% margin of error and status.
- State, source period, explicit household/citizen/age universe, total unfiltered person rows, and the sum of approved cell point counts.
- File-level source/member/header hashes, original run/aggregate/checksum identities, exact projection code/config/approval hashes, and bounded source/resource provenance.
- Explicit limits: sampling approximation conditional on the PUMS release; not ANES transport uncertainty, a political-effect estimate, a national population or a fitted synthetic population.

No person records, household/respondent/cluster identifiers, source row positions, party or attitude answers, contact fields,80-replicate vectors,144-entry covariance matrix, allocation counts or small exclusion counts enter the derivative. Do not copy the source object and delete selected keys; construct the output from a literal whitelist and validate the complete output schema.

Admission requires all twelve cells to have at least30 unweighted contributors, no low-support flag, finite valid point/share/scalar uncertainty values, and the reviewed conditional-error status. If any cell fails, emit no cell-valued derivative. A future suppression/complementary-suppression policy would need separate review; do not tune thresholds or selectively remove unfavorable cells. The threshold is an engineering disclosure convention, not an anonymity or differential-privacy guarantee. Exact point totals are included only if all twelve cells pass, preventing recovery of a suppressed cell from a published total.

Sequence: independent methods review of this proposal; isolated projection implementation and synthetic fixtures; fresh code/schema/fixture approval bound to exact source and projection design; then one local derivative and exact replay, followed by independent output/disclosure verification. The RunStore manifest must precede approved source processing and use only admitted safe metadata; errors preserve type-only failed evidence. Recheck source artifact/ledger identities before and after projection, preserve the original local run, and refuse unexpected fields or source drift.

Only the separately accepted derivative could enter an owner-review reproducibility pack or dashboard. Renaming the original local-only artifact is insufficient. No network acquisition, national scaling, calibration/fitting, paid inference, public deployment or external publication follows from this proposal.
