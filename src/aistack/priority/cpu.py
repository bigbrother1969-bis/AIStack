from __future__ import annotations

_EPSILON = 1e-6


def cpus_equal(current: float | None, target: float | None) -> bool:
    """
    Whether a container's current CPU ceiling already matches the target.

    **`None` and `0` are the same fact stated two ways.** Docker's
    own convention (`docker inspect`'s `HostConfig.NanoCpus: 0`
    means "no limit") is mirrored by this feature's own
    `ContainerPriorityDefinition.normal_cpus` — absent means
    unlimited, `komf`'s 0.5 (decision #5) being the one override.
    Treating `None` and `0.0` as unequal here would report every
    unlimited container as needing a write, forever.

    **An epsilon, not exact equality.** `docker inspect` answers in
    nanocpus; converting back to the same decimal a human wrote
    (`0.1`, say) can lose the last bit or two. The epsilon absorbs
    that without hiding a real change — the smallest gap between
    two governed values here is 0.1 core, four orders of magnitude
    above it.
    """

    normalised_current = current or 0.0
    normalised_target = target or 0.0

    return abs(normalised_current - normalised_target) < _EPSILON


def format_cpus(value: float | None) -> str:
    """
    How a target CPU ceiling is written for `docker update --cpus`.

    `None` (unlimited) is Docker's own `0` — passing it removes an
    existing limit rather than leaving one in place. A trailing
    `.0` is trimmed only for readability in dry-run output and
    logs; Docker's own flag parses `3` and `3.0` identically.
    """

    return f"{value or 0:g}"
