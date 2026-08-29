from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from aistack.kernel.catalog.views import CatalogView


class CatalogViewArtifactGenerator:
    """
    Generate a governed artifact from a Catalog View.

    Generic on purpose: a Catalog View names no technology, so
    neither does the generator that writes one. It sits beside
    the technology-scoped generator packages rather than inside
    one, which is what ADR-0004 § *Decision* asks of anything
    that does not depend on a specific technology.

    **It exists because the path it serves had none.** Until
    2026-08-29 `docker_selection_catalog` serialised with
    `write_text` and a `default=lambda item: item.__dict__` hook
    — ADR-0002 § *Implementation state* recorded that the live
    path wrote its artifact with no Artifact Generator at all.
    """

    def generate(self, view: CatalogView, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(asdict(view), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_path
