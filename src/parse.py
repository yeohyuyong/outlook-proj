"""Parse macro outlook tracker markdown reports into structured rows."""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .config import CONVICTION_TO_N, STANCE_TO_N, VARIABLE_NAMES

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

    conviction_raw = fields.get("conviction", "").lower()
    if conviction_raw not in CONVICTION_TO_N:
        log.warning(
            "entry %r has unrecognized conviction %r; defaulting to 'med'",
            source_title, conviction_raw,
        )
        conviction_raw = "med"
    conviction_canonical = "med" if conviction_raw == "medium" else conviction_raw

    return {
        "source_title": source_title,
        "source": fields.get("source", ""),
        "source_url": fields.get("source url", ""),
        "source_date": fields.get("source date", ""),
        "value": _coerce_float(fields.get("value", "")),
        "unit": fields.get("unit", ""),
        "horizon": fields.get("horizon", ""),
        "stance": stance_raw,
        "stance_n": STANCE_TO_N[stance_raw],
        "conviction": conviction_canonical,
        "conviction_n": CONVICTION_TO_N[conviction_raw],
        "key_claim": fields.get("key claim", ""),
        "evidence": fields.get("evidence", ""),
    }


def parse_report(path: Path) -> tuple[RunMeta, list[dict]]:
    """Parse one markdown report into (run metadata, list of entry rows)."""
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
    seen: set[tuple[str, str, str]] = set()

    for h2_heading, h2_body in _split_on_heading(text, 2):
        variable = _match_variable(h2_heading)
        if variable is None:
            log.warning("%s: H2 heading %r does not match any known variable", path, h2_heading)
            continue

        for h3_heading, h3_body in _split_on_heading(h2_body, 3):
            entry = _parse_entry(h3_heading, h3_body)
            if entry is None:
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

    return meta, rows
