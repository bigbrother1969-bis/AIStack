from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from aistack.kernel.catalog import Catalog


class DockerCatalogArtifactGenerator:
    """
    Generate a Docker catalog artifact from a governed Catalog.

    Took a `dict` until 2026-08-29, because `DockerRuntimeCatalogBuilder`
    returned one. Both moved in the same commit: a generator that
    accepts whatever shape its producer happens to emit cannot
    state what it writes.
    """

    def generate(self, catalog: Catalog, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(asdict(catalog), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_path
