"""Collect every headline number used in the README, fishbone and slides into one dict (findings.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from case_study.paths import REPORTS


def _row(df: pd.DataFrame, col: str, val) -> pd.Series:
    return df.loc[df[col] == val].iloc[0]


def collect(res: dict[str, pd.DataFrame], impacts) -> dict:
    dq, kpi = res["data_quality"].iloc[0], res["kpi_overview"].iloc[0]
    par, tail, bor = res["pareto_request_days"], res["street_light_tail"], res["street_light_by_borough"]
    mon, sc, mix = res["street_light_by_month"], res["street_condition_by_descriptor"], res["outcome_mix"]
    back, fd = res["open_backlog"], res["failure_demand_by_type"]
    sl = _row(par, "complaint_type", "Street Light Condition")
    sc_fd = _row(fd, "complaint_type", "Street Condition")
    cave, hw = _row(sc, "descriptor", "Cave-in"), _row(sc, "descriptor", "Defective Hardware")
    blocked, pot = _row(sc, "descriptor", "Blocked - Construction"), _row(sc, "descriptor", "Pothole")
    side_mix = mix[mix["complaint_type"] == "Sidewalk Condition"]
    side_third = float(side_mix.loc[side_mix["outcome"] == "Third party must repair", "pct_of_type"].sum())
    imp = {im.key: {"title": im.title, "scope": im.scope, "baseline": im.baseline, "estimate": im.estimate,
                    "assumptions": im.assumptions} for im in impacts}
    open_total = int(dq["still_open_at_snapshot"])
    return {
        "requests": int(dq["requests"]),
        "snapshot_at": str(dq["snapshot_at"]),
        "closed_before_created": int(dq["closed_before_created_excluded"]),
        "still_open": open_total,
        "still_open_median_age_days": float(back["median_age_days"].iloc[0]),
        "median_days_all": float(kpi["median_days"]),
        "p90_days_all": float(kpi["p90_days"]),
        "total_request_days": float(kpi["total_request_days"]),
        "pct_outcome_not_published": float(kpi["pct_outcome_not_published"]),
        "street_light_pct_requests": float(sl["pct_requests"]),
        "street_light_pct_request_days": float(sl["pct_request_days"]),
        "top4_cum_pct_request_days": float(par.iloc[3]["cum_pct_request_days"]),
        "sl_out_requests": int(tail["requests"].sum()),
        "sl_tail_pct_requests": float(tail.iloc[3:]["pct_requests"].sum()),
        "sl_tail_pct_request_days": float(tail.iloc[3:]["pct_request_days"].sum()),
        "sl_borough_max": {"borough": bor.iloc[0]["borough"].title(), "p90": float(bor.iloc[0]["p90_days"]),
                           "median": float(bor.iloc[0]["median_days"])},
        "sl_borough_min": {"borough": bor.iloc[-1]["borough"].title(), "p90": float(bor.iloc[-1]["p90_days"])},
        "sl_winter_p90_range": [float(mon[mon["created_month"] <= 4]["p90_days"].min()),
                                float(mon[mon["created_month"] <= 4]["p90_days"].max())],
        "sl_july_p90": float(_row(mon, "created_month", 7)["p90_days"]),
        "street_condition_requests": int(sc_fd["requests"]),
        "street_condition_failure_demand": int(sc_fd["failure_demand_requests"]),
        "street_condition_pct_failure_demand": float(sc_fd["pct_failure_demand"]),
        "cavein_pct_wrong_agency": float(cave["pct_wrong_agency"]),
        "hardware_pct_wrong_agency": float(hw["pct_wrong_agency"]),
        "blocked_pct_no_defect": float(blocked["pct_no_defect"]),
        "pothole_pct_repaired": float(pot["pct_repaired"]),
        "pothole_median_days": float(pot["median_days"]),
        "sidewalk_pct_third_party": side_third,
        "impacts": imp,
    }


def fishbone_evidence(f: dict) -> dict[str, list[str]]:
    r1 = f["impacts"]["R1"]["baseline"]
    return {
        "Intake & channel": [f"{f['cavein_pct_wrong_agency']:.0f}% of cave-in reports go to another agency",
                             f"{f['hardware_pct_wrong_agency']:.0f}% of defective-hardware reports referred",
                             f"{f['blocked_pct_no_defect']:.0f}% of 'blocked by construction' find no defect",
                             "No photo / permit check before dispatch"],
        "Backlog management": [f"Street lights open > 30 d: {f['sl_tail_pct_requests']:.0f}% of requests",
                               f"... but {f['sl_tail_pct_request_days']:.0f}% of street-light waiting",
                               f"{f['still_open']:,} 2025 requests still open at snapshot",
                               "No visible aging / escalation trigger"],
        "Measurement": [f"{f['pct_outcome_not_published']:.0f}% of requests: outcome not published",
                        "Street lights & signals: 100% 'see DOT website'",
                        f"{f['closed_before_created']:,} records closed before created"],
        "Routing & jurisdiction": [f"{r1['misrouted_requests']:,} Street Condition misroutes",
                                   f"median {r1['median_days_until_referral']:.1f} d before referral",
                                   f"{r1['pct_referred_to_dep']:.0f}% of these referrals go to DEP (sewer / water)"],
        "Geography & season": [f"{f['sl_borough_max']['borough']} p90 {f['sl_borough_max']['p90']:.0f} d vs "
                               f"{f['sl_borough_min']['borough']} {f['sl_borough_min']['p90']:.0f} d",
                               f"Jan-Apr p90 {f['sl_winter_p90_range'][0]:.0f}-{f['sl_winter_p90_range'][1]:.0f} d "
                               f"vs Jul {f['sl_july_p90']:.0f} d"],
        "Third parties": [f"Sidewalks: {f['sidewalk_pct_third_party']:.0f}% need owner / contractor action",
                          "Corrective Action Repair: 30-day contractor window"],
    }


def save(f: dict, path: Path = REPORTS / "findings.json") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(f, indent=2, default=str) + "\n")
    return path
