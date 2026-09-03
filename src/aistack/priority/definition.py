from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JellyfinDetectorDefinition:
    """
    Detect activity by asking Jellyfin's own `/Sessions` endpoint.

    **The original, and only, detection mechanism until 2026-09-03.**
    This is exactly what `JellyfinPriorityDefinition` used to carry
    directly on the definition itself — `url`/`api_key_env` mirror
    `SyncthingDefinition` exactly, same reasoning: the monitor runs
    on the host, so `url` is the host-published address
    (`http://127.0.0.1:8096`, not the Docker-internal one), and
    GOV-P-001 holds here too — `api_key_env` names an environment
    variable, it is never the key.

    Reshaped, not rewritten, by decision 1 of
    `claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md`: a
    priority app's detection method had to become a declared,
    per-app choice rather than the one mechanism this feature
    started with, so this struct moved from being the whole
    `jellyfin:` block to being one detector `type:` among others,
    unchanged in its own fields.
    """

    url: str
    api_key_env: str = ""
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class CpuThresholdDetectorDefinition:
    """
    Detect activity by a container's own live CPU usage.

    For a priority app with no API of its own to ask — decision 1's
    whole reason for existing: one fixed mechanism (Jellyfin's own
    `/Sessions`) cannot generalise to "any priority app", so a
    second detector type exists from the start rather than being
    added only once a second app needed one.

    **`sustained_seconds` debounces the way up, on purpose — the
    opposite of `grace.py`'s own debounce.** `resolve_boosted`
    already smooths the way *down* from active to idle (a session
    pausing for a moment must not immediately un-boost); nothing
    upstream of it smooths the way *up*, because Jellyfin's own
    `/Sessions` answer already *is* the fact, not a noisy proxy for
    it. A CPU reading is a proxy: a two-second spike from a cron
    job or a health check is not "someone is using this
    application", so this detector's own state (not `grace.py`'s)
    requires the reading to stay at or above `threshold_percent`
    for this many consecutive seconds before it reports active at
    all.

    **50% / 15s is the owner's own starting number, not a measured
    one** — chosen 2026-09-03 alongside this design, before any
    non-Jellyfin priority app exists to measure against. Revisit
    once a real app uses this detector, the same way Jellyfin's own
    CPU ceilings were corrected once measured live rather than
    guessed.
    """

    threshold_percent: float = 50.0
    sustained_seconds: float = 15.0


DetectorDefinition = JellyfinDetectorDefinition | CpuThresholdDetectorDefinition


@dataclass(frozen=True)
class PriorityAppDefinition:
    """
    One priority app: what "boosted" means for it, and how it is
    detected.

    **A list entry, not a named singular field.** Until 2026-09-03
    this feature had exactly one priority app, Jellyfin, and
    `ResourcePriorityDefinition.jellyfin` said so directly. Decision
    4 of `claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md` —
    "chaque appli suit sa propre activité" — only makes sense once
    more than one priority app can exist, so the singular field
    became a tuple of these instead, each carrying its own
    `container`, its own two CPU values, and its own `detector`.

    **`normal_cpus`/`boosted_cpus` are this app's own values,
    unaffected by any other priority app.** The monitor computes
    this app's target from this app's own detector alone — a second,
    idle priority app does not read `boosted_cpus` just because a
    different one is busy. Only the *background* containers pool
    every priority app's activity into one union.
    """

    container: str
    normal_cpus: float
    boosted_cpus: float
    detector: DetectorDefinition


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

    Decision #7 (2026-09-03, the original build): one shared
    throttled value, not a per-container ceiling — 0.1 CPU is
    enough for a container to stay alive and answer, and little
    enough to barely contest a priority app on a 4-core machine.

    **Membership here is now an owner decision made through
    `priority_ui`, not a hardcoded fourteen-container list.**
    Decision 3 of `claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-
    2026-09-03.md` — a container Docker reports that appears in
    neither this list nor `priority` is left alone entirely, never
    queried, never limited. Nothing here says *when* to apply the
    throttle; that belongs to `aistack.priority.targets.
    resolve_resource_targets`.
    """

    default_throttled_cpus: float
    containers: tuple[ContainerPriorityDefinition, ...] = ()


@dataclass(frozen=True)
class ResourcePriorityDefinition:
    """
    The whole governed shape of the resource-priority feature.

    Named rather than written into code, the same reason
    `ApplicationDefinition` exists for the Selection UI family: what
    counts as a priority app, what "boosted" means for each, which
    containers are background, and the host's own facts are data the
    owner decided — first on 2026-09-03
    (`claude/PLAN-RESOURCE-PRIORITY-2026-09-03.md`), generalised the
    same day (`claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md`)
    — not constants a future change should require touching code to
    revise.

    **`unlimited_cpus` is a Docker fact, not a policy choice** —
    added at étape 4 of the original build, deliberately not
    earlier, so it would not move a file already deployed before
    anything consumed it. Once a container's CPU ceiling has ever
    been set, Docker cannot clear it back to "no limit"
    (`apply_resource_priority`'s own docstring has the verified
    detail); restoring "unlimited" is instead written as a concrete
    cap at this many cores, the whole host's own count. It is host
    data the same way `source_root` is for the Selection UI family
    — real, not repository-relative, and wrong on any machine but
    GIGABYTE.

    **`grace_seconds` was a monitor constant until this change** —
    `GRACE_SECONDS = 60.0` in `aistack.cli.resource_priority_monitor`
    — and moves here because it was already the owner's own decision
    (2026-09-03), just not yet written down alongside the rest of
    this feature's decisions. `60.0` is its default only so that a
    definition predating this field still loads; the real file
    states it explicitly.
    """

    priority: tuple[PriorityAppDefinition, ...]
    background: BackgroundPriorityDefinition
    unlimited_cpus: float
    grace_seconds: float = 60.0
