from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.container_health import ContainerHealth


@dataclass(frozen=True)
class ContainerStateReading:
    """
    One container's reported state and health at one point in time.

    A reading, not a verdict: `aistack.runtime.container_distress`
    judges it. `state` is Docker's `State` (`running`, `restarting`,
    `exited`, ...); `health` is already parsed by `health_of`.
    """

    container: str
    state: str
    health: ContainerHealth

    def __post_init__(self) -> None:
        if not self.container.strip():
            raise ValueError(
                "a container state reading is about one container; "
                "this one names none"
            )

        if not self.state.strip():
            raise ValueError(
                f"{self.container} reports no state at all; use "
                f"'unknown' rather than an empty string, so the absence "
                f"is named"
            )
