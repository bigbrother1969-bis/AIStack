from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.catalog import Catalog


class DockerCatalogArtifactGenerator:
    """
    Write a Docker `Catalog` as JSON, with Observation History
    (see `write_artifact_with_history`).
    """

    def generate(self, catalog: Catalog, output_path: Path) -> Path:
        content = json.dumps(asdict(catalog), indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
