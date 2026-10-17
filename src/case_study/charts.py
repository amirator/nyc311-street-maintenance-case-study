"""Figures for the README and slide deck. Every chart is drawn from reports/tables or the DuckDB file."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, PercentFormatter  # noqa: E402

from case_study.paths import FIGS  # noqa: E402

NAVY, TEAL, AMBER, RED, GREY, LIGHT = "#1F3A5F", "#2A9D8F", "#F2A93B", "#D64545", "#6B7280", "#E5E9EF"
SOURCE = "Source: NYC Open Data, 311 Service Requests (erm2-nwe9), agency = DOT, created in 2025. Independent analysis."

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#9CA3AF", "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlelocation": "left",
    "axes.titlecolor": NAVY, "axes.labelcolor": "#374151", "xtick.color": "#374151", "ytick.color": "#374151",
})

thousands = FuncFormatter(lambda v, _: f"{v / 1000:,.0f}k" if abs(v) >= 1000 else f"{v:,.0f}")


def _finish(fig, path: Path, subtitle: str | None = None) -> Path:
    if subtitle:
        fig.text(0.012, 0.935, subtitle, fontsize=9.5, color=GREY)
    fig.text(0.012, 0.012, SOURCE, fontsize=7, color=GREY)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def pareto(df: pd.DataFrame, out: Path = FIGS / "pareto_request_days.png", top: int = 10) -> Path:
    d = df.head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    fig.subplots_adjust(top=0.84, left=0.24)
    colours = [RED if i == len(d) - 1 else NAVY for i in range(len(d))]
    ax.barh(d["complaint_type"], d["request_days"], color=colours)
    ax.xaxis.set_major_formatter(thousands)
    ax.set_xlabel("Total days requests stayed open (request-days)")
    for y, (rd, pct, req) in enumerate(zip(d["request_days"], d["pct_request_days"], d["pct_requests"])):
        ax.text(rd, y, f"  {pct:.0f}% of wait  |  {req:.0f}% of requests", va="center", fontsize=8.5, color="#374151")
    ax.set_xlim(0, d["request_days"].max() * 1.45)
    ax.set_title("Where the waiting happens: request-days by complaint type")
    lead = df.iloc[0]
    return _finish(fig, out, f"{lead['complaint_type']} is {lead['pct_requests']:.0f}% of requests but "
                             f"{lead['pct_request_days']:.0f}% of all waiting time. Top 4 types = "
                             f"{df.iloc[3]['cum_pct_request_days']:.0f}% of request-days.")


def street_light_tail(df: pd.DataFrame, out: Path = FIGS / "street_light_tail.png") -> Path:
    labels = [b.split(": ")[1] for b in df["age_band"]]
    x = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.subplots_adjust(top=0.84)
    ax.bar(x - 0.2, df["pct_requests"], 0.4, color=LIGHT, edgecolor=NAVY, label="% of requests")
    ax.bar(x + 0.2, df["pct_request_days"], 0.4, color=[NAVY, NAVY, NAVY, RED, RED], label="% of request-days")
    for i, (a, b) in enumerate(zip(df["pct_requests"], df["pct_request_days"])):
        ax.text(i - 0.2, a + 1, f"{a:.0f}%", ha="center", fontsize=9)
        ax.text(i + 0.2, b + 1, f"{b:.0f}%", ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(x, labels)
    ax.set_xlabel("Time from request to closure")
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.legend(frameon=False)
    ax.set_title("Street Light Out: a small tail of old requests holds most of the waiting")
    tail_req = df.iloc[3:]["pct_requests"].sum()
    tail_days = df.iloc[3:]["pct_request_days"].sum()
    return _finish(fig, out, f"Requests open more than 30 days are {tail_req:.0f}% of the volume but "
                             f"{tail_days:.0f}% of request-days (n = {df['requests'].sum():,} closed requests).")


def borough(df: pd.DataFrame, out: Path = FIGS / "street_light_by_borough.png") -> Path:
    d = df.sort_values("p90_days")
    fig, ax = plt.subplots(figsize=(10, 4.6))
    fig.subplots_adjust(top=0.82, left=0.16)
    y = np.arange(len(d))
    ax.hlines(y, d["median_days"], d["p90_days"], color=LIGHT, lw=6)
    ax.scatter(d["median_days"], y, color=TEAL, s=70, zorder=3, label="Median")
    ax.scatter(d["p90_days"], y, color=RED, s=70, zorder=3, label="90th percentile")
    for yi, (m, p, pct) in enumerate(zip(d["median_days"], d["p90_days"], d["pct_over_30_days"])):
        ax.text(p + 2, yi, f"{p:.0f} d  ({pct:.0f}% > 30 d)", va="center", fontsize=9)
        ax.text(m - 1.5, yi, f"{m:.0f}", va="center", ha="right", fontsize=9, color=TEAL)
    ax.set_yticks(y, [b.title() for b in d["borough"]])
    ax.set_xlabel("Days from request to closure")
    ax.set_xlim(-6, d["p90_days"].max() * 1.35)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("Street Light Out by borough: medians are similar, tails are not")
    top, low = d.iloc[-1], d.iloc[0]
    return _finish(fig, out, f"{top['borough'].title()} has the fastest typical fix ({top['median_days']:.0f} d) but "
                             f"the longest tail (p90 {top['p90_days']:.0f} d) vs {low['borough'].title()} "
                             f"(p90 {low['p90_days']:.0f} d).")


def failure_demand(df: pd.DataFrame, out: Path = FIGS / "street_condition_failure_demand.png", top: int = 9) -> Path:
    d = df.head(top).iloc[::-1].copy()
    d["pct_other"] = 100 - d[["pct_repaired", "pct_no_defect", "pct_wrong_agency", "pct_duplicate"]].sum(axis=1)
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    fig.subplots_adjust(top=0.84, left=0.27)
    left = np.zeros(len(d))
    for col, colour, label in (("pct_repaired", TEAL, "Repaired by DOT"), ("pct_no_defect", AMBER, "No defect found"),
                               ("pct_wrong_agency", RED, "Wrong agency / referred"),
                               ("pct_duplicate", "#F4A3A3", "Duplicate"),
                               ("pct_other", LIGHT, "Other (third party, deferred, unpublished)")):
        ax.barh(d["descriptor"], d[col], left=left, color=colour, label=label)
        left += d[col].to_numpy()
    for yi, (n, fd) in enumerate(zip(d["requests"], d["pct_failure_demand"])):
        ax.text(101, yi, f"{fd:.0f}% failure demand  (n={n:,})", va="center", fontsize=8.5)
    ax.set_xlim(0, 135)
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.legend(ncol=3, frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.45, -0.08))
    ax.set_title("Street Condition: outcome of each request by what the caller reported")
    return _finish(fig, out, "Potholes are fixed 71% of the time. Cave-ins, hardware and construction complaints "
                             "mostly end with 'no defect' or a referral to another agency.")


def fishbone(evidence: dict[str, list[str]], out: Path = FIGS / "fishbone.png",
             effect: str = "Long, uneven waits\nand wasted\ninspections") -> Path:
    """Ishikawa diagram: 3 cause categories above the spine, 3 below, evidence listed beside each bone."""
    import textwrap

    fig, ax = plt.subplots(figsize=(14, 7.2))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    spine_y = 3.6
    ax.annotate("", xy=(11.2, spine_y), xytext=(0.3, spine_y),
                arrowprops=dict(arrowstyle="-|>", lw=3, color=NAVY, mutation_scale=25))
    ax.text(11.35, spine_y, effect, va="center", fontsize=13, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.7", fc=RED, ec=RED))
    cats = list(evidence.items())
    cols = [0.35, 3.95, 7.55]
    for i, (cat, items) in enumerate(cats):
        top = i < 3
        x0 = cols[i % 3]
        box_y = 6.75 if top else 0.45
        bone_x0, bone_x1 = x0 + 3.15, x0 + 3.55
        ax.plot([bone_x0, bone_x1], [box_y, spine_y], color=NAVY, lw=2)
        ax.text(x0, box_y, cat, fontsize=11.5, fontweight="bold", color=NAVY, va="center",
                bbox=dict(boxstyle="round,pad=0.35", fc="#EEF2F7", ec=NAVY, lw=1))
        lines = []
        for it in items:
            wrapped = textwrap.wrap(it, 34)
            lines.append(wrapped)
        y = box_y - 0.5 if top else box_y + 0.5
        step = -0.3 if top else 0.3
        seq = lines if top else lines[::-1]
        for wrapped in seq:
            block = wrapped if top else wrapped[::-1]
            for k, ln in enumerate(block):
                prefix = "• " if (k == 0 and top) or (k == len(block) - 1 and not top) else "   "
                ax.text(x0 + 0.05, y, prefix + ln, fontsize=9, color="#1F2937", va="center")
                y += step
    ax.set_title("Root causes (Ishikawa), each backed by a number from the 2025 data", loc="left")
    return _finish(fig, out)


def impact_chart(impacts, out: Path = FIGS / "impact.png") -> Path:
    rows = []
    for im in impacts:
        for metric in ("citizen_days_saved", "inspections_avoided", "handlings_avoided"):
            if metric in im.estimate["base"]:
                rows.append((im.key, metric, im.estimate["low"][metric], im.estimate["base"][metric],
                             im.estimate["high"][metric]))
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), gridspec_kw={"width_ratios": [1, 1]})
    fig.subplots_adjust(wspace=0.5)
    for ax, metric, title in ((axes[0], "citizen_days_saved", "Citizen waiting days saved / year"),
                              (axes[1], None, "DOT handlings / inspections avoided / year")):
        sel = [r for r in rows if (r[1] == metric if metric else r[1] != "citizen_days_saved")]
        labels = [f"{r[0]}" + ("" if metric else (" (referrals)" if r[1] == "handlings_avoided" else " (no-defect)"))
                  for r in sel]
        y = np.arange(len(sel))
        ax.barh(y, [r[3] for r in sel], color=NAVY if metric else TEAL)
        ax.errorbar([r[3] for r in sel], y, xerr=[[r[3] - r[2] for r in sel], [r[4] - r[3] for r in sel]],
                    fmt="none", ecolor="#111827", capsize=4, lw=1)
        for yi, r in enumerate(sel):
            ax.text(r[4] * 1.03, yi, f"{r[3]:,.0f}\n({r[2]:,.0f}-{r[4]:,.0f})", va="center", fontsize=8.5)
        ax.set_yticks(y, labels)
        ax.xaxis.set_major_formatter(thousands)
        ax.set_xlim(0, max(r[4] for r in sel) * 1.45)
        ax.set_title(title, fontsize=11)
    return _finish(fig, out)
