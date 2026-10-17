"""Build the DuckDB database from the raw extract and export every analysis result to CSV."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pandas as pd

from case_study.paths import DB, MANIFEST, RAW_CSV, SQL, TABLES


def snapshot_ts(manifest_path: Path = MANIFEST) -> str:
    """Snapshot time in New York local time (311 timestamps are NY local, without offset)."""
    if manifest_path.exists():
        utc = datetime.strptime(json.loads(manifest_path.read_text())["downloaded_utc"], "%Y-%m-%dT%H:%M:%SZ")
        utc = utc.replace(tzinfo=timezone.utc)
    else:
        utc = datetime.now(timezone.utc)
    return utc.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S")


def _render(sql: str, **params) -> str:
    for k, v in params.items():
        sql = sql.replace("{" + k + "}", str(v).replace("'", "''"))
    return sql


def build(con: duckdb.DuckDBPyConnection, raw_csv: Path = RAW_CSV, snapshot: str | None = None) -> None:
    params = {"raw_csv_path": Path(raw_csv).as_posix(), "snapshot_ts": snapshot or snapshot_ts()}
    for name in ("01_staging.sql", "02_outcomes.sql"):
        con.execute(_render((SQL / name).read_text(), **params))


def analysis_blocks(path: Path = SQL / "03_analysis.sql") -> dict[str, str]:
    """Split 03_analysis.sql into {name: query} using '-- name: x' headers."""
    blocks, name, buf = {}, None, []
    for line in path.read_text().splitlines():
        m = re.match(r"--\s*name:\s*(\w+)", line)
        if m:
            if name:
                blocks[name] = "\n".join(buf).strip().rstrip(";")
            name, buf = m.group(1), []
        elif name:
            buf.append(line)
    if name:
        blocks[name] = "\n".join(buf).strip().rstrip(";")
    return blocks


def run_analyses(con: duckdb.DuckDBPyConnection, out_dir: Path = TABLES) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, query in analysis_blocks().items():
        df = con.execute(query).df()
        df.to_csv(out_dir / f"{name}.csv", index=False)
        results[name] = df
    return results


def connect(db_path: Path | str = DB) -> duckdb.DuckDBPyConnection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True) if str(db_path) != ":memory:" else None
    con = duckdb.connect(str(db_path))
    con.execute("SET enable_progress_bar = false")
    return con


def run(raw_csv: Path = RAW_CSV, db_path: Path | str = DB, out_dir: Path = TABLES) -> dict[str, pd.DataFrame]:
    if not Path(raw_csv).exists():
        raise FileNotFoundError(f"{raw_csv} not found. Run: python scripts/download_data.py")
    con = connect(db_path)
    try:
        build(con, raw_csv)
        return run_analyses(con, out_dir)
    finally:
        con.close()
