"""SQL pipeline + validation on the real 1% fixture."""

from case_study import validate


def test_validation_checks_pass_on_fixture(fixture_db, fixture_results):
    assert validate.run_checks(fixture_db, fixture_results, check_manifest=False) == []


def test_every_row_classified(fixture_db):
    n, classified = fixture_db.execute(
        "SELECT count(*), count(outcome) FROM fct_requests_enriched").fetchone()
    assert n == 2106 and classified == n


def test_negative_durations_flagged_not_used(fixture_db):
    flagged, leaked = fixture_db.execute("""
        SELECT sum(dq_closed_before_created::INT), sum((days_to_close < 0)::INT) FROM fct_requests_enriched
    """).fetchone()
    assert leaked in (0, None)
    assert flagged >= 0


def test_pareto_is_cumulative_and_sorted(fixture_results):
    par = fixture_results["pareto_request_days"]
    assert par["request_days"].is_monotonic_decreasing
    assert par["cum_pct_request_days"].is_monotonic_increasing
    assert abs(par["cum_pct_request_days"].iloc[-1] - 100) < 0.1


def test_open_requests_have_age_not_duration(fixture_db):
    bad, = fixture_db.execute("""
        SELECT count(*) FROM fct_requests_enriched
        WHERE (NOT is_closed AND (days_to_close IS NOT NULL OR open_age_days IS NULL))
           OR (is_closed AND open_age_days IS NOT NULL)""").fetchone()
    assert bad == 0


def test_mojibake_repaired(fixture_db):
    n, = fixture_db.execute(
        "SELECT count(*) FROM fct_requests_enriched WHERE resolution_description LIKE '%â%'").fetchone()
    assert n == 0


def test_analysis_blocks_all_present():
    from case_study.pipeline import analysis_blocks

    assert set(analysis_blocks()) >= {"data_quality", "pareto_request_days", "street_light_tail",
                                      "street_condition_by_descriptor", "open_backlog"}
