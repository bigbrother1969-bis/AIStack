"""
What Beszel says of the machines it watches (ADR-0032, slice O1c).

Beszel's hub already answers the architecture page: the provider logs in with a read-only
account and lists the systems, and `beszel_reading` turns each record into numbers (disk,
memory, temperature, status), `None` when Beszel omits one. This module reuses both and
only adds the boot checks' way of reporting a failure: a state with a reason, never an
exception, and never the address or the account in the reason.

The CPU is not read: a single instant of it says nothing about a start, a history will.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aistack.architecture.beszel_reading import BeszelSystemReading, build_beszel_readings
from aistack.boot_checks.trend import DiskPoint
from aistack.providers.beszel import collect_beszel

UP = "up"
DOWN = "down"


@dataclass(frozen=True)
class SystemsReading:
    """The machines Beszel watches and what it says of them, or why it could not be asked."""

    reachable: bool
    reason: str = ""
    systems: tuple[BeszelSystemReading, ...] = field(default_factory=tuple)
    # name -> the used space of its system disk every 8 hours, oldest first (O4); a machine with no history is not in it.
    history: tuple[tuple[str, tuple[DiskPoint, ...]], ...] = field(default_factory=tuple)


def _why(reason: str) -> str:
    """A reason for the page: what failed, without the address or the account the provider's sentence carries."""

    if "refused authentication" in reason:
        return "Beszel refused the account"

    if "unreadable" in reason or "no token" in reason:
        return "Beszel answered something unreadable"

    return "Beszel did not answer"


def read_systems(url: str, email: str, password: str, timeout: float = 8.0) -> SystemsReading:
    """Sign in, list the systems, and for each one Beszel calls down ask when its last measure arrived; a failure is a state with a reason."""

    observation = collect_beszel(url, email, password, timeout=timeout, last_readings=True, disk_history=True)
    state = observation["beszel"]

    if not state["reachable"]:
        return SystemsReading(False, _why(str(state["unreachable_reason"])))

    return SystemsReading(True, "", build_beszel_readings(state["systems"]), _histories(state["systems"]))


def _stamp(raw: Any) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(raw).replace(" ", "T").replace("Z", "+00:00"))
    except ValueError:
        return None

    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _histories(raw_systems: Any) -> tuple[tuple[str, tuple[DiskPoint, ...]], ...]:
    """What the provider attached to each machine, as points; a row that is not a date and two numbers is left out."""

    found = []

    for item in raw_systems if isinstance(raw_systems, list) else []:
        rows = item.get("disk_history") if isinstance(item, dict) else None

        if not isinstance(rows, list) or not isinstance(item.get("name"), str):
            continue

        points = []

        for row in rows:
            moment = _stamp(row.get("at")) if isinstance(row, dict) else None

            if moment is not None and isinstance(row.get("total"), (int, float)) and isinstance(row.get("used"), (int, float)):
                points.append(DiskPoint(moment, float(row["total"]), float(row["used"])))

        found.append((item["name"], tuple(points)))

    return tuple(found)
