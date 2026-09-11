from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.container_health import ContainerHealth


@dataclass(frozen=True)
class ContainerStateReading:
    """
    One container's own reported state and health, at one point in
    time.

    `PLAN-J7`'s third domain (Services) — `OPS-0004`'s third reference
    incident: after a sudden power outage, containers were observed
    restart-looping or stuck unhealthy, visible via the Raspberry's own
    Homepage page. ARC-P-012's boundary applies here exactly as it
    does to `ContainerCpuReading`/`StorageReading`: this is what
    Docker reported, concluding nothing about whether it is a
    problem. Whether a container is in distress is a question for
    something that reads a collection of these against a declared
    rule (`aistack.runtime.container_distress.find_container_distress`),
    not this type.

    `state` is Docker's own `State` field (`running`, `restarting`,
    `exited`, …) — the same field `runtime_diagnose.containers()`
    already reads for every subject, carried here alongside `health`
    rather than alone. `health` is `ContainerHealth.health_of(Status)`
    — already parsed, not re-derived by a caller.

    **Deliberately instantaneous-only.** A true restart *loop* could
    in principle be measured over time (`docker inspect`'s own
    `RestartCount`, counted across two readings); the owner chose a
    snapshot-only v1 (2026-09-11) — the same "static threshold, no
    fill-rate detection" scope storage's own v1 chose first. This type
    carries no history because nothing collects one yet; it is a
    single instant, exactly as `StorageReading` is.
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
                f"'unknown' rather than an empty string — FDN-0003 "
                f"Article 12 names an absence, it does not leave one "
                f"silent"
            )
