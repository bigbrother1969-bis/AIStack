from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history


class NetworkDockerObservationArtifactGenerator:
    """
    Generate a governed artifact from a network Docker discovery raw
    observation.

    Same shape as `BeszelObservationArtifactGenerator` — a
    provider's observation is a `dict`, and this writes it as JSON
    plus its Observation History, nothing more.
    """

    def generate(
        self,
        observation: dict[str, Any],
        output_path: Path,
    ) -> Path:
        content = json.dumps(observation, indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
