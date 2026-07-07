from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DockerKnowledgeAssetGenerator:
    """Generate a Docker Knowledge Asset artifact."""

    def generate(
        self,
        asset: dict[str, Any],
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(asset, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_path
