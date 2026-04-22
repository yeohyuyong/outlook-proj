# Macro Outlook Tracker

Six variables I'm tracking: Core CPI, Fed Funds, 10y Treasury, DXY, US GDP, Brent oil. Sources rotate — whoever the research tool surfaces that cycle. Two charts come out the end: forecast values over time, and a matrix of which sources have shown up recently.

## The 2-3 day loop

1. Paste `prompts/tracker_prompt.md` into the research assistant.
2. Save the response as `reports/YYYY-MM-DD.md`. Date has to match the H1 inside the file, otherwise the parser barfs.
3. `python -m src.cli ingest-all` — rebuilds both CSVs in `data/` from scratch by walking `reports/`.
4. Open `notebooks/dashboard.ipynb`, run all cells. If Jupyter isn't available on the laptop, run `python -m src.cli build-html` instead and open `data/dashboard.html` in a browser — same charts, self-contained (works offline, no server).

## Setup

```bash
pip install -r requirements.txt
pytest
python -m src.cli ingest-all
```

## Where things live

- `prompts/tracker_prompt.md`: paste into the research tool.
- `reports/*.md`: one markdown per cycle.
- `data/entries.csv`: parsed rows, one per source forecast.
- `data/runs.csv`: audit log.
- `src/`: parsing, CSV writing, charts.
- `notebooks/dashboard.ipynb`: the two charts.
- `tests/`: fixtures and unit tests.

## Changing the tracked variables

Edit `src/config.py` (the `VARIABLES` list) and the matching table in `prompts/tracker_prompt.md`. Keep them in sync. If the prompt asks for a variable that isn't in config the parser will silently drop that whole section, which is the kind of bug that wastes a cycle before you notice. Re-run `ingest-all` after.
