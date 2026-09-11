from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GpuReading:
    """
    One GPU's own reported state, at one point in time: utilization,
    memory occupancy, and temperature.

    `PLAN-J7`'s fifth domain (GPU) — the owner's own stated
    requirement: *"Vérifier que tous les services qui peuvent déléguer
    du calcul au GPU le font bien et surveiller la consommation du duo
    CPU/GPU."* v1 scope, the owner's own choice, covers only the
    second half — consumption monitoring — not per-service delegation
    verification (`OPS-0007` § *Out of scope for this version*).
    `ARC-P-012`'s boundary applies here exactly as it does to
    `StorageReading`/`ContainerStateReading`: this is what `nvidia-smi`
    reported, concluding nothing about whether it is a problem.
    Whether a reading is anomalous is a question for something that
    reads a collection of these against a declared threshold
    (`aistack.runtime.gpu_anomaly.find_gpu_anomalies`), not this type.

    `name` identifies the card (`nvidia-smi`'s own `name` field, e.g.
    "Quadro P400") rather than a host — the same "this process only
    ever examines the host it runs on" scope `StorageReading`/
    `TemperatureReading` already hold without carrying a `host` field
    themselves.

    **No `power_watts` field.** The owner's own GPU (a Quadro P400)
    reports `power.draw`/`power.limit` as `N/A` via `nvidia-smi` —
    confirmed live, 2026-09-11 — so this type carries only what this
    hardware can actually report; power is out of scope by
    construction, not by choice (`OPS-0007` § *Out of scope for this
    version*).
    """

    name: str
    observed_at: datetime
    utilization_percent: float
    memory_used_mib: float
    memory_total_mib: float
    temperature_celsius: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "a GPU reading is about one card; this one names none"
            )

        if not (0 <= self.utilization_percent <= 100):
            raise ValueError(
                f"{self.name} reports {self.utilization_percent}% "
                f"utilization, outside the 0-100 range"
            )

        if self.memory_used_mib < 0 or self.memory_total_mib < 0:
            raise ValueError(
                f"{self.name} reports a negative memory figure: "
                f"used={self.memory_used_mib}, total={self.memory_total_mib}"
            )

        if self.memory_used_mib > self.memory_total_mib:
            raise ValueError(
                f"{self.name} reports {self.memory_used_mib} MiB used, "
                f"exceeding its own reported total of "
                f"{self.memory_total_mib} MiB"
            )

    @property
    def memory_percent(self) -> float:
        """
        `memory_used_mib` as a percentage of `memory_total_mib` — 0.0
        for a card this reads as having no memory at all, rather than
        dividing by zero. Mirrors `StorageReading.percent_used`.
        """

        if self.memory_total_mib == 0:
            return 0.0

        return (self.memory_used_mib / self.memory_total_mib) * 100
