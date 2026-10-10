from __future__ import annotations

_EPSILON = 1e-6


def cpus_equal(current: float | None, target: float | None) -> bool:
    """
    Whether a container's current CPU ceiling already matches the target.

    `None` and `0` both mean "no limit" (Docker's `NanoCpus: 0`); treating
    them as different would report every unlimited container as needing a
    write. An epsilon absorbs the rounding of nanocpus back to decimals.
    """

    normalised_current = current or 0.0
    normalised_target = target or 0.0

    return abs(normalised_current - normalised_target) < _EPSILON


def format_cpus(value: float | None) -> str:
    """
    Format a CPU ceiling for `docker update --cpus`.

    `None` (unlimited) becomes `0`, which removes an existing limit.
    """

    return f"{value or 0:g}"
