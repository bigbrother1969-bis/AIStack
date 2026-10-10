from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.container_health import ContainerHealth
from aistack.contracts.container_state_reading import ContainerStateReading

# Closed set of distress reasons (OPS-0004).
RESTARTING = "restarting"
UNHEALTHY = "unhealthy"

REASONS = (RESTARTING, UNHEALTHY)


@dataclass(frozen=True)
class ContainerDistress:
    """
    A container found restarting or unhealthy (OPS-0004).

    `reasons` holds one or both, never none; the constructor checks each
    against the reading.
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
                f"(instantaneous state only; restart loops are counted "
                f"apart)"
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
