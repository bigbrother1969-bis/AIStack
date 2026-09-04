from __future__ import annotations

from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.catalog import Catalog
from aistack.catalog.docker.explanation import explain_docker_catalog


class DockerExplanationArtifactGenerator:
    """
    Generate the Docker catalog's explanation artifact — one
    sentence per container, per `explain_docker_catalog`.

    Mirrors `DockerCatalogArtifactGenerator` exactly: same
    `generate(catalog, output_path) -> Path` shape, same history
    mechanism, so a reader of one already knows the other. Written
    2026-09-04 for `STD-0300` VS-1 criterion 1.4, which asks for a
    generated explanation and had nothing to point at until now.
    """

    def generate(self, catalog: Catalog, output_path: Path) -> Path:
        content = "\n".join(explain_docker_catalog(catalog)) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
