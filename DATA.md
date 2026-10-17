# Data source, terms and modifications

| | |
|---|---|
| Dataset | **311 Service Requests from 2020 to Present** (NYC Open Data id `erm2-nwe9`) |
| Publisher | City of New York, NYC Open Data. Dataset attribution field: "311" |
| Dataset page | https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9 |
| API used | https://data.cityofnewyork.us/resource/erm2-nwe9.csv (Socrata SODA, no key required) |
| Terms | NYC Admin. Code §23-502(d) (Local Law 11 of 2012): public data sets are made available *"without any registration requirement, license requirement or restrictions on their use"*. The City may require republishers to identify the source and version and describe modifications, which this file does. Text: https://cityofnewyork.github.io/opendatatsm/LocalLaw11of2012.html |
| Version used | Snapshot downloaded 2026-10-17 11:56 UTC. 212,103 rows; SHA-256 in `data/raw/manifest.json` |

## Extract
`scripts/download_data.py` requests 13 of the 40+ columns for
`agency = 'DOT' AND created_date between 2025-01-01 and 2025-12-31` and pages through the API
50,000 rows at a time. The live dataset changes as requests close, so a re-download gives a newer
snapshot with slightly different numbers. `manifest.json` records exactly which one you have.

## Modifications made in this project
1. Column subset only (unique_key, created/closed/resolution-update dates, agency, complaint type,
   descriptor, status, resolution description, borough, channel, community board, ZIP). Addresses and
   coordinates were not downloaded.
2. Apostrophes and quotes that the source double-encodes (`â€™` shown as `â`) are repaired in
   `sql/01_staging.sql`.
3. 835 requests whose closed date is earlier than their created date are flagged and left out of
   duration statistics. They are still counted in volumes.
4. Free-text resolution descriptions are mapped to 9 outcome classes by the rules in
   `sql/02_outcomes.sql`. This is the author's interpretation, not an official DOT code.
5. `tests/fixtures/dot311_2025_sample.csv` is a deterministic 1% row subset (unique_key % 100 = 7).

The raw CSV (~69 MB) is not committed. `python -m case_study` downloads it if it is missing.

This is an independent analysis. It is not affiliated with, commissioned by, or endorsed by NYC DOT,
NYC 311 or the City of New York.
