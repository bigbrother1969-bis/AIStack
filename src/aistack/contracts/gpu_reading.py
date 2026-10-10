from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GpuReading:
    """
    One GPU's reported utilization, memory and temperature at one point
    in time, as `nvidia-smi` gives them.

    A reading, not a verdict: `aistack.runtime.gpu_anomaly` judges it.
    `name` is the card's name (e.g. "Quadro P400"). There is no power
    field: some cards report `power.draw` as `N/A`.
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
        """Memory used as a percentage of total; 0.0 when total is 0."""

        if self.memory_total_mib == 0:
            return 0.0

        return (self.memory_used_mib / self.memory_total_mib) * 100
