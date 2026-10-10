from __future__ import annotations

from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.catalog import Catalog
from aistack.catalog.docker.explanation import explain_docker_catalog


class DockerExplanationArtifactGenerator:
    """
    Generate the Docker catalog's explanation artifact: one sentence
    per container, from `explain_docker_catalog`, with Observation
    History. Same shape as `DockerCatalogArtifactGenerator`.
    """

    def generate(self, catalog: Catalog, output_path: Path) -> Path:
        content = "\n".join(explain_docker_catalog(catalog)) + "\n"
        write_artifact_with_history(content, output_path)
        return output_path
