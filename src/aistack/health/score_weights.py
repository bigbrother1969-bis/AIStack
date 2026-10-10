from __future__ import annotations

from pathlib import Path

from aistack.contracts.health_score import HealthScoreWeights
from aistack.health.yaml import load_health_score_weights_yaml


def health_score_weights(path: Path) -> tuple[HealthScoreWeights | None, str]:
    """
    Read the health-score weights at `path`, or return `None` with a note
    saying why (missing or unreadable file). Never raises.
    """

    if not path.exists():
        return None, (
            f"no health-score weight definition at {path}; health score is "
            f"not computed"
        )

    try:
        weights = load_health_score_weights_yaml(path)
    except (ValueError, OSError) as error:
        return None, (
            f"health-score weight definition not readable ({error}); health "
            f"score is not computed"
        )

    return weights, ""
