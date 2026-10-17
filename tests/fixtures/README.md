`dot311_2025_sample.csv` is a deterministic 1% subset of the real NYC 311 extract: every DOT request
created in 2025 whose `unique_key` ends in `07` (unique_key % 100 = 7). It is real public data from
NYC Open Data (dataset erm2-nwe9) with the same columns as `data/raw/nyc311_dot_2025.csv`. Only the
row selection differs. The tests use it so they can run without downloading the full file.
