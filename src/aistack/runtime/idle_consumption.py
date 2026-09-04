from __future__ import annotations

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.unexplained_consumption import UnexplainedConsumption
from aistack.priority.definition import ResourcePriorityDefinition


# The owner's own starting number for `resource_priority.yml`'s
# per-app CPU thresholds was 50 % / 15 s, chosen alongside that
# design before any measurement existed to check it against
# (`CpuThresholdDetectorDefinition`'s own docstring).
#
# This is the same kind of guess, not a measured one, and it is
# proposed here rather than declared by the owner: the reference
# incident sat at 48-58 %, comfortably above almost any threshold
# that would also catch it, so 5 % is chosen to be sensitive rather
# than to fit that one number — a background container idling at
# rest is expected to sit close to 0 %, and 5 % sustained is already
# a container doing real, continuous work. Revisit once a live sweep
# on the reference deployment shows what "idle" actually reads at
# for containers nobody has classified yet.
DEFAULT_THRESHOLD_PERCENT = 5.0


def find_unexplained_consumption(
    readings: list[ContainerCpuReading] | tuple[ContainerCpuReading, ...],
    definition: ResourcePriorityDefinition,
    threshold_percent: float = DEFAULT_THRESHOLD_PERCENT,
) -> tuple[UnexplainedConsumption, ...]:
    """
    Which containers are using CPU while nothing declares what for.

    `STD-0300` § VS-4 criterion 4.1's "without being pointed at the
    service" is satisfied by the caller collecting every container's
    reading in one `docker stats` call, not by this function — this
    only decides, given readings already collected, which ones carry
    no explanation.

    **"Declared" means present in `definition` at all, priority or
    background — never whether a value is set.** A background
    container with `normal_cpus: None` is still declared: someone
    looked at it and decided "no limit at rest" is right. Absence
    from both lists is a different fact — nobody looked — and it is
    the only one this function reads. Mirrors
    `LifecycleRegister.for_container` returning `None` for the same
    reason: `resolve_resource_targets` already treats a missing
    `boosted` entry as "not boosted" for a *different* purpose
    (deciding today's CPU cap); this one is deciding whether the
    container was ever classified at all.

    Pure, like `resolve_cpu_active`: a snapshot of readings in,
    findings out, nothing read from the clock or the host here.
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
