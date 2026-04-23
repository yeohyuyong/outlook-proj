import csv
import shutil
from pathlib import Path

from src.load import ingest_all

FIXTURES = Path(__file__).parent / "fixtures"
FROZEN_NOW = "2026-04-22T00:00:00"
SECOND_NOW = "2026-04-23T00:00:00"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def test_ingest_all(tmp_path):
    entries_path = tmp_path / "entries.csv"
    runs_path = tmp_path / "runs.csv"
    levels_path = tmp_path / "current_levels.csv"
    n_runs, n_entries = ingest_all(
        reports_dir=FIXTURES,
        entries_path=entries_path,
        runs_path=runs_path,
        levels_path=levels_path,
        now=FROZEN_NOW,
    )
    assert n_runs == 2
    # apr15: 2 × 3 = 6; apr18: 1 cpi + 3 fed + 1 10y = 5; total 11
    assert n_entries == 11

    rows = _read_csv(entries_path)
    assert len(rows) == 11
    assert {r["run_date"] for r in rows} == {"2026-04-15", "2026-04-18"}

    # Value column holds the numeric forecast and empty string for N/A
    values_by_source_var = {
        (r["source"], r["variable"]): r["value"] for r in rows if r["run_date"] == "2026-04-15"
    }
    assert values_by_source_var[("Goldman Sachs", "Core CPI YoY")] == "2.8"
    assert values_by_source_var[("Goldman Sachs", "US 10y Treasury Yield")] == ""  # was N/A

    assert levels_path.exists()
    assert _read_csv(levels_path) == []


def test_idempotent_preserves_run_timestamps_for_unchanged_files(tmp_path):
    entries_path = tmp_path / "entries.csv"
    runs_path = tmp_path / "runs.csv"
    levels_path = tmp_path / "current_levels.csv"
    ingest_all(
        reports_dir=FIXTURES,
        entries_path=entries_path,
        runs_path=runs_path,
        levels_path=levels_path,
        now=FROZEN_NOW,
    )
    first_entries = entries_path.read_text()
    first_runs = runs_path.read_text()

    ingest_all(
        reports_dir=FIXTURES,
        entries_path=entries_path,
        runs_path=runs_path,
        levels_path=levels_path,
        now=SECOND_NOW,
    )
    assert entries_path.read_text() == first_entries
    assert runs_path.read_text() == first_runs


def test_changed_file_gets_new_ingested_at_without_rewriting_unchanged_rows(tmp_path):
    reports_dir = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, reports_dir)

    entries_path = tmp_path / "entries.csv"
    runs_path = tmp_path / "runs.csv"
    levels_path = tmp_path / "current_levels.csv"

    ingest_all(
        reports_dir=reports_dir,
        entries_path=entries_path,
        runs_path=runs_path,
        levels_path=levels_path,
        now=FROZEN_NOW,
    )

    target = reports_dir / "2026-04-18.md"
    target.write_text(
        target.read_text().replace("**Value:** 4.20", "**Value:** 4.10"),
        encoding="utf-8",
    )

    ingest_all(
        reports_dir=reports_dir,
        entries_path=entries_path,
        runs_path=runs_path,
        levels_path=levels_path,
        now=SECOND_NOW,
    )

    rows = _read_csv(runs_path)
    timestamps = {Path(row["file_path"]).name: row["ingested_at"] for row in rows}

    assert timestamps["2026-04-15.md"] == FROZEN_NOW
    assert timestamps["2026-04-18.md"] == SECOND_NOW
