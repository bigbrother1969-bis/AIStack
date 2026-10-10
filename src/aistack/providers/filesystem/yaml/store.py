from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.storage_threshold import (
    FREE_BYTES,
    KINDS,
    HostStorageThresholds,
    StorageThreshold,
    StorageThresholdRegister,
)

_REQUIRED_HOST_FIELDS = ("host", "thresholds")
_REQUIRED_THRESHOLD_FIELDS = ("mount", "kind")

# Must match the conversion `evaluate_storage` uses to report GB back.
_BYTES_PER_GB = 1024**3


def load_storage_thresholds_yaml(path: Path) -> StorageThresholdRegister:
    """Load the declared storage thresholds (`OPS-0005`) from YAML.

    The file is written by hand and read-only, so errors name the missing
    key and where. Thresholds are scoped by host, since a volume only
    exists on the host that mounts it; `hosts[].host` is matched against
    `socket.gethostname()`. A `free_bytes` entry gives `free_gb`, converted
    once to bytes; a `percent_used` entry gives `percent_used`.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            # `storage_thresholds_for_host` only catches ValueError/OSError.
            raise ValueError(
                f"Storage threshold definition {path} is not valid YAML: "
                f"{error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(
            f"Storage threshold definition must contain a mapping: {path}"
        )

    if "hosts" not in data:
        raise ValueError(f"Storage threshold definition {path} is missing: hosts")

    hosts_data = data["hosts"]

    if not isinstance(hosts_data, list):
        raise ValueError(
            f"Storage threshold definition {path}: hosts must be a list"
        )

    return StorageThresholdRegister(
        hosts=tuple(
            _load_host(item, path, index)
            for index, item in enumerate(hosts_data)
        )
    )


def _load_host(data: Any, path: Path, index: int) -> HostStorageThresholds:
    label = f"Storage threshold definition {path}: hosts[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_HOST_FIELDS, label)

    thresholds_data = data["thresholds"]

    if not isinstance(thresholds_data, list):
        raise ValueError(f"{label}.thresholds must be a list")

    return HostStorageThresholds(
        host=data["host"],
        thresholds=tuple(
            _load_threshold(item, path, index, threshold_index)
            for threshold_index, item in enumerate(thresholds_data)
        ),
    )


def _load_threshold(
    data: Any, path: Path, host_index: int, threshold_index: int
) -> StorageThreshold:
    label = (
        f"Storage threshold definition {path}: "
        f"hosts[{host_index}].thresholds[{threshold_index}]"
    )

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_THRESHOLD_FIELDS, label)

    kind = data["kind"]

    if kind not in KINDS:
        raise ValueError(
            f"{label} declares an unknown threshold kind {kind!r}; "
            f"OPS-0005 declares only {KINDS}"
        )

    if kind == FREE_BYTES:
        _require(data, ("free_gb",), label)
        value = float(data["free_gb"]) * _BYTES_PER_GB
    else:
        _require(data, ("percent_used",), label)
        value = float(data["percent_used"])

    return StorageThreshold(mount=data["mount"], kind=kind, value=value)


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
