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
    Return the mounts that cross the threshold declared for them (`OPS-0005`).

    A reading for a mount with no declared threshold is skipped, not treated
    as healthy.
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
