from __future__ import annotations

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.unexplained_consumption import UnexplainedConsumption
from aistack.priority.definition import ResourcePriorityDefinition


# An estimate, not a measurement: a background container at rest should sit
# near 0 %, so 5 % sustained already means real, continuous work.
DEFAULT_THRESHOLD_PERCENT = 5.0


def find_unexplained_consumption(
    readings: list[ContainerCpuReading] | tuple[ContainerCpuReading, ...],
    definition: ResourcePriorityDefinition,
    threshold_percent: float = DEFAULT_THRESHOLD_PERCENT,
) -> tuple[UnexplainedConsumption, ...]:
    """
    Return the containers using CPU above the threshold that `definition`
    does not declare at all.

    "Declared" means listed in `definition` as priority or background,
    whatever its values: a background container with `normal_cpus: None`
    is still declared. Pure: no clock or host access.
    """

    declared = {app.container for app in definition.priority} | {
        container.name for container in definition.background.containers
    }

    return tuple(
        UnexplainedConsumption(
            container=reading.container,
            cpu_percent=reading.cpu_percent,
            threshold_percent=threshold_percent,
        )
        for reading in readings
        if reading.container not in declared
        and reading.cpu_percent >= threshold_percent
    )
