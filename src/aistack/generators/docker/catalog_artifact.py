from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DockerCatalogArtifactGenerator:
    """Generate a Docker catalog artifact from canonical infrastructure assets."""

    def generate(self, catalog: dict[str, Any], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_path
