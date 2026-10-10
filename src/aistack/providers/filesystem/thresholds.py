from __future__ import annotations

from pathlib import Path

from aistack.contracts.backup_threshold import BackupThreshold
from aistack.contracts.storage_threshold import StorageThreshold
from aistack.providers.filesystem.yaml import (
    load_backup_thresholds_yaml,
    load_storage_thresholds_yaml,
)


def storage_thresholds_for_host(
    path: Path, hostname: str
) -> tuple[tuple[StorageThreshold, ...], str]:
    """Return `path`'s storage thresholds for `hostname`, or an empty tuple
    and a note explaining why. Never raises.

    `hostname` (the caller's `socket.gethostname()`) narrows a fleet-wide
    file to the host this process runs on.
    """

    if not path.exists():
        return (), (
            f"no storage-threshold definition at {path}; storage "
            f"capacity is not checked"
        )

    try:
        register = load_storage_thresholds_yaml(path)
    except (ValueError, OSError) as error:
        return (), (
            f"storage-threshold definition not readable ({error}); "
            f"storage capacity is not checked"
        )

    thresholds = register.for_host(hostname)

    if not thresholds:
        return (), (
            f"no storage thresholds declared for host {hostname!r} in "
            f"{path}; storage capacity is not checked"
        )

    return thresholds, ""


def backup_thresholds_for_host(
    path: Path, hostname: str
) -> tuple[tuple[BackupThreshold, ...], str]:
    """Return `path`'s backup thresholds for `hostname`, or an empty tuple
    and a note explaining why. Never raises.

    Same branches and messages as `storage_thresholds_for_host`.
    """

    if not path.exists():
        return (), (
            f"no backup-threshold definition at {path}; backup freshness "
            f"is not checked"
        )

    try:
        register = load_backup_thresholds_yaml(path)
    except (ValueError, OSError) as error:
        return (), (
            f"backup-threshold definition not readable ({error}); backup "
            f"freshness is not checked"
        )

    thresholds = register.for_host(hostname)

    if not thresholds:
        return (), (
            f"no backup thresholds declared for host {hostname!r} in "
            f"{path}; backup freshness is not checked"
        )

    return thresholds, ""
