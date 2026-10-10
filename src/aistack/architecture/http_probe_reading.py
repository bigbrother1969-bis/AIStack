from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HttpProbeReading:
    """
    One HTTP probe target, as of the last render.

    `reachable` is True when any HTTP response came back, whatever its
    status; `status_code` is `None` exactly when `reachable` is False.
    """

    name: str
    url: str
    reachable: bool
    status_code: int | None = None
    unreachable_reason: str = ""


def build_http_probe_readings(raw_targets: Any) -> tuple[HttpProbeReading, ...]:
    """
    Turn `HttpProbeProvider.collect()["http_probe"]["targets"]` into typed
    readings. Tolerant: malformed entries or fields are skipped.
    """

    if not isinstance(raw_targets, list):
        return ()

    readings = []

    for item in raw_targets:
        reading = _build_one(item)

        if reading is not None:
            readings.append(reading)

    return tuple(readings)


def _build_one(item: Any) -> HttpProbeReading | None:
    if not isinstance(item, dict):
        return None

    name = item.get("name")

    if not isinstance(name, str) or not name:
        return None

    url = item.get("url")
    url = url if isinstance(url, str) else ""

    reachable = item.get("reachable")
    reachable = reachable if isinstance(reachable, bool) else False

    status_code = item.get("status_code")
    status_code = (
        status_code
        if isinstance(status_code, int) and not isinstance(status_code, bool)
        else None
    )

    unreachable_reason = item.get("unreachable_reason")
    unreachable_reason = (
        unreachable_reason if isinstance(unreachable_reason, str) else ""
    )

    return HttpProbeReading(
        name=name,
        url=url,
        reachable=reachable,
        status_code=status_code,
        unreachable_reason=unreachable_reason,
    )
