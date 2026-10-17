"""Data and result validation run on every build (also exercised by pytest)."""

from __future__ import annotations

import hashlib
import json

import pandas as pd

from case_study.paths import MANIFEST, RAW_CSV

OUTCOMES = {"Repaired / completed", "No defect found", "Wrong agency / referred", "Duplicate",
            "Insufficient information", "Third party must repair", "Deferred to planned work",
            "Outcome not published", "No resolution text", "Other"}


def run_checks(con, res: dict[str, pd.DataFrame], check_manifest: bool = True) -> list[str]:
    problems = []
    q = lambda s: con.execute(s).fetchone()  # noqa: E731
    n, distinct = q("SELECT count(*), count(DISTINCT request_id) FROM fct_requests_enriched")
    if n != distinct:
        problems.append(f"duplicate request ids: {n - distinct}")
    if check_manifest and MANIFEST.exists() and RAW_CSV.exists():
        m = json.loads(MANIFEST.read_text())
        if m["rows"] != n:
            problems.append(f"row count {n} != manifest {m['rows']}")
        if hashlib.sha256(RAW_CSV.read_bytes()).hexdigest() != m["sha256"]:
            problems.append("raw CSV SHA-256 does not match manifest (file changed?)")
    bad_agency, = q("SELECT count(*) FROM fct_requests_enriched WHERE agency <> 'DOT'")
    if bad_agency:
        problems.append(f"{bad_agency} rows not assigned to DOT")
    out_of_year, = q("SELECT count(*) FROM fct_requests_enriched WHERE year(created_at) <> 2025")
    if out_of_year:
        problems.append(f"{out_of_year} rows created outside 2025")
    found = {r[0] for r in con.execute("SELECT DISTINCT outcome FROM fct_requests_enriched").fetchall()}
    if not found <= OUTCOMES:
        problems.append(f"unexpected outcome classes: {found - OUTCOMES}")
    other_pct, = q("SELECT 100.0 * avg((outcome = 'Other')::INT) FROM fct_requests_enriched")
    if other_pct > 5:
        problems.append(f"'Other' outcome share {other_pct:.1f}% > 5% (classification rules need review)")
    neg, = q("SELECT count(*) FROM fct_requests_enriched WHERE days_to_close < 0")
    if neg:
        problems.append(f"{neg} negative durations leaked into analysis")
    par = res["pareto_request_days"]
    if abs(par["pct_request_days"].sum() - 100) > 0.5:
        problems.append("Pareto shares do not sum to 100%")
    if not par["request_days"].is_monotonic_decreasing:
        problems.append("Pareto not sorted")
    tail = res["street_light_tail"]
    if abs(tail["pct_requests"].sum() - 100) > 0.5 or abs(tail["pct_request_days"].sum() - 100) > 0.5:
        problems.append("street-light age bands do not sum to 100%")
    return problems
