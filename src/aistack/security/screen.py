"""
What the security screen and its card's badge read (ADR-0028 slice T4b).

Pure functions over the last report (`security-assessment.json`) and the
series (`security-series.jsonl`): which findings count on the card, in which
colour, how they are grouped on the page, which fixed text goes with each
kind of finding, and the graphs as SVG. Nothing here writes, asks a host or
calls an engine.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatchcase
from html import escape
from typing import Any

from aistack.security.findings import FIX, SEVERITIES, URGENT, WATCH

# The drift of files and units is the owner's own doing while a window is open.
HELD_PREFIX = "drift."

ATTACKS, VULNERABILITIES = "attacks", "vulnerabilities"
_ATTACK_AREAS = ("logs", "refusals", "drift")

# On the card and on the page: what counts is "to watch" and worse.
COUNTED = (WATCH, FIX, URGENT)


def instant(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def findings_of(report: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    raw = report.get("findings") if report else None
    return [item for item in raw if isinstance(item, dict) and isinstance(item.get("key"), str)] if isinstance(raw, list) else []


def is_held(finding: Mapping[str, Any], in_window: bool) -> bool:
    """Held by the maintenance window: told after it, never as urgent news."""

    return in_window and str(finding["key"]).startswith(HELD_PREFIX) and finding.get("severity") != URGENT


def group_of(key: str) -> str:
    """Something that is happening (logs, refusals, drift) or something that is open (the rest)."""

    return ATTACKS if key.split(".")[0] in _ATTACK_AREAS else VULNERABILITIES


@dataclass(frozen=True)
class Attention:
    """What the card's badge says: how many, and the worst of them; `level` None when none."""

    count: int
    level: str | None


def attention(report: Mapping[str, Any] | None, in_window: bool) -> Attention:
    counted = [
        item
        for item in findings_of(report)
        if item.get("severity") in COUNTED and not is_held(item, in_window)
    ]
    if not counted:
        return Attention(0, None)
    worst = max((str(item["severity"]) for item in counted), key=SEVERITIES.index)
    return Attention(len(counted), worst)


@dataclass(frozen=True)
class Row:
    """One finding as the page shows it."""

    key: str
    severity: str
    title: str
    evidence: tuple[str, ...]
    unknown: str
    held: bool
    since: datetime | None
    kind: str


def rows(
    report: Mapping[str, Any] | None,
    in_window: bool,
    watch_since: Mapping[str, str],
    only: str | None = None,
) -> list[Row]:
    """The findings of `only` (a group) worth a line: to watch and worse, worst first."""

    found = [
        Row(
            key=str(item["key"]),
            severity=str(item.get("severity")),
            title=str(item.get("title", item["key"])),
            evidence=tuple(str(line) for line in item.get("evidence") or []),
            unknown=str(item.get("unknown") or ""),
            held=is_held(item, in_window),
            since=instant(watch_since.get(str(item["key"]))),
            kind=kind_of(str(item["key"])),
        )
        for item in findings_of(report)
        if item.get("severity") in COUNTED and (only is None or group_of(str(item["key"])) == only)
    ]
    return sorted(found, key=lambda row: (-SEVERITIES.index(row.severity), row.key))


def source_problems(report: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """The findings that say a source could not be read: the watch is blind there."""

    return [
        item
        for item in findings_of(report)
        if "unread" in str(item["key"]) or str(item["key"]).endswith(("silent", ".source", "not_read"))
    ]


def information_count(report: Mapping[str, Any] | None) -> int:
    return sum(1 for item in findings_of(report) if item.get("severity") not in COUNTED)


# ---------------------------------------------------------------------------
# The fixed text that goes with a kind of finding. The kinds are closed; the
# words are in the `security.guide.<kind>` catalog, written by hand, never
# generated (GOV-P-001).
# ---------------------------------------------------------------------------

KINDS = (
    "exposure_open",
    "exposure_undeclared",
    "exposure_other",
    "hygiene_socket",
    "hygiene_network",
    "host_updates",
    "host_reboot",
    "host_files",
    "host_other",
    "images",
    "logs_ssh",
    "logs_kernel",
    "logs_npm",
    "logs_other",
    "refusals",
    "drift_sensitive",
    "drift_other",
    "other",
)


def kind_of(key: str) -> str:
    parts = key.split(".")
    area = parts[0]

    if area == "exposure" and "reachable_from_anywhere" in parts:
        return "exposure_open"
    if area == "exposure" and "undeclared_on_all_interfaces" in parts:
        return "exposure_undeclared"
    if area in ("exposure", "firewall"):
        return "exposure_other"
    if area == "hygiene":
        return "hygiene_network" if "host_network" in parts else "hygiene_socket"
    if area == "host":
        if "files" in parts:
            return "host_files"
        if "updates" in parts:
            return "host_updates"
        if "reboot" in parts:
            return "host_reboot"
        return "host_other"
    if area == "images":
        return "images"
    if area == "logs":
        for name in ("ssh", "kernel", "npm"):
            if name in parts:
                return f"logs_{name}"
        return "logs_other"
    if area == "refusals":
        return "refusals"
    if area == "drift":
        return "drift_sensitive" if "sensitive" in parts else "drift_other"
    return "other"


# ---------------------------------------------------------------------------
# What goes to the local engine as data (ADR-0028 slice T4b).
# ---------------------------------------------------------------------------

EVIDENCE_LINES = 5
EVIDENCE_WIDTH = 120


def clean_line(text: str) -> str:
    """One evidence line made safe to quote: a container's name, a path or a log's words can be
    chosen by whoever attacks, so no control character, no line break, no long run survives."""

    flat = "".join(" " if (not char.isprintable() or char in "\r\n\t") else char for char in text)
    flat = " ".join(flat.split())
    return flat[:EVIDENCE_WIDTH]


def facts_for_engine(row: Row, t: Callable[..., str]) -> str:
    """The context block handed to the engine: what the screen already says, the evidence fenced
    as data, and what the answer must not do."""

    lines = [clean_line(line) for line in row.evidence[:EVIDENCE_LINES]]
    out = [
        f"- {t('security.engine.severity')}: {row.severity}",
        f"- {t('security.engine.title')}: {clean_line(row.title)}",
    ]
    if row.unknown:
        out.append(f"- {t('security.engine.unknown')}: {clean_line(row.unknown)}")
    out.append(t("security.engine.evidence_intro"))
    out.extend(f"> {line}" for line in lines)
    if not lines:
        out.append("> -")
    out.append(t("security.engine.rules"))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Graphs.
# ---------------------------------------------------------------------------

RANGES = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
DEFAULT_RANGE = "24h"
# A hole longer than this is shown as a hole, not joined: the vigil passes every 15 minutes.
GAP = timedelta(minutes=50)


@dataclass(frozen=True)
class Line:
    """One curve: the sum of the measures whose key matches a pattern (none present: a gap)."""

    label: str
    patterns: tuple[str, ...]
    colour: str
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True)
class Graph:
    title: str
    lines: tuple[Line, ...]


GRAPHS = (
    Graph(
        "findings",
        (
            Line("watch", ("findings.watch",), "#a16207"),
            Line("fix", ("findings.fix",), "#ea580c"),
            Line("urgent", ("findings.urgent",), "#b91c1c"),
        ),
    ),
    Graph("refusals", (Line("refused", ("refusals.*",), "#1f6feb", exclude=("refusals.covered_minutes",)),)),
    Graph("ssh", (Line("failed", ("ssh.*.failed.*",), "#1f6feb"), Line("invalid", ("ssh.*.invalid_user.*",), "#7c3aed"))),
    Graph(
        "proxy",
        (
            Line("probes", ("npm.*.probes.*",), "#1f6feb"),
            Line("paths", ("npm.*.app_paths.*",), "#7c3aed"),
            Line("answered", ("npm.*.probes_answered", "npm.*.app_paths_answered"), "#b91c1c"),
        ),
    ),
    Graph("packages", (Line("updates", ("packages.*.updates",), "#1f6feb"), Line("security", ("packages.*.security",), "#b91c1c"))),
    Graph("drift", (Line("sensitive", ("drift.*.sensitive",), "#a16207"), Line("other", ("drift.*.other",), "#6b7280"))),
)


def _value(measures: Mapping[str, Any], line: Line) -> int | None:
    found = [
        value
        for key, value in measures.items()
        if isinstance(value, int)
        and not isinstance(value, bool)
        and any(fnmatchcase(key, pattern) for pattern in line.patterns)
        and not any(fnmatchcase(key, pattern) for pattern in line.exclude)
    ]
    return sum(found) if found else None


def points(series: Sequence[Mapping[str, Any]], line: Line) -> list[tuple[datetime, int | None]]:
    out: list[tuple[datetime, int | None]] = []
    for entry in series:
        at = instant(entry.get("collected_at") or entry.get("at"))
        measures = entry.get("measures")
        if at is not None and isinstance(measures, dict):
            out.append((at, _value(measures, line)))
    return sorted(out, key=lambda point: point[0])


WIDTH, HEIGHT, LEFT, RIGHT, TOP, BOTTOM = 640, 150, 34, 8, 8, 20


def svg(
    series: Sequence[Mapping[str, Any]],
    graph: Graph,
    start: datetime,
    end: datetime,
    labels: Mapping[str, str],
    description: str,
    zone: Any = timezone.utc,
) -> str:
    """One graph as an SVG: lines with holes where nothing was read; "no data" when nothing was."""

    curves = [(line, points(series, line)) for line in graph.lines]
    values = [value for _line, found in curves for _at, value in found if value is not None]
    span = (end - start).total_seconds() or 1.0
    top = max(values) if values else 0
    top = max(top, 1)
    plot_width, plot_height = WIDTH - LEFT - RIGHT, HEIGHT - TOP - BOTTOM

    def x(at: datetime) -> float:
        return LEFT + plot_width * min(max((at - start).total_seconds() / span, 0.0), 1.0)

    def y(value: int) -> float:
        return TOP + plot_height * (1 - value / top)

    parts = [
        f'<svg class="graph" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(description, quote=True)}" '
        f'xmlns="http://www.w3.org/2000/svg">',
        f"<title>{escape(description)}</title>",
        f'<rect x="{LEFT}" y="{TOP}" width="{plot_width}" height="{plot_height}" fill="#fafafa" stroke="#ddd"/>',
        f'<text x="{LEFT - 4}" y="{TOP + 9}" text-anchor="end" font-size="10" fill="#555">{top}</text>',
        f'<text x="{LEFT - 4}" y="{TOP + plot_height}" text-anchor="end" font-size="10" fill="#555">0</text>',
        f'<text x="{LEFT}" y="{HEIGHT - 6}" font-size="10" fill="#555">{escape(start.astimezone(zone).strftime("%d/%m %H:%M"))}</text>',
        f'<text x="{WIDTH - RIGHT}" y="{HEIGHT - 6}" text-anchor="end" font-size="10" fill="#555">{escape(end.astimezone(zone).strftime("%d/%m %H:%M"))}</text>',
    ]

    if not values:
        parts.append(
            f'<text x="{LEFT + plot_width / 2}" y="{TOP + plot_height / 2}" text-anchor="middle" font-size="12" fill="#666">'
            f'{escape(labels.get("none", ""))}</text>'
        )
    else:
        for line, found in curves:
            segment: list[tuple[datetime, int]] = []
            drawn: list[list[tuple[datetime, int]]] = []
            previous: datetime | None = None
            for at, value in found:
                if at < start or at > end:
                    continue
                if value is None or (previous is not None and at - previous > GAP):
                    if segment:
                        drawn.append(segment)
                    segment = []
                if value is not None:
                    segment.append((at, value))
                    previous = at
                else:
                    previous = None
            if segment:
                drawn.append(segment)
            for piece in drawn:
                if len(piece) == 1:
                    at, value = piece[0]
                    parts.append(f'<circle cx="{x(at):.1f}" cy="{y(value):.1f}" r="2" fill="{line.colour}"/>')
                else:
                    path = " ".join(f"{x(at):.1f},{y(value):.1f}" for at, value in piece)
                    parts.append(
                        f'<polyline points="{path}" fill="none" stroke="{line.colour}" stroke-width="2" stroke-linejoin="round"/>'
                    )

    parts.append("</svg>")
    return "".join(parts)
