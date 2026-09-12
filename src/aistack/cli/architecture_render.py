from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from aistack.architecture.beszel_reading import build_beszel_readings
from aistack.architecture.dependency_graph import build_dependency_graph
from aistack.architecture.graph import build_architecture_graph
from aistack.architecture.views import build_all_views
from aistack.architecture.yaml import (
    load_infrastructure_topology_yaml,
    load_service_categorization_yaml,
)
from aistack.catalog.compose import ComposeRuntimeCatalogBuilder
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.generators.architecture import ArchitectureHtmlArtifactGenerator
from aistack.generators.beszel import BeszelObservationArtifactGenerator
from aistack.kernel.bootstrap import create_kernel
from aistack.providers.beszel import BeszelProvider

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

# Added 2026-09-12 (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10) — same
# convention, alongside `service_categorization.yml`.
DEFAULT_TOPOLOGY = (
    Path(__file__).resolve().parents[1]
    / "architecture"
    / "definitions"
    / "infrastructure_topology.yml"
)


def main(environ: Mapping[str, str] | None = None) -> None:
    """
    J2 step 6 (`claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`): the
    CLI wiring steps 3-5 built and tested against fixtures, run for
    real against GIGABYTE's own Docker and Compose catalogs.

    **Two providers, one categorization, one graph.** Both catalogs
    are built the same way their own single-purpose CLIs
    (`docker_catalog.py`, `compose_catalog.py`) already build them —
    this command does not duplicate that logic, it composes it with
    `build_architecture_graph`, which is what step 3 exists for.

    **A third, optional provider, added 2026-09-12** (§10, last
    bullet): if `infrastructure_topology.yml` declares a `beszel:`
    block, its two env var names are read from `environ` (real
    `os.environ` by default, injectable for tests — same convention
    `jellyfin_discover.main`/`syncthing_discover.main` already use)
    and handed to `BeszelProvider`. Unlike the Docker/Compose
    providers, Beszel being unreachable or unconfigured is never
    fatal: `build_beszel_readings` on an empty/failed observation's
    `systems` list is simply `()`, and `render_html` renders no
    "État en direct" section at all — the same "nothing to show"
    degradation the topology sub-blocks already have.

    **A dependency graph, same day** (§10, third gap): `ComposeProvider`
    itself now reads each project's real `depends_on:`, so no
    additional provider call is needed here — `build_dependency_graph`
    reads it straight off the already-built `compose_catalog`. A
    project with no `depends_on:` anywhere is simply absent from the
    graph; `render_html` adds no "Dépendances" view at all when the
    graph carries no project — the same "nothing to show" degradation.
    """

    environ = os.environ if environ is None else environ

    ctx = create_kernel()

    docker_observation = ctx.registries.providers.get("docker").collect()
    docker_catalog = DockerRuntimeCatalogBuilder().build(docker_observation)

    compose_observation = ctx.registries.providers.get("compose").collect()
    compose_catalog = ComposeRuntimeCatalogBuilder().build(compose_observation)

    categorization = load_service_categorization_yaml(DEFAULT_CATEGORIZATION)
    topology = load_infrastructure_topology_yaml(DEFAULT_TOPOLOGY)

    graph = build_architecture_graph(categorization, docker_catalog, compose_catalog)
    views = build_all_views(graph)
    dependency_graph = build_dependency_graph(compose_catalog)

    beszel_readings: tuple = ()

    if topology.beszel is not None:
        email = environ.get(topology.beszel.email_env, "")
        password = environ.get(topology.beszel.password_env, "")

        beszel_observation = BeszelProvider(
            topology.beszel.url, email, password
        ).collect()

        BeszelObservationArtifactGenerator().generate(
            observation=beszel_observation,
            output_path=Path("reports/generated/beszel-observation.json"),
        )

        beszel_readings = build_beszel_readings(
            beszel_observation["beszel"]["systems"]
        )

    output_path = ArchitectureHtmlArtifactGenerator().generate(
        views=views,
        output_path=Path("reports/generated/architecture.html"),
        topology=topology,
        beszel_readings=beszel_readings,
        dependency_graph=dependency_graph,
    )

    print(f"Architecture diagram written to {output_path}")


if __name__ == "__main__":
    main()
