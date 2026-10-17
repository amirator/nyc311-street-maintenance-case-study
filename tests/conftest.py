import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
FIXTURE = ROOT / "tests" / "fixtures" / "dot311_2025_sample.csv"


@pytest.fixture(scope="session")
def fixture_db():
    from case_study import pipeline

    con = pipeline.connect(":memory:")
    pipeline.build(con, FIXTURE, snapshot="2026-10-17 07:56:07")
    yield con
    con.close()


@pytest.fixture(scope="session")
def fixture_results(fixture_db, tmp_path_factory):
    from case_study import pipeline

    return pipeline.run_analyses(fixture_db, tmp_path_factory.mktemp("tables"))
