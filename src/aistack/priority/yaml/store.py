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
    Load the governed resource-priority definition from YAML.

    **Written by hand, not generated** — same reasoning as
    `load_application_definition_yaml`: this file is typed by the
    owner (or, from `priority_ui`, rewritten by code that already
    respects this same shape), so a missing key here is a typo, and
    the error names which one and where, rather than pointing at a
    line inside this module.

    **`priority:` is a list now, not a singular `jellyfin:` block.**
    Reshaped 2026-09-03 by
    `claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md` — the
    generic feature can have any number of priority apps, each
    carrying its own `detector:`, tagged by `type:`.
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


def save_resource_priority_yaml(
    definition: ResourcePriorityDefinition, path: Path
) -> Path:
    """
    Save a governed resource-priority definition to YAML — the write
    side `priority_ui/app.py`'s own `/save` uses, symmetric to
    `load_resource_priority_yaml`.

    **Built explicitly, not `dataclasses.asdict` on the whole
    tree.** `DetectorDefinition` is a tagged union with no `type:`
    field on the dataclass itself — `_load_detector` switches on
    which YAML keys are present, `build_detector`
    (`aistack.priority.detectors.factory`) on `isinstance`. This is
    the one place the `type:` tag is written back, so a file this
    function writes still names it — `_dump_detector` mirrors
    `build_detector`'s own `isinstance` check for exactly that
    reason.

    A background container's `normal_cpus` is omitted entirely when
    `None`, never written as `normal_cpus: null` — YAML's own
    absence, which `_load_container`'s `data.get("normal_cpus")`
    already reads back as "unlimited", the same convention this
    whole feature carries throughout.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {
        "priority": [
            {
                "container": app.container,
                "normal_cpus": app.normal_cpus,
                "boosted_cpus": app.boosted_cpus,
                "detector": _dump_detector(app.detector),
            }
            for app in definition.priority
        ],
        "unlimited_cpus": definition.unlimited_cpus,
        "grace_seconds": definition.grace_seconds,
        "background": {
            "default_throttled_cpus": definition.background.default_throttled_cpus,
            "containers": [
                (
                    {"name": container.name, "normal_cpus": container.normal_cpus}
                    if container.normal_cpus is not None
                    else {"name": container.name}
                )
                for container in definition.background.containers
            ],
        },
    }

    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)

    return path


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
