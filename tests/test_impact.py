import numpy as np
import pytest

from case_study import impact


def test_simulate_tail_only_touches_requests_over_threshold():
    days = np.array([1, 10, 30, 40, 130])
    out = impact.simulate_tail(days, 30, 0.5)
    assert out.tolist() == [1, 10, 30, 35, 80]


def test_simulate_tail_full_recovery_caps_at_threshold():
    assert impact.simulate_tail(np.array([5.0, 90.0]), 30, 1.0).max() == 30


@pytest.fixture(scope="module")
def impacts(fixture_db):
    a = impact.load_assumptions()
    for sec in ("r1_intake_routing", "r2_pre_dispatch_screening"):
        a[sec]["min_requests"] = 5  # the fixture is a 1% sample
    return {im.key: im for im in impact.compute(fixture_db, a)}


def test_scenarios_are_ordered(impacts):
    for im in impacts.values():
        for metric in im.estimate["base"]:
            lo, base, hi = (im.estimate[s][metric] for s in ("low", "base", "high"))
            if metric.startswith(("new_", "mean_days_after")):
                assert lo >= base >= hi, (im.key, metric)  # bigger change -> shorter waits
            elif metric != "mean_days_before":
                assert lo <= base <= hi, (im.key, metric)


def test_r3_savings_equal_recovered_excess(impacts):
    r3 = impacts["R3"]
    expected = r3.baseline["excess_days_over_threshold"] * 0.5
    assert abs(r3.estimate["base"]["citizen_days_saved"] - expected) <= 1


def test_r1_scope_is_data_driven(impacts):
    assert "Cave-in" in impacts["R1"].scope
    assert impacts["R1"].baseline["misrouted_requests"] > 0


def test_assumptions_file_has_all_sections():
    a = impact.load_assumptions()
    assert {"r1_intake_routing", "r2_pre_dispatch_screening", "r3_street_light_aging"} <= set(a)
