from __future__ import annotations

from collections.abc import Mapping

from aistack.priority.definition import ResourcePriorityDefinition


def resolve_resource_targets(
    definition: ResourcePriorityDefinition, boosted: Mapping[str, bool]
) -> dict[str, float | None]:
    """
    Return the CPU ceiling every governed container should have now.

    `boosted` maps each priority app's container to its current boosted
    state (already passed through `resolve_boosted`); a missing entry
    means not boosted. Each priority app's target depends only on its own
    entry. Background containers are throttled as soon as any priority app
    is boosted, and restored to their own `normal_cpus` otherwise. `None`
    in the result means no limit. Pure: never touches the host.
    """

    any_boosted = any(
        boosted.get(app.container, False) for app in definition.priority
    )

    targets: dict[str, float | None] = {
        app.container: (
            app.boosted_cpus if boosted.get(app.container, False) else app.normal_cpus
        )
        for app in definition.priority
    }

    for container in definition.background.containers:
        targets[container.name] = (
            definition.background.default_throttled_cpus
            if any_boosted
            else container.normal_cpus
        )

    return targets
