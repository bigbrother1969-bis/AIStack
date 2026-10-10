from __future__ import annotations

import subprocess

from aistack.contracts.temperature_reading import TemperatureReading
from aistack.providers.host.sensors import parse_sensors_output


class HostProvider:
    """Observe the physical host AIStack runs on, without drawing conclusions.

    Currently reads temperatures from `sensors` (lm-sensors, `OPS-0004`).
    """

    provider_id = "aistack.provider.host"
    provider_name = "Host Provider"

    def collect_temperatures(self) -> tuple[TemperatureReading, ...]:
        """Every temperature `sensors` reports.

        Never raises: a missing binary or no configured sensors returns
        an empty tuple.
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
