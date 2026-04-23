"""Parse macro outlook tracker markdown reports into structured rows."""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import STANCE_TO_N, VARIABLE_NAMES

log = logging.getLogger(__name__)


@dataclass
class RunMeta:
    run_date: str
    file_path: str
    file_sha256: str


H1_RE = re.compile(r"^#\s*Macro Outlook Tracker:\s*(\d{4}-\d{2}-\d{2})", re.M)
FIELD_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.*?)\s*$", re.M)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_date_delta_days(run_iso: str, source_iso: str) -> int | None:
    """Days from source_date to run_date. None if either is not ISO YYYY-MM-DD."""
    try:
        return (date.fromisoformat(run_iso) - date.fromisoformat(source_iso)).days
    except ValueError:
        return None


def _coerce_float(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r"[,\s%$]", "", raw).strip()
    if cleaned.lower() in {"n/a", "na", "none", "null", "-", ""}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        log.warning("could not parse value as float: %r", raw)
        return None


def _coerce_horizon_months(raw: str) -> int | None:
    """Integer 1..18, or None if missing / N/A (e.g. US Real GDP Growth) / invalid."""
    if not raw:
        return None
    cleaned = raw.strip()
    if cleaned.lower() in {"n/a", "na", "none", "null", "-", ""}:
        return None
    try:
        n = int(cleaned)
    except ValueError:
        log.warning("could not parse horizon_months as int: %r", raw)
        return None
    if n < 1 or n > 18:
        log.warning("horizon_months %d out of [1, 18]; storing as None", n)
        return None
    return n


def _split_on_heading(text: str, level: int) -> list[tuple[str, str]]:
    """Split markdown on H<level> headings. Returns (heading_text, body) tuples."""
    prefix = "#" * level + " "
    pattern = re.compile(rf"^{re.escape(prefix)}(.+?)\s*$", re.M)
    matches = list(pattern.finditer(text))
    blocks: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append((m.group(1).strip(), text[start:end]))
    return blocks


def _match_variable(heading: str) -> str | None:
    core = re.sub(r"\s*\([^)]*\)\s*$", "", heading).strip()
    for name in VARIABLE_NAMES:
        if name.lower() == core.lower():
            return name
    return None


def _parse_entry(source_title: str, body: str) -> dict | None:
    fields: dict[str, str] = {}
    for m in FIELD_RE.finditer(body):
        fields[m.group(1).strip().lower()] = m.group(2).strip()

    stance_raw = fields.get("stance", "").lower()
    if stance_raw not in STANCE_TO_N:
        log.warning("entry %r has unrecognized stance %r; skipping", source_title, stance_raw)
        return None

    return {
        "source_title": source_title,
        "source": fields.get("source", ""),
        "source_url": fields.get("source url", ""),
        "source_date": fields.get("source date", ""),
        "value": _coerce_float(fields.get("value", "")),
        "unit": fields.get("unit", ""),
        "horizon": fields.get("horizon", ""),
        "horizon_months": _coerce_horizon_months(fields.get("horizon (months)", "")),
        "stance": stance_raw,
        "stance_n": STANCE_TO_N[stance_raw],
        "key_claim": fields.get("key claim", ""),
        "evidence": fields.get("evidence", ""),
    }


def _parse_spot_table(body: str, run_date: str) -> list[dict]:
    """Extract spot rows from the body of a `## Current Spot Levels` H2 section.

    Accepts both 4-column (legacy) and 5-column (with Source URL) tables.
    """
    rows: list[dict] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) not in (4, 5):
            continue
        if cells[0].lower() == "variable":
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        variable_raw, spot_raw, as_of, source = cells[:4]
        source_url = cells[4] if len(cells) == 5 else ""
        variable = next(
            (v for v in VARIABLE_NAMES if v.lower() == variable_raw.lower()), None
        )
        if variable is None:
            log.warning("spot table: unknown variable %r", variable_raw)
            continue
        rows.append({
            "run_date": run_date,
            "variable": variable,
            "value": _coerce_float(spot_raw),
            "as_of_date": as_of,
            "source": source,
            "source_url": source_url,
        })
    return rows


def parse_report(path: Path) -> tuple[RunMeta, list[dict], list[dict]]:
    """Parse one markdown report into (run metadata, entry rows, spot rows)."""
    text = path.read_text(encoding="utf-8")

    m = H1_RE.search(text)
    if not m:
        raise ValueError(f"{path}: missing H1 header '# Macro Outlook Tracker: YYYY-MM-DD'")
    run_date = m.group(1)

    meta = RunMeta(
        run_date=run_date,
        file_path=str(path),
        file_sha256=_sha256_file(path),
    )

    rows: list[dict] = []
    spot_rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for h2_heading, h2_body in _split_on_heading(text, 2):
        if h2_heading.strip().lower().startswith("current spot levels"):
            spot_rows.extend(_parse_spot_table(h2_body, run_date))
            continue

        variable = _match_variable(h2_heading)
        if variable is None:
            log.warning("%s: H2 heading %r does not match any known variable", path, h2_heading)
            continue

        for h3_heading, h3_body in _split_on_heading(h2_body, 3):
            entry = _parse_entry(h3_heading, h3_body)
            if entry is None:
                continue

            delta = _source_date_delta_days(run_date, entry["source_date"])
            if delta is None:
                log.warning(
                    "%s: entry %r has missing or non-ISO source_date %r; skipping",
                    path, h3_heading, entry["source_date"],
                )
                continue
            if delta < 0:
                log.warning(
                    "%s: entry %r source_date %s is after run_date %s; skipping",
                    path, h3_heading, entry["source_date"], run_date,
                )
                continue

            dedup_key = (variable, entry["source"], entry["source_date"])
            if dedup_key in seen:
                log.warning(
                    "%s: duplicate entry for %s / %s / %s; keeping first",
                    path, variable, entry["source"], entry["source_date"],
                )
                continue
            seen.add(dedup_key)

            entry["run_date"] = run_date
            entry["variable"] = variable
            rows.append(entry)

    return meta, rows, spot_rows
