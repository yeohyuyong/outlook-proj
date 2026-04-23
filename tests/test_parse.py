from pathlib import Path

from src.parse import parse_report

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_apr15():
    meta, entries = parse_report(FIXTURES / "2026-04-15.md")
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
    meta, entries = parse_report(FIXTURES / "2026-04-18.md")
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
