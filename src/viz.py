"""Plotly chart functions for the dashboard. Pure: (df) -> Figure."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import STALENESS_CUTOFF_DAYS, VARIABLES

_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def _variable_unit(name: str) -> str:
    for v in VARIABLES:
        if v["name"] == name:
            return v["unit"]
    return ""


def _source_color_map(sources: list[str]) -> dict[str, str]:
    return {s: _PALETTE[i % len(_PALETTE)] for i, s in enumerate(sorted(sources))}


_MONTHS_FWD_RE = re.compile(r"(\d+)\s*m(?:o(?:nths?)?)?\s*(?:forward|fwd|ahead|out)?", re.I)
_NEXT_N_RE = re.compile(r"next\s+(\d+)\s*m(?:o(?:nths?)?)?", re.I)
_YEAR_END_RE = re.compile(r"(?:year[- ]?end|end[- ]?of|end[- ])\s*(\d{4})", re.I)
_QUARTER_RE = re.compile(r"(\d{4})\s*Q([1-4])|Q([1-4])\s*(\d{4})", re.I)


def _horizon_to_date(horizon: str, source_date: pd.Timestamp) -> pd.Timestamp | None:
    """Parse a free-text horizon string into an approximate target date."""
    if not isinstance(horizon, str) or not horizon.strip():
        return None
    h = horizon.strip().lower()

    if "current calendar year" in h or "current year" in h or "year-end current year" in h:
        return pd.Timestamp(year=source_date.year, month=12, day=31)

    m = _YEAR_END_RE.search(h)
    if m:
        return pd.Timestamp(year=int(m.group(1)), month=12, day=31)

    m = _QUARTER_RE.search(h)
    if m:
        year = int(m.group(1) or m.group(4))
        q = int(m.group(2) or m.group(3))
        month = q * 3
        return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

    m = _NEXT_N_RE.search(h) or _MONTHS_FWD_RE.search(h)
    if m:
        months = int(m.group(1))
        return source_date + pd.DateOffset(months=months)

    return None


def forecast_term_structure(df: pd.DataFrame) -> go.Figure:
    """Viz 1b — same grid, but X is the target date parsed from the horizon field.

    Useful as a sanity check: points should cluster near each variable's canonical
    horizon. Scatter on X flags sources quoting off-horizon forecasts.
    """
    d = df.dropna(subset=["value"]).copy()
    d["source_date"] = pd.to_datetime(d["source_date"])
    d["target_date"] = d.apply(
        lambda r: _horizon_to_date(r["horizon"], r["source_date"]), axis=1
    )
    d = d.dropna(subset=["target_date"])

    variables = [v["name"] for v in VARIABLES]
    rows, cols = 2, 3
    titles = [f"{v} ({_variable_unit(v)})" for v in variables]
    fig = make_subplots(
        rows=rows, cols=cols, subplot_titles=titles,
        horizontal_spacing=0.08, vertical_spacing=0.16,
    )

    color_map = _source_color_map(d["source"].unique().tolist() if not d.empty else [])
    legend_shown: set[str] = set()

    for idx, variable in enumerate(variables):
        r, c = idx // cols + 1, idx % cols + 1
        sub = d[d["variable"] == variable]
        if sub.empty:
            continue
        for source, sub_src in sub.groupby("source"):
            sub_src = sub_src.sort_values("target_date")
            hover = [
                f"<b>{source}</b><br>"
                f"published: {row.source_date.date()}<br>"
                f"target: {row.target_date.date()}<br>"
                f"horizon: {row.horizon}<br>"
                f"value: {row.value} {row.unit}<br>"
                f"stance: {row.stance} / {row.conviction}<br>"
                f"{row.key_claim}<br>"
                f"<i>{row.source_title} — shift+click to open</i>"
                for row in sub_src.itertuples()
            ]
            show = source not in legend_shown
            legend_shown.add(source)
            fig.add_trace(
                go.Scatter(
                    x=sub_src["target_date"],
                    y=sub_src["value"],
                    mode="lines+markers",
                    name=source,
                    legendgroup=source,
                    showlegend=show,
                    line=dict(color=color_map.get(source, "#333"), dash="dot"),
                    marker=dict(
                        size=sub_src["conviction_n"].astype(float) * 4 + 4,
                        color=color_map.get(source, "#333"),
                    ),
                    hovertext=hover,
                    hoverinfo="text",
                    customdata=sub_src["source_url"].fillna("").tolist(),
                ),
                row=r, col=c,
            )

    fig.update_layout(
        title="Forecast term structure (X = target date parsed from horizon)",
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18),
        margin=dict(t=70, b=90, l=60, r=40),
    )
    return fig


def forecast_trajectories(df: pd.DataFrame) -> go.Figure:
    """Viz 1 — 6 small multiples, one per variable, lines per source."""
    d = df.dropna(subset=["value"]).copy()
    d["source_date"] = pd.to_datetime(d["source_date"])

    variables = [v["name"] for v in VARIABLES]
    rows, cols = 2, 3
    titles = [f"{v} ({_variable_unit(v)})" for v in variables]
    fig = make_subplots(
        rows=rows, cols=cols, subplot_titles=titles,
        horizontal_spacing=0.08, vertical_spacing=0.16,
    )

    color_map = _source_color_map(d["source"].unique().tolist() if not d.empty else [])
    legend_shown: set[str] = set()

    for idx, variable in enumerate(variables):
        r, c = idx // cols + 1, idx % cols + 1
        sub = d[d["variable"] == variable]
        if sub.empty:
            continue
        for source, sub_src in sub.groupby("source"):
            sub_src = sub_src.sort_values("source_date")
            hover = [
                f"<b>{source}</b><br>"
                f"{row.source_date.date()}<br>"
                f"value: {row.value} {row.unit}<br>"
                f"horizon: {row.horizon}<br>"
                f"stance: {row.stance} / {row.conviction}<br>"
                f"{row.key_claim}<br>"
                f"<i>{row.source_title} — shift+click to open</i>"
                for row in sub_src.itertuples()
            ]
            show = source not in legend_shown
            legend_shown.add(source)
            fig.add_trace(
                go.Scatter(
                    x=sub_src["source_date"],
                    y=sub_src["value"],
                    mode="lines+markers",
                    name=source,
                    legendgroup=source,
                    showlegend=show,
                    line=dict(color=color_map.get(source, "#333")),
                    marker=dict(
                        size=sub_src["conviction_n"].astype(float) * 4 + 4,
                        color=color_map.get(source, "#333"),
                    ),
                    hovertext=hover,
                    hoverinfo="text",
                    customdata=sub_src["source_url"].fillna("").tolist(),
                ),
                row=r, col=c,
            )

    fig.update_layout(
        title="Forecast trajectories by variable",
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18),
        margin=dict(t=70, b=90, l=60, r=40),
    )
    return fig


def source_presence_matrix(df: pd.DataFrame) -> go.Figure:
    """Viz 2 — source × run heatmap, colored by staleness."""
    if df.empty:
        return go.Figure().update_layout(title="Source presence (no data)")

    d = df.copy()
    d["run_date"] = pd.to_datetime(d["run_date"])

    run_dates = sorted(d["run_date"].unique())
    sources = (
        d.groupby("source").size().sort_values(ascending=False).index.tolist()
    )

    present = {(s, rd): False for s in sources for rd in run_dates}
    for (s, rd), _ in d.groupby(["source", "run_date"]):
        present[(s, rd)] = True

    z = np.full((len(sources), len(run_dates)), np.nan)
    for i, s in enumerate(sources):
        last_present: pd.Timestamp | None = None
        for j, rd in enumerate(run_dates):
            if present[(s, pd.Timestamp(rd))]:
                z[i, j] = 0.0
                last_present = pd.Timestamp(rd)
            elif last_present is not None:
                days = (pd.Timestamp(rd) - last_present).days
                z[i, j] = 1.0 if days <= STALENESS_CUTOFF_DAYS else 2.0

    variables_map: dict[tuple[str, pd.Timestamp], list[str]] = {}
    for (s, rd), grp in d.groupby(["source", "run_date"]):
        variables_map[(s, pd.Timestamp(rd))] = sorted(grp["variable"].unique())

    hover_text: list[list[str]] = []
    for i, s in enumerate(sources):
        row = []
        for j, rd in enumerate(run_dates):
            rd_ts = pd.Timestamp(rd)
            val = z[i, j]
            if np.isnan(val):
                row.append(f"<b>{s}</b><br>{rd_ts.date()}<br>not yet seen")
            elif val == 0.0:
                vars_ = ", ".join(variables_map.get((s, rd_ts), []))
                row.append(f"<b>{s}</b><br>{rd_ts.date()}<br>present — {vars_}")
            elif val == 1.0:
                row.append(f"<b>{s}</b><br>{rd_ts.date()}<br>stale")
            else:
                row.append(f"<b>{s}</b><br>{rd_ts.date()}<br>dropped")
        hover_text.append(row)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[pd.Timestamp(rd).date().isoformat() for rd in run_dates],
        y=sources,
        zmin=0, zmax=2,
        colorscale=[
            [0.0, "#2ca02c"],
            [0.5, "#ffbf00"],
            [1.0, "#aaaaaa"],
        ],
        showscale=False,
        text=hover_text,
        hoverinfo="text",
        xgap=2, ygap=2,
    ))
    fig.update_layout(
        title="Source presence matrix (green = present, yellow = stale, grey = dropped)",
        xaxis_title="Run date",
        yaxis_title="Source",
        height=max(300, len(sources) * 32 + 150),
        margin=dict(t=70, b=60, l=160, r=40),
    )
    return fig
