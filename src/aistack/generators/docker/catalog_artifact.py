from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.catalog import Catalog


class DockerCatalogArtifactGenerator:
    """
    Generate a Docker catalog artifact from a governed Catalog.

    Took a `dict` until 2026-08-29, because `DockerRuntimeCatalogBuilder`
    returned one. Both moved in the same commit: a generator that
    accepts whatever shape its producer happens to emit cannot
    state what it writes.

    **Keeps Observation History since 2026-09-03** — see
    `write_artifact_with_history`.
    """

    def generate(self, catalog: Catalog, output_path: Path) -> Path:
        content = json.dumps(asdict(catalog), indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
