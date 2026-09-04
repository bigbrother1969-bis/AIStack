from __future__ import annotations

from pathlib import Path

from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.generators.docker import (
    DockerCatalogArtifactGenerator,
    DockerExplanationArtifactGenerator,
)
from aistack.kernel.bootstrap import create_kernel


def main() -> None:
    ctx = create_kernel()
    observation = ctx.registries.providers.get("docker").collect()
    catalog = DockerRuntimeCatalogBuilder().build(observation)

    output_path = DockerCatalogArtifactGenerator().generate(
        catalog=catalog,
        output_path=Path("reports/generated/docker-runtime-catalog.json"),
    )

    print(f"Docker runtime catalog written to {output_path}")

    # STD-0300 VS-1 criterion 1.4 asks for a generated explanation
    # alongside the catalog it explains — added 2026-09-04, run in
    # the same pass so the two are always taken from one
    # observation rather than two runs that could disagree.
    explanation_path = DockerExplanationArtifactGenerator().generate(
        catalog=catalog,
        output_path=Path("reports/generated/docker-runtime-explanation.txt"),
    )

    print(f"Docker runtime explanation written to {explanation_path}")


if __name__ == "__main__":
    main()
