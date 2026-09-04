from __future__ import annotations

import subprocess

from aistack.contracts.temperature_reading import TemperatureReading
from aistack.providers.host.sensors import parse_sensors_output


class HostProvider:
    """
    Observe the physical host `aistack` runs on, and conclude
    nothing.

    Every other provider in this heritage observes a container;
    nothing before this read anything about the machine underneath
    them. The first reading it exists for is temperature —
    `STD-0300` § VS-4's sustainability-anomaly qualification asks
    for one correlated against a CPU reading, and `sensors`
    (lm-sensors) is the source the owner already reads it from
    (`OPS-0004`).
    """

    provider_id = "aistack.provider.host"
    provider_name = "Host Provider"

    def collect_temperatures(self) -> tuple[TemperatureReading, ...]:
        """
        Every temperature `sensors` reports, in one call.

        Never raises: no `sensors` binary installed, no sensors
        configured, a host this runs on that has none at all — each
        reads the same as nothing to report rather than a failure
        worth stopping for, the convention
        `DockerProvider.collect_process` already holds.
        """

        try:
            result = subprocess.run(
                ["sensors"], capture_output=True, text=True
            )
        except OSError:
            return ()

        if result.returncode != 0:
            return ()

        return parse_sensors_output(result.stdout)
