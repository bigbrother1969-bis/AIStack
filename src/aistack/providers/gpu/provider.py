from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from aistack.contracts.gpu_reading import GpuReading

# Field order matters: one comma-separated line per GPU. No
# `power.draw`/`power.limit`: they read `[N/A]` on consumer/entry cards
# such as the Quadro P400.
_QUERY_FIELDS = "name,utilization.gpu,memory.used,memory.total,temperature.gpu"

_EXPECTED_FIELD_COUNT = 5


class NvidiaGpuProvider:
    """Observe the host's NVIDIA GPUs via `nvidia-smi`, without drawing
    conclusions (`OPS-0007`).

    Never raises: no `nvidia-smi`, no driver, or a malformed line yields
    nothing to report.
    """

    provider_id = "aistack.provider.gpu.nvidia"
    provider_name = "NVIDIA GPU Provider"

    def collect_readings(self) -> tuple[GpuReading, ...]:
        """One reading per GPU `nvidia-smi` reports."""

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
                # A field reported as `[N/A]` rather than a number.
                continue

        return tuple(readings)
