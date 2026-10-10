from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BeszelSystemReading:
    """
    One Beszel-monitored system, as of the last render (the page is static).

    Numeric fields are `None` when Beszel omits them, never a made-up zero.
    The GPU field (`g`) is not carried: it reads 0 when GPU monitoring is not
    enabled on the agent, which would look like a verified idle GPU.
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
    Turn `BeszelProvider.collect()["beszel"]["systems"]` into typed readings.

    Tolerant: this reads a third-party API, so a missing or oddly typed
    field is skipped rather than raised, and the page still renders.
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
