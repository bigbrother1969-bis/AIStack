from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.catalog import Catalog


class ComposeCatalogArtifactGenerator:
    """
    Generate a JSON artifact from the Compose Runtime Catalog.

    **Keeps Observation History since 2026-09-03** — see
    `write_artifact_with_history`.
    """

    def generate(self, catalog: Catalog, output_path: Path) -> Path:
        content = json.dumps(asdict(catalog), indent=2, ensure_ascii=False)
        write_artifact_with_history(content, output_path)

        return output_path
