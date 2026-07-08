from __future__ import annotations

from pathlib import Path
from typing import Protocol


class KnowledgePipeline(Protocol):
    """Executable governed knowledge pipeline.

    A Knowledge Pipeline orchestrates a deterministic chain:

        provider -> observation -> catalog -> artifact

    Pipelines are Runtime capabilities.
    They are registered and executed by the Kernel Runtime.
    """

    pipeline_id: str
    pipeline_name: str

    def run(self, output_path: Path) -> Path:
        ...
