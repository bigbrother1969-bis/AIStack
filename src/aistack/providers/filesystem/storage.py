from __future__ import annotations

import shutil

from aistack.contracts.storage_reading import StorageReading


class StorageProvider:
    """
    Observe the physical volumes the host mounts, and conclude
    nothing.

    The second thing this heritage reads about the host itself,
    after `HostProvider.collect_temperatures` — the same boundary
    (ARC-P-012), applied to disk capacity instead of heat. Reads
    `shutil.disk_usage`, the standard library's own wrapper around
    `statvfs`, rather than parsing `df`'s text output: `df -h` is
    where the reference incident (`OPS-0004`'s second reference
    incident) was read by the owner, by hand, but a provider reads
    the same numbers `df` prints without depending on its formatting.
    """

    provider_id = "aistack.provider.storage"
    provider_name = "Storage Provider"

    def collect_usage(
        self, mounts: tuple[str, ...]
    ) -> tuple[StorageReading, ...]:
        """
        Every declared mount's own usage, in one call.

        `mounts` is declared by the caller — `OPS-0005`'s own table,
        not this provider — the same "the caller says what to look
        at" `find_unexplained_consumption` already holds for
        `resource_priority.yml`; a filesystem has no self-enumeration
        a provider could trust to name only the volumes `OPS-0005`
        actually covers.

        A mount that does not exist on this host, or is not
        currently mounted, is skipped rather than raised on — never
        raises: the same convention `HostProvider.collect_temperatures`
        holds for a host with no `sensors` at all.
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
