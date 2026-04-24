"""Plotly chart functions for the dashboard. Pure: (df) -> Figure."""
from __future__ import annotations

import re

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import VARIABLES

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


_RECENCY_FLOOR = 0.05
_RECENCY_HALF_LIFE_DAYS = 30


def _recency_opacity(source_dates: pd.Series, today: pd.Timestamp) -> list[float]:
    """Map publication age to marker opacity. Halves every _RECENCY_HALF_LIFE_DAYS."""
    age = (today - pd.to_datetime(source_dates)).dt.days.clip(lower=0)
    op = (0.5 ** (age / _RECENCY_HALF_LIFE_DAYS)).clip(lower=_RECENCY_FLOOR)
    return op.tolist()


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.3f})"


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


def forecast_chart(
    df: pd.DataFrame,
    current_levels: pd.DataFrame | None = None,
) -> go.Figure:
    """Forward-looking outlook by variable. X = target date parsed from horizon."""
    today = pd.Timestamp.now().normalize()
    d = df.dropna(subset=["value"]).copy()
    d["source_date"] = pd.to_datetime(d["source_date"])

    def _target(r: pd.Series) -> pd.Timestamp | None:
        n = r.get("horizon_months") if "horizon_months" in r else None
        if pd.notna(n):
            try:
                return r["source_date"] + pd.DateOffset(months=int(n))
            except (TypeError, ValueError):
                pass
        return _horizon_to_date(r["horizon"], r["source_date"])

    d["target_date"] = d.apply(_target, axis=1)
    d = d.dropna(subset=["target_date"])

    variables = [v["name"] for v in VARIABLES]
    rows, cols = 2, 4
    titles = [f"{v} ({_variable_unit(v)})" for v in variables]
    titles += [""] * (rows * cols - len(titles))
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
                f"stance: {row.stance}<br>"
                f"{row.key_claim}<br>"
                f"<i>{row.source_title} — shift+click to open</i>"
                for row in sub_src.itertuples()
            ]
            show = source not in legend_shown
            legend_shown.add(source)
            color = color_map.get(source, "#333")
            opacities = _recency_opacity(sub_src["source_date"], today)
            line_opacity = sum(opacities) / len(opacities)
            fig.add_trace(
                go.Scatter(
                    x=sub_src["target_date"],
                    y=sub_src["value"],
                    mode="lines+markers",
                    name=source,
                    legendgroup=source,
                    showlegend=show,
                    line=dict(color=_hex_to_rgba(color, line_opacity), dash="dot"),
                    marker=dict(
                        size=10,
                        color=color,
                        opacity=opacities,
                    ),
                    hovertext=hover,
                    hoverinfo="text",
                    customdata=sub_src["source_url"].fillna("").tolist(),
                ),
                row=r, col=c,
            )

    if current_levels is not None and not current_levels.empty:
        latest = (
            current_levels.dropna(subset=["value"])
            .sort_values("as_of_date")
            .groupby("variable")
            .last()
        )
        x_left = today
        x_right = today + pd.DateOffset(months=12)
        for idx, variable in enumerate(variables):
            if variable not in latest.index:
                continue
            r, c = idx // cols + 1, idx % cols + 1
            spot = latest.loc[variable, "value"]
            source = latest.loc[variable, "source"]
            as_of = pd.to_datetime(latest.loc[variable, "as_of_date"]).date()
            url = latest.loc[variable, "source_url"] if "source_url" in latest.columns else ""
            url = url if isinstance(url, str) else ""
            hint = "<i>shift+click to open source</i>" if url else ""
            hover = (
                f"<b>now: {spot}</b><br>"
                f"{source}<br>"
                f"as of {as_of}"
                + (f"<br>{hint}" if hint else "")
            )
            fig.add_trace(
                go.Scatter(
                    x=[x_left, x_right],
                    y=[spot, spot],
                    mode="lines",
                    line=dict(color="#c0392b", dash="dash", width=1.2),
                    hovertext=[hover, hover],
                    hoverinfo="text",
                    customdata=[url, url],
                    showlegend=False,
                    name=f"spot — {variable}",
                ),
                row=r, col=c,
            )

    fig.update_xaxes(range=[today, today + pd.DateOffset(months=12)], title_text="Horizon")

    fig.update_layout(
        title=dict(
            text="Forecast outlook by variable",
            font=dict(size=15),
            x=0,
            xanchor="left",
        ),
        height=820,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.14,
            font=dict(size=11),
        ),
        margin=dict(t=55, b=110, l=60, r=40),
    )
    return fig


