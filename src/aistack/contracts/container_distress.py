from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.container_health import ContainerHealth
from aistack.contracts.container_state_reading import ContainerStateReading

# The two conditions `OPS-0004`'s third reference incident names —
# closed the same way `StorageThreshold.KINDS` is: no third reason
# without a real case naming one (`GOV-P-001`).
RESTARTING = "restarting"
UNHEALTHY = "unhealthy"

REASONS = (RESTARTING, UNHEALTHY)


@dataclass(frozen=True)
class ContainerDistress:
    """
    One container already found to be in a state `OPS-0004`'s third
    reference incident names as a problem — restart-looping, or
    Docker's own healthcheck declaring it unhealthy.

    Mirrors `StorageShortage`: the reading, and the reason(s) it was
    already found to cross into distress, enforced here rather than
    only in the caller — `find_container_distress`
    (`aistack.runtime.container_distress`) only ever constructs one
    already confirmed; it does not re-derive "in distress" from a
    bare reading handed to it from elsewhere.

    `reasons` may carry both at once — a container can be restarting
    *and* declared unhealthy in the same instant — but never neither;
    an instance naming no reason is not what this type states, the
    same "a shortage that is not actually short cannot be
    constructed" discipline `StorageShortage` already holds.
    """

    reading: ContainerStateReading
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError(
                f"{self.reading.container} is declared in distress but "
                f"names no reason; ContainerDistress states a confirmed "
                f"condition, not a bare reading"
            )

        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError(
                f"{self.reading.container} cites the same reason more "
                f"than once in {self.reasons}"
            )

        unknown = [reason for reason in self.reasons if reason not in REASONS]

        if unknown:
            raise ValueError(
                f"{self.reading.container} cites {unknown} as a distress "
                f"reason; only {REASONS} are detected in this scope "
                f"(instantaneous state only — no restart-loop counting, "
                f"the owner's chosen v1 scope, 2026-09-11)"
            )

        if RESTARTING in self.reasons and self.reading.state != RESTARTING:
            raise ValueError(
                f"{self.reading.container} cites 'restarting' but its "
                f"own reading reports state={self.reading.state!r}"
            )

        if (
            UNHEALTHY in self.reasons
            and self.reading.health != ContainerHealth.UNHEALTHY
        ):
            raise ValueError(
                f"{self.reading.container} cites 'unhealthy' but its "
                f"own reading reports health={self.reading.health!r}"
            )
