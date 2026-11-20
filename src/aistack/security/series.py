"""
The measures over time (ADR-0028 slice T4a): `security-series.jsonl`.

At each pass the vigil appends one line, `{"at", "collected_at", "window",
"measures"}`, taken from the report the assessment just wrote. The page of
slice T4b draws its graphs from this file. Counts only (see
`aistack.security.measures`). A report that was not rewritten since the last
line is not appended twice, so a pass where the assessment failed leaves a
gap, not a flat line. Lines older than `series_days` are dropped.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SERIES = "security-series.jsonl"
REPORT = "security-assessment.json"


def _instant(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_report(generated_dir: Path) -> dict[str, Any] | None:
    """The `security` object of the last report; None when absent or unreadable."""

    try:
        data = json.loads((generated_dir / REPORT).read_text(encoding="utf-8"))["security"]
    except (OSError, ValueError, KeyError, TypeError):
        return None

    return data if isinstance(data, dict) else None


def read(generated_dir: Path, since: datetime | None = None) -> list[dict[str, Any]]:
    """The lines of the series, oldest first; a line that cannot be read is skipped."""

    try:
        text = (generated_dir / SERIES).read_text(encoding="utf-8")
    except OSError:
        return []

    lines: list[dict[str, Any]] = []
    for raw in text.splitlines():
        try:
            line = json.loads(raw)
        except ValueError:
            continue
        at = _instant(line.get("at")) if isinstance(line, dict) else None
        if at is not None and (since is None or at >= since):
            lines.append(line)

    return lines


def append(generated_dir: Path, now: datetime, in_window: bool, days: int) -> bool:
    """Append the last report's measures; False when there is nothing new to add."""

    report = read_report(generated_dir)
    measures = report.get("measures") if report else None
    collected = _instant(report.get("collected_at")) if report else None

    if not isinstance(measures, dict) or collected is None:
        return False

    kept = read(generated_dir, now - timedelta(days=days))
    last = _instant(kept[-1].get("collected_at")) if kept else None
    dropped = len(kept) != len(read(generated_dir))

    if last is not None and collected <= last:
        if dropped:
            _rewrite(generated_dir, kept)
        return False

    kept.append(
        {
            "at": now.isoformat(timespec="seconds"),
            "collected_at": collected.isoformat(timespec="seconds"),
            "window": in_window,
            "measures": measures,
        }
    )
    if dropped:
        _rewrite(generated_dir, kept)
    else:
        _add(generated_dir, kept[-1])
    return True


def _add(generated_dir: Path, line: dict[str, Any]) -> None:
    generated_dir.mkdir(parents=True, exist_ok=True)
    with (generated_dir / SERIES).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n")


def _rewrite(generated_dir: Path, lines: list[dict[str, Any]]) -> None:
    path = generated_dir / SERIES
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        "".join(json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n" for line in lines), encoding="utf-8"
    )
    temporary.replace(path)
