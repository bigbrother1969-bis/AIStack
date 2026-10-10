from __future__ import annotations

from aistack.config import configured

import os
from collections.abc import Mapping
from pathlib import Path

from aistack.architecture.beszel_reading import build_beszel_readings
from aistack.architecture.dependency_graph import build_dependency_graph
from aistack.architecture.graph import build_architecture_graph
from aistack.architecture.http_probe_reading import build_http_probe_readings
from aistack.architecture.views import build_all_views
from aistack.architecture.yaml import (
    load_cmdb_probe_targets_yaml,
    load_infrastructure_topology_yaml,
    load_service_categorization_yaml,
)
from aistack.catalog.compose import ComposeRuntimeCatalogBuilder
from aistack.catalog.docker import DockerRuntimeCatalogBuilder
from aistack.generators.architecture import ArchitectureHtmlArtifactGenerator
from aistack.generators.beszel import BeszelObservationArtifactGenerator
from aistack.generators.http_probe import HttpProbeObservationArtifactGenerator
from aistack.i18n import default_languages
from aistack.i18n.pages import page_file
from aistack.kernel.bootstrap import create_kernel
from aistack.providers.beszel import BeszelProvider
from aistack.providers.http_probe import HttpProbeProvider

DEFAULT_CATEGORIZATION = (
    configured(Path(__file__).resolve().parents[1]
    / "architecture"
    / "definitions"
    / "service_categorization.yml")
)

DEFAULT_TOPOLOGY = (
    configured(Path(__file__).resolve().parents[1]
    / "architecture"
    / "definitions"
    / "infrastructure_topology.yml")
)

DEFAULT_CMDB_TARGETS = (
    configured(Path(__file__).resolve().parents[1]
    / "architecture"
    / "definitions"
    / "cmdb_probe_targets.yml")
)


def main(environ: Mapping[str, str] | None = None) -> None:
    """
    Render `architecture.html` from the Docker and Compose catalogs and the categorization.

    Optional live sections: Beszel, when `infrastructure_topology.yml`
    declares a `beszel:` block (credentials read from `environ` under
    the names it gives), and HTTP probes of the targets in
    `cmdb_probe_targets.yml`. An unreachable or undeclared source is
    never fatal; its section is simply left out, as is the dependency
    view when no Compose project declares `depends_on:`.
    """

    environ = os.environ if environ is None else environ

    ctx = create_kernel()

    docker_observation = ctx.registries.providers.get("docker").collect()
    docker_catalog = DockerRuntimeCatalogBuilder().build(docker_observation)

    compose_observation = ctx.registries.providers.get("compose").collect()
    compose_catalog = ComposeRuntimeCatalogBuilder().build(compose_observation)

    categorization = load_service_categorization_yaml(DEFAULT_CATEGORIZATION)
    topology = load_infrastructure_topology_yaml(DEFAULT_TOPOLOGY)
    cmdb_targets = load_cmdb_probe_targets_yaml(DEFAULT_CMDB_TARGETS)

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

    cmdb_readings: tuple = ()

    if cmdb_targets:
        http_probe_observation = HttpProbeProvider(
            tuple((target.name, target.url) for target in cmdb_targets)
        ).collect()

        HttpProbeObservationArtifactGenerator().generate(
            observation=http_probe_observation,
            output_path=Path("reports/generated/http-probe-observation.json"),
        )

        cmdb_readings = build_http_probe_readings(
            http_probe_observation["http_probe"]["targets"]
        )

    # ADR-0010 § 5: one page per declared language from the same readings;
    # the reference language keeps `architecture.html`.
    languages = default_languages()
    generated_dir = Path("reports/generated")
    written: list[str] = []

    for language in languages.available:
        path = ArchitectureHtmlArtifactGenerator().generate(
            views=views,
            output_path=page_file(
                generated_dir, "architecture.html", language.code, languages.reference
            ),
            topology=topology,
            beszel_readings=beszel_readings,
            dependency_graph=dependency_graph,
            cmdb_readings=cmdb_readings,
            lang=language.code,
        )
        written.append(path.name)

    output_path = generated_dir / "architecture.html"

    print(
        f"Architecture diagram written to {output_path} "
        f"({', '.join(written)})"
    )


if __name__ == "__main__":
    main()
