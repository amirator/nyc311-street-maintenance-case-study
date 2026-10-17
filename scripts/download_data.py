"""Download NYC 311 Service Requests handled by NYC DOT in calendar year 2025.

Source : NYC Open Data, "311 Service Requests from 2020 to Present" (dataset id erm2-nwe9)
         https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9
API    : Socrata SODA 2.0, https://data.cityofnewyork.us/resource/erm2-nwe9.csv (no key needed)
Terms  : NYC Open Data Law, NYC Admin. Code 23-502(d): public data sets are available "without any
         registration requirement, license requirement or restrictions on their use"; republishers may
         be asked to identify the source and version and describe modifications (see DATA.md).
         https://cityofnewyork.github.io/opendatatsm/LocalLaw11of2012.html

The live dataset keeps changing as requests are closed, so every download is a dated
snapshot. The script writes data/raw/nyc311_dot_2025.csv plus data/raw/manifest.json
(row count, SHA-256, UTC timestamp, exact query). Usage:

    python scripts/download_data.py            # full year, about 212k rows, takes a few minutes
    python scripts/download_data.py --limit 5000   # quick smoke test
Set SODA_APP_TOKEN in the environment to raise API rate limits (optional).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
DATASET_PAGE = "https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9"
TERMS = "https://cityofnewyork.github.io/opendatatsm/LocalLaw11of2012.html"
COLUMNS = ["unique_key", "created_date", "closed_date", "agency", "complaint_type", "descriptor", "status",
           "resolution_description", "resolution_action_updated_date", "borough", "open_data_channel_type",
           "community_board", "incident_zip"]
WHERE = "agency='DOT' AND created_date between '2025-01-01T00:00:00' and '2025-12-31T23:59:59'"
PAGE = 50_000


def fetch(offset: int, limit: int) -> str:
    params = {"$select": ",".join(COLUMNS), "$where": WHERE, "$order": "unique_key", "$limit": limit,
              "$offset": offset}
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": "nyc311-case-study/1.0"}
    if os.environ.get("SODA_APP_TOKEN"):
        headers["X-App-Token"] = os.environ["SODA_APP_TOKEN"]
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=600) as r:
                return r.read().decode("utf-8")
        except Exception as exc:  # network hiccup or 5xx: back off and retry
            wait = 10 * (attempt + 1)
            print(f"  attempt {attempt + 1} failed ({exc}); retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit("download failed after 5 attempts")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=None, help="max rows (for a quick test)")
    ap.add_argument("--out", default=RAW / "nyc311_dot_2025.csv")
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    rows, offset = 0, 0
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        while True:
            n = PAGE if args.limit is None else min(PAGE, args.limit - rows)
            if n <= 0:
                break
            reader = csv.reader(io.StringIO(fetch(offset, n)))
            header = next(reader, None)
            if header != COLUMNS:
                raise SystemExit(f"unexpected header from API: {header}")
            page = list(reader)
            writer.writerows(page)
            rows += len(page)
            offset += len(page)
            print(f"  fetched {rows:,} rows", flush=True)
            if len(page) < n:
                break
    tmp.replace(out)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    manifest = {
        "dataset": "311 Service Requests from 2020 to Present (erm2-nwe9)",
        "publisher": "City of New York, NYC Open Data (dataset attribution: 311)",
        "dataset_page": DATASET_PAGE,
        "api_endpoint": ENDPOINT,
        "terms_of_use": "NYC Admin. Code 23-502(d) (Local Law 11 of 2012): no registration, license or use restrictions",
        "terms_url": TERMS,
        "filter": WHERE,
        "columns": COLUMNS,
        "rows": rows,
        "sha256": sha,
        "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "file": out.name,
    }
    (out.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {out} ({rows:,} rows, sha256 {sha[:12]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
