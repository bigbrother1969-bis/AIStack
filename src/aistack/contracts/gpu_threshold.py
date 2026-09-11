from __future__ import annotations

from dataclasses import dataclass

# The three threshold kinds `OPS-0007` declares — no more without the
# owner naming a fourth, the same discipline `OPS-0005`'s two kinds
# hold for storage. Unlike `StorageThreshold` (keyed to one `mount`
# among several on a host) or `BackupThreshold` (keyed to one `path`
# among several), a `GpuThreshold` names no card of its own: the
# owner's v1 scope is one GPU per host, so every declared threshold
# applies to every `GpuReading` `find_gpu_anomalies` is handed for
# that host.
TEMPERATURE_CELSIUS = "temperature_celsius"
UTILIZATION_PERCENT = "utilization_percent"
MEMORY_PERCENT = "memory_percent"

KINDS = (TEMPERATURE_CELSIUS, UTILIZATION_PERCENT, MEMORY_PERCENT)


@dataclass(frozen=True)
class GpuThreshold:
    """
    One host's own declared GPU alert threshold — `OPS-0007`, not a
    value this heritage chose. `GOV-P-001`: the owner states the
    number; this type only shapes it so `find_gpu_anomalies` can
    compare a reading against it without inventing what "too hot",
    "too busy" or "too full" means for a GPU no case has named a value
    for.

    Three kinds, declared against real `nvidia-smi` output taken live
    from GIGABYTE's Quadro P400, 2026-09-11 (`OPS-0007` § *Provenance*):
    `TEMPERATURE_CELSIUS` (°C), `UTILIZATION_PERCENT` (sustained
    utilization, 0-100), `MEMORY_PERCENT` (VRAM occupied, 0-100). All
    three read "at or above this value is anomalous" — the same
    direction `StorageThreshold.PERCENT_USED` already holds — never
    "too low", since an idle GPU is never itself a problem this domain
    detects.
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
    One host's own declared GPU thresholds.

    Mirrors `HostStorageThresholds`/`HostBackupThresholds`: `OPS-0007`
    scopes every threshold to the host it was declared for — GIGABYTE
    is the only host with a GPU the owner has confirmed exploitable
    (`OPS-0007` § *Declared thresholds*). `host` is matched against
    `socket.gethostname()` by the caller (`aistack.cli.runtime_diagnose`),
    not by this type.
    """

    host: str
    thresholds: tuple[GpuThreshold, ...]

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("a host's GPU thresholds name no host")


@dataclass(frozen=True)
class GpuThresholdRegister:
    """
    Every host's declared GPU thresholds, as `OPS-0007`'s YAML file
    loads it (`aistack.providers.gpu.yaml.load_gpu_thresholds_yaml`).

    `for_host` mirrors `StorageThresholdRegister.for_host`/
    `BackupThresholdRegister.for_host` exactly: a pure derivation from
    data already held, and a host with no entry returns `()` — "not
    declared for this host", not "declared as nothing to check" — the
    same `FDN-0003` Article 12 absence `find_gpu_anomalies` already
    holds for a threshold kind never declared at all.
    """

    hosts: tuple[HostGpuThresholds, ...]

    def for_host(self, hostname: str) -> tuple[GpuThreshold, ...]:
        for entry in self.hosts:
            if entry.host == hostname:
                return entry.thresholds

        return ()
