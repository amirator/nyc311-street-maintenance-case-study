"""Checks on the full 2025 snapshot and the committed results. Skipped if the raw file is absent."""

import json

import pytest

from conftest import ROOT

RAW = ROOT / "data" / "raw" / "nyc311_dot_2025.csv"
FINDINGS = ROOT / "reports" / "findings.json"


@pytest.mark.skipif(not RAW.exists(), reason="full dataset not downloaded")
def test_raw_matches_manifest():
    import hashlib

    m = json.loads((ROOT / "data" / "raw" / "manifest.json").read_text())
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == m["sha256"]
    with RAW.open(encoding="utf-8") as fh:
        import csv
        assert sum(1 for _ in csv.reader(fh)) - 1 == m["rows"]


def test_readme_numbers_match_findings():
    """Every headline number quoted in the README must equal the generated findings.json."""
    f = json.loads(FINDINGS.read_text())
    readme = (ROOT / "README.md").read_text()
    r1, r2, r3 = (f["impacts"][k] for k in ("R1", "R2", "R3"))
    expected = [
        f"{f['requests']:,}",
        f"{f['street_light_pct_requests']:.0f}% of requests",
        f"{f['street_light_pct_request_days']:.0f}% of all waiting time",
        f"{f['street_condition_pct_failure_demand']:.0f}%",
        f"{f['pct_outcome_not_published']:.0f}%",
        f"{r1['baseline']['misrouted_requests']:,}",
        f"{r2['baseline']['no_defect_inspections']:,}",
        f"{r3['estimate']['base']['citizen_days_saved']:,}",
        f"{f['sl_tail_pct_request_days']:.0f}%",
    ]
    missing = [e for e in expected if e not in readme]
    assert not missing, f"README out of date, missing: {missing}"
