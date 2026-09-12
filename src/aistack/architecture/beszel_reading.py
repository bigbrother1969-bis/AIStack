from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BeszelSystemReading:
    """
    One Beszel-monitored system, as a snapshot at render time — not a
    live, in-browser-updating value. `architecture.html` is a static
    page (`render_html` is pure, no wall clock); "temps réel"
    (`PLAN-J11-CONSOLE-2026-09-11.md` §10) means "as of the last time
    `architecture_render` ran", the same snapshot discipline every
    other status in this page already has (a service's
    observed/declared split is exactly as current as the last Docker
    Catalog build, never live either).

    Every numeric field is optional — Beszel's own `info` object omits
    a key it has nothing to report for (`omitempty`/`omitzero` on
    almost every field, confirmed against
    `github.com/henrygd/beszel@v0.19.0/internal/entities/system`'s own
    `Info` struct) — `None` here means "not reported", never a
    fabricated zero.

    **Field selection, decided with the owner 2026-09-12**: `status`,
    `cpu_pct`, `mem_pct`, `disk_pct`, `temp_c`, `load_avg` and
    `uptime_seconds` travel; `g` (GPU%), `p` (Podman), `os` (OS enum)
    and `bb` (bandwidth bytes) do not — `g` in particular reads `0` on
    every system today, which almost certainly means GPU monitoring
    is not enabled on the agent side rather than a real idle GPU, so
    displaying it would look like a fact this project verified and
    is not.
    """

    name: str
    host: str
    status: str
    cpu_pct: float | None = None
    mem_pct: float | None = None
    disk_pct: float | None = None
    temp_c: float | None = None
    load_avg: tuple[float, float, float] | None = None
    uptime_seconds: int | None = None


def build_beszel_readings(raw_systems: Any) -> tuple[BeszelSystemReading, ...]:
    """
    Turn `BeszelProvider.collect()["beszel"]["systems"]` (Beszel's own
    REST API records, unqualified) into typed readings.

    **Tolerant, not strict** — unlike
    `load_infrastructure_topology_yaml`, which raises on a malformed
    hand-written file (a typo there is the owner's own mistake to
    fix), this reads a live third-party API response: a missing or
    oddly-typed field is skipped rather than raising, so a Beszel
    version bump that adds, removes or reshapes a field degrades to
    "that one reading is missing", never to a page that fails to
    render at all.
    """

    if not isinstance(raw_systems, list):
        return ()

    readings = []

    for item in raw_systems:
        reading = _build_one(item)

        if reading is not None:
            readings.append(reading)

    return tuple(readings)


def _build_one(item: Any) -> BeszelSystemReading | None:
    if not isinstance(item, dict):
        return None

    name = item.get("name")

    if not isinstance(name, str) or not name:
        return None

    host = item.get("host")
    host = host if isinstance(host, str) else ""

    status = item.get("status")
    status = status if isinstance(status, str) else ""

    info = item.get("info")
    info = info if isinstance(info, dict) else {}

    return BeszelSystemReading(
        name=name,
        host=host,
        status=status,
        cpu_pct=_number(info.get("cpu")),
        mem_pct=_number(info.get("mp")),
        disk_pct=_number(info.get("dp")),
        temp_c=_number(info.get("dt")),
        load_avg=_load_avg(info.get("la")),
        uptime_seconds=_integer(info.get("u")),
    )


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    return None


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return int(value)

    return None


def _load_avg(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None

    numbers = [_number(entry) for entry in value]

    if any(number is None for number in numbers):
        return None

    return (numbers[0], numbers[1], numbers[2])  # type: ignore[return-value]
