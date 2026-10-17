"""python -m case_study [all|build|figures|slides|validate]"""

from __future__ import annotations

import argparse
import sys

from case_study.paths import DB, FIGS, RAW_CSV, REPORTS


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m case_study", description=__doc__)
    ap.add_argument("step", nargs="?", default="all", choices=["all", "build", "figures", "slides", "validate"])
    args = ap.parse_args(argv)
    sys.path.insert(0, str(RAW_CSV.parents[2] / "scripts"))

    if not RAW_CSV.exists():
        print("Raw data not found; downloading (about 212k rows, a few minutes)...")
        import download_data  # noqa: E402
        sys.argv = ["download_data.py"]
        download_data.main()

    from case_study import charts, findings, impact, pipeline, process_maps, slides, validate

    print("1/5 Building DuckDB model and running SQL analyses...")
    res = pipeline.run()
    con = pipeline.connect(DB)
    try:
        impacts = impact.compute(con)
        impact.export(impacts)
        print("2/5 Validating data and results...")
        problems = validate.run_checks(con, res)
    finally:
        con.close()
    for p in problems:
        print(f"  FAIL {p}")
    if problems:
        return 1
    print("  all checks passed")
    if args.step in ("build", "validate"):
        return 0
    f = findings.collect(res, impacts)
    findings.save(f)
    print("3/5 Drawing figures...")
    charts.pareto(res["pareto_request_days"])
    charts.street_light_tail(res["street_light_tail"])
    charts.borough(res["street_light_by_borough"])
    charts.failure_demand(res["street_condition_by_descriptor"])
    charts.fishbone(findings.fishbone_evidence(f))
    charts.impact_chart(impacts)
    print("4/5 Rendering process maps...")
    process_maps.render(f)
    if args.step == "figures":
        return 0
    print("5/5 Building slide deck...")
    pdf = slides.build(f)
    print(f"\nDone. Slides: {pdf.relative_to(REPORTS.parent)}  Figures: {FIGS.relative_to(REPORTS.parent)}/  "
          f"Tables: reports/tables/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
