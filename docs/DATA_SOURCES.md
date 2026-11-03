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

## Additional candidate and geography inputs

The subsequent user upload adds these local files, with hashes and structural checks recorded in the inventory:

- Candidate summary CSVs: 5,302 records for the 2024 file and 4,540 for the 2026 file, each with 50 columns. These contain candidate and financial reporting information; coverage dates must be checked before use in any time-bounded analysis.
- FEC-format candidate master files (`cn22`, `cn24`, `cn26`): respectively 8,578, 9,796 and 8,890 headerless, pipe-delimited records, with 15 fields each.
- FEC-format candidate–committee linkage files (`ccl22`, `ccl24`, `ccl26`): respectively 7,683, 8,619 and 8,397 headerless, pipe-delimited records, with seven fields each. These link candidates and committees; they are not election returns.
- `cd120.zip`: a national block-to-congressional-district assignment table with 8,174,955 records, plus nine state tables. Each has six columns: GEOID, STATEFP, COUNTYFP, TRACTCE, BLOCKCE and CDFP. State and national files must not be concatenated as independent records without overlap checks. This is a geographic assignment input, not a district polygon shapefile or an ACS population table. Release provenance, applicable boundary revisions and compatibility with historical geography remain unverified.

The additional ANES ZIP is byte-identical to the previously registered archive. The two `cd120` ZIPs are byte-identical, as are all three `cn26` ZIPs. Duplicate uploads are registered as aliases to a single local copy.

The [FEC candidate master documentation](https://www.fec.gov/campaign-finance-data/candidate-master-file-description/) says that its universe includes active committees regardless of election year and some candidates referenced by other committees. Accordingly, candidate registration records alone do not establish the official 2026 general-election ballot. The [candidate–committee linkage documentation](https://www.fec.gov/campaign-finance-data/candidate-committee-linkage-file-description/) describes the seven linkage fields. These references support format interpretation; they do not authenticate the supplied downloads' exact upstream release.

At this registration stage, acquisition gaps included ACS demographic tables and questionnaires; the subsequent delivery below supplies those inputs. Remaining work includes primary-scale selection, permitted experiment text, official general-election ballot verification, complete dated race ratings if used, and authoritative geography-version checks. The geography and candidate inputs partially address E01 requirements; they do not complete those gates. No paid inference or experiment was run.

## ACS benchmarks and questionnaire delivery

Four user-supplied ZIPs now provide 2024 ACS five-year detailed tables B01001 (age/sex), B03002 (Hispanic origin/race), B15003 (education) and B19001 (household income), with column metadata and table notes. All four tables have 52 geographic records: the 50 states, DC and Puerto Rico. Puerto Rico is retained in the raw files but is outside the proposed 50-state-plus-DC experiment. Each data CSV has a machine-name header and an additional descriptive-label row; that label row is not a geography observation. Margins of error are preserved.

The B01001 product ZIP additionally contains an ACS one-year table, registered separately. Use the five-year product for consistency across these starting benchmarks. These separate marginal tables do not establish joint demographic distributions, citizenship or voter eligibility. B15003 covers people age 25 and older and B19001 covers households; their denominators cannot be treated as interchangeable person-level sampling weights. Joint population fitting, ANES calibration and numerical consistency checks remain to be implemented.

Two ANES questionnaire PDFs were received and opened. Their first pages were text-extracted, rendered and visually inspected. The full pre/post-election questionnaire has 481 pages and a cover date of August 8, 2025 despite the supplied filename ending in `20240808`. Preserve that discrepancy and reconcile the version with the existing codebook before selecting items. The paper questionnaire has 20 pages. Receipt of questionnaires does not mean a primary scale, scoring rule or variable mapping has been chosen.

The additional `file.xhtml` is a saved Dataverse file landing page titled “Copy of Stanford_A1R_Codebook B.tab”, with DOI `10.7910/DVN/KJ8IH2` observed in its HTML. Its underlying data, relevance and license have not been verified. `download.html` is an ANES 2016 updates/errata page, not the 2024 study dataset. Both are preserved as inert local reference pages and are not counted as acquired underlying datasets. Embedded scripts and instructions were not executed.

These acquisitions close the initial state-level ACS and questionnaire download gaps. E02 still needs permitted text stimuli and a frozen protocol, instrument mapping and sampling/analysis implementation. They do not establish representative synthetic populations or validate any election forecast.

## Validation limits and next use

### Cook Political Report ratings PDFs

User-supplied House (three pages) and Senate (two pages) PDFs are stored locally at `data/raw/ratings/cook_2026/`. Both display a November 2, 2026 ratings date. PDF metadata records creation on November 3, 2026 at 09:46:33 UTC (House) and 09:46:26 UTC (Senate). These are local metadata observations, not independently verified archive timestamps.

All pages were text-extracted and the first page of each PDF was rendered and visually inspected. The horizontally scrolling race-detail tables are clipped in the printouts, so complete individual-race ratings cannot be recovered from these PDFs alone. Register these sources as partially acquired; a complete permitted export or accessible race-level source is still needed for sample selection. The displayed November 2 date does not establish a frozen November 2 snapshot or validate prospective forecasting. PDFs and full-text extracts remain excluded from Git; redistribution rights have not been established.

Archive CRC integrity, hashes, CSV record counts and column widths were checked. These checks do not establish statistical validity, complete geographic coverage or correct vote aggregation. Dataverse dataset DOIs, release versions, reuse terms and original download URLs still require confirmation.

Before election aggregation, account for total versus component voting modes, fusion party lines, redacted vote counts, special elections, runoffs and changing boundaries. Before ANES population fitting, verify survey design, variable universes, weights and response codes. Historical election outcomes must remain separated from any prospective forecast workflow. No experiment or paid inference was run during registration.
