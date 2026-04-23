"""Render the dashboard as a self-contained HTML file."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from . import viz
from .config import DATA_DIR, ENTRIES_CSV

DASHBOARD_HTML = DATA_DIR / "dashboard.html"


def build_html(
    entries_path: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    entries_path = entries_path or ENTRIES_CSV
    out_path = out_path or DASHBOARD_HTML

    df = pd.read_csv(entries_path, parse_dates=["run_date", "source_date"])

    fig1 = viz.forecast_trajectories(df)
    fig1b = viz.forecast_term_structure(df)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    generated = datetime.now().isoformat(timespec="seconds")

    with out_path.open("w", encoding="utf-8") as fp:
        fp.write(
            "<!DOCTYPE html>\n"
            "<html>\n<head>\n"
            "<meta charset='utf-8'>\n"
            "<title>Macro Outlook Tracker</title>\n"
            "<style>"
            "body{font-family:system-ui,-apple-system,sans-serif;"
            "max-width:1400px;margin:2em auto;padding:0 1em;color:#222}"
            "h1{margin-bottom:.2em}"
            ".meta{color:#888;font-size:.9em;margin-bottom:2em}"
            "</style>\n"
            "</head>\n<body>\n"
            "<h1>Macro Outlook Tracker</h1>\n"
            f"<p class='meta'>Generated {generated}</p>\n"
        )
        # Embed plotly.js inline on the first figure so the HTML works offline;
        # subsequent figures reuse the already-loaded library.
        fp.write(fig1.to_html(full_html=False, include_plotlyjs=True))
        fp.write(fig1b.to_html(full_html=False, include_plotlyjs=False))
        fp.write(
            "<script>\n"
            "document.querySelectorAll('.plotly-graph-div').forEach(function(el){\n"
            "  if (typeof el.on !== 'function') return;\n"
            "  el.on('plotly_click', function(data){\n"
            "    var ev = data && data.event;\n"
            "    if (!ev || !ev.shiftKey) return;\n"
            "    var p = data.points && data.points[0];\n"
            "    if (!p) return;\n"
            "    var url = p.customdata;\n"
            "    if (Array.isArray(url)) url = url[0];\n"
            "    if (url) window.open(url, '_blank', 'noopener');\n"
            "  });\n"
            "});\n"
            "</script>\n"
        )
        fp.write("</body>\n</html>\n")

    return out_path
