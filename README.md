# Macro Outlook Tracker

Six variables I'm tracking: Core CPI, Fed Funds, 10y Treasury, DXY, US GDP, Brent oil. Sources rotate — whoever the research tool surfaces that cycle. Two charts come out the end: forecast values over time, and a matrix of which sources have shown up recently.

## The 2-3 day loop

1. Substitute the scan-window dates into `prompts/tracker_prompt.md` and paste it into the research assistant. Save the response as `reports/tracker_YYYY-MM-DD.md` where the date matches the H1 inside the file, otherwise the parser barfs.
2. Substitute today's date into `prompts/spot_prompt.md` (`{{AS_OF_DATE}}`) and paste it into the research assistant — separately from the tracker run, since spot levels use public market data sources outside the internal research platform. Save the response as `reports/spot_YYYY-MM-DD.md`, again with date matching the H1.
3. `python -m src.cli ingest-all` — rebuilds all three CSVs in `data/` from scratch by walking `reports/`.
4. `python -m src.cli build-html` — renders `data/dashboard.html`. Self-contained (works offline, no server); open in a browser.

The `tracker_` / `spot_` filename prefixes are a human-ordering convention only — `parse.py` reads `run_date` from the H1, not the filename, and dispatches on H2 headings ([src/parse.py:173](src/parse.py#L173)). Older `reports/YYYY-MM-DD.md` files (from before the split, with both forecasts and spot in one file) continue to parse correctly.

## Setup

```bash
pip install -r requirements.txt
pytest
python -m src.cli ingest-all
```

## Where things live

- `prompts/tracker_prompt.md`: forecasts only. Paste into the internal research tool. Output → `reports/tracker_YYYY-MM-DD.md`.
- `prompts/spot_prompt.md`: current spot levels only. Uses public market data sources (BLS, FRED, ICE, EIA, etc.). Output → `reports/spot_YYYY-MM-DD.md`.
- `reports/*.md`: one or more markdowns per cycle (one tracker, one spot, plus any legacy combined files).
- `data/entries.csv`: parsed forecast rows, one per source.
- `data/current_levels.csv`: parsed spot rows, one per variable per spot run.
- `data/runs.csv`: audit log.
- `src/`: parsing, CSV writing, charts, HTML renderer.
- `tests/`: fixtures and unit tests.

## Changing the tracked variables

Edit `src/config.py` (the `VARIABLES` list) and the matching table in `prompts/tracker_prompt.md`. Keep them in sync. If the prompt asks for a variable that isn't in config the parser will silently drop that whole section, which is the kind of bug that wastes a cycle before you notice. Re-run `ingest-all` after.
