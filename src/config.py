"""Configuration for the macro outlook tracker."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"
ENTRIES_CSV = DATA_DIR / "entries.csv"
RUNS_CSV = DATA_DIR / "runs.csv"

VARIABLES = [
    {
        "name": "Core CPI YoY",
        "unit": "%",
        "horizon": "next 12 months",
        "stance_semantics": "bullish = higher/stickier; bearish = lower/faster disinflation",
    },
    {
        "name": "Fed Funds Rate",
        "unit": "%",
        "horizon": "year-end current year",
        "stance_semantics": "bullish = hawkish (higher path); bearish = dovish",
    },
    {
        "name": "US 10y Treasury Yield",
        "unit": "%",
        "horizon": "12 months forward",
        "stance_semantics": "bullish = higher yields; bearish = lower yields",
    },
    {
        "name": "DXY Index",
        "unit": "idx",
        "horizon": "12 months forward",
        "stance_semantics": "bullish = stronger USD",
    },
    {
        "name": "US Real GDP Growth",
        "unit": "%",
        "horizon": "current calendar year",
        "stance_semantics": "bullish = above consensus / accelerating",
    },
    {
        "name": "Brent Oil",
        "unit": "$/bbl",
        "horizon": "12 months forward",
        "stance_semantics": "bullish = higher prices",
    },
    {
        "name": "S&P 500",
        "unit": "idx",
        "horizon": "12 months forward",
        "stance_semantics": "bullish = higher prices / above target",
    },
]

VARIABLE_NAMES = [v["name"] for v in VARIABLES]

STANCE_TO_N = {"bullish": 1, "neutral": 0, "bearish": -1}
