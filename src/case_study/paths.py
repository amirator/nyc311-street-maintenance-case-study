from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "raw" / "nyc311_dot_2025.csv"
MANIFEST = ROOT / "data" / "raw" / "manifest.json"
DB = ROOT / "data" / "nyc311.duckdb"
SQL = ROOT / "sql"
TABLES = ROOT / "reports" / "tables"
FIGS = ROOT / "docs" / "img"
REPORTS = ROOT / "reports"
MAPS = ROOT / "process_maps"
ASSUMPTIONS = ROOT / "assumptions.toml"
