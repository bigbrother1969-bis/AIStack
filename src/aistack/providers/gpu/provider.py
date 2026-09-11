from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from aistack.contracts.gpu_reading import GpuReading

# The exact fields this provider asks `nvidia-smi` for, and in this
# order — `noheader,nounits` gives one clean comma-separated line per
# GPU with no units to strip and no header row to skip, confirmed live
# against GIGABYTE's Quadro P400, 2026-09-11.
#
# **No `power.draw`/`power.limit`.** Both read `[N/A]` on this
# hardware — confirmed the same day — so asking for them would only
# ever produce a field this provider could never parse as a number.
# `GpuReading` carries no power field for the same reason.
_QUERY_FIELDS = "name,utilization.gpu,memory.used,memory.total,temperature.gpu"

_EXPECTED_FIELD_COUNT = 5


class NvidiaGpuProvider:
    """
    Observe the host's own NVIDIA GPU via `nvidia-smi`, and conclude
    nothing.

    `PLAN-J7`'s fifth domain (GPU) — the owner's own stated
    requirement to monitor GPU/CPU consumption (`OPS-0007`). The same
    boundary (`ARC-P-012`) `StorageProvider`/`HostProvider` already
    hold: this is what `nvidia-smi` reported, concluding nothing about
    whether it is a problem.

    **Never raises**, the same convention `HostProvider
    .collect_temperatures` already holds for `sensors`: no `nvidia-smi`
    binary on the host (a GPU-less host, or an AMD/Intel GPU with no
    NVIDIA tooling), no NVIDIA driver loaded, or a malformed line —
    each reads as nothing to report rather than a failure worth
    stopping the whole diagnosis for.
    """

    provider_id = "aistack.provider.gpu.nvidia"
    provider_name = "NVIDIA GPU Provider"

    def collect_readings(self) -> tuple[GpuReading, ...]:
        """
        Every GPU `nvidia-smi` reports, in one call.

        One line of CSV per GPU. The owner's own host (GIGABYTE)
        carries exactly one (a Quadro P400) — this provider does not
        assume that: a host with several GPUs reports several
        readings, unchanged by anything this domain's v1 scope
        declares only one host's threshold for.
        """

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--query-gpu={_QUERY_FIELDS}",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
            )
        except OSError:
            return ()

        if result.returncode != 0:
            return ()

        observed_at = datetime.now(timezone.utc)
        readings: list[GpuReading] = []

        for line in result.stdout.splitlines():
            if not line.strip():
                continue

            fields = [field.strip() for field in line.split(",")]

            if len(fields) != _EXPECTED_FIELD_COUNT:
                continue

            name, utilization, memory_used, memory_total, temperature = fields

            try:
                readings.append(
                    GpuReading(
                        name=name,
                        observed_at=observed_at,
                        utilization_percent=float(utilization),
                        memory_used_mib=float(memory_used),
                        memory_total_mib=float(memory_total),
                        temperature_celsius=float(temperature),
                    )
                )
            except ValueError:
                # A field `nvidia-smi` reported as `[N/A]` or similar
                # rather than a number — the same "skip what cannot be
                # trusted rather than crash the whole read" choice
                # `collect_freshness` makes for an unreadable file
                # `stat()`.
                continue

        return tuple(readings)
