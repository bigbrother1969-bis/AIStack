from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    CpuThresholdDetectorDefinition,
    DetectorDefinition,
    JellyfinDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)

_REQUIRED_FIELDS = ("priority", "background", "unlimited_cpus")
_REQUIRED_PRIORITY_FIELDS = ("container", "normal_cpus", "boosted_cpus", "detector")
_REQUIRED_BACKGROUND_FIELDS = ("default_throttled_cpus", "containers")
_REQUIRED_CONTAINER_FIELDS = ("name",)

_DEFAULT_GRACE_SECONDS = 60.0

_REQUIRED_JELLYFIN_DETECTOR_FIELDS = ("url",)


def load_resource_priority_yaml(path: Path) -> ResourcePriorityDefinition:
    """
    Load the resource-priority definition from YAML.

    The file is edited by hand or by the priority screen; a missing key
    raises a `ValueError` naming the key and the file. `priority:` is a list
    of apps, each with a `detector:` tagged by `type:`.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(
            f"Resource priority definition must contain a mapping: {path}"
        )

    _require(data, _REQUIRED_FIELDS, f"Resource priority definition {path}")

    priority_data = data["priority"]

    if not isinstance(priority_data, list):
        raise ValueError(
            f"Resource priority definition {path}: priority must be a list"
        )

    return ResourcePriorityDefinition(
        priority=tuple(
            _load_priority_app(item, path, index)
            for index, item in enumerate(priority_data)
        ),
        background=_load_background(data["background"], path),
        unlimited_cpus=float(data["unlimited_cpus"]),
        grace_seconds=float(data.get("grace_seconds") or _DEFAULT_GRACE_SECONDS),
    )


def _load_priority_app(
    data: Any, path: Path, index: int
) -> PriorityAppDefinition:
    label = f"Resource priority definition {path}: priority[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_PRIORITY_FIELDS, label)

    return PriorityAppDefinition(
        container=data["container"],
        normal_cpus=float(data["normal_cpus"]),
        boosted_cpus=float(data["boosted_cpus"]),
        detector=_load_detector(data["detector"], path, index),
    )


def _load_detector(data: Any, path: Path, index: int) -> DetectorDefinition:
    label = f"Resource priority definition {path}: priority[{index}].detector"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, ("type",), label)

    detector_type = data["type"]

    if detector_type == "jellyfin":
        return _load_jellyfin_detector(data, label)

    if detector_type == "cpu_threshold":
        return _load_cpu_threshold_detector(data)

    raise ValueError(
        f"{label}: unknown detector type {detector_type!r} "
        "(known: jellyfin, cpu_threshold)"
    )


def _load_jellyfin_detector(
    data: dict, label: str
) -> JellyfinDetectorDefinition:
    _require(data, _REQUIRED_JELLYFIN_DETECTOR_FIELDS, label)

    return JellyfinDetectorDefinition(
        url=data["url"],
        api_key_env=data.get("api_key_env", ""),
        timeout_seconds=float(data.get("timeout_seconds") or 5.0),
    )


def _load_cpu_threshold_detector(data: dict) -> CpuThresholdDetectorDefinition:
    threshold_percent = data.get("threshold_percent")
    sustained_seconds = data.get("sustained_seconds")

    return CpuThresholdDetectorDefinition(
        threshold_percent=(
            float(threshold_percent) if threshold_percent is not None else 50.0
        ),
        sustained_seconds=(
            float(sustained_seconds) if sustained_seconds is not None else 15.0
        ),
    )


def _load_background(data: Any, path: Path) -> BackgroundPriorityDefinition:
    label = f"Resource priority definition {path}: background"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_BACKGROUND_FIELDS, label)

    containers_data = data["containers"]

    if not isinstance(containers_data, list):
        raise ValueError(f"{label}.containers must be a list")

    return BackgroundPriorityDefinition(
        default_throttled_cpus=float(data["default_throttled_cpus"]),
        containers=tuple(
            _load_container(item, path, index)
            for index, item in enumerate(containers_data)
        ),
    )


def _load_container(
    data: Any, path: Path, index: int
) -> ContainerPriorityDefinition:
    label = f"Resource priority definition {path}: background.containers[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_CONTAINER_FIELDS, label)

    normal_cpus = data.get("normal_cpus")

    return ContainerPriorityDefinition(
        name=data["name"],
        normal_cpus=float(normal_cpus) if normal_cpus is not None else None,
    )


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")


_HEADER_COMMENT = """\
# Resource priority definition — priority apps vs. background containers.
#
# Loaded by `load_resource_priority_yaml`
# (`src/aistack/priority/yaml/store.py`), and read by the
# monitor (`aistack.cli.resource_priority_monitor`).
#
# This header and the section comments below are rewritten on every
# save from the CPU priority screen: edits to comments are not kept.

"""

_PRIORITY_COMMENT = """\
# One entry per priority app — boosted to its own `boosted_cpus`
# while its own `detector` reports activity, restored to
# `normal_cpus` otherwise. Each app follows only its own activity,
# never another app's.
"""

_UNLIMITED_COMMENT = """\
# The host's own core count. Docker cannot clear a CPU limit once
# one has been set, so "unlimited" is written as a cap at every core
# the host has — operationally the same thing.
"""

_GRACE_COMMENT = """\
# Seconds a priority app must sit idle before its background
# containers are throttled back down — long enough to absorb a short
# gap without thrashing, short enough that closing the app for good
# gives the machine back promptly.
"""

_BACKGROUND_COMMENT = """\
# `default_throttled_cpus` applies to every container below while
# any priority app is active. A container's own `normal_cpus`, if
# given, is only its resting-state value — omit it for "no limit at
# rest". What is classified here (or as `priority` above) is an
# owner decision made through `priority_ui`, or by hand; anything
# Docker reports that is classified in neither place is left alone
# entirely.
"""


def save_resource_priority_yaml(
    definition: ResourcePriorityDefinition, path: Path
) -> Path:
    """
    Save a resource-priority definition to YAML, the inverse of
    `load_resource_priority_yaml`.

    Built explicitly rather than with `dataclasses.asdict`, so the
    detector's `type:` tag is written back. A background container's
    `normal_cpus` is omitted when `None` (unlimited). Each top-level key is
    dumped separately with a static comment above it, because PyYAML
    drops comments and the file would otherwise lose its documentation on
    every save.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    priority_data = [
        {
            "container": app.container,
            "normal_cpus": app.normal_cpus,
            "boosted_cpus": app.boosted_cpus,
            "detector": _dump_detector(app.detector),
        }
        for app in definition.priority
    ]

    background_data = {
        "default_throttled_cpus": definition.background.default_throttled_cpus,
        "containers": [
            (
                {"name": container.name, "normal_cpus": container.normal_cpus}
                if container.normal_cpus is not None
                else {"name": container.name}
            )
            for container in definition.background.containers
        ],
    }

    with path.open("w", encoding="utf-8") as stream:
        stream.write(_HEADER_COMMENT)

        stream.write(_PRIORITY_COMMENT)
        _dump_section(stream, "priority", priority_data)
        stream.write("\n")

        stream.write(_UNLIMITED_COMMENT)
        _dump_section(stream, "unlimited_cpus", definition.unlimited_cpus)
        stream.write("\n")

        stream.write(_GRACE_COMMENT)
        _dump_section(stream, "grace_seconds", definition.grace_seconds)
        stream.write("\n")

        stream.write(_BACKGROUND_COMMENT)
        _dump_section(stream, "background", background_data)

    return path


def _dump_section(stream: Any, key: str, value: Any) -> None:
    yaml.safe_dump({key: value}, stream, sort_keys=False, allow_unicode=True)


def _dump_detector(detector: DetectorDefinition) -> dict[str, Any]:
    if isinstance(detector, CpuThresholdDetectorDefinition):
        return {
            "type": "cpu_threshold",
            "threshold_percent": detector.threshold_percent,
            "sustained_seconds": detector.sustained_seconds,
        }

    return {
        "type": "jellyfin",
        "url": detector.url,
        "api_key_env": detector.api_key_env,
        "timeout_seconds": detector.timeout_seconds,
    }
