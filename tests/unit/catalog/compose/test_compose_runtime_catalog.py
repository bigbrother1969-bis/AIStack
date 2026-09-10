from aistack.catalog.compose import ComposeRuntimeCatalogBuilder
from aistack.kernel.catalog import Catalog


def observation(*projects: dict) -> dict:
    return {
        "provider": {"id": "aistack.provider.compose"},
        "collected_at": "2026-09-10T09:00:00+00:00",
        "compose": {"projects": list(projects)},
    }


def project(name: str, **services: dict) -> dict:
    return {
        "name": name,
        "working_dir": f"/srv/{name}",
        "config_files": "docker-compose.yml",
        "services": services,
    }


def test_the_builder_returns_a_governed_catalog():
    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(project("aistack", web={"container_name": "aistack-core"}))
    )

    assert isinstance(catalog, Catalog)
    assert catalog.catalog_id == "compose-runtime"
    assert catalog.metadata["source_provider"] == "aistack.provider.compose"
    assert catalog.metadata["collected_at"] == "2026-09-10T09:00:00+00:00"


def test_items_is_a_tuple_matching_what_catalog_declares():
    """
    `Catalog.items: tuple[CatalogItem, ...]` — until 2026-09-10 this
    builder passed a list comprehension instead, which Python's own
    dataclass machinery accepts without complaint (a declared field
    type is not enforced at runtime). `mypy` found the mismatch on
    its first run against this codebase.
    """

    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(project("aistack", web={"container_name": "aistack-core"}))
    )

    assert isinstance(catalog.items, tuple)


def test_a_project_carries_its_own_container_membership():
    """
    Until 2026-09-10 a project's `services` collapsed to a count —
    `service_count` — and the container names themselves were
    discarded, even though `ComposeProvider.collect()` already
    resolves one per service. Rendering VS-4's own reference
    deployment as a diagram (`PLAN-TRAJECTOIRE-2026-09-04` J2) needs
    exactly this edge: which containers belong to which project.
    """

    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(
            project(
                "aistack",
                core={"container_name": "aistack-core"},
                ui={"container_name": "aistack-selection-ui"},
            )
        )
    )

    project_item = catalog.items[0]
    assert project_item.metadata["service_count"] == "2"
    assert (
        project_item.metadata["containers"]
        == "aistack-core,aistack-selection-ui"
    )


def test_container_membership_is_sorted_regardless_of_service_order():
    """
    `project["services"]` iterates in `docker ps` order, which
    `DockerRuntimeCatalogBuilder` already found unstable across two
    calls with no host change (`STD-0300`/VS-1 criterion 1.3, the
    `mounts` and `images` fields). The same instability applies
    here: sorted so regeneration is deterministic (`ARC-P-006`).
    """

    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(
            project(
                "aistack",
                ui={"container_name": "aistack-selection-ui"},
                core={"container_name": "aistack-core"},
            )
        )
    )

    assert (
        catalog.items[0].metadata["containers"]
        == "aistack-core,aistack-selection-ui"
    )


def test_a_service_with_no_container_name_is_not_counted_as_a_container():
    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(project("aistack", web={}))
    )

    assert catalog.items[0].metadata["containers"] == ""


def test_duplicate_container_names_across_services_are_not_repeated():
    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(
            project(
                "aistack",
                a={"container_name": "aistack-core"},
                b={"container_name": "aistack-core"},
            )
        )
    )

    assert catalog.items[0].metadata["containers"] == "aistack-core"
