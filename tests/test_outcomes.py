"""The outcome classifier (sql/02_outcomes.sql) on real DOT resolution texts."""

import duckdb
import pytest

from conftest import ROOT

CASES = [
    ("The Department of Transportation inspected this complaint and repaired the problem.", "Repaired / completed"),
    ("The Department of Transportation has completed the request or corrected the condition.", "Repaired / completed"),
    ("The Department of Transportation determined that this complaint is a duplicate of a previously filed "
     "complaint. The original complaint is being addressed.", "Duplicate"),
    ("The Department of Transportation inspected and has requested the Department of Environmental Protection "
     "address the issue. The condition will be re-inspected in 60 days.", "Wrong agency / referred"),
    ("The Department of Transportation has determined that this issue is not within its jurisdiction.",
     "Wrong agency / referred"),
    ("The Department of Transportation inspected this complaint and did not find the reported problem.",
     "No defect found"),
    ("The Department of Transportation inspected the condition you reported and found that the condition meets "
     "its standards and/or there is a valid permit to conduct work.", "No defect found"),
    ("The Department of Transportation inspected the condition and issued a Corrective Action Repair (CAR) to the "
     "contractor or utility company.", "Third party must repair"),
    ("The Department of Transportation inspected the condition and made the determination that the street meets "
     "resurfacing standards and will be planned for either the next or future resurfacing seasons (2 - 3 years).",
     "Deferred to planned work"),
    ("The Department of Transportation investigated this request and determined this street requires a "
     "reconstruction project.", "Deferred to planned work"),
    ("The request submitted did not have sufficient information for the Department of Transportation to respond.",
     "Insufficient information"),
    ("Service Request status for this request is available on the Department of Transportation's website. "
     "Please click the 'Learn More' link below.", "Outcome not published"),
    ("", "No resolution text"),
]


@pytest.fixture(scope="module")
def classify():
    con = duckdb.connect()
    sql = (ROOT / "sql" / "02_outcomes.sql").read_text()

    def run(text):
        con.execute("CREATE OR REPLACE TABLE fct_requests AS SELECT ?::VARCHAR AS resolution_description", [text])
        con.execute(sql)
        return con.execute("SELECT outcome FROM fct_requests_outcome").fetchone()[0]

    return run


@pytest.mark.parametrize("text,expected", CASES)
def test_classifier(classify, text, expected):
    assert classify(text) == expected
