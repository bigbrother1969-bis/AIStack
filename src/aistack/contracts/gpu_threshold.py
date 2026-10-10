from __future__ import annotations

from dataclasses import dataclass

# The threshold kinds OPS-0007 declares. A `GpuThreshold` names no card:
# one GPU per host is assumed, so each threshold applies to every
# reading of that host.
TEMPERATURE_CELSIUS = "temperature_celsius"
UTILIZATION_PERCENT = "utilization_percent"
MEMORY_PERCENT = "memory_percent"

KINDS = (TEMPERATURE_CELSIUS, UTILIZATION_PERCENT, MEMORY_PERCENT)


ANY_HOST = "*"


@dataclass(frozen=True)
class GpuThreshold:
    """
    One declared GPU alert threshold (OPS-0007).

    Kinds: `TEMPERATURE_CELSIUS` (°C), `UTILIZATION_PERCENT` (0-100),
    `MEMORY_PERCENT` (VRAM used, 0-100). A reading at or above the value
    is anomalous; an idle GPU is never a problem.
    """

    kind: str
    value: float

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(
                f"unknown GPU threshold kind {self.kind!r}; OPS-0007 "
                f"declares only {KINDS}"
            )

        if self.value < 0:
            raise ValueError(
                f"a {self.kind} threshold cannot be negative: {self.value}"
            )


@dataclass(frozen=True)
class HostGpuThresholds:
    """
    One host's declared GPU thresholds. The caller matches `host`
    against the local hostname.
    """

    host: str
    thresholds: tuple[GpuThreshold, ...]

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("a host's GPU thresholds name no host")


@dataclass(frozen=True)
class GpuThresholdRegister:
    """
    Every host's declared GPU thresholds, as loaded by
    `aistack.providers.gpu.yaml.load_gpu_thresholds_yaml`.

    `for_host` returns `()` for a host with no entry and no `"*"` entry.
    """

    hosts: tuple[HostGpuThresholds, ...]

    def for_host(self, hostname: str) -> tuple[GpuThreshold, ...]:
        for entry in self.hosts:
            if entry.host == hostname:
                return entry.thresholds

        # `host: "*"` matches any host the file does not name; a new
        # installation ships it before it knows its own hostname.
        for entry in self.hosts:
            if entry.host == ANY_HOST:
                return entry.thresholds

        return ()
