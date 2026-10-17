"""Slide-style PDF (16:9) built with matplotlib from the generated figures and findings."""

from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

from case_study.charts import AMBER, GREY, NAVY, RED, TEAL  # noqa: E402
from case_study.paths import FIGS, REPORTS  # noqa: E402

W, H = 13.333, 7.5
AUTHOR = "Mohammad Amir Khan"
FOOT = "Independent case study on public data (NYC Open Data, 311 Service Requests, DOT, 2025). Not affiliated with NYC DOT."


class Deck:
    def __init__(self, path: Path):
        self.path, self.pdf, self.n = path, PdfPages(path), 0
        self.pdf.infodict().update({"Title": "NYC 311 street-maintenance process improvement", "Author": AUTHOR})

    def new(self, title: str, takeaway: str | None = None):
        self.n += 1
        fig = plt.figure(figsize=(W, H))
        fig.add_artist(Rectangle((0, 0.9), 1, 0.1, transform=fig.transFigure, color=NAVY))
        fig.text(0.035, 0.95, title, color="white", fontsize=21, fontweight="bold", va="center")
        if takeaway:
            fig.text(0.035, 0.855, takeaway, color=NAVY, fontsize=13.5, va="center", fontweight="bold")
        fig.text(0.035, 0.025, FOOT, fontsize=7.5, color=GREY)
        fig.text(0.965, 0.025, str(self.n), fontsize=9, color=GREY, ha="right")
        return fig

    def save(self, fig):
        self.pdf.savefig(fig)
        plt.close(fig)

    def close(self):
        self.pdf.close()


def _image(fig, path: Path, rect):
    ax = fig.add_axes(rect)
    ax.imshow(mpimg.imread(path))
    ax.axis("off")


def _bullets(fig, x, y, items, size=12.5, width=62, gap=0.012, colour="#1F2937"):
    for it in items:
        lines = textwrap.wrap(it, width)
        fig.text(x, y, "•", fontsize=size, color=TEAL, fontweight="bold", va="top")
        fig.text(x + 0.018, y, "\n".join(lines), fontsize=size, color=colour, va="top", linespacing=1.35)
        y -= 0.043 * len(lines) * size / 12.5 + gap
    return y


def _card(fig, x, y, w, h, big, small, colour=NAVY):
    fig.add_artist(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                                  transform=fig.transFigure, fc="#F4F6F8", ec="#E1E5EA"))
    fig.add_artist(Rectangle((x, y), 0.006, h, transform=fig.transFigure, color=colour))
    fig.text(x + 0.02, y + h - 0.035, big, fontsize=24, fontweight="bold", color=colour, va="top")
    fig.text(x + 0.02, y + 0.03, "\n".join(textwrap.wrap(small, 30)), fontsize=10, color="#374151", va="bottom")


def build(f: dict, out: Path = REPORTS / "case_study_slides.pdf") -> Path:
    im = f["impacts"]
    r1, r2, r3, r4 = im["R1"], im["R2"], im["R3"], im["R4"]
    d = Deck(out)

    # 1 Title
    fig = plt.figure(figsize=(W, H))
    fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, color=NAVY))
    fig.add_artist(Rectangle((0.06, 0.585), 0.07, 0.008, transform=fig.transFigure, color=TEAL))
    fig.text(0.06, 0.68, "Fixing the long tail", fontsize=40, fontweight="bold", color="white")
    fig.text(0.06, 0.62, "Process improvement for NYC street-maintenance requests (311, 2025)", fontsize=20,
             color="#C9D3DF")
    fig.text(0.06, 0.50, f"{f['requests']:,} DOT service requests  ·  Python + DuckDB SQL  ·  root-cause analysis  ·  "
             "to-be process  ·  impact model", fontsize=13, color="white")
    fig.text(0.06, 0.16, f"{AUTHOR}  ·  Independent case study on public data  ·  {date.today():%B %Y}",
             fontsize=12, color="#C9D3DF")
    fig.text(0.06, 0.11, "Source: NYC Open Data, 311 Service Requests from 2020 to Present (erm2-nwe9). "
             "Not affiliated with or endorsed by NYC DOT or NYC 311.", fontsize=9.5, color="#9FB0C4")
    d.n += 1
    d.save(fig)

    # 2 Problem
    fig = d.new("The problem", "Residents wait a median of "
                f"{f['median_days_all']:.1f} days, but 1 in 10 waits {f['p90_days_all']:.0f}+ days, and much "
                "of DOT's field effort finds nothing to fix")
    _card(fig, 0.035, 0.56, 0.205, 0.22, f"{f['requests']:,}", "DOT service requests created in 2025")
    _card(fig, 0.26, 0.56, 0.205, 0.22, f"{f['total_request_days'] / 1e6:.1f}M", "request-days of waiting (sum of time to close)")
    _card(fig, 0.485, 0.56, 0.205, 0.22, f"{f['street_condition_pct_failure_demand']:.0f}%",
          "of Street Condition requests are failure demand", RED)
    _card(fig, 0.71, 0.56, 0.205, 0.22, f"{f['pct_outcome_not_published']:.0f}%",
          "of requests close without a published outcome", AMBER)
    fig.text(0.035, 0.47, "Business questions", fontsize=14, fontweight="bold", color=NAVY)
    _bullets(fig, 0.035, 0.42, ["Where does residents' waiting time accumulate, and why?",
                                "How much inspection effort is spent on requests DOT cannot or need not fix?",
                                "Which process changes would cut waiting and wasted visits, and by how much?"],
             width=70)
    fig.text(0.55, 0.47, "Scope", fontsize=14, fontweight="bold", color=NAVY)
    _bullets(fig, 0.55, 0.42, ["In: all 311 requests assigned to NYC DOT, created 1 Jan - 31 Dec 2025",
                               "Out: field crew rosters and costs (not public); requests handled outside 311",
                               "Lens: Lean, i.e. lead time, failure demand, first-time-right"], width=55)
    d.save(fig)

    # 3 Data & method
    fig = d.new("Data and method", "A reproducible pipeline: download → DuckDB SQL models → tests → charts → this deck")
    _bullets(fig, 0.035, 0.78, [
        "Source: NYC Open Data '311 Service Requests from 2020 to Present' (erm2-nwe9), via the public SODA API. "
        "Published without license or use restrictions (NYC Admin. Code §23-502(d)).",
        f"Snapshot: {f['snapshot_at'][:10]} (New York time); {f['requests']:,} rows, SHA-256 in data/raw/manifest.json.",
        "SQL (DuckDB): staging → request facts → outcome classification (9 classes from DOT's free-text "
        "resolution) → 10 analysis queries exported to CSV.",
        "Request-days = sum of (closed − created). It weights each request by how long a resident waited.",
        "Failure demand = closed as no defect found, wrong agency, duplicate or insufficient information.",
        f"Data quality: {f['closed_before_created']:,} records closed before they were created (excluded); "
        f"{f['still_open']:,} still open at snapshot (reported separately as backlog).",
    ], width=118, size=12.5, gap=0.02)
    d.save(fig)

    # 4 As-is
    fig = d.new("As-is process", "Pain points (red) come from the data: misroutes, no-defect visits, no aging "
                "trigger, unpublished outcomes")
    _image(fig, FIGS / "process_as_is.png", [0.01, 0.06, 0.68, 0.77])
    _bullets(fig, 0.70, 0.77, ["Intake accepts any report as-is: no photo, asset-owner or permit check.",
                               "The inspector visit is the first filter, so no-defect and wrong-agency jobs "
                               "still cost a visit.",
                               "No aging trigger: old street-light outages sit in the queue.",
                               "Closure text often hides the outcome, so first-time-fix cannot be measured."],
             width=34, size=12, gap=0.025)
    d.save(fig)

    # 5 Pareto
    fig = d.new("Where the waiting happens",
                f"Street lights: {f['street_light_pct_requests']:.0f}% of requests, "
                f"{f['street_light_pct_request_days']:.0f}% of all waiting time")
    _image(fig, FIGS / "pareto_request_days.png", [0.03, 0.07, 0.62, 0.75])
    _bullets(fig, 0.67, 0.75, [f"The top 4 complaint types hold {f['top4_cum_pct_request_days']:.0f}% of request-days.",
                               f"Potholes are a success story: {f['pothole_pct_repaired']:.0f}% repaired, median "
                               f"{f['pothole_median_days']:.1f} days.",
                               "So the biggest lever for waiting time is street-light outages, not "
                               "pothole speed."], width=38, size=12)
    d.save(fig)

    # 6 Street light tail
    b_hi, b_lo = f["sl_borough_max"], f["sl_borough_min"]
    fig = d.new("Street Light Out: the long tail",
                f"{f['sl_tail_pct_requests']:.0f}% of outages wait more than 30 days and hold "
                f"{f['sl_tail_pct_request_days']:.0f}% of street-light waiting")
    _image(fig, FIGS / "street_light_tail.png", [0.02, 0.08, 0.5, 0.72])
    _image(fig, FIGS / "street_light_by_borough.png", [0.5, 0.3, 0.49, 0.5])
    _bullets(fig, 0.53, 0.27, [f"{b_hi['borough']}: fastest median ({b_hi['median']:.0f} d) but p90 "
                               f"{b_hi['p90']:.0f} d; {b_lo['borough']} p90 {b_lo['p90']:.0f} d.",
                               f"Jan-Apr requests: p90 {f['sl_winter_p90_range'][0]:.0f}-"
                               f"{f['sl_winter_p90_range'][1]:.0f} d vs {f['sl_july_p90']:.0f} d in July."],
             width=62, size=11)
    d.save(fig)

    # 7 Failure demand
    fig = d.new("Failure demand in Street Condition",
                f"{f['street_condition_failure_demand']:,} of {f['street_condition_requests']:,} requests "
                f"({f['street_condition_pct_failure_demand']:.0f}%) end without a DOT repair being possible")
    _image(fig, FIGS / "street_condition_failure_demand.png", [0.02, 0.07, 0.64, 0.76])
    _bullets(fig, 0.68, 0.75, [f"Cave-in: {f['cavein_pct_wrong_agency']:.0f}% referred elsewhere.",
                               f"Defective hardware: {f['hardware_pct_wrong_agency']:.0f}% referred.",
                               f"{r1['baseline']['pct_referred_to_dep']:.0f}% of these referrals go to DEP "
                               "(sewer and water).",
                               f"Blocked - Construction: {f['blocked_pct_no_defect']:.0f}% 'no defect', often a "
                               "permitted work site."], width=36, size=12)
    d.save(fig)

    # 8 Fishbone
    fig = d.new("Root causes", "Two process gaps explain most of it: intake has no screening, and nobody "
                "manages the aging backlog")
    _image(fig, FIGS / "fishbone.png", [0.02, 0.06, 0.96, 0.76])
    d.save(fig)

    # 9 To-be
    fig = d.new("To-be process", "Screen and route at intake, escalate at day 30, publish an outcome on every closure")
    _image(fig, FIGS / "process_to_be.png", [0.01, 0.06, 0.62, 0.77])
    _bullets(fig, 0.64, 0.77, ["R1: guided questions send sewer, manhole and utility conditions straight to "
                               "DEP or the utility.",
                               "R2: photo + map pin, a duplicate check and an active-permit check run before an "
                               "inspector is sent.",
                               "R3: any street-light outage still open on day 30 is escalated and listed in a "
                               "weekly aging report.",
                               "R4: every closure carries a standard outcome code that is published to Open Data."],
             width=40, size=12, gap=0.025)
    d.save(fig)

    # 10 Recommendations & impact
    fig = d.new("Recommendations and estimated impact", "Base case: "
                f"{r3['estimate']['base']['citizen_days_saved'] + r1['estimate']['base']['citizen_days_saved']:,} "
                f"citizen-days and {r1['estimate']['base']['handlings_avoided'] + r2['estimate']['base']['inspections_avoided']:,} "
                "DOT handlings avoided per year")
    rows = [
        ("R1", "Route sewer / utility cues at intake", f"{r1['baseline']['misrouted_requests']:,} misroutes",
         f"{r1['estimate']['base']['handlings_avoided']:,} handlings, {r1['estimate']['base']['citizen_days_saved']:,} citizen-days"),
        ("R2", "Photo + permit check before dispatch", f"{r2['baseline']['no_defect_inspections']:,} no-defect visits",
         f"{r2['estimate']['base']['inspections_avoided']:,} visits (~{r2['estimate']['base']['inspector_hours_freed']:,} h*)"),
        ("R3", "Day-30 escalation for street lights", f"{r3['baseline']['requests_over_threshold']:,} outages > 30 d",
         f"{r3['estimate']['base']['citizen_days_saved']:,} citizen-days; p90 {r3['baseline']['p90_days']:.0f}→"
         f"{r3['estimate']['base']['new_p90_days']:.0f} d"),
        ("R4", "Publish outcome code on every closure", f"{r4['baseline']['requests_without_published_outcome']:,} unpublished",
         "Outcome measurable for 100% of requests"),
    ]
    ys = 0.76
    for i, hdr in enumerate(["", "Change", "Addressable (2025)", "Base-case impact / year"]):
        fig.text([0.035, 0.07, 0.34, 0.51][i], ys, hdr, fontsize=11, fontweight="bold", color=GREY)
    for k, ch, addr, imp in rows:
        ys -= 0.062
        fig.text(0.035, ys, k, fontsize=13, fontweight="bold", color=TEAL)
        fig.text(0.07, ys, ch, fontsize=11.5)
        fig.text(0.34, ys, addr, fontsize=11.5)
        fig.text(0.51, ys, imp, fontsize=11.5, fontweight="bold", color=NAVY)
    fig.text(0.035, ys - 0.05, "* inspector-hours use an illustrative 1.5 h per visit (not in the data). Low/high "
             "ranges and all assumptions are in assumptions.toml.", fontsize=9, color=GREY)
    _image(fig, FIGS / "impact.png", [0.05, 0.05, 0.9, 0.40])
    d.save(fig)

    # 11 Roadmap & KPIs
    fig = d.new("Roadmap, KPIs and caveats", "Start with the cheap, measurable changes; prove impact before scaling")
    fig.text(0.035, 0.79, "90-day roadmap", fontsize=14, fontweight="bold", color=NAVY)
    _bullets(fig, 0.035, 0.74, ["Days 0-30: publish outcome codes (R4); weekly street-light aging report (R3).",
                                "Days 30-60: pilot routing questions for cave-in / hardware in one borough (R1).",
                                "Days 60-90: photo + permit check for construction-related descriptors (R2); "
                                "compare pilot vs control boroughs."], width=55, size=12)
    fig.text(0.52, 0.79, "KPIs to track", fontsize=14, fontweight="bold", color=NAVY)
    _bullets(fig, 0.52, 0.74, ["Street-light p90 days and % open > 30 days",
                               "Failure-demand rate by descriptor",
                               "Misroute rate and days to referral",
                               "% of closures with a published outcome code"], width=48, size=12)
    fig.text(0.035, 0.37, "Caveats", fontsize=14, fontweight="bold", color=RED)
    _bullets(fig, 0.035, 0.32, ["Public 311 data only: no crew capacity, cost or asset data, so impacts are in "
                                "days and visits, not dollars.",
                                "Closure time can reflect paperwork as well as repair. Outcome classes come from "
                                "DOT's free text using documented rules.",
                                "Estimates assume 2025 volumes repeat. Pilot results should replace the assumed "
                                "adoption rates."], width=120, size=11.5)
    d.save(fig)
    d.close()
    return out
