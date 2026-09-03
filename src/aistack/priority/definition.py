from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JellyfinPriorityDefinition:
    """
    What "boosted" means for Jellyfin itself while it is watched,
    and where the monitor (étape 4) reaches it to find out.

    Decision #6 of 2026-09-03: the cores freed by throttling the
    background containers have to go somewhere, so Jellyfin's own
    ceiling rises too — from its already-configured 3 cores to the
    machine's full 4 — while a session is playing, and drops back
    to `normal_cpus` the moment it is not.

    **`url` and `api_key_env` mirror `SyncthingDefinition`
    exactly** — the monitor runs on the host, same as the Selection
    UI, so `url` is the host-published address
    (`http://127.0.0.1:8096`, not the Docker-internal one). GOV-P-001
    holds here too: `api_key_env` names an environment variable, it
    is never the key.
    """

    container: str
    normal_cpus: float
    boosted_cpus: float
    url: str
    api_key_env: str = ""
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class ContainerPriorityDefinition:
    """
    One background container's own "normal" state.

    **`normal_cpus` absent means unlimited, not zero.** Thirteen of
    the fourteen governed containers run with no CPU limit at all
    today (measured live on GIGABYTE, 2026-09-03) — restoring them
    "to normal" means removing the limit, not setting one. `komf`
    is the one exception: it already runs capped at 0.5 CPU, and
    restoring it to that value, not to "unlimited", is the whole
    reason this field exists instead of a single shared constant.
    """

    name: str
    normal_cpus: float | None = None


@dataclass(frozen=True)
class BackgroundPriorityDefinition:
    """
    The non-priority containers, and what "throttled" means for all of them.

    Decision #7: one shared throttled value, not a per-container
    ceiling — 0.1 CPU is enough for a container to stay alive and
    answer, and little enough to barely contest Jellyfin on a
    4-core machine. Nothing here says *when* to apply it; that
    belongs to `aistack.priority.playback.has_active_playback` and
    whatever, in a later step, turns its answer into `docker
    update` calls.
    """

    default_throttled_cpus: float
    containers: tuple[ContainerPriorityDefinition, ...] = ()


@dataclass(frozen=True)
class ResourcePriorityDefinition:
    """
    The whole governed shape of the resource-priority feature.

    Named rather than written into code, the same reason
    `ApplicationDefinition` exists for the Selection UI family: the
    fourteen background containers and Jellyfin's own two CPU
    ceilings are data the owner decided on 2026-09-03
    (`claude/PLAN-RESOURCE-PRIORITY-2026-09-03.md`), not constants
    a future change should require touching code to revise.

    **`unlimited_cpus` is a Docker fact, not a policy choice** —
    added at étape 4, deliberately not at étape 3, so it would not
    move a file already deployed before anything consumed it. Once
    a container's CPU ceiling has ever been set, Docker cannot
    clear it back to "no limit" (`apply_resource_priority`'s own
    docstring has the verified detail); restoring "unlimited" is
    instead written as a concrete cap at this many cores, the whole
    host's own count. It is host data the same way `source_root`
    is for the Selection UI family — real, not repository-relative,
    and wrong on any machine but GIGABYTE.
    """

    jellyfin: JellyfinPriorityDefinition
    background: BackgroundPriorityDefinition
    unlimited_cpus: float
