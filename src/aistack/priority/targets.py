from __future__ import annotations

from aistack.priority.definition import ResourcePriorityDefinition


def resolve_resource_targets(
    definition: ResourcePriorityDefinition, playing: bool
) -> dict[str, float | None]:
    """
    What every governed container's CPU ceiling should be right now.

    **Pure, and separate from `apply_resource_priority` on
    purpose** — the same split `resolve_subtrees`/
    `materialise_by_hardlink` and `has_active_playback`/
    `JellyfinProvider` already draw: deciding the target state
    never touches the host, and is exhaustively testable without
    one.

    `playing` is the caller's own concern to produce — ordinarily
    `has_active_playback(JellyfinProvider(...).collect()["jellyfin"]
    ["sessions"])` — this function only asks what follows once that
    is known. Jellyfin itself is keyed by
    `definition.jellyfin.container` alongside the fourteen
    background containers, in the one mapping a caller needs to
    apply.

    `None` in the returned mapping means *no limit*, the same
    convention `ContainerPriorityDefinition.normal_cpus` already
    carries — a background container with no override reads as
    unlimited when not playing, exactly as measured live on
    GIGABYTE 2026-09-03.
    """

    targets: dict[str, float | None] = {
        definition.jellyfin.container: (
            definition.jellyfin.boosted_cpus
            if playing
            else definition.jellyfin.normal_cpus
        )
    }

    for container in definition.background.containers:
        targets[container.name] = (
            definition.background.default_throttled_cpus
            if playing
            else container.normal_cpus
        )

    return targets
