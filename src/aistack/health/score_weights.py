from __future__ import annotations

from pathlib import Path

from aistack.contracts.health_score import HealthScoreWeights
from aistack.health.yaml import load_health_score_weights_yaml


def health_score_weights(path: Path) -> tuple[HealthScoreWeights | None, str]:
    """
    Read `path`'s declared health-score weights, or `None` with a note
    explaining why — never raises.

    Mirrors `storage_thresholds_for_host`/`backup_thresholds_for_host`/
    `gpu_thresholds_for_host`'s own two-branch shape (missing file,
    unreadable file), minus the third branch none of those three
    needed here either: `OPS-0008` is not scoped by host, so there is
    no "declared for some hosts but not this one" state to name —
    only "the file exists and reads" or it does not.
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
