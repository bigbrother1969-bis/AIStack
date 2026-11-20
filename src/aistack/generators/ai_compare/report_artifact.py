from __future__ import annotations

from pathlib import Path

from aistack.generators.history import write_artifact_with_history


class AiCompareReportArtifactGenerator:
    """
    Write the comparison of the local engines as markdown, with Observation
    History: the latest one stays at `output_path`, every other run is kept
    beside it under `history/`, so two runs can be read against each other.
    """

    def generate(self, report: str, output_path: Path) -> tuple[Path, Path]:
        return write_artifact_with_history(report, output_path)
