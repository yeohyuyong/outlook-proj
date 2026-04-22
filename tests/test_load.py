import csv
from pathlib import Path

from src.load import ingest_all

FIXTURES = Path(__file__).parent / "fixtures"
FROZEN_NOW = "2026-04-22T00:00:00"


def test_ingest_all(tmp_path):
    entries_path = tmp_path / "entries.csv"
    runs_path = tmp_path / "runs.csv"
    n_runs, n_entries = ingest_all(
        reports_dir=FIXTURES,
        entries_path=entries_path,
        runs_path=runs_path,
        now=FROZEN_NOW,
    )
    assert n_runs == 2
    # apr15: 2 × 3 = 6; apr18: 1 cpi + 3 fed + 1 10y = 5; total 11
    assert n_entries == 11

    with entries_path.open(encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    assert len(rows) == 11
    assert {r["run_date"] for r in rows} == {"2026-04-15", "2026-04-18"}

    # Value column holds the numeric forecast and empty string for N/A
    values_by_source_var = {
        (r["source"], r["variable"]): r["value"] for r in rows if r["run_date"] == "2026-04-15"
    }
    assert values_by_source_var[("Goldman Sachs", "Core CPI YoY")] == "2.8"
    assert values_by_source_var[("Goldman Sachs", "US 10y Treasury Yield")] == ""  # was N/A


def test_idempotent(tmp_path):
    entries_path = tmp_path / "entries.csv"
    runs_path = tmp_path / "runs.csv"
    ingest_all(
        reports_dir=FIXTURES,
        entries_path=entries_path,
        runs_path=runs_path,
        now=FROZEN_NOW,
    )
    first_entries = entries_path.read_text()
    first_runs = runs_path.read_text()

    ingest_all(
        reports_dir=FIXTURES,
        entries_path=entries_path,
        runs_path=runs_path,
        now=FROZEN_NOW,
    )
    assert entries_path.read_text() == first_entries
    assert runs_path.read_text() == first_runs
