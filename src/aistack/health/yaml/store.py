from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.health_score import DomainWeight, HealthScoreWeights

_REQUIRED_WEIGHT_FIELDS = ("domain", "points")


def load_health_score_weights_yaml(path: Path) -> HealthScoreWeights:
    """
    Load `OPS-0008`'s declared health-score weights from YAML.

    Mirrors `load_gpu_thresholds_yaml` field for field (written by
    hand, read-only, a missing key names which one and where) but not
    in shape: there is no `hosts` wrapper here — a health score is
    computed for whichever host `aistack.cli.health_render` is running
    on, over domains a cockpit already scopes to that host itself, so
    this register declares one flat list of domain weights rather than
    a per-host one.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            # Folded into the same `ValueError` a missing field already
            # produces, the same reasoning `load_gpu_thresholds_yaml`
            # gives: this loader's own caller
            # (`aistack.health.score_weights.health_score_weights`) is
            # documented never to raise anything but `ValueError`/`OSError`.
            raise ValueError(
                f"health-score weight definition {path} is not valid YAML: {error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(
            f"health-score weight definition must contain a mapping: {path}"
        )

    if "weights" not in data:
        raise ValueError(f"health-score weight definition {path} is missing: weights")

    weights_data = data["weights"]

    if not isinstance(weights_data, list):
        raise ValueError(
            f"health-score weight definition {path}: weights must be a list"
        )

    return HealthScoreWeights(
        weights=tuple(
            _load_weight(item, path, index) for index, item in enumerate(weights_data)
        )
    )


def _load_weight(data: Any, path: Path, index: int) -> DomainWeight:
    label = f"health-score weight definition {path}: weights[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    missing = [field for field in _REQUIRED_WEIGHT_FIELDS if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")

    return DomainWeight(domain=data["domain"], points=int(data["points"]))
