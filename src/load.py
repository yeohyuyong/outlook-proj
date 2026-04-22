"""Ingest all reports and rebuild data/entries.csv + data/runs.csv."""
from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

from .config import ENTRIES_CSV, REPORTS_DIR, RUNS_CSV
from .parse import parse_report

log = logging.getLogger(__name__)

ENTRY_COLUMNS = [
    "run_date", "variable", "source", "source_title", "source_url",
    "source_date", "value", "unit", "horizon",
    "stance", "stance_n", "conviction", "conviction_n",
    "key_claim", "evidence",
]

RUN_COLUMNS = [
    "run_date", "file_path", "file_sha256", "n_entries", "ingested_at",
]


def _atomic_write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    tmp.replace(path)


def ingest_all(
    reports_dir: Path | None = None,
    entries_path: Path | None = None,
    runs_path: Path | None = None,
    now: str | None = None,
) -> tuple[int, int]:
    """Parse every *.md in reports/, rebuild entries.csv + runs.csv.

    Returns (n_runs, n_entries).
    `now` can be passed for deterministic tests; defaults to current timestamp.
    """
    reports_dir = reports_dir or REPORTS_DIR
    entries_path = entries_path or ENTRIES_CSV
    runs_path = runs_path or RUNS_CSV
    ingested_at = now or datetime.now().isoformat(timespec="seconds")

    md_files = sorted(p for p in reports_dir.glob("*.md"))

    all_entries: list[dict] = []
    run_rows: list[dict] = []

    for path in md_files:
        try:
            meta, entries = parse_report(path)
        except ValueError as e:
            log.error("skipping %s: %s", path, e)
            continue
        all_entries.extend(entries)
        run_rows.append({
            "run_date": meta.run_date,
            "file_path": meta.file_path,
            "file_sha256": meta.file_sha256,
            "n_entries": len(entries),
            "ingested_at": ingested_at,
        })

    _atomic_write_csv(entries_path, ENTRY_COLUMNS, all_entries)
    _atomic_write_csv(runs_path, RUN_COLUMNS, run_rows)

    log.info("ingested %d runs, %d entries", len(run_rows), len(all_entries))
    return len(run_rows), len(all_entries)
