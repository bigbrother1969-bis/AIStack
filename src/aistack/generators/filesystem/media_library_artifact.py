from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history


class MediaLibraryObservationArtifactGenerator:
    """
    Generate a governed artifact from a Media Library raw observation.

    Same shape as `DockerObservationArtifactGenerator`,
    `JellyfinObservationArtifactGenerator` and
    `SyncthingObservationArtifactGenerator` — kept as its own class
    for the same reason all three are: a generator that accepts
    whatever shape its producer happens to emit cannot state what
    it writes.

    **Keeps Observation History since 2026-09-03**
    (`write_artifact_with_history`) — extended to a new on-demand
    command (`aistack.cli.media_library_discover`) rather than
    `selection_ui`'s own per-page-view call to
    `MediaLibraryProvider`, whose volume "keep everything,
    indefinitely" was not decided for. `MediaLibraryProvider.
    collect()` itself costs on the order of 1,4 s on the owner's
    real library (its own docstring's measurement) — on demand is
    the only cadence that stays cheap.
    """

    def generate(
        self,
        observation: dict[str, Any],
        output_path: Path,
    ) -> Path:
        content = json.dumps(observation, indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
