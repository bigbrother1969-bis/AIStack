from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.storage_shortage import StorageShortage
from aistack.contracts.storage_threshold import FREE_BYTES, StorageThreshold


def find_storage_shortage(
    readings: Sequence[StorageReading],
    thresholds: Sequence[StorageThreshold],
) -> tuple[StorageShortage, ...]:
    """
    Which mounts have crossed the threshold `OPS-0005` declares for
    them.

    Mirrors `find_unexplained_consumption`: given readings already
    collected and thresholds already declared, decides which ones are
    actually short — it never proposes a threshold itself.

    A reading for a mount with no declared threshold is silently not
    evaluated, not treated as healthy — the same "not measured is not
    zero" convention `TemperatureReading`'s absent limits already
    hold: a mount `OPS-0005` has not been asked about yet is outside
    what this call can state anything about, not thereby fine.

    Pure: readings and thresholds already collected in, shortages
    out — the same discipline `find_unexplained_consumption` and
    `evaluate` already hold.
    """

    by_mount = {threshold.mount: threshold for threshold in thresholds}

    shortages: list[StorageShortage] = []

    for reading in readings:
        threshold = by_mount.get(reading.mount)

        if threshold is None:
            continue

        if threshold.kind == FREE_BYTES:
            is_short = reading.free_bytes <= threshold.value
        else:
            is_short = reading.percent_used >= threshold.value

        if not is_short:
            continue

        shortages.append(
            StorageShortage(
                reading=reading,
                threshold_kind=threshold.kind,
                threshold_value=threshold.value,
            )
        )

    return tuple(shortages)
