from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DockerObservationArtifactGenerator:
    """Generate a governed artifact from Docker raw observations."""

    def generate(
        self,
        observation: dict[str, Any],
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(observation, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_path
