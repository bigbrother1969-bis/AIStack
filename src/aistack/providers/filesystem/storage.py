from __future__ import annotations

import shutil

from aistack.contracts.storage_reading import StorageReading


class StorageProvider:
    """Observe the usage of the host's mounted volumes, without drawing
    conclusions.

    Uses `shutil.disk_usage` (`statvfs`) rather than parsing `df` output.
    """

    provider_id = "aistack.provider.storage"
    provider_name = "Storage Provider"

    def collect_usage(
        self, mounts: tuple[str, ...]
    ) -> tuple[StorageReading, ...]:
        """Usage of each mount the caller declares (`OPS-0005`).

        Never raises: a mount that is missing or not mounted is skipped.
        """

        readings: list[StorageReading] = []

        for mount in mounts:
            try:
                usage = shutil.disk_usage(mount)
            except OSError:
                continue

            readings.append(
                StorageReading(
                    mount=mount,
                    total_bytes=usage.total,
                    used_bytes=usage.used,
                    free_bytes=usage.free,
                )
            )

        return tuple(readings)
