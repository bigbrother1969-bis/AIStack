from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.gpu_threshold import (
    KINDS,
    TEMPERATURE_CELSIUS,
    GpuThreshold,
    GpuThresholdRegister,
    HostGpuThresholds,
)

_REQUIRED_HOST_FIELDS = ("host", "thresholds")
_REQUIRED_THRESHOLD_FIELDS = ("kind",)


def load_gpu_thresholds_yaml(path: Path) -> GpuThresholdRegister:
    """Load the declared GPU thresholds (`OPS-0007`) from YAML.

    The file is written by hand, so errors name the missing key and where.
    `hosts[].host` is matched against `socket.gethostname()`. A
    `temperature_celsius` entry gives `celsius`; the percent kinds give
    `percent`. No unit conversion.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            # `gpu_thresholds_for_host` only catches ValueError/OSError.
            raise ValueError(
                f"GPU threshold definition {path} is not valid YAML: {error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(
            f"GPU threshold definition must contain a mapping: {path}"
        )

    if "hosts" not in data:
        raise ValueError(f"GPU threshold definition {path} is missing: hosts")

    hosts_data = data["hosts"]

    if not isinstance(hosts_data, list):
        raise ValueError(f"GPU threshold definition {path}: hosts must be a list")

    return GpuThresholdRegister(
        hosts=tuple(
            _load_host(item, path, index)
            for index, item in enumerate(hosts_data)
        )
    )


def _load_host(data: Any, path: Path, index: int) -> HostGpuThresholds:
    label = f"GPU threshold definition {path}: hosts[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_HOST_FIELDS, label)

    thresholds_data = data["thresholds"]

    if not isinstance(thresholds_data, list):
        raise ValueError(f"{label}.thresholds must be a list")

    return HostGpuThresholds(
        host=data["host"],
        thresholds=tuple(
            _load_threshold(item, path, index, threshold_index)
            for threshold_index, item in enumerate(thresholds_data)
        ),
    )


def _load_threshold(
    data: Any, path: Path, host_index: int, threshold_index: int
) -> GpuThreshold:
    label = (
        f"GPU threshold definition {path}: "
        f"hosts[{host_index}].thresholds[{threshold_index}]"
    )

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_THRESHOLD_FIELDS, label)

    kind = data["kind"]

    if kind not in KINDS:
        raise ValueError(
            f"{label} declares an unknown threshold kind {kind!r}; "
            f"OPS-0007 declares only {KINDS}"
        )

    if kind == TEMPERATURE_CELSIUS:
        _require(data, ("celsius",), label)
        value = float(data["celsius"])
    else:
        _require(data, ("percent",), label)
        value = float(data["percent"])

    return GpuThreshold(kind=kind, value=value)


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
