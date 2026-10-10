from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.health_score import DomainWeight, HealthScoreWeights

_REQUIRED_WEIGHT_FIELDS = ("domain", "points")


def load_health_score_weights_yaml(path: Path) -> HealthScoreWeights:
    """
    Load the `OPS-0008` health-score weights from YAML: one flat list of
    domain weights. A missing key raises a `ValueError` naming it.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            # Raised as `ValueError`, which is all the caller catches.
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
