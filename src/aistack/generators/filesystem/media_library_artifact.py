from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history


class MediaLibraryObservationArtifactGenerator:
    """
    Write a Media Library raw observation as JSON, with Observation
    History.

    Used by the on-demand `aistack.cli.media_library_discover` command
    only: `MediaLibraryProvider.collect()` is slow on a large library,
    so it is not recorded on every page view.
    """

    def generate(
        self,
        observation: dict[str, Any],
        output_path: Path,
    ) -> Path:
        content = json.dumps(observation, indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
