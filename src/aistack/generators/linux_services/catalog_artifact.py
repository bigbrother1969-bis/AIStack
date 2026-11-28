from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.catalog import Catalog


class LinuxServicesCatalogArtifactGenerator:
    """
    Write a Linux services `Catalog` as JSON, with Observation History
    (see `write_artifact_with_history`) — the same shape as
    `DockerCatalogArtifactGenerator`.
    """

    def generate(self, catalog: Catalog, output_path: Path) -> Path:
        content = json.dumps(asdict(catalog), indent=2, ensure_ascii=False) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
