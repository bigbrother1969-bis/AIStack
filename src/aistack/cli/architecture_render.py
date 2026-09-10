from __future__ import annotations

from pathlib import Path

from aistack.architecture.graph import build_architecture_graph
from aistack.architecture.views import build_all_views
from aistack.architecture.yaml import load_service_categorization_yaml
from aistack.catalog.compose import ComposeRuntimeCatalogBuilder
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.generators.architecture import ArchitectureHtmlArtifactGenerator
from aistack.kernel.bootstrap import create_kernel

# Same convention as `resource_priority_monitor.py`'s own
# `DEFAULT_DEFINITION` — a `Path(__file__).resolve()`-relative default,
# not `importlib.resources`. `GOV-0002/OS-056` is what makes this safe
# to rely on from a real, installed distribution and not only an
# editable one.
DEFAULT_CATEGORIZATION = (
    Path(__file__).resolve().parents[1]
    / "architecture"
    / "definitions"
    / "service_categorization.yml"
)


def main() -> None:
    """
    J2 step 6 (`claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`): the
    CLI wiring steps 3-5 built and tested against fixtures, run for
    real against GIGABYTE's own Docker and Compose catalogs.

    **Two providers, one categorization, one graph.** Both catalogs
    are built the same way their own single-purpose CLIs
    (`docker_catalog.py`, `compose_catalog.py`) already build them —
    this command does not duplicate that logic, it composes it with
    `build_architecture_graph`, which is what step 3 exists for.
    """

    ctx = create_kernel()

    docker_observation = ctx.registries.providers.get("docker").collect()
    docker_catalog = DockerRuntimeCatalogBuilder().build(docker_observation)

    compose_observation = ctx.registries.providers.get("compose").collect()
    compose_catalog = ComposeRuntimeCatalogBuilder().build(compose_observation)

    categorization = load_service_categorization_yaml(DEFAULT_CATEGORIZATION)

    graph = build_architecture_graph(categorization, docker_catalog, compose_catalog)
    views = build_all_views(graph)

    output_path = ArchitectureHtmlArtifactGenerator().generate(
        views=views,
        output_path=Path("reports/generated/architecture.html"),
    )

    print(f"Architecture diagram written to {output_path}")


if __name__ == "__main__":
    main()
