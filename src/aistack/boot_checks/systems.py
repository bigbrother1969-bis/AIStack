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

from aistack.architecture.beszel_reading import BeszelSystemReading, build_beszel_readings
from aistack.providers.beszel import collect_beszel

UP = "up"
DOWN = "down"


@dataclass(frozen=True)
class SystemsReading:
    """The machines Beszel watches and what it says of them, or why it could not be asked."""

    reachable: bool
    reason: str = ""
    systems: tuple[BeszelSystemReading, ...] = field(default_factory=tuple)


def _why(reason: str) -> str:
    """A reason for the page: what failed, without the address or the account the provider's sentence carries."""

    if "refused authentication" in reason:
        return "Beszel refused the account"

    if "unreadable" in reason or "no token" in reason:
        return "Beszel answered something unreadable"

    return "Beszel did not answer"


def read_systems(url: str, email: str, password: str, timeout: float = 8.0) -> SystemsReading:
    """Sign in, list the systems, and for each one Beszel calls down ask when its last measure arrived; a failure is a state with a reason."""

    observation = collect_beszel(url, email, password, timeout=timeout, last_readings=True)
    state = observation["beszel"]

    if not state["reachable"]:
        return SystemsReading(False, _why(str(state["unreachable_reason"])))

    return SystemsReading(True, "", build_beszel_readings(state["systems"]))
