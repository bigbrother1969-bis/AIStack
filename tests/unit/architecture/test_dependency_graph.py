from aistack.architecture.dependency_graph import (
    ComposeProjectDependencies,
    ContainerDependencyEdge,
    DependencyGraph,
    build_dependency_graph,
)
from aistack.kernel.catalog import Catalog, CatalogItem


def catalog(*items: CatalogItem) -> Catalog:
    return Catalog(
        catalog_id="compose-runtime",
        title="Docker Compose Runtime Catalog",
        items=items,
    )


def project_item(
    name: str, containers: str = "", dependency_edges: str = "", kind: str = "compose-project"
) -> CatalogItem:
    return CatalogItem(
        id=name,
        label=name,
        kind=kind,
        metadata={"containers": containers, "dependency_edges": dependency_edges},
    )


# --------------------------------------------------------------------
# The real, common case
# --------------------------------------------------------------------


def test_a_project_with_edges_is_included():
    graph = build_dependency_graph(
        catalog(
            project_item(
                "bookstack",
                containers="bookstack,bookstack_db",
                dependency_edges="bookstack->bookstack_db",
            )
        )
    )

    assert len(graph.projects) == 1
    project = graph.projects[0]
    assert project.project == "bookstack"
    assert project.containers == ("bookstack", "bookstack_db")
    assert project.edges == (
        ContainerDependencyEdge("bookstack", "bookstack_db"),
    )


def test_several_edges_are_all_carried():
    graph = build_dependency_graph(
        catalog(
            project_item(
                "immich",
                containers="immich_postgres,immich_redis,immich_server",
                dependency_edges=(
                    "immich_server->immich_postgres,"
                    "immich_server->immich_redis"
                ),
            )
        )
    )

    assert graph.projects[0].edges == (
        ContainerDependencyEdge("immich_server", "immich_postgres"),
        ContainerDependencyEdge("immich_server", "immich_redis"),
    )


# --------------------------------------------------------------------
# "Nothing observed, nothing rendered"
# --------------------------------------------------------------------


def test_a_project_with_no_dependency_edges_is_absent_from_the_graph():
    graph = build_dependency_graph(
        catalog(project_item("jellyfin", containers="jellyfin", dependency_edges=""))
    )

    assert graph.projects == ()


def test_a_catalog_item_that_is_not_a_compose_project_is_ignored():
    graph = build_dependency_graph(
        catalog(
            project_item(
                "not-a-project",
                containers="a,b",
                dependency_edges="a->b",
                kind="container",
            )
        )
    )

    assert graph.projects == ()


def test_an_empty_catalog_yields_an_empty_graph():
    graph = build_dependency_graph(catalog())

    assert graph == DependencyGraph()
    assert graph.projects == ()


# --------------------------------------------------------------------
# Determinism — project order is not trusted from the catalog
# --------------------------------------------------------------------


def test_projects_are_sorted_by_name_regardless_of_catalog_order():
    graph = build_dependency_graph(
        catalog(
            project_item("zzz", containers="z1,z2", dependency_edges="z1->z2"),
            project_item("aaa", containers="a1,a2", dependency_edges="a1->a2"),
        )
    )

    assert [project.project for project in graph.projects] == ["aaa", "zzz"]


# --------------------------------------------------------------------
# Tolerance — a governed `Catalog`'s own metadata, but still parsed
# defensively rather than trusted blindly
# --------------------------------------------------------------------


def test_a_missing_metadata_key_reads_as_empty_not_a_raise():
    graph = build_dependency_graph(
        catalog(
            CatalogItem(id="bare", label="bare", kind="compose-project", metadata={})
        )
    )

    assert graph.projects == ()


def test_malformed_edge_chunks_without_an_arrow_are_skipped():
    graph = build_dependency_graph(
        catalog(
            project_item(
                "odd",
                containers="a,b",
                dependency_edges="a->b,not-an-edge,",
            )
        )
    )

    assert graph.projects[0].edges == (ContainerDependencyEdge("a", "b"),)


def test_an_edge_with_a_blank_side_is_skipped():
    graph = build_dependency_graph(
        catalog(
            project_item(
                "odd",
                containers="a",
                dependency_edges="a->,->a,a->a",
            )
        )
    )

    assert graph.projects[0].edges == (ContainerDependencyEdge("a", "a"),)


def test_the_containers_metadata_is_split_and_trimmed():
    graph = build_dependency_graph(
        catalog(
            project_item(
                "spaced",
                containers=" a , b ,,c",
                dependency_edges="a->b",
            )
        )
    )

    assert graph.projects[0].containers == ("a", "b", "c")


# --------------------------------------------------------------------
# The dataclasses default to empty when built directly
# --------------------------------------------------------------------


def test_dataclasses_default_to_empty_when_built_directly():
    assert DependencyGraph().projects == ()
    assert ComposeProjectDependencies(project="x").containers == ()
    assert ComposeProjectDependencies(project="x").edges == ()
