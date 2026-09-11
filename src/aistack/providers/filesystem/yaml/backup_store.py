from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.backup_threshold import (
    BackupThreshold,
    BackupThresholdRegister,
    HostBackupThresholds,
)

_REQUIRED_HOST_FIELDS = ("host", "thresholds")
_REQUIRED_THRESHOLD_FIELDS = ("path", "max_age_days")

_HOURS_PER_DAY = 24


def load_backup_thresholds_yaml(path: Path) -> BackupThresholdRegister:
    """
    Load `OPS-0006`'s declared backup thresholds from YAML.

    Mirrors `load_storage_thresholds_yaml` field for field: written by
    hand, read-only (every value here is the owner's own declared
    threshold — `OPS-0006` § *Declared thresholds* — so a missing key
    is a typo, and the error names which one and where; nothing
    writes this file back), and scoped by host the same way (`hosts
    []. host` is what `aistack.cli.runtime_diagnose` matches against
    `socket.gethostname()`).

    A threshold entry states `max_age_days` in the file — the unit
    the owner declared it in ("7 jours") — and this loader converts
    it to hours once, the unit `BackupThreshold.max_age_hours` stores,
    the same single-point conversion `load_storage_thresholds_yaml`
    already holds for `free_gb` → bytes.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            # `load_storage_thresholds_yaml` folds a YAML syntax error
            # into the same `ValueError` a missing field already
            # produces, for the same reason: this loader's own caller
            # (`aistack.providers.filesystem.thresholds
            # .backup_thresholds_for_host`) is documented never to
            # raise anything but `ValueError`/`OSError`.
            raise ValueError(
                f"Backup threshold definition {path} is not valid YAML: "
                f"{error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(
            f"Backup threshold definition must contain a mapping: {path}"
        )

    if "hosts" not in data:
        raise ValueError(f"Backup threshold definition {path} is missing: hosts")

    hosts_data = data["hosts"]

    if not isinstance(hosts_data, list):
        raise ValueError(
            f"Backup threshold definition {path}: hosts must be a list"
        )

    return BackupThresholdRegister(
        hosts=tuple(
            _load_host(item, path, index)
            for index, item in enumerate(hosts_data)
        )
    )


def _load_host(data: Any, path: Path, index: int) -> HostBackupThresholds:
    label = f"Backup threshold definition {path}: hosts[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_HOST_FIELDS, label)

    thresholds_data = data["thresholds"]

    if not isinstance(thresholds_data, list):
        raise ValueError(f"{label}.thresholds must be a list")

    return HostBackupThresholds(
        host=data["host"],
        thresholds=tuple(
            _load_threshold(item, path, index, threshold_index)
            for threshold_index, item in enumerate(thresholds_data)
        ),
    )


def _load_threshold(
    data: Any, path: Path, host_index: int, threshold_index: int
) -> BackupThreshold:
    label = (
        f"Backup threshold definition {path}: "
        f"hosts[{host_index}].thresholds[{threshold_index}]"
    )

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_THRESHOLD_FIELDS, label)

    max_age_hours = float(data["max_age_days"]) * _HOURS_PER_DAY

    return BackupThreshold(path=data["path"], max_age_hours=max_age_hours)


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
