from pathlib import Path

from src.parse import parse_report

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_apr15():
    meta, entries, _spot = parse_report(FIXTURES / "2026-04-15.md")
    assert meta.run_date == "2026-04-15"
    assert len(entries) == 6  # 3 variables × 2 sources

    by_var: dict[str, list[dict]] = {}
    for e in entries:
        by_var.setdefault(e["variable"], []).append(e)

    assert set(by_var) == {"Core CPI YoY", "Fed Funds Rate", "US 10y Treasury Yield"}

    goldman_cpi = next(e for e in by_var["Core CPI YoY"] if e["source"] == "Goldman Sachs")
    assert goldman_cpi["value"] == 2.8
    assert goldman_cpi["stance"] == "bearish"
    assert goldman_cpi["stance_n"] == -1
    assert goldman_cpi["unit"] == "%"
    assert goldman_cpi["source_date"] == "2026-04-10"

    # N/A value coerces to None
    goldman_10y = next(e for e in by_var["US 10y Treasury Yield"] if e["source"] == "Goldman Sachs")
    assert goldman_10y["value"] is None
    assert goldman_10y["stance"] == "bearish"


def test_parse_apr18_source_churn():
    meta, entries, _spot = parse_report(FIXTURES / "2026-04-18.md")
    assert meta.run_date == "2026-04-18"

    by_var: dict[str, list[dict]] = {}
    for e in entries:
        by_var.setdefault(e["variable"], []).append(e)

    # Goldman dropped out of Core CPI vs apr15
    cpi_sources = {e["source"] for e in by_var.get("Core CPI YoY", [])}
    assert cpi_sources == {"JPMorgan"}

    # Morgan Stanley appeared in Fed Funds
    fed_sources = {e["source"] for e in by_var.get("Fed Funds Rate", [])}
    assert "Morgan Stanley" in fed_sources
    assert len(by_var["Fed Funds Rate"]) == 3


def _entry_block(title, source, url, src_date, value, stance):
    return (
        f"### {title}\n"
        f"**Source:** {source}\n"
        f"**Source URL:** {url}\n"
        f"**Source date:** {src_date}\n"
        f"**Value:** {value}\n"
        f"**Unit:** %\n"
        f"**Horizon:** 12m forward\n"
        f"**Stance:** {stance}\n"
        f"**Key claim:** claim\n"
        f"**Evidence:** evidence\n\n"
    )


def test_parse_drops_out_of_window_and_undated(tmp_path):
    report = tmp_path / "2026-04-23.md"
    body = (
        "# Macro Outlook Tracker: 2026-04-23\n\n"
        "## Core CPI YoY (%)\n\n"
        # in-window: 3 days old → kept
        + _entry_block("In-window note", "Goldman Sachs", "https://x/1", "2026-04-20", "2.7", "bearish")
        # out-of-window: 8 days old → dropped
        + _entry_block("Too-old note", "JPMorgan", "https://x/2", "2026-04-15", "3.0", "bullish")
        # undated → dropped
        + _entry_block("Undated note", "Citi", "https://x/3", "TBD", "2.5", "neutral")
        # on the start boundary: exactly 7 days → kept (inclusive)
        + _entry_block("Boundary note", "Morgan Stanley", "https://x/4", "2026-04-16", "2.6", "bullish")
        # future-dated: negative delta → dropped
        + _entry_block("Future note", "Barclays", "https://x/5", "2026-04-25", "2.9", "bullish")
    )
    report.write_text(body)

    _meta, entries, _spot = parse_report(report)
    sources = {e["source"] for e in entries}
    assert sources == {"Goldman Sachs", "Morgan Stanley"}
