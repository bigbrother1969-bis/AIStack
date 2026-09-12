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


# --------------------------------------------------------------------
# `dependency_edges` — added 2026-09-12
# (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, third gap)
# --------------------------------------------------------------------


def test_a_depends_on_resolves_to_a_container_to_container_edge():
    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(
            project(
                "bookstack",
                bookstack={
                    "container_name": "bookstack",
                    "depends_on": ["bookstack_db"],
                },
                bookstack_db={"container_name": "bookstack_db"},
            )
        )
    )

    assert (
        catalog.items[0].metadata["dependency_edges"]
        == "bookstack->bookstack_db"
    )


def test_a_project_with_no_depends_on_anywhere_has_no_edges():
    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(project("aistack", web={"container_name": "aistack-core"}))
    )

    assert catalog.items[0].metadata["dependency_edges"] == ""


def test_a_depends_on_naming_a_service_not_observed_as_a_container_is_dropped():
    """
    `depends_on` can name a service Compose declares but that is not
    (or no longer) running — `ComposeProvider` itself already only
    records a `depends_on` for a service it *did* observe (the
    depending side); this is the other side of the same discipline:
    an edge to a container nothing here has ever seen is not
    asserted (`ARC-P-012`), the target service is simply absent from
    `services` in the first place in this fixture, matching what a
    stopped/removed sidecar would look like.
    """

    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(
            project(
                "aistack",
                web={
                    "container_name": "aistack-core",
                    "depends_on": ["a-service-that-does-not-exist"],
                },
            )
        )
    )

    assert catalog.items[0].metadata["dependency_edges"] == ""


def test_several_edges_are_sorted_and_comma_joined():
    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(
            project(
                "immich",
                server={
                    "container_name": "immich_server",
                    "depends_on": ["redis", "database"],
                },
                redis={"container_name": "immich_redis"},
                database={"container_name": "immich_postgres"},
            )
        )
    )

    assert catalog.items[0].metadata["dependency_edges"] == (
        "immich_server->immich_postgres,immich_server->immich_redis"
    )


def test_a_service_with_no_depends_on_key_contributes_no_edge():
    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(
            project(
                "aistack",
                web={"container_name": "aistack-core"},
                db={"container_name": "aistack-db"},
            )
        )
    )

    assert catalog.items[0].metadata["dependency_edges"] == ""


def test_a_service_depending_on_itself_is_still_recorded_as_an_edge():
    """
    Not observed on GIGABYTE, but nothing in `ComposeProvider` or
    this builder rules it out, and a real Compose file could still
    declare it (a typo, most likely) — recorded rather than silently
    dropped, since dropping it would hide the very mistake this graph
    would otherwise surface.
    """

    catalog = ComposeRuntimeCatalogBuilder().build(
        observation(
            project(
                "odd",
                web={
                    "container_name": "odd-web",
                    "depends_on": ["web"],
                },
            )
        )
    )

    assert catalog.items[0].metadata["dependency_edges"] == "odd-web->odd-web"
