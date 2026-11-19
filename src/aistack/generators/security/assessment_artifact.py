from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history


class SecurityAssessmentArtifactGenerator:
    """
    Write the security assessment (ADR-0028) as JSON, with Observation
    History: each run is kept, so the next slices can say since when a
    finding stands.
    """

    def generate(self, assessment: dict[str, Any], output_path: Path) -> Path:
        content = json.dumps(assessment, indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
