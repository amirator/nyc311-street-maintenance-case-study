"""Impact estimates for each recommendation, computed from the data plus assumptions.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from case_study.paths import ASSUMPTIONS, TABLES


def load_assumptions(path: Path = ASSUMPTIONS) -> dict:
    return tomllib.loads(Path(path).read_text())


@dataclass
class Impact:
    key: str
    title: str
    scope: str
    baseline: dict
    estimate: dict
    assumptions: list[str] = field(default_factory=list)


def r1_intake_routing(con, a) -> Impact:
    cfg = a["r1_intake_routing"]
    descs = con.execute("""
        SELECT descriptor FROM fct_requests_enriched WHERE complaint_type = 'Street Condition'
        GROUP BY 1 HAVING count(*) >= ?
           AND 100.0 * avg((outcome = 'Wrong agency / referred')::INT) >= ?
        ORDER BY 1""", [cfg["min_requests"], cfg["min_wrong_agency_pct"]]).fetchall()
    descs = [d[0] for d in descs]
    n, days, med, dep = con.execute(f"""
        SELECT count(*), sum(days_to_close), median(days_to_close),
               sum((resolution_description ILIKE '%Environmental Protection%')::INT) FROM fct_requests_enriched
        WHERE complaint_type = 'Street Condition' AND outcome = 'Wrong agency / referred'
          AND list_contains(?::VARCHAR[], descriptor)""", [descs]).fetchone()
    est = {lvl: {"handlings_avoided": round(n * cfg[f"adoption_{lvl}"]),
                 "citizen_days_saved": round((days or 0) * cfg[f"adoption_{lvl}"])}
           for lvl in ("low", "base", "high")}
    return Impact("R1", "Route sewer / utility conditions to the right agency at intake",
                  "Street Condition: " + ", ".join(descs),
                  {"misrouted_requests": n, "days_until_referral_total": round(days or 0),
                   "median_days_until_referral": round(med or 0, 1),
                   "pct_referred_to_dep": round(100 * (dep or 0) / n, 1) if n else 0.0},
                  est,
                  [f"Descriptors with >= {cfg['min_wrong_agency_pct']:.0f}% of requests later referred elsewhere",
                   f"Share of those caught at intake: {cfg['adoption_low']:.0%} / {cfg['adoption_base']:.0%} / "
                   f"{cfg['adoption_high']:.0%} (low / base / high)",
                   "Citizen-days saved = days the request sat with DOT before referral"])


def r2_pre_dispatch(con, a) -> Impact:
    cfg = a["r2_pre_dispatch_screening"]
    descs = [d[0] for d in con.execute("""
        SELECT descriptor FROM fct_requests_enriched WHERE complaint_type = 'Street Condition'
        GROUP BY 1 HAVING count(*) >= ? AND 100.0 * avg((outcome = 'No defect found')::INT) >= ?
        ORDER BY 1""", [cfg["min_requests"], cfg["min_no_defect_pct"]]).fetchall()]
    n = con.execute(f"""
        SELECT count(*) FROM fct_requests_enriched
        WHERE complaint_type = 'Street Condition' AND outcome = 'No defect found'
          AND list_contains(?::VARCHAR[], descriptor)""", [descs]).fetchone()[0]
    est = {lvl: {"inspections_avoided": round(n * cfg[f"avoided_{lvl}"]),
                 "inspector_hours_freed": round(n * cfg[f"avoided_{lvl}"] * cfg["hours_per_inspection"])}
           for lvl in ("low", "base", "high")}
    return Impact("R2", "Screen 'no defect' prone requests before dispatch (photo + permit check)",
                  "Street Condition: " + ", ".join(descs),
                  {"no_defect_inspections": n}, est,
                  [f"Descriptors where >= {cfg['min_no_defect_pct']:.0f}% of inspections found no defect",
                   f"Share of those visits avoided: {cfg['avoided_low']:.0%} / {cfg['avoided_base']:.0%} / "
                   f"{cfg['avoided_high']:.0%}",
                   f"Illustrative {cfg['hours_per_inspection']} inspector-hours per visit (not in the data)"])


def simulate_tail(days: np.ndarray, threshold: float, recovery: float) -> np.ndarray:
    """Requests beyond the threshold lose `recovery` of their excess days; others are unchanged."""
    out = days.astype(float).copy()
    tail = out > threshold
    out[tail] = threshold + (out[tail] - threshold) * (1 - recovery)
    return out


def r3_street_light(con, a) -> Impact:
    cfg = a["r3_street_light_aging"]
    t = cfg["threshold_days"]
    days = con.execute("""
        SELECT days_to_close FROM fct_requests_enriched
        WHERE complaint_type = 'Street Light Condition' AND descriptor = 'Street Light Out'
          AND days_to_close IS NOT NULL""").df()["days_to_close"].to_numpy()
    base = {"requests": int(days.size), "median_days": round(float(np.median(days)), 1),
            "p90_days": round(float(np.quantile(days, 0.9)), 1),
            "requests_over_threshold": int((days > t).sum()),
            "pct_request_days_in_tail": round(100 * days[days > t].sum() / days.sum(), 1),
            "excess_days_over_threshold": round(float(np.clip(days - t, 0, None).sum()))}
    est = {}
    for lvl in ("low", "base", "high"):
        sim = simulate_tail(days, t, cfg[f"recovery_{lvl}"])
        est[lvl] = {"citizen_days_saved": round(float(days.sum() - sim.sum())),
                    "new_p90_days": round(float(np.quantile(sim, 0.9)), 1),
                    "mean_days_before": round(float(days.mean()), 1),
                    "mean_days_after": round(float(sim.mean()), 1)}
    return Impact("R3", f"Escalate street-light outages still open at day {t}",
                  "Street Light Condition: Street Light Out", base, est,
                  [f"Escalation removes {cfg['recovery_low']:.0%} / {cfg['recovery_base']:.0%} / "
                   f"{cfg['recovery_high']:.0%} of each request's days beyond day {t}",
                   "Requests under the threshold are unchanged (median is unaffected by design)",
                   "Still-open requests are excluded, so savings are conservative"])


def r4_outcome_publishing(con, a) -> Impact:
    n, total, types = con.execute("""
        SELECT sum((outcome = 'Outcome not published')::INT), count(*),
               string_agg(DISTINCT complaint_type, ', ' ORDER BY complaint_type)
                   FILTER (WHERE complaint_type IN (
                       SELECT complaint_type FROM fct_requests_enriched GROUP BY 1
                       HAVING count(*) >= 1000 AND avg((outcome = 'Outcome not published')::INT) > 0.9))
        FROM fct_requests_enriched""").fetchone()
    pct = round(100 * n / total, 1)
    return Impact("R4", "Publish a standard outcome code on every closed request",
                  f"All DOT requests (fully affected: {types})",
                  {"requests_without_published_outcome": int(n), "pct_of_all_requests": pct},
                  {lvl: {"requests_with_measurable_outcome": int(n)} for lvl in ("low", "base", "high")},
                  ["No time saving claimed: this fixes measurement so first-time-fix and repeat-visit "
                   "rates can be tracked for street lights and traffic signals"])


def compute(con: duckdb.DuckDBPyConnection, assumptions: dict | None = None) -> list[Impact]:
    a = assumptions or load_assumptions()
    return [r1_intake_routing(con, a), r2_pre_dispatch(con, a), r3_street_light(con, a),
            r4_outcome_publishing(con, a)]


def to_frame(impacts: list[Impact]) -> pd.DataFrame:
    rows = []
    for im in impacts:
        for lvl, vals in im.estimate.items():
            for metric, v in vals.items():
                rows.append({"rec": im.key, "title": im.title, "scenario": lvl, "metric": metric, "value": v})
    return pd.DataFrame(rows)


def export(impacts: list[Impact], out_dir: Path = TABLES) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "impact_estimates.csv"
    to_frame(impacts).to_csv(p, index=False)
    return p
