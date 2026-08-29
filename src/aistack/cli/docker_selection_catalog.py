from __future__ import annotations

from pathlib import Path

from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.generators.catalog_view import CatalogViewArtifactGenerator
from aistack.kernel.bootstrap import create_kernel


def main() -> None:
    """
    Infrastructure Data Catalog → Catalog View Engine → consumer.

    **ADR-0002's flow, on a path that runs.** Both halves of that
    sentence were repaired on 2026-08-29: the type, under
    GOV-0002/OS-042, and the ability to execute at all, under
    GOV-0002/OS-044.

    The engine is **retrieved from the Kernel registry by
    identifier** rather than instantiated. That is what makes the
    producer governed knowledge instead of a class name written
    in a command — and it gives `catalog_views` its first read
    site, which `unused-registrations` had reported as a registry
    written to and never read.
    """

    ctx = create_kernel()
    observation = ctx.registries.providers.get("docker").collect()
    catalog = DockerRuntimeCatalogBuilder().build(observation)
    view = ctx.registries.catalog_views.get("docker-containers").build(catalog)

    output_path = CatalogViewArtifactGenerator().generate(
        view=view,
        output_path=Path("reports/generated/docker-selection-catalog.json"),
    )

    print(f"Docker container catalog view written to {output_path}")


if __name__ == "__main__":
    main()
