from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from aistack.kernel.catalog import Catalog


class ComposeCatalogArtifactGenerator:
    """Generate a JSON artifact from the Compose Runtime Catalog."""

    def generate(self, catalog: Catalog, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(
            json.dumps(asdict(catalog), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path
