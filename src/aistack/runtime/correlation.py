from __future__ import annotations

from collections.abc import Iterable, Mapping

from aistack.contracts.correlated_finding import CorrelatedFinding


CONTAINER_REFERENCE = "docker ps --no-trunc"


def correlate_findings(
    containers: Iterable[str],
    container_commands: Mapping[str, str],
    processes: Mapping[str, str],
    deployment_definitions: Mapping[str, tuple[str, str]],
) -> tuple[CorrelatedFinding, ...]:
    """
    Stitch three independently-collected observations of the same
    containers into one finding each. `STD-0300` § VS-4 criterion
    4.2.

    **`containers` names which subjects to correlate — it is not
    derived from the maps.** This runs after 4.1 or 4.3 has already
    named a container worth a closer look; correlating every
    container on the host regardless would produce sixty findings a
    reader did not ask for, for the sixty this repository cannot
    even describe a deployment definition for.

    A name absent from `container_commands` or `processes` reads as
    the empty string, not an error — the same convention `states.get`
    already carries in `runtime_diagnose`'s own report: a reference
    that could not be resolved is a fact about the collection, worth
    seeing, not a reason to drop the correlation entirely.

    `deployment_definitions` is `container -> (command, reference)`
    for the few containers this repository can actually describe.
    Absence means exactly what `CorrelatedFinding` already declares:
    unasserted, not `None` standing in for "nobody looked" versus
    "declared as having none" — there is no third state here, unlike
    `LifecycleRegister`, because a deployment definition either names
    a command or it does not exist to ask.
    """

    return tuple(
        CorrelatedFinding(
            container=container,
            container_command=container_commands.get(container, ""),
            container_reference=CONTAINER_REFERENCE,
            process_command=processes.get(container, ""),
            process_reference=f"docker top {container}",
            deployment_command=deployment_definitions.get(container, (None, None))[0],
            deployment_reference=deployment_definitions.get(container, (None, None))[1],
        )
        for container in containers
    )
