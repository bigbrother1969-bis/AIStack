from __future__ import annotations

from pathlib import Path

from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.generators.docker import DockerCatalogArtifactGenerator
from aistack.kernel.bootstrap import create_kernel


def main() -> None:
    ctx = create_kernel()
    observation = ctx.providers.get("docker").collect()
    catalog = DockerRuntimeCatalogBuilder().build(observation)

    output_path = DockerCatalogArtifactGenerator().generate(
        catalog=catalog,
        output_path=Path("reports/generated/docker-runtime-catalog.json"),
    )

    print(f"Docker runtime catalog written to {output_path}")


if __name__ == "__main__":
    main()
