from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history


class JellyfinObservationArtifactGenerator:
    """
    Generate a governed artifact from a Jellyfin raw observation.

    Same shape as `DockerObservationArtifactGenerator` — a
    provider's observation is a `dict`, and this writes it as JSON
    plus its Observation History, nothing more — kept as its own
    generator rather than reused across providers because a
    generator that accepts whatever shape its producer happens to
    emit cannot state what it writes (`DockerCatalogArtifactGenerator`'s
    own docstring, 2026-08-29, is where this project settled that).

    **Keeps Observation History since 2026-09-03**
    (`write_artifact_with_history`) — the extension of the same
    mechanism from Docker/Compose to Jellyfin, owner-scoped to a new
    on-demand command (`aistack.cli.jellyfin_discover`) rather than
    the CPU monitor's own 5-second poll, whose volume was not what
    "keep everything, indefinitely" was decided for.
    """

    def generate(
        self,
        observation: dict[str, Any],
        output_path: Path,
    ) -> Path:
        content = json.dumps(observation, indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
