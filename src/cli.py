"""Command-line interface for the tracker."""
from __future__ import annotations

import argparse
import logging

from .load import ingest_all


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="outlook-tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest-all", help="parse every reports/*.md and rebuild data/*.csv")
    sub.add_parser("build-html", help="rebuild CSVs and render a self-contained data/dashboard.html")

    args = parser.parse_args(argv)

    if args.cmd == "ingest-all":
        n_runs, n_entries = ingest_all()
        print(f"ingested {n_runs} runs, {n_entries} entries")
        return 0

    if args.cmd == "build-html":
        n_runs, n_entries = ingest_all()
        print(f"ingested {n_runs} runs, {n_entries} entries")
        from .report import build_html
        path = build_html()
        print(f"wrote {path}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
