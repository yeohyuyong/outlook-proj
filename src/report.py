"""Render the dashboard as a self-contained HTML file."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from . import viz
from .config import DATA_DIR, ENTRIES_CSV, LEVELS_CSV

DASHBOARD_HTML = DATA_DIR / "dashboard.html"


def build_html(
    entries_path: Path | None = None,
    levels_path: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    entries_path = entries_path or ENTRIES_CSV
    levels_path = levels_path or LEVELS_CSV
    out_path = out_path or DASHBOARD_HTML

    df = pd.read_csv(entries_path, parse_dates=["run_date", "source_date"])

    levels_df = None
    if levels_path.exists():
        levels_df = pd.read_csv(levels_path, parse_dates=["run_date", "as_of_date"])

    fig1 = viz.forecast_chart(df, current_levels=levels_df)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    generated = datetime.now().isoformat(timespec="seconds")

    with out_path.open("w", encoding="utf-8") as fp:
        fp.write(
            "<!DOCTYPE html>\n"
            "<html>\n<head>\n"
            "<meta charset='utf-8'>\n"
            "<title>Macro Outlook Tracker</title>\n"
            "<style>"
            "*{box-sizing:border-box}"
            "body{font-family:system-ui,-apple-system,sans-serif;"
            "max-width:1440px;margin:2em auto;padding:0 1.5em;color:#222}"
            "h1{margin-bottom:.2em;font-size:1.5rem}"
            ".meta{color:#888;font-size:.85em;margin-bottom:1.5em}"
            ".legend-key{"
            "display:flex;flex-wrap:wrap;gap:.6em 1.4em;"
            "background:#f7f7f7;border:1px solid #e0e0e0;border-radius:6px;"
            "padding:.75em 1em;margin-bottom:1em;font-size:.82em;color:#444}"
            ".legend-key span{display:flex;align-items:center;gap:.4em;white-space:nowrap}"
            ".swatch{display:inline-block;width:28px;height:3px;border-radius:2px;flex-shrink:0}"
            "@media(max-width:900px){body{padding:0 .5em}}"
            "</style>\n"
            "</head>\n<body>\n"
            "<h1>Macro Outlook Tracker</h1>\n"
            f"<p class='meta'>Generated {generated}</p>\n"
        )
        fp.write(
            "<div class='legend-key'>"
            "<strong style='margin-right:.5em;color:#222'>How to read:</strong>"
            "<span><svg width='28' height='10'><line x1='0' y1='5' x2='14' y2='5' "
            "stroke='#555' stroke-width='2' stroke-dasharray='3,2'/>"
            "<circle cx='21' cy='5' r='4' fill='#555' fill-opacity='1'/></svg>"
            "Dot opacity = recency (brighter = newer forecast)</span>"
            "<span><svg width='28' height='10'><line x1='0' y1='5' x2='28' y2='5' "
            "stroke='#c0392b' stroke-width='2' stroke-dasharray='5,3'/></svg>"
            "Red dashed line = current spot level</span>"
            "<span>X-axis = forecast target date</span>"
            "<span>Shift+click a point to open the source report</span>"
            "</div>\n"
        )
        fp.write(fig1.to_html(full_html=False, include_plotlyjs=True))
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
