from aistack.architecture.definition import (
    ServiceCategorizationDefinition,
    ServiceCategoryDefinition,
    ServiceDefinition,
)
from aistack.architecture.graph import (
    ArchitectureGraph,
    ServiceStatus,
    build_architecture_graph,
)
from aistack.kernel.catalog import Catalog, CatalogItem


def docker_catalog(*container_names: str) -> Catalog:
    return Catalog(
        catalog_id="docker-runtime",
        title="Docker Runtime Catalog",
        items=tuple(
            CatalogItem(id=name, label=name, kind="container")
            for name in container_names
        ),
    )


def compose_catalog(**projects: str) -> Catalog:
    """Each keyword is a project name; its value is a comma-joined
    `containers` string, mirroring `ComposeRuntimeCatalogBuilder`'s
    own output shape."""

    return Catalog(
        catalog_id="compose-runtime",
        title="Docker Compose Runtime Catalog",
        items=tuple(
            CatalogItem(
                id=project,
                label=project,
                kind="compose-project",
                metadata={"containers": containers},
            )
            for project, containers in projects.items()
        ),
    )


def categorization(*categories: ServiceCategoryDefinition) -> ServiceCategorizationDefinition:
    return ServiceCategorizationDefinition(categories=tuple(categories))


def category(name: str, *services: ServiceDefinition) -> ServiceCategoryDefinition:
    return ServiceCategoryDefinition(name=name, services=tuple(services))


def test_a_service_with_no_container_is_marked_no_container():
    graph = build_architecture_graph(
        categorization(category("Supervision", ServiceDefinition(name="Pi-hole"))),
        docker_catalog(),
        compose_catalog(),
    )

    node = graph.categories[0].services[0]
    assert node.name == "Pi-hole"
    assert node.category == "Supervision"
    assert node.container is None
    assert node.status == ServiceStatus.NO_CONTAINER
    assert node.compose_project is None


def test_a_container_belonging_to_a_compose_project_is_marked_in_compose_project():
    graph = build_architecture_graph(
        categorization(
            category(
                "AIStack",
                ServiceDefinition(name="AIStack Core", container="aistack-core"),
            )
        ),
        docker_catalog("aistack-core"),
        compose_catalog(aistack="aistack-core,aistack-selection-ui"),
    )

    node = graph.categories[0].services[0]
    assert node.status == ServiceStatus.IN_COMPOSE_PROJECT
    assert node.compose_project == "aistack"


def test_a_container_observed_but_in_no_known_compose_project_is_marked_observed():
    graph = build_architecture_graph(
        categorization(
            category(
                "Développement",
                ServiceDefinition(name="Gitea", container="gitea"),
            )
        ),
        docker_catalog("gitea"),
        compose_catalog(),
    )

    node = graph.categories[0].services[0]
    assert node.status == ServiceStatus.OBSERVED
    assert node.compose_project is None


def test_a_declared_container_neither_catalog_has_seen_is_declared_not_observed():
    """
    The Raspberry Pi's own services — Pi-hole, Uptime Kuma, NPM — name
    a container in `homepage/services.yaml`, but AIStack's one Docker
    provider only observes GIGABYTE, so they exist here as a name with
    nothing behind it.
    """

    graph = build_architecture_graph(
        categorization(
            category(
                "Administration, Cloud & Utilitaires",
                ServiceDefinition(name="Nginx Proxy Manager", container="npm"),
            )
        ),
        docker_catalog("portainer"),
        compose_catalog(),
    )

    node = graph.categories[0].services[0]
    assert node.status == ServiceStatus.DECLARED_NOT_OBSERVED
    assert node.compose_project is None


def test_compose_project_membership_is_checked_before_plain_observation():
    """
    A container can be both live in the Docker Catalog and named by a
    Compose project — `docker ps -a` and a project's own
    `docker-compose.yml` are not mutually exclusive facts. Project
    membership is the stronger one and wins, so the status is
    `IN_COMPOSE_PROJECT`, never `OBSERVED`.
    """

    graph = build_architecture_graph(
        categorization(
            category(
                "AIStack",
                ServiceDefinition(name="AIStack Core", container="aistack-core"),
            )
        ),
        docker_catalog("aistack-core"),
        compose_catalog(aistack="aistack-core"),
    )

    assert graph.categories[0].services[0].status == ServiceStatus.IN_COMPOSE_PROJECT


def test_a_compose_projects_container_need_not_be_currently_running():
    """
    `DockerRuntimeCatalogBuilder` observes with `docker ps -a` —
    stopped containers included — but project membership is decided
    from the Compose Catalog alone, so a container absent from the
    Docker Catalog entirely (stopped so long it was pruned, or simply
    not passed to this test's fixture) still resolves as
    `IN_COMPOSE_PROJECT` once its project names it.
    """

    graph = build_architecture_graph(
        categorization(
            category(
                "AIStack",
                ServiceDefinition(name="AIStack Core", container="aistack-core"),
            )
        ),
        docker_catalog(),
        compose_catalog(aistack="aistack-core"),
    )

    assert graph.categories[0].services[0].status == ServiceStatus.IN_COMPOSE_PROJECT


def test_only_container_kind_catalog_items_count_as_observed():
    """
    An image, network or volume sharing a container's own name is not
    the container existing — `DockerRuntimeCatalogBuilder` gives each
    family its own identifier space (`kind`), and this builder must
    respect that separation rather than matching on `id` alone.
    """

    graph = build_architecture_graph(
        categorization(
            category(
                "Développement",
                ServiceDefinition(name="Gitea", container="gitea"),
            )
        ),
        Catalog(
            catalog_id="docker-runtime",
            title="Docker Runtime Catalog",
            items=(CatalogItem(id="gitea", label="gitea", kind="image"),),
        ),
        compose_catalog(),
    )

    assert (
        graph.categories[0].services[0].status
        == ServiceStatus.DECLARED_NOT_OBSERVED
    )


def test_an_empty_containers_field_on_a_compose_project_matches_nothing():
    graph = build_architecture_graph(
        categorization(
            category(
                "Développement",
                ServiceDefinition(name="Gitea", container="gitea"),
            )
        ),
        docker_catalog(),
        compose_catalog(empty=""),
    )

    assert (
        graph.categories[0].services[0].status
        == ServiceStatus.DECLARED_NOT_OBSERVED
    )


def test_multiple_categories_each_carry_their_own_services():
    graph = build_architecture_graph(
        categorization(
            category(
                "Supervision", ServiceDefinition(name="Beszel", container="beszel")
            ),
            category(
                "Développement", ServiceDefinition(name="Gitea", container="gitea")
            ),
        ),
        docker_catalog("beszel", "gitea"),
        compose_catalog(),
    )

    assert isinstance(graph, ArchitectureGraph)
    assert [c.name for c in graph.categories] == ["Supervision", "Développement"]
    assert graph.categories[0].services[0].name == "Beszel"
    assert graph.categories[1].services[0].name == "Gitea"


def test_icon_href_and_description_travel_straight_through_regardless_of_status():
    """
    `icon`/`href`/`description` are a plain pass-through (`graph.py`'s
    own docstring: "nothing here joins them against a catalog") —
    unlike `status`, they must not vary with what the catalogs
    observed. Checked across two services deliberately landing on
    different statuses (`NO_CONTAINER` and `DECLARED_NOT_OBSERVED`),
    so a future change coupling them to `container`/`status` by
    accident is caught here.
    """

    graph = build_architecture_graph(
        categorization(
            category(
                "Supervision",
                ServiceDefinition(
                    name="Pi-hole",
                    icon="pi-hole",
                    href="https://pihole.persiaut-family.fr/admin",
                    description="Gestionnaire de DNS + Blocage de publicités",
                ),
                ServiceDefinition(
                    name="Nginx Proxy Manager",
                    container="npm",
                    icon="nginx-proxy-manager",
                    href="https://npm.persiaut-family.fr",
                    description="Gestionnaire des Proxy Hosts",
                ),
            )
        ),
        docker_catalog(),
        compose_catalog(),
    )

    pihole, npm = graph.categories[0].services

    assert pihole.status == ServiceStatus.NO_CONTAINER
    assert pihole.icon == "pi-hole"
    assert pihole.href == "https://pihole.persiaut-family.fr/admin"
    assert pihole.description == "Gestionnaire de DNS + Blocage de publicités"

    assert npm.status == ServiceStatus.DECLARED_NOT_OBSERVED
    assert npm.icon == "nginx-proxy-manager"
    assert npm.href == "https://npm.persiaut-family.fr"
    assert npm.description == "Gestionnaire des Proxy Hosts"


def test_icon_href_and_description_default_to_none():
    graph = build_architecture_graph(
        categorization(category("Supervision", ServiceDefinition(name="Pi-hole"))),
        docker_catalog(),
        compose_catalog(),
    )

    node = graph.categories[0].services[0]
    assert node.icon is None
    assert node.href is None
    assert node.description is None


def test_an_empty_categorization_produces_an_empty_graph():
    graph = build_architecture_graph(
        categorization(), docker_catalog(), compose_catalog()
    )

    assert graph.categories == ()


def test_the_real_categorization_joins_against_a_live_shaped_catalog_pair():
    """
    Not a fixture round-trip — a sanity check that the real, shipped
    categorization (47 services, `test_the_real_service_categorization_
    loads`) still joins cleanly against catalog shapes matching
    `DockerRuntimeCatalogBuilder`/`ComposeRuntimeCatalogBuilder`'s own
    output, so a future field rename in either builder is caught here
    rather than only once this runs against the real GIGABYTE catalogs
    (step 6).
    """

    from pathlib import Path

    from aistack.architecture.yaml import load_service_categorization_yaml

    repo_root = Path(__file__).resolve().parents[3]
    real_categorization = load_service_categorization_yaml(
        repo_root
        / "src"
        / "aistack"
        / "architecture"
        / "definitions"
        / "service_categorization.yml"
    )

    graph = build_architecture_graph(
        real_categorization,
        docker_catalog("npm", "jellyfin"),
        compose_catalog(),
    )

    all_services = [
        service for cat in graph.categories for service in cat.services
    ]
    assert len(all_services) == 47

    by_name = {service.name: service for service in all_services}

    assert by_name["Nginx Proxy Manager"].status == ServiceStatus.OBSERVED
    assert by_name["Jellyfin"].status == ServiceStatus.OBSERVED
    assert by_name["Pi-hole"].status == ServiceStatus.NO_CONTAINER
    assert by_name["Portainer"].status == ServiceStatus.DECLARED_NOT_OBSERVED
