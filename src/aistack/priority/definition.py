from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JellyfinDetectorDefinition:
    """
    Detect activity by asking Jellyfin's `/Sessions` endpoint.

    The monitor runs on the host, so `url` is the host-published address
    (e.g. `http://127.0.0.1:8096`). `api_key_env` names an environment
    variable; it is never the key itself.
    """

    url: str
    api_key_env: str = ""
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class CpuThresholdDetectorDefinition:
    """
    Detect activity by a container's live CPU usage, for priority apps with
    no API to ask.

    A CPU reading is a noisy proxy (a cron job or healthcheck can spike it),
    so the detector reports active only after the reading stays at or above
    `threshold_percent` for `sustained_seconds`. This debounces the way up;
    `grace.resolve_boosted` debounces the way down. The defaults are
    estimates, not measurements.
    """

    threshold_percent: float = 50.0
    sustained_seconds: float = 15.0


DetectorDefinition = JellyfinDetectorDefinition | CpuThresholdDetectorDefinition


@dataclass(frozen=True)
class PriorityAppDefinition:
    """
    One priority app: its container, its normal and boosted CPU values, and
    its detector.

    Each app's target depends only on its own detector: an idle priority app
    is not boosted because another one is busy. Only background containers
    pool the activity of all priority apps.
    """

    container: str
    normal_cpus: float
    boosted_cpus: float
    detector: DetectorDefinition


@dataclass(frozen=True)
class ContainerPriorityDefinition:
    """
    One background container's "normal" state.

    `normal_cpus` absent means unlimited, not zero; set it for a container
    that normally runs with a cap, so restoring it keeps that cap.
    """

    name: str
    normal_cpus: float | None = None


@dataclass(frozen=True)
class BackgroundPriorityDefinition:
    """
    The non-priority containers and the shared throttled CPU value.

    A container listed neither here nor in `priority` is never touched.
    When to throttle is decided by `aistack.priority.targets.resolve_resource_targets`.
    """

    default_throttled_cpus: float
    containers: tuple[ContainerPriorityDefinition, ...] = ()


@dataclass(frozen=True)
class ResourcePriorityDefinition:
    """
    The whole resource-priority configuration, loaded from
    `resource_priority.yml`.

    `unlimited_cpus` is the host's core count. Once a container has a CPU
    ceiling, Docker cannot clear it back to "no limit", so "unlimited" is
    written as a cap at this many cores (see `apply_resource_priority`).
    `grace_seconds` defaults to 60 so that files without the field still load.
    """

    priority: tuple[PriorityAppDefinition, ...]
    background: BackgroundPriorityDefinition
    unlimited_cpus: float
    grace_seconds: float = 60.0
