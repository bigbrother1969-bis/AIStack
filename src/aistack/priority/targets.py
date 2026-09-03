from __future__ import annotations

from collections.abc import Mapping

from aistack.priority.definition import ResourcePriorityDefinition


def resolve_resource_targets(
    definition: ResourcePriorityDefinition, boosted: Mapping[str, bool]
) -> dict[str, float | None]:
    """
    What every governed container's CPU ceiling should be right now.

    **Pure, and separate from `apply_resource_priority` on
    purpose** — the same split `resolve_subtrees`/
    `materialise_by_hardlink` and `has_active_playback`/
    `JellyfinProvider` already draw: deciding the target state
    never touches the host, and is exhaustively testable without
    one.

    `boosted` is the caller's own concern to produce — one entry
    per `definition.priority` app, keyed by its `container` name,
    each already carrying that app's own detector answer folded
    through `aistack.priority.grace.resolve_boosted` (its own grace
    period, its own state). This function only asks what follows
    once every app's boosted state is known.

    **Each priority app's own target depends only on its own
    entry.** Decision 4 of
    `claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md` —
    "chaque appli suit sa propre activité" — a second, idle
    priority app is not boosted just because a different one is
    busy; a missing entry in `boosted` reads as "not boosted", the
    same fallback `resolve_boosted`'s own caller uses for an
    unreachable detector.

    **Background containers pool every priority app's activity
    into one union — the only place that pooling happens.**
    Throttled the moment *any* priority app is boosted, restored to
    each container's own `normal_cpus` only once none are.

    `None` in the returned mapping means *no limit*, the same
    convention `ContainerPriorityDefinition.normal_cpus` already
    carries — a background container with no override reads as
    unlimited when nothing is boosted, exactly as measured live on
    GIGABYTE 2026-09-03.
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
