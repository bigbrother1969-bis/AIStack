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

# The same conversion `evaluate_storage` uses in the other direction
# when it reports a `free_bytes` shortage back in GB — kept in step
# with it so a value round-trips: what the owner declared in GB here
# is what a report states in GB there.
_BYTES_PER_GB = 1024**3


def load_storage_thresholds_yaml(path: Path) -> StorageThresholdRegister:
    """
    Load `OPS-0005`'s declared storage thresholds from YAML.

    **Written by hand, read-only** — same reasoning as
    `load_service_categorization_yaml`: every value here is the
    owner's own declared threshold (`OPS-0005` § *Declared
    thresholds*, itself read from live `df -h` output on GIGABYTE and
    the Raspberry), so a missing key here is a typo, and the error
    names which one and where. Nothing writes this file back — no UI
    edits storage thresholds the way `priority_ui` edits resource
    priority.

    **Scoped by host, unlike `resource_priority.yml` or
    `service_categorization.yml`.** Those describe the fleet as a
    whole; a storage threshold is only meaningful for the volume it
    was declared against, on the host that mounts it — the Raspberry
    has no `/media/Films`, and GIGABYTE's `/` is fourteen times
    larger than the Raspberry's. `hosts[].host` is what
    `aistack.cli.runtime_diagnose` matches against
    `socket.gethostname()` to select the one host's thresholds this
    process should actually check.

    A `free_bytes` entry states `free_gb` in the file — the unit the
    owner declared it in ("alert below 20 GB free") — and this loader
    converts it to bytes once, the unit `StorageThreshold.value`
    stores for that kind. A `percent_used` entry states
    `percent_used` directly, already the unit `StorageThreshold
    .value` stores for that kind.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            # `load_resource_priority_yaml`/`load_service_categorization_yaml`
            # leave a syntax error to propagate as `yaml.YAMLError` — no
            # caller of either has needed to catch one yet. This loader's
            # own caller (`aistack.cli.runtime_diagnose.storage_thresholds`)
            # is documented never to raise, so a malformed file is folded
            # into the same `ValueError` a missing field already produces,
            # rather than leaving one exception type undocumented at that
            # boundary.
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
