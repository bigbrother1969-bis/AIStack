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
    """Load the declared backup thresholds (`OPS-0006`) from YAML.

    The file is written by hand, so errors name the missing key and where.
    `hosts[].host` is matched against `socket.gethostname()`.
    `max_age_days` is converted once to `BackupThreshold.max_age_hours`.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            # `backup_thresholds_for_host` only catches ValueError/OSError.
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
