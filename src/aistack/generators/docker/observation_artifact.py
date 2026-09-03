from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history


class DockerObservationArtifactGenerator:
    """
    Generate a governed artifact from Docker raw observations.

    **Keeps Observation History since 2026-09-03**
    (`write_artifact_with_history`) — every run used to overwrite
    the one file this generator writes, discarding the previous
    observation. `output_path` still carries the latest observation
    exactly as before; a timestamped copy now survives beside it.
    """

    def generate(
        self,
        observation: dict[str, Any],
        output_path: Path,
    ) -> Path:
        content = json.dumps(observation, indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
