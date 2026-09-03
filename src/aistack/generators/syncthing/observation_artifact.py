from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history


class SyncthingObservationArtifactGenerator:
    """
    Generate a governed artifact from a Syncthing raw observation.

    Same shape as `DockerObservationArtifactGenerator` and
    `JellyfinObservationArtifactGenerator` — kept as its own class
    for the same reason both of those are: a generator that accepts
    whatever shape its producer happens to emit cannot state what
    it writes.

    **Keeps Observation History since 2026-09-03**
    (`write_artifact_with_history`) — extended from Jellyfin the
    same day to a new on-demand command
    (`aistack.cli.syncthing_discover`) rather than `selection_ui`'s
    own per-page-view call, whose volume "keep everything,
    indefinitely" was not decided for.
    """

    def generate(
        self,
        observation: dict[str, Any],
        output_path: Path,
    ) -> Path:
        content = json.dumps(observation, indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
