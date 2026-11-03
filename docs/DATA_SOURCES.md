# Registered research inputs

The machine-readable inventory is [SOURCE_INVENTORY.json](../configs/SOURCE_INVENTORY.json). It records archive and extracted-member SHA-256 hashes, file sizes, CSV columns and record counts. Raw downloads and extracted files are local under `data/raw/`, excluded from Git; this commit does not redistribute ANES respondent records or the large election tables.

## Received from the user

- ANES 2024 May 19, 2026 release: 5,521 CSV records and the user guide/codebook PDF. The separate questionnaire was not included in this ZIP. Survey weights, missing-value codes and substantive mappings have not yet been validated.
- MEDSL 2024 House precinct returns: 1,177,213 CSV records, README and codebook. `dataverse_files (1).zip` has identical extracted contents to `dataverse_files.zip`; these are one dataset, not independent observations.
- MEDSL 2024 Senate precinct returns: 994,635 CSV records, README and codebook.
- MEDSL 2022 Senate county returns: 21,938 CSV records and codebook. These are county-level data, unlike the 2024 precinct tables.
- GDELT snapshot: 868 headerless records with 27 tab-separated fields. The original small versioned ingestion fixture remains in `tests/fixtures/gdelt/`.
- The resupplied master execution blueprint matches the committed copy byte for byte.

## MEDSL 2022 official repository

User-specified source: <https://github.com/MEDSL/2022-elections-official>.

SSH authentication was unavailable; HTTPS succeeded. A shallow, filtered clone without checkout is stored at `data/raw/medsl_2022_repository`. The exact observed commit is pinned in the inventory. This registers the source; it does not mean the repository's complete state datasets have been downloaded or validated. The project Git remote remains `secondary-inc/synthetic-society-lab`.

## Validation limits and next use

Archive CRC integrity, hashes, CSV record counts and column widths were checked. These checks do not establish statistical validity, complete geographic coverage or correct vote aggregation. Dataverse dataset DOIs, release versions, reuse terms and original download URLs still require confirmation.

Before election aggregation, account for total versus component voting modes, fusion party lines, redacted vote counts, special elections, runoffs and changing boundaries. Before ANES population fitting, verify survey design, variable universes, weights and response codes. Historical election outcomes must remain separated from any prospective forecast workflow. No experiment or paid inference was run during registration.
